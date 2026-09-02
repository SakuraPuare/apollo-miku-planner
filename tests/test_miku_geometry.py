"""Property and regression tests for MIKU's centre-interval geometry."""

from __future__ import annotations

import random

import pytest

from miku_geometry import ForbiddenInterval, brute_force_max_gap, solve_max_gap


def test_prefix_max_regression_for_nested_intervals() -> None:
    """The previous adjacent-v formula overestimated the middle gap here."""

    intervals = [
        ForbiddenInterval(-1.5, 1.2),
        ForbiddenInterval(-0.8, -0.3),
        ForbiddenInterval(0.4, 0.7),
    ]

    result = solve_max_gap(intervals, -2.0, 2.0)

    assert result.prefix_max_v == pytest.approx((1.2, 1.2, 1.2))
    assert result.candidate_gaps == pytest.approx((0.5, -2.0, -0.8, 0.8))
    assert result.split_index == 3
    assert result.gap == pytest.approx(0.8)


@pytest.mark.parametrize("seed", range(20))
def test_fast_solver_matches_exhaustive_oracle(seed: int) -> None:
    """Check exact optimal width for 4,000 deterministic random instances."""

    rng = random.Random(seed)
    for _ in range(200):
        road_lower = rng.uniform(-4.0, -1.0)
        road_upper = rng.uniform(1.0, 4.0)
        intervals = []
        for _ in range(rng.randint(0, 8)):
            centre = rng.uniform(road_lower - 1.5, road_upper + 1.5)
            half_width = rng.uniform(0.01, 2.0)
            intervals.append(
                ForbiddenInterval(centre - half_width, centre + half_width)
            )

        fast = solve_max_gap(intervals, road_lower, road_upper)
        oracle = brute_force_max_gap(intervals, road_lower, road_upper)

        assert fast.gap == pytest.approx(oracle.gap, abs=1.0e-12)
        assert fast.upper - fast.lower == pytest.approx(fast.gap)


def test_feasibility_uses_centre_width_epsilon_not_vehicle_width() -> None:
    result = solve_max_gap([ForbiddenInterval(-0.5, 0.5)], -1.0, 1.0)

    assert result.gap == pytest.approx(0.5)
    assert result.is_feasible(1.0e-6)
    assert not result.is_feasible(0.6)


@pytest.mark.parametrize(
    ("road_lower", "road_upper"),
    [(1.0, -1.0), (float("-inf"), 1.0), (-1.0, float("inf"))],
)
def test_invalid_road_bounds_are_rejected(road_lower: float, road_upper: float) -> None:
    with pytest.raises(ValueError):
        solve_max_gap([], road_lower, road_upper)


def test_invalid_forbidden_interval_is_rejected() -> None:
    with pytest.raises(ValueError):
        ForbiddenInterval(1.0, -1.0)
