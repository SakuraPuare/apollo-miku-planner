"""Run MIKU through a native CommonRoad solution/evaluator boundary.

The planner itself still consumes the repository's Apollo Planning Scenario
object.  This runner is deliberately explicit about that boundary: it reads a
CommonRoad planning problem with the official reader, converts a successful
Frenet rollout back to official ``KSState`` objects, writes a standard
``PlanningProblemSolution``/solution XML, and evaluates it with the official
drivability checker.  A planner failure is retained as a benchmark row; no
placeholder trajectory is emitted.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np

from commonroad_adapter import adapt_commonroad_xml
from experiment_methods import method_by_key, run_method
from run_commonroad_reactive import (
    BASE,
    EXTENDED_SCENARIOS,
    FAMILY_BASES,
    FAMILY_LABELS,
    FAMILY_SCENARIOS,
    SCENARIOS,
    _evaluate,
)


def _circular_midpoint(start: float, end: float) -> float:
    delta = float(np.arctan2(np.sin(end - start), np.cos(end - start)))
    return float(np.arctan2(np.sin(start + 0.5 * delta), np.cos(start + 0.5 * delta)))


def _versions() -> dict[str, str]:
    packages = (
        "commonroad-io",
        "commonroad-drivability-checker",
        "commonroad-route-planner",
    )
    return {name: importlib.metadata.version(name) for name in packages}


def _polyline_state(polyline: np.ndarray, station: float, lateral: float) -> tuple[np.ndarray, float]:
    vectors = np.diff(polyline, axis=0)
    lengths = np.linalg.norm(vectors, axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    s = float(np.clip(station, 0.0, cumulative[-1]))
    index = int(np.clip(np.searchsorted(cumulative, s, side="right") - 1, 0, len(vectors) - 1))
    fraction = (s - cumulative[index]) / lengths[index]
    point = polyline[index] + fraction * vectors[index]
    unit = vectors[index] / lengths[index]
    normal = np.array([-unit[1], unit[0]])
    return point + float(lateral) * normal, float(np.arctan2(unit[1], unit[0]))


def _state_kinematics(positions: list[np.ndarray], times: np.ndarray, speeds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Recover a KS-compatible heading and steering sequence from the rollout.

    The previous native writer emitted the reference-path heading together with
    zero steering.  That can describe neither a lateral offset nor a curved
    reference path, so CommonRoad's official KS feasibility checker correctly
    rejected otherwise collision-free trajectories.  Heading is recovered from
    the emitted positions and steering from ``kappa = yaw_rate / v`` using the
    BMW-320i wheelbase used by the solution protocol.
    """
    points = np.asarray(positions, dtype=float)
    if len(points) < 2:
        return np.zeros(len(points)), np.zeros(len(points))
    delta = np.diff(points, axis=0)
    headings = np.unwrap(np.arctan2(delta[:, 1], delta[:, 0]))
    headings = np.concatenate(([headings[0]], headings))
    if len(headings) > len(points):
        headings = headings[: len(points)]
    yaw_rate = np.gradient(headings, times, edge_order=1)
    wheelbase = 2.5789128  # CommonRoad VehicleType.BMW_320i (a+b)
    steering = np.arctan2(wheelbase * yaw_rate, np.maximum(np.abs(speeds), 0.1))
    return headings, np.clip(steering, -1.066, 1.066)


