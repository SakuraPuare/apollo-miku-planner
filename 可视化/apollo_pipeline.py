# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "matplotlib>=3.8",
#     "numpy>=1.26",
#     "scipy>=1.11",
#     "osqp>=0.6.3",
# ]
# ///
"""Apollo path-then-speed 全链路复刻 — Baseline vs MIKU 对照可视化。

执行链（对应 Apollo lane_follow/conf/pipeline.pb.txt）：

  Path 阶段：
    ① PathBoundsDecider     — 给 SL 平面横向 [l_min, l_max]
    ② PathOptimizer (QP)    — 在 SL bounds 内出 l(s)

  Speed 阶段：
    ③ SpeedBoundsDecider 1  — 把障碍物预测轨迹投到 ST 图（依赖 path）
    ④ PathTimeHeuristicOpt  — DP 在 ST 网格上粗搜 s_dp(t)
    ⑤ SpeedDecider          — 按 DP 结果给每个障碍物贴 YIELD/OVERTAKE 标签
    ⑥ SpeedBoundsDecider 2  — 按决策重建 s_j^ub / s_j^lb
    ⑦ PiecewiseJerkSpeed    — QP 出最终平滑 s(t), v(t), a(t)

  MIKU 改动：① 用 τ(s)-shifted 障碍位置；⑥ 之后多注入一路 corridor 约束。

输出 PNG：apollo_pipeline.png（6 子图：SL × ST × 时序，左 Baseline / 右 MIKU）。
"""

from __future__ import annotations

import csv
import json
import os
import time
import warnings
from dataclasses import dataclass
from typing import List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import osqp
import scipy.sparse as sp
from matplotlib.patches import Circle, Polygon, Rectangle

warnings.filterwarnings("ignore")

# CJK 字体兜底
for f in ("Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Zen Hei",
          "Source Han Sans CN", "Source Han Sans SC", "Noto Sans"):
    try:
        mpl.font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False


# ============================ 场景定义 ============================

@dataclass
class Ego:
    s0: float = 0.0
    l0: float = 0.0
    v0: float = 8.0
    a0: float = 0.0
    W: float = 1.8
    L: float = 4.0


@dataclass
class Obstacle:
    s0: float
    l0: float
    vs: float = 0.0
    vl: float = 0.0
    W: float = 0.5
    L: float = 0.5
    is_static: bool = False
    name: str = ""
    # 论文第五章第二节：障碍物类型，决定 f_type 因子
    obs_type: str = "vehicle"  # "ped" | "bike" | "vehicle" | "unknown_movable" | "static"

    def position_at(self, t: float) -> Tuple[float, float]:
        return self.s0 + self.vs * t, self.l0 + self.vl * t


@dataclass
class Scenario:
    ego: Ego
    obstacles: List[Obstacle]
    s_max: float = 25.0
    t_max: float = 3.5
    l_road_min: float = -1.875
    l_road_max: float = 1.875
    # Baseline 用统一 δ（Apollo `GetBufferBetweenADCCenterAndEdge`）
    delta_baseline: float = 0.3
    # MIKU 差异化 δ_i 上下界（论文第五章第四节 式(5.10)）
    delta_min: float = 0.10
    delta_max: float = 0.40
    # LaneBorrow：模拟 Apollo LaneBorrowPath
    lane_borrow: str = "none"   # "none" | "left" | "right" | "both"
    lane_width: float = 3.75


# ============================ 第八章 消融开关（5 个正交组件） ============================

@dataclass
class AblationFlags:
    """MIKU 5 个组件级开关，对应论文第五至七章各小节算法步骤。

    C1 tau_shift       第六章步骤1-2 — 时变 SL 投影 τ(s)-shifted 障碍位置
    C2 grouping        第六章步骤3   — 扫描线纵向连通分量合并
    C3 max_gap         第六章步骤4-5 — 组内 k+1 间隙 argmax 选 p*
    C4 threat_delta    第五章第四节 式(5.10) — 多因子威胁度 → 差异化 δ_i
    C5 corridor_inject 第七章 SBD2 后扩展 — (s_k, τ_k) 走廊注入 ST
    """
    tau_shift: bool = True
    grouping: bool = True
    max_gap: bool = True
    threat_delta: bool = True
    corridor_inject: bool = True
    name: str = "M5_full"

    @classmethod
    def baseline(cls) -> "AblationFlags":
        return cls(False, False, False, False, False, "M0_baseline")

    @classmethod
    def full(cls) -> "AblationFlags":
        return cls(True, True, True, True, True, "M5_full")

    @classmethod
    def from_mode(cls, mode_or_flags) -> "AblationFlags":
        if isinstance(mode_or_flags, cls):
            return mode_or_flags
        if mode_or_flags == "baseline":
            return cls.baseline()
        if mode_or_flags == "miku":
            return cls.full()
        raise ValueError(f"unknown mode: {mode_or_flags!r}")

    def all_off(self) -> bool:
        return not any([self.tau_shift, self.grouping, self.max_gap,
                        self.threat_delta, self.corridor_inject])


# ============================ 第五章 多因子威胁度 → δ_i ============================

# 论文式 (5.5) 权重
THREAT_WEIGHTS = (0.30, 0.20, 0.15, 0.10, 0.25)
T_CRIT = 2.0     # 临界 TTC
T_MAX = 7.0      # 最大关注 TTC
D_CLUSTER = 10.0 # 交互密度聚类半径
V_LIMIT = 12.0   # 道路限速（用于 f_vel sigmoid 归一化）

# 论文式 (5.8) f_type 离散映射
F_TYPE_MAP = {
    "ped": 1.0, "bike": 1.0, "vehicle": 0.7,
    "unknown_movable": 0.5, "static": 0.3,
    "cone": 0.15,  # 交通锥/反光屏障：小尺寸、低质量、置信度高，威胁权重最低
}


def f_ttc(obs: Obstacle, ego: Ego) -> float:
    ds = obs.s0 - ego.s0
    rel_v = ego.v0 - obs.vs
    if ds <= 0 or rel_v <= 1e-3:
        return 0.0
    ttc = ds / rel_v
    if ttc <= T_CRIT:
        return 1.0
    if ttc >= T_MAX:
        return 0.0
    return (T_MAX - ttc) / (T_MAX - T_CRIT)


def f_overlap(obs: Obstacle, ego: Ego) -> float:
    obs_lo, obs_hi = obs.l0 - obs.W / 2, obs.l0 + obs.W / 2
    ego_lo, ego_hi = ego.l0 - ego.W / 2, ego.l0 + ego.W / 2
    overlap = max(0.0, min(obs_hi, ego_hi) - max(obs_lo, ego_lo))
    denom = max(0.1, min(obs.W, ego.W))
    return min(1.0, overlap / denom)


def f_vel(obs: Obstacle, ego: Ego) -> float:
    rel_v = ego.v0 - obs.vs
    return 1.0 / (1.0 + np.exp(-5.0 * rel_v / V_LIMIT))


def f_type(obs: Obstacle) -> float:
    return F_TYPE_MAP.get(obs.obs_type, 0.5)


def f_inter(obs: Obstacle, all_obs: List[Obstacle]) -> float:
    if len(all_obs) <= 1:
        return 0.0
    total = 0.0
    for j in all_obs:
        if j is obs:
            continue
        d = float(np.hypot(obs.s0 - j.s0, obs.l0 - j.l0))
        if d < D_CLUSTER:
            total += (D_CLUSTER - d) / D_CLUSTER
    return min(1.0, total / max(1, len(all_obs) - 1))


def compute_threat(obs: Obstacle, scn: Scenario) -> float:
    w = THREAT_WEIGHTS
    return (w[0] * f_ttc(obs, scn.ego) + w[1] * f_overlap(obs, scn.ego)
            + w[2] * f_vel(obs, scn.ego) + w[3] * f_type(obs)
            + w[4] * f_inter(obs, scn.obstacles))


def compute_delta(obs: Obstacle, scn: Scenario) -> float:
    """论文第五章第四节 式(5.10)：δ_i = δ_min + (δ_max - δ_min) · Θ_i"""
    theta = compute_threat(obs, scn)
    return scn.delta_min + (scn.delta_max - scn.delta_min) * theta


