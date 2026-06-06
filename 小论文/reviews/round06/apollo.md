# Round 06 审稿意见 — persona: Apollo 工程审

稿件 `drafts/v6.tex`，事实源 `~/Apollo`（Apollo 11.0 checkout，`modules/planning`）+ 毕设 `毕业论文/`。
本人只读不改稿。下列每条均已在 Apollo 11.0 源码树内逐项 grep 复核，给出可定位的源码证据（类名/函数名/默认值/调用关系/pipeline 顺序）。

核查口径（本轮在 `~/Apollo/modules/planning` 下复核）：
`path_bounds_decider_util.{h,cc}`：`IsWithinPathDeciderScopeObstacle`（函数体 `if (!obstacle.IsStatic() || obstacle.speed() > FLAGS_static_obstacle_speed_threshold) return false;`）、
`GetBufferBetweenADCCenterAndEdge`（`adc_half_width + FLAGS_obstacle_lat_buffer`）、`TrimPathBounds`、`UpdatePathBoundaryBySLPolygon`（`LEFT_NUDGE`/`RIGHT_NUDGE`）；
gflags 默认值 `obstacle_lat_buffer=0.4`、`static_obstacle_nudge_l_buffer=0.3`、`nonstatic_obstacle_nudge_l_buffer=0.4`、`use_st_drivable_boundary=false`、`prediction_total_time=5.0`；
`prediction_gflags.cc` `prediction_trajectory_time_length=6.0`；`speed_bounds_decider` proto `total_time` 默认 `7.0`；
`piecewise_jerk_speed_optimizer.cc`（s 上界装配 = `st_graph_data.st_boundaries()` 经 `GetUnblockSRange` 得 `s_upper`、`std::fmin` 收紧后 `set_x_bounds`，且全文件零 `drivable_boundary` 读取）；
`st_drivable_boundary.proto`（`STDrivableBoundaryInstance{t, s_lower, s_upper, v_obs_lower, v_obs_upper}`）；
`st_graph_data.{h,cc}`（`st_drivable_boundary_` 为 `StGraphData` 成员、`SetSTDrivableBoundary` 以 `add_st_boundary()` 追加、`LoadData` 不清空该字段）；
`reference_line_info.h`（`StGraphData st_graph_data_;` 为成员，经 `mutable_st_graph_data()` 暴露）；
`scenarios/lane_follow/conf/pipeline.pb.txt`（task 链 `LaneChangePath→LaneFollowPath→LaneBorrowPath→FallbackPath→PathDecider→RuleBasedStopDecider→SpeedBoundsDecider(PRIORI)→PathTimeHeuristicOptimizer→SpeedDecider→SpeedBoundsDecider(FINAL)→PiecewiseJerkSpeedOptimizer`，零 `STBoundsDecider`）；
`tasks/st_bounds_decider/`（真实 Task、`st_bounds_decider.cc:73` 调 `SetSTDrivableBoundary`、仅出现在 `park_and_go`/`traffic_light_*`/`pull_over` pipeline）；
`lane_follow_path.cc`（`OptimizePath` 调 `PathBoundsDeciderUtil::*` 构边界、`PathOptimizerUtil::*` 求解）；
`PiecewiseJerkPathOptimizer` 全树 0 命中、`PathOptimizerUtil`/`PiecewiseJerkPathProblem` 在册、`BuildMikuSTDrivableBoundary`/`Miku` 全树 0 命中。

---

## 总评

v6 把 round05 全部 4 条 minor（A-1 摘要匿名、A-2 FallbackPath 降级下 QP 行为误述、A-3 盒约束产出链略去 SpeedBoundsDecider、A-4 预测时域错配）**逐条真改掉了**，非幻觉式处置，源码与稿件逐项复核通过：