def _tracking_inputs(
    positions: list[np.ndarray],
    times: np.ndarray,
    speeds: np.ndarray,
    initial_state,
    dt: float,
    goal_orientation: float | None = None,
    terminal_orientation_strong: bool = False,
    goal_position: np.ndarray | None = None,
):
    """Track the planned geometric rollout with bounded KS controls."""
    from commonroad.scenario.state import InputState

    wheelbase = 2.5789128
    position = np.asarray(initial_state.position, dtype=float).copy()
    heading = float(initial_state.orientation)
    velocity = max(0.0, float(speeds[0]))
    steering = 0.0
    inputs = []

    def wrap(angle: float) -> float:
        return float(np.arctan2(np.sin(angle), np.cos(angle)))

    for index in range(len(times) - 1):
        target_index = min(index + 2, len(positions) - 1)
        target_position = np.asarray(positions[target_index], dtype=float)
        if goal_position is not None:
            remaining = float(times[-1] - times[index])
            if remaining < 0.8:
                blend_position = min(0.8, max(0.0, (0.8 - remaining) / 0.8))
                target_position = (
                    (1.0 - blend_position) * target_position
                    + blend_position * np.asarray(goal_position, dtype=float)
                )
        delta_position = target_position - position
        distance = max(float(np.linalg.norm(delta_position)), 1.0)
        target_heading = float(np.arctan2(delta_position[1], delta_position[0]))
        if target_index < len(positions) - 1:
            segment = np.asarray(positions[target_index + 1]) - np.asarray(positions[target_index])
            if float(np.linalg.norm(segment)) > 1.0e-6:
                path_heading = float(np.arctan2(segment[1], segment[0]))
                # Pure pursuit supplies cross-track correction while the
                # local path tangent keeps the KS heading inside the terminal
                # orientation interval used by CommonRoad goal regions.
                target_heading = wrap(0.35 * target_heading + 0.65 * path_heading)
        if goal_orientation is not None:
            remaining = float(times[-1] - times[index])
            # Do not teleport the heading to the goal at the first control
            # cycle.  A three-second ramp is a conservative approximation of
            # the BMW-320i steering-rate reachable set; the official checker
            # remains the authority when the interval is not reachable.
            ramp = max(1.0, min(3.0, float(times[-1] - times[0])))
            blend = min(1.0, max(0.0, 1.0 - remaining / ramp))
            target_heading = wrap(
                (1.0 - blend) * target_heading + blend * float(goal_orientation)
            )
        heading_error = wrap(target_heading - heading)
        curvature = 2.0 * np.sin(heading_error) / distance
        steering_target = float(np.clip(np.arctan(wheelbase * curvature), -1.0, 1.0))
        # Add a feed-forward curvature term from the planned polyline.  Pure
        # pursuit alone reacts after a lateral error has already accumulated;
        # this term preserves the reference path's turning direction under
        # the KS steering-rate bound.
        if index + 2 < len(positions):
            segment0 = np.asarray(positions[index + 1]) - np.asarray(positions[index])
            segment1 = np.asarray(positions[index + 2]) - np.asarray(positions[index + 1])
            if float(np.linalg.norm(segment0)) > 1.0e-6 and float(np.linalg.norm(segment1)) > 1.0e-6:
                heading0 = float(np.arctan2(segment0[1], segment0[0]))
                heading1 = float(np.arctan2(segment1[1], segment1[0]))
                path_yaw_rate = wrap(heading1 - heading0) / dt
                feedforward = float(
                    np.clip(np.arctan(wheelbase * path_yaw_rate / max(velocity, 0.5)), -1.0, 1.0)
                )
                steering_target = 0.65 * steering_target + 0.35 * feedforward
        # Keep the feedback command inside the BMW-320i friction circle before
        # the official checker integrates it.
        max_lateral_acceleration = 3.0
        steering_limit = np.arctan(
            wheelbase * max_lateral_acceleration / max(velocity * velocity, 1.0)
        )
        steering_target = float(
            np.clip(steering_target, -steering_limit, steering_limit)
        )
        steering_rate_limit = 0.4
        steering_rate = float(
            np.clip((steering_target - steering) / dt, -steering_rate_limit, steering_rate_limit)
        )
        desired_speed = max(0.0, float(speeds[min(index + 1, len(speeds) - 1)]))
        lateral_acceleration = abs(
            velocity * velocity * np.tan(steering) / wheelbase
        )
        longitudinal_limit = np.sqrt(
            max(0.0, 11.5 * 11.5 - lateral_acceleration * lateral_acceleration)
        )
        acceleration = float(
            np.clip((desired_speed - velocity) / dt, -longitudinal_limit, longitudinal_limit)
        )
        inputs.append(
            InputState(
                time_step=int(initial_state.time_step) + index,
                steering_angle_speed=steering_rate,
                acceleration=acceleration,
            )
        )
        # Match the KS state convention used by the official checker closely
        # enough for the next feedback step; the checker remains authoritative.
        steering = float(np.clip(steering + steering_rate * dt, -1.066, 1.066))
        velocity = max(0.0, velocity + acceleration * dt)
        heading = wrap(heading + velocity / wheelbase * np.tan(steering) * dt)
        position = position + velocity * np.asarray(
            [np.cos(heading), np.sin(heading)], dtype=float
        ) * dt
    return inputs


