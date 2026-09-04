"""Run the bounded CommonRoad adapter and planner smoke on one public XML."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "可视化") not in sys.path:
    sys.path.insert(0, str(ROOT / "可视化"))

from commonroad_adapter import adapt_commonroad_xml  # noqa: E402
from experiment_cases import RandomCase  # noqa: E402
from experiment_metrics import evaluate_run  # noqa: E402
from experiment_methods import method_by_key, run_method  # noqa: E402


DEFAULT_URL = (
    "https://gitlab.lrz.de/tum-cps/commonroad-scenarios/-/raw/"
    "2020a_scenarios/scenarios/recorded/NGSIM/Lankershim/"
    "USA_Lanker-1_1_T-1.xml"
)


def run(url: str = DEFAULT_URL, timeout: float = 30.0) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = response.read()
    adapted = adapt_commonroad_xml(payload)
    case = RandomCase("commonroad_adapter_smoke", 0, adapted.scenario, adapted.scenario)
    methods = {}
    for method_key in ("B0", "MIKU"):
        method_run = run_method(method_by_key(method_key), adapted.scenario)
        metrics = evaluate_run(method_run, case)
        certificate = method_run.result.get("joint_search_certificate")
        certificate_summary = None
        if certificate is not None:
            certificate_summary = {
                "status": certificate.get("status"),
                "domain_size": certificate.get("domain_size"),
                "evaluated_candidates": certificate.get("evaluated_candidates"),
                "expanded_spatial_branches": certificate.get("expanded_spatial_branches"),
            }
        methods[method_key] = {
            "success": metrics["success"],
            "collision": metrics["collision"],
            "degraded_stop": metrics["degraded_stop"],
            "min_clearance_m": metrics["min_clearance_m"],
            "runtime_ms": method_run.runtime_ms,
            "joint_search_status": method_run.result.get("joint_search_status"),
            "joint_search_certificate": certificate_summary,
        }
    return {
        "url": url,
        "adapter": {
            "benchmark_id": adapted.benchmark_id,
            "route_lanelet_ids": adapted.route_lanelet_ids,
            "source_lanelets": adapted.source_lanelets,
            "source_dynamic_obstacles": adapted.source_dynamic_obstacles,
            "projected_obstacles": adapted.projected_obstacles,
            "skipped_obstacles": adapted.skipped_obstacles,
            "maximum_projection_residual_m": adapted.maximum_projection_residual_m,
            "limitations": adapted.limitations,
        },
        "methods": methods,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "小论文-2" / "generated" / "commonroad_adapter_smoke.json",
    )
    arguments = parser.parse_args()
    report = run(arguments.url, arguments.timeout)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
