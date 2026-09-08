from __future__ import annotations

import numpy as np

from experiment_cases import generate_case
from experiment_methods import method_by_key, run_method
from experiment_metrics import trajectory_from_run
from joint_reference import JointGrid


def test_joint_reference_is_registered_separately_from_main_methods():
    method = method_by_key("B3")
    assert method.label == "B3-JointReference"
    assert method.solver == "joint_grid"


def test_joint_reference_respects_grid_dynamics_and_physical_clearance():
    case = generate_case("vehicle_cut_in", 0)
    run = run_method(method_by_key("B3"), case.planning_scenario)
    trajectory = trajectory_from_run(run, case.planning_scenario)
    grid = JointGrid()

    assert len(trajectory.time_s) == len(trajectory.longitudinal_m)
    assert np.all(np.diff(trajectory.longitudinal_m) >= -1e-9)
    assert np.max(np.abs(np.diff(trajectory.speed_mps) / grid.dt)) <= 4.0 + 1e-9
    assert np.max(np.abs(np.diff(trajectory.lateral_m) / grid.dt)) <= grid.max_lateral_speed + 1e-9
    assert run.result["joint_states_retained"] > len(trajectory.time_s)
