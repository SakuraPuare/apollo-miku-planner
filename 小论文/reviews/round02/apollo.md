# Round 02 审稿意见 — persona: Apollo 工程审

稿件 `drafts/v2.tex`，事实源 `~/Apollo`（Apollo 11.0 checkout，`modules/planning`）+ 毕设 `毕业论文/chapters`。
本人只读不改稿。下列每条均已在 Apollo 11.0 源码树内核对，给出可定位的源码证据（类名/函数名/默认值/调用关系）。

核查口径：本轮在 `~/Apollo/modules/planning` 与 `modules/prediction` 下逐条 grep 了
`PiecewiseJerkPathOptimizer`、`PathOptimizerUtil::OptimizePath`、`PiecewiseJerkPathProblem`、
`LaneFollowPath`、`STDrivableBoundary` / `SetSTDrivableBoundary` / `use_st_drivable_boundary`、
`STBoundsDecider`、`SpeedBoundsDecider`、`SpeedDecider`、`PathTimeHeuristicOptimizer` / `DpStCost`、
`IsWithinPathDeciderScopeObstacle` / `IsStatic` / `static_obstacle_speed_threshold`、
`TrimPathBounds`、`FallbackPath`、`obstacle_lat_buffer`、`planning_loop_rate`、
`prediction_trajectory_time_length`、`piecewise_jerk_speed` 目录下对 `st_drivable_boundary` 的引用。

---

## 总评

v2 对 Apollo 源码机制的转述总体忠实，且**上一轮三条 major 已全部修复**，这是真改不是幻觉式处置：

- round01 A-1（基线 `PiecewiseJerkPathOptimizer` 在 11.0 不存在为独立 Task）→ v2 第 114 行、第 155 行均补上了版本沿革注脚“已由独立 Task 重构为 LaneFollowPath 等路径 Task 内部调用 PathOptimizerUtil 与底层 PiecewiseJerkPathProblem 实现，本文沿用其历史 Task 名指代”。与源码一致：全树 `PiecewiseJerkPathOptimizer` 零命中，`PathOptimizerUtil::OptimizePath` 在 `path_optimizer_util.cc:96`，`PiecewiseJerkPathProblem` 在 `planning_base/math/piecewise_jerk/`，`LaneFollowPath::OptimizePath` 在 `tasks/lane_follow_path/lane_follow_path.h:51`。**已解决，不再列入。**
- round01 A-2（`STDrivableBoundary` 原生链路）→ v2 第 423 行明确补充“该结构在原生 Apollo 中由 STBoundsDecider 生产、并默认仅在动态规划启发式搜索阶段被消费，速度二次规划本身并不读取它；本文重新利用这一既有数据结构……接入原本不经过该结构的速度二次规划”。逐项核对属实：`SetSTDrivableBoundary` 仅由 `st_bounds_decider.cc:73` 调用，`FLAGS_use_st_drivable_boundary` 默认 `false`（`planning_gflags.cc:377`），消费者是 `gridded_path_time_graph.cc` / `dp_st_cost.cc:119` 的 DP 启发式，`tasks/piecewise_jerk_speed/` 下对 `st_drivable_boundary` **零命中**（QP 的 s 界来自 `piecewise_jerk_speed_optimizer.cc:98` 的 `st_graph_data.st_boundaries()`）。**已解决。**
- round01 A-9（“OSQP 对约束数量的增量不敏感”过强断言）→ v2 已删除该半句，第 423/717 行只保留“仅改写 x^ub 分量、不增约束行、不改 H/A_eq 稀疏模式”这一可被源码直接验证的表述（`piecewise_jerk_speed_optimizer.cc:182` 的 `set_x_bounds`）。**已解决。**

其余可核查的事实点全部对得上：`obstacle_lat_buffer` 默认 0.4（`planning_gflags.cc:175`）、`static_obstacle_speed_threshold` 默认 0.5（`planning_gflags.cc:186`）、`planning_loop_rate=10`（`planning_gflags.cc:21`，对应 100 ms 周期）、Prediction 轨迹时长 `prediction_trajectory_time_length=6.0`（与稿件“未来 6 s 预测轨迹”一致）、`TrimPathBounds` 为真实函数（`path_bounds_decider_util.cc:170`，9 处调用，blocked-then-trim 机制属实）、`FallbackPath` 在 `scenarios/lane_follow/conf/pipeline.pb.txt:19` 的流水线里、`IsWithinPathDeciderScopeObstacle` 内 `IsStatic` 过滤在 `path_bounds_decider_util.cc:686`、其后紧跟 `TODO(jiacheng)`（对应稿件第 165 行“该过滤逻辑附近存在未完成的工程考虑”，属实）。MIKU 自身的 `BuildMikuSTDrivableBoundary` 不在 stock checkout 内，属本组 fork，稿件已明示为新增逻辑，未冒充原生接口，诚实。

