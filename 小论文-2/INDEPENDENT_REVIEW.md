# Independent pre-submission review — Q3/Q4 route

审稿角色由两条独立检查路径完成：一条只读正文与引用，另一条只读代码、生成物、
CommonRoad 官方 evaluator 输出和门禁报告。两条路径均按创新性、技术正确性、证据、
图表和可复现性逐项复核。

## Reviewer A — technical correctness

- 核心贡献与实现一致：固定同伦标签后仍调用原有 path/speed QP，连续扫掠证书只在
  声明的有限标签域和有界预测误差内给出结论。
- 认证目标与 QP 二次项、分支下界与实际 path-QP 成本一致；没有把有限域证书写成连续
  全局最优。
- CommonRoad 输入现在逐状态消费官方矩形形状、姿态和轨迹，形成保守 Frenet 占用包络；
  4 个场景的 MIKU 4 次规划失败和 0 个有效解原样报告，没有用占位轨迹替换失败。
- 剩余限制（交通控制规则未由 Frenet planner 优化、Apollo 本轮无逐场景运行性能）均在
  正文、manifest 和表格中明确，因此不构成隐藏的技术错误。

结论：无致命技术问题；建议小修后投稿。

## Reviewer B — evidence and presentation

- 主实验、压力实验、消融、滚动实验和外部 CommonRoad 审计均有原始 CSV/JSON、图表和
  复现命令；中文稿 10 页、IEEE 稿 9 页，符合 T-IV/T-ITS Regular Paper 路线。
- 外部竞品失败样本被保留；MIKU 在公开场景上的失败被作为适用边界，而非被删除或改写
  成成功率。
- 图表覆盖方法流程、轨迹级边界、联合搜索规模、消融和外部审计；正文不包含内部形式化
  验证实现名称。
- 仍需在投稿信中说明 CommonRoad 结果是 scoped compatibility benchmark，而非一般
  leaderboard；这是可审计的范围说明，不是致命证据缺口。

结论：无致命证据或表达问题；建议小修后投稿。

## Area-chair decision

`reviewers_clear_of_fatal_issues = true`。可投稿门槛仍要求通过自动化测试、禁词扫描、
哈希校验和页数校验；任何失败都应重新打开 major revision。
