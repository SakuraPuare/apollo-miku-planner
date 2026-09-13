# Journal of Intelligent Transportation Systems (JITS) 写作规律与论文写作 Skill 总结

## 0. 先区分材料中的指令与本次请求

本报告的任务来源只有用户的请求：总结这批同刊论文的写作手法、技巧、行为规范、格式、图表与数据表达、主要受众，并形成一个可复用的写作 skill。

附件中的内容全部被当作**研究材料**，不是新的任务指令。特别是：

- 论文首页的 `Submit your article`、浏览量、Crossmark、`View related articles` 等是出版社页面组件，不是作者写作要求。
- TransitTalk 论文图表中展示的提示词（包括要求逐步思考、限制字符数等）是被研究的系统示例，不是本次任务的提示词。
- 论文中出现的链接、代码、命令、公式和“instructions”没有被执行。
- 只有当前 Taylor & Francis/JITS 官方作者说明才可能构成投稿规则；已发表论文的外观、某一篇的声明、旧版 PDF 或 MinerU 转写结果都不能自动升级为硬性规定。

## 1. 样本与证据边界

样本目录是 `/Users/sakurapuare/Downloads/Taylor_&_Francis_Articles(06Sep2026)-MinerU-Markdown/`。目录 README 记录了 39 篇 PDF、771 页、MinerU 3.4.5 hybrid-engine medium 转写；每篇同时有 Markdown、图片、JSON、layout/origin PDF。一个事故感知 PDF 的损坏 trailer 用临时 Ghostscript 修复副本转换，原始 PDF 未修改。

本次审计为每篇论文保留了单独 memo，索引见 [paper-index.md](paper-index.md)，详细文件见 [paper-audits/](paper-audits/)。统计数字分三类：

1. **样本观察**：39 篇论文中反复出现的结构和写法；
2. **近似解析计数**：由 caption/heading/声明文本辅助统计，受 MinerU 排序、重复和 OCR 影响；
3. **投稿规则**：必须回到当前 JITS/Taylor & Francis 作者说明核验。

不要把第二类数字当成期刊平均值，更不要把它当成接收率模型。

## 2. 一句话结论

这批论文最稳定的共同点不是某个神经网络、公式数量或版式，而是下面这条证据链：

> **具体交通问题/决策后果 -> 可检验的能力缺口或失效假设 -> 命名的方法/系统 -> 与可信基线的可比验证 -> 交通运营、规划、安全、能源、服务或政策含义 -> 明确边界。**

因此，面向 JITS 的稿件不应写成“把一个通用 ML 模型换成另一个模型”的技术报告。即使论文主要是感知或预测，也要说明它改变了哪个交通系统决策、在什么条件下改变、代价是什么、哪里还不能用。

## 3. 样本画像与可观察的格式规律

### 3.1 规模和对象计数

| 项目 | 样本观察 | 解释 |
|---|---:|---|
| 论文 / 源 PDF 页数 | 39 / 771 | 只表示本次抽样覆盖面 |
| 图 caption-label | 约 461 个 | 是转写文本中的标签出现次数，不是出版社对象总数 |
| 表 caption-label | 约 215 个 | 同上；续表和 OCR 重复可能计数偏差 |
| 算法标签 | 约 7 个 | 只有少数论文单独排版 Algorithm |
| 编号公式标签 | 约 707 个 | 理论/控制/优化文章贡献了大部分 |
| 单篇显式图标签范围 | 约 3-23 | 按审计 memo 的可识别 caption 估计 |
| 单篇显式表标签范围 | 0-10 | 取决于文章是公式型还是数据/调查型 |
| 单篇显式公式范围 | 约 1-43 | 不是篇幅或质量目标 |

一个没有“理想图表数”的事实很重要：定理型控制论文可能有 40 多个公式、1 张参数表和少量结果图；调查或运营论文可能有多张分布表而几乎没有公式。图表应该由证据任务决定。

### 3.2 章节出现情况

39 篇均能识别摘要、引言、结论和参考文献的功能；约 25 篇有明确文献/相关工作标题，约 29 篇有方法/建模/问题 formulation 标题，约 32 篇有结果/实验/案例标题，约 16 篇单列 discussion，约 6 篇单列 limitations。其余论文往往把讨论或局限放进结果末尾、结论或 future work。

