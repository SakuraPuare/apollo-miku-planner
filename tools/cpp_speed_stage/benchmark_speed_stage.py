#!/usr/bin/env python3
"""Time the Python initial speed stage on exported, fixed path samples."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

import numpy as np

from export_path_snapshots import ROOT, initial_speed_stage
from apollo_pipeline import Ego, Obstacle, Scenario


def validate(observed: dict, expected: dict, label: str) -> None:
    for field in ("forbidden_count", "decision_statuses", "decision_labels",
                  "solved", "terminal_goal_relaxed"):
        if observed[field] != expected[field]:
            raise ValueError(f"{label}: {field} reference changed")
    for field in ("st_boundaries", "dp_s", "upper", "lower", "s", "v", "a"):
        a, b = observed[field], expected[field]
        if a is None or b is None:
            if a != b:
                raise ValueError(f"{label}: {field} solver status changed")
            continue
        if len(a) != len(b):
            raise ValueError(f"{label}: {field} length changed")
        if field == "st_boundaries":
            for bound_a, bound_b in zip(a, b, strict=True):
                if len(bound_a) != len(bound_b) or not np.allclose(
                    bound_a, bound_b, atol=1e-8, rtol=0,
                ):
                    raise ValueError(f"{label}: ST occupancy changed")
        elif not np.allclose(a, b, atol=1e-5, rtol=0):
            raise ValueError(f"{label}: {field} changed")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=ROOT / "submission_artifacts" /
                   "cpp_benchmark" / "miku_speed_stage_3500.jsonl")
    p.add_argument("--output", type=Path, default=ROOT / "submission_artifacts" /
                   "cpp_benchmark" / "miku_speed_stage.python_raw.csv")
    p.add_argument("--limit", type=int)
    p.add_argument("--repeats", type=int, default=3)
    args = p.parse_args()
    if args.limit is not None and args.limit < 1 or args.repeats < 1:
        p.error("--limit and --repeats must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    times = []
    with args.input.open(encoding="utf-8") as source, args.output.open(
        "w", newline="", encoding="utf-8",
    ) as destination:
        writer = csv.DictWriter(destination, fieldnames=(
            "case_kind", "seed", "runtime_ms", "repeats", "solved",
            "terminal_goal_relaxed",
        ))
        writer.writeheader()
        for index, line in enumerate(source):
            if args.limit is not None and index >= args.limit:
                break
            row = json.loads(line)
            if row["schema_version"] != "miku-speed-stage-v1":
                raise ValueError("unknown snapshot schema")
            data = row["scenario"]
            scenario = Scenario(
                ego=Ego(**data["ego"]),
                obstacles=[Obstacle(**obs) for obs in data["obstacles"]],
                s_max=data["s_max"], t_max=data["t_max"],
            )
            stations = np.asarray(row["path_stations"], dtype=float)
            offsets = np.asarray(row["path_offsets"], dtype=float)
            label = f"{row['case_kind']}/{row['seed']}"
            warm = initial_speed_stage(scenario, stations, offsets, row["blocked_idx"])
            validate(warm, row["expected"], label)
            readings = []
            for _ in range(args.repeats):
                sample = []
                measured = initial_speed_stage(
                    scenario, stations, offsets, row["blocked_idx"], sample,
                )
                validate(measured, row["expected"], label)
                readings.append(sample[0])
            median_ms = statistics.median(readings)
            if not math.isfinite(median_ms):
                raise ValueError(f"{label}: invalid runtime")
            times.append(median_ms)
            writer.writerow({"case_kind": row["case_kind"], "seed": row["seed"],
                             "runtime_ms": f"{median_ms:.12g}",
                             "repeats": args.repeats,
                             "solved": int(warm["solved"]),
                             "terminal_goal_relaxed": int(warm["terminal_goal_relaxed"])})
            if (index + 1) % 250 == 0:
                print(f"benchmarked {index + 1} Python speed stages", flush=True)
    print(f"python speed-stage cases={len(times)} mean_ms={statistics.mean(times):.6f} "
          f"median_ms={statistics.median(times):.6f} output={args.output}")


if __name__ == "__main__":
    main()
