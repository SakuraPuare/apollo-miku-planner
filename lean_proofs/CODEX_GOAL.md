# Codex Goal: 两篇论文的 Lean 形式化闭环

## 目标

对 `小论文/`（三区稿）和 `小论文-2/`（二区稿）正文中提到的算法、引理、定理及
可形式化的安全/可行性主张逐项建立 Lean 规格。所有已经声明为“已证明”的定理必须
在 Lean 4.33.1 + Mathlib 下无 `sorry`、无 `axiom` 地重复编译；固定示例不得冒充通用定理。

## 工作规则

1. 先从正文、Python 实现和测试盘点算法入口，再建立精确的有理数/实数规格。
2. 证明失败时区分：规格错误、算法反例、或假设不足；前两类修正实现/测试，后一类在覆盖矩阵中写明假设。
3. 数值浮点、Apollo/CyberRT、实验统计和复杂度只有在建立相应 refinement 后才能宣称已覆盖。
4. 每次变更都运行 `MIKUProofs/verify_all.sh`；脚本同时检查 Python 链接、禁止词、全部 Lean 文件和回归测试。

## 交付物

- `小论文/lean/Paper3.lean` 与 `小论文-2/lean/Paper2.lean`：论文专属证书；
- `MIKUProofs/*.lean`：共享规格与证明；
- `FORMAL_COVERAGE.md`：逐算法覆盖矩阵和未覆盖项；
- `MIKUProofs/verify_all.sh`：可重复验证入口；
- `README.md`：环境和运行说明。

## 当前边界

当前已证明的是数学核心和有限域证书；尚未完成的实现级 refinement（Python 排序、
beam/heap 截断、浮点舍入、Apollo QP/控制跟踪、端到端 pipeline）明确列在覆盖矩阵中。
因此本目标完成前，不得把当前结果表述为“两篇论文所有内容均已被 Lean 证明”。
