"""Tests for occupancy-derived temporal homotopy windows."""

from __future__ import annotations

import random

import pytest

from miku_time import (
    ConflictPoint,
    OccupancyInterval,
    TimeWindow,
    intersect_window_sets,
    enumerate_temporal_homotopies,
    safe_time_windows,
    select_time_window,
)
from apollo_pipeline import (
    Ego,
    Obstacle,
    Scenario,
    build_st_bounds,
    run_pipeline,
    st_boundary_mapper,
    validate_pipeline_candidate_continuous_safety,
)

import numpy as np


def test_single_conflict_has_before_and_after_candidates() -> None:
    windows = safe_time_windows(
        [OccupancyInterval(3.0, 5.0)],
        TimeWindow(0.0, 10.0),
        safety_guard=0.5,
    )

    assert windows == (TimeWindow(0.0, 2.5), TimeWindow(5.5, 10.0))


def test_interleaved_occupancies_are_merged_before_complement() -> None:
    windows = safe_time_windows(
        [
            OccupancyInterval(2.0, 4.0),
            OccupancyInterval(3.0, 5.0),
            OccupancyInterval(7.0, 8.0),
        ],
        TimeWindow(0.0, 10.0),
    )

    assert windows == (
        TimeWindow(0.0, 2.0),
        TimeWindow(5.0, 7.0),
        TimeWindow(8.0, 10.0),
    )


def test_nominal_arrival_only_selects_the_homotopy_class() -> None:
    windows = (TimeWindow(0.0, 2.0), TimeWindow(5.0, 9.0))

    before = select_time_window(windows, 1.5, TimeWindow(0.0, 8.0))
    after = select_time_window(windows, 4.5, TimeWindow(0.0, 8.0))

    assert before.window == TimeWindow(0.0, 2.0)
    assert before.target_arrival == pytest.approx(1.5)
    assert after.window == TimeWindow(5.0, 8.0)
    assert after.target_arrival == pytest.approx(5.0)


def test_empty_intersection_triggers_explicit_stop_fallback() -> None:
    common = intersect_window_sets(
        [
            (TimeWindow(0.0, 2.0),),
            (TimeWindow(3.0, 5.0),),
        ]
    )

    assert common == ()
    assert select_time_window(common, 2.0, TimeWindow(0.0, 6.0)).status == "stop"


@pytest.mark.parametrize("seed", range(10))
def test_random_safe_windows_match_pointwise_occupancy_oracle(seed: int) -> None:
    rng = random.Random(seed)
    horizon = TimeWindow(0.0, 12.0)
    for _ in range(100):
        occupancies = []
        for _ in range(rng.randint(0, 8)):
            enter = rng.uniform(-2.0, 13.0)
            exit = enter + rng.uniform(0.0, 3.0)
            occupancies.append(OccupancyInterval(enter, exit))
        guard = rng.uniform(0.0, 0.4)
        safe = safe_time_windows(occupancies, horizon, guard)

        for sample_index in range(1, 240):
            t = horizon.start + (horizon.end - horizon.start) * sample_index / 240
            in_safe = any(window.start < t < window.end for window in safe)
            in_blocked = any(
                occupancy.enter - guard < t < occupancy.exit + guard
                for occupancy in occupancies
            )
            assert in_safe == (not in_blocked)


def test_invalid_guard_is_rejected() -> None:
    with pytest.raises(ValueError):
        safe_time_windows([], TimeWindow(0.0, 1.0), -0.1)


def test_st_bounds_encode_reachable_before_pass_window() -> None:
    scenario = Scenario(Ego(v0=5.0), [], s_max=20.0, t_max=6.0)
    ts = np.linspace(0.0, 6.0, 61)
    boundary = {
        "name": "crossing",
        "is_static": False,
        "vs": 0.0,
        "vl": 1.0,
        "intervals": [(t, 8.0, 10.0) for t in np.arange(3.0, 4.01, 0.05)],
    }
    decisions = []
    upper, lower = build_st_bounds(
        scenario,
        [boundary],
        np.zeros_like(ts),
        ts,
        safe_window_mode=True,
        decision_log=decisions,
    )
    # Pass-before is complete by the first safe-window end, before occupancy.
    assert decisions[0]["window"][1] == pytest.approx(2.85)
    assert decisions[0]["homotopy_label"] == "pass_before"
    assert np.all(lower[ts >= 2.85] >= 10.05)
    window_start = decisions[0]["window"][0]
    assert np.all(upper[ts >= window_start] == 1e4)


