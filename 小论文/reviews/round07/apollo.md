# Round 07 评审 — persona: Apollo 工程审

审稿对象：`drafts/v7.tex`（全文）。事实源：本机 `~/Apollo` 11.0 checkout（HEAD `40c8a0127a`）。
本轮只读不改稿。逐项把 v7 中涉及 Apollo 11.0 源码机制的承重声称重新对源码核实，并对照 round06 遗留。

---

## 0. 本轮结论速览

v7 在 Apollo 工程事实维度**已达到二区可投的稳定状态**，全部承重集成声称经 11.0 源码结构逐项复核可立，无 P0、无 major。本轮新查仍未发现任何臆造接口或不实机制。round06 三条 minor 中 A-1（容器层级）、A-2（跨阶段持久性前提）已在 v7 改净，A-3（PRIORI/FINAL 二次运行）仍未交代，作 minor 顺延。另首次提出两条精度/鲁棒性 minor。两项 needs-new-experiment（走廊激活、C++ 运行时计时）仍受数据红线挡住，文字防御到位，仅作完备性登记。

---

## 1. 本轮逐项源码核实（承重声称，全部 PASS）

下列声称构成全文 Apollo 集成叙事的承重墙，本轮均回到 11.0 源码确认属实：

- **路径边界承载方 `PathBoundsDeciderUtil`**：实体在 `planning_interface_base/.../path_util/path_bounds_decider_util.{h,cc}`，为静态方法集合。v7 第 149/237/302/475 行称其以静态方法承载路径边界构建、并沿用历史 Task 名 `PathBoundsDecider` 指代，注脚式转述准确。PASS。
- **动态障碍物过滤 `IsWithinPathDeciderScopeObstacle` + `IsStatic`**：函数体（`path_bounds_decider_util.cc:674`）确以 `!obstacle.IsStatic() || obstacle.speed() > FLAGS_static_obstacle_speed_threshold` 将运动障碍物排除于路径决策；阈值 `static_obstacle_speed_threshold` 默认 `0.5`（`planning_gflags.cc:186`）。v7 第 159/237/475/615 行的「IsStatic 过滤把动态障碍物排除、转交速度阶段」与 0.5 m/s 二分均属实。PASS。
- **「过滤逻辑附近未完成的工程考虑」（v7 第 159 行）**：函数体内确有 `TODO(jiacheng)` 注释，明言部分因红灯或被阻挡而暂静止的障碍物近期几乎必然重新运动、不应 side-pass。v7 的转述忠实且未夸大，措辞收敛得当。PASS。
- **统一缓冲 `GetBufferBetweenADCCenterAndEdge`**：函数体（`path_bounds_decider_util.cc:667`）返回 `adc_half_width + FLAGS_obstacle_lat_buffer`，对所有障碍物同值。v7 第 237 行「对所有障碍物返回同一套安全裕度，即半车宽再加固定额外缓冲 `obstacle_lat_buffer`」属实。PASS。
- **nudge 分级参数**：`static_obstacle_nudge_l_buffer=0.3`、`nonstatic_obstacle_nudge_l_buffer=0.4`、`obstacle_lat_buffer=0.4`（`planning_gflags.cc:138/140/175`）。v7 第 237 行称三者「分属不同参数、走不同代码路径」准确——`GetBufferBetweenADCCenterAndEdge` 用 `obstacle_lat_buffer`，而 SL-polygon nudge 路径（`UpdatePathBoundaryBySLPolygon`）用 nudge_l_buffer，二者确为不同路径（且 SL-polygon 内对 `GetBufferBetweenADCCenterAndEdge` 的调用实际被注释，更佐证 v7 不混同二者的谨慎）。PASS。
- **blocked-then-trim 与 `FallbackPath`**：`TrimPathBounds`（`path_bounds_decider_util.cc:170`）、调用点 `:441`，`FallbackPath` 为 lane_follow pipeline 内 task。v7 第 196/302/424/489/685 行的「判 BLOCKED → TrimPathBounds 截断 → FallbackPath 停车」与 Apollo blocked-then-trim 记忆一致。PASS。
- **`LaneFollowPath` / `LaneBorrowPath` 接入点**：`tasks/lane_follow_path/lane_follow_path.{h}` 类 `LaneFollowPath` 在册；lane_follow pipeline（`scenarios/lane_follow/conf/pipeline.pb.txt`）task 链为 `LaneChangePath → LaneFollowPath → LaneBorrowPath → FallbackPath → PathDecider → RuleBasedStopDecider → SpeedBoundsDecider(PRIORI) → SpeedHeuristicOptimizer(=PathTimeHeuristicOptimizer) → SpeedDecider → SpeedBoundsDecider(FINAL) → PiecewiseJerkSpeed`。v7 把接入点定位在 `LaneFollowPath`、并诚实披露 Baseline 未启用 `LaneBorrowPath`（第 797 行），与 pipeline 一致。PASS。
- **`STDrivableBoundary` 生产者/消费者与 `use_st_drivable_boundary` 门控**：`SetSTDrivableBoundary` 全仓**仅**由 `STBoundsDecider`（`st_bounds_decider.cc:73`）调用；`st_drivable_boundary()` 全仓**仅**由 `gridded_path_time_graph.cc:78`（即 PathTimeHeuristic 的 DP 代价）读取，且其消费受 `FLAGS_use_st_drivable_boundary` 门控，该 flag 默认 `false`（`planning_gflags.cc:377`、`planning.conf:32`）。lane_follow pipeline **无 `STBoundsDecider`**。故 v7 第 413 行「该结构在原生 Apollo 由 STBoundsDecider 生产、下游消费受开关门控默认关闭、在 LaneFollowPath pipeline 中本就闲置」**逐句属实**。PASS。这是全文最具技巧性的复用声称，本轮再次坐实。
- **`PiecewiseJerkSpeedOptimizer` 原生不读 STDrivableBoundary**：`piecewise_jerk_speed_optimizer.cc` 原生消费 `st_graph_data.st_boundaries()`（`:98`）与 `speed_limit()`（`:142`），**不读** `st_drivable_boundary`。v7 第 413/424 行把「PiecewiseJerkSpeedOptimizer 读入该上界包络并取最小值」明确标为 MIKU **新增**改动（「`PiecewiseJerkSpeedOptimizer` 新增对该上界包络的读入与取最小值」），未把新增代码伪装成原生行为。框定正确。PASS。
- **跨阶段持久性机制（round06 A-2 的底层前提）**：`StGraphData::LoadData`（`st_graph_data.cc`，由 `SpeedBoundsDecider` FINAL 在 `LaneFollowPath` 之后于 `speed_bounds_decider.cc:125` 调用）函数体重填 `st_boundaries_`/`init_point_` 等，**不触碰 `st_drivable_boundary_`**。故路径阶段 `LaneFollowPath` 写入的 `STDrivableBoundary` 内容能存活过 FINAL 的 `LoadData` 抵达速度 QP。v7 第 413 行已补「其间速度边界决策仅刷新 ST 边界而不清空该字段，故路径阶段的写入得以存活至速度阶段被读取」——**与源码完全吻合，round06 A-2 已修净**。PASS。
- **数据总线容器层级（round06 A-1）**：v7 第 413/424 行已写为「写入 `ReferenceLineInfo` 持有的 `StGraphData` 的 `STDrivableBoundary` 字段」，`ReferenceLineInfo` 确有 `mutable_st_graph_data()`、`StGraphData` 确含 `st_drivable_boundary_` 成员（`st_graph_data.h:85`）。层级表述已精确化，**round06 A-1 已修净**。PASS。
- **类名驼峰**：全文 `PathBoundsDeciderUtil` / `LaneFollowPath` / `STDrivableBoundary` / `PiecewiseJerkSpeedOptimizer` / `SpeedBoundsDecider` / `PathTimeHeuristicOptimizer` / `SpeedDecider` / `ReferenceLineInfo` / `StGraphData` / `VehicleState` 等一律驼峰无空格，符合 SPEC D-4。PASS。
- **无臆造接口**：`BuildMikuSTDrivableBoundary`（第 413 行）为 MIKU 自有新方法、文中明确署其为新增，非冒充原生 API；其余所引方法名（`UpdatePathBoundaryBySLPolygon` 第 302 行、`GetBufferBetweenADCCenterAndEdge` 第 237 行）均在源码中存在。未发现任何虚构接口。PASS。

