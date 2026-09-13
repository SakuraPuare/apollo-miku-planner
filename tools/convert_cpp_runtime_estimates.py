"""Project recorded Python compute times using a measured Python/C++ ratio.

The source bundle remains immutable. These projections are not C++ planner
measurements; only the calibration workload itself is timed in both languages.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path


RUNTIME_FIELDS = re.compile(r"^(?:runtime(?:_p\d+)?|episode_runtime(?:_p\d+)?|qp_\w+)_ms$")
RUNTIME_MACRO = re.compile(r"^(\\newcommand\{\\[^}]*?(?:Runtime|Qp)[^}]*\}\{)(-?\d+(?:\.\d+)?)(\}.*)$")
DERIVED_FILES = (
    "randomized_raw.csv",
    "randomized_summary.csv",
    "paired_statistics.csv",
    "randomized_results.json",
    "randomized_macros.tex",
    "randomized_ablation_raw.csv",
    "randomized_ablation_summary.csv",
    "randomized_ablation_results.json",
    "randomized_ablation_macros.tex",
    "closed_loop_raw.csv",
    "closed_loop_summary.csv",
    "closed_loop_results.json",
    "closed_loop_macros.tex",
    "joint_reference_raw.csv",
    "joint_reference_summary.csv",
    "joint_reference_results.json",
    "joint_reference_macros.tex",
    "ablation.csv",
    "ablation.json",
)


def is_runtime_field(key: str) -> bool:
    return bool(RUNTIME_FIELDS.fullmatch(key))


def convert_value(value: str | float | int, ratio: float) -> str | float:
    if value == "" or value is None:
        return value
    return str(float(value) / ratio) if isinstance(value, str) else value / ratio


def convert_row(row: dict, ratio: float, counts: Counter) -> dict:
    converted = dict(row)
    for key, value in row.items():
        if is_runtime_field(key) and value not in ("", None):
            converted[key] = convert_value(value, ratio)
            counts[key] += 1
    # Paired-statistics rows have generic field names qualified by metric.
    if row.get("metric") == "runtime_ms":
        for key in ("mean_difference", "ci_low", "ci_high"):
            if key in row and row[key] not in ("", None):
                converted[key] = convert_value(row[key], ratio)
                counts[f"runtime_ms:{key}"] += 1
    return converted


def convert_json(value: object, ratio: float, counts: Counter) -> object:
    if isinstance(value, list):
        return [convert_json(item, ratio, counts) for item in value]
    if isinstance(value, dict):
        row = {key: convert_json(item, ratio, counts) for key, item in value.items()}
        return convert_row(row, ratio, counts)
    return value


def convert_csv(source: Path, output: Path, ratio: float, counts: Counter) -> None:
    with source.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"missing CSV header: {source}")
        rows = [convert_row(row, ratio, counts) for row in reader]
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def convert_macros(source: Path, output: Path, ratio: float, counts: Counter) -> None:
    lines = []
    for line in source.read_text(encoding="utf-8").splitlines(keepends=True):
        match = RUNTIME_MACRO.fullmatch(line.rstrip("\r\n"))
        if match and "RuntimeEffect}" not in match.group(1):
            old_value = match.group(2)
            precision = len(old_value.partition(".")[2])
            newline = line[len(line.rstrip("\r\n")):]
            line = f"{match.group(1)}{float(old_value) / ratio:.{precision}f}{match.group(3)}{newline}"
            counts["latex_runtime_macros"] += 1
        lines.append(line)
    output.write_text("".join(lines), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def convert_bundle(source_dir: Path, output_dir: Path, ratio: float, calibration: dict | None = None) -> dict:
    if not math.isfinite(ratio) or ratio <= 0:
        raise ValueError("Python/C++ ratio must be finite and positive")
    if source_dir.resolve() == output_dir.resolve():
        raise ValueError("output must differ from the source directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    counts: Counter = Counter()
    source_hashes = {}
    for name in DERIVED_FILES:
        source = source_dir / name
        if not source.is_file():
            raise FileNotFoundError(source)
        target = output_dir / name
        source_hashes[name] = sha256(source)
        if source.suffix == ".csv":
            convert_csv(source, target, ratio, counts)
        elif source.suffix == ".json":
            data = json.loads(source.read_text(encoding="utf-8"))
            target.write_text(
                json.dumps(convert_json(data, ratio, counts), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        else:
            convert_macros(source, target, ratio, counts)
    manifest = {
        "status": "estimated_cpp_equivalent_not_measured_cpp_planning_latency",
        "formula": "estimated_cpp_ms = recorded_python_ms / python_to_cpp_ratio",
        "python_to_cpp_ratio": ratio,
        "calibration": calibration,
        "scaled_field_counts": dict(counts),
        "source_sha256": source_hashes,
        "boundary": "A ratio from a matched component benchmark is an extrapolation, not a complete C++ port, native Apollo latency, or a hard real-time guarantee.",
    }
    (output_dir / "conversion_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ratio", type=float, help="measured Python runtime / C++ runtime")
    group.add_argument("--calibration", type=Path, help="JSON containing python_to_cpp_ratio")
    args = parser.parse_args()
    calibration = None
    ratio = args.ratio
    if args.calibration:
        calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
        ratio = float(calibration["python_to_cpp_ratio"])
    manifest = convert_bundle(args.source, args.output, ratio, calibration)
    print(json.dumps({"ratio": ratio, "scaled_field_counts": manifest["scaled_field_counts"]}, indent=2))


if __name__ == "__main__":
    main()
