#!/usr/bin/env python3
"""Export the deterministic MIKU planning cases to a C++-friendly CSV.

The manuscript's open-loop protocol generates seven families with the same
seed range for every method.  This utility reuses that generator rather than
reimplementing its random-number stream, and serializes the *planning*
scenario (the prediction-noise family intentionally differs from its truth
scenario).  One row represents one case; obstacle fields are flattened into a
fixed number of columns so a dependency-free C++ harness can read the file.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = REPO_ROOT / "小论文" / "jits_submission" / "supplement" / "code"
VIS_ROOT = CODE_ROOT / "可视化"
if str(VIS_ROOT) not in sys.path:
    sys.path.insert(0, str(VIS_ROOT))

from experiment_cases import CASE_KINDS, generate_case  # noqa: E402


SCHEMA_VERSION = "miku-cpp-input-v1"
OBSTACLE_FIELDS = (
    "s0",
    "l0",
    "vs",
    "vl",
    "W",
    "L",
    "is_static",
    "obs_type",
    "uncertainty_s0",
    "uncertainty_l0",
    "uncertainty_vs",
    "uncertainty_vl",
)
BASE_FIELDS = (
    "schema_version",
    "case_kind",
    "seed",
    "ego_s0",
    "ego_l0",
    "ego_v0",
    "ego_a0",
    "ego_W",
    "ego_L",
    "s_max",
    "t_max",
    "l_road_min",
    "l_road_max",
    "delta_baseline",
    "delta_min",
    "delta_max",
    "lane_borrow",
    "lane_width",
    "obstacle_count",
)


def _float(value: float) -> str:
    """Use a round-trippable representation across Python and C++."""

    return format(float(value), ".17g")


def _row(kind: str, seed: int, scenario, max_obstacles: int) -> dict[str, str]:
    obstacles = scenario.obstacles
    if len(obstacles) > max_obstacles:
        raise ValueError(
            f"{kind}/{seed} has {len(obstacles)} obstacles; "
            f"increase --max-obstacles (currently {max_obstacles})"
        )

    row: dict[str, str] = {
        "schema_version": SCHEMA_VERSION,
        "case_kind": kind,
        "seed": str(seed),
        "ego_s0": _float(scenario.ego.s0),
        "ego_l0": _float(scenario.ego.l0),
        "ego_v0": _float(scenario.ego.v0),
        "ego_a0": _float(scenario.ego.a0),
        "ego_W": _float(scenario.ego.W),
        "ego_L": _float(scenario.ego.L),
        "s_max": _float(scenario.s_max),
        "t_max": _float(scenario.t_max),
        "l_road_min": _float(scenario.l_road_min),
        "l_road_max": _float(scenario.l_road_max),
        "delta_baseline": _float(scenario.delta_baseline),
        "delta_min": _float(scenario.delta_min),
        "delta_max": _float(scenario.delta_max),
        "lane_borrow": scenario.lane_borrow,
        "lane_width": _float(scenario.lane_width),
        "obstacle_count": str(len(obstacles)),
    }
    for index in range(max_obstacles):
        obstacle = obstacles[index] if index < len(obstacles) else None
        for field in OBSTACLE_FIELDS:
            key = f"obs{index}_{field}"
            if obstacle is None:
                row[key] = ""
            elif field == "is_static":
                row[key] = "1" if obstacle.is_static else "0"
            elif field == "obs_type":
                row[key] = obstacle.obs_type
            else:
                row[key] = _float(getattr(obstacle, field))
    return row


def export(seed_start: int, seeds: int, output: Path, max_obstacles: int) -> None:
    if seed_start < 0 or seeds <= 0:
        raise ValueError("seed_start must be non-negative and seeds must be positive")
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(BASE_FIELDS)
    for index in range(max_obstacles):
        fields.extend(f"obs{index}_{field}" for field in OBSTACLE_FIELDS)

    count = 0
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for kind in CASE_KINDS:
            for seed in range(seed_start, seed_start + seeds):
                case = generate_case(kind, seed)
                writer.writerow(_row(kind, seed, case.planning_scenario, max_obstacles))
                count += 1

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "case_kinds": list(CASE_KINDS),
        "seed_start": seed_start,
        "seed_count_per_kind": seeds,
        "case_count": count,
        "max_obstacles": max_obstacles,
        "scenario_role": "planning_scenario",
        "generator": "小论文/jits_submission/supplement/code/可视化/experiment_cases.py",
    }
    output.with_suffix(".json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {count} cases to {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seeds", type=int, default=500)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "submission_artifacts" / "cpp_benchmark" / "miku_cases_3500.csv",
    )
    parser.add_argument("--max-obstacles", type=int, default=8)
    args = parser.parse_args()
    if args.max_obstacles <= 0:
        parser.error("--max-obstacles must be positive")
    export(args.seed_start, args.seeds, args.output, args.max_obstacles)


if __name__ == "__main__":
    main()
