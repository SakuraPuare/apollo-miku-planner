# Round 03 审稿意见 — persona: Apollo 工程审

稿件 `drafts/v3.tex`，事实源 `~/Apollo`（Apollo 11.0 checkout，`modules/planning`）+ 毕设 `毕业论文/`。
本人只读不改稿。下列每条均已在 Apollo 11.0 源码树内核对，给出可定位的源码证据（类名/函数名/默认值/调用关系）。

核查口径：本轮在 `~/Apollo/modules/planning` 下逐条 grep 复核了
`PathBoundsDecider` / `PathBoundsDeciderUtil`、`GetBufferBetweenADCCenterAndEdge`、
`UpdatePathBoundaryBySLPolygon`、`IsWithinPathDeciderScopeObstacle` / `IsStatic` / `TrimPathBounds`、
`obstacle_lat_buffer` / `static_obstacle_nudge_l_buffer` / `nonstatic_obstacle_nudge_l_buffer` /
`static_obstacle_speed_threshold`、`LaneFollowPath`、`PiecewiseJerkPathProblem`、
`PathOptimizerUtil`、`SetSTDrivableBoundary` / `use_st_drivable_boundary` / `STBoundsDecider`、
`PiecewiseJerkSpeedOptimizer`（`st_graph_data.st_boundaries()`）、`SpeedBoundsDecider` /
`st_boundary_mapper`、`PathTimeHeuristicOptimizer`、`BuildMikuSTDrivableBoundary`。

---

## 总评

v3 把 round02 的两条 major **全部修掉了**，是真改不是幻觉式处置，源码逐项复核通过：

- round02 A-1（走廊产出方在 `PathBoundsDecider` 与 `LaneFollowPath` 之间横跳）→ v3 第 434 行已统一：显式通道改动落点写成「`LaneFollowPath` 的路径边界构建新增时变 SL 投影与 `STDrivableBoundary` 重建」「`PiecewiseJerkSpeedOptimizer` 新增对该上界包络的读入与取最小值」，宿主类与第 423 行的 `LaneFollowPath::BuildMikuSTDrivableBoundary` 对齐，不再出现「`PathBoundsDecider` 新增 𝒯 输出」的旧表述。**已解决。**
- round02 A-2（QP 到底读 `STDrivableBoundary` 还是读时间清单 𝒯，接口说不清）→ v3 第 423、434 行统一为「QP 在组装 `s_j^{ub,SBD}` 之后读入挂在 `ReferenceLineInfo` 上的 `STDrivableBoundary` 上界包络，按式 (tighten_ub) 取最小值」，𝒯 退为路径侧构造走廊的中间量，不再作为 QP 直接读入对象。与源码改动语义自洽（原生 QP 的 s 界来自 `piecewise_jerk_speed_optimizer.cc:98` 的 `st_graph_data.st_boundaries()`，MIKU 在其后插一步取 min）。**已解决。**
- round02 A-5（0.1 s 速度网格 vs 100 ms 周期）→ v3 第 408 行已补「此处 0.1 s 为速度二次规划的时间离散步长，由速度优化配置决定，与 100 ms 规划重规划周期分属两个量」。**已解决。**
- round02 A-6（`SpeedDecider` 全时段让行措辞偏强）→ v3 第 432 行已改为「把基于全时刻并集投影的保守让行替换为按 τ(s_k) 的精确等待截止时间」。**已解决。**
- round02 A-7（Python 复现与 C++ 数据源切割）→ v3 第 598、603 行已两处显式声明数值指标取自 Python 复现、Dreamview 仅展示 C++ 接入定性行为、二者「分属两类独立证据」。**已解决。**

