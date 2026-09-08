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
