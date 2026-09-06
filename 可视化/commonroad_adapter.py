"""Bounded CommonRoad XML -> Frenet prototype adapter.

The adapter intentionally exposes two explicit modes.  The legacy smoke mode
uses lanelet centerlines, successor routing, point/rectangle initial states,
and constant-velocity obstacle projections.  The native-boundary mode can use
the official reference polyline, project every published dynamic-obstacle
state, and retain the sampled Frenet center trajectory.  Neither mode claims
full CommonRoad occupancy, shape/orientation, rule, or dynamic-model fidelity.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import math
import xml.etree.ElementTree as ET

import numpy as np

from apollo_pipeline import Ego, Obstacle, Scenario


MAX_CENTERLINE_RESIDUAL_M = 6.0


@dataclass(frozen=True)
class CommonRoadAdapterResult:
    scenario: Scenario
    route_polyline: np.ndarray
    initial_time_step: int
    planning_problem_id: int | str
    benchmark_id: str
    route_lanelet_ids: tuple[str, ...]
    source_lanelets: int
    source_dynamic_obstacles: int
    projected_obstacles: int
    skipped_obstacles: int
    trajectory_states_used: int
    occupancy_obstacles: int
    occupancy_samples: int
    planner_relevant_obstacles: int
    route_irrelevant_obstacles: int
    route_l_min: float
    route_l_max: float
    maximum_projection_residual_m: float
    limitations: tuple[str, ...]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local(child.tag) == name]


def _first(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    for child in list(element):
        if _local(child.tag) == name:
            return child
    return None


def _descendant(element: ET.Element | None, *names: str) -> ET.Element | None:
    current = element
    for name in names:
        current = next(
            (node for node in current.iter() if _local(node.tag) == name), None
        ) if current is not None else None
    return current


def _number(element: ET.Element | None, default: float | None = None) -> float | None:
    if element is None or element.text is None:
        return default
    try:
        return float(element.text)
    except ValueError:
        return default


def _point_list(bound: ET.Element | None) -> np.ndarray:
    if bound is None:
        return np.empty((0, 2), dtype=float)
    points = []
    for point in _children(bound, "point"):
        x = _number(_first(point, "x"))
        y = _number(_first(point, "y"))
        if x is not None and y is not None:
            points.append((x, y))
    return np.asarray(points, dtype=float)


def _resample(points: np.ndarray, count: int) -> np.ndarray:
    if len(points) == count:
        return points
    if len(points) < 2:
        raise ValueError("lanelet bound must contain at least two points")
    parameter = np.linspace(0.0, 1.0, len(points))
    target = np.linspace(0.0, 1.0, count)
    return np.column_stack(
        [np.interp(target, parameter, points[:, coordinate]) for coordinate in range(2)]
    )


def _centerline(lanelet: ET.Element) -> np.ndarray:
    left = _point_list(_first(lanelet, "leftBound"))
    right = _point_list(_first(lanelet, "rightBound"))
    count = max(len(left), len(right))
    if count < 2:
        raise ValueError(f"lanelet {lanelet.attrib.get('id')} has incomplete bounds")
    return (_resample(left, count) + _resample(right, count)) / 2.0


def _nearest_lanelets(
    centerlines: dict[str, np.ndarray], point: np.ndarray, limit: int = 20
) -> tuple[str, ...]:
    ordered = sorted(
        centerlines,
        key=lambda lanelet_id: float(
            np.min(np.linalg.norm(centerlines[lanelet_id] - point, axis=1))
        ),
    )
    return tuple(ordered[:limit])


def _route(
    successors: dict[str, tuple[str, ...]], start: str, goal: str
) -> tuple[str, ...]:
    queue: deque[str] = deque([start])
    previous: dict[str, str | None] = {start: None}
    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for successor in successors.get(current, ()):
            if successor not in previous:
                previous[successor] = current
                queue.append(successor)
    if goal not in previous:
        raise ValueError(f"no successor route between lanelets {start} and {goal}")
    route: list[str] = []
    current: str | None = goal
    while current is not None:
        route.append(current)
        current = previous[current]
    return tuple(reversed(route))


def _polyline_for_route(
    centerlines: dict[str, np.ndarray], route: tuple[str, ...]
) -> np.ndarray:
    pieces = []
    for lanelet_id in route:
        centerline = centerlines[lanelet_id]
        pieces.append(centerline if not pieces else centerline[1:])
    polyline = np.vstack(pieces)
    if np.any(np.linalg.norm(np.diff(polyline, axis=0), axis=1) < 1e-6):
        raise ValueError("route centerline contains duplicate points")
    return polyline


def _project(polyline: np.ndarray, point: np.ndarray) -> tuple[float, float, float]:
    starts = polyline[:-1]
    vectors = np.diff(polyline, axis=0)
    lengths = np.linalg.norm(vectors, axis=1)
    unit = vectors / lengths[:, None]
    offsets = point[None, :] - starts
    fraction = np.clip(np.sum(offsets * vectors, axis=1) / lengths**2, 0.0, 1.0)
    projections = starts + fraction[:, None] * vectors
    distances = np.linalg.norm(point[None, :] - projections, axis=1)
    index = int(np.argmin(distances))
    station = float(np.sum(lengths[:index]) + fraction[index] * lengths[index])
    projection = projections[index]
    # Preserve a signed station outside the route endpoints.  Clamping every
    # point to s=0 made vehicles behind the route look like obstacles at the
    # ego's current station and could create an immediately negative ST bound.
    # Only the first/last segment is extrapolated; interior segments retain the
    # usual closest-point projection.
    if index == 0 and fraction[index] <= 1e-12:
        longitudinal = float(np.dot(point - starts[index], unit[index]))
        if longitudinal < 0.0:
            station = longitudinal
            projection = starts[index] + longitudinal * unit[index]
    elif index == len(lengths) - 1 and fraction[index] >= 1.0 - 1e-12:
        longitudinal = float(np.dot(point - starts[index], unit[index]))
        if longitudinal > lengths[index]:
            station = float(np.sum(lengths[:-1]) + longitudinal)
            projection = starts[index] + longitudinal * unit[index]
    signed_lateral = float(
        unit[index, 0] * (point[1] - projection[1])
        - unit[index, 1] * (point[0] - projection[0])
    )
    return station, signed_lateral, float(np.linalg.norm(point - projection))


def _lanelet_cross_section_profiles(
    lanelets: dict[str, ET.Element], polyline: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Intersect local reference normals with the connected drivable road.

    Projecting and globally sorting boundary vertices mixes branches at
    junctions.  A local normal cross-section instead selects the connected
    lanelet interval containing the reference point, then unions directly
    adjacent intervals.  This represents the road polygon actually available
    to the vehicle at each station.
    """
    polygons = []
    for lanelet in lanelets.values():
        left = _point_list(_first(lanelet, "leftBound"))
        right = _point_list(_first(lanelet, "rightBound"))
        if len(left) >= 2 and len(right) >= 2:
            polygons.append(np.vstack([left, right[::-1]]))
    cumulative = np.concatenate(
        [np.asarray([0.0]), np.cumsum(np.linalg.norm(np.diff(polyline, axis=0), axis=1))]
    )
    lower = np.empty(len(polyline), dtype=float)
    upper = np.empty(len(polyline), dtype=float)
    for index, origin in enumerate(polyline):
        if index == 0:
            tangent = polyline[1] - polyline[0]
        elif index == len(polyline) - 1:
            tangent = polyline[-1] - polyline[-2]
        else:
            tangent = polyline[index + 1] - polyline[index - 1]
        tangent = tangent / max(float(np.linalg.norm(tangent)), 1.0e-9)
        normal = np.asarray([-tangent[1], tangent[0]])
        intervals = []
        for polygon in polygons:
            local = polygon - origin
            longitudinal = local @ tangent
            lateral = local @ normal
            crossings = []
            for edge in range(len(polygon)):
                nxt = (edge + 1) % len(polygon)
                x0, x1 = longitudinal[edge], longitudinal[nxt]
                if (x0 <= 0.0 <= x1 or x1 <= 0.0 <= x0) and abs(x1 - x0) > 1.0e-9:
                    fraction = -x0 / (x1 - x0)
                    crossings.append(float(lateral[edge] + fraction * (lateral[nxt] - lateral[edge])))
            if len(crossings) >= 2:
                intervals.append((min(crossings), max(crossings)))
        if not intervals:
            lower[index] = lower[index - 1] if index else -1.875
            upper[index] = upper[index - 1] if index else 1.875
            continue
        intervals.sort()
        containing = [item for item in intervals if item[0] <= 0.05 and item[1] >= -0.05]
        selected = min(
            containing or intervals,
            key=lambda item: 0.0 if item[0] <= 0.0 <= item[1] else min(abs(item[0]), abs(item[1])),
        )
        lo, hi = selected
        changed = True
        while changed:
            changed = False
            for candidate_lo, candidate_hi in intervals:
                if candidate_hi >= lo - 0.05 and candidate_lo <= hi + 0.05:
                    new_lo, new_hi = min(lo, candidate_lo), max(hi, candidate_hi)
                    changed = changed or new_lo < lo or new_hi > hi
                    lo, hi = new_lo, new_hi
        lower[index], upper[index] = lo, hi
    return cumulative, lower, upper


