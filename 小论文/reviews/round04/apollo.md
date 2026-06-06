# Round 04 审稿意见 — persona: Apollo 工程审

稿件 `drafts/v4.tex`，事实源 `~/Apollo`（Apollo 11.0 checkout，`modules/planning`）+ 毕设 `毕业论文/`。
本人只读不改稿。下列每条均已在 Apollo 11.0 源码树内核对，给出可定位的源码证据（类名/函数名/默认值/调用关系/pipeline 顺序）。

核查口径：本轮在 `~/Apollo/modules/planning` 下逐条 grep 复核了
`PathBoundsDeciderUtil`、`GetBufferBetweenADCCenterAndEdge`、`UpdatePathBoundaryBySLPolygon`、
`IsWithinPathDeciderScopeObstacle` / `IsStatic` / `TrimPathBounds`、
`obstacle_lat_buffer` / `static_obstacle_nudge_l_buffer` / `nonstatic_obstacle_nudge_l_buffer` /
`static_obstacle_speed_threshold`、`LaneFollowPath`、`PiecewiseJerkSpeedOptimizer`（s 界来源）、
`SpeedBoundsDecider`（`total_time`）、`STBoundsDecider` / `SetSTDrivableBoundary` / `use_st_drivable_boundary`、
`StGraphData`（`ReferenceLineInfo` 归属）、`gridded_path_time_graph` / `dp_st_cost`（DP 消费 + flag 门控）、
`scenarios/lane_follow/conf/pipeline.pb.txt`（task 顺序）、`prediction_trajectory_time_length`、`BuildMikuSTDrivableBoundary`。

---

## 总评

v4 把 round03 的唯一 major（A-1，`PathBoundsDecider` 类名在 11.0 不作活跃代码主体）**真改掉了**，非幻觉式处置，源码逐项复核通过：

- round03 A-1 → v4 全文已无任何裸排活跃代码 `PathBoundsDecider`（grep `PathBoundsDecider[^U]` 去 footnote 后零命中）。第 149 行首次出现处补了版本注脚「该环节在 Apollo 11.0 中由 `PathBoundsDeciderUtil` 的静态方法承载，本文沿用历史 Task 名指代」，第 237、302 行的 `GetBufferBetweenADCCenterAndEdge` / `UpdatePathBoundaryBySLPolygon` 已统一挂到 `PathBoundsDeciderUtil`。**已解决。**
- round03 A-4 → v4 第 237 行已补「此处的速度二分缓冲由 `static_/nonstatic_obstacle_nudge_l_buffer` 控制，与前述 `obstacle_lat_buffer` 分属不同参数、走不同代码路径」。**已解决。**

本轮可核查的硬事实全部对得上，逐条记录如下，供整合编辑放心：

- `IsWithinPathDeciderScopeObstacle`：`path_bounds_decider_util.cc:686-688`，体为 `if (!obstacle.IsStatic() || obstacle.speed() > FLAGS_static_obstacle_speed_threshold) return false;`，即非静态或速度超阈值的障碍物被排除于路径决策——与稿件第 149、237、475、615 行「`IsStatic` 过滤把动态障碍物排除、转交速度阶段」逐字相符。
- 缓冲默认值：`obstacle_lat_buffer=0.4`（`planning_gflags.cc:175`）、`static_obstacle_nudge_l_buffer=0.3`、`nonstatic_obstacle_nudge_l_buffer=0.4`（`:138/140`）、`static_obstacle_speed_threshold=0.5`（`:186`）。与稿件第 129、237 行四个数值全部一致。
- `GetBufferBetweenADCCenterAndEdge` 体为 `adc_half_width + FLAGS_obstacle_lat_buffer`（`path_bounds_decider_util.cc:671`），稿件第 129、237 行「半车宽再加固定额外缓冲」相符。
- `TrimPathBounds`（`path_bounds_decider_util.{h,cc}`）+ `FallbackPath`（`tasks/fallback_path/`）：blocked-then-trim 机制属实，稿件第 196、302、424、489、685 行表述与源码一致。
- ST 时间视野：`SpeedBoundsDecider` 默认 `total_time: 7.0`（`tasks/speed_bounds_decider/conf/default_conf.pb.txt:1` 与 `proto:9`），印证稿件第 271 行「$T_{max}=7.0$\,s 与 Apollo ST 图时间视野一致」。**该断言属实。**
- 预测视野：`prediction_trajectory_time_length=6.0`（`prediction/common/prediction_gflags.cc:24`），印证稿件第 348 行「未来 6\,s 预测轨迹」。**属实。**
- 速度 QP 的 s 界来源：`piecewise_jerk_speed_optimizer.cc:70/98` 从 `reference_line_info_->mutable_st_graph_data()` 取 `st_graph_data.st_boundaries()` 组装 `s_bounds`，再 `set_x_bounds`——印证稿件第 398、413、415 行「QP 在组装 $s_j^{ub,\mathrm{SBD}}$ 之后插一步取 min」在结构上可行。
- `STDrivableBoundary` 归属：`StGraphData::st_drivable_boundary_`（`st_graph_data.h:85`）、`SetSTDrivableBoundary`（`:67`），`StGraphData st_graph_data_` 为 `ReferenceLineInfo` 成员（`reference_line_info.h:392`）——印证稿件第 413、424 行「挂载于 `ReferenceLineInfo` 随数据总线传至速度阶段」。
- `STDrivableBoundary` 消费方：全树仅 `gridded_path_time_graph.cc:78` 与 `dp_st_cost.cc` 读取，`PiecewiseJerkSpeedOptimizer` 不读取（grep `drivable` 在 PJ speed 目录零命中）——印证稿件第 413 行「速度二次规划本身并不读取它，本文重新利用」。**核心声称属实。**
- `BuildMikuSTDrivableBoundary` 全树零命中，属本组 fork，稿件第 413 行明示为新增逻辑、未冒充原生接口，诚实。

