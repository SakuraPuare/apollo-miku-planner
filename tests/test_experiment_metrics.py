from __future__ import annotations

import numpy as np

from experiment_metrics import bootstrap_paired_difference


def test_paired_statistics_are_deterministic_and_directional():
    candidate = np.array([2.0, 3.0, 4.0, 6.0])
    reference = np.array([1.0, 2.0, 3.0, 4.0])
    first = bootstrap_paired_difference(candidate, reference, seed=5, samples=1000)
    second = bootstrap_paired_difference(candidate, reference, seed=5, samples=1000)
    assert first == second
    assert first["n"] == 4
    assert first["ci_low"] > 0.0
    assert first["mean_difference"] == 1.25


def test_paired_statistics_drop_only_nonfinite_pairs():
    result = bootstrap_paired_difference(
        np.array([1.0, np.nan, 3.0]), np.array([0.0, 1.0, np.inf]), seed=1
    )
    assert result["n"] == 1
    assert result["mean_difference"] == 1.0