本轮可核查事实点全部对得上：`GetBufferBetweenADCCenterAndEdge` 体为 `adc_half_width + FLAGS_obstacle_lat_buffer`（`path_bounds_decider_util.cc:667`，默认 0.4，`planning_gflags.cc:175`），`static_obstacle_nudge_l_buffer=0.3`、`nonstatic_obstacle_nudge_l_buffer=0.4`、`static_obstacle_speed_threshold=0.5`（`planning_gflags.cc:138/140/186`），`IsStatic` 过滤在 `path_bounds_decider_util.cc:686`、其后紧跟 `TODO(jiacheng)`（对应稿件第 165/486 行「附近存在未完成的工程考虑」，属实），`UpdatePathBoundaryBySLPolygon`（`:217`）、`STBoundsDecider` 产 `SetSTDrivableBoundary`（`st_bounds_decider.cc:73`）、`use_st_drivable_boundary` 默认 false（`:377`）、`PathTimeHeuristicOptimizer` 在 `scenarios/lane_follow/conf/pipeline.pb.txt` 内、`SpeedBoundsDecider` 经 `st_boundary_mapper.cc:169` 同时产 lower/upper points，均一致。`BuildMikuSTDrivableBoundary` 全树零命中，属本组 fork，稿件明示为新增逻辑、未冒充原生接口，诚实。

本轮无 P0。新发现一条 major，根因与 round01 A-1（`PiecewiseJerkPathOptimizer` 类名版本一致性）**同源同型**：v3 仍把 11.0 里不存在的类名 `PathBoundsDecider` 当作正文活跃代码主体，并向它挂接具体的 Util 静态方法。其余为 minor。均为「改文字能修」，不触数据红线。

- P0（致命）：0
- major（必改）：1
- minor（建议）：4

---

## P0（致命）

无。未发现臆造接口、伪造源码行为或在 11.0 生产代码中站不住的硬伤。

---

## major（必改）

### A-1【Apollo 工程事实】`PathBoundsDecider` 在 Apollo 11.0 中不作为类/Task 存在，却被当作正文活跃代码主体并挂接具体 Util 方法，与 round01 A-1 的整改逻辑不自洽

类别：Apollo 工程事实。可定位、可执行。改文字能修，不触数据红线。

定位：
- 第 155 行：「由 `PathBoundsDecider`（Apollo 11.0 中由 `PathBoundsDeciderUtil` 承载）构建通行带」——此处给了版本注脚，是对的。
- 第 247 行：「Apollo 的 `PathBoundsDecider` 在 `GetBufferBetweenADCCenterAndEdge` 中对所有障碍物返回同一套安全裕度」——把 Util 静态方法挂到不存在的类上。
- 第 312 行：「Apollo 的 `PathBoundsDecider` 在 `UpdatePathBoundaryBySLPolygon` 中逐障碍物决定 LEFT_NUDGE 或 RIGHT_NUDGE」——同上。
- 第 165、202、486、626 行：均以裸 `PathBoundsDecider` 作路径边界构建主体。

源码事实：全树 grep `class PathBoundsDecider`（非 Util）零命中；唯一带该词根的实体是 `PathBoundsDeciderUtil`（`planning_interface_base/task_base/common/path_util/path_bounds_decider_util.{h,cc}`），其中 `GetBufferBetweenADCCenterAndEdge`（`:667`）、`UpdatePathBoundaryBySLPolygon`（`:217`）、`IsWithinPathDeciderScopeObstacle`（`:674`）、`IsStatic` 过滤（`:686`）、`TrimPathBounds` 均为 `PathBoundsDeciderUtil` 的**静态方法**，由四个路径 Task（`LaneFollowPath` / `LaneBorrowPathGeneric` / `LaneChangePathGeneric` / `FallbackPath`）各自内部调用（如 `lane_borrow_path_generic.cc:141` / `lane_change_path_generic.cc:117` 调 `PathBoundsDeciderUtil::UpdatePathBoundaryBySLPolygon`）。`PathBoundsDecider` 与 `PiecewiseJerkPathOptimizer` 一样，是 6.0–8.0 时代的独立 Task 名，11.0 已重构为 Util + 路径 Task。

问题：这与 round01 A-1（基线 `PiecewiseJerkPathOptimizer` 类名版本一致性）是同一型错误，而 v3 对 `PiecewiseJerkPathOptimizer` 已经很专业地加了「历史 Task 名」注脚（第 155 行末），却对同样被重构掉的 `PathBoundsDecider` 处理标准不一——第 155 行加了「由 PathBoundsDeciderUtil 承载」一句注脚，但第 247、312 行又把它当成活跃类、并向它挂具体的 Util 函数名（`GetBufferBetweenADCCenterAndEdge` / `UpdatePathBoundaryBySLPolygon`）。一个读过 11.0 代码的审稿人会问：你说基于 11.0，却把 `PathBoundsDeciderUtil` 的静态方法说成是「`PathBoundsDecider` 在某函数中」，那个类在 11.0 搜不到。这正是 round01 已经认过的坑，应一并整改到位。