def _state_point(state: ET.Element | None) -> np.ndarray | None:
    point = _descendant(state, "position", "point")
    if point is None:
        rectangle = _descendant(state, "position", "rectangle", "center")
        point = rectangle
    x = _number(_first(point, "x"))
    y = _number(_first(point, "y"))
    if x is None or y is None:
        return None
    return np.array([x, y], dtype=float)


def _goal_region_corners(
    state: ET.Element | None, lanelets: dict[str, ET.Element] | None = None
) -> np.ndarray:
    """Return the official goal position as point/rectangle corner points."""
    position = _first(state, "position")
    rectangle = _first(position, "rectangle")
    center = _state_point(state)
    lanelet = _first(position, "lanelet")
    if lanelet is not None and lanelets is not None:
        node = lanelets.get(lanelet.attrib.get("ref", ""))
        if node is not None:
            points = np.vstack(
                [
                    _point_list(_first(node, "leftBound")),
                    _point_list(_first(node, "rightBound")),
                ]
            )
            if len(points) >= 2:
                return points
    if rectangle is None or center is None:
        return np.asarray([center], dtype=float) if center is not None else np.empty((0, 2))
    length = _number(_first(rectangle, "length"))
    width = _number(_first(rectangle, "width"))
    orientation = _number(_first(rectangle, "orientation"), 0.0)
    if length is None or width is None or length <= 0.0 or width <= 0.0:
        return np.asarray([center], dtype=float)
    local = np.asarray(
        [(-length / 2.0, -width / 2.0), (-length / 2.0, width / 2.0),
         (length / 2.0, -width / 2.0), (length / 2.0, width / 2.0)],
        dtype=float,
    )
    c, s = math.cos(float(orientation)), math.sin(float(orientation))
    rotation = np.asarray([[c, -s], [s, c]], dtype=float)
    return center + local @ rotation.T


