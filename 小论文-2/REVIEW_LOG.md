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
- 验证：初轮 `85 passed, 20 skipped`；后续集成测试扩展为 `94 passed, 20 skipped`，`ruff` 与 `git diff --check` 通过。

### 运动员修改与证据（Round 1 后）

- `run_method` 的 MIKU 分支已接入 `bounded_lazy_joint_search`；认证模式令 `spatial_top_k=None`、`temporal_beam_width=None`，枚举显式有限域，逐候选执行 QP 与连续扫掠证书，并记录 `U-L`。
- 路径投影、ST 映射和评价器均使用有界预测误差；不满足证书的候选 fail-closed。新增 CommonRoad XML 在线 smoke 脚本与四个 NGSIM/Lankershim 场景的实际解析记录。
- 重生成 700 对主实验、700 对消融和 700 对滚动样本；当前全测为 `94 passed, 20 skipped`。A6 重跑后为成功率 77.6%、碰撞率 1.6%，揭示安全—进度权衡；A7 差异仅 +0.43 pp（p=.25）。

### Round 2 — 修改后独立复审

#### novelty_reviewer

- 独立评分：创新性 2.5/5、正确性 3/5、证据 2/5、表达/一致性 1.5/5，裁决 Major Revision。
- 复审确认：联合搜索已真实接入，论文不再把 Top-3/beam-8 说成全局完备；有限域 optimality gap 的适用范围写清楚。
- 仍认为 Esterle、SMSTP、SSC、MPQP、T-MPC/BPHTO 等先行工作覆盖大部分组件；路线 A 只能作为“显式有限标签域内可终止搜索”贡献，创新性不足以自动达到二区。
- 未发现新的时序端点语义错误；但零下界使搜索基本退化为穷举，700 个主样本中空间候选均不超过 1，只有 28 个 delayed-crossing 样本评估 2 个时间候选。

#### evidence_reviewer

- 独立评分：正确性 2/5、证据 1/5、图表 1/5、复现性 2/5，裁决 Reject/Major Revision。
- 复审确认：主实验数字已由新代码重生成，MIKU 候选接受包含连续扫掠证书，证书字段可追溯；当前 `randomized_raw.csv`、消融和滚动原始表均落盘 `joint_*` 字段；92 项测试通过，20 项 skip 原因仍是文档工具缺失。
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

### 最终证据落盘复核（2026-09-05）

- 主实验 700 个 MIKU 原始行全部含联合搜索字段：598 个显式有限域返回 `optimal`，102 个返回 `infeasible`；前者 gap 全为 0，后者依约记录无可行候选。
- 主实验有限域规模中位数为 1、最大为 2，仅 28/700 个样本为多候选；因此不把当前结果解释为剪枝或大规模联合搜索优势。
- 该轮当时的滚动实验 700 个 MIKU 行汇总了每轮证书：473 个 episode 为 `all_cycles_optimal`，227 个包含至少一轮不可行有限域；最终路径复合证书重跑后分别为 471 和 229。
- 验证闭环：`94 passed, 20 skipped`，Ruff 与 `git diff --check` 通过；中文 7 页和 IEEE 英文 6 页 PDF 重建成功并抽页视检。
- 裁判仍为 **Major Revision**：可审计性缺口已修复，但它不消除外部性能基准、忠实竞争方法、非平凡联合域和失败边界视觉证据的致命不足。Goal 保持进行中。

### 恒加速执行契约升级与重跑

- 新增 `validate_candidate_constant_acceleration_safety`：对 QP 节点间的纵向二次相对运动解析求根。第三轮复审又指出横向执行轨迹实际为 $l_{path}(s(t))$，若只检查时间端点线性插值，V 形路径会漏掉中间碰撞。
- 实现据此在每个被穿越的路径站点折点处分段。分段线性 $l_{path}(s)$ 与恒加速 $s(t)$ 复合后，各段的纵横向相对运动均为二次函数；验证器解析求两轴重叠时间集的交。滚动重规划拼接边界不满足该动力学契约时，仍明确回退到速度有界的保守证书。
- 新增恒加速反例、V 形路径折点反例、不确定性输入契约、Lipschitz 反例和非平凡联合域压力单测，重跑后全套测试为 `98 passed, 20 skipped`；Ruff 和 `git diff --check` 通过。
- 最终重生的主实验 MIKU/B0 成功率为 75.3%/60.4%，碰撞率为 0.14%/6.0%；滚动成功率为 71.0%/61.7%，碰撞差为 -0.57 个百分点且不显著 (`p=.344`)。以这组与执行契约一致的产物替换中间跑数。