def _refine_terminal_controls(
    inputs,
    initial_state,
    dt: float,
    goal_position: np.ndarray,
    goal_orientation: float,
):
    """Refine terminal steering rates under the official BMW-320i KS model.

    The Frenet planner supplies a geometrically valid terminal point, but a
    bounded-rate KS rollout can still miss that point after discretisation.
    A small, deterministic shooting problem adjusts at most twenty steering
    rate knots while keeping the planner's longitudinal controls unchanged.
    The official CommonRoad evaluator remains authoritative: this refinement
    is accepted only when its simulated terminal residual improves; collision
    and goal checks are still performed on the emitted solution.
    """
    if len(inputs) < 4:
        return inputs
    try:
        from commonroad.common.solution import VehicleModel, VehicleType
        from commonroad.scenario.state import InputState
        from commonroad.scenario.trajectory import Trajectory
        from commonroad_dc.feasibility import solution_checker
        from scipy.optimize import least_squares

        base_rates = np.asarray(
            [state.steering_angle_speed for state in inputs], dtype=float
        )
        accelerations = np.asarray(
            [state.acceleration for state in inputs], dtype=float
        )
        knot_count = min(20, len(inputs))
        knot_grid = np.linspace(0.0, float(len(inputs) - 1), knot_count)
        initial_knots = np.interp(knot_grid, np.arange(len(inputs)), base_rates)
        dynamics = solution_checker.VehicleDynamics.from_model(
            VehicleModel.KS, VehicleType.BMW_320i
        )

        def expand(knots: np.ndarray) -> np.ndarray:
            return np.interp(np.arange(len(inputs)), knot_grid, knots)

        def simulate(knots: np.ndarray):
            rates = expand(knots)
            states = [
                InputState(
                    time_step=int(initial_state.time_step) + index,
                    steering_angle_speed=float(rate),
                    acceleration=float(acceleration),
                )
                for index, (rate, acceleration) in enumerate(zip(rates, accelerations))
            ]
            trajectory = Trajectory(
                initial_time_step=int(initial_state.time_step), state_list=states
            )
            return dynamics.simulate_trajectory(initial_state, trajectory, dt)

        def wrap(angle: float) -> float:
            return float(np.arctan2(np.sin(angle), np.cos(angle)))

        def residual(knots: np.ndarray) -> np.ndarray:
            terminal = simulate(knots).state_list[-1]
            return np.concatenate(
                (
                    np.asarray(terminal.position, dtype=float)
                    - np.asarray(goal_position, dtype=float),
                    [wrap(float(terminal.orientation) - float(goal_orientation))],
                )
            )

        baseline_residual = float(np.linalg.norm(residual(initial_knots)))
        fit = least_squares(
            residual,
            initial_knots,
            bounds=(-0.4, 0.4),
            diff_step=0.02,
            max_nfev=80,
        )
        refined_residual = float(np.linalg.norm(residual(fit.x)))
        if refined_residual >= baseline_residual - 1.0e-3:
            return inputs
        rates = expand(fit.x)
        return [
            InputState(
                time_step=int(initial_state.time_step) + index,
                steering_angle_speed=float(rate),
                acceleration=float(acceleration),
            )
            for index, (rate, acceleration) in enumerate(zip(rates, accelerations))
        ]
    except Exception:
        # Refinement is an optional post-processing step.  A missing optional
        # dependency or an ill-conditioned shooting problem must not hide the
        # native planner result.
        return inputs


