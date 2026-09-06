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
        == "official_lanelet_reference_path_and_station_varying_polygon_cross_section; relevant_sampled_shape_pose_occupancy_envelope; all_source_obstacles_audited"
        for row in miku_rows
    )
    assert report["miku_native_benchmark"] is True
    assert "occupancy_envelope" in report["benchmark_scope"]
    assert report["miku_valid_solution_count"] == 2
    assert report["miku_planner_failure_count"] == 1
    assert report["miku_non_valid_count"] == 2
    assert sum(row.get("outcome") == "valid_solution" for row in miku_rows) == 2
    assert sum(row.get("outcome") != "valid_solution" for row in miku_rows) == 2
    assert sum(row.get("outcome") == "planner_failure" for row in miku_rows) == 1
    assert [row["skipped_obstacles"] for row in miku_rows] == [0, 0, 0, 0]
    assert [row["projected_obstacles"] for row in miku_rows] == [24, 42, 36, 34]
    assert all(row.get("occupancy_obstacles") == row.get("projected_obstacles") for row in miku_rows)
    assert all(row.get("occupancy_samples", 0) > 0 for row in miku_rows)
    assert all("goal_heading_error_rad" in row for row in miku_rows)
    assert all("planner_terminal_slope_target" in row for row in miku_rows)
    assert all("selected_goal_time_s" in row for row in miku_rows)
    assert all("selected_goal_knot" in row for row in miku_rows)
    assert all(row.get("station_varying_road_bounds") is True for row in miku_rows)
    assert all(row.get("road_center_width_min_m", 0.0) > 0.0 for row in miku_rows)
    assert all(
        row.get("planner_relevant_obstacles", 0)
        + row.get("route_irrelevant_obstacles", 0)
        == row.get("projected_obstacles", 0)
        for row in miku_rows
    )
    assert all(
        row.get("failure_diagnostics", {}).get("failure_stage")
        in {"solved", "path_bounds", "speed_bounds", "speed_qp", "goal_bounds"}
        for row in miku_rows
    )
