from __future__ import annotations

from dataclasses import dataclass
import itertools
import random

import pytest

from joint_homotopy_search import (
    AxisAlignedMotionSample,
    CandidateEvaluation,
    JointHomotopyCandidate,
    SpatialHomotopyBranch,
    bounded_lazy_joint_search,
    certify_sampled_axis_aligned_motion,
    validate_candidate_constant_acceleration_safety,
    validate_candidate_continuous_safety,
)


@dataclass(frozen=True)
class ToyPayload:
    feasible: bool
    objective: float


def _candidate(
    spatial: int,
    temporal: int,
    lower_bound: float,
    objective: float,
    feasible: bool = True,
) -> JointHomotopyCandidate[ToyPayload]:
    return JointHomotopyCandidate(
        (spatial,),
        (temporal,),
        lower_bound,
        ToyPayload(feasible, objective),
    )


def _evaluate(candidate: JointHomotopyCandidate[ToyPayload]):
    payload = candidate.payload
    if not payload.feasible:
        return CandidateEvaluation[str](False)
    return CandidateEvaluation(True, payload.objective, f"solution-{candidate.label}")


def test_best_first_search_proves_optimality_without_evaluating_dominated_leaf():
    evaluated_labels = []

    def recording_evaluator(candidate):
        evaluated_labels.append(candidate.label)
        return _evaluate(candidate)

    branches = (
        SpatialHomotopyBranch(
            (0,),
            0.0,
            lambda: (
                _candidate(0, 0, 0.1, 0.0, feasible=False),
                _candidate(0, 1, 5.0, 5.0),
            ),
        ),
        SpatialHomotopyBranch(
            (1,),
            3.0,
            lambda: (_candidate(1, 0, 3.0, 3.5),),
        ),
    )

    result = bounded_lazy_joint_search(branches, recording_evaluator)

    assert result.status == "optimal"
    assert result.incumbent is not None
    assert result.incumbent.label == ((1,), (0,))
    assert result.upper_bound == pytest.approx(3.5)
    assert result.lower_bound == pytest.approx(3.5)
    assert result.absolute_gap == pytest.approx(0.0)
    assert ((0,), (1,)) not in evaluated_labels


def test_budget_truncation_returns_valid_nonzero_gap():
    branches = (
        SpatialHomotopyBranch(
            (0,), 0.0, lambda: (_candidate(0, 0, 0.0, 5.0),)
        ),
        SpatialHomotopyBranch(
            (1,), 3.0, lambda: (_candidate(1, 0, 3.0, 3.5),)
        ),
    )

    result = bounded_lazy_joint_search(branches, _evaluate, max_evaluations=1)

    assert result.status == "budget_exhausted"
    assert result.evaluated_candidates == 1
    assert result.lower_bound == pytest.approx(3.0)
    assert result.upper_bound == pytest.approx(5.0)
    assert result.absolute_gap == pytest.approx(2.0)
    assert result.relative_gap == pytest.approx(0.4)


def test_exhaustive_certificate_matches_brute_force_random_domains():
    rng = random.Random(20260905)
    for _ in range(100):
        candidates_by_spatial = []
        for spatial in range(rng.randint(1, 5)):
            candidates = []
            for temporal in range(rng.randint(1, 5)):
                objective = rng.uniform(0.0, 20.0)
                candidates.append(
                    _candidate(
                        spatial,
                        temporal,
                        rng.uniform(0.0, objective),
                        objective,
                        feasible=rng.random() > 0.25,
                    )
                )
            candidates_by_spatial.append(tuple(candidates))

        branches = tuple(
            SpatialHomotopyBranch(
                (spatial,),
                min(candidate.lower_bound for candidate in candidates),
                lambda candidates=candidates: candidates,
            )
            for spatial, candidates in enumerate(candidates_by_spatial)
        )
        feasible = [
            candidate
            for candidate in itertools.chain.from_iterable(candidates_by_spatial)
            if candidate.payload.feasible
        ]
        result = bounded_lazy_joint_search(branches, _evaluate)

        if not feasible:
            assert result.status == "infeasible"
            assert result.incumbent is None
        else:
            expected = min(
                feasible,
                key=lambda candidate: (candidate.payload.objective, candidate.label),
            )
            assert result.status == "optimal"
            assert result.incumbent is not None
            assert result.incumbent.label == expected.label
            assert result.upper_bound == pytest.approx(expected.payload.objective)
            assert result.absolute_gap == pytest.approx(0.0)


