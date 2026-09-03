"""MIKU lateral geometry primitives.

All lateral bounds in this module refer to the ego reference point (normally
the vehicle centre).  Vehicle half-width and safety margins must therefore be
applied exactly once before constructing :class:`ForbiddenInterval` objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import math
from typing import Sequence


@dataclass(frozen=True)
class ForbiddenInterval:
    """Closed forbidden interval ``[u, v]`` for the ego reference point."""

    u: float
    v: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.u) or not math.isfinite(self.v):
            raise ValueError("forbidden interval bounds must be finite")
        if self.u > self.v:
            raise ValueError(f"invalid forbidden interval [{self.u}, {self.v}]")


@dataclass(frozen=True)
class MaxGapResult:
    """Exact maximum-width band and its continuous direction partition."""

    ordered_indices: tuple[int, ...]
    split_index: int
    lower: float
    upper: float
    gap: float
    candidate_gaps: tuple[float, ...]
    prefix_max_v: tuple[float, ...]
    directions: tuple[str, ...]

    def is_feasible(self, epsilon: float = 1.0e-6) -> bool:
        """Return whether the centre band meets the numerical width tolerance."""

        if epsilon < 0.0:
            raise ValueError("epsilon must be non-negative")
        return self.gap >= epsilon


@dataclass(frozen=True)
class BruteForceResult:
    """Reference result obtained by enumerating all ``2**k`` assignments."""

    lower: float
    upper: float
    gap: float
    directions: tuple[str, ...]


@dataclass(frozen=True)
class LateralBandCandidate:
    """One continuous lateral homotopy band induced by an ordered split."""

    split_index: int
    lower: float
    upper: float
    gap: float
    directions: tuple[str, ...]


@dataclass(frozen=True)
class SpatialHomotopy:
    """A longitudinally coherent sequence of lateral band candidates."""

    bands: tuple[LateralBandCandidate, ...]
    cost: float


def _validate_road(road_lower: float, road_upper: float) -> None:
    if not math.isfinite(road_lower) or not math.isfinite(road_upper):
        raise ValueError("road centre bounds must be finite")
    if road_lower > road_upper:
        raise ValueError("road_lower must not exceed road_upper")


def solve_max_gap(
    intervals: Sequence[ForbiddenInterval],
    road_lower: float,
    road_upper: float,
) -> MaxGapResult:
    """Solve the lateral direction assignment in ``O(k log k)`` time.

    Intervals are sorted by ``u`` (and by descending ``v`` for deterministic
    ties).  For split ``p``, intervals before ``p`` impose lower bounds and the
    remaining intervals impose upper bounds.  The running prefix maximum of
    ``v`` is essential: adjacent interval edges alone are not sufficient when
    forbidden intervals overlap or nest.

    Bounds are clipped against the centre-feasible road interval, so the same
    formula also handles obstacles extending beyond either road boundary.
    """

    _validate_road(road_lower, road_upper)
    ordered_indices = tuple(
        sorted(range(len(intervals)), key=lambda i: (intervals[i].u, -intervals[i].v, i))
    )
    ordered = [intervals[i] for i in ordered_indices]

    prefix_max_v = [road_lower]
    for interval in ordered:
        prefix_max_v.append(max(prefix_max_v[-1], interval.v))

    candidate_lowers: list[float] = []
    candidate_uppers: list[float] = []
    candidate_gaps: list[float] = []
    for split in range(len(ordered) + 1):
        lower = prefix_max_v[split]
        upper = road_upper if split == len(ordered) else min(road_upper, ordered[split].u)
        candidate_lowers.append(lower)
        candidate_uppers.append(upper)
        candidate_gaps.append(upper - lower)

    split_index = max(range(len(candidate_gaps)), key=candidate_gaps.__getitem__)
    ordered_directions = (
        ["left"] * split_index + ["right"] * (len(ordered) - split_index)
    )
    directions = [""] * len(intervals)
    for ordered_position, original_index in enumerate(ordered_indices):
        directions[original_index] = ordered_directions[ordered_position]

    return MaxGapResult(
        ordered_indices=ordered_indices,
        split_index=split_index,
        lower=candidate_lowers[split_index],
        upper=candidate_uppers[split_index],
        gap=candidate_gaps[split_index],
        candidate_gaps=tuple(candidate_gaps),
        prefix_max_v=tuple(prefix_max_v[1:]),
        directions=tuple(directions),
    )


def enumerate_lateral_bands(
    intervals: Sequence[ForbiddenInterval],
    road_lower: float,
    road_upper: float,
    top_k: int | None = None,
) -> tuple[LateralBandCandidate, ...]:
    """Enumerate the ranked continuous homotopy bands in ``O(k log k)``.

    Sorting forbidden intervals by their lower edge establishes the only
    direction assignments that can bound a non-empty continuous free band:
    a prefix lies below the ego band and the remaining suffix lies above it.
    Consequently, ``k`` obstacles induce at most ``k + 1`` candidates instead
    of ``2**k`` arbitrary side assignments.  Candidates are ranked by width,
    then by distance of their centre to the road centre for deterministic
    warm-start-friendly selection.
    """

    _validate_road(road_lower, road_upper)
    if top_k is not None and top_k <= 0:
        raise ValueError("top_k must be positive or None")

    ordered_indices = tuple(
        sorted(range(len(intervals)), key=lambda i: (intervals[i].u, -intervals[i].v, i))
    )
    ordered = [intervals[i] for i in ordered_indices]
    prefix_max_v = [road_lower]
    for interval in ordered:
        prefix_max_v.append(max(prefix_max_v[-1], interval.v))

    candidates = []
    for split in range(len(ordered) + 1):
        lower = prefix_max_v[split]
        upper = road_upper if split == len(ordered) else min(road_upper, ordered[split].u)
        ordered_directions = ["left"] * split + ["right"] * (len(ordered) - split)
        directions = [""] * len(intervals)
        for ordered_position, original_index in enumerate(ordered_indices):
            directions[original_index] = ordered_directions[ordered_position]
        candidates.append(
            LateralBandCandidate(
                split_index=split,
                lower=lower,
                upper=upper,
                gap=upper - lower,
                directions=tuple(directions),
            )
        )

    road_centre = 0.5 * (road_lower + road_upper)
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            -candidate.gap,
            abs(0.5 * (candidate.lower + candidate.upper) - road_centre),
            candidate.split_index,
        ),
    )
    return tuple(ranked if top_k is None else ranked[:top_k])


def select_spatial_homotopy(
    layers: Sequence[Sequence[LateralBandCandidate]],
    initial_lateral: float,
    transition_weight: float = 0.05,
    gap_epsilon: float = 1.0e-6,
) -> SpatialHomotopy | None:
    """Select the best coherent spatial homotopy with dynamic programming."""

    plans = enumerate_spatial_homotopies(
        layers,
        initial_lateral,
        top_k=1,
        transition_weight=transition_weight,
        gap_epsilon=gap_epsilon,
    )
    return plans[0] if plans else None


def enumerate_spatial_homotopies(
    layers: Sequence[Sequence[LateralBandCandidate]],
    initial_lateral: float,
    top_k: int = 3,
    transition_weight: float = 0.05,
    gap_epsilon: float = 1.0e-6,
) -> tuple[SpatialHomotopy, ...]:
    """Return the exact Top-K paths through the layered lateral-band graph.

    The node cost rewards wider bands and the edge cost penalizes lateral
    centre changes.  Keeping the K best prefixes *per terminal node* is exact
    for this first-order layered graph: every future cost depends on a prefix
    only through its current band.  Complexity is ``O(M K Q^2 log(KQ))`` for
    ``M`` layers of at most ``Q`` candidates.
    """

    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if transition_weight < 0.0 or not math.isfinite(transition_weight):
        raise ValueError("transition_weight must be finite and non-negative")
    if gap_epsilon < 0.0 or not math.isfinite(gap_epsilon):
        raise ValueError("gap_epsilon must be finite and non-negative")
    if not layers:
        return (SpatialHomotopy((), 0.0),)

    feasible_layers = [
        [band for band in layer if band.gap >= gap_epsilon] for layer in layers
    ]
    if any(not layer for layer in feasible_layers):
        return ()

    # State is (cost, band sequence).  Maintain K prefixes for each current
    # terminal band rather than a single winner, enabling genuine QP fallback.
    states_by_terminal: list[list[tuple[float, tuple[LateralBandCandidate, ...]]]] = []
    for band in feasible_layers[0]:
        centre = 0.5 * (band.lower + band.upper)
        states_by_terminal.append(
            [
                (
                    -band.gap + transition_weight * abs(centre - initial_lateral),
                    (band,),
                )
            ]
        )

    for layer in feasible_layers[1:]:
        next_by_terminal = []
        for band in layer:
            centre = 0.5 * (band.lower + band.upper)
            expanded = []
            for prefixes in states_by_terminal:
                for cost, sequence in prefixes:
                    previous = sequence[-1]
                    previous_centre = 0.5 * (previous.lower + previous.upper)
                    expanded.append(
                        (
                            cost
                            - band.gap
                            + transition_weight * abs(centre - previous_centre),
                            sequence + (band,),
                        )
                    )
            expanded.sort(
                key=lambda item: (
                    item[0],
                    tuple(candidate.split_index for candidate in item[1]),
                )
            )
            next_by_terminal.append(expanded[:top_k])
        states_by_terminal = next_by_terminal

    complete = [state for terminal in states_by_terminal for state in terminal]
    complete.sort(
        key=lambda item: (
            item[0],
            tuple(candidate.split_index for candidate in item[1]),
        )
    )
    return tuple(SpatialHomotopy(sequence, cost) for cost, sequence in complete[:top_k])


def brute_force_max_gap(
    intervals: Sequence[ForbiddenInterval],
    road_lower: float,
    road_upper: float,
) -> BruteForceResult:
    """Enumerate every direction assignment as a small-instance oracle."""

    _validate_road(road_lower, road_upper)
    best: BruteForceResult | None = None
    for directions in product(("left", "right"), repeat=len(intervals)):
        lower = max(
            [road_lower]
            + [interval.v for interval, side in zip(intervals, directions) if side == "left"]
        )
        upper = min(
            [road_upper]
            + [interval.u for interval, side in zip(intervals, directions) if side == "right"]
        )
        candidate = BruteForceResult(lower, upper, upper - lower, directions)
        if best is None or candidate.gap > best.gap:
            best = candidate

    assert best is not None
    return best
