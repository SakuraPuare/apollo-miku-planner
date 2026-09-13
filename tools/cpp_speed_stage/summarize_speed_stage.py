#!/usr/bin/env python3
"""Summarize paired, validated initial-speed-stage Python/C++ timing CSVs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import osqp

from export_path_snapshots import ROOT, VIS


def read_rows(path: Path) -> dict[tuple[str, int], dict]:
    rows = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = row["case_kind"], int(row["seed"])
            if key in rows:
                raise ValueError(f"duplicate case in {path}: {key}")
            rows[key] = row
    return rows


def stats(data: list[float]) -> dict[str, float]:
    return {"mean": statistics.mean(data),
            "p50": float(np.percentile(data, 50)),
            "p95": float(np.percentile(data, 95)),
            "p99": float(np.percentile(data, 99))}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(python_csv: Path, cpp_csv: Path, snapshots: Path) -> dict:
    py, cpp = read_rows(python_csv), read_rows(cpp_csv)
    if py.keys() != cpp.keys():
        raise ValueError(f"paired keys differ: python={len(py)}, cpp={len(cpp)}")
    keys = sorted(py)
    paired = [key for key in keys if cpp[key]["parity_ok"] == "1"]
    if not paired:
        raise ValueError("no validated Python/C++ speed stages")
    py_times = [float(py[k]["runtime_ms"]) for k in paired]
    cpp_times = [float(cpp[k]["runtime_ms"]) for k in paired]
    if any(ms <= 0 or not np.isfinite(ms) for ms in py_times + cpp_times):
        raise ValueError("non-positive or non-finite runtime")
    bad_flags = [key for key in keys if (py[key]["solved"], py[key]["terminal_goal_relaxed"]) !=
                 (cpp[key]["solved"], cpp[key]["terminal_goal_relaxed"])]
    if bad_flags:
        raise ValueError(f"failure status mismatch at {bad_flags[:3]}")
    ratios = [p / c for p, c in zip(py_times, cpp_times, strict=True)]
    categories = {}
    for kind in sorted({key[0] for key in paired}):
        selected = [key for key in paired if key[0] == kind]
        p = [float(py[key]["runtime_ms"]) for key in selected]
        c = [float(cpp[key]["runtime_ms"]) for key in selected]
        categories[kind] = {"case_count": len(selected),
                            "python_mean_ms": statistics.mean(p),
                            "cpp_mean_ms": statistics.mean(c),
                            "python_ms": stats(p),
                            "cpp_ms": stats(c),
                            "qp_failed": sum(py[key]["solved"] == "0" for key in selected),
                            "terminal_goal_relaxed": sum(
                                py[key]["terminal_goal_relaxed"] == "1" for key in selected
                            ),
                            "paired_sum_ratio": sum(p) / sum(c)}
    sources = [
        VIS / "apollo_pipeline.py",
        VIS / "miku_time.py",
        VIS / "experiment_cases.py",
        ROOT / "tools" / "cpp_speed_stage" / "speed_stage.cpp",
        ROOT / "tools" / "cpp_speed_stage" / "speed_stage.h",
        ROOT / "tools" / "cpp_speed_stage" / "benchmark_speed_stage.cpp",
        ROOT / "tools" / "cpp_speed_stage" / "benchmark_speed_stage.py",
        ROOT / "tools" / "cpp_speed_stage" / "export_path_snapshots.py",
    ]
    return {
        "scope": "one initial speed stage of MIKU on exported Python path samples",
        "included": "ST mapper + speed DP + ST bounds/temporal graph + goal/blocked trim + speed QP with setup and conditional retry",
        "excluded": "path construction/QP, scenario generation, JSON/CSV I/O, verification, outer iteration, alternate spatial/temporal candidates, Apollo runtime",
        "warmups_per_case": 1,
        "timed_repeats_per_case": 3,
        "case_time_aggregation": "median of 3 individually timed repetitions",
        "count_total": len(keys),
        "count_parity": len(paired),
        "count_unmatched": len(keys) - len(paired),
        "count_solved": sum(py[key]["solved"] == "1" for key in keys),
        "count_qp_failed": sum(py[key]["solved"] == "0" for key in keys),
        "count_terminal_goal_relaxed": sum(py[key]["terminal_goal_relaxed"] == "1" for key in keys),
        "mismatch_reasons": dict(Counter(cpp[key]["parity_reason"] for key in keys
                                         if cpp[key]["parity_ok"] != "1")),
        "python_ms": stats(py_times),
        "cpp_ms": stats(cpp_times),
        "paired_sum_ratio_python_over_cpp": sum(py_times) / sum(cpp_times),
        "paired_case_ratio_python_over_cpp": stats(ratios),
        "case_kinds": categories,
        "environment": {"python": sys.version.split()[0],
                        "python_executable": sys.executable,
                        "osqp_python": osqp.__version__,
                        "platform": platform.platform(),
                        "compiler": "g++ -std=c++17 -O2 -Wall -Wextra -Werror -losqp"},
        "sha256": {str(path.relative_to(ROOT)): sha(path) for path in [
            snapshots, python_csv, cpp_csv, *sources]},
    }


def main() -> None:
    p = argparse.ArgumentParser()
    base = ROOT / "submission_artifacts" / "cpp_benchmark"
    p.add_argument("--python", type=Path,
                   default=base / "miku_speed_stage.python_raw.csv")
    p.add_argument("--cpp", type=Path,
                   default=base / "miku_speed_stage.cpp_raw.csv")
    p.add_argument("--snapshots", type=Path,
                   default=base / "miku_speed_stage_3500.jsonl")
    p.add_argument("--output", type=Path,
                   default=base / "miku_speed_stage.calibration.json")
    args = p.parse_args()
    summary = summarize(args.python, args.cpp, args.snapshots)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"validated={summary['count_parity']}/{summary['count_total']} "
          f"python_mean_ms={summary['python_ms']['mean']:.6f} "
          f"cpp_mean_ms={summary['cpp_ms']['mean']:.6f} "
          f"paired_sum_ratio={summary['paired_sum_ratio_python_over_cpp']:.6f} "
          f"output={args.output}")


if __name__ == "__main__":
    main()
