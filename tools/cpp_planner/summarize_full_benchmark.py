"""Check paired complete-method timings and persist a reproducible ratio."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    "tools/cpp_planner/benchmark_first_pass.cpp",
    "tools/cpp_path_stage/miku_path_bounds.cpp",
    "tools/cpp_path_stage/miku_path_bounds.h",
    "tools/cpp_path_qp/miku_path_qp.cpp",
    "tools/cpp_path_qp/miku_path_qp.h",
    "tools/cpp_speed_stage/speed_stage.cpp",
    "tools/cpp_speed_stage/speed_stage.h",
    "小论文/jits_submission/supplement/code/可视化/experiment_methods.py",
    "小论文/jits_submission/supplement/code/可视化/apollo_pipeline.py",
    "小论文/jits_submission/supplement/code/可视化/miku_geometry.py",
    "小论文/jits_submission/supplement/code/可视化/miku_time.py",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(numbers: list[float], probability: float) -> float:
    ordered = sorted(numbers)
    position = (len(ordered) - 1) * probability
    index = int(position)
    fraction = position - index
    return ordered[index] * (1.0 - fraction) + ordered[min(index + 1, len(ordered) - 1)] * fraction


def read_rows(path: Path) -> dict[tuple[str, int], dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    output = {}
    for row in rows:
        key = row["case_kind"], int(row["seed"])
        if key in output:
            raise ValueError(f"duplicate key in {path}: {key}")
        output[key] = row
    return output


def calibrate(python_csv: Path, cpp_csv: Path, reference: Path) -> dict:
    python_report = python_csv.with_suffix(".json")
    report = json.loads(python_report.read_text(encoding="utf-8"))
    if (report.get("input_sha256") != digest(reference) or
            report.get("parity_error_count") != 0 or
            report.get("case_count") != 140):
        raise ValueError("Python timing sidecar does not match the current 140-case reference")
    python, cpp = read_rows(python_csv), read_rows(cpp_csv)
    if len(python) != 140 or python.keys() != cpp.keys():
        raise ValueError("complete-method calibration requires the same 140 scenarios")
    cases = []
    for key, py in python.items():
        native = cpp[key]
        if py["parity_ok"] != "1" or native["parity_ok"] != "1":
            raise ValueError(f"trajectory mismatch for {key}: {py['parity_reason']}/{native['parity_reason']}")
        for field in ("speed_qp_solved", "terminal_goal_relaxed", "iterations", "converged"):
            if py[field] != native[field]:
                raise ValueError(f"{field} mismatch for {key}")
        if int(py["repeats"]) != int(native["repeats"]) or int(py["repeats"]) != 3:
            raise ValueError(f"unpaired repetition count for {key}")
        py_ms, cpp_ms = float(py["runtime_ms"]), float(native["runtime_ms"])
        if not all(math.isfinite(x) and x > 0 for x in (py_ms, cpp_ms)):
            raise ValueError(f"invalid duration for {key}")
        cases.append((key[0], py_ms, cpp_ms))
    py_times, native_times = [item[1] for item in cases], [item[2] for item in cases]
    total_python, total_cpp = sum(py_times), sum(native_times)
    families = sorted({item[0] for item in cases})
    return {
        "schema_version": "miku-complete-method-paired-calibration-v1",
        "status": "measured_matching_simulation_method_outputs_on_calibration_sample",
        "runtime_scope": "MIKU run_method path bounds, path QP, ST/DP/temporal graph, speed QP, fallback, optional refinement, trajectory postprocessing",
        "python_to_cpp_ratio": total_python / total_cpp,
        "formula": "sum of matched Python per-scenario medians / sum of matched C++ per-scenario medians",
        "sample": "20 seeds spaced 25 apart from each of seven 500-seed scenario families",
        "case_count": len(cases),
        "matched_cases": len(cases),
        "repeat_count_per_language": 3,
        "warmup_count_per_language": 1,
        "python_aggregate_median_runtime_ms": total_python,
        "cpp_aggregate_median_runtime_ms": total_cpp,
        "python_p50_ms": quantile(py_times, 0.50),
        "cpp_p50_ms": quantile(native_times, 0.50),
        "python_p95_ms": quantile(py_times, 0.95),
        "cpp_p95_ms": quantile(native_times, 0.95),
        "python_p99_ms": quantile(py_times, 0.99),
        "cpp_p99_ms": quantile(native_times, 0.99),
        "families": [
            {
                "name": name,
                "case_count": sum(1 for group, _, _ in cases if group == name),
                "python_to_cpp_ratio": (
                    sum(py for group, py, _ in cases if group == name) /
                    sum(native for group, _, native in cases if group == name)
                ),
            }
            for name in families
        ],
        "source_sha256": {path: digest(ROOT / path) for path in SOURCES},
        "input_sha256": {
            "python_csv": digest(python_csv),
            "python_report": digest(python_report),
            "cpp_csv": digest(cpp_csv),
            "reference_jsonl": digest(reference),
        },
        "compiler": "g++ -std=c++17 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -Werror -I. -Itools/cpp_path_stage -Itools/cpp_path_qp -Itools/cpp_speed_stage; -losqp",
        "boundary": "Native C++ port of the simulated MIKU planning method on 140 matching cases. This ratio applied to the paper's 3500-scenario Python runtime distribution is an estimate, not measured C++ P99 for all 3500 cases or Apollo/CyberRT latency.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    folder = ROOT / "submission_artifacts/cpp_benchmark"
    parser.add_argument("--python-csv", type=Path, default=folder / "miku_full_method_140.python_raw.csv")
    parser.add_argument("--cpp-csv", type=Path, default=folder / "miku_full_method_140.cpp_raw.csv")
    parser.add_argument("--reference", type=Path, default=folder / "miku_full_method_140.jsonl")
    parser.add_argument("--output", type=Path, default=folder / "miku_full_method_140.calibration.json")
    args = parser.parse_args()
    data = calibrate(args.python_csv, args.cpp_csv, args.reference)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: data[key] for key in ("case_count", "matched_cases", "python_to_cpp_ratio", "python_p99_ms", "cpp_p99_ms")}, indent=2))


if __name__ == "__main__":
    main()
