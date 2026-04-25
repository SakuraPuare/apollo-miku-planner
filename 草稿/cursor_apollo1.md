# 撰写基于Apollo的路径规划论文大纲
_Exported on 2025/11/25 at GMT+8 23:45:04 from Cursor (2.1.26)_

---

**User**

# 撰写基于Apollo的路径规划论文大纲



_Exported on 2025/11/25 at GMT+8 23:40:30 from Cursor (2.1.26)_

---

**User**

# Generate a name for the prompt

_Exported on 2025/11/25 at GMT+8 23:28:57 from Cursor (2.1.26)_

---

**User**

现在我想撰写一篇标题为《基于Apollo的多障碍物场景下路径规划算法实现》的毕业论文

我的论文架构应该是如下的

必要性

国内外研究现状

原有算法

当前问题

提出的算法

算法实现

算法对比

结论与展望

请你帮我分析 有哪些是需要阅读 Apollo源代码 来获得的 需要获得哪些信息

有哪些是需要通过文件来获得的 我的关键词应该是什么 

---

**Cursor**

下面按论文大纲逐项说明需要从 Apollo 源码了解的内容、需查阅的资料类型，以及可用的关键词，帮你明确调研范围。

必要性  

- **信息来源**：行业报告、自动驾驶白皮书、政策规范、道路安全统计等公开资料。  

- **关键词建议**：`自动驾驶 复杂场景 安全需求`、`多障碍物 规划必要性`、`Apollo 落地案例`。

国内外研究现状  

- **信息来源**：学术论文、期刊、会议（IV、IROS、ITSC 等）以及 Apollo 官方博客/技术分享。  

- **关键词建议**：`multi-obstacle path planning`、`Apollo planning research`、`自动驾驶 规划 对比`。

原有算法  

- **需查 Apollo 源码**：了解 Apollo 默认规划框架（如 EM planner、Lattice planner、Hybrid A* 等）的实现流程、模块划分和核心数据结构。  

- **源码关注点**：`modules/planning` 下的 `planner_*`、`path_decider`、`obstacle`、`reference_line` 等关键目录。  

- **关键词建议**：`Apollo EM planner 源码`、`apollo planning_obstacle`、`lattice planner implementation`。  

- **其他资料**：Apollo 技术文档、官方 PPT/视频，帮助梳理算法思路。

当前问题  

- **需查 Apollo 源码 + 文献**：梳理现有算法在多障碍物或复杂道路下的局限（如计算耗时、路径平滑性、障碍物交互处理）。  

- **关键词建议**：`Apollo planner limitations`、`多障碍物 场景挑战`、`planning latency apollo`。  

- **资料来源**：社区 issue、开源讨论、实验数据或自己复现实验的记录。

提出的算法  

- **信息来源**：依据你自己的研究构想，需要引用的主要是已有方法的不足与对比；可参考相关论文或算法框架文献。  

- **关键词建议**：根据方案特点给出，如 `强化学习 路径规划`、`图搜索 多障碍物`、`MPC 决策` 等。

算法实现  

- **源码必要性**：需要理解 Apollo 的模块接口（如如何接入新的 `planner` 类、ROS message/Proto 定义、配置文件等）。  

- **查阅位置**：`modules/planning/planner/`、`conf/planning_config.pb.txt`、`cyber` 通信、`modules/common/math` 等。  

- **关键词建议**：`Apollo planner plugin`、`planning_config`、`path_boundary`、`reference_line_info`。  

- **资料来源**：Apollo开发者手册、代码注释、编译/运行文档。

算法对比  

- **信息来源**：实验结果、仿真日志、benchmark 数据。若要与 Apollo baseline 对比，需要跑仿真或分析 `planning` 输出日志。  

- **关键词建议**：`Apollo planning log analysis`、`dreamview simulation`、`planning metrics`。  

- **需要文件**：仿真配置、测试场景描述、输出日志（如 `apollo/data/log`）。

结论与展望  

- **信息来源**：前面章节的归纳外加行业趋势、Apollo 开发路线图。  

- **关键词建议**：`Apollo roadmap`、`自动驾驶 规划 趋势`、`多障碍物 场景 展望`。

总结  

1. **必须读 Apollo 源码的部分**：原有算法、当前问题、算法实现（包括接口与模块协作）。重点是 `modules/planning` 目录下的代码、配置和数据结构。  

