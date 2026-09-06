#!/usr/bin/env python3
"""Audit whether Apollo runtime dumps can be mapped to indexed fixtures.

This is intentionally read-only.  Runtime component names and timestamps are
useful provenance, but they do not identify which planning fixture was loaded.
The audit therefore fails closed when scenario/config identifiers are absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APOLLO_ROOT = ROOT.parent / "core-11.0"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit() -> dict[str, object]:
    fixture_manifest = json.loads(
        (ROOT / "apollo_fixture_manifest.json").read_text(encoding="utf-8")
    )
    source_manifest = json.loads(
        (ROOT / "apollo_evidence_manifest.json").read_text(encoding="utf-8")
    )
    dump_root = APOLLO_ROOT / "dumps"
    runtime_paths = sorted(path for path in dump_root.glob("*") if path.is_file())
    fixture_tokens = sorted(
        {
            token
            for fixture in fixture_manifest["fixtures"]["planning_inputs"]
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", fixture["name"])
            if len(token) >= 4
        }
    )
    matched_tokens: dict[str, list[str]] = {token: [] for token in fixture_tokens}
    runtime_index = []
    for path in runtime_paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        matches = [token for token in fixture_tokens if token.lower() in text.lower()]
        for token in matches:
            matched_tokens[token].append(path.name)
        stat = path.stat()
        runtime_index.append(
            {
                "path": str(path.relative_to(APOLLO_ROOT)),
                "size_bytes": stat.st_size,
                "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "sha256": _sha256(path),
                "fixture_tokens_found": matches,
            }
        )
    mapped_fixture_tokens = {
        token: paths for token, paths in matched_tokens.items() if paths
    }
    return {
        "schema_version": 1,
        "apollo_source_commit": source_manifest["apollo_source"]["commit"],
        "runtime_root": str(dump_root),
        "runtime_file_count": len(runtime_index),
        "runtime_files": runtime_index,
        "indexed_fixture_tokens": fixture_tokens,
        "matched_fixture_tokens": mapped_fixture_tokens,
        "exact_scenario_to_runtime_output_mapping": False,
        "mapping_status": "pending",
        "blocking_reason": (
            "Runtime dumps expose component/process statistics but contain no indexed "
            "planning fixture, scenario, or configuration identifier."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "apollo_runtime_mapping_audit.json",
    )
    args = parser.parse_args()
    report = audit()
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