def _native_solution(scenario, problem_set, problem, adapted, method_run, dt: float):
    from commonroad.common.solution import (
        CostFunction,
        PlanningProblemSolution,
        Solution,
        VehicleModel,
        VehicleType,
    )
    from commonroad.scenario.trajectory import Trajectory

    result = method_run.result
    if result.get("s_qp") is None:
        return None
    stations = np.asarray(result["s_qp"], dtype=float)
    speeds = np.asarray(result["v_qp"], dtype=float)
    times = np.asarray(result["ts"], dtype=float)
    path_lateral = np.interp(stations, result["s_arr"], result["l_path"])
    positions = []
    for index, (station, elapsed) in enumerate(zip(stations, times)):
        position, orientation = _polyline_state(adapted.route_polyline, station, float(path_lateral[index]))
        positions.append(position)
    # Anchor the geometric rollout to the exact CommonRoad initial position
    # before recovering headings/steering.  Otherwise the first control would
    # track a projected point that can be a few centimetres away from the
    # official state and the integrated trajectory drifts from the goal.
    positions[0] = np.asarray(problem.initial_state.position, dtype=float)
    goal_orientation = None
    try:
        orientation_region = problem.goal.state_list[0].orientation
        if hasattr(orientation_region, "center"):
            goal_orientation = float(orientation_region.center)
        else:
            goal_orientation = _circular_midpoint(
                float(orientation_region.start), float(orientation_region.end)
            )
    except (AttributeError, IndexError, TypeError, ValueError):
        pass
    terminal_orientation_strong = False
    if goal_orientation is not None:
        _, terminal_path_heading = _polyline_state(
            adapted.route_polyline,
            float(stations[-1]),
            float(path_lateral[-1]),
        )
        terminal_orientation_strong = abs(
            float(
                np.arctan2(
                    np.sin(goal_orientation - terminal_path_heading),
                    np.cos(goal_orientation - terminal_path_heading),
                )
            )
        ) > 0.2
    inputs = _tracking_inputs(
        positions,
        times,
        speeds,
        problem.initial_state,
        dt,
        goal_orientation=goal_orientation,
        terminal_orientation_strong=terminal_orientation_strong,
        # Track and shoot towards the planner's selected terminal state.  The
        # official goal is a rectangle region, so forcing its geometric centre
        # can move a valid endpoint out of the planner's reachable corridor.
        goal_position=np.asarray(positions[-1], dtype=float),
    )
    if goal_orientation is not None:
        inputs = _refine_terminal_controls(
            inputs,
            problem.initial_state,
            dt,
            np.asarray(positions[-1], dtype=float),
            goal_orientation,
        )
    # Emit controls, not a hand-interpolated KS trajectory.  The official
    # CommonRoad checker then integrates exactly the declared BMW-320i KS model
    # from the planning-problem initial state.  This keeps the evaluator's
    # dynamics semantics authoritative and exposes any control/goal failure.
    trajectory = Trajectory(
        initial_time_step=adapted.initial_time_step,
        state_list=inputs,
    )
    pps = PlanningProblemSolution(
        planning_problem_id=problem.planning_problem_id,
        vehicle_model=VehicleModel.KS,
        vehicle_type=VehicleType.BMW_320i,
        cost_function=CostFunction.JB1,
        trajectory=trajectory,
    )
    return Solution(scenario.scenario_id, [pps])


def _failure_diagnostics(method_run, adapted) -> dict[str, object]:
    """Expose where a negative native run ends, without weakening constraints.

    A planner failure is otherwise easy to misread as a reader/evaluator
    failure.  These fields are deliberately diagnostic: they do not turn an
    infeasible candidate into a score and are not used to select a successful
    trajectory.
    """
    result = method_run.result
    l_min = np.asarray(result.get("l_min", ()), dtype=float)
    l_max = np.asarray(result.get("l_max", ()), dtype=float)
    s_ub = np.asarray(result.get("s_ub", ()), dtype=float)
    path_width = l_max - l_min
    path_infeasible = int(np.sum(path_width < -1e-7)) if path_width.size else 0
    st_bounds = result.get("st_bounds", ()) or ()
    active_bounds = [boundary for boundary in st_bounds if boundary.get("intervals")]
    interval_count = sum(len(boundary.get("intervals", ())) for boundary in active_bounds)
    if result.get("terminal_goal_infeasible"):
        stage = "goal_bounds"
        reason = "goal_station_unreachable_under_safe_corridor"
    elif result.get("s_qp") is not None:
        stage = "solved"
        reason = "candidate_solved"
    elif path_infeasible:
        stage = "path_bounds"
        reason = "empty_path_corridor"
    elif s_ub.size and float(np.min(s_ub)) < float(adapted.scenario.ego.s0) - 1e-6:
        stage = "speed_bounds"
        reason = "st_upper_bound_below_current_station"
    else:
        stage = "speed_qp"
        reason = "speed_qp_infeasible_or_safety_certificate_rejected"
    return {
        "failure_stage": stage,
        "failure_reason": reason,
        "path_min_width_m": float(np.min(path_width)) if path_width.size else None,
        "path_infeasible_knot_count": path_infeasible,
        "st_active_obstacle_count": len(active_bounds),
        "st_interval_count": interval_count,
        "st_upper_min_m": float(np.min(s_ub)) if s_ub.size else None,
        "ego_station_m": float(adapted.scenario.ego.s0),
        "projected_obstacle_count": adapted.projected_obstacles,
    }