- round05 A-1 → v6 第 94 行摘要已具名「MIKU 以增量方式接入 Apollo 11.0 生产级自动驾驶栈的路径边界构建环节」，与标题、引言（111）、实验（592）、相关工作（833）、结论（868）全文同口径具名，连续四轮遗留的摘要匿名内部矛盾**已消除**。
- round05 A-2 → v6 第 685 行已改为「Baseline 路径阶段判定阻塞后回退至 `FallbackPath` 停车，其速度求解针对的是一个短路径或停车的降级问题，与 MIKU 在完整通行路径上的求解非同一规模」，去掉了「QP 提前中止/不完整计算」这一对 11.0 降级机制的误述（11.0 中速度链路在回退路径上跑完整流程）。**已解决。**
- round05 A-3 → v6 第 376 行已补「`SpeedDecider` 标定 YIELD/OVERTAKE 纵向决策、再由 `SpeedBoundsDecider` 映射为 $ST$ 边界所得的线性盒约束」，第 568 行同步补「`SpeedDecider` 标定让行或超车、再由 `SpeedBoundsDecider` 产出的线性约束」。盒约束的真实产出方 `SpeedBoundsDecider` 已补入因果链。**已解决。**
- round05 A-4 → v6 第 348 行已补「路径阶段时变投影以 Prediction 输出的 $6$\,s 预测轨迹为源……其与速度阶段 $7$\,s ST 视野的衔接由该越界保守延拓处理」，6 s/7 s 两时域衔接已点明。**已解决。**

本轮所有承重工程事实再次逐项核对，全部对得上，承重集成声称均经源码结构验证可行：

- **IsStatic 过滤**：`IsWithinPathDeciderScopeObstacle` 函数体 `!IsStatic() || speed() > FLAGS_static_obstacle_speed_threshold`，印证第 237/348/475/615 行「动态障碍物经 IsStatic 过滤排除于路径决策、转交速度阶段」。属实。
- **统一缓冲与 nudge 二分**：`GetBufferBetweenADCCenterAndEdge` 返回 `adc_half_width + FLAGS_obstacle_lat_buffer`（=半车宽+0.4）；`static_obstacle_nudge_l_buffer=0.3`、`nonstatic_obstacle_nudge_l_buffer=0.4` 为独立参数。印证第 129/237 行的缓冲粒度与三参数取值。属实。
- **blocked-then-trim**：`UpdatePathBoundaryBySLPolygon` 逐障碍物置 `LEFT_NUDGE`/`RIGHT_NUDGE`，`l^{+}<l^{-}` 后 `TrimPathBounds` 截断。印证第 196/237/302/424/486 行 blocked-then-trim 与 FallbackPath 触发链。属实。
- **速度 QP s 界装配**：`piecewise_jerk_speed_optimizer.cc` 从 `st_graph_data.st_boundaries()` 经 `GetUnblockSRange` 得 `s_upper`、以 `std::fmin` 收紧后 `set_x_bounds`，印证第 398/413/418 行「QP 组装 $s_j^{ub,\mathrm{SBD}}$ 之后插一步取 min」与式 dual_source 的双源取最小落点。属实。
- **STDrivableBoundary proto**：`STDrivableBoundaryInstance{t,s_lower,s_upper,v_obs_lower,v_obs_upper}`，逐 $t$ 一个 $s_{upper}$，恰承载 MIKU 时变上界包络（式 tighten_ub）。第 413 行字段对应一致。属实。
- **pipeline 与 STBoundsDecider 缺席**：lane_follow task 链零 `STBoundsDecider`、含 `LaneBorrowPath`+`FallbackPath`，DP→SpeedDecider→SpeedBoundsDecider(FINAL)→PiecewiseJerkSpeedOptimizer 顺序与第 376/413/568/797 行一致。属实。
- **闲置性**：`PiecewiseJerkSpeedOptimizer` 全文件零 `drivable_boundary` 读取、`use_st_drivable_boundary` 默认 false、lane_follow 无 STBoundsDecider，三者共同支撑第 413 行「该结构本就闲置、速度二次规划亦不读取它，本文重新利用」。属实，闲置说足。
- **STBoundsDecider 真实存在**：`tasks/st_bounds_decider/` 为独立 Task，`st_bounds_decider.cc:73` 调 `SetSTDrivableBoundary`，仅出现在 park_and_go/traffic_light/pull_over pipeline，印证第 413 行「由 STBoundsDecider 在含其的 pipeline 中生产、本文接入的 LaneFollowPath pipeline 并不含它」。属实。
- **历史名/新增名**：`PiecewiseJerkPathOptimizer` 全树 0 命中（第 111/149/828 行均带历史名注脚）、`BuildMikuSTDrivableBoundary` 全树 0 命中（第 413 行明示 MIKU 新增逻辑、未冒充原生接口）。诚实，无臆造接口。
- **路径 QP 求解链**：`lane_follow_path.cc` `OptimizePath` 实调 `PathBoundsDeciderUtil::*`+`PathOptimizerUtil::*`+底层 `PiecewiseJerkPathProblem`，印证第 149/424 行接入点。属实。