2. **主要靠外部／文件资料的部分**：必要性、国内外研究现状、提出的算法背景、对比时的实验数据整理、结论展望。需要查阅论文、官方文档、仿真日志等。  

3. **关键词**：上面按章节列出，可依研究方向再细化（如具体算法名、障碍物类型、仿真平台等）。

这样分工后，你可以先把需要深入阅读 Apollo 源码的块划出，建立笔记，再结合文献和实验数据完成论文结构。

---

**User**

现在问题是这样的 apollo的 路径生成分为两大块 routing 和 planning

routing 负责大方向的路径生成  也就是走什么路

planning 负责小方向的路径生成  也就是怎么走

---

**Cursor**

你的理解是正确的：Apollo 的路径生成确实可分为 `Routing` 和 `Planning` 两个主要模块。

- `Routing`：负责宏观路径规划，根据地图和交通规则生成从起点到终点的全局路线，即“走哪条路”。可以视为导航路径，输出路段序列或参考线。

- `Planning`：在 routing 给出的参考线基础上，根据实时感知与预测结果，细化每一刻的车辆轨迹，即“怎么在这条路上走”，包含速度规划、障碍物避让、局部决策等。

在撰写论文时：

- 如果你要分析“多障碍物场景下路径规划算法”，重点应放在 `Planning` 模块（尤其是 path planning 与 speed planning 的协同）如何处理障碍物、生成轨迹。

- `Routing` 可作为背景或前置条件描述，不需要特别深入，只需说明它提供全局参考线与车道信息，供 `Planning` 使用。

后续如需具体说明 `Planning` 的代码结构或模块职责，可以继续细化到 `task`、`decider`、`optimizer` 等子模块。

---

**User**

那我论文应该如何进行构造 请帮我撰写论文的大纲

---

**Cursor**

可以围绕“Routing 提供全局路径、Planning 在多障碍物场景下做局部轨迹优化”来展开，建议大纲如下（可直接用于毕业论文）：

1. 引言（必要性与研究背景）  

- 自动驾驶多障碍物场景的复杂性与安全需求  

- Apollo 作为研究平台的优势与应用场景  

- 研究目标与贡献概述（如：提出改进算法、实验验证）

2. 国内外研究现状  

- 多障碍物路径规划主流方法（图搜索、采样、优化、学习等）  

- Routing 与 Planning 的典型框架对比  

- Apollo 相关研究与业界实践进展

3. Apollo 路径规划系统概述  

- Apollo 规划架构：Routing、Planning、Prediction、Control 等关系  

- Routing 模块：地图、道路拓扑、路径决策流程  

- Planning 模块：任务流、决策/规划/优化子模块（例如 EM、Lattice、Decider、Optimizer）

4. 原有算法与存在问题  

- Apollo 基准算法（如 EM Planner、Lattice Planner、Hybrid A* 等）的实现思路  

- 多障碍物场景中暴露的问题（计算开销、障碍物交互、局部最优、速度耦合等）  

- 实际案例或仿真日志分析（引用 Apollo 源码/日志说明问题）

5. 提出的算法与改进思路  

- 设计目标：提升避障能力、提高实时性、增强轨迹平滑等  

- 算法整体框架（如优化模型、约束、目标函数或学习策略）  

- 与 Apollo 现有模块的接口方式（替换/增补哪些 task、decider、optimizer）

6. 算法实现与系统集成  

- 模块实现细节：数据流、关键数据结构、重要函数（引用源码位置）  

- 与 Routing、Prediction、Control 的交互关系  

- 算法复杂度分析、参数设置、软件环境及硬件配置

7. 实验设计与结果对比  

- 测试场景：仿真环境、真实道路、障碍物配置  

- 评价指标：路径长度、时间、平滑度、碰撞率、计算延迟等  

- 对比方案：Apollo 基准规划器 vs 提出算法  

- 实验结果分析与可视化（图表、轨迹图）

8. 结论与展望  

- 研究成果总结（算法优势、适用场景）  

- 局限性与改善方向（更复杂的动态障碍、多车协同、学习驱动等）  

- 未来研究计划（与高精地图结合、与控制/感知协同优化等）

附录（可选）  

- 关键公式推导  

- 参数表、配置文件  

- 代码目录说明或运行脚本