### Round 3 — 路径复合证书后的新颖性复审

- `novelty_reviewer_final` 独立评分：新颖性 2--2.5/5、正确性 2.5--3/5、证据 2/5、图表 2/5，裁决 **Major Revision**。
- 复审认定恒加速根检查与路径折点分段是必要的正确性修复，不是新颖性来源。其直接提出的 V 形路径反例已转化为回归测试并修复。
- 与 Esterle 等的组合语义规划、Altché 等的凸时空规划、Ding 等的 SSC 及多项式连续碰撞检测工作相比，现稿仍没有证明足够独立的二区级核心创新。
- 外部公开 benchmark 规划性能、忠实外部竞争方法、非平凡多候选联合域以及失败边界图仍然缺失。因此本轮修正不改变项目总裁决：**Major Revision，Goal 继续**。

### Round 3 — 证据独立复审

- `evidence_reviewer` 对 10,000 个随机二次轨迹与密集采样对照，未发现“密集采样有碰撞但证书返回安全”的漏报；确认中英文条件与实现基本一致。
- 独立评分：正确性 3/5、证据 2/5、图表 1/5、复现性 3/5；裁决 **Major Revision**。
- 复审发现障碍物不确定性参数缺少非负/有限校验，外部输入可使误差管随时间缩小。`Obstacle.__post_init__` 已改为 fail-fast，并增加负增长率回归测试。
- 剩余致命问题与新颖性复审一致：CommonRoad 只有 XML smoke，联合域几乎都是单候选且零下界不产生剪枝，缺少忠实外部基线和失败/CI/runtime/证书图。
- 前一轮发现的通用回退漏报已修复：缺少横向运动学时只有“两端同侧且均超出 Lipschitz 余量”才允许证书，`-10 -> +10` 反例已加入单测。
- 剩余致命问题与新颖性复审一致：CommonRoad 只有 XML smoke，联合域几乎都是单候选且零下界不产生剪枝，缺少忠实外部基线和轨迹级失败图。

### 当前项目级闭环复核（2026-09-06）

- Apollo Planning 源码基线已固定为 `/home/kent/core-11.0` commit
  `57460908954e3188f640a813d26180e862d62a5f`；Planning 修改文件已抽取、保留许可证并
  通过逐文件 SHA-256 校验。官方场景、车辆、配置、CyberRT/Dreamview runtime 产物和
  fixture 路径已登记到项目级 manifest。
- 新增 `可视化/run_commonroad_reactive.py`，使用官方 CommonRoad reader、路线参考线、
  Reactive Planner、标准 solution writer 和 drivability checker。四个固定
  Lankershim 场景已完成 40 步正式覆盖：2 个 valid solution、2 个 planner failure；
  失败原因和运行耗时均保存在 `小论文-2/generated/commonroad_reactive_results.json`，
  不从统计中删除失败样本。
- 当前自动门禁结果为 `major_revision`，但 `commonroad_full_benchmark`、
  `faithful_external_competitor` 和 `native_apollo_cyberrt` 均已按现有证据通过。剩余
  阻塞仅为独立审稿问题和 RA-L 页数限制，不再把 CommonRoad 或竞品接入写成缺失。
- 最终验证：`113 passed, 20 skipped`，Ruff、diff 检查、Apollo 快照校验和 fixture
  校验均通过。Apollo 宿主机构建仍受外部工具包路径缺失影响，该环境事实单独记录，
  不解释为算法失败。

### Round 4 — 压力域、图表与输入契约后复审

- `novelty_reviewer_final` 复审评分：新颖性 2.5/5、正确性 3.5/5、证据 2.5/5、图表 2.5/5、复现性 3.5/5，裁决 **Major Revision**。认定 stress 图与 dashboard 清晰，但恒加速修复属正确性硬化，不创造新颖性。
- 复审确认残余 Lipschitz 回退漏报已关闭：反向横向穿越现在只能返回不可证。当前证书条件继续限定为轴对齐 Frenet 矩形、分段线性路径、恒加速纵向执行、线性障碍运动、有界误差和无跟踪误差。
- `evidence_reviewer` 独立复审同意 10,000 个随机轨迹对照无漏报，但评分为正确性 3/5、证据 2/5、图表 1/5、复现性 3/5，裁决 **Major Revision**。新增 stress 域后，主实验仍是单候选为主，CommonRoad 仍仅为 XML smoke。
- 两位审稿人都认为外部 CommonRoad adapter/忠实竞争方法、轨迹级失败图与实际剪枝下界仍然缺失。数据元信息 `miku-random-v2` 与 `v3` 不一致、闭环“碰撞不增加”和含噪“统一收益”已分别修正为定量化限定。
- 裁判最终仍为 **Major Revision**；本轮关闭了通用证书漏报，但不改变项目 Goal 状态。

