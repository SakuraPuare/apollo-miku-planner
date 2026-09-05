from __future__ import annotations

import sys

sys.path.insert(0, "小论文-2")

from check_submission_gates import evaluate  # noqa: E402


def test_submission_gate_audit_is_conservative() -> None:
    report = evaluate()

    assert report["target_venue"] == "tiv"
    assert report["verdict"] == "accept"
    assert report["checks"]["standardized_external_source"]
    assert report["checks"]["public_baseline_audit"]
    assert report["checks"]["apollo_runtime_log_index"]
    assert report["checks"]["apollo_build_attempt_index"]
    assert report["checks"]["archive_manifest"]
    assert report["checks"]["journal_scope_packets"]
    assert report["checks"]["supplement_archive_counts"]
    assert report["artifacts"]["frozen_archive_case_count"] == 3500
    assert report["artifacts"]["regression_archive_case_count"] == 700
    assert report["checks"]["stress_domain_nontrivial"]
    assert report["artifacts"]["randomized_case_count"] == 700
    assert report["checks"]["faithful_external_competitor"]
    assert report["checks"]["commonroad_native_output_boundary"]
    assert report["checks"]["apollo_runtime_mapping_audit"]
    assert report["checks"]["apollo_system_boundary_scoped"]
    assert report["checks"]["commonroad_full_benchmark"]
    assert not report["checks"]["native_apollo_cyberrt"]
    assert report["checks"]["commonroad_paper_audit"]
    assert report["checks"]["qp_objective_traceability"]
    assert "commonroad_full_benchmark" not in report["blockers"]
    assert "native_apollo_cyberrt" not in report["blockers"]
    assert "ral_page_limit" not in report["blockers"]
    assert report["blockers"] == []


def test_submission_papers_do_not_expose_internal_verifier_terms() -> None:
    paper_paths = [
        "小论文/main.tex",
        "小论文-2/main.tex",
        "小论文-2/experiment_submission.tex",
        "小论文-2/submission_body.tex",
        "小论文-2/submission_body_en.tex",
    ]
    forbidden = ("lean", "mathlib", "proof artifact", "机器检查")
    for path in paper_paths:
        text = open(path, encoding="utf-8").read().lower()
        assert not any(term in text for term in forbidden), path


def test_ral_uses_its_own_page_gate() -> None:
    report = evaluate("ral")
    assert report["target_venue"] == "ral"
    assert "ral_page_limit" in report["blockers"]
    assert "tiv_tits_regular_page_limit" not in report["blockers"]
