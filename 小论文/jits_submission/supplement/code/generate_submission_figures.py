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
DEFAULT_DATA = ROOT / "data" / "小论文-2" / "generated"
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
    "parked_and_oncoming": "Parked / oncoming",
    "narrow_multi_obstacle": "Narrow",
    "interleaved_dynamic": "Interleaved",
    "prediction_noise": "Prediction noise",
    "delayed_crossing": "Delayed crossing",
}
FAMILY_SHORT_LABELS = {
    **FAMILY_LABELS,
    "parked_and_oncoming": "Parked / oncoming",
    "prediction_noise": "Pred. noise",
    "delayed_crossing": "Delayed crossing",
}
FAMILY_TINY_LABELS = {
    "crossing_pedestrian": "Crossing",
    "vehicle_cut_in": "Cut-in",
    "parked_and_oncoming": "Parked",
    "narrow_multi_obstacle": "Narrow",
    "interleaved_dynamic": "Interleaved",
    "prediction_noise": "Pred. noise",
    "delayed_crossing": "Delayed",
}
# A restrained palette keeps the figure legible after grayscale printing.  The
# teal is used only for the proposed method and the headline effects.
INK = "#1F2933"
MID = "#66727D"
LIGHT = "#E9EDF0"
GRID = "#D7DDE2"
ACCENT = "#007C83"
ACCENT_LIGHT = "#E5F1F1"

METHOD_STYLES = {
    "B0": {"color": "#7A858E", "ls": "--", "lw": 1.05, "label": "B0"},
    "B1": {"color": "#AAB2B8", "ls": ":", "lw": 1.15, "label": "B1"},
    "B2": {"color": INK, "ls": "-.", "lw": 1.05, "label": "B2"},
    "MIKU": {"color": ACCENT, "ls": "-", "lw": 1.8, "label": "MIKU"},
}

# Short labels are intentional: the full component names are given in the
# ablation table, while this compact panel should remain readable at 34pc.
ABLATION_LABELS = {
    "A1": "A1 proj.",
    "A2": "A2 grouping",
    "A3": "A3 spatial H",
    "A4": "A4 threat",
    "A5": "A5 temporal H",
    "A6": "A6 robust tube",
    "A7": "A7 refine",
}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _configure_plotting() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "mathtext.fontset": "cm",
            "font.size": 7.4,
            "axes.titlesize": 8.5,
            "axes.labelsize": 7.3,
            "legend.fontsize": 6.8,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": True,
            "axes.spines.bottom": True,
            "axes.edgecolor": INK,
            "axes.linewidth": 0.7,
            "axes.grid": True,
            "axes.grid.axis": "both",
            "grid.alpha": 0.8,
            "grid.color": GRID,
            "grid.linestyle": "-",
            "grid.linewidth": 0.45,
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

    # Keep the two headline gains visible without turning every row into a
    # colored band.  The alternating gray rows also survive photocopying.
    for idx in range(len(FAMILIES)):
        if idx % 2 == 1:
            ax.axhspan(idx - 0.45, idx + 0.45, color="#F7F9FA", zorder=0)
    for idx in (3, 6):
        ax.axhspan(idx - 0.45, idx + 0.45, color=ACCENT_LIGHT, zorder=0)

    ax.axvline(0.0, color=INK, linewidth=0.85, linestyle="--", zorder=1)

    colors = [ACCENT if val > 0.5 else MID for val in means]
    ax.errorbar(
        means,
        y,
        xerr=np.vstack((means - lows, highs - means)),
        fmt="none",
        ecolor=INK,
        elinewidth=1.15,
        capsize=2.6,
        capthick=1.0,
        zorder=3,
    )
    ax.scatter(means, y, c=colors, s=27, edgecolors=INK, linewidths=0.65, zorder=4)

    # Numeric callouts make the key result readable without consulting the
    # paragraph, while retaining the confidence intervals as the primary mark.
    for idx, mean in enumerate(means):
        label = f"{mean:+.1f} pp" if abs(mean) > 0.05 else "0.0 pp"
        x_label = highs[idx] + 1.5 if mean > 0.05 else 1.5
        ax.text(
            x_label,
            y[idx] - 0.16,
            label,
            fontsize=7.0 if idx in (3, 6) else 6.4,
            color=ACCENT if mean > 0.05 else MID,
            fontweight="bold" if idx in (3, 6) else "normal",
            ha="left",
            va="center",
        )

    ax.set_yticks(y, [FAMILY_SHORT_LABELS[name] for name in FAMILIES])
    ax.invert_yaxis()
    ax.set_xlim(-4.0, 78.0)
    ax.set_xticks([0, 20, 40, 60])
    ax.set_xlabel("MIKU - B0 success difference (pp)")
    ax.set_title(r"$\mathbf{a}$  Family-level success gain (95% CI)", loc="left", pad=5)


