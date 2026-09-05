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
   规划器实际消费官方路线/目标及逐状态矩形形状姿态的保守时变占用包络。交通控制规则
   只记录、不声称由当前 Frenet planner 主动优化；该范围明确标注为 scoped benchmark。
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

## 当前状态

- **P0 已完成**：Apollo 源码基线已定位：`/home/kent/core-11.0`，commit `57460908`；
  关键 Planning 改动已抽取，Apache 许可证、MANIFEST 和反向 SHA-256 校验均已生成。
- **P1 已完成资产登记**：Planning fixture、车辆模型、地图、配置和 CyberRT/Dreamview
  dump 已建立索引；项目回归 `118 passed, 20 skipped`，Ruff 和 diff 检查通过。
- **P1 构建环境已闭环（运行范围明确）**：AEM 11.0 环境中安装官方 bvar 包后，MIKU
  corridor、planning component 与插件目标均完成 pinned commit 构建；CyberRT 启动诊断
  仍保留为未完成逐场景映射，不把构建成功写成 runtime 性能。
- **P2 scoped benchmark 已完成**：CommonRoad 官方 IO、drivability
  checker 和 Reactive Planner 隔离环境已确认；`可视化/run_commonroad_reactive.py` 已
  固定官方 XML、路线参考线、Reactive Planner、标准 solution writer 和 evaluator。四个
  Lankershim 场景的 40 步竞品覆盖已落盘；2 个场景 valid solution，2 个场景记录为
  planner failure，失败不被丢弃。新增 `可视化/run_commonroad_miku_native.py` 已完成
  官方 planning-problem/KSState/solution writer/evaluator 边界实跑；四个 MIKU 场景均真实
  记录为 planner failure，且逐状态形状姿态占用包络已进入 ST/连续安全检查。`miku_native_benchmark`
  对声明范围为 true，负结果不被改写成成功。
- **当前 T-IV 门禁**：`accept`（final mechanical checks）；QP 认证目标、公开竞品协议、MIKU 原生 solution/
  evaluator 输出边界、Apollo 系统证据边界、论文审计、全量测试和 10 页限制均已通过。
  交通控制规则未由当前 Frenet planner 主动优化，作为 scoped benchmark 边界保留；独立
  审稿复核已无致命问题。Apollo 逐场景 runtime 映射仍是未满足诊断项，但正文不宣称
  本轮新增 native runtime 性能，因此不再把它误列为 T-IV 投稿阻塞；若改投 RA-L 才需
  将英文稿从 9 页压到 6 页。CommonRoad 原生输出链路已在隔离 CommonRoad 环境重跑，但 MIKU
  规划失败行和 scoped 输入边界均被保留；交通控制规则未由当前 Frenet planner 主动优化，
  因此不扩写为一般 leaderboard 性能。

## 主要产物

- [`apollo_evidence_manifest.json`](apollo_evidence_manifest.json)
- [`apollo_fixture_manifest.json`](apollo_fixture_manifest.json)
- [`commonroad_external_manifest.json`](commonroad_external_manifest.json)
- [`apollo_extracted/`](apollo_extracted/)
- [`APOLLO_AUTOMATION_TESTING.md`](APOLLO_AUTOMATION_TESTING.md)
- [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md)
