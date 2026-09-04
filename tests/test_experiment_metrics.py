from __future__ import annotations

import numpy as np
import pytest

from apollo_pipeline import Ego, Obstacle, Scenario
from experiment_metrics import Trajectory, _safety_metrics, exact_mcnemar


def test_exact_mcnemar_counts_discordant_pairs() -> None:
    candidate = np.array([1, 1, 1, 0, 0, 1])
    reference = np.array([0, 0, 1, 1, 0, 1])

    result = exact_mcnemar(candidate, reference)

    assert result["candidate_only"] == 2
    assert result["reference_only"] == 1
    assert result["discordant"] == 3
    assert result["mcnemar_exact_p"] == pytest.approx(1.0)


def test_exact_mcnemar_detects_one_sided_discordance() -> None:
    candidate = np.ones(10)
    reference = np.zeros(10)

    result = exact_mcnemar(candidate, reference)

    assert result["mcnemar_exact_p"] == pytest.approx(2.0 / 2**10)


def test_exact_mcnemar_rejects_non_binary_values() -> None:
    with pytest.raises(ValueError):
        exact_mcnemar(np.array([0.5]), np.array([0.0]))


def test_swept_collision_is_detected_between_trajectory_samples() -> None:
    truth = Scenario(
        Ego(s0=-2.0, l0=0.0, v0=4.0, L=1.0, W=1.0),
        [Obstacle(s0=0.0, l0=0.0, L=1.0, W=1.0, is_static=True)],
        s_max=3.0,
        t_max=1.0,
    )
    trajectory = Trajectory(
        time_s=np.array([0.0, 1.0]),
        longitudinal_m=np.array([-2.0, 2.0]),
        lateral_m=np.array([0.0, 0.0]),
        speed_mps=np.array([4.0, 4.0]),
        acceleration_mps2=np.array([0.0, 0.0]),
        fallback_stop=False,
    )

    _clearance, _ttc, collision, _entries = _safety_metrics(trajectory, truth)

    assert collision == 1