def _runtime_panel(ax: plt.Axes, raw: list[dict[str, str]]) -> None:
    for method in ("B0", "B1", "B2", "MIKU"):
        values = np.sort(
            np.array(
                [float(row["runtime_ms"]) for row in raw if row["method"] == method],
                dtype=float,
            )
        )
        probability = np.arange(1, len(values) + 1) / len(values)
        style = METHOD_STYLES[method]
        ax.step(
            values,
            probability,
            where="post",
            color=style["color"],
            linestyle=style["ls"],
            linewidth=style["lw"],
            label=style["label"],
            zorder=3 if method == "MIKU" else 2,
        )

    # Quantile guides are deliberately faint so that the curves remain the
    # visual focus.
    ax.axhline(0.50, color=GRID, linestyle="--", linewidth=0.65, zorder=1)
    ax.axhline(0.95, color=GRID, linestyle=":", linewidth=0.65, zorder=1)

    ax.set_xscale("log")
    ax.set_ylim(0.0, 1.02)
    ax.set_xlim(2.5, 1200)
    ax.set_xlabel("Planning latency (ms; log)")
    ax.set_ylabel("ECDF")
    ax.set_title(r"$\mathbf{b}$  Latency ECDF", loc="left", pad=4, fontsize=8.0)
    ax.legend(
        frameon=False,
        ncol=2,
        loc="lower right",
        handlelength=1.7,
        columnspacing=0.7,
        borderaxespad=0.1,
    )

    # Annotate MIKU median latency
    ax.scatter([9.98], [0.50], color=ACCENT, s=23, zorder=5, edgecolors=INK, linewidths=0.65)
    ax.annotate(
        "MIKU P50 9.98 ms",
        xy=(9.98, 0.50),
        xytext=(3.7, 0.69),
        arrowprops=dict(arrowstyle="->", color=ACCENT, lw=0.8, shrinkA=1, shrinkB=2),
        fontsize=6.3,
        color=ACCENT,
        fontweight="bold",
    )


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

    for idx in range(len(labels)):
        if idx % 2 == 1:
            ax.axhspan(idx - 0.45, idx + 0.45, color="#F7F9FA", zorder=0)
    for idx in (2, 3):
        ax.axhspan(idx - 0.45, idx + 0.45, color=ACCENT_LIGHT, zorder=0)

    ax.axvline(0.0, color=INK, linewidth=0.85, linestyle="--", zorder=1)

    colors = [ACCENT if val >= 5.0 else MID for val in means]
    ax.errorbar(
        means,
        y,
        xerr=np.vstack((means - lows, highs - means)),
        fmt="none",
        ecolor=INK,
        elinewidth=1.1,
        capsize=2.5,
        capthick=1.0,
        zorder=3,
    )
    ax.scatter(means, y, c=colors, s=26, edgecolors=INK, linewidths=0.65, zorder=4)

    # Callouts for the two components that dominate the aggregate effect.
    for idx in (2, 3):
        ax.text(
            means[idx] + 0.35,
            y[idx] - 0.16,
            f"-{means[idx]:.2f} pp",
            fontsize=6.4,
            color=ACCENT,
            fontweight="bold",
            va="center",
        )
    ax.text(
        means[4] + 0.35,
        y[4] - 0.16,
        f"-{means[4]:.2f} pp",
        fontsize=6.2,
        color=MID,
        va="center",
    )

    ax.set_yticks(y, [ABLATION_LABELS[lbl] for lbl in labels])
    ax.invert_yaxis()
    ax.set_xlim(-0.5, 12.4)
    ax.set_xticks([0, 5, 10])
    ax.set_xlabel("Success drop (pp)")
    ax.set_title(r"$\mathbf{c}$  Ablation effects", loc="left", pad=4, fontsize=8.0)


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

    y = np.arange(len(FAMILIES))
    left = np.zeros(len(FAMILIES))

    # Solid fill and hatching encode the outcomes independently of color.
    colors = {"Success": INK, "Safe non-arrival": "#D6DDE2", "Collision": "#FFFFFF"}
    hatches = {"Success": "", "Safe non-arrival": "///", "Collision": "xxx"}
    legend_labels = {"Success": "Success", "Safe non-arrival": "Safe stop", "Collision": "Collision"}

    success_values = None
    for outcome in ("Success", "Safe non-arrival", "Collision"):
        values = np.array(
            [100 * grouped[name][outcome] / sum(grouped[name].values()) for name in FAMILIES]
        )
        if outcome == "Success":
            success_values = values
        ax.barh(
            y,
            values,
            left=left,
            color=colors[outcome],
            hatch=hatches[outcome],
            edgecolor=INK,
            linewidth=0.55,
            height=0.68,
            label=legend_labels[outcome],
            zorder=3,
        )
        left += values

    # Label the two headline family outcomes inside the dark success segment.
    for idx in (3, 6):
        ax.text(
            success_values[idx] - 1.4,
            y[idx],
            f"{success_values[idx]:.0f}%",
            ha="right",
            va="center",
            color="white",
            fontsize=6.1,
            fontweight="bold",
            zorder=4,
        )

    ax.set_yticks(y, [FAMILY_TINY_LABELS[name] for name in FAMILIES])
    ax.invert_yaxis()
    # Reserve a slim empty row above the first bar for the outcome key; this
    # keeps the key attached to panel (d) without crossing into panel (c).
    ax.set_ylim(len(FAMILIES) - 0.5, -1.25)
    ax.set_xlim(0.0, 100.0)
    ax.set_xticks([0, 50, 100])
    ax.set_xlabel("MIKU cases (%)")
    ax.set_title(r"$\mathbf{d}$  Outcome profile", loc="left", pad=4, fontsize=8.0)
    ax.legend(
        frameon=False,
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.99),
        columnspacing=0.25,
        handlelength=0.9,
        handletextpad=0.25,
        fontsize=5.5,
    )


