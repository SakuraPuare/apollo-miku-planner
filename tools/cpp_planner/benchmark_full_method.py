#!/usr/bin/env python3
"""Benchmark frozen Python run_method against sampled complete-method references.

This script uses the supplement's Python 3.12 planner.  It validates each
warmup and timed trajectory against `expected_full` outside the measured
region, then writes per-case medians compatible with the paired C++ planner
benchmark.  Use it only when other CPU benchmarks have finished.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import platform
from statistics import median
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
VIS = ROOT / "小论文" / "jits_submission" / "supplement" / "code" / "可视化"
if str(VIS) not in sys.path:
    sys.path.insert(0, str(VIS))

from experiment_cases import generate_case  # noqa: E402
from experiment_methods import method_by_key, run_method  # noqa: E402


RAW_FIELDS = (
    "case_kind",
    "seed",
    "runtime_ms",
    "repeats",
    "path_qp_solved",
    "speed_qp_solved",
    "terminal_goal_relaxed",
    "iterations",
    "converged",
    "parity_ok",
    "parity_reason",
    "external_wall_ms",
    "reference_runtime_ms",
)


def _compare_values(actual, expected, name: str, tolerance: float) -> str:
    if expected is None or actual is None:
        return "" if expected is None and actual is None else f"{name} nullability"
    left = np.asarray(actual, dtype=float)
    right = np.asarray(expected, dtype=float)
    if left.shape != right.shape:
        return f"{name} length"
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        return f"{name} non-finite"
    mismatches = np.flatnonzero(np.abs(left - right) > tolerance)
    if mismatches.size:
        return f"{name} at {int(mismatches[0])}"
    return ""


def validate_full(method, reference: dict, tolerance: float) -> str:
    """Return the first specific mismatch against exporter `expected_full`."""

    result = method.result
    scalar_checks = (
        (method.iterations, reference["iterations"], "iteration count"),
        (method.converged, reference["converged"], "convergence"),
        (result["blocked_idx"], reference["blocked_idx"], "blocked index"),
        (
            result["spatial_homotopy_candidate_count"],
            reference["spatial_candidate_count"],
            "spatial candidate count",
        ),
        (
            result["temporal_homotopy_candidate_count"],
            reference["temporal_candidate_count"],
            "temporal candidate count",
        ),
        (
            result["terminal_goal_relaxed"],
            reference["terminal_goal_relaxed"],
            "terminal retry",
        ),
        (result["s_qp"] is not None, reference["s"] is not None, "speed QP status"),
    )
    for actual, expected, name in scalar_checks:
        if actual != expected:
            return name

    trajectories = (
        (result["s_arr"], reference["path_stations"], "path stations", 1e-9),
        (result["l_path"], reference["path_offsets"], "path offsets", tolerance),
        (result["kappa_s"], reference["curvature"], "curvature", tolerance),
        (
            result["a_y"],
            reference["lateral_acceleration"],
            "lateral acceleration",
            tolerance,
        ),
        (result["s_qp"], reference["s"], "s", tolerance),
        (result["v_qp"], reference["v"], "v", tolerance),
        (result["a_qp"], reference["a"], "a", tolerance),
    )
    for actual, expected, name, allowed_error in trajectories:
        reason = _compare_values(actual, expected, name, allowed_error)
        if reason:
            return reason
    return ""


def _read_references(path: Path, expected_cases: int) -> list[tuple]:
    cases = []
    seen = set()
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("schema_version") != "miku-speed-stage-v1":
                raise ValueError(f"line {number}: unexpected reference schema")
            key = row["case_kind"], int(row["seed"])
            if key in seen:
                raise ValueError(f"duplicate scenario {key}")
            seen.add(key)
            reference = row.get("expected_full")
            if not isinstance(reference, dict):
                raise ValueError(f"{key}: missing expected_full reference")
            scenario = generate_case(*key).planning_scenario
            if asdict(scenario) != row["scenario"]:
                raise ValueError(f"{key}: scenario generator and snapshot differ")
            cases.append((key, scenario, reference))
    if not cases or (expected_cases and len(cases) != expected_cases):
        raise ValueError(f"expected {expected_cases or 'nonzero'} cases, got {len(cases)}")
    return cases


def _quantile(values: list[float], probability: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), probability))


def benchmark(
    cases: list[tuple],
    repeats: int,
    warmup: int,
    trajectory_tolerance: float,
) -> tuple[list[dict], dict]:
    if repeats <= 0 or warmup < 0 or trajectory_tolerance <= 0.0:
        raise ValueError("repeats > 0, warmup >= 0 and trajectory tolerance > 0 required")

    method_spec = method_by_key("MIKU")
    raw_rows = []
    reference_worst_ratio = 0.0
    for key, scenario, reference in cases:
        reasons = []
        last_run = None
        for _ in range(warmup):
            last_run = run_method(method_spec, scenario)
            reasons.append(validate_full(last_run, reference, trajectory_tolerance))

        internal_ms = []
        external_ms = []
        for _ in range(repeats):
            started = time.perf_counter_ns()
            last_run = run_method(method_spec, scenario)
            external_ms.append((time.perf_counter_ns() - started) / 1e6)
            internal_ms.append(last_run.runtime_ms)
            reasons.append(validate_full(last_run, reference, trajectory_tolerance))

        assert last_run is not None
        observed = last_run.result
        reason = next((value for value in reasons if value), "")
        reference_runtime_ms = float(reference["runtime_ms"])
        if not math.isfinite(reference_runtime_ms) or reference_runtime_ms <= 0:
            raise ValueError(f"{key}: invalid reference runtime")
        reference_worst_ratio = max(
            reference_worst_ratio,
            median(internal_ms) / reference_runtime_ms,
        )
        raw_rows.append(
            {
                "case_kind": key[0],
                "seed": key[1],
                "runtime_ms": median(internal_ms),
                "repeats": repeats,
                # run_method returns the path solution, not its solver status.
                "path_qp_solved": "",
                "speed_qp_solved": int(observed["s_qp"] is not None),
                "terminal_goal_relaxed": int(observed["terminal_goal_relaxed"]),
                "iterations": last_run.iterations,
                "converged": int(last_run.converged),
                "parity_ok": int(not reason),
                "parity_reason": reason,
                "external_wall_ms": median(external_ms),
                "reference_runtime_ms": reference_runtime_ms,
            }
        )

    inner = [float(row["runtime_ms"]) for row in raw_rows]
    external = [float(row["external_wall_ms"]) for row in raw_rows]
    mismatches = [row for row in raw_rows if not row["parity_ok"]]
    summary = {
        "schema_version": "miku-full-python-timing-v1",
        "runtime_scope": "complete MethodRun.runtime_ms (run_method(MIKU))",
        "case_count": len(raw_rows),
        "repeats_per_case": repeats,
        "warmup_per_case": warmup,
        "matched_case_count": len(raw_rows) - len(mismatches),
        "parity_error_count": len(mismatches),
        "first_parity_error": (
            None
            if not mismatches
            else f"{mismatches[0]['case_kind']}/{mismatches[0]['seed']}: "
            f"{mismatches[0]['parity_reason']}"
        ),
        "python_runtime_p50_ms": _quantile(inner, 0.5),
        "python_runtime_p95_ms": _quantile(inner, 0.95),
        "python_runtime_p99_ms": _quantile(inner, 0.99),
        "python_runtime_sum_ms": sum(inner),
        "external_wall_p50_ms": _quantile(external, 0.5),
        "external_wall_p95_ms": _quantile(external, 0.95),
        "external_wall_p99_ms": _quantile(external, 0.99),
        "external_wall_sum_ms": sum(external),
        "max_repeated_over_reference_runtime_ratio": reference_worst_ratio,
        "trajectory_abs_tolerance_m_or_mps": trajectory_tolerance,
        "path_qp_solver_status": "not exposed by run_method; standalone path QP has a separate 3500-case status check",
        "interpreter": sys.version.split()[0],
        "machine": platform.platform(),
    }
    return raw_rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "submission_artifacts" / "cpp_benchmark" / "miku_full_method_140.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "submission_artifacts" / "cpp_benchmark" / "miku_full_method_140.python_raw.csv",
    )
    parser.add_argument("--expected-cases", type=int, default=140)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--tolerance", type=float, default=0.01)
    args = parser.parse_args()
    if args.expected_cases < 0:
        parser.error("--expected-cases must be non-negative")
    if sys.version_info[:2] != (3, 12):
        parser.error("use the frozen supplement's Python 3.12 environment")

    cases = _read_references(args.input, args.expected_cases)
    raw_rows, summary = benchmark(cases, args.repeats, args.warmup, args.tolerance)
    summary["input_jsonl"] = str(args.input)
    summary["input_sha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    summary["raw_csv"] = str(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=RAW_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(raw_rows)
    summary_path = args.output.with_suffix(".json")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if summary["parity_error_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