# 场景库 —— 每个场景一个独立 PNG
SCENARIOS = {
    "01_crossing_ped": Scenario(
        ego=Ego(s0=0.0, l0=0.0, v0=8.0, a0=0.0),
        obstacles=[
            Obstacle(s0=12.0, l0=-0.6, vs=0.0, vl=1.2, W=0.5, L=0.5,
                     is_static=False, name="行人", obs_type="ped"),
        ],
        s_max=25.0, t_max=5.0,
    ),

    "02_ped_plus_parked": Scenario(
        ego=Ego(s0=0.0, l0=0.0, v0=8.0, a0=0.0),
        obstacles=[
            Obstacle(s0=10.0, l0=-0.5, vs=0.0, vl=1.2, W=0.5, L=0.5,
                     is_static=False, name="行人", obs_type="ped"),
            Obstacle(s0=22.0, l0=1.3, vs=0.0, vl=0.0, W=1.0, L=4.0,
                     is_static=True, name="停车", obs_type="static"),
        ],
        s_max=32.0, t_max=6.5,
    ),

    "03_narrow_cones": Scenario(
        # 双侧交通锥构成窄路 — 第5章差异化裕度对照
        # Baseline 一刀切 δ=0.30 → l_min > l_max → blocked；
        # MIKU 识别交通锥低威胁 → δ_i≈0.19 → ego 中心可走余量约 0.07 m → 通过。
        ego=Ego(s0=0.0, l0=0.0, v0=4.0, a0=0.0),
        obstacles=[
            # 左侧锥列（l=+1.20, W=0.15）三个，纵向 s=20/30/40
            Obstacle(s0=20.0, l0=1.20, vs=0.0, vl=0.0, W=0.15, L=0.5,
                     is_static=True, name="锥L1", obs_type="cone"),
            Obstacle(s0=30.0, l0=1.20, vs=0.0, vl=0.0, W=0.15, L=0.5,
                     is_static=True, name="锥L2", obs_type="cone"),
            Obstacle(s0=40.0, l0=1.20, vs=0.0, vl=0.0, W=0.15, L=0.5,
                     is_static=True, name="锥L3", obs_type="cone"),
            # 右侧锥列（l=-1.20, W=0.15）三个，与左列对称
            Obstacle(s0=20.0, l0=-1.20, vs=0.0, vl=0.0, W=0.15, L=0.5,
                     is_static=True, name="锥R1", obs_type="cone"),
            Obstacle(s0=30.0, l0=-1.20, vs=0.0, vl=0.0, W=0.15, L=0.5,
                     is_static=True, name="锥R2", obs_type="cone"),
            Obstacle(s0=40.0, l0=-1.20, vs=0.0, vl=0.0, W=0.15, L=0.5,
                     is_static=True, name="锥R3", obs_type="cone"),
        ],
        s_max=50.0, t_max=14.0,
    ),

    "04_dense_construction": Scenario(
        # 单车道维修封闭 + 交通锥导流至左侧相邻车道
        # 入口漏斗 5 锥（由右沿斜跨至左沿）+ 维持段 8 屏障（沿左沿连续墙）+ 出口漏斗 5 锥（反向）
        # 所有锥与屏障构成单一大型连通分量；MIKU 识别为整体导流, 一次性 LaneBorrow
        # Baseline 逐障碍物贪心：入口漏斗段每锥独立选侧, 受 room_left/room_right 摆动, 路径锯齿
        ego=Ego(s0=0.0, l0=0.0, v0=6.0, a0=0.0),
        obstacles=[
            # 入口漏斗 (s=15-27): 5 锥连续, 由原车道右沿斜跨至左沿; ego 在 s=0-15 段有 15m 加速与对齐
            Obstacle(s0=16.0, l0=-1.50, vs=0.0, vl=0.0, W=0.4, L=2.5, is_static=True, name="锥E1", obs_type="static"),
            Obstacle(s0=18.5, l0=-0.85, vs=0.0, vl=0.0, W=0.4, L=2.5, is_static=True, name="锥E2", obs_type="static"),
            Obstacle(s0=21.0, l0=-0.20, vs=0.0, vl=0.0, W=0.4, L=2.5, is_static=True, name="锥E3", obs_type="static"),
            Obstacle(s0=23.5, l0=0.50,  vs=0.0, vl=0.0, W=0.4, L=2.5, is_static=True, name="锥E4", obs_type="static"),
            Obstacle(s0=26.0, l0=1.20,  vs=0.0, vl=0.0, W=0.4, L=2.5, is_static=True, name="锥E5", obs_type="static"),
            # 维持段 (s=27-59): 8 段水马横跨车道分界线 (l=2.0, W=1.0 → 占据 l∈[1.5,2.5], 跨入借道车道)
            # Baseline 视作 "borrow 车道有障碍" → 反方向 push 右, 与入口锥桶 push 左产生 l_min > l_max 冲突
            Obstacle(s0=29.0, l0=2.00, vs=0.0, vl=0.0, W=1.0, L=4.0, is_static=True, name="水马M1", obs_type="static"),
            Obstacle(s0=33.0, l0=2.00, vs=0.0, vl=0.0, W=1.0, L=4.0, is_static=True, name="水马M2", obs_type="static"),
            Obstacle(s0=37.0, l0=2.00, vs=0.0, vl=0.0, W=1.0, L=4.0, is_static=True, name="水马M3", obs_type="static"),
            Obstacle(s0=41.0, l0=2.00, vs=0.0, vl=0.0, W=1.0, L=4.0, is_static=True, name="水马M4", obs_type="static"),
            Obstacle(s0=45.0, l0=2.00, vs=0.0, vl=0.0, W=1.0, L=4.0, is_static=True, name="水马M5", obs_type="static"),
            Obstacle(s0=49.0, l0=2.00, vs=0.0, vl=0.0, W=1.0, L=4.0, is_static=True, name="水马M6", obs_type="static"),
            Obstacle(s0=53.0, l0=2.00, vs=0.0, vl=0.0, W=1.0, L=4.0, is_static=True, name="水马M7", obs_type="static"),
            Obstacle(s0=57.0, l0=2.00, vs=0.0, vl=0.0, W=1.0, L=4.0, is_static=True, name="水马M8", obs_type="static"),
            # 出口漏斗 (s=59-71): 5 锥连续, 由左沿斜跨回原车道右沿
            Obstacle(s0=60.0, l0=1.20,  vs=0.0, vl=0.0, W=0.4, L=2.5, is_static=True, name="锥X1", obs_type="static"),
            Obstacle(s0=62.5, l0=0.50,  vs=0.0, vl=0.0, W=0.4, L=2.5, is_static=True, name="锥X2", obs_type="static"),
            Obstacle(s0=65.0, l0=-0.20, vs=0.0, vl=0.0, W=0.4, L=2.5, is_static=True, name="锥X3", obs_type="static"),
            Obstacle(s0=67.5, l0=-0.85, vs=0.0, vl=0.0, W=0.4, L=2.5, is_static=True, name="锥X4", obs_type="static"),
            Obstacle(s0=70.0, l0=-1.50, vs=0.0, vl=0.0, W=0.4, L=2.5, is_static=True, name="锥X5", obs_type="static"),
        ],
        s_max=85.0, t_max=15.0,
        lane_borrow="left",
    ),
}

# 默认场景（兼容旧接口）
SCENARIO = SCENARIOS["01_crossing_ped"]


# ============================ 到达时间 τ(s) ============================

def arrival_time(s: float, scn: Scenario) -> float:
    e = scn.ego
    ds = s - e.s0
    if ds < 0:
        return 0.0
    if abs(e.a0) < 1e-3:
        return ds / max(e.v0, 1e-3)
    disc = e.v0 ** 2 + 2 * e.a0 * ds
    if disc < 0:
        return 1e6
    return (-e.v0 + np.sqrt(disc)) / e.a0


# ============================ ① PathBoundsDecider ============================

def _baseline_path_bounds(scn: Scenario, s_arr: np.ndarray):
    """Apollo PathBoundsDecider 复刻 — IsStatic 过滤 + 逐障碍物贪心 nudge。"""
    e = scn.ego
    eff_l_max = scn.l_road_max + (scn.lane_width if scn.lane_borrow in ("left", "both") else 0.0)
    eff_l_min = scn.l_road_min - (scn.lane_width if scn.lane_borrow in ("right", "both") else 0.0)
    road_buffer = scn.delta_baseline
    l_min = np.full_like(s_arr, eff_l_min + road_buffer + e.W / 2)
    l_max = np.full_like(s_arr, eff_l_max - road_buffer - e.W / 2)

    for obs in scn.obstacles:
        if not obs.is_static:
            continue  # IsStatic() 过滤
        for i, s in enumerate(s_arr):
            os_, ol_ = obs.position_at(0.0)
            if abs(os_ - s) > obs.L / 2 + e.L / 2:
                continue
            obs_l_left = ol_ + obs.W / 2 + scn.delta_baseline + e.W / 2
            obs_l_right = ol_ - obs.W / 2 - scn.delta_baseline - e.W / 2
            room_left = eff_l_max - obs_l_left
            room_right = obs_l_right - eff_l_min
            if room_right >= room_left:
                l_max[i] = min(l_max[i], obs_l_right)
            else:
                l_min[i] = max(l_min[i], obs_l_left)
    return l_min, l_max, eff_l_min, eff_l_max


