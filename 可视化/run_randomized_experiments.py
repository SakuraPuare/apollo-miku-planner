"""Run six paired randomized scenario families and generate paper-ready evidence.

The default protocol evaluates seeds 0--99 for every family.  Planning receives
the same case for all methods; safety metrics are evaluated against the separate
truth scenario retained by ``experiment_cases``.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from experiment_cases import CASE_KINDS, generate_case
from experiment_methods import METHODS, run_method
from experiment_metrics import bootstrap_paired_difference, evaluate_run


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "小论文-2" / "generated"
RAW_FIELDS = (
    "schema_version",
    "case_kind",
    "seed",
    "method",
    "method_label",
    "success",
    "reached",
    "collision",
    "min_clearance_m",
    "min_ttc_s",
    "arrival_time_s",
    "penalized_travel_time_s",
    "progress_ratio",
    "average_speed_mps",
    "path_length_m",
    "max_longitudinal_acceleration_mps2",
    "max_lateral_acceleration_mps2",
    "jerk_rms_mps3",
    "time_window_violations",
    "degraded_stop",
    "runtime_ms",
    "iterations",
    "iterative_converged",
)


def _write_csv(path: Path, rows: list[dict], fields: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _finite_values(rows: list[dict], key: str) -> np.ndarray:
    values = [row[key] for row in rows if row.get(key) is not None]
    array = np.asarray(values, dtype=float)
    return array[np.isfinite(array)]


def _mean(rows: list[dict], key: str) -> float | None:
    values = _finite_values(rows, key)
    return float(np.mean(values)) if len(values) else None


def _aggregate(rows: list[dict]) -> list[dict]:
    aggregates = []
    for case_kind in (*CASE_KINDS, "all"):
        for method in METHODS:
            subset = [
                row
                for row in rows
                if row["method"] == method.key
                and (case_kind == "all" or row["case_kind"] == case_kind)
            ]
            runtimes = _finite_values(subset, "runtime_ms")
            aggregates.append(
                {
                    "case_kind": case_kind,
                    "method": method.key,
                    "n": len(subset),
                    "success_rate": _mean(subset, "success"),
                    "reach_rate": _mean(subset, "reached"),
                    "collision_rate": _mean(subset, "collision"),
                    "degraded_stop_rate": _mean(subset, "degraded_stop"),
                    "min_clearance_mean_m": _mean(subset, "min_clearance_m"),
                    "min_ttc_mean_s": _mean(subset, "min_ttc_s"),
                    "arrival_time_success_mean_s": _mean(
                        [row for row in subset if row["success"]], "arrival_time_s"
                    ),
                    "progress_ratio_mean": _mean(subset, "progress_ratio"),
                    "average_speed_mean_mps": _mean(subset, "average_speed_mps"),
                    "path_length_mean_m": _mean(subset, "path_length_m"),
                    "max_longitudinal_acceleration_mean_mps2": _mean(
                        subset, "max_longitudinal_acceleration_mps2"
                    ),
                    "max_lateral_acceleration_mean_mps2": _mean(
                        subset, "max_lateral_acceleration_mps2"
                    ),
                    "jerk_rms_mean_mps3": _mean(subset, "jerk_rms_mps3"),
                    "time_window_violations_mean": _mean(
                        subset, "time_window_violations"
                    ),
                    "runtime_p50_ms": float(np.quantile(runtimes, 0.50)),
                    "runtime_p95_ms": float(np.quantile(runtimes, 0.95)),
                    "runtime_p99_ms": float(np.quantile(runtimes, 0.99)),
                }
            )
    return aggregates


def _paired_statistics(rows: list[dict]) -> list[dict]:
    metrics = (
        "success",
        "collision",
        "min_clearance_m",
        "progress_ratio",
        "penalized_travel_time_s",
        "average_speed_mps",
        "jerk_rms_mps3",
        "runtime_ms",
    )
    indexed = {
        (row["case_kind"], row["seed"], row["method"]): row for row in rows
    }
    statistics = []
    bootstrap_seed = 91000
    for case_kind in (*CASE_KINDS, "all"):
        case_keys = sorted(
            {
                (row["case_kind"], row["seed"])
                for row in rows
                if case_kind == "all" or row["case_kind"] == case_kind
            }
        )
        for baseline in METHODS[:-1]:
            for metric in metrics:
                miku = np.asarray(
                    [indexed[(*key, "MIKU")][metric] for key in case_keys], dtype=float
                )
                comparison = np.asarray(
                    [indexed[(*key, baseline.key)][metric] for key in case_keys],
                    dtype=float,
                )
                result = bootstrap_paired_difference(
                    miku, comparison, seed=bootstrap_seed
                )
                bootstrap_seed += 1
                statistics.append(
                    {
                        "case_kind": case_kind,
                        "comparison": f"MIKU-{baseline.key}",
                        "metric": metric,
                        **result,
                    }
                )
    return statistics


def _failure_rows(rows: list[dict]) -> list[dict]:
    failures = []
    for row in rows:
        if row["success"]:
            continue
        if row["collision"]:
            failure_type = "collision"
        elif row["degraded_stop"] and not row["reached"]:
            failure_type = "unreached_or_fallback_stop"
        else:
            failure_type = "other"
        failures.append(
            {
                "case_kind": row["case_kind"],
                "seed": row["seed"],
                "method": row["method"],
                "failure_type": failure_type,
                "progress_ratio": row["progress_ratio"],
                "min_clearance_m": row["min_clearance_m"],
            }
        )
    return failures


def _latex_macros(aggregates: list[dict], statistics: list[dict]) -> str:
    overall = {row["method"]: row for row in aggregates if row["case_kind"] == "all"}
    lines = [
        "% Auto-generated by run_randomized_experiments.py; do not edit.",
        f"\\newcommand{{\\RandomCaseCount}}{{{overall['MIKU']['n']}}}",
        f"\\newcommand{{\\RandomMikuSuccessRate}}{{{100 * overall['MIKU']['success_rate']:.1f}\\%}}",
        f"\\newcommand{{\\RandomMikuCollisionRate}}{{{100 * overall['MIKU']['collision_rate']:.1f}\\%}}",
        f"\\newcommand{{\\RandomMikuRuntimePfive}}{{{overall['MIKU']['runtime_p95_ms']:.2f}}}",
        f"\\newcommand{{\\RandomMikuRuntimePnine}}{{{overall['MIKU']['runtime_p99_ms']:.2f}}}",
    ]
    for baseline in METHODS[:-1]:
        key = baseline.key
        lines.append(
            f"\\newcommand{{\\Random{key}SuccessRate}}"
            f"{{{100 * overall[key]['success_rate']:.1f}\\%}}"
        )
        stat = next(
            row
            for row in statistics
            if row["case_kind"] == "all"
            and row["comparison"] == f"MIKU-{key}"
            and row["metric"] == "success"
        )
        lines.append(
            f"\\newcommand{{\\RandomMikuVs{key}SuccessDiff}}"
            f"{{{100 * stat['mean_difference']:.1f}}}"
        )
    return "\n".join(lines) + "\n"


def _plot_summary(output: Path, aggregates: list[dict]) -> None:
    overall = [row for row in aggregates if row["case_kind"] == "all"]
    labels = [row["method"] for row in overall]
    positions = np.arange(len(labels))
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.2))
    axes[0].bar(positions - 0.18, [row["success_rate"] for row in overall], 0.36, label="Success")
    axes[0].bar(positions + 0.18, [row["collision_rate"] for row in overall], 0.36, label="Collision")
    axes[0].set_ylabel("Rate")
    axes[0].set_ylim(0.0, 1.0)
    axes[0].legend(fontsize=8)
    axes[1].bar(positions, [row["min_clearance_mean_m"] for row in overall])
    axes[1].set_ylabel("Mean minimum clearance [m]")
    axes[2].bar(positions, [row["runtime_p95_ms"] for row in overall])
    axes[2].set_ylabel("Full-cycle runtime P95 [ms]")
    for axis in axes:
        axis.set_xticks(positions, labels)
        axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output / "randomized_summary.png", dpi=220)
    plt.close(fig)


def _json_safe(value):
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def run(seed_start: int, seed_count: int, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    total_cases = len(CASE_KINDS) * seed_count
    completed = 0
    for kind in CASE_KINDS:
        for seed in range(seed_start, seed_start + seed_count):
            case = generate_case(kind, seed)
            for method in METHODS:
                rows.append(evaluate_run(run_method(method, case.planning_scenario), case))
            completed += 1
            if completed % 25 == 0 or completed == total_cases:
                print(f"completed {completed}/{total_cases} paired cases", flush=True)

    aggregates = _aggregate(rows)
    statistics = _paired_statistics(rows)
    failures = _failure_rows(rows)
    _write_csv(output / "randomized_raw.csv", rows, RAW_FIELDS)
    _write_csv(output / "randomized_summary.csv", aggregates, tuple(aggregates[0]))
    _write_csv(output / "paired_statistics.csv", statistics, tuple(statistics[0]))
    _write_csv(output / "failure_cases.csv", failures, tuple(failures[0]))
    (output / "randomized_macros.tex").write_text(
        _latex_macros(aggregates, statistics), encoding="utf-8"
    )
    metadata = {
        "protocol": "miku-random-v1",
        "case_kinds": list(CASE_KINDS),
        "methods": [
            {
                "key": method.key,
                "label": method.label,
                "flags": asdict(method.flags),
                "iterative": method.iterative,
                "max_iterations": method.max_iterations,
            }
            for method in METHODS
        ],
        "seed_start": seed_start,
        "seed_count_per_kind": seed_count,
        "paired_case_count": total_cases,
        "raw_row_count": len(rows),
        "failure_counts": dict(Counter(row["failure_type"] for row in failures)),
        "decision_gates": {
            "C5_safe_window": "Excluded from the main MIKU method after corrected deterministic ablation showed no independent benefit and one repeatable regression."
        },
        "metric_notes": {
            "safety_truth": "Unperturbed truth Scenario; planning input differs only in prediction_noise.",
            "clearance": "Minimum signed boundary distance between axis-aligned physical rectangles in straight-road SL coordinates; collision requires more than 1 mm penetration.",
            "ttc": "Minimum longitudinal TTC while physical lateral footprints overlap; absent values are null.",
            "penalized_travel_time": "Arrival time for collision-free arrivals; otherwise scenario horizon plus 5 s.",
            "runtime": "Wall time of the complete method call; B2 includes all coordination iterations.",
            "confidence_interval": "Paired percentile bootstrap, 5000 resamples.",
            "effect_size": "Paired Cohen dz on finite paired differences.",
        },
        "aggregates": aggregates,
        "paired_statistics": statistics,
    }
    (output / "randomized_results.json").write_text(
        json.dumps(_json_safe(metadata), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _plot_summary(output, aggregates)
    print(f"wrote evidence bundle to {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.seed_start < 0 or args.seeds <= 0:
        parser.error("--seed-start must be non-negative and --seeds must be positive")
    run(args.seed_start, args.seeds, args.output)


if __name__ == "__main__":
    main()
