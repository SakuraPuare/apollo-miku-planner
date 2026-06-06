# Round 05 审稿意见 — persona: Apollo 工程审

稿件 `drafts/v5.tex`，事实源 `~/Apollo`（Apollo 11.0 checkout，`modules/planning`）+ 毕设 `毕业论文/`。
本人只读不改稿。下列每条均已在 Apollo 11.0 源码树内核对，给出可定位的源码证据（类名/函数名/默认值/调用关系/pipeline 顺序）。

核查口径：本轮在 `~/Apollo/modules/planning` 下逐条 grep 复核了
`PathBoundsDeciderUtil` / `IsWithinPathDeciderScopeObstacle`（函数体）/ `TrimPathBounds`、
`GetBufferBetweenADCCenterAndEdge` / `UpdatePathBoundaryBySLPolygon`、
`obstacle_lat_buffer`(=0.4) / `static_obstacle_nudge_l_buffer`(=0.3) / `nonstatic_obstacle_nudge_l_buffer`(=0.4) /
`static_obstacle_speed_threshold`(=0.5)、`LaneFollowPath` / `LaneBorrowPath` / `FallbackPath`、
`PiecewiseJerkSpeedOptimizer`（`s_bounds` 装配源 = `st_graph_data.st_boundaries()` + `GetUnblockSRange` + `fmin`）、
`SpeedBoundsDecider`（`total_time: 7.0`）、`STBoundsDecider` / `SetSTDrivableBoundary` / `use_st_drivable_boundary`(默认 false)、
`st_drivable_boundary.proto`（`STDrivableBoundaryInstance{t, s_lower, s_upper, ...}`）、
`scenarios/lane_follow/conf/pipeline.pb.txt`（task 顺序）、`PiecewiseJerkPathOptimizer`（全树 0 命中，确为历史名）、
`PathOptimizerUtil`(17) / `PiecewiseJerkPathProblem`(4)、`prediction_trajectory_time_length`(=6.0) / `prediction_total_time`(=5.0)。

---

## 总评

v5 把 round04 唯一 major（A-1，`SpeedDecider` 与 `PathTimeHeuristicOptimizer` 执行顺序写反）与四条 minor **全部真改掉了**，非幻觉式处置，源码逐项复核通过：

- round04 A-1 → v5 第 376 行已改为「Baseline 经 `PathTimeHeuristicOptimizer` 在 ST 图上动态规划粗搜索、再由 `SpeedDecider` 标定 YIELD/OVERTAKE」，第 568 行同步改为「`PathTimeHeuristicOptimizer` 动态规划粗搜索、再由 `SpeedDecider` 标定让行或超车」。与 `lane_follow` pipeline 实际顺序（DP 在前、SpeedDecider 在后）一致。**已解决，两处一并改对。**
- round04 A-2（裸排 `STDrivableBoundary`）→ v5 全文 `grep STDrivableBoundary | grep -v 'texttt{STDrivableBoundary}'` 零命中，全部已加 `\texttt`。**已解决。**
- round04 A-4（`STBoundsDecider`/flag 门控措辞偏强）→ v5 第 413 行已收敛为「该结构在原生 Apollo 中由 `STBoundsDecider` 在含其的 pipeline 中生产，且其下游消费受 `use_st_drivable_boundary` 开关门控、默认关闭；在本文接入的 `LaneFollowPath` 路径 pipeline 中并不含 `STBoundsDecider`，该结构本就闲置」。与源码（flag 默认 false、lane_follow 链无 STBoundsDecider）逐项相符。**已解决，且把闲置性说足。**
- round04 A-5（「符合插件式扩展规范」措辞略夸张）→ v5 第 424 行已改为「改动局部化于两个既有 Task 内部，不触及求解器内部数据结构与求解流程，亦不新增对外接口」，去除了对 plugin 机制的归类性声称。**已解决。**

本轮可核查的硬事实再次全部对得上，承重的工程集成声称均经源码结构验证可行：