这说明“必须有完全相同的英文标题”不是规律；稳定的是功能，而不是标题字面。新稿可以用 `Methods`, `Model formulation`, `Experimental setup`, `Results and discussion`, `Conclusions and limitations` 等清楚表达功能。

### 3.3 后置声明

样本中的 `Disclosure/Conflict` 文本普遍出现；funding、data/code、author contributions、ORCID、ethics/consent、AI 使用声明和 supplementary 的出现并不一致。直接文本检测大致得到：funding 27 篇、data availability 9 篇、code availability 3 篇、author-contribution 标题约 5 篇、ORCID 16 篇、显式 AI/ChatGPT 文本 6 篇、appendix 6 篇、supplementary 2 篇。由于声明可能藏在版式、网页元数据或不同标题下，这些只应作为“需要核对的存在指标”。

结论不是“没写过就可以不写”，而是：声明必须按研究实际和当前 IFA 逐项补全。

## 4. 期刊定位与主要受众

当前 JITS 官方页面把期刊定位在智能交通技术、规划和运营，强调移动性、安全、能源/排放、控制、计算、通信、算法、数据库、仿真、人机交互等与地面交通系统的联系。页面还提示稿件需要有实质性的交通规划或运营含义；纯通用图像处理/ML、没有交通系统后果的稿件存在 scope desk-reject 风险。请以当天的 [JITS journal overview and scope](https://www.tandfonline.com/journals/gits20/about-this-journal) 为准，不把网页上的比例或编辑提示当成稳定统计规律。

### 4.1 受众-决策-证据矩阵

| 主要读者 | 他们要作的判断 | 稿件应给的证据 |
|---|---|---|
| ITS、控制、ML 研究者 | 机制是否定义清楚，比较是否公平，结论是否超出设计 | 问题定义、假设、基线、消融、误差、可复现参数 |
| 交通机构、运营者、信号/线路工程师 | 结果是否改变一个现实操作决定 | 延误、吞吐、可靠性、服务、排放、风险、覆盖、延迟、成本、失败条件 |
| 规划者、监管者、政策读者 | 能否迁移、治理和审计 | 时空覆盖、利益相关者抽样、隐私/伦理、公平性、外部有效性、制度约束 |
| 系统和部署工程师 | 能否接入、运行、监控和维护 | 输入输出接口、数据血缘、阈值、硬件/软件、通信假设、人工兜底、资源成本 |
| 人因、服务和调查研究者 | 用户/工作人员经历了什么，下一步行动是什么 | 假设/问题、招募、同意、实验顺序、效应量、不利和不显著结果、子群体 |

引言中应明确最主要的决策者，讨论中再次回答“他/她依据这项结果会做什么”。只说“模型很有用”无法服务任何一类读者。

## 5. 反复出现的五种论文骨架

### A. 控制与优化

常见顺序是：运营冲突 -> 状态/目标/约束 -> 控制器或求解器 -> 可行性/稳定性 -> 正常和压力场景 -> 服务、安全、能源、成本和计算时间权衡。

写作要点：

- 在公式前说明物理对象、决策间隔、延迟、饱和、约束和边界；
- 把每个模块对应到一个缺口，并设计一个可去除/替换的消融；
- 用理论阈值设计场景，例如阈值下、刚超过阈值和极端条件，而不是任意挑好看的曲线；
- 同时报目标值和实际可用性：稳定/可行、控制代价、舒适性、安全裕度、求解/推理时间；
- 仿真结果要称为仿真证据，不能自动称为现场或部署验证。

代表性文章包括车道变换、绿灯起始时差、公交/电车协调、校车路径、CACC 延迟、随机周界控制等。它们的共同写法是将假设-公式-场景-运营指标串起来，而不是只展示算法流程图。

### B. 预测、感知与重识别

常见顺序是：数据与标签 -> 独立单位和泄漏隔离 -> 架构/特征 -> 经典与近期基线 -> 消融/迁移/误差/延迟 -> 交通后果。

写作要点：

- 说明同一人、车、行程、场景、道路段或日期是否跨越 train/validation/test；
- 不能用大量重叠窗口代替独立样本量；
- 对不平衡任务给出类别数、每类指标、混淆/错误类型、校准或阈值分析；
- 对“实时”“端侧”“可部署”给硬件、负载、延迟、内存、功耗或模型大小；
- 用交通任务指标补充通用 accuracy/F1/mAP/RMSE，例如延误、覆盖、误触发、预警提前量、线路服务质量。

地铁/公交多图预测、速度预测、道路表面分割、目标检测和车辆 re-ID 论文都体现了“机制拆分 + 基线 + 消融 + 迁移或错误分析”的模式，但样本中也反复暴露 split、统计不确定性和运行成本报告不足的问题。

### C. 人因、调查、政策与服务

常见顺序是：研究问题/假设 -> 招募、抽样和伦理 -> 工具/问卷/实验 -> 可解释统计 -> 子群体和不利发现 -> 机构或用户行动。

写作要点：

- 先给招募渠道、资格、排除、有效样本、缺失和伦理/同意；
- 重复测量、固定顺序、随机化和反平衡必须同时出现在设计与分析中；
- 调查论文应给基数、类别编码、系数、p 值、边际效应和拟合信息，而不只给比例图；
- 把便利样本、自报偏差、横截面设计和单一利益相关者范围写成可测的局限；
- 同时报有利、不显著和不利结果，尤其是安全、舒适、隐私和信任相关结果。

轨迹引导、驾驶压力、robotaxi 执法人员和 Wi-Fi/UBI 研究表明，人因或政策论文也能适配 JITS，但必须把研究对象和交通决策写清楚。

### D. 理论或方法论文

常见顺序是：定义/假设 -> 推导、定理或证明 -> 算法/伪代码 -> 参数化数值检查 -> 精确的适用边界。

不要把一组选定的仿真图称为定理证明；把“参数适当调节”改成可复现范围，把未知量、稳定条件、初值、求解容差和搜索分辨率写出来。

### E. 系统与数据管线

常见顺序是：现实数据或流程瓶颈 -> 端到端模块 -> 触发/标签/质量检查 -> 留出或现场核验 -> 隐私、成本、接口和失败行为。

交叉口几何提取、重型车辆重量识别、雷达-视频事故感知和 TransitTalk 都体现了这种骨架。GUI、demo 或一段短视频只能证明“系统能运行”，不能单独证明“现场有效”。

## 6. 写作修辞与段落技术

### 6.1 标题

样本中最稳定的标题公式是：

`[交通任务/后果] + using/based on [方法或系统] + in/for [场景、约束、利益相关者或数据源]`

标题应让读者知道改变的对象（信号、车道、时刻表、客流、风险等）和运行条件。缩写可以在描述性短语之后出现；只写 acronym 会降低检索性和范围可读性。

### 6.2 摘要

大多数摘要是一个连贯段落，可按六个动作写：

1. 交通问题及后果；
2. 既有方法失效的具体假设或缺口；
3. 命名方法及其模块；
4. 数据、站点、参与者、仿真规模、切分或验证设计；
5. 2-4 个可追溯数字：绝对值、匹配基线/变化、成本或安全/延迟；
6. 面向某个决策者的含义和主要边界。

避免用没有分母的“significant improvement”。绝对差写 `percentage points`，相对变化写 `percent change`；明确数字来自 benchmark、校准、仿真、现场观察还是部署。

### 6.3 引言

有效的 funnel 是：现实重要性 -> 按能力/假设/数据源分组的文献 -> 2-4 个具体缺口 -> 编号贡献 -> 路线图。不要只写引用清单，也不要用“研究很少”代替可检验的能力缺口。

推荐句式逻辑：既有方法在假设 A 下有效；目标交通环境违反 A；本研究的模块针对该违反；实验将模块效果与基线分开测量。

贡献条目应同时写出：

- 交付物或机制是什么；
- 它解决哪个缺口；
- 哪个章节、实验和指标检验它。

### 6.4 方法

从概览走向可审计细节：范围和单位 -> 框架图 -> 方程/算法/伪代码 -> 数据血缘 -> 训练/校准/求解设置 -> 基线和指标。

每个模块用同一小循环：`动机 -> 公式/算法 -> 符号与参数 -> 预期机制 -> 消融或验证`。公式后立即解释物理或运营意义，参数表集中定义符号和单位。

### 6.5 结果

按研究问题而不是代码执行顺序排列：主比较 -> 机制/消融 -> 敏感性/迁移/鲁棒性 -> 错误和副作用/成本 -> 代表性案例。

每个主要结果都回答四个问题：在什么条件下、比谁好多少、指标和分母是什么、为什么会这样。保留 trade-off，不强行选一个“全面最好”的方法。

### 6.6 讨论、局限和结论

讨论常用链条是：机制 -> 与先前能力比较 -> 交通决策。把数据直接证明的内容和对部署的推断分开。

局限采用：

`[边界/假设] -> [有效性或部署后果] -> [下一项可测研究]`

结论只回答研究问题、重述可追溯的 2-3 个数字和受边界约束的应用含义，不引入新指标或新的普遍性宣称。

### 6.7 语言、时态和符号

- 方法和实验中已完成的收集、训练、校准、测试通常用过去时；图表所显示的关系和定义可用现在时；全篇保持一致。
- 用主动的 `we define / we test / we compare` 做论证路标；程序细节可用简洁被动语态，但不能隐藏责任主体。
- 首次出现展开缩写；符号、单位、百分号、0-1 比例和百分比全篇统一。
- 用具体动词替代无定义的 `novel`, `robust`, `efficient`, `safe`, `universal`, `significant`。
- 图、表、方程在第一次相关论断附近引用；不要只把对象丢在文末让读者猜。

## 7. 图、表和数据表达的规律

### 7.1 一张图只承担一个证据任务

| 图的任务 | 应该显示什么 |
|---|---|
| 框架/数据流 | 输入、预处理、模块、决策点、输出和使用者 |
| 研究场景 | 地图、传感器、网络、参与者流程、实验或仿真场景 |
| 方法定义 | 几何、图结构、时序、控制器、算法流程 |
| 主比较 | 按条件的曲线/柱图，含基线、单位、样本或重复说明 |
| 机制/消融 | 一次只改变一个模块、参数或约束 |
| 鲁棒性/失败 | 留出站点/日期、扰动、错误类别、覆盖和副作用 |
| 案例/部署 | 代表性轨迹、时刻表、交叉口、运营者界面或异常案例 |

多 panel caption 要说明 panel 角色、线型、marker、单位、聚合方式和条件。图中文字应在最终栏宽、灰度和色觉可访问性下仍可读。出版社图标、等式截图、MinerU 占位图不是研究证据。

### 7.2 表的任务

样本中的表主要用于：

- 符号、参数、约束和实验配置；
- 站点、网络、数据来源和样本构成；
- 主指标与基线的精确值；
- 消融、敏感性、子群体、错误类别和运行成本。

单位放在表头；脚注定义分母、缺失值、均值/中位数/范围、重复次数和 bold/underline 规则。若值是单次运行，明确写出；不要让粗体暗示统计显著。

### 7.3 数据与验证应如何入图表

数据部分至少交代来源、日期、站点、传感器/平台、采样和聚合、标签/真值、过滤、缺失、隐私和独立单位。图表中的“样本量”要区分独立车辆/行程/参与者/站点和重叠窗口/记录数。

验证矩阵可按下表组织：

| 论文主张 | 最低可解释证据 | 更强证据 |
|---|---|---|
| 优于替代方案 | 同数据、预处理、预算和域基线 | 经典+近期+分析/现场基线，并有不确定性 |
| 某模块有效 | 单因素消融 | 消融 + 阈值/视野/图结构/延迟/损失敏感性 |
| 可泛化 | 一个固定切分外的条件 | 留出站点、日期、数据集、用户、天气或需求 |
| 可靠 | 重复运行或误差分布 | 区间/效应量、子群体、失败案例、校准 |
| 可使用 | 运行时间或资源报告 | 现场/官方记录、成本、延迟、安全、排放或操作收益 |

### 7.4 样本中的数字写法示例

以下数字是审计中观察到的**写法样例**，不是新论文的目标值：

- 轨迹引导研究用 35 名参与者、140 次试验、H1-H4 假设，并同时报告收益、不显著和不利结果；
- robotaxi 调查报告 3,498 份有效回答，并给 Fisher 检验、有序 logit、边际效应和便利抽样局限；
- 全州交叉口提取将 99,349 个候选、79,824 个后处理输出、mAP .956 和 1,200 条人工核验放在同一条端到端证据链；
- 公交客流研究报告 512 个站点和约 950,000 条刷卡记录，并按 30/45/60 分钟 horizon 做图结构消融；
- SAC 信号控制在 3x3 SUMO 网络、多个流量条件、基线和消融、50 次运行/扰动场景下讨论网络整体与局部 trade-off；
- 随机周界控制用 500 条 Brownian 路径和运行时间报告数值求解代价；
- CACC 延迟论文把基线 1.33 s 延迟边界与 TPF 12.94 s 的条件性稳定范围对照，直接让场景检验理论阈值。

这些例子显示“规模 + 对照 + 条件 + 交通含义”比单独报一个漂亮百分比更有说服力。

## 8. 定量和统计行为规范

### 应该做

- 预先定义指标、方向、单位、分母和聚合方式；
- 报告独立样本量、重复次数、随机种子、缺失和筛选；
- 预测/分类同时报类别数、每类结果、错误类型、校准或区间；
- 仿真报告 warm-up、horizon、需求/场景、seed、重复、软件版本；
- 调查/人因报告效应量、分析单位、检验假设、多重比较和重复测量结构；
- 把运行时间、参数量、内存、能耗、求解时间或人工成本放进“可用性”证据。

### 不应该做

- 把五个随机 seed 的均值叫作统计显著；
- 把 benchmark F1、R-squared、仿真图或 GUI demo 写成部署证明；
- 把绝对百分点变化叫相对 percent change；
- 用“accuracy/FPR/risk”但不给标准定义；
- 用几十万重叠窗口掩盖真正独立单位很小；
- 只展示平均收益，省略安全、舒适、隐私、延迟、子群体或失败代价。

## 9. 反复发现的缺陷，以及新稿应如何避免

这些是样本审计发现的风险模式，不是对期刊或单篇作者的判定。

1. **数据泄漏/样本膨胀**：同一车辆、参与者、行程、日期或场景跨 split，或用重叠窗口冒充独立观测。解决：在方法中写独立单位和 group/time/site split。
2. **指标定义漂移**：FPR/accuracy 自定义、比例和百分比混用、MAPE 遇零未处理、摘要数字与表不一致。解决：给公式、分母、单位和一条可复算示例。
3. **统计词失控**：`significant/significantly` 没有检验、区间、效应量或阈值。解决：若只是幅度，改成具体数值；若是推断，补完整分析。
4. **基线不公平**：基线调参、数据、预算、停止规则和新方法不同，或没有消融。解决：建立 baseline ledger，记录每个模型的同等条件。
5. **部署过度宣称**：单站点、单桥、短视频、仿真、原型 GUI 被写成 real-world/field-ready。解决：把 evidence type 和 deployment boundary 明写在摘要和结论。
6. **可复现信息缺失**：没有 split、seed、硬件/软件、参数表、solver、停止规则、代码/数据路线。解决：在方法末尾给 reproducibility block。
7. **隐藏不利结果**：平均收益掩盖安全、舒适、隐私、类别、延迟或网络局部退化。解决：增加 failure/side-effect figure 或表。
8. **新颖性/因果性膨胀**：`first`, `state-of-the-art`, `comprehensive`, `causes`, `proves` 没有检索边界、识别设计或定理条件。解决：限定比较范围和因果措辞。
9. **照抄转写版式**：把 OCR 乱码、出版社 landing page、两栏成品 PDF、错误 caption 顺序复制到投稿稿。解决：用可编辑单栏源文件和当前 portal 要求。

## 10. 观察到的出版物外观 vs 当前投稿文件

### 10.1 样本 PDF 的成品外观

多数下载 PDF 的第一页是出版社 landing/cover，正文从后续页开始；正文常见期刊/DOI 头、蓝色标题、作者单位、阴影摘要区域、article history、keywords、双栏正文、作者-年份引文、图题在图下、表题在表上、编号公式和双栏参考文献。开放获取标记、通讯作者、appendix 和声明位置会变化。

这描述的是**排版后的出版物**，不是投稿文件模板。

### 10.2 投稿前要现场核验的项目

按当天的 [JITS Instructions for Authors direct endpoint](https://www.tandfonline.com/action/authorSubmission?journalCode=gits20&page=instructions)、[Taylor & Francis manuscript layout guide](https://authorservices.taylorandfrancis.com/publishing-your-research/writing-your-paper/journal-manuscript-layout-guide/)、[submission portal guide](https://authorservices.taylorandfrancis.com/publishing-your-research/making-your-submission/using-taylor-francis-submission-portal/) 和 [format-free guidance](https://authorservices.taylorandfrancis.com/publishing-your-research/making-your-submission/format-free-manuscript-submission/) 核对：

- article type、special issue 和 scope；
- full manuscript 与 anonymized manuscript/title page；
- 摘要、关键词、正文、参考文献、appendix 和 supplementary 的位置；
- 可编辑源文件、图表文件、caption、分辨率和权限；
- 当前字数、关键词数、引文/参考文献样式和模板版本；
- funding、conflict、author contributions、ethics/consent、data/code/software、AI、preprint 和 supplementary 声明；
- 颜色可访问性、替代文本、第三方地图/照片/图标许可；
- portal 的文件验证和特殊 issue 要求。

通用 Taylor & Francis layout guide 的字体、行距、页边距只是通用建议，期刊 IFA 优先。旧的 `gitsauth.pdf` 曾流传具体字数、字体和图表放置规则，但版本很旧；只能作为历史线索，不能在 skill 中硬编码。

## 11. 已交付的写作 Skill

Skill 目录：[`/Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/`](/Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/)。它包含：

- [`SKILL.md`](/Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/SKILL.md)：触发边界、核心证据链、五种文章模式、摘要/引言/方法/结果/讨论/声明规则；
- [`references/corpus-patterns.md`](/Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/references/corpus-patterns.md)：39 篇交叉论文模式、受众矩阵、图表数据语法、反模式和样例；
- [`references/manuscript-template.md`](/Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/references/manuscript-template.md)：可填充的标题、摘要、章节、验证矩阵、声明和图表 ledger；
- [`references/submission-and-format.md`](/Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/references/submission-and-format.md)：成品 PDF 与当前投稿规则的边界、官方核验链接、历史文件警告；
- [`scripts/audit_jits_manuscript.py`](/Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/scripts/audit_jits_manuscript.py)：Markdown/plain text/TeX 的 evidence-hygiene 预检器；
- [`agents/openai.yaml`](/Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/agents/openai.yaml)：Codex UI 元数据。

预检器的用法：

```bash
python3 /Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/scripts/audit_jits_manuscript.py draft.md
python3 /Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/scripts/audit_jits_manuscript.py main.tex --json
python3 /Users/sakurapuare/Desktop/homelab/docs/skills/jits-writing/scripts/audit_jits_manuscript.py draft.md --strict
```

它检查结构提示、摘要数字与正文的近似可追溯性、TeX `input/include`、图表 caption/引用、重复/未定义 label、统计措辞、百分比口径、仿真/ML/人因复现线索和声明提醒。默认 `WARN/INFO` 不代表论文错；`--strict` 只是把提醒转成项目门禁。它不执行 TeX、不预测接收、不替代统计或当前 IFA 审核。

## 12. 建议的后续使用流程

1. 用一句 fit sentence 写清交通决策、缺口、方法、数据/场景、基线和指标。
2. 选一个主文章骨架，建立 contribution-to-test evidence ledger。
3. 先写数据/假设/基线和验证矩阵，再写摘要和结果 prose。
4. 生成图表 ledger，确保每个对象只有一个证据任务、一个首次引用和一个可复算数字。
5. 跑预检器，逐条判断 WARN 是真实缺口、合法文章类型差异还是抽取/文本限制。
6. 渲染可编辑稿，检查栏宽、公式、灰度、caption、交叉引用和摘要/表/结论的一致性。
7. 最后重新打开当前 JITS IFA，逐项核对投稿文件和声明；不要用这批论文替代当天规则。
