# 投稿前二次校正验收报告（2026-09-06）

## 已通过

- 主张—证据矩阵、Apollo 源码/fixture 索引、3,500/700 数据版本关系和三轮内部审阅记录已建立。
- Q3/Q4 投稿正文已收缩为可审计的 Apollo Planning 接口与代表性回放表述，不声称实车道路测试。
- 外部公开方法资产已登记：CommonRoad Reactive Planner，以及 Cortado 公开基准中的 SSC、EM、Frenet、NLVO；不作跨数据集 leaderboard 结论。
- 系统级指标审计已完成；缺少原生 runtime 证据的 P99 和跟踪误差不再被正文暗示为已测量。
- 期刊适配包和实验产物哈希清单已建立；冻结 3,500 行数据已实际导出到 `submission_artifacts/frozen_3500/`，并与 700 回归包分离。
- 论文投稿文件内部验证术语扫描通过。
- 回归测试：`116 passed, 20 skipped`。
- Apollo snapshot/fixture 路径校验通过。
- Q3 中文稿 XeLaTeX 编译通过，当前 14 页；三区/四区期刊路线不套用 T-IV/T-ITS 10 页门限。

## 当前仍需在小论文一投稿前完成的门禁

| 门禁 | 当前状态 | 原因 |
|---|---|---|
| `native_apollo_cyberrt` | 非本稿必需的诊断项 | 小论文一不把本轮新 native runtime 性能作为投稿主张；保留接口、场景和 Dreamview 回放证据边界 |
| `commonroad_full_benchmark` | 不属于本稿协议 | 小论文一正文不把 CommonRoad 结果作为性能主张；不将二区稿门禁移植到本稿 |
| `reviewers_clear_of_fatal_issues` | 已通过 | `Q3Q4_REVIEW_ROUNDS.md` 三轮本稿专属审阅均无投稿阻塞项 |
| `ral_page_limit` | 不适用 | 小论文一按三区/四区期刊路线准备，不投 RA-L |

## 本轮新增审计

- CommonRoad 原生输出边界在独立 Python 3.12 环境中重新执行，四个官方
  Lankershim 场景均保留 MIKU 规划失败行；由于输入仍是受限 Frenet adapter，
  `commonroad_full_benchmark` 继续关闭。
- Apollo 11.0 的窄 corridor 目标和 `--config=opt` 重建均复现缺失
  `third_party/var/bvar/bvar.h`，旧 Bazel 缓存中的共享库未被冒充为当前构建证据。

上述构建阻塞已在临时 AEM 容器安装官方 `bvar=9.0.0-rc-r2` 后关闭：MIKU corridor、
完整 Planning component 以及两个缺失插件均完成构建，并记录 SHA-256。随后 mainboard
进入插件加载阶段但未形成 fixture→trajectory 映射，因此 `native_apollo_cyberrt` 仍不放行。

## 投稿决策

小论文一当前的投稿决策不再由二区稿的 CommonRoad 或 T-IV/T-ITS 门禁决定。三区优先、
四区保底路线的主张—证据反查、Apollo 平台边界措辞、图表解释、禁词扫描、编译和三轮
编辑/工程/理论审阅均已完成。原生 Apollo 逐场景 runtime 映射不是本稿的新增性能主张；
若在投稿信中提及，只能表述为接口与代表性回放证据。