- 速度 QP 的 s 界装配：`piecewise_jerk_speed_optimizer.cc` 从 `reference_line_info_->mutable_st_graph_data().st_boundaries()` 取各 `STBoundary`，经 `GetUnblockSRange` 得 `s_upper`/`s_lower`，以 `s_upper_bound = fmin(...)` 装配后 `set_x_bounds`——印证稿件第 398、413、418 行「QP 在组装 $s_j^{ub,\mathrm{SBD}}$ 之后插一步取 min」结构上可行，式\eqref{eq:dual_source} 的双源取最小落点真实存在。
- `STDrivableBoundary` proto 结构：`st_drivable_boundary.proto` 的 `STDrivableBoundaryInstance` 含 `optional double t / s_lower / s_upper`——即逐 $t$ 一个 $s_{upper}$，恰好承载 MIKU 时变上界包络（式\eqref{eq:tighten_ub} 对 $t_j<\tau_k$ 收紧 $s_j^{ub}\leftarrow\min(\cdot,s_k)$）。稿件第 413 行「重建其内容、写入上界包络」与 proto 字段一一对应，非臆造。
- `IsWithinPathDeciderScopeObstacle` 函数体（`path_bounds_decider_util.cc`）：`if (!obstacle.IsStatic() || obstacle.speed() > FLAGS_static_obstacle_speed_threshold) return false;`，且其后紧跟 jiacheng 的 TODO 注释「等红灯/被堵的低速障碍物近期几乎必动」——印证稿件第 237 行「该过滤逻辑附近存在未完成的工程考虑，提示部分当前低速或静止的障碍物可能在短时间内重新运动」。**该旁注属实。**
- `lane_follow` pipeline task 链：`LaneChangePath → LaneFollowPath → LaneBorrowPath → FallbackPath → PathDecider → RuleBasedStopDecider → SpeedBoundsDecider(PRIORI) → PathTimeHeuristicOptimizer → SpeedDecider → SpeedBoundsDecider(FINAL) → PiecewiseJerkSpeedOptimizer`。无 `STBoundsDecider`，含 `LaneBorrowPath` 与 `FallbackPath`——印证第 413、797 行借道未启用与第 413 行 STBoundsDecider 缺席两处声称。
- `PiecewiseJerkPathOptimizer` 全树 0 命中，`PathOptimizerUtil`(17)/`PiecewiseJerkPathProblem`(4) 在册——印证第 149 行「已由独立 Task 重构、本文沿用历史 Task 名指代」。**历史名处置内部自洽。**
- ST 时间视野 `total_time: 7.0`、预测视野 `prediction_trajectory_time_length=6.0`、四个缓冲/阈值默认值，与稿件第 129、237、271、348 行逐字一致（round04 已核，本轮复核未回退）。
- `BuildMikuSTDrivableBoundary` 全树 0 命中，稿件第 413 行明示为 `LaneFollowPath` 新增逻辑、未冒充原生接口，诚实。

本轮**无 P0、无 major**。未发现臆造接口、伪造源码行为或在 11.0 生产代码中站不住的硬伤；类名一律驼峰、历史名均带版本注脚。剩余 4 条均为 minor 精度/一致性问题，全部「改文字能修」，不触数据红线。

- P0（致命）：0
- major（必改）：0
- minor（建议）：4

---

## P0（致命）

无。

## major（必改）

无。round04 唯一 major（pipeline 顺序）已确认修净，本轮未发现新的承重工程事实错。

---

## minor（建议）

### A-1【文风 / 一致性，3 轮遗留】摘要把 Apollo 匿名为「某生产级自动驾驶栈」，与标题、引言及全文显式具名 Apollo 11.0 自相矛盾

类别：文风 / Apollo 工程事实一致性。改文字能修。

定位：第 94 行（摘要）「MIKU 以增量方式接入**某生产级自动驾驶栈**的路径边界构建环节」。而全文其余处一律具名：标题与作者无碍，第 111 行「沿用 Apollo~11.0 原有的数据流」、第 585/592 行「Apollo 11.0 生产级代码」、第 833 行「在 Apollo 11.0 生产级代码上实现」、第 868 行「接入 Apollo 11.0 生产级 C++ 代码」。

说明：这是 round03 A-3、round04 A-3 连续两轮已记的遗留，本轮仍未动。摘要匿名而标题/正文/相关工作全部具名，是一处肉眼可见的内部不一致；对二区 Apollo 方向审稿人而言，摘要遮遮掩掩、正文又大方具名，反而显得作者对「在量产栈上落地」这一最强卖点不自信。本工作的核心竞争力恰是「在 Apollo 11.0 生产级代码上实现验证」（GOAL C 节单 insight 第 5 点），摘要理应同口径具名。

处置（改文字能修）：第 94 行「某生产级自动驾驶栈」改为「Apollo 11.0 生产级自动驾驶栈」（或「百度 Apollo 11.0」），与全文统一。若出于双盲投稿考虑而刻意匿名，则应全文一致匿名（连同第 111/585/592/833/868 行与相关工作的 `fan2018baidu`、`apollo2024` 引用一并处理），不能只匿名摘要一处。鉴于全文已大量具名且对照基线、pipeline、类名均显式依赖 Apollo，建议统一为具名。建议补入 MODIFICATIONS.md「⑥文风与格式」类。