def run_one(path: Path, method_key: str, dt: float, steps: int, output_dir: Path | None) -> dict[str, object]:
    from commonroad.common.file_reader import CommonRoadFileReader
    from commonroad.common.solution import CommonRoadSolutionWriter
    from commonroad_rp.utility.utils_coordinate_system import create_initial_ref_path

    scenario, problem_set = CommonRoadFileReader(str(path)).open()
    problem = next(iter(problem_set.planning_problem_dict.values()))
    raw_xml = path.read_bytes()
    # The official reference path already contains the initial-state station
    # (the first several samples may lie behind the origin); do not prepend a
    # straight chord, which would change the route geometry and lateral frame.
    official_reference_path = create_initial_ref_path(scenario.lanelet_network, problem)
    adapted = adapt_commonroad_xml(
        raw_xml,
        polyline_override=official_reference_path,
        project_all_dynamic_obstacles=True,
        preserve_sampled_prediction=True,
        time_scale=dt,
        horizon_slack=0.0,
    )
    # Keep the planner horizon identical to the official competitor protocol.
    adapted.scenario.t_max = min(float(adapted.scenario.t_max), float(steps) * dt)
    method_run = run_method(method_by_key(method_key), adapted.scenario)
    row: dict[str, object] = {
        "scenario": path.name.removesuffix(".xml"),
        "benchmark_id": adapted.benchmark_id,
        "planning_problem_id": problem.planning_problem_id,
        "method": method_key,
        "dt": dt,
        "horizon_steps": steps,
        "native_commonroad_protocol": True,
        "planner_protocol": "MIKU_or_B0_same_initial_state_dt_horizon_and_official_evaluator",
        "planner_input_semantics": "official_lanelet_reference_path_and_station_varying_polygon_cross_section; relevant_sampled_shape_pose_occupancy_envelope; all_source_obstacles_audited",
        "occupancy_semantics": "conservative_frenet_envelope_from_all_published_rectangle_states; route-relevance filter before planning",
        "reference_path_source": "CommonRoad RoutePlanner/ReferencePathPlanner",
        "route_lanelet_count": len(adapted.route_lanelet_ids),
        "source_lanelets": adapted.source_lanelets,
        "source_dynamic_obstacles": adapted.source_dynamic_obstacles,
        "projected_obstacles": adapted.projected_obstacles,
        "planner_relevant_obstacles": adapted.planner_relevant_obstacles,
        "route_irrelevant_obstacles": adapted.route_irrelevant_obstacles,
        "route_lateral_bounds_m": [adapted.route_l_min, adapted.route_l_max],
        "station_varying_road_bounds": adapted.scenario.road_s_profile is not None,
        "road_center_width_min_m": (
            float(np.min(np.asarray(adapted.scenario.road_l_max_profile) - np.asarray(adapted.scenario.road_l_min_profile)))
            if adapted.scenario.road_l_min_profile is not None
            and adapted.scenario.road_l_max_profile is not None
            else None
        ),
        "skipped_obstacles": adapted.skipped_obstacles,
        "trajectory_states_used": adapted.trajectory_states_used,
        "occupancy_obstacles": adapted.occupancy_obstacles,
        "occupancy_samples": adapted.occupancy_samples,
        "maximum_projection_residual_m": adapted.maximum_projection_residual_m,
        "planner_success": method_run.result.get("s_qp") is not None,
        "planner_runtime_ms": method_run.runtime_ms,
        "goal_time_window_s": [
            adapted.scenario.goal_time_start,
            adapted.scenario.goal_time_end,
        ],
        "goal_velocity_interval_mps": [
            adapted.scenario.goal_v_min,
            adapted.scenario.goal_v_max,
        ],
        "goal_station_m": adapted.scenario.s_max,
        "goal_station_interval_m": [
            adapted.scenario.goal_s_min,
            adapted.scenario.goal_s_max,
        ],
        "goal_region_kind": adapted.scenario.goal_region_kind,
        "goal_lateral_interval_m": [
            adapted.scenario.goal_l_min,
            adapted.scenario.goal_l_max,
        ],
        "goal_heading_error_rad": adapted.scenario.goal_heading_error,
        "planner_terminal_slope_target": method_run.result.get("terminal_slope_target"),
        "selected_goal_time_s": method_run.result.get("selected_goal_time"),
        "selected_goal_knot": method_run.result.get("selected_goal_index"),
        "temporal_plan_fallback_from_rank": method_run.result.get(
            "temporal_plan_fallback_from_rank"
        ),
    }
    row["failure_diagnostics"] = _failure_diagnostics(method_run, adapted)
    solution = _native_solution(scenario, problem_set, problem, adapted, method_run, dt)
    if solution is None:
        row.update(
            {
                "outcome": "planner_failure",
                "failure_category": "planner_failure",
                "native_solution_written": False,
            }
        )
        return row
    checks = _evaluate(scenario, problem_set, solution, dt)
    row.update(checks)
    row["failure_category"] = (
        "valid"
        if row.get("valid_solution") is True
        else "goal_not_reached"
        if row.get("goal_reached") is False
        else "obstacle_collision"
        if row.get("obstacle_collision") is not False
        else "boundary_collision"
        if row.get("boundary_collision") is not False
        else "dynamics_invalid"
    )
    result = method_run.result
    if result.get("s_qp") is not None:
        row["terminal_station_m"] = float(result["s_qp"][-1])
        row["terminal_speed_mps"] = float(result["v_qp"][-1])
    row["native_solution_written"] = True
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        CommonRoadSolutionWriter(solution).write_to_file(
            output_path=str(output_dir),
            filename=f"miku_{method_key.lower()}_{path.stem}.xml",
            overwrite=True,
        )
    return row


