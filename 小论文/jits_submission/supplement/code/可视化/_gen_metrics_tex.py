# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
r"""读 meta.json + st_curves.csv 派生指标，输出 LaTeX 宏定义文件。

幂等设计：本脚本是确定性函数，相同输入永远输出相同 _experiment_metrics.tex 内容
（除 qp_solve_ms 这一时间敏感字段，建议 chapter 引用其它字段）。

输出位置：毕业论文/_experiment_metrics.tex（gitignore，由 Makefile 自动重生成）

chapter 用法（替代硬编码数字）：
    平均速度从 \MOneBaselineAvgV\,m/s 提升至 \MOneMikuAvgV\,m/s
    可比场景通行成功率：Baseline \MComparableBaselinePassCount / MIKU \MComparableMikuPassCount

宏命名规则：M<场景><模式><字段>，全字母（LaTeX 宏不支持数字/下划线）。
- 场景：One/Two/Three/Four/Five/Six/Seven/Eight/Pressure/Comparable/Summary
- 模式：Baseline/Miku/Summary
- 字段：AvgV/MaxAbsA/MaxAbsJerk/SEnd/TArrive/QpPath/QpSpeed/QpTotal/PassCount/VImprovement/ExtraMs
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "图片" / "data"
OUT = ROOT / "毕业论文" / "_experiment_metrics.tex"

SCN_NAMES = [
    "01_crossing_ped",
    "02_ped_plus_parked",
    "03_narrow_cones",
    "04_dense_construction",
    "05_crossing_ped_cmp",
    "06_ped_plus_parked_cmp",
    "07_narrow_cones_cmp",
    "08_dense_construction_cmp",
]
PRESSURE_SCN_NAMES = SCN_NAMES[:4]
COMPARABLE_SCN_NAMES = SCN_NAMES[4:]
SCN_WORDS = {
    "01": "One",
    "02": "Two",
    "03": "Three",
    "04": "Four",
    "05": "Five",
    "06": "Six",
    "07": "Seven",
    "08": "Eight",
}

FIELD_WORDS = {
    "avg_v": "AvgV",
    "min_v": "MinV",
    "max_abs_a": "MaxAbsA",
    "max_abs_a_lat": "MaxAbsALat",
    "max_abs_jerk": "MaxAbsJerk",
    "s_end": "SEnd",
    "t_arrive": "TArrive",
    "stop_dur": "StopDur",
    "qp_solve_ms_path": "QpPath",
    "qp_solve_ms_speed": "QpSpeed",
    "qp_solve_ms_total": "QpTotal",
    "efficiency": "Efficiency",
    "pass_count": "PassCount",
    "v_improvement": "VImprovement",
    "extra_ms": "ExtraMs",
}

# 字段 → LaTeX 输出格式
FMT = {
    "avg_v": "{:.2f}",
    "min_v": "{:.2f}",
    "max_abs_a": "{:.2f}",
    "max_abs_a_lat": "{:.2f}",
    "max_abs_jerk": "{:.2f}",
    "s_end": "{:.1f}",
    "t_arrive": "{:.2f}",
    "stop_dur": "{:.2f}",
    "qp_solve_ms_path": "{:.2f}",
    "qp_solve_ms_speed": "{:.2f}",
    "qp_solve_ms_total": "{:.2f}",
    "efficiency": "{:.0%}",
    "pass_count": "{:d}",
    "v_improvement": "{:.1f}",
    "extra_ms": "{:.2f}",
}


MODE_WORDS = {"baseline": "Baseline", "miku": "Miku", "summary": "Summary"}


def macro_name(scn: str, mode: str, field: str) -> str:
    s = SCN_WORDS.get(scn, scn.capitalize())
    m = MODE_WORDS.get(mode, mode.capitalize())
    f = FIELD_WORDS.get(field, "".join(w.capitalize() for w in field.split("_")))
    return f"M{s}{m}{f}"


def fmt_value(field: str, val) -> str:
    if val is None and field == "t_arrive":
        return r"$\infty$"
    if val is None:
        return r"--"
    fmt = FMT.get(field, "{}")
    try:
        s = fmt.format(val)
    except Exception:
        s = str(val)
    # LaTeX 转义：% 是注释符，必须 \%
    return s.replace("%", r"\%")


def derive_min_v_stop_dur(scn: str, mode: str) -> tuple[float | None, float]:
    f = DATA / scn / "st_curves.csv"
    if not f.exists():
        return None, 0.0
    vs, ts = [], []
    with f.open("r", encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            if row["mode"] != mode or row["v_qp"] in ("", None):
                continue
            try:
                vs.append(float(row["v_qp"]))
                ts.append(float(row["t"]))
            except Exception:
                pass
    if not vs:
        return None, 0.0
    dt = ts[1] - ts[0] if len(ts) >= 2 else 0.1
    return min(vs), sum(dt for v in vs if v < 0.3)


def collect():
    out: dict[tuple[str, str, str], object] = {}
    metas = {}
    for scn in SCN_NAMES:
        meta = json.loads((DATA / scn / "meta.json").read_text(encoding="utf-8"))
        metas[scn] = meta
        nn = scn.split("_")[0]
        for mode in ("baseline", "miku"):
            m = meta["metrics"][mode]
            qp = m["qp_solve_ms"]
            for f in (
                "avg_v",
                "max_abs_a",
                "max_abs_a_lat",
                "max_abs_jerk",
                "s_end",
                "t_arrive",
                "efficiency",
            ):
                out[(nn, mode, f)] = m.get(f)
            out[(nn, mode, "qp_solve_ms_path")] = qp["path"]
            out[(nn, mode, "qp_solve_ms_speed")] = qp["speed"]
            out[(nn, mode, "qp_solve_ms_total")] = qp["total"]
            mn, sd = derive_min_v_stop_dur(scn, mode)
            out[(nn, mode, "min_v")] = mn
            out[(nn, mode, "stop_dur")] = sd

    def add_summary(key: str, names: list[str], mode: str):
        avg_vs, qps, pths = [], [], []
        passed = 0
        for scn in names:
            m = metas[scn]["metrics"][mode]
            sm = metas[scn]["scn_params"]["s_max"]
            avg_vs.append(m["avg_v"])
            qps.append(m["qp_solve_ms"]["total"])
            pths.append(m["qp_solve_ms"]["path"])
            if m["s_end"] >= sm - 1.0:
                passed += 1
        out[(key, mode, "avg_v")] = sum(avg_vs) / len(avg_vs)
        out[(key, mode, "qp_solve_ms_total")] = sum(qps) / len(qps)
        out[(key, mode, "qp_solve_ms_path")] = sum(pths) / len(pths)
        out[(key, mode, "pass_count")] = passed

    # 汇总：Summary 为 8 场景全局，Pressure/Comparable 分别对应原压力组和复制可比组。
    for mode in ("baseline", "miku"):
        add_summary("summary", SCN_NAMES, mode)
        add_summary("pressure", PRESSURE_SCN_NAMES, mode)
        add_summary("comparable", COMPARABLE_SCN_NAMES, mode)

    bavg = out[("summary", "baseline", "avg_v")]
    gavg = out[("summary", "miku", "avg_v")]
    if bavg and bavg > 0:
        out[("summary", "summary", "v_improvement")] = (gavg - bavg) / bavg * 100
    bp = out[("summary", "baseline", "qp_solve_ms_path")]
    gp = out[("summary", "miku", "qp_solve_ms_path")]
    out[("summary", "summary", "extra_ms")] = gp - bp
    return out


def main():
    mapping = collect()
    lines = [
        "% 自动生成：实验指标宏定义。请勿手动编辑。",
        "% 来源：可视化/_gen_metrics_tex.py 读 图片/data/<scn>/meta.json 派生",
        "% 重生成：cd 可视化 && uv run _gen_metrics_tex.py",
        "% chapter 引用方式：\\MOneBaselineAvgV 等",
        "",
    ]
    lines.extend(
        [
            rf"\newcommand{{\MScenarioTotal}}{{{len(SCN_NAMES)}}}",
            rf"\newcommand{{\MPressureScenarioTotal}}{{{len(PRESSURE_SCN_NAMES)}}}",
            rf"\newcommand{{\MComparableScenarioTotal}}{{{len(COMPARABLE_SCN_NAMES)}}}",
        ]
    )
    for (scn, mode, field), val in sorted(mapping.items()):
        name = macro_name(scn, mode, field)
        v = fmt_value(field, val)
        lines.append(rf"\newcommand{{\{name}}}{{{v}}}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] {len(mapping)} 宏 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
