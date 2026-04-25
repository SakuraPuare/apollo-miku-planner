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

