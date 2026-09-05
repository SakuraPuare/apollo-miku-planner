from __future__ import annotations

import sys

sys.path.insert(0, "小论文-2")

from check_submission_gates import evaluate  # noqa: E402


def test_submission_gate_audit_is_conservative() -> None:
    report = evaluate()

    assert report["verdict"] == "major_revision"
    assert report["checks"]["standardized_external_source"]
    assert report["checks"]["public_baseline_audit"]
    assert report["checks"]["stress_domain_nontrivial"]
    assert report["artifacts"]["randomized_case_count"] == 700
    assert report["checks"]["faithful_external_competitor"]
    assert not report["checks"]["commonroad_full_benchmark"]
    assert not report["checks"]["native_apollo_cyberrt"]
    assert report["checks"]["commonroad_paper_audit"]
    assert report["checks"]["qp_objective_traceability"]
    assert "commonroad_full_benchmark" in report["blockers"]
    assert "native_apollo_cyberrt" in report["blockers"]
    assert "ral_page_limit" in report["blockers"]


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
