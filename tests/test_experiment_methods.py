from __future__ import annotations

from apollo_pipeline import COMPARABLE_SCENARIOS, PRESSURE_SCENARIOS
from experiment_methods import METHODS, method_by_key, run_method


def test_registry_contains_three_baselines_and_miku():
    assert [method.key for method in METHODS] == ["B0", "B1", "B2", "MIKU"]
    assert sum(method.key.startswith("B") for method in METHODS) == 3


def test_iterative_baseline_runs_multiple_updates():
    scenario = COMPARABLE_SCENARIOS["05_crossing_ped_cmp"]
    run = run_method(method_by_key("B2"), scenario)
    assert 2 <= run.iterations <= 3
    assert run.runtime_ms > 0.0
    assert run.result["s_qp"] is not None


def test_unknown_method_is_rejected():
    try:
        method_by_key("missing")
    except KeyError as exc:
        assert exc.args == ("missing",)
    else:
        raise AssertionError("missing method key should raise KeyError")


def test_pure_dynamic_full_width_conflict_is_deferred_to_speed_stage():
    scenario = PRESSURE_SCENARIOS["01_crossing_ped"]
    run = run_method(method_by_key("MIKU"), scenario)
    assert run.result["blocked_idx"] == -1
    assert run.result["st_bounds"][0]["intervals"]
