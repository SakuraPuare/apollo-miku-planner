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
from experiment_metrics import bootstrap_paired_difference, evaluate_run, exact_mcnemar


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
                if metric in ("success", "collision"):
                    result.update(exact_mcnemar(miku, comparison))
                else:
                    result.update(
                        {
                            "candidate_only": None,
                            "reference_only": None,
                            "discordant": None,
                            "mcnemar_exact_p": None,
                        }
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
    case_words = {
        "crossing_pedestrian": "Crossing",
        "vehicle_cut_in": "CutIn",
        "parked_and_oncoming": "Parked",
        "narrow_multi_obstacle": "Narrow",
        "interleaved_dynamic": "Interleaved",
        "prediction_noise": "Noise",
        "delayed_crossing": "Delayed",
        "all": "All",
    }
    method_words = {"B0": "BZero", "B1": "BOne", "B2": "BTwo", "MIKU": "Miku"}
    metric_formats = {
        "success_rate": ("SuccessPct", 100.0, 1),
        "reach_rate": ("ReachPct", 100.0, 1),
        "collision_rate": ("CollisionPct", 100.0, 1),
        "degraded_stop_rate": ("StopPct", 100.0, 1),
        "min_clearance_mean_m": ("Clearance", 1.0, 3),
        "arrival_time_success_mean_s": ("Arrival", 1.0, 2),
        "progress_ratio_mean": ("ProgressPct", 100.0, 1),
        "average_speed_mean_mps": ("AvgSpeed", 1.0, 2),
        "jerk_rms_mean_mps3": ("JerkRms", 1.0, 2),
        "runtime_p50_ms": ("RuntimePfifty", 1.0, 2),
        "runtime_p95_ms": ("RuntimePninetyfive", 1.0, 2),
        "runtime_p99_ms": ("RuntimePninetynine", 1.0, 2),
    }
    overall = {row["method"]: row for row in aggregates if row["case_kind"] == "all"}
    lines = [
        "% Auto-generated by run_randomized_experiments.py; do not edit.",
        f"\\newcommand{{\\RandCaseCount}}{{{overall['MIKU']['n']}}}",
        f"\\newcommand{{\\RandSeedCount}}{{{overall['MIKU']['n'] // len(CASE_KINDS)}}}",
    ]
    for row in aggregates:
        case_word = case_words[row["case_kind"]]
        method_word = method_words[row["method"]]
        for key, (suffix, scale, decimals) in metric_formats.items():
            value = row[key]
            rendered = "NA" if value is None else f"{scale * value:.{decimals}f}"
            lines.append(
                f"\\newcommand{{\\Rand{case_word}{method_word}{suffix}}}{{{rendered}}}"
            )
    comparison_words = {
        "MIKU-B0": "MikuVsBZero",
        "MIKU-B1": "MikuVsBOne",
        "MIKU-B2": "MikuVsBTwo",
    }
    statistic_metrics = {
        "success": ("Success", 100.0, 1),
        "collision": ("Collision", 100.0, 1),
        "min_clearance_m": ("Clearance", 1.0, 3),
        "penalized_travel_time_s": ("Travel", 1.0, 2),
        "runtime_ms": ("Runtime", 1.0, 2),
    }
    for row in statistics:
        if row["metric"] not in statistic_metrics:
            continue
        case_word = case_words[row["case_kind"]]
        comparison_word = comparison_words[row["comparison"]]
        metric_word, scale, decimals = statistic_metrics[row["metric"]]
        prefix = f"\\Rand{case_word}{comparison_word}{metric_word}"
        lines.extend(
            [
                f"\\newcommand{{{prefix}Diff}}{{{scale * row['mean_difference']:.{decimals}f}}}",
                f"\\newcommand{{{prefix}CiLow}}{{{scale * row['ci_low']:.{decimals}f}}}",
                f"\\newcommand{{{prefix}CiHigh}}{{{scale * row['ci_high']:.{decimals}f}}}",
                f"\\newcommand{{{prefix}Effect}}{{{row['cohen_dz']:.3f}}}",
            ]
        )
        if row.get("mcnemar_exact_p") is not None:
            lines.append(
                f"\\newcommand{{{prefix}McNemarP}}{{{row['mcnemar_exact_p']:.4g}}}"
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


def _write_derived(
    rows: list[dict], seed_start: int, seed_count: int, output: Path
) -> None:
    total_cases = len(CASE_KINDS) * seed_count
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
        "protocol": "miku-random-v2",
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


def _read_raw(path: Path) -> list[dict]:
    integer_fields = {
        "seed",
        "success",
        "reached",
        "collision",
        "time_window_violations",
        "degraded_stop",
        "iterations",
        "iterative_converged",
    }
    text_fields = {"schema_version", "case_kind", "method", "method_label"}
    rows = []
    with path.open(encoding="utf-8", newline="") as stream:
        for raw in csv.DictReader(stream):
            row = {}
            for key, value in raw.items():
                if key in text_fields:
                    row[key] = value
                elif key in integer_fields:
                    row[key] = int(value)
                else:
                    row[key] = None if value == "" else float(value)
            rows.append(row)
    return rows


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
    _write_csv(output / "randomized_raw.csv", rows, RAW_FIELDS)
    _write_derived(rows, seed_start, seed_count, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    if args.seed_start < 0 or args.seeds <= 0:
        parser.error("--seed-start must be non-negative and --seeds must be positive")
    if args.summarize_only:
        rows = _read_raw(args.output / "randomized_raw.csv")
        _write_derived(rows, args.seed_start, args.seeds, args.output)
    else:
        run(args.seed_start, args.seeds, args.output)


if __name__ == "__main__":
    main()
