#!/usr/bin/env python3
"""Read-only consistency check for the Q3/Q4 manuscript evidence package."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "小论文" / "main.tex"
ARCHIVE = ROOT / "submission_artifacts" / "frozen_3500" / "小论文-2" / "generated"

EXPECTED_HASHES = {
    "randomized_raw.csv": "d858e6ffdef2e72d8111cab4b22ae335a697ec6709a28b3214374258b70bbca7",
    "randomized_results.json": "10ba825b23967160c51a7710ac6fe985be9f8dba63bce89fc212f6e937df5034",
    "randomized_summary.csv": "d8d5c347da110223ff38b27367fbd52d13f39c0420d6c7c10074c58dadc5fcd5",
}

EXPECTED = {
    "B0": (0.6268571428571429, 0.021714285714285714, 0.7751633224889197, 1.252001504612598, 56.793048946565236),
    "B1": (0.5237142857142857, 0.02142857142857143, 0.7106700572388596, 1.3145684975751057, 63.2359966431977),
    "B2": (0.6208571428571429, 0.022285714285714287, 0.766217957946165, 1.300439109673116, 169.48996889914264),
    "MIKU": (0.7745714285714286, 0.011428571428571429, 0.8644885712645644, 1.1324153124368965, 55.9330896445317),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    tex = TEX.read_text(encoding="utf-8")
    assert "在通用路径--速度解耦规划链中" in tex
    assert "Apollo Planning 作为工程集成与场景验证平台" in tex
    assert "不等同于真实道路实车测试" in tex
    assert "Apollo Planning 解耦基线" in tex
    forbidden = re.compile(r"(?i)lean|mathlib|formal proof|proof artifact|形式化证明|机器检查")
    assert not forbidden.search(tex), "forbidden internal-verification term in submission TeX"

    for name, expected_hash in EXPECTED_HASHES.items():
        path = ARCHIVE / name
        assert path.is_file(), path
        assert sha256(path) == expected_hash, f"hash mismatch: {name}"

    summary = ARCHIVE / "randomized_summary.csv"
    with summary.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    all_rows = {row["method"]: row for row in rows if row["case_kind"] == "all"}
    assert set(EXPECTED) <= set(all_rows), all_rows.keys()
    for method, values in EXPECTED.items():
        row = all_rows[method]
        observed = tuple(float(row[key]) for key in ("success_rate", "collision_rate", "progress_ratio_mean", "jerk_rms_mean_mps3", "runtime_p95_ms"))
        for actual, target in zip(observed, values):
            assert abs(actual - target) < 1e-9, (method, actual, target)

    metadata = json.loads((ARCHIVE / "randomized_results.json").read_text(encoding="utf-8"))
    assert metadata.get("protocol") == "miku-random-v2"
    assert metadata.get("paired_case_count") == 3500
    print("Q3/Q4 consistency check: PASS")
    print("  manuscript: forbidden-term and Apollo-boundary checks passed")
    print("  archive: 3 frozen hashes, 3,500 cases, B0/B1/B2/MIKU summary values passed")


if __name__ == "__main__":
    main()
