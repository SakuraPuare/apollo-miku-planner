# MIKU 主张可追踪表

本表把最终稿中可验证的主张映射到公式、实现、测试和生成数据。“定理正确”与“经验性能改善”分开记录。

| 主张 | 论文位置 | 实现 | 自动验证/数据 | 允许的结论强度 |
|---|---|---|---|---|
| 道路和障碍物使用同一自车中心区间语义 | 方法“组内最大中心间隙”定义 | `apollo_pipeline.py::_miku_path_bounds` | `test_miku_geometry.py::test_feasibility_uses_centre_width_epsilon_not_vehicle_width` | 实现和几何定义一致；不单独推导安全率 |
| $2^k$ 避让分配可缩减为 $k+1$ 个连续分割 | 引理 3.1、定理 3.1 | `miku_geometry.py::solve_max_gap` | `test_miku_geometry.py`：20 种子、4,000 例与 $2^k$ 穷举一致 | 在文中区间模型与固定分割约束下精确 |
| 单组求解复杂度为 $O(k\log k)$ | 定理 3.1 及伪代码 | `miku_geometry.py` 排序+前缀最大扫描 | 穷举 oracle 与非单调反例 | 算法复杂度主张，不等于整个规划器端到端复杂度 |
| 纯动态全宽冲突交由 ST 层处理 | 方法“到达时间查询与动态冲突降级” | `apollo_pipeline.py` 中 `temporal_only` 分支 | `test_pure_dynamic_full_width_conflict_is_deferred_to_speed_stage` | 防止将时间冲突误作永久路径阻塞；不保证最终速度解一定到达 |
| C5 安全时窗数学运算正确 | 方法第 3.4 节负结果说明 | `miku_time.py`, `build_st_bounds(..., safe_window_mode=True)` | `test_miku_time.py`, `test_miku_time_oracle.py` | 可表达先/后通过与空集停车；不作为主方法贡献 |
| C5 在当前压力场景无独立正收益 | 随机实验“消融决策与限制” | `run_ablation.py` | `generated/ablation.csv/json`：M4/M5，P2 回归 | 从主 MIKU 关闭；不宣称时窗的性能贡献 |
| MIKU 在 600 个配对随机场景中相对 B0 的汇总到达率差为 +5.33 个百分点 | 摘要、实验主结果、结论 | `experiment_cases.py`, `experiment_methods.py`, `experiment_metrics.py` | `generated/randomized_*`；95% CI [1.67, 9.00] | 仅支持公开生成分布上的汇总差；改善由窄路类驱动 |
| 主实验不支持碰撞率下降 | 实验主结果 | `experiment_metrics.py::_safety_metrics` | B0/MIKU 碰撞率均 2.83%，`paired_statistics.csv` 差值 0 | 只报告可达性差，不宣称安全性提升 |
| 方法在动态时序类有负面边界 | 分场景差异与失效分析 | 同上 | 横穿行人 -17 pp，多动态交织 -24 pp | 一次 $\tau(s)$ 查询不能代替联合时空协调 |
| B3 子集提示可行性差异，但不能确立总体优势 | 联合参照补充实验 | `joint_reference.py`, `run_joint_reference_experiments.py` | `generated/joint_reference_*`：B3/MIKU 83.3%/70.0%，差 -13.3 pp，95% CI [-30.0, 3.3]；不一致对 5/1 | 保护带定义不同，不能单独归因于解耦结构；且 B3 不是全局最优或安全上界 |
| 滚动子集中 MIKU 到达率点估计更高，但安全不能外推 | 滚动重规划补充实验 | `closed_loop.py`, `run_closed_loop_experiments.py` | `generated/closed_loop_*`：MIKU/B0 25.0%/18.3%；碰撞 1.7%/0% | 只是 60 例规划器状态闭合，不是完整系统闭环或实车证据 |
| 威胁度权重局部稳定，但时序/预测误差仍敏感 | 灵敏度分析 | `sensitivity_analysis.py` | `generated/sensitivity_trajectory.*`：80 条权重轨迹全到达；24 个单因子端点到达 75%，动态场景端点 50% | 不宣称对感知/预测误差鲁棒 |

参考文献条目与正文引用由 `references.bib` 和 LaTeX/Biber 构建共同检查；文献元数据核验不构成对外部方法实验结果的复现声称。
