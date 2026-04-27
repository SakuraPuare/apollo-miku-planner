# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy>=1.26",
# ]
# ///
"""MIKU 消融实验综合评分 — 两层评分（硬门 + 软指标加权几何平均），输出 LaTeX 三件套。

输入：图片/data/ablation/ablation.csv（24 行 = 6 变体 × 4 场景）
输出：图片/data/ablation/
        - score_per_scenario.csv     单场景每变体得分（0-100）
        - score_overall.csv          全局排名（按 S_overall 降序）
        - score_table.tex            主表，pgfplots 直接 \\input
        - score_radar.tex            雷达图 4 维度 × 6 变体
        - score_heatmap.tex          热力图 6 变体 × 4 场景

设计要点：
1. 硬门：success==1 且 blocked==0 才进入软指标计算，否则该场景得 0
2. 归一化：以 M5_full 为 ref，越大越好用 x/ref，越小越好用 ref/x
3. 维度内部子指标等权乘积；维度间按权重几何平均
4. 全局对 4 场景几何平均，× 100 得 0-100 分
"""

from __future__ import annotations

import csv
import os
from collections import OrderedDict, defaultdict
from typing import Dict, List, Tuple

import numpy as np


HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "图片", "data", "ablation"))
THESIS_DIR = os.path.normpath(os.path.join(HERE, "..", "毕业论文"))


# 维度权重（论文 §8.6 评分体系）
DIM_WEIGHTS: Dict[str, float] = {
    "efficiency": 0.30,
    "smoothness": 0.30,
    "robustness": 0.25,
    "compute":    0.15,
}

# 维度内部子指标定义： (csv 列名, 是否「越小越好」)
DIM_METRICS: Dict[str, List[Tuple[str, bool]]] = {
    "efficiency": [("v_avg", False), ("t_arrive", True)],
    "smoothness": [("jerk_rms", True), ("a_y_max", True), ("kappa_rms", True)],
    "robustness": [("l_max_dev", True), ("tau_violation", True),
                   ("decision_switches", True)],
    "compute":    [("qp_total_ms", True)],
}

DIM_LABEL_ZH = {"efficiency": "通行效率", "smoothness": "轨迹平顺",
                 "robustness": "决策鲁棒", "compute": "计算开销"}

VARIANT_LABEL_ZH = {
    "M0_baseline": "M0 Apollo Baseline",
    "M1_no_C1":    "M1 MIKU w/o C1 (\\(\\tau\\)-shift)",
    "M2_no_C2C3":  "M2 MIKU w/o C2-C3 (grouping)",
    "M3_no_C4":    "M3 MIKU w/o C4 (\\(\\delta_i\\))",
    "M4_no_C5":    "M4 MIKU w/o C5 (corridor)",
    "M5_full":     "M5 MIKU Full",
}

REFERENCE_VARIANT = "M5_full"
EPS = 1e-3

# 注：以下三参数仅作论文 macro 描述用。运行时实际取值来自 apollo_pipeline.Scenario
# 默认；本脚本独立运行时为避免拉入完整模块栈，仅复刻常量。
DELTA_BASELINE = 0.30
DELTA_MIN = 0.10
DELTA_MAX = 0.40
# t_arrive 失败惩罚：来自 run_ablation.py `t_arrive_val = scn.t_max + 5.0`
FAIL_PENALTY_S = 5


# ============================ 数据加载 ============================

def load_rows() -> List[dict]:
    path = os.path.join(DATA_DIR, "ablation.csv")
    rows = []
    float_cols = ("v_avg", "t_arrive", "s_end", "s_target",
                  "jerk_rms", "a_y_max", "kappa_rms", "l_max_dev",
                  "qp_path_ms", "qp_speed_ms", "qp_total_ms")
    int_cols = ("success", "blocked", "tau_violation",
                "decision_switches", "C1_tau", "C2_group",
                "C3_maxgap", "C4_delta", "C5_corridor")
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in float_cols:
                if k in r:
                    r[k] = float(r[k])
            for k in int_cols:
                if k in r:
                    r[k] = int(r[k])
            rows.append(r)
    return rows