### A-2【Apollo 工程事实】第 685 行「QP 求解提前中止于减速停车阶段……反映降级前的不完整计算」对 Apollo 降级行为的刻画偏离实际机制

类别：Apollo 工程事实。改文字能修。

定位：第 685 行「在压力场景 P1--P4 中 Baseline 进入 `FallbackPath` 降级分支，**QP 求解提前中止于减速停车阶段，记录的耗时反映降级前的不完整计算**，不构成两种算法的效率比较依据」。

源码事实：在 Apollo 11.0 中，路径阶段判 BLOCKED 后由 `TrimPathBounds` 截断、`FallbackPath`（`tasks/fallback_path/`）生成一条回退路径，随后速度链路（`SpeedBoundsDecider` → `PathTimeHeuristicOptimizer` → `SpeedDecider` → `PiecewiseJerkSpeedOptimizer`）**仍在该回退路径上完整运行至求解结束**，得到一条减速/停车速度剖面。即速度 QP 并非「提前中止」或「不完整计算」，而是在一个退化（短路径/停车）问题上跑完整流程。耗时不可比的真实原因是「两者求解的是不同规模/不同性质的问题（完整通行 vs 停车降级）」，而非「Baseline 的 QP 被中途打断」。

影响：不破坏结论（耗时不可比、效率结论仅取 C1--C4，这点正确且第 870 行结论节用的「进入 `FallbackPath` 停车降级拉低均值」措辞干净无误）。但「QP 提前中止/不完整计算」这一机制描述会被 Apollo 熟手识别为对降级路径下速度求解行为的误述。另注：本节实验取自 Python 复现程序（第 587 行），若「提前中止」是复现程序自身的建模简化，则应点明是复现口径而非 Apollo C++ 行为，避免读者把它当作 Apollo 原生机制。

处置（改文字能修，二选一）：
- (a) 改为「Baseline 在路径阶段判定阻塞后回退至 `FallbackPath` 停车，其速度求解针对的是一个降级停车问题，与 MIKU 在完整通行路径上的求解非同一规模，记录耗时不构成对等效率比较依据」；
- (b) 若确为复现程序行为，补一句「本复现程序在 Baseline 触发降级时于停车阶段终止速度求解记录」，明确是复现口径。
建议补入 MODIFICATIONS.md「②Apollo 工程事实」类。

### A-3【Apollo 工程事实】第 376/568 行把注入速度 QP 的「线性盒约束」归因为 `PathTimeHeuristicOptimizer + SpeedDecider`「所得」，略去真正产出盒约束的 `SpeedBoundsDecider`

类别：Apollo 工程事实（精度）。改文字能修。

定位：
- 第 376 行「这与 Baseline 经 `PathTimeHeuristicOptimizer` 在 ST 图上动态规划粗搜索、再由 `SpeedDecider` 标定 YIELD/OVERTAKE **所得的线性盒约束**在 QP 结构上一致」。
- 第 568 行「该盒式约束与 Baseline 经 `PathTimeHeuristicOptimizer` 动态规划粗搜索、再由 `SpeedDecider` 标定让行或超车**所得的线性约束**在二次规划结构上一致」。

源码事实：注入 `PiecewiseJerkSpeedOptimizer` 的 $s$ 盒约束实际由 **`SpeedBoundsDecider`（FINAL，pipeline pos 42）** 产出的 `st_boundaries` 经 `GetUnblockSRange` 转换而来（见 `piecewise_jerk_speed_optimizer.cc` 装配 `s_bounds` 处）。`PathTimeHeuristicOptimizer` 输出的是 ST 图上的粗速度引导剖面（DP guide），并不直接emit QP 盒约束；`SpeedDecider` 设置各障碍物 YIELD/OVERTAKE/STOP/FOLLOW 纵向决策，影响 FINAL `SpeedBoundsDecider` 把障碍物映射到 ST 边界的方向（压上界还是抬下界）。因此盒约束的产出方是 `SpeedBoundsDecider`，DP 与 `SpeedDecider` 只是塑形者。

影响：不破坏承重结论（MIKU 注入的也是逐时间步线性盒上界，与 Baseline 的盒约束同型、QP 目标矩阵/等式约束/稀疏模式不变——这一点成立且第 568 行下半句、第 415/422 行已正确指出与 `SpeedBoundsDecider` 取最小值融合）。仅是这一句把盒约束的产出链写得不够准，严格的 Apollo 审稿人会指出 DP 不产出 QP 盒约束。

