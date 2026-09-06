"""Run the published CommonRoad Reactive Planner on pinned XML scenarios.

The runner uses the official CommonRoad reader, route/reference-path planner,
solution writer, and drivability-checker components.  A short horizon is
useful for a smoke run; a formal benchmark should pass a horizon long enough
for every planning problem to reach its goal.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import tempfile
import time
import urllib.request
from pathlib import Path

BASE = (
    "https://gitlab.lrz.de/tum-cps/commonroad-scenarios/-/raw/"
    "2020a_scenarios/scenarios/recorded/NGSIM/Lankershim/"
)
FAMILY_BASES = {
    "lankershim": BASE,
    "peachtree": (
        "https://gitlab.lrz.de/tum-cps/commonroad-scenarios/-/raw/"
        "2020a_scenarios/scenarios/recorded/NGSIM/Peachtree/"
    ),
    "us101": (
        "https://gitlab.lrz.de/tum-cps/commonroad-scenarios/-/raw/"
        "2020a_scenarios/scenarios/recorded/NGSIM/US101/"
    ),
}
SCENARIOS = (
    "USA_Lanker-1_1_T-1.xml",
    "USA_Lanker-1_2_T-1.xml",
    "USA_Lanker-1_3_T-1.xml",
    "USA_Lanker-1_4_T-1.xml",
)
FAMILY_SCENARIOS = {
    "lankershim": SCENARIOS,
    "peachtree": (
        "USA_Peach-1_1_T-1.xml",
        "USA_Peach-2_1_T-1.xml",
        "USA_Peach-3_1_T-1.xml",
        "USA_Peach-4_1_T-1.xml",
    ),
    "us101": (
        "USA_US101-1_1_T-1.xml",
        "USA_US101-10_1_T-1.xml",
        "USA_US101-11_1_T-1.xml",
        "USA_US101-12_1_T-1.xml",
    ),
}
FAMILY_LABELS = {
    "lankershim": "Lankershim",
    "peachtree": "Peachtree",
    "us101": "US101",
}
EXTENDED_SCENARIOS = SCENARIOS + (
    "USA_Lanker-1_5_T-1.xml",
    "USA_Lanker-2_1_T-1.xml",
    "USA_Lanker-1_6_T-1.xml",
    "USA_Lanker-1_7_T-1.xml",
    "USA_Lanker-1_8_T-1.xml",
    "USA_Lanker-2_2_T-1.xml",
    "USA_Lanker-2_3_T-1.xml",
    "USA_Lanker-1_9_T-1.xml",
    "USA_Lanker-1_10_T-1.xml",
    "USA_Lanker-1_11_T-1.xml",
    "USA_Lanker-1_12_T-1.xml",
    "USA_Lanker-2_4_T-1.xml",
)


def _versions() -> dict[str, str]:
    names = {
        "commonroad-io": "commonroad-io",
        "commonroad-drivability-checker": "commonroad-drivability-checker",
        "commonroad-route-planner": "commonroad-route-planner",
        "commonroad-clcs": "commonroad-clcs",
        "commonroad-reactive-planner": "commonroad-reactive-planner",
    }
    return {key: importlib.metadata.version(package) for key, package in names.items()}


def _evaluate(scenario, problem_set, solution, dt: float) -> dict[str, object]:
    from commonroad_dc.feasibility import solution_checker

    result: dict[str, object] = {}
    try:
        feasible = solution_checker.solution_feasible(solution, dt, problem_set)
        result["dynamics_feasible"] = all(item[0] for item in feasible.values())
        result["dynamics_details"] = {str(key): bool(item[0]) for key, item in feasible.items()}
    except Exception as exc:  # evaluator errors remain visible in the report
        result["dynamics_feasible"] = None
        result["dynamics_error"] = f"{type(exc).__name__}: {exc}"
    for name, function in (
        ("obstacle_collision", solution_checker.obstacle_collision),
        ("boundary_collision", solution_checker.boundary_collision),
        ("ego_collision", solution_checker.ego_collision),
    ):
        try:
            result[name] = bool(function(scenario, problem_set, solution))
        except Exception as exc:
            result[name] = None
            result[f"{name}_error"] = f"{type(exc).__name__}: {exc}"
    try:
        result["goal_reached"] = bool(solution_checker.goal_reached(scenario, problem_set, solution))
    except Exception as exc:
        result["goal_reached"] = False
        result["goal_error"] = f"{type(exc).__name__}: {exc}"
    result["valid_solution"] = bool(
        result.get("dynamics_feasible") is True
        and result.get("goal_reached") is True
        and result.get("obstacle_collision") is False
        and result.get("boundary_collision") is False
        and result.get("ego_collision") is False
    )
    result["outcome"] = "valid_solution" if result["valid_solution"] else "invalid_solution"
    return result


def run_one(path: Path, steps: int, dt: float, output_dir: Path | None = None) -> dict[str, object]:
    from commonroad.common.file_reader import CommonRoadFileReader
    from commonroad.common.solution import CommonRoadSolutionWriter
    from commonroad_rp.reactive_planner import ReactivePlanner
    from commonroad_rp.utility.config import ReactivePlannerConfiguration
    from commonroad_rp.utility.evaluation import create_planning_problem_solution
    from commonroad_rp.utility.utils_coordinate_system import (
        create_coordinate_system,
        create_initial_ref_path,
    )

    scenario, problem_set = CommonRoadFileReader(str(path)).open()
    problem = next(iter(problem_set.planning_problem_dict.values()))
    config = ReactivePlannerConfiguration()
    config.scenario = scenario
    config.planning_problem = problem
    config.planning_problem_set = problem_set
    config.planning.dt = dt
    config.planning.time_steps_computation = steps
    config.debug.multiproc = False
    config.debug.show_plots = False
    config.debug.show_evaluation_plots = False
    config.debug.draw_ref_path = False
    config.debug.draw_planning_problem = False
    config.debug.logging_level = "ERROR"

    reference_path = create_initial_ref_path(scenario.lanelet_network, problem)
    planner = ReactivePlanner(config)
    planner.set_reference_path(coordinate_system=create_coordinate_system(reference_path))
    planner.set_desired_velocity(current_speed=float(problem.initial_state.velocity))
    row: dict[str, object] = {
        "scenario": path.name.removesuffix(".xml"),
        "benchmark_id": str(scenario.scenario_id),
        "planning_problem_id": problem.planning_problem_id,
        "dt": dt,
        "horizon_steps": steps,
        "planner_states": 0,
        "planned": False,
        "reference_path_source": "CommonRoad RoutePlanner/ReferencePathPlanner",
        "planner_protocol": "official_reactive_planner_one_shot_same_dt_horizon_and_evaluator",
    }
    started = time.perf_counter()
    try:
        planned = planner.plan()
    except Exception as exc:
        row["runtime_ms"] = (time.perf_counter() - started) * 1000.0
        row["planner_error"] = f"{type(exc).__name__}: {exc}"
        row["planner_exception"] = True
        row["outcome"] = "planner_failure"
        return row
    runtime_ms = (time.perf_counter() - started) * 1000.0
    row["runtime_ms"] = runtime_ms
    row["planned"] = planned is not None
    if planned is None:
        row["planner_error"] = "ReactivePlanner returned no trajectory"
        row["outcome"] = "planner_failure"
        return row

    trajectory, _, _ = planned
    row["planner_states"] = len(trajectory.state_list)
    solution = create_planning_problem_solution(config, trajectory, scenario, problem)
    checks = _evaluate(scenario, problem_set, solution, dt)
    row.update(checks)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        CommonRoadSolutionWriter(solution).write_to_file(
            output_path=str(output_dir),
            filename=f"reactive_{path.stem}.xml",
            overwrite=True,
        )
    return row


def run(
    steps: int = 20,
    dt: float = 0.1,
    timeout: float = 60.0,
    output_dir: Path | None = None,
    scenario_files: tuple[str, ...] = SCENARIOS,
    base_url: str = BASE,
    benchmark: str = "CommonRoad NGSIM Lankershim",
) -> dict[str, object]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="miku-commonroad-reactive-") as directory:
        root = Path(directory)
        for filename in scenario_files:
            local = root / filename
            with urllib.request.urlopen(base_url + filename, timeout=timeout) as response:
                local.write_bytes(response.read())
            rows.append(run_one(local, steps, dt, output_dir))
    return {
        "benchmark": benchmark,
        "source": base_url,
        "competitor": "commonroad-reactive-planner",
        "parameters": {"dt": dt, "horizon_steps": steps},
        "packages": _versions(),
        "scenario_count": len(rows),
        "rows": rows,
        "planned_count": sum(row.get("planned") is True for row in rows),
        "valid_solution_count": sum(row.get("valid_solution") is True for row in rows),
        "all_solutions_valid": all(row.get("valid_solution") is True for row in rows),
        "benchmark_complete": len(rows) == len(scenario_files)
        and all(
            "planned" in row
            and (row.get("planned") is False or "outcome" in row)
            for row in rows
        ),
        "formal_benchmark_ready": len(rows) == len(scenario_files)
        and all(
            "planned" in row
            and (row.get("planned") is False or "outcome" in row)
            for row in rows
        ),
        "protocol_scope": "one-shot official ReactivePlanner; same initial state, dt, horizon, solution writer and evaluator as native comparison",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--family", choices=tuple(FAMILY_SCENARIOS), default="lankershim")
    parser.add_argument("--output", type=Path, default=Path("小论文-2/generated/commonroad_reactive_results.json"))
    parser.add_argument("--solution-dir", type=Path, default=Path("小论文-2/generated/commonroad_reactive_solutions"))
    args = parser.parse_args()
    report = run(
        args.steps,
        args.dt,
        args.timeout,
        args.solution_dir,
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