# ============================ 评分计算 ============================

def hard_gate(row: dict) -> int:
    return int(row["success"] == 1 and row["blocked"] == 0)


def normalize(value: float, ref: float, smaller_better: bool) -> float:
    if smaller_better:
        return (ref + EPS) / (value + EPS)
    return (value + EPS) / (ref + EPS)


def dim_score(row: dict, ref: dict, dim: str) -> float:
    metrics = DIM_METRICS[dim]
    score = 1.0
    n_sub = len(metrics)
    for name, smaller in metrics:
        n_val = normalize(row[name], ref[name], smaller)
        score *= n_val ** (1.0 / n_sub)
    return float(score)


def scenario_score(row: dict, ref: dict) -> Tuple[float, Dict[str, float]]:
    """返回单场景总分（0-1）与 4 维度子分（0-1）。"""
    dims = {d: dim_score(row, ref, d) for d in DIM_METRICS}
    G = hard_gate(row)
    if G == 0:
        return 0.0, {d: 0.0 for d in DIM_METRICS}
    total = 1.0
    for d, w in DIM_WEIGHTS.items():
        total *= dims[d] ** w
    return float(total), dims


def overall_score(scn_scores: List[float]) -> float:
    """N 场景几何平均 × 100。"""
    if not scn_scores:
        return 0.0
    arr = np.array([max(s, 0.0) for s in scn_scores])
    if (arr <= 0).any():
        # 任一场景 0 分 → 全局严重折损（取算术平均 × 0.5 防止全 0）
        return float(arr.mean() * 100 * 0.5)
    return float(np.exp(np.mean(np.log(arr))) * 100)


# ============================ 评分主流程 ============================

def compute_all_scores(rows: List[dict]) -> Tuple[List[dict], List[dict]]:
    by_scenario = defaultdict(list)
    for r in rows:
        by_scenario[r["scenario"]].append(r)

    refs: Dict[str, dict] = {}
    for scn, scn_rows in by_scenario.items():
        ref = next((r for r in scn_rows if r["variant"] == REFERENCE_VARIANT), None)
        if ref is None:
            raise RuntimeError(f"reference variant {REFERENCE_VARIANT} missing in {scn}")
        refs[scn] = ref

    per_scn_rows: List[dict] = []
    by_variant: Dict[str, Dict[str, dict]] = defaultdict(dict)
    for scn, scn_rows in by_scenario.items():
        ref = refs[scn]
        for r in scn_rows:
            total, dims = scenario_score(r, ref)
            entry = {
                "scenario": scn,
                "variant": r["variant"],
                "S_scn": round(total * 100, 2),
                "efficiency": round(dims["efficiency"] * 100, 2),
                "smoothness": round(dims["smoothness"] * 100, 2),
                "robustness": round(dims["robustness"] * 100, 2),
                "compute":    round(dims["compute"] * 100, 2),
                "hard_gate":  hard_gate(r),
            }
            per_scn_rows.append(entry)
            by_variant[r["variant"]][scn] = entry

    overall_rows: List[dict] = []
    for variant, scn_map in by_variant.items():
        scn_scores = [scn_map[s]["S_scn"] / 100.0 for s in by_scenario]
        dim_means = {}
        for d in DIM_METRICS:
            ds = [scn_map[s][d] / 100.0 for s in by_scenario]
            arr = np.array(ds)
            if (arr <= 0).any():
                dim_means[d] = float(arr.mean() * 100)
            else:
                dim_means[d] = float(np.exp(np.mean(np.log(arr))) * 100)
        overall_rows.append({
            "variant": variant,
            "S_overall": round(overall_score(scn_scores), 2),
            "efficiency_avg": round(dim_means["efficiency"], 2),
            "smoothness_avg": round(dim_means["smoothness"], 2),
            "robustness_avg": round(dim_means["robustness"], 2),
            "compute_avg":    round(dim_means["compute"], 2),
            "n_pass":         sum(scn_map[s]["hard_gate"] for s in by_scenario),
            "n_total":        len(by_scenario),
        })

    overall_rows.sort(key=lambda x: -x["S_overall"])
    for rk, row in enumerate(overall_rows, start=1):
        row["rank"] = rk
    return per_scn_rows, overall_rows


