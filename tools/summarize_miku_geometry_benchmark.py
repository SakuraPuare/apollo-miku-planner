#!/usr/bin/env python3
"""Validate paired MIKU geometry timings and write an auditable calibration."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import statistics
from pathlib import Path


KEY = ("case_kind", "seed", "group_index")
FLOAT_TOLERANCE = 1e-9


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matches(left: str, right: str) -> bool:
    return math.isclose(
        float(left), float(right), rel_tol=FLOAT_TOLERANCE, abs_tol=FLOAT_TOLERANCE
    )


def cpu_model() -> str | None:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                return line.partition(":")[2].strip()
    return None


def summarize(input_path: Path, python_json_path: Path, python_raw_path: Path,
              cpp_raw_path: Path, cpp_source_path: Path) -> dict:
    cases = read_rows(input_path)
    python_raw = read_rows(python_raw_path)
    cpp_raw = read_rows(cpp_raw_path)
    python_summary = json.loads(python_json_path.read_text(encoding="utf-8"))
    if not cases or len(cases) != len(python_raw) or len(cases) != len(cpp_raw):
        raise ValueError("input/Python/C++ row counts do not match")

    repeats = {int(row["repeats"]) for row in (*python_raw, *cpp_raw)}
    if len(repeats) != 1:
        raise ValueError("Python and C++ repeat counts must agree across groups")
    repeat_count = repeats.pop()
    if repeat_count <= 0 or repeat_count != python_summary["repeat_count"]:
        raise ValueError("Python summary repeat count does not match raw records")

    for case, py, cpp in zip(cases, python_raw, cpp_raw, strict=True):
        key = tuple(case[field] for field in KEY)
        if key != tuple(py[field] for field in KEY) or key != tuple(cpp[field] for field in KEY):
            raise ValueError(f"case/group order mismatch at {key}")
        if int(case["n"]) != int(py["interval_count"]) or int(case["n"]) != int(cpp["interval_count"]):
            raise ValueError(f"case/group interval count mismatch at {key}")
        if int(case["expected_split"]) != int(cpp["max_gap_split"]):
            raise ValueError(f"maximum-gap split mismatch at {key}")
        for expected, actual in (
            ("expected_gap", "max_gap_width"),
            ("expected_lower", "max_gap_lower"),
            ("expected_upper", "max_gap_upper"),
        ):
            if not matches(case[expected], cpp[actual]):
                raise ValueError(f"maximum-gap {expected} mismatch at {key}")
        n_bands = int(case["expected_band_count"])
        if n_bands != int(cpp["band_count"]):
            raise ValueError(f"band count mismatch at {key}")
        for i in range(n_bands):
            if int(case[f"expected_band{i}_split"]) != int(cpp[f"band{i}_split"]):
                raise ValueError(f"band {i} split mismatch at {key}")
            for expected, actual in (
                ("gap", "width"),
                ("lower", "lower"),
                ("upper", "upper"),
            ):
                if not matches(
                    case[f"expected_band{i}_{expected}"], cpp[f"band{i}_{actual}"]
                ):
                    raise ValueError(f"band {i} {expected} mismatch at {key}")

    python_elapsed = sum(float(row["runtime_ms"]) * repeat_count / 1000 for row in python_raw)
    cpp_elapsed = sum(float(row["runtime_ms"]) * repeat_count / 1000 for row in cpp_raw)
    if not math.isclose(python_elapsed, float(python_summary["elapsed_s"]), rel_tol=1e-8):
        raise ValueError("Python aggregate time differs from Python raw CSV")
    if not (math.isfinite(cpp_elapsed) and cpp_elapsed > 0):
        raise ValueError("invalid C++ aggregate time")

    n_calls = len(cases) * repeat_count
    return {
        "schema_version": "miku-geometry-paired-calibration-v1",
        "status": "measured_geometry_primitives_only",
        "runtime_scope": "solve_max_gap + enumerate_lateral_bands(top_k=3) per active group",
        "python_to_cpp_ratio": python_elapsed / cpp_elapsed,
        "python_aggregate_elapsed_s": python_elapsed,
        "cpp_aggregate_elapsed_s": cpp_elapsed,
        "python_microseconds_per_call_pair": python_elapsed * 1e6 / n_calls,
        "cpp_microseconds_per_call_pair": cpp_elapsed * 1e6 / n_calls,
        "python_median_microseconds_per_call_pair": statistics.median(
            float(row["runtime_ms"]) * 1000 for row in python_raw
        ),
        "cpp_median_microseconds_per_call_pair": statistics.median(
            float(row["runtime_ms"]) * 1000 for row in cpp_raw
        ),
        "case_scenario_count": int(python_summary["seed_count_per_kind"])
        * int(python_summary["scenario_family_count"]),
        "case_group_count": len(cases),
        "repeat_count": repeat_count,
        "call_pair_count": n_calls,
        "matched_groups": len(cases),
        "matched_bands": sum(int(row["expected_band_count"]) for row in cases),
        "floating_point_tolerance": FLOAT_TOLERANCE,
        "geometry_share_diagnostic": python_summary.get("geometry_share_diagnostic"),
        "python": {
            "version": python_summary["interpreter"],
            "checksum": python_summary["checksum"],
            "raw_timing_csv": str(python_raw_path),
        },
        "cpp": {
            "compiler": "g++ (GCC) 16.2.1 20260810",
            "flags": "-std=c++17 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -Werror",
            "raw_timing_csv": str(cpp_raw_path),
            "source": str(cpp_source_path),
            "source_sha256": sha256(cpp_source_path),
        },
        "machine": {
            "cpu_model": cpu_model(),
            "architecture": platform.machine(),
            "system": platform.platform(),
        },
        "input_csv": str(input_path),
        "input_sha256": sha256(input_path),
        "limitation": (
            "A geometry-kernel speed ratio is not an end-to-end C++ planner runtime. "
            "No QP solve, ST stage, certified joint search, safety verification, "
            "iteration, Apollo task scheduling, or CyberRT cycle was measured. "
            "Scaling a complete Python runtime by this ratio is an extrapolation."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--python-json", type=Path, required=True)
    parser.add_argument("--python-raw", type=Path, required=True)
    parser.add_argument("--cpp-raw", type=Path, required=True)
    parser.add_argument("--cpp-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.input, args.python_json, args.python_raw, args.cpp_raw, args.cpp_source)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "python_to_cpp_ratio", "python_aggregate_elapsed_s", "cpp_aggregate_elapsed_s",
        "case_group_count", "matched_bands"
    )}, indent=2))


if __name__ == "__main__":
    main()
