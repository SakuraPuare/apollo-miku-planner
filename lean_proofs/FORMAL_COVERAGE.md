# Lean 形式化覆盖矩阵（持续更新）

状态说明：`已证明` 表示 Lean 中有无 `sorry` 的定理；`契约性质` 表示证明了算法所需的数学前提；`未覆盖` 表示尚未把实现与规格连接起来，不能据此声称论文整体正确。

| 论文主张/算法 | Lean 文件 | 状态 | 范围与假设 |
|---|---|---|---|
| 三区固定截面最大间隙 | `小论文/lean/Paper3.lean` | 已证明 | 固定道路和 3 个整数障碍区间；完整 `2³` 枚举与 4 个连续切分比较 |
| 通用 `k+1` 连续分割方向不变量 | `MIKUProofs/Partition.lean` | 契约性质 | 对已排序、正宽度区间证明安全带方向不能“先右后左”，因此方向序列为前缀/后缀；尚未把 Python 排序、前缀最大值和候选构造在同一实现定理中闭合 |
| `k+1` 候选间隙的有限最大值扫描 | `MIKUProofs/MaxGap.lean` | 已证明 | 对任意 `n+1` 个有理数 gap，证明最大值存在、可达且扫描结果支配所有候选；尚未证明几何构造恰好产生这些 gap |
| prefix-max 与间隙单调性 | `MIKUProofs/PrefixGap.lean` | 已证明 | 任意列表的前缀最大包络覆盖输入，且 gap 对 upper 单调、对 lower 反单调 |
| 扫描线连通分组 | `MIKUProofs/Grouping.lean`, `MIKUProofs/Scanline.lean` | 契约性质 | 可执行递归扫描器已证明 flatten 保持输入顺序和成员、各组非空；新组边界越过前沿时与已见区间不相交；尚未证明 Python 字典记录的逐字段 refinement |
| 扫描线前沿/包络不变量 | `MIKUProofs/Scanline.lean` | 已证明 | 证明任意列表上的 frontier 覆盖、单调性和追加区间后包络保持；尚未证明完整排序实现 |
| 差异化威胁度/安全裕度 | `MIKUProofs/MIKUCommon.lean` | 契约性质 | 证明非负额外裕度会扩大安全边界；未验证 Python 权重公式 |
| 五因子威胁归一化与裕度映射 | `MIKUProofs/Threat.lean` | 已证明 | 固定 Python 权重 `(0.30,0.20,0.15,0.10,0.25)` 已在 Lean 中验证非负且和为 1；各因子在 `[0,1]` 时证明威胁和裕度映射有界/单调 |
| Python TTC/重叠截断函数与五因子加权 | `MIKUProofs/ThreatExact.lean` | 已证明 | 对论文代码的 TTC 分段、非闭合退化分支、TTC 反单调性、闭区间重叠长度、无重叠归零、overlap 截断、邻居交互贡献/有界平均截断和加权和建立有理数规格；指数 sigmoid、浮点舍入仍未形式化 |
| 相对速度 sigmoid 归一化 | `MIKUProofs/ThreatSigmoid.lean` | 已证明 | 实数 `exp` 定义；按 Python 的 `5·Δv/12` 公式证明 `f_vel` 严格位于 `(0,1)` 且单调 |
| 障碍物类型威胁映射 | `MIKUProofs/TypeThreat.lean` | 已证明 | 形式化代码中的六类离散分值，证明均在 `[0,1]` 且行人分值最大 |
| 到达时间单调性 | `MIKUProofs/MIKUCommon.lean` | 已证明 | 匀速模型，正速度，定点纵向位置 |
| 二阶运动学位移单调性/匀速到达恒等式 | `MIKUProofs/Kinematics.lean` | 已证明 | 非负初速、加速度和时间；匀速分支要求速度非零 |
| 时空走廊端点非空 | `MIKUProofs/MIKUCommon.lean` | 已证明 | 端点满足 guard 后的线性不等式 |
| before/after 时间窗语义 | `MIKUProofs/TimeWindows.lean` | 已证明 | 正确表达先通过/后通过；并证明任一点不在扩张占用区间内必位于其前侧或后侧 |
| 时间窗相交、投影与非空判定 | `MIKUProofs/WindowAlgebra.lean` | 已证明 | 闭区间有理数语义；投影始终落在窗口内，相交非空当且仅当存在共同时间点 |
| ST 走廊 pass-before / yield-after 编译 | `MIKUProofs/STCorridor.lean` | 已证明 | 论文中的空间/时间不等式可排除冲突；正最大速度下因果边可传递且时间单调 |
| 安全时间窗是扩张占据的补集 | `MIKUProofs/SafeWindowComplement.lean` | 契约性质 | 证明前侧/后侧安全性、互补性和不相交；明确安全证书使用窗口严格内部，闭端点仅用于数值投影/ST 编译；浮点端点舍入仍未形式化 |
| 固定路径上下界的可行点 | `MIKUProofs/MIKUCommon.lean` | 已证明 | 有理数区间，取中点 |
| 连续碰撞分离契约 | `MIKUProofs/MIKUCommon.lean` | 已证明 | 轴对齐中心/半径区间且满足分离不等式 |
| 分段线性轨迹的连续安全保持 | `MIKUProofs/ContinuousSafety.lean` | 已证明 | 端点均满足同一轴向分离不等式；线性插值参数在 `[0,1]` |
| 路段带宽包络排除开放障碍区间 | `MIKUProofs/GeometrySafety.lean` | 已证明 | 对带方向标记的区间列表，以 min/max 折叠构造上下界；仅证明满足包络约束时的安全排除 |
| 二区有限空间—时间联合搜索 | `小论文-2/lean/Paper2.lean` | 已证明 | 5 个显式候选；证明该域全部已评估时的全域最小值与零 gap；不含 Python 队列 refinement |
| 实际 branch-and-bound 实现 | — | 未覆盖 | 尚未形式化 heap、预算截断及浮点语义 |
| 有限搜索下界/gap 证书 | `MIKUProofs/Certificates.lean` | 已证明 | 评估集与待处理集覆盖有限域、下界与容差为有理数；证明全域误差界和零 gap 最小性 |
| 走廊到参考线的平方距离下界 | `MIKUProofs/CorridorLowerBound.lean` | 已证明 | 对有理数横向盒，证明盒内任意路径值的平方不小于到零点的最小距离平方；非负其它目标项保持可采纳性 |
| 递归有限候选最小化器 | `MIKUProofs/FiniteSearch.lean` | 已证明 | 任意候选列表；证明选择器不会增大目标、返回候选属于域且支配域中所有目标 |
| 连续扫掠安全证书 | `MIKUProofs/QuadraticSweep.lean` | 契约性质 | 证明正二次项且判别式非正时全时域非负；尚未连接 Python 根区间实现、浮点舍入和二维车辆包络 |
| 有界预测误差传播/鲁棒膨胀 | `MIKUProofs/RobustEnvelope.lean`, `MIKUProofs/RobustSafety.lean` | 已证明 | 线性位置-速度预测模型，误差边界有理数；证明误差管传播、更大膨胀保持保守性，以及真实占据是鲁棒占据子集时安全证书可向下传递 |
| 路径/速度 QP 凸性与动力学 | `MIKUProofs/LinearQP.lean` | 契约性质 | 证明有限个线性半空间与逐坐标盒约束的交集是凸集；尚未形式化 Apollo QP 数据结构、稀疏矩阵和求解器 |
| 固定同伦盒约束的凸性/非空性与标量凸二次目标 | `MIKUProofs/QP.lean` | 已证明 | 任意有限维有理数盒；不等同于 Apollo 多变量求解器实现 |
| 区间/盒约束可行性 | `MIKUProofs/MIKUCommon.lean` | 已证明 | 有理数上下界；中点构造可行点 |
| fail-closed 可行/阻塞分类 | `MIKUProofs/Fallback.lean` | 已证明 | `gap` 与 `epsilon` 的精确有理数比较 |
| 纯解耦投影覆盖导致不可行 | `MIKUProofs/Feasibility.lean` | 已证明 | 若道路区间每一点都落入禁行投影，则不存在安全点 |
| 走廊约束保持安全/恢复非空 | `MIKUProofs/Feasibility.lean` | 已证明 | 走廊包含于原安全盒时保持安全；已有原可行见证时约束集非空 |
| 实际降级、停车和滚动实现 | — | 未覆盖 | 尚未把 Python 状态与递归可行性连接到 Lean 状态机 |
| 滚动承诺/阻塞状态保持 | `MIKUProofs/Rolling.lean` | 已证明 | 三态抽象状态机：committed 和 blocked 状态不会被新决策覆盖 |
| 时间同伦因果可传递性 | `MIKUProofs/Rolling.lean` | 已证明 | 正最大速度和有序站点；离散选择满足旅行时间下界时可传递 |
| 到达时间反馈细化 | `MIKUProofs/Refinement.lean` | 已证明 | `τ⁺=(1−α)τ+ατ̂` 在 `α∈[0,1]` 时保持给定时间区间；边界 α=0/1 恒等式 |
| 复杂度、实验通过率、Apollo 集成 | — | 未覆盖 | 这些不是当前 Lean 定理 |

