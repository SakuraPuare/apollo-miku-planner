#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
生成 24 个 fig_exp_<scn>_{sl,st,va}.tex 实验对比图文件。
PEP 723 单文件，uv run _gen_exp_figs.py 即可。
"""

import json
from pathlib import Path

FIGDIR = Path(__file__).parent

# 场景列表（目录名 == scn 标识）
SCENARIOS = [
    "01_crossing_ped",
    "02_ped_plus_parked",
    "03_two_peds_sequential",
    "04_dense_construction",
]

# 各场景障碍物（inline 写死，来自 obstacles.csv + 任务规范）
# 格式：(name, obs_type, s0, l0, vs, vl, W, L)
OBSTACLES = {
    "01_crossing_ped": [
        ("行人", "ped", 12.0, -0.6, 0, 1.2, 0.5, 0.5),
    ],
    "02_ped_plus_parked": [
        ("行人", "ped", 10.0, -0.5, 0, 1.2, 0.5, 0.5),
        ("停车", "static", 22.0, 1.3, 0, 0, 1.0, 4.0),
    ],
    "03_two_peds_sequential": [
        ("行人A", "ped", 13.0, -0.4, 0, 1.0, 0.5, 0.5),
        ("行人B", "ped", 26.0, -0.4, 0, 1.0, 0.5, 0.5),
    ],
    "04_dense_construction": [
        # 入口漏斗 5 锥
        ("锥E1", "static", 16.0, -1.50, 0, 0, 0.4, 2.5),
        ("锥E2", "static", 18.5, -0.85, 0, 0, 0.4, 2.5),
        ("锥E3", "static", 21.0, -0.20, 0, 0, 0.4, 2.5),
        ("锥E4", "static", 23.5,  0.50, 0, 0, 0.4, 2.5),
        ("锥E5", "static", 26.0,  1.20, 0, 0, 0.4, 2.5),
        # 维持段 8 水马 (横跨车道分界线 l=2.0, W=1.0 占据 l∈[1.5,2.5])
        ("水马M1", "static", 29.0, 2.00, 0, 0, 1.0, 4.0),
        ("水马M2", "static", 33.0, 2.00, 0, 0, 1.0, 4.0),
        ("水马M3", "static", 37.0, 2.00, 0, 0, 1.0, 4.0),
        ("水马M4", "static", 41.0, 2.00, 0, 0, 1.0, 4.0),
        ("水马M5", "static", 45.0, 2.00, 0, 0, 1.0, 4.0),
        ("水马M6", "static", 49.0, 2.00, 0, 0, 1.0, 4.0),
        ("水马M7", "static", 53.0, 2.00, 0, 0, 1.0, 4.0),
        ("水马M8", "static", 57.0, 2.00, 0, 0, 1.0, 4.0),
        # 出口漏斗 5 锥
        ("锥X1", "static", 60.0,  1.20, 0, 0, 0.4, 2.5),
        ("锥X2", "static", 62.5,  0.50, 0, 0, 0.4, 2.5),
        ("锥X3", "static", 65.0, -0.20, 0, 0, 0.4, 2.5),
        ("锥X4", "static", 67.5, -0.85, 0, 0, 0.4, 2.5),
        ("锥X5", "static", 70.0, -1.50, 0, 0, 0.4, 2.5),
    ],
}

# discard if not style（每个 fig 都要）
DISCARD_STYLE = r"""\pgfplotsset{
    discard if not/.style 2 args={x filter/.code={
        \edef\tempa{\thisrow{#1}}\edef\tempb{#2}
        \ifx\tempa\tempb\else\def\pgfmathresult{nan}\fi
    }},
    discard if not2/.style n args={4}{x filter/.code={
        \edef\tempa{\thisrow{#1}}\edef\tempb{#2}
        \edef\tempc{\thisrow{#3}}\edef\tempd{#4}
        \ifx\tempa\tempb
            \ifx\tempc\tempd\else\def\pgfmathresult{nan}\fi
        \else\def\pgfmathresult{nan}\fi
    }}
}"""


def obs_sl_tikz(obs_list: list, t_max: float) -> str:
    """生成 SL 图中障碍物的 TikZ 命令（含残影、标签、速度箭头）"""
    lines = []
    t_show_max = min(t_max, 2.0)
    ghost_times = [0.0, t_show_max * 0.33, t_show_max * 0.66, t_show_max]
    ghost_alphas = [0.95, 0.55, 0.35, 0.20]

    for name, otype, s0, l0, vs, vl, W, L in obs_list:
        half_l = L / 2.0
        half_w = W / 2.0
        is_dynamic = (vs != 0 or vl != 0)
        lines.append(rf"% 障碍物 {name}")

        if otype == "ped" or otype == "bike":
            r = max(W, L) / 2.0
            if is_dynamic:
                # 4帧残影
                for t_frame, alpha in zip(ghost_times, ghost_alphas):
                    sx = s0 + vs * t_frame
                    lx = l0 + vl * t_frame
                    lines.append(
                        rf"\fill[dangerred, opacity={alpha:.2f}] (axis cs:{sx:.3f},{lx:.3f}) circle [radius=5pt];"
                    )
                # 速度箭头（从第一帧到最末帧）
                s_end = s0 + vs * t_show_max
                l_end = l0 + vl * t_show_max
                lines.append(
                    rf"\draw[->, dangerred, very thick, opacity=0.85] (axis cs:{s0:.3f},{l0:.3f}) -- (axis cs:{s_end:.3f},{l_end:.3f});"
                )
                # 动态标签
                lines.append(
                    rf"\node[anchor=south, font=\tiny, color=dangerred] at (axis cs:{s0:.3f},{l0 + r + 0.5:.3f}) {{{name} $v=({(0.0 if abs(vs)<1e-9 else vs):+.1f},{(0.0 if abs(vl)<1e-9 else vl):+.1f})$}};"
                )
            else:
                lines.append(
                    rf"\fill[dangerred, opacity=0.95] (axis cs:{s0:.3f},{l0:.3f}) circle [radius=5pt];"
                )
                # 静态标签
                lines.append(
                    rf"\node[anchor=south, font=\tiny, color=dangerred!80!black] at (axis cs:{s0:.3f},{l0 + r + 0.3:.3f}) {{{name}}};"
                )
        elif otype == "static":
            lines.append(
                rf"\fill[dangerred!70, draw=dangerred, thick] (axis cs:{s0-half_l:.3f},{l0-half_w:.3f}) rectangle (axis cs:{s0+half_l:.3f},{l0+half_w:.3f});"
            )
            lines.append(
                rf"\node[anchor=south, font=\tiny, color=dangerred!80!black] at (axis cs:{s0:.3f},{l0 + half_w + 0.3:.3f}) {{{name}}};"
            )
        elif otype == "vehicle":
            if is_dynamic:
                # 4帧残影
                for t_frame, alpha in zip(ghost_times, ghost_alphas):
                    sx = s0 + vs * t_frame
                    lx = l0 + vl * t_frame
                    lines.append(
                        rf"\fill[lightorange!90!black, draw=dangerred, opacity={alpha:.2f}] (axis cs:{sx-half_l:.3f},{lx-half_w:.3f}) rectangle (axis cs:{sx+half_l:.3f},{lx+half_w:.3f});"
                    )
                # 速度箭头
                s_end = s0 + vs * t_show_max
                l_end = l0 + vl * t_show_max
                lines.append(
                    rf"\draw[->, dangerred, very thick, opacity=0.85] (axis cs:{s0:.3f},{l0:.3f}) -- (axis cs:{s_end:.3f},{l_end:.3f});"
                )
                # 动态标签
                lines.append(
                    rf"\node[anchor=south, font=\tiny, color=dangerred] at (axis cs:{s0:.3f},{l0 + half_w + 0.5:.3f}) {{{name} $v=({(0.0 if abs(vs)<1e-9 else vs):+.1f},{(0.0 if abs(vl)<1e-9 else vl):+.1f})$}};"
                )
            else:
                lines.append(
                    rf"\fill[lightorange, draw=dangerred, thick] (axis cs:{s0-half_l:.3f},{l0-half_w:.3f}) rectangle (axis cs:{s0+half_l:.3f},{l0+half_w:.3f});"
                )
                lines.append(
                    rf"\node[anchor=south, font=\tiny, color=dangerred!80!black] at (axis cs:{s0:.3f},{l0 + half_w + 0.3:.3f}) {{{name}}};"
                )

    return "\n".join(lines)


def gen_sl(scn: str, meta: dict, obs_list: list) -> str:
    params = meta["scn_params"]
    s_max = params["s_max"]
    l_road_min = params["l_road_min"]
    l_road_max = params["l_road_max"]
    lane_borrow = params.get("lane_borrow", "none")
    t_max = params["t_max"]
    ego = meta["ego"]
    ego_s0 = ego["s0"]
    ego_l0 = ego["l0"]
    ego_L = ego["L"]
    ego_W = ego["W"]

    # 判断是否有借道（扩展 y 范围 + 子图高度按比例放大，避免 7.8m 范围被压成扁条）
    if lane_borrow != "none":
        ymin = -3.9
        ymax = 3.9
        sub_height = "6.6cm"  # 7.8m 范围按 ~9.5 mm/m 出图，与无借道场景颗粒度对齐
    else:
        ymin = -2.2
        ymax = 2.2
        sub_height = "4.2cm"

    obs_tikz = obs_sl_tikz(obs_list, t_max)

    # ego 车辆：矩形 + 车头三角 + 文字
    ego_half_l = ego_L / 2.0
    ego_half_w = ego_W / 2.0
    # 车头三角顶点（朝+s方向）
    tri_front_x = ego_s0 + ego_half_l
    tri_base_x = ego_s0 + ego_half_l - min(ego_L * 0.25, 0.6)
    tri_top_y = ego_l0 + ego_W * 0.45
    tri_bot_y = ego_l0 - ego_W * 0.45
    # ego 用绝对单位的 node，避免 axis 拉伸导致比例失真。L:W = 4:1.8 ≈ 2.2:1
    ego_tikz = (
        rf"\node[rectangle, fill=deepblue!75, draw=deepblue, thick, "
        rf"minimum width=18pt, minimum height=8pt, inner sep=0pt] "
        rf"(egobox) at (axis cs:{ego_s0:.3f},{ego_l0:.3f}) {{}};"
        "\n"
        rf"\fill[white] ([xshift=0pt]egobox.east) -- "
        rf"([xshift=-3pt,yshift=2.5pt]egobox.east) -- "
        rf"([xshift=-3pt,yshift=-2.5pt]egobox.east) -- cycle;"
        "\n"
        rf"\node[anchor=south west, font=\tiny\bfseries, color=deepblue] "
        rf"at (axis cs:{ego_s0+0.2:.2f},{ego_l0+ego_half_w+0.05:.2f}) {{EGO}};"
    )

    # 路面背景
    road_bg = (
        rf"\addplot[fill=bglight, draw=none, forget plot, on layer=axis background] coordinates {{"
        rf"(0,{l_road_min}) ({s_max},{l_road_min}) ({s_max},{l_road_max}) (0,{l_road_max})"
        rf"}} \closedcycle;"
    )

    # 借道扩展背景
    borrow_bg = ""
    if lane_borrow == "left":
        borrow_bg = (
            rf"\addplot[fill=vibrantorange!25, draw=none, forget plot, on layer=axis background] coordinates {{"
            rf"(0,{l_road_max}) ({s_max},{l_road_max}) ({s_max},{l_road_max*2:.3f}) (0,{l_road_max*2:.3f})"
            rf"}} \closedcycle;"
        )
    elif lane_borrow == "right":
        borrow_bg = (
            rf"\addplot[fill=vibrantorange!25, draw=none, forget plot, on layer=axis background] coordinates {{"
            rf"(0,{l_road_min*2:.3f}) ({s_max},{l_road_min*2:.3f}) ({s_max},{l_road_min}) (0,{l_road_min})"
            rf"}} \closedcycle;"
        )

    # 道路边界实线（车道两侧）
    road_edges = (
        rf"\draw[black!55, semithick] (axis cs:0,{l_road_min}) -- (axis cs:{s_max},{l_road_min});"
        "\n"
        rf"\draw[black!55, semithick] (axis cs:0,{l_road_max}) -- (axis cs:{s_max},{l_road_max});"
        "\n"
        rf"\draw[black!30, dashed, thin] (axis cs:0,0) -- (axis cs:{s_max},0);"
    )

    # blocked 标注：从 meta.json 读取 blocked_s, 在 trim 处插红色 X 标记 + 截断 path 线
    metrics = meta.get("metrics", {})

    def _blocked_marker(mode: str) -> tuple[str, str, str]:
        """返回 (path_addplot, x_marker_tikz, trim_legend) 三段，未 blocked 则后两段为空。

        path_addplot 是已展开的 TeX 字符串（不含再次插值需要 escape 的占位符），
        颜色用 __COLOR__ 占位、由 subfig 替换。"""
        m = metrics.get(mode, {})
        bs = m.get("blocked_s")
        # 共用 table 子句
        table_clause = (
            rf"table[col sep=comma, x=s, y=l_path, "
            rf"discard if not={{mode}}{{{mode}}}] {{\datapath sl.csv}};"
        )
        if bs is None:
            path = rf"\addplot[__COLOR__, line width=2pt, unbounded coords=discard] {table_clause}"
            return path, "", ""
        # 读 sl.csv 抽取 blocked_s 处 l_path 实际值
        import csv as _csv
        sl_path = FIGDIR / "data" / scn / "sl.csv"
        l_at_block = 0.0
        if sl_path.exists():
            with open(sl_path) as f:
                rd = _csv.DictReader(f)
                last_l = 0.0
                for row in rd:
                    if row["mode"] != mode:
                        continue
                    s_v = float(row["s"])
                    if s_v <= bs + 1e-6:
                        last_l = float(row["l_path"])
                    else:
                        break
                l_at_block = last_l
        # 截断 path 线在 blocked_s 处（unbounded coords=jump 才让 pgfplots 真切断线，
        # 默认 discard 会让 last visible point 连到 next visible point 形成虚假水平段）
        path = (rf"\addplot[__COLOR__, line width=2pt, "
                rf"unbounded coords=jump, "
                rf"restrict x to domain=0:{bs:.3f}] {table_clause}")
        # X 标记 + 垂直虚线
        marker = (
            rf"\draw[red, thick, dashed] (axis cs:{bs:.3f},{ymin}) -- (axis cs:{bs:.3f},{ymax});"
            "\n"
            rf"\node[red, font=\Large\bfseries, inner sep=0pt] at (axis cs:{bs:.3f},{l_at_block:.3f}) {{$\times$}};"
        )
        legend = (rf"\addlegendimage{{red, thick, dashed}}"
                  rf"\addlegendentry{{Trim @ $s$={bs:.1f}\,m}}")
        return path, marker, legend

    def subfig(mode: str, color: str, label: str) -> str:
        path_plot, x_marker, trim_legend = _blocked_marker(mode)
        path_plot = path_plot.replace("__COLOR__", color)
        # blocked 时 lmin/lmax 曲线也按 blocked_s 截断（避免冻结区双线重叠拉到 xmax）
        bs = metrics.get(mode, {}).get("blocked_s")
        bound_restrict = (f"unbounded coords=jump, restrict x to domain=0:{bs:.3f}, "
                          if bs is not None else "")
        return rf"""\begin{{subfigure}}[b]{{\textwidth}}
\centering
\begin{{tikzpicture}}
\begin{{axis}}[
    width=\linewidth, height={sub_height},
    xlabel={{$s$ (m)}}, ylabel={{$l$ (m)}},
    xmin=0, xmax={s_max}, ymin={ymin}, ymax={ymax},
    grid=both, grid style={{gray!25}},
    axis line style={{thick}},
    tick label style={{font=\scriptsize}},
    label style={{font=\footnotesize}},
    legend style={{at={{(0.98,0.02)}}, anchor=south east, font=\scriptsize, draw=none, fill=white, fill opacity=0.85}},
]
{road_bg}
{borrow_bg}
{road_edges}
% 可行带阴影（blocked 时按 blocked_s 截断）
\addplot[name path=lmin_{mode}, draw=vibrantorange, thin, dashed, forget plot, {bound_restrict}]
    table[col sep=comma, x=s, y=l_min, discard if not={{mode}}{{{mode}}}] {{\datapath sl.csv}};
\addplot[name path=lmax_{mode}, draw=vibrantorange, thin, dashed, forget plot, {bound_restrict}]
    table[col sep=comma, x=s, y=l_max, discard if not={{mode}}{{{mode}}}] {{\datapath sl.csv}};
\addplot[fill=lightgreen!35, draw=none, forget plot] fill between[of=lmin_{mode} and lmax_{mode}];
% 路径（blocked 时按 blocked_s 截断）
{path_plot}
\addlegendentry{{{label}}}
{trim_legend}
{x_marker}
{obs_tikz}
{ego_tikz}
\end{{axis}}
\end{{tikzpicture}}
\caption{{{label}}}
\end{{subfigure}}"""

    baseline_sub = subfig("baseline", "deepblue", "Baseline")
    gtoc_sub = subfig("gtoc", "vibrantgreen", "GTOC")

    scn_nn = scn[:2]
    return rf"""% 场景{scn_nn} SL 平面 Baseline vs GTOC 对比（上下排，每子图占满 \textwidth）
\def\datapath{{data/{scn}/}}
{DISCARD_STYLE}
{baseline_sub}

\vspace{{0.6em}}

{gtoc_sub}
"""


def gen_st(scn: str, meta: dict, obs_list: list) -> str:
    params = meta["scn_params"]
    s_max = params["s_max"]
    t_max = params["t_max"]

    # corridor.csv 是否有效
    corridor_path = FIGDIR / "data" / scn / "corridor.csv"
    has_corridor = False
    corridor_rows = []
    if corridor_path.exists():
        lines = corridor_path.read_text().splitlines()
        # 头行 + 至少 1 条数据
        if len(lines) >= 2 and lines[1].strip():
            has_corridor = True
            for row in lines[1:]:
                row = row.strip()
                if row:
                    parts = row.split(",")
                    if len(parts) >= 2:
                        try:
                            corridor_rows.append((float(parts[0]), float(parts[1])))
                        except ValueError:
                            pass

    # st_bounds.csv 解析：按 (mode, obs_name) 分组，避免 \addplot table 把多障碍物连成乱跑的折线
    st_bounds_path = FIGDIR / "data" / scn / "st_bounds.csv"
    st_obs = {"baseline": [], "gtoc": []}  # 保序 list，去重
    if st_bounds_path.exists():
        for line in st_bounds_path.read_text().splitlines()[1:]:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                mode_v, obs_v = parts[0], parts[1]
                if mode_v in st_obs and obs_v not in st_obs[mode_v]:
                    st_obs[mode_v].append(obs_v)
    has_bounds = {m: bool(st_obs[m]) for m in st_obs}

    # GTOC 子图额外走廊标注（hatch 禁行区 + 节点）
    corridor_extra = ""
    if has_corridor:
        hatch_blocks = []
        node_labels = []
        for s_k, tau_k in corridor_rows:
            hatch_blocks.append(
                rf"\addplot[pattern=north east lines, pattern color=deeppink!60, draw=deeppink!60, semithick, forget plot]"
                "\n"
                rf"    coordinates {{(0,{s_k:.4f}) ({tau_k:.4f},{s_k:.4f}) ({tau_k:.4f},{s_max*1.5:.1f}) (0,{s_max*1.5:.1f})}} \closedcycle;"
            )
            tau_str = f"{tau_k:.2f}"
            sk_str = f"{s_k:.1f}"
            node_labels.append(
                rf"\node[deeppink, font=\tiny, fill=white, fill opacity=0.85, text opacity=1, inner sep=1pt] at (axis cs:{tau_k+0.4:.3f},{s_k+2.5:.3f}) {{$\tau_k{{=}}{tau_str},\,s_k{{=}}{sk_str}$}};"
            )
        hatch_str = "\n".join(hatch_blocks)
        nodes_str = "\n".join(node_labels)
        corridor_extra = rf"""% GTOC 走廊禁行区 hatch
{hatch_str}
{nodes_str}
% GTOC 走廊关键点（tau_k 标注）
\addplot[deeppink, very thick, dashed, mark=diamond*, mark size=4pt, mark options={{fill=deeppink, draw=black, line width=0.6pt}}]
    table[col sep=comma, x=tau_k, y=s_k] {{\datapath corridor.csv}};
\addlegendentry{{走廊节点 $\tau_k$}}"""

    def subfig_st(mode: str, path_color: str, label: str, extra: str = "") -> str:
        # 按 obs_name 独立画 fill_between，避免 \addplot table 把多个障碍物的边界连成跨障碍物的乱多边形
        if has_bounds[mode]:
            blocks = []
            for i, obs in enumerate(st_obs[mode]):
                blocks.append(rf"""% obs={obs}
\addplot[name path=stlo_{mode}_{i}, draw=none, forget plot]
    table[col sep=comma, x=t, y=s_lo, discard if not2={{mode}}{{{mode}}}{{obs_name}}{{{obs}}}] {{\datapath st_bounds.csv}};
\addplot[name path=sthi_{mode}_{i}, draw=none, forget plot]
    table[col sep=comma, x=t, y=s_hi, discard if not2={{mode}}{{{mode}}}{{obs_name}}{{{obs}}}] {{\datapath st_bounds.csv}};
\addplot[fill=dangerred!40, draw=none, forget plot] fill between[of=stlo_{mode}_{i} and sthi_{mode}_{i}];""")
            # 单一图例项（用 addlegendimage 避免 fill_between forget plot 不可加 legend）
            blocks.append(r"\addlegendimage{area legend, fill=dangerred!40, draw=none}")
            blocks.append(r"\addlegendentry{障碍物 ST 禁行区}")
            bounds_block = "\n".join(blocks)
        else:
            bounds_block = "% 该模式无 ST 禁行区（路径阶段已绕开冲突，无投影）"
        return rf"""\begin{{subfigure}}[b]{{0.48\textwidth}}
\centering
\begin{{tikzpicture}}
\begin{{axis}}[
    width=\linewidth, height=5.5cm,
    xlabel={{$t$ (s)}}, ylabel={{$s$ (m)}},
    xmin=0, xmax={t_max}, ymin=0, ymax={s_max*1.5:.1f},
    restrict y to domain*=0:{s_max*1.5:.1f},
    unbounded coords=jump,
    grid=both, grid style={{gray!25}},
    axis line style={{thick}},
    tick label style={{font=\scriptsize}},
    label style={{font=\footnotesize}},
    legend style={{at={{(0.02,0.98)}}, anchor=north west, font=\scriptsize, draw=none, fill=white, fill opacity=0.9}},
]
{bounds_block}
% DP 粗解
\addplot[improvedpink, thick, dashed]
    table[col sep=comma, x=t, y=s_dp, discard if not={{mode}}{{{mode}}}] {{\datapath st_curves.csv}};
\addlegendentry{{$s_{{dp}}$}}
% QP 精解
\addplot[{path_color}, line width=2pt]
    table[col sep=comma, x=t, y=s_qp, discard if not={{mode}}{{{mode}}}] {{\datapath st_curves.csv}};
\addlegendentry{{$s_{{qp}}$ ({label})}}
{extra}
\end{{axis}}
\end{{tikzpicture}}
\caption{{{label}}}
\end{{subfigure}}"""

    baseline_sub = subfig_st("baseline", "deepblue", "Baseline")
    gtoc_sub = subfig_st("gtoc", "vibrantgreen", "GTOC", corridor_extra)

    scn_nn = scn[:2]
    return rf"""% 场景{scn_nn} ST 平面 Baseline vs GTOC 对比
\def\datapath{{data/{scn}/}}
{DISCARD_STYLE}
{baseline_sub}\hfill
{gtoc_sub}
"""


def _fmt_metric(val, fmt=".2f"):
    if val is None:
        return "INF"
    try:
        return format(float(val), fmt)
    except (TypeError, ValueError):
        return "INF"


def gen_va(scn: str, meta: dict) -> str:
    params = meta["scn_params"]
    t_max = params["t_max"]
    v0 = meta["ego"]["v0"]
    metrics = meta.get("metrics", {})
    mb = metrics.get("baseline", {})
    mg = metrics.get("gtoc", {})

    avg_v_b = _fmt_metric(mb.get("avg_v"))
    max_a_b = _fmt_metric(mb.get("max_abs_a"))
    max_j_b = _fmt_metric(mb.get("max_abs_jerk"))
    s_end_b = _fmt_metric(mb.get("s_end"), ".1f")

    avg_v_g = _fmt_metric(mg.get("avg_v"))
    max_a_g = _fmt_metric(mg.get("max_abs_a"))
    max_j_g = _fmt_metric(mg.get("max_abs_jerk"))
    s_end_g = _fmt_metric(mg.get("s_end"), ".1f")

    v_max_axis = v0 * 1.3
    # 指标框放在 v_max_axis - 0.5 处
    box_y = v_max_axis - 0.5

    scn_nn = scn[:2]

    return rf"""% 场景{scn_nn} 速度/加速度 Baseline vs GTOC 对比
\def\datapath{{data/{scn}/}}
{DISCARD_STYLE}
\begin{{subfigure}}[b]{{\textwidth}}
\centering
\begin{{tikzpicture}}
\begin{{axis}}[
    width=\linewidth, height=4.2cm,
    xlabel={{$t$ (s)}}, ylabel={{$v$ (m/s)}},
    xmin=0, xmax={t_max}, ymin=0, ymax={v_max_axis:.1f},
    grid=both, grid style={{gray!25}},
    axis line style={{thick}},
    tick label style={{font=\tiny}},
    label style={{font=\scriptsize}},
    legend style={{at={{(0.5,-0.34)}}, anchor=north, legend columns=2,
        font=\fontsize{{6}}{{7}}\selectfont, draw=none, /tikz/every even column/.append style={{column sep=2em}}}},
]
% v_ref 参考线
\draw[black!50, dashed, thick] (axis cs:0,{v0:.2f}) -- (axis cs:{t_max:.2f},{v0:.2f});
\node[black!50, font=\tiny, anchor=south east] at (axis cs:{t_max:.2f},{v0:.2f}) {{$v_{{ref}}$}};
\addplot[deepblue, line width=2pt]
    table[col sep=comma, x=t, y=v_qp, discard if not={{mode}}{{baseline}}] {{\datapath st_curves.csv}};
\addlegendentry{{Baseline\,(\,$\bar{{v}}{{=}}{avg_v_b}$,\,$|a|_{{max}}{{=}}{max_a_b}$,\,$|j|_{{max}}{{=}}{max_j_b}$,\,$s_{{end}}{{=}}{s_end_b}$\,m\,)}}
\addplot[vibrantgreen, line width=2pt]
    table[col sep=comma, x=t, y=v_qp, discard if not={{mode}}{{gtoc}}] {{\datapath st_curves.csv}};
\addlegendentry{{GTOC\,(\,$\bar{{v}}{{=}}{avg_v_g}$,\,$|a|_{{max}}{{=}}{max_a_g}$,\,$|j|_{{max}}{{=}}{max_j_g}$,\,$s_{{end}}{{=}}{s_end_g}$\,m\,)}}
\end{{axis}}
\end{{tikzpicture}}
\caption{{速度对比}}
\end{{subfigure}}

\vspace{{0.8em}}

\begin{{subfigure}}[b]{{\textwidth}}
\centering
\begin{{tikzpicture}}
\begin{{axis}}[
    width=\linewidth, height=4.2cm,
    xlabel={{$t$ (s)}}, ylabel={{$a$ (m/s$^2$)}},
    xmin=0, xmax={t_max}, ymin=-5, ymax=5,
    restrict y to domain*=-5:5,
    unbounded coords=jump,
    grid=both, grid style={{gray!25}},
    axis line style={{thick}},
    tick label style={{font=\tiny}},
    label style={{font=\scriptsize}},
    legend style={{at={{(0.5,-0.34)}}, anchor=north, legend columns=4,
        font=\fontsize{{6}}{{7}}\selectfont, draw=none, /tikz/every even column/.append style={{column sep=1em}}}},
]
% Baseline a_x 实线
\addplot[deepblue, line width=1.8pt]
    table[col sep=comma, x=t, y=a_qp, discard if not={{mode}}{{baseline}}] {{\datapath st_curves.csv}};
\addlegendentry{{Baseline\,$a_x$}}
% GTOC a_x 实线
\addplot[vibrantgreen, line width=1.8pt]
    table[col sep=comma, x=t, y=a_qp, discard if not={{mode}}{{gtoc}}] {{\datapath st_curves.csv}};
\addlegendentry{{GTOC\,$a_x$}}
% Baseline a_y dashed
\addplot[deepblue, line width=1.4pt, dashed]
    table[col sep=comma, x=t, y=a_y, discard if not={{mode}}{{baseline}}] {{\datapath st_curves.csv}};
\addlegendentry{{Baseline\,$a_y$}}
% GTOC a_y dashed
\addplot[vibrantgreen, line width=1.4pt, dashed]
    table[col sep=comma, x=t, y=a_y, discard if not={{mode}}{{gtoc}}] {{\datapath st_curves.csv}};
\addlegendentry{{GTOC\,$a_y$}}
\end{{axis}}
\end{{tikzpicture}}
\caption{{纵向/横向加速度对比（$a_x$ 实线、$a_y$ 虚线；蓝 Baseline、绿 GTOC）}}
\end{{subfigure}}

\vspace{{0.8em}}

\begin{{subfigure}}[b]{{\textwidth}}
\centering
\begin{{tikzpicture}}
\begin{{axis}}[
    width=\linewidth, height=4.2cm,
    xlabel={{$t$ (s)}}, ylabel={{$j$ (m/s$^3$)}},
    xmin=0, xmax={t_max},
    grid=both, grid style={{gray!25}},
    axis line style={{thick}},
    tick label style={{font=\tiny}},
    label style={{font=\scriptsize}},
    legend style={{at={{(0.5,-0.34)}}, anchor=north, legend columns=2,
        font=\fontsize{{6}}{{7}}\selectfont, draw=none, /tikz/every even column/.append style={{column sep=2em}}}},
]
\addplot[deepblue, line width=1.6pt]
    table[col sep=comma, x=t, y=j_qp, discard if not={{mode}}{{baseline}}] {{\datapath st_curves.csv}};
\addlegendentry{{Baseline\,$j$}}
\addplot[vibrantgreen, line width=1.6pt]
    table[col sep=comma, x=t, y=j_qp, discard if not={{mode}}{{gtoc}}] {{\datapath st_curves.csv}};
\addlegendentry{{GTOC\,$j$}}
\end{{axis}}
\end{{tikzpicture}}
\caption{{jerk 对比}}
\end{{subfigure}}
"""


def main():
    generated = []
    for scn in SCENARIOS:
        meta_path = FIGDIR / "data" / scn / "meta.json"
        meta = json.loads(meta_path.read_text())
        obs_list = OBSTACLES[scn]

        for fig_type, gen_fn, args in [
            ("sl", gen_sl, (scn, meta, obs_list)),
            ("st", gen_st, (scn, meta, obs_list)),
            ("va", gen_va, (scn, meta)),
        ]:
            content = gen_fn(*args)
            fname = FIGDIR / f"fig_exp_{scn}_{fig_type}.tex"
            fname.write_text(content, encoding="utf-8")
            generated.append(fname.name)
            print(f"  wrote  {fname.name}")

    print(f"\n共生成 {len(generated)} 个文件。")


if __name__ == "__main__":
    main()
