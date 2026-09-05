# 形式化目标完成审计

本文件按 Codex Goal 的原始范围审计当前证据。状态不是“未发现问题”，而是要求对应
的正面证据等级。

| 要求 | 当前证据 | 状态 |
|---|---|---|
| Lean 环境可重复运行 | `elan toolchain list` 显示 Lean 4.33.1；`MIKUProofs/verify_all.sh` | 已满足 |
| 无 `sorry` / `axiom` | 验证脚本的禁止词扫描 | 已满足 |
| 两篇论文专属证明 | `小论文/lean/Paper3.lean`、`小论文-2/lean/Paper2.lean` | 已满足（范围受限） |
| 最大间隙与连续分割 | `MaxGap.lean`、`Partition.lean`、固定实例 `Paper3.lean` | 契约/固定实例；通用实现 refinement 未满足 |
| 扫描线分组 | `Grouping.lean`、`Scanline.lean` | 递归规格性质已满足；Python 字段 refinement 未满足 |
| 威胁度与安全裕度 | `Threat.lean`、`ThreatExact.lean`、`ThreatSigmoid.lean`、`TypeThreat.lean` | 数学核心已满足；浮点实现 refinement 未满足 |
| 到达时间与时间窗 | `Kinematics.lean`、`TimeWindows.lean`、`WindowAlgebra.lean`、`SafeWindowComplement.lean` | 契约已满足；完整 `merge_windows` refinement 未满足 |
| ST 走廊与因果图 | `STCorridor.lean`、`Rolling.lean` | 方程和传递性已满足；分层笛卡尔路径的层数、空层和非空域构造在 `LayeredSearch.lean`；实际图搜索未满足 |
| 有限联合搜索和 gap | `FiniteSearch.lean`、`Certificates.lean`、`Paper2.lean` | 有限域证书已满足；Python heap/预算 refinement 未满足 |
| 连续碰撞判定 | `ContinuousSafety.lean`、`QuadraticSweep.lean`、`RobustSafety.lean` | 数学安全契约已满足；二维求根实现 refinement 未满足 |
| 降级/fail-closed/滚动一致性 | `Fallback.lean`、`Rolling.lean` | 抽象状态性质已满足；端到端状态连接未满足 |
| Python/Apollo 端到端正确性 | `check_lean_links.py` 仅做符号存在性审计；无端到端 Lean refinement | 未满足 |
| 实验、复杂度、控制跟踪 | 当前只有 Python 回归测试和文档 | 未满足（不属于已有 Lean 定理） |

因此当前证据支持“已形式化的数学契约在假设下成立”，不支持“论文整体和全部实现已被
Lean 证明”。
