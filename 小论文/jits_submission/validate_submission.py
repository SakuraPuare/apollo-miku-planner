#!/usr/bin/env python3
"""Run deterministic pre-upload checks for the MIKU JITS package."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "supplement" / "data" / "\u5c0f\u8bba\u6587-2" / "generated"
EXPECTED_JSON_SHA256 = (
    "10ba825b23967160c51a7710ac6fe985be9f8dba63bce89fc212f6e937df5034"
)


def run(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(actual: float, expected: float, tolerance: float = 1e-9) -> bool:
    return abs(actual - expected) <= tolerance


def main() -> int:
    errors: list[str] = []
    checks: list[str] = []

    required = [
        "manuscript.tex",
        "anonymous.tex",
        "manuscript.pdf",
        "anonymous.pdf",
        "interact.cls",
        "references.bib",
        "named_metadata.tex",
        "cover_letter.md",
        "submission_checklist.md",
        "package_submission.sh",
        "supplement/README.md",
        "supplement/metadata_corrections.md",
        "supplement/reproduce.sh",
        "supplement/SHA256SUMS",
        "supplement/code/pyproject.toml",
        "supplement/code/README.md",
        "supplement/code/tests/test_miku_geometry.py",
        "figures/evidence_dashboard.pdf",
        "figures/fig_teaser_en.pdf",
        "figures/fig_max_gap_en.pdf",
        "figures/fig_narrow_en.pdf",
        "figures/fig_framework_en.pdf",
        "figures/dreamview/scn01_during.png",
        "figures/dreamview/scn02_during.png",
        "figures/dreamview/scn03_during.png",
        "deliverables/MIKU_JITS_named.pdf",
        "deliverables/MIKU_JITS_anonymous.pdf",
        "deliverables/MIKU_JITS_named_submission.zip",
        "deliverables/MIKU_JITS_anonymous_submission.zip",
        "deliverables/MIKU_JITS_supplement.zip",
        "deliverables/SHA256SUMS",
    ]
    for relative in required:
        if (ROOT / relative).is_file():
            checks.append(f"present: {relative}")
        else:
            errors.append(f"missing required file: {relative}")

    result_json = DATA / "randomized_results.json"
    if result_json.is_file():
        actual_hash = sha256(result_json)
        if actual_hash == EXPECTED_JSON_SHA256:
            checks.append("frozen randomized_results.json hash matches commit 29a337a")
        else:
            errors.append(
                "frozen randomized_results.json hash mismatch: "
                f"{actual_hash} != {EXPECTED_JSON_SHA256}"
            )
        metadata = json.loads(result_json.read_text(encoding="utf-8"))
        if metadata.get("protocol") != "miku-random-v2":
            errors.append("main protocol is not miku-random-v2")
        if metadata.get("paired_case_count") != 3500:
            errors.append("main protocol does not contain 3,500 paired cases")
        if metadata.get("raw_row_count") != 14000:
            errors.append("main protocol does not contain 14,000 method rows")
        aggregates = {
            (row["case_kind"], row["method"]): row
            for row in metadata.get("aggregates", [])
        }
        expected = {
            ("all", "B0", "success_rate"): 0.6268571428571429,
            ("all", "MIKU", "success_rate"): 0.7745714285714286,
            ("all", "B0", "collision_rate"): 0.021714285714285714,
            ("all", "MIKU", "collision_rate"): 0.011428571428571428,
            ("all", "MIKU", "progress_ratio_mean"): 0.8644885700991409,
            ("all", "MIKU", "runtime_p50_ms"): 9.980233007809147,
            ("all", "MIKU", "runtime_p95_ms"): 55.9330896445317,
            ("all", "MIKU", "runtime_p99_ms"): 221.79837652482038,
        }
        headline_ok = True
        for (case_kind, method, field), value in expected.items():
            row = aggregates.get((case_kind, method))
            if row is None or not close(float(row[field]), value, 1e-7):
                errors.append(f"headline value mismatch: {case_kind}/{method}/{field}")
                headline_ok = False
        if headline_ok:
            checks.append("headline aggregate values match frozen metadata")
    else:
        errors.append(f"missing frozen result file: {result_json}")

    raw = DATA / "randomized_raw.csv"
    if raw.is_file():
        row_count = sum(1 for _ in raw.open(encoding="utf-8")) - 1
        if row_count == 14000:
            checks.append("randomized_raw.csv contains 14,000 data rows")
        else:
            errors.append(f"randomized_raw.csv row count is {row_count}, expected 14000")

    manuscript_sources = [ROOT / "manuscript.tex", *sorted((ROOT / "sections").glob("*.tex"))]
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in manuscript_sources)
    bib_text = (ROOT / "references.bib").read_text(encoding="utf-8")
    cited = {
        key.strip()
        for group in re.findall(r"\\cite[pt]?\{([^}]*)\}", source_text)
        for key in group.split(",")
    }
    bib_keys = set(re.findall(r"^@\w+\{([^,]+),", bib_text, flags=re.MULTILINE))
    missing_citations = sorted(cited - bib_keys)
    if missing_citations:
        errors.append(f"missing bibliography keys: {', '.join(missing_citations)}")
    else:
        checks.append(f"all {len(cited)} cited keys exist in references.bib")
    labels = re.findall(r"\\label\{([^}]*)\}", source_text)
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        errors.append(f"duplicate labels: {', '.join(duplicates)}")
    else:
        checks.append(f"all {len(labels)} LaTeX labels are unique")
    if re.search(r"\b(?:TODO|FIXME|TBD)\b", source_text):
        errors.append("placeholder token found in manuscript source")
    else:
        checks.append("no TODO/FIXME/TBD token in manuscript source")

    anonymous_source_files = [
        ROOT / "anonymous.tex",
        ROOT / "manuscript.tex",
        *sorted(
            path
            for path in (ROOT / "sections").glob("*.tex")
            if not path.name.endswith("_named.tex") and path.name != "09_ai_statement_named.tex"
        ),
    ]
    anonymous_source_text = "\n".join(
        path.read_text(encoding="utf-8") for path in anonymous_source_files
    )
    identity_tokens = (
        "JiaWang Liao",
        "YuFei Hu",
        "ChaoYang Shi",
        "ChengJiao Sun",
        "jiao1952@126.com",
        "Hubei University of Arts and Science",
        "Xiangyang Municipal Key Laboratory",
        "2025BEB002",
    )
    source_leaks = [token for token in identity_tokens if token in anonymous_source_text]
    if source_leaks:
        errors.append(f"anonymous source identity leak: {', '.join(source_leaks)}")
    else:
        checks.append("anonymous source branch contains no supplied identity tokens")

    for log_name in ("manuscript.log", "anonymous.log"):
        log_path = ROOT / log_name
        if not log_path.is_file():
            errors.append(f"missing compile log: {log_name}")
            continue
        log = log_path.read_text(encoding="utf-8", errors="replace")
        forbidden = (
            "LaTeX Error",
            "Emergency stop",
            "undefined citations",
            "undefined references",
            "Citation `",
            "Reference `",
        )
        found = [token for token in forbidden if token in log]
        if found:
            errors.append(f"{log_name} contains compile diagnostics: {', '.join(found)}")
        else:
            checks.append(f"{log_name} has no fatal or undefined-reference diagnostics")

    for pdf_name in ("manuscript.pdf", "anonymous.pdf"):
        pdf_path = ROOT / pdf_name
        if not pdf_path.is_file() or pdf_path.stat().st_size < 10000:
            errors.append(f"invalid or empty PDF: {pdf_name}")
    if (ROOT / "anonymous.pdf").is_file():
        anonymous_text = run(["pdftotext", "-layout", str(ROOT / "anonymous.pdf"), "-"])
        leaks = [token for token in identity_tokens if token in anonymous_text]
        if leaks:
            errors.append(f"anonymous PDF identity leak: {', '.join(leaks)}")
        else:
            checks.append("anonymous PDF text contains no supplied identity tokens")
        info = run(["pdfinfo", str(ROOT / "anonymous.pdf")])
        if not re.search(r"^Author:\s+Anonymous\s*$", info, flags=re.MULTILINE):
            errors.append("anonymous PDF metadata author is not Anonymous")
        else:
            checks.append("anonymous PDF metadata is anonymized")

    manifest = ROOT / "supplement" / "SHA256SUMS"
    if manifest.is_file():
        try:
            run(["sha256sum", "-c", str(manifest)], cwd=manifest.parent)
        except subprocess.CalledProcessError:
            errors.append("supplement/SHA256SUMS verification failed")
        else:
            checks.append("supplement SHA-256 manifest verifies")

    delivery_manifest = ROOT / "deliverables" / "SHA256SUMS"
    if delivery_manifest.is_file():
        try:
            run(["sha256sum", "-c", str(delivery_manifest)], cwd=delivery_manifest.parent)
        except subprocess.CalledProcessError:
            errors.append("deliverables/SHA256SUMS verification failed")
        else:
            checks.append("delivery SHA-256 manifest verifies")

    print("Submission validation")
    for item in checks:
        print(f"PASS  {item}")
    for item in errors:
        print(f"FAIL  {item}")
    print(f"Result: {'PASS' if not errors else 'FAIL'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
