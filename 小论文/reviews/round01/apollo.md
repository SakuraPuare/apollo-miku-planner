# Round 01 审稿意见 — persona: Apollo 工程审

稿件 `drafts/v1.tex`，事实源 `~/Apollo`（Apollo 11.0 checkout）+ 毕设 `毕业论文/chapters`。
本人只读不改稿。下列每条均已在 Apollo 11.0 源码树内核对，给出可定位的源码证据。

核查口径说明：本轮逐条 grep 了 `PathBoundsDeciderUtil`、`LaneFollowPath`、`STDrivableBoundary`、
`PiecewiseJerkSpeedOptimizer`、`SpeedBoundsDecider`、`PathTimeHeuristicOptimizer`、`SpeedDecider`、
`IsWithinPathDeciderScopeObstacle`、`TrimPathBounds`、`FallbackPath`、`st_bounds_decider`、
`use_st_drivable_boundary` 等接口在 `modules/planning` 下的真实存在与调用关系。

---

## 总评

整体对 Apollo 源码机制的转述基本忠实，绝大多数类名、过滤逻辑、blocked-then-trim、
默认参数（obstacle_lat_buffer=0.4、static_obstacle_speed_threshold=0.5、planning_loop_rate=10）
均与 11.0 源码一致，没有发现凭空臆造的接口或函数签名。MIKU 自身的接入函数
（BuildMikuSTDrivableBoundary 等）不在 stock checkout 内，属本组 fork 代码，无法在本树证伪，
但稿件已明示其为新增逻辑，未冒充原生接口，这一点是诚实的。

需要修的问题集中在两处：一是基线优化器类名 `PiecewiseJerkPathOptimizer` 在 Apollo 11.0 中
已不作为独立 Task 存在（与稿件反复强调"Apollo 11.0"自相矛盾），二是 `STDrivableBoundary`
在原生 Apollo 中的生产者/消费者链路与稿件叙述不符，需补一句"本文为何重新利用该结构"的澄清，
否则 Apollo 熟手审稿人会判定为对源码机制的误述。这两条都是改文字能修、不触数据红线。

- P0（致命）：0
- major（必改）：3
- minor（建议）：6

---

## P0（致命，答辩或审稿会被毙）

无。未发现臆造接口、伪造源码行为或在生产代码中站不住的硬伤。

---

## major（必改）

### A-1【Apollo 工程事实】基线类名 `PiecewiseJerkPathOptimizer` 在 Apollo 11.0 中不存在为独立 Task，与全文"Apollo 11.0"定位冲突

定位：摘要无此名（用 PiecewiseJerkPathOptimizer 仅在正文），第 65 行（引言贡献段
"对照基线为 Apollo 原生的 PiecewiseJerkPathOptimizer"）、第 106 行、第 387 行（命题证明）、
第 668 行（相关工作"本文对照基线所采用的 PiecewiseJerkPathOptimizer 即源出该框架"）。

源码事实：在 `~/Apollo/modules/planning` 全树 grep `PiecewiseJerkPathOptimizer` 零命中。
11.0 的路径优化不再是独立 Task，而由四个互斥路径 Task（LaneFollowPath / LaneBorrowPath /
LaneChangePath / FallbackPath）各自内部调用 `PathOptimizerUtil::OptimizePath`
（`path_optimizer_util.cc:96`），底层数学问题为 `PiecewiseJerkPathProblem`
（`planning_base/math/piecewise_jerk/piecewise_jerk_path_problem.{h,cc}`）。
`PiecewiseJerkPathOptimizer` 是 Apollo 6.0–8.0 时代的 Task 名，11.0 已重构掉。

矛盾点：稿件第 106 行对 `PathBoundsDecider` 已经很专业地加了版本注脚
"（Apollo 11.0 中由 PathBoundsDeciderUtil 承载）"，却对同样被重构掉的
`PiecewiseJerkPathOptimizer` 不加任何说明，前后处理标准不一致。一个读过 11.0 代码的审稿人
会立刻发现：你说基于 11.0，却把基线命名为一个 11.0 里搜不到的类。

