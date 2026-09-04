from __future__ import annotations

import sys
import urllib.request

import pytest

sys.path.insert(0, "可视化")
from validate_commonroad_external import validate  # noqa: E402
from validate_commonroad_external import BASE  # noqa: E402
from commonroad_adapter import adapt_commonroad_xml  # noqa: E402


@pytest.mark.network
def test_public_commonroad_xml_smoke():
    try:
        report = validate(timeout=10.0)
    except Exception as exc:  # network is an optional reproducibility gate
        pytest.skip(f"CommonRoad network source unavailable: {exc}")
    assert len(report) == 4
    assert all(item["lanelets"] > 0 and item["dynamic_obstacles"] > 0 for item in report)


@pytest.mark.network
def test_public_commonroad_adapter_smoke():
    try:
        with urllib.request.urlopen(BASE + "USA_Lanker-1_1_T-1.xml", timeout=10.0) as response:
            adapted = adapt_commonroad_xml(response.read())
    except Exception as exc:  # network is an optional reproducibility gate
        pytest.skip(f"CommonRoad network source unavailable: {exc}")
    assert len(adapted.route_lanelet_ids) >= 2
    assert adapted.projected_obstacles > 0
    assert adapted.scenario.s_max > adapted.scenario.ego.s0
