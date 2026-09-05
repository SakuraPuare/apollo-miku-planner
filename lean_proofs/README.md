# MIKU Lean 形式化验证

本目录对应两份稿件的不同目标：

- `小论文/lean/Paper3.lean`：三区稿的固定截面最大间隙/连续分割目标。对一个三障碍物截面，形式化枚举完整的 `2^3` 左右绕行分配，并证明四个连续切分候选覆盖其最优值。
- `小论文-2/lean/Paper2.lean`：二区稿升级后的有限空间--时间同伦联合搜索目标。显式定义有限候选域、候选下界和目标值，证明返回候选是全域最小目标，且最优性 gap 为零。

两份证明均使用 Lean 4.33.1 + Mathlib v4.33.1，未使用 `sorry` 或公理化跳过。

```bash
cd lean_proofs/MIKUProofs
./verify_all.sh
lake env lean ../../小论文/lean/Paper3.lean
lake env lean ../../小论文-2/lean/Paper2.lean
```

`FORMAL_COVERAGE.md` 是当前覆盖矩阵；它会把已证明的数学契约和仍未与
Python/Apollo 实现建立 refinement 的部分分开记录。
`COMPLETION_AUDIT.md` 按原始 Codex Goal 逐项给出完成证据等级，避免把契约证明误报为
端到端实现证明。

当前主要对应关系：

- `miku_geometry.solve_max_gap` → `MIKU.MaxGap` 的有限最大值契约；三区稿的具体截面证书在 `小论文/lean/Paper3.lean`。
- `miku_time.safe_time_windows` → `MIKU.Time` 的 before/after 窗口安全契约。
- `joint_homotopy_search.bounded_lazy_joint_search` → `MIKU.Certificates` 的 gap 证书和 `MIKU.FiniteSearch` 的递归有限域最小化器。
- `apollo_pipeline.arrival_time` → `MIKU.Common.arrival_time_monotone` 与 `MIKU.Kinematics` 的匀速/二阶运动学契约。
- `apollo_pipeline.validate_pipeline_candidate_continuous_safety` → `MIKU.ContinuousSafety` 的分段线性轴向分离定理。

新增的 `GeometrySafety.lean`、`WindowAlgebra.lean`、`Partition.lean` 和
`QuadraticSweep.lean` 分别覆盖了通用几何包络、时间窗代数、连续分割方向不变量和
恒加速度二次安全判定的可证明核心；`Grouping.lean` 则给出扫描线递归分组器及其
输入保持、非空和边界分离性质；`RobustSafety.lean` 证明鲁棒占据不相交可向真实
占据子集传递；`STCorridor.lean` 和 `SafeWindowComplement.lean` 直接对应论文的
pass-before/yield-after 与安全时间窗补集方程。
`Threat.lean` 还固定验证了 Python 实际使用的五因子权重和为 1。
`LayeredSearch.lean` 定义分层空间候选的笛卡尔路径枚举，并证明每个生成路径的层数
与输入一致；实际 Python Top-K 动态规划仍单独标注为未完成 refinement。

这些箭头表示规格层对应，不表示已经完成实现级 refinement；未完成项继续在覆盖矩阵中标记。

证明范围是刻意收敛的：三区证明针对论文的固定截面区间模型；二区证明针对论文明确声明的有限候选域，不外推为连续空间全局最优或真实 Apollo/CyberRT 全栈证明。