---

## 2. 本轮意见清单

### A-1【Apollo 工程事实｜精度｜minor｜round06 A-3 顺延，仍未改】SpeedBoundsDecider 在 lane_follow 中运行两次（PRIORI/FINAL），注入速度 QP 的 ST 边界来自 FINAL，正文以「SpeedBoundsDecider」泛指未点明

- 定位：v7 第 376、398、415、422、568 行多处以 `SpeedBoundsDecider` 泛指。
- 源码事实：lane_follow pipeline 含 `SPEED_BOUNDS_PRIORI_DECIDER`（DP 之前）与 `SPEED_BOUNDS_FINAL_DECIDER`（`SpeedDecider` 之后）两次同类 task；真正装配进 `PiecewiseJerkSpeedOptimizer` 的 s 盒约束、且为最后一次 `LoadData` 重建者是 FINAL。
- 影响：基本不影响——第 376/422 行把 `SpeedBoundsDecider` 列于 `SpeedDecider` 之后，已隐含指向 FINAL，substantively 正确。仅式 \eqref{eq:dual_source}（双源取最小，第 415/418 行）邻近的泛指略欠精确，极挑剔的同行可能追问「双源取最小针对 PRIORI 还是 FINAL」。
- 处置（改文字能修）：在双源融合首现处（约第 415 行）补半句或脚注「此处 `SpeedBoundsDecider` 指 pipeline 末次（FINAL）调用所产 ST 边界，亦即与速度 QP 直接衔接者」。优先级低，可与 A-2/A-3 合并处理。记入 MODIFICATIONS.md「②Apollo 工程事实」。