def _circular_midpoint(start: float, end: float) -> float:
    """Midpoint on the shorter angular arc, robust across +/-pi."""
    delta = math.atan2(math.sin(end - start), math.cos(end - start))
    return math.atan2(math.sin(start + 0.5 * delta), math.cos(start + 0.5 * delta))


def _state_scalar(state: ET.Element | None, name: str, default: float = 0.0) -> float:
    exact = _descendant(state, name, "exact")
    if exact is None:
        exact = _descendant(state, name)
    value = _number(exact)
    return default if value is None else value


def _trajectory_states(obstacle: ET.Element) -> tuple[ET.Element, ...]:
    """Return the initial state followed by any CommonRoad trajectory states."""
    initial = _first(obstacle, "initialState")
    trajectory = _first(obstacle, "trajectory")
    states = tuple(_children(trajectory, "state")) if trajectory is not None else ()
    return (() if initial is None else (initial,)) + states


def _trajectory_uncertainty(
    obstacle: ET.Element,
    polyline: np.ndarray,
    baseline_s: float,
    baseline_l: float,
    baseline_vs: float,
    baseline_vl: float,
    time_scale: float = 1.0,
) -> tuple[float, float, float, float, int]:
    """Bound linear prediction error using the supplied CommonRoad trajectory.

    The planner only accepts constant-velocity obstacles.  We therefore keep
    that model and encode the observed trajectory deviation as a conservative
    affine radius ``r0 + t * rv``.  This is an input envelope, not a claim that
    the original trajectory dynamics or occupancy sets were preserved.
    """
    states = _trajectory_states(obstacle)
    if len(states) < 2:
        return 0.0, 0.0, 0.0, 0.0, 0
    initial_time = _state_scalar(states[0], "time", default=0.0)
    residual_s: list[tuple[float, float]] = []
    residual_l: list[tuple[float, float]] = []
    for state in states[1:]:
        point = _state_point(state)
        if point is None:
            continue
        time_delta = (
            _state_scalar(state, "time", default=initial_time) - initial_time
        ) * time_scale
        if time_delta <= 0.0:
            continue
        station, lateral, _ = _project(polyline, point)
        residual_s.append(
            (time_delta, abs(station - (baseline_s + baseline_vs * time_delta)))
        )
        residual_l.append(
            (time_delta, abs(lateral - (baseline_l + baseline_vl * time_delta)))
        )

    def _radius(samples: list[tuple[float, float]]) -> tuple[float, float]:
        if not samples:
            return 0.0, 0.0
        # A non-negative affine envelope covering every sampled residual.
        rate = max(residual / time for time, residual in samples)
        intercept = max(residual - rate * time for time, residual in samples)
        return max(0.0, intercept), max(0.0, rate)

    s0, vs = _radius(residual_s)
    l0, vl = _radius(residual_l)
    return s0, l0, vs, vl, len(residual_s)