按此结构可逐章填充：先铺垫背景与现状，再详述 Apollo 的架构和现有算法问题，接着引出你的改进方案及实现细节，最后通过实验对比支撑结论。

---

**User**

但是你给出的框架 Apollo 基准算法（如 EM Planner、Lattice Planner、Hybrid A* 等）的实现思路 这些都是routing中的 planning的路径规划指的是在参考线上的路径生成 是凸优化问题

---

**Cursor**

你说得对：在 Apollo 的规划系统里，常提到的 EM Planner、Lattice Planner、Hybrid A* 等算法确实属于 `Planning` 模块，负责在 routing 提供的参考线附近进行局部路径与速度联合规划。它们主要通过凸优化或图搜索+优化的组合来生成满足约束的轨迹，并非 routing 层面的全局路径搜索。因此在论文中可这样定位：

- Routing：仍是基于地图拓扑的路径搜索，输出参考线（road segment 序列）。这一层通常不涉及 EM/Lattice 等算法，而是采用更经典的图搜索（A*、Dijkstra）或基于导航的路径。

- Planning：针对 routing 给出的参考线，在 Frenet 或 SL 坐标系中求解车辆路径与速度。EM、Lattice、Hybrid A* 等都在此层执行，问题形式多为凸优化或分层优化（path/speed）并结合障碍物约束。

所以在“原有算法”章节应聚焦 Planning 层的凸优化问题（如 EM Planner 中的路径 QP、速度 QP、决策任务流），说明它们如何在参考线附近生成轨迹以及对应的数学建模。Routing 只需简述其职责即可。

---

**User**

所以请重新帮我构造

---

**Cursor**

可以围绕“Routing 只负责参考线，Planning 在参考线附近做凸优化轨迹”来重构论文大纲，建议如下：

1. 引言  

- 多障碍物场景的复杂性与安全需求  

- Apollo 作为实验平台的优势及研究动机  

- 论文目标：在现有 Planning 框架内提出改进算法并验证

2. 背景与相关工作  

- 国内外多障碍物局部路径规划方法（凸优化、图搜索、混合策略、学习方法）  

- 自动驾驶系统中 Routing 与 Planning 的典型划分  

- Apollo Planning 相关研究与实践案例

3. Apollo 规划系统概述  

- 系统架构：Routing、Prediction、Planning、Control 的数据流  

- Routing 功能：基于高精地图的全局路径搜索（简述即可）  

- Planning 任务分层：`task/decider/optimizer` 结构、Frenet/SL 表达方式、与感知/预测的接口

4. Apollo 基准规划算法及问题分析（重点在 Planning）  

- EM Planner：路径/速度两阶段凸优化(QP)，参考线附近的轨迹生成策略  

- Lattice Planner：离散采样+目标轨迹拼接的图搜索方法  

- Hybrid A* / 其他优化器：低速或特殊场景下的搜索优化结合  

- 多障碍物场景中的局限：障碍交互建模、计算延时、速度/路径耦合、可行域收缩等  

- 结合源码与日志的案例说明（引用 `modules/planning` 相关子模块）

5. 改进算法设计  

- 设计目标：提升多障碍物避让能力、提高鲁棒性或实时性  

- 数学建模：目标函数、约束、变量（明确凸优化形式或其它框架）  

- 与 Apollo Planning 接口：在哪个 task/decider/optimizer 中接入，数据结构与 Proto 说明  

- 若涉及多阶段/分层求解，描述各阶段流程与信息交换

6. 算法实现与系统集成  

- 模块化实现：关键类、函数、配置文件（引用源码路径）  

- 数据流与状态机：如何利用感知/预测输出、如何写回规划结果  

- 复杂度与实时性分析、参数调优策略、运行环境

7. 实验与结果  

- 场景设置：仿真环境、障碍物配置、起终点参考线、测试路线  

- 评价指标：轨迹安全性、平滑度、耗时、最小距离、碰撞率等  

- 对比基线：Apollo 原有 EM/Lattice 等规划器  

- 实验结果展示与分析（图表、轨迹可视化、日志片段）

8. 结论与展望  

- 研究成果总结：算法优势、适用场景  

- 局限性：对预测依赖、特殊场景未覆盖等  

- 展望：更复杂交通互动、学习/预测耦合、与控制协同优化等

附录（可选）  

- 关键公式推导、QP 约束矩阵  

- 参数表、配置文件示例  