def run(
    methods: tuple[str, ...] = ("B0", "MIKU"),
    dt: float = 0.1,
    steps: int = 100,
    timeout: float = 60.0,
    output_dir: Path | None = None,
    scenario_files: tuple[str, ...] = SCENARIOS,
    base_url: str = BASE,
    benchmark: str = "CommonRoad NGSIM Lankershim",
) -> dict[str, object]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="miku-commonroad-native-") as directory:
        root = Path(directory)
        for filename in scenario_files:
            local = root / filename
            with urllib.request.urlopen(base_url + filename, timeout=timeout) as response:
                local.write_bytes(response.read())
            for method_key in methods:
                started = time.perf_counter()
                try:
                    row = run_one(local, method_key, dt, steps, output_dir)
                except Exception as exc:  # preserve evaluator/parser failures as rows
                    row = {
                        "scenario": filename.removesuffix(".xml"),
                        "method": method_key,
                        "native_commonroad_protocol": True,
                        "outcome": "runner_failure",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                row["wall_time_ms"] = (time.perf_counter() - started) * 1000.0
                rows.append(row)
    miku_rows = [row for row in rows if row.get("method") == "MIKU"]
    return {
        "benchmark": benchmark,
        "source": base_url,
        "runner": "run_commonroad_miku_native.py",
        "parameters": {"dt": dt, "horizon_steps": steps},
        "packages": _versions(),
        "scenario_count": len(scenario_files),
        "method_count": len(methods),
        "rows": rows,
        "native_solution_protocol": all(row.get("native_commonroad_protocol") is True for row in rows),
        # The benchmark is native for the declared scope: official lanelet
        # route/goal, all dynamic rectangle poses, conservative Frenet
        # occupancy envelopes, and the official solution/evaluator protocol.
        # Traffic-control elements are recorded separately because this
        # Frenet planner does not optimize a rule-compliance policy.
        "miku_native_benchmark": bool(
            rows
            and all(
                row.get("native_commonroad_protocol") is True
                and row.get("projected_obstacles", 0) == row.get("occupancy_obstacles", -1)
                and row.get("occupancy_samples", 0) > 0
                for row in rows
            )
        ),
        "benchmark_scope": "official_route_goal_dynamic_rectangle_pose_occupancy_envelope_and_evaluator; traffic_control_rules_recorded_only",
        "miku_valid_solution_count": sum(row.get("valid_solution") is True for row in miku_rows),
        "miku_planner_failure_count": sum(row.get("outcome") == "planner_failure" for row in miku_rows),
        "miku_non_valid_count": sum(row.get("outcome") != "valid_solution" for row in miku_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--family", choices=tuple(FAMILY_SCENARIOS), default="lankershim")
    parser.add_argument("--output", type=Path, default=Path("小论文-2/generated/commonroad_miku_native_results.json"))
    parser.add_argument("--solution-dir", type=Path, default=Path("小论文-2/generated/commonroad_miku_native_solutions"))
    args = parser.parse_args()
    report = run(
        dt=args.dt,
        steps=args.steps,
        timeout=args.timeout,
        output_dir=args.solution_dir,
        scenario_files=(
            EXTENDED_SCENARIOS if args.extended and args.family == "lankershim"
            else FAMILY_SCENARIOS[args.family]
        ),
        base_url=FAMILY_BASES[args.family],
        benchmark=f"CommonRoad NGSIM {FAMILY_LABELS[args.family]}",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
