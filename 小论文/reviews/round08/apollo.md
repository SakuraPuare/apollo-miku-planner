# Round 08 评审 — persona: Apollo 工程审

审稿对象：`drafts/v8.tex`（全文）。事实源：本机 `~/Apollo` 11.0 checkout（HEAD `40c8a0127a`，与 round07 同一 checkout）。
本轮只读不改稿。逐项把 v8 中涉及 Apollo 11.0 源码机制的承重声称重新对源码核实，并对照 round07 三条遗留 minor 的修复情况。

---

## 0. 本轮结论速览

v8 在 Apollo 工程事实维度**保持二区可投的稳定状态**，全部承重集成声称经 11.0 源码结构逐项复核仍立，无 P0、无 major。本轮新查仍未发现任何臆造接口或不实机制。round07 三条 minor（A-1 PRIORI/FINAL 点名、A-2 `use_st_drivable_boundary` 配置前提、A-3 原生消费者点名）在 v8 中**已全部改净**，逐句对照源码无误。本轮新提两条 minor，一条是 v8 为修 A-1/A-3 引入的同位语赘述（事实正确但文字重复，属文风溢出到工程表述），一条是历史 Task 名注脚在多处重复声明的精简空间。两项 needs-new-experiment（走廊激活、C++ 运行时计时）仍受数据红线挡住，文字防御到位，仅作完备性登记。

---

## 1. 本轮逐项源码核实（承重声称，全部 PASS）

下列声称构成全文 Apollo 集成叙事的承重墙，本轮均回到 11.0 源码确认属实：

