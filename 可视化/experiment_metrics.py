"""Truth-based trajectory metrics and paired statistics for MIKU experiments."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from apollo_pipeline import Obstacle, Scenario
from experiment_cases import RandomCase
from experiment_methods import MethodRun
from joint_homotopy_search import AxisAlignedMotionSample, validate_candidate_continuous_safety


RAW_SCHEMA_VERSION = "miku-random-v2"
COLLISION_TOLERANCE_M = 1e-3


@dataclass(frozen=True)
class Trajectory:
    time_s: np.ndarray
    longitudinal_m: np.ndarray
    lateral_m: np.ndarray
    speed_mps: np.ndarray
    acceleration_mps2: np.ndarray
    fallback_stop: bool


def _fallback_trajectory(scn: Scenario, ts: np.ndarray) -> Trajectory:
    """Declared emergency fallback: straight-line braking at 4 m/s^2."""
    stop_time = scn.ego.v0 / 4.0
    moving_t = np.minimum(ts, stop_time)
    s = scn.ego.s0 + scn.ego.v0 * moving_t - 2.0 * moving_t**2
    v = np.maximum(scn.ego.v0 - 4.0 * ts, 0.0)
    a = np.where(ts < stop_time, -4.0, 0.0)
    lateral = np.full_like(ts, scn.ego.l0)
    return Trajectory(ts, s, lateral, v, a, True)


def trajectory_from_run(run: MethodRun, scn: Scenario) -> Trajectory:
    result = run.result
    ts = np.asarray(result["ts"], dtype=float)
    if result.get("s_qp") is None:
        return _fallback_trajectory(scn, ts)
    s = np.asarray(result["s_qp"], dtype=float)
    v = np.asarray(result["v_qp"], dtype=float)
    a = np.asarray(result["a_qp"], dtype=float)
    if result.get("l_qp") is not None:
        lateral = np.asarray(result["l_qp"], dtype=float)
    else:
        lateral = np.interp(s, result["s_arr"], result["l_path"])
    return Trajectory(ts, s, lateral, v, a, False)


def _signed_clearance(
    ego_s: float,
    ego_l: float,
    ego_length: float,
    ego_width: float,
    obs_s: float,
    obs_l: float,
    obs: Obstacle,
) -> float:
    ds = abs(ego_s - obs_s) - (ego_length + obs.L) / 2.0
    dl = abs(ego_l - obs_l) - (ego_width + obs.W) / 2.0
    if ds <= 0.0 and dl <= 0.0:
        return -min(-ds, -dl)
    return float(np.hypot(max(ds, 0.0), max(dl, 0.0)))


def _safety_metrics(trajectory: Trajectory, truth: Scenario) -> tuple[float, float, int, int]:
    min_clearance = float("inf")
    min_ttc = float("inf")
    collision = 0
    window_entries = 0
    active_dynamic: set[int] = set()

    for index, t in enumerate(trajectory.time_s):
        current_dynamic: set[int] = set()
        for obs_index, obs in enumerate(truth.obstacles):
            obs_s, obs_l = obs.position_at(float(t))
            clearance = _signed_clearance(
                float(trajectory.longitudinal_m[index]),
                float(trajectory.lateral_m[index]),
                truth.ego.L,
                truth.ego.W,
                obs_s,
                obs_l,
                obs,
            )
            min_clearance = min(min_clearance, clearance)
            if clearance < -COLLISION_TOLERANCE_M:
                collision = 1
                if not obs.is_static:
                    current_dynamic.add(obs_index)

            lateral_gap = abs(float(trajectory.lateral_m[index]) - obs_l) - (
                truth.ego.W + obs.W
            ) / 2.0
            if lateral_gap > 0.0:
                continue
            relative_s = obs_s - float(trajectory.longitudinal_m[index])
            longitudinal_gap = abs(relative_s) - (truth.ego.L + obs.L) / 2.0
            if longitudinal_gap <= 0.0:
                min_ttc = 0.0
                continue
            closing_speed = (
                float(trajectory.speed_mps[index]) - obs.vs
                if relative_s >= 0.0
                else obs.vs - float(trajectory.speed_mps[index])
            )
            if closing_speed > 1e-3:
                min_ttc = min(min_ttc, longitudinal_gap / closing_speed)

        window_entries += len(current_dynamic - active_dynamic)
        active_dynamic = current_dynamic

    # Sample-wise checks above remain useful for TTC and event counts.  The
    # collision flag additionally uses a piecewise-linear swept-rectangle
    # check so an overlap between two QP samples cannot be missed.
    maximum_ego_speed = float(np.max(np.abs(trajectory.speed_mps)))
    for obs in truth.obstacles:
        samples = []
        for index, t in enumerate(trajectory.time_s):
            obs_s, obs_l = obs.position_at(float(t))
            samples.append(
                AxisAlignedMotionSample(
                    float(t),
                    float(trajectory.longitudinal_m[index] - obs_s),
                    float(trajectory.lateral_m[index] - obs_l),
                    (truth.ego.L + obs.L) / 2.0,
                    (truth.ego.W + obs.W) / 2.0,
                )
            )
        certificate = validate_candidate_continuous_safety(
            samples,
            relative_longitudinal_speed_bound=maximum_ego_speed + abs(obs.vs),
            relative_lateral_speed_bound=maximum_ego_speed + abs(obs.vl),
        )
        if not certificate.certified:
            collision = 1

    return min_clearance, min_ttc, collision, window_entries


def evaluate_run(run: MethodRun, case: RandomCase) -> dict[str, object]:
    planning = case.planning_scenario
    trajectory = trajectory_from_run(run, planning)
    min_clearance, min_ttc, collision, window_violations = _safety_metrics(
        trajectory, case.truth_scenario
    )

    target = case.truth_scenario.s_max - 1.0
    reached_indices = np.flatnonzero(trajectory.longitudinal_m >= target - 1e-3)
    reached = int(len(reached_indices) > 0)
    arrival_time_s = (
        float(trajectory.time_s[int(reached_indices[0])])
        if reached_indices.size
        else None
    )
    end_index = (
        int(reached_indices[0]) if reached_indices.size else len(trajectory.time_s) - 1
    )
    ds = np.diff(trajectory.longitudinal_m[: end_index + 1])
    dl = np.diff(trajectory.lateral_m[: end_index + 1])
    path_length = float(np.sum(np.hypot(ds, dl))) if len(ds) else 0.0
    duration = max(
        float(trajectory.time_s[end_index] - trajectory.time_s[0]), 1e-9
    )
    average_speed = path_length / duration
    jerk = np.diff(trajectory.acceleration_mps2) / np.diff(trajectory.time_s)
    jerk_rms = float(np.sqrt(np.mean(jerk**2))) if len(jerk) else 0.0

    a_y = run.result.get("a_y")
    if a_y is None or trajectory.fallback_stop:
        max_lateral_acceleration = 0.0
    else:
        max_lateral_acceleration = float(np.max(np.abs(a_y[: end_index + 1])))

    progress_ratio = float(
        np.clip(
            (trajectory.longitudinal_m[-1] - case.truth_scenario.ego.s0)
            / max(target - case.truth_scenario.ego.s0, 1e-9),
            0.0,
            1.0,
        )
    )
    degraded_stop = int(trajectory.fallback_stop or not reached)
    success = int(reached and not collision)
    penalized_travel_time = (
        arrival_time_s
        if success and arrival_time_s is not None
        else float(case.truth_scenario.t_max + 5.0)
    )

    return {
        "schema_version": RAW_SCHEMA_VERSION,
        "case_kind": case.kind,
        "seed": case.seed,
        "method": run.method.key,
        "method_label": run.method.label,
        "success": success,
        "reached": reached,
        "collision": collision,
        "min_clearance_m": float(min_clearance),
        "min_ttc_s": None if not np.isfinite(min_ttc) else float(min_ttc),
        "arrival_time_s": arrival_time_s,
        "penalized_travel_time_s": penalized_travel_time,
        "progress_ratio": progress_ratio,
        "average_speed_mps": average_speed,
        "path_length_m": path_length,
        "max_longitudinal_acceleration_mps2": float(
            np.max(np.abs(trajectory.acceleration_mps2))
        ),
        "max_lateral_acceleration_mps2": max_lateral_acceleration,
        "jerk_rms_mps3": jerk_rms,
        "time_window_violations": window_violations,
        "degraded_stop": degraded_stop,
        "runtime_ms": run.runtime_ms,
        "iterations": run.iterations,
        "iterative_converged": int(run.converged),
    }


def bootstrap_paired_difference(
    candidate: np.ndarray,
    reference: np.ndarray,
    seed: int,
    samples: int = 5000,
) -> dict[str, float | int]:
    """Candidate-reference mean difference, percentile CI, and paired Cohen dz."""
    if candidate.shape != reference.shape:
        raise ValueError("paired arrays must have equal shapes")
    valid = np.isfinite(candidate) & np.isfinite(reference)
    differences = candidate[valid] - reference[valid]
    if len(differences) == 0:
        return {"n": 0, "mean_difference": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "cohen_dz": float("nan")}
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(differences), size=(samples, len(differences)))
    bootstrap_means = differences[indices].mean(axis=1)
    standard_deviation = float(np.std(differences, ddof=1)) if len(differences) > 1 else 0.0
    mean_difference = float(np.mean(differences))
    effect = mean_difference / standard_deviation if standard_deviation > 0.0 else 0.0
    return {
        "n": int(len(differences)),
        "mean_difference": mean_difference,
        "ci_low": float(np.quantile(bootstrap_means, 0.025)),
        "ci_high": float(np.quantile(bootstrap_means, 0.975)),
        "cohen_dz": effect,
    }


def exact_mcnemar(candidate: np.ndarray, reference: np.ndarray) -> dict[str, float | int]:
    """Two-sided exact McNemar test for paired binary outcomes."""

    if candidate.shape != reference.shape:
        raise ValueError("paired arrays must have equal shapes")
    candidate = np.asarray(candidate)
    reference = np.asarray(reference)
    valid = np.isfinite(candidate) & np.isfinite(reference)
    candidate = candidate[valid]
    reference = reference[valid]
    if not np.all(np.isin(candidate, (0, 1))) or not np.all(np.isin(reference, (0, 1))):
        raise ValueError("McNemar inputs must be binary")
    candidate = candidate.astype(int)
    reference = reference.astype(int)

    candidate_only = int(np.sum((candidate == 1) & (reference == 0)))
    reference_only = int(np.sum((candidate == 0) & (reference == 1)))
    discordant = candidate_only + reference_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant, index)
            for index in range(min(candidate_only, reference_only) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2.0 * tail)
    return {
        "candidate_only": candidate_only,
        "reference_only": reference_only,
        "discordant": discordant,
        "mcnemar_exact_p": float(p_value),
    }
