"""Small-scale spatiotemporal joint-search reference for MIKU experiments.

The reference searches time, longitudinal position, lateral position,
longitudinal speed, and lateral speed together.  It is deliberately restricted
to a coarse public grid and a deterministic beam so it remains tractable on a
paired subset.  It is a quality/cost reference, not a claim of continuous
global optimality.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from apollo_pipeline import Scenario, compute_delta


@dataclass(frozen=True)
class JointGrid:
    dt: float = 0.5
    ds: float = 0.5
    dl: float = 0.25
    dv: float = 1.0
    max_speed: float = 13.0
    max_lateral_speed: float = 0.5
    max_lateral_acceleration: float = 1.0
    beam_width: int = 20_000


State = tuple[int, int, int, int]


def _center_road_limits(scn: Scenario, grid: JointGrid) -> tuple[float, float]:
    road_min = scn.l_road_min
    road_max = scn.l_road_max
    if scn.lane_borrow in ("right", "both"):
        road_min -= scn.lane_width
    if scn.lane_borrow in ("left", "both"):
        road_max += scn.lane_width
    inset = scn.ego.W / 2.0 + scn.delta_min
    return road_min + inset, road_max - inset


def _collision_free(scn: Scenario, t: float, s: float, lateral: float) -> bool:
    for obs in scn.obstacles:
        obs_s, obs_l = obs.position_at(t)
        longitudinal_uncertainty = (
            obs.uncertainty_s0 + obs.uncertainty_vs * t if not obs.is_static else 0.0
        )
        lateral_uncertainty = (
            obs.uncertainty_l0 + obs.uncertainty_vl * t if not obs.is_static else 0.0
        )
        longitudinal_limit = (
            (scn.ego.L + obs.L) / 2.0
            + (0.15 if not obs.is_static else 0.0)
            + longitudinal_uncertainty
        )
        lateral_limit = (
            (scn.ego.W + obs.W) / 2.0
            + compute_delta(obs, scn)
            + lateral_uncertainty
        )
        if (
            abs(s - obs_s) < longitudinal_limit
            and abs(lateral - obs_l) < lateral_limit
        ):
            return False
    return True


def run_joint_reference(scn: Scenario, grid: JointGrid | None = None) -> dict:
    """Run deterministic beam dynamic programming on a joint ST--SL grid."""
    grid = grid or JointGrid()
    ts = np.arange(0.0, scn.t_max + 0.5 * grid.dt, grid.dt)
    road_min, road_max = _center_road_limits(scn, grid)
    lateral_grid = np.arange(road_min, road_max + 0.5 * grid.dl, grid.dl)
    lateral_grid = lateral_grid[lateral_grid <= road_max + 1e-9]
    if lateral_grid.size == 0:
        raise ValueError("road is narrower than the ego center corridor")

    initial_s_index = int(round(scn.ego.s0 / grid.ds))
    initial_l_index = int(np.argmin(np.abs(lateral_grid - scn.ego.l0)))
    initial_v_index = int(np.clip(round(scn.ego.v0 / grid.dv), 0, round(grid.max_speed / grid.dv)))
    initial: State = (initial_s_index, initial_l_index, initial_v_index, 0)
    layers: list[dict[State, tuple[float, State | None]]] = [{initial: (0.0, None)}]
    max_v_index = int(round(grid.max_speed / grid.dv))
    max_lateral_step = int(round(grid.max_lateral_speed * grid.dt / grid.dl))
    lateral_steps = range(-max_lateral_step, max_lateral_step + 1)
    maximum_lateral_step_change = max(
        1, int(round(grid.max_lateral_acceleration * grid.dt**2 / grid.dl))
    )
    target = max(scn.s_max - 1.0, scn.ego.s0)

    for time_index in range(1, len(ts)):
        next_candidates: dict[State, tuple[float, State]] = {}
        t = float(ts[time_index])
        for state, (cost, _parent) in layers[-1].items():
            s_index, l_index, v_index, lateral_step = state
            minimum_v = max(0, v_index - int(round(4.0 * grid.dt / grid.dv)))
            maximum_v = min(
                max_v_index, v_index + int(round(2.0 * grid.dt / grid.dv))
            )
            for next_v_index in range(minimum_v, maximum_v + 1):
                next_speed = next_v_index * grid.dv
                longitudinal_increment = int(round(next_speed * grid.dt / grid.ds))
                next_s_index = min(
                    int(round(target / grid.ds)), s_index + longitudinal_increment
                )
                next_s = next_s_index * grid.ds
                acceleration = (next_v_index - v_index) * grid.dv / grid.dt
                for next_lateral_step in lateral_steps:
                    if abs(next_lateral_step - lateral_step) > maximum_lateral_step_change:
                        continue
                    next_l_index = l_index + next_lateral_step
                    if not 0 <= next_l_index < len(lateral_grid):
                        continue
                    next_l = float(lateral_grid[next_l_index])
                    if not _collision_free(scn, t, next_s, next_l):
                        continue
                    lateral_acceleration = (
                        (next_lateral_step - lateral_step) * grid.dl / grid.dt**2
                    )
                    stage_cost = (
                        0.02 * (next_speed - scn.ego.v0) ** 2
                        + 0.04 * acceleration**2
                        + 0.08 * next_l**2
                        + 0.10 * lateral_acceleration**2
                        - 0.35 * (next_s_index - s_index) * grid.ds
                    )
                    next_state: State = (
                        next_s_index,
                        next_l_index,
                        next_v_index,
                        next_lateral_step,
                    )
                    next_cost = cost + stage_cost
                    previous = next_candidates.get(next_state)
                    if previous is None or next_cost < previous[0]:
                        next_candidates[next_state] = (next_cost, state)

        if not next_candidates:
            break
        if len(next_candidates) > grid.beam_width:
            ranked = sorted(
                next_candidates.items(),
                key=lambda item: (
                    item[1][0] - 2.0 * item[0][0] * grid.ds,
                    -item[0][0],
                    abs(float(lateral_grid[item[0][1]])),
                    item[0],
                ),
            )[: grid.beam_width]
            next_candidates = dict(ranked)
        layers.append(next_candidates)

    final_state = min(
        layers[-1],
        key=lambda state: (
            -state[0],
            layers[-1][state][0],
            abs(float(lateral_grid[state[1]])),
            state,
        ),
    )
    states = [final_state]
    for layer_index in range(len(layers) - 1, 0, -1):
        parent = layers[layer_index][states[-1]][1]
        if parent is None:
            break
        states.append(parent)
    states.reverse()

    used_ts = ts[: len(states)]
    longitudinal = np.asarray([state[0] * grid.ds for state in states], dtype=float)
    lateral = np.asarray([lateral_grid[state[1]] for state in states], dtype=float)
    speed = np.asarray([state[2] * grid.dv for state in states], dtype=float)
    speed[0] = scn.ego.v0
    acceleration = np.zeros_like(speed)
    if len(speed) > 1:
        acceleration[1:] = np.diff(speed) / grid.dt
        acceleration[0] = scn.ego.a0
    lateral_acceleration = np.zeros_like(lateral)
    if len(lateral) > 2:
        lateral_acceleration[1:-1] = np.diff(lateral, n=2) / grid.dt**2

    return {
        "ts": used_ts,
        "s_qp": longitudinal,
        "l_qp": lateral,
        "v_qp": speed,
        "a_qp": acceleration,
        "a_y": lateral_acceleration,
        "s_arr": longitudinal,
        "l_path": lateral,
        "time_window_decisions": [],
        "joint_grid": grid,
        "joint_states_retained": sum(len(layer) for layer in layers),
        "joint_reached": bool(longitudinal[-1] >= target - 1e-9),
    }
