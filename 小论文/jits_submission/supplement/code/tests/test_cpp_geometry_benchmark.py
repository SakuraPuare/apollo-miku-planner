"""Regression checks for the paired Python/C++ MIKU benchmark inputs."""

import csv
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.benchmark_miku_geometry import (  # noqa: E402
    FIELDS,
    _capture_calls,
    _read_input,
    _time_calls,
    _validate,
)
from tools.export_miku_cases import export  # noqa: E402


def test_case_export_preserves_the_seven_matched_planning_scenarios(tmp_path):
    output = tmp_path / "cases.csv"
    export(0, 1, output, 8)

    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 7
    assert [row["seed"] for row in rows] == ["0"] * 7
    assert rows[3]["case_kind"] == "narrow_multi_obstacle"
    assert rows[3]["obstacle_count"] == "6"
    assert rows[5]["case_kind"] == "prediction_noise"
    assert float(rows[5]["obs0_uncertainty_s0"]) == 0.35


def test_geometry_pairs_use_actual_path_bound_groups(tmp_path):
    rows = _capture_calls(0, 1)
    assert rows
    assert all(int(row["expected_band_count"]) > 0 for row in rows)

    path = tmp_path / "geometry.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    parsed, calls = _read_input(path)
    _validate(parsed, calls)

    output = _time_calls(parsed, calls, repeats=3, output=path)
    assert output["case_group_count"] == len(rows)
    assert output["call_pair_count"] == 3 * len(rows)
    assert output["microseconds_per_call_pair"] > 0
    with (tmp_path / "geometry.python_raw.csv").open(encoding="utf-8") as stream:
        timed_rows = list(csv.DictReader(stream))
    assert len(timed_rows) == len(rows)
    assert all(row["repeats"] == "3" for row in timed_rows)