处置（改文字能修）：首次出现处（第 65 行或第 106 行）补版本注脚，例如
"Apollo 分段加加速度路径优化（11.0 中由 LaneFollowPath 内部调用 PathOptimizerUtil
与 PiecewiseJerkPathProblem 实现，下文沿用其历史 Task 名 PiecewiseJerkPathOptimizer 指代该路径优化环节）"。
注意 SPEC C 节已把基线锁定为"Apollo 原生 PiecewiseJerkPathOptimizer (Baseline)"，故不必改名，
只需补一句版本沿革说明使其与 11.0 自洽即可。毕设 chapter2.tex:155、chapter3.tex:54 本身
也讲清了"历史版本独立 Task、11.0 表现为 Util / Problem"，转写时把这层信息一并带上即可。

### A-2【Apollo 工程事实】`STDrivableBoundary` 的原生生产者/消费者链路与稿件叙述不符，"注入速度 QP"易被误读为原生通路

定位：摘要第 48 行"经 STDrivableBoundary 注入速度二次规划（QP）"；
4.4 节标题"经 STDrivableBoundary 注入速度二次规划"（第 292 行）；第 310 行
"工程上走廊约束以 STDrivableBoundary 这一 ST 可行驶边界结构承载……传至
PiecewiseJerkSpeedOptimizer，后者据此按式 (eq:tighten_ub) 收紧上界"；结论第 708 行同义表述。

源码事实（逐项核对）：
1. 原生 `STDrivableBoundary`（proto 见 `planning_base/proto/st_drivable_boundary.proto`）
   由 **`st_bounds_decider`** Task 生产（`st_bounds_decider.cc:73` 调
   `st_graph_data->SetSTDrivableBoundary(...)`），**不是** SpeedBoundsDecider 生产。
2. 原生消费者是 **DP 启发式搜索**：`gridded_path_time_graph.cc:78` 把
   `st_drivable_boundary()` 传给 `DpStCost`，在 `dp_st_cost.cc:119` 处
   `if (FLAGS_use_st_drivable_boundary)` 才生效。**QP（PiecewiseJerkSpeedOptimizer）
   从不读取 STDrivableBoundary**：grep `modules/planning/tasks/piecewise_jerk_speed/`
   对 `st_drivable_boundary` 零命中；其 s 上下界来自 `st_graph_data.st_boundaries()`
   逐 STBoundary 的 `GetUnblockSRange`（`piecewise_jerk_speed_optimizer.cc:98-132`）。
3. `FLAGS_use_st_drivable_boundary` 默认 **false**（`planning_gflags.cc:377`）。
4. 生产该结构的 `st_bounds_decider` Task **不在** lane_follow 默认流水线里
   （`scenarios/lane_follow/conf/pipeline.pb.txt` 只有两处 SpeedBoundsDecider，无 StBoundsDecider）。

也就是说，stock Apollo 里 STDrivableBoundary 是"给 DP 用、默认关闭、由 st_bounds_decider 产、
lane_follow 流水线根本没挂"的结构。MIKU 把它重新利用为"路径阶段产 → QP 端读"的载体，
这是一个合理的工程设计选择（proto 字段 t/s_lower/s_upper 确实够用，
StGraphData 挂在 ReferenceLineInfo 上也确实是合规的上下文传递），毕设 chapter7.tex:284/310/319
对这层改造交代得相当清楚。但小论文的摘要与 4.4 节把它写成"经 STDrivableBoundary 注入速度 QP"，
未点明"这是对一个原生默认关闭、原供 DP 使用的结构的重新利用 + 新增 QP 端读取逻辑"，
会让熟悉 11.0 的审稿人误以为你在描述一条原生通路，进而怀疑你没读懂源码。

处置（改文字能修，不触数据）：在 4.4 节第 310 行那句后补一句澄清，例如
"需说明，原生 Apollo 中 STDrivableBoundary 由 StBoundsDecider 生成并供 DP 阶段使用且默认关闭；
本文复用其 (t, s_lower, s_upper) 字段作为路径阶段到速度 QP 的约束载体，
并在 PiecewiseJerkSpeedOptimizer 内新增对该结构的读取与上界收紧逻辑"。
这样既忠实又能挡住"链路写反了"的质疑。摘要因篇幅可保留现表述，但正文必须把改造点讲明。