def _miku_path_bounds(scn: Scenario, s_arr: np.ndarray,
                       flags: Optional[AblationFlags] = None, debug=False):
    """MIKU PathBoundsDecider — 论文第六章算法\\ref{alg:optimal_band}：

    步骤1: 到达时间 τ(s_i^-)
    步骤2: 时变 SL 投影 + 差异化 δ_i → u_i = l_i^- - δ_i, v_i = l_i^+ + δ_i
    步骤3: 按 s_i^- 升序，扫描线分组（s_i^- ≤ s_max 入当前组）
    步骤4: 组内按 u_i 升序排，计算 k+1 个间隙 g_p（式 6.gap_def）
    步骤5: p* = argmax g_p；分配 d_(i)：i ≤ p* → L（左绕），i > p* → R（右绕）
    步骤6: 在该组的纵向区间内置 l^+ = u_(p*+1)（or l_road^+），l^- = v_(p*)（or l_road^-）

    flags 控制 4 个组件的启停（C1/C2/C3/C4），默认 full。

    返回 (l_min, l_max, eff_l_min, eff_l_max, debug_info)。
    """
    if flags is None:
        flags = AblationFlags.full()
    e = scn.ego
    eff_l_max = scn.l_road_max + (scn.lane_width if scn.lane_borrow in ("left", "both") else 0.0)
    eff_l_min = scn.l_road_min - (scn.lane_width if scn.lane_borrow in ("right", "both") else 0.0)

    road_buffer = scn.delta_min  # 路边裕度退化为最小裕度（无威胁）
    l_min = np.full_like(s_arr, eff_l_min + road_buffer + e.W / 2)
    l_max = np.full_like(s_arr, eff_l_max - road_buffer - e.W / 2)

    # —— 步骤1+2：对每个障碍物在其 s_i^- 处计算 SL 投影（τ-shifted 动态位置）+ 差异化 δ_i
    obs_proj = []
    for obs in scn.obstacles:
        s_minus_static = obs.s0 - obs.L / 2
        s_plus_static = obs.s0 + obs.L / 2
        # 动态障碍物：用 τ(s_i^-) 时刻的预测位置；C1 关闭时退化为 t=0 快照
        if obs.is_static or not flags.tau_shift:
            tau = 0.0
        else:
            tau = arrival_time(s_minus_static, scn)
        os_, ol_ = obs.position_at(tau)
        s_minus = os_ - obs.L / 2
        s_plus = os_ + obs.L / 2
        # C4：差异化 δ_i 关闭时退化为统一 delta_baseline
        delta = compute_delta(obs, scn) if flags.threat_delta else scn.delta_baseline
        u = ol_ - obs.W / 2 - delta  # 右侧通行边（自车从右过则 ego 中心 ≤ u - W/2）
        v = ol_ + obs.W / 2 + delta  # 左侧通行边（自车从左过则 ego 中心 ≥ v + W/2）
        obs_proj.append({
            "obs": obs, "s_minus": s_minus, "s_plus": s_plus,
            "u": u, "v": v, "delta": delta,
        })

    # —— 步骤3：按 s_i^- 升序，扫描线合连通分量
    # C2 关闭：每个障碍物自成一组（退化为逐障碍物决策）
    obs_proj.sort(key=lambda r: r["s_minus"])
    groups: List[List[dict]] = []
    if not flags.grouping:
        groups = [[r] for r in obs_proj]
    else:
        s_max_run = -float("inf")
        for r in obs_proj:
            if not groups or r["s_minus"] > s_max_run:
                groups.append([r])
                s_max_run = r["s_plus"]
            else:
                groups[-1].append(r)
                s_max_run = max(s_max_run, r["s_plus"])

    # —— 步骤4-5：组内 max-gap 求解，得到分组的 [l^-, l^+]
    group_decisions = []
    for grp in groups:
        # 剔除已完全越出有效路面的障碍物（论文第六章第四节边界情形）
        active = [r for r in grp if r["u"] < eff_l_max and r["v"] > eff_l_min]
        if not active:
            group_decisions.append({
                "grp": grp, "l_minus": eff_l_min, "l_plus": eff_l_max,
                "p_star": None, "g_star": eff_l_max - eff_l_min, "ordered": [],
            })
            continue
        # 按 u_i 升序（u 相同时按 v 降序——论文第六章第四节第三条）
        ordered = sorted(active, key=lambda r: (r["u"], -r["v"]))
        k = len(ordered)
        # 计算 k+1 个间隙
        gaps = []
        # g_0 = u_(1) - l_road^-（自车走最右通道，所有障碍均右绕）
        gaps.append(ordered[0]["u"] - eff_l_min)
        for p in range(1, k):
            gaps.append(ordered[p]["u"] - ordered[p - 1]["v"])
        # g_k = l_road^+ - v_(k)
        gaps.append(eff_l_max - ordered[-1]["v"])
        # C3 关闭：退化为「整组绕一侧」二元决策，比较 g_0 与 g_k
        if flags.max_gap:
            p_star = int(np.argmax(gaps))
        else:
            p_star = k if gaps[k] >= gaps[0] else 0
        # 分配 L/R：i ≤ p* → 左绕（在通道左侧 → ego 走通道右侧 → ego l ≤ u_(p*+1)）
        # 论文记号：L_p = {(1)..(p)}，R_p = {(p+1)..(k)}；通行带 l^+ = min_{R} u, l^- = max_{L} v
        if p_star == 0:
            l_minus = eff_l_min
            l_plus = ordered[0]["u"]
        elif p_star == k:
            l_minus = ordered[-1]["v"]
            l_plus = eff_l_max
        else:
            # 0 < p* < k：L = {(1)..(p*)}, R = {(p*+1)..(k)}
            l_minus = max(r["v"] for r in ordered[:p_star])
            l_plus = min(r["u"] for r in ordered[p_star:])
        group_decisions.append({
            "grp": grp, "l_minus": l_minus, "l_plus": l_plus,
            "p_star": p_star, "g_star": gaps[p_star],
            "ordered": ordered, "gaps": gaps,
        })

    # —— 步骤6：把每组的决策投影回 path_boundary
    # 论文第七章第二节：每个 s 截面上用 τ(s) 重算障碍物位置 → l_min/l_max(s) 反映障碍物横向移动
    # 分组结构与 p_star 沿用步骤 4-5 的 t=0 选择（论文保守近似），但每个 s 处重算 (u_i, v_i)
    for gd in group_decisions:
        grp = gd["grp"]
        s_lo = min(r["s_minus"] for r in grp) - e.L / 2
        s_hi = max(r["s_plus"] for r in grp) + e.L / 2
        p_star = gd["p_star"]
        ordered = gd["ordered"]  # 按 t=0 时 u_i 升序

        # 对纯静态组 fallback 到原标量结果（无时变）
        all_static = all(r["obs"].is_static for r in grp)

        for i, s in enumerate(s_arr):
            if not (s_lo <= s <= s_hi):
                continue
            if p_star is None:
                continue

            if all_static:
                # 静态组：直接用 step 4-5 的固定 l_minus / l_plus
                l_lo_ego = gd["l_minus"] + e.W / 2
                l_hi_ego = gd["l_plus"] - e.W / 2
            else:
                # 动态组：在该 s 处重算 τ(s) 与每个障碍物的时变 (u, v)
                tau_s = arrival_time(float(s), scn)
                uv_pairs = []
                active_mask = []
                for r_orig in ordered:
                    obs = r_orig["obs"]
                    tau_use = 0.0 if obs.is_static else tau_s
                    os_t, ol_t = obs.position_at(tau_use)
                    # 活跃性：障碍物当前纵向位置与该 s 的距离 ≤ L/2 + ego_L/2 才记入
                    is_active = abs(os_t - s) <= (obs.L / 2 + e.L / 2)
                    delta = r_orig["delta"]
                    uv_pairs.append((ol_t - obs.W / 2 - delta,
                                     ol_t + obs.W / 2 + delta))
                    active_mask.append(is_active)

                # 仅活跃障碍物参与 L/R 分配；若全不活跃则该 s 处不收紧
                if not any(active_mask):
                    continue

                # 沿用 t=0 选定的 p_star 进行 L/R 分配
                k = len(uv_pairs)
                left_uv = [uv_pairs[idx] for idx in range(p_star)
                           if active_mask[idx]]
                right_uv = [uv_pairs[idx] for idx in range(p_star, k)
                            if active_mask[idx]]
                if p_star == 0:
                    l_minus_s = eff_l_min
                    l_plus_s = min((uv[0] for uv in right_uv),
                                   default=eff_l_max)
                elif p_star == k:
                    l_minus_s = max((uv[1] for uv in left_uv),
                                    default=eff_l_min)
                    l_plus_s = eff_l_max
                else:
                    l_minus_s = max((uv[1] for uv in left_uv),
                                    default=eff_l_min)
                    l_plus_s = min((uv[0] for uv in right_uv),
                                   default=eff_l_max)

                l_lo_ego = l_minus_s + e.W / 2
                l_hi_ego = l_plus_s - e.W / 2

            # 取多组重叠时的并集收紧（保守）
            l_min[i] = max(l_min[i], l_lo_ego)
            l_max[i] = min(l_max[i], l_hi_ego)

    return l_min, l_max, eff_l_min, eff_l_max, group_decisions


