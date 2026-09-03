"""Rolling-horizon execution for the randomized MIKU scenario families."""

from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

from apollo_pipeline import Ego, Obstacle, Scenario
from experiment_cases import RandomCase
from experiment_methods import MethodRun, MethodSpec, run_method
from experiment_metrics import trajectory_from_run


@dataclass(frozen=True)
class ClosedLoopConfig:
    replan_period_s: float = 0.5
    minimum_cycle_horizon_s: float = 2.0
    target_tolerance_m: float = 1.0


def _observation_biases(case: RandomCase) -> tuple[Ego, list[Obstacle]]:
    truth = case.truth_scenario
    planning = case.planning_scenario
    ego_bias = Ego(
        s0=planning.ego.s0 - truth.ego.s0,
        l0=planning.ego.l0 - truth.ego.l0,
        v0=planning.ego.v0 - truth.ego.v0,
        a0=planning.ego.a0 - truth.ego.a0,
        W=0.0,
        L=0.0,
    )
    obstacle_biases = []
    for planned, actual in zip(planning.obstacles, truth.obstacles, strict=True):
        obstacle_biases.append(
            Obstacle(
                s0=planned.s0 - actual.s0,
                l0=planned.l0 - actual.l0,
                vs=planned.vs - actual.vs,
                vl=planned.vl - actual.vl,
                W=0.0,
                L=0.0,
            )
        )
    return ego_bias, obstacle_biases


def _cycle_scenario(
    case: RandomCase,
    absolute_time: float,
    state: tuple[float, float, float, float],
    config: ClosedLoopConfig,
) -> Scenario:
    truth = case.truth_scenario
    ego_bias, obstacle_biases = _observation_biases(case)
    current_s, current_l, current_v, current_a = state
    ego = copy.deepcopy(truth.ego)
    ego.s0 = current_s + ego_bias.s0
    ego.l0 = current_l + ego_bias.l0
    ego.v0 = max(0.0, current_v + ego_bias.v0)
    ego.a0 = current_a + ego_bias.a0

    obstacles = []
    for actual, bias in zip(truth.obstacles, obstacle_biases, strict=True):
        actual_s, actual_l = actual.position_at(absolute_time)
        observed = copy.deepcopy(actual)
        observed.s0 = actual_s + bias.s0
        observed.l0 = actual_l + bias.l0
        observed.vs = actual.vs + bias.vs
        observed.vl = actual.vl + bias.vl
        obstacles.append(observed)

    remaining = max(truth.t_max - absolute_time, 0.0)
    cycle_horizon = max(config.minimum_cycle_horizon_s, remaining)
    return Scenario(
        ego=ego,
        obstacles=obstacles,
        # Keep the QP's terminal stopping point one metre beyond the evaluation
        # line. Otherwise repeated replanning asymptotically brakes just before
        # the line because run_pipeline uses s_max - 1 as its terminal target.
        s_max=truth.s_max + 1.0,
        t_max=cycle_horizon,
        l_road_min=truth.l_road_min,
        l_road_max=truth.l_road_max,
        delta_baseline=truth.delta_baseline,
        delta_min=truth.delta_min,
        delta_max=truth.delta_max,
        lane_borrow=truth.lane_borrow,
        lane_width=truth.lane_width,
    )


def run_closed_loop(
    method: MethodSpec,
    case: RandomCase,
    config: ClosedLoopConfig | None = None,
) -> MethodRun:
    """Execute the first replan-period segment and repeat until horizon/goal."""
    config = config or ClosedLoopConfig()
    truth = case.truth_scenario
    state = (truth.ego.s0, truth.ego.l0, truth.ego.v0, truth.ego.a0)
    times = [0.0]
    longitudinal = [state[0]]
    lateral = [state[1]]
    speed = [state[2]]
    acceleration = [state[3]]
    lateral_acceleration = [0.0]
    total_runtime_ms = 0.0
    planning_cycles = 0
    all_converged = True
    target = truth.s_max - config.target_tolerance_m

    while times[-1] < truth.t_max - 1e-9 and longitudinal[-1] < target - 1e-9:
        cycle = _cycle_scenario(case, times[-1], state, config)
        planned = run_method(method, cycle)
        planned_trajectory = trajectory_from_run(planned, cycle)
        total_runtime_ms += planned.runtime_ms
        planning_cycles += 1
        all_converged = all_converged and planned.converged

        relative_indices = np.flatnonzero(
            (planned_trajectory.time_s > 1e-9)
            & (planned_trajectory.time_s <= config.replan_period_s + 1e-9)
        )
        if relative_indices.size == 0:
            break
        start_s = float(planned_trajectory.longitudinal_m[0])
        start_l = float(planned_trajectory.lateral_m[0])
        start_v = float(planned_trajectory.speed_mps[0])
        cycle_start_time = times[-1]
        for index in relative_indices:
            absolute_t = cycle_start_time + float(planned_trajectory.time_s[index])
            if absolute_t > truth.t_max + 1e-9:
                break
            executed_s = state[0] + (
                float(planned_trajectory.longitudinal_m[index]) - start_s
            )
            executed_l = state[1] + float(planned_trajectory.lateral_m[index]) - start_l
            executed_v = max(
                0.0,
                state[2] + float(planned_trajectory.speed_mps[index]) - start_v,
            )
            times.append(absolute_t)
            longitudinal.append(executed_s)
            lateral.append(executed_l)
            speed.append(executed_v)
            acceleration.append(float(planned_trajectory.acceleration_mps2[index]))
            cycle_a_y = planned.result.get("a_y")
            lateral_acceleration.append(
                0.0 if cycle_a_y is None else float(cycle_a_y[index])
            )
            if executed_s >= target - 1e-9:
                break

        state = (
            longitudinal[-1],
            lateral[-1],
            speed[-1],
            acceleration[-1],
        )
        if times[-1] <= cycle_start_time + 1e-9:
            break

    result = {
        "ts": np.asarray(times, dtype=float),
        "s_qp": np.asarray(longitudinal, dtype=float),
        "l_qp": np.asarray(lateral, dtype=float),
        "v_qp": np.asarray(speed, dtype=float),
        "a_qp": np.asarray(acceleration, dtype=float),
        "a_y": np.asarray(lateral_acceleration, dtype=float),
        "s_arr": np.asarray(longitudinal, dtype=float),
        "l_path": np.asarray(lateral, dtype=float),
        "closed_loop_cycles": planning_cycles,
    }
    return MethodRun(
        method=method,
        result=result,
        runtime_ms=total_runtime_ms,
        iterations=planning_cycles,
        converged=all_converged,
    )
