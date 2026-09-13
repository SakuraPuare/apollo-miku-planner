#!/usr/bin/env python3
"""Validate the paired C++/Python path-QP run before computing its ratio."""

from __future__ import annotations

import argparse
import csv
import ctypes
import ctypes.util
import hashlib
import json
import platform
import subprocess
from pathlib import Path


def _rows(path: Path) -> dict[tuple[str, int], dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    indexed = {(row["case_kind"], int(row["seed"])): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"duplicate case in {path}")
    return indexed


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(
    input_path: Path,
    python_json: Path,
    python_raw: Path,
    cpp_raw: Path,
    cpp_source: Path,
    tolerance: float,
) -> dict:
    if tolerance <= 0.0:
        raise ValueError("positive absolute numerical tolerance is required")
    python = json.loads(python_json.read_text(encoding="utf-8"))
    if python["input_sha256"] != _sha256(input_path):
        raise ValueError("Python path-QP input hash no longer matches TSV")
    py_rows, cpp_rows = _rows(python_raw), _rows(cpp_raw)
    if py_rows.keys() != cpp_rows.keys() or len(py_rows) != python["case_count"]:
        raise ValueError("Python and C++ path-QP case keys differ")

    repeat = python["repeat_count"]
    max_error = 0.0
    solved = 0
    station_count = 0
    cpp_elapsed_ms = 0.0
    python_elapsed_ms = 0.0
    for key, py_row in py_rows.items():
        cpp_row = cpp_rows[key]
        for field in ("station_count", "blocked_idx", "repeats"):
            if py_row[field] != cpp_row[field]:
                raise ValueError(f"{key}: {field} differs across language runs")
        if int(cpp_row["repeats"]) != repeat:
            raise ValueError(f"{key}: repeat count is inconsistent")
        error = float(cpp_row["max_abs_error_m"])
        if error > tolerance:
            raise ValueError(f"{key}: path output differs by {error} m")
        max_error = max(max_error, error)
        solved += int(cpp_row["solved"])
        station_count += int(cpp_row["station_count"])
        cpp_elapsed_ms += float(cpp_row["runtime_ms"]) * repeat
        python_elapsed_ms += float(py_row["runtime_ms"]) * repeat
    if station_count != python["station_count"]:
        raise ValueError("station count does not match the Python export")
    if abs(python_elapsed_ms / 1000 - python["python_aggregate_elapsed_s"]) > 1e-6:
        raise ValueError("Python raw elapsed time differs from Python summary")
    osqp_library = ctypes.util.find_library("osqp")
    if osqp_library is None:
        raise RuntimeError("system libosqp is unavailable")
    linked_osqp = ctypes.CDLL(osqp_library)
    linked_osqp.osqp_version.restype = ctypes.c_char_p
    c_osqp_version = linked_osqp.osqp_version().decode("ascii")
    compiler = subprocess.run(
        ["g++", "--version"], capture_output=True, text=True, check=True
    ).stdout.splitlines()[0]
    cpp_elapsed_s = cpp_elapsed_ms / 1000.0
    python_elapsed_s = python_elapsed_ms / 1000.0
    return {
        "schema_version": "miku-path-qp-paired-calibration-v1",
        "status": "measured_path_qp_only",
        "runtime_scope": python["runtime_scope"],
        "python_to_cpp_ratio": python_elapsed_s / cpp_elapsed_s,
        "python_aggregate_elapsed_s": python_elapsed_s,
        "cpp_aggregate_elapsed_s": cpp_elapsed_s,
        "case_count": len(py_rows),
        "station_count": station_count,
        "repeat_count": repeat,
        "measured_call_count": len(py_rows) * repeat,
        "matched_cases": len(py_rows),
        "matched_station_values": station_count,
        "max_abs_lateral_error_m": max_error,
        "numeric_tolerance_m": tolerance,
        "cpp_solved_case_count": solved,
        "path_qp_share_diagnostic": python.get("path_qp_share_diagnostic"),
        "python": {
            "interpreter": python["interpreter"],
            "osqp_version": python["osqp_python_version"],
            "raw_timing_csv": str(python_raw),
        },
        "cpp": {
            "compiler": compiler,
            "flags": "-std=c++17 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -Werror -I. -losqp",
            "libosqp_version": c_osqp_version,
            "source": str(cpp_source),
            "source_sha256": _sha256(cpp_source),
            "raw_timing_csv": str(cpp_raw),
        },
        "machine": {"architecture": platform.machine(), "system": platform.platform()},
        "input_tsv": str(input_path),
        "input_sha256": python["input_sha256"],
        "limitation": "Path QP only: path bounds, ST mapping, DP, speed QP, search, fallback decisions, Apollo/CyberRT and end-to-end planning are excluded. Dividing a full Python planner time by this ratio is an extrapolation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path("submission_artifacts/cpp_benchmark")
    parser.add_argument("--input", type=Path, default=root / "miku_path_qp_3500.tsv")
    parser.add_argument(
        "--python-json", type=Path, default=root / "miku_path_qp_3500.python.json"
    )
    parser.add_argument(
        "--python-raw", type=Path, default=root / "miku_path_qp_3500.python_raw.csv"
    )
    parser.add_argument(
        "--cpp-raw", type=Path, default=root / "miku_path_qp_3500.cpp_raw.csv"
    )
    parser.add_argument(
        "--cpp-source", type=Path, default=Path("tools/cpp_path_qp/miku_path_qp.cpp")
    )
    parser.add_argument("--tolerance", type=float, default=0.001)
    parser.add_argument(
        "--output", type=Path, default=root / "miku_path_qp_3500.calibration.json"
    )
    args = parser.parse_args()
    summary = summarize(
        args.input,
        args.python_json,
        args.python_raw,
        args.cpp_raw,
        args.cpp_source,
        args.tolerance,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
