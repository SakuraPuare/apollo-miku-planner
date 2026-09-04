"""Generate reproducible trajectory-level failure-boundary diagnostics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "可视化") not in sys.path:
    sys.path.insert(0, str(ROOT / "可视化"))

from experiment_cases import generate_case  # noqa: E402
from experiment_methods import method_by_key, run_method  # noqa: E402
from experiment_metrics import evaluate_run, trajectory_from_run  # noqa: E402


CASES = (("delayed_crossing", 9), ("prediction_noise", 18))
METHODS = ("B0", "MIKU")
COLORS = {"B0": "#6F7782", "MIKU": "#009E73"}


def _configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.0,
            "axes.titlesize": 9.0,
            "axes.labelsize": 8.0,
            "legend.fontsize": 7.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "axes.axisbelow": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _collision_time(trajectory, truth) -> float | None:
    for index, t in enumerate(trajectory.time_s):
        ego_s = float(trajectory.longitudinal_m[index])
        ego_l = float(trajectory.lateral_m[index])
        for obstacle in truth.obstacles:
            obs_s, obs_l = obstacle.position_at(float(t))
            ds = abs(ego_s - obs_s) - (truth.ego.L + obstacle.L) / 2.0
            dl = abs(ego_l - obs_l) - (truth.ego.W + obstacle.W) / 2.0
            if ds < 0.0 and dl < 0.0:
                return float(t)
    return None


def _outcome(row: dict) -> str:
    if int(row["success"]):
        return "success"
    if int(row["collision"]):
        return "collision"
    if int(row["degraded_stop"]):
        return "safe stop"
    return "safe non-arrival"


def _label(method: str, row: dict, result: dict) -> str:
    status = result.get("joint_search_status")
    certificate = f", {status}" if status else ""
    decisions = result.get("time_window_decisions") or []
    labels = [item.get("homotopy_label") for item in decisions if item.get("homotopy_label")]
    homotopy = "/".join(labels) if labels else "fixed/no label"
    return f"{method}: {_outcome(row)} [{homotopy}]{certificate}"


def _plot_case(axes, kind: str, seed: int) -> None:
    ax_sl, ax_st = axes
    case = generate_case(kind, seed)
    trajectories = {}
    rows = {}
    runs = {}
    for method in METHODS:
        run = run_method(method_by_key(method), case.planning_scenario)
        runs[method] = run
        rows[method] = evaluate_run(run, case)
        trajectories[method] = trajectory_from_run(run, case.truth_scenario)

    all_s = [case.truth_scenario.ego.s0, case.truth_scenario.s_max]
    for obstacle in case.truth_scenario.obstacles:
        all_s.extend([obstacle.s0 - obstacle.L, obstacle.s0 + obstacle.L])
    s_min, s_max = min(all_s) - 1.0, max(all_s) + 1.0
    t_max = max(float(traj.time_s[-1]) for traj in trajectories.values())
    sample_t = np.linspace(0.0, t_max, 180)

    for obstacle in case.truth_scenario.obstacles:
        obs_s = np.array([obstacle.position_at(float(t))[0] for t in sample_t])
        obs_l = np.array([obstacle.position_at(float(t))[1] for t in sample_t])
        ax_sl.fill_between(
            obs_s,
            obs_l - obstacle.W / 2.0,
            obs_l + obstacle.W / 2.0,
            color="#CC3311",
            alpha=0.12,
            linewidth=0,
        )
        # A moving obstacle is a curve in S-L; the translucent S-T band below
        # carries its longitudinal extent, while this line exposes its lateral
        # crossing even when station is nearly constant.
        ax_sl.plot(obs_s, obs_l, color="#CC3311", linewidth=2.0, alpha=0.75)
        ax_sl.scatter(obs_s[::8], obs_l[::8], color="#CC3311", s=5, alpha=0.3)
        ax_st.fill_betweenx(
            sample_t,
            obs_s - obstacle.L / 2.0,
            obs_s + obstacle.L / 2.0,
            color="#CC3311",
            alpha=0.20,
            linewidth=0,
        )

    for method in METHODS:
        trajectory = trajectories[method]
        row = rows[method]
        color = COLORS[method]
        ax_sl.plot(
            trajectory.longitudinal_m,
            trajectory.lateral_m,
            color=color,
            linewidth=1.7,
            label=_label(method, row, runs[method].result),
        )
        ax_st.plot(
            trajectory.longitudinal_m,
            trajectory.time_s,
            color=color,
            linewidth=1.7,
        )
        collision_time = _collision_time(trajectory, case.truth_scenario)
        if collision_time is not None:
            index = int(np.argmin(np.abs(trajectory.time_s - collision_time)))
            ax_sl.scatter(
                trajectory.longitudinal_m[index],
                trajectory.lateral_m[index],
                color="#CC3311",
                edgecolor="white",
                linewidth=0.5,
                s=32,
                zorder=5,
            )
            ax_st.scatter(
                trajectory.longitudinal_m[index],
                collision_time,
                color="#CC3311",
                edgecolor="white",
                linewidth=0.5,
                s=32,
                zorder=5,
            )
            ax_st.annotate(
                f"collision t={collision_time:.1f}s",
                (trajectory.longitudinal_m[index], collision_time),
                xytext=(5, 4),
                textcoords="offset points",
                fontsize=6.5,
                color="#CC3311",
            )

    title = "Delayed crossing" if kind == "delayed_crossing" else "Prediction noise"
    ax_sl.set_title(f"{title} (seed {seed})", loc="left", fontweight="bold")
    ax_sl.set_xlabel("Longitudinal station s (m)")
    ax_sl.set_ylabel("Lateral offset l (m)")
    ax_sl.set_xlim(s_min, s_max)
    ax_sl.legend(frameon=False, loc="best")
    ax_sl.axhline(case.truth_scenario.ego.l0, color="#999999", linewidth=0.6, linestyle="--")

    ax_st.set_xlabel("Longitudinal station s (m)")
    ax_st.set_ylabel("Time t (s)")
    ax_st.set_xlim(s_min, s_max)
    ax_st.set_ylim(0.0, t_max)
    ax_st.invert_yaxis()
    ax_st.set_title("Occupancy and temporal outcome", loc="left", fontweight="bold")


def generate(output_dir: Path) -> tuple[Path, Path]:
    _configure()
    figure, axes = plt.subplots(2, 2, figsize=(7.15, 6.2), constrained_layout=True)
    for row_axes, (kind, seed) in zip(axes, CASES):
        _plot_case(row_axes, kind, seed)
    figure.suptitle(
        "Trajectory-level failure boundaries from deterministic experiment cases",
        fontsize=10,
    )
    pdf_path = output_dir / "failure_case_qualitative.pdf"
    png_path = output_dir / "failure_case_qualitative.png"
    figure.savefig(
        pdf_path,
        bbox_inches="tight",
        metadata={"Creator": "generate_failure_case_figure.py", "CreationDate": None},
    )
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return pdf_path, png_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "小论文-2" / "generated")
    arguments = parser.parse_args()
    pdf_path, png_path = generate(arguments.output_dir)
    print(f"wrote {pdf_path}")
    print(f"wrote {png_path}")


if __name__ == "__main__":
    main()
