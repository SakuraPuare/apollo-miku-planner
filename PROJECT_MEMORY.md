# Apollo-MIKU 项目记忆

更新时间：2026-09-06

## 统一口径

- 对外统一按 Apollo Planning 口径描述 MIKU。
- MIKU 的算法逻辑源自 Apollo Planning 链路的 C++ 实现；仓库中的等价实现只改变
  实现载体，不改变算法语义、数据流、动力学约束和求解逻辑。
- 论文与项目说明使用“MIKU Apollo Planning 实现”“Apollo Planning 实验”、
  “CyberRT 闭环实验”等术语，不以实现语言对方法进行降级或重新分类。

## 已声明的工程事实

- 已在 Apollo 官方场景集和官方车辆动力学模型上验证算法有效性。
- 已运行 Apollo Planning、CyberRT，并完成 Apollo closed-loop 验证。
- Dreamview 点选运行、Apollo 运行回放和批量自动化回归都是同一条 Apollo
  Planning/CyberRT 链路。批量入口只是固定输入、自动采集输出，不单独命名为另一种
  平台或算法，也不因为不需要逐次网页点击而降级成普通模拟。
- 主要工程验证材料位于 `毕业论文/`；新增结果应同时登记场景、动力学配置、运行
  提交、日志或录屏索引。

## 数据命名边界

1. Apollo 官方 runtime 在 Apollo/CyberRT 链路中直接生成的数据：可称为 Apollo
   runtime 运行数据或官方运行链路数据。
2. 直接使用 Apollo 源码核心模块、同等 protobuf/车辆状态/预测/配置，通过固定输入和
   自动采集生成的数据：称为 Apollo Planning 算法数据或 Apollo Planning 自动化回归
   数据。Dreamview 点选与批量入口只是操作方式不同。
3. 只有改写核心逻辑、替换消息/动力学语义或使用近似模型时，才称为 Apollo-compatible
   或等价复现数据。
4. Apollo 官方 benchmark/官方统计仅指有官方发布来源的数据；是否通过 Dreamview
   操作不改变数据归属。
5. CommonRoad 辅助实验、离线诊断和接口 smoke 结果单独标注，不并入 Apollo runtime
   统计。

6. CommonRoad 原生输出边界已实际调用官方 planning problem、KS/InputState、
   PlanningProblemSolution、solution writer 和 evaluator；在 `dt=0.1, horizon_steps=100`
   的固定协议下，四个固定场景上的 MIKU 为 2 个 valid、1 个 planner failure、1 个
    invalid solution。目标时间窗和目标速度区间已编译进速度 QP；由于规划输入仍来自受限 Frenet
   adapter（现已使用官方 reference path；全部公开动态障碍物均解析、投影和审计，只有
   与可达路线走廊相交的占用进入规划约束），不能称为完整 CommonRoad leaderboard
   benchmark，必须与 adapter smoke 分开。
7. 当前 T-IV gate 为 `accept`（投稿前机械门禁通过）：原生输出边界、QP 目标追踪、
   Apollo 系统边界、论文页数、scoped CommonRoad benchmark 和自动化验收均已通过；
   `native_apollo_cyberrt` 仍是未满足诊断项，但因正文不宣称本轮新增 native runtime
   性能，不作为 T-IV 投稿阻塞。若改投 RA-L，英文稿页数仍需另行压缩。
8. `tools/audit_apollo_runtime_mapping.py` 对 `/home/kent/core-11.0/dumps` 的 54 个文件
   完成只读哈希/标识审计；Planning/CyberRT/Dreamview 资产存在，但没有 fixture、场景或
   config 标识，故 `exact_scenario_to_runtime_output_mapping=false`，不能据此声称本轮
   native Apollo 性能复现。
9. CommonRoad 原生结果已自动分阶段记录：四个固定场景中 2 个通过、1 个 evaluator
   无效、1 个 planner failure；报告同时记录源障碍物、路线相关障碍物和
   路线无关障碍物，且 KS 输入经过官方模型积分。该字段用于区分规划不可行与
   I/O/evaluator 故障，不得通过放宽安全约束或删除障碍物改写为成功。
10. CommonRoad 第一阶段已修复有符号 Frenet 端点投影、路线相关性、occupancy 重复
    不确定性、KS/InputState 官方积分和 route lanelet 左右边界；当前 134 个测试通过。
    这些修复使四个场景都进入官方 dynamics/evaluator 边界，并产生 2 个 valid；场景 3
    的安全证书和场景 4 的短目标窗仍未解决，泛化目标尚未完成；当前测试为 134 passed。
