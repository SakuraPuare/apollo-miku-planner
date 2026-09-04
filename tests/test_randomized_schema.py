from __future__ import annotations

from experiment_cases import generate_case
from experiment_methods import method_by_key, run_method
from experiment_metrics import RAW_SCHEMA_VERSION, evaluate_run
from run_randomized_experiments import RAW_FIELDS


def test_randomized_row_schema_and_ranges():
    case = generate_case("crossing_pedestrian", 0)
    row = evaluate_run(run_method(method_by_key("B0"), case.planning_scenario), case)
    assert tuple(row) == RAW_FIELDS
    assert row["schema_version"] == RAW_SCHEMA_VERSION
    assert row["success"] in (0, 1)
    assert row["collision"] in (0, 1)
    assert 0.0 <= row["progress_ratio"] <= 1.0
    assert row["runtime_ms"] > 0.0
    assert row["joint_search_status"] is None
    assert row["joint_domain_size"] is None


def test_miku_randomized_row_persists_joint_search_certificate():
    case = generate_case("crossing_pedestrian", 0)
    row = evaluate_run(run_method(method_by_key("MIKU"), case.planning_scenario), case)

    assert tuple(row) == RAW_FIELDS
    assert row["joint_search_status"] in {"optimal", "infeasible"}
    assert row["joint_domain_size"] >= row["joint_evaluated_candidates"] >= 1
    assert row["joint_expanded_spatial_branches"] >= 1
    assert row["joint_absolute_gap"] == 0.0
