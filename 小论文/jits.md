# JITS 投稿闭环

目标期刊：*Journal of Intelligent Transportation Systems*

文章类型：Research Article

状态：技术交付完成，待作者最终确认后投稿

## 作者与单位

- JiaWang Liao
- YuFei Hu
- ChaoYang Shi
- ChengJiao Sun（通讯作者，`jiao1952@126.com`）
- School of Computer Engineering, Hubei University of Arts and Science, 296 Longzhong Road, Xiangyang 441053, Hubei, China

## 已确认声明

- Funding: Xiangyang Municipal Key Laboratory of Heterogeneous Big Data; Hubei Superior and Distinctive Discipline Group of “New Energy Vehicle and Smart Transportation”; Key Research and Development Program of Hubei Province (Grant No. 2025BEB002).
- Competing interests: The authors declare no competing interests.
- Data and code: anonymous review materials随稿提交；公开仓库在录用后发布，审稿期间可向通讯作者合理申请。
- AI-assisted language editing: OpenAI Codex (GPT-5)仅用于将既有中文稿英译、语言编辑并按期刊呈现需要重组，未用于原创或得出科学论证，也未生成底层数据或分析；引用与书目信息已依据原始材料和正式记录核验；JiaWang Liao负责逐项核验，作者对全文承担责任。

## 证据边界

- 主统计证据：固定随机种子下的3,500个配对数值场景。
- 算法精确性证据：4,000个固定截面区间实例。
- 闭环稳健性证据：独立的700场景闭环实验，不与3,500场景统计合并。
- 工程证据：Apollo 11.0接口集成与代表性行为观察，不表述为实车测试或Apollo原生性能基准。
- 联合规划参考：B3是固定离散精度的有限网格参考，不表述为全局最优解或公开SOTA。

## 执行清单

- [x] 完整阅读JITS专项skill、39篇文章模式总结和稿件骨架
- [x] 完整阅读现稿、模板、证据索引和既有验收记录
- [x] 锁定冻结数据，补齐统计、联合参考、配置和哈希清单
- [x] 建立研究问题—主张—证据矩阵
- [x] 创建独立英文投稿工程并转换到`interact`模板
- [x] 重写标题、摘要、引言、相关工作与问题定义
- [x] 英译并审计方法、定理、算法和复杂度陈述
- [x] 按RQ重组实验、结果、负面结果和证据边界
- [x] 新增Discussion、Limitations和Conclusion
- [x] 审计全部正文引用并转换为APA作者—年份格式
- [x] 完成Funding、CRediT、利益冲突、数据代码与AI使用声明
- [x] 生成署名稿、匿名稿、独立图文件与补充材料
- [x] 完成cover letter和投稿清单
- [x] 编译、视觉检查、交叉引用检查、数值追溯和匿名化验收
- [x] 提交最终git commit

## 投稿门槛

- 所有主要数字可回指冻结文件和SHA-256记录。
- 署名稿与匿名稿均可从干净目录完整编译。
- 无未定义引用、重复标签、缺失图片、中文残留或不可接受的版面警告。
- 正文明确报告尾延迟和非优势指标，不作超出仿真与接口证据的部署声明。
- 投稿包包含论文源文件、PDF、参考文献、图文件、补充材料、投稿信和声明。

## 已生成交付物

- 署名PDF：`小论文/jits_submission/deliverables/MIKU_JITS_named.pdf`
- 双盲PDF：`小论文/jits_submission/deliverables/MIKU_JITS_anonymous.pdf`
- 署名源包：`小论文/jits_submission/deliverables/MIKU_JITS_named_submission.zip`
- 双盲源包：`小论文/jits_submission/deliverables/MIKU_JITS_anonymous_submission.zip`
- 独立补充材料包：`小论文/jits_submission/deliverables/MIKU_JITS_supplement.zip`

## 自动验收记录

- `latexmk`：署名版和双盲版均为17页，干净目录可编译。
- 补充测试：78 passed；根目录投稿材料测试：3 passed。
- `validate_submission.py`：冻结主数据哈希、主结果、引用、标签、图、匿名分支和补充材料哈希均通过。
- 双盲源包已实测展开编译，且不含实名元数据文件。

## 待作者确认

- 最终确认作者姓名顺序、单位地址、通讯邮箱和基金名称。
- JiaWang Liao 完成逐行英文/引用/数字核验并确认AI使用声明。
- 全体作者确认原创性、未一稿多投、署名与CRediT分工，确认已审阅AI工具条款并批准AI使用声明，并在投稿系统补充ORCID等字段。
