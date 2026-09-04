# 交叉审阅记录

## Round 1 — 初审（2026-09-05）

### algorithm_athlete（独立只读后提出升级）

- 当前实现是空间 Top-3、时间 beam-8 的串行候选链；未覆盖完整空间×时间有限域。
- `s_qp != None` 被当成候选可行，缺少鲁棒轨迹验证。
- `st_boundary_mapper` 与评价器均为离散采样，不能推出连续时间安全。
- 推荐路线 A：惰性联合 best-first，返回 `U-L` 最优性 gap；路线 C 作为连续安全修补。

### novelty_reviewer（独立敌意审稿）

- Esterle et al. (ITSC 2018) 已明确 before/after/right/left、路径—速度解耦和 semantic language/跨周期一致性，直接覆盖现稿“时序同伦首次统一”叙事。
- 审稿人质疑 `build_st_bounds` 的首/末安全窗语义。裁判复核后认定代码按安全窗端点编译正确；真正错误是论文把 pass-before 写到占用退出、yield-after 写到占用进入，已修正文公式。
- 现有 max-gap 只对固定一维截面成立；不能外推到动态换序、曲线路径和 QP 可行性。

### evidence_reviewer（独立实验/理论审阅）

- 仓库是 Python/NumPy/OSQP 原型，不是真实 Apollo/CyberRT/Planning 运行；20 个 skip 也不是 Apollo 集成测试。
- 鲁棒管没有进入路径投影，且候选接受无碰撞验证。
- 评价器只检查 0.1 s 离散点；无公开 benchmark 或外部竞争方法。
- 主实验总体增益主要由窄路和延迟族驱动，需报告分族 CI/宏平均、超时率和失败根因。

### 裁判裁决

**Reject（对当前投稿版本）/ Major Revision（对研究项目）**。创新性、正确性、证据充分性均存在致命缺口；不接受“已可投”的旧结论。选定路线 A 为唯一中心升级，路线 C 为安全必修项；在代码接入、时序修复、公开外部验证前不得完成 Goal。

### 运动员修改与证据

- 新增 `可视化/joint_homotopy_search.py`：有限联合候选的 lazy best-first、可采纳 LB、预算截断 gap、fail-closed 检查。
- 新增 `certify_sampled_axis_aligned_motion`：明确采样点不蕴含连续安全，并提供 Lipschitz 保守证书。
- 新增 `tests/test_joint_homotopy_search.py`：随机穷举 oracle、预算 gap、下界反例、采样间穿越共 7 项。
- 验证：初轮 `85 passed, 20 skipped`；后续集成测试扩展为 `91 passed, 20 skipped`，`ruff` 与 `git diff --check` 通过。

### 运动员修改与证据（Round 1 后）

- `run_method` 的 MIKU 分支已接入 `bounded_lazy_joint_search`；认证模式令 `spatial_top_k=None`、`temporal_beam_width=None`，枚举显式有限域，逐候选执行 QP 与连续扫掠证书，并记录 `U-L`。
- 路径投影、ST 映射和评价器均使用有界预测误差；不满足证书的候选 fail-closed。新增 CommonRoad XML 在线 smoke 脚本与四个 NGSIM/Lankershim 场景的实际解析记录。
- 重生成 700 对主实验、700 对消融和 700 对滚动样本；当前全测为 `91 passed, 20 skipped`。A6 重跑后为成功率 77.6%、碰撞率 1.6%，揭示安全—进度权衡；A7 差异仅 +0.43 pp（p=.25）。

### Round 2 — 修改后独立复审

#### novelty_reviewer

- 独立评分：创新性 2.5/5、正确性 3/5、证据 2/5、表达/一致性 1.5/5，裁决 Major Revision。
- 复审确认：联合搜索已真实接入，论文不再把 Top-3/beam-8 说成全局完备；有限域 optimality gap 的适用范围写清楚。
- 仍认为 Esterle、SMSTP、SSC、MPQP、T-MPC/BPHTO 等先行工作覆盖大部分组件；路线 A 只能作为“显式有限标签域内可终止搜索”贡献，创新性不足以自动达到二区。
- 未发现新的时序端点语义错误；但零下界使搜索基本退化为穷举，700 个主样本中空间候选均不超过 1，只有 28 个 delayed-crossing 样本评估 2 个时间候选。

#### evidence_reviewer

- 独立评分：正确性 2/5、证据 1/5、图表 1/5、复现性 2/5，裁决 Reject/Major Revision。
- 复审确认：主实验数字已由新代码重生成，MIKU 候选接受包含连续扫掠证书，证书字段可追溯；90 项测试通过，20 项 skip 原因仍是文档工具缺失。
- CommonRoad 四个公开 XML 的下载/解析 smoke 实际通过，但没有把坐标 lanelet 转换成当前 Frenet 场景，不能算公开基准性能。
- 发现含噪场景 MIKU 成功率 17% vs B0 33%、B3 碰撞率 35.7%、滚动碰撞差不显著以及 A6 证书 flag 未传递。裁判修复 A6 flag 并重跑消融，同时把中英文的错误方向结论改为安全—进度权衡/B3 诊断。
- 图形计划仍有失败案例/ECDF 等待生成；论文不能以现有柱状图替代。

### 裁判二轮裁决

**Major Revision（不建议当前版本直接投二区）**。算法和证据链已从初审的“未接入/无验收”提升为可审计的有限域认证原型；但外部性能基准、原生平台证据和视觉结果仍不足，且主要组件与先行工作重叠。Goal 继续进行。

### 尚未解决

1. CommonRoad 仍需真实 adapter 与规划性能实验，外部竞争方法尚未忠实复现。
2. 认证搜索在多数现有场景退化为单候选，需构造非平凡多分支公开测试以展示 gap/剪枝价值。
3. pass-before/yield-after 公式已按安全窗端点修正；仍需在论文图中展示端点语义。
4. 两稿重合、失败案例图和投稿诚信文件正在补齐。

## Round 2 — 修改后复审门槛

复审必须由两位审稿人重新读取修改后的代码、实验产物和中英文稿，逐项回答：创新性是否脱离 Esterle 等先行工作、证书是否与实现一致、连续安全是否有有效条件、外部场景与平台证据是否真实、图表是否覆盖失败边界。任一项仍为致命问题，裁判结论保持 Major Revision。