本轮无 P0。新发现集中在两类：一是 v2 修复 A-2 时**新引入的生产者命名前后不一致**（PathBoundsDecider 与 LaneFollowPath 混指走廊产出方），二是若干表述精度与类名格式问题。均为“改文字能修”，不触数据红线。

- P0（致命）：0
- major（必改）：2
- minor（建议）：5

---

## P0（致命）

无。未发现臆造接口、伪造源码行为或在 11.0 生产代码中站不住的硬伤。

---

## major（必改）

### A-1【Apollo 工程事实 / 叙事】走廊产出方在 `PathBoundsDecider` 与 `LaneFollowPath` 之间反复横跳，11.0 语境下指代不自洽

定位：
- 第 423 行：走廊由 `\texttt{LaneFollowPath}` 的 `\texttt{BuildMikuSTDrivableBoundary}` 重建并挂到 `ReferenceLineInfo`。
- 第 434 行（同一节、相隔两段）：显式通道把 $\mathcal{T}$ 作为 `\texttt{PathBoundsDecider}` 的新增输出；紧接着“改动范围限于两处，`PathBoundsDecider` 新增时变 SL 投影与 $\mathcal{T}$ 输出，`PiecewiseJerkSpeedOptimizer` 新增 $\mathcal{T}$ 读入与上界收紧”。
- 第 626 行：“Apollo 原生的 `PathBoundsDecider` 通过 `IsWithinPathDeciderScopeObstacle` 将动态障碍物排除”。
- 第 165、202、155 行均以 `PathBoundsDecider` 作为路径边界构建主体。

问题：v2 第 155 行（及 round01 已确立）已经讲清——11.0 里 `PathBoundsDecider` 不是独立 Task，路径边界构建由 `LaneFollowPath` 等路径 Task 内部调用 `PathBoundsDeciderUtil` 完成。既然如此，**新增逻辑的宿主就该统一落在 `LaneFollowPath`（或其调用的 `PathBoundsDeciderUtil`）上**。可第 434 行又把新增输出/改动主体写成 `PathBoundsDecider`，与第 423 行的 `LaneFollowPath::BuildMikuSTDrivableBoundary` 直接打架。一个读过 11.0 代码的审稿人会问：你的 `\mathcal{T}` 到底是 `PathBoundsDecider`（11.0 已无此 Task）产出，还是 `LaneFollowPath` 产出？这正是 round01 A-1 想根除的版本错配，在描述 MIKU **自身改动落点**时又复发了一次，比基线命名更要命，因为这是在讲“我改了哪个文件”。

源码事实：`IsWithinPathDeciderScopeObstacle` 与 `TrimPathBounds` 均属 `PathBoundsDeciderUtil`（`path_bounds_decider_util.cc:674`/`:170`），由 `LaneFollowPath` 等 Task 调用；不存在名为 `PathBoundsDecider` 的 11.0 Task。

处置（改文字能修）：在 4.4 节与第 626 行统一口径。建议把 MIKU 新增逻辑的宿主一律写成“`LaneFollowPath` 路径边界分支（其内部的 `PathBoundsDeciderUtil` 时变投影）”，并在首次出现处加一句与第 155 行同款的版本注脚，例如“下文以 `PathBoundsDeciderUtil` 指代 11.0 中承载路径边界构建的工具类，历史版本对应独立的 `PathBoundsDecider` Task”。第 434 行“`PathBoundsDecider` 新增 $\mathcal{T}$ 输出”改为“`LaneFollowPath` 经 `PathBoundsDeciderUtil` 新增 $\mathcal{T}$ 输出”。这样与第 423 行、与摘要第 97 行“以 LaneFollowPath 路径边界分支接入”三处自洽。

