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


@dataclass(frozen=True)
class MethodSpec:
    key: str
    label: str
    flags: AblationFlags
    iterative: bool = False
    max_iterations: int = 1


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
        # Corrected safe-window injection (C5) is retained for ablation only:
        # it had no independent benefit and caused a repeatable P2 regression.
        AblationFlags(True, True, True, True, False, "MIKU"),
    ),
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


def run_method(spec: MethodSpec, scn: Scenario, convergence_s: float = 0.05) -> MethodRun:
    """Run one method and measure the complete planning call(s), not QP only."""
    start = time.perf_counter()
    result = run_pipeline(spec.flags, scn)
    iterations = 1
    converged = not spec.iterative

    if spec.iterative:
        probe_s = np.linspace(scn.ego.s0, scn.s_max, 64)
        previous_tau = np.array([arrival_time(float(s), scn) for s in probe_s])
        for iteration in range(2, spec.max_iterations + 1):
            tau_fn = _trajectory_tau(result, scn)
            updated_tau = np.array([tau_fn(float(s)) for s in probe_s])
            result = run_pipeline(spec.flags, scn, tau_fn=tau_fn)
            iterations = iteration
            if float(np.max(np.abs(updated_tau - previous_tau))) <= convergence_s:
                converged = True
                break
            previous_tau = updated_tau

    runtime_ms = (time.perf_counter() - start) * 1000.0
    return MethodRun(spec, result, runtime_ms, iterations, converged)


def method_by_key(key: str) -> MethodSpec:
    for method in METHODS:
        if method.key == key:
            return method
    raise KeyError(key)
