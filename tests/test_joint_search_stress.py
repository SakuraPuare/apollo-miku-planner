from __future__ import annotations

from dataclasses import replace

import pytest

from experiment_methods import (
    corridor_lateral_lower_bound,
    method_by_key,
    run_method,
)
from run_joint_search_stress import build_stress_scenario


def test_corridor_lateral_lower_bound_is_zero_only_when_centerline_is_reachable() -> None:
    assert corridor_lateral_lower_bound(
        {"l_min": [-2.0, -0.5], "l_max": [1.0, 0.5]}, 2.0
    ) == pytest.approx(0.0)
    assert corridor_lateral_lower_bound(
        {"l_min": [1.0, -3.0], "l_max": [2.0, -2.0]}, 2.0
    ) == pytest.approx(5.0)


def test_corridor_lateral_lower_bound_rejects_invalid_weight() -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        corridor_lateral_lower_bound({"l_min": [1.0], "l_max": [2.0]}, -1.0)


def test_stress_scenario_exercises_nontrivial_joint_domain() -> None:
    method = replace(
        method_by_key("MIKU"),
        iterative=False,
        refine_on_demand=False,
        certificate_lateral_weight=1.0,
    )
    run = run_method(method, build_stress_scenario(2))
    certificate = run.result["joint_search_certificate"]

    assert run.result["spatial_homotopy_candidate_count"] == 4
    assert certificate["domain_size"] >= 5
    assert certificate["evaluated_candidates"] < certificate["domain_size"]
    assert certificate["expanded_spatial_branches"] < 4
    assert certificate["status"] == "optimal"
    assert certificate["absolute_gap"] == 0.0