def test_st_bounds_encode_after_pass_window_when_before_is_unreachable() -> None:
    scenario = Scenario(Ego(v0=1.0), [], s_max=20.0, t_max=6.0)
    ts = np.linspace(0.0, 6.0, 61)
    boundary = {
        "name": "crossing",
        "is_static": False,
        "vs": 0.0,
        "vl": 1.0,
        "intervals": [(t, 8.0, 10.0) for t in np.arange(2.0, 4.01, 0.05)],
    }
    decisions = []
    upper, lower = build_st_bounds(
        scenario,
        [boundary],
        np.zeros_like(ts),
        ts,
        safe_window_mode=True,
        decision_log=decisions,
    )
    # Yield-after remains behind until the final safe-window opens.
    assert decisions[0]["window"] == pytest.approx((4.15, 6.0))
    assert decisions[0]["homotopy_label"] == "yield_after"
    assert np.all(upper[ts < 4.15] <= 7.95)
    assert np.all(lower == 0.0)


def test_temporal_graph_enforces_causal_travel_between_conflicts() -> None:
    homotopies = enumerate_temporal_homotopies(
        [
            ConflictPoint(
                "near",
                10.0,
                (TimeWindow(0.0, 1.0), TimeWindow(3.0, 8.0)),
                0.8,
            ),
            ConflictPoint(
                "far",
                30.0,
                (TimeWindow(0.0, 2.0), TimeWindow(4.0, 8.0)),
                2.0,
            ),
        ],
        start_station=0.0,
        max_speed=10.0,
    )

    assert homotopies
    # Reaching s=30 by t=2 after visiting s=10 is impossible at 10 m/s, so the
    # far conflict must use its later safe component.
    assert all(plan.choices[-1].window_index == 1 for plan in homotopies)
    assert all(plan.choices[-1].target_arrival >= 4.0 for plan in homotopies)


def test_temporal_graph_returns_ranked_finite_beam() -> None:
    conflicts = [
        ConflictPoint(
            f"c{index}",
            5.0 * (index + 1),
            (TimeWindow(0.0, 3.0), TimeWindow(4.0, 10.0)),
            float(index + 1),
        )
        for index in range(4)
    ]

    homotopies = enumerate_temporal_homotopies(
        conflicts,
        start_station=0.0,
        max_speed=13.0,
        beam_width=3,
    )

    assert 1 <= len(homotopies) <= 3
    assert [plan.cost for plan in homotopies] == sorted(plan.cost for plan in homotopies)
    assert all(len(plan.choices) == len(conflicts) for plan in homotopies)


def test_temporal_graph_respects_previous_cycle_preference() -> None:
    point = ConflictPoint(
        "crossing",
        10.0,
        (TimeWindow(1.0, 2.0), TimeWindow(3.0, 5.0)),
        2.5,
    )

    default = enumerate_temporal_homotopies([point], 0.0, max_speed=20.0)
    persistent = enumerate_temporal_homotopies(
        [point],
        0.0,
        max_speed=20.0,
        preferred_window_labels={"crossing": "yield_after"},
        persistence_penalty=1.0,
    )

    assert default[0].choices[0].window_index == 0
    assert persistent[0].choices[0].window_index == 1


def test_robust_mapper_propagates_reported_prediction_error() -> None:
    obstacle = Obstacle(
        s0=10.0,
        l0=1.2,
        vs=1.0,
        vl=-0.2,
        W=0.5,
        L=1.0,
        uncertainty_s0=0.4,
        uncertainty_l0=0.2,
        uncertainty_vs=0.3,
        uncertainty_vl=0.1,
    )
    scenario = Scenario(Ego(), [obstacle], s_max=25.0, t_max=3.0)
    stations = np.linspace(0.0, 25.0, 51)
    path = np.zeros_like(stations)

    nominal = st_boundary_mapper(scenario, stations, path, robust_prediction=False)[0]
    robust = st_boundary_mapper(scenario, stations, path, robust_prediction=True)[0]

    assert len(robust["intervals"]) >= len(nominal["intervals"])
    shared_time = nominal["intervals"][0][0]
    nominal_interval = next(row for row in nominal["intervals"] if row[0] == shared_time)
    robust_interval = next(row for row in robust["intervals"] if row[0] == shared_time)
    assert robust_interval[1] < nominal_interval[1]
    assert robust_interval[2] > nominal_interval[2]


def test_pipeline_candidate_exposes_continuous_safety_validation() -> None:
    obstacle = Obstacle(
        s0=10.0,
        l0=5.0,
        W=0.5,
        L=1.0,
        is_static=True,
        name="off-road obstacle",
    )
    scenario = Scenario(Ego(v0=3.0), [obstacle], s_max=15.0, t_max=5.0)
    result = run_pipeline("miku", scenario)

    certificates = validate_pipeline_candidate_continuous_safety(scenario, result)

    assert certificates[obstacle.name].certified
