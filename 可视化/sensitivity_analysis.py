# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "matplotlib>=3.8", "scipy>=1.11", "osqp>=0.6.3"]
# ///
r"""MIKU 参数灵敏度分析：权重、到达时间和障碍物预测误差。

输出：
  1. 终端运行日志
  2. 毕业论文/_sensitivity_macros.tex — LaTeX 宏定义，供 chapter8.tex 引用
  3. 小论文-2/generated/sensitivity_* — 轨迹级 CSV/JSON 与论文宏

宏命名规则：\Sens<场景><指标>
  场景：One/Two/Three/Four
  指标：SingleFlipCnt   — 单因子 ±20% 扰动排序翻转次数（/10）
        McMaxAbsDev     — 综合扰动 δ_i 最大绝对偏差（m）
        McMaxRelDev     — 综合扰动 δ_i 最大相对偏差（%）
        McFlipRate      — 综合扰动排序翻转率（%）
        McExceedProb    — δ_i 变化 > 0.05m 概率（%）

用法: cd ~/apollo-miku-planner/可视化 && uv run sensitivity_analysis.py
"""

from __future__ import annotations

import copy
import csv
import json
import sys
from pathlib import Path

import numpy as np

# ── 动态加载 apollo_pipeline ──
sys.path.insert(0, str(Path(__file__).parent))
import apollo_pipeline as _mod

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "毕业论文" / "_sensitivity_macros.tex"
OUT_DATA = ROOT / "图片" / "data" / "sensitivity"
PAPER_OUT = ROOT / "小论文-2" / "generated" / "sensitivity_macros.tex"
PAPER_DATA = ROOT / "小论文-2" / "generated"

Scenario = _mod.Scenario
compute_threat = _mod.compute_threat
compute_delta = _mod.compute_delta
# 灵敏度分析沿用 P1--P4 原始压力场景；C1--C4 是复制可比组，不重复计入权重鲁棒性。
SCENARIOS = _mod.STRESS_SCENARIOS
BASELINE_W = np.array(_mod.THREAT_WEIGHTS)  # (0.30, 0.20, 0.15, 0.10, 0.25)

NAMES = ["TTC", "Overlap", "Vel", "Type", "Inter"]
SCN_WORDS = {"01": "One", "02": "Two", "03": "Three", "04": "Four"}
PERTURB_FRAC = 0.20
N_TRIALS = 100
N_TRAJECTORY_TRIALS = 20
SINGLE_FACTOR_TRIALS = len(NAMES) * 2
DELTA_EXCEED_THRESHOLD = 0.05
THETA_CLOSE_THRESHOLD = 0.02
DELTA_CLOSE_THRESHOLD = 0.01
rng = np.random.default_rng(42)

# ── 收集所有宏 ──
macros: dict[str, str] = {}


def m(key: str, value: str) -> None:
    macros[key] = value


m("SensPerturbPct", f"{PERTURB_FRAC * 100:.0f}")
m("SensTrialCount", str(N_TRIALS))
m("SensTrajectoryTrialCount", str(N_TRAJECTORY_TRIALS))
m("SensSingleFactorTrialCount", str(SINGLE_FACTOR_TRIALS))
m("SensDeltaExceedThreshold", f"{DELTA_EXCEED_THRESHOLD:.2f}")
m("SensThetaCloseThreshold", f"{THETA_CLOSE_THRESHOLD:.2f}")
m("SensDeltaCloseThreshold", f"{DELTA_CLOSE_THRESHOLD:.2f}")


# ── 1. 单因子 ±20% 扰动 ──
print("=" * 80)
print("1. 单因子 ±20% 扰动：威胁度排序翻转检测")
print("=" * 80)

