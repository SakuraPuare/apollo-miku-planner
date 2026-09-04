# 外部标准化来源验证

为避免把自生成场景冒充公开基准，仓库增加了
`可视化/validate_commonroad_external.py`。脚本固定读取 CommonRoad
`2020a_scenarios` 公共仓库中的四个 NGSIM/Lankershim XML，检查下载、XML
解析以及 lanelet、dynamic obstacle、planning problem 实体。另有
`可视化/commonroad_adapter.py` 对一个严格子集执行 lanelet 后继路由、中心线
弧长投影和动态障碍初始状态转换；`run_commonroad_adapter_smoke.py` 在公开 XML
上实际调用该 adapter 和 B0/MIKU planner。该 adapter 仍不是 CommonRoad 原生
规划器，也不把轴对齐 Frenet 原型包装成完整 CommonRoad/Apollo 运行。

2026-09-05 在线 smoke run（原始 XML，不写入工作区）结果：

| 场景 | lanelets | dynamic obstacles | static obstacles | planning problems |
|---|---:|---:|---:|---:|
| USA_Lanker-1_1_T-1 | 95 | 24 | 0 | 1 |
| USA_Lanker-1_2_T-1 | 95 | 42 | 0 | 1 |
| USA_Lanker-1_3_T-1 | 95 | 36 | 0 | 1 |
| USA_Lanker-1_4_T-1 | 95 | 34 | 0 | 1 |

来源：[CommonRoad 场景页](https://commonroad.in.tum.de/scenarios/)，原始仓库
[tum-cps/commonroad-scenarios](https://gitlab.lrz.de/tum-cps/commonroad-scenarios)。

## 适配器边界与实际 smoke

对 `USA_Lanker-1_1_T-1.xml` 的 adapter smoke（2026-09-05）得到：95 个
lanelet、24 个动态障碍物，沿规划问题的后继链 `3630 -> 3650 -> 3614` 建立
中心线路径；其中 8 个障碍物通过 6 m 中心线残差门限投影，16 个因不在该路段或
不满足形状/距离子集而跳过。B0 与 MIKU 均在该转换场景上实际运行；该样本因
公开轨迹的初始拥挤和常速度投影而触发降级/不可行，不能作为性能优越性结论。
完整 JSON 记录位于 `generated/commonroad_adapter_smoke.json`。

该结果证明的是“公开 XML -> 受限 Frenet 场景 -> planner 调用”链路可执行，
不是对 CommonRoad 规则、曲线几何、occupancy set、感知误差或外部基线的忠实
评测。因此论文仍不宣称 CommonRoad benchmark 性能；二区送审前仍需完整
lanelet/occupancy 语义、公开场景批量指标和忠实外部方法对比。
