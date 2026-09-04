"""Generate manuscript evidence figures from the committed experiment CSVs."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "小论文-2" / "generated"
FAMILIES = (
    "crossing_pedestrian",
    "vehicle_cut_in",
    "parked_and_oncoming",
    "narrow_multi_obstacle",
    "interleaved_dynamic",
    "prediction_noise",
    "delayed_crossing",
)
FAMILY_LABELS = {
    "crossing_pedestrian": "Crossing",
    "vehicle_cut_in": "Cut-in",
    "parked_and_oncoming": "Parked/oncoming",
    "narrow_multi_obstacle": "Narrow",
    "interleaved_dynamic": "Interleaved",
    "prediction_noise": "Prediction noise",
    "delayed_crossing": "Delayed crossing",
}
METHOD_COLORS = {
    "B0": "#6F7782",
    "B1": "#0072B2",
    "B2": "#D55E00",
    "MIKU": "#009E73",
}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _configure_plotting() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.0,
            "axes.titlesize": 9.0,
            "axes.labelsize": 8.0,
            "legend.fontsize": 7.0,
            "xtick.labelsize": 7.0,
            "ytick.labelsize": 7.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "x",
            "grid.alpha": 0.22,
            "axes.axisbelow": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _family_effect_panel(ax: plt.Axes, paired: list[dict[str, str]]) -> None:
    selected = {
        row["case_kind"]: row
        for row in paired
        if row["comparison"] == "MIKU-B0"
        and row["metric"] == "success"
        and row["case_kind"] in FAMILIES
    }
    y = np.arange(len(FAMILIES))
    means = np.array([float(selected[name]["mean_difference"]) * 100 for name in FAMILIES])
    lows = np.array([float(selected[name]["ci_low"]) * 100 for name in FAMILIES])
    highs = np.array([float(selected[name]["ci_high"]) * 100 for name in FAMILIES])
    colors = ["#D55E00" if value < 0 else "#0072B2" for value in means]
    ax.errorbar(
        means,
        y,
        xerr=np.vstack((means - lows, highs - means)),
        fmt="none",
        ecolor="#3B4148",
        elinewidth=1.3,
        capsize=2.2,
    )
    ax.scatter(means, y, c=colors, s=22, zorder=3)
    ax.axvline(0.0, color="#222222", linewidth=0.8)
    ax.set_yticks(y, [FAMILY_LABELS[name] for name in FAMILIES])
    ax.invert_yaxis()
    ax.set_xlabel("MIKU - B0 success (percentage points)")
    ax.set_title("a  Paired family effects (95% CI)", loc="left", fontweight="bold")


def _runtime_panel(ax: plt.Axes, raw: list[dict[str, str]]) -> None:
    for method in ("B0", "B1", "B2", "MIKU"):
        values = np.sort(
            np.array(
                [float(row["runtime_ms"]) for row in raw if row["method"] == method],
                dtype=float,
            )
        )
        probability = np.arange(1, len(values) + 1) / len(values)
        ax.step(values, probability, where="post", color=METHOD_COLORS[method], label=method)
    ax.set_xscale("log")
    ax.set_ylim(0.0, 1.01)
    ax.set_xlabel("Complete-planning latency (ms, log scale)")
    ax.set_ylabel("Empirical CDF")
    ax.set_title("b  Runtime distribution", loc="left", fontweight="bold")
    ax.legend(frameon=False, ncol=2, loc="lower right")


def _ablation_panel(ax: plt.Axes, paired: list[dict[str, str]]) -> None:
    labels = [f"A{index}" for index in range(1, 8)]
    selected = {
        row["comparison"].split("-")[1]: row
        for row in paired
        if row["case_kind"] == "all"
        and row["comparison"].startswith("MIKU-A")
        and row["metric"] == "success"
    }
    y = np.arange(len(labels))
    means = np.array([float(selected[label]["mean_difference"]) * 100 for label in labels])
    lows = np.array([float(selected[label]["ci_low"]) * 100 for label in labels])
    highs = np.array([float(selected[label]["ci_high"]) * 100 for label in labels])
    colors = ["#D55E00" if value < 0 else "#009E73" for value in means]
    ax.errorbar(
        means,
        y,
        xerr=np.vstack((means - lows, highs - means)),
        fmt="none",
        ecolor="#3B4148",
        elinewidth=1.3,
        capsize=2.2,
    )
    ax.scatter(means, y, c=colors, s=22, zorder=3)
    ax.axvline(0.0, color="#222222", linewidth=0.8)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Full MIKU - ablation success (percentage points)")
    ax.set_title("c  Component effects (95% CI)", loc="left", fontweight="bold")


def _outcome_panel(ax: plt.Axes, raw: list[dict[str, str]]) -> None:
    miku = [row for row in raw if row["method"] == "MIKU"]
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for row in miku:
        if int(row["success"]):
            outcome = "Success"
        elif int(row["collision"]):
            outcome = "Collision"
        else:
            outcome = "Safe non-arrival"
        grouped[row["case_kind"]][outcome] += 1
    x = np.arange(len(FAMILIES))
    bottom = np.zeros(len(FAMILIES))
    colors = {"Success": "#009E73", "Safe non-arrival": "#E69F00", "Collision": "#CC3311"}
    for outcome in ("Success", "Safe non-arrival", "Collision"):
        values = np.array(
            [100 * grouped[name][outcome] / sum(grouped[name].values()) for name in FAMILIES]
        )
        ax.bar(x, values, bottom=bottom, color=colors[outcome], width=0.76, label=outcome)
        bottom += values
    ax.set_xticks(x, [FAMILY_LABELS[name] for name in FAMILIES], rotation=32, ha="right")
    ax.set_ylim(0.0, 112.0)
    ax.set_ylabel("Share of MIKU cases (%)")
    ax.set_title("d  Failure and degradation profile", loc="left", fontweight="bold")
    ax.legend(frameon=False, ncol=3, loc="upper center")


def generate(data_dir: Path) -> tuple[Path, Path]:
    _configure_plotting()
    raw = _read_rows(data_dir / "randomized_raw.csv")
    paired = _read_rows(data_dir / "paired_statistics.csv")
    ablation = _read_rows(data_dir / "randomized_ablation_paired.csv")

    figure, axes = plt.subplots(2, 2, figsize=(7.15, 6.0), constrained_layout=True)
    _family_effect_panel(axes[0, 0], paired)
    _runtime_panel(axes[0, 1], raw)
    _ablation_panel(axes[1, 0], ablation)
    _outcome_panel(axes[1, 1], raw)

    pdf_path = data_dir / "evidence_dashboard.pdf"
    png_path = data_dir / "evidence_dashboard.png"
    figure.savefig(
        pdf_path,
        bbox_inches="tight",
        metadata={"Creator": "generate_submission_figures.py", "CreationDate": None},
    )
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return pdf_path, png_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    arguments = parser.parse_args()
    pdf_path, png_path = generate(arguments.data_dir)
    print(f"wrote {pdf_path}")
    print(f"wrote {png_path}")


if __name__ == "__main__":
    main()