本轮**无 P0、无 major**。未发现臆造接口、伪造源码行为或在 11.0 生产代码中站不住的承重硬伤；类名一律驼峰、历史名均带版本注脚。新增 3 条 minor 均为「改文字能修」的精度/完备性问题，不触数据红线。另登记 2 项受数据红线挡住、需新实验方能坐实的集成验证缺口（非本轮稿改对象）。

- P0（致命）：0
- major（必改）：0
- minor（建议）：3

---

## P0（致命）

无。

## major（必改）

无。round05 唯一可疑面（摘要匿名连续遗留）已于 v6 修净，本轮未发现新的承重工程事实错。

---

## minor（建议）

### A-1【Apollo 工程事实，精度】第 413 行「挂载于 ReferenceLineInfo 上下文」对 STDrivableBoundary 的实际容器层级表述偏粗

类别：Apollo 工程事实（精度）。改文字能修。

定位：第 413 行「由 `LaneFollowPath` 的 `BuildMikuSTDrivableBoundary` 依据路径阶段的时变投影重建其内容，**挂载于 `ReferenceLineInfo` 上下文随数据总线传至速度阶段**」；第 424 行同义复述「写入挂载于 `ReferenceLineInfo` 的 `STDrivableBoundary`」。

源码事实：`STDrivableBoundary` 在 11.0 中并非直接挂在 `ReferenceLineInfo` 顶层，而是 `StGraphData` 的成员字段 `st_drivable_boundary_`（`st_graph_data.h:85`），由 `StGraphData::SetSTDrivableBoundary`（`st_graph_data.cc:73`）写入；`StGraphData` 又是 `ReferenceLineInfo` 的成员 `st_graph_data_`（`reference_line_info.h:392`），经 `mutable_st_graph_data()`（`reference_line_info.h:234`）暴露。即精确容器层级为 `ReferenceLineInfo::st_graph_data_::st_drivable_boundary_`。

影响：不破坏结论——`ReferenceLineInfo` 确为跨 Task 的数据总线，`StGraphData` 为其成员，故「随数据总线传至速度阶段」substantively 正确，方向无误。仅是「挂载于 ReferenceLineInfo」略过了中间的 `StGraphData` 这一层，严格的 Apollo 审稿人会指出写入实经 `mutable_st_graph_data()->SetSTDrivableBoundary` 而非 `ReferenceLineInfo` 直接字段。

处置（改文字能修）：将「挂载于 `ReferenceLineInfo` 上下文」收紧为「写入 `ReferenceLineInfo` 持有的 `StGraphData` 的 `STDrivableBoundary` 字段（经 `mutable_st_graph_data()`）」，或简述为「挂载于 `ReferenceLineInfo` 的 `StGraphData` 上随数据总线传递」。不涉数据。建议补入 MODIFICATIONS.md「②Apollo 工程事实」类。

### A-2【Apollo 工程事实，完备性】跨阶段持久性这一关键前提未点明——StGraphData::LoadData（由 SpeedBoundsDecider FINAL 在 LaneFollowPath 之后运行）不清空 st_drivable_boundary_，正是路径阶段写入能存活到速度阶段的机制

类别：Apollo 工程事实（完备性，承重声称的隐含前提）。改文字能修。

定位：第 413/424 行声称 MIKU 在路径阶段（`LaneFollowPath`，pipeline pos 10）由 `BuildMikuSTDrivableBoundary` 写入 `STDrivableBoundary`，到速度阶段（`PiecewiseJerkSpeedOptimizer`，pos 47）由其读入收紧上界。