- **`STDrivableBoundary` 生产者唯一性**：`SetSTDrivableBoundary` 全仓仅由 `StGraphData::SetSTDrivableBoundary`（`st_graph_data.cc:73`）定义、唯一业务调用方为 `STBoundsDecider`（`st_bounds_decider.cc:73`）。v8 第 413 行「该结构在原生 Apollo 中由 `STBoundsDecider` 这一 ST 边界生产环节生产」属实。PASS。
- **`st_drivable_boundary()` 原生消费者唯一性**：全仓读取该字段者仅 `gridded_path_time_graph.cc:78`（即 `PathTimeHeuristicOptimizer` 的 DP 代价初始化）。v8 第 413 行新增「其唯一原生消费者为 `PathTimeHeuristicOptimizer` 的动态规划代价项」**逐字属实**——此即 round07 A-3 的修复，点名准确。PASS。
- **`use_st_drivable_boundary` 默认关闭**：`planning_gflags.cc:377` 为 `DEFINE_bool(use_st_drivable_boundary, false, ...)`。v8 第 413 行「该消费受 `use_st_drivable_boundary` 开关门控、默认关闭」与「上述复用以默认关闭为前提……该开关若被开启则 `PathTimeHeuristicOptimizer` 亦会读取经本文重写的该字段」**严格成立**——此即 round07 A-2 的修复，配置前提补全到位。PASS。
- **lane_follow pipeline 无 `STBoundsDecider`**：`scenarios/lane_follow/conf/pipeline.pb.txt` 的 task 链为 `LaneChangePath → LaneFollowPath → LaneBorrowPath → FallbackPath → PathDecider → RuleBasedStopDecider → SpeedBoundsDecider(PRIORI) → PathTimeHeuristicOptimizer(SPEED_HEURISTIC_OPTIMIZER) → SpeedDecider → SpeedBoundsDecider(FINAL) → PiecewiseJerkSpeedOptimizer`，**确无 `STBoundsDecider`**。v8「`LaneFollowPath` pipeline 中并不含 `STBoundsDecider`、该结构本就闲置」属实。PASS。
- **PRIORI/FINAL 两次 `SpeedBoundsDecider`**：pipeline 确含 `SPEED_BOUNDS_PRIORI_DECIDER`（DP 之前）与 `SPEED_BOUNDS_FINAL_DECIDER`（`SpeedDecider` 之后）两次同类 task。v8 第 415 行新增「此处 `SpeedBoundsDecider` 指 pipeline 末次即 `SpeedDecider` 之后的 FINAL 调用所产 ST 边界，亦即与速度二次规划直接衔接者」**与 pipeline 顺序吻合**——此即 round07 A-1 的修复，双源取最小的歧义已消除。PASS。
- **`SpeedDecider` 标定 YIELD/OVERTAKE**：`speed_decider.cc:306/320/457/494` 确以 YIELD/OVERTAKE 决策标注障碍物纵向关系。v8 第 376/568 行「`SpeedDecider` 标定 YIELD/OVERTAKE 纵向决策」属实。PASS。
- **`StGraphData` 由 `ReferenceLineInfo` 持有**：`reference_line_info.h:392` 含成员 `StGraphData st_graph_data_;`，并由 `mutable_st_graph_data()`（`:234`）暴露。`STDrivableBoundary` 是 `StGraphData` 的成员字段（`st_graph_data.h:85`）。v8 第 413 行「写入 `ReferenceLineInfo` 持有的 `StGraphData` 的 `STDrivableBoundary` 字段并经其随数据总线传至速度阶段」的容器层级**逐层属实**。PASS。
- **`PiecewiseJerkSpeedOptimizer` 原生不读 `STDrivableBoundary`**：`piecewise_jerk_speed_optimizer.cc` 原生经 `StGraphData` 消费 `st_boundaries()`（`:98`）与 `speed_limit()`（`:142`），**不读** `st_drivable_boundary()`。v8 第 424 行把「`PiecewiseJerkSpeedOptimizer` 新增对该上界包络的读入与取最小值」明确标为 MIKU 新增改动，未把新增代码伪装为原生行为。框定正确。PASS。此外该文件 `:158` 已存在 `std::fmin(speed_limit..., v_upper_bound)`，佐证 v8 式\eqref{eq:tighten_ub}「取最小值收紧上界」与该求解器既有的 fmin 写法同构、属低侵入改动，声称可立。
- **`IsStatic` 过滤 + 阈值**：`path_bounds_decider_util.cc:686` 确以 `!obstacle.IsStatic() || obstacle.speed() > FLAGS_static_obstacle_speed_threshold` 排除运动障碍物；阈值默认 `0.5`（`planning_gflags.cc:186`）。v8 第 237/475/615/866 行的「IsStatic 过滤把动态障碍物排除、转交速度阶段」与 0.5 m/s 二分均属实。PASS。
- **统一缓冲 `GetBufferBetweenADCCenterAndEdge`**：函数体（`:667`）返回 `adc_half_width + FLAGS_obstacle_lat_buffer`，`obstacle_lat_buffer` 默认 `0.4`（`:175`）。v8 第 237 行「对所有障碍物返回同一套安全裕度，即半车宽再加固定额外缓冲 `obstacle_lat_buffer`」属实。PASS。
- **nudge 分级参数三者独立**：`static_obstacle_nudge_l_buffer=0.3`（`:138`）、`nonstatic_obstacle_nudge_l_buffer=0.4`（`:140`）、`obstacle_lat_buffer=0.4`（`:175`）。v8 第 237 行「静态取 0.3 m、非静态取 0.4 m，与 `obstacle_lat_buffer` 分属不同参数、走不同代码路径」属实。PASS。
- **blocked-then-trim 与 `FallbackPath`**：`TrimPathBounds`（`:170`，调用点 `:441`）、`FallbackPath` 为 lane_follow pipeline 内 task。v8 第 424/489/615/685/696/866/870 行的「判 BLOCKED → TrimPathBounds 截断 → FallbackPath 停车降级」与 Apollo blocked-then-trim 记忆一致。PASS。
- **`LaneBorrowPath` 未启用的诚实披露**：`LaneBorrowPath` 在 pipeline 中在册，v8 第 797 行如实声明 Baseline 未启用借道路径分支、并指出 P4 正是其设计触发条件，与 pipeline 一致且未夸大。PASS。
- **历史 Task 名注脚**：`PathBoundsDeciderUtil` 为静态方法集合、`PathOptimizerUtil`/`PiecewiseJerkPathProblem` 承载路径优化（`path_optimizer_util.{h,cc}`、`piecewise_jerk_path_problem.h` 均在册）。v8 第 149 行「沿用历史 Task 名 `PathBoundsDecider`/`PiecewiseJerkPathOptimizer` 指代」的转述准确，未把历史名当作 11.0 现存 Task。PASS。
- **`BuildMikuSTDrivableBoundary`**：此为 MIKU 自有新增方法名，v8 明确归属于「`LaneFollowPath` 的 `BuildMikuSTDrivableBoundary`」即本文新增代码，非伪装为 Apollo 原生接口。命名前缀 `Miku` 已自证为本文产物，无臆造原生接口之嫌。PASS。