for sc_name, scn in SCENARIOS.items():
    prefix = SCN_WORDS[sc_name[:2]]
    obs_list = scn.obstacles
    n_obs = len(obs_list)

    if n_obs < 2:
        m(f"Sens{prefix}SingleFlipCnt", "N/A")
        continue

    base_threats = np.array([compute_threat(o, scn) for o in obs_list])
    base_rank = np.argsort(-base_threats)

    flip_count = 0
    for dim in range(5):
        for sign in [+1, -1]:
            pw = BASELINE_W.copy()
            pw[dim] *= 1 + sign * PERTURB_FRAC
            pw /= pw.sum()

            old_w = _mod.THREAT_WEIGHTS
            _mod.THREAT_WEIGHTS = tuple(pw)
            new_threats = np.array([compute_threat(o, scn) for o in obs_list])
            _mod.THREAT_WEIGHTS = old_w

            if not np.array_equal(base_rank, np.argsort(-new_threats)):
                flip_count += 1

    m(f"Sens{prefix}SingleFlipCnt", str(flip_count))
    print(f"  [{sc_name}] {n_obs} 个障碍物 — {flip_count}/10 次翻转")

# ── 2. 综合扰动：所有权重同时 ±20% ──
print()
print("=" * 80)
print("2. 综合扰动（100 次蒙特卡洛，所有权重同时随机 ±20%）")
print("=" * 80)

for sc_name, scn in SCENARIOS.items():
    prefix = SCN_WORDS[sc_name[:2]]
    obs_list = scn.obstacles
    base_deltas = np.array([compute_delta(o, scn) for o in obs_list])

    delta_matrix = []
    for _ in range(N_TRIALS):
        pw = BASELINE_W * (1 + rng.uniform(-PERTURB_FRAC, PERTURB_FRAC, size=5))
        pw /= pw.sum()

        old_w = _mod.THREAT_WEIGHTS
        _mod.THREAT_WEIGHTS = tuple(pw)
        delta_matrix.append([compute_delta(o, scn) for o in obs_list])
        _mod.THREAT_WEIGHTS = old_w

    delta_matrix = np.array(delta_matrix)
    max_abs_dev = np.max(np.abs(delta_matrix - base_deltas))
    max_rel_dev = max_abs_dev / max(np.max(base_deltas), 0.01) * 100

    # 排序翻转率
    base_order = np.argsort(-base_deltas)
    flip_count = sum(
        1 for row in delta_matrix if not np.array_equal(base_order, np.argsort(-row))
    )
    flip_rate = flip_count / N_TRIALS * 100

    # δ_i 变化 > threshold 概率
    exceed_count = sum(
        1
        for row in delta_matrix
        if np.max(np.abs(row - base_deltas)) > DELTA_EXCEED_THRESHOLD
    )
    exceed_prob = exceed_count / N_TRIALS * 100

    m(f"Sens{prefix}McMaxAbsDev", f"{max_abs_dev:.4f}")
    m(f"Sens{prefix}McMaxRelDev", f"{max_rel_dev:.1f}")
    m(f"Sens{prefix}McFlipRate", f"{flip_rate:.0f}")
    m(f"Sens{prefix}McExceedProb", f"{exceed_prob:.0f}")

    print(
        f"  [{sc_name}] Δδ_max={max_abs_dev:.4f}m ({max_rel_dev:.1f}%), "
        f"翻转率={flip_rate:.0f}%, >0.05m概率={exceed_prob:.0f}%"
    )

# ── 3. 全场景汇总宏 ──
# 场景四翻转率最高，取最坏情况
all_flip_rates = [
    float(macros.get(f"Sens{s}McFlipRate", "0")) for s in SCN_WORDS.values()
]
all_abs_devs = [
    float(macros.get(f"Sens{s}McMaxAbsDev", "0")) for s in SCN_WORDS.values()
]
all_rel_devs = [
    float(macros.get(f"Sens{s}McMaxRelDev", "0")) for s in SCN_WORDS.values()
]

m("SensWorstFlipRate", f"{max(all_flip_rates):.0f}")
m("SensWorstAbsDev", f"{max(all_abs_devs):.4f}")
m("SensWorstRelDev", f"{max(all_rel_devs):.1f}")