处置（改文字能修，二选一，建议 a）：
- (a) 全文把作为「代码主体」的 `PathBoundsDecider` 统一收敛到 `PathBoundsDeciderUtil`（驼峰、`\texttt`），即第 247 行改为「`PathBoundsDeciderUtil::GetBufferBetweenADCCenterAndEdge`」、第 312 行改为「`PathBoundsDeciderUtil` 的 `UpdatePathBoundaryBySLPolygon`」；其余作泛指「路径边界构建环节」处可保留口语化但不带具体函数。
- (b) 若要保留 `PathBoundsDecider` 作为「路径边界决策环节」的历史称谓，则比照 `PiecewiseJerkPathOptimizer` 的处理，在首次出现处补一句版本注脚「11.0 中由 `PathBoundsDeciderUtil` 的静态方法承载，本文沿用其历史 Task 名指代该路径边界构建环节」，并把第 247、312 行的「在 `GetBufferBetweenADCCenterAndEdge`/`UpdatePathBoundaryBySLPolygon` 中」明确为「由 `PathBoundsDeciderUtil` 的同名静态方法实现」。
两种修法都只动文字，不触数据红线。建议补入 MODIFICATIONS.md「②Apollo 工程事实」类，与 round01 A-1 串成同一条「11.0 版本一致性：重构后类名统一加注脚或收敛到 Util」整改线。

---

## minor（建议）

### A-2【文风 / Apollo 工程事实】Apollo 类名在正文与摘要之间 `\texttt` / 裸排仍混用（round01 A-8 → round02 A-3 未完全清理，第三轮仍在）

类别：文风。改文字能修。

定位：仍有裸排正文类名——摘要第 97 行 `LaneFollowPath`；引言第 112 行 `STDrivableBoundary`、第 114 行 `LaneFollowPath`/`PiecewiseJerkPathOptimizer`/`Baseline`；**4.4 节子节标题第 405 行「经 STDrivableBoundary 注入速度二次规划」裸排**；理论节第 577 行 `STDrivableBoundary` 裸排；图注第 240 行 `STDrivableBoundary` 裸排。而正文绝大多数处（第 155、423、432、434、486、579、626 等）已统一 `\texttt`。
说明：同一稿内同名类两种字形，最扎眼的是子节标题第 405 行与理论节第 577 行（正文位置却无 `\texttt`）。
处置：约定「正文与子节标题类名统一 `\texttt`；摘要为版面整洁可裸排但需全摘要一致」。重点清理第 405、577、240 三处。纯格式，不涉事实。本条已是第三轮跟进，建议本轮一次清干净。

### A-3【叙事 / Apollo 工程事实】摘要把系统匿名为「某生产级自动驾驶栈」，正文却通篇直呼 Apollo 11.0，匿名口径自相矛盾

类别：叙事。改文字能修。

定位：摘要第 97 行「MIKU 以增量方式接入**某生产级自动驾驶栈**的路径边界构建环节」；而标题页第 88 行署单位、引言第 106/114 行及全文方法/理论/实验节均直书 `Apollo 11.0`、`Apollo EM Planner`、具体类名。
说明：若投稿期刊要求双盲，正文已大面积暴露 Apollo 与具体类名，摘要单独匿名既无效也不一致；若非双盲，则摘要也应直书 Apollo 以与正文统一。当前是「半匿名」，Apollo 熟手一眼能识别，反显刻意。
处置（改文字能修）：与目标期刊投稿策略对齐二选一——(a) 非双盲：摘要第 97 行「某生产级自动驾驶栈」改为「Apollo 11.0 生产级自动驾驶栈」，与正文一致；(b) 双盲：正文/摘要统一匿名（工作量大，且类名难匿，通常不现实）。建议 (a)。本条是叙事一致性，不涉源码事实。

### A-4【Apollo 工程事实】第 247 行 `nudge_l_buffer` 的静态/非静态二分应点明对应的是 `static_/nonstatic_obstacle_nudge_l_buffer` 两个独立 flag，而非 `obstacle_lat_buffer`

类别：Apollo 工程事实。改文字能修。

