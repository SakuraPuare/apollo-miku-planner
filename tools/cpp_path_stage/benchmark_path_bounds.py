#!/usr/bin/env python3
"""Time the frozen Python MIKU path-boundary call on exported planning cases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VIS_ROOT = REPO_ROOT / "小论文" / "jits_submission" / "supplement" / "code" / "可视化"
sys.path.insert(0, str(VIS_ROOT))

import apollo_pipeline as pipeline  # noqa: E402
from experiment_cases import generate_case  # noqa: E402


def run(source: Path, repeats: int, raw_output: Path) -> dict:
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    total_ms = 0.0
    total_stations = 0
    checksum = 0.0
    rows = []
    with source.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            kind = row["case_kind"]
            seed = int(row["seed"])
            scenario = generate_case(kind, seed).planning_scenario
            if len(scenario.obstacles) != int(row["obstacle_count"]):
                raise ValueError(f"case mismatch: {kind}/{seed}")
            for _ in range(3):
                pipeline.path_bounds_decider(scenario, "miku")
            start = time.perf_counter()
            for _ in range(repeats):
                stations, lower, upper, blocked, groups = pipeline.path_bounds_decider(
                    scenario, "miku"
                )
                candidates = groups[0]["spatial_homotopy_candidate_count"] if groups else 0
                checksum += float(lower[0]) + float(upper[-1]) + blocked + candidates
            runtime_ms = (time.perf_counter() - start) * 1000.0 / repeats
            total_stations += len(stations)
            total_ms += runtime_ms * repeats
            rows.append(
                {"case_kind": kind, "seed": seed, "station_count": len(stations),
                 "repeat_count": repeats, "runtime_ms": runtime_ms,
                 "blocked_idx": blocked, "spatial_candidate_count": candidates}
            )
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    with raw_output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {
        "runtime_scope": "frozen Python path_bounds_decider(scenario, 'miku') only",
        "input_file": str(source),
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "case_count": len(rows),
        "station_count": total_stations,
        "repeat_count": repeats,
        "elapsed_s": total_ms / 1000.0,
        "mean_runtime_us": total_ms * 1000.0 / (len(rows) * repeats),
        "checksum": checksum,
        "interpreter": sys.version.split()[0],
        "machine": platform.platform(),
        "raw_timing_csv": str(raw_output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--repeat", type=int, default=20)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    raw_output = args.summary.with_name(args.summary.stem + "_raw.csv")
    report = run(args.input, args.repeat, raw_output)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
