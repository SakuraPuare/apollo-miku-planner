"""Regression checks for the held-out CommonRoad road-family audit."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_peachtree_native_report_is_a_separate_family() -> None:
    report = json.loads(
        (ROOT / "小论文-2" / "generated" / "commonroad_miku_native_peachtree_results.json")
        .read_text(encoding="utf-8")
    )
    rows = [row for row in report["rows"] if row.get("method") == "MIKU"]
    assert report["benchmark"] == "CommonRoad NGSIM Peachtree"
    assert report["scenario_count"] == 4
    assert len(rows) == 4
    assert report["miku_native_benchmark"] is True
    assert sum(row.get("valid_solution") is True for row in rows) == 1
    assert all(row.get("station_varying_road_bounds") is True for row in rows)


def test_peachtree_reactive_report_uses_the_same_scope() -> None:
    report = json.loads(
        (ROOT / "小论文-2" / "generated" / "commonroad_reactive_peachtree_results.json")
        .read_text(encoding="utf-8")
    )
    assert report["benchmark"] == "CommonRoad NGSIM Peachtree"
    assert report["scenario_count"] == 4
    assert report["benchmark_complete"] is True
    assert report["valid_solution_count"] == 0
    assert report["protocol_scope"].startswith("one-shot official ReactivePlanner")
    assert all(
        row.get("planner_protocol")
        == "official_reactive_planner_one_shot_same_dt_horizon_and_evaluator"
        for row in report["rows"]
    )


def test_us101_lanelet_goal_report_is_supported() -> None:
    report = json.loads(
        (ROOT / "小论文-2" / "generated" / "commonroad_miku_native_us101_results.json")
        .read_text(encoding="utf-8")
    )
    rows = [row for row in report["rows"] if row.get("method") == "MIKU"]
    assert report["benchmark"] == "CommonRoad NGSIM US101"
    assert report["scenario_count"] == 4
    assert len(rows) == 4
    assert sum(row.get("valid_solution") is True for row in rows) == 2
    assert all(row.get("goal_station_interval_m") for row in rows)
    goal_kinds = {row.get("goal_region_kind") for row in rows}
    assert goal_kinds == {"lanelet", "rectangle"}
    assert any(
        row.get("scenario") == "USA_US101-1_1_T-1"
        and row.get("goal_region_kind") == "lanelet"
        for row in rows
    )
