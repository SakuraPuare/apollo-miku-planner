"""Safe arrival-window construction for MIKU conflict points.

The nominal arrival estimate is used only to choose a temporal homotopy class.
Safety bounds themselves are derived directly from predicted obstacle occupancy.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence


@dataclass(frozen=True, order=True)
class TimeWindow:
    """Closed time window used after applying an explicit safety guard."""

    start: float
    end: float

    def __post_init__(self) -> None:
        if math.isnan(self.start) or math.isnan(self.end):
            raise ValueError("time-window bounds must not be NaN")
        if self.start > self.end:
            raise ValueError(f"invalid time window [{self.start}, {self.end}]")

    def intersect(self, other: TimeWindow) -> TimeWindow | None:
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        return TimeWindow(start, end) if start <= end else None

    def project(self, value: float) -> float:
        return min(self.end, max(self.start, value))


@dataclass(frozen=True)
class OccupancyInterval:
    """Predicted time interval during which a conflict region is occupied."""

    enter: float
    exit: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.enter) or not math.isfinite(self.exit):
            raise ValueError("occupancy bounds must be finite")
        if self.enter > self.exit:
            raise ValueError("occupancy enter time must not exceed exit time")


@dataclass(frozen=True)
class WindowSelection:
    """Selected safe homotopy class, or an explicit stop fallback."""

    status: str
    window: TimeWindow | None
    target_arrival: float | None
    candidate_count: int


def merge_windows(windows: Iterable[TimeWindow]) -> tuple[TimeWindow, ...]:
    """Return the sorted union of overlapping or touching closed windows."""

    ordered = sorted(windows)
    merged: list[TimeWindow] = []
    for window in ordered:
        if not merged or window.start > merged[-1].end:
            merged.append(window)
        else:
            merged[-1] = TimeWindow(merged[-1].start, max(merged[-1].end, window.end))
    return tuple(merged)


def safe_time_windows(
    occupancies: Sequence[OccupancyInterval],
    horizon: TimeWindow,
    safety_guard: float = 0.0,
) -> tuple[TimeWindow, ...]:
    """Compute safe arrival components from obstacle occupancy, not from ``tau``.

    Each occupancy is expanded by ``safety_guard`` and clipped to the planning
    horizon.  The result is the complement of the merged occupied set.  A
    single conflict therefore naturally yields the before-pass and after-pass
    candidates; interleaved obstacles may yield more components.
    """

    if safety_guard < 0.0 or not math.isfinite(safety_guard):
        raise ValueError("safety_guard must be finite and non-negative")
    blocked = []
    for occupancy in occupancies:
        expanded = TimeWindow(
            occupancy.enter - safety_guard,
            occupancy.exit + safety_guard,
        ).intersect(horizon)
        if expanded is not None:
            blocked.append(expanded)

    merged = merge_windows(blocked)
    if not merged:
        return (horizon,)

    safe: list[TimeWindow] = []
    cursor = horizon.start
    for occupied in merged:
        if cursor < occupied.start:
            safe.append(TimeWindow(cursor, occupied.start))
        cursor = max(cursor, occupied.end)
    if cursor < horizon.end:
        safe.append(TimeWindow(cursor, horizon.end))
    return tuple(safe)


def intersect_window_sets(
    window_sets: Sequence[Sequence[TimeWindow]],
) -> tuple[TimeWindow, ...]:
    """Intersect unions of windows and explicitly return an empty tuple."""

    if not window_sets:
        return ()
    feasible = tuple(window_sets[0])
    for windows in window_sets[1:]:
        intersections = []
        for left in feasible:
            for right in windows:
                overlap = left.intersect(right)
                if overlap is not None:
                    intersections.append(overlap)
        feasible = merge_windows(intersections)
        if not feasible:
            break
    return feasible


def select_time_window(
    safe_windows: Sequence[TimeWindow],
    nominal_arrival: float,
    reachable: TimeWindow,
) -> WindowSelection:
    """Choose a safe homotopy class closest to the current-cycle arrival seed."""

    if not math.isfinite(nominal_arrival):
        raise ValueError("nominal_arrival must be finite")
    feasible = [
        overlap
        for window in safe_windows
        if (overlap := window.intersect(reachable)) is not None
    ]
    if not feasible:
        return WindowSelection("stop", None, None, 0)

    ranked = sorted(
        (
            (abs(window.project(nominal_arrival) - nominal_arrival), window.project(nominal_arrival), window)
            for window in feasible
        ),
        key=lambda item: (item[0], item[1], item[2].start, item[2].end),
    )
    _, target, window = ranked[0]
    return WindowSelection("selected", window, target, len(feasible))