def path_bounds_decider(scn: Scenario, mode_or_flags):
    """Apollo PathBoundsDecider 入口（支持字符串 mode 与 AblationFlags 两种调用）。

    - 'baseline' / AblationFlags.baseline()：Apollo IsStatic 过滤 + 逐障碍物贪心 nudge
    - 'miku'     / AblationFlags.full()    ：扫描线分组 + 最大间隙策略
    - 任意 AblationFlags                    ：5 个组件级开关消融

    返回 (s_arr, l_min, l_max, blocked_idx, group_decisions)。
    blocked_idx=-1 表示全程通畅；group_decisions 仅 MIKU 路径分支非空。
    """
    flags = AblationFlags.from_mode(mode_or_flags)
    e = scn.ego
    s_arr = np.arange(0.0, scn.s_max + 0.01, 0.5)
    group_decisions = []
    if flags.all_off():
        l_min, l_max, _, _ = _baseline_path_bounds(scn, s_arr)
    else:
        l_min, l_max, _, _, group_decisions = _miku_path_bounds(scn, s_arr, flags)

    # ego 起点位置硬约束
    l_min[0] = l_max[0] = e.l0

    # Apollo 真实行为：l_min > l_max 直接 blocked，下游 trim。无 squeeze hack。
    blocked_idx = -1
    for i in range(len(s_arr)):
        if l_min[i] > l_max[i]:
            blocked_idx = i
            break

    if blocked_idx >= 0:
        # Trim：blocked 之后的 path 锁死到上一个可行的中线
        if blocked_idx > 0:
            prev_mid = 0.5 * (l_min[blocked_idx - 1] + l_max[blocked_idx - 1])
        else:
            prev_mid = e.l0
        for i in range(blocked_idx, len(s_arr)):
            l_min[i] = l_max[i] = prev_mid

    return s_arr, l_min, l_max, blocked_idx, group_decisions


# ============================ ② Path QP（piecewise jerk path） ============================

def path_optimizer(s_arr, l_min, l_max):
    N = len(s_arr)
    ds = s_arr[1] - s_arr[0]
    w_l = 0.5
    w_dl = 100.0
    w_ddl = 800.0

    P = np.zeros((N, N))
    for j in range(N):
        P[j, j] += 2 * w_l
    for j in range(N - 1):
        c = 2 * w_dl / ds ** 2
        P[j, j] += c; P[j+1, j+1] += c
        P[j, j+1] -= c; P[j+1, j] -= c
    for j in range(N - 2):
        c = 2 * w_ddl / ds ** 4
        idx = [j, j+1, j+2]
        coef = [1, -2, 1]
        for a in range(3):
            for b in range(3):
                P[idx[a], idx[b]] += c * coef[a] * coef[b]
    P_sp = sp.csc_matrix(P)
    q = np.zeros(N)
    A = sp.eye(N, format="csc")
    prob = osqp.OSQP()
    prob.setup(P_sp, q, A, l_min, l_max,
               verbose=False, polish=True, max_iter=40000,
               eps_abs=1e-6, eps_rel=1e-6)
    t0 = time.perf_counter()
    res = prob.solve()
    qp_ms = (time.perf_counter() - t0) * 1000
    if res.info.status != "solved":
        return np.clip(np.zeros(N), l_min, l_max), qp_ms
    return res.x, qp_ms


# ============================ ③ SpeedBoundsDecider 1：障碍物投到 ST ============================

def st_boundary_mapper(scn: Scenario, s_arr_path, l_path):
    """对每个障碍物，沿时间 t 检查它和 ego path 的横向重叠；重叠时给出 (t, s_lo, s_hi)。"""
    e = scn.ego
    boundaries = []
    ts = np.arange(0.0, scn.t_max + 0.01, 0.05)

    for obs in scn.obstacles:
        intervals = []
        for t in ts:
            os_, ol_ = obs.position_at(t)
            if os_ < 0 or os_ > scn.s_max:
                continue
            l_ego = float(np.interp(os_, s_arr_path, l_path))
            # ST mapper 仅检查几何重叠；安全裕度 δ 已在 PathBounds 阶段吃掉，不再叠加
            ego_l_lo = l_ego - e.W / 2
            ego_l_hi = l_ego + e.W / 2
            obs_l_lo = ol_ - obs.W / 2
            obs_l_hi = ol_ + obs.W / 2
            if obs_l_lo >= ego_l_hi or obs_l_hi <= ego_l_lo:
                continue  # 横向不重叠（含边界严格分离）
            s_lo = os_ - obs.L / 2 - e.L / 2
            s_hi = os_ + obs.L / 2 + e.L / 2
            intervals.append((float(t), float(s_lo), float(s_hi)))
        boundaries.append({"name": obs.name, "intervals": intervals,
                           "is_static": obs.is_static})
    return boundaries


# ============================ ④ PathTimeHeuristicOptimizer (DP) ============================

def speed_dp(scn: Scenario, st_bounds):
    e = scn.ego
    dt = 0.1
    ds = 0.5
    nt = int(scn.t_max / dt) + 1
    ns = int(scn.s_max / ds) + 1
    ts = np.linspace(0.0, scn.t_max, nt)
    ss = np.linspace(0.0, scn.s_max, ns)

    forbidden = np.zeros((nt, ns), dtype=bool)
    for b in st_bounds:
        for (t, s_lo, s_hi) in b["intervals"]:
            ti = int(round(t / dt))
            if 0 <= ti < nt:
                lo = max(0, int(np.floor(s_lo / ds)))
                hi = min(ns - 1, int(np.ceil(s_hi / ds)))
                forbidden[ti, lo:hi+1] = True

    INF = 1e15
    cost = np.full((nt, ns), INF)
    parent = np.full((nt, ns), -1, dtype=np.int32)
    cost[0, 0] = 0.0

    v_ref, w_v, w_a = e.v0, 1.0, 0.5
    a_min, a_max, v_max = -4.0, 2.0, 13.0

    for ti in range(nt - 1):
        for si in range(ns):
            if cost[ti, si] >= INF:
                continue
            if forbidden[ti, si]:
                continue
            v_now = (si - parent[ti, si]) * ds / dt if parent[ti, si] >= 0 else e.v0
            sj_lo = si
            sj_hi = min(ns - 1, si + int(np.ceil(v_max * dt / ds)))
            for sj in range(sj_lo, sj_hi + 1):
                if forbidden[ti + 1, sj]:
                    continue  # 硬禁行
                v_eff = (sj - si) * ds / dt
                if v_eff < 0 or v_eff > v_max + 1e-3:
                    continue
                a_eff = (v_eff - v_now) / dt
                if a_eff < a_min - 0.1 or a_eff > a_max + 0.1:
                    continue
                step = w_v * (v_eff - v_ref) ** 2 + w_a * a_eff ** 2
                nc = cost[ti, si] + step
                if nc < cost[ti + 1, sj]:
                    cost[ti + 1, sj] = nc
                    parent[ti + 1, sj] = si

    last = cost[-1].copy()
    last[forbidden[-1]] = INF
    if last.min() >= INF:
        last = cost[-1]
    best = int(np.argmin(last))
    path = [best]
    for ti in range(nt - 1, 0, -1):
        p = parent[ti, path[-1]]
        if p < 0:
            p = path[-1]
        path.append(int(p))
    path.reverse()
    s_dp = ss[path]
    return ts, s_dp, forbidden, ss


# ============================ ⑤ SpeedDecider + ⑥ SBD final ============================

def build_st_bounds(scn: Scenario, st_bounds, s_dp, ts,
                    corridor: Optional[List[Tuple[float, float]]] = None):
    """重建 s_j^ub / s_j^lb；动态障碍物默认 YIELD（Apollo DP 失败时的兜底逻辑）。"""
    dt = ts[1] - ts[0]
    nt = len(ts)
    # 默认 s_ub 设大（视化用）：让 ego 在没障碍/没 trim 时可以匀速跑到 t_max
    s_ub = np.full(nt, 1e4)
    s_lb = np.zeros(nt)

    # 静态障碍物：把全时段 s 上界压到障碍物 s_lo
    for b in st_bounds:
        if b["is_static"] and b["intervals"]:
            s_block = min(s for (_, s, _) in b["intervals"])
            s_ub[:] = np.minimum(s_ub, s_block)

    # 动态障碍物：默认 YIELD（s_ub 压到 s_lo）。DP 仅用于可视化粗解。
    for b in st_bounds:
        if b["is_static"]:
            continue
        for (t, s_lo, _s_hi) in b["intervals"]:
            ti = int(round(t / dt))
            if 0 <= ti < nt:
                s_ub[ti] = min(s_ub[ti], s_lo)

    if corridor:
        for (s_k, tau_k) in corridor:
            for j in range(nt):
                if ts[j] < tau_k:
                    s_ub[j] = min(s_ub[j], s_k)
    return s_ub, s_lb


# ============================ ⑦ PiecewiseJerkSpeedOptimizer (QP) ============================

