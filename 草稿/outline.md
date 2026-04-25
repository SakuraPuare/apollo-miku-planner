## 论文大纲（结合已收集资料）

1. **引言与研究必要性**  
- 多障碍物场景对自动驾驶安全性的挑战、实时规划需求  
- Apollo 平台优势：Cyber RT 实时框架、完整 Routing→Planning→Control 链路  
- 研究目标：基于 Apollo Planning（凸优化路径）提出改进方案并验证

2. **国内外研究现状**  
- 图搜索、采样、凸优化、学习型局部规划方法的对比  
- Routing 与 Planning 分层架构的主流实践  
- Apollo Planning 相关研究与开源案例（Scenario-based、Open Space 等）

3. **Apollo 规划系统概述**  
- 系统数据流：Routing 输出参考线，Planning 订阅感知/预测/底盘/定位并发布 `ADCTrajectory`  
- Routing 模块：配置、拓扑图、A* 搜索、参考线主题  
- Planning 模块：组件初始化、DependencyInjector、消息接口、Scenario/Stage/Task 管理

4. **基准算法与凸优化流程**  
- 参考线平滑与样条建模（Reference Line Smoother）  
- PublicRoadPlanner路径-速度解耦两阶段优化（源自早期EM Planner思想）：QP 样条路径优化与速度 QP（Piecewise Jerk/NLP）
- Lattice Planner（备选规划器，适用于高速公路等简单场景）：Frenet 采样、Path-Time 图、碰撞检测
- Hybrid A* / Open Space Planner：低速场景、二阶段优化
- Speed Bounds Decider 与 ST 边界构建

5. **多障碍物场景暴露的问题**  
- PathDecider 在阻塞/借道场景的限制造成可行域缩小  
- ST 边界重叠导致速度规划保守、计算开销增大  
- Scenario 切换滞后、Lattice 组合爆炸引发实时性风险  
- 结合日志/源码的实际案例分析

6. **改进算法设计**  
- 设计目标（提升避障鲁棒性、降低计算量、柔性约束）  
- 数学建模：优化目标与约束、变量定义、凸/非凸求解策略  
- 系统集成点：自定义 Task/Optimizer、PlanningContext 扩展、配置修改  
- 与 Routing/Prediction/Control 接口的兼容性

7. **实现细节与集成流程**  
- 关键模块/类/函数的实现说明及源码位置  
- 数据流、状态机、参数配置、运行环境  
- 复杂度分析与实时调优策略

8. **实验设计与结果对比**  
- 仿真/实车场景设定（障碍物配置、参考线路、地图）  
- 评价指标：安全余量、平滑度、耗时、碰撞率、规划延迟等  
- 对比基线：Apollo PublicRoadPlanner（默认）/Lattice Planner/Hybrid A*  
- 结果展示：轨迹可视化、指标表格、日志分析

9. **结论与展望**  
- 研究成果总结及在多障碍物场景中的优势  
- 局限性：预测依赖、极端场景、实时性瓶颈  
- 未来方向：Scenario 扩展、学习-优化融合、协同路网/控制一体化

10. **附录（可选）**  
- 关键公式推导、QP 约束矩阵、参数表  
- 配置文件与运行脚本说明（`planning_config.pb.txt`、仿真步骤）