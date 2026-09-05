"""Regression checks for the native CommonRoad output boundary artifact."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_native_boundary_report_preserves_failures_and_scope() -> None:
    report = json.loads(
        (ROOT / "小论文-2" / "generated" / "commonroad_miku_native_results.json")
        .read_text(encoding="utf-8")
    )
    miku_rows = [row for row in report["rows"] if row.get("method") == "MIKU"]
    assert len(miku_rows) == report["scenario_count"] == 4
    assert all(row.get("native_commonroad_protocol") is True for row in miku_rows)
    assert all(
        row.get("planner_input_semantics")
        == "official_lanelet_route_and_sampled_shape_pose_occupancy_envelope"
        for row in miku_rows
    )
    assert report["miku_native_benchmark"] is True
    assert "occupancy_envelope" in report["benchmark_scope"]
    assert report["miku_valid_solution_count"] == 0
    assert report["miku_planner_failure_count"] == 4
    assert [row["skipped_obstacles"] for row in miku_rows] == [0, 0, 0, 0]
    assert [row["projected_obstacles"] for row in miku_rows] == [24, 42, 36, 34]
    assert all(row.get("occupancy_obstacles") == row.get("projected_obstacles") for row in miku_rows)
    assert all(row.get("occupancy_samples", 0) > 0 for row in miku_rows)
