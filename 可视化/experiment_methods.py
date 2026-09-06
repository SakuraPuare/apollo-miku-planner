"""Fair method registry for deterministic and randomized MIKU experiments.

Every method receives the same :class:`Scenario` object and uses the same path
and speed optimizers from ``apollo_pipeline``.  The only differences are the
documented coordination policy and, for B2, repeated arrival-time updates.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import numpy as np

from apollo_pipeline import (
    AblationFlags,
    PATH_W_L,
    Scenario,
    arrival_time,
    path_qp_objective,
    pipeline_objective,
    run_pipeline,
    validate_pipeline_candidate_continuous_safety,
)
from joint_reference import run_joint_reference
from joint_homotopy_search import (
    CandidateEvaluation,
    JointHomotopyCandidate,
    SpatialHomotopyBranch,
    bounded_lazy_joint_search,
)


@dataclass(frozen=True)
class MethodSpec:
    key: str
    label: str
    flags: AblationFlags
    iterative: bool = False
    max_iterations: int = 1
    solver: str = "pipeline"
    damping: float = 1.0
    refine_on_demand: bool = False
    temporal_top_k: int = 1
    spatial_top_k: int = 1
    require_continuous_certificate: bool = False
    certified_joint_search: bool = False
    # Retained as a diagnostic knob for stress fixtures, but the production
    # certificate always uses PATH_W_L so its lower bound is admissible for
    # the actual path/speed QP objective.
    certificate_lateral_weight: float = PATH_W_L


@dataclass
class MethodRun:
    method: MethodSpec
    result: dict
    runtime_ms: float
    iterations: int
    converged: bool


def corridor_lateral_lower_bound(candidate: dict, weight: float) -> float:
    """Return the admissible lateral-cost lower bound for one corridor."""
    weight = float(weight)
    if not np.isfinite(weight) or weight < 0.0:
        raise ValueError("certificate lateral weight must be finite and non-negative")
    lower = np.asarray(candidate.get("l_min"), dtype=float)
    upper = np.asarray(candidate.get("l_max"), dtype=float)
    if lower.shape != upper.shape or lower.ndim != 1 or len(lower) == 0:
        return 0.0
    nearest = np.where(
        (lower <= 0.0) & (upper >= 0.0),
        0.0,
        np.minimum(np.abs(lower), np.abs(upper)),
    )
    # path_optimizer uses PATH_W_L * sum(l_j^2) (the solver's objective is
    # represented up to the same fixed discretisation).  Keep the lower bound
    # in that exact scale rather than silently normalising by grid length.
    return float(weight * np.sum(nearest**2))


METHODS: tuple[MethodSpec, ...] = (
    MethodSpec("B0", "B0-TimeBlind", AblationFlags.baseline()),
    MethodSpec(
        "B1",
        "B1-TimeAwareGreedy",
        AblationFlags(True, False, False, False, False, "B1_time_aware_greedy"),
    ),
    MethodSpec(
        "B2",
        "B2-IterativePVD",
        AblationFlags(True, False, False, False, False, "B2_iterative_pvd"),
        iterative=True,
        max_iterations=3,
    ),
    MethodSpec(
        "MIKU",
        "MIKU",
        AblationFlags(True, True, True, True, True, "MIKU", True),
        iterative=True,
        max_iterations=2,
        damping=0.7,
        refine_on_demand=True,
        temporal_top_k=3,
        spatial_top_k=3,
        require_continuous_certificate=True,
        certified_joint_search=True,
    ),
)

JOINT_REFERENCE = MethodSpec(
    "B3",
    "B3-JointReference",
    AblationFlags.baseline(),
    solver="joint_grid",
)


def _trajectory_tau(result: dict, scn: Scenario) -> Callable[[float], float]:
    """Construct first-arrival ``tau(s)`` from the preceding speed solution."""
    s_qp = result.get("s_qp")
    ts = result.get("ts")
    v_qp = result.get("v_qp")
    if s_qp is None or ts is None or len(s_qp) < 2:
        return lambda s: arrival_time(s, scn)

    monotone_s = np.maximum.accumulate(np.asarray(s_qp, dtype=float))
    unique_s, first_indices = np.unique(monotone_s, return_index=True)
    unique_t = np.asarray(ts, dtype=float)[first_indices]
    last_s = float(unique_s[-1])
    last_t = float(unique_t[-1])
    last_v = float(v_qp[-1]) if v_qp is not None else 0.0
    extrapolation_speed = max(last_v, 0.5)

    def tau(s: float) -> float:
        if s <= unique_s[0]:
            return float(unique_t[0])
        if s <= last_s:
            return float(np.interp(s, unique_s, unique_t))
        return last_t + (s - last_s) / extrapolation_speed

    return tau


def run_method(
    spec: MethodSpec,
    scn: Scenario,
    convergence_s: float = 0.05,
    preferred_homotopy: dict[str, str] | None = None,
) -> MethodRun:
    """Run one method and measure the complete planning call(s), not QP only."""
    start = time.perf_counter()

    def candidate_is_acceptable(candidate: dict) -> bool:
        if candidate.get("s_qp") is None:
            return False
        if not spec.require_continuous_certificate:
            return True
        try:
            certificates = validate_pipeline_candidate_continuous_safety(
                scn, candidate, robust_prediction=spec.flags.robust_prediction
            )
        except (KeyError, ValueError):
            return False
        candidate["continuous_safety_certificates"] = certificates
        return all(certificate.certified for certificate in certificates.values())

    def plan_pipeline_once(
        tau_fn: Callable[[float], float] | None = None,
    ) -> dict:
        common = dict(
            tau_fn=tau_fn,
            preferred_homotopy=preferred_homotopy,
        )
        if not spec.certified_joint_search:
            candidate = run_pipeline(spec.flags, scn, **common)
            if candidate_is_acceptable(candidate):
                return candidate
            spatial_count = max(
                1,
                min(spec.spatial_top_k, int(candidate.get("spatial_homotopy_candidate_count", 0))),
            )
            for spatial_rank in range(spatial_count):
                temporal_count = max(
                    1,
                    min(spec.temporal_top_k, int(candidate.get("temporal_homotopy_candidate_count", 0))),
                )
                for temporal_rank in range(temporal_count):
                    alternative = run_pipeline(
                        spec.flags,
                        scn,
                        candidate_rank=spatial_rank,
                        temporal_plan_rank=temporal_rank,
                        **common,
                    )
                    if candidate_is_acceptable(alternative):
                        return alternative
            failed = dict(candidate)
            failed["s_qp"] = failed["v_qp"] = failed["a_qp"] = None
            return failed

        cache: dict[tuple[int, int], dict] = {}

        def solve(spatial_rank: int, temporal_rank: int) -> dict:
            key = (spatial_rank, temporal_rank)
            if key not in cache:
                cache[key] = run_pipeline(
                    spec.flags,
                    scn,
                    candidate_rank=spatial_rank,
                    temporal_plan_rank=temporal_rank,
                    spatial_top_k=None,
                    temporal_beam_width=None,
                    **common,
                )
            return cache[key]

        seed = solve(0, 0)
        spatial_count = max(1, int(seed.get("spatial_homotopy_candidate_count", 0)))

        def make_branch(spatial_rank: int) -> SpatialHomotopyBranch[tuple[int, int]]:
            first = solve(spatial_rank, 0)
            # All temporal children reuse this spatial path.  The solved path
            # QP objective is therefore an admissible branch lower bound; all
            # speed-QP terms are non-negative.
            branch_lower_bound = path_qp_objective(first)

            def expand() -> tuple[JointHomotopyCandidate[tuple[int, int]], ...]:
                temporal_count = max(
                    1, int(first.get("temporal_homotopy_candidate_count", 0))
                )
                return tuple(
                    JointHomotopyCandidate(
                        (spatial_rank,),
                        (temporal_rank,),
                        branch_lower_bound,
                        (spatial_rank, temporal_rank),
                    )
                    for temporal_rank in range(temporal_count)
                )

            return SpatialHomotopyBranch((spatial_rank,), branch_lower_bound, expand)

        def evaluate(
            joint: JointHomotopyCandidate[tuple[int, int]],
        ) -> CandidateEvaluation[dict]:
            candidate = solve(*joint.payload)
            if not candidate_is_acceptable(candidate):
                return CandidateEvaluation(False)
            return CandidateEvaluation(True, pipeline_objective(scn, candidate), candidate)

        certificate = bounded_lazy_joint_search(
            (make_branch(rank) for rank in range(spatial_count)), evaluate
        )
        selected = certificate.solution
        if selected is None:
            selected = dict(seed)
            selected["s_qp"] = selected["v_qp"] = selected["a_qp"] = None
        else:
            selected = dict(selected)
        selected["joint_search_certificate"] = {
            "status": certificate.status,
            "lower_bound": certificate.lower_bound,
            "upper_bound": certificate.upper_bound,
            "absolute_gap": certificate.absolute_gap,
            "relative_gap": certificate.relative_gap,
            "evaluated_candidates": certificate.evaluated_candidates,
            "expanded_spatial_branches": certificate.expanded_spatial_branches,
            "remaining_queue_items": certificate.remaining_queue_items,
            # Count the finite labels explicitly for auditability.  ``solve``
            # is cached, so this does not re-run already materialised QPs.
            "domain_size": int(
                sum(
                    max(1, int(solve(rank, 0).get("temporal_homotopy_candidate_count", 0)))
                    for rank in range(spatial_count)
                )
            ),
            "domain": "finite enumerated spatial-temporal homotopy labels",
            "objective": "path_speed_qp_quadratic_cost_v1",
            "objective_definition": (
                "path and speed QP quadratic terms with the candidate terminal reference"
            ),
        }
        return selected

    if spec.solver == "joint_grid":
        result = run_joint_reference(scn)
    elif spec.solver == "pipeline":
        result = plan_pipeline_once()
    else:
        raise ValueError(f"unknown method solver: {spec.solver}")
    iterations = 1
    converged = not spec.iterative

    if spec.iterative:
        probe_s = np.linspace(scn.ego.s0, scn.s_max, 64)
        previous_tau = np.array([arrival_time(float(s), scn) for s in probe_s])
        target = max(scn.s_max - 1.0, scn.ego.s0)

        def planner_score(candidate: dict) -> tuple[int, int, int, float]:
            trajectory = candidate.get("s_qp")
            if trajectory is None:
                return (0, 0, 0, -float("inf"))
            progress = float(np.asarray(trajectory, dtype=float)[-1])
            reached = int(progress >= target - 1e-3)
            hard_goal = int(not candidate.get("terminal_goal_relaxed", False))
            return (1, reached, hard_goal, progress)

        best_result = result
        requires_refinement = (
            not spec.refine_on_demand
            or (
                planner_score(result)[1] == 0
                and any(not obstacle.is_static for obstacle in scn.obstacles)
                and not any(obstacle.is_static for obstacle in scn.obstacles)
            )
        )
        for iteration in range(2, spec.max_iterations + 1):
            if not requires_refinement:
                break
            tau_fn = _trajectory_tau(result, scn)
            raw_tau = np.array([tau_fn(float(s)) for s in probe_s])
            updated_tau = (
                spec.damping * raw_tau + (1.0 - spec.damping) * previous_tau
            )

            def damped_tau(s: float) -> float:
                return float(np.interp(s, probe_s, updated_tau))

            result = plan_pipeline_once(damped_tau)
            iterations = iteration
            if planner_score(result) > planner_score(best_result):
                best_result = result
            if float(np.max(np.abs(updated_tau - previous_tau))) <= convergence_s:
                converged = True
                break
            previous_tau = updated_tau
        result = best_result

    runtime_ms = (time.perf_counter() - start) * 1000.0
    return MethodRun(spec, result, runtime_ms, iterations, converged)


def method_by_key(key: str) -> MethodSpec:
    for method in (*METHODS, JOINT_REFERENCE):
        if method.key == key:
            return method
    raise KeyError(key)