- 运行/复现实验指南

此结构凸显了 Planning 层的凸优化本质：Routing 只提供参考线，核心篇幅集中在现有规划算法分析与改进方案，方便结合 Apollo 源码与实验数据撰写。

根据以上内容 请你详细调研代码库 帮我分点撰写我需要的资料和文档 以便我参考

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

## 路由（Routing）资料卡

- 模块定位：`routing_component.cc` 展示了组件加载配置、创建 QoS Writer、周期性写入历史路由以及调用核心 `routing_` 对象完成 A* 搜索，适合写“Routing 提供参考线”的工程描述  

```29:95:modules/routing/routing_component.cc

bool RoutingComponent::Init() {

  RoutingConfig routing_conf;

  ACHECK(cyber::ComponentBase::GetProtoConfig(&routing_conf));

  ...

  return routing_.Init().ok() && routing_.Start().ok();

}

```

- 参数来源：`modules/routing/conf/routing_config.pb.txt` 提供速度、转弯惩罚、话题名等，可引用为“路由代价函数/通信配置”。  

- 框架概述：`modules/routing/README_cn.md` 与 `modules/routing/graph/*.cc` 解释拓扑图构建、黑名单、A* 策略，结合关键词 `routing topo_graph`, `routing_strategy`。

- 论文章节对应：第3章概述时引用上面文件，强调 Routing 仅输出车道序列与参考线，关键词建议 `Apollo routing map`, `routing_response_topic`, `拓扑图 A*`。

## 规划总体架构与接口

- 组件流程：`planning_component.cc` 说明 Init/Proc 逻辑、订阅内容、写回轨迹、重新路由触发，适合用于“系统架构/接口”段落。  

```44:237:modules/planning/planning_component/planning_component.cc

bool PlanningComponent::Init() {

  injector_ = std::make_shared<DependencyInjector>();

  ...

  planning_writer_ = node_->CreateWriter<ADCTrajectory>(

      config_.topic_config().planning_trajectory_topic());

}

```

- Topic/模式：`planning_component/conf/planning_config.pb.txt` 中的 `topic_config`、`learning_mode`、参考线类可用于描述输入输出与学习模式选择。  

- 官方文档：`docs/08_Planning/planning_component.md` 提供模块图、消息流，作为文字引用说明 Planning 处理流程与 Scenario/Task 管理。

- 关键词：`PlanningComponent topic`, `DependencyInjector`, `planning_learning_mode`, `Dreamview 模块`.

## 基准规划算法（凸优化/采样/开空间）

- Lattice/Path-Time 典型实现：  

```95:373:modules/planning/planners/lattice/lattice_planner.cc

auto ptr_path_time_graph = std::make_shared<PathTimeGraph>(

    ptr_prediction_querier->GetObstacles(), *ptr_reference_line,

    reference_line_info, init_s[0],

    init_s[0] + FLAGS_speed_lon_decision_horizon, 0.0,

    FLAGS_trajectory_time_length, init_d);

```

  描述 Frenet 转换、轨迹采样、约束/碰撞检查、备份轨迹触发。关键词 `PathTimeGraph`, `TrajectoryEvaluator`, `CollisionChecker`。

- QP 凸优化资料：  

```1:52:docs/08_Planning/qp_spline_path_optimizer_cn.md

# 二次规划（QP）样条路径优化

... cost = Σ w1∫(f′)^2 + w2∫(f″)^2 + w3∫(f‴)^2

```

  结合 `planning_base/math` 下的 piecewise jerk/ spline 代码可写 EM 风格路径/速度分阶段 QP。

- 参考线平滑：  

```1:45:modules/planning/planning_component/docs/reference_line_smoother_cn.md

x = f_i(t) = a_{i0} + ... + a_{i5} t^5; y = g_i(t) = ...

```

  用于说明参考线前处理的凸优化建模。

- Open Space 场景：`docs/08_Planning/Open_Space_Planner.md`、`planning_open_space/*` 描述 Hybrid A* + QP 二阶段，实现倒车/窄路情形，关键词 `open_space ROI`, `hybrid A* raw trajectory`.

- 速度优化：`docs/08_Planning/planning_speed_bounds_decider.md`、`planning_piecewise_jerk_nonlinear_speed_optimizer.md`（非线性版本）解释 ST 边界构造与速度限制。

