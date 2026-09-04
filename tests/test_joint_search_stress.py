from __future__ import annotations

from dataclasses import replace

from experiment_methods import method_by_key, run_method
from run_joint_search_stress import build_stress_scenario


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