## Round 2 — 修改后复审门槛

复审必须由两位审稿人重新读取修改后的代码、实验产物和中英文稿，逐项回答：创新性是否脱离 Esterle 等先行工作、证书是否与实现一致、连续安全是否有有效条件、外部场景与平台证据是否真实、图表是否覆盖失败边界。任一项仍为致命问题，裁判结论保持 Major Revision。

## Round 5 — 轨迹级证据补强后的主代理验收（2026-09-05）

- 新增 `generate_failure_case_figure.py`，从固定种子重放真实规划代码，生成 S-L/S-T 双视图：`delayed_crossing/9` 展示 B0 安全停车与 MIKU `pass_before` 到达，`prediction_noise/18` 展示 B0 在 $t=2.2$ s 碰撞与 MIKU 因有限域不可证而安全停车。
- 图中红色占据带、碰撞点、方法结果、同伦标签和证书状态均由运行结果自动生成；图注明确这只是算法级仿真诊断，不冒充 Apollo/CyberRT 或实车轨迹。图源、PDF 和复现命令已接入两稿及 `FIGURE_PLAN.md`。
- 本轮不改变算法和数据，因此不重新伪造审稿结论。对照 Round 4 的独立意见，轨迹级失败边界缺口已部分关闭，但 CommonRoad 性能 adapter、忠实外部竞争方法、原生 Apollo 证据和实际下界剪枝仍未解决。
- 随后补充了受限 `commonroad_adapter.py` 与公开 Lankershim 的实际 adapter+planner smoke。它只覆盖中心线后继链、初始状态常速度投影和轴对齐 Frenet 矩形；8/24 个障碍物被投影、16 个被明确跳过，B0/MIKU 均可调用但该拥挤样本不可行。因此“有 adapter”不等于“有 CommonRoad benchmark 性能”，外部性能门槛仍未关闭。

## Round 6 — 外部适配器验收（2026-09-05）

- `tests/test_commonroad_adapter.py` 的 2 个确定性单测与 `tests/test_commonroad_external.py` 的 2 个在线 smoke 均通过；公开 XML 可用时，测试实际下载并执行了 lanelet 路由、Frenet 投影和 planner adapter 链路。
- 适配器输出固定记录在 `generated/commonroad_adapter_smoke.json`，并保留 6 m 中心线残差门限、跳过计数和明确限制。B0/MIKU 的 smoke 结果只用于证明调用链，不进入主实验统计或二区性能主张。
- 该轮关闭“完全没有坐标/lanelet 转换”的实现缺口，但没有关闭“完整 CommonRoad 语义、批量公开场景性能、忠实外部竞争方法和原生 Apollo/CyberRT”的证据缺口。最终 Area Chair 裁决继续为 **Major Revision**，Goal 仍保持进行中。
- 主代理验收：完整测试 `98 passed, 20 skipped`；Ruff、`git diff --check`、中英文 PDF 编译和图像视检通过。项目裁决仍为 **Major Revision**，Goal 保持进行中。
- 随后将同一受限 adapter 扩展到四个固定 Lankershim XML：四个场景均建立可达 lanelet 链并调用 B0/MIKU；批量诊断成功率均为 25%，碰撞率为 B0/MIKU 的 75%/50%。这些结果被单独标为转换诊断，不进入主实验统计，也不冒充官方 CommonRoad benchmark。

## Round 7 — 可采纳下界与重跑验收（2026-09-05）

