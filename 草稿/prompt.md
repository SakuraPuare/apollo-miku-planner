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


现在问题是这样的 apollo的 路径生成分为两大块 routing 和 planning

routing 负责大方向的路径生成  也就是走什么路
planning 负责小方向的路径生成  也就是怎么走


你的理解是正确的：Apollo 的路径生成确实可分为 `Routing` 和 `Planning` 两个主要模块。

- `Routing`：负责宏观路径规划，根据地图和交通规则生成从起点到终点的全局路线，即“走哪条路”。可以视为导航路径，输出路段序列或参考线。
- `Planning`：在 routing 给出的参考线基础上，根据实时感知与预测结果，细化每一刻的车辆轨迹，即“怎么在这条路上走”，包含速度规划、障碍物避让、局部决策等。

在撰写论文时：
- 如果你要分析“多障碍物场景下路径规划算法”，重点应放在 `Planning` 模块（尤其是 path planning 与 speed planning 的协同）如何处理障碍物、生成轨迹。
- `Routing` 可作为背景或前置条件描述，不需要特别深入，只需说明它提供全局参考线与车道信息，供 `Planning` 使用。

后续如需具体说明 `Planning` 的代码结构或模块职责，可以继续细化到 `task`、`decider`、`optimizer` 等子模块。