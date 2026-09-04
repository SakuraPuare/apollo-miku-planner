# 外部标准化来源验证

为避免把自生成场景冒充公开基准，仓库增加了
`可视化/validate_commonroad_external.py`。脚本固定读取 CommonRoad
`2020a_scenarios` 公共仓库中的四个 NGSIM/Lankershim XML，检查下载、XML
解析以及 lanelet、dynamic obstacle、planning problem 实体。该边界测试不是
CommonRoad 规划器适配，也不把本项目的 Frenet 轴对齐原型包装成原生
CommonRoad/Apollo 运行。

2026-09-05 在线 smoke run（原始 XML，不写入工作区）结果：

| 场景 | lanelets | dynamic obstacles | static obstacles | planning problems |
|---|---:|---:|---:|---:|
| USA_Lanker-1_1_T-1 | 95 | 24 | 0 | 1 |
| USA_Lanker-1_2_T-1 | 95 | 42 | 0 | 1 |
| USA_Lanker-1_3_T-1 | 95 | 36 | 0 | 1 |
| USA_Lanker-1_4_T-1 | 95 | 34 | 0 | 1 |

来源：[CommonRoad 场景页](https://commonroad.in.tum.de/scenarios/)，原始仓库
[tum-cps/commonroad-scenarios](https://gitlab.lrz.de/tum-cps/commonroad-scenarios)。
由于当前规划器尚未实现曲线 lanelet、坐标变换和 CommonRoad occupancy adapter，
这些公开场景目前只能作为输入完整性与来源审计证据；论文不得宣称已经在其上
完成 MIKU 规划性能比较。二区送审前仍需完成真实 adapter 和外部方法对比。