def test_invalid_lower_bound_fails_closed():
    branch = SpatialHomotopyBranch(
        (0,), 2.0, lambda: (_candidate(0, 0, 1.0, 3.0),)
    )
    with pytest.raises(ValueError, match="below its parent"):
        bounded_lazy_joint_search((branch,), _evaluate)

    branch = SpatialHomotopyBranch(
        (0,), 0.0, lambda: (_candidate(0, 0, 2.0, 1.0),)
    )
    with pytest.raises(ValueError, match="violates candidate"):
        bounded_lazy_joint_search((branch,), _evaluate)


def test_sample_points_alone_do_not_imply_continuous_safety():
    # The centers are separated at both endpoints but cross between them.
    samples = (
        AxisAlignedMotionSample(0.0, -1.5, 0.0, 0.5, 0.5),
        AxisAlignedMotionSample(1.0, 1.5, 0.0, 0.5, 0.5),
    )

    certificate = certify_sampled_axis_aligned_motion(
        samples,
        relative_longitudinal_speed_bound=3.0,
        relative_lateral_speed_bound=0.0,
    )

    assert not certificate.certified
    assert certificate.failed_interval == 0


def test_lipschitz_inflation_certifies_inter_sample_separation():
    samples = (
        AxisAlignedMotionSample(0.0, 5.0, 0.0, 1.0, 1.0),
        AxisAlignedMotionSample(0.2, 4.9, 0.0, 1.0, 1.0),
        AxisAlignedMotionSample(0.5, 4.7, 0.0, 1.0, 1.0),
    )

    certificate = certify_sampled_axis_aligned_motion(
        samples,
        relative_longitudinal_speed_bound=1.0,
        relative_lateral_speed_bound=0.5,
    )

    assert certificate.certified
    assert certificate.failed_interval is None
    assert certificate.maximum_longitudinal_guard == pytest.approx(0.3)
    assert certificate.maximum_lateral_guard == pytest.approx(0.15)

    swept = validate_candidate_continuous_safety(
        samples,
        relative_longitudinal_speed_bound=1.0,
        relative_lateral_speed_bound=0.5,
    )
    assert swept.certified
    assert swept.failed_interval is None


def test_continuous_certificate_rejects_invalid_sampling_contract():
    duplicate_times = (
        AxisAlignedMotionSample(0.0, 5.0, 0.0, 1.0, 1.0),
        AxisAlignedMotionSample(0.0, 5.0, 0.0, 1.0, 1.0),
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        certify_sampled_axis_aligned_motion(
            duplicate_times,
            relative_longitudinal_speed_bound=1.0,
            relative_lateral_speed_bound=1.0,
        )


def test_piecewise_linear_validator_detects_inter_sample_crossing():
    samples = (
        AxisAlignedMotionSample(0.0, -1.5, 0.0, 0.5, 0.5),
        AxisAlignedMotionSample(1.0, 1.5, 0.0, 0.5, 0.5),
    )

    result = validate_candidate_continuous_safety(
        samples,
        relative_longitudinal_speed_bound=3.0,
        relative_lateral_speed_bound=0.0,
    )

    assert not result.certified
    assert result.failed_interval == 0


def test_piecewise_linear_validator_accepts_axis_separated_sweep():
    samples = (
        AxisAlignedMotionSample(0.0, -1.5, 2.0, 0.5, 0.5),
        AxisAlignedMotionSample(1.0, 1.5, 2.0, 0.5, 0.5),
    )

    result = validate_candidate_continuous_safety(
        samples,
        relative_longitudinal_speed_bound=3.0,
        relative_lateral_speed_bound=0.0,
    )

    assert result.certified


def test_constant_acceleration_validator_detects_between_knot_crossing():
    samples = (
        AxisAlignedMotionSample(0.0, -2.0, 0.0, 0.5, 0.5, 0.0, 8.0),
        AxisAlignedMotionSample(1.0, 2.0, 0.0, 0.5, 0.5),
    )
    result = validate_candidate_constant_acceleration_safety(
        samples,
        relative_longitudinal_speed_bound=4.0,
        relative_lateral_speed_bound=0.0,
    )
    assert not result.certified
    assert result.failed_interval == 0


def test_constant_acceleration_validator_accepts_lateral_separation():
    samples = (
        AxisAlignedMotionSample(0.0, -2.0, 2.0, 0.5, 0.5, 0.0, 8.0),
        AxisAlignedMotionSample(1.0, 2.0, 2.0, 0.5, 0.5),
    )
    result = validate_candidate_constant_acceleration_safety(
        samples,
        relative_longitudinal_speed_bound=4.0,
        relative_lateral_speed_bound=0.0,
    )
    assert result.certified