本轮无 P0，无臆造接口、无伪造源码行为。新发现一条 major：稿件两处把 Baseline 速度链路的 task 执行顺序写反（`SpeedDecider` 与 `PathTimeHeuristicOptimizer` 先后颠倒），与 `lane_follow` pipeline 实际顺序不符，属可被 Apollo 熟手当场识破的事实错。其余为 minor，含两条 round03 遗留。全部「改文字能修」，不触数据红线。

- P0（致命）：0
- major（必改）：1
- minor（建议）：4

---

## P0（致命）

无。未发现臆造接口、伪造源码行为或在 11.0 生产代码中站不住的硬伤。

---

## major（必改）

### A-1【Apollo 工程事实】把 `SpeedDecider` 与 `PathTimeHeuristicOptimizer` 的执行先后写反，与 `lane_follow` pipeline 实际顺序矛盾（出现两处）

类别：Apollo 工程事实。可定位、可执行。改文字能修，不触数据红线。

定位：
- 第 568 行：「该盒式约束与 Baseline 经 `SpeedDecider` 标定让行或超车、再由 `PathTimeHeuristicOptimizer` 动态规划搜索所得的线性约束在二次规划结构上一致」。
- 第 376 行：同型表述「经 `SpeedDecider` 标定 YIELD/OVERTAKE、再由 `PathTimeHeuristicOptimizer` 动态规划搜索所得的线性盒约束」。

源码事实：`scenarios/lane_follow/conf/pipeline.pb.txt` 内 task 顺序为
`SpeedBoundsDecider`（SPEED_BOUNDS_PRIORI_DECIDER，pos 30）→ `PathTimeHeuristicOptimizer`（SPEED_HEURISTIC_OPTIMIZER，pos 34）→ `SpeedDecider`（SPEED_DECIDER，pos 38）→ `SpeedBoundsDecider`（SPEED_BOUNDS_FINAL_DECIDER，pos 42）→ `PiecewiseJerkSpeedOptimizer`（pos 46）。即 **DP 启发式搜索在前、`SpeedDecider` 标定让行/超车在后**。语义上也如此：`PathTimeHeuristicOptimizer` 先用 DP 在 ST 图上搜出粗速度剖面，`SpeedDecider` 再依据该剖面给各障碍物打 YIELD/OVERTAKE/STOP/FOLLOW 标签。稿件「先 `SpeedDecider`、再 DP」正好倒置。

影响：该句是解释「Baseline 的线性盒约束如何产生」的类比，不构成 MIKU 注入逻辑的承重论证，但它是一个完全可验证的 Apollo pipeline 事实错，二区 Apollo 方向审稿人一眼可见，按 SPEC E 节忠实红线必须修。

