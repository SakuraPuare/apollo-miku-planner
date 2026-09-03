from __future__ import annotations

import numpy as np

from closed_loop import run_closed_loop
from experiment_cases import generate_case
from experiment_methods import method_by_key
from experiment_metrics import evaluate_run, trajectory_from_run


def test_rolling_horizon_executes_multiple_planning_cycles():
    case = generate_case("crossing_pedestrian", 0)
    run = run_closed_loop(method_by_key("MIKU"), case)
    trajectory = trajectory_from_run(run, case.planning_scenario)

    assert run.iterations >= 2
    assert run.result["closed_loop_cycles"] == run.iterations
    assert np.all(np.diff(trajectory.time_s) > 0.0)
    assert np.all(np.diff(trajectory.longitudinal_m) >= -1e-6)
    assert trajectory.time_s[-1] <= case.truth_scenario.t_max + 1e-9
    assert evaluate_run(run, case)["runtime_ms"] == run.runtime_ms


def test_closed_loop_preserves_prediction_noise_as_observation_bias():
    case = generate_case("prediction_noise", 0)
    run = run_closed_loop(method_by_key("B0"), case)

    assert run.result["closed_loop_cycles"] >= 1
    assert run.result["s_qp"][0] == case.truth_scenario.ego.s0
    assert run.result["l_qp"][0] == case.truth_scenario.ego.l0