### A-2【Apollo 工程事实｜鲁棒性/配置｜minor｜本轮新增】`use_st_drivable_boundary` 一旦被开启，pipeline 中实际在跑的 PathTimeHeuristicOptimizer 会意外消费 MIKU 写入的 STDrivableBoundary，与 v7「该结构闲置」的前提产生隐含耦合

- 定位：v7 第 413 行「在本文接入的 `LaneFollowPath` 路径 pipeline 中并不含 `STBoundsDecider`，该结构本就闲置，速度二次规划亦不读取它；本文重新利用这一既有闲置数据结构」。
- 源码事实：`st_drivable_boundary()` 的唯一原生读者 `gridded_path_time_graph.cc:78` 属 `PathTimeHeuristicOptimizer`（即 pipeline 中**确在运行**的 `SPEED_HEURISTIC_OPTIMIZER`），其消费受 `FLAGS_use_st_drivable_boundary` 门控、默认 `false`。v7 的「闲置」前提**严格成立于默认配置**；但 MIKU 让 `PiecewiseJerkSpeedOptimizer` 无条件读取该字段，而该字段已被 MIKU 重写。若运维侧将 `use_st_drivable_boundary` 翻为 `true`，则 `PathTimeHeuristicOptimizer` 的 DP 代价会一并消费 MIKU 写入的边界，产生设计外的二次耦合（DP 粗搜索与 QP 精解读到同一份 MIKU 边界，语义未必一致）。
- 影响：不影响默认配置下的全部实验与结论（数值复现与 Dreamview 均默认关），故非 major；但作为「生产级代码集成」的工程严谨性，承重声称「该结构闲置、复用无副作用」应明确其成立的配置前提。
- 处置（改文字能修，不涉数据）：在第 413 行末补半句限定，例如「上述复用以 `use_st_drivable_boundary` 默认关闭为前提，该开关开启时 `PathTimeHeuristicOptimizer` 亦会读取该字段，MIKU 的接入默认运行于该开关关闭的生产配置下」。记入 MODIFICATIONS.md「②Apollo 工程事实」。

### A-3【Apollo 工程事实｜精度｜minor｜本轮新增，可选】STDrivableBoundary 的原生消费者是 PathTimeHeuristicOptimizer 的 DP 代价，而非速度 QP，正文未点名原生消费者