处置（改文字能修，二选一）：
- (a) 调换语序，改为「Baseline 经 `PathTimeHeuristicOptimizer` 动态规划粗搜索、再由 `SpeedDecider` 标定让行或超车所得的线性约束」；
- (b) 弱化为不带先后的并列，「Baseline 经 ST 启发式动态规划与让行/超车标定所得的线性盒约束」，回避顺序声称。
两处（376、568）需一并改。建议补入 MODIFICATIONS.md「②Apollo 工程事实」类。

---

## minor（建议）

### A-2【文风 / Apollo 工程事实】裸排 `STDrivableBoundary`（未加 `\texttt`）仍残留四处，round03 A-2 第四轮遗留

类别：文风。改文字能修。

定位：第 109 行（引言正文）「再经 STDrivableBoundary 注入速度 QP」；第 230 行（图注）「经 STDrivableBoundary 注入速度 QP」；**第 395 行（子节标题）「经 STDrivableBoundary 注入速度二次规划」**；第 566 行（理论节正文）「并经 STDrivableBoundary 以收紧上界的方式注入」。其余绝大多数处（第 413、424、577 等）已统一 `\texttt{STDrivableBoundary}`。

说明：`LaneFollowPath`、`PiecewiseJerkPathOptimizer`、`PathBoundsDeciderUtil` 等其余类名在正文已无裸排（本轮 grep 复核），唯 `STDrivableBoundary` 仍同稿混排，最扎眼的是子节标题第 395 行与理论节第 566 行。这是 round01 A-8 → round02 A-3 → round03 A-2 的第四轮遗留。

处置：约定「正文与子节标题类名统一 `\texttt`」，重点清第 395、566 两处正文位（子节标题与理论正文），第 230 图注、第 109 引言一并清。纯格式，不涉事实。建议本轮一次清净，勿再带入 round05。

### A-3【叙事 / Apollo 工程事实】摘要「某生产级自动驾驶栈」与正文通篇 Apollo 11.0 的匿名口径仍自相矛盾，round03 A-3 未处理

类别：叙事。改文字能修。

定位：摘要第 94 行「MIKU 以增量方式接入**某生产级自动驾驶栈**的路径边界构建环节」；而标题页第 86 行署单位、引言第 103/111 行及方法/理论/实验各节均直书 `Apollo 11.0`、`Apollo EM Planner` 与具体类名。

说明：正文已大面积暴露 Apollo 与类名，摘要单独半匿名既无效也不一致，Apollo 熟手一眼能识别，反显刻意。本条 round03 已提，v4 未动。

处置（改文字能修）：与目标期刊投稿策略对齐——若非双盲（RAS/JIRS 多为单盲），摘要第 94 行「某生产级自动驾驶栈」直接改「Apollo 11.0 生产级自动驾驶栈」，与正文统一。建议此选项。不涉源码事实。

### A-4【Apollo 工程事实】第 413 行「`STDrivableBoundary` 由 `STBoundsDecider` 生产、默认仅在动态规划启发式搜索阶段被消费」表述不够精确，可进一步收紧反而更利己

类别：Apollo 工程事实。改文字能修。

定位：第 413 行「该结构在原生 Apollo 中由 `STBoundsDecider` 生产、并默认仅在动态规划启发式搜索阶段被消费，速度二次规划本身并不读取它」。

源码事实：
1. DP 对该结构的消费受 `FLAGS_use_st_drivable_boundary` 门控，而该 flag **默认 false**（`planning_gflags.cc:377`，`planning.conf:32` 亦 `=false`），见 `gridded_path_time_graph.cc:52`（`if (FLAGS_use_st_drivable_boundary) return false;`）与 `dp_st_cost.cc:119`。即**默认配置下连 DP 也不消费它**，「默认仅在 DP 阶段被消费」措辞偏强，准确说是「默认根本不被消费，仅在打开该 flag 时由 DP 消费」。
2. 更关键的是，MIKU 实际接入的 `lane_follow` pipeline（`LaneFollowPath` 所在）**根本不含 `STBoundsDecider`**（其 task 链为 `SpeedBoundsDecider`×2 + `PathTimeHeuristicOptimizer` + `SpeedDecider` + `PiecewiseJerkSpeedOptimizer`，无 `STBoundsDecider`）。因此在 MIKU 的工作 pipeline 里该结构既非由 `STBoundsDecider` 生产、默认也无人消费，是一块彻底闲置的空结构。