def speed_qp(scn: Scenario, s_ub, s_lb, ts):
    e = scn.ego
    K = len(ts)
    dt = ts[1] - ts[0]
    n = 3 * K  # [s, v, a] × K
    v_ref, w_v, w_a, w_jerk = e.v0, 5.0, 1.0, 100.0
    v_max, a_min, a_max = 13.0, -4.0, 2.0

    P = np.zeros((n, n))
    q = np.zeros(n)
    for j in range(K):
        P[3*j+1, 3*j+1] += 2 * w_v
        P[3*j+2, 3*j+2] += 2 * w_a
        q[3*j+1] += -2 * w_v * v_ref
    for j in range(K - 1):
        c = 2 * w_jerk / dt ** 2
        P[3*j+2, 3*j+2] += c
        P[3*(j+1)+2, 3*(j+1)+2] += c
        P[3*j+2, 3*(j+1)+2] -= c
        P[3*(j+1)+2, 3*j+2] -= c

    eq_r, eq_c, eq_v, eq_b = [], [], [], []
    r = 0
    for j in range(K - 1):
        eq_r += [r]*4; eq_c += [3*(j+1), 3*j, 3*j+1, 3*j+2]
        eq_v += [1.0, -1.0, -dt, -0.5*dt**2]; eq_b.append(0.0); r += 1
        eq_r += [r]*3; eq_c += [3*(j+1)+1, 3*j+1, 3*j+2]
        eq_v += [1.0, -1.0, -dt]; eq_b.append(0.0); r += 1
    for k, val in [(0, e.s0), (1, e.v0), (2, e.a0)]:
        eq_r += [r]; eq_c += [k]; eq_v += [1.0]; eq_b.append(val); r += 1

    A_eq = sp.csc_matrix((eq_v, (eq_r, eq_c)), shape=(r, n))
    b_eq = np.array(eq_b)

    lb = np.empty(n); ub = np.empty(n)
    for j in range(K):
        lb[3*j] = s_lb[j];   ub[3*j] = max(s_ub[j], s_lb[j] + 1e-6)
        lb[3*j+1] = 0;       ub[3*j+1] = v_max
        lb[3*j+2] = a_min;   ub[3*j+2] = a_max

    A = sp.vstack([A_eq, sp.eye(n, format="csc")], format="csc")
    l = np.concatenate([b_eq, lb])
    u = np.concatenate([b_eq, ub])

    prob = osqp.OSQP()
    prob.setup(sp.csc_matrix(P), q, A, l, u,
               verbose=False, polish=True, max_iter=60000,
               eps_abs=1e-5, eps_rel=1e-5)
    t0 = time.perf_counter()
    res = prob.solve()
    qp_ms = (time.perf_counter() - t0) * 1000
    if res.info.status != "solved":
        return None, None, None, qp_ms
    x = res.x
    return x[0::3], x[1::3], x[2::3], qp_ms


# ============================ 全链路执行 ============================

def run_pipeline(mode_or_flags, scn: Scenario):
    flags = AblationFlags.from_mode(mode_or_flags)
    s_arr, l_min, l_max, blocked_idx, group_decisions = path_bounds_decider(scn, flags)
    l_path, path_qp_ms = path_optimizer(s_arr, l_min, l_max)
    st_bounds = st_boundary_mapper(scn, s_arr, l_path)
    ts, s_dp, forbidden, ss = speed_dp(scn, st_bounds)

    corridor = None
    if flags.corridor_inject and group_decisions:
        # 论文第六章步骤7：仅对"依赖动态障碍物移开"的位置注入 (s_k, τ_k)
        # — 即：连通分量内含动态障碍物，且其 SL 投影是 ego 路径在该 s 段的活跃约束
        corridor = []
        for gd in group_decisions:
            grp = gd["grp"]
            dynamic = [r for r in grp if not r["obs"].is_static]
            if not dynamic:
                continue
            # 取组内最早出现的动态障碍物作为走廊顶点（避免重复注入同一组）
            r = min(dynamic, key=lambda r: r["s_minus"])
            s_k = r["s_minus"] - scn.ego.L / 2
            tau_k = arrival_time(s_k, scn)
            corridor.append((s_k, tau_k))

    s_ub, s_lb = build_st_bounds(scn, st_bounds, s_dp, ts, corridor)

    # Apollo TrimPathBounds：blocked 时强制 ego 在阻塞 s 之前停下
    blocked_s = None
    if blocked_idx >= 0:
        blocked_s = max(s_arr[blocked_idx] - scn.ego.L / 2, 0.0)
        s_ub = np.minimum(s_ub, blocked_s)

    s_qp, v_qp, a_qp, speed_qp_ms = speed_qp(scn, s_ub, s_lb, ts)

    # 横向加速度 a_y(t) = v(t)^2 · κ(s(t))
    # 直道前提：κ_ref = 0 → κ(s) ≈ l''(s)，由 l_path 二阶中心差分得到
    ds = s_arr[1] - s_arr[0] if len(s_arr) >= 2 else 0.5
    kappa_s = np.zeros_like(s_arr)
    if len(s_arr) >= 3:
        kappa_s[1:-1] = (l_path[2:] - 2.0 * l_path[1:-1] + l_path[:-2]) / (ds * ds)
        kappa_s[0] = kappa_s[1]
        kappa_s[-1] = kappa_s[-2]
    if s_qp is not None:
        kappa_t = np.interp(s_qp, s_arr, kappa_s)
        a_y = v_qp ** 2 * kappa_t
    else:
        a_y = None

    return dict(s_arr=s_arr, l_min=l_min, l_max=l_max, l_path=l_path,
                kappa_s=kappa_s,
                blocked_idx=blocked_idx, blocked_s=blocked_s,
                st_bounds=st_bounds, ts=ts, s_dp=s_dp, forbidden=forbidden,
                ss=ss, s_ub=s_ub, s_lb=s_lb,
                s_qp=s_qp, v_qp=v_qp, a_qp=a_qp, a_y=a_y, corridor=corridor,
                qp_solve_ms={"path": path_qp_ms, "speed": speed_qp_ms,
                             "total": path_qp_ms + speed_qp_ms})


# ============================ 绘图 ============================

C_PED   = "#d62728"
C_STAT  = "#7f7f7f"
C_PATH  = "#2ca02c"
C_BAS   = "#1f77b4"
C_MIKU  = "#2ca02c"
C_BOUND = "#ff7f0e"
C_DP    = "#9467bd"
C_QP    = "#000000"
C_CORR  = "#e377c2"


def _draw_vehicle(ax, x, y, length, width, heading_dir=1.0,
                  facecolor="gray", alpha=0.85, edgecolor="black",
                  name=None, name_color="white", zorder=3):
    """车辆/自行车：长方形 + 朝向三角（车头）。heading_dir: +1 沿+s 行驶，-1 沿-s。"""
    ax.add_patch(Rectangle((x - length/2, y - width/2), length, width,
                           facecolor=facecolor, alpha=alpha,
                           edgecolor=edgecolor, lw=0.6, zorder=zorder))
    # 车头三角（方向指示）
    front_x = x + heading_dir * length/2
    base_x = x + heading_dir * (length/2 - min(length*0.25, 0.6))
    tri = Polygon([(front_x, y),
                   (base_x, y + width*0.45),
                   (base_x, y - width*0.45)],
                  facecolor="white", edgecolor=edgecolor, lw=0.6,
                  alpha=min(1.0, alpha+0.1), zorder=zorder+0.1)
    ax.add_patch(tri)
    if name:
        ax.text(x - heading_dir*length*0.15, y, name,
                ha="center", va="center", fontsize=7.5,
                color=name_color, fontweight="bold", zorder=zorder+0.2)


def _draw_pedestrian(ax, x, y, color=C_PED, alpha=0.85, radius=0.3, zorder=3):
    """行人/VRU：圆形（顶视近圆柱）。"""
    ax.add_patch(Circle((x, y), radius, facecolor=color, alpha=alpha,
                        edgecolor=color, lw=0.4, zorder=zorder))


def _draw_obstacle(ax, obs: Obstacle, t: float, alpha: float = 0.85):
    os_, ol_ = obs.position_at(t)
    if obs.obs_type in ("ped",):
        _draw_pedestrian(ax, os_, ol_, color=C_PED, alpha=alpha,
                         radius=max(obs.W, obs.L)/2)
    elif obs.obs_type in ("bike", "vehicle"):
        # 车头朝向：vs>0 → +s；vs<0 → -s；vs=0 → +s（默认沿路停）
        heading = 1.0 if obs.vs >= 0 else -1.0
        col = "#7fb069" if obs.obs_type == "bike" else "#5b8def"
        _draw_vehicle(ax, os_, ol_, obs.L, obs.W, heading_dir=heading,
                      facecolor=col, alpha=alpha,
                      name=obs.name, name_color="white")
    else:  # static (parked, truck, cone)
        _draw_vehicle(ax, os_, ol_, obs.L, obs.W, heading_dir=1.0,
                      facecolor=C_STAT, alpha=alpha,
                      name=obs.name, name_color="white")


