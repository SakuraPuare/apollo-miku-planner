#!/usr/bin/env python3
"""Join per-case Python/C++ path-boundary timings after output validation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
from pathlib import Path

from validate_path_bounds import compare


def summarize(cpp_path: Path, python_path: Path, python_raw: Path,
              inputs: Path, reference: Path, repeat: int) -> dict:
    if repeat <= 0:
        raise ValueError("repeat must be positive")
    python_report = json.loads(python_path.read_text(encoding="utf-8"))
    if hashlib.sha256(inputs.read_bytes()).hexdigest() != python_report["input_sha256"]:
        raise ValueError("Python and C++ CSV input hashes differ")
    validation = compare(cpp_path, reference, 1e-9)
    if not validation["matched"]:
        raise ValueError(f"Python/C++ station mismatch: {validation['mismatch_examples']}")
    with python_raw.open(encoding="utf-8", newline="") as stream:
        raw = {
            (row["case_kind"], int(row["seed"])): row
            for row in csv.DictReader(stream)
        }
    cpp_ms = 0.0
    python_ms = 0.0
    case_count = 0
    station_count = 0
    worst_per_case_runtime_ratio = 0.0
    checksum_per_run = 0.0
    last_station_idx = -1
    with cpp_path.open(encoding="utf-8", newline="") as stream:
        last_key = None
        previous_upper = 0.0
        for row in csv.DictReader(stream):
            key = row["case_kind"], int(row["seed"])
            station_idx = int(row["station_idx"])
            if key != last_key:
                if last_key is not None:
                    if last_station_idx + 1 != int(raw[last_key]["station_count"]):
                        raise ValueError(f"incomplete station sequence for {last_key}")
                    checksum_per_run += previous_upper
                if station_idx != 0 or key not in raw:
                    raise ValueError(f"unmatched first station: {key}/{station_idx}")
                if int(raw[key]["station_count"]) < 1:
                    raise ValueError(f"empty case: {key}")
                case_count += 1
                cpp_runtime = float(row["runtime_ms"])
                python_runtime = float(raw[key]["runtime_ms"])
                cpp_ms += cpp_runtime
                python_ms += python_runtime
                worst_per_case_runtime_ratio = max(
                    worst_per_case_runtime_ratio, python_runtime / cpp_runtime
                )
                checksum_per_run += (
                    float(row["l_min"]) + int(row["blocked_idx"])
                    + int(row["spatial_candidate_count"])
                )
                last_key = key
            elif station_idx != last_station_idx + 1:
                raise ValueError("invalid station sequence")
            previous_upper = float(row["l_max"])
            last_station_idx = station_idx
            station_count += 1
        if last_key is not None:
            if last_station_idx + 1 != int(raw[last_key]["station_count"]):
                raise ValueError(f"incomplete station sequence for {last_key}")
            checksum_per_run += previous_upper
    if case_count != python_report["case_count"] or station_count != python_report["station_count"]:
        raise ValueError("Python/C++ case or station count differs")
    if abs(python_ms * python_report["repeat_count"] / 1000.0 -
           python_report["elapsed_s"]) > 1e-6:
        raise ValueError("Python per-case and aggregate times disagree")
    if abs(checksum_per_run - python_report["checksum"] /
           python_report["repeat_count"]) > 1e-6:
        raise ValueError("Python/C++ normalized result checksum differs")
    return {
        "runtime_scope": "frozen path_bounds_decider(scn, 'miku') only",
        "input_file": str(inputs),
        "input_sha256": python_report["input_sha256"],
        "cpp_station_csv": str(cpp_path),
        "python_summary": str(python_path),
        "case_count": case_count,
        "station_count": station_count,
        "compared_stations": validation["station_count"],
        "max_station_abs_error_m": validation["max_abs_error"],
        "cpp_repeat_count": repeat,
        "python_repeat_count": python_report["repeat_count"],
        "cpp_aggregate_elapsed_s": cpp_ms * repeat / 1000.0,
        "python_aggregate_elapsed_s": python_report["elapsed_s"],
        "cpp_mean_runtime_us": cpp_ms * 1000.0 / case_count,
        "python_mean_runtime_us": python_ms * 1000.0 / case_count,
        "python_to_cpp_ratio": python_ms / cpp_ms,
        "worst_per_case_runtime_ratio": worst_per_case_runtime_ratio,
        "normalized_result_checksum_cpp": checksum_per_run,
        "normalized_result_checksum_python": (
            python_report["checksum"] / python_report["repeat_count"]
        ),
        "compiler": subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
        "flags": "-std=c++17 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -Werror",
        "python_interpreter": python_report["interpreter"],
        "machine": platform.platform(),
        "timing_note": (
            "Saved Python/C++ repetition runs briefly overlapped on CPU; "
            "the stage ratio is indicative and is not a full-method conversion."
        ),
        "limitation": (
            "Path boundary only; excludes path QP, ST mapping/DP, speed QP, "
            "replanning, fallback, Apollo integration and system overhead."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpp", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--python-raw", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--cpp-repeat", type=int, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.cpp, args.python, args.python_raw, args.input,
                       args.reference, args.cpp_repeat)
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