- 建议章节引用：第4章“原有算法”引用上述源码，突出“参考线坐标系内凸优化 + 障碍约束”。

## Task / Scenario / 多障碍物处理

- PathDecider：  

```50:232:modules/planning/tasks/path_decider/path_decider.cc

if (obstacle->Id() == blocking_obstacle_id &&

    !injector_->planning_context()->planning_status()

         .path_decider().is_in_path_lane_borrow_scenario()) {

  *object_decision.mutable_stop() = GenerateObjectStopDecision(*obstacle);

}

```

  适合作为“多障碍物判定”代码证据，说明 STOP/Nudge/Ignore 逻辑、PlanningContext 记忆。

- SpeedBounds/ST：`modules/planning/tasks/speed_bounds_decider`、`st_bounds_decider`、`path_time_heuristic` 为多障碍速度约束资料来源；借助 `docs/08_Planning/planning_speed_bounds_decider.md` 文字说明。

- Scenario Manager：`modules/planning/planners/public_road/public_road_planner.cc` + `planners/public_road/conf/planner_config.pb.txt` 列出 11 种 Scenario，方便第4章“状态机”描述。

- `modules/planning/scenarios/*`：可点出 `lane_follow`, `traffic_light`, `pull_over` 下的 Stage/StageConfig 以分析特定复杂场景；关键词 `ScenarioStatusType`, `StageContext`, `lane_follow_command`.

- `planning_open_space/*`：讨论停车/倒车等多障碍特殊场景，强调 ROI、Hybrid A*、QP 平滑。

- 日志/实验：`data/log`、`data/bag`、`dreamview` Replay；`docs/08_Planning/planning_and_control_simulation.md` 说明仿真步骤，可为“算法对比”章节的实验描述来源。

- 关键词集合：`path_decision blocking`, `STBoundary keep_clear`, `PlanningContext rerouting`, `Dreamview simulation metrics`.

## 论文大纲与资料映射

| 章节 | 需读源码/文档 | 获取信息 | 建议关键词 |

| --- | --- | --- | --- |

| 必要性/背景 | `docs/08_Planning/planning_and_control_simulation.md`, `README.md`, 行业报告 | 场景复杂性、Apollo 应用示例 | `自动驾驶 多障碍`, `Dreamview simulation` |

| 国内外研究现状 | 论文库 + `docs/08_Planning/Open_Space_Planner.md` 等 | 主流算法、Apollo 最新实践 | `multi-obstacle path planning`, `Scenario-based planning` |

| Apollo 系统概述 | `routing_component.cc`, `planning_component.cc`, `planning_component.md` | Routing vs Planning 职责、消息流 | `routing_response_topic`, `planning_trajectory_topic` |

| 原有算法 | `lattice_planner.cc`, `planning_component/docs/reference_line_smoother_cn.md`, `qp_spline_path_optimizer_cn.md`, `planning_speed_bounds_decider.md` | Frenet/QP/采样算法流程、凸优化模型 | `PathTimeGraph`, `QP spline`, `piecewise jerk` |

| 当前问题 | `tasks/path_decider`, `speed_bounds_decider`, `planning_context` 状态、`data/log` | 多障碍重叠、计算耗时、 rerouting 触发 | `blocking obstacle`, `rerouting`, `planning latency` |

| 提出算法/实现 | 依据自研方案，参考 `planning_interface_base`, `planning_component/conf` 接口 | 如何接入新 planner/task、proto 定义 | `planner plugin`, `task_base`, `planning_config` |

| 算法对比/实验 | `dreamview` 仿真、`planning_and_control_simulation.md`, `data/log`、`modules/tools` | 仿真步骤、指标、日志位置 | `planning log analysis`, `PNC simulation`, `trajectory_debug` |

| 结论展望 | Apollo 路线图（社区 issue/README）、Scenario 扩展文档 | 行业趋势、未来方向 | `Apollo roadmap`, `scenario-based planning future` |

## 下一步建议

- 建立“源码摘录 + 论文章节”对照笔记，按上表逐项收集截图/公式。

- 仿真阶段利用 Dreamview PNC Simulation 记录 `planning` topic、`debug.planning_data`，作为“算法对比”附录。

- 若需更细粒度的凸优化推导，可继续阅读 `modules/planning/planning_base/math` 下的 `piecewise_jerk` 与 `discrete_points_smoothing`。

