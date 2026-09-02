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
