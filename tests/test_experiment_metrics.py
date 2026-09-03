from __future__ import annotations

import numpy as np
import pytest

from experiment_metrics import exact_mcnemar


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
