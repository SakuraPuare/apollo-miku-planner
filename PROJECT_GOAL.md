# Apollo-MIKU 项目 Goal / Plan

更新时间：2026-09-06

## Goal

以 `/home/kent/core-11.0` 中 Apollo Planning 的 MIKU 提交为唯一算法基线，完成一套
可追溯、可批量回归、可接 CommonRoad evaluator 的规划实验资产。核心算法直接来自
Apollo 源码；不另写一套近似 planner，不把操作入口差异当成算法差异。

## 完成定义

Goal 只有在以下条件全部满足时才算完成：

1. Apollo 关键源码已经抽取到项目内，并保存原始 commit、文件哈希、许可证和依赖索引。
2. 抽取快照可以由单条命令重新生成，且重复生成不会产生未登记差异。
3. Apollo Planning 的输入 fixture、输出 fixture、配置和场景索引可追溯。
4. Dreamview/CyberRT 在环结果与批量回归结果使用同一核心链路，差异只在触发和采集方式。
5. CommonRoad 使用正式场景、planning problem、车辆模型、标准 solution 和 evaluator；
   全部动态障碍物先经过官方形状/姿态占用解析和路线相关性审计，只有与可达路线走廊
   相交的保守时变占用包络进入规划约束。交通控制规则只记录、不声称由当前 Frenet
   planner 主动优化；该范围明确标注为 scoped benchmark。
6. 至少一个独立公开竞争方法在同一 CommonRoad 协议下完成运行和结果记录。
7. 所有论文指标都能反查到源码 commit、场景、配置和原始结果。
8. 自动门禁能区分“已具备证据”“历史记录”“仍需运行”的状态，不因缺失日志而默认放行。

## 执行顺序

### P0：源码基线与快照

- 固定 Apollo 分支、commit 和 MIKU 修改文件。
- 保留原始版权头，生成源码快照、哈希和依赖清单。
- 禁止继续把时间花在网页操作或 AEM/Bazel 修复上，除非完成定义确实需要新的运行证据。

### P1：Apollo Planning 回归资产

- 固定官方场景、车辆动力学、Planning 配置和 protobuf fixture。
- 记录轨迹、边界、状态码、fallback 和耗时。
- 用已有 Dreamview/CyberRT 运行产物建立在环索引；新的批量结果必须引用同一源码基线。

### P2：CommonRoad 正式 benchmark

- 使用官方场景和 planning problem，不再把中心线近似转换作为正式结果。
- 统一车辆模型、时间预算、代价和 evaluator。
- 接入一个公开独立竞争方法，与 MIKU 共享全部评测条件。

### P3：论文和门禁闭环

- 更新主张追踪、复现说明、图表和投稿门禁。
- 每个数字必须有原始 CSV/JSON、配置和提交索引。
- 真实运行未覆盖的项目只标为 pending，不用文档措辞替代实验。

### P4：CommonRoad 泛化算法（当前活动目标）

- 将 lanelet 几何边界、目标时间窗和 KS 可执行控制纳入统一规划协议。
- 增加合法等待/通过分支，并由官方 CommonRoad evaluator 验证积分后的轨迹。
- 只有在公平协议下出现可复核 valid solution 和安全指标后，才提升论文的外部泛化主张。
- 详细门槛和当前阻塞见 [`COMMONROAD_GENERALIZATION_PLAN.md`](COMMONROAD_GENERALIZATION_PLAN.md)。

## 当前状态

- **P0 已完成**：Apollo 源码基线已定位：`/home/kent/core-11.0`，commit `57460908`；
  关键 Planning 改动已抽取，Apache 许可证、MANIFEST 和反向 SHA-256 校验均已生成。
- **P1 已完成资产登记**：Planning fixture、车辆模型、地图、配置和 CyberRT/Dreamview
  dump 已建立索引；项目回归 `134 passed, 20 skipped`，Ruff 和 diff 检查通过。
- **P1 构建环境已闭环（运行范围明确）**：AEM 11.0 环境中安装官方 bvar 包后，MIKU
  corridor、planning component 与插件目标均完成 pinned commit 构建；CyberRT 启动诊断
  仍保留为未完成逐场景映射，不把构建成功写成 runtime 性能。
- **P2 scoped benchmark 已完成**：CommonRoad 官方 IO、drivability
  checker 和 Reactive Planner 隔离环境已确认；`可视化/run_commonroad_reactive.py` 已
  固定官方 XML、路线参考线、Reactive Planner、标准 solution writer 和 evaluator。四个
  Lankershim 场景的 100 步竞品覆盖已落盘，失败不被丢弃。新增
  `可视化/run_commonroad_miku_native.py` 已完成官方 planning-problem/InputState/
  solution writer/evaluator 边界实跑；当前 MIKU 为 2 valid、1 planner failure、1 invalid
  solution，且逐状态形状姿态占用包络已进入 ST/连续安全检查。`miku_native_benchmark`
  对声明范围为 true，负结果不被改写成成功。
- **当前 T-IV 门禁**：`accept`（final mechanical checks）；QP 认证目标、公开竞品协议、MIKU 原生 solution/
  evaluator 输出边界、Apollo 系统证据边界、论文审计、全量测试和 10 页限制均已通过。
  交通控制规则未由当前 Frenet planner 主动优化，作为 scoped benchmark 边界保留；独立
  审稿复核已无致命问题。Apollo 逐场景 runtime 映射仍是未满足诊断项，但正文不宣称
  本轮新增 native runtime 性能，因此不再把它误列为 T-IV 投稿阻塞；若改投 RA-L 才需
  将英文稿从 9 页压到 6 页。CommonRoad 原生输出链路已在隔离 CommonRoad 环境重跑，但 MIKU
  规划失败行和 scoped 输入边界均被保留；交通控制规则未由当前 Frenet planner 主动优化，
  因此不扩写为一般 leaderboard 性能。
- **CommonRoad 泛化第一阶段已完成**：新增有符号端点 Frenet 投影、路线相关性过滤、
  occupancy 与预测残差去重、CommonRoad KS 输入控制输出和反馈跟踪器。全部源障碍物
  仍被解析和计数，路线无关对象不再制造虚假的 `s=0` 前向约束；当前四个场景均能
  进入官方 dynamics/evaluator 边界；统一 100 步协议下已有 2/4 场景通过，主要剩余问题
  是场景 3 的安全同伦和场景 4 的短目标窗可执行性。这是真实进展，不等同于泛化完成。
  已额外运行同一公开目录的十二个扩展场景；在保守 goal-rectangle 区间语义修复后，
  十六场景结果为 7 valid、3 planner failure、6 evaluator-invalid，扩展结果独立存档，
  不替代主四场景协议；其中 2 个已被提前
  判定为 goal station 在安全 corridor 下不可达。原生 writer 另含官方 BMW-320i KS
  终端 steering-rate shooting，只有终端残差改善时才采用，最终有效性仍由官方 evaluator
  判定。

## 主要产物

- [`apollo_evidence_manifest.json`](apollo_evidence_manifest.json)
- [`apollo_fixture_manifest.json`](apollo_fixture_manifest.json)
- [`commonroad_external_manifest.json`](commonroad_external_manifest.json)
- [`apollo_extracted/`](apollo_extracted/)
- [`APOLLO_AUTOMATION_TESTING.md`](APOLLO_AUTOMATION_TESTING.md)
- [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md)
