"""Bounded CommonRoad XML -> Frenet prototype adapter.

The adapter intentionally supports only the subset needed to audit the
planner boundary: lanelet centerlines, successor routing, point/rectangle
initial states, and constant-velocity obstacle projections.  It does not
claim CommonRoad rule, shape, or dynamic-model fidelity.
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
    benchmark_id: str
    route_lanelet_ids: tuple[str, ...]
    source_lanelets: int
    source_dynamic_obstacles: int
    projected_obstacles: int
    skipped_obstacles: int
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


def _nearest_lanelet(centerlines: dict[str, np.ndarray], point: np.ndarray) -> str:
    return min(
        centerlines,
        key=lambda lanelet_id: float(
            np.min(np.linalg.norm(centerlines[lanelet_id] - point, axis=1))
        ),
    )


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
    signed_lateral = float(unit[index, 0] * (point[1] - projections[index, 1]) - unit[index, 1] * (point[0] - projections[index, 0]))
    return station, signed_lateral, float(distances[index])


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


def _state_scalar(state: ET.Element | None, name: str, default: float = 0.0) -> float:
    exact = _descendant(state, name, "exact")
    if exact is None:
        exact = _descendant(state, name)
    value = _number(exact)
    return default if value is None else value


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


def adapt_commonroad_xml(source: str | Path | bytes) -> CommonRoadAdapterResult:
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
    if goal_point is None:
        raise ValueError("planning problem goal state has no point/rectangle center")
    start_lanelet = _nearest_lanelet(centerlines, initial_point)
    goal_lanelet = _nearest_lanelet(centerlines, goal_point)
    route = _route(successors, start_lanelet, goal_lanelet)
    polyline = _polyline_for_route(centerlines, route)
    ego_s, ego_l, ego_residual = _project(polyline, initial_point)
    goal_s, _, goal_residual = _project(polyline, goal_point)
    route_tangent = np.diff(polyline, axis=0)
    route_heading = np.arctan2(route_tangent[:, 1], route_tangent[:, 0])

    ego_velocity = _state_scalar(initial_state, "velocity", default=0.0)
    ego = Ego(s0=ego_s, l0=ego_l, v0=max(ego_velocity, 0.1))
    dynamic_nodes = [node for node in root.iter() if _local(node.tag) == "dynamicObstacle"]
    obstacles: list[Obstacle] = []
    skipped = 0
    residuals = [ego_residual, goal_residual]
    for node in dynamic_nodes:
        point = _state_point(_first(node, "initialState"))
        dimensions = _obstacle_dimensions(node)
        if point is None or dimensions is None:
            skipped += 1
            continue
        station, lateral, residual = _project(polyline, point)
        if (
            residual > MAX_CENTERLINE_RESIDUAL_M
            or station < -10.0
            or station > goal_s + 20.0
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
        raw_type = (_descendant(node, "type").text or "unknown") if _descendant(node, "type") is not None else "unknown"
        obstacles.append(
            Obstacle(
                s0=station,
                l0=lateral,
                vs=velocity * math.cos(heading_delta),
                vl=velocity * math.sin(heading_delta),
                W=width,
                L=length,
                name=f"commonroad-{node.attrib.get('id', 'obstacle')}",
                obs_type=_obstacle_type(raw_type),
            )
        )

    goal_time = _descendant(goal_state, "time", "intervalEnd")
    t_max = min(max(_number(goal_time, 10.0) or 10.0, 5.0), 15.0)
    scenario = Scenario(
        ego=ego,
        obstacles=obstacles,
        s_max=max(goal_s, ego_s + 5.0),
        t_max=t_max,
        l_road_min=-3.75,
        l_road_max=3.75,
        lane_borrow="both",
    )
    return CommonRoadAdapterResult(
        scenario=scenario,
        benchmark_id=root.attrib.get("benchmarkID", "unknown"),
        route_lanelet_ids=route,
        source_lanelets=len(lanelets),
        source_dynamic_obstacles=len(dynamic_nodes),
        projected_obstacles=len(obstacles),
        skipped_obstacles=skipped,
        maximum_projection_residual_m=max(residuals),
        limitations=(
            "centerline-only lanelet route",
            "initial-state constant-velocity obstacle projection",
            "axis-aligned Frenet rectangles; no CommonRoad rule/shape semantics",
            "not a native CommonRoad planner benchmark",
        ),
    )