def plot_sl(ax, r, title, scn: Scenario):
    ax.set_title(title, fontsize=11, fontweight="bold")
    # 主车道
    ax.fill_between(r["s_arr"], scn.l_road_min, scn.l_road_max,
                    color="#f0f0f0", zorder=0)
    # 车道中心虚线
    ax.axhline(0, color="#aaa", ls=(0, (8, 8)), lw=0.8, zorder=0)
    # LaneBorrow：邻车道用淡蓝色区分
    if scn.lane_borrow in ("left", "both"):
        ax.fill_between(r["s_arr"], scn.l_road_max, scn.l_road_max + scn.lane_width,
                        color="#dde7f5", zorder=0, label="借用左车道")
        ax.axhline(scn.l_road_max, color="#888", ls="--", lw=0.5, zorder=0)
    if scn.lane_borrow in ("right", "both"):
        ax.fill_between(r["s_arr"], scn.l_road_min - scn.lane_width, scn.l_road_min,
                        color="#dde7f5", zorder=0, label="借用右车道")
        ax.axhline(scn.l_road_min, color="#888", ls="--", lw=0.5, zorder=0)
    ax.fill_between(r["s_arr"], r["l_min"], r["l_max"],
                    color="#fff3cc", alpha=0.6, label="可行 l 区间", zorder=1)
    ax.plot(r["s_arr"], r["l_min"], color=C_BOUND, lw=0.8, ls="--", zorder=2)
    ax.plot(r["s_arr"], r["l_max"], color=C_BOUND, lw=0.8, ls="--", zorder=2)
    ax.plot(r["s_arr"], r["l_path"], color=C_PATH, lw=2.6,
            label="Path l(s)", zorder=4)

    for obs in scn.obstacles:
        if obs.is_static:
            _draw_obstacle(ax, obs, 0, alpha=0.85)
        else:
            t_show_max = min(scn.t_max, 2.0)
            for t_show, alpha in [(0.0, 0.9), (t_show_max*0.33, 0.55),
                                  (t_show_max*0.66, 0.35), (t_show_max, 0.2)]:
                _draw_obstacle(ax, obs, t_show, alpha=alpha)
            os0, ol0 = obs.position_at(0)
            os1, ol1 = obs.position_at(t_show_max)
            ax.annotate("", xy=(os1, ol1), xytext=(os0, ol0),
                        arrowprops=dict(arrowstyle="->", color=C_PED, lw=1.2,
                                        alpha=0.8))
            ax.text(os0, ol0 + max(obs.W, 0.4) + 0.5,
                    f"{obs.name} v=({obs.vs:+.1f},{obs.vl:+.1f})",
                    fontsize=7.5, color=C_PED, ha="center")

    # ego 也用车辆样式
    _draw_vehicle(ax, scn.ego.s0, scn.ego.l0, scn.ego.L, scn.ego.W,
                  heading_dir=1.0, facecolor=C_BAS, alpha=0.55,
                  edgecolor=C_BAS, name="EGO", name_color="white", zorder=4)

    # blocked 标记
    if r.get("blocked_s") is not None:
        bs = r["blocked_s"]
        ax.axvline(bs, color="red", lw=1.6, ls="--", zorder=6,
                   label=f"Trim @ s={bs:.1f}（path blocked）")
        ax.plot(bs, 0, marker="X", color="red", markersize=14,
                mec="white", mew=1.5, zorder=7)

    ax.axhline(0, color="gray", ls=":", lw=0.5)
    ax.set_xlabel("s [m]")
    ax.set_ylabel("l [m]")
    ax.set_xlim(0, scn.s_max)
    # 视图范围根据是否借道扩展
    y_lo = scn.l_road_min - 0.4
    y_hi = scn.l_road_max + 0.4
    if scn.lane_borrow in ("left", "both"):
        y_hi = scn.l_road_max + scn.lane_width + 0.4
    if scn.lane_borrow in ("right", "both"):
        y_lo = scn.l_road_min - scn.lane_width - 0.4
    ax.set_ylim(y_lo, y_hi)
    # 1m=1m 保留障碍物真实比例；adjustable='datalim' 让画框先占满 gridspec 分配高度，
    # 再自动外扩 l 视图范围，避免 box 模式下 SL 行被压成细条。
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(loc="lower right", fontsize=7.5, ncol=2)
    ax.grid(alpha=0.3)


def plot_st(ax, r, title, scn: Scenario):
    ax.set_title(title, fontsize=11, fontweight="bold")
    for b in r["st_bounds"]:
        if not b["intervals"]:
            continue
        ts_p = [t for (t, _, _) in b["intervals"]]
        s_lo_p = [s for (_, s, _) in b["intervals"]]
        s_hi_p = [s for (_, _, s) in b["intervals"]]
        col = C_STAT if b["is_static"] else C_PED
        ax.fill_between(ts_p, s_lo_p, s_hi_p, color=col, alpha=0.35,
                        label=f"{b['name']} ST 边界")

    if r["corridor"]:
        # —— 走廊左下沿：连续 τ(s) 斜线 ——
        # 论文 Ω = {(s, t) | t ≥ τ(s) ∧ g_{p*}(s) ≥ W_ego}
        # τ(s) 是 ego 从 s_ego0 出发的到达时间函数，匀速时斜率 = v_ego，加速时为单调凹曲线
        s_grid = np.linspace(scn.ego.s0, scn.s_max, 200)
        tau_grid = np.array([arrival_time(float(s), scn) for s in s_grid])
        mask = (tau_grid >= 0) & (tau_grid <= scn.t_max)
        if mask.any():
            ax.plot(tau_grid[mask], s_grid[mask],
                    color=C_CORR, lw=2.2, ls="-",
                    label=r"$t{=}\tau(s)$ 走廊左下沿")
            # ego 不可达区（t < τ(s)）淡填色
            ax.fill_betweenx(s_grid[mask], 0, tau_grid[mask],
                             color=C_CORR, alpha=0.08)
            # 斜率注解（在曲线中段）
            mid_idx = mask.sum() // 2
            mid_t = tau_grid[mask][mid_idx]
            mid_s = s_grid[mask][mid_idx]
            slope_lbl = (f"斜率$\\,{{=}}\\,v_{{ego}}{{=}}{scn.ego.v0:.0f}$ m/s"
                         if abs(scn.ego.a0) < 1e-3
                         else f"$v_0{{=}}{scn.ego.v0:.0f}$, $a_0{{=}}{scn.ego.a0:.1f}$")
            ax.annotate(slope_lbl,
                        (mid_t, mid_s),
                        xytext=(mid_t + 0.4, mid_s - 1.2),
                        fontsize=7.5, color=C_CORR,
                        arrowprops=dict(arrowstyle="-", color=C_CORR, lw=0.5, alpha=0.6))

        # —— 离散采样点 (s_k, τ_k) 及对应的 s_j^ub 收紧效果矩形 ——
        for (s_k, tau_k) in r["corridor"]:
            ax.fill_betweenx([s_k, scn.s_max], 0, tau_k,
                             color=C_CORR, alpha=0.16, hatch="///",
                             edgecolor=C_CORR, linewidth=0.8,
                             label=f"$\\mathcal{{T}}$ 收紧 ($s{{>}}{s_k:.1f}$, $t{{<}}{tau_k:.2f}$)")
            ax.plot(tau_k, s_k, "P", color=C_CORR, markersize=11,
                    mec="black", mew=0.5)
            ax.annotate(f"$(\\tau_k{{=}}{tau_k:.2f}, s_k{{=}}{s_k:.1f})$",
                        (tau_k, s_k), xytext=(tau_k+0.15, s_k-2.0),
                        fontsize=8, color=C_CORR,
                        arrowprops=dict(arrowstyle="->", color=C_CORR, lw=0.6))

    ax.plot(r["ts"], r["s_ub"], color="red", lw=0.9, alpha=0.7,
            label="$s_j^{ub}$ (融合后)")
    ax.plot(r["ts"], r["s_dp"], color=C_DP, lw=1.4, ls="--",
            label="DP 粗解 $s_{dp}(t)$")
    if r["s_qp"] is not None:
        ax.plot(r["ts"], r["s_qp"], color=C_QP, lw=2.6,
                label="QP 精解 $s^*(t)$")
    ax.set_xlabel("t [s]")
    ax.set_ylabel("s [m]")
    ax.set_xlim(0, scn.t_max)
    ax.set_ylim(0, scn.s_max)
    ax.legend(loc="lower right", fontsize=7.2)
    ax.grid(alpha=0.3)


