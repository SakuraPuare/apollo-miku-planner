from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _run(script: str) -> None:
    subprocess.run(
        [str(ROOT / "tools" / script)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_apollo_source_snapshot_is_verified() -> None:
    _run("verify_apollo_snapshot.sh")
    manifest = json.loads(
        (ROOT / "apollo_evidence_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["apollo_source"]["commit"].startswith("57460908")
    assert manifest["runtime_assets"]["status"] == "artifacts_present"


def test_apollo_fixture_and_runtime_assets_are_present() -> None:
    _run("verify_apollo_fixtures.sh")
    manifest = json.loads(
        (ROOT / "apollo_fixture_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"]["fixture_paths_indexed"] is True
    assert manifest["runtime_outputs"]["planning"].startswith("planning.")


def test_runtime_mapping_audit_fails_closed_without_fixture_identity() -> None:
    audit = json.loads(
        (ROOT / "apollo_runtime_mapping_audit.json").read_text(encoding="utf-8")
    )
    assert audit["runtime_file_count"] > 0
    assert audit["mapping_status"] == "pending"
    assert audit["exact_scenario_to_runtime_output_mapping"] is False