运行全部当前证明：

```bash
cd lean_proofs/MIKUProofs
lake env lean MIKUCommon.lean
lake env lean Threat.lean
lake env lean TimeWindows.lean
lake env lean Scanline.lean
lake env lean Fallback.lean
lake env lean ../../小论文/lean/Paper3.lean
lake env lean ../../小论文-2/lean/Paper2.lean
```

验证脚本还会审计覆盖矩阵引用的 Python 函数是否存在，并拒绝 Lean 源码中出现 `sorry` 或 `axiom`。
若环境存在 `uv`，还会运行几何、时间和联合搜索回归测试（当前结果：71 passed）。

## 实现符号盘点

下表把两篇论文正文实际调用的主要 Python 算法入口逐一列出。`规格/契约`表示
Lean 已证明数学性质但还没有逐行 refinement；`部分`表示只有其中一段语义已证明；
`未覆盖`表示当前没有声称有 Lean 证明。

| Python 入口 | Lean 对应 | 状态 |
|---|---|---|
| `solve_max_gap` / `brute_force_max_gap` | `MaxGap.lean`, `Paper3.lean`, `Partition.lean` | 规格/固定实例；通用排序实现 refinement 未完成 |
| `enumerate_lateral_bands` | `MaxGap.lean`, `Partition.lean` | 部分；候选结构不变量已证明，排序/Top-K 未证明 |
| `select_spatial_homotopy` / `enumerate_spatial_homotopies` | `FiniteSearch.lean`, `LayeredSearch.lean`, `Paper2.lean` | 部分；Lean 定义分层路径笛卡尔枚举并证明路径长度、空层不可行及各层非空时存在完整路径；有限候选最小化已证明；实际 DP/Top-K 截断 refinement 未证明 |
| `safe_time_windows` / `intersect_window_sets` | `TimeWindows.lean`, `WindowAlgebra.lean` | 规格/契约；Python merge/complement refinement 未完成 |
| `select_time_window` | `WindowAlgebra.lean`, `MaxGap.lean` | 部分；投影与有限择优骨架已证明 |
| `enumerate_temporal_homotopies` | `Rolling.lean`, `Certificates.lean` | 部分；因果可传递与有限 gap 已证明，beam 实现未证明 |
| `bounded_lazy_joint_search` | `FiniteSearch.lean`, `Certificates.lean`, `Paper2.lean` | 有限域规格已证明；heap/预算/浮点实现未证明 |
| `certify_sampled_axis_aligned_motion` / `validate_candidate_continuous_safety` | `ContinuousSafety.lean`, `GeometrySafety.lean` | 契约；采样充分性与实现 refinement 未证明 |
| `validate_candidate_constant_acceleration_safety` | `QuadraticSweep.lean` | 契约；二维二次根求交实现未证明 |
| `f_ttc` / `f_overlap` / `compute_threat` / `compute_delta` | `ThreatExact.lean`, `Threat.lean`, `ThreatSigmoid.lean`, `TypeThreat.lean` | 数学核心已证明；Python 浮点与所有分支 refinement 未完成 |
| `arrival_time` / `speed_dp` / `speed_qp` | `Kinematics.lean`, `MIKUCommon.lean`, `QP.lean` | 运动学与盒凸性契约；Apollo 求解器实现未覆盖 |
| `path_bounds_decider` / `path_optimizer` / `st_boundary_mapper` | `Feasibility.lean`, `ContinuousSafety.lean` | 安全/可行性契约；完整数据结构和数值求解未覆盖 |
| `run_pipeline` / `validate_pipeline_candidate_continuous_safety` | `Fallback.lean`, `Rolling.lean`, `RobustEnvelope.lean` | fail-closed/状态/误差管契约；端到端 refinement 未覆盖 |
