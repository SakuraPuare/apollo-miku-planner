"""Audit pinned CommonRoad XML with the official commonroad-io parser.

The project keeps commonroad-io optional so the core prototype remains small.
This script is an external semantic audit only: it does not run MIKU or claim
that the restricted Frenet adapter is a native CommonRoad planner.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import urllib.request


BASE = (
    "https://gitlab.lrz.de/tum-cps/commonroad-scenarios/-/raw/"
    "2020a_scenarios/scenarios/recorded/NGSIM/Lankershim/"
)
SCENARIOS = (
    "USA_Lanker-1_1_T-1.xml",
    "USA_Lanker-1_2_T-1.xml",
    "USA_Lanker-1_3_T-1.xml",
    "USA_Lanker-1_4_T-1.xml",
)


def _parse(path: Path) -> dict[str, object]:
    try:
        from commonroad.common.file_reader import CommonRoadFileReader
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "native audit requires optional commonroad-io; run with "
            "uv run --with commonroad-io python "
            "可视化/validate_commonroad_native.py"
        ) from exc

    scenario, problem_set = CommonRoadFileReader(str(path)).open()
    dynamic = tuple(scenario.dynamic_obstacles)
    static = tuple(scenario.static_obstacles)
    rectangle_count = sum(
        type(obstacle.obstacle_shape).__name__ == "RectObstacleShape"
        for obstacle in (*dynamic, *static)
    )
    predicted_states = sum(
        len(obstacle.prediction.trajectory.state_list)
        for obstacle in dynamic
        if obstacle.prediction is not None
    )
    return {
        "file": path.name,
        "benchmark_id": str(scenario.scenario_id),
        "scenario_id": str(scenario.scenario_id),
        "lanelets": len(scenario.lanelet_network.lanelets),
        "dynamic_obstacles": len(dynamic),
        "static_obstacles": len(static),
        "planning_problems": len(problem_set.planning_problem_dict),
        "rectangular_obstacles": rectangle_count,
        "predicted_trajectory_states": predicted_states,
        "goal_regions": len(problem_set.planning_problem_dict),
    }


def validate(timeout: float = 30.0) -> list[dict[str, object]]:
    report = []
    with tempfile.TemporaryDirectory(prefix="miku-commonroad-") as directory:
        root = Path(directory)
        for filename in SCENARIOS:
            with urllib.request.urlopen(BASE + filename, timeout=timeout) as response:
                path = root / filename
                path.write_bytes(response.read())
            report.append(_parse(path))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate(args.timeout)
    payload = json.dumps(report, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
