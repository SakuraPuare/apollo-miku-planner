# 投稿前二次校正验收报告（2026-09-06）

## 已通过

- 主张—证据矩阵、Apollo 源码/fixture 索引、3,500/700 数据版本关系和三轮内部审阅记录已建立。
- Q3/Q4 投稿正文已收缩为可审计的 Apollo Planning 接口与代表性回放表述，不声称实车道路测试。
- 外部公开方法资产已登记：CommonRoad Reactive Planner，以及 Cortado 公开基准中的 SSC、EM、Frenet、NLVO；不作跨数据集 leaderboard 结论。
- 系统级指标审计已完成；缺少原生 runtime 证据的 P99 和跟踪误差不再被正文暗示为已测量。
- 期刊适配包和实验产物哈希清单已建立；投稿压缩包仍需把冻结 3,500 行数据从 Git 历史实际导出。
- 论文投稿文件内部验证术语扫描通过。
- 回归测试：`115 passed, 20 skipped`。
- Apollo snapshot/fixture 路径校验通过。
- Q3 中文稿 XeLaTeX 编译通过，当前 15 页；T-IV/T-ITS 10 页门限通过。

## 尚未通过的硬门禁

| 门禁 | 当前状态 | 原因 |
|---|---|---|
| `native_apollo_cyberrt` | blocked | fixture 尚未完成本轮新重放和逐场景输入—输出—日志映射；宿主机缺少 `/opt/apollo/neo` 构建依赖路径 |
| `commonroad_full_benchmark` | blocked | MIKU 输入仍为受限 Frenet adapter，尚未保留完整 lanelet/occupancy/rule 语义 |
| `reviewers_clear_of_fatal_issues` | open | 以上两项证据缺口仍会触发工程审稿人的 major revision |
| `ral_page_limit` | blocked | IEEE 版当前 9 页，超过 6 页路线；不应直接投 RA-L |

## 投稿决策

自动门禁当前仍为 `major_revision`。因此本次验收把“论文写作与证据边界闭环”标记为完成，
把“原生 Apollo 重放和公平 CommonRoad benchmark”保留为明确的外部工作项：四区路线可以
继续准备，三区投稿需先补齐至少一个原生 Apollo fixture 映射和公平外部比较。该结论不是
对论文工作的否定，而是避免在投稿材料中把资产登记误写成运行结果。
