"""Reproducible smoke validation against public CommonRoad XML scenarios.

This deliberately validates the external source without pretending that the
axis-aligned Frenet prototype is a CommonRoad-compliant planner.  It checks
that the pinned public XML files download, parse, and contain the road,
traffic, and planning-problem entities required by the adapter boundary.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
import xml.etree.ElementTree as ET


BASE = (
    "https://gitlab.lrz.de/tum-cps/commonroad-scenarios/-/raw/"
    "2020a_scenarios/scenarios/recorded/NGSIM/Lankershim/"
)
SCENARIOS = (
    "USA_Lanker-1_1_T-1.xml",
    "USA_Lanker-1_2_T-1.xml",
    "USA_Lanker-1_3_T-1.xml",
    "USA_Lanker-1_4_T-1.xml",
)


def validate(timeout: float = 30.0) -> list[dict[str, object]]:
    report = []
    for filename in SCENARIOS:
        url = BASE + filename
        with urllib.request.urlopen(url, timeout=timeout) as response:
            root = ET.fromstring(response.read())
        counts = {
            "lanelets": len(root.findall(".//lanelet")),
            "dynamic_obstacles": len(root.findall(".//dynamicObstacle")),
            "static_obstacles": len(root.findall(".//staticObstacle")),
            "planning_problems": len(root.findall(".//planningProblem")),
        }
        if not counts["lanelets"] or not counts["dynamic_obstacles"] or not counts["planning_problems"]:
            raise ValueError(f"incomplete CommonRoad scenario: {filename}: {counts}")
        report.append({"file": filename, "benchmark_id": root.attrib.get("benchmarkID"), **counts})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    print(json.dumps(validate(args.timeout), indent=2))
