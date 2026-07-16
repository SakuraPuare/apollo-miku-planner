# 第二战役 Round04 — Apollo 工程审（审 v13）

专项：pipeline 顺序声明与组件职责描述复查（§3.4 注入链路为重点）。

## P0

无。

## major

无。

## minor

无。

## 确认项

- "SpeedBoundsDecider 指 pipeline 末次即 SpeedDecider 之后的 FINAL 调用"与双源融合 $s_j^{ub}=\min(s_j^{ub,\mathrm{SBD}}, s_j^{ub,\mathrm{corridor}})$ 的口径与第一战役核实结论一致。
- PathTimeHeuristicOptimizer（ST 图 DP 粗搜索）、SpeedDecider（纵向超车让行决策）、SpeedBoundsDecider（ST 边界决策）三环节职责描述准确。
- A3-1 修复后 §3.2 工程外扩判据句与 §4.1 参数声明（12\,m）闭环，方法—实验参数链路全部可追溯。
- 走廊未激活的实验事实（§4.4 M4 段、§4.5 局限）与 §3.4 机制描述（注入即收紧上界）不冲突：前者是场景覆盖问题，后者是机制定义，文中已由"其价值由架构设计论证而非本组消融数据给出"明确切分。
- $\Delta t{=}0.1$\,s（速度 QP 离散步长）与 100\,ms（重规划周期）"分属两个量"的辨析句保留。

SCORE: P0=0 major=0 minor=0
