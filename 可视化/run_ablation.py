# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "matplotlib>=3.8",
#     "numpy>=1.26",
#     "scipy>=1.11",
#     "osqp>=0.6.3",
# ]
# ///
"""MIKU 消融实验主控脚本 — 6 变体 × 4 场景全跑，输出 ablation.csv / ablation.json。

变体定义（论文第八章第六节表）：

    M0_baseline   — Apollo 原始流程（IsStatic 过滤 + 逐障碍物贪心 nudge）
    M1_no_C1      — 仅关闭 C1 时变 SL 投影 (τ-shift)
    M2_no_C2C3    — 关闭 C2 扫描线分组 与 C3 组内 max-gap
    M3_no_C4      — 关闭 C4 多因子差异化裕度 δ_i
    M4_no_C5      — 关闭 C5 ST 走廊注入
    M5_full       — 完整 MIKU

每个变体在每个场景下输出 13 列指标，落盘 CSV 给 metric_score.py 与 pgfplots 直接吃。
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from dataclasses import asdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apollo_pipeline import (  # noqa: E402
    AblationFlags,
    SCENARIOS,
    SCENARIO_META,
    compute_metrics,
    run_pipeline,
)


VARIANTS = [
    AblationFlags(False, False, False, False, False, "M0_baseline"),
    AblationFlags(False, True,  True,  True,  True,  "M1_no_C1"),
    AblationFlags(True,  False, False, True,  True,  "M2_no_C2C3"),
    AblationFlags(True,  True,  True,  False, True,  "M3_no_C4"),
    AblationFlags(True,  True,  True,  True,  False, "M4_no_C5"),
    AblationFlags(True,  True,  True,  True,  True,  "M5_full"),
]

METRIC_COLUMNS = [
    "scenario", "variant",
    "C1_tau", "C2_group", "C3_maxgap", "C4_delta", "C5_corridor",
    "success", "blocked",
    "v_avg", "t_arrive", "s_end", "s_target",
    "jerk_rms", "a_y_max", "kappa_rms",
    "l_max_dev", "tau_violation", "decision_switches",
    "qp_path_ms", "qp_speed_ms", "qp_total_ms",
]


def _metric_row(scn_name: str, flags: AblationFlags, scn, m, r) -> dict:
    """把 compute_metrics 的输出展平到 CSV 行。"""
    qp = m.get("qp_solve_ms", {"path": 0.0, "speed": 0.0, "total": 0.0})
    is_inf = bool(m.get("_infeasible"))

    def _safe(key, default=0.0):
        val = m.get(key)
        return default if val is None else float(val)

    t_arrive = m.get("t_arrive")
    if t_arrive is None or (isinstance(t_arrive, float) and math.isnan(t_arrive)):
        # 未通过场景：t_arrive 用场景 t_max + 显著惩罚（5 s）以便归一化时正确扣分
        t_arrive_val = float(scn.t_max) + 5.0
    else:
        t_arrive_val = float(t_arrive)

    s_end_val = m.get("s_end")
    if s_end_val is None:
        s_qp = r.get("s_qp")
        s_end_val = float(s_qp[-1]) if s_qp is not None and len(s_qp) > 0 else 0.0

    return {
        "scenario": scn_name,
        "variant": flags.name,
        "C1_tau":      int(flags.tau_shift),
        "C2_group":    int(flags.grouping),
        "C3_maxgap":   int(flags.max_gap),
        "C4_delta":    int(flags.threat_delta),
        "C5_corridor": int(flags.corridor_inject),
        "success": int(m.get("success", 0) and not is_inf),
        "blocked": int(m.get("blocked", 0)),
        "v_avg":    round(_safe("avg_v"), 4),
        "t_arrive": round(t_arrive_val, 4),
        "s_end":    round(float(s_end_val), 4),
        "s_target": round(float(scn.s_max - 1.0), 4),
        "jerk_rms": round(_safe("jerk_rms"), 4),
        "a_y_max":  round(_safe("max_abs_a_lat"), 4),
        "kappa_rms": round(_safe("kappa_rms"), 6),
        "l_max_dev": round(_safe("l_max_dev"), 4),
        "tau_violation":     int(m.get("tau_violation", 0) or 0),
        "decision_switches": int(m.get("decision_switches", 0) or 0),
        "qp_path_ms":  round(qp.get("path", 0.0), 4),
        "qp_speed_ms": round(qp.get("speed", 0.0), 4),
        "qp_total_ms": round(qp.get("total", 0.0), 4),
    }


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "图片", "data", "ablation")
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    print(f"{'场景':<24}{'变体':<14}{'success':>8}{'v_avg':>8}{'t_arr':>8}"
          f"{'jerk':>8}{'l_dev':>8}{'switches':>10}{'qp_ms':>9}")
    print("-" * 100)
    for scn_name, scn in SCENARIOS.items():
        for flags in VARIANTS:
            r = run_pipeline(flags, scn)
            m = compute_metrics(r, scn)
            row = _metric_row(scn_name, flags, scn, m, r)
            rows.append(row)
            print(f"{scn_name:<24}{flags.name:<14}"
                  f"{row['success']:>8d}{row['v_avg']:>8.2f}"
                  f"{row['t_arrive']:>8.2f}{row['jerk_rms']:>8.2f}"
                  f"{row['l_max_dev']:>8.2f}"
                  f"{row['decision_switches']:>10d}"
                  f"{row['qp_total_ms']:>9.2f}")
        print("-" * 100)

    csv_path = os.path.join(out_dir, "ablation.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=METRIC_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f"\n→ {csv_path}  ({len(rows)} rows)")

    json_path = os.path.join(out_dir, "ablation.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "variants": [asdict(v) for v in VARIANTS],
            "scenarios": list(SCENARIO_META.items()),
            "rows": rows,
        }, f, ensure_ascii=False, indent=2)
    print(f"→ {json_path}")


if __name__ == "__main__":
    main()
