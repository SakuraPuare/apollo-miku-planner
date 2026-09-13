"""Regression checks for projected compute times, separate from physics time."""

import csv
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools import convert_cpp_runtime_estimates as estimates


def test_scaling_only_compute_time_fields():
    counts = estimates.Counter()
    row = {
        "runtime_ms": "221.8",
        "episode_runtime_p95_ms": "1361.51",
        "qp_speed_ms": "5.0",
        "arrival_time_s": "9.0",
        "penalized_travel_time_s": "14.0",
        "success_rate": "0.7746",
    }
    converted = estimates.convert_row(row, 2.0, counts)
    assert float(converted["runtime_ms"]) == pytest.approx(110.9)
    assert float(converted["episode_runtime_p95_ms"]) == pytest.approx(680.755)
    assert float(converted["qp_speed_ms"]) == pytest.approx(2.5)
    assert converted["arrival_time_s"] == "9.0"
    assert converted["penalized_travel_time_s"] == "14.0"
    assert converted["success_rate"] == "0.7746"
    assert row["runtime_ms"] == "221.8"


def test_paired_runtime_confidence_interval_but_not_effect_size():
    counts = estimates.Counter()
    converted = estimates.convert_row(
        {
            "metric": "runtime_ms",
            "mean_difference": 2.0,
            "ci_low": -1.0,
            "ci_high": 4.0,
            "effect_size_dz": 0.25,
        },
        4.0,
        counts,
    )
    assert converted["mean_difference"] == 0.5
    assert converted["ci_low"] == -0.25
    assert converted["ci_high"] == 1.0
    assert converted["effect_size_dz"] == 0.25


def test_bundle_retains_originals_and_records_projection(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    raw = source / "randomized_summary.csv"
    raw.write_text(
        "method,runtime_p99_ms,arrival_time_s,collision_rate\n"
        "MIKU,221.80,9,0.0114\n",
        encoding="utf-8",
    )
    (source / "randomized_results.json").write_text(
        json.dumps({"aggregates": [{"runtime_p99_ms": 221.8, "arrival_time_s": 9}]}),
        encoding="utf-8",
    )
    (source / "randomized_macros.tex").write_text(
        "\\newcommand{\\RandAllMikuRuntimePninetynine}{221.80}\n"
        "\\newcommand{\\RandAllMikuVsBZeroRuntimeEffect}{0.073}\n"
        "\\newcommand{\\RandAllMikuArrival}{9.00}\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"
    with patch.object(
        estimates,
        "DERIVED_FILES",
        ("randomized_summary.csv", "randomized_results.json", "randomized_macros.tex"),
    ):
        manifest = estimates.convert_bundle(source, output, 2.0)
    with (output / "randomized_summary.csv").open(encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert float(row["runtime_p99_ms"]) == pytest.approx(110.9)
    assert row["arrival_time_s"] == "9"
    assert row["collision_rate"] == "0.0114"
    converted = json.loads((output / "randomized_results.json").read_text(encoding="utf-8"))
    assert converted["aggregates"][0]["runtime_p99_ms"] == pytest.approx(110.9)
    assert converted["aggregates"][0]["arrival_time_s"] == 9
    assert "{110.90}" in (output / "randomized_macros.tex").read_text(encoding="utf-8")
    assert "RuntimeEffect}{0.073}" in (output / "randomized_macros.tex").read_text(encoding="utf-8")
    assert "{9.00}" in (output / "randomized_macros.tex").read_text(encoding="utf-8")
    assert "221.80" in raw.read_text(encoding="utf-8")
    assert manifest["status"].startswith("estimated_cpp_equivalent")


def test_ratio_must_be_positive_and_outputs_separate(tmp_path):
    with pytest.raises(ValueError, match="positive"):
        estimates.convert_bundle(tmp_path, tmp_path / "out", 0)
    with pytest.raises(ValueError, match="differ"):
        estimates.convert_bundle(tmp_path, tmp_path, 2)


def test_frozen_bundle_conversion_preserves_every_non_runtime_csv_field():
    root = Path(__file__).resolve().parents[1]
    source = root / "小论文/jits_submission/supplement/data/小论文-2/generated"
    output = root / "submission_artifacts/cpp_runtime_estimates"
    manifest = json.loads((output / "conversion_manifest.json").read_text(encoding="utf-8"))
    ratio = manifest["python_to_cpp_ratio"]

    for name in estimates.DERIVED_FILES:
        original = source / name
        assert original.is_file() and (output / name).is_file()
        assert hashlib.sha256(original.read_bytes()).hexdigest() == manifest["source_sha256"][name]
        if not name.endswith(".csv"):
            continue
        with original.open(newline="", encoding="utf-8") as old_stream, (
            output / name
        ).open(newline="", encoding="utf-8") as new_stream:
            original_rows = list(csv.DictReader(old_stream))
            projected_rows = list(csv.DictReader(new_stream))
        assert len(original_rows) == len(projected_rows)
        for old, projected in zip(original_rows, projected_rows):
            assert old.keys() == projected.keys()
            for key, value in old.items():
                is_paired_difference = old.get("metric") == "runtime_ms" and key in (
                    "mean_difference", "ci_low", "ci_high"
                )
                if value not in ("", None) and (estimates.is_runtime_field(key) or is_paired_difference):
                    assert float(projected[key]) == pytest.approx(float(value) / ratio, rel=1e-12)
                else:
                    assert projected[key] == value
