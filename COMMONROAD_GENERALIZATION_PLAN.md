# CommonRoad 泛化改造目标

更新时间：2026-09-06

## 目标

把 MIKU 从“Apollo 结构化场景内有效”推进到“在公开外部场景上具有可复核泛化证据”的算法版本。二区标准要求外部输入语义、车辆模型、评测协议和失败边界都能被独立复现；不能用删除障碍物、放宽安全约束或把无效轨迹改名为成功来达成。

## 已完成的第一阶段

- CommonRoad 参考路线端点投影保留有符号 station，不再把路线外点截断到 `s=0`。
- 所有源动态障碍物都解析、形状/姿态投影和计数；只有扫掠占用与可达路线走廊相交的对象进入规划约束，路线无关对象仍保留审计计数。
- 外部 occupancy 已从固定常速度残差约束中分离，避免同一轨迹被重复扩大不确定性。
- 原生输出改为 CommonRoad `InputState`，由官方 BMW-320i KS 模型积分；新增有界反馈跟踪器并约束 steering-rate、加速度和摩擦圆。
- CommonRoad 目标横向坐标进入外部场景 path endpoint 约束。
- route lanelet 的左右边界已用于外部场景横向可行域，关闭了没有 route 可达性证明的
  全局 lane-borrow；四个场景的边界范围已写入 native JSON。
- 当前回归：`121 passed, 20 skipped`；四个官方 Lankershim 场景在统一 `dt=0.1, horizon_steps=100` 协议下为 `2 valid / 1 planner_failure / 1 invalid_solution`；两个有效解通过官方 BMW-320i dynamics、障碍物、边界和目标检查。

## 当前科学阻塞

场景 3 的有限空间/时间同伦候选仍无法同时通过连续安全证书；场景 4 的目标时间窗
只有约 0.4 s，初始速度约 0.99 m/s，且官方 KS 的 steering-angle-speed 上限为
0.4 rad/s，几何终点虽可达，但终端姿态在该动力学约束下尚未进入目标区域。这个
阻塞属于规划目标、道路边界和可执行控制的耦合问题，不是 CommonRoad 文件读取问题。

## 下一阶段门槛

1. 已将 lanelet polygon 与 reference-path 法向横截面转换为逐 station 的车辆中心可行域，替代固定全局 lateral 范围；仍需继续验证跨拓扑 route 的连通性。
2. 已在速度 QP 中加入 CommonRoad goal time window 的 admissible-knot 枚举、目标速度边界、终端进度约束和有限 wait/pass candidate fallback；等待分支仍需补充停车距离、加速度、jerk 和连续安全证书。
3. 已用同一官方 evaluator 重跑 MIKU、B0 和 Reactive Planner；当前成功率、碰撞率、目标到达率和耗时均可回查到原始结果，但 MIKU 与 B0 成功率相同。
4. 若上述约束下仍无 valid solution，保留负结果并把论文泛化主张降为“未证实”，不得继续声称外部泛化完成。

## 扩展审计

已新增第二道路族留出协议 Peachtree（4 个 XML），与 Lankershim 完全分离。Peachtree
native 结果为 MIKU `1/4 valid、3 planner_failure`，B0 `1/4 valid、2 planner_failure、
1 evaluator-invalid`，Reactive Planner `0/4 valid`。这证明官方读写/evaluator 与局部
lanelet 边界实现能够迁移到不同 NGSIM 道路族，但 MIKU 没有相对 B0 的性能增益，泛化目标
仍未完成。详见 [`小论文-2/COMMONROAD_CROSS_FAMILY_RUN.md`](小论文-2/COMMONROAD_CROSS_FAMILY_RUN.md)。

另新增 US101 lanelet-goal 留出集（4 个 XML）。这些场景的官方目标使用
`goalState/position/lanelet ref`，adapter 已将目标 lanelet polygon 投影为 station/lateral
区间。US101 native 结果为 MIKU `2/4 valid`、B0 `2/4 valid`，Reactive `0/4 valid`；这关闭
了“只支持 point/rectangle goal”的输入缺口，但仍不构成 MIKU 性能优势。
对 lanelet goal，规划 horizon 现在从目标 lanelet 的最早 admissible station 开始，而不是
使用目标区域中点；这样保留“任意进入目标区域”的官方语义。US101 计数未改变，修复被视为
正确性改进而非性能增益。

已对同一公开 NGSIM/Lankershim 目录的十二个新增场景运行相同官方协议。十六场景
MIKU 结果为 `7 valid / 3 planner_failure / 6 evaluator-invalid`；这说明当前算法
已有跨场景有效解，但泛化率仍不足以宣称完成。

原生输出端增加了官方 BMW-320i KS 模型下的有限维终端转向 shooting：只调整不超过
20 个 steering-rate 结点，纵向控制、动力学边界和障碍物约束不放宽；若终端残差不改善
则保留原控制，最终仍由 CommonRoad evaluator 判定。目标矩形区间语义修复后，扩展集为
7/16 valid；不改变四场景主协议的 2/4 结果。

同时，外部 goal 的中心投影作为 path-QP 的精确等距网格端点（分辨率不超过 0.5 m），
矩形四角投影出的 station/lateral 区间另行写入终端约束；本轮 16 场景通过数为 7/16，
说明剩余失败主要是官方动力学/道路边界可执行性，而非 station 离散误差。

目标状态解析已改为读取 `goalState` 直接子节点，避免误取 goal rectangle 自带的姿态。
对 `|goal_heading_error|≤0.5 rad` 的局部 Frenet 情形，path QP 在最后四段渐进匹配目标
切向；大角度目标不强行套用 `tan(Δheading)`，避免制造伪造的横向冲出。这一分支仍由
官方 KS/evaluator 做最终可执行性裁决。
