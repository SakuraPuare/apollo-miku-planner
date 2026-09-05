from __future__ import annotations

import sys

sys.path.insert(0, "小论文-2")

from check_submission_gates import evaluate  # noqa: E402


def test_submission_gate_audit_is_conservative() -> None:
    report = evaluate()

    assert report["verdict"] == "major_revision"
    assert report["checks"]["standardized_external_source"]
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