处置（改文字能修）：把 376/568 两处的因果链补全或弱化，例如「与 Baseline 经 `PathTimeHeuristicOptimizer` 粗搜索、`SpeedDecider` 标定纵向决策、再由 `SpeedBoundsDecider` 映射为 ST 边界所得的线性盒约束在 QP 结构上一致」，或弱化为「与 Baseline 速度链路最终注入 QP 的线性盒约束（由 `SpeedBoundsDecider` 产出）在结构上一致」。不涉数据。建议补入 MODIFICATIONS.md「②Apollo 工程事实」类。

### A-4【Apollo 工程事实】第 348 行时变投影查询「未来 6 s 预测轨迹」与 planning 侧预测截断（`prediction_total_time=5.0`）及 ST 视野（7.0 s）三个时域并存，宜点明 τ(s) 实际查询的时域

类别：Apollo 工程事实（精度）。改文字能修。

定位：第 348 行「在 Prediction 模块给出的**未来 6 s 预测轨迹**中查询时刻 $\tau(s)$ 的位置并线性插值」。

源码事实：本机 Apollo 内同时存在三个时域参数——Prediction 模块 `prediction_trajectory_time_length=6.0`（预测轨迹长度，稿件引用值正确）、planning 侧 `prediction_total_time=5.0`（planning 对预测的消费/截断）、`SpeedBoundsDecider` ST 图 `total_time=7.0`（速度时域）。三者不一致。MIKU 的路径阶段时变投影查询 6 s 预测轨迹，而速度阶段 ST 视野 7 s、planning 对预测又有 5 s 截断，存在时域错配的潜在追问。

影响：不构成硬伤——稿件第 348 行已有「预测视野之外保守取最后预测位置不变」兜底，且 $\tau(s)$ 越界令 $+\infty$ 退回静态投影（第 346 行），边界处理完备。仅是未点明 path 阶段投影用的是哪一个时域，Apollo 审稿人可能追问「为何 path 投影用 6 s 而速度 ST 用 7 s、planning 又截 5 s」。

处置（改文字能修，可选）：在第 348 行补半句说明 τ(s) 投影以 Prediction 输出的 6 s 轨迹为源，超出部分按上句兜底，与速度阶段 7 s ST 视野的衔接由「越界保守延拓」处理；或直接保留现状（兜底已闭合逻辑），仅在审稿人追问时答复。鉴于已有兜底，本条优先级最低。建议记入 MODIFICATIONS.md「②Apollo 工程事实」类备查。

---

## 与前几轮的对照

- round01 三条 major（基线类名版本错配 / `STDrivableBoundary` 原生链路 / OSQP 过强断言）→ round02/03 修复，本轮再核仍成立，未回退。
- round02 两条 major（走廊产出方横跳 / `STDrivableBoundary`↔𝒯 接口）→ round03 修复，本轮第 413/424 行落点单一、QP 读取链路与 `st_drivable_boundary.proto` 字段及 `piecewise_jerk_speed_optimizer.cc` 装配逻辑自洽，未回退。
- round03 唯一 major（`PathBoundsDecider` 类名版本一致性）→ round04 确认修净，本轮复核全文无裸排活跃代码 `PathBoundsDecider`，首现处注脚在位，未回退。
- round04 唯一 major（`SpeedDecider`/`PathTimeHeuristicOptimizer` 顺序写反，两处）→ **本轮确认 v5 已修净**，376/568 两处顺序与 pipeline 一致。round04 四条 minor（A-2 裸排 `\texttt`、A-3 摘要匿名、A-4 STBoundsDecider 门控措辞、A-5 插件式扩展措辞）中，A-2/A-4/A-5 **已修净**，唯 A-3（摘要匿名）仍遗留，本轮降级续报为 A-1。
- 本轮新增 A-2（FallbackPath 降级下 QP 行为刻画）、A-3（盒约束产出链精度）、A-4（预测时域错配）三条 minor 为首次提出，均为精度性微调，不影响承重结论，全部改文字能修。

总体判断：v5 在 Apollo 工程事实维度已达到二区可投状态，承重集成声称（STDrivableBoundary 复用、PJ 取 min 注入、ReferenceLineInfo 数据总线、blocked-then-trim、IsStatic 过滤、借道未启用诚实披露）均经源码结构核实可立。剩余 4 条 minor 为措辞精度与摘要一致性，建议一并清掉以免末轮被同行挑刺，但均不构成投稿障碍。

SCORE: P0=0 major=0 minor=4
