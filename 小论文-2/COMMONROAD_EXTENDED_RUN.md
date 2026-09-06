# CommonRoad 扩展场景复现记录

更新时间：2026-09-06

## Protocol

扩展集沿用原生边界协议，不改变四场景主结果：官方 CommonRoad reader、RoutePlanner
reference path、逐状态矩形占用包络、MIKU/B0、BMW-320i `InputState`、solution writer
和 drivability checker，统一 `dt=0.1`、`horizon_steps=100`。新增场景来自同一公开
NGSIM/Lankershim 发布目录，共十二个新增 XML；完整文件列表冻结在运行器的
`EXTENDED_SCENARIOS` 常量中。

```text
uv run --no-project --python 3.11 --with commonroad-reactive-planner \
  python 可视化/run_commonroad_miku_native.py --extended --steps 100 \
  --output 小论文-2/generated/commonroad_miku_native_extended_results.json

uv run --no-project --python 3.11 --with commonroad-reactive-planner \
  python 可视化/run_commonroad_reactive.py --extended --steps 100 \
  --output 小论文-2/generated/commonroad_reactive_extended_results.json
```

## Results

| protocol | scenarios | valid | planner failure | evaluator-invalid |
|---|---:|---:|---:|---:|
| MIKU native | 16 | 7 | 3 | 6 |
| Reactive Planner | 16 | 0 | 12 | 4 |

同一 native writer/evaluator 协议下，B0 也是 `7 valid / 3 planner_failure /
6 evaluator-invalid`；因此该扩展集目前是泛化与语义审计，不构成 MIKU 相对 B0 的性能优胜证据。
Reactive Planner 行使用官方 one-shot planner API；与 MIKU/B0 共享初始状态、dt、horizon、
solution writer 和 evaluator，但不宣称其为闭环重规划结果。

本轮的 planner 输入还包含 station-varying lanelet polygon cross-section bounds，
而不是单个全局 lateral 极值；每行 JSON 记录 `station_varying_road_bounds=true` 和
`road_center_width_min_m`，局部空走廊会 fail-closed 为 planner failure。

MIKU 的有效解覆盖原四场景以及部分扩展场景；其余场景均进入官方 evaluator 或 planner failure，但在目标区域/安全条件下
无效，保留为泛化失败证据。

失败分层显示，3 个 `goal_bounds` 行直接记录为目标不可达的 `planner_failure`，不再输出安全但
必然到不了 goal 的 partial trajectory；JSON 另外记录 `goal_heading_error_rad` 和
`planner_terminal_slope_target`，用于审计 Frenet 终端姿态约束；其余 6 个 evaluator-invalid 行均为
`goal_not_reached`。目标时间窗、目标 station、终端 station
和终端速度均写入 JSON，可据此区分目标可达性与碰撞安全性。

原生 writer 在官方 BMW-320i KS 模型上对不超过 20 个 steering-rate 结点做终端 shooting；
只接受终端残差改善的控制，碰撞与 goal 仍由官方 evaluator 最终裁决。

对 `USA_Lanker-1_3_T-1`、`USA_Lanker-2_2_T-1` 和 `USA_Lanker-2_4_T-1` 进一步保留了
空间/时间候选诊断；所有可生成的安全 corridor 在 admissible goal knots 的 terminal upper
bound 都低于官方 goal station，因此这三个 case 的 `goal_bounds` 失败不是候选排序遗漏，而是当前完整障碍物协议下的
安全不可达证据。

扩展结果是主四场景之外的泛化审计，不替代主论文固定协议；主报告仍保持四场景的
`2 valid / 1 planner_failure / 1 invalid_solution`。