---

## 2. 本轮意见清单

### A-1【Apollo 工程事实 / 文风｜精度｜minor｜本轮新增，v8 修 A-1/A-3 时引入】类名同位语出现同义反复，事实正确但文字重复

- 定位：v8 第 376 行「Baseline 经 `PathTimeHeuristicOptimizer` **这一 ST 图动态规划粗搜索环节**在 $ST$ 图上**动态规划粗搜索**、`SpeedDecider` **这一纵向超车让行决策环节**标定 YIELD/OVERTAKE **纵向决策**、再由 `SpeedBoundsDecider` **这一 ST 边界决策环节**映射为 $ST$ 边界」。同处问题在第 568 行有对应较简洁的写法（无同位语），二者表述不一致。
- 源码事实：三处类名的职责描述本身全部属实（`PathTimeHeuristicOptimizer` 即 DP 粗搜索、`SpeedDecider` 标 YIELD/OVERTAKE、`SpeedBoundsDecider` 产 ST 边界，§1 均已坐实），**无事实错误**。问题纯在文字：为每个类名插入「这一……环节」同位语后，紧跟的动词短语与同位语语义重复，读成「ST 图动态规划粗搜索环节在 ST 图上动态规划粗搜索」。
- 影响：不构成工程事实错误，但同义反复在方法节承重句中读感冗赘，且与第 568 行的简洁版不一致，挑剔的同行会注意到。归因应是为落实 round07 A-3「点名原生消费者/职责」时全局加注同位语、未回收原有动词短语所致。
- 处置（改文字能修，不涉数据）：三选一去重——或保留同位语删后续动词短语（「经 `PathTimeHeuristicOptimizer` 这一 ST 图动态规划粗搜索环节、`SpeedDecider` 这一纵向让行超车决策环节、`SpeedBoundsDecider` 这一 ST 边界决策环节所得的线性盒约束」），或保留动词短语删同位语（回到第 568 行写法）。建议与第 568 行措辞统一。记入 MODIFICATIONS.md「⑥文风与格式 / ②Apollo 工程事实」。

### A-2【Apollo 工程事实｜精度｜minor｜round06 起多轮遗留的同类问题，可选收尾】历史 Task 名注脚在正文多处重复声明，可考虑收敛为单次首现注脚

- 定位：v8 第 149 行已完整交代「`PathBoundsDecider`/`PiecewiseJerkPathOptimizer` 为沿用的历史 Task 名」，但第 237、302、475 等处再次出现这两个历史名时，部分仍附带或暗示同类说明，存在重复。
- 源码事实：历史名转述本身正确（§1 已 PASS），此非事实问题，纯属行文经济性。11.0 中真实承载者为 `PathBoundsDeciderUtil` 静态方法与 `PathOptimizerUtil`/`PiecewiseJerkPathProblem`，v8 对此已在首现处讲清。
- 影响：极轻微。首现处注脚已足够，后续重复声明不影响正确性，仅略显啰嗦。
- 处置（改文字能修，可选）：在首现注脚（第 149 行）确立「下文统称」后，后续出现处直接用历史名而不再重复解释。优先级最低，可保留现状。记入 MODIFICATIONS.md「⑥文风与格式」备查。