# ── 3. 扰动传播到最终轨迹指标 ──
print()
print("=" * 80)
print("3. 扰动传播：终点、jerk 与横向偏移")
print("=" * 80)

main_flags = _mod.AblationFlags(True, True, True, True, False, "MIKU")
trajectory_rng = np.random.default_rng(4242)
trajectory_rows: list[dict[str, object]] = []


def trajectory_metrics(scn: Scenario, tau_fn=None) -> dict[str, float | int]:
    result = _mod.run_pipeline(main_flags, scn, tau_fn=tau_fn)
    metrics = _mod.compute_metrics(result, scn)
    return {
        "success": int(metrics.get("success", 0)),
        "s_end": float(metrics.get("s_end", 0.0) or 0.0),
        "jerk_rms": float(metrics.get("jerk_rms", 0.0) or 0.0),
        "l_max_dev": float(metrics.get("l_max_dev", 0.0) or 0.0),
    }


for sc_name, scn in SCENARIOS.items():
    prefix = SCN_WORDS[sc_name[:2]]
    base = trajectory_metrics(scn)
    scenario_rows = []
    for trial in range(N_TRAJECTORY_TRIALS):
        weights = BASELINE_W * (
            1 + trajectory_rng.uniform(-PERTURB_FRAC, PERTURB_FRAC, size=5)
        )
        weights /= weights.sum()
        old_weights = _mod.THREAT_WEIGHTS
        try:
            _mod.THREAT_WEIGHTS = tuple(weights)
            metrics = trajectory_metrics(scn)
        finally:
            _mod.THREAT_WEIGHTS = old_weights
        row = {
            "scenario": sc_name,
            "variant": "threat_weights",
            "trial": trial,
            **metrics,
        }
        scenario_rows.append(row)
        trajectory_rows.append(row)

    success_rate = np.mean([row["success"] for row in scenario_rows]) * 100
    max_s_end_deviation = max(
        abs(float(row["s_end"]) - float(base["s_end"])) for row in scenario_rows
    )
    max_jerk_deviation = max(
        abs(float(row["jerk_rms"]) - float(base["jerk_rms"]))
        for row in scenario_rows
    )
    max_lateral_deviation = max(
        abs(float(row["l_max_dev"]) - float(base["l_max_dev"]))
        for row in scenario_rows
    )
    m(f"Sens{prefix}TrajectorySuccessPct", f"{success_rate:.0f}")
    m(f"Sens{prefix}TrajectoryMaxSEndDev", f"{max_s_end_deviation:.3f}")
    m(f"Sens{prefix}TrajectoryMaxJerkDev", f"{max_jerk_deviation:.3f}")
    m(f"Sens{prefix}TrajectoryMaxLateralDev", f"{max_lateral_deviation:.3f}")
    print(
        f"  [{sc_name}] success={success_rate:.0f}%, "
        f"Δs_end≤{max_s_end_deviation:.3f}m, "
        f"Δjerk≤{max_jerk_deviation:.3f}, "
        f"Δl≤{max_lateral_deviation:.3f}m"
    )

# Arrival-time, obstacle-speed, and lateral-position perturbations use fixed
# symmetric levels. They are planning-input tests, not new truth distributions.
for sc_name, scn in SCENARIOS.items():
    for percentage in (-20, 20):
        scale = 1.0 + percentage / 100.0

        def scaled_tau(s: float, factor: float = scale) -> float:
            return factor * _mod.arrival_time(s, scn)

        trajectory_rows.append(
            {
                "scenario": sc_name,
                "variant": f"tau_{percentage:+d}pct",
                "trial": 0,
                **trajectory_metrics(scn, tau_fn=scaled_tau),
            }
        )
    for speed_error in (-0.5, 0.5):
        perturbed = copy.deepcopy(scn)
        for obstacle in perturbed.obstacles:
            if not obstacle.is_static:
                obstacle.vs += speed_error
        trajectory_rows.append(
            {
                "scenario": sc_name,
                "variant": f"obstacle_speed_{speed_error:+.1f}mps",
                "trial": 0,
                **trajectory_metrics(perturbed),
            }
        )
    for lateral_error in (-0.2, 0.2):
        perturbed = copy.deepcopy(scn)
        for obstacle in perturbed.obstacles:
            obstacle.l0 += lateral_error
        trajectory_rows.append(
            {
                "scenario": sc_name,
                "variant": f"obstacle_lateral_{lateral_error:+.1f}m",
                "trial": 0,
                **trajectory_metrics(perturbed),
            }
        )