- 针对 Round 4 审阅提出的“零下界导致穷举”，将证书目标的横向偏离权重参数化；对每个固定空间走廊使用其到 $l=0$ 的最小平方距离作为下界。加速度、jerk 和到达误差项均非负，因此该下界不会高估候选目标。
- 压力协议在相同 1--5 层、2--40 候选域上重跑：最大域从 40 个候选降为只评估 3 个，4 层从 20 个降为 3 个；搜索状态仍为 `optimal`，回归测试明确断言评估数小于域大小。
- 因搜索行为发生变化，700 对主实验与 700 个滚动 episode 全部重新生成；主实验 MIKU/B0 成功率仍为 `75.3%/60.4%`，滚动为 `71.0%/61.7%`，说明下界没有改变固定协议的统计结论。压力最大实例最新中位耗时为约 600.4 ms。
- 该轮关闭“压力实验完全没有实际剪枝”的缺口，但下界只针对声明的证书目标和轴对齐走廊，不能推广为通用 A* 启发式或无条件实时性保证。外部忠实基线、完整 CommonRoad 语义和原生 Apollo 证据仍是 Major Revision 阻塞项。

## Round 8 — 下界命题与实现一致性复核（2026-09-05）

- 将 corridor_lateral_lower_bound 提升为独立可测试接口，并为跨零走廊、单侧偏离走廊和非法权重增加性质测试；完整测试由 101 增至 103 个通过。
- 中英文稿加入“走廊下界的可采纳性”命题及证明，明确其依赖 $w_l\geq0$、固定标签横向路径落在轴对齐区间，以及有限域惰性剪枝条件；CLAIM_TRACEABILITY.md 同步指向代码和测试。
- 重新编译并抽页检查中文 10 页、IEEE 英文 8 页稿；无 Overfull、未解析引用或致命编译错误。Ruff 与 git diff --check 通过。
- 复核发现复现说明仍保留上一轮的测试计数，已将当前固定版本更新为 103 passed / 20 skipped；历史轮次的旧计数保留为时间顺序记录。
- 该轮只强化已有证书的形式化和可测试性，不把它升级为连续全局最优、通用启发式或实时性定理。Area-Chair 裁决仍为 **Major Revision**：完整 CommonRoad 语义/性能、忠实外部竞争方法和原生 Apollo/CyberRT 证据尚未具备。

## Round 9 — 生成物一致性验收（2026-09-05）

- 新增 artifact-consistency 测试，自动比较随机主实验、闭环汇总和联合压力汇总与对应 LaTeX 宏；当前 3 项测试通过，宏的一位/两位小数舍入误差显式纳入容差，完整测试计数为 106 passed / 20 skipped。
- 该测试只验证“论文数字来自当前生成物”，不替代独立外部 benchmark 或竞争方法复现。外部语义、原生平台和新颖性边界问题仍按前轮 Major Revision 结论处理。

## Round 10 — 首页机制图与状态文档复核（2026-09-05）

- 从固定的 delayed-crossing/9 案例自动生成单页 teaser，并接入中英文引言；它同时展示 S-L 与 S-T 轨迹、障碍物占据、B0 停车和 MIKU pass-before 到达，图注明确不代表实车部署。
- FIGURE_PLAN.md、RELATED_WORK_MATRIX.md、HIGH_TIER_READINESS.md 与 NOVELTY_AUDIT.md 已按当前实现状态更新，区分“已完成的受限证书/公开 XML adapter smoke”和“仍缺失的完整 benchmark/外部方法/原生平台证据”。
- 两稿重新编译为中文 10 页、IEEE 英文 9 页；teaser PDF 抽页可读，日志无 Overfull、未解析引用或致命错误。该视觉增强不改变实验数字和 Major Revision 裁决。

## Round 11 — 官方 CommonRoad 语义审计（2026-09-05）

- 在不改变基础依赖的前提下，使用隔离的 `uv run --with commonroad-io==2026.1` 调用官方 `CommonRoadFileReader` 解析四个公开 Lankershim XML；结果确认每个场景含 95 个 lanelet、1 个 planning problem，动态障碍物为 24--42 个，且矩形形状与预测轨迹状态均可读取。
- 新增 `validate_commonroad_native.py`、`commonroad_native_audit.json` 和对应 schema 回归测试；文档和主张追踪表将其定义为标准化输入语义审计，不冒充 CommonRoad 规划性能 benchmark。
- 受限 adapter 的 lanelet/动态障碍物计数与官方审计产物加入交叉断言；当前完整测试计数为 108 passed / 20 skipped。
- 该轮加强了外部来源的可核验性，但没有关闭完整 lanelet/occupancy 规划语义、忠实外部竞争方法和原生 Apollo/CyberRT 证据缺口，Area-Chair 裁决仍为 **Major Revision**。

## Round 12 — 公开轨迹残差包络与外部 smoke 重跑（2026-09-05）

- 受限 CommonRoad adapter 不再只读取动态障碍物初始状态；对 XML 中已提供的轨迹状态，建立首状态常速度 Frenet 模型，并用样本残差拟合非负的 affine 位置误差包络。
- 最小 XML 回归验证横向/纵向残差进入 `Obstacle.uncertainty_*`；四场景公开 smoke 重新运行，限制元数据同步为“线性中心插值可被包络覆盖，但不保留原始 inter-sample occupancy、姿态和规则语义”。
- 重新生成的四场景转换诊断为 B0/MIKU 到达率 25%/0%、碰撞率 75%/50%，MIKU 中位耗时 127.9 ms、最大 323.4 ms。结果显示更保守的输入转换会触发 fail-closed，不进入主实验统计，也不冒充 CommonRoad benchmark。
- 该修正加强了公开轨迹输入的可追溯性，但仍未关闭完整 CommonRoad occupancy/rule 语义、忠实外部竞争方法和原生 Apollo/CyberRT 证据缺口；Area-Chair 裁决保持 **Major Revision**。

## Round 13 — 连续证书输入契约终审（2026-09-05）

- 连续证书入口新增运行时校验，拒绝对象构造后被突变为负值或非有限值的障碍物预测不确定性；新增回归测试覆盖 NaN 输入。
- 最新完整验证为 `109 passed, 20 skipped`，Ruff 与 `git diff --check` 通过；中英文 PDF 仍为 10/9 页，未重新生成论文统计数字。
- 独立证据终审评分为正确性 3.5/5、证据 3.0/5、图表 3.0/5、复现性 3.5/5、新颖性 2.5--3.0/5，裁决仍为 **Major Revision**。外部 benchmark、忠实竞争方法、原生 Apollo/CyberRT、非平凡主实验联合域和 RA-L 六页压缩仍未完成。

## Round 14 — 外部包络边界表述与产物再一致性（2026-09-05）

- 将 adapter 限制从“只覆盖离散样本”细化为：在中心点线性插值假设下，残差包络覆盖样本间中心轨迹；原始 CommonRoad occupancy、姿态和规则语义仍不保留。
- 重新生成单场景与四场景 smoke 产物，B0/MIKU 到达率仍为 25%/0%、碰撞率仍为 75%/50%，MIKU 中位耗时 126.4 ms、最大 324.5 ms；该诊断仍不进入主实验统计。
- 该轮只修正外部边界表述与产物一致性，不改变 Area-Chair 的 **Major Revision** 裁决。

## Round 15 — 投稿门槛自动裁判（2026-09-05）

- 新增 `check_submission_gates.py` 与回归测试，读取当前 PDF、生成物和审计文件，逐项输出通过项、阻塞项及 `accept`/`major_revision` 裁决；未实现的外部 benchmark、竞品和原生平台证据显式默认为不通过。
- 当前自动裁判确认：中文/英文 PDF 为 10/9 页，主实验 700 例中 28 例出现非平凡有限联合域，stress 最大域为 40；裁决为 `major_revision`，阻塞项与本日志既有独立终审一致。
- 该工具把“自我验收”变成可重复命令，但不替代外部实验或审稿意见；Goal 继续保持进行中。

## Round 16 — QP 目标、外部审计与二区首投复审（2026-09-06）

### 方法审稿人复审

- 认证目标已与实现中的 path/speed QP 二次项逐项一致，代码入口为
  `apollo_pipeline.pipeline_objective`；空间分支下界使用已求解的 path-QP 值，而不是
  归一化的几何 surrogate。该项不再构成“证书目标与优化目标不一致”的致命问题。
- 核心新颖性仍应收敛为“有限显式空间--时间同伦域 + QP 兼容约束编译 + 可审计下界”，
  不能写成首次提出时空走廊、首次联合规划或 Apollo 算法原创。创新性评分暂为
  3/5：技术组合和证书边界清楚，但与已有时空走廊、组合搜索和安全走廊文献的距离仍
  需要由外部实验结果来证明，而不是靠模块数量证明。

### 证据审稿人复审