以上内容均围绕 Apollo Routing/Planning 源码与官方文档整理，可直接引用到《基于Apollo的多障碍物场景下路径规划算法实现》各章节。

```plaintext

bool RoutingComponent::Init() {

  RoutingConfig routing_conf;

  ACHECK(cyber::ComponentBase::GetProtoConfig(&routing_conf));

  ...

  return routing_.Init().ok() && routing_.Start().ok();

}

```

```plaintext

bool PlanningComponent::Init() {

  injector_ = std::make_shared<DependencyInjector>();

  ...

  planning_writer_ = node_->CreateWriter<ADCTrajectory>(

      config_.topic_config().planning_trajectory_topic());

}

```

```plaintext

auto ptr_path_time_graph = std::make_shared<PathTimeGraph>(

    ptr_prediction_querier->GetObstacles(), *ptr_reference_line,

    reference_line_info, init_s[0],

    init_s[0] + FLAGS_speed_lon_decision_horizon, 0.0,

    FLAGS_trajectory_time_length, init_d);

```

```plaintext

# 二次规划（QP）样条路径优化

... cost = Σ w1∫(f′)^2 + w2∫(f″)^2 + w3∫(f‴)^2

```

```plaintext

x = f_i(t) = a_{i0} + ... + a_{i5} t^5; y = g_i(t) = ...

```

```plaintext

if (obstacle->Id() == blocking_obstacle_id &&

    !injector_->planning_context()->planning_status()

         .path_decider().is_in_path_lane_borrow_scenario()) {

  *object_decision.mutable_stop() = GenerateObjectStopDecision(*obstacle);

}

```

根据以上内容 撰写完整的文档 详细讲述算法 和 原理

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

## 全文结构与参考资料

### 1. 引言与研究必要性
- **多障碍物场景动机**：Apollo 规划模块通过 Cyber RT 组件订阅感知、预测、底盘与定位消息，在每个周期输出平滑轨迹，目标是保证安全、舒适与可行性。`PlanningComponent::Proc()` 展示了输入融合、重规划触发与轨迹发布过程，可直接引用说明局部规划是实时在线的苛刻任务。  
```132:266:modules/planning/planning_component/planning_component.cc
ADCTrajectory adc_trajectory_pb;
planning_base_->RunOnce(local_view_, &adc_trajectory_pb);
...
planning_writer_->Write(adc_trajectory_pb);
```
- **Routing 提供宏观约束**：`RoutingComponent::Init/Proc` 负责读取 `routing_config`、创建 QoS Writer 并周期性写入历史路由，说明 routing 输出的是车道序列和参考线主题，可在引言中强调“全局路网 → 本地轨迹”的职责分层。  
```29:95:modules/routing/routing_component.cc
bool RoutingComponent::Init() {
  RoutingConfig routing_conf;
  ...
  return routing_.Init().ok() && routing_.Start().ok();
}
```
- **资料来源建议**：行业报告/事故统计（说明必要性）、Apollo 发布案例（Dreamview 仿真、PNC Simulation 文档），关键词：`自动驾驶 多障碍`, `Apollo routing_response`, `planning_trajectory_topic`。

### 2. 国内外研究现状与Apollo背景
- **Routing vs. Planning 框架**：`docs/08_Planning/planning_component.md` 的流程图展示 Reader/Writer 关系，可用于对比传统规划架构与 Apollo 实现。  
```19:33:docs/08_Planning/planning_component.md
Messages are partially input from readers… PlanningComponent output the message by …
```
- **主流算法综述**：结合学术文献列出图搜索（A*/Hybrid A*）、采样（Lattice）、凸优化（QP/非线性 jerk）、学习型（E2E）。Apollo 的 scenario-based 体系与这些方法对应，可引用 `public_road_planner` 中 scenario manager 的流程。  
```28:66:modules/planning/planners/public_road/public_road_planner.cc
scenario_manager_.Update(planning_start_point, frame);
scenario_ = scenario_manager_.mutable_scenario();
...
auto result = scenario_->Process(planning_start_point, frame);
```
- **关键词**：`multi-obstacle path planning`, `scenario-based planning`, `Hybrid A* autonomous parking`.

