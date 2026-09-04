# MIKU 主张可追踪表

本表把投稿主文中的理论、算法和实验主张映射到实现与自动证据。Apollo 已有的路径/速度 QP 是基础求解骨架；MIKU 的原创主张集中在候选组织、约束构造和双向信息传递。

| 主张 | 论文位置 | 实现 | 自动验证/数据 | 结论范围 |
|---|---|---|---|---|
| 自车中心语义下车宽只计入一次 | 式(1)、式(6) | `apollo_pipeline.py::_miku_path_bounds` | `test_feasibility_uses_centre_width_epsilon_not_vehicle_width` | 几何定义与实现一致 |
| $2^k$ 分配可由 $k+1$ 连续分割覆盖 | 引理3.1、定理3.1 | `miku_geometry.py::enumerate_lateral_bands`, `solve_max_gap` | 4,000 例与全枚举 oracle 一致 | 仅对固定截面区间模型精确；不外推到动态换序 |
| 分层图精确 K-best 空间同伦保留 QP 回退候选 | 方法3.2、算法1 | `miku_geometry.py::enumerate_spatial_homotopies`, `apollo_pipeline.py::_miku_path_bounds` | 100 个随机分层图的 K-best 与全枚举一致 | 仅对给定分层图精确；MIKU 认证路径使用全部正宽空间带 |
| 多冲突时间图满足站点因果关系 | 式(12)、方法3.3 | `miku_time.py::enumerate_temporal_homotopies` | `test_temporal_graph_enforces_causal_travel_between_conflicts` | 离散时间窗和速度上界模型 |
| 双向 ST 走廊表达先通过与后通过 | 式(13)--(14) | `build_st_bounds(..., safe_window_mode=True)` | 首/末安全窗端点单测；论文公式已改为 $b_i=t_i^- -\varepsilon_t$ 与 $a_i=t_i^+ +\varepsilon_t$ | 代码与安全窗语义一致；连续安全仍待验证 |
| 高排名时间候选不可行时回退 | 方法3.3、算法1 | `apollo_pipeline.py::run_pipeline`, `experiment_methods.py` | 时间图因果测试、候选连续证书测试 | 认证 MIKU 使用全部有限安全窗；直接 API 默认仍可设 beam=8 |
| 鲁棒占据传播有界预测误差 | 式(8)、鲁棒安全命题 | `Obstacle.uncertainty_*`, `_miku_path_bounds`, `st_boundary_mapper`, continuous certifier | 路径/ST 投影、恒加速度纵向/线性横向扫掠和候选 fail-closed 测试 | 仅当真值误差落入声明的有界管、且执行动力学/速度界成立时 |
| 曲线路径整段包络避免角点漏检 | 方法3.1 | `st_boundary_mapper` | 几何/ST 回归测试 | 离散采样及车辆 Minkowski 模型 |
| 固定同伦后保持凸 QP | 凸性命题 | `path_optimizer`, `speed_qp`, `build_st_bounds` | 约束均为逐点上下界；QP 回归测试 | 只说明固定标签子问题，不含候选安全性 |
| 按需交替细化修正到达时间 | 式(15)、算法1 | `experiment_methods.run_method` | A7：`+0.43 pp`, `p=.25` | 初始求解+至多一次反馈细化；效果不显著，不作独立贡献主张 |
| 有限联合同伦搜索与最优性 gap | 新算法接口 | `joint_homotopy_search.py::bounded_lazy_joint_search`, `experiment_methods.run_method` | 100 个随机域穷举、预算截断、下界反例；`randomized_raw.csv`/`closed_loop_raw.csv` 的 `joint_*` 字段 | 证书只相对于显式有限候选域；不宣称连续全局最优；主实验多数域实际只有 1 个候选，已如实保留 |
| 候选连续安全验证 | 新安全接口 | `validate_pipeline_candidate_continuous_safety`, `experiment_methods.run_method` | 二次纵向根 + 线性横向扫掠矩形测试；MIKU 候选 fail-closed | 仅在恒加速度纵向/线性横向执行契约和误差包络条件下证书化 |
| 滚动语义保持与先行承诺避免临近翻转 | 方法3.4 | `closed_loop.py` | `test_pass_before_commitment_survives_rolling_replanning`; 700 例滚动数据 | 工程承诺机制；不是递归可行性证明 |
| 主实验到达率提升 | 摘要、实验4.2、结论 | 主实验脚本和方法注册 | 700 对：MIKU/B0 `73.9%/60.3%`, 差 `+13.6 pp`, CI `[10.4,16.9]`, `p=2.10e-15` | 公开随机生成分布 |
| 主实验碰撞率下降 | 摘要、实验4.2 | 真值几何评价 | MIKU/B0 `0.43%/6.71%`, 差 `-6.29 pp`, CI `[-8.14,-4.57]`, `p=1.14e-13` | 同上；恒加速度扫掠检查更严格，总体差异不代表每个场景族均改善 |
| 关键模块具有独立贡献 | 实验4.4 | `run_randomized_ablation.py` | A2--A7 的配对 bootstrap 与 McNemar | A1 仅作初始化，不声称独立显著收益 |
| 滚动规划延续单周期收益 | 实验4.5 | `closed_loop.py`, rolling runner | 700 对：到达率差 `+14.3 pp`, CI `[10.9,18.0]`, `p=1.565e-14`; 碰撞差 `-0.57 pp`, CI `[-5.0,3.9]`, `p=.847` | 不等同于实车全系统闭环 |
| 联合网格诊断参照 | 实验4.5 | `joint_reference.py`, joint runner | 70 对：MIKU 比 B3 到达率高 `+28.6 pp`，碰撞低 `-35.7 pp`，差异显著 | B3 是自建粗网格、不同碰撞检查器，不是外部方法或全局最优 |
| 威胁权重局部稳定 | 实验4.6 | `sensitivity_analysis.py` | ±20% 权重扰动；80 条完整轨迹均成功 | 局部权重稳定性 |

文献条目由 `references.bib` 与 LaTeX/Biber 构建共同检查；实验脚本不会修改论文中的理论表述。
