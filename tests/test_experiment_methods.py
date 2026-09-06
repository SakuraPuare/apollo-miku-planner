from __future__ import annotations

import pytest
import numpy as np

from apollo_pipeline import (
    COMPARABLE_SCENARIOS,
    Ego,
    Scenario,
    path_bounds_decider,
    path_optimizer,
    path_qp_objective,
    pipeline_objective,
    run_pipeline,
    speed_qp_objective,
)
from experiment_cases import generate_case
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
    scenario = generate_case("crossing_pedestrian", 0).planning_scenario
    run = run_method(method_by_key("MIKU"), scenario)
    assert run.result["blocked_idx"] == -1
    assert run.result["st_bounds"][0]["intervals"]


def test_default_miku_uses_temporal_homotopy_corridor_semantics():
    scenario = COMPARABLE_SCENARIOS["06_ped_plus_parked_cmp"]

    result = run_pipeline("miku", scenario)

    assert result["corridor"] is None
    assert result["time_window_decisions"]
    assert result["time_window_decisions"][0]["status"] == "selected"
    assert result["s_qp"][-1] >= scenario.s_max - 1.0 - 1.0e-6


def test_external_goal_station_is_an_exact_path_qp_knot():
    scenario = Scenario(
        Ego(v0=2.0),
        [],
        s_max=2.3,
        goal_lateral=0.4,
    )
    s_arr, *_ = path_bounds_decider(scenario, "miku")
    assert s_arr[-1] == pytest.approx(scenario.s_max)
    assert np.max(np.diff(s_arr)) <= 0.5 + 1.0e-12


def test_external_goal_rectangle_compiles_terminal_lateral_interval():
    scenario = Scenario(
        Ego(v0=2.0),
        [],
        s_max=2.3,
        goal_s_min=1.8,
        goal_s_max=2.3,
        goal_l_min=-0.4,
        goal_l_max=0.6,
    )
    s_arr, l_min, l_max, blocked, _ = path_bounds_decider(scenario, "miku")
    assert blocked == -1
    assert s_arr[-1] == pytest.approx(2.3)
    assert l_min[-1] == pytest.approx(-0.4)
    assert l_max[-1] == pytest.approx(0.6)


def test_external_goal_time_window_selects_an_admissible_early_knot():
    scenario = Scenario(
        Ego(v0=1.0),
        [],
        s_max=2.0,
        goal_s_min=0.5,
        goal_s_max=1.5,
        goal_l_min=-0.5,
        goal_l_max=0.5,
        goal_time_start=0.2,
        goal_time_end=0.8,
    )
    result = run_pipeline("miku", scenario)
    assert result["s_qp"] is not None
    assert result["selected_goal_time"] is not None
    assert 0.2 - 1.0e-9 <= result["selected_goal_time"] <= 0.8 + 1.0e-9


def test_external_goal_heading_shapes_terminal_path_slope():
    stations = np.linspace(0.0, 5.0, 11)
    path, _ = path_optimizer(
        stations,
        np.full(11, -3.0),
        np.full(11, 3.0),
        terminal_slope=0.5,
    )
    terminal_slope = (path[-1] - path[-2]) / (stations[-1] - stations[-2])
    assert terminal_slope > 0.4


def test_miku_reports_finite_joint_search_certificate():
    scenario = COMPARABLE_SCENARIOS["06_ped_plus_parked_cmp"]
    run = run_method(method_by_key("MIKU"), scenario)
    certificate = run.result["joint_search_certificate"]
    assert certificate["status"] in {"optimal", "infeasible"}
    assert certificate["evaluated_candidates"] >= 1
    assert certificate["domain_size"] >= certificate["evaluated_candidates"]
    if certificate["status"] == "optimal":
        assert certificate["absolute_gap"] == 0.0
    else:
        assert certificate["absolute_gap"] == float("inf")


def test_certificate_objective_is_the_path_plus_speed_qp_objective():
    scenario = COMPARABLE_SCENARIOS["06_ped_plus_parked_cmp"]
    result = run_pipeline("miku", scenario)
    assert result["s_qp"] is not None
    assert pipeline_objective(scenario, result) == pytest.approx(
        path_qp_objective(result) + speed_qp_objective(scenario, result)
    )
