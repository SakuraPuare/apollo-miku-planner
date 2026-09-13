#!/usr/bin/env python3
"""Compare the standalone C++ path boundary with frozen Python case outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _reference_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        yield from csv.DictReader(stream, delimiter="\t")


def _generated_rows(path: Path, rank: int):
    from benchmark_path_bounds import generate_case, pipeline

    with path.open(newline="", encoding="utf-8") as stream:
        for case in csv.DictReader(stream):
            kind, seed = case["case_kind"], int(case["seed"])
            scenario = generate_case(kind, seed).planning_scenario
            stations, lower, upper, blocked, groups = pipeline.path_bounds_decider(
                scenario, "miku", candidate_rank=rank
            )
            candidates = groups[0]["spatial_homotopy_candidate_count"] if groups else 0
            for index, station in enumerate(stations):
                yield {
                    "case_kind": kind, "seed": seed, "station_idx": index,
                    "s": station, "l_min": lower[index], "l_max": upper[index],
                    "blocked_idx": blocked, "spatial_candidate_count": candidates,
                }


def compare(cpp_path: Path, python_path: Path, tolerance: float,
            *, generated: bool = False, rank: int = 0) -> dict:
    checked = 0
    cases = set()
    max_abs_error = 0.0
    examples: list[dict] = []
    with cpp_path.open(newline="", encoding="utf-8") as cpp_stream:
        cpp_rows = csv.DictReader(cpp_stream)
        python_rows = (_generated_rows(python_path, rank) if generated
                       else _reference_rows(python_path))
        for cpp, reference in zip(cpp_rows, python_rows, strict=True):
            key_cpp = (cpp["case_kind"], int(cpp["seed"]), int(cpp["station_idx"]))
            key_python = (
                reference["case_kind"],
                int(reference["seed"]),
                int(reference["station_idx"]),
            )
            if key_cpp != key_python:
                raise AssertionError(f"case order differs: {key_cpp} != {key_python}")
            cases.add(key_cpp[:2])
            checked += 1
            for field in ("s", "l_min", "l_max"):
                actual = float(cpp[field])
                expected = float(reference[field])
                error = abs(actual - expected)
                max_abs_error = max(max_abs_error, error)
                if error > tolerance * max(1.0, abs(actual), abs(expected)):
                    if len(examples) < 10:
                        examples.append(
                            {"key": key_cpp, "field": field, "cpp": actual,
                             "python": expected, "error": error}
                        )
            for field in ("blocked_idx", "spatial_candidate_count"):
                if int(cpp[field]) != int(reference[field]):
                    if len(examples) < 10:
                        examples.append(
                            {"key": key_cpp, "field": field, "cpp": cpp[field],
                             "python": reference[field]}
                        )
    summary = {
        "case_count": len(cases),
        "station_count": checked,
        "max_abs_error": max_abs_error,
        "tolerance": tolerance,
        "mismatch_examples": examples,
        "matched": not examples,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpp", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--python", type=Path, help="frozen Python path-QP TSV")
    source.add_argument("--cases", type=Path, help="regenerate frozen Python oracle")
    parser.add_argument("--candidate-rank", type=int, default=0)
    parser.add_argument("--tolerance", type=float, default=1e-9)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    if args.candidate_rank < 0 or (args.python and args.candidate_rank):
        parser.error("--candidate-rank requires --cases and nonnegative rank")
    result = compare(args.cpp, args.cases or args.python, args.tolerance,
                     generated=args.cases is not None, rank=args.candidate_rank)
    report = json.dumps(result, indent=2) + "\n"
    print(report, end="")
    if args.summary:
        args.summary.write_text(report, encoding="utf-8")
    if not result["matched"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
