"""Regression checks for the sixteen-scenario CommonRoad extension audit."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_extended_native_report_is_separate_and_fail_closed() -> None:
    report = json.loads(
        (ROOT / "小论文-2" / "generated" / "commonroad_miku_native_extended_results.json")
        .read_text(encoding="utf-8")
    )
    rows = [row for row in report["rows"] if row.get("method") == "MIKU"]
    assert report["scenario_count"] == 16
    assert len(rows) == 16
    assert report["miku_valid_solution_count"] == 7
    assert report["miku_planner_failure_count"] == 3
    assert report["miku_non_valid_count"] == 9
    assert all(row.get("native_commonroad_protocol") is True for row in rows)
    assert any(row["scenario"] == "USA_Lanker-1_5_T-1" for row in rows)
    assert any(row["scenario"] == "USA_Lanker-2_1_T-1" for row in rows)
    assert next(
        row for row in rows if row["scenario"] == "USA_Lanker-1_10_T-1"
    )["failure_category"] == "valid"
    assert all(row.get("outcome") in {"valid_solution", "invalid_solution", "planner_failure"} for row in rows)
    assert sum(row.get("failure_category") == "goal_not_reached" for row in rows) == 6
    assert sum(row.get("failure_category") == "boundary_collision" for row in rows) == 0
    assert sum(row.get("failure_category") == "valid" for row in rows) == 7
    assert sum(row.get("failure_category") == "planner_failure" for row in rows) == 3
    assert sum(
        row.get("failure_diagnostics", {}).get("failure_stage") == "goal_bounds"
        for row in rows
    ) == 3


def test_extended_reactive_report_uses_same_six_scenario_scope() -> None:
    report = json.loads(
        (ROOT / "小论文-2" / "generated" / "commonroad_reactive_extended_results.json")
        .read_text(encoding="utf-8")
    )
    assert report["scenario_count"] == 16
    assert report["planned_count"] == 4
    assert report["valid_solution_count"] == 0
    assert report["benchmark_complete"] is True
