# 第二战役 Round01 — Apollo 工程审（审 v10）

核查重构与压缩后 Apollo 11.0 事实链是否仍准确：类名/方法名/开关/参数的挂靠关系、pipeline 描述、历史 Task 名指代声明。

## P0

无。

## major

无。压缩未引入新的工程事实错误：抽查 STDrivableBoundary 复用链（STBoundsDecider 生产 / PathTimeHeuristicOptimizer 唯一原生消费 / use_st_drivable_boundary 默认关 / LaneFollowPath pipeline 不含 STBoundsDecider / 速度边界决策刷新而不清空）逐句与 v9 等价；obstacle_lat_buffer 0.4 m、nudge 双参数 0.3/0.4 m、0.5 m/s 阈值、Δt=0.1 s 与 100 ms 周期分属两个量、OSQP/Apollo 11.0/C++17 版本号均保留。

## minor

- **A1-1**（§3.2 L257）：`UpdatePathBoundaryBySLPolygon` 在压缩后首次出现时不再挂靠 `PathBoundsDeciderUtil`，写作"Apollo 在 \texttt{UpdatePathBoundaryBySLPolygon} 中…"。该方法是 PathBoundsDeciderUtil 的静态方法，类归属虽在 §2 出现过，但跨节悬空指代不利复核。**修复**：改为"Apollo 在 \texttt{PathBoundsDeciderUtil} 的 \texttt{UpdatePathBoundaryBySLPolygon} 中…"。
- **A1-2**（§4 比较口径段）：压缩后删去了 IsWithinPathDeciderScopeObstacle / SpeedBoundsDecider 的点名，改为"Apollo原生流水线将动态障碍物排除在路径阶段之外、交由ST阶段以时间窗约束兜底"。机制语义不变且 §2 已点名，可接受；建议补"如第\ref{sec:problem}节所述"指回，明确口径出处。**判定**：低优先级，可与 A1-1 同批处理或维持。

## 确认项

- 历史 Task 名指代声明（PathBoundsDecider / PiecewiseJerkPathOptimizer 沿用历史名）在 §2 保留，正文后续使用一致。
- 引言新增的工业部署引用（Apollo/Autoware/ROVER 5.0）与 v9 相关工作节事实一致，无新增声称。
- P4 与 LaneBorrowPath 触发条件的局限声明保留。
- Dreamview 在环佐证与数值复现程序数据源分离声明保留。

SCORE: P0=0 major=0 minor=2
