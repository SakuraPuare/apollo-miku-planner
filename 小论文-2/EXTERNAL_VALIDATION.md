# 外部标准化来源验证

为避免把自生成场景冒充公开基准，仓库增加了
`可视化/validate_commonroad_external.py`。脚本固定读取 CommonRoad
`2020a_scenarios` 公共仓库中的四个 NGSIM/Lankershim XML，检查下载、XML
解析以及 lanelet、dynamic obstacle、planning problem 实体。另有
`可视化/commonroad_adapter.py` 对一个严格子集执行 lanelet 后继路由、中心线
弧长投影和动态障碍转换；`run_commonroad_adapter_smoke.py` 在公开 XML
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
公开轨迹的初始拥挤和保守包络而触发降级/不可行，不能作为性能优越性结论。
完整 JSON 记录位于 `generated/commonroad_adapter_smoke.json`。adapter 对 XML
中的预测状态采用首状态常速度 Frenet 模型，并以已提供轨迹样本相对该模型的
残差构造随时间增长的保守位置包络；包络不声称覆盖样本之间的 occupancy。

进一步对四个固定 Lankershim 文件执行批量 adapter smoke，四个场景均成功建立
起终点可达链并调用两种方法。受限转换后的诊断结果为：B0/MIKU 成功率为
25%/0%，碰撞率为 75%/50%，MIKU 的中位耗时为 127.9 ms（最大 323.4 ms）。
轨迹包络使 MIKU 在该四场景诊断中全部采取降级策略；这不是性能退化结论，而是
更保守输入转换的直接结果。这些数字只反映“中心线投影 + 轨迹残差包络 + 轴对齐
矩形”这一受限转换，不能
与 CommonRoad 官方规划器或公开基线比较；原始行和元数据见
`generated/commonroad_batch_raw.csv` 与 `generated/commonroad_batch_results.json`。

## 官方解析器语义审计

为验证轻量 XML 解析器没有把公开文件的实体结构误读为自定义格式，另用可选的
`commonroad-io==2026.1` 官方 `CommonRoadFileReader` 对同四个 XML 做只读审计。结果
落盘于 `generated/commonroad_native_audit.json`：四个场景均解析出 95 个 lanelet、
1 个 planning problem 和 0 个静态障碍物；动态障碍物数分别为 24、42、36、34，
矩形障碍物数与动态障碍物数一致，官方预测轨迹状态总数分别为 914、2111、1321、
506。该审计确认了 lanelet、矩形形状和时序预测实体的存在，但没有把官方对象直接
转换成 MIKU 的 Frenet 规划输入，也没有执行 CommonRoad 规则、碰撞或性能评分。
因此它加强的是“标准化外部输入语义可读取”证据，仍不等同于完整 benchmark 或
忠实外部竞争方法。

该结果证明的是“公开 XML -> 受限 Frenet 场景 -> planner 调用”链路可执行，
不是对 CommonRoad 规则、曲线几何、occupancy set、感知误差或外部基线的忠实
评测。因此论文仍不宣称 CommonRoad benchmark 性能；二区送审前仍需完整
lanelet/occupancy 语义、公开场景批量指标和忠实外部方法对比。
