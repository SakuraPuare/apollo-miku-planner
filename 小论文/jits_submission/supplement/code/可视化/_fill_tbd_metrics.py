# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.26"]
# ///
"""读 8 场景 meta.json + st_curves.csv，回填 chapter8/9 里的 TBD-METRIC 占位。

字段命名：%%TBD-METRIC-<NN>-<mode>-<field>%%
  NN     ∈ {01..08, summary}
  mode   ∈ {baseline, miku}
  field  ∈ {avg_v, min_v, max_abs_a, max_abs_jerk, s_end, t_arrive,
            stop_dur, qp_solve_ms_path, qp_solve_ms_speed, qp_solve_ms_total,
            pass_count, v_improvement, extra_ms, efficiency}
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "图片" / "data"
CHAPTERS = ROOT / "毕业论文" / "chapters"

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


def fmt_num(v, fmt: str) -> str:
    if v is None:
        return r"$\infty$"
    try:
        return fmt.format(v)
    except Exception:
        return str(v)


def derive_min_v_stop_dur(scn: str, mode: str) -> tuple[float | None, float]:
    f = DATA / scn / "st_curves.csv"
    if not f.exists():
        return None, 0.0
    vs, ts = [], []
    with f.open("r", encoding="utf-8") as fp:
        r = csv.DictReader(fp)
        for row in r:
            if row["mode"] != mode or row["v_qp"] in ("", None):
                continue
            try:
                vs.append(float(row["v_qp"]))
                ts.append(float(row["t"]))
            except Exception:
                pass
    if not vs:
        return None, 0.0
    min_v = min(vs)
    if len(ts) < 2:
        return min_v, 0.0
    dt = ts[1] - ts[0]
    stop_dur = sum(dt for v in vs if v < 0.3)
    return min_v, stop_dur


def collect_metrics():
    """返回 {(scn, mode, field): value} 映射。"""
    out: dict[tuple[str, str, str], object] = {}
    metas = {}
    for scn in SCN_NAMES:
        meta = json.loads((DATA / scn / "meta.json").read_text(encoding="utf-8"))
        metas[scn] = meta
        nn = scn.split("_")[0]
        for mode in ("baseline", "miku"):
            m = meta["metrics"][mode]
            qp = m["qp_solve_ms"]
            out[(nn, mode, "avg_v")] = m["avg_v"]
            out[(nn, mode, "max_abs_a")] = m["max_abs_a"]
            out[(nn, mode, "max_abs_jerk")] = m["max_abs_jerk"]
            out[(nn, mode, "s_end")] = m["s_end"]
            out[(nn, mode, "t_arrive")] = m["t_arrive"]
            out[(nn, mode, "qp_solve_ms_path")] = qp["path"]
            out[(nn, mode, "qp_solve_ms_speed")] = qp["speed"]
            out[(nn, mode, "qp_solve_ms_total")] = qp["total"]
            out[(nn, mode, "efficiency")] = m["efficiency"]
            min_v, stop_dur = derive_min_v_stop_dur(scn, mode)
            out[(nn, mode, "min_v")] = min_v
            out[(nn, mode, "stop_dur")] = stop_dur

    # 汇总：N 场景平均 + pass_count
    summary_avg = {}
    summary_path_qp = {}
    for mode in ("baseline", "miku"):
        avg_vs = []
        pass_cnt = 0
        total_qp = 0.0
        path_qps = []
        for scn in SCN_NAMES:
            m = metas[scn]["metrics"][mode]
            scnp = metas[scn]["scn_params"]
            avg_vs.append(m["avg_v"])
            if m["s_end"] >= scnp["s_max"] - 1.0:
                pass_cnt += 1
            total_qp += m["qp_solve_ms"]["total"]
            path_qps.append(m["qp_solve_ms"]["path"])
        summary_avg[mode] = sum(avg_vs) / len(avg_vs)
        summary_path_qp[mode] = sum(path_qps) / len(path_qps)
        out[("summary", mode, "avg_v")] = summary_avg[mode]
        out[("summary", mode, "pass_count")] = pass_cnt
        out[("summary", mode, "qp_solve_ms_total")] = total_qp / len(SCN_NAMES)

    # 派生：v_improvement = (miku - baseline) / baseline；extra_ms = path qp 差值
    base = summary_avg["baseline"]
    if base > 0:
        out[("summary", "summary", "v_improvement")] = (
            summary_avg["miku"] - base
        ) / base
    out[("summary", "summary", "extra_ms")] = (
        summary_path_qp["miku"] - summary_path_qp["baseline"]
    )

    return out


# 字段 → 格式 + 单位（单位由 LaTeX 文本自带，这里只输出数字）
FMT = {
    "avg_v": "{:.2f}",
    "min_v": "{:.2f}",
    "max_abs_a": "{:.2f}",
    "max_abs_jerk": "{:.2f}",
    "s_end": "{:.1f}",
    "t_arrive": "{:.2f}",
    "stop_dur": "{:.2f}",
    "qp_solve_ms_path": "{:.2f}",
    "qp_solve_ms_speed": "{:.2f}",
    "qp_solve_ms_total": "{:.2f}",
    "efficiency": "{:.0%}",
    "pass_count": "{:d}",
    "v_improvement": "{:.1%}",
    "extra_ms": "{:.2f}",
}


def replace_in_text(text: str, mapping: dict) -> tuple[str, int, list[str]]:
    """匹配 %%TBD-METRIC-<scn>-<mode>-<field>%% 并替换。"""
    pattern = re.compile(r"%%TBD-METRIC-([0-9a-z_]+)-([a-z_]+)-([a-z_]+)%%")
    miss: list[str] = []
    count = 0

    def sub(m):
        nonlocal count
        scn, mode, field = m.group(1), m.group(2), m.group(3)
        key = (scn, mode, field)
        if key not in mapping:
            miss.append(m.group(0))
            return m.group(0)
        val = mapping[key]
        fmt = FMT.get(field, "{}")
        if val is None and field in ("t_arrive",):
            count += 1
            return r"$\infty$"
        if isinstance(val, int) and field == "pass_count":
            count += 1
            return fmt.format(val)
        if isinstance(val, float) and field == "efficiency":
            count += 1
            return fmt.format(val)
        if val is None:
            miss.append(m.group(0))
            return m.group(0)
        count += 1
        return fmt.format(val)

    new = pattern.sub(sub, text)
    return new, count, miss


def main():
    mapping = collect_metrics()
    print(f"[collected] {len(mapping)} metrics")

    for fname in ("chapter8.tex", "chapter9.tex"):
        f = CHAPTERS / fname
        text = f.read_text(encoding="utf-8")
        new, cnt, miss = replace_in_text(text, mapping)
        f.write_text(new, encoding="utf-8")
        print(f"[{fname}] replaced {cnt} occurrences")
        if miss:
            print(f"  ⚠ missed {len(miss)}:")
            for m in miss:
                print(f"    {m}")

    # 检查残留
    import subprocess

    r = subprocess.run(
        ["grep", "-rn", "TBD-METRIC", str(CHAPTERS)], capture_output=True, text=True
    )
    if r.stdout.strip():
        print("\n⚠ 残留 TBD-METRIC：")
        print(r.stdout)
    else:
        print("\n[ok] 全部 TBD-METRIC 已替换")


if __name__ == "__main__":
    main()
