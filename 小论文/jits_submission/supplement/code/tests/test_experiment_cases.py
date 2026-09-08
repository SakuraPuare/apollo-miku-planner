from __future__ import annotations

from dataclasses import asdict

import pytest

from experiment_cases import CASE_KINDS, generate_case


@pytest.mark.parametrize("kind", CASE_KINDS)
def test_case_generation_is_reproducible(kind):
    first = generate_case(kind, 17)
    second = generate_case(kind, 17)
    assert asdict(first) == asdict(second)


def test_noise_case_separates_planning_input_from_truth():
    case = generate_case("prediction_noise", 3)
    planned = case.planning_scenario.obstacles[0]
    truth = case.truth_scenario.obstacles[0]
    assert (planned.s0, planned.l0, planned.vs, planned.vl) != (
        truth.s0,
        truth.l0,
        truth.vs,
        truth.vl,
    )


def test_invalid_case_request_is_rejected():
    with pytest.raises(KeyError):
        generate_case("unknown", 0)
    with pytest.raises(ValueError):
        generate_case(CASE_KINDS[0], -1)
