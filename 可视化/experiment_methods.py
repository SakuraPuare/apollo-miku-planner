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

from apollo_pipeline import AblationFlags, Scenario, arrival_time, run_pipeline
from joint_reference import run_joint_reference


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


@dataclass
class MethodRun:
    method: MethodSpec
    result: dict
    runtime_ms: float
    iterations: int
    converged: bool


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
    if spec.solver == "joint_grid":
        result = run_joint_reference(scn)
    elif spec.solver == "pipeline":
        result = run_pipeline(
            spec.flags,
            scn,
            preferred_homotopy=preferred_homotopy,
        )
    else:
        raise ValueError(f"unknown method solver: {spec.solver}")
    if spec.solver == "pipeline" and result.get("s_qp") is None:
        # Validate the Cartesian product lazily: temporal alternatives on the
        # best spatial class first, then the remaining spatial classes.  Stop
        # as soon as a convex QP certifies feasibility.
        spatial_count = max(
            1,
            min(
                spec.spatial_top_k,
                int(result.get("spatial_homotopy_candidate_count", 0)),
            ),
        )
        for spatial_rank in range(spatial_count):
            spatial_result = result
            if spatial_rank > 0:
                spatial_result = run_pipeline(
                    spec.flags,
                    scn,
                    preferred_homotopy=preferred_homotopy,
                    candidate_rank=spatial_rank,
                    temporal_plan_rank=0,
                )
                if spatial_result.get("s_qp") is not None:
                    result = spatial_result
                    break
            temporal_count = max(
                1,
                min(
                    spec.temporal_top_k,
                    int(spatial_result.get("temporal_homotopy_candidate_count", 0)),
                ),
            )
            for temporal_rank in range(1, temporal_count):
                temporal_result = run_pipeline(
                    spec.flags,
                    scn,
                    preferred_homotopy=preferred_homotopy,
                    candidate_rank=spatial_rank,
                    temporal_plan_rank=temporal_rank,
                )
                if temporal_result.get("s_qp") is not None:
                    result = temporal_result
                    break
            if result.get("s_qp") is not None:
                break
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

            result = run_pipeline(
                spec.flags,
                scn,
                tau_fn=damped_tau,
                preferred_homotopy=preferred_homotopy,
            )
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
