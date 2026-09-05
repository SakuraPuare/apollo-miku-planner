"""Audit the submission gates without turning missing evidence into a pass."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parent


def _page_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        result = subprocess.run(
            ["pdfinfo", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def evaluate() -> dict[str, object]:
    generated = ROOT / "generated"
    main_pages = _page_count(ROOT / "main.pdf")
    ieee_pages = _page_count(ROOT / "main_ieee.pdf")
    stress = json.loads(
        (generated / "joint_search_stress_results.json").read_text(encoding="utf-8")
    )
    randomized = json.loads(
        (generated / "randomized_results.json").read_text(encoding="utf-8")
    )
    stress_rows = stress["summary"]
    stress_nontrivial = any(
        int(row["domain_size"]) > 1 for row in stress_rows
    )
    randomized_raw = (generated / "randomized_raw.csv").read_text(encoding="utf-8")
    main_nontrivial = sum(
        int(match.group(1)) > 1
        for match in re.finditer(r"(?:^|,)optimal,(\d+),", randomized_raw, re.MULTILINE)
    )
    apollo_manifest = ROOT.parent / "apollo_evidence_manifest.json"
    fixture_manifest = ROOT.parent / "apollo_fixture_manifest.json"
    commonroad_report = generated / "commonroad_reactive_results.json"
    commonroad_native_report = generated / "commonroad_miku_native_results.json"
    frozen_archive_report = ROOT.parent / "submission_artifacts" / "frozen_3500" / "小论文-2" / "generated" / "randomized_results.json"
    regression_archive_report = ROOT.parent / "submission_artifacts" / "regression_700" / "randomized_results.json"
    commonroad_macros = generated / "commonroad_macros.tex"
    english_body = ROOT / "submission_body_en.tex"
    chinese_body = ROOT / "experiment_submission.tex"
    apollo_evidence_present = False
    if apollo_manifest.exists() and fixture_manifest.exists():
        try:
            apollo_data = json.loads(apollo_manifest.read_text(encoding="utf-8"))
            fixture_data = json.loads(fixture_manifest.read_text(encoding="utf-8"))
            apollo_evidence_present = (
                apollo_data.get("apollo_source", {}).get("commit")
                and apollo_data.get("runtime_assets", {}).get("status") == "artifacts_present"
                and fixture_data.get("status", {}).get("fixture_paths_indexed") is True
                and apollo_data.get("runtime_assets", {}).get("verification_scope")
                == "replayed_and_mapped"
                and fixture_data.get("status", {}).get("exact_scenario_to_runtime_output_mapping")
                == "complete"
            )
        except (OSError, json.JSONDecodeError):
            apollo_evidence_present = False
    commonroad_data = {}
    commonroad_native_data = {}
    frozen_archive_data = {}
    regression_archive_data = {}
    try:
        commonroad_data = json.loads(commonroad_report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        commonroad_data = {}
    try:
        commonroad_native_data = json.loads(
            commonroad_native_report.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        commonroad_native_data = {}
    try:
        frozen_archive_data = json.loads(frozen_archive_report.read_text(encoding="utf-8"))
        regression_archive_data = json.loads(regression_archive_report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        frozen_archive_data = {}
        regression_archive_data = {}
    competitor_evidence_present = bool(
        commonroad_data.get("competitor") == "commonroad-reactive-planner"
        and commonroad_data.get("scenario_count", 0) >= 1
        and all("planned" in row for row in commonroad_data.get("rows", []))
    )
    checks = {
        "novelty_audit": (ROOT / "NOVELTY_AUDIT.md").exists(),
        "related_work_matrix": (ROOT / "RELATED_WORK_MATRIX.md").exists(),
        "claim_traceability": (ROOT / "CLAIM_TRACEABILITY.md").exists(),
        "public_baseline_audit": (
            (ROOT.parent / "小论文" / "PUBLIC_BASELINE_AUDIT.md").exists()
            and (ROOT.parent / "小论文" / "P1_METRICS_AUDIT.md").exists()
        ),
        "apollo_runtime_log_index": (
            (ROOT.parent / "小论文" / "APOLLO_RUNTIME_RUN_INDEX.md").exists()
            and "planning has no trajectory point"
            in (ROOT.parent / "小论文" / "APOLLO_RUNTIME_RUN_INDEX.md").read_text(
                encoding="utf-8"
            )
        ),
        "archive_manifest": (ROOT.parent / "小论文" / "EXPERIMENT_ARCHIVE_MANIFEST.json").exists(),
        "journal_scope_packets": (ROOT.parent / "小论文" / "SUBMISSION_SCOPE_PACKETS.md").exists(),
        "supplement_archive_counts": (
            frozen_archive_data.get("paired_case_count") == 3500
            and regression_archive_data.get("paired_case_count") == 700
        ),
        "standardized_external_source": (generated / "commonroad_native_audit.json").exists(),
        # A competitor-only run is not a MIKU CommonRoad benchmark.  The gate
        # remains closed until the native MIKU adapter preserves the declared
        # scenario semantics and shares the same evaluator/protocol.
        "commonroad_full_benchmark": (
            commonroad_data.get("formal_benchmark_ready") is True
            and commonroad_data.get("miku_native_benchmark") is True
        ),
        "faithful_external_competitor": competitor_evidence_present,
        "commonroad_native_output_boundary": (
            commonroad_native_data.get("native_solution_protocol") is True
            and len(commonroad_native_data.get("rows", [])) >= 1
            and all(
                row.get("native_commonroad_protocol") is True
                for row in commonroad_native_data.get("rows", [])
            )
        ),
        "commonroad_paper_audit": (
            commonroad_macros.exists()
            and "External CommonRoad Audit" in english_body.read_text(encoding="utf-8")
            and "外部 CommonRoad 审计" in chinese_body.read_text(encoding="utf-8")
        ),
        "qp_objective_traceability": (
            "pipeline_objective" in (ROOT.parent / "可视化" / "apollo_pipeline.py").read_text(encoding="utf-8")
            and "eq:qp-objective" in english_body.read_text(encoding="utf-8")
        ),
        "native_apollo_cyberrt": bool(apollo_evidence_present),
        "reviewers_clear_of_fatal_issues": False,
        "main_joint_domain_nontrivial": main_nontrivial > 0,
        "stress_domain_nontrivial": stress_nontrivial,
        "tiv_tits_regular_page_limit": ieee_pages is not None and ieee_pages <= 10,
        "ral_page_limit": ieee_pages is not None and ieee_pages <= 6,
    }
    blockers = [
        name
        for name, passed in checks.items()
        if not passed
    ]
    verdict = "accept" if not blockers else "major_revision"
    return {
        "verdict": verdict,
        "checks": checks,
        "blockers": blockers,
        "artifacts": {
            "main_pages": main_pages,
            "main_ieee_pages": ieee_pages,
            "stress_max_domain": max(int(row["domain_size"]) for row in stress_rows),
            "main_nontrivial_optimal_rows": main_nontrivial,
            "randomized_case_count": randomized.get("paired_case_count"),
            "apollo_source_commit": (
                json.loads(apollo_manifest.read_text(encoding="utf-8"))
                .get("apollo_source", {})
                .get("commit")
                if apollo_manifest.exists()
                else None
            ),
            "commonroad_scenario_count": commonroad_data.get("scenario_count"),
            "commonroad_valid_solution_count": commonroad_data.get("valid_solution_count"),
            "commonroad_miku_native_valid_solution_count": commonroad_native_data.get(
                "miku_valid_solution_count"
            ),
            "frozen_archive_case_count": frozen_archive_data.get("paired_case_count"),
            "regression_archive_case_count": regression_archive_data.get("paired_case_count"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = evaluate()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.strict and report["verdict"] != "accept":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