def _trajectory_projection(
    obstacle: ET.Element,
    polyline: np.ndarray,
    time_scale: float = 1.0,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    """Project every published CommonRoad center state onto the route.

    The returned arrays are a conservative input-side representation only: the
    internal planner still reasons in Frenet coordinates and does not consume
    CommonRoad occupancy sets or vehicle orientations.
    """
    states = _trajectory_states(obstacle)
    if len(states) < 2:
        return (), (), ()
    initial_time = _state_scalar(states[0], "time", default=0.0)
    samples: list[tuple[float, float, float]] = []
    for state in states:
        point = _state_point(state)
        if point is None:
            continue
        time_delta = (
            _state_scalar(state, "time", default=initial_time) - initial_time
        ) * time_scale
        station, lateral, _ = _project(polyline, point)
        samples.append((time_delta, station, lateral))
    samples.sort(key=lambda sample: sample[0])
    unique: list[tuple[float, float, float]] = []
    for sample in samples:
        if unique and sample[0] <= unique[-1][0]:
            continue
        unique.append(sample)
    if len(unique) < 2:
        return (), (), ()
    return (
        tuple(sample[0] for sample in unique),
        tuple(sample[1] for sample in unique),
        tuple(sample[2] for sample in unique),
    )


def _trajectory_occupancy_envelope(
    obstacle: ET.Element,
    polyline: np.ndarray,
    length: float,
    width: float,
    time_scale: float = 1.0,
) -> tuple[
    tuple[float, ...],
    tuple[float, ...],
    tuple[float, ...],
    tuple[float, ...],
    tuple[float, ...],
]:
    """Project each published rectangle occupancy into a conservative Frenet box.

    The CommonRoad rectangle is rotated by its state orientation before all
    four corners are projected.  Interpolating the resulting extrema gives the
    planner a conservative time-varying occupancy envelope rather than a
    constant-velocity point prediction.  This intentionally retains a
    documented axis-aligned approximation in Frenet coordinates while
    consuming every available trajectory state and body pose.
    """
    states = _trajectory_states(obstacle)
    if len(states) < 2:
        return (), (), (), (), ()
    initial_time = _state_scalar(states[0], "time", default=0.0)
    local_corners = np.asarray(
        [
            (-length / 2.0, -width / 2.0),
            (-length / 2.0, width / 2.0),
            (length / 2.0, -width / 2.0),
            (length / 2.0, width / 2.0),
        ],
        dtype=float,
    )
    samples = []
    for state in states:
        center = _state_point(state)
        if center is None:
            continue
        time_delta = (
            _state_scalar(state, "time", default=initial_time) - initial_time
        ) * time_scale
        orientation = _state_scalar(state, "orientation", default=0.0)
        c, s = math.cos(orientation), math.sin(orientation)
        rotation = np.asarray([[c, -s], [s, c]], dtype=float)
        corners = center + local_corners @ rotation.T
        projected = np.asarray([_project(polyline, corner) for corner in corners])
        samples.append(
            (
                float(time_delta),
                float(np.min(projected[:, 0])),
                float(np.max(projected[:, 0])),
                float(np.min(projected[:, 1])),
                float(np.max(projected[:, 1])),
            )
        )
    samples.sort(key=lambda sample: sample[0])
    unique = []
    for sample in samples:
        if unique and sample[0] <= unique[-1][0]:
            continue
        unique.append(sample)
    if len(unique) < 2:
        return (), (), (), (), ()
    return tuple(tuple(sample[index] for sample in unique) for index in range(5))


def _obstacle_type(raw: str) -> str:
    value = raw.lower()
    if "pedestrian" in value:
        return "ped"
    if "bicycle" in value or "bike" in value:
        return "bike"
    if value in {"car", "truck", "bus", "motorcycle"}:
        return "vehicle"
    return "unknown_movable"


def _obstacle_dimensions(obstacle: ET.Element) -> tuple[float, float] | None:
    rectangle = _descendant(obstacle, "shape", "rectangle")
    length = _number(_descendant(rectangle, "length"))
    width = _number(_descendant(rectangle, "width"))
    if length is None or width is None or length <= 0.0 or width <= 0.0:
        return None
    return length, width


def _source_root(source: str | Path | bytes) -> ET.Element:
    if isinstance(source, bytes):
        return ET.fromstring(source)
    return ET.parse(source).getroot()


def adapt_commonroad_xml(
    source: str | Path | bytes,
    polyline_override: np.ndarray | None = None,
    project_all_dynamic_obstacles: bool = False,
    preserve_sampled_prediction: bool = False,
    time_scale: float = 1.0,
    horizon_slack: float = 0.0,
) -> CommonRoadAdapterResult:
    root = _source_root(source)
    lanelets = {
        lanelet.attrib["id"]: lanelet
        for lanelet in root.iter()
        if _local(lanelet.tag) == "lanelet" and "id" in lanelet.attrib
    }
    if not lanelets:
        raise ValueError("CommonRoad source contains no lanelets")
    centerlines = {lanelet_id: _centerline(node) for lanelet_id, node in lanelets.items()}
    successors = {
        lanelet_id: tuple(
            ref.attrib["ref"]
            for ref in node.iter()
            if _local(ref.tag) == "successor" and "ref" in ref.attrib
        )
        for lanelet_id, node in lanelets.items()
    }

    problem = next((node for node in root.iter() if _local(node.tag) == "planningProblem"), None)
    if problem is None:
        raise ValueError("CommonRoad source contains no planning problem")
    initial_state = _first(problem, "initialState")
    initial_point = _state_point(initial_state)
    if initial_point is None:
        raise ValueError("planning problem initial state has no point position")
    goal_state = _first(problem, "goalState")
    goal_point = _state_point(goal_state)
    goal_position = _first(goal_state, "position")
    goal_lanelet_node = _first(goal_position, "lanelet")
    goal_lanelet_ref = (
        goal_lanelet_node.attrib.get("ref")
        if goal_lanelet_node is not None
        else None
    )
    if goal_point is None and goal_lanelet_ref in lanelets:
        goal_lanelet = lanelets[goal_lanelet_ref]
        goal_points = np.vstack(
            [
                _point_list(_first(goal_lanelet, "leftBound")),
                _point_list(_first(goal_lanelet, "rightBound")),
            ]
        )
        if len(goal_points) >= 2:
            goal_point = np.mean(goal_points, axis=0)
    if goal_point is None:
        raise ValueError("planning problem goal state has no point/rectangle center")
    route = None
    start_candidates = _nearest_lanelets(centerlines, initial_point)
    goal_candidates = (
        (goal_lanelet_ref,)
        if goal_lanelet_ref in lanelets
        else _nearest_lanelets(centerlines, goal_point)
    )
    for start_lanelet in start_candidates:
        for goal_lanelet in goal_candidates:
            try:
                route = _route(successors, start_lanelet, goal_lanelet)
            except ValueError:
                continue
            break
        if route is not None:
            break
    if route is None:
        raise ValueError(
            "no successor route between nearest lanelet candidates "
            f"{start_candidates[:3]} and {goal_candidates[:3]}"
        )
    polyline = (
        _polyline_for_route(centerlines, route)
        if polyline_override is None
        else np.asarray(polyline_override, dtype=float)
    )
    if polyline.ndim != 2 or polyline.shape[1] != 2 or len(polyline) < 2:
        raise ValueError("reference polyline must contain at least two x/y points")
    ego_s, ego_l, ego_residual = _project(polyline, initial_point)
    goal_s, goal_l, goal_residual = _project(polyline, goal_point)
    goal_corners = _goal_region_corners(goal_state, lanelets)
    goal_corner_projection = np.asarray([_project(polyline, corner) for corner in goal_corners])
    goal_s_min = float(np.min(goal_corner_projection[:, 0]))
    goal_s_max = float(np.max(goal_corner_projection[:, 0]))
    goal_l_min = float(np.min(goal_corner_projection[:, 1]))
    goal_l_max = float(np.max(goal_corner_projection[:, 1]))
    route_tangent = np.diff(polyline, axis=0)
    route_heading = np.arctan2(route_tangent[:, 1], route_tangent[:, 0])
    route_left_l: list[float] = []
    route_right_l: list[float] = []
    for lanelet_id in route:
        lanelet = lanelets.get(str(lanelet_id))
        if lanelet is None:
            continue
        for point in _point_list(_first(lanelet, "leftBound")):
            route_left_l.append(_project(polyline, point)[1])
        for point in _point_list(_first(lanelet, "rightBound")):
            route_right_l.append(_project(polyline, point)[1])
    route_l_min = min(route_right_l) if route_right_l else -1.875
    route_l_max = max(route_left_l) if route_left_l else 1.875
    route_s_profile, right_profile, left_profile = _lanelet_cross_section_profiles(
        lanelets, polyline
    )
    route_l_min = float(np.min(right_profile))
    route_l_max = float(np.max(left_profile))

    ego_velocity = _state_scalar(initial_state, "velocity", default=0.0)
    # Match the official CommonRoad BMW_320i KS solution model used by the
    # native writer/evaluator.  Apollo synthetic fixtures retain Ego's native
    # dimensions; only this external adapter changes the vehicle contract.
    ego = Ego(s0=ego_s, l0=ego_l, v0=max(ego_velocity, 0.1), L=4.508, W=1.61)
    dynamic_nodes = [node for node in root.iter() if _local(node.tag) == "dynamicObstacle"]
    obstacles: list[Obstacle] = []
    skipped = 0
    trajectory_states_used = 0
    occupancy_obstacles = 0
    occupancy_samples = 0
    planner_relevant_obstacles = 0
    route_irrelevant_obstacles = 0
    residuals = [ego_residual, goal_residual]
    for node in dynamic_nodes:
        point = _state_point(_first(node, "initialState"))
        dimensions = _obstacle_dimensions(node)
        if point is None or dimensions is None:
            skipped += 1
            continue
        station, lateral, residual = _project(polyline, point)
        if not project_all_dynamic_obstacles and (
            residual > MAX_CENTERLINE_RESIDUAL_M
            or station < -10.0
            or station > goal_s_max + 20.0
            or abs(lateral) > 15.0
        ):
            skipped += 1
            continue
        residuals.append(residual)
        state = _first(node, "initialState")
        velocity = _state_scalar(state, "velocity", default=0.0)
        orientation = _state_scalar(state, "orientation", default=float(route_heading[0]))
        segment = int(np.clip(np.searchsorted(np.cumsum(np.linalg.norm(np.diff(polyline, axis=0), axis=1)), station), 0, len(route_heading) - 1))
        heading_delta = math.atan2(math.sin(orientation - route_heading[segment]), math.cos(orientation - route_heading[segment]))
        length, width = dimensions
        uncertainty_s0, uncertainty_l0, uncertainty_vs, uncertainty_vl, used_states = (
            _trajectory_uncertainty(
                node,
                polyline,
                station,
                lateral,
                velocity * math.cos(heading_delta),
                velocity * math.sin(heading_delta),
                time_scale=time_scale,
            )
        )
        if preserve_sampled_prediction:
            prediction_t, prediction_s, prediction_l = _trajectory_projection(
                node, polyline, time_scale=time_scale
            )
            occupancy_t, occupancy_s_min, occupancy_s_max, occupancy_l_min, occupancy_l_max = (
                _trajectory_occupancy_envelope(
                    node, polyline, length, width, time_scale=time_scale
                )
            )
            if occupancy_t:
                occupancy_obstacles += 1
                occupancy_samples += len(occupancy_t)
        else:
            prediction_t, prediction_s, prediction_l = (), (), ()
            occupancy_t = occupancy_s_min = occupancy_s_max = occupancy_l_min = occupancy_l_max = ()
        trajectory_states_used += used_states
        raw_type = (_descendant(node, "type").text or "unknown") if _descendant(node, "type") is not None else "unknown"
        obstacle = Obstacle(
                s0=station,
                l0=lateral,
                vs=velocity * math.cos(heading_delta),
                vl=velocity * math.sin(heading_delta),
                W=width,
                L=length,
                name=f"commonroad-{node.attrib.get('id', 'obstacle')}",
                obs_type=_obstacle_type(raw_type),
                uncertainty_s0=uncertainty_s0,
                uncertainty_l0=uncertainty_l0,
                uncertainty_vs=uncertainty_vs,
                uncertainty_vl=uncertainty_vl,
                prediction_t=prediction_t,
                prediction_s=prediction_s,
                prediction_l=prediction_l,
                occupancy_t=occupancy_t,
                occupancy_s_min=occupancy_s_min,
                occupancy_s_max=occupancy_s_max,
                occupancy_l_min=occupancy_l_min,
                occupancy_l_max=occupancy_l_max,
            )
        # CommonRoad files contain traffic on adjacent lanes and behind the
        # planning route.  Parse and audit all of it, but do not turn an object
        # that never intersects the route's reachable Frenet corridor into a
        # false forward ST constraint.  The corridor includes the configured
        # Apollo lane-borrow envelope and the ego half-width.
        route_s_min = ego_s - ego.L
        route_s_max = goal_s_max + ego.L
        route_corridor_min = route_l_min - ego.W / 2.0
        route_corridor_max = route_l_max + ego.W / 2.0
        if occupancy_t:
            relevant = any(
                s_hi >= route_s_min
                and s_lo <= route_s_max
                and l_hi >= route_corridor_min
                and l_lo <= route_corridor_max
                for s_lo, s_hi, l_lo, l_hi in zip(
                    occupancy_s_min,
                    occupancy_s_max,
                    occupancy_l_min,
                    occupancy_l_max,
                )
            )
        else:
            relevant = (
                station + length / 2.0 >= route_s_min
                and station - length / 2.0 <= route_s_max
                and lateral + width / 2.0 >= route_corridor_min
                and lateral - width / 2.0 <= route_corridor_max
            )
        if relevant:
            obstacles.append(obstacle)
            planner_relevant_obstacles += 1
        else:
            route_irrelevant_obstacles += 1

    goal_time_start = _number(_descendant(goal_state, "time", "intervalStart"))
    goal_time_end = _number(_descendant(goal_state, "time", "intervalEnd"))
    goal_v_min = _number(_descendant(goal_state, "velocity", "intervalStart"))
    goal_v_max = _number(_descendant(goal_state, "velocity", "intervalEnd"))
    # The rectangle inside ``goalState/position`` has its own orientation
    # element.  Read the goal-state orientation as a direct child; a generic
    # descendant search would silently return the rectangle orientation and
    # discard the actual terminal heading interval.
    goal_orientation_node = _first(goal_state, "orientation")
    goal_orientation_start = _number(_first(goal_orientation_node, "intervalStart"))
    goal_orientation_end = _number(_first(goal_orientation_node, "intervalEnd"))
    goal_orientation_exact = _number(_first(goal_orientation_node, "exact"))
    if goal_orientation_exact is not None:
        goal_orientation = goal_orientation_exact
    elif goal_orientation_start is not None and goal_orientation_end is not None:
        goal_orientation = _circular_midpoint(goal_orientation_start, goal_orientation_end)
    else:
        goal_orientation = None
    goal_heading_error = None
    if goal_orientation is not None:
        cumulative = np.cumsum(np.linalg.norm(np.diff(polyline, axis=0), axis=1))
        goal_segment = int(
            np.clip(np.searchsorted(cumulative, goal_s), 0, len(route_heading) - 1)
        )
        goal_heading_error = math.atan2(
            math.sin(goal_orientation - float(route_heading[goal_segment])),
            math.cos(goal_orientation - float(route_heading[goal_segment])),
        )
    if goal_time_end is None:
        goal_time_end = _number(_descendant(goal_state, "time", "exact"))
    goal_time_start = 0.0 if goal_time_start is None else goal_time_start * time_scale
    goal_time_end = 10.0 if goal_time_end is None else goal_time_end * time_scale
    t_max = min(
        max(
            goal_time_end + horizon_slack,
            0.1,
        ),
        15.0,
    )
    scenario = Scenario(
        ego=ego,
        obstacles=obstacles,
        # Preserve short CommonRoad goals.  The old Apollo smoke default of
        # ``ego_s + 5`` silently moved a goal that is only a few metres away
        # past its official region (notably Lankershim-1_4), making a valid
        # endpoint impossible under the native evaluator.
        # For lanelet goals, entering the first admissible station is already
        # a legal CommonRoad terminal state; using the lanelet midpoint would
        # silently turn a region goal into a point goal.  Rectangle goals keep
        # the centre projection as the finite horizon for compatibility.
        s_max=max(
            goal_s_min if goal_lanelet_ref in lanelets else goal_s,
            ego_s + 0.5,
        ),
        t_max=t_max,
        l_road_min=route_l_min,
        l_road_max=route_l_max,
        road_s_profile=route_s_profile,
        road_l_min_profile=right_profile,
        road_l_max_profile=left_profile,
        delta_min=0.0,
        lane_borrow="none",
        goal_lateral=goal_l,
        goal_s_min=goal_s_min,
        goal_s_max=goal_s_max,
        goal_l_min=goal_l_min,
        goal_l_max=goal_l_max,
        goal_region_kind="lanelet" if goal_lanelet_ref in lanelets else "rectangle",
        goal_heading_error=goal_heading_error,
        dynamic_path_bounds=False,
        v_max=50.8,
        a_min=-11.5,
        a_max=11.5,
        goal_time_start=goal_time_start,
        goal_time_end=goal_time_end,
        goal_v_min=goal_v_min,
        goal_v_max=goal_v_max,
    )
    planning_problem_id_raw = problem.attrib.get("id", "0")
    try:
        planning_problem_id: int | str = int(planning_problem_id_raw)
    except ValueError:
        # CommonRoad permits opaque string identifiers; preserve them instead
        # of making the adapter fail on otherwise valid XML fixtures.
        planning_problem_id = planning_problem_id_raw
    return CommonRoadAdapterResult(
        scenario=scenario,
        route_polyline=polyline,
        initial_time_step=int(round(_state_scalar(initial_state, "time", default=0.0))),
        planning_problem_id=planning_problem_id,
        benchmark_id=root.attrib.get("benchmarkID", "unknown"),
        route_lanelet_ids=route,
        source_lanelets=len(lanelets),
        source_dynamic_obstacles=len(dynamic_nodes),
        projected_obstacles=len(dynamic_nodes) - skipped,
        skipped_obstacles=skipped,
        trajectory_states_used=trajectory_states_used,
        occupancy_obstacles=occupancy_obstacles,
        occupancy_samples=occupancy_samples,
        planner_relevant_obstacles=planner_relevant_obstacles,
        route_irrelevant_obstacles=route_irrelevant_obstacles,
        route_l_min=route_l_min,
        route_l_max=route_l_max,
        maximum_projection_residual_m=max(residuals),
        limitations=(
            "reference-path Frenet route with station-varying lanelet cross-section bounds",
            "constant-velocity obstacle model with sampled-trajectory residual envelope",
            "official rectangle shape and orientation are conservatively consumed as sampled Frenet occupancy envelopes",
            "lanelet routing and goal remain official; traffic-control rules are recorded but not optimized by the Frenet planner",
        ),
    )
