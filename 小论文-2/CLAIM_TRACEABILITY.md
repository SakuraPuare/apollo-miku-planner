# MIKU 主张可追踪表

本表把投稿主文中的理论、算法和实验主张映射到实现与自动证据。Apollo 已有的路径/速度 QP 是基础求解骨架；MIKU 的原创主张集中在候选组织、约束构造和双向信息传递。

| 主张 | 论文位置 | 实现 | 自动验证/数据 | 结论范围 |
|---|---|---|---|---|
| 自车中心语义下车宽只计入一次 | 式(1)、式(6) | `apollo_pipeline.py::_miku_path_bounds` | `test_feasibility_uses_centre_width_epsilon_not_vehicle_width` | 几何定义与实现一致 |
| $2^k$ 分配可由 $k+1$ 连续分割覆盖 | 引理3.1、定理3.1 | `miku_geometry.py::enumerate_lateral_bands`, `solve_max_gap` | 4,000 例与全枚举 oracle 一致 | 对论文区间模型精确 |
| 分层图精确 K-best 空间同伦保留 QP 回退候选 | 方法3.2、算法1 | `miku_geometry.py::enumerate_spatial_homotopies`, `apollo_pipeline.py::_miku_path_bounds` | 100 个随机分层图的 Top-3 与全枚举一致；A3：完整方法到达率高 `10.2 pp`, `p=1.363e-107` | 一阶跨组转移代价；当前 7 类随机分布 |
| 多冲突时间图满足站点因果关系 | 式(12)、方法3.3 | `miku_time.py::enumerate_temporal_homotopies` | `test_temporal_graph_enforces_causal_travel_between_conflicts` | 离散时间窗和速度上界模型 |
| 双向 ST 走廊表达先通过与后通过 | 式(13)--(14) | `build_st_bounds(..., safe_window_mode=True)` | before/after 单测与随机点集 oracle | 主 MIKU 默认启用 |
| 高排名时间候选不可行时回退 | 方法3.3、算法1 | `apollo_pipeline.py::run_pipeline` | 时间同伦 beam/排序测试，随机 A5 | 固定 beam 宽度 8 |
| 鲁棒占据传播有界预测误差 | 式(8)、鲁棒安全命题 | `Obstacle.uncertainty_*`, `st_boundary_mapper(..., robust_prediction=True)` | mapper 单测；A6 碰撞差 `-1.1 pp`, `p=1.455e-11` | 真实误差落在给定管内 |
| 曲线路径整段包络避免角点漏检 | 方法3.1 | `st_boundary_mapper` | 几何/ST 回归测试 | 离散采样及车辆 Minkowski 模型 |
| 固定同伦后保持凸 QP | 凸性命题 | `path_optimizer`, `speed_qp`, `build_st_bounds` | 约束均为逐点上下界；QP 回归测试 | 不主张跨同伦问题整体凸 |
| 按需交替细化修正到达时间 | 式(15)、算法1 | `run_pipeline` refinement branch | A7：`+0.8 pp`, `p=3.725e-09` | 初始求解+至多一次反馈细化，阻尼 0.7 |
| 滚动语义保持与先行承诺避免临近翻转 | 方法3.4 | `closed_loop.py` | `test_pass_before_commitment_survives_rolling_replanning`; 700 例滚动数据 | 规划器状态闭环 |
| 主实验到达率提升 | 摘要、实验4.2、结论 | 主实验脚本和方法注册 | 3,500 对：MIKU/B0 `77.5%/62.7%`, 差 `+14.8 pp`, CI `[13.5,16.0]`, `p=1.939e-133` | 公开随机生成分布 |
| 主实验碰撞率下降 | 摘要、实验4.2 | 真值几何评价 | MIKU/B0 `1.1%/2.2%`, 差 `-1.0 pp`, CI `[-1.4,-0.7]`, `p=2.91e-11` | 同上 |
| 关键模块具有独立贡献 | 实验4.4 | `run_randomized_ablation.py` | A2--A7 的配对 bootstrap 与 McNemar | A1 仅作初始化，不声称独立显著收益 |
| 滚动规划延续单周期收益 | 实验4.5 | `closed_loop.py`, rolling runner | 700 对：到达率差 `+10.0 pp`, CI `[7.6,12.6]`, `p=1.524e-15`; 碰撞率相同 | 不等同于实车全系统闭环 |
| 与联合网格参照到达率相当、计算显著更低 | 实验4.5 | `joint_reference.py`, joint runner | 70 对配对统计及 P95 完整规划耗时 | B3 是质量--开销参照，不是连续全局最优 |
| 威胁权重局部稳定 | 实验4.6 | `sensitivity_analysis.py` | ±20% 权重扰动；80 条完整轨迹均成功 | 局部权重稳定性 |

文献条目由 `references.bib` 与 LaTeX/Biber 构建共同检查；实验脚本不会修改论文中的理论表述。