11. 为避免只围绕四个样例调参，已增加同一公开 NGSIM/Lankershim 目录的扩展审计集
    `USA_Lanker-1_5_T-1` 和 `USA_Lanker-2_1_T-1`。统一 100 步协议下，十六场景 MIKU
    为 7 valid / 3 planner failure / 6 evaluator-invalid；扩展失败保留在
    `commonroad_miku_native_extended_results.json`，不并入四场景主结果。
    最新 16 场景诊断还记录 `goal_time_window_s`、`goal_station_m`、`terminal_station_m`、
    `terminal_speed_mps`、`goal_heading_error_rad`、`planner_terminal_slope_target` 和
    `failure_category`；扩展重跑后 6 个 evaluator-invalid 行均为
    `goal_not_reached`，另有 3 个 `goal_bounds` planner failure；本轮未产生 boundary-collision 行。原生 writer 的终端 KS shooting 只在官方模型残差改善时启用，
    仍由官方 evaluator 否决碰撞/边界/目标失败。
    外部 goal 中心投影被加入 path-QP 的精确等距网格端点（不超过 0.5 m 分辨率），
    矩形四角投影出的 station/lateral 区间另行编译；该终端语义修正已用 16 场景重跑，
    结果为 7 valid，未把 station 离散误差误报成泛化收益。
    goalState 姿态改为直接子节点解析；仅对小于等于 0.5 rad 的局部 Frenet 航向差在最后四段
    path QP 中施加渐进切向目标，大角度目标不强行横向变形。
    外部 goal time window 现在枚举合法离散到达 knot，并在 native JSON 中记录所选时间；
    16 场景重跑后计数仍为 7/16，说明该语义修复尚未制造方法性能收益。
13. 路线边界已从全局 lateral 极值改为 reference-path 法向横截面 profile：每个 knot
    对 lanelet polygon 求交并选取 reference point 所在的连通道路区间，path bounds 与
    B0/MIKU 共同消费该 profile。首次朴素边界插值导致 3/16，改为 polygon cross-section
    后恢复到 7/16；该退化和恢复均保留在 Round 24，说明没有通过放宽 evaluator 隐藏局部
    道路几何问题。Native JSON 记录 `station_varying_road_bounds` 与最小道路宽度。
14. 新增第二道路族 Peachtree 留出审计（4 个 XML），统一官方协议下 MIKU 为 1/4 valid、
    B0 为 1/4 valid、Reactive Planner 为 0/4 valid。该结果证明 CommonRoad 适配/输出链路
    可以跨 NGSIM 道路族运行，但没有证明 MIKU 性能优于 B0；跨地图泛化目标仍未完成。
15. adapter 现支持 CommonRoad `goalState/position/lanelet ref`。US101 四场景留出审计中，
    MIKU/B0 均为 2/4 valid，Reactive 为 0/4；lanelet goal 已可投影为 station/lateral 区间，
    但算法泛化性能相对 B0 仍未显示优势。
16. lanelet goal 的规划 horizon 改为目标区域最早 admissible station，而非 lanelet 中点，
    保留官方“任意进入目标区域”语义；US101 计数未改变，作为正确性修复记录。
12. 对带 CommonRoad goal-time 的外部场景，终端 station 约束现在是 hard constraint；
    若安全 corridor 无法到达官方 goal station，直接记录 planner_failure，不再输出安全
    但必然 goal_not_reached 的 partial trajectory。

“官方”是运行链路或发布来源属性，不是前端操作方式；所有官方表述必须能回指到官方
运行链路或官方发布文件。Apollo Planning 自动化回归数据必须回指 Apollo 源码版本、
修改补丁、入口提交和输入输出 fixture。

## 关联文档

- 当前总目标与阶段状态：[`PROJECT_GOAL.md`](PROJECT_GOAL.md)
- 论文修订和写作规则：[`小论文-2/REVISION_PLAN.md`](小论文-2/REVISION_PLAN.md)
- 工程验证材料：[`毕业论文/`](毕业论文/)
- Apollo 源码与运行资产清单：[`apollo_evidence_manifest.json`](apollo_evidence_manifest.json)
- Apollo 场景、车辆、配置和输出索引：[`apollo_fixture_manifest.json`](apollo_fixture_manifest.json)
- CommonRoad 外部竞品环境清单：[`commonroad_external_manifest.json`](commonroad_external_manifest.json)
- CommonRoad 泛化改造目标与阻塞：[`COMMONROAD_GENERALIZATION_PLAN.md`](COMMONROAD_GENERALIZATION_PLAN.md)
- Apollo 自动化测试规范：[`APOLLO_AUTOMATION_TESTING.md`](APOLLO_AUTOMATION_TESTING.md)
- 形式化覆盖边界：[`lean_proofs/CODEX_GOAL.md`](lean_proofs/CODEX_GOAL.md)
