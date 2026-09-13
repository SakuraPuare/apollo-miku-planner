#!/usr/bin/env python3
"""Benchmark paired Python MIKU geometry calls on the manuscript case inputs.

Capture the actual active interval groups passed to enumerate_lateral_bands
during each case's initial MIKU path-boundary construction.  The timed region
contains exactly one solve_max_gap and one enumerate_lateral_bands(top_k=3) per
CSV row.  It excludes scenario generation, CSV parsing, QP, ST and iteration;
its speed ratio is therefore a *geometry-kernel* ratio, not a full-planner one.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import statistics
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
from miku_geometry import (  # noqa: E402
    ForbiddenInterval,
    enumerate_lateral_bands,
    solve_max_gap,
)


MAX_INTERVALS = 8
BAND_COUNT = 3
FIELDS = [
    "case_kind",
    "seed",
    "group_index",
    "road_lower",
    "road_upper",
    "n",
]
for _index in range(MAX_INTERVALS):
    FIELDS.extend((f"obs{_index}_u", f"obs{_index}_v"))
FIELDS.extend(
    (
        "expected_split",
        "expected_gap",
        "expected_lower",
        "expected_upper",
        "expected_band_count",
    )
)
for _index in range(BAND_COUNT):
    FIELDS.extend(
        (
            f"expected_band{_index}_split",
            f"expected_band{_index}_gap",
            f"expected_band{_index}_lower",
            f"expected_band{_index}_upper",
        )
    )


def _float(value: float) -> str:
    return format(float(value), ".17g")


def _capture_calls(seed_start: int, seeds: int) -> list[dict]:
    rows: list[dict] = []
    original = pipeline.enumerate_lateral_bands
    current_kind = ""
    current_seed = -1
    group_index = 0

    def record(intervals, road_lower, road_upper, top_k=None):
        nonlocal group_index
        if top_k != BAND_COUNT:
            raise ValueError(f"unexpected MIKU top_k: {top_k}")
        if len(intervals) > MAX_INTERVALS:
            raise ValueError(
                f"{current_kind}/{current_seed} group {group_index}: "
                f"{len(intervals)} intervals exceeds {MAX_INTERVALS}"
            )
        result = original(intervals, road_lower, road_upper, top_k=top_k)
        expected = solve_max_gap(intervals, road_lower, road_upper)
        row = {
            "case_kind": current_kind,
            "seed": current_seed,
            "group_index": group_index,
            "road_lower": _float(road_lower),
            "road_upper": _float(road_upper),
            "n": len(intervals),
            "expected_split": expected.split_index,
            "expected_gap": _float(expected.gap),
            "expected_lower": _float(expected.lower),
            "expected_upper": _float(expected.upper),
            "expected_band_count": len(result),
        }
        for index, interval in enumerate(intervals):
            row[f"obs{index}_u"] = _float(interval.u)
            row[f"obs{index}_v"] = _float(interval.v)
        for index, band in enumerate(result):
            row[f"expected_band{index}_split"] = band.split_index
            row[f"expected_band{index}_gap"] = _float(band.gap)
            row[f"expected_band{index}_lower"] = _float(band.lower)
            row[f"expected_band{index}_upper"] = _float(band.upper)
        rows.append(row)
        group_index += 1
        return result

    pipeline.enumerate_lateral_bands = record
    try:
        for kind in CASE_KINDS:
            for seed in range(seed_start, seed_start + seeds):
                current_kind, current_seed, group_index = kind, seed, 0
                scenario = generate_case(kind, seed).planning_scenario
                pipeline.path_bounds_decider(scenario, method_by_key("MIKU").flags)
    finally:
        pipeline.enumerate_lateral_bands = original
    return rows


def _read_input(path: Path) -> tuple[list[dict], list[tuple]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError("input CSV does not match the geometry benchmark schema")
        rows = list(reader)
    calls = []
    for row in rows:
        n = int(row["n"])
        if not 0 <= n <= MAX_INTERVALS:
            raise ValueError("invalid interval count")
        intervals = tuple(
            ForbiddenInterval(float(row[f"obs{i}_u"]), float(row[f"obs{i}_v"]))
            for i in range(n)
        )
        calls.append((intervals, float(row["road_lower"]), float(row["road_upper"])))
    return rows, calls


def _validate(rows: list[dict], calls: list[tuple]) -> None:
    for row, (intervals, road_lower, road_upper) in zip(rows, calls, strict=True):
        result = solve_max_gap(intervals, road_lower, road_upper)
        bands = enumerate_lateral_bands(intervals, road_lower, road_upper, top_k=3)
        label = f"{row['case_kind']}/{row['seed']}/{row['group_index']}"
        if result.split_index != int(row["expected_split"]):
            raise AssertionError(f"{label}: maximum-gap split changed")
        for field in ("gap", "lower", "upper"):
            if not math.isclose(
                getattr(result, field), float(row[f"expected_{field}"]), abs_tol=1e-12
            ):
                raise AssertionError(f"{label}: maximum-gap {field} changed")
        if len(bands) != int(row["expected_band_count"]):
            raise AssertionError(f"{label}: candidate count changed")
        for index, band in enumerate(bands):
            if band.split_index != int(row[f"expected_band{index}_split"]):
                raise AssertionError(f"{label}: candidate {index} split changed")
            for field in ("gap", "lower", "upper"):
                if not math.isclose(
                    getattr(band, field),
                    float(row[f"expected_band{index}_{field}"]),
                    abs_tol=1e-12,
                ):
                    raise AssertionError(f"{label}: candidate {index} {field} changed")


def _time_calls(rows: list[dict], calls: list[tuple], repeats: int, output: Path) -> dict:
    if not calls or repeats <= 0:
        raise ValueError("need at least one input and one timed repeat")
    # Match the C++ harness exactly: for each parsed group, warm it three
    # times, then time repeated solve+enumerate pairs for that same group.
    checksum = 0.0
    total_elapsed_s = 0.0
    raw = []
    for row, (intervals, road_lower, road_upper) in zip(rows, calls, strict=True):
        for _ in range(3):
            result = solve_max_gap(intervals, road_lower, road_upper)
            bands = enumerate_lateral_bands(intervals, road_lower, road_upper, top_k=3)
            value = result.gap
            for band in bands:
                value += band.gap
            checksum += value
        start = time.perf_counter()
        for _ in range(repeats):
            result = solve_max_gap(intervals, road_lower, road_upper)
            bands = enumerate_lateral_bands(intervals, road_lower, road_upper, top_k=3)
            value = result.gap
            for band in bands:
                value += band.gap
            checksum += value
        elapsed_s = time.perf_counter() - start
        total_elapsed_s += elapsed_s
        raw.append(
            {
                "case_kind": row["case_kind"],
                "seed": row["seed"],
                "group_index": row["group_index"],
                "interval_count": len(intervals),
                "repeats": repeats,
                "runtime_ms": elapsed_s * 1000.0 / repeats,
            }
        )
    raw_path = output.with_suffix(".python_raw.csv")
    with raw_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(raw[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(raw)
    return {
        "runtime_scope": "solve_max_gap + enumerate_lateral_bands(top_k=3) per active group",
        "elapsed_s": total_elapsed_s,
        "case_group_count": len(calls),
        "repeat_count": repeats,
        "call_pair_count": len(calls) * repeats,
        "microseconds_per_call_pair": total_elapsed_s * 1e6 / (len(calls) * repeats),
        "checksum": checksum,
        "raw_timing_csv": str(raw_path),
        "interpreter": sys.version.split()[0],
        "platform": platform.platform(),
    }


def _time_full_method(seed_start: int, seeds: int) -> dict:
    from experiment_methods import run_method

    method = method_by_key("MIKU")
    times = []
    for kind in CASE_KINDS:
        for seed in range(seed_start, seed_start + seeds):
            scenario = generate_case(kind, seed).planning_scenario
            times.append(run_method(method, scenario).runtime_ms)
    return {
        "case_count": len(times),
        "runtime_scope": "Python run_method(MIKU), including all QP and fallbacks",
        "p50_ms": statistics.median(times),
        "mean_ms": statistics.mean(times),
    }


def _measure_coverage(seed_start: int, seeds: int, stride: int) -> dict:
    """Sample the geometry share inside the actual complete Python MIKU call."""

    from experiment_methods import run_method

    counters = {"solve_max_gap": [0, 0], "enumerate_lateral_bands": [0, 0]}
    original_solve = pipeline.solve_max_gap
    original_bands = pipeline.enumerate_lateral_bands

    def measured_solve(*args, **kwargs):
        start = time.perf_counter_ns()
        try:
            return original_solve(*args, **kwargs)
        finally:
            counters["solve_max_gap"][0] += time.perf_counter_ns() - start
            counters["solve_max_gap"][1] += 1

    def measured_bands(*args, **kwargs):
        start = time.perf_counter_ns()
        try:
            return original_bands(*args, **kwargs)
        finally:
            counters["enumerate_lateral_bands"][0] += time.perf_counter_ns() - start
            counters["enumerate_lateral_bands"][1] += 1

    method = method_by_key("MIKU")
    family_rows = []
    pipeline.solve_max_gap = measured_solve
    pipeline.enumerate_lateral_bands = measured_bands
    try:
        for kind in CASE_KINDS:
            elapsed_ms = 0.0
            before_ns = sum(value[0] for value in counters.values())
            before_calls = sum(value[1] for value in counters.values())
            for seed in range(seed_start, seed_start + seeds * stride, stride):
                scenario = generate_case(kind, seed).planning_scenario
                elapsed_ms += run_method(method, scenario).runtime_ms
            geometry_ms = (
                sum(value[0] for value in counters.values()) - before_ns
            ) / 1e6
            calls = sum(value[1] for value in counters.values()) - before_calls
            family_rows.append(
                {
                    "case_kind": kind,
                    "case_count": seeds,
                    "full_python_runtime_ms": elapsed_ms,
                    "geometry_python_runtime_ms": geometry_ms,
                    "geometry_share": geometry_ms / elapsed_ms,
                    "geometry_call_count": calls,
                }
            )
    finally:
        pipeline.solve_max_gap = original_solve
        pipeline.enumerate_lateral_bands = original_bands

    full_ms = sum(row["full_python_runtime_ms"] for row in family_rows)
    geometry_ms = sum(row["geometry_python_runtime_ms"] for row in family_rows)
    return {
        "scope": "instrumented geometry functions within complete Python run_method(MIKU)",
        "seed_start": seed_start,
        "seed_stride": stride,
        "sample_count_per_family": seeds,
        "total_case_count": seeds * len(CASE_KINDS),
        "full_python_runtime_ms": full_ms,
        "geometry_python_runtime_ms": geometry_ms,
        "geometry_share": geometry_ms / full_ms,
        "function_call_counts": {key: value[1] for key, value in counters.items()},
        "by_family": family_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seeds", type=int, default=500)
    parser.add_argument("--repeat", type=int, default=100)
    parser.add_argument(
        "--input", type=Path, help="reuse an existing exported CSV instead of regenerating"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "submission_artifacts" / "cpp_benchmark" / "miku_geometry_3500.csv",
    )
    parser.add_argument(
        "--full-method", action="store_true", help="add separate Python full-method diagnostics"
    )
    parser.add_argument(
        "--coverage-seeds",
        type=int,
        default=0,
        help="sample this many seeds per family inside full run_method (0=off)",
    )
    parser.add_argument("--coverage-stride", type=int, default=25)
    args = parser.parse_args()
    if args.seed_start < 0 or args.seeds <= 0 or args.repeat <= 0:
        parser.error("--seed-start >= 0, --seeds > 0 and --repeat > 0 required")
    if args.coverage_seeds < 0 or args.coverage_stride <= 0:
        parser.error("--coverage-seeds >= 0 and --coverage-stride > 0 required")

    path = args.input or args.output
    if args.input is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=FIELDS, lineterminator="\n", extrasaction="raise"
            )
            writer.writeheader()
            writer.writerows(_capture_calls(args.seed_start, args.seeds))
    rows, calls = _read_input(path)
    _validate(rows, calls)
    output = _time_calls(rows, calls, args.repeat, args.output)
    output.update(
        {
            "schema_version": "miku-geometry-v1",
            "input_file": str(path),
            "seed_start": args.seed_start,
            "seed_count_per_kind": args.seeds,
            "scenario_family_count": len(CASE_KINDS),
            "validation": "all expected splits, bounds and Top-3 bands match",
        }
    )
    if args.full_method:
        output["python_full_method_diagnostic"] = _time_full_method(
            args.seed_start, args.seeds
        )
    if args.coverage_seeds:
        output["geometry_share_diagnostic"] = _measure_coverage(
            args.seed_start, args.coverage_seeds, args.coverage_stride
        )
    destination = args.output.with_suffix(".python.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