# ============================ LaTeX 输出 ============================

def write_main_table(overall_rows: List[dict], path: str):
    """主表 6 行 × 7 列，按总分降序。"""
    lines = [
        "% 由 metric_score.py 自动生成 — 请勿手动编辑",
        "\\begin{tabular}{lrrrrrrr}",
        "\\toprule",
        "变体 & 总分 & 通行 & 平顺 & 鲁棒 & 开销 & 通过/总 & 排名 \\\\",
        "\\midrule",
    ]
    for row in overall_rows:
        label = VARIANT_LABEL_ZH.get(row["variant"], row["variant"])
        marker = " $\\star$" if row["rank"] == 1 else ""
        lines.append(
            f"{label} & {row['S_overall']:.2f} & "
            f"{row['efficiency_avg']:.1f} & {row['smoothness_avg']:.1f} & "
            f"{row['robustness_avg']:.1f} & {row['compute_avg']:.1f} & "
            f"{row['n_pass']}/{row['n_total']} & {row['rank']}{marker} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_radar(overall_rows: List[dict], path: str):
    """4 维度雷达图：6 折线 × 4 顶点。pgfplots polaraxis。"""
    head = [
        "% 由 metric_score.py 自动生成",
        "\\begin{tikzpicture}",
        "  \\begin{polaraxis}[",
        "    width=0.62\\textwidth, xtick={0,90,180,270},",
        "    xticklabels={通行效率, 轨迹平顺, 决策鲁棒, 计算开销},",
        "    ymin=0, ymax=120, ytick={20,40,60,80,100}, yticklabel=\\empty,",
        "    grid=both, major grid style={gray!30}, minor grid style={gray!10},",
        "    legend style={font=\\small, at={(1.18,0.95)}, anchor=north west, draw=none},",
        "  ]",
    ]
    plot_lines = []
    color_palette = ["red", "orange", "olive", "blue", "violet", "teal"]
    for idx, row in enumerate(overall_rows):
        col = color_palette[idx % len(color_palette)]
        # 雷达 4 个角点，顺序与 xticklabels 一致
        e = row["efficiency_avg"]
        s = row["smoothness_avg"]
        r = row["robustness_avg"]
        c = row["compute_avg"]
        plot_lines.append(
            f"    \\addplot+[mark=*, thick, color={col}] "
            f"coordinates {{(0,{e:.1f}) (90,{s:.1f}) (180,{r:.1f}) (270,{c:.1f}) (360,{e:.1f})}};"
        )
        plot_lines.append(
            f"    \\addlegendentry{{{VARIANT_LABEL_ZH.get(row['variant'], row['variant'])}}}"
        )
    tail = ["  \\end{polaraxis}", "\\end{tikzpicture}"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(head + plot_lines + tail) + "\n")


def write_heatmap(per_scn_rows: List[dict], path: str):
    """热力图 6 行变体 × 4 列场景，色阶按 S_scn(0-100)。"""
    variants = list(OrderedDict.fromkeys(r["variant"] for r in per_scn_rows))
    # 场景按论文章节出现顺序展示：03→05章, 02→06章, 04→06章, 01→07章
    scenario_order = ["03_narrow_cones", "02_ped_plus_parked",
                      "04_dense_construction", "01_crossing_ped"]
    csv_scenarios = set(r["scenario"] for r in per_scn_rows)
    scenarios = [s for s in scenario_order if s in csv_scenarios]
    scn_label = {
        "03_narrow_cones":       "场景一",
        "02_ped_plus_parked":    "场景二",
        "04_dense_construction": "场景三",
        "01_crossing_ped":       "场景四",
    }

    grid: Dict[str, Dict[str, float]] = defaultdict(dict)
    for r in per_scn_rows:
        grid[r["variant"]][r["scenario"]] = r["S_scn"]

    # 内嵌自定义 RdYlGn colormap，避免依赖 pgfplots 可选 colormap 包
    head = [
        "% 由 metric_score.py 自动生成",
        "\\begin{tikzpicture}",
        "  \\pgfplotsset{",
        "    colormap={RdYlGnLocal}{rgb255=(215,25,28) rgb255=(253,174,97) rgb255=(255,255,191) rgb255=(166,217,106) rgb255=(26,150,65)},",
        "  }",
        "  \\begin{axis}[",
        "    width=0.78\\textwidth, height=0.42\\textwidth,",
        "    enlargelimits=false, axis on top,",
        f"    xtick={{{','.join(str(i) for i in range(len(scenarios)))}}},",
        "    xticklabels={" + ",".join(scn_label.get(s, s) for s in scenarios) + "},",
        f"    ytick={{{','.join(str(i) for i in range(len(variants)))}}},",
        "    yticklabels={"
        + ",".join(
            "{" + VARIANT_LABEL_ZH.get(v, v).replace("\\(", "$").replace("\\)", "$") + "}"
            for v in variants)
        + "},",
        "    point meta min=0, point meta max=100,",
        "    colormap name=RdYlGnLocal, colorbar,",
        "    colorbar style={width=0.3cm, ylabel={$S_{\\mathrm{scn}}$}},",
        "    nodes near coords, nodes near coords align={center},",
        "    every node near coord/.append style={font=\\scriptsize, text=black},",
        "    xlabel={场景}, ylabel={变体},",
        "  ]",
        "    \\addplot[matrix plot*, mesh/cols="
        + str(len(scenarios))
        + ", point meta=explicit] table[meta=val] {",
        "    x y val",
    ]
    rows = []
    for vi, v in enumerate(variants):
        for si, s in enumerate(scenarios):
            val = grid[v].get(s, 0.0)
            rows.append(f"    {si} {vi} {val:.2f}")
    tail = ["    };", "  \\end{axis}", "\\end{tikzpicture}"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(head + rows + tail) + "\n")


def write_macros(rows: List[dict], overall_rows: List[dict], path: str):
    """生成 _ablation_macros.tex 供 chapter8 引用，所有数字均从 ablation.csv 派生。"""
    by_variant = {row["variant"]: row for row in overall_rows}

    def find_row(variant: str, scenario: str) -> dict:
        for r in rows:
            if r["variant"] == variant and r["scenario"] == scenario:
                return r
        raise KeyError(f"missing ablation row for ({variant}, {scenario})")

    def fmt(x: float, prec: int = 2) -> str:
        return f"{x:.{prec}f}"

    macros: Dict[str, str] = {}

    # 总分（按变体）
    variant_to_macro = {
        "M0_baseline": "Zero",
        "M1_no_C1":    "One",
        "M2_no_C2C3":  "Two",
        "M3_no_C4":    "Three",
        "M4_no_C5":    "Four",
        "M5_full":     "Five",
    }
    for variant, suffix in variant_to_macro.items():
        ov = by_variant[variant]
        macros[f"\\AblationScoreM{suffix}"] = fmt(ov["S_overall"])
        macros[f"\\AblationComputeM{suffix}"] = fmt(ov["compute_avg"], 1)

    # 失败变体得分上限：max(M1,M2,M3) 向上取整，作正文「落到 N 分以下」的精确数
    failed_scores = [by_variant[v]["S_overall"] for v in ("M1_no_C1", "M2_no_C2C3", "M3_no_C4")]
    macros["\\AblationFailedScoreCeil"] = str(int(np.ceil(max(failed_scores))))

    # M4 vs M5 微弱超越的差值
    margin = by_variant["M4_no_C5"]["S_overall"] - by_variant["M5_full"]["S_overall"]
    macros["\\AblationMarginMFourMFive"] = fmt(margin)

    # M4 计算开销相对 M5 的优势百分比：compute_avg - 100
    compute_adv = by_variant["M4_no_C5"]["compute_avg"] - 100.0
    macros["\\AblationComputeAdvMFourPct"] = fmt(compute_adv, 1)

    # 特定 (variant, scenario) 数据点
    # 注：\newcommand 名禁止含数字，故场景编号写英文（ScFour 而非 Sc4）
    m2_sc4 = find_row("M2_no_C2C3", "04_dense_construction")
    macros["\\AblationMTwoScFourVAvg"] = fmt(m2_sc4["v_avg"])
    macros["\\AblationMTwoScFourSEnd"] = fmt(m2_sc4["s_end"])
    sc4_target = m2_sc4["s_target"]
    sc4_pct = m2_sc4["s_end"] / sc4_target * 100 if sc4_target > 0 else 0.0
    macros["\\AblationMTwoScFourSEndPct"] = fmt(sc4_pct, 1)

    m3_sc3 = find_row("M3_no_C4", "03_narrow_cones")
    macros["\\AblationMThreeScThreeVAvg"] = fmt(m3_sc3["v_avg"])

    # 通用参数
    macros["\\AblationFailPenalty"] = str(FAIL_PENALTY_S)
    macros["\\DeltaBaseline"] = fmt(DELTA_BASELINE, 2)
    macros["\\DeltaIntervalLow"] = fmt(DELTA_MIN, 2)
    macros["\\DeltaIntervalHigh"] = fmt(DELTA_MAX, 2)

    lines = [
        "% 自动生成：消融实验数据宏定义。请勿手动编辑。",
        "% 来源：可视化/metric_score.py 读 图片/data/ablation/ablation.csv 派生",
        "% 重生成：cd 可视化 && uv run metric_score.py",
        "% chapter 引用方式：\\AblationScoreMFive 等",
        "",
    ]
    for name in sorted(macros):
        lines.append(f"\\newcommand{{{name}}}{{{macros[name]}}}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_csv(rows: List[dict], path: str, columns: List[str]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in columns})


# ============================ 主流程 ============================

def main():
    rows = load_rows()
    per_scn_rows, overall_rows = compute_all_scores(rows)

    print("\n========== 综合评分排名（按 S_overall 降序）==========\n")
    print(f"{'排名':<4}{'变体':<32}{'总分':>8}{'通行':>8}{'平顺':>8}"
          f"{'鲁棒':>8}{'开销':>8}{'通过':>8}")
    print("-" * 90)
    for r in overall_rows:
        label = r["variant"]
        marker = " ★" if r["rank"] == 1 else ""
        print(f"{r['rank']:<4}{label:<32}{r['S_overall']:>8.2f}"
              f"{r['efficiency_avg']:>8.1f}{r['smoothness_avg']:>8.1f}"
              f"{r['robustness_avg']:>8.1f}{r['compute_avg']:>8.1f}"
              f"{r['n_pass']}/{r['n_total']}{marker}")

    write_csv(per_scn_rows, os.path.join(DATA_DIR, "score_per_scenario.csv"),
              columns=["scenario", "variant", "S_scn", "efficiency",
                       "smoothness", "robustness", "compute", "hard_gate"])
    write_csv(overall_rows, os.path.join(DATA_DIR, "score_overall.csv"),
              columns=["rank", "variant", "S_overall", "efficiency_avg",
                       "smoothness_avg", "robustness_avg", "compute_avg",
                       "n_pass", "n_total"])

    write_main_table(overall_rows, os.path.join(DATA_DIR, "score_table.tex"))
    write_radar(overall_rows, os.path.join(DATA_DIR, "score_radar.tex"))
    write_heatmap(per_scn_rows, os.path.join(DATA_DIR, "score_heatmap.tex"))

    macros_path = os.path.join(THESIS_DIR, "_ablation_macros.tex")
    write_macros(rows, overall_rows, macros_path)

    print(f"\n→ {DATA_DIR}/score_per_scenario.csv")
    print(f"→ {DATA_DIR}/score_overall.csv")
    print(f"→ {DATA_DIR}/score_table.tex")
    print(f"→ {DATA_DIR}/score_radar.tex")
    print(f"→ {DATA_DIR}/score_heatmap.tex")
    print(f"→ {macros_path}")


if __name__ == "__main__":
    main()