def compute_metrics(r, scn: Scenario):
    """轨迹质量指标：通行效率、平顺性、鲁棒性、计算开销，覆盖消融评分四个维度。"""
    qp_solve_ms = r.get("qp_solve_ms", {"path": 0.0, "speed": 0.0, "total": 0.0})
    s_target = scn.s_max - 1.0

    # 路径阶段几何指标（即便速度 QP 不可行，路径几何也存在）
    l_path = r.get("l_path")
    l_max_dev = 0.0
    decision_switches = 0
    if l_path is not None and len(l_path) >= 1:
        l_max_dev = float(np.max(np.abs(l_path)))
    if l_path is not None and len(l_path) >= 3:
        dl = np.diff(l_path)
        sign_changes = np.sum(np.diff(np.sign(dl)) != 0)
        decision_switches = int(sign_changes)
    kappa_s = r.get("kappa_s")
    kappa_rms = (float(np.sqrt(np.mean(kappa_s ** 2)))
                 if kappa_s is not None and len(kappa_s) > 0 else 0.0)

    blocked_flag = int(r.get("blocked_idx", -1) >= 0)

    if r["v_qp"] is None:
        return {"qp_solve_ms": qp_solve_ms, "_infeasible": True,
                "success": 0, "blocked": blocked_flag,
                "l_max_dev": l_max_dev, "kappa_rms": kappa_rms,
                "decision_switches": decision_switches,
                "tau_violation": 0}

    ts, v, a, s = r["ts"], r["v_qp"], r["a_qp"], r["s_qp"]
    dt = ts[1] - ts[0]
    # 巡航段平均速度：只算 ego 在主动行驶时（排除末端到达后停留）
    arrive_idx = int(np.argmax(s >= s_target)) if (s >= s_target).any() else -1
    if arrive_idx > 0:
        v_active = v[:arrive_idx + 1]
        a_active = a[:arrive_idx + 1]
        t_arrive = float(ts[arrive_idx])
    else:
        # 没到达：用 v>0.3 部分
        mask = v > 0.3
        v_active = v[mask] if mask.any() else v
        a_active = a[mask] if mask.any() else a
        t_arrive = float("nan")  # 表示未通过
    avg_v_cruise = float(np.mean(v_active))
    max_abs_a = float(np.max(np.abs(a_active)))
    jerk = np.diff(a) / dt
    max_abs_jerk = float(np.max(np.abs(jerk))) if len(jerk) > 0 else 0.0
    jerk_rms = (float(np.sqrt(np.mean(jerk ** 2)))
                if len(jerk) > 0 else 0.0)
    s_end = float(s[-1])
    efficiency = avg_v_cruise / scn.ego.v0
    success = 1 if (s_end >= s_target and not np.isnan(t_arrive)) else 0
    # 横向（向心）加速度极值
    a_y_arr = r.get("a_y")
    if a_y_arr is not None and len(a_y_arr) > 0:
        if arrive_idx > 0:
            a_y_active = a_y_arr[:arrive_idx + 1]
        else:
            mask = v > 0.3
            a_y_active = a_y_arr[mask] if mask.any() else a_y_arr
        max_abs_a_lat = float(np.max(np.abs(a_y_active)))
    else:
        max_abs_a_lat = 0.0

    # τ(s) 走廊违反次数：t<τ_k 时 ego 已越过 s_k 即违反
    tau_violation = 0
    corridor = r.get("corridor") or []
    for (s_k, tau_k) in corridor:
        for j, t_j in enumerate(ts):
            if t_j < tau_k and s[j] >= s_k:
                tau_violation += 1
    return dict(avg_v=avg_v_cruise, max_abs_a=max_abs_a,
                max_abs_a_lat=max_abs_a_lat,
                max_abs_jerk=max_abs_jerk, jerk_rms=jerk_rms,
                kappa_rms=kappa_rms, l_max_dev=l_max_dev,
                decision_switches=decision_switches,
                tau_violation=tau_violation,
                blocked=blocked_flag, success=success,
                s_end=s_end,
                efficiency=efficiency, t_arrive=t_arrive,
                qp_solve_ms=qp_solve_ms)


def _metrics_text(m):
    if m is None or m.get("_infeasible"):
        return "QP 不可行"
    if np.isnan(m["t_arrive"]):
        arrive_str = "未通过"
    else:
        arrive_str = f"t_arrive = {m['t_arrive']:.2f} s"
    return (f"巡航 v = {m['avg_v']:.2f} m/s   eff = {m['efficiency']*100:.0f}%\n"
            f"{arrive_str}     s_end = {m['s_end']:.1f} m\n"
            f"|a|max = {m['max_abs_a']:.2f} m/s²\n"
            f"|jerk|max = {m['max_abs_jerk']:.2f} m/s³")


def plot_compare_v(ax, r_b, r_g, scn: Scenario):
    ax.set_title("速度曲线 v(t) 对比", fontsize=11, fontweight="bold")
    if r_b["v_qp"] is not None:
        ax.plot(r_b["ts"], r_b["v_qp"], color=C_BAS, lw=2.4, label="Baseline")
    if r_g["v_qp"] is not None:
        ax.plot(r_g["ts"], r_g["v_qp"], color=C_MIKU, lw=2.4, label="MIKU")
    ax.axhline(scn.ego.v0, color="gray", ls=":", lw=0.8,
               label=f"v_ref={scn.ego.v0}")
    ax.set_xlabel("t [s]")
    ax.set_ylabel("v [m/s]")
    ax.legend(fontsize=9, loc="lower right")
    ax.set_xlim(0, scn.t_max)
    ax.set_ylim(-0.5, max(13, scn.ego.v0 + 4))
    ax.grid(alpha=0.3)
    # 指标文字框
    m_b = compute_metrics(r_b, scn)
    m_g = compute_metrics(r_g, scn)
    ax.text(0.02, 0.98,
            f"Baseline\n{_metrics_text(m_b)}",
            transform=ax.transAxes, fontsize=8, va="top", ha="left",
            bbox=dict(facecolor="white", edgecolor=C_BAS, lw=1.0,
                      alpha=0.92, boxstyle="round,pad=0.3"))
    ax.text(0.45, 0.98,
            f"MIKU\n{_metrics_text(m_g)}",
            transform=ax.transAxes, fontsize=8, va="top", ha="left",
            bbox=dict(facecolor="white", edgecolor=C_MIKU, lw=1.0,
                      alpha=0.92, boxstyle="round,pad=0.3"))


def plot_compare_a(ax, r_b, r_g, scn: Scenario):
    ax.set_title("加速度 a(t) 对比 + jerk", fontsize=11, fontweight="bold")
    dt = r_b["ts"][1] - r_b["ts"][0]
    if r_b["a_qp"] is not None:
        ax.plot(r_b["ts"], r_b["a_qp"], color=C_BAS, lw=2.4, label="Baseline a")
        jerk_b = np.diff(r_b["a_qp"]) / dt
        ax.plot(r_b["ts"][1:], jerk_b * 0.2, color=C_BAS, lw=1.0, ls=":",
                alpha=0.6, label="Baseline jerk×0.2")
    if r_g["a_qp"] is not None:
        ax.plot(r_g["ts"], r_g["a_qp"], color=C_MIKU, lw=2.4, label="MIKU a")
        jerk_g = np.diff(r_g["a_qp"]) / dt
        ax.plot(r_g["ts"][1:], jerk_g * 0.2, color=C_MIKU, lw=1.0, ls=":",
                alpha=0.6, label="MIKU jerk×0.2")
    ax.axhline(0, color="gray", ls=":", lw=0.6)
    ax.set_xlabel("t [s]")
    ax.set_ylabel("a [m/s²]  /  jerk×0.2 [m/s³]")
    ax.legend(fontsize=8, loc="upper right", ncol=2)
    ax.set_xlim(0, scn.t_max)
    ax.set_ylim(-5.5, 4.0)
    ax.grid(alpha=0.3)


SCENARIO_META = {
    "01_crossing_ped":           "场景四：单行人横穿（基础对照）",
    "02_ped_plus_parked":        "场景二：行人横穿 + 左侧停车（动+静混合）",
    "03_narrow_cones":           "场景一：窄路通行+双侧交通锥（差异化裕度对照）",
    "04_dense_construction":     "场景三：单车道维修封闭 + 交通锥导流借道（18 个静态障碍构成单一导流连通分量）",
}


