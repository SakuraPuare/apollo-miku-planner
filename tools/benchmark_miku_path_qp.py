#!/usr/bin/env python3
"""Export and time the manuscript Python path QP with identical C++ inputs.

The TSV contains the bounds constructed by the frozen supplement's MIKU path
decider plus the path_optimizer's expected solution at every station.  The
timed function includes dense Hessian assembly, sparse CSC conversion, OSQP
setup/solve and the original fallback exactly as in apollo_pipeline.py.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIS_ROOT = (
    REPO_ROOT / "小论文" / "jits_submission" / "supplement" / "code" / "可视化"
)
if str(VIS_ROOT) not in sys.path:
    sys.path.insert(0, str(VIS_ROOT))

import apollo_pipeline as pipeline  # noqa: E402
from experiment_cases import CASE_KINDS, generate_case  # noqa: E402
from experiment_methods import method_by_key  # noqa: E402


FIELDS = (
    "case_kind",
    "seed",
    "station_idx",
    "s",
    "l_min",
    "l_max",
    "expected_l_path",
    "blocked_idx",
    "spatial_candidate_count",
)


def _float(value: float) -> str:
    return format(float(value), ".17g")


def _generate_cases(seed_start: int, seeds: int):
    flags = method_by_key("MIKU").flags
    for kind in CASE_KINDS:
        for seed in range(seed_start, seed_start + seeds):
            scenario = generate_case(kind, seed).planning_scenario
            s_arr, l_min, l_max, blocked, groups = pipeline.path_bounds_decider(
                scenario, flags
            )
            expected, _ = pipeline.path_optimizer(s_arr, l_min, l_max)
            candidate_count = max(
                (
                    int(group.get("spatial_homotopy_candidate_count", 0))
                    for group in groups
                ),
                default=0,
            )
            yield (
                kind,
                seed,
                s_arr,
                l_min,
                l_max,
                expected,
                blocked,
                candidate_count,
            )


def export(seed_start: int, seeds: int, path: Path) -> dict:
    if seed_start < 0 or seeds <= 0:
        raise ValueError("seed_start must be non-negative and seeds must be positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    case_count = 0
    station_count = 0
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(FIELDS)
        for kind, seed, stations, lower, upper, expected, blocked, candidates in (
            _generate_cases(seed_start, seeds)
        ):
            case_count += 1
            for index, (s, l_min, l_max, l_path) in enumerate(
                zip(stations, lower, upper, expected, strict=True)
            ):
                writer.writerow(
                    (
                        kind,
                        seed,
                        index,
                        _float(s),
                        _float(l_min),
                        _float(l_max),
                        _float(l_path),
                        blocked,
                        candidates,
                    )
                )
                station_count += 1
    return {
        "case_count": case_count,
        "station_count": station_count,
        "seed_start": seed_start,
        "seed_count_per_kind": seeds,
        "family_count": len(CASE_KINDS),
    }


def _read(path: Path) -> list[tuple]:
    cases: list[tuple] = []
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("unexpected path-QP TSV schema")
        for row in reader:
            key = row["case_kind"], int(row["seed"])
            if not cases or cases[-1][0] != key:
                cases.append((key, [], [], [], [], int(row["blocked_idx"])))
            label, stations, lower, upper, expected, blocked = cases[-1]
            if key != label or int(row["station_idx"]) != len(stations):
                raise ValueError("cases or station indices are not contiguous")
            if blocked != int(row["blocked_idx"]):
                raise ValueError("inconsistent blocked index within one case")
            stations.append(float(row["s"]))
            lower.append(float(row["l_min"]))
            upper.append(float(row["l_max"]))
            expected.append(float(row["expected_l_path"]))
    if not cases:
        raise ValueError("empty path-QP input")
    return cases


def benchmark(cases: list[tuple], path: Path, repeats: int, tolerance: float) -> dict:
    import numpy as np

    if repeats <= 0 or tolerance <= 0:
        raise ValueError("repeats and tolerance must be positive")
    total_ms = 0.0
    checksum = 0.0
    max_abs_error = 0.0
    raw_rows = []
    for key, s_arr, lower, upper, expected, blocked in cases:
        stations = np.asarray(s_arr, dtype=float)
        lo = np.asarray(lower, dtype=float)
        hi = np.asarray(upper, dtype=float)
        target = np.asarray(expected, dtype=float)
        for _ in range(3):
            path_result, _ = pipeline.path_optimizer(stations, lo, hi)
            checksum += float(path_result.sum())

        start = time.perf_counter()
        for _ in range(repeats):
            path_result, _ = pipeline.path_optimizer(stations, lo, hi)
            checksum += float(path_result.sum())
        runtime_ms = (time.perf_counter() - start) * 1000.0 / repeats
        total_ms += runtime_ms
        error = float(np.max(np.abs(path_result - target)))
        max_abs_error = max(max_abs_error, error)
        if not math.isfinite(error) or error > tolerance:
            raise AssertionError(f"Python path-QP drift at {key}: {error}")
        raw_rows.append(
            {
                "case_kind": key[0],
                "seed": key[1],
                "station_count": len(stations),
                "blocked_idx": blocked,
                "repeats": repeats,
                "runtime_ms": runtime_ms,
                "max_abs_error_m": error,
            }
        )

    raw_path = path.with_suffix(".python_raw.csv")
    with raw_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(raw_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(raw_rows)
    return {
        "runtime_scope": "path_optimizer: Hessian/CSC assembly + OSQP setup/solve + fallback",
        "input_file": str(path),
        "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "case_count": len(cases),
        "station_count": sum(len(case[1]) for case in cases),
        "repeat_count": repeats,
        "measured_call_count": len(cases) * repeats,
        "python_aggregate_elapsed_s": total_ms * repeats / 1000.0,
        "python_mean_runtime_ms": total_ms / len(cases),
        "max_python_rerun_abs_error_m": max_abs_error,
        "checksum": checksum,
        "raw_timing_csv": str(raw_path),
        "interpreter": sys.version.split()[0],
        "osqp_python_version": __import__("osqp").__version__,
        "machine": platform.platform(),
    }


def _measure_coverage(seed_start: int, seeds: int, stride: int) -> dict:
    """Measure this QP's share in actual complete Python MIKU planning calls."""

    from experiment_methods import run_method

    original = pipeline.path_optimizer
    timed_ns = 0
    invocation_count = 0

    def measured_path_optimizer(*args, **kwargs):
        nonlocal timed_ns, invocation_count
        start = time.perf_counter_ns()
        try:
            return original(*args, **kwargs)
        finally:
            timed_ns += time.perf_counter_ns() - start
            invocation_count += 1

    method = method_by_key("MIKU")
    family_rows = []
    pipeline.path_optimizer = measured_path_optimizer
    try:
        for kind in CASE_KINDS:
            before_ns = timed_ns
            before_calls = invocation_count
            elapsed_ms = 0.0
            for seed in range(seed_start, seed_start + seeds * stride, stride):
                scenario = generate_case(kind, seed).planning_scenario
                elapsed_ms += run_method(method, scenario).runtime_ms
            path_ms = (timed_ns - before_ns) / 1e6
            family_rows.append(
                {
                    "case_kind": kind,
                    "case_count": seeds,
                    "full_python_runtime_ms": elapsed_ms,
                    "path_optimizer_runtime_ms": path_ms,
                    "path_qp_share": path_ms / elapsed_ms,
                    "path_optimizer_call_count": invocation_count - before_calls,
                }
            )
    finally:
        pipeline.path_optimizer = original

    full_ms = sum(row["full_python_runtime_ms"] for row in family_rows)
    path_ms = sum(row["path_optimizer_runtime_ms"] for row in family_rows)
    return {
        "scope": "path_optimizer within complete Python run_method(MIKU)",
        "seed_start": seed_start,
        "seed_stride": stride,
        "sample_count_per_family": seeds,
        "total_case_count": seeds * len(CASE_KINDS),
        "full_python_runtime_ms": full_ms,
        "path_optimizer_runtime_ms": path_ms,
        "path_qp_share": path_ms / full_ms,
        "path_optimizer_call_count": invocation_count,
        "by_family": family_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seeds", type=int, default=500)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--tolerance", type=float, default=1e-5)
    parser.add_argument("--coverage-seeds", type=int, default=0)
    parser.add_argument("--coverage-stride", type=int, default=25)
    parser.add_argument("--input", type=Path, help="read a previously exported TSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "submission_artifacts" / "cpp_benchmark" / "miku_path_qp_3500.tsv",
    )
    args = parser.parse_args()
    if args.seed_start < 0 or args.seeds <= 0 or args.repeat <= 0:
        parser.error("--seed-start >= 0, --seeds > 0 and --repeat > 0 required")
    if args.coverage_seeds < 0 or args.coverage_stride <= 0:
        parser.error("--coverage-seeds >= 0 and --coverage-stride > 0 required")

    path = args.input or args.output
    if args.input is None:
        metadata = export(args.seed_start, args.seeds, path)
    else:
        metadata = {}
    result = benchmark(_read(path), path, args.repeat, args.tolerance)
    result.update(metadata)
    if args.coverage_seeds:
        result["path_qp_share_diagnostic"] = _measure_coverage(
            args.seed_start, args.coverage_seeds, args.coverage_stride
        )
    target = args.output.with_suffix(".python.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