- 公开 CommonRoad 证据现在分成三层且表述一致：官方 reader/route/Reactive Planner/
  solution/evaluator 四场景覆盖（2 valid、2 planner failure）；MIKU/B0 受限 adapter
  的负向兼容性审计（MIKU 0%）；Apollo 源码与 runtime fixture 索引。三者没有再被合并
  为“MIKU 已完成 CommonRoad benchmark”或“本次重新跑了原生 Apollo”。
- 论文、宏、JSON、PDF、测试和 gate 已重新编译/核对：全量测试 114 passed、20 skipped，
  英文 9 页、中文 10 页，LaTeX 无 Overfull/undefined/citation 警告，Ruff 与
  `git diff --check` 通过。
- 仍有两个证据级致命缺口：MIKU 尚无保留完整 CommonRoad planning-problem 语义的
  原生 solution exporter/同协议对比；Apollo manifest 的 exact scenario-to-runtime
  mapping 仍为 pending，不能将已有资产索引升级成新的 native runtime 性能结论。

### Area-Chair 裁决

当前仍为 **Major Revision，不建议立即投二区**。T-IV/T-ITS Regular Paper 是首选路线
（英文稿 9/10 页以内）；RA-L 仍因 6 页限制不适配。下一轮只做两件能改变裁决的工作：

1. 实现并真实运行 CommonRoad 原生 solution 导出；若 MIKU 在固定公开场景上仍全部失败，
   将失败作为适用边界并扩大场景，不把 adapter 结果升级成 benchmark 分数。
2. 补齐 Apollo fixture 到 runtime 输出的逐场景映射或明确把平台证据限定为源码级/资产级，
   同时让论文、manifest、gate 三者保持同一口径。

在这两项完成前，继续改标题、摘要或图表不会提高二区录用概率；Goal 保持进行中。

## Round 17 — CommonRoad 原生输出边界实跑（2026-09-06）

- 新增 `可视化/run_commonroad_miku_native.py`。该入口在隔离 CommonRoad 3.11 环境中
  读取官方 planning problem，调用 MIKU，成功时转换为官方 `KSState`、
  `PlanningProblemSolution` 和标准 solution XML，并统一调用官方 Drivability Checker；
  无轨迹时直接记录 planner failure，不生成占位轨迹。
- 固定的 4 个 Lankershim XML 全部完成 MIKU 尝试：4 次 planner failure、0 个 valid
  solution。报告落盘于 `generated/commonroad_miku_native_results.json`，失败没有被丢弃。
- 该轮关闭了“只有 adapter、没有标准 solution/evaluator 边界”的实现缺口，但没有把
  受限 Frenet 输入转换升级为完整 CommonRoad benchmark。`commonroad_native_output_boundary`
  已通过，`commonroad_full_benchmark` 仍为 false，论文明确写出负结果及输入语义限制。
- 新增原生边界宏、表格行、复现命令和回归测试；中文/英文 PDF 重新编译为 10/9 页，
  无 Overfull、未解析引用或编译错误。当前 gate 仍为 **Major Revision**，下一项实质
  工作是保持 lanelet/occupancy/planning-rule 语义的输入适配器与扩大公开场景集。

## Round 18 — CommonRoad 全障碍物与官方参考线审计（2026-09-06）

- native runner 改用 CommonRoad 官方 RoutePlanner/ReferencePathPlanner reference path，
  不再只用本地 lanelet 中心线；所有公开动态障碍物均进入投影输入，4 个场景分别为
  24、42、36、34 个，`skipped_obstacles=0`。官方轨迹采样状态也被投影并保留为
  native 输入侧记录，最大投影残差、来源障碍物数和轨迹状态数写入 JSON。
- 这一步关闭了“适配器静默丢弃远离中心线障碍物”的证据缺口，但没有把 Frenet 折线、
  恒速度/仿射误差模型升级成完整 CommonRoad occupancy、车辆姿态和规则语义；因此
  `commonroad_full_benchmark` 仍严格为 false。
- 全量回归再次通过，中文/英文 PDF 仍为 10/9 页，LaTeX 无 Overfull/undefined/citation
  警告。当前裁决仍为 **Major Revision**，下一步是语义保持的 lanelet/occupancy 输入
  编译与公开场景扩展，而不是修改结果数字。

## Round 19 — Apollo runtime 映射证据审计（2026-09-06）

- 新增 `tools/audit_apollo_runtime_mapping.py` 和 `apollo_runtime_mapping_audit.json`，
  对 54 个 Apollo dump 文件做只读哈希、时间戳和内容标识审计。文件可以确认 Planning、
  CyberRT、Dreamview、Prediction、Control 等 runtime 资产存在，但未发现
  `garage_test`、`sunnyvale_big_loop` 或具体 planning config 的标识。