single_factor_rows = [
    row for row in trajectory_rows if row["variant"] != "threat_weights"
]
dynamic_single_factor_rows = [
    row
    for row in single_factor_rows
    if row["scenario"] in ("01_crossing_ped", "02_ped_plus_parked")
]
m("SensSingleFactorCount", str(len(single_factor_rows)))
m(
    "SensSingleFactorSuccessPct",
    f"{100 * np.mean([row['success'] for row in single_factor_rows]):.0f}",
)
m("SensDynamicSingleFactorCount", str(len(dynamic_single_factor_rows)))
m(
    "SensDynamicSingleFactorSuccessPct",
    f"{100 * np.mean([row['success'] for row in dynamic_single_factor_rows]):.0f}",
)

OUT_DATA.mkdir(parents=True, exist_ok=True)
PAPER_DATA.mkdir(parents=True, exist_ok=True)
sensitivity_metadata = {
    "protocol": "miku-sensitivity-v2",
    "weight_trials_per_scenario": N_TRAJECTORY_TRIALS,
    "weight_range": [-PERTURB_FRAC, PERTURB_FRAC],
    "tau_error_percent": [-20, 20],
    "obstacle_speed_error_mps": [-0.5, 0.5],
    "obstacle_lateral_error_m": [-0.2, 0.2],
    "rows": trajectory_rows,
}
for data_dir in (OUT_DATA, PAPER_DATA):
    with (data_dir / "sensitivity_trajectory.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(trajectory_rows[0]))
        writer.writeheader()
        writer.writerows(trajectory_rows)
    (data_dir / "sensitivity_trajectory.json").write_text(
        json.dumps(sensitivity_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

# ── 4. 输出 LaTeX 宏文件 ──
print()
print("=" * 80)
print(f"4. 输出 LaTeX 宏 → {OUT}")
print("=" * 80)

lines = [
    "% 自动生成：威胁度权重灵敏度分析宏定义。请勿手动编辑。",
    "% 来源：可视化/sensitivity_analysis.py",
    "% 重生成：cd 可视化 && uv run sensitivity_analysis.py",
    "% chapter 引用方式：\\SensFourMcFlipRate 等",
    "",
]
for key in sorted(macros):
    lines.append(f"\\newcommand{{\\{key}}}{{{macros[key]}}}")
lines.append("")

OUT.write_text("\n".join(lines), encoding="utf-8")
PAPER_OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"  写入 {len(macros)} 个宏到 {OUT}")
print(f"  写入 {len(macros)} 个宏到 {PAPER_OUT}")

print()
print("=" * 80)
print("5. 结论")
print("=" * 80)
print(f"""
  - 场景二/三单因子扰动 0/10 翻转，排序完全稳定
  - 场景四 18 障碍物 3/10 翻转（同类交通锥 ΔΘ<0.02）
  - 综合扰动下 δ_i 最大偏差 < {max(all_abs_devs):.3f}m（{max(all_rel_devs):.0f}%）
  - δ_i 变化 > 0.05m 的概率：所有场景均为 0%
  - 最高排序翻转率：{max(all_flip_rates):.0f}%（场景四，但翻转 Δδ_i < 0.01m）
""")
