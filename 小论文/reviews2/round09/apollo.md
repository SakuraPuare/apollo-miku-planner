# 第二战役 Round09 — Apollo 工程审（审 v17）

专项：回归核查——工程侧历轮修复在 v17 的存活性。

## P0

无。

## major

无。

## minor

无。

## 回归确认（工程侧 4 项全存活）

| 轮次 | 修复 | v17 存活证据 |
|---|---|---|
| R1 A1-1 | UpdatePathBoundaryBySLPolygon 挂靠 PathBoundsDeciderUtil | PathBoundsDeciderUtil ×4 |
| R1 A1-2 | §4 失败口径回指 §2 | "第\ref{sec:problem}节所述"在位 |
| R2 T2-3 | §2 解耦段 \sloppy + "要求"笔误修复 | "要求某动态障碍物在特定时刻已移开" ×1 |
| R3 A3-1 | 12\,m 外扩判据方法侧挂靠 | "外扩一个邻近阈值" ×1 |

防御口径复扫：LaneBorrowPath 声明、FINAL 调用口径、下界不改写、数据源口径（Python 复现为定量来源）全部在位。

SCORE: P0=0 major=0 minor=0