源码事实（构成隐含前提的关键链）：在 lane_follow pipeline 中，`SpeedBoundsDecider`（PRIORI pos 30、FINAL pos 42）位于 `LaneFollowPath`（pos 10）**之后**，且 `SpeedBoundsDecider` 会调用 `StGraphData::LoadData`（`speed_bounds_decider.cc:125`）重新装配 ST 图。核查 `LoadData` 函数体（`st_graph_data.cc:30` 起）：它置 `init_=true` 并重填 `st_boundaries_`、`min_s_on_st_boundaries_`、`init_point_` 等，**但不触碰 `st_drivable_boundary_`**；而 `SetSTDrivableBoundary` 以 `add_st_boundary()` 追加（`st_graph_data.cc:51`）而非先清空。因此路径阶段写入的 `STDrivableBoundary` 内容能存活过 pos 42 的 `LoadData` 而抵达 pos 47 的速度 QP——这正是 v6 跨阶段数据总线声称得以成立的底层机制，且因 lane_follow 无 `STBoundsDecider`、无原生 `SetSTDrivableBoundary` 调用，不存在与 MIKU 写入的双重追加冲突，每周期新建 `ReferenceLineInfo` 又保证 `st_drivable_boundary_` 起始为空。

影响：不破坏结论，反而**支撑**第 413/424 行（机制核实为真）。但 v6 把这一非平凡的持久性前提当作不言自明，一个挑剔的 11.0 审稿人首问即是「`SpeedBoundsDecider` 在 `LaneFollowPath` 之后运行并 `LoadData`，难道不会把路径阶段写的 `STDrivableBoundary` 冲掉？」稿中目前无一句回应。补一句把「`LoadData` 不清空该字段、故路径阶段写入存活至速度阶段」点明，可把这条最具技巧性的集成声称从「读者需自行查证」升级为「作者已交代清楚」。

处置（改文字能修）：在第 413 行末或第 424 行补半句，例如「`SpeedBoundsDecider` 后续重建 ST 图时仅刷新 ST 边界而不清空该 `STDrivableBoundary` 字段，故路径阶段的写入得以存活至速度阶段被读取」。不涉数据。建议补入 MODIFICATIONS.md「②Apollo 工程事实」类（优先级高于 A-1，因其是承重声称的前提交代）。

### A-3【Apollo 工程事实，精度，可选】lane_follow 中 SpeedBoundsDecider 运行两次（PRIORI/FINAL），注入速度 QP 的盒约束来自 FINAL，正文多处以「SpeedBoundsDecider」泛指未点明

类别：Apollo 工程事实（精度）。改文字能修。优先级最低。

定位：第 398 行「`SpeedBoundsDecider` 给出的 ST 边界 $s_j^{lb,\mathrm{SBD}} \leq s_j \leq s_j^{ub,\mathrm{SBD}}$」、第 415/418/422 行双源融合处的 `SpeedBoundsDecider` 均为泛指。

源码事实：lane_follow pipeline 含两次 `SpeedBoundsDecider`——`SPEED_BOUNDS_PRIORI_DECIDER`（pos 30，DP 之前）与 `SPEED_BOUNDS_FINAL_DECIDER`（pos 42，`SpeedDecider` 之后）。真正装配进 `PiecewiseJerkSpeedOptimizer` s 盒约束的是 FINAL 的输出（其 `LoadData` 是最后一次 ST 图重建）。

影响：基本不影响——第 376/568 行的链式描述「DP→SpeedDecider→SpeedBoundsDecider」因把 `SpeedBoundsDecider` 列在 `SpeedDecider` 之后，已隐含指向 FINAL，substantively 正确。仅式 dual_source 邻近（398/415/422）的泛指略欠精确。极挑剔的审稿人或追问「双源取最小是对 PRIORI 还是 FINAL」。

处置（改文字能修，可选）：在双源融合首现处（约第 415 行）补一处脚注或半句「此处 `SpeedBoundsDecider` 指 pipeline 末次（FINAL）调用所产 ST 边界」。鉴于链式描述已隐含 FINAL，本条可并入 A-1/A-2 一并处理或保留现状，优先级最低。建议记入 MODIFICATIONS.md「②Apollo 工程事实」类备查。

---

## 受数据红线挡住、需新实验方能坐实的集成验证缺口（仅登记，非本轮稿改对象）

以下两项不是文字问题，而是「C++ 集成声称结构上成立、但缺乏数据层面的运行验证」。v6 已在局限节做了诚实框定，文字防御到位，本轮不动稿，仅作为 Apollo 工程审视角的待补项登记，供 MODIFICATIONS.md「⑧需新实验」类核对。