### A-2【Apollo 工程事实】“`PiecewiseJerkSpeedOptimizer` 新增 $\mathcal{T}$ 读入”与“经 `STDrivableBoundary` 注入”两种机制并存，注入点叙述含糊

定位：第 423 行称走廊“在 `\texttt{PiecewiseJerkSpeedOptimizer}` 处按式 (tighten\_ub) 收紧上界”，且经 `STDrivableBoundary` 承载、挂 `ReferenceLineInfo`；第 434 行又称“`PiecewiseJerkSpeedOptimizer` 新增 $\mathcal{T}$ 读入与上界收紧”，把 $\mathcal{T}=\{(s_k,\tau_k)\}$ 当作直接读入对象。

问题：到底是（a）QP 直接读 `STDrivableBoundary` 这个 ST 结构、还是（b）QP 直接读时间清单 $\mathcal{T}$？这两者在源码改动上是不同的接口。原生 `PiecewiseJerkSpeedOptimizer` 的 s 上下界来自 `st_graph_data.st_boundaries()`（`piecewise_jerk_speed_optimizer.cc:98–132`），它既不读 `STDrivableBoundary` 也不读任何 $\mathcal{T}$。稿件需要在一处把改动接口讲死：MIKU 是在 QP 组装 `s_bounds` 之前，用从 `STDrivableBoundary`（或 $\mathcal{T}$）算出的 `s_j^{ub,corridor}` 对 `st_graph_data.st_boundaries()` 推出的上界取 min。现在两段分别说 STDrivableBoundary 和 $\mathcal{T}$，读者无法判断到底改了哪一个读取路径，落到 11.0 代码上会被质疑“说不清接口”。

处置（改文字能修）：统一为单一表述。建议：QP 侧只新增一步——在 `piecewise_jerk_speed_optimizer.cc` 组装 `s_bounds`（对应稿件 `s_j^{ub,SBD}`）后、`set_x_bounds` 前，对每个时间步用挂在 `ReferenceLineInfo` 上的 `STDrivableBoundary`（其内容由路径阶段重建、等价于 $\mathcal{T}$ 收紧后的上界包络）取 min。把第 434 行“新增 $\mathcal{T}$ 读入”改为“新增对 `STDrivableBoundary` 上界包络的读入与按式 (tighten\_ub) 的取 min”，与第 423 行的承载结构对齐，避免 $\mathcal{T}$ 与 `STDrivableBoundary` 两个名词指同一件事却像两条通路。

---

## minor（建议）

### A-3【文风 / Apollo 工程事实】Apollo 类名在摘要与正文之间 `\texttt` / 裸排混用（round01 A-8 未完全清理）

定位：摘要第 97 行 `LaneFollowPath`、引言第 112/114 行 `STDrivableBoundary`/`LaneFollowPath`/`PiecewiseJerkPathProblem`、第 626 行 `PathBoundsDecider`/`IsWithinPathDeciderScopeObstacle`/`SpeedBoundsDecider`、第 579 行 `SpeedBoundsDecider` 均为**裸排**；而正文 4.4 节、结论段（第 155、423、432、434、860 行）用 `\texttt{}`。同一稿内同名类两种字形。
处置：约定“正文类名统一 `\texttt`；摘要为版面整洁可裸排但需全摘要一致”。重点清理第 579、626 两行正文裸排（这两处在正文却没 `\texttt`，最扎眼）。纯格式，不涉事实。

### A-4【Apollo 工程事实】“`STBoundsDecider`” 与 round01 我方记录的 `st_bounds_decider` 需确认稿件用的是类名而非文件名

定位：第 423 行 `\texttt{STBoundsDecider}`。
核对：源码类名确为 `STBoundsDecider`（`st_bounds_decider.h:44: class STBoundsDecider : public Decider`，plugins.xml 注册 `apollo::planning::STBoundsDecider`），文件/Task 名为 `st_bounds_decider`。稿件用的是**驼峰类名 `STBoundsDecider`，正确**，符合 D 节“类名驼峰”。此条仅作确认，无需改；提醒整合编辑勿误把它“修正”成 `SpeedBoundsDecider`——二者是不同 Task（`SpeedBoundsDecider` 在 `tasks/speed_bounds_decider/`，`STBoundsDecider` 在 `tasks/st_bounds_decider/`），稿件区分正确。

