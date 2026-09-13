"""Pair sampled initial-stage snapshots with frozen Python MIKU run_method outputs."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
VIS = ROOT / "小论文/jits_submission/supplement/code/可视化"
sys.path.insert(0, str(VIS))

from experiment_cases import generate_case  # noqa: E402
from experiment_methods import method_by_key, run_method  # noqa: E402


def reference_rows(input_file: Path, output_file: Path, stride: int) -> int:
    count = 0
    with input_file.open(encoding="utf-8") as source, output_file.open("w", encoding="utf-8") as target:
        for line in source:
            row = json.loads(line)
            if row["seed"] % stride:
                continue
            scn = generate_case(row["case_kind"], row["seed"]).planning_scenario
            if row["scenario"] != asdict(scn):
                raise ValueError(f"scenario snapshot mismatch: {row['case_kind']}/{row['seed']}")
            method = run_method(method_by_key("MIKU"), scn)
            result = method.result
            row["expected_full"] = {
                "runtime_ms": method.runtime_ms,
                "iterations": method.iterations,
                "converged": method.converged,
                "spatial_candidate_count": result["spatial_homotopy_candidate_count"],
                "temporal_candidate_count": result["temporal_homotopy_candidate_count"],
                "path_stations": result["s_arr"].tolist(),
                "path_offsets": result["l_path"].tolist(),
                "curvature": result["kappa_s"].tolist(),
                "lateral_acceleration": (
                    None if result["a_y"] is None else result["a_y"].tolist()
                ),
                "blocked_idx": result["blocked_idx"],
                "terminal_goal_relaxed": result["terminal_goal_relaxed"],
                "s": None if result["s_qp"] is None else result["s_qp"].tolist(),
                "v": None if result["v_qp"] is None else result["v_qp"].tolist(),
                "a": None if result["a_qp"] is None else result["a_qp"].tolist(),
            }
            target.write(json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "submission_artifacts/cpp_benchmark/miku_speed_stage_3500.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "submission_artifacts/cpp_benchmark/miku_full_method_140.jsonl")
    parser.add_argument("--stride", type=int, default=25, help="select seeds divisible by stride in each family")
    args = parser.parse_args()
    if args.stride <= 0:
        parser.error("stride must be positive")
    count = reference_rows(args.input, args.output, args.stride)
    print(f"exported {count} frozen Python complete-method references")


if __name__ == "__main__":
    main()
