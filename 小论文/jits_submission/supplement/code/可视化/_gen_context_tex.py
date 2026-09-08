# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy>=1.26",
#     "matplotlib>=3.8",
#     "scipy>=1.11",
#     "osqp>=0.6.3",
# ]
# ///
"""Generate paper context macros from the existing Apollo simulation config.

This file collects scenario parameters, method constants, and example values
that are reused across the thesis text. The paper should reference these
macros instead of embedding bare numbers inline.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "毕业论文" / "_experiment_context.tex"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apollo_pipeline as ap  # noqa: E402


def fmt(v, digits: int = 2) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, int):
        return str(v)
    return f"{v:.{digits}f}"


def add(lines: list[str], name: str, value, digits: int = 2) -> None:
    lines.append(rf"\newcommand{{\{name}}}{{{fmt(value, digits)}}}")


def main() -> None:
    lines = [
        "% 自动生成：论文上下文与场景参数宏。请勿手动编辑。",
        "% 来源：可视化/_gen_context_tex.py 读取 apollo_pipeline.py 中的场景定义与方法常量",
        "% 重生成：cd 可视化 && uv run _gen_context_tex.py",
        "",
    ]

    # 威胁度模型权重
    weights = ap.THREAT_WEIGHTS
    add(lines, "ThreatWeightTtc", weights[0], 2)
    add(lines, "ThreatWeightOverlap", weights[1], 2)
    add(lines, "ThreatWeightVel", weights[2], 2)
    add(lines, "ThreatWeightType", weights[3], 2)
    add(lines, "ThreatWeightInter", weights[4], 2)
    add(lines, "ThreatTtcCrit", ap.T_CRIT, 1)
    add(lines, "ThreatTtcMax", ap.T_MAX, 1)
    add(lines, "ThreatClusterRadius", ap.D_CLUSTER, 1)
    add(lines, "ThreatVelLimit", ap.V_LIMIT, 1)
    add(lines, "ThreatTypePed", ap.F_TYPE_MAP["ped"], 1)
    add(lines, "ThreatTypeBike", ap.F_TYPE_MAP["bike"], 1)
    add(lines, "ThreatTypeVehicle", ap.F_TYPE_MAP["vehicle"], 1)
    add(lines, "ThreatTypeUnknownMovable", ap.F_TYPE_MAP["unknown_movable"], 1)
    add(lines, "ThreatTypeStatic", ap.F_TYPE_MAP["static"], 1)
    add(lines, "ThreatTypeCone", ap.F_TYPE_MAP["cone"], 2)

    # Narrow cones pressure/comparable scenes
    narrow_p = ap.PRESSURE_SCENARIOS["03_narrow_cones"]
    narrow_c = ap.COMPARABLE_SCENARIOS["07_narrow_cones_cmp"]
    left_obs = narrow_c.obstacles[: len(narrow_c.obstacles) // 2]
    right_obs = narrow_c.obstacles[len(narrow_c.obstacles) // 2 :]
    add(lines, "NarrowRoadLeft", narrow_p.l_road_min, 3)
    add(lines, "NarrowRoadRight", narrow_p.l_road_max, 3)
    add(lines, "NarrowRoadWidth", narrow_p.l_road_max - narrow_p.l_road_min, 2)
    add(lines, "NarrowEgoWidth", narrow_p.ego.W, 2)
    add(lines, "NarrowEgoHalfWidth", narrow_p.ego.W / 2, 3)
    add(lines, "NarrowEgoSpeed", narrow_p.ego.v0, 1)
    add(lines, "NarrowConeWidth", right_obs[0].W, 2)
    add(lines, "NarrowConeLength", right_obs[0].L, 1)
    add(lines, "NarrowCmpObsCountPerSide", len(left_obs), 0)
    add(lines, "NarrowCmpConeCountPerSide", len(left_obs), 0)  # ch8 compat
    add(lines, "NarrowCmpLongitudinalSpacing", left_obs[1].s0 - left_obs[0].s0, 1)
    # Left side: water barriers (static type)
    add(lines, "NarrowCmpLeftBarrierL", left_obs[0].l0, 2)
    add(lines, "NarrowCmpLeftBarrierWidth", left_obs[0].W, 1)
    add(lines, "NarrowCmpLeftBarrierLength", left_obs[0].L, 1)
    # Right side: cones
    add(lines, "NarrowCmpRightConeL", right_obs[0].l0, 2)
    words = ["One", "Two", "Three"]
    for word, obs in zip(words, right_obs):
        add(lines, f"NarrowCmpRightConeS{word}", obs.s0, 1)
        add(lines, f"NarrowCmpRightConeL{word}", obs.l0, 2)
    add(lines, "NarrowCmpConeWidth", right_obs[0].W, 2)
    add(lines, "NarrowCmpConeLength", right_obs[0].L, 1)

    # Dense construction scene counts
    dense_p = ap.PRESSURE_SCENARIOS["04_dense_construction"]
    dense_c = ap.COMPARABLE_SCENARIOS["08_dense_construction_cmp"]
    add(lines, "DenseConstructionTotalObstacles", len(dense_p.obstacles), 0)
    add(
        lines,
        "DenseConstructionEntranceCones",
        sum(1 for obs in dense_p.obstacles if obs.name.startswith("锥E")),
        0,
    )
    add(
        lines,
        "DenseConstructionMaintenanceBarriers",
        sum(1 for obs in dense_p.obstacles if obs.name.startswith("水马")),
        0,
    )
    add(
        lines,
        "DenseConstructionExitCones",
        sum(1 for obs in dense_p.obstacles if obs.name.startswith("锥X")),
        0,
    )
    add(lines, "DenseConstructionLaneBorrow", dense_p.lane_borrow, 0)
    add(lines, "DenseConstructionEgoSpeed", dense_p.ego.v0, 1)
    add(lines, "DenseConstructionCmpBarrierL", dense_c.obstacles[5].l0, 3)

    # Crossing pedestrian scene used in chapter 7
    ped_c = ap.COMPARABLE_SCENARIOS["05_crossing_ped_cmp"]
    add(lines, "PedCmpEgoSpeed", ped_c.ego.v0, 1)
    add(lines, "PedCmpObstacleS", ped_c.obstacles[0].s0, 1)
    add(lines, "PedCmpObstacleL", ped_c.obstacles[0].l0, 1)
    add(lines, "PedCmpPedVel", ped_c.obstacles[0].vl, 2)
    add(lines, "PedCmpPedWidth", ped_c.obstacles[0].W, 1)
    add(lines, "PedCmpRoadLeft", ped_c.l_road_min, 3)
    add(lines, "PedCmpRoadRight", ped_c.l_road_max, 3)
    add(lines, "PedCmpRoadWidth", ped_c.l_road_max - ped_c.l_road_min, 2)
    ped_s_minus = ped_c.obstacles[0].s0 - ped_c.obstacles[0].L / 2
    ped_tau = ap.arrival_time(ped_s_minus, ped_c)
    ped_pred_l = ped_c.obstacles[0].position_at(ped_tau)[1]
    ped_delta = ap.compute_delta(ped_c.obstacles[0], ped_c)
    ped_u = ped_pred_l - ped_c.obstacles[0].W / 2 - ped_delta
    ped_v = ped_pred_l + ped_c.obstacles[0].W / 2 + ped_delta
    add(lines, "PedCmpSMinus", ped_s_minus, 2)
    add(lines, "PedCmpDelta", ped_delta, 2)
    add(lines, "PedCmpTau", ped_tau, 2)
    add(lines, "PedCmpPredL", ped_pred_l, 2)
    add(lines, "PedCmpU", ped_u, 2)
    add(lines, "PedCmpV", ped_v, 2)
    add(lines, "PedCmpGapZero", ped_u - ped_c.l_road_min, 2)
    add(lines, "PedCmpGapOne", ped_c.l_road_max - ped_v, 2)

    # Small analytic example used in the ST corridor derivation
    add(lines, "PedExampleS", 10.0, 1)
    add(lines, "PedExampleTau", 1.25, 2)
    add(lines, "PedExampleVel", 8.0, 1)
    add(lines, "PedExampleLatVel", 1.7, 1)
    add(lines, "PedExampleDelta", 1.2, 1)
    add(lines, "PedExamplePredL", 2.125, 3)
    add(lines, "PedExampleLeftBoundary", 1.875, 3)
    add(lines, "PedExampleRightBoundary", 2.375, 3)
    add(lines, "PedExampleGapZero", 2.55, 2)
    add(lines, "PedExampleGapOne", -1.70, 2)
    add(lines, "PedExampleDeltaT", 0.1, 1)
    add(lines, "PedExampleSk", 10.0, 1)
    add(lines, "PedExampleTauK", 1.25, 2)
    add(lines, "PedExampleBoundaryL", 0.0, 1)
    add(lines, "PedExampleRoadLeft", -1.875, 3)
    add(lines, "PedExampleRoadRight", 1.875, 3)
    add(lines, "PedExampleRoadWidth", 3.75, 2)
    add(lines, "PedExamplePedWidth", 0.5, 1)
    add(lines, "PedExamplePedHalfWidth", 0.25, 2)
    add(lines, "PedExampleEgoWidth", narrow_p.ego.W, 2)
    add(lines, "PedExampleMidTau", 0.625, 3)
    add(lines, "PedExampleMidS", 5.0, 1)
    add(lines, "PedExampleMidLatShift", 1.0625, 2)
    add(lines, "PedExampleFinalL", 2.125, 3)
    add(lines, "PedExampleBoundaryLow", 1.875, 3)
    add(lines, "PedExampleBoundaryHigh", 2.375, 3)
    add(lines, "PedExampleBaselineGap", 0.425, 3)
    add(lines, "PedExampleLastRestrictedIndex", 12, 0)
    add(lines, "PedExampleLastRestrictedTime", 1.2, 1)
    add(lines, "PedExampleFirstFreeIndex", 13, 0)
    add(lines, "PedExampleFirstFreeTime", 1.3, 1)
    # Overshoot = PedExamplePredL - PedExampleRoadRight = 2.125 - 1.875
    add(lines, "PedExampleOvershoot", 0.25, 2)

    # Chapter 6 independent-vs-group decision example
    add(lines, "GroupExampleRoadWidth", 7.5, 1)
    add(lines, "GroupExampleRoadLeft", -3.75, 2)
    add(lines, "GroupExampleRoadRight", 3.75, 2)
    add(lines, "GroupExampleDelta", 1.2, 1)
    add(lines, "GroupExampleRightObsLow", 0.1, 1)
    add(lines, "GroupExampleRightObsHigh", 0.4, 1)
    add(lines, "GroupExampleRightObsCenter", 0.25, 2)
    add(lines, "GroupExampleLeftObsLow", -0.4, 1)
    add(lines, "GroupExampleLeftObsHigh", -0.1, 1)
    add(lines, "GroupExampleLeftObsCenter", -0.25, 2)
    add(lines, "GroupExampleGreedyUpper", -1.1, 1)
    add(lines, "GroupExampleGreedyLower", 1.1, 1)
    add(lines, "GroupExampleInnerGap", 0.2, 1)
    add(lines, "GroupExampleUnifiedUpper", -1.6, 1)
    add(lines, "GroupExampleUnifiedLower", 1.6, 1)
    add(lines, "GroupExampleUnifiedWidth", 2.15, 2)

    # Chapter 7 timing and corridor examples
    add(lines, "PlannerCycleMs", ap.PLANNER_CYCLE_MS, 0)
    add(lines, "PlannerCycleSeconds", ap.PLANNER_CYCLE_MS / 1000, 1)
    add(lines, "PredictionHorizonSeconds", 5.0, 1)
    add(lines, "CitySpeedMin", 8.0, 1)
    add(lines, "CitySpeedMax", 12.0, 1)
    add(lines, "PredictionDistanceMin", 40.0, 0)
    add(lines, "PredictionDistanceMax", 60.0, 0)
    add(lines, "ArrivalCompareEgoSpeed", 5.0, 1)
    add(lines, "ArrivalCompareAccel", 2.0, 1)
    add(lines, "ArrivalCompareRange", 30.0, 0)
    add(lines, "ArrivalCompareProbeS", 20.0, 0)
    add(lines, "ArrivalCompareUniformError", 0.87, 2)
    add(lines, "ArrivalCompareSecondOrderError", 0.51, 2)
    # Improvement = (UniformError - SecondOrderError) / UniformError * 100 = (0.87 - 0.51) / 0.87 * 100 ≈ 41.4
    add(lines, "ArrivalCompareImprovementPct", 41.4, 1)
    add(lines, "AccelMax", 2.0, 1)
    add(lines, "VelocityPredError", 0.2, 1)
    add(lines, "PositionPredError", 0.01, 2)
    add(lines, "DeltaRangeLow", 0.15, 2)
    add(lines, "DeltaRangeHigh", 0.90, 2)
    add(lines, "CorridorRoadLeft", -2.0, 1)
    add(lines, "CorridorRoadRight", 2.0, 1)
    add(lines, "CorridorEgoWidth", 1.5, 1)
    add(lines, "CorridorEgoSpeed", 4.0, 1)
    add(lines, "CorridorStaticSMin", 2.5, 1)
    add(lines, "CorridorStaticSMax", 4.0, 1)
    add(lines, "CorridorStaticLMin", -1.2, 1)
    add(lines, "CorridorStaticLMax", 0.3, 1)
    add(lines, "CorridorDynamicSMin", 6.5, 1)
    add(lines, "CorridorDynamicSMax", 7.0, 1)
    add(lines, "CorridorDynamicLMin", -1.3, 1)
    add(lines, "CorridorDynamicLMax", 1.3, 1)
    add(lines, "CorridorDynamicLatVel", 0.4, 1)
    add(lines, "CorridorSliceSStar", 3.25, 2)
    add(lines, "CorridorGapZero", 0.8, 1)
    add(lines, "CorridorGapOne", 1.7, 1)
    add(lines, "CorridorGapStar", 1.7, 1)
    add(lines, "CorridorDynamicGapMin", 1.35, 2)
    add(lines, "CorridorDynamicGapMax", 1.40, 2)
    add(lines, "CorridorTauMin", 1.625, 3)
    add(lines, "CorridorTauMax", 1.75, 2)

    # Chapter 5 illustrative narrow-cone example
    narrow_example_road_left = -1.875
    narrow_example_road_right = 1.875
    narrow_example_cone_left = -0.685
    narrow_example_cone_right = -0.385
    narrow_example_apollo_delta = narrow_c.delta_baseline
    narrow_example_miku_delta = 0.15
    add(lines, "NarrowExampleRoadLeft", narrow_example_road_left, 3)
    add(lines, "NarrowExampleRoadRight", narrow_example_road_right, 3)
    add(lines, "NarrowExampleConeLeft", narrow_example_cone_left, 3)
    add(lines, "NarrowExampleConeRight", narrow_example_cone_right, 3)
    add(lines, "NarrowExampleConeWidth", narrow_example_cone_right - narrow_example_cone_left, 2)
    add(lines, "NarrowExampleApolloDelta", narrow_example_apollo_delta, 2)
    add(lines, "NarrowExampleMikuDelta", narrow_example_miku_delta, 2)
    add(lines, "NarrowExampleEgoWidth", narrow_p.ego.W, 2)
    add(
        lines,
        "NarrowExampleApolloGap",
        narrow_example_road_right - narrow_example_cone_right - narrow_example_apollo_delta,
        2,
    )
    add(
        lines,
        "NarrowExampleMikuGap",
        narrow_example_road_right - narrow_example_cone_right - narrow_example_miku_delta,
        2,
    )
    add(
        lines,
        "NarrowExampleApolloRightGap",
        narrow_example_cone_left - narrow_example_road_left - narrow_example_apollo_delta,
        2,
    )

    # Threat factors for the right-side cone (low threat)
    threat_cone = right_obs[0]
    rel_v = narrow_c.ego.v0 - threat_cone.vs
    ttc_seconds = (threat_cone.s0 - narrow_c.ego.s0) / rel_v
    add(lines, "NarrowThreatProbeS", threat_cone.s0, 1)
    add(lines, "NarrowThreatTtcSeconds", ttc_seconds, 1)
    add(lines, "NarrowThreatTtc", ap.f_ttc(threat_cone, narrow_c.ego), 2)
    add(lines, "NarrowThreatTtcFactor", ap.f_ttc(threat_cone, narrow_c.ego), 2)
    add(lines, "NarrowThreatOverlap", ap.f_overlap(threat_cone, narrow_c.ego), 0)
    add(lines, "NarrowThreatVel", ap.f_vel(threat_cone, narrow_c.ego), 2)
    add(lines, "NarrowThreatType", ap.f_type(threat_cone), 2)
    add(lines, "NarrowThreatInter", ap.f_inter(threat_cone, narrow_c.obstacles), 2)
    add(lines, "NarrowThreatTheta", ap.compute_threat(threat_cone, narrow_c), 2)
    add(lines, "NarrowThreatDelta", ap.compute_delta(threat_cone, narrow_c), 2)
    add(lines, "NarrowThreatTotalDelta", narrow_p.ego.W / 2 + ap.compute_delta(threat_cone, narrow_c), 2)
    # Threat factors for the left-side barrier (higher threat)
    threat_barrier = left_obs[0]
    add(lines, "NarrowBarrierThreatType", ap.f_type(threat_barrier), 2)
    add(lines, "NarrowBarrierThreatTheta", ap.compute_threat(threat_barrier, narrow_c), 2)
    add(lines, "NarrowBarrierThreatDelta", ap.compute_delta(threat_barrier, narrow_c), 2)
    add(lines, "NarrowBarrierThreatTotalDelta", narrow_p.ego.W / 2 + ap.compute_delta(threat_barrier, narrow_c), 2)
    add(lines, "NarrowBaselineTotalDelta", narrow_p.ego.W / 2 + narrow_c.delta_baseline, 2)

    # Chapter 8 configuration values
    add(lines, "AlgoEgoWidth", narrow_p.ego.W, 2)
    add(lines, "GroupingThreshold", ap.GROUPING_THRESHOLD, 1)
    add(lines, "AlphaCoeff", ap.ALPHA_COEFF, 2)
    add(lines, "BorrowMaxDepth", ap.BORROW_MAX_DEPTH, 0)
    add(lines, "MinBorrowWidth", ap.MIN_BORROW_WIDTH, 1)
    add(lines, "PlanningTimeRangeMin", ap.PLANNING_TIME_RANGE_MIN, 1)
    add(lines, "PlanningTimeRangeMax", ap.PLANNING_TIME_RANGE_MAX, 1)
    add(lines, "PathBoundaryStep", ap.PATH_BOUNDARY_STEP, 1)
    add(lines, "HardwareCpu", "Intel(R) Core(TM) i9-14900HX", 0)
    add(lines, "HardwareMemory", "64GB DDR5", 0)
    add(lines, "HardwareStorage", "2048GB NVMe SSD", 0)
    add(lines, "HardwareOS", "ArchLinux 6.19.11-arch1-1", 0)
    add(lines, "SoftwareApollo", "11.0", 0)
    add(lines, "SoftwareBazel", "5.0+", 0)
    add(lines, "SoftwareLang", "C++17", 0)
    add(lines, "SoftwareOSQP", "0.6.2", 0)
    add(lines, "SoftwareDreamview", "2.0", 0)
    add(lines, "SoftwarePython", "3.12", 0)

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] context macros → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