### A-3【Apollo 工程事实】YIELD/OVERTAKE 标签的设定者是 `SpeedDecider`，稿件把它归给 `PathTimeHeuristicOptimizer`

定位：第 290 行"这与 Baseline 在 PathTimeHeuristicOptimizer 给出 YIELD/OVERTAKE
组合后所得的线性盒约束在 QP 结构上一致"；理论 4.4 节第 466 行同一表述
"Baseline 在 PathTimeHeuristicOptimizer 给出让行或超车组合后所得的线性约束"。

源码事实：`PathTimeHeuristicOptimizer`（DP）只在 ST 图上搜出**粗速度曲线**作为暖启动，
真正对每个 STBoundary 写入 YIELD/FOLLOW/OVERTAKE **决策标签**的是 `SpeedDecider`
（`speed_decider.cc:219 MakeObjectDecision`，298 FOLLOW、306/308 YIELD/CreateYieldDecision、
320 OVERTAKE）。默认流水线顺序为 SpeedBoundsDecider → PathTimeHeuristicOptimizer →
SpeedDecider → SpeedBoundsDecider(FINAL) → PiecewiseJerkSpeedOptimizer
（`pipeline.pb.txt:30-47`，毕设 chapter7.tex:362 已正确写出这条顺序）。

说明：DP 在搜索中隐含地做了 yield/overtake 取舍，因此"PathTimeHeuristicOptimizer 给出组合"
并非全错，但把"给出 YIELD/OVERTAKE 组合"这个明确的决策动作直接挂在 DP 上、绕开 SpeedDecider，
表述不够精确。毕设 chapter7.tex:362 的写法更准——"DP 枚举 YIELD/OVERTAKE 组合得粗解，
SpeedDecider 再据此对各 boundary 写入标签"。小论文为压缩篇幅把 SpeedDecider 略去了，
丢了关键一环。

处置（改文字能修）：把两处"PathTimeHeuristicOptimizer 给出 YIELD/OVERTAKE 组合"
改为"Baseline 速度侧经 PathTimeHeuristicOptimizer 的 DP 搜索与 SpeedDecider 的让行/超车决策
后形成线性盒约束"，或至少补上 SpeedDecider 这一环。理论节同改。

---

## minor（建议改）

### A-4【Apollo 工程事实】Prediction 预测时域稿件写"未来 5 s"，11.0 默认为 6.0 s

定位：第 262 行"在 Prediction 模块给出的未来 5 s 预测轨迹中查询"。
源码：`prediction_gflags.cc:24 DEFINE_double(prediction_trajectory_time_length, 6.0, ...)`。
处置：改为"未来约 6 s"或"Prediction 给出的预测轨迹时域内"以免被抓默认值不符。
若毕设另有按 5 s 截断的工程理由，需在文中点明取 5 s 的依据，否则按默认值写。

### A-5【Apollo 工程事实 / 实验方法】以源码 TODO 注释作为学术论据，分量偏弱且转述有偏移

定位：第 116 行"Apollo 开发团队在该过滤函数源码中留有 TODO 注释，提示部分当前低速或静止的
障碍物可能在短时间内重新运动"。
源码：`path_bounds_decider_util.cc:690` 的 TODO 原文是
"Some obstacles are not moving, but only because they are waiting for red light
or because they are blocked by others (social). These obstacles will almost
certainly move ... we should not side-pass such obstacles."
两点：其一，原注释强调的是"因红灯/被堵而暂时静止、几乎必然再动、故**不应**对其 side-pass"，
稿件转述为"低速或静止的障碍物可能在短时间内重新运动"，把"red light / social blocked"
这一具体语义抹平了，略有偏移。其二，SCI 正文引用源码内 TODO 注释作为论据，
在 Apollo 审稿人看来分量较弱，注释不是可正式引用的文献。
处置：要么精确转述（点出红灯/被堵的静止语义），要么把该句降级为脚注或直接删去，
靠命题 prop:decoupled_infeasible 的形式化论证支撑即可，不必倚赖 TODO。

### A-6【Apollo 工程事实】`PathOptimizer` 一词在 4.4 节作为模块名出现，11.0 无此独立 Task

