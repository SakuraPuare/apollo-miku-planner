#!/usr/bin/env python3
"""Export actual Python MIKU path samples and speed-stage reference results.

The exported data describes *one initial run_pipeline call*, not the outer
run_method() spatial/temporal candidate retries or trajectory iteration.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
VIS = ROOT / "小论文" / "jits_submission" / "supplement" / "code" / "可视化"
sys.path.insert(0, str(VIS))

from apollo_pipeline import (  # noqa: E402
    build_st_bounds,
    path_bounds_decider,
    path_optimizer,
    speed_dp,
    speed_qp,
    st_boundary_mapper,
)
from experiment_cases import generate_case  # noqa: E402
from experiment_methods import method_by_key  # noqa: E402


def initial_speed_stage(scn, stations, offsets, blocked_idx, timing_sink=None):
    start = time.perf_counter()
    st = st_boundary_mapper(scn, stations, offsets, robust_prediction=True)
    ts, s_dp, forbidden, ss = speed_dp(scn, st)
    log = []
    upper, lower = build_st_bounds(
        scn, st, s_dp, ts, safe_window_mode=True, decision_log=log,
    )
    target = max(scn.s_max - 1, scn.ego.s0)
    upper = np.minimum(upper, target)
    if blocked_idx >= 0:
        upper = np.minimum(upper, max(stations[blocked_idx] - scn.ego.L / 2, 0))
    before_goal = float(lower[-1])
    lower[-1] = min(target, upper[-1])
    s, v, a, _ = speed_qp(scn, upper, lower, ts)
    relaxed = False
    if s is None and lower[-1] > before_goal + 1e-9:
        lower[-1] = before_goal
        s, v, a, _ = speed_qp(scn, upper, lower, ts)
        relaxed = True
    if timing_sink is not None:
        timing_sink.append((time.perf_counter() - start) * 1000)
    return {
        "st_boundaries": [b["intervals"] for b in st],
        "dp_s": s_dp.tolist(),
        "forbidden_count": int(np.count_nonzero(forbidden)),
        "upper": upper.tolist(),
        "lower": lower.tolist(),
        "decision_statuses": [d["status"] for d in log],
        "decision_labels": [d.get("homotopy_label", "") for d in log],
        "terminal_goal_relaxed": relaxed,
        "solved": s is not None,
        "s": None if s is None else s.tolist(),
        "v": None if v is None else v.tolist(),
        "a": None if a is None else a.tolist(),
    }


def export(input_csv: Path, output: Path, limit: int | None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with input_csv.open(newline="", encoding="utf-8") as source:
        with output.open("w", encoding="utf-8") as destination:
            for row in csv.DictReader(source):
                if limit is not None and n >= limit:
                    break
                kind, seed = row["case_kind"], int(row["seed"])
                scn = generate_case(kind, seed).planning_scenario
                flags = method_by_key("MIKU").flags
                stations, lower, upper, blocked, _ = path_bounds_decider(scn, flags)
                offsets, _ = path_optimizer(stations, lower, upper)
                snapshot = {
                    "schema_version": "miku-speed-stage-v1",
                    "case_kind": kind,
                    "seed": seed,
                    "scenario": asdict(scn),
                    "path_stations": stations.tolist(),
                    "path_offsets": offsets.tolist(),
                    "path_lower": lower.tolist(),
                    "path_upper": upper.tolist(),
                    "blocked_idx": blocked,
                    "expected": initial_speed_stage(scn, stations, offsets, blocked),
                }
                destination.write(json.dumps(snapshot, allow_nan=False, separators=(",", ":")) + "\n")
                n += 1
                if n % 250 == 0:
                    print(f"exported {n} path and speed-stage references", flush=True)
    print(f"wrote {n} path/speed reference cases to {output}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=ROOT / "submission_artifacts" /
                   "cpp_benchmark" / "miku_cases_3500.csv")
    p.add_argument("--output", type=Path, default=ROOT / "submission_artifacts" /
                   "cpp_benchmark" / "miku_speed_stage_3500.jsonl")
    p.add_argument("--limit", type=int)
    args = p.parse_args()
    if args.limit is not None and args.limit < 1:
        p.error("--limit must be positive")
    export(args.input, args.output, args.limit)


if __name__ == "__main__":
    main()
