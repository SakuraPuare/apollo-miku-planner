"""Certified lazy search over a finite joint homotopy domain.

The planner has two discrete levels.  A spatial homotopy determines a path
corridor; only then can its path-dependent temporal homotopies be constructed.
This module keeps that dependency explicit: spatial branches are expanded
lazily into complete spatial--temporal candidates, while a single best-first
queue provides a global lower bound over everything not evaluated yet.

The certificate is relative to the supplied *finite* candidate domain.  It
does not claim completeness of the discretisation used to construct that
domain.  Every lower bound is checked at runtime against its parent and, after
evaluation, against the realised objective so an invalid certificate cannot be
reported silently.
"""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Callable, Generic, Iterable, Literal, Sequence, TypeVar


PayloadT = TypeVar("PayloadT")
SolutionT = TypeVar("SolutionT")


@dataclass(frozen=True)
class JointHomotopyCandidate(Generic[PayloadT]):
    """One complete spatial--temporal label and an admissible cost bound."""

    spatial_label: tuple[int, ...]
    temporal_label: tuple[int, ...]
    lower_bound: float
    payload: PayloadT

    @property
    def label(self) -> tuple[tuple[int, ...], tuple[int, ...]]:
        return self.spatial_label, self.temporal_label


@dataclass(frozen=True)
class SpatialHomotopyBranch(Generic[PayloadT]):
    """Lazy path-dependent temporal domain below one spatial homotopy."""

    spatial_label: tuple[int, ...]
    lower_bound: float
    expand_temporal: Callable[[], Iterable[JointHomotopyCandidate[PayloadT]]]


@dataclass(frozen=True)
class CandidateEvaluation(Generic[SolutionT]):
    """Result of the fixed-homotopy continuous optimisation and validation."""

    feasible: bool
    objective: float | None = None
    solution: SolutionT | None = None

    def __post_init__(self) -> None:
        if self.feasible:
            if self.objective is None or not math.isfinite(self.objective):
                raise ValueError("a feasible evaluation needs a finite objective")
        elif self.objective is not None:
            raise ValueError("an infeasible evaluation must not report an objective")


SearchStatus = Literal["optimal", "budget_exhausted", "infeasible"]


@dataclass(frozen=True)
class JointSearchResult(Generic[PayloadT, SolutionT]):
    """Incumbent and a posteriori optimality certificate."""

    status: SearchStatus
    incumbent: JointHomotopyCandidate[PayloadT] | None
    solution: SolutionT | None
    lower_bound: float
    upper_bound: float
    absolute_gap: float
    relative_gap: float
    evaluated_candidates: int
    expanded_spatial_branches: int
    remaining_queue_items: int