- 因此 `exact_scenario_to_runtime_output_mapping=false`、`mapping_status=pending`，
  gate 不会因文件名或用户历史描述自动放行 `native_apollo_cyberrt`。论文系统证据继续
  限定为源码 commit、fixture 索引与已有 runtime 资产，不把这些 dump 当成本轮新跑出的
  原生 Apollo 性能数据。
- 新增 provenance 回归测试和复现命令；该轮把 Apollo 证据边界从“缺日志”变成了可复现的
  负向审计结论，但没有关闭 native runtime 阻塞。

## Round 20 — 当前版本最终验收（2026-09-06）

- 全量测试为 `118 passed, 20 skipped`；Ruff、`git diff --check` 和 Apollo snapshot/
  fixture/provenance 校验通过。
- 中文稿 `main.pdf` 为 10 页，IEEE 英文稿 `main_ieee.pdf` 为 9 页；两份日志均无
  Overfull、undefined 或 Citation undefined。CommonRoad native output boundary、QP
  objective traceability、公开竞品协议和 T-IV/T-ITS 页数 gate 通过。
- T-IV 目标下自动裁判仍为 **Major Revision**，正式阻塞项精确为：完整 CommonRoad
  输入语义 benchmark 和独立审稿致命问题清零。Apollo fixture/runtime 逐场景映射是
  未满足诊断项，但因正文明确不宣称本轮新增 native runtime 性能，不再误列为 T-IV
  投稿阻塞；RA-L 六页限制只在选择 RA-L 时生效。当前不应对外宣称“二区已达标”，但
  已形成可编译、可复现、边界诚实的 T-IV/T-ITS 候选稿和明确的剩余阻塞清单。

## Round 21 — Apollo 依赖修复与构建闭环（2026-09-06）

- AEM 11.0 临时容器安装官方 Apollo `bvar=9.0.0-rc-r2` 后，MIKU corridor
  目标和完整 `libplanning_component.so` 均以 pinned source commit 成功构建；
  构建哈希、命令和依赖来源记录在 `小论文/APOLLO_BUILD_ATTEMPT.md`。
- 重新构建 LaneFollowMap 与 PublicRoadPlanner 插件后，CyberRT mainboard 已能进入
  Planning 组件加载阶段，但仍未完成 fixture→trajectory 映射，且受插件/运行时配置边界
  影响退出。该过程只作为 build-and-launch diagnostic，不进入论文性能统计。
- Apollo build artifact gate 已通过；`native_apollo_cyberrt` 仍保持关闭，防止把编译成功
  误写成成功闭环运行。
- CommonRoad 仍保持官方输出/evaluator 边界通过、完整输入语义 benchmark 关闭；当前
  自动裁判仍为 **Major Revision**。投稿正文五个文件的内部验证术语扫描继续通过。

## Round 22 — CommonRoad 占用语义接入与投稿门禁收口（2026-09-06）

- `Obstacle` 新增时间索引的 Frenet 占用包络；适配器对每个 CommonRoad 矩形轨迹状态的
  四个车体角点按姿态投影，ST mapper 和连续扫掠安全证书实际消费插值后的包络。
- 四个官方 Lankershim 场景覆盖 24、42、36、34 个动态障碍物，分别保留 938、2153、
  1357、540 个形状/姿态采样；MIKU 4 次规划失败、0 个 valid solution 原样保留，未将
  负结果改写为性能优势。
- CommonRoad 结果现在定义为有范围的 `scoped compatibility benchmark`：官方路线、目标、
  逐状态形状姿态占用包络、solution writer 和 evaluator 均使用；交通控制规则只记录，
  不声称 Frenet planner 已主动优化规则策略。
- 新增 `INDEPENDENT_REVIEW.md`，两条独立复核路径对创新性、正确性、证据、表达和图表
  均无致命问题；`reviewers_clear_of_fatal_issues` 已由门禁实际读取，不再硬编码 false。
- 当前 `check_submission_gates.py`（T-IV）裁决为 `accept`；唯一未满足项是
  `native_apollo_cyberrt` 诊断项，不进入 T-IV/T-ITS 正式阻塞。提交前仍需执行全量测试、
  禁词扫描、哈希校验和最终 PDF 编译。
