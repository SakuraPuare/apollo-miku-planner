# 三区稿 Lean 证明

`Paper3.lean` 是三区稿固定三障碍物截面的可重复证书：枚举全部 `2^3` 方向分配，
比较四个连续分割候选，并证明最大中心间隙及其可实现性。

运行：

```bash
cd lean_proofs/MIKUProofs
lake env lean ../../小论文/lean/Paper3.lean
```

这是论文示例截面的完整证明，不是任意障碍物数量、浮点实现或 Apollo 端到端证明。
通用连续分割方向不变量见 `lean_proofs/MIKUProofs/Partition.lean`。

依赖由 `lean_proofs/MIKUProofs/lakefile.toml` 固定到公开的
Mathlib `v4.33.1`，因此不依赖作者本机路径。完整共享证明、覆盖矩阵和禁止词审计由
`lean_proofs/MIKUProofs/verify_all.sh` 一键运行。
