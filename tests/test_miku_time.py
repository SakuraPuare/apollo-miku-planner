"""Tests for occupancy-derived temporal homotopy windows."""

from __future__ import annotations

import random

import pytest

from miku_time import (
    OccupancyInterval,
    TimeWindow,
    intersect_window_sets,
    safe_time_windows,
    select_time_window,
)
from apollo_pipeline import Ego, Scenario, build_st_bounds

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
    assert decisions[0]["window"][1] == pytest.approx(2.9)
    assert np.all(lower[ts >= 2.9] >= 10.0)
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
    assert decisions[0]["window"] == pytest.approx((4.1, 6.0))
    assert np.all(upper[ts < 4.1] <= 8.0)
    assert np.all(lower == 0.0)
