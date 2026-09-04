from __future__ import annotations

import csv
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "小论文-2" / "generated"


def _read_rows(name: str) -> list[dict[str, str]]:
    with (ARTIFACTS / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _macro(name: str, path: str) -> float:
    text = (ARTIFACTS / path).read_text(encoding="utf-8")
    match = re.search(
        rf"\\newcommand\{{\\{re.escape(name)}\}}\{{([^}}]+)\}}", text
    )
    if match is None:
        raise AssertionError(f"missing LaTeX macro {name}")
    return float(match.group(1))


def test_randomized_summary_matches_latex_macros() -> None:
    rows = {
        (row["case_kind"], row["method"]): row
        for row in _read_rows("randomized_summary.csv")
    }
    for method, macro_name in (("B0", "BZero"), ("MIKU", "Miku")):
        row = rows[("all", method)]
        assert _macro(f"RandAll{macro_name}SuccessPct", "randomized_macros.tex") == pytest.approx(
            100.0 * float(row["success_rate"]), abs=0.05
        )
        assert _macro(f"RandAll{macro_name}CollisionPct", "randomized_macros.tex") == pytest.approx(
            100.0 * float(row["collision_rate"]), abs=0.05
        )


def test_closed_loop_summary_matches_latex_macros() -> None:
    rows = {row["method"]: row for row in _read_rows("closed_loop_summary.csv")}
    for method, macro_name in (("B0", "BZero"), ("MIKU", "Miku")):
        row = rows[method]
        assert _macro(f"Closed{macro_name}SuccessPct", "closed_loop_macros.tex") == pytest.approx(
            100.0 * float(row["success_rate"]), abs=0.05
        )
        assert _macro(f"Closed{macro_name}CollisionPct", "closed_loop_macros.tex") == pytest.approx(
            100.0 * float(row["collision_rate"]), abs=0.05
        )


def test_joint_stress_macros_match_largest_summary_row() -> None:
    rows = _read_rows("joint_search_stress_summary.csv")
    largest = max(rows, key=lambda row: int(row["spatial_layers"]))
    assert _macro("StressMaxLayers", "joint_search_stress_macros.tex") == float(
        largest["spatial_layers"]
    )
    assert _macro("StressDomainSize", "joint_search_stress_macros.tex") == float(
        largest["domain_size"]
    )
    assert _macro("StressEvaluatedCount", "joint_search_stress_macros.tex") == float(
        largest["evaluated_candidates"]
    )
