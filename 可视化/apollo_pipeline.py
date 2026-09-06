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

  MIKU 改动：鲁棒时变占据、Top-K 空间同伦、多冲突时间同伦、
  双向 ST 约束与按需路径--速度细化；两个 QP 求解骨架保持不变。

输出 PNG：apollo_pipeline.png（6 子图：SL × ST × 时序，左 Baseline / 右 MIKU）。
"""

from __future__ import annotations

import csv
import copy
import json
import math
import os
import time
import warnings
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import osqp
import scipy.sparse as sp
from joint_homotopy_search import (
    AxisAlignedMotionSample,
    ContinuousSafetyCertificate,
    validate_candidate_constant_acceleration_safety,
    validate_candidate_continuous_safety,
)
from matplotlib.patches import Circle, Polygon, Rectangle
from miku_geometry import (
    ForbiddenInterval,
    enumerate_lateral_bands,
    enumerate_spatial_homotopies,
    solve_max_gap,
)
from miku_time import (
    ConflictPoint,
    OccupancyInterval,
    TimeWindow,
    enumerate_temporal_homotopies,
    safe_time_windows,
)

# Keep the scalar objective weights in one place.  The certified finite-label
# search imports these values so its certificate cannot silently drift from
# the path/speed QP builders below.
PATH_W_L = 0.5
PATH_W_DL = 100.0
PATH_W_DDL = 800.0
PATH_W_GOAL_HEADING = 5000.0
PATH_GOAL_HEADING_WINDOW = 4
SPEED_W_V = 5.0
SPEED_W_A = 1.0
SPEED_W_JERK = 100.0
SPEED_W_TERMINAL = 20.0

warnings.filterwarnings("ignore")

# CJK 字体兜底
for f in (
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "WenQuanYi Zen Hei",
    "Source Han Sans CN",
    "Source Han Sans SC",
    "Noto Sans",
):
    try:
        mpl.font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False


# ============================ 场景定义 ============================

DELTA_BASELINE = 0.30
DELTA_MIN = 0.10
DELTA_MAX = 0.40
PLANNER_CYCLE_MS = 100
GROUPING_THRESHOLD = 12.0
ALPHA_COEFF = 1.25
BORROW_MAX_DEPTH = 3
MIN_BORROW_WIDTH = 2.0
PLANNING_TIME_RANGE_MIN = 6.0
PLANNING_TIME_RANGE_MAX = 15.0
PATH_BOUNDARY_STEP = 0.5
PATH_GAP_EPSILON = 1e-6
ABLATION_FAIL_PENALTY_S = 5


@dataclass
class Ego:
    s0: float = 0.0
    l0: float = 0.0
    v0: float = 8.0
    a0: float = 0.0
    W: float = 2.11
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
    obs_type: str = (
        "vehicle"  # "ped" | "bike" | "vehicle" | "unknown_movable" | "static"
    )
    # Calibrated bounded prediction error.  MIKU propagates the initial
    # position radius with the velocity-error radius over the prediction time.
    uncertainty_s0: float = 0.0
    uncertainty_l0: float = 0.0
    uncertainty_vs: float = 0.0
    uncertainty_vl: float = 0.0
    # Optional CommonRoad sampled prediction.  The ordinary Apollo-style
    # experiments leave these empty and use the constant-velocity model above.
    # External adapters may provide a time-indexed centerline projection so
    # the planner does not silently discard the published trajectory states.
    prediction_t: Tuple[float, ...] = ()
    prediction_s: Tuple[float, ...] = ()
    prediction_l: Tuple[float, ...] = ()
    # Optional conservative body-occupancy envelope sampled from an external
    # scenario format.  The envelope is expressed in the same Frenet frame as
    # the planner and is consumed by both ST mapping and continuous safety
    # certificates.  Empty arrays retain the ordinary axis-aligned fallback.
    occupancy_t: Tuple[float, ...] = ()
    occupancy_s_min: Tuple[float, ...] = ()
    occupancy_s_max: Tuple[float, ...] = ()
    occupancy_l_min: Tuple[float, ...] = ()
    occupancy_l_max: Tuple[float, ...] = ()

    def __post_init__(self) -> None:
        uncertainty = (
            self.uncertainty_s0,
            self.uncertainty_l0,
            self.uncertainty_vs,
            self.uncertainty_vl,
        )
        if not all(math.isfinite(value) and value >= 0.0 for value in uncertainty):
            raise ValueError("prediction uncertainty radii must be finite and non-negative")
        if self.prediction_t or self.prediction_s or self.prediction_l:
            lengths = {len(self.prediction_t), len(self.prediction_s), len(self.prediction_l)}
            if len(lengths) != 1 or len(self.prediction_t) < 2:
                raise ValueError("sampled prediction arrays must have equal length >= 2")
            if not all(math.isfinite(value) for value in (*self.prediction_t, *self.prediction_s, *self.prediction_l)):
                raise ValueError("sampled prediction arrays must be finite")
            if any(next_t <= current_t for current_t, next_t in zip(self.prediction_t, self.prediction_t[1:])):
                raise ValueError("sampled prediction times must be strictly increasing")
        occupancy_arrays = (
            self.occupancy_t,
            self.occupancy_s_min,
            self.occupancy_s_max,
            self.occupancy_l_min,
            self.occupancy_l_max,
        )
        if any(occupancy_arrays):
            lengths = {len(array) for array in occupancy_arrays}
            if len(lengths) != 1 or len(self.occupancy_t) < 2:
                raise ValueError("occupancy arrays must have equal length >= 2")
            if not all(
                math.isfinite(value)
                for array in occupancy_arrays
                for value in array
            ):
                raise ValueError("occupancy arrays must be finite")
            if any(
                next_t <= current_t
                for current_t, next_t in zip(self.occupancy_t, self.occupancy_t[1:])
            ):
                raise ValueError("occupancy times must be strictly increasing")
            if any(
                s_min > s_max or l_min > l_max
                for s_min, s_max, l_min, l_max in zip(
                    self.occupancy_s_min,
                    self.occupancy_s_max,
                    self.occupancy_l_min,
                    self.occupancy_l_max,
                )
            ):
                raise ValueError("occupancy bounds must be ordered")

    def position_at(self, t: float) -> Tuple[float, float]:
        if self.prediction_t:
            query = float(t)
            times = np.asarray(self.prediction_t, dtype=float)
            stations = np.asarray(self.prediction_s, dtype=float)
            laterals = np.asarray(self.prediction_l, dtype=float)
            if query < times[0]:
                slope_s = (stations[1] - stations[0]) / (times[1] - times[0])
                slope_l = (laterals[1] - laterals[0]) / (times[1] - times[0])
                return (
                    float(stations[0] + slope_s * (query - times[0])),
                    float(laterals[0] + slope_l * (query - times[0])),
                )
            if query > times[-1]:
                slope_s = (stations[-1] - stations[-2]) / (times[-1] - times[-2])
                slope_l = (laterals[-1] - laterals[-2]) / (times[-1] - times[-2])
                return (
                    float(stations[-1] + slope_s * (query - times[-1])),
                    float(laterals[-1] + slope_l * (query - times[-1])),
                )
            return (
                float(np.interp(query, times, stations)),
                float(np.interp(query, times, laterals)),
            )
        return self.s0 + self.vs * t, self.l0 + self.vl * t

    def occupancy_bounds_at(self, t: float) -> Tuple[float, float, float, float]:
        """Return conservative ``(s_min, s_max, l_min, l_max)`` at time ``t``."""
        if self.occupancy_t:
            query = float(t)
            times = np.asarray(self.occupancy_t, dtype=float)
            values = tuple(
                np.asarray(array, dtype=float)
                for array in (
                    self.occupancy_s_min,
                    self.occupancy_s_max,
                    self.occupancy_l_min,
                    self.occupancy_l_max,
                )
            )
            return tuple(float(np.interp(query, times, array)) for array in values)  # type: ignore[return-value]
        center_s, center_l = self.position_at(float(t))
        return (
            center_s - self.L / 2.0,
            center_s + self.L / 2.0,
            center_l - self.W / 2.0,
            center_l + self.W / 2.0,
        )


@dataclass
class Scenario:
    ego: Ego
    obstacles: List[Obstacle]
    s_max: float = 25.0
    t_max: float = 3.5
    l_road_min: float = -1.875
    l_road_max: float = 1.875
    # Optional station-indexed lanelet center-feasible bounds.  External
    # adapters populate these from the route polygon; synthetic Apollo cases
    # retain the scalar bounds above.
    road_s_profile: np.ndarray | None = None
    road_l_min_profile: np.ndarray | None = None
    road_l_max_profile: np.ndarray | None = None
    # Baseline 用统一 δ（Apollo `GetBufferBetweenADCCenterAndEdge`）
    delta_baseline: float = DELTA_BASELINE
    # MIKU 差异化 δ_i 上下界（论文第五章第四节 式(5.10)）
    delta_min: float = DELTA_MIN
    delta_max: float = DELTA_MAX
    # LaneBorrow：模拟 Apollo LaneBorrowPath
    lane_borrow: str = "none"  # "none" | "left" | "right" | "both"
    lane_width: float = 3.75
    # Optional external-benchmark goal lateral coordinate.  Apollo-style
    # synthetic fixtures leave this unset and retain the original soft
    # centreline terminal objective.
    goal_lateral: float | None = None
    # CommonRoad goal-region projection.  When present, the terminal state
    # may land anywhere inside this conservative Frenet box; the centre
    # remains only a soft preference (and ``goal_lateral`` is retained for
    # legacy synthetic fixtures).
    goal_s_min: float | None = None
    goal_s_max: float | None = None
    goal_l_min: float | None = None
    goal_l_max: float | None = None
    goal_region_kind: str = "point"
    # Desired terminal heading relative to the reference-path tangent.  The
    # external adapter fills this from the official goal orientation; Apollo
    # synthetic fixtures leave it unset.
    goal_heading_error: float | None = None
    # External lanelet benchmarks can keep moving obstacles in ST only.  The
    # Apollo-style synthetic protocol retains the original dynamic path-bound
    # behavior for backwards-compatible ablations.
    dynamic_path_bounds: bool = True
    # Longitudinal limits are Apollo defaults for synthetic fixtures and are
    # overridden by the external adapter to match the official vehicle model.
    v_max: float = 13.0
    a_min: float = -4.0
    a_max: float = 2.0
    goal_time_start: float | None = None
    goal_time_end: float | None = None
    goal_v_min: float | None = None
    goal_v_max: float | None = None


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
    robust_prediction: bool = False

    @classmethod
    def baseline(cls) -> "AblationFlags":
        return cls(False, False, False, False, False, "M0_baseline")

    @classmethod
    def full(cls) -> "AblationFlags":
        return cls(True, True, True, True, True, "M5_full", True)

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
        return not any(
            [
                self.tau_shift,
                self.grouping,
                self.max_gap,
                self.threat_delta,
                self.corridor_inject,
                self.robust_prediction,
            ]
        )


# ============================ 第五章 多因子威胁度 → δ_i ============================

# 论文式 (5.5) 权重
THREAT_WEIGHTS = (0.30, 0.20, 0.15, 0.10, 0.25)
T_CRIT = 2.0  # 临界 TTC
T_MAX = 7.0  # 最大关注 TTC
D_CLUSTER = 10.0  # 交互密度聚类半径
V_LIMIT = 12.0  # 道路限速（用于 f_vel sigmoid 归一化）

# 论文式 (5.8) f_type 离散映射
F_TYPE_MAP = {
    "ped": 1.0,
    "bike": 1.0,
    "vehicle": 0.7,
    "unknown_movable": 0.5,
    "static": 0.3,
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
    return (
        w[0] * f_ttc(obs, scn.ego)
        + w[1] * f_overlap(obs, scn.ego)
        + w[2] * f_vel(obs, scn.ego)
        + w[3] * f_type(obs)
        + w[4] * f_inter(obs, scn.obstacles)
    )


def compute_delta(obs: Obstacle, scn: Scenario) -> float:
    """返回障碍物外侧附加缓冲（不含自车半宽）。"""
    theta = compute_threat(obs, scn)
    return scn.delta_min + (scn.delta_max - scn.delta_min) * theta


# 四个原始压力场景：保留 Baseline 易失败的临界构型，用于说明问题存在性与消融退化。
PRESSURE_SCENARIOS = {
    "01_crossing_ped": Scenario(
        ego=Ego(s0=0.0, l0=0.0, v0=8.0, a0=0.0),
        obstacles=[
            Obstacle(
                s0=12.0,
                l0=-0.6,
                vs=0.0,
                vl=1.25,
                W=0.5,
                L=0.5,
                is_static=False,
                name="行人",
                obs_type="ped",
            ),
        ],
        s_max=25.0,
        t_max=5.0,
    ),
    "02_ped_plus_parked": Scenario(
        ego=Ego(s0=0.0, l0=0.0, v0=8.0, a0=0.0),
        obstacles=[
            Obstacle(
                s0=10.0,
                l0=-0.5,
                vs=0.0,
                vl=1.5,
                W=0.5,
                L=0.5,
                is_static=False,
                name="行人",
                obs_type="ped",
            ),
            Obstacle(
                s0=22.0,
                l0=1.3,
                vs=0.0,
                vl=0.0,
                W=1.0,
                L=4.0,
                is_static=True,
                name="停车",
                obs_type="static",
            ),
        ],
        s_max=32.0,
        t_max=6.5,
    ),
    "03_narrow_cones": Scenario(
        # 混合障碍物窄路 — 第5章差异化裕度对照。
        # 左侧水马（static，高威胁）+ 右侧交通锥（cone，低威胁），
        # 多因子模型对两类障碍物给出不同 Θ_i → 不同 δ_i，
        # 统一裕度下通行带为零，差异化裕度释放锥侧空间使路径可行。
        ego=Ego(s0=0.0, l0=0.0, v0=4.0, a0=0.0),
        obstacles=[
            # 左侧水马（static, W=0.4, l=+1.55）三个
            Obstacle(
                s0=20.0,
                l0=1.55,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=0.8,
                is_static=True,
                name="水马L1",
                obs_type="static",
            ),
            Obstacle(
                s0=30.0,
                l0=1.55,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=0.8,
                is_static=True,
                name="水马L2",
                obs_type="static",
            ),
            Obstacle(
                s0=40.0,
                l0=1.55,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=0.8,
                is_static=True,
                name="水马L3",
                obs_type="static",
            ),
            # 右侧交通锥（cone, W=0.15, l=-1.35）三个
            Obstacle(
                s0=20.0,
                l0=-1.35,
                vs=0.0,
                vl=0.0,
                W=0.15,
                L=0.5,
                is_static=True,
                name="锥R1",
                obs_type="cone",
            ),
            Obstacle(
                s0=30.0,
                l0=-1.35,
                vs=0.0,
                vl=0.0,
                W=0.15,
                L=0.5,
                is_static=True,
                name="锥R2",
                obs_type="cone",
            ),
            Obstacle(
                s0=40.0,
                l0=-1.35,
                vs=0.0,
                vl=0.0,
                W=0.15,
                L=0.5,
                is_static=True,
                name="锥R3",
                obs_type="cone",
            ),
        ],
        s_max=50.0,
        t_max=14.0,
    ),
    "04_dense_construction": Scenario(
        # 单车道维修封闭 + 交通锥导流至左侧相邻车道
        # 入口漏斗 5 锥（由右沿斜跨至左沿）+ 维持段 8 屏障（沿左沿连续墙）+ 出口漏斗 5 锥（反向）
        # 所有锥与屏障构成单一大型连通分量；MIKU 识别为整体导流, 一次性 LaneBorrow
        # Baseline 逐障碍物贪心：入口漏斗段每锥独立选侧, 受 room_left/room_right 摆动, 路径锯齿
        ego=Ego(s0=0.0, l0=0.0, v0=6.0, a0=0.0),
        obstacles=[
            # 入口漏斗 (s=15-27): 5 锥连续, 由原车道右沿斜跨至左沿; ego 在 s=0-15 段有 15m 加速与对齐
            Obstacle(
                s0=16.0,
                l0=-1.50,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=2.5,
                is_static=True,
                name="锥E1",
                obs_type="static",
            ),
            Obstacle(
                s0=18.5,
                l0=-0.85,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=2.5,
                is_static=True,
                name="锥E2",
                obs_type="static",
            ),
            Obstacle(
                s0=21.0,
                l0=-0.20,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=2.5,
                is_static=True,
                name="锥E3",
                obs_type="static",
            ),
            Obstacle(
                s0=23.5,
                l0=0.50,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=2.5,
                is_static=True,
                name="锥E4",
                obs_type="static",
            ),
            Obstacle(
                s0=26.0,
                l0=1.20,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=2.5,
                is_static=True,
                name="锥E5",
                obs_type="static",
            ),
            # 维持段 (s=27-59): 8 段水马横跨车道分界线
            # Baseline 先受入口锥桶左推，再被水马右推，形成互斥边界。
            Obstacle(
                s0=29.0,
                l0=2.00,
                vs=0.0,
                vl=0.0,
                W=1.0,
                L=4.0,
                is_static=True,
                name="水马M1",
                obs_type="static",
            ),
            Obstacle(
                s0=33.0,
                l0=2.00,
                vs=0.0,
                vl=0.0,
                W=1.0,
                L=4.0,
                is_static=True,
                name="水马M2",
                obs_type="static",
            ),
            Obstacle(
                s0=37.0,
                l0=2.00,
                vs=0.0,
                vl=0.0,
                W=1.0,
                L=4.0,
                is_static=True,
                name="水马M3",
                obs_type="static",
            ),
            Obstacle(
                s0=41.0,
                l0=2.00,
                vs=0.0,
                vl=0.0,
                W=1.0,
                L=4.0,
                is_static=True,
                name="水马M4",
                obs_type="static",
            ),
            Obstacle(
                s0=45.0,
                l0=2.00,
                vs=0.0,
                vl=0.0,
                W=1.0,
                L=4.0,
                is_static=True,
                name="水马M5",
                obs_type="static",
            ),
            Obstacle(
                s0=49.0,
                l0=2.00,
                vs=0.0,
                vl=0.0,
                W=1.0,
                L=4.0,
                is_static=True,
                name="水马M6",
                obs_type="static",
            ),
            Obstacle(
                s0=53.0,
                l0=2.00,
                vs=0.0,
                vl=0.0,
                W=1.0,
                L=4.0,
                is_static=True,
                name="水马M7",
                obs_type="static",
            ),
            Obstacle(
                s0=57.0,
                l0=2.00,
                vs=0.0,
                vl=0.0,
                W=1.0,
                L=4.0,
                is_static=True,
                name="水马M8",
                obs_type="static",
            ),
            # 出口漏斗 (s=59-71): 5 锥连续, 由左沿斜跨回原车道右沿
            Obstacle(
                s0=60.0,
                l0=1.20,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=2.5,
                is_static=True,
                name="锥X1",
                obs_type="static",
            ),
            Obstacle(
                s0=62.5,
                l0=0.50,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=2.5,
                is_static=True,
                name="锥X2",
                obs_type="static",
            ),
            Obstacle(
                s0=65.0,
                l0=-0.20,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=2.5,
                is_static=True,
                name="锥X3",
                obs_type="static",
            ),
            Obstacle(
                s0=67.5,
                l0=-0.85,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=2.5,
                is_static=True,
                name="锥X4",
                obs_type="static",
            ),
            Obstacle(
                s0=70.0,
                l0=-1.50,
                vs=0.0,
                vl=0.0,
                W=0.4,
                L=2.5,
                is_static=True,
                name="锥X5",
                obs_type="static",
            ),
        ],
        s_max=85.0,
        t_max=15.0,
        lane_borrow="left",
    ),
}

# 四个配对可比场景：逐一复制原场景，只做时间窗或几何参数的轻量放宽。
COMPARABLE_SCENARIOS = copy.deepcopy(PRESSURE_SCENARIOS)

COMPARABLE_SCENARIOS["05_crossing_ped_cmp"] = COMPARABLE_SCENARIOS.pop(
    "01_crossing_ped"
)
COMPARABLE_SCENARIOS["05_crossing_ped_cmp"].t_max = 6.0

COMPARABLE_SCENARIOS["06_ped_plus_parked_cmp"] = COMPARABLE_SCENARIOS.pop(
    "02_ped_plus_parked"
)
for _obs in COMPARABLE_SCENARIOS["06_ped_plus_parked_cmp"].obstacles:
    if _obs.name == "停车":
        _obs.l0 = 1.60

COMPARABLE_SCENARIOS["07_narrow_cones_cmp"] = COMPARABLE_SCENARIOS.pop(
    "03_narrow_cones"
)
for _obs in COMPARABLE_SCENARIOS["07_narrow_cones_cmp"].obstacles:
    if _obs.obs_type == "static":
        _obs.l0 = 1.75  # 水马外移，Baseline 统一裕度下仍可通过
    # 锥侧保持 l=-1.35 不变

COMPARABLE_SCENARIOS["08_dense_construction_cmp"] = COMPARABLE_SCENARIOS.pop(
    "04_dense_construction"
)
for _obs in COMPARABLE_SCENARIOS["08_dense_construction_cmp"].obstacles:
    if _obs.name.startswith("水马"):
        _obs.l0 = 1.875

# 场景库 —— 主实验输出 8 个 PNG/CSV：4 压力 + 4 配对可比。
SCENARIOS = {}
SCENARIOS.update(PRESSURE_SCENARIOS)
SCENARIOS.update(COMPARABLE_SCENARIOS)

# 消融实验只使用原始压力场景，避免把可比复制场景重复计入组件必要性评分。
STRESS_SCENARIOS = PRESSURE_SCENARIOS

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
    disc = e.v0**2 + 2 * e.a0 * ds
    if disc < 0:
        return 1e6
    return (-e.v0 + np.sqrt(disc)) / e.a0


# ============================ ① PathBoundsDecider ============================


def _road_center_bounds(scn: Scenario, s_arr: np.ndarray):
    """Return lanelet-derived road bounds sampled at the path knots."""
    if (
        scn.road_s_profile is not None
        and scn.road_l_min_profile is not None
        and scn.road_l_max_profile is not None
        and len(scn.road_s_profile) >= 2
    ):
        profile_s = np.asarray(scn.road_s_profile, dtype=float)
        l_min = np.interp(
            s_arr,
            profile_s,
            np.asarray(scn.road_l_min_profile, dtype=float),
        )
        l_max = np.interp(
            s_arr,
            profile_s,
            np.asarray(scn.road_l_max_profile, dtype=float),
        )
    else:
        l_min = np.full_like(s_arr, float(scn.l_road_min), dtype=float)
        l_max = np.full_like(s_arr, float(scn.l_road_max), dtype=float)
    if scn.lane_borrow in ("right", "both"):
        l_min = l_min - scn.lane_width
    if scn.lane_borrow in ("left", "both"):
        l_max = l_max + scn.lane_width
    return l_min, l_max


def _baseline_path_bounds(scn: Scenario, s_arr: np.ndarray):
    """Apollo PathBoundsDecider 复刻 — IsStatic 过滤 + 逐障碍物贪心 nudge。"""
    e = scn.ego
    eff_l_min, eff_l_max = _road_center_bounds(scn, s_arr)
    road_buffer = scn.delta_baseline
    l_min = eff_l_min + road_buffer + e.W / 2
    l_max = eff_l_max - road_buffer - e.W / 2

    for obs in scn.obstacles:
        if not obs.is_static:
            continue  # IsStatic() 过滤
        for i, s in enumerate(s_arr):
            os_, ol_ = obs.position_at(0.0)
            if abs(os_ - s) > obs.L / 2 + e.L / 2:
                continue
            obs_l_left = ol_ + obs.W / 2 + scn.delta_baseline + e.W / 2
            obs_l_right = ol_ - obs.W / 2 - scn.delta_baseline - e.W / 2
            room_left = eff_l_max[i] - obs_l_left
            room_right = obs_l_right - eff_l_min[i]
            if room_right >= room_left:
                l_max[i] = min(l_max[i], obs_l_right)
            else:
                l_min[i] = max(l_min[i], obs_l_left)
    return l_min, l_max, eff_l_min, eff_l_max


def _miku_path_bounds(
    scn: Scenario,
    s_arr: np.ndarray,
    flags: Optional[AblationFlags] = None,
    debug=False,
    tau_fn: Optional[Callable[[float], float]] = None,
    candidate_rank: int = 0,
    split_overrides: Optional[dict[int, int]] = None,
    spatial_top_k: Optional[int] = 3,
):
    """MIKU PathBoundsDecider — 论文第六章算法\\ref{alg:optimal_band}：

    步骤1: 到达时间 τ(s_i^-)
    步骤2: 时变 SL 投影 + 差异化 δ_i → u_i = l_i^- - δ_i, v_i = l_i^+ + δ_i
    步骤3: 按 s_i^- 升序，扫描线分组（s_i^- ≤ s_max 入当前组）
    步骤4: 组内按 u_i 升序排，计算 k+1 个间隙 g_p（式 6.gap_def）
    步骤5: p* = argmax g_p；分配 d_(i)：i ≤ p* → L（左绕），i > p* → R（右绕）
    步骤6: 将整组 L/R 决策写回各障碍物自身 SLBoundary 对应的 s 截面；
           分组只统一绕行方向，不把整组纵向区间统一收缩成一个大边界。

    flags 控制空间、时间与鲁棒性组件的启停，默认 full。

    返回 (l_min, l_max, eff_l_min, eff_l_max, debug_info)。
    """
    if flags is None:
        flags = AblationFlags.full()
    if tau_fn is None:
        def default_tau(s: float) -> float:
            return arrival_time(s, scn)

        tau_fn = default_tau
    e = scn.ego
    eff_l_min, eff_l_max = _road_center_bounds(scn, s_arr)
    # The discrete homotopy solver uses a conservative global envelope for
    # ordering; each station is still clamped to its local lanelet bounds
    # before the path QP is formed.
    global_eff_l_min = float(np.min(eff_l_min))
    global_eff_l_max = float(np.max(eff_l_max))

    road_buffer = scn.delta_min  # 道路物理边界内缩半车宽与路侧安全裕度
    center_road_min = global_eff_l_min + road_buffer + e.W / 2
    center_road_max = global_eff_l_max - road_buffer - e.W / 2
    l_min = eff_l_min + road_buffer + e.W / 2
    l_max = eff_l_max - road_buffer - e.W / 2

    # —— 步骤1+2：对每个障碍物在其 s_i^- 处计算 SL 投影（τ-shifted 动态位置）+ 差异化 δ_i
    obs_proj = []
    for obs in scn.obstacles:
        if not scn.dynamic_path_bounds and not obs.is_static:
            continue
        s_minus_static = obs.s0 - obs.L / 2
        # 动态障碍物：用 τ(s_i^-) 时刻的预测位置；C1 关闭时退化为 t=0 快照
        if obs.is_static or not flags.tau_shift:
            tau = 0.0
        else:
            tau = tau_fn(s_minus_static)
        os_, ol_ = obs.position_at(tau)
        robust_s = (
            obs.uncertainty_s0 + abs(tau) * obs.uncertainty_vs
            if flags.robust_prediction and not obs.is_static
            else 0.0
        )
        robust_l = (
            obs.uncertainty_l0 + abs(tau) * obs.uncertainty_vl
            if flags.robust_prediction and not obs.is_static
            else 0.0
        )
        s_minus = os_ - obs.L / 2 - robust_s
        s_plus = os_ + obs.L / 2 + robust_s
        # C4：差异化 δ_i 关闭时退化为统一 delta_baseline
        delta = compute_delta(obs, scn) if flags.threat_delta else scn.delta_baseline
        center_buffer = e.W / 2 + delta
        u = ol_ - obs.W / 2 - center_buffer - robust_l
        v = ol_ + obs.W / 2 + center_buffer + robust_l
        obs_proj.append(
            {
                "obs": obs,
                "s_minus": s_minus,
                "s_plus": s_plus,
                "u": u,
                "v": v,
                "delta": delta,
            }
        )

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
    for group_index, grp in enumerate(groups):
        # 完全位于中心可行区间外的障碍物不收紧当前道路截面。
        active = [
            r for r in grp if r["u"] < center_road_max and r["v"] > center_road_min
        ]
        if not active:
            group_decisions.append(
                {
                    "grp": grp,
                    "l_minus": center_road_min,
                    "l_plus": center_road_max,
                    "p_star": None,
                    "g_star": center_road_max - center_road_min,
                    "ordered": [],
                }
            )
            continue
        # A localized lateral crossing is a temporal homotopy decision. Trying
        # to squeeze the path around it at one estimated arrival time makes the
        # path boundary discontinuous and can turn a feasible yield manoeuvre
        # into a false blockage. C5 owns these obstacles and transfers their
        # occupancy to the speed stage.
        temporal_only = [
            r
            for r in active
            if flags.corridor_inject
            and not r["obs"].is_static
            and abs(float(r["obs"].vl)) >= 0.2
            and abs(float(r["obs"].vs)) <= 1.0
        ]
        if temporal_only:
            active = [r for r in active if r not in temporal_only]
            if not active:
                group_decisions.append(
                    {
                        "grp": grp,
                        "l_minus": center_road_min,
                        "l_plus": center_road_max,
                        "p_star": None,
                        "g_star": center_road_max - center_road_min,
                        "ordered": [],
                        "temporal_only": temporal_only,
                    }
                )
                continue
        solution = solve_max_gap(
            [ForbiddenInterval(r["u"], r["v"]) for r in active],
            center_road_min,
            center_road_max,
        )
        # A pure dynamic full-width conflict is temporal, not a permanent path
        # blockage.  Preserve the static geometry here and leave the dynamic
        # occupancy to the downstream ST bounds.  If the static subset is also
        # infeasible, the ordinary blocked-path handling remains active.
        if solution.gap < PATH_GAP_EPSILON:
            newly_temporal = [r for r in active if not r["obs"].is_static]
            if newly_temporal:
                temporal_only.extend(newly_temporal)
                active = [r for r in active if r["obs"].is_static]
                if not active:
                    group_decisions.append(
                        {
                            "grp": grp,
                            "l_minus": center_road_min,
                            "l_plus": center_road_max,
                            "p_star": None,
                            "g_star": center_road_max - center_road_min,
                            "ordered": [],
                            "temporal_only": temporal_only,
                        }
                    )
                    continue
                solution = solve_max_gap(
                    [ForbiddenInterval(r["u"], r["v"]) for r in active],
                    center_road_min,
                    center_road_max,
                )
        ordered = [active[i] for i in solution.ordered_indices]
        k = len(ordered)
        gaps = list(solution.candidate_gaps)
        # C3 关闭：退化为「整组绕一侧」二元决策，比较 g_0 与 g_k
        if flags.max_gap:
            ranked_bands = enumerate_lateral_bands(
                [ForbiddenInterval(r["u"], r["v"]) for r in active],
                center_road_min,
                center_road_max,
                top_k=None,
            )
            selected_band = ranked_bands[min(candidate_rank, len(ranked_bands) - 1)]
            p_star = (
                split_overrides.get(group_index, selected_band.split_index)
                if split_overrides is not None
                else selected_band.split_index
            )
        else:
            ranked_bands = ()
            p_star = k if gaps[k] >= gaps[0] else 0
        # 分配 L/R：i ≤ p* → 左绕（在通道左侧 → ego 走通道右侧 → ego l ≤ u_(p*+1)）
        # 论文记号：L_p = {(1)..(p)}，R_p = {(p+1)..(k)}；通行带 l^+ = min_{R} u, l^- = max_{L} v
        if p_star == 0:
            l_minus = center_road_min
            l_plus = min(center_road_max, ordered[0]["u"])
        elif p_star == k:
            l_minus = max(center_road_min, max(r["v"] for r in ordered))
            l_plus = center_road_max
        else:
            # 0 < p* < k：L = {(1)..(p*)}, R = {(p*+1)..(k)}
            l_minus = max(center_road_min, max(r["v"] for r in ordered[:p_star]))
            l_plus = min(center_road_max, ordered[p_star]["u"])
        group_decisions.append(
            {
                "grp": grp,
                "l_minus": l_minus,
                "l_plus": l_plus,
                "p_star": p_star,
                "g_star": gaps[p_star],
                "ordered": ordered,
                "gaps": gaps,
                "temporal_only": temporal_only,
                "band_candidates": ranked_bands,
                "group_index": group_index,
            }
        )

    # Select one longitudinally coherent sequence from the Top-K band layers.
    # Explicit overrides and nonzero ranks are retained for ablation/oracle
    # experiments; the default planner uses the global dynamic program.
    spatial_homotopy = None
    spatial_homotopies = ()
    spatial_layers = [
        gd for gd in group_decisions if gd.get("band_candidates")
    ]
    if (
        flags.max_gap
        and split_overrides is None
        and spatial_layers
    ):
        exhaustive_count = int(np.prod([len(gd["band_candidates"]) for gd in spatial_layers]))
        spatial_homotopies = enumerate_spatial_homotopies(
            [gd["band_candidates"] for gd in spatial_layers],
            initial_lateral=e.l0,
            top_k=exhaustive_count if spatial_top_k is None else spatial_top_k,
            transition_weight=0.05,
            gap_epsilon=PATH_GAP_EPSILON,
        )
        spatial_homotopy = (
            spatial_homotopies[min(candidate_rank, len(spatial_homotopies) - 1)]
            if spatial_homotopies
            else None
        )
        if spatial_homotopy is not None:
            for gd, band in zip(
                spatial_layers,
                spatial_homotopy.bands,
                strict=True,
            ):
                gd["p_star"] = band.split_index
                gd["l_minus"] = band.lower
                gd["l_plus"] = band.upper
                gd["g_star"] = band.gap
                gd["selected_band"] = band

    for gd in group_decisions:
        gd["spatial_homotopy_cost"] = (
            None if spatial_homotopy is None else spatial_homotopy.cost
        )
        gd["spatial_homotopy_candidate_count"] = len(spatial_homotopies)

    # —— 步骤6：把每组的 L/R 决策投影回 path_boundary
    # 分组只决定同一连通分量内各障碍物的绕行侧；道路边界仍按单个障碍物
    # 自身的 SLBoundary 逐截面收缩，避免把整组区间压成一个统一大台阶。
    # 动态障碍物在每个 s 截面用 τ(s) 重算 (u_i, v_i)，静态障碍物保持 t=0。
    for gd in group_decisions:
        grp = gd["grp"]
        s_lo = min(r["s_minus"] for r in grp) - e.L / 2
        s_hi = max(r["s_plus"] for r in grp) + e.L / 2
        p_star = gd["p_star"]
        ordered = gd["ordered"]  # 按 t=0 时 u_i 升序

        for i, s in enumerate(s_arr):
            if not (s_lo <= s <= s_hi):
                continue
            if p_star is None:
                continue

            tau_s = tau_fn(float(s)) if flags.tau_shift else 0.0
            left_v = []
            right_u = []
            for idx, r_orig in enumerate(ordered):
                obs = r_orig["obs"]
                tau_use = 0.0 if obs.is_static else tau_s
                os_t, ol_t = obs.position_at(tau_use)
                robust_s = (
                    obs.uncertainty_s0 + abs(tau_use) * obs.uncertainty_vs
                    if flags.robust_prediction and not obs.is_static
                    else 0.0
                )
                robust_l = (
                    obs.uncertainty_l0 + abs(tau_use) * obs.uncertainty_vl
                    if flags.robust_prediction and not obs.is_static
                    else 0.0
                )
                s_minus_t = os_t - obs.L / 2 - robust_s
                s_plus_t = os_t + obs.L / 2 + robust_s
                if not (s_minus_t - e.L / 2 <= s <= s_plus_t + e.L / 2):
                    continue

                delta = r_orig["delta"]
                center_buffer = e.W / 2 + delta
                u_t = ol_t - obs.W / 2 - center_buffer - robust_l
                v_t = ol_t + obs.W / 2 + center_buffer + robust_l
                if idx < p_star:
                    left_v.append(v_t)
                else:
                    right_u.append(u_t)

            # 仅活跃障碍物收缩当前截面；若全不活跃，该 s 保持原道路边界。
            if not left_v and not right_u:
                continue

            l_lo_ego = max(left_v, default=float(l_min[i]))
            l_hi_ego = min(right_u, default=float(l_max[i]))

            # 取多组重叠时的并集收紧（保守）
            l_min[i] = max(l_min[i], l_lo_ego)
            l_max[i] = min(l_max[i], l_hi_ego)

    return l_min, l_max, eff_l_min, eff_l_max, group_decisions


def path_bounds_decider(
    scn: Scenario,
    mode_or_flags,
    tau_fn: Optional[Callable[[float], float]] = None,
    candidate_rank: int = 0,
    split_overrides: Optional[dict[int, int]] = None,
    spatial_top_k: Optional[int] = 3,
):
    """Apollo PathBoundsDecider 入口（支持字符串 mode 与 AblationFlags 两种调用）。

    - 'baseline' / AblationFlags.baseline()：Apollo IsStatic 过滤 + 逐障碍物贪心 nudge
    - 'miku'     / AblationFlags.full()    ：扫描线分组 + 最大间隙策略
    - 任意 AblationFlags                    ：5 个组件级开关消融

    返回 (s_arr, l_min, l_max, blocked_idx, group_decisions)。
    blocked_idx=-1 表示全程通畅；group_decisions 仅 MIKU 路径分支非空。
    """
    flags = AblationFlags.from_mode(mode_or_flags)
    e = scn.ego
    # Keep the external goal station as an exact path-QP knot.  A fixed
    # ``arange(..., 0.5)`` grid can end short of a CommonRoad goal station;
    # constraining the nearest knot then leaves the native writer to
    # interpolate an unconstrained terminal lateral state.  The linspace grid
    # preserves the <=0.5 m resolution while making the real goal endpoint a
    # hard path constraint.
    grid_count = max(int(np.ceil(float(scn.s_max) / 0.5)) + 1, 2)
    s_arr = np.linspace(0.0, float(scn.s_max), grid_count)
    group_decisions = []
    if flags.all_off():
        l_min, l_max, _, _ = _baseline_path_bounds(scn, s_arr)
    else:
        l_min, l_max, _, _, group_decisions = _miku_path_bounds(
            scn,
            s_arr,
            flags,
            tau_fn=tau_fn,
            candidate_rank=candidate_rank,
            split_overrides=split_overrides,
            spatial_top_k=spatial_top_k,
        )

    # ego 当前起点位置硬约束。初次规划 s0=0；滚动重规划时将已经驶过的
    # 前缀固定到当前横向状态，避免求解器把起点错误地留在全局 s=0。
    start_index = int(np.argmin(np.abs(s_arr - e.s0)))
    l_min[: start_index + 1] = e.l0
    l_max[: start_index + 1] = e.l0

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

    if scn.goal_l_min is not None and scn.goal_l_max is not None:
        goal_index = int(np.argmin(np.abs(s_arr - scn.s_max)))
        # CommonRoad's rectangle is a region, not a centre-point equality.
        # Intersect the terminal corridor with its conservative Frenet
        # projection and leave the centre as a soft objective downstream.
        l_min[goal_index] = max(l_min[goal_index], float(scn.goal_l_min))
        l_max[goal_index] = min(l_max[goal_index], float(scn.goal_l_max))
    elif scn.goal_lateral is not None:
        goal_index = int(np.argmin(np.abs(s_arr - scn.s_max)))
        goal_lateral = float(scn.goal_lateral)
        # A goal rectangle can be outside the currently selected homotopy
        # corridor.  Keep the candidate infeasible in that case (so the
        # caller records a real failure) rather than constructing an invalid
        # QP workspace through crossed endpoint bounds.
        if l_min[goal_index] - 1e-9 <= goal_lateral <= l_max[goal_index] + 1e-9:
            l_min[goal_index] = l_max[goal_index] = goal_lateral

    # Goal-region intersection can expose a genuine empty terminal corridor.
    # Trim it in the same fail-closed manner as Apollo PathBoundsDecider so a
    # malformed OSQP workspace is never constructed.
    invalid = np.flatnonzero(l_min > l_max + 1.0e-9)
    if len(invalid):
        first_invalid = int(invalid[0])
        blocked_idx = first_invalid if blocked_idx < 0 else min(blocked_idx, first_invalid)
        previous = e.l0 if blocked_idx == 0 else 0.5 * (
            l_min[blocked_idx - 1] + l_max[blocked_idx - 1]
        )
        l_min[blocked_idx:] = previous
        l_max[blocked_idx:] = previous

    return s_arr, l_min, l_max, blocked_idx, group_decisions


# ============================ ② Path QP（piecewise jerk path） ============================


def path_optimizer(s_arr, l_min, l_max, terminal_slope: float | None = None):
    N = len(s_arr)
    if np.any(np.asarray(l_min) > np.asarray(l_max) + 1.0e-9):
        # Preserve a deterministic fail-closed path for callers that invoke
        # the QP directly with an empty corridor.
        return np.minimum(np.maximum(np.zeros(N), l_max), l_min), 0.0
    ds = s_arr[1] - s_arr[0]
    w_l = PATH_W_L
    w_dl = PATH_W_DL
    w_ddl = PATH_W_DDL

    P = np.zeros((N, N))
    for j in range(N):
        P[j, j] += 2 * w_l
    for j in range(N - 1):
        c = 2 * w_dl / ds**2
        P[j, j] += c
        P[j + 1, j + 1] += c
        P[j, j + 1] -= c
        P[j + 1, j] -= c
    for j in range(N - 2):
        c = 2 * w_ddl / ds**4
        idx = [j, j + 1, j + 2]
        coef = [1, -2, 1]
        for a in range(3):
            for b in range(3):
                P[idx[a], idx[b]] += c * coef[a] * coef[b]
    terminal_heading_segments = ()
    if terminal_slope is not None and N >= 2:
        # In a Frenet frame, dl/ds = tan(heading - reference_heading) to first
        # order.  Penalising the last few finite-difference residuals makes
        # the geometric plan honour the official terminal orientation through
        # a gradual approach, rather than creating a single sharp endpoint
        # kink before the KS tracking stage.
        first_segment = max(0, N - 1 - PATH_GOAL_HEADING_WINDOW)
        terminal_heading_segments = tuple(range(first_segment, N - 1))
        c = 2.0 * PATH_W_GOAL_HEADING / ds**2
        for segment in terminal_heading_segments:
            left, right = segment, segment + 1
            P[left, left] += c
            P[right, right] += c
            P[left, right] -= c
            P[right, left] -= c
    P_sp = sp.csc_matrix(P)
    q = np.zeros(N)
    if terminal_heading_segments:
        linear = 2.0 * PATH_W_GOAL_HEADING * float(terminal_slope) / ds
        for segment in terminal_heading_segments:
            q[segment] += linear
            q[segment + 1] -= linear
    A = sp.eye(N, format="csc")
    prob = osqp.OSQP()
    prob.setup(
        P_sp,
        q,
        A,
        l_min,
        l_max,
        verbose=False,
        polish=True,
        max_iter=40000,
        eps_abs=1e-6,
        eps_rel=1e-6,
    )
    t0 = time.perf_counter()
    res = prob.solve()
    qp_ms = (time.perf_counter() - t0) * 1000
    if res.info.status != "solved":
        return np.clip(np.zeros(N), l_min, l_max), qp_ms
    return res.x, qp_ms


# ============================ ③ SpeedBoundsDecider 1：障碍物投到 ST ============================


def st_boundary_mapper(
    scn: Scenario,
    s_arr_path,
    l_path,
    robust_prediction: bool = False,
):
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
            # The ego centre can be anywhere within the longitudinal Minkowski
            # interval while its rectangle overlaps the obstacle.  On a curved
            # lateral-offset path, querying l(s) only at the obstacle centre
            # misses collisions near the front/rear corners.  Use the complete
            # path envelope over that interval.
            if obs.occupancy_t:
                obs_s_lo, obs_s_hi, obs_l_lo, obs_l_hi = obs.occupancy_bounds_at(float(t))
            else:
                obs_s_lo = os_ - obs.L / 2.0
                obs_s_hi = os_ + obs.L / 2.0
                obs_l_lo = ol_ - obs.W / 2.0
                obs_l_hi = ol_ + obs.W / 2.0
            envelope_lo = max(float(s_arr_path[0]), obs_s_lo - e.L / 2.0)
            envelope_hi = min(float(s_arr_path[-1]), obs_s_hi + e.L / 2.0)
            envelope_mask = (s_arr_path >= envelope_lo) & (s_arr_path <= envelope_hi)
            envelope_values = list(np.asarray(l_path)[envelope_mask])
            envelope_values.extend(
                [
                    float(np.interp(envelope_lo, s_arr_path, l_path)),
                    float(np.interp(envelope_hi, s_arr_path, l_path)),
                ]
            )
            ego_l_lo = min(envelope_values) - e.W / 2
            ego_l_hi = max(envelope_values) + e.W / 2
            if robust_prediction and not obs.is_static and not obs.occupancy_t:
                lateral_uncertainty = obs.uncertainty_l0 + obs.uncertainty_vl * float(t)
                longitudinal_uncertainty = (
                    obs.uncertainty_s0 + obs.uncertainty_vs * float(t)
                )
            else:
                lateral_uncertainty = 0.0
                longitudinal_uncertainty = 0.0
            # Shared numerical guard for the 0.1 s speed grid; this is not part
            # of the method-specific prediction tube.
            if not obs.is_static:
                longitudinal_uncertainty += 0.15
            if not obs.occupancy_t:
                obs_l_lo = obs_l_lo - lateral_uncertainty
                obs_l_hi = obs_l_hi + lateral_uncertainty
            if obs_l_lo >= ego_l_hi or obs_l_hi <= ego_l_lo:
                continue  # 横向不重叠（含边界严格分离）
            if obs.occupancy_t:
                s_lo = obs_s_lo - e.L / 2.0
                s_hi = obs_s_hi + e.L / 2.0
            else:
                s_lo = os_ - obs.L / 2 - e.L / 2
                s_hi = os_ + obs.L / 2 + e.L / 2
            s_lo -= longitudinal_uncertainty
            s_hi += longitudinal_uncertainty
            if s_hi < e.s0 - 1e-9:
                continue
            intervals.append((float(t), float(s_lo), float(s_hi)))
        boundaries.append(
            {
                "name": obs.name,
                "intervals": intervals,
                "is_static": obs.is_static,
                "vs": obs.vs,
                "vl": obs.vl,
                "rear_approaching": (
                    not obs.is_static
                    and obs.s0 + obs.L / 2.0 < e.s0 - 0.25
                    and obs.vs > 0.0
                ),
            }
        )
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
        for t, s_lo, s_hi in b["intervals"]:
            ti = int(round(t / dt))
            if 0 <= ti < nt:
                lo = max(0, int(np.floor(s_lo / ds)))
                hi = min(ns - 1, int(np.ceil(s_hi / ds)))
                forbidden[ti, lo : hi + 1] = True

    INF = 1e15
    cost = np.full((nt, ns), INF)
    parent = np.full((nt, ns), -1, dtype=np.int32)
    start_index = int(np.clip(round(e.s0 / ds), 0, ns - 1))
    cost[0, start_index] = 0.0

    v_ref, w_v, w_a = e.v0, 1.0, 0.5
    a_min, a_max, v_max = scn.a_min, scn.a_max, scn.v_max

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
                step = w_v * (v_eff - v_ref) ** 2 + w_a * a_eff**2
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


def build_st_bounds(
    scn: Scenario,
    st_bounds,
    s_dp,
    ts,
    corridor: Optional[List[Tuple[float, float]]] = None,
    safe_window_mode: bool = False,
    tau_fn: Optional[Callable[[float], float]] = None,
    decision_log: Optional[list[dict]] = None,
    preferred_homotopy: Optional[dict[str, str]] = None,
    temporal_plan_rank: int = 0,
    temporal_beam_width: Optional[int] = 8,
):
    """重建 ``s_j^ub / s_j^lb``，并将时序同伦类编码为凸约束。"""
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

    if decision_log is None:
        decision_log = []

    # Build one layered temporal graph for all localized crossing conflicts.
    # Nodes are safe arrival components; graph edges enforce causal travel
    # between stations. This prevents independently plausible local windows
    # from forming a globally inconsistent sequence.
    crossing_metadata: dict[int, dict] = {}
    conflict_points = []
    horizon = TimeWindow(0.0, float(scn.t_max))
    for boundary_index, b in enumerate(st_bounds):
        localized_crossing = (
            not b["is_static"]
            and bool(b["intervals"])
            and abs(float(b.get("vl", 0.0))) >= 0.2
            and abs(float(b.get("vs", 0.0))) <= 1.0
        )
        if not safe_window_mode or not localized_crossing:
            continue

        occupancy_times = sorted(float(item[0]) for item in b["intervals"])
        occupancies = []
        enter = occupancy_times[0]
        previous = enter
        for current in occupancy_times[1:]:
            if current - previous > 0.075:
                occupancies.append(OccupancyInterval(enter, previous))
                enter = current
            previous = current
        occupancies.append(OccupancyInterval(enter, previous))

        conflict_s_lo = min(float(item[1]) for item in b["intervals"])
        conflict_s_hi = max(float(item[2]) for item in b["intervals"])
        distance = max(conflict_s_hi - scn.ego.s0, 0.0)
        earliest = (
            (-scn.ego.v0 + np.sqrt(scn.ego.v0**2 + 2.0 * scn.a_max * distance)) / scn.a_max
            if distance > 0.0
            else 0.0
        )
        temporal_guard = 0.10 + 0.05 * min(abs(float(b.get("vl", 0.0))), 2.0)
        safe = safe_time_windows(occupancies, horizon, safety_guard=temporal_guard)
        nominal = (
            tau_fn(0.5 * (conflict_s_lo + conflict_s_hi))
            if tau_fn is not None
            else arrival_time(0.5 * (conflict_s_lo + conflict_s_hi), scn)
        )
        graph_name = f"{boundary_index}:{b['name']}"
        crossing_metadata[boundary_index] = {
            "graph_name": graph_name,
            "conflict_s_lo": conflict_s_lo,
            "conflict_s_hi": conflict_s_hi,
            "safe": safe,
            "nominal": nominal,
        }
        conflict_points.append(
            ConflictPoint(
                graph_name,
                conflict_s_hi,
                safe,
                nominal,
                min(max(earliest, 0.0), scn.t_max),
            )
        )

    temporal_plans = enumerate_temporal_homotopies(
        conflict_points,
        start_station=scn.ego.s0,
        start_time=0.0,
        max_speed=scn.v_max,
        beam_width=temporal_beam_width,
        preferred_window_labels={
            metadata["graph_name"]: preferred_homotopy[b["name"]]
            for boundary_index, b in enumerate(st_bounds)
            if preferred_homotopy is not None
            and b["name"] in preferred_homotopy
            and (metadata := crossing_metadata.get(boundary_index)) is not None
        },
        persistence_penalty=0.20,
    )
    selected_temporal_plan = (
        temporal_plans[min(temporal_plan_rank, len(temporal_plans) - 1)]
        if temporal_plans
        else None
    )
    selected_temporal_choices = (
        {choice.name: choice for choice in selected_temporal_plan.choices}
        if temporal_plans
        else {}
    )

    # 动态障碍物：基线保持 YIELD；MIKU 从预测占用的补集中选择
    # 先通过/后通过同伦类。tau 只排序候选窗，不定义安全边界。
    for boundary_index, b in enumerate(st_bounds):
        if b["is_static"] or not b["intervals"]:
            continue
        if b.get("rear_approaching"):
            # A vehicle initially behind the ego and moving forward has a
            # pass-before temporal homotopy.  Encoding its rear edge as an
            # upper bound would force an impossible stop when the front edge
            # reaches the ego station; the safe alternative is to require the
            # ego to be ahead of the obstacle's front edge at the conflict
            # knots, with the same continuous certificate applied later.
            for t, _s_lo, s_hi in b["intervals"]:
                ti = int(round(t / dt))
                if 0 <= ti < nt:
                    s_lb[ti] = max(s_lb[ti], min(float(s_hi), scn.s_max))
            decision_log.append(
                {
                    "name": b["name"],
                    "status": "pass_before_rear_approaching",
                    "interval_count": len(b["intervals"]),
                }
            )
            continue
        # A single arrival window is meaningful for a localized crossing region.
        # Longitudinally moving obstacles instead retain pointwise ST following
        # bounds; collapsing their swept tube to one station would over-constrain.
        localized_crossing = abs(float(b.get("vl", 0.0))) >= 0.2 and abs(
            float(b.get("vs", 0.0))
        ) <= 1.0
        if not safe_window_mode or not localized_crossing:
            for t, s_lo, _s_hi in b["intervals"]:
                ti = int(round(t / dt))
                if 0 <= ti < nt:
                    # An occupancy interval can straddle the current ego
                    # station (e.g. a vehicle starting behind the route origin).
                    # Never encode that as an impossible negative station; the
                    # legal response is to stop at the current station and let
                    # the downstream temporal plan decide whether/when to pass.
                    s_ub[ti] = min(s_ub[ti], max(float(s_lo), scn.ego.s0))
            continue

        metadata = crossing_metadata[boundary_index]
        conflict_s_lo = metadata["conflict_s_lo"]
        conflict_s_hi = metadata["conflict_s_hi"]
        choice = selected_temporal_choices.get(metadata["graph_name"])
        if choice is None:
            s_ub[:] = np.minimum(s_ub, conflict_s_lo)
            decision_log.append(
                {
                    "name": b["name"],
                    "status": "stop",
                    "graph_candidate_count": len(temporal_plans),
                }
            )
            continue

        window = choice.window
        longitudinal_guard = 0.05
        has_lower_boundary = window.start > horizon.start + 1e-9
        has_upper_boundary = window.end < horizon.end - 1e-9
        # A safe component [a,b] is compiled at its own boundaries: remain
        # behind the conflict until a, and be beyond it from b onward.  Thus a
        # first component [0,b] is pass-before and a final [a,T] is yield-after.
        if has_lower_boundary:
            s_ub[ts < window.start] = np.minimum(
                s_ub[ts < window.start], conflict_s_lo - longitudinal_guard
            )
        if has_upper_boundary:
            s_lb[ts >= window.end] = np.maximum(
                s_lb[ts >= window.end], conflict_s_hi + longitudinal_guard
            )
        decision_log.append(
            {
                "name": b["name"],
                "status": "selected",
                "window": (window.start, window.end),
                "target_arrival": choice.target_arrival,
                "window_index": choice.window_index,
                "homotopy_label": choice.label,
                "candidate_count": len(metadata["safe"]),
                "graph_candidate_count": len(temporal_plans),
                "homotopy_cost": selected_temporal_plan.cost,
                "temporal_plan_rank": temporal_plan_rank,
            }
        )

    if corridor:
        for s_k, tau_k in corridor:
            for j in range(nt):
                if ts[j] < tau_k:
                    s_ub[j] = min(s_ub[j], s_k)
    return s_ub, s_lb


# ============================ ⑦ PiecewiseJerkSpeedOptimizer (QP) ============================


def speed_qp(scn: Scenario, s_ub, s_lb, ts, goal_index_override: int | None = None):
    e = scn.ego
    K = len(ts)
    dt = ts[1] - ts[0]
    n = 3 * K  # [s, v, a] × K
    v_ref = e.v0
    w_v, w_a, w_jerk, w_terminal = (
        SPEED_W_V,
        SPEED_W_A,
        SPEED_W_JERK,
        SPEED_W_TERMINAL,
    )
    v_max, a_min, a_max = scn.v_max, scn.a_min, scn.a_max

    P = np.zeros((n, n))
    q = np.zeros(n)
    for j in range(K):
        P[3 * j + 1, 3 * j + 1] += 2 * w_v
        P[3 * j + 2, 3 * j + 2] += 2 * w_a
        q[3 * j + 1] += -2 * w_v * v_ref
    for j in range(K - 1):
        c = 2 * w_jerk / dt**2
        P[3 * j + 2, 3 * j + 2] += c
        P[3 * (j + 1) + 2, 3 * (j + 1) + 2] += c
        P[3 * j + 2, 3 * (j + 1) + 2] -= c
        P[3 * (j + 1) + 2, 3 * j + 2] -= c

    # The velocity objective alone may prefer a comfortable but unnecessarily
    # long post-yield recovery.  Apollo's speed optimizer also carries progress
    # guidance from the coarse search.  A terminal reference preserves that
    # role without inheriting the discretisation error of this compact DP grid.
    if scn.goal_s_min is not None and scn.goal_s_max is not None:
        goal_centre = 0.5 * (float(scn.goal_s_min) + float(scn.goal_s_max))
        terminal_target = min(float(s_ub[-1]), max(float(s_lb[-1]), goal_centre))
    else:
        terminal_target = min(float(s_ub[-1]), scn.s_max - 1.0)
    P[3 * (K - 1), 3 * (K - 1)] += 2 * w_terminal
    q[3 * (K - 1)] += -2 * w_terminal * terminal_target

    eq_r, eq_c, eq_v, eq_b = [], [], [], []
    r = 0
    for j in range(K - 1):
        eq_r += [r] * 4
        eq_c += [3 * (j + 1), 3 * j, 3 * j + 1, 3 * j + 2]
        eq_v += [1.0, -1.0, -dt, -0.5 * dt**2]
        eq_b.append(0.0)
        r += 1
        eq_r += [r] * 3
        eq_c += [3 * (j + 1) + 1, 3 * j + 1, 3 * j + 2]
        eq_v += [1.0, -1.0, -dt]
        eq_b.append(0.0)
        r += 1
    for k, val in [(0, e.s0), (1, e.v0), (2, e.a0)]:
        eq_r += [r]
        eq_c += [k]
        eq_v += [1.0]
        eq_b.append(val)
        r += 1

    A_eq = sp.csc_matrix((eq_v, (eq_r, eq_c)), shape=(r, n))
    b_eq = np.array(eq_b)

    lb = np.empty(n)
    ub = np.empty(n)
    for j in range(K):
        lb[3 * j] = s_lb[j]
        ub[3 * j] = s_ub[j]
        lb[3 * j + 1] = 0
        ub[3 * j + 1] = v_max
        lb[3 * j + 2] = a_min
        ub[3 * j + 2] = a_max

    # A locally varying lanelet corridor can legitimately collapse at a
    # knot after ST/goal constraints are intersected.  Reject that candidate
    # before handing malformed bounds to OSQP; callers retain the failure
    # stage instead of converting it into a runner exception.
    if np.any(lb[0::3] > ub[0::3] + 1.0e-8) or np.any(
        lb[3 * np.arange(K) + 1] > ub[3 * np.arange(K) + 1] + 1.0e-8
    ):
        return None, None, None, 0.0

    # CommonRoad goal regions are time-indexed state constraints, not merely
    # a horizon truncation.  Compile the latest admissible goal instant into
    # the same speed-QP boundary used by Apollo's terminal progress target.
    if scn.goal_time_end is not None:
        goal_index = (
            int(goal_index_override)
            if goal_index_override is not None
            else int(np.floor(float(scn.goal_time_end) / dt + 1.0e-9))
        )
        goal_index = min(max(goal_index, 0), K - 1)
        lb[3 * goal_index] = max(lb[3 * goal_index], float(s_lb[goal_index]))
        if scn.goal_v_min is not None:
            lb[3 * goal_index + 1] = max(lb[3 * goal_index + 1], float(scn.goal_v_min))
        if scn.goal_v_max is not None:
            ub[3 * goal_index + 1] = min(ub[3 * goal_index + 1], float(scn.goal_v_max))

    A = sp.vstack([A_eq, sp.eye(n, format="csc")], format="csc")
    constraint_lower = np.concatenate([b_eq, lb])
    constraint_upper = np.concatenate([b_eq, ub])
    if np.any(constraint_lower > constraint_upper + 1.0e-8):
        return None, None, None, 0.0

    prob = osqp.OSQP()
    prob.setup(
        sp.csc_matrix(P),
        q,
        A,
        constraint_lower,
        constraint_upper,
        verbose=False,
        polish=True,
        max_iter=60000,
        eps_abs=1e-5,
        eps_rel=1e-5,
    )
    t0 = time.perf_counter()
    res = prob.solve()
    qp_ms = (time.perf_counter() - t0) * 1000
    if res.info.status != "solved":
        return None, None, None, qp_ms
    x = res.x
    return x[0::3], x[1::3], x[2::3], qp_ms


# ============================ 全链路执行 ============================


def run_pipeline(
    mode_or_flags,
    scn: Scenario,
    tau_fn: Optional[Callable[[float], float]] = None,
    safe_window_mode: bool = False,
    candidate_rank: int = 0,
    split_overrides: Optional[dict[int, int]] = None,
    preferred_homotopy: Optional[dict[str, str]] = None,
    temporal_plan_rank: int = 0,
    spatial_top_k: Optional[int] = 3,
    temporal_beam_width: Optional[int] = 8,
):
    flags = AblationFlags.from_mode(mode_or_flags)
    s_arr, l_min, l_max, blocked_idx, group_decisions = path_bounds_decider(
        scn,
        flags,
        tau_fn=tau_fn,
        candidate_rank=candidate_rank,
        split_overrides=split_overrides,
        spatial_top_k=spatial_top_k,
    )
    # The local Frenet slope approximation is valid for a small heading
    # mismatch.  Large-angle CommonRoad goals require a true curvilinear
    # vehicle maneuver; forcing tan(delta) into a path QP would create an
    # artificial lateral excursion and can violate lanelet boundaries.
    terminal_slope = (
        float(np.tan(scn.goal_heading_error))
        if scn.goal_heading_error is not None
        and abs(float(scn.goal_heading_error)) <= 0.5
        else None
    )
    l_path, path_qp_ms = path_optimizer(
        s_arr,
        l_min,
        l_max,
        terminal_slope=terminal_slope,
    )
    st_bounds = st_boundary_mapper(
        scn,
        s_arr,
        l_path,
        robust_prediction=flags.robust_prediction,
    )
    ts, s_dp, forbidden, ss = speed_dp(scn, st_bounds)

    corridor = None
    # C5 is the temporal-homotopy coordination layer. ``safe_window_mode`` is
    # retained as a diagnostic override; full MIKU enables the same semantics
    # through its component flag.
    use_temporal_homotopy = flags.corridor_inject or safe_window_mode

    time_window_decisions: list[dict] = []
    s_ub, s_lb = build_st_bounds(
        scn,
        st_bounds,
        s_dp,
        ts,
        safe_window_mode=use_temporal_homotopy,
        tau_fn=tau_fn,
        decision_log=time_window_decisions,
        preferred_homotopy=preferred_homotopy,
        temporal_plan_rank=temporal_plan_rank,
        temporal_beam_width=temporal_beam_width,
    )

    # 公平比较的统一终点：让轨迹在 s_target 处自然收敛并停车，
    # 避免全程匀速穿透终点后再用 t_max 尾段掩盖减速行为。
    external_goal_interval = (
        scn.goal_s_min is not None
        and scn.goal_s_max is not None
        and scn.goal_l_min is not None
        and scn.goal_l_max is not None
    )
    s_target = max(
        scn.s_max
        if external_goal_interval
        else (scn.s_max if scn.goal_lateral is not None else scn.s_max - 1.0),
        scn.ego.s0,
    )
    safe_corridor_terminal_upper = float(s_ub[-1])
    s_ub = np.minimum(s_ub, s_target)

    # Apollo TrimPathBounds：blocked 时强制 ego 在阻塞 s 之前停下
    blocked_s = None
    if blocked_idx >= 0:
        blocked_s = max(s_arr[blocked_idx] - scn.ego.L / 2, 0.0)
        s_ub = np.minimum(s_ub, blocked_s)

    goal_lower = (
        max(float(scn.goal_s_min), scn.ego.s0)
        if external_goal_interval
        else s_target
    )
    terminal_goal_infeasible = bool(
        scn.goal_time_end is not None
        and safe_corridor_terminal_upper < goal_lower - 1.0e-6
    )

    # Encode the planning goal as a terminal boundary condition whenever the
    # constructed corridor reaches it. This avoids reporting a false failure
    # merely because a soft objective converges a few centimetres short.
    terminal_lower_before_goal = float(s_lb[-1])
    selected_goal_index: int | None = None
    if scn.goal_time_end is not None and external_goal_interval:
        # CommonRoad accepts the first state entering the goal region at any
        # admissible time.  Enumerate the finite time knots instead of
        # over-constraining the final horizon knot to the latest instant.
        dt = float(ts[1] - ts[0]) if len(ts) > 1 else 0.1
        first_goal_index = max(
            0, int(np.ceil(float(scn.goal_time_start or 0.0) / dt - 1.0e-9))
        )
        last_goal_index = min(
            len(ts) - 1,
            int(np.floor(float(scn.goal_time_end) / dt + 1.0e-9)),
        )
        candidates = []
        for goal_index in range(first_goal_index, last_goal_index + 1):
            candidate_lb = np.array(s_lb, dtype=float, copy=True)
            candidate_ub = np.array(s_ub, dtype=float, copy=True)
            candidate_lb[goal_index] = max(
                candidate_lb[goal_index], float(scn.goal_s_min)
            )
            candidate_ub[goal_index] = min(
                candidate_ub[goal_index], float(scn.goal_s_max)
            )
            if candidate_lb[goal_index] > candidate_ub[goal_index] + 1.0e-7:
                continue
            candidate = speed_qp(
                scn,
                candidate_ub,
                candidate_lb,
                ts,
                goal_index_override=goal_index,
            )
            candidates.append((goal_index, candidate_lb, candidate_ub, candidate))
            if candidate[0] is not None:
                selected_goal_index, s_lb, s_ub, solved = candidates[-1]
                s_qp, v_qp, a_qp, speed_qp_ms = solved
                terminal_goal_infeasible = False
                break
        if selected_goal_index is None:
            s_qp = v_qp = a_qp = None
            speed_qp_ms = sum(float(item[3][3]) for item in candidates)
            terminal_goal_infeasible = True
    elif scn.goal_time_end is not None:
        # External goal states are hard terminal progress constraints.  Do not
        # replace an unreachable goal by the last safe partial station; that
        # would produce a collision-free but evaluator-invalid trajectory and
        # hide the actual wait/pass infeasibility from the benchmark.
        s_lb[-1] = goal_lower
        s_qp, v_qp, a_qp, speed_qp_ms = speed_qp(scn, s_ub, s_lb, ts)
    else:
        s_lb[-1] = min(s_target, s_ub[-1])
        s_qp, v_qp, a_qp, speed_qp_ms = speed_qp(scn, s_ub, s_lb, ts)
    terminal_goal_relaxed = False
    if (
        s_qp is None
        and s_lb[-1] > terminal_lower_before_goal + 1e-9
        and scn.goal_time_end is None
    ):
        # A hard goal must never turn a safe partial plan into solver failure.
        # Retry with the original corridor bound and expose the relaxation in
        # the result so experiments can count it explicitly.
        s_lb[-1] = terminal_lower_before_goal
        s_qp, v_qp, a_qp, retry_ms = speed_qp(scn, s_ub, s_lb, ts)
        speed_qp_ms += retry_ms
        terminal_goal_relaxed = True

    # A temporal homotopy graph may contain several legal wait/pass plans.
    # If the selected rank cannot reach the goal under its certified corridor,
    # try the next finite candidate before declaring planner failure.  This is
    # a bounded algorithmic fallback, not a relaxed collision check.
    if (
        use_temporal_homotopy
        and (s_qp is None or terminal_goal_infeasible)
        and temporal_plan_rank < max(0, (temporal_beam_width or 1) - 1)
    ):
        alternate = run_pipeline(
            mode_or_flags,
            scn,
            tau_fn=tau_fn,
            safe_window_mode=safe_window_mode,
            candidate_rank=candidate_rank,
            split_overrides=split_overrides,
            preferred_homotopy=preferred_homotopy,
            temporal_plan_rank=temporal_plan_rank + 1,
            spatial_top_k=spatial_top_k,
            temporal_beam_width=temporal_beam_width,
        )
        if alternate.get("s_qp") is not None and not alternate.get(
            "terminal_goal_infeasible", False
        ):
            alternate["temporal_plan_fallback_from_rank"] = temporal_plan_rank
            return alternate

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
        a_y = v_qp**2 * kappa_t
    else:
        a_y = None

    return dict(
        s_arr=s_arr,
        l_min=l_min,
        l_max=l_max,
        l_path=l_path,
        kappa_s=kappa_s,
        blocked_idx=blocked_idx,
        blocked_s=blocked_s,
        group_decisions=group_decisions,
        st_bounds=st_bounds,
        ts=ts,
        s_dp=s_dp,
        forbidden=forbidden,
        ss=ss,
        s_ub=s_ub,
        s_lb=s_lb,
        s_qp=s_qp,
        v_qp=v_qp,
        a_qp=a_qp,
        a_y=a_y,
        corridor=corridor,
        time_window_decisions=time_window_decisions,
        terminal_goal_relaxed=terminal_goal_relaxed,
        terminal_goal_infeasible=terminal_goal_infeasible,
        selected_goal_index=selected_goal_index,
        selected_goal_time=(
            float(ts[selected_goal_index])
            if selected_goal_index is not None
            else None
        ),
        safe_corridor_terminal_upper=safe_corridor_terminal_upper,
        terminal_slope_target=terminal_slope,
        candidate_rank=candidate_rank,
        split_overrides=split_overrides,
        temporal_plan_rank=temporal_plan_rank,
        spatial_homotopy_candidate_count=max(
            (
                int(decision.get("spatial_homotopy_candidate_count", 0))
                for decision in group_decisions
            ),
            default=0,
        ),
        temporal_homotopy_candidate_count=max(
            (
                int(decision.get("graph_candidate_count", 0))
                for decision in time_window_decisions
            ),
            default=0,
        ),
        qp_solve_ms={
            "path": path_qp_ms,
            "speed": speed_qp_ms,
            "total": path_qp_ms + speed_qp_ms,
        },
        execution_interpolation_contract="constant_acceleration_longitudinal",
    )


def path_qp_objective(result: dict) -> float:
    """Return the objective represented by :func:`path_optimizer`."""
    l_path = np.asarray(result["l_path"], dtype=float)
    s_arr = np.asarray(result["s_arr"], dtype=float)
    if l_path.ndim != 1 or len(l_path) != len(s_arr) or len(s_arr) < 2:
        raise ValueError("candidate path samples do not match station grid")
    ds = float(s_arr[1] - s_arr[0])
    if ds <= 0.0:
        raise ValueError("candidate station grid must be strictly increasing")
    path_cost = PATH_W_L * float(np.sum(l_path**2))
    path_cost += PATH_W_DL * float(np.sum((np.diff(l_path) / ds) ** 2))
    if len(l_path) > 2:
        path_cost += PATH_W_DDL * float(
            np.sum((np.diff(l_path, n=2) / ds**2) ** 2)
        )
    return float(path_cost)


def speed_qp_objective(scn: Scenario, result: dict) -> float:
    """Return the objective represented by :func:`speed_qp`."""
    s_qp = np.asarray(result["s_qp"], dtype=float)
    v_qp = np.asarray(result["v_qp"], dtype=float)
    a_qp = np.asarray(result["a_qp"], dtype=float)
    ts = np.asarray(result["ts"], dtype=float)
    if len(ts) < 1 or len(s_qp) != len(ts) or len(v_qp) != len(ts):
        raise ValueError("candidate speed samples do not match time grid")
    dt = float(ts[1] - ts[0]) if len(ts) > 1 else 1.0
    if dt <= 0.0:
        raise ValueError("candidate time grid must be strictly increasing")
    speed_cost = SPEED_W_V * float(np.sum((v_qp - scn.ego.v0) ** 2))
    speed_cost += SPEED_W_A * float(np.sum(a_qp**2))
    if len(a_qp) > 1:
        speed_cost += SPEED_W_JERK * float(np.sum((np.diff(a_qp) / dt) ** 2))
    s_ub = np.asarray(result["s_ub"], dtype=float)
    terminal_target = min(float(s_ub[-1]), scn.s_max - 1.0)
    speed_cost += SPEED_W_TERMINAL * float((s_qp[-1] - terminal_target) ** 2)
    return float(speed_cost)


def pipeline_objective(scn: Scenario, result: dict) -> float:
    """Return the scalar objective represented by the two QP builders.

    This is the objective used by the finite-label certificate.  It mirrors
    the quadratic terms assembled in :func:`path_optimizer` and
    :func:`speed_qp`, including the terminal reference selected for the
    candidate's longitudinal upper bound.
    """
    return path_qp_objective(result) + speed_qp_objective(scn, result)


def validate_pipeline_candidate_continuous_safety(
    scn: Scenario,
    result: dict,
    *,
    robust_prediction: bool = True,
) -> dict[str, ContinuousSafetyCertificate]:
    """Certify a pipeline candidate between its trajectory samples.

    This is a callable fixed-homotopy validation interface, separate from the
    experiment metric sampler.  It uses horizon-wide uncertainty extents and
    conservative relative-speed bounds.  A failed certificate is inconclusive
    and the caller must refine or reject the candidate; only ``certified=True``
    is a continuous-time safety result under the declared motion bounds and a
    constant-acceleration longitudinal execution contract used by the speed-QP
    rollout.  Each interval is split where it crosses a path station knot, so
    both longitudinal motion and the piecewise-linear path composition
    ``l_path(s(t))`` are quadratic on every checked subinterval.
    """

    if result.get("s_qp") is None:
        raise ValueError("continuous safety requires a solved speed candidate")
    interpolation_contract = result.get("execution_interpolation_contract")
    if interpolation_contract not in (
        None,
        "piecewise_linear_centers",
        "constant_acceleration_longitudinal",
    ):
        raise ValueError("unsupported execution interpolation contract")
    ts = np.asarray(result["ts"], dtype=float)
    longitudinal = np.asarray(result["s_qp"], dtype=float)
    if result.get("l_qp") is not None:
        lateral = np.asarray(result["l_qp"], dtype=float)
    else:
        lateral = np.interp(longitudinal, result["s_arr"], result["l_path"])
    if len(ts) != len(longitudinal) or len(ts) != len(lateral):
        raise ValueError("candidate time, longitudinal, and lateral arrays must align")

    path_stations = np.asarray(result["s_arr"], dtype=float)
    path_lateral = np.asarray(result["l_path"], dtype=float)
    station_steps = np.diff(path_stations)
    candidate_speed = result.get("v_qp")
    candidate_acceleration = result.get("a_qp")
    maximum_speed = (
        float(np.max(np.abs(candidate_speed)))
        if candidate_speed is not None
        else scn.v_max
    )
    if np.any(station_steps <= 0.0):
        path_lateral_speed_bound = 0.0
    else:
        maximum_path_slope = float(
            np.max(np.abs(np.diff(path_lateral) / station_steps))
        )
        path_lateral_speed_bound = maximum_path_slope * maximum_speed

    maximum_time = float(ts[-1])
    certificates = {}
    for obstacle_index, obstacle in enumerate(scn.obstacles):
        uncertainty_values = (
            obstacle.uncertainty_s0,
            obstacle.uncertainty_l0,
            obstacle.uncertainty_vs,
            obstacle.uncertainty_vl,
        )
        if not all(
            math.isfinite(float(value)) and float(value) >= 0.0
            for value in uncertainty_values
        ):
            raise ValueError(
                "obstacle prediction uncertainty radii must be finite and non-negative"
            )
        if robust_prediction and not obstacle.is_static:
            longitudinal_uncertainty = (
                obstacle.uncertainty_s0 + obstacle.uncertainty_vs * maximum_time
            )
            lateral_uncertainty = (
                obstacle.uncertainty_l0 + obstacle.uncertainty_vl * maximum_time
            )
        else:
            longitudinal_uncertainty = 0.0
            lateral_uncertainty = 0.0
        # Match the dynamic numerical guard used by the ST mapper.
        longitudinal_numerical_guard = 0.15 if not obstacle.is_static else 0.0
        name = obstacle.name or f"obstacle-{obstacle_index}"
        half_length = (
            (scn.ego.L + obstacle.L) / 2.0
            + longitudinal_uncertainty
            + longitudinal_numerical_guard
        )
        half_width = (scn.ego.W + obstacle.W) / 2.0 + lateral_uncertainty
        if interpolation_contract == "constant_acceleration_longitudinal":
            if candidate_speed is None or candidate_acceleration is None:
                raise ValueError("constant-acceleration contract requires speed and acceleration")
            samples = path_rollout_motion_samples(
                ts,
                longitudinal,
                np.asarray(candidate_speed, dtype=float),
                np.asarray(candidate_acceleration, dtype=float),
                path_stations,
                path_lateral,
                obstacle,
                combined_half_length=half_length,
                combined_half_width=half_width,
            )
            if obstacle.occupancy_t:
                # Replace the fixed body rectangle with the official
                # occupancy envelope at each rollout knot.  The validator is
                # still axis-aligned in Frenet coordinates, but now covers
                # the published shape/orientation trajectory conservatively.
                adjusted = []
                for sample in samples:
                    s_lo, s_hi, l_lo, l_hi = obstacle.occupancy_bounds_at(sample.time)
                    center_s = (s_lo + s_hi) / 2.0
                    center_l = (l_lo + l_hi) / 2.0
                    adjusted.append(
                        AxisAlignedMotionSample(
                            sample.time,
                            sample.relative_longitudinal + obstacle.position_at(sample.time)[0] - center_s,
                            sample.relative_lateral + obstacle.position_at(sample.time)[1] - center_l,
                            (s_hi - s_lo) / 2.0 + scn.ego.L / 2.0,
                            (l_hi - l_lo) / 2.0 + scn.ego.W / 2.0,
                        )
                    )
                samples = adjusted
                # A CommonRoad occupancy prediction is valid only on its
                # published time interval.  ``occupancy_bounds_at`` clamps
                # outside that interval for interpolation convenience, but
                # treating the last rectangle as a persistent obstacle would
                # create a false collision after the source trajectory ends.
                occupancy_start = float(obstacle.occupancy_t[0])
                occupancy_end = float(obstacle.occupancy_t[-1])
                samples = [
                    sample
                    for sample in samples
                    if occupancy_start - 1.0e-9 <= sample.time <= occupancy_end + 1.0e-9
                ]
                # The occupancy envelope is piecewise-linear in time and its
                # knots need not coincide with the ego QP knots.  Use the
                # Lipschitz certificate for this external-interface branch;
                # forcing the envelope into the ego-only constant-acceleration
                # contract would reject otherwise well-formed candidates due
                # to a missing/incorrect relative-kinematics annotation.
                validator = validate_candidate_continuous_safety
                occupancy_centers = np.column_stack(
                    (
                        (np.asarray(obstacle.occupancy_s_min) + np.asarray(obstacle.occupancy_s_max)) / 2.0,
                        (np.asarray(obstacle.occupancy_l_min) + np.asarray(obstacle.occupancy_l_max)) / 2.0,
                    )
                )
                occupancy_dt = np.diff(np.asarray(obstacle.occupancy_t, dtype=float))
                occupancy_speed_s = float(
                    np.max(np.abs(np.diff(occupancy_centers[:, 0]) / occupancy_dt))
                )
                occupancy_speed_l = float(
                    np.max(np.abs(np.diff(occupancy_centers[:, 1]) / occupancy_dt))
                )
            else:
                occupancy_speed_s = abs(float(obstacle.vs))
                occupancy_speed_l = abs(float(obstacle.vl))
                validator = validate_candidate_constant_acceleration_safety
        else:
            samples = []
            for index, time_value in enumerate(ts):
                if obstacle.occupancy_t:
                    s_lo, s_hi, l_lo, l_hi = obstacle.occupancy_bounds_at(float(time_value))
                    obstacle_s = (s_lo + s_hi) / 2.0
                    obstacle_l = (l_lo + l_hi) / 2.0
                    sample_half_length = (s_hi - s_lo) / 2.0 + scn.ego.L / 2.0
                    sample_half_width = (l_hi - l_lo) / 2.0 + scn.ego.W / 2.0
                else:
                    obstacle_s, obstacle_l = obstacle.position_at(float(time_value))
                    sample_half_length = half_length
                    sample_half_width = half_width
                samples.append(
                    AxisAlignedMotionSample(
                        float(time_value),
                        float(longitudinal[index] - obstacle_s),
                        float(lateral[index] - obstacle_l),
                        sample_half_length,
                        sample_half_width,
                    )
                )
            if obstacle.occupancy_t:
                occupancy_start = float(obstacle.occupancy_t[0])
                occupancy_end = float(obstacle.occupancy_t[-1])
                samples = [
                    sample
                    for sample in samples
                    if occupancy_start - 1.0e-9 <= sample.time <= occupancy_end + 1.0e-9
                ]
            validator = validate_candidate_continuous_safety
            occupancy_speed_s = abs(float(obstacle.vs))
            occupancy_speed_l = abs(float(obstacle.vl))
        certificates[name] = validator(
            samples,
            relative_longitudinal_speed_bound=maximum_speed + occupancy_speed_s,
            relative_lateral_speed_bound=path_lateral_speed_bound + occupancy_speed_l,
        )
    return certificates


def path_rollout_motion_samples(
    times: np.ndarray,
    stations: np.ndarray,
    speeds: np.ndarray,
    accelerations: np.ndarray,
    path_stations: np.ndarray,
    path_lateral: np.ndarray,
    obstacle: Obstacle,
    *,
    combined_half_length: float,
    combined_half_width: float,
) -> list[AxisAlignedMotionSample]:
    """Split a QP rollout wherever ``l_path(s(t))`` changes linear segment."""
    arrays = (times, stations, speeds, accelerations)
    if len({len(array) for array in arrays}) != 1 or len(times) < 2:
        raise ValueError("QP rollout arrays must align and contain two knots")
    if len(path_stations) != len(path_lateral) or len(path_stations) < 2:
        raise ValueError("path arrays must align and contain two stations")
    if not all(np.all(np.isfinite(array)) for array in (*arrays, path_stations, path_lateral)):
        raise ValueError("QP rollout and path arrays must be finite")
    if np.any(np.diff(path_stations) <= 0.0):
        raise ValueError("path stations must be strictly increasing")

    samples: list[AxisAlignedMotionSample] = []
    for index in range(len(times) - 1):
        dt = float(times[index + 1] - times[index])
        if dt <= 0.0:
            raise ValueError("QP knot times must be strictly increasing")
        s0 = float(stations[index])
        v0 = float(speeds[index])
        a0 = float(accelerations[index])
        crossing_times = [0.0, dt]
        predicted_s1 = s0 + v0 * dt + 0.5 * a0 * dt * dt
        traversed_stations = [s0, predicted_s1]
        if abs(a0) > 1.0e-14:
            turning_time = -v0 / a0
            if 0.0 < turning_time < dt:
                traversed_stations.append(
                    s0 + v0 * turning_time + 0.5 * a0 * turning_time * turning_time
                )
        low, high = min(traversed_stations), max(traversed_stations)
        for path_station in path_stations:
            target = float(path_station)
            if not low + 1.0e-10 < target < high - 1.0e-10:
                continue
            if abs(a0) <= 1.0e-14:
                roots = () if abs(v0) <= 1.0e-14 else ((target - s0) / v0,)
            else:
                discriminant = v0 * v0 - 2.0 * a0 * (s0 - target)
                if discriminant < 0.0:
                    roots = ()
                else:
                    root = math.sqrt(max(0.0, discriminant))
                    roots = ((-v0 - root) / a0, (-v0 + root) / a0)
            crossing_times.extend(root for root in roots if 1.0e-10 < root < dt - 1.0e-10)
        crossing_times = sorted(set(crossing_times))

        for sub_index, elapsed in enumerate(crossing_times[:-1]):
            next_elapsed = crossing_times[sub_index + 1]
            midpoint = 0.5 * (elapsed + next_elapsed)
            midpoint_station = s0 + v0 * midpoint + 0.5 * a0 * midpoint * midpoint
            if midpoint_station <= path_stations[0] or midpoint_station >= path_stations[-1]:
                slope = 0.0
            else:
                path_index = int(
                    np.searchsorted(path_stations, midpoint_station, side="right") - 1
                )
                path_index = int(np.clip(path_index, 0, len(path_stations) - 2))
                ds = float(path_stations[path_index + 1] - path_stations[path_index])
                slope = 0.0 if ds <= 0.0 else float(
                    (path_lateral[path_index + 1] - path_lateral[path_index]) / ds
                )
            station = s0 + v0 * elapsed + 0.5 * a0 * elapsed * elapsed
            speed = v0 + a0 * elapsed
            absolute_time = float(times[index] + elapsed)
            obstacle_s, obstacle_l = obstacle.position_at(absolute_time)
            sample = AxisAlignedMotionSample(
                absolute_time,
                station - obstacle_s,
                float(np.interp(station, path_stations, path_lateral)) - obstacle_l,
                combined_half_length,
                combined_half_width,
                speed - obstacle.vs,
                a0,
                slope * speed - obstacle.vl,
                slope * a0,
            )
            if samples and math.isclose(samples[-1].time, absolute_time, abs_tol=1.0e-12):
                samples[-1] = sample
            else:
                samples.append(sample)

    final_time = float(times[-1])
    final_obstacle_s, final_obstacle_l = obstacle.position_at(final_time)
    samples.append(
        AxisAlignedMotionSample(
            final_time,
            float(stations[-1] - final_obstacle_s),
            float(np.interp(stations[-1], path_stations, path_lateral) - final_obstacle_l),
            combined_half_length,
            combined_half_width,
        )
    )
    return samples


# ============================ 绘图 ============================

C_PED = "#d62728"
C_STAT = "#7f7f7f"
C_PATH = "#2ca02c"
C_BAS = "#1f77b4"
C_MIKU = "#2ca02c"
C_BOUND = "#ff7f0e"
C_DP = "#9467bd"
C_QP = "#000000"
C_CORR = "#e377c2"


def _draw_vehicle(
    ax,
    x,
    y,
    length,
    width,
    heading_dir=1.0,
    facecolor="gray",
    alpha=0.85,
    edgecolor="black",
    name=None,
    name_color="white",
    zorder=3,
):
    """车辆/自行车：长方形 + 朝向三角（车头）。heading_dir: +1 沿+s 行驶，-1 沿-s。"""
    ax.add_patch(
        Rectangle(
            (x - length / 2, y - width / 2),
            length,
            width,
            facecolor=facecolor,
            alpha=alpha,
            edgecolor=edgecolor,
            lw=0.6,
            zorder=zorder,
        )
    )
    # 车头三角（方向指示）
    front_x = x + heading_dir * length / 2
    base_x = x + heading_dir * (length / 2 - min(length * 0.25, 0.6))
    tri = Polygon(
        [(front_x, y), (base_x, y + width * 0.45), (base_x, y - width * 0.45)],
        facecolor="white",
        edgecolor=edgecolor,
        lw=0.6,
        alpha=min(1.0, alpha + 0.1),
        zorder=zorder + 0.1,
    )
    ax.add_patch(tri)
    if name:
        ax.text(
            x - heading_dir * length * 0.15,
            y,
            name,
            ha="center",
            va="center",
            fontsize=7.5,
            color=name_color,
            fontweight="bold",
            zorder=zorder + 0.2,
        )


def _draw_pedestrian(ax, x, y, color=C_PED, alpha=0.85, radius=0.3, zorder=3):
    """行人/VRU：圆形（顶视近圆柱）。"""
    ax.add_patch(
        Circle(
            (x, y),
            radius,
            facecolor=color,
            alpha=alpha,
            edgecolor=color,
            lw=0.4,
            zorder=zorder,
        )
    )


def _draw_obstacle(ax, obs: Obstacle, t: float, alpha: float = 0.85):
    os_, ol_ = obs.position_at(t)
    if obs.obs_type in ("ped",):
        _draw_pedestrian(
            ax, os_, ol_, color=C_PED, alpha=alpha, radius=max(obs.W, obs.L) / 2
        )
    elif obs.obs_type in ("bike", "vehicle"):
        # 车头朝向：vs>0 → +s；vs<0 → -s；vs=0 → +s（默认沿路停）
        heading = 1.0 if obs.vs >= 0 else -1.0
        col = "#7fb069" if obs.obs_type == "bike" else "#5b8def"
        _draw_vehicle(
            ax,
            os_,
            ol_,
            obs.L,
            obs.W,
            heading_dir=heading,
            facecolor=col,
            alpha=alpha,
            name=obs.name,
            name_color="white",
        )
    else:  # static (parked, truck, cone)
        _draw_vehicle(
            ax,
            os_,
            ol_,
            obs.L,
            obs.W,
            heading_dir=1.0,
            facecolor=C_STAT,
            alpha=alpha,
            name=obs.name,
            name_color="white",
        )


def plot_sl(ax, r, title, scn: Scenario):
    ax.set_title(title, fontsize=11, fontweight="bold")
    # 主车道
    ax.fill_between(
        r["s_arr"], scn.l_road_min, scn.l_road_max, color="#f0f0f0", zorder=0
    )
    # 车道中心虚线
    ax.axhline(0, color="#aaa", ls=(0, (8, 8)), lw=0.8, zorder=0)
    # LaneBorrow：邻车道用淡蓝色区分
    if scn.lane_borrow in ("left", "both"):
        ax.fill_between(
            r["s_arr"],
            scn.l_road_max,
            scn.l_road_max + scn.lane_width,
            color="#dde7f5",
            zorder=0,
            label="借用左车道",
        )
        ax.axhline(scn.l_road_max, color="#888", ls="--", lw=0.5, zorder=0)
    if scn.lane_borrow in ("right", "both"):
        ax.fill_between(
            r["s_arr"],
            scn.l_road_min - scn.lane_width,
            scn.l_road_min,
            color="#dde7f5",
            zorder=0,
            label="借用右车道",
        )
        ax.axhline(scn.l_road_min, color="#888", ls="--", lw=0.5, zorder=0)
    ax.fill_between(
        r["s_arr"],
        r["l_min"],
        r["l_max"],
        color="#fff3cc",
        alpha=0.6,
        label="可行 l 区间",
        zorder=1,
    )
    ax.plot(r["s_arr"], r["l_min"], color=C_BOUND, lw=0.8, ls="--", zorder=2)
    ax.plot(r["s_arr"], r["l_max"], color=C_BOUND, lw=0.8, ls="--", zorder=2)
    ax.plot(r["s_arr"], r["l_path"], color=C_PATH, lw=2.6, label="Path l(s)", zorder=4)

    for obs in scn.obstacles:
        if obs.is_static:
            _draw_obstacle(ax, obs, 0, alpha=0.85)
        else:
            t_show_max = min(scn.t_max, 2.0)
            for t_show, alpha in [
                (0.0, 0.9),
                (t_show_max * 0.33, 0.55),
                (t_show_max * 0.66, 0.35),
                (t_show_max, 0.2),
            ]:
                _draw_obstacle(ax, obs, t_show, alpha=alpha)
            os0, ol0 = obs.position_at(0)
            os1, ol1 = obs.position_at(t_show_max)
            ax.annotate(
                "",
                xy=(os1, ol1),
                xytext=(os0, ol0),
                arrowprops=dict(arrowstyle="->", color=C_PED, lw=1.2, alpha=0.8),
            )
            ax.text(
                os0,
                ol0 + max(obs.W, 0.4) + 0.5,
                f"{obs.name} v=({obs.vs:+.1f},{obs.vl:+.1f})",
                fontsize=7.5,
                color=C_PED,
                ha="center",
            )

    # ego 也用车辆样式
    _draw_vehicle(
        ax,
        scn.ego.s0,
        scn.ego.l0,
        scn.ego.L,
        scn.ego.W,
        heading_dir=1.0,
        facecolor=C_BAS,
        alpha=0.55,
        edgecolor=C_BAS,
        name="EGO",
        name_color="white",
        zorder=4,
    )

    # blocked 标记
    if r.get("blocked_s") is not None:
        bs = r["blocked_s"]
        ax.axvline(
            bs,
            color="red",
            lw=1.6,
            ls="--",
            zorder=6,
            label=f"Trim @ s={bs:.1f}（path blocked）",
        )
        ax.plot(
            bs,
            0,
            marker="X",
            color="red",
            markersize=14,
            mec="white",
            mew=1.5,
            zorder=7,
        )

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
        ax.fill_between(
            ts_p, s_lo_p, s_hi_p, color=col, alpha=0.35, label=f"{b['name']} ST 边界"
        )

    if r["corridor"]:
        # —— 走廊左下沿：连续 τ(s) 斜线 ——
        # 论文 Ω = {(s, t) | t ≥ τ(s) ∧ g_{p*}(s) ≥ W_ego}
        # τ(s) 是 ego 从 s_ego0 出发的到达时间函数，匀速时斜率 = v_ego，加速时为单调凹曲线
        s_grid = np.linspace(scn.ego.s0, scn.s_max, 200)
        tau_grid = np.array([arrival_time(float(s), scn) for s in s_grid])
        mask = (tau_grid >= 0) & (tau_grid <= scn.t_max)
        if mask.any():
            ax.plot(
                tau_grid[mask],
                s_grid[mask],
                color=C_CORR,
                lw=2.2,
                ls="-",
                label=r"$t{=}\tau(s)$ 走廊左下沿",
            )
            # ego 不可达区（t < τ(s)）淡填色
            ax.fill_betweenx(s_grid[mask], 0, tau_grid[mask], color=C_CORR, alpha=0.08)
            # 斜率注解（在曲线中段）
            mid_idx = mask.sum() // 2
            mid_t = tau_grid[mask][mid_idx]
            mid_s = s_grid[mask][mid_idx]
            slope_lbl = (
                f"斜率$\\,{{=}}\\,v_{{ego}}{{=}}{scn.ego.v0:.0f}$ m/s"
                if abs(scn.ego.a0) < 1e-3
                else f"$v_0{{=}}{scn.ego.v0:.0f}$, $a_0{{=}}{scn.ego.a0:.1f}$"
            )
            ax.annotate(
                slope_lbl,
                (mid_t, mid_s),
                xytext=(mid_t + 0.4, mid_s - 1.2),
                fontsize=7.5,
                color=C_CORR,
                arrowprops=dict(arrowstyle="-", color=C_CORR, lw=0.5, alpha=0.6),
            )

        # —— 离散采样点 (s_k, τ_k) 及对应的 s_j^ub 收紧效果矩形 ——
        for s_k, tau_k in r["corridor"]:
            ax.fill_betweenx(
                [s_k, scn.s_max],
                0,
                tau_k,
                color=C_CORR,
                alpha=0.16,
                hatch="///",
                edgecolor=C_CORR,
                linewidth=0.8,
                label=f"$\\mathcal{{T}}$ 收紧 ($s{{>}}{s_k:.1f}$, $t{{<}}{tau_k:.2f}$)",
            )
            ax.plot(tau_k, s_k, "P", color=C_CORR, markersize=11, mec="black", mew=0.5)
            ax.annotate(
                f"$(\\tau_k{{=}}{tau_k:.2f}, s_k{{=}}{s_k:.1f})$",
                (tau_k, s_k),
                xytext=(tau_k + 0.15, s_k - 2.0),
                fontsize=8,
                color=C_CORR,
                arrowprops=dict(arrowstyle="->", color=C_CORR, lw=0.6),
            )

    ax.plot(
        r["ts"], r["s_ub"], color="red", lw=0.9, alpha=0.7, label="$s_j^{ub}$ (融合后)"
    )
    ax.plot(
        r["ts"], r["s_dp"], color=C_DP, lw=1.4, ls="--", label="DP 粗解 $s_{dp}(t)$"
    )
    if r["s_qp"] is not None:
        ax.plot(r["ts"], r["s_qp"], color=C_QP, lw=2.6, label="QP 精解 $s^*(t)$")
    ax.set_xlabel("t [s]")
    ax.set_ylabel("s [m]")
    ax.set_xlim(0, scn.t_max)
    ax.set_ylim(0, scn.s_max)
    ax.legend(loc="lower right", fontsize=7.2)
    ax.grid(alpha=0.3)


def compute_metrics(r, scn: Scenario):
    """轨迹质量指标：通行效率、平顺性、鲁棒性、计算开销，覆盖消融评分四个维度。"""
    qp_solve_ms = r.get("qp_solve_ms", {"path": 0.0, "speed": 0.0, "total": 0.0})
    s_target = max(scn.s_max - 1.0, scn.ego.s0)
    eps = 1e-3

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
    kappa_rms = (
        float(np.sqrt(np.mean(kappa_s**2)))
        if kappa_s is not None and len(kappa_s) > 0
        else 0.0
    )

    blocked_flag = int(r.get("blocked_idx", -1) >= 0)

    if r["v_qp"] is None:
        return {
            "qp_solve_ms": qp_solve_ms,
            "_infeasible": True,
            "success": 0,
            "blocked": blocked_flag,
            "l_max_dev": l_max_dev,
            "kappa_rms": kappa_rms,
            "decision_switches": decision_switches,
            "tau_violation": 0,
        }

    ts, v, a, s = r["ts"], r["v_qp"], r["a_qp"], r["s_qp"]
    dt = ts[1] - ts[0]
    # 巡航段平均速度：只算 ego 在主动行驶时（排除末端到达后停留）
    arrive_idx = (
        int(np.argmax(s >= s_target - eps)) if (s >= s_target - eps).any() else -1
    )
    if arrive_idx > 0:
        v_active = v[: arrive_idx + 1]
        a_active = a[: arrive_idx + 1]
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
    jerk_rms = float(np.sqrt(np.mean(jerk**2))) if len(jerk) > 0 else 0.0
    s_end = float(s[-1])
    efficiency = avg_v_cruise / scn.ego.v0
    success = 1 if (s_end >= s_target - eps and not np.isnan(t_arrive)) else 0
    # 横向（向心）加速度极值
    a_y_arr = r.get("a_y")
    if a_y_arr is not None and len(a_y_arr) > 0:
        if arrive_idx > 0:
            a_y_active = a_y_arr[: arrive_idx + 1]
        else:
            mask = v > 0.3
            a_y_active = a_y_arr[mask] if mask.any() else a_y_arr
        max_abs_a_lat = float(np.max(np.abs(a_y_active)))
    else:
        max_abs_a_lat = 0.0

    # τ(s) 走廊违反次数：t<τ_k 时 ego 已越过 s_k 即违反
    tau_violation = 0
    corridor = r.get("corridor") or []
    for s_k, tau_k in corridor:
        for j, t_j in enumerate(ts):
            if t_j < tau_k and s[j] >= s_k:
                tau_violation += 1
    return dict(
        avg_v=avg_v_cruise,
        max_abs_a=max_abs_a,
        max_abs_a_lat=max_abs_a_lat,
        max_abs_jerk=max_abs_jerk,
        jerk_rms=jerk_rms,
        kappa_rms=kappa_rms,
        l_max_dev=l_max_dev,
        decision_switches=decision_switches,
        tau_violation=tau_violation,
        blocked=blocked_flag,
        success=success,
        s_end=s_end,
        efficiency=efficiency,
        t_arrive=t_arrive,
        qp_solve_ms=qp_solve_ms,
    )


def _metrics_text(m):
    if m is None or m.get("_infeasible"):
        return "QP 不可行"
    if np.isnan(m["t_arrive"]):
        arrive_str = "未通过"
    else:
        arrive_str = f"t_arrive = {m['t_arrive']:.2f} s"
    return (
        f"巡航 v = {m['avg_v']:.2f} m/s   eff = {m['efficiency'] * 100:.0f}%\n"
        f"{arrive_str}     s_end = {m['s_end']:.1f} m\n"
        f"|a|max = {m['max_abs_a']:.2f} m/s²\n"
        f"|jerk|max = {m['max_abs_jerk']:.2f} m/s³"
    )


def plot_compare_v(ax, r_b, r_g, scn: Scenario):
    ax.set_title("速度曲线 v(t) 对比", fontsize=11, fontweight="bold")
    if r_b["v_qp"] is not None:
        ax.plot(r_b["ts"], r_b["v_qp"], color=C_BAS, lw=2.4, label="Baseline")
    if r_g["v_qp"] is not None:
        ax.plot(r_g["ts"], r_g["v_qp"], color=C_MIKU, lw=2.4, label="MIKU")
    ax.axhline(scn.ego.v0, color="gray", ls=":", lw=0.8, label=f"v_ref={scn.ego.v0}")
    ax.set_xlabel("t [s]")
    ax.set_ylabel("v [m/s]")
    ax.legend(fontsize=9, loc="lower right")
    ax.set_xlim(0, scn.t_max)
    ax.set_ylim(-0.5, max(13, scn.ego.v0 + 4))
    ax.grid(alpha=0.3)
    # 指标文字框
    m_b = compute_metrics(r_b, scn)
    m_g = compute_metrics(r_g, scn)
    ax.text(
        0.02,
        0.98,
        f"Baseline\n{_metrics_text(m_b)}",
        transform=ax.transAxes,
        fontsize=8,
        va="top",
        ha="left",
        bbox=dict(
            facecolor="white",
            edgecolor=C_BAS,
            lw=1.0,
            alpha=0.92,
            boxstyle="round,pad=0.3",
        ),
    )
    ax.text(
        0.45,
        0.98,
        f"MIKU\n{_metrics_text(m_g)}",
        transform=ax.transAxes,
        fontsize=8,
        va="top",
        ha="left",
        bbox=dict(
            facecolor="white",
            edgecolor=C_MIKU,
            lw=1.0,
            alpha=0.92,
            boxstyle="round,pad=0.3",
        ),
    )


def plot_compare_a(ax, r_b, r_g, scn: Scenario):
    ax.set_title("加速度 a(t) 对比 + jerk", fontsize=11, fontweight="bold")
    dt = r_b["ts"][1] - r_b["ts"][0]
    if r_b["a_qp"] is not None:
        ax.plot(r_b["ts"], r_b["a_qp"], color=C_BAS, lw=2.4, label="Baseline a")
        jerk_b = np.diff(r_b["a_qp"]) / dt
        ax.plot(
            r_b["ts"][1:],
            jerk_b * 0.2,
            color=C_BAS,
            lw=1.0,
            ls=":",
            alpha=0.6,
            label="Baseline jerk×0.2",
        )
    if r_g["a_qp"] is not None:
        ax.plot(r_g["ts"], r_g["a_qp"], color=C_MIKU, lw=2.4, label="MIKU a")
        jerk_g = np.diff(r_g["a_qp"]) / dt
        ax.plot(
            r_g["ts"][1:],
            jerk_g * 0.2,
            color=C_MIKU,
            lw=1.0,
            ls=":",
            alpha=0.6,
            label="MIKU jerk×0.2",
        )
    ax.axhline(0, color="gray", ls=":", lw=0.6)
    ax.set_xlabel("t [s]")
    ax.set_ylabel("a [m/s²]  /  jerk×0.2 [m/s³]")
    ax.legend(fontsize=8, loc="upper right", ncol=2)
    ax.set_xlim(0, scn.t_max)
    ax.set_ylim(-5.5, 4.0)
    ax.grid(alpha=0.3)


SCENARIO_META = {
    "01_crossing_ped": "P1：单行人横穿（压力参数）",
    "02_ped_plus_parked": "P2：行人横穿 + 左侧停车（压力参数）",
    "03_narrow_cones": "P3：窄路通行 + 水马/交通锥混合（压力参数）",
    "04_dense_construction": "P4：单车道维修封闭 + 导流借道（压力参数）",
    "05_crossing_ped_cmp": "C1：单行人横穿（可比参数）",
    "06_ped_plus_parked_cmp": "C2：行人横穿 + 左侧停车（可比参数）",
    "07_narrow_cones_cmp": "C3：窄路通行 + 水马/交通锥混合（可比参数）",
    "08_dense_construction_cmp": "C4：单车道维修封闭 + 导流借道（可比参数）",
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
                w.writerow(
                    [
                        mode,
                        f"{s:.4f}",
                        f"{r['l_min'][i]:.4f}",
                        f"{r['l_max'][i]:.4f}",
                        f"{r['l_path'][i]:.4f}",
                    ]
                )

    with open(
        os.path.join(data_dir, "st_curves.csv"), "w", newline="", encoding="utf-8"
    ) as f:
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
                        j_qp_val = f"{(a_arr[i + 1] - a_arr[i]) / dt:.4f}"
                    else:
                        j_qp_val = "0.0000"
                else:
                    s_qp_val = v_qp_val = a_qp_val = a_y_val = j_qp_val = ""
                w.writerow(
                    [
                        mode,
                        f"{t:.3f}",
                        s_ub_val,
                        s_dp_val,
                        s_qp_val,
                        v_qp_val,
                        a_qp_val,
                        a_y_val,
                        j_qp_val,
                    ]
                )

    with open(
        os.path.join(data_dir, "st_bounds.csv"), "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow(["mode", "obs_name", "t", "s_lo", "s_hi", "is_static"])
        for mode, r in [("baseline", r_b), ("miku", r_g)]:
            for b in r["st_bounds"]:
                is_s = 1 if b["is_static"] else 0
                for t, s_lo, s_hi in b["intervals"]:
                    w.writerow(
                        [
                            mode,
                            b["name"],
                            f"{t:.3f}",
                            f"{s_lo:.4f}",
                            f"{s_hi:.4f}",
                            is_s,
                        ]
                    )

    with open(
        os.path.join(data_dir, "corridor.csv"), "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow(["s_k", "tau_k"])
        if r_g["corridor"]:
            for s_k, tau_k in r_g["corridor"]:
                w.writerow([f"{s_k:.4f}", f"{tau_k:.4f}"])

    with open(
        os.path.join(data_dir, "obstacles.csv"), "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow(["name", "obs_type", "is_static", "s0", "l0", "vs", "vl", "W", "L"])
        for obs in scn.obstacles:
            w.writerow(
                [
                    obs.name,
                    obs.obs_type,
                    1 if obs.is_static else 0,
                    f"{obs.s0:.4f}",
                    f"{obs.l0:.4f}",
                    f"{obs.vs:.4f}",
                    f"{obs.vl:.4f}",
                    f"{obs.W:.4f}",
                    f"{obs.L:.4f}",
                ]
            )

    def _metrics_dict(m, r):
        if m is None or m.get("_infeasible"):
            qp_ms = m["qp_solve_ms"] if m else {"path": 0.0, "speed": 0.0, "total": 0.0}
            return {
                "avg_v": None,
                "max_abs_a": None,
                "max_abs_a_lat": None,
                "max_abs_jerk": None,
                "s_end": None,
                "t_arrive": None,
                "blocked_idx": int(r.get("blocked_idx", -1)),
                "blocked_s": None
                if r.get("blocked_s") is None
                else round(float(r["blocked_s"]), 4),
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
            "s0": scn.ego.s0,
            "l0": scn.ego.l0,
            "v0": scn.ego.v0,
            "L": scn.ego.L,
            "W": scn.ego.W,
        },
        "scn_params": {
            "s_max": scn.s_max,
            "t_max": scn.t_max,
            "l_road_min": scn.l_road_min,
            "l_road_max": scn.l_road_max,
            "lane_borrow": scn.lane_borrow,
            "delta_baseline": scn.delta_baseline,
            "delta_min": scn.delta_min,
            "delta_max": scn.delta_max,
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
    ax_v = fig.add_subplot(gs[2, 0])
    ax_a = fig.add_subplot(gs[2, 1])

    plot_sl(ax_sl_b, r_b, "Baseline ① PathBounds → ② Path QP", scn)
    plot_sl(ax_sl_g, r_g, "MIKU     ① PathBounds (τ-shifted) → ② Path QP", scn)
    plot_st(ax_st_b, r_b, "Baseline ③ SBD → ④ DP → ⑤⑥ → ⑦ QP", scn)
    plot_st(ax_st_g, r_g, "MIKU     ③ SBD → ④ DP → ⑤⑥ → 走廊注入 → ⑦ QP", scn)
    plot_compare_v(ax_v, r_b, r_g, scn)
    plot_compare_a(ax_a, r_b, r_g, scn)

    title = SCENARIO_META.get(scn_name, scn_name)
    fig.suptitle(
        f"{title} —— Baseline vs MIKU 全链路对照",
        fontsize=14,
        fontweight="bold",
        y=0.995,
    )
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
            summary.append(
                (label, dict(v_min=v_min, v_min_t=v_min_t, a_min=a_min, s_end=s_end))
            )
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
                print(
                    f"{title:<32} {label:<10} "
                    f"{m['v_min']:>6.2f}m/s {m['a_min']:>6.2f}m/s² "
                    f"{m['s_end']:>5.1f}m"
                )
        print("-" * 78)


if __name__ == "__main__":
    main()
