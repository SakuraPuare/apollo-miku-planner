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
    checks = {
        "novelty_audit": (ROOT / "NOVELTY_AUDIT.md").exists(),
        "related_work_matrix": (ROOT / "RELATED_WORK_MATRIX.md").exists(),
        "claim_traceability": (ROOT / "CLAIM_TRACEABILITY.md").exists(),
        "standardized_external_source": (generated / "commonroad_native_audit.json").exists(),
        "commonroad_full_benchmark": False,
        "faithful_external_competitor": False,
        "native_apollo_cyberrt": False,
        "reviewers_clear_of_fatal_issues": False,
        "main_joint_domain_nontrivial": main_nontrivial > 0,
        "stress_domain_nontrivial": stress_nontrivial,
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
