"""Run the bounded adapter on the four pinned public Lankershim XML files."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "可视化") not in sys.path:
    sys.path.insert(0, str(ROOT / "可视化"))

from commonroad_adapter import adapt_commonroad_xml  # noqa: E402
from experiment_cases import RandomCase  # noqa: E402
from experiment_metrics import evaluate_run  # noqa: E402
from experiment_methods import method_by_key, run_method  # noqa: E402
from validate_commonroad_external import BASE, SCENARIOS  # noqa: E402


def _run_scenario(filename: str, timeout: float) -> tuple[dict[str, object], list[dict[str, object]]]:
    with urllib.request.urlopen(BASE + filename, timeout=timeout) as response:
        adapted = adapt_commonroad_xml(response.read())
    case = RandomCase("commonroad_batch", 0, adapted.scenario, adapted.scenario)
    rows = []
    for method_key in ("B0", "MIKU"):
        method_run = run_method(method_by_key(method_key), adapted.scenario)
        metrics = evaluate_run(method_run, case)
        certificate = method_run.result.get("joint_search_certificate") or {}
        rows.append(
            {
                "scenario": filename.removesuffix(".xml"),
                "benchmark_id": adapted.benchmark_id,
                "method": method_key,
                "success": metrics["success"],
                "collision": metrics["collision"],
                "degraded_stop": metrics["degraded_stop"],
                "min_clearance_m": metrics["min_clearance_m"],
                "runtime_ms": method_run.runtime_ms,
                "joint_status": certificate.get("status"),
                "joint_domain_size": certificate.get("domain_size"),
                "joint_evaluated_candidates": certificate.get("evaluated_candidates"),
            }
        )
    metadata = {
        "scenario": filename.removesuffix(".xml"),
        "benchmark_id": adapted.benchmark_id,
        "source_lanelets": adapted.source_lanelets,
        "source_dynamic_obstacles": adapted.source_dynamic_obstacles,
        "projected_obstacles": adapted.projected_obstacles,
        "skipped_obstacles": adapted.skipped_obstacles,
        "route_lanelet_ids": adapted.route_lanelet_ids,
        "maximum_projection_residual_m": adapted.maximum_projection_residual_m,
    }
    return metadata, rows


def run(timeout: float = 30.0) -> dict[str, object]:
    metadata = []
    rows = []
    for filename in SCENARIOS:
        scenario_metadata, scenario_rows = _run_scenario(filename, timeout)
        metadata.append(scenario_metadata)
        rows.extend(scenario_rows)
    summary = []
    for method in ("B0", "MIKU"):
        selected = [row for row in rows if row["method"] == method]
        summary.append(
            {
                "method": method,
                "scenario_count": len(selected),
                "success_rate": float(np.mean([row["success"] for row in selected])),
                "collision_rate": float(np.mean([row["collision"] for row in selected])),
                "degraded_stop_rate": float(np.mean([row["degraded_stop"] for row in selected])),
                "median_runtime_ms": float(np.median([row["runtime_ms"] for row in selected])),
                "max_runtime_ms": float(np.max([row["runtime_ms"] for row in selected])),
            }
        )
    return {
        "source": BASE,
        "scenario_count": len(metadata),
        "adapter_limitations": [
            "centerline-only lanelet route",
            "initial-state constant-velocity obstacle projection",
            "axis-aligned Frenet rectangles; no CommonRoad rule/shape semantics",
            "not a native CommonRoad planner benchmark",
        ],
        "scenarios": metadata,
        "rows": rows,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "小论文-2" / "generated")
    arguments = parser.parse_args()
    report = run(arguments.timeout)
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = arguments.output_dir / "commonroad_batch_results.json"
    csv_path = arguments.output_dir / "commonroad_batch_raw.csv"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        rows = report["rows"]
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