### 3. Apollo 路径规划系统概述
1. **整体数据流**  
   - Routing 输出参考线主题：`routing_response_topic`、`routing_response_history_topic`。  
   - Planning 订阅预测/底盘/定位等 6+ 主题，并写 `planning_trajectory`。  
   - 说明 `DependencyInjector` 如何注入 `PlanningContext`、`History`、`LearningData`。

2. **Routing 工作流**  
   - 引用 `routing_component.cc` 描述加载配置、QoS 设置、调用 A*，强调“决定走哪条路”。

3. **Planning 工作流**  
   - `PlanningComponent::Init` 中 Reader/Writer 列表可作为表格，说明消息接口。  
   - `CheckInput()` 展示对定位、底盘、地图、命令的就绪检查，可突出系统安全冗余。  
   - `SetLocation()` 填充轨迹位姿信息，可解释输出消息字段。

4. **场景/Task 管理**  
   - `public_road_planner` + `scenario_manager`：两层状态机（Scenario → Stage → Task）。  
   - 说明 `planning_config.pb.txt` 可启用不同 planner/学习模式。

### 4. 原有规划算法（凸优化与采样）
1. **参考线平滑 (Reference Line Smoother)**  
   - 文档展示二维样条 + QP 目标函数 `∫(f'''^2 + g'''^2)`，用于将 routing 输出的离散路线变为可微参考线。  
```1:38:modules/planning/planning_component/docs/reference_line_smoother_cn.md
x = f_i(t) = a_{i0} + ... + a_{i5} t^5
...
cost = Σ ∫(f_i'''(t))^2 + ∫(g_i'''(t))^2
```
2. **EM / QP 样条路径**  
   - `qp_spline_path_optimizer_cn.md` 给出 station-lateral 坐标下的 5 次样条、`w1∫(f′)^2 + w2∫(f″)^2 + w3∫(f‴)^2` 目标函数与等式、不等式约束（起终点、平滑节点、采样点安全边界）。  
```1:145:docs/08_Planning/qp_spline_path_optimizer_cn.md
cost = Σ w1∫(f_i')^2 + w2∫(f_i'')^2 + w3∫(f_i''')^2
```
3. **Lattice Planner (采样+组合)**  
   - `lattice_planner.cc` 展示 Frenet 初值计算、PathTimeGraph 构建、生成纵/横 1D 轨迹、通过 `TrajectoryEvaluator` 组合并调用 `CollisionChecker`。可用于描述“先采样再评估”的流程，并强调多障碍 ST 图的重要性。  
```95:375:modules/planning/planners/lattice/lattice_planner.cc
auto ptr_path_time_graph = std::make_shared<PathTimeGraph>(…);
Trajectory1dGenerator trajectory1d_generator(...);
TrajectoryEvaluator trajectory_evaluator(...);
```
4. **速度规划（Piecewise Jerk/NLP）**  
   - `planning_piecewise_jerk_nonlinear_speed_optimizer.md` 解释速度 QP/NLP 目标：满足速度/加速度/jerk 限制并兼顾舒适性，可添加 ST 图示说明。
5. **速度边界 (Speed Bounds Decider)**  
   - 文档描述三步：障碍映射到 ST，生成路径限速，设置搜索范围，为速度优化提供约束。

### 5. 现有算法在多障碍物场景的问题
- **障碍交互复杂度**：`PathDecider::MakeStaticObstacleDecision` 展示 STOP/Nudge 判断；在多障碍密集时会频繁触发 STOP 或 lane borrow，导致可行域缩小。  
```77:252:modules/planning/tasks/path_decider/path_decider.cc
if (obstacle->Id() == blocking_obstacle_id ...
  *object_decision.mutable_stop() = GenerateObjectStopDecision(*obstacle);
...
object_decision.mutable_nudge()->set_type(ObjectNudge::LEFT_NUDGE);
```
- **ST 边界重叠**：SpeedBoundsDecider 需要遍历所有障碍构建边界，障碍数量增加会放大计算开销与约束保守性。
- **Scenario 切换迟滞**：`public_road_planner` 需要 ScenarioStatus=Done 才切换，下游瓶颈可能导致策略滞后。
- **计算实时性**：Lattice 组合数量随障碍激增，`TrajectoryEvaluator` 可能评估大量 pair，带来延迟。

