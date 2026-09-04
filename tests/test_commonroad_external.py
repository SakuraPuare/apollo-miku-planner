from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "可视化")
from validate_commonroad_external import validate  # noqa: E402


@pytest.mark.network
def test_public_commonroad_xml_smoke():
    try:
        report = validate(timeout=10.0)
    except Exception as exc:  # network is an optional reproducibility gate
        pytest.skip(f"CommonRoad network source unavailable: {exc}")
    assert len(report) == 4
    assert all(item["lanelets"] > 0 and item["dynamic_obstacles"] > 0 for item in report)
