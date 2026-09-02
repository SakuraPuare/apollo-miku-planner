"""Deterministic generators for the six randomized experiment families."""

from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

from apollo_pipeline import Ego, Obstacle, Scenario


CASE_KINDS = (
    "crossing_pedestrian",
    "vehicle_cut_in",
    "parked_and_oncoming",
    "narrow_multi_obstacle",
    "interleaved_dynamic",
    "prediction_noise",
)


@dataclass(frozen=True)
class RandomCase:
    kind: str
    seed: int
    planning_scenario: Scenario
    truth_scenario: Scenario


def _rng(kind: str, seed: int) -> np.random.Generator:
    try:
        kind_index = CASE_KINDS.index(kind)
    except ValueError as exc:
        raise KeyError(kind) from exc
    return np.random.default_rng(np.random.SeedSequence([20260903, kind_index, seed]))


def _crossing_pedestrian(rng: np.random.Generator) -> Scenario:
    ego = Ego(v0=float(rng.uniform(6.0, 9.0)))
    side = float(rng.choice((-1.0, 1.0)))
    ped = Obstacle(
        s0=float(rng.uniform(13.0, 20.0)),
        l0=side * float(rng.uniform(1.0, 1.7)),
        vl=-side * float(rng.uniform(0.65, 1.35)),
        W=float(rng.uniform(0.45, 0.65)),
        L=float(rng.uniform(0.45, 0.65)),
        name="pedestrian",
        obs_type="ped",
    )
    return Scenario(ego, [ped], s_max=32.0, t_max=9.0)


def _vehicle_cut_in(rng: np.random.Generator) -> Scenario:
    ego = Ego(v0=float(rng.uniform(7.0, 10.0)))
    side = float(rng.choice((-1.0, 1.0)))
    vehicle = Obstacle(
        s0=float(rng.uniform(14.0, 23.0)),
        l0=side * float(rng.uniform(1.5, 2.1)),
        vs=float(rng.uniform(2.0, 5.0)),
        vl=-side * float(rng.uniform(0.25, 0.55)),
        W=float(rng.uniform(1.7, 2.0)),
        L=float(rng.uniform(4.0, 4.8)),
        name="cut-in vehicle",
        obs_type="vehicle",
    )
    return Scenario(ego, [vehicle], s_max=42.0, t_max=10.0)


def _parked_and_oncoming(rng: np.random.Generator) -> Scenario:
    ego = Ego(v0=float(rng.uniform(5.0, 7.0)))
    parked = Obstacle(
        s0=float(rng.uniform(19.0, 25.0)),
        l0=float(rng.uniform(-1.35, -1.05)),
        W=float(rng.uniform(1.7, 1.9)),
        L=float(rng.uniform(4.2, 4.9)),
        is_static=True,
        name="parked vehicle",
        obs_type="static",
    )
    oncoming = Obstacle(
        s0=float(rng.uniform(34.0, 43.0)),
        l0=float(rng.uniform(2.7, 3.5)),
        vs=-float(rng.uniform(3.0, 5.0)),
        W=float(rng.uniform(1.7, 2.0)),
        L=float(rng.uniform(4.2, 4.8)),
        name="oncoming vehicle",
        obs_type="vehicle",
    )
    return Scenario(
        ego,
        [parked, oncoming],
        s_max=48.0,
        t_max=10.0,
        lane_borrow="left",
    )


def _narrow_multi_obstacle(rng: np.random.Generator) -> Scenario:
    ego = Ego(v0=float(rng.uniform(4.0, 6.0)))
    obstacles = []
    lateral_jitter = rng.normal(0.0, 0.06, size=6)
    for index, s0 in enumerate((14.0, 22.0, 30.0)):
        obstacles.append(
            Obstacle(
                s0=s0 + float(rng.uniform(-1.0, 1.0)),
                l0=1.54 + float(lateral_jitter[2 * index]),
                W=float(rng.uniform(0.30, 0.45)),
                L=float(rng.uniform(0.6, 1.0)),
                is_static=True,
                name=f"barrier-{index}",
                obs_type="static",
            )
        )
        obstacles.append(
            Obstacle(
                s0=s0 + float(rng.uniform(-1.0, 1.0)),
                l0=-1.38 + float(lateral_jitter[2 * index + 1]),
                W=float(rng.uniform(0.12, 0.22)),
                L=float(rng.uniform(0.4, 0.7)),
                is_static=True,
                name=f"cone-{index}",
                obs_type="cone",
            )
        )
    return Scenario(ego, obstacles, s_max=40.0, t_max=12.0)


def _interleaved_dynamic(rng: np.random.Generator) -> Scenario:
    ego = Ego(v0=float(rng.uniform(6.0, 8.0)))
    first_side = float(rng.choice((-1.0, 1.0)))
    obstacles = [
        Obstacle(
            s0=float(rng.uniform(13.0, 17.0)),
            l0=first_side * float(rng.uniform(1.0, 1.5)),
            vl=-first_side * float(rng.uniform(0.6, 1.0)),
            W=0.55,
            L=0.55,
            name="crossing-a",
            obs_type="ped",
        ),
        Obstacle(
            s0=float(rng.uniform(20.0, 25.0)),
            l0=-first_side * float(rng.uniform(1.0, 1.5)),
            vl=first_side * float(rng.uniform(0.55, 0.95)),
            W=0.55,
            L=0.55,
            name="crossing-b",
            obs_type="ped",
        ),
        Obstacle(
            s0=float(rng.uniform(27.0, 33.0)),
            l0=first_side * float(rng.uniform(1.5, 2.0)),
            vs=float(rng.uniform(1.5, 3.5)),
            vl=-first_side * float(rng.uniform(0.15, 0.35)),
            W=1.8,
            L=4.3,
            name="merge vehicle",
            obs_type="vehicle",
        ),
    ]
    return Scenario(ego, obstacles, s_max=45.0, t_max=14.0)


def _prediction_noise(rng: np.random.Generator) -> RandomCase:
    truth = _vehicle_cut_in(rng)
    planning = copy.deepcopy(truth)
    planning.ego.s0 += float(rng.normal(0.0, 0.12))
    planning.ego.l0 += float(rng.normal(0.0, 0.08))
    planning.ego.v0 = max(0.5, planning.ego.v0 + float(rng.normal(0.0, 0.25)))
    for obstacle in planning.obstacles:
        obstacle.s0 += float(rng.normal(0.0, 0.35))
        obstacle.l0 += float(rng.normal(0.0, 0.18))
        obstacle.vs += float(rng.normal(0.0, 0.30))
        obstacle.vl += float(rng.normal(0.0, 0.12))
    return RandomCase("prediction_noise", -1, planning, truth)


def generate_case(kind: str, seed: int) -> RandomCase:
    if seed < 0:
        raise ValueError("seed must be non-negative")
    rng = _rng(kind, seed)
    if kind == "prediction_noise":
        generated = _prediction_noise(rng)
        return RandomCase(kind, seed, generated.planning_scenario, generated.truth_scenario)

    generators = {
        "crossing_pedestrian": _crossing_pedestrian,
        "vehicle_cut_in": _vehicle_cut_in,
        "parked_and_oncoming": _parked_and_oncoming,
        "narrow_multi_obstacle": _narrow_multi_obstacle,
        "interleaved_dynamic": _interleaved_dynamic,
    }
    try:
        scenario = generators[kind](rng)
    except KeyError as exc:
        raise KeyError(kind) from exc
    return RandomCase(kind, seed, scenario, copy.deepcopy(scenario))