### A-5【Apollo 工程事实】第 408 行“`PiecewiseJerkSpeedOptimizer` 在等时间间隔 $\Delta t=0.1$ s 上”宜点明该时间网格的来源，避免与 100 ms 规划周期混淆

定位：第 408 行。
说明：0.1 s 的速度离散步长与 `planning_loop_rate=10`（100 ms 规划周期）数值巧合但语义不同，前者是 QP 时间网格分辨率、后者是重规划频率。源码层面速度 QP 的时间分辨率由速度优化配置而非 `planning_loop_rate` 决定。建议加半句限定“此处 0.1 s 为速度二次规划的时间离散步长，与 100 ms 规划周期分属两个量”，以免 Apollo 熟手误读为二者同源。改文字能修。

### A-6【Apollo 工程事实】第 432 行“`SpeedDecider` 过度保守的全时段让行”措辞偏强，宜收敛为机制描述

定位：第 432 行“把 `SpeedDecider` 过度保守的全时段让行替换为精确时间窗”。
核对：`SpeedDecider`（`speed_decider.cc`）确实产出 FOLLOW/YIELD/OVERTAKE 决策（`:298/:306/:320`），其 YIELD 是基于 ST 边界的让行。但“全时段让行”是对 YIELD 语义的强归纳——YIELD 也带时间范围，并非字面意义上对所有 t 让行。建议改为“把基于全时刻并集投影的保守让行替换为按 $\tau(s_k)$ 的精确等待截止时间”，更贴近源码且不被 SpeedDecider 维护者抓措辞。改文字能修。

### A-7【叙事 / Apollo 工程事实】第 598、603、862 行“Dreamview 在环”与“C++ 实现在 Apollo 工程中运行”需与“Python 数值复现”切割得再硬一点

定位：第 598 行“Dreamview 在环截图来自 MIKU 的 C++ 实现在 Apollo 工程中的运行”；第 862 行结论同义。
说明：稿件已两处声明数值指标来自 Python 复现、Dreamview 仅展示 C++ 接入行为、两者“分属两类独立证据”，这是诚实且必要的。唯一隐患：通篇定量结论（通过率、速度、QP 耗时、消融、灵敏度）**全部出自 Python 复现**，而 C++ 实现只贡献定性截图。建议在实验节开头或局限节再补一句显式声明“本文全部定量指标取自 Python 数值复现程序，C++ 实现仅用于验证生产代码可接入性与定性行为，二者不构成同一数据源的交叉验证”，以免审稿人误以为 QP 耗时来自 Apollo C++ 实测（那会引出“为何不报 Apollo 内置 timer”之类追问）。此为防御性框定，改文字能修，不触数据红线。

---

## 与前几轮的对照

- round01 三条 major（A-1 基线类名版本错配、A-2 STDrivableBoundary 原生链路、A-9 OSQP 过强断言）**本轮确认全部已修**，源码逐项复核通过，非幻觉式处置。
- round01 minor A-8（类名 `\texttt`/裸排混用）**仅部分清理**，本轮降级为 A-3 继续跟。
- 本轮新增 A-1/A-2 两条 major，根因是 v2 在修复 round01 A-2 时把走廊的“生产者（路径侧宿主类）”与“消费者（速度 QP 读取接口）”写散了，出现 `PathBoundsDecider`↔`LaneFollowPath`、`STDrivableBoundary`↔`$\mathcal{T}$` 两组同指异名。建议补入 MODIFICATIONS.md “②Apollo 工程事实”类，与 round01 A-1/A-2 串成同一条“11.0 版本一致性 + 改动落点单一化”整改线。

数据红线核对：本轮所有意见均为“改文字能修”，无一条需新实验或改数字。通过率（压力 0/4 vs 4/4、汇总 4/8 vs 8/8）、平均速度（3.53→4.57，提升 29.3%）、QP 耗时（可比 19.16→6.26、汇总 21.56→5.56、C2 离群 56.41 vs 3.17、C1 反慢 10.44 vs 12.53）、消融（M5=100、M4=99.18）、灵敏度（最坏翻转 57%、最大偏差 6.4%、越界 0）等均与 SPEC B 节冻结值逐字一致，未见外推或美化。

---

SCORE: P0=0 major=2 minor=5