定位：第 321 行"而 PathOptimizer 与 SpeedBoundsDecider 不作修改"。
源码：11.0 无名为 PathOptimizer 的 Task，路径优化封装在 PathOptimizerUtil。
毕设 chapter7.tex:319 用的也是"PathOptimizer"作泛指，但小论文既然反复强调"生产级 11.0 代码接入"，
模块名宜精确。处置：改为"路径优化环节（PathOptimizerUtil）"或"PiecewiseJerkPathProblem 求解步骤"。

### A-7【Apollo 工程事实 / 叙事】FallbackPath 的触发因果链被压缩，宜更准确

定位：第 131 行"调用 TrimPathBounds 截断路径并触发 FallbackPath 停车"；第 387 行同义。
源码事实：TrimPathBounds（`path_bounds_decider_util.cc:170`）只做边界截断；
FallbackPath（`tasks/fallback_path/`）是独立路径 Task，在 LaneFollowPath 等生成失败时
由 Stage 的路径 Task 列表择一兜底执行，并非由 TrimPathBounds 直接"触发"。
处置：改为"截断路径，路径生成失败后由 FallbackPath 兜底停车"之类的弱因果表述，
避免"TrimPathBounds 触发 FallbackPath"这种直接调用关系的暗示。毕设 chapter3.tex:54
已说清四个互斥路径 Task 择一执行的机制，转述时保留这层。

### A-8【Apollo 工程事实 / 文风】`STDrivableBoundary` 等类名在正文混用 \texttt 等宽与无格式两种写法

定位：摘要第 48 行 STDrivableBoundary、LaneFollowPath 为无格式；正文如第 310、706 行
用 \texttt{STDrivableBoundary}。引言第 65 行 LaneFollowPath、STDrivableBoundary 也无格式。
处置：全文统一。按 D 节"Apollo 类名驼峰无空格"已满足驼峰要求，但同一稿内
等宽/非等宽混排不规范，建议正文类名统一 \texttt（摘要内可不用等宽以免破版，但需与正文约定一致）。
这是格式问题，不影响事实正确性。

### A-9【Apollo 工程事实】"OSQP 对约束数量的增量不敏感"为偏强的工程断言，宜收敛

定位：第 565 行"走廊约束以标准 ST 上界形式注入，OSQP 对约束数量的增量不敏感，
不改变 QP 的稀疏结构"；4.4 节亦称"保持 H、A_eq 与稀疏模式完全不变"。
源码层面：MIKU 只改 x^ub 分量（box bound），确实不增行约束、不改 H/A_eq 稀疏模式
（`piecewise_jerk_problem.cc` 的 FormulateProblem 结构固定），这点准确。
但"OSQP 对约束数量的增量不敏感"是对求解器性质的一般化断言，与本文"未增约束数"的事实是两回事，
容易被优化方向审稿人挑刺。处置：删去"OSQP 对约束数量的增量不敏感"这半句，
保留"仅收紧 box 上界、不增约束行、不改 H/A_eq 稀疏模式"这一可被源码直接验证的精确表述即可。

---

## 与前几轮的对照

本轮为第 1 轮，`reviews/` 下尚无 round00/更早的 Apollo persona 记录，无历史遗留可对照。
但比照 GOAL 第 6 节与 SPEC E 节的"忠实红线"既有清单，本轮新发现两条此前未被显式列出的
源码机制隐患，建议补入 MODIFICATIONS.md 的"②Apollo 工程事实"类：
- A-1：基线类名 PiecewiseJerkPathOptimizer 与 11.0 重构后命名的版本一致性问题（毕设也带此名，
  建议毕设/小论文统一加版本注脚）；
- A-2：STDrivableBoundary 原生链路（st_bounds_decider 产、DP 消费、默认 false、不在 lane_follow 流水线）
  与稿件"注入速度 QP"叙述的落差，需补一句重新利用说明。

数据红线核对：本轮所有意见均为"改文字能修"类，无一条需要新实验或改实验数字。
通过率（压力 0/4 vs 4/4、汇总 4/8 vs 8/8）、平均速度（3.53→4.57）、QP 耗时（可比 19.16→6.26）、
消融评分、灵敏度（最坏翻转 57%、最大偏差 6.4%、越界 0）等均与 SPEC B 节冻结值一字一致，
未发现外推或美化。

---

SCORE: P0=0 major=3 minor=6