### 6. 提出算法与实现指引（示例模板）
> 根据你的研究方向填充，建议聚焦“多障碍凸优化增强”或“分层图优化+学习预测”：
- **设计目标**：如引入障碍耦合约束的柔性表述、减少 ST 边界保守度、引入障碍聚类。
- **数学模型**：在 Frenet 坐标构建联合目标（平滑+安全+实时），可复用 QP/SOCP 模式；若采用分布式优化，说明各子问题变量、约束。
- **系统接口**：说明接入点（如自定义 `Task` 或 `Optimizer`），需要修改 `modules/planning/conf/planning_config.pb.txt` 增加插件条目，引用 `planning_interface_base` 规范数据结构。
- **数据结构**：利用 `ReferenceLineInfo`、`PathDecision`、`StGraphData`，必要时扩展 `PlanningContext` 保存多障碍历史。
- **实现步骤**：  
  1. 在 `modules/planning/tasks/` 新增自定义任务；  
  2. 在 Scenario 配置中替换/插入任务；  
  3. 若需要额外输入，如障碍聚类结果，可通过 `frame` 注入。

### 7. 算法对比与实验方案
- **仿真工具**：`docs/08_Planning/planning_and_control_simulation.md`（Dreamview PNC Simulation），使用 `routing_request` 与场景地图（`data/map_data`）。
- **数据记录**：`planning_writer_` 输出 `ADCTrajectory`，可在 `data/log` 中抓取 `planning.INFO`、`debug.planning_data`；也可在 `modules/tools` 下利用 `plot_planning_result.py`。
- **评价指标**：路径安全余量、最小障碍距离、速度波动、规划延迟（从 `Clock::NowInSeconds()` 记录）、轨迹平滑度（jerk）。
- **对比流程**：Baseline 使用 EM/Lattice/Hybrid A*；改进算法在同一场景下统计指标，输出轨迹图/表格。

### 8. 结论与展望
- **总结**：回顾 Routing/Planning 分工、多障碍改进的收益（安全率、实时性、平滑度）。  
- **局限**：对预测精度依赖、鲁棒性测试不足、仿真与实车差异。  
- **未来方向**：Scenario 扩展（协同车流、交互式障碍）、学习结合优化、跨模态输入（Bird’s Eye View）等；参考 Open Space Planner 的场景化策略推动更多专用算法。

### 附录建议
- **公式与参数**：整理 QP/Hessian 构造、约束矩阵、任务权重表。  
- **配置文件**：列出 `planning_config.pb.txt` 中相关段落、`routing_config.pb.txt` 关键参数。  
- **运行脚本**：说明 `apollo.sh build_opt`, `bootstrap_lgsvl.sh`, `cyber_recorder` 使用方法。

---

这样整理后，你可直接按章节填充论文初稿：先引用上述代码/文档说明 Apollo 现状，再嵌入自研算法的建模与实验结果。若后续需要特定模块的更深源码解析（例如 `piecewise_jerk_path_optimizer` 具体矩阵构造、`speed_bounds_decider` 障碍投影细节），欢迎继续指出。

```plaintext
ADCTrajectory adc_trajectory_pb;
planning_base_->RunOnce(local_view_, &adc_trajectory_pb);
...
planning_writer_->Write(adc_trajectory_pb);
```

```plaintext
bool RoutingComponent::Init() {
  RoutingConfig routing_conf;
  ...
  return routing_.Init().ok() && routing_.Start().ok();
}
```

```plaintext
Messages are partially input from readers… PlanningComponent output the message by …
```

```plaintext
scenario_manager_.Update(planning_start_point, frame);
scenario_ = scenario_manager_.mutable_scenario();
...
auto result = scenario_->Process(planning_start_point, frame);
```

```plaintext
x = f_i(t) = a_{i0} + ... + a_{i5} t^5
...
cost = Σ ∫(f_i'''(t))^2 + ∫(g_i'''(t))^2
```

```plaintext
cost = Σ w1∫(f_i')^2 + w2∫(f_i'')^2 + w3∫(f_i''')^2
```

```plaintext
auto ptr_path_time_graph = std::make_shared<PathTimeGraph>(…);
Trajectory1dGenerator trajectory1d_generator(...);
TrajectoryEvaluator trajectory_evaluator(...);
```

```plaintext
if (obstacle->Id() == blocking_obstacle_id ...
  *object_decision.mutable_stop() = GenerateObjectStopDecision(*obstacle);
...
object_decision.mutable_nudge()->set_type(ObjectNudge::LEFT_NUDGE);
```

