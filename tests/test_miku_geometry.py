"""Property and regression tests for MIKU's centre-interval geometry."""

from __future__ import annotations

from itertools import product
import random

import pytest

from miku_geometry import (
    ForbiddenInterval,
    LateralBandCandidate,
    brute_force_max_gap,
    enumerate_lateral_bands,
    enumerate_spatial_homotopies,
    select_spatial_homotopy,
    solve_max_gap,
)


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


def test_top_k_bands_are_ranked_and_match_max_gap() -> None:
    intervals = [ForbiddenInterval(-1.1, -0.4), ForbiddenInterval(0.2, 0.8)]

    bands = enumerate_lateral_bands(intervals, -2.0, 2.0, top_k=2)
    optimum = solve_max_gap(intervals, -2.0, 2.0)

    assert len(bands) == 2
    assert bands[0].gap == pytest.approx(optimum.gap)
    assert bands[0].split_index == optimum.split_index
    assert bands[0].gap >= bands[1].gap


def test_k_obstacles_have_only_k_plus_one_continuous_bands() -> None:
    intervals = [
        ForbiddenInterval(-1.5, -1.0),
        ForbiddenInterval(-0.2, 0.4),
        ForbiddenInterval(0.8, 1.1),
    ]

    bands = enumerate_lateral_bands(intervals, -2.0, 2.0)

    assert len(bands) == len(intervals) + 1
    assert {band.split_index for band in bands} == {0, 1, 2, 3}


def test_invalid_top_k_is_rejected() -> None:
    with pytest.raises(ValueError):
        enumerate_lateral_bands([], -1.0, 1.0, top_k=0)


def test_spatial_homotopy_trades_small_width_for_continuity() -> None:
    first = (
        # Slightly wider, but far left.
        enumerate_lateral_bands([ForbiddenInterval(-0.2, 1.6)], -2.0, 2.0)[0],
    )
    second_candidates = enumerate_lateral_bands(
        [ForbiddenInterval(-1.6, 0.2)], -2.0, 2.0
    )

    selected = select_spatial_homotopy(
        (first, second_candidates),
        initial_lateral=0.0,
        transition_weight=1.0,
    )

    assert selected is not None
    assert len(selected.bands) == 2
    assert all(band.gap > 0.0 for band in selected.bands)


def test_spatial_homotopy_rejects_layer_without_positive_band() -> None:
    blocked = enumerate_lateral_bands(
        [ForbiddenInterval(-2.0, 2.0)], -1.0, 1.0
    )

    assert select_spatial_homotopy((blocked,), 0.0) is None


def test_spatial_homotopy_dynamic_program_matches_exhaustive_sequences() -> None:
    rng = random.Random(17)
    for _ in range(100):
        initial_lateral = rng.uniform(-1.0, 1.0)
        transition_weight = rng.uniform(0.0, 1.0)
        layers = []
        for _ in range(rng.randint(1, 6)):
            layer = []
            for split_index in range(rng.randint(1, 4)):
                centre = rng.uniform(-2.0, 2.0)
                gap = rng.uniform(0.1, 3.0)
                layer.append(
                    LateralBandCandidate(
                        split_index,
                        centre - gap / 2.0,
                        centre + gap / 2.0,
                        gap,
                        (),
                    )
                )
            layers.append(tuple(layer))

        def sequence_key(sequence):
            cost = 0.0
            previous_centre = initial_lateral
            for band in sequence:
                centre = 0.5 * (band.lower + band.upper)
                cost += -band.gap + transition_weight * abs(
                    centre - previous_centre
                )
                previous_centre = centre
            return cost, tuple(band.split_index for band in sequence)

        exhaustive = min(product(*layers), key=sequence_key)
        selected = select_spatial_homotopy(
            layers,
            initial_lateral,
            transition_weight,
        )

        assert selected is not None
        assert selected.bands == exhaustive
        assert selected.cost == pytest.approx(sequence_key(exhaustive)[0])


def test_top_k_spatial_homotopies_match_exhaustive_ranking() -> None:
    rng = random.Random(23)
    for _ in range(100):
        initial_lateral = rng.uniform(-1.0, 1.0)
        transition_weight = rng.uniform(0.0, 1.0)
        layers = []
        for _ in range(rng.randint(1, 5)):
            layer = []
            for split_index in range(rng.randint(1, 4)):
                centre = rng.uniform(-2.0, 2.0)
                gap = rng.uniform(0.1, 3.0)
                layer.append(
                    LateralBandCandidate(
                        split_index,
                        centre - gap / 2.0,
                        centre + gap / 2.0,
                        gap,
                        (),
                    )
                )
            layers.append(tuple(layer))

        def sequence_key(sequence):
            cost = 0.0
            previous_centre = initial_lateral
            for band in sequence:
                centre = 0.5 * (band.lower + band.upper)
                cost += -band.gap + transition_weight * abs(
                    centre - previous_centre
                )
                previous_centre = centre
            return cost, tuple(band.split_index for band in sequence)

        exhaustive = sorted(product(*layers), key=sequence_key)[:3]
        selected = enumerate_spatial_homotopies(
            layers,
            initial_lateral,
            top_k=3,
            transition_weight=transition_weight,
        )

        assert tuple(plan.bands for plan in selected) == tuple(exhaustive)
        assert tuple(plan.cost for plan in selected) == pytest.approx(
            tuple(sequence_key(sequence)[0] for sequence in exhaustive)
        )
