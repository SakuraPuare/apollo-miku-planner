"""Measure certified joint search on a non-trivial branching scenario family."""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from apollo_pipeline import Ego, Obstacle, Scenario
from experiment_methods import method_by_key, run_method


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "小论文-2" / "generated"


def build_stress_scenario(spatial_layers: int) -> Scenario:
    """Create two feasible bands per separated static-conflict layer."""
    if spatial_layers <= 0:
        raise ValueError("spatial_layers must be positive")
    obstacles = [
        Obstacle(
            s0=7.0 + 10.0 * index,
            l0=-1.4 if index % 2 == 0 else 1.4,
            W=1.0,
            L=2.0,
            is_static=True,
            name=f"static-layer-{index}",
        )
        for index in range(spatial_layers)
    ]
    obstacles.append(
        Obstacle(
            s0=12.0,
            l0=-3.0,
            vl=1.0,
            W=0.8,
            L=1.0,
            name="dynamic-crossing",
        )
    )
    return Scenario(
        Ego(v0=5.0),
        obstacles,
        s_max=10.0 * spatial_layers + 8.0,
        t_max=max(8.0, 2.0 * spatial_layers + 5.0),
        lane_borrow="both",
    )


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _plot(summary: list[dict[str, object]], output: Path) -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.0,
            "axes.titlesize": 9.0,
            "axes.labelsize": 8.0,
            "legend.fontsize": 7.0,
            "pdf.fonttype": 42,
        }
    )
    layers = np.asarray([row["spatial_layers"] for row in summary], dtype=float)
    domains = np.asarray([row["domain_size"] for row in summary], dtype=float)
    evaluated = np.asarray([row["evaluated_candidates"] for row in summary], dtype=float)
    runtime = np.asarray([row["runtime_median_ms"] for row in summary], dtype=float)
    low = np.asarray([row["runtime_min_ms"] for row in summary], dtype=float)
    high = np.asarray([row["runtime_max_ms"] for row in summary], dtype=float)

    figure, left = plt.subplots(figsize=(3.45, 2.45), constrained_layout=True)
    left.plot(layers, domains, "o-", color="#0072B2", label="Finite domain")
    left.plot(layers, evaluated, "x--", color="#CC3311", label="QP evaluations")
    left.set_yscale("log", base=2)
    left.set_xticks(layers.astype(int))
    left.set_xlabel("Separated spatial conflict layers")
    left.set_ylabel("Candidates (log2 scale)")
    left.grid(axis="y", alpha=0.22)

    right = left.twinx()
    right.errorbar(
        layers,
        runtime,
        yerr=np.vstack((runtime - low, high - runtime)),
        fmt="s-",
        color="#009E73",
        capsize=2.0,
        label="Runtime",
    )
    right.set_ylabel("Complete search runtime (ms)")
    left_handles, left_labels = left.get_legend_handles_labels()
    right_handles, right_labels = right.get_legend_handles_labels()
    left.legend(
        left_handles + right_handles,
        left_labels + right_labels,
        frameon=False,
        loc="upper left",
    )
    left.set_title("Certified search scaling with zero lower bounds", loc="left")

    figure.savefig(
        output / "joint_search_scaling.pdf",
        bbox_inches="tight",
        metadata={"Creator": "run_joint_search_stress.py", "CreationDate": None},
    )
    figure.savefig(output / "joint_search_scaling.png", dpi=220, bbox_inches="tight")
    plt.close(figure)


def run(max_layers: int, repeats: int, output: Path) -> None:
    if max_layers <= 0 or repeats <= 0:
        raise ValueError("max_layers and repeats must be positive")
    output.mkdir(parents=True, exist_ok=True)
    method = replace(
        method_by_key("MIKU"),
        key="MIKU-STRESS",
        label="MIKU certified stress",
        iterative=False,
        refine_on_demand=False,
    )
    raw: list[dict[str, object]] = []
    for layers in range(1, max_layers + 1):
        for repeat in range(repeats):
            result = run_method(method, build_stress_scenario(layers))
            certificate = result.result["joint_search_certificate"]
            raw.append(
                {
                    "spatial_layers": layers,
                    "repeat": repeat,
                    "spatial_homotopies": result.result[
                        "spatial_homotopy_candidate_count"
                    ],
                    "domain_size": certificate["domain_size"],
                    "evaluated_candidates": certificate["evaluated_candidates"],
                    "expanded_spatial_branches": certificate[
                        "expanded_spatial_branches"
                    ],
                    "status": certificate["status"],
                    "absolute_gap": certificate["absolute_gap"],
                    "runtime_ms": result.runtime_ms,
                }
            )
        print(f"completed stress layer count: {layers}", flush=True)

    summary: list[dict[str, object]] = []
    for layers in range(1, max_layers + 1):
        rows = [row for row in raw if row["spatial_layers"] == layers]
        runtime = np.asarray([row["runtime_ms"] for row in rows], dtype=float)
        first = rows[0]
        summary.append(
            {
                "spatial_layers": layers,
                "spatial_homotopies": first["spatial_homotopies"],
                "domain_size": first["domain_size"],
                "evaluated_candidates": first["evaluated_candidates"],
                "expanded_spatial_branches": first["expanded_spatial_branches"],
                "runtime_median_ms": float(np.median(runtime)),
                "runtime_min_ms": float(np.min(runtime)),
                "runtime_max_ms": float(np.max(runtime)),
            }
        )
    _write_csv(output / "joint_search_stress_raw.csv", raw)
    _write_csv(output / "joint_search_stress_summary.csv", summary)
    largest = summary[-1]
    (output / "joint_search_stress_macros.tex").write_text(
        "\n".join(
            (
                "% Auto-generated by run_joint_search_stress.py; do not edit.",
                f"\\newcommand{{\\StressMaxLayers}}{{{largest['spatial_layers']}}}",
                f"\\newcommand{{\\StressSpatialCount}}{{{largest['spatial_homotopies']}}}",
                f"\\newcommand{{\\StressDomainSize}}{{{largest['domain_size']}}}",
                f"\\newcommand{{\\StressEvaluatedCount}}{{{largest['evaluated_candidates']}}}",
                f"\\newcommand{{\\StressRuntimeMedian}}{{{largest['runtime_median_ms']:.2f}}}",
                "",
            )
        ),
        encoding="utf-8",
    )
    _plot(summary, output)
    metadata = {
        "protocol": "miku-joint-search-stress-v1",
        "max_spatial_layers": max_layers,
        "repeats": repeats,
        "construction": "Two feasible lateral bands per separated static layer plus one dynamic crossing.",
        "scope": "Complexity diagnostic. Zero lower bounds imply exhaustive evaluation; this is not a pruning claim.",
        "summary": summary,
    }
    (output / "joint_search_stress_results.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-layers", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    run(arguments.max_layers, arguments.repeats, arguments.output)


if __name__ == "__main__":
    main()
