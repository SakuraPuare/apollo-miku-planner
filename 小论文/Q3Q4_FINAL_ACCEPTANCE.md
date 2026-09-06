# 小论文一投稿前最终验收

日期：2026-09-06
范围：仅 `小论文/`，不适用于 `小论文-2/`

## 最终裁决

**通过投稿前技术验收：三区优先、四区保底，可进入投稿材料整理。**

首选路线为 `IET Intelligent Transport Systems`，第二目标为 `Journal of Intelligent
Transportation Systems`；Transportation Letters/JTE Part A 作为后续选择，Journal of
Intelligent & Robotic Systems 与 International Journal of Automotive Technology 作为四区保底。
正式提交前仍需在期刊官网复核当年分区、文章类型、图表格式、数据声明、APC 和投稿系统字段。

## 已通过的硬门禁

- 主稿算法定义面向通用路径--速度解耦规划链；Apollo Planning 仅作为工程集成与场景验证平台。
- 摘要、实验设置、系统边界图、Apollo 回放小节和结论均明确：代表性回放不等同于真实道路实车测试。
- 相关体系表已将 Apollo 写为工程解耦基线实例，不把 Apollo 当作 MIKU 的算法前提。
- 主稿没有内部验证实现术语；`q3q4_consistency_check.py` 的正文扫描通过。
- 3,500 配对场景、4,000 固定截面实例、B0/B1/B2/MIKU 汇总数字与冻结 CSV/JSON 哈希一致。
- 理论、自动驾驶工程、期刊编辑三轮审阅无投稿阻塞项，记录见 `Q3Q4_REVIEW_ROUNDS.md`。
- 图表覆盖方法框架、机制、随机统计、运行时间、消融、灵敏度和 Apollo 回放；不再机械增加图表。
- CommonRoad 受限 adapter、未完成的 native runtime 逐场景映射和实车测试均不作为本稿性能主张。

## 可复现验收结果

```text
uv run pytest -q
118 passed, 20 skipped

python 小论文/q3q4_consistency_check.py
Q3/Q4 consistency check: PASS

(cd 小论文 && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex)
success; 14-page A4 PDF; no undefined references
```

PDF 当前包含 12 个 figure 环境和 7 个 table 环境，标签 69 个、引用 39 个，缺失引用为 0。
编译仍有既有 biblatex 重定义、pgfplots 无界坐标提示和少量 underfull hbox，不影响生成或引用
正确性；新增系统边界图的节点连接警告已消除。

## 提交前仅剩的事务性工作

1. 按目标期刊官网最新模板调整标题页、摘要格式、图表分辨率和参考文献样式。
2. 整理冻结 3,500 场景归档、Apollo 接口/回放图、数据可用性声明和补充材料索引。
3. 生成 IET ITS 主投版投稿信，并保留 JITS/四区路线的摘要与投稿信备选。
4. 上传前再次确认投稿系统中不包含 `小论文/lean/` 或其他内部审计文件。