---

## 3. needs-new-experiment / 数据红线挡住（仅登记，文字防御已到位）

### N-1【Apollo 工程验证完备性｜需新实验｜数据红线｜自 round03 遗留】走廊注入组件未被任何场景激活（M4≈M5），时间通道这一标题级 insight 的注入侧未获数据验证

- 本轮已结构性复核注入链全部成立：proto 字段在册、`PiecewiseJerkSpeedOptimizer` 可在组装 s 盒上界后插一步 fmin（其 `:158` 已有同构 fmin）、`STDrivableBoundary` 由 `ReferenceLineInfo`/`StGraphData` 跨阶段持有、lane_follow 中该结构闲置可被复用。但 v8 第 768/779/805 行如实承认 4 个压力场景均未触发活跃时间窗约束，M4（关闭走廊注入）=99.18 与 M5=100.00 仅差 0.82。即集成通路验证为可接入，但注入的走廊约束从未在数据上被实际行使。
- 处置：v8 第 779/805 行已把 M4≈M5 诚实归因于「当前压力场景未激活活跃边界」、且明言「定量贡献由架构设计论证而非本组消融数据给出」，文字防御充分、未夸大。受数据冻结红线挡住，须补能触发活跃时间窗约束的动态冲突密集场景方能实证。记入 MODIFICATIONS.md「⑧需新实验」，**不动稿**。

### N-2【Apollo 工程事实 / 实验方法｜需新实验｜数据红线】C++ 生产运行时未计时，全部耗时取自 Python 复现，二者非同一数据源

- v8 第 587/592/723/793 行已反复声明 QP 耗时取自 Python 数值复现、C++ 实现仅作 Dreamview 在环定性佐证、不与数值指标混作同源。框定到位。Apollo C++ 生产运行时的绝对耗时须另测，受数据红线挡住。记入 MODIFICATIONS.md「⑧需新实验」，**不动稿**。

---

## 4. 对照前几轮的遗留收敛情况

- round05 四条 minor（摘要匿名、FallbackPath 降级 QP 行为、盒约束产出链、预测时域错配）→ round06 已修净，v8 维持不回退。
- round06 三条 minor（容器层级、跨阶段持久性前提、PRIORI/FINAL）→ 前两条 v7 已修，第三条顺延至 round07 A-1。
- **round07 三条 minor 在 v8 全部改净**：A-1（PRIORI/FINAL 点名）→ v8 第 415 行已补「此处 `SpeedBoundsDecider` 指 pipeline 末次即 FINAL 调用所产 ST 边界」，**已修**；A-2（`use_st_drivable_boundary` 配置前提）→ v8 第 413 行已补「上述复用以默认关闭为前提……开关开启时 `PathTimeHeuristicOptimizer` 亦会读取经本文重写的该字段」，**已修**；A-3（原生消费者点名）→ v8 第 413 行已补「其唯一原生消费者为 `PathTimeHeuristicOptimizer` 的动态规划代价项」，**已修**。三条均逐句对照源码无误。
- 连续多轮的承重声称（STDrivableBoundary 复用、PJ 取 min 注入、ReferenceLineInfo/StGraphData 数据总线、blocked-then-trim、IsStatic 过滤、借道未启用诚实披露、历史名注脚、跨阶段持久化、SpeedDecider 标 YIELD/OVERTAKE）本轮再次全部经源码结构核实可立。

总体判断：v8 在 Apollo 工程事实维度已稳定可投二区，无 P0、无 major。round07 三条 minor 全部修净。本轮新提两条 minor 均为措辞精简（A-1 同位语去重 + A-2 历史名注脚收敛），全部改文字能修、不触数据、不影响任何事实正确性，建议末轮前一并清掉以免被同行挑剔行文。两项 needs-new-experiment 受数据红线挡住，文字防御已到位，仅作完备性登记。

SCORE: P0=0 major=0 minor=2