def _finite_bound(value: float, field: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _certificate_values(
    incumbent_objective: float,
    open_lower_bound: float,
) -> tuple[float, float, float, float]:
    if math.isfinite(incumbent_objective):
        lower = min(incumbent_objective, open_lower_bound)
        upper = incumbent_objective
        gap = max(0.0, upper - lower)
        relative = gap / max(abs(upper), 1.0e-12)
        return lower, upper, gap, relative
    return open_lower_bound, math.inf, math.inf, math.inf


def bounded_lazy_joint_search(
    branches: Iterable[SpatialHomotopyBranch[PayloadT]],
    evaluate: Callable[
        [JointHomotopyCandidate[PayloadT]], CandidateEvaluation[SolutionT]
    ],
    *,
    max_evaluations: int | None = None,
    absolute_tolerance: float = 1.0e-9,
) -> JointSearchResult[PayloadT, SolutionT]:
    """Best-first branch-and-bound with an anytime optimality gap.

    ``max_evaluations`` limits expensive fixed-homotopy evaluations; expanding
    a spatial branch does not consume this budget.  With no budget limit, the
    method returns the minimum-objective feasible candidate in the finite
    domain or proves that the domain is infeasible.  Under truncation it returns
    ``U-L``, where ``U`` is the best evaluated feasible objective and ``L`` is
    the smallest admissible bound among the incumbent and all open items.

    A child's bound must be no smaller than its spatial parent's bound, and a
    realised feasible objective must be no smaller than its candidate bound.
    These checks make the reported certificate fail closed.
    """

    if max_evaluations is not None and max_evaluations < 0:
        raise ValueError("max_evaluations must be non-negative or None")
    if absolute_tolerance < 0.0 or not math.isfinite(absolute_tolerance):
        raise ValueError("absolute_tolerance must be finite and non-negative")

    # (lower bound, kind order, deterministic label, serial, object)
    queue: list[tuple[float, int, tuple, int, object]] = []
    serial = 0
    for branch in branches:
        bound = _finite_bound(branch.lower_bound, "branch lower_bound")
        heapq.heappush(queue, (bound, 0, branch.spatial_label, serial, branch))
        serial += 1

    incumbent: JointHomotopyCandidate[PayloadT] | None = None
    incumbent_solution: SolutionT | None = None
    incumbent_objective = math.inf
    evaluated = 0
    expanded = 0

    while queue:
        open_lower = queue[0][0]
        if incumbent is not None and incumbent_objective <= open_lower + absolute_tolerance:
            lower, upper, gap, relative = _certificate_values(
                incumbent_objective, open_lower
            )
            return JointSearchResult(
                "optimal",
                incumbent,
                incumbent_solution,
                lower,
                upper,
                gap,
                relative,
                evaluated,
                expanded,
                len(queue),
            )

        bound, kind, _label, _serial, item = heapq.heappop(queue)
        if kind == 0:
            branch = item
            assert isinstance(branch, SpatialHomotopyBranch)
            children = tuple(branch.expand_temporal())
            expanded += 1
            seen_temporal_labels: set[tuple[int, ...]] = set()
            for child in children:
                if child.spatial_label != branch.spatial_label:
                    raise ValueError("temporal child has a different spatial label")
                if child.temporal_label in seen_temporal_labels:
                    raise ValueError("duplicate temporal label within a spatial branch")
                seen_temporal_labels.add(child.temporal_label)
                child_bound = _finite_bound(child.lower_bound, "candidate lower_bound")
                if child_bound + absolute_tolerance < bound:
                    raise ValueError("candidate lower bound is below its parent bound")
                joint_label = (child.spatial_label, child.temporal_label)
                heapq.heappush(queue, (child_bound, 1, joint_label, serial, child))
                serial += 1
            continue

        candidate = item
        assert isinstance(candidate, JointHomotopyCandidate)
        if max_evaluations is not None and evaluated >= max_evaluations:
            # Put the unevaluated candidate back: it contributes to L.
            heapq.heappush(queue, (bound, kind, _label, _serial, candidate))
            lower, upper, gap, relative = _certificate_values(
                incumbent_objective, queue[0][0]
            )
            return JointSearchResult(
                "budget_exhausted",
                incumbent,
                incumbent_solution,
                lower,
                upper,
                gap,
                relative,
                evaluated,
                expanded,
                len(queue),
            )

        evaluation = evaluate(candidate)
        evaluated += 1
        if not evaluation.feasible:
            continue
        assert evaluation.objective is not None
        if evaluation.objective + absolute_tolerance < candidate.lower_bound:
            raise ValueError("realised objective violates candidate lower bound")
        candidate_key = candidate.label
        incumbent_key = None if incumbent is None else incumbent.label
        if (
            evaluation.objective < incumbent_objective - absolute_tolerance
            or (
                abs(evaluation.objective - incumbent_objective) <= absolute_tolerance
                and (incumbent_key is None or candidate_key < incumbent_key)
            )
        ):
            incumbent = candidate
            incumbent_solution = evaluation.solution
            incumbent_objective = evaluation.objective

    if incumbent is None:
        return JointSearchResult(
            "infeasible",
            None,
            None,
            math.inf,
            math.inf,
            math.inf,
            math.inf,
            evaluated,
            expanded,
            0,
        )
    return JointSearchResult(
        "optimal",
        incumbent,
        incumbent_solution,
        incumbent_objective,
        incumbent_objective,
        0.0,
        0.0,
        evaluated,
        expanded,
        0,
    )


@dataclass(frozen=True)
class AxisAlignedMotionSample:
    """Relative center positions and fixed footprint half-extents at one time."""

    time: float
    relative_longitudinal: float
    relative_lateral: float
    combined_half_length: float
    combined_half_width: float


@dataclass(frozen=True)
class ContinuousSafetyCertificate:
    """Sound, potentially conservative, inter-sample separation result."""

    certified: bool
    failed_interval: int | None
    maximum_longitudinal_guard: float
    maximum_lateral_guard: float


def certify_sampled_axis_aligned_motion(
    samples: Sequence[AxisAlignedMotionSample],
    *,
    relative_longitudinal_speed_bound: float,
    relative_lateral_speed_bound: float,
) -> ContinuousSafetyCertificate:
    """Certify continuous separation between samples using Lipschitz guards.

    For every interval, either endpoint must separate the rectangles along one
    axis by the footprint extent plus ``L * dt``.  A relative center trajectory
    whose speed on that axis is bounded by ``L`` then cannot close that margin
    anywhere in the interval.  The test is sound but incomplete: returning
    ``False`` means that denser sampling or a swept-volume check is required,
    not that a collision necessarily occurs.

    This closes the common logical gap between collision-free grid samples and
    continuous-time safety, provided the caller supplies valid relative-speed
    bounds and the footprint extents cover the complete interval.
    """

    longitudinal_bound = _finite_bound(
        relative_longitudinal_speed_bound,
        "relative_longitudinal_speed_bound",
    )
    lateral_bound = _finite_bound(
        relative_lateral_speed_bound,
        "relative_lateral_speed_bound",
    )
    if longitudinal_bound < 0.0 or lateral_bound < 0.0:
        raise ValueError("relative-speed bounds must be non-negative")
    if len(samples) < 2:
        raise ValueError("at least two time samples are required")

    maximum_longitudinal_guard = 0.0
    maximum_lateral_guard = 0.0
    for index, (left, right) in enumerate(zip(samples, samples[1:])):
        dt = float(right.time - left.time)
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("sample times must be finite and strictly increasing")
        for sample in (left, right):
            values = (
                sample.relative_longitudinal,
                sample.relative_lateral,
                sample.combined_half_length,
                sample.combined_half_width,
            )
            if not all(math.isfinite(float(value)) for value in values):
                raise ValueError("sample geometry must be finite")
            if sample.combined_half_length < 0.0 or sample.combined_half_width < 0.0:
                raise ValueError("combined footprint half-extents must be non-negative")

        longitudinal_guard = longitudinal_bound * dt
        lateral_guard = lateral_bound * dt
        maximum_longitudinal_guard = max(
            maximum_longitudinal_guard, longitudinal_guard
        )
        maximum_lateral_guard = max(maximum_lateral_guard, lateral_guard)

        def endpoint_certifies(sample: AxisAlignedMotionSample) -> bool:
            return (
                abs(sample.relative_longitudinal)
                > sample.combined_half_length + longitudinal_guard
                or abs(sample.relative_lateral)
                > sample.combined_half_width + lateral_guard
            )

        if not endpoint_certifies(left) and not endpoint_certifies(right):
            return ContinuousSafetyCertificate(
                False,
                index,
                maximum_longitudinal_guard,
                maximum_lateral_guard,
            )

    return ContinuousSafetyCertificate(
        True,
        None,
        maximum_longitudinal_guard,
        maximum_lateral_guard,
    )


def validate_candidate_continuous_safety(
    samples: Sequence[AxisAlignedMotionSample],
    *,
    relative_longitudinal_speed_bound: float,
    relative_lateral_speed_bound: float,
) -> ContinuousSafetyCertificate:
    """Validate every piecewise-linear swept rectangle interval.

    Relative centers are linearly interpolated between successive trajectory
    samples.  On each interval the larger endpoint footprint is used on each
    axis, so linearly growing uncertainty tubes are conservatively covered.
    Collision occurs iff the time fractions for which the longitudinal and
    lateral projections overlap have a non-empty intersection.  The result is
    therefore exact for constant extents and conservative for endpoint-bounded
    varying extents; it does not rely on collision-free sample points alone.
    Soundness requires an execution adapter that actually uses this linear
    center interpolation.  The certificate does not cover the quadratic
    constant-acceleration curve between speed-QP knots.

    The speed bounds remain part of the explicit motion contract and are
    validated here.  They are also consumed by the more conservative
    :func:`certify_sampled_axis_aligned_motion` when callers cannot assume
    piecewise-linear interpolation.
    """

    longitudinal_bound = _finite_bound(
        relative_longitudinal_speed_bound,
        "relative_longitudinal_speed_bound",
    )
    lateral_bound = _finite_bound(
        relative_lateral_speed_bound,
        "relative_lateral_speed_bound",
    )
    if longitudinal_bound < 0.0 or lateral_bound < 0.0:
        raise ValueError("relative-speed bounds must be non-negative")
    if len(samples) < 2:
        raise ValueError("at least two time samples are required")

    def overlap_fraction(value0: float, value1: float, half_extent: float):
        delta = value1 - value0
        if abs(delta) <= 1.0e-15:
            return (0.0, 1.0) if abs(value0) <= half_extent else None
        first = (-half_extent - value0) / delta
        second = (half_extent - value0) / delta
        lower = max(0.0, min(first, second))
        upper = min(1.0, max(first, second))
        return (lower, upper) if lower <= upper else None

    for index, (left, right) in enumerate(zip(samples, samples[1:])):
        dt = float(right.time - left.time)
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("sample times must be finite and strictly increasing")
        values = (
            left.relative_longitudinal,
            left.relative_lateral,
            right.relative_longitudinal,
            right.relative_lateral,
            left.combined_half_length,
            left.combined_half_width,
            right.combined_half_length,
            right.combined_half_width,
        )
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("sample geometry must be finite")
        if min(values[4:]) < 0.0:
            raise ValueError("combined footprint half-extents must be non-negative")
        longitudinal = overlap_fraction(
            left.relative_longitudinal,
            right.relative_longitudinal,
            max(left.combined_half_length, right.combined_half_length),
        )
        lateral = overlap_fraction(
            left.relative_lateral,
            right.relative_lateral,
            max(left.combined_half_width, right.combined_half_width),
        )
        if (
            longitudinal is not None
            and lateral is not None
            and max(longitudinal[0], lateral[0])
            <= min(longitudinal[1], lateral[1])
        ):
            return ContinuousSafetyCertificate(False, index, 0.0, 0.0)

    return ContinuousSafetyCertificate(True, None, 0.0, 0.0)