影响：这两点都不削弱 MIKU 的核心声称，反而**强化**「重新利用既有闲置数据结构、不与原生消费方冲突」的论证。当前措辞却给了 Apollo 熟手一个「`STBoundsDecider` 不在 lane_follow 链上，作者是不是没跑通」的误读口子。

处置（改文字能修）：第 413 行收紧为「该结构在原生 Apollo 中由 `STBoundsDecider` 在含其的 pipeline 中生产，且其下游消费受 `use_st_drivable_boundary` 开关门控、默认关闭；在本文接入的 `LaneFollowPath` 路径 pipeline 中该结构本就闲置，故重新利用它不与任何原生消费方冲突」。事实不动，只把闲置性说足。

### A-5【Apollo 工程事实 / 叙事】第 424 行「符合 Apollo 的插件式扩展规范」措辞略过，实为对两个既有 Task 插件的内部改写而非新增插件

类别：Apollo 工程事实。改文字能修。

定位：第 424 行「改动范围限于两处，`LaneFollowPath` 的路径边界构建新增时变 SL 投影与 `STDrivableBoundary` 重建，`PiecewiseJerkSpeedOptimizer` 新增对该上界包络的读入与取最小值……符合 Apollo 的插件式扩展规范」。

说明：Apollo 的插件式扩展（plugin + `plugins.xml` 注册机制）指**新增一个 Task 插件、不改动既有插件源码**即可挂入 pipeline。而 MIKU 是改写 `LaneFollowPath` 与 `PiecewiseJerkSpeedOptimizer` 这两个既有插件的内部实现（`BuildMikuSTDrivableBoundary` 是注入进 `LaneFollowPath`、QP 取 min 是注入进 `PiecewiseJerkSpeedOptimizer`），属于 fork 既有插件而非新增插件。称「符合插件式扩展规范」是轻微夸张。「改动范围限于两处」「下游求解器内部结构不变」本身诚实可保留。

处置（改文字能修）：把「符合 Apollo 的插件式扩展规范」改为「改动局部化于两个既有 Task 内部，不触及求解器（OSQP）内部数据结构与求解流程，亦不新增对外接口」之类的事实陈述，避免对 plugin 机制的归类性声称。不涉数据。

---

## 与前几轮的对照

- round01 三条 major（A-1 基线类名版本错配、A-2 `STDrivableBoundary` 原生链路、A-9 OSQP 过强断言）→ round02/03 已确认修复，本轮再核仍成立，未回退。
- round02 两条 major（走廊产出方横跳、`STDrivableBoundary`↔𝒯 接口说不清）→ round03 确认修复，本轮第 413/424 行落点单一、QP 读 `STDrivableBoundary` 取 min 的链路与源码自洽，未回退。
- round03 唯一 major（A-1，`PathBoundsDecider` 类名版本一致性）→ **本轮确认 v4 已修净**，全文无裸排活跃代码 `PathBoundsDecider`，首现处加注脚、Util 方法归属正确。round03 minor A-4（nudge 参数归属）亦确认已修（第 237 行）。
- round03 两条 minor 仍遗留并入本轮：A-2（`\texttt`/裸排，本轮 → A-2，第四轮）、A-3（摘要匿名口径，本轮 → A-3，第二轮未动）。
- 本轮新 major A-1（pipeline 顺序写反）为首次发现，与既往「类名版本一致性」线无关，属 task 执行顺序事实错。
- 本轮新 minor A-4/A-5 为首次发现，均为「越收紧越利己」的精确性问题，不削弱核心声称。

数据红线核对：本轮所有意见均为「改文字能修」，无一条需新实验或改数字。通过率（压力 0/4 vs 4/4、汇总 4/8 vs 8/8）、平均速度（汇总 3.53→4.57 提升 29.3%、压力 2.58→4.66、可比 4.48→4.47）、QP 耗时（可比 19.16→6.26、汇总 21.56→5.56、C2 离群 56.41 vs 3.17、C1 反慢 10.44 vs 12.53、C3 4.11/3.75、C4 5.68/5.58）、消融（M5=100、M4=99.18、M2=37.13、M3=34.50、M1=25.29、M0=0）、灵敏度（最坏翻转 57%、最大偏差 6.4%、越界 0）均与 SPEC B 节冻结值逐字一致，未见外推或美化。Apollo 参数事实（0.3/0.4/0.4/0.5、ST 7.0s、预测 6.0s、`use_st_drivable_boundary=false`）均经本轮源码复核属实。

---

SCORE: P0=0 major=1 minor=4