- 定位：v7 第 413 行称该结构「下游消费受 `use_st_drivable_boundary` 开关门控、默认关闭」，但未点出原生消费者究竟是谁。
- 源码事实：唯一原生读者为 `gridded_path_time_graph` / `dp_st_cost`（PathTimeHeuristic 的 DP 代价项），并非 `PiecewiseJerkSpeedOptimizer`。点明这一点可与第 376 行已有的「`PathTimeHeuristicOptimizer` 在 ST 图上动态规划粗搜索」呼应，进一步坐实 MIKU 把该闲置结构改作速度 QP 上界来源是**重定向**了其原生用途，而非简单填充。
- 影响：纯属可加分的精度提升，现状不构成错误。优先级最低。
- 处置（改文字能修，可选）：在第 413 行「下游消费受开关门控」处附半句「其原生消费者为 `PathTimeHeuristicOptimizer` 的 DP 代价项」。可并入 A-1/A-2 一并处理或保留现状。记入 MODIFICATIONS.md「②Apollo 工程事实」备查。

---

## 3. needs-new-experiment / 数据红线挡住（仅登记，文字防御已到位）

### N-1【Apollo 工程验证完备性｜需新实验｜数据红线｜自 round03 遗留】走廊注入组件未被任何场景激活（M4≈M5），时间通道这一标题级 insight 的注入侧未获数据验证

- 本轮已结构性核实注入链全部成立：proto 字段在册、`PiecewiseJerkSpeedOptimizer` 可在组装 s 盒上界后插一步 `fmin`、`STDrivableBoundary` 跨阶段持久（§1）、lane_follow 中该结构闲置可被复用。但 v7 第 779/805 行如实承认 4 个压力场景均未触发活跃时间窗约束，第 768 行 M4（关闭走廊注入）=99.18 与 M5=100.00 仅差 0.82。即集成通路验证为可接入，但注入的走廊约束从未在数据上被实际行使。
- 处置：v7 第 779/805 行已把 M4≈M5 诚实归因于「当前压力场景未激活活跃边界」、且明言「定量贡献由架构设计论证而非本组消融数据给出」，文字防御充分、未夸大。受数据冻结红线挡住，须补能触发活跃时间窗约束的动态冲突密集场景方能实证。记入 MODIFICATIONS.md「⑧需新实验」，**不动稿**。

### N-2【Apollo 工程事实/实验方法｜需新实验｜数据红线】C++ 生产运行时未计时，全部耗时取自 Python 复现，二者非同一数据源

- v7 第 587/592/723/793 行已反复声明 QP 耗时取自 Python 数值复现、C++ 实现仅作 Dreamview 在环定性佐证、不与数值指标混作同源。框定到位。Apollo C++ 生产运行时的绝对耗时须另测，受数据红线挡住。记入 MODIFICATIONS.md「⑧需新实验」，**不动稿**。

---

## 4. 对照前几轮的遗留收敛情况

- round05 四条 minor（摘要匿名、FallbackPath 降级 QP 行为、盒约束产出链、预测时域错配）→ round06 已确认修净，v7 维持不回退。
- round06 三条 minor：A-1（容器层级）→ v7 第 413 行已精确化为 ReferenceLineInfo→StGraphData→STDrivableBoundary，**已修**；A-2（跨阶段持久性前提）→ v7 第 413 行已补「速度边界决策仅刷新 ST 边界而不清空该字段」，**已修**；A-3（PRIORI/FINAL）→ **未改，本轮顺延为 A-1**。
- 连续多轮的承重声称（STDrivableBoundary 复用、PJ 取 min 注入、ReferenceLineInfo/StGraphData 数据总线、blocked-then-trim、IsStatic 过滤、借道未启用诚实披露、历史名注脚、LoadData 不清空持久化）本轮再次全部经源码结构核实可立。

总体判断：v7 在 Apollo 工程事实维度已稳定可投二区，无 P0、无 major。剩余三条 minor（A-1 顺延 + A-2/A-3 新增）均为精度与配置前提的措辞微调、全部改文字能修、不触数据，建议末轮前一并清掉以免被同行挑刺。两项 needs-new-experiment 受数据红线挡住，文字防御已到位，仅作完备性登记。

SCORE: P0=0 major=0 minor=3