def generate(data_dir: Path) -> tuple[Path, Path]:
    _configure_plotting()
    raw = _read_rows(data_dir / "randomized_raw.csv")
    paired = _read_rows(data_dir / "paired_statistics.csv")
    ablation = _read_rows(data_dir / "randomized_ablation_paired.csv")

    # The manuscript is set at 34pc.  Designing at that width avoids a second
    # round of down-scaling in LaTeX and gives the headline panel clear visual
    # priority over the three supporting diagnostics.
    figure = plt.figure(figsize=(5.65, 5.95))
    grid = figure.add_gridspec(
        2,
        3,
        height_ratios=(1.23, 1.0),
        hspace=0.28,
        wspace=0.72,
    )
    main_ax = figure.add_subplot(grid[0, :])
    runtime_ax = figure.add_subplot(grid[1, 0])
    ablation_ax = figure.add_subplot(grid[1, 1])
    outcome_ax = figure.add_subplot(grid[1, 2])

    _family_effect_panel(main_ax, paired)
    _runtime_panel(runtime_ax, raw)
    _ablation_panel(ablation_ax, ablation)
    _outcome_panel(outcome_ax, raw)

    figure.subplots_adjust(left=0.14, right=0.985, top=0.965, bottom=0.12)

    # Keep auxiliary panels quiet: their marks carry the comparison, while
    # the shared grid and panel titles provide the visual hierarchy.
    for axis in (main_ax, runtime_ax, ablation_ax, outcome_ax):
        axis.tick_params(which="both", length=2.5, width=0.65, color=INK, pad=2)
        axis.grid(axis="y", visible=False)

    pdf_path = data_dir / "evidence_dashboard.pdf"
    png_path = data_dir / "evidence_dashboard.png"
    figure.savefig(
        pdf_path,
        bbox_inches="tight",
        pad_inches=0.03,
        metadata={"Creator": "generate_submission_figures.py", "CreationDate": None},
    )
    figure.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.03)
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
