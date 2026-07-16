# 第二战役 Round02 — Apollo 工程审（审 v11）

复核 round01 修复；对引言新增的工业系统表述与伪代码数据接口做第二遍专项。

## P0

无。

## major

无。

## minor

无新增工程事实问题。

## 确认项

- A1-1/A1-2 修复确认：UpdatePathBoundaryBySLPolygon 已挂靠 PathBoundsDeciderUtil（grep 计 1）；§4 口径段已指回 §2。
- 引言"百度Apollo规划器沿用该框架"与 fan2018baidu 的 EM Planner 源流关系表述一致；ROVER 5.0、Autoware 的"采用类似分解策略"为弱化声称，无过度具体化。
- 伪代码输入输出与 Apollo 数据接口一致：自车状态取自 VehicleState（§3.3 已声明）、预测轨迹 6 s 视野（Prediction 模块输出）、输出路径边界与 $\mathcal{T}$ 经 STDrivableBoundary 注入（§3.4 链路已述）。
- 参数一致性复查：obstacle_lat_buffer 0.4 m（§2 统一裕度）与 nudge 双参数 0.3/0.4 m（§3.1 分级现状）分属不同参数的声明保留，无混淆。
- "速度边界决策仅刷新 ST 边界而不清空它"的存活性声明保留，与第一战役核实结论一致。

SCORE: P0=0 major=0 minor=0