1. **走廊注入组件未被任何场景激活（M4≈M5）→ 时间通道这一标题级 insight 的注入侧未获数据验证。** 本轮已结构性核实注入链全部成立：proto 字段在册、`PiecewiseJerkSpeedOptimizer` 可在 `set_x_bounds` 前插一步 `fmin`、`STDrivableBoundary` 跨阶段持久（见 A-2）、lane_follow 中该结构闲置可被复用。但第 779/805 行如实承认 4 个压力场景均未触发活跃时间窗约束，第 768 行 M4（关闭走廊注入）=99.18 与 M5=100 仅差 0.82。即：**集成通路验证为可接入，但注入的走廊约束从未在数据上被实际行使过**。从 Apollo 工程验证的完备性看，这是全文最大的「声称已实现、但未在数据上跑通生效」缺口。需补能触发活跃时间窗约束的动态冲突密集场景。自 round03 即登记，仍遗留。需新实验。

2. **全部耗时取自 Python 复现、无 Apollo C++ 生产运行时计时。** 「计算代价几乎不增加」「满足 100\,ms 周期」（第 111/457/559/723 行）依据的是复杂度 $O(n\log n+K)$ 加桌面 Python 实测，而非 Apollo C++ 运行时墙钟。集成的**结构可行性**已验证（改动局部于两 Task、不触求解器内部、不增约束行数），但**集成后的真实运行时开销**未在 C++ 栈上测量。v6 第 723 行已明确标注「为同一套 Python 复现程序内的同程序对比……非 Apollo C++ 生产运行时的绝对耗时」、第 559 行「车载嵌入式平台实时性须另行评估，本工作不就此外推」，框定充分、无需稿改。仅作完备性登记：C++ 集成的性能闭环需后续在 Apollo 运行时补测。需新实验。

---

## 与前几轮的对照

- round01 三条 major（基线类名版本错配 / `STDrivableBoundary` 原生链路 / OSQP 过强断言）→ round02/03 修复，本轮再核仍成立，未回退。
- round02 两条 major（走廊产出方横跳 / `STDrivableBoundary`↔𝒯 接口）→ round03 修复，本轮第 413/424 行落点单一、QP 读取链与 proto 字段及装配逻辑自洽，未回退。
- round03 唯一 major（`PathBoundsDecider` 类名版本一致性）→ round04 修净，本轮全文无裸排活跃代码 `PathBoundsDecider`，首现注脚在位，未回退。
- round04 唯一 major（`SpeedDecider`/`PathTimeHeuristicOptimizer` 顺序写反）→ round05 修净，本轮 376/568 顺序与 pipeline 一致，未回退。
- round05 四条 minor（A-1 摘要匿名、A-2 FallbackPath 降级 QP 行为、A-3 盒约束产出链、A-4 预测时域错配）→ **本轮确认 v6 全部修净**，无一遗留。这是 Apollo 视角连续多轮以来首次「上一轮 minor 清零」。
- 本轮新增 A-1（STDrivableBoundary 容器层级）、A-2（跨阶段持久性前提未点明）、A-3（SpeedBoundsDecider PRIORI/FINAL 二次运行）三条 minor 均为首次提出，皆精度/完备性微调，不影响承重结论，全部改文字能修。

总体判断：v6 在 Apollo 工程事实维度已稳定达到二区可投状态，承重集成声称（STDrivableBoundary 复用、PJ 取 min 注入、ReferenceLineInfo/StGraphData 数据总线、blocked-then-trim、IsStatic 过滤、借道未启用诚实披露、历史名注脚）均经 11.0 源码结构核实可立，且本轮新查的跨阶段持久性机制（LoadData 不清空 st_drivable_boundary_）进一步坐实了 v6 最具技巧性的注入声称。剩余 3 条 minor 为措辞精度与前提交代，建议在末轮前一并清掉以免被同行挑刺，但均不构成投稿障碍。两项 needs-new-experiment（走廊激活、C++ 运行时计时）受数据红线挡住，文字防御已到位，仅作完备性登记。

SCORE: P0=0 major=0 minor=3
