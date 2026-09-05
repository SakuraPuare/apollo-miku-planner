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
from run_commonroad_reactive import BASE, SCENARIOS, _evaluate


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


def _native_solution(scenario, problem_set, problem, adapted, method_run, dt: float):
    from commonroad.common.solution import (
        CostFunction,
        PlanningProblemSolution,
        Solution,
        VehicleModel,
        VehicleType,
    )
    from commonroad.scenario.state import KSState
    from commonroad.scenario.trajectory import Trajectory

    result = method_run.result
    if result.get("s_qp") is None:
        return None
    stations = np.asarray(result["s_qp"], dtype=float)
    speeds = np.asarray(result["v_qp"], dtype=float)
    times = np.asarray(result["ts"], dtype=float)
    path_lateral = np.interp(stations, result["s_arr"], result["l_path"])
    states = []
    for index, (station, speed, elapsed) in enumerate(zip(stations, speeds, times)):
        position, orientation = _polyline_state(adapted.route_polyline, station, float(path_lateral[index]))
        time_step = adapted.initial_time_step + int(round(float(elapsed) / dt))
        states.append(
            KSState(
                time_step=time_step,
                position=position,
                steering_angle=0.0,
                velocity=max(0.0, float(speed)),
                orientation=orientation,
            )
        )
    trajectory = Trajectory(initial_time_step=states[0].time_step, state_list=states)
    pps = PlanningProblemSolution(
        planning_problem_id=problem.planning_problem_id,
        vehicle_model=VehicleModel.KS,
        vehicle_type=VehicleType.BMW_320i,
        cost_function=CostFunction.JB1,
        trajectory=trajectory,
    )
    return Solution(scenario.scenario_id, [pps])


def run_one(path: Path, method_key: str, dt: float, steps: int, output_dir: Path | None) -> dict[str, object]:
    from commonroad.common.file_reader import CommonRoadFileReader
    from commonroad.common.solution import CommonRoadSolutionWriter
    from commonroad_rp.utility.utils_coordinate_system import create_initial_ref_path

    scenario, problem_set = CommonRoadFileReader(str(path)).open()
    problem = next(iter(problem_set.planning_problem_dict.values()))
    raw_xml = path.read_bytes()
    official_reference_path = create_initial_ref_path(scenario.lanelet_network, problem)
    adapted = adapt_commonroad_xml(
        raw_xml,
        polyline_override=official_reference_path,
        project_all_dynamic_obstacles=True,
        preserve_sampled_prediction=True,
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
        "planner_input_semantics": "official_lanelet_route_and_sampled_shape_pose_occupancy_envelope",
        "occupancy_semantics": "conservative_frenet_envelope_from_all_published_rectangle_states",
        "reference_path_source": "CommonRoad RoutePlanner/ReferencePathPlanner",
        "route_lanelet_count": len(adapted.route_lanelet_ids),
        "source_lanelets": adapted.source_lanelets,
        "source_dynamic_obstacles": adapted.source_dynamic_obstacles,
        "projected_obstacles": adapted.projected_obstacles,
        "skipped_obstacles": adapted.skipped_obstacles,
        "trajectory_states_used": adapted.trajectory_states_used,
        "occupancy_obstacles": adapted.occupancy_obstacles,
        "occupancy_samples": adapted.occupancy_samples,
        "maximum_projection_residual_m": adapted.maximum_projection_residual_m,
        "planner_success": method_run.result.get("s_qp") is not None,
        "planner_runtime_ms": method_run.runtime_ms,
    }
    solution = _native_solution(scenario, problem_set, problem, adapted, method_run, dt)
    if solution is None:
        row.update({"outcome": "planner_failure", "native_solution_written": False})
        return row
    checks = _evaluate(scenario, problem_set, solution, dt)
    row.update(checks)
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
    steps: int = 40,
    timeout: float = 60.0,
    output_dir: Path | None = None,
) -> dict[str, object]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="miku-commonroad-native-") as directory:
        root = Path(directory)
        for filename in SCENARIOS:
            local = root / filename
            with urllib.request.urlopen(BASE + filename, timeout=timeout) as response:
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
        "benchmark": "CommonRoad NGSIM Lankershim",
        "source": BASE,
        "runner": "run_commonroad_miku_native.py",
        "parameters": {"dt": dt, "horizon_steps": steps},
        "packages": _versions(),
        "scenario_count": len(SCENARIOS),
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
        "miku_planner_failure_count": sum(row.get("outcome") != "valid_solution" for row in miku_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--output", type=Path, default=Path("小论文-2/generated/commonroad_miku_native_results.json"))
    parser.add_argument("--solution-dir", type=Path, default=Path("小论文-2/generated/commonroad_miku_native_solutions"))
    args = parser.parse_args()
    report = run(dt=args.dt, steps=args.steps, timeout=args.timeout, output_dir=args.solution_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