定位：第 247 行「其上仅有的分级来自 `nudge_l_buffer` 以 0.5 m/s 速度阈值所做的静态与非静态二分，静态障碍物取 0.3 m、非静态取 0.4 m」。
核对：数值与阈值全部属实——`static_obstacle_nudge_l_buffer=0.3`、`nonstatic_obstacle_nudge_l_buffer=0.4`、`static_obstacle_speed_threshold=0.5`（`planning_gflags.cc:138/140/186`，使用见 `obstacle.cc:463/759`、`sl_polygon.cc:210`）。唯一可改进处：稿件前一句（第 247 行）刚说 `GetBufferBetweenADCCenterAndEdge` 返回「半车宽再加固定额外缓冲」，该固定缓冲是 `obstacle_lat_buffer`（0.4），与此处做静态/非静态二分的 `*_nudge_l_buffer` 是**两组不同 flag、走不同代码路径**（前者在 path bounds 的 ADC-edge buffer，后者在 SL polygon / obstacle nudge 判定）。稿件把两者并置叙述时未点明是不同参数，易让 Apollo 熟手误以为「固定 0.4 缓冲」与「非静态 0.4 nudge」是同一个量。
处置（改文字能修）：在第 247 行点一句「此处的速度二分缓冲由 `static_/nonstatic_obstacle_nudge_l_buffer` 控制，与前述 `obstacle_lat_buffer` 分属不同参数」，或把两句的缓冲来源分别注明。事实数值不动，仅澄清参数归属。

### A-5【Apollo 工程事实 / 确认项】`STBoundsDecider`（ST 边界）与 `SpeedBoundsDecider`（速度边界）系不同 Task，稿件区分正确，提醒整合编辑勿误改

类别：Apollo 工程事实（确认，无需改）。

定位：第 386、423、579 行用 `STBoundsDecider`（走廊承载结构 `STDrivableBoundary` 的原生生产者 + DP 消费），第 155、408、425、432、434、626 行用 `SpeedBoundsDecider`（ST 图 s 上下界）。
核对：源码确为两个独立 Task——`STBoundsDecider`（`tasks/st_bounds_decider/`，产 `SetSTDrivableBoundary`，默认仅 DP 消费）、`SpeedBoundsDecider`（`tasks/speed_bounds_decider/`，经 `st_boundary_mapper` 产 lower/upper STPoint 供 QP）。稿件二者区分正确、驼峰规范，符合 D 节。**此条仅作确认，无需改**；提醒整合编辑切勿在批量替换时把二者混为一谈或互改。

---

## 与前几轮的对照

- round01 三条 major（A-1 基线类名版本错配、A-2 STDrivableBoundary 原生链路、A-9 OSQP 过强断言）→ round02 已确认全部修复，本轮再次复核仍成立，未回退。
- round02 两条 major（A-1 走廊产出方横跳、A-2 STDrivableBoundary↔𝒯 接口说不清）→ **本轮确认 v3 已全部修复**，源码逐项复核通过，非幻觉式处置（第 423、434 行落点单一化）。
- round02 minor A-5/A-6/A-7 → **本轮确认已修**（0.1 s 注脚、SpeedDecider 让行措辞、Python/C++ 数据源切割）。
- 本轮新 major A-1（`PathBoundsDecider` 类名版本一致性）与 round01 A-1（`PiecewiseJerkPathOptimizer`）**同型未尽**：v3 修了优化器、漏了边界决策器。本质是同一条「11.0 重构后类名一律加注脚或收敛到 Util」整改线尚未覆盖全部重构掉的类名。
- 本轮 minor A-2（`\texttt`/裸排混用）是 round01 A-8 → round02 A-3 的**第三轮遗留**，建议本轮一次清净，避免再带入 round04。

数据红线核对：本轮所有意见均为「改文字能修」，无一条需新实验或改数字。通过率（压力 0/4 vs 4/4、汇总 4/8 vs 8/8）、平均速度（3.53→4.57，提升 29.3%）、QP 耗时（可比 19.16→6.26、汇总 21.56→5.56、C2 离群 56.41 vs 3.17、C1 反慢 10.44 vs 12.53）、消融（M5=100、M4=99.18、其余 <38）、灵敏度（最坏翻转 57%、最大偏差 6.4%、越界 0）均与 SPEC B 节冻结值逐字一致，未见外推或美化。

---

SCORE: P0=0 major=1 minor=4