def dump_data(data_dir: str, r_b, r_g, scn: Scenario, m_b, m_g):
    os.makedirs(data_dir, exist_ok=True)

    with open(os.path.join(data_dir, "sl.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mode", "s", "l_min", "l_max", "l_path"])
        for mode, r in [("baseline", r_b), ("miku", r_g)]:
            # blocked 模式下，path/bounds 在 blocked_idx 之后被冻结复制；
            # CSV 写入时直接截断到 blocked_idx + 1（含），让 pgfplots 看不到冻结行
            blocked_idx = r.get("blocked_idx", -1)
            n_rows = (blocked_idx + 1) if blocked_idx >= 0 else len(r["s_arr"])
            for i in range(n_rows):
                s = r["s_arr"][i]
                w.writerow([mode, f"{s:.4f}", f"{r['l_min'][i]:.4f}",
                            f"{r['l_max'][i]:.4f}", f"{r['l_path'][i]:.4f}"])

    with open(os.path.join(data_dir, "st_curves.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mode", "t", "s_ub", "s_dp", "s_qp", "v_qp", "a_qp", "a_y", "j_qp"])
        for mode, r in [("baseline", r_b), ("miku", r_g)]:
            ts = r["ts"]
            dt = (ts[1] - ts[0]) if len(ts) > 1 else 0.1
            a_arr = r["a_qp"] if r["a_qp"] is not None else None
            a_y_arr = r.get("a_y")
            for i, t in enumerate(ts):
                s_ub_val = f"{r['s_ub'][i]:.4f}" if r["s_ub"][i] < 9999 else "10000"
                s_dp_val = f"{r['s_dp'][i]:.4f}"
                if r["s_qp"] is not None:
                    s_qp_val = f"{r['s_qp'][i]:.4f}"
                    v_qp_val = f"{r['v_qp'][i]:.4f}"
                    a_qp_val = f"{r['a_qp'][i]:.4f}"
                    a_y_val = f"{a_y_arr[i]:.4f}" if a_y_arr is not None else ""
                    if i + 1 < len(a_arr):
                        j_qp_val = f"{(a_arr[i+1] - a_arr[i]) / dt:.4f}"
                    else:
                        j_qp_val = "0.0000"
                else:
                    s_qp_val = v_qp_val = a_qp_val = a_y_val = j_qp_val = ""
                w.writerow([mode, f"{t:.3f}", s_ub_val, s_dp_val,
                            s_qp_val, v_qp_val, a_qp_val, a_y_val, j_qp_val])

    with open(os.path.join(data_dir, "st_bounds.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mode", "obs_name", "t", "s_lo", "s_hi", "is_static"])
        for mode, r in [("baseline", r_b), ("miku", r_g)]:
            for b in r["st_bounds"]:
                is_s = 1 if b["is_static"] else 0
                for (t, s_lo, s_hi) in b["intervals"]:
                    w.writerow([mode, b["name"], f"{t:.3f}",
                                f"{s_lo:.4f}", f"{s_hi:.4f}", is_s])

    with open(os.path.join(data_dir, "corridor.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["s_k", "tau_k"])
        if r_g["corridor"]:
            for (s_k, tau_k) in r_g["corridor"]:
                w.writerow([f"{s_k:.4f}", f"{tau_k:.4f}"])

    with open(os.path.join(data_dir, "obstacles.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "obs_type", "is_static", "s0", "l0", "vs", "vl", "W", "L"])
        for obs in scn.obstacles:
            w.writerow([obs.name, obs.obs_type, 1 if obs.is_static else 0,
                        f"{obs.s0:.4f}", f"{obs.l0:.4f}",
                        f"{obs.vs:.4f}", f"{obs.vl:.4f}",
                        f"{obs.W:.4f}", f"{obs.L:.4f}"])

    def _metrics_dict(m, r):
        if m is None or m.get("_infeasible"):
            qp_ms = m["qp_solve_ms"] if m else {"path": 0.0, "speed": 0.0, "total": 0.0}
            return {
                "avg_v": None, "max_abs_a": None, "max_abs_a_lat": None,
                "max_abs_jerk": None,
                "s_end": None, "t_arrive": None,
                "blocked_idx": int(r.get("blocked_idx", -1)),
                "blocked_s": None if r.get("blocked_s") is None else round(float(r["blocked_s"]), 4),
                "qp_solve_ms": {
                    "path": round(qp_ms["path"], 4),
                    "speed": round(qp_ms["speed"], 4),
                    "total": round(qp_ms["total"], 4),
                },
                "efficiency": None,
            }
        t_arrive = None if (m["t_arrive"] != m["t_arrive"]) else m["t_arrive"]
        blocked_s = r.get("blocked_s")
        return {
            "avg_v": round(m["avg_v"], 4),
            "max_abs_a": round(m["max_abs_a"], 4),
            "max_abs_a_lat": round(m.get("max_abs_a_lat", 0.0), 4),
            "max_abs_jerk": round(m["max_abs_jerk"], 4),
            "s_end": round(m["s_end"], 4),
            "t_arrive": None if t_arrive is None else round(t_arrive, 4),
            "blocked_idx": int(r.get("blocked_idx", -1)),
            "blocked_s": None if blocked_s is None else round(float(blocked_s), 4),
            "qp_solve_ms": {
                "path": round(m["qp_solve_ms"]["path"], 4),
                "speed": round(m["qp_solve_ms"]["speed"], 4),
                "total": round(m["qp_solve_ms"]["total"], 4),
            },
            "efficiency": round(m["efficiency"], 4),
        }

    meta = {
        "scenario": os.path.basename(data_dir),
        "ego": {
            "s0": scn.ego.s0, "l0": scn.ego.l0,
            "v0": scn.ego.v0, "L": scn.ego.L, "W": scn.ego.W,
        },
        "scn_params": {
            "s_max": scn.s_max, "t_max": scn.t_max,
            "l_road_min": scn.l_road_min, "l_road_max": scn.l_road_max,
            "lane_borrow": scn.lane_borrow,
            "delta_baseline": scn.delta_baseline,
            "delta_min": scn.delta_min, "delta_max": scn.delta_max,
        },
        "metrics": {
            "baseline": _metrics_dict(m_b, r_b),
            "miku": _metrics_dict(m_g, r_g),
        },
    }
    with open(os.path.join(data_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def render_scenario(scn_name: str, scn: Scenario, out_path: str, data_dir: str = None):
    print(f"\n[{scn_name}] Running ...")
    r_b = run_pipeline("baseline", scn)
    r_g = run_pipeline("miku", scn)
    for label, r in [("Baseline", r_b), ("MIKU", r_g)]:
        bi = r.get("blocked_idx", -1)
        bs = r.get("blocked_s")
        qp_ok = "OK" if r["s_qp"] is not None else "INF"
        print(f"  {label}: blocked_idx={bi}, blocked_s={bs}, QP={qp_ok}")

    m_b = compute_metrics(r_b, scn)
    m_g = compute_metrics(r_g, scn)

    # SL 用 datalim 模式可占满分配高度（自动外扩 l 范围显示路侧空地），
    # 故给 SL 行加大高度比，让场景图更醒目。
    fig = plt.figure(figsize=(16, 15))
    gs = fig.add_gridspec(3, 2, height_ratios=[2.6, 3, 2.4], hspace=0.42, wspace=0.18)
    ax_sl_b = fig.add_subplot(gs[0, 0])
    ax_sl_g = fig.add_subplot(gs[0, 1])
    ax_st_b = fig.add_subplot(gs[1, 0])
    ax_st_g = fig.add_subplot(gs[1, 1])
    ax_v    = fig.add_subplot(gs[2, 0])
    ax_a    = fig.add_subplot(gs[2, 1])

    plot_sl(ax_sl_b, r_b, "Baseline ① PathBounds → ② Path QP", scn)
    plot_sl(ax_sl_g, r_g, "MIKU     ① PathBounds (τ-shifted) → ② Path QP", scn)
    plot_st(ax_st_b, r_b, "Baseline ③ SBD → ④ DP → ⑤⑥ → ⑦ QP", scn)
    plot_st(ax_st_g, r_g, "MIKU     ③ SBD → ④ DP → ⑤⑥ → 走廊注入 → ⑦ QP", scn)
    plot_compare_v(ax_v, r_b, r_g, scn)
    plot_compare_a(ax_a, r_b, r_g, scn)

    title = SCENARIO_META.get(scn_name, scn_name)
    fig.suptitle(f"{title} —— Baseline vs MIKU 全链路对照",
                 fontsize=14, fontweight="bold", y=0.995)
    plt.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out_path}")

    if data_dir is not None:
        dump_data(data_dir, r_b, r_g, scn, m_b, m_g)
        print(f"  → {data_dir}/")

    summary = []
    for label, r in [("Baseline", r_b), ("MIKU", r_g)]:
        if r["v_qp"] is None:
            summary.append((label, None))
        else:
            v_min = float(r["v_qp"].min())
            v_min_t = float(r["ts"][int(np.argmin(r["v_qp"]))])
            a_min = float(r["a_qp"].min())
            s_end = float(r["s_qp"][-1])
            summary.append((label, dict(v_min=v_min, v_min_t=v_min_t,
                                        a_min=a_min, s_end=s_end)))
    return summary


def main():
    out_dir = "outputs"
    data_root = "../图片/data"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(data_root, exist_ok=True)

    all_summary = {}
    for name, scn in SCENARIOS.items():
        png = os.path.join(out_dir, f"{name}.png")
        data_dir = os.path.join(data_root, name)
        os.makedirs(data_dir, exist_ok=True)
        all_summary[name] = render_scenario(name, scn, png, data_dir=data_dir)

    print("\n" + "=" * 78)
    print(f"{'场景':<32} {'方案':<10} {'v_min':>7} {'a_min':>7} {'s_end':>7}")
    print("-" * 78)
    for name, summ in all_summary.items():
        title = SCENARIO_META.get(name, name)
        for label, m in summ:
            if m is None:
                print(f"{title:<32} {label:<10} {'INF':>7} {'INF':>7} {'-':>7}")
            else:
                print(f"{title:<32} {label:<10} "
                      f"{m['v_min']:>6.2f}m/s {m['a_min']:>6.2f}m/s² "
                      f"{m['s_end']:>5.1f}m")
        print("-" * 78)


if __name__ == "__main__":
    main()
