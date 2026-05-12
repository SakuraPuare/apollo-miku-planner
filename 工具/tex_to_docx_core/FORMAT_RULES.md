# docx 格式规则手册

本文档规则来源：
1. `模板/计算机工程学院毕业论文（设计）教学方案-工作细则-评阅与标准-规范化要求（2025年12月修订）.docx.md`（学校规范，下称 **§规范**）
2. 0045robot 格式检测器实际口径（下称 **§检测**）

规则按"颗粒度+作用域"两维编排。实现层由 `_apply_format_rules(doc)` 单入口按章节块分发。

---

## 0. 全文档默认

| # | 规则 | 值 | 来源 |
|---|---|---|---|
| 0.1 | 页面 | A4, 上下 2.54cm, 左右 3.17cm | §规范⑵ |
| 0.2 | 默认行距 | 1.5 倍 | §规范⑶ |
| 0.3 | 中文字体 | 宋体 | §规范 |
| 0.4 | 英文/数字字体 | Times New Roman | §规范⑷ |
| 0.5 | 自动项目编号 | 禁用 | §规范⑹ |
| 0.6 | 页脚 | 五号 TNR 居中 | §规范⑷ |
| 0.7 | 前置页页码 | 罗马 I, II | §规范⑷ |
| 0.8 | 正文页码 | 阿拉伯从 1 开始 | §规范⑷ |
| 0.9 | 全文黑色 | 超链接也黑色 | 检测 |

---

## 1. 章节块划分

`_apply_format_rules` 把 body 段按顺序扫描，识别出以下块，再按块内规则应用。

| 块名 | 起始标识 | 结束标识 |
|---|---|---|
| cover | body 起 | "学生声明" H1 前 |
| declaration | "学生声明" H1 | "授权使用说明" H1 前 |
| authorization | "授权使用说明" H1 | "目  录" / "目录" 段前 |
| toc | "目  录" 标题段 | 中文论文题目段前 |
| zh_abstract | 中文题目段（居中 16pt） | 英文题目段前 |
| en_abstract | 英文题目段（居中 16pt） | "1 绪论" H1 前 |
| body | 正文 H1（非附件 H1） | "参考文献" H1 前 |
| bibliography | "参考文献" H1 | "致谢" H1 前 |
| acknowledge | "致谢" H1 | "本科期间的学习与科研成果" H1 前 |
| achievement | "本科期间的学习与科研成果" H1 | 文末 |

---

## 2. 段落规则（按块+段类型二级索引）

### 2.1 toc 块

| 段类型 | 对齐 | 字体 | 字号 | 加粗 | 行距 | 段前段后 | 首行缩进 | 备注 |
|---|---|---|---|---|---|---|---|---|
| 目录标题"目  录" | 居中 | 黑体 | 三号(16pt) | ✓ | 1.5倍 | - | - | §规范⑶ |
| 目录说明"(打开文档后右键...)" | 两端 | 宋体 | 小四 | - | 1.5倍 | - | - | 检测 |
| TOC1 一级目录项 | 左 | 黑体 | 小四(12pt) | ✓ | 1.5倍 | 段后 0 | 2字符 | §规范⑶+检测 |
| TOC2 二级目录项 | 左 | 宋体 | 小四 | - | 1.5倍 | 段后 0 | 2字符 | §规范⑶+检测 |
| TOC 段右侧 tab leader | - | - | - | - | - | - | dot 至 pos=8306 | 检测 |

### 2.2 zh_abstract / en_abstract 块

| 段类型 | 对齐 | 字体 | 字号 | 加粗 | 行距 | 段前段后 | 首行缩进 | 备注 |
|---|---|---|---|---|---|---|---|---|
| 论文题目段 | 居中 | 黑体(中)/TNR(英) | 三号(16pt) | ✓ | 1.5倍 | before=120 after=31 | - | §规范+检测 |
| "摘要：" / "Abstract:" 前缀 | 两端 | 黑体(中)/TNR(英) | 小四 | ✓ | 1.5倍 | 0/0 | 2字符 | §规范 |
| 摘要内容段 | 两端 | 宋体(中)/TNR(英) | 小四 | - | 1.5倍 | 0/0 | 2字符 | §规范 |
| "关键词：" / "Key words:" 前缀 | 两端 | 黑体/TNR | 小四 | ✓ | 1.5倍 | 0/0 | 2字符 | §规范 |

### 2.3 body 块（正文）

| 段类型 | 对齐 | 字体 | 字号 | 加粗 | 行距 | 段前段后 | 首行缩进 | 备注 |
|---|---|---|---|---|---|---|---|---|
| H1 章标题 | 左 | 黑体 | 四号(14pt) | ✓ | 1.5倍 | Word Heading1 | - | §规范；一级标题前分页 |
| H2 节标题 | 左 | 黑体 | 小四 | ✓ | 1.5倍 | - | - | §规范 |
| H3 小节标题 | 左 | 宋体 | 小四(12pt) | ✓ | 1.5倍 | - | - | §规范；注意 sz=24 非 28 |
| 正文段 | 两端 | 宋体 | 小四 | ✗ | 1.5倍 | 0/0 | 2字符 | §规范；**run-level bold 一律清除** |
| 图 caption | 居中 | 宋体 | 小四 | ✓ | 1.5倍 | 0/0 | - | §规范"小四号宋体加粗居中"；**"图"与"1.1"之间无空格** |
| 表 caption | 居中 | 宋体 | 小四 | ✓ | 1.5倍 | 0/0 | - | §规范；**"表"与"1.1"之间无空格** |
| 代码/算法 caption（<40字短标题段） | 居中 | 宋体 | 小四 | ✓ | 1.5倍 | 段前6 段后0 | **无** | 检测要求"代码X-Y"无空格、无首行缩进 |
| 代码 caption 内部块 | - | - | 五号 | - | 单倍 | - | - | 代码块五号左对齐 |
| 公式编号段 "(N-M)" / "（N-M）" | **右** | TNR | 小四 | - | 1.5倍 | - | - | §规范 |
| 表格单元格 | 上下左右居中 | 宋体 | 小四 | - | 单倍 | - | - | §规范 |
| 参考文献上标 `[N]` | - | TNR | 小四 | - | - | - | - | §规范 |

### 2.4 bibliography 块

| 段类型 | 对齐 | 字体 | 字号 | 加粗 | 行距 | 备注 |
|---|---|---|---|---|---|---|
| "参考文献" 标题 | 左 | 黑体 | 四号 | ✓ | 1.5倍 | §规范 |
| `[N]` 文献条目 | 两端 | 宋体(中)/TNR(英) | 小四 | - | **固定 20 磅 exact** | §规范（行距固定 20 磅）；悬挂缩进 |

### 2.5 acknowledge 块

| 段类型 | 对齐 | 字体 | 字号 | 加粗 | 行距 | 备注 |
|---|---|---|---|---|---|---|
| "致 谢" 标题 | 居中 | 黑体 | 三号 | ✓ | 1.5倍 | §规范 |
| 致谢内容 | 两端 | 宋体 | 小四 | - | 1.5倍 | §规范 |

### 2.6 achievement 块

同正文段规则，标题"本科期间的学习与科研成果"居中。

---

## 3. 字符/Run 级规则

| # | 规则 | 作用 |
|---|---|---|
| 3.1 | 中文 eastAsia=宋体 / 黑体 / 仿宋 / 楷体 之外一律改宋体 | 防 Dengxian / Calibri / 等线泄漏 |
| 3.2 | ascii/hAnsi=Times New Roman | 英文字体 |
| 3.3 | Consolas / SourceCode / VerbatimChar 除代码块内部外回落正文字体 | §规范 |
| 3.4 | 段内数学对象 m:r 字号 sz=24（小四） | §规范 |
| 3.5 | 中文段里半角 "," → 全角"，" | §规范（§GB15834）；**参考文献英文逗号保留** |
| 3.6 | 正文 run-level `<w:b/> <w:bCs/>` 除 caption/heading/前缀段外一律清除 | 检测"字形加粗误报" |
| 3.7 | 居中 16pt 的段首 run 补 `<w:b/>` | 论文题目"部分常规"误报 |
| 3.8 | "目  录" 段 run 补 `<w:b/>` | 检测"目录字形加粗部分常规" |
| 3.9 | caption 前缀"图/表/代码/算法"与 N.M 之间空白清零（含 U+00A0 / 全角空格） | 检测 "图x.x" 格式 |

---

## 4. 样式级规则（styles.xml）

| 样式 | 关键属性 | 值 |
|---|---|---|
| docDefaults/rPrDefault/rFonts | ascii, hAnsi, cs | Times New Roman |
| docDefaults/rPrDefault/rFonts | eastAsia | 宋体 |
| Heading1 | sz/b/eastAsia | 28 (14pt 四号) / true / 黑体 |
| Heading2 | sz/b/eastAsia | 32 (16pt 小三? 应 24 小四)；当前 32，§规范要求小四 12pt | ⚠ 待核 |
| Heading3 | sz/b/eastAsia | **24 (12pt 小四)** / true / 宋体 |
| Bibliography | spacing | line=400 lineRule=exact |
| TOC1 | spacing, ind, tabs, rPr | after=0 line=360 auto / firstLineChars=200 firstLine=480 / tab right dot pos=8306 / b=true eastAsia=黑体 sz=24 |
| TOC2 | spacing, ind, tabs, rPr | after=0 line=360 auto / firstLineChars=200 firstLine=480 / tab right dot pos=8306 / b=false eastAsia=宋体 sz=24 |
| Heading Style (H1/H2) | b+eastAsia 迁移到 style-level | 防 Word 更新 TOC 域时污染 |

---

## 5. 检测器口径（不成文但必须遵守）

| # | 规则 | 原因 |
|---|---|---|
| 5.1 | 图/表 caption 前缀"图/表" 与数字**无空格** | "要求：图x.x 实际：图 x.x" |
| 5.2 | 代码/算法 caption 同上 | "要求：代码1-1 实际：代码 1-1" |
| 5.3 | 代码/算法 caption 段**无首行缩进** | "要求：无首行缩进 实际：首行缩进2.00字符" |
| 5.4 | 目录段 after=0 而非 Word 默认 10 | "段后要求：0.00磅 实际：10.00磅" |
| 5.5 | 目录段行距 1.5 倍而非单倍 | "行距值要求：1.5倍 实际：单倍行距" |
| 5.6 | TOC 段首行缩进 2 字符 | "缩进要求：首行缩进2字符 实际：0" |
| 5.7 | 摘要/Abstract 页**论文题目段**（不是摘要前缀段）段前 6 磅 段后 1.54 磅 | "段前要求：6.00磅 实际：0.00磅" |
| 5.8 | 参考文献行距固定 20 磅（exact）而非 auto | "要求：固定值20磅 实际：1.5倍行距" |
| 5.9 | 独立公式编号段"(N-M)" / "（N-M）" 右对齐 | "公式编号应右对齐" |
| 5.10 | 正文段出现 `<w:b/>` 被判"加粗" 即使视觉上不明显 | "字形要求常规 实际加粗" |
| 5.11 | TOC1 所有 run 须加粗，否则"部分常规" | "字形要求加粗 实际部分常规" |

---

## 6. 提醒级（可接受）

以下检测器"提醒"级问题不强制闭环：

- DOI 核验（格式合法即可，内容需人工核对）
- 目录项页码与实际页码不一致（TOC 域在 Word 首次更新时同步，检测器看的是缓存值）
- 段末空白（分页自然产生的孤行）
- 表格跨页（短表续表）
- 核实空格是否必要（数学公式周围空白）

---

## 7. 实现映射

| 规则节 | 代码位置 |
|---|---|
| §0 全局默认 | `normalize_all_fonts` / `_set_page_margins_a4` / `setup_page_numbers_and_sections` |
| §1 块划分 | `_apply_format_rules` 主调度 |
| §2.1 toc | `_rule_toc` + TOC1/TOC2 样式定义 |
| §2.2 abstract | `_rule_abstract_page` |
| §2.3 body | `_rule_body`（正文段/caption/公式/代码 caption） |
| §2.4 bibliography | `_rule_bibliography` |
| §2.5 acknowledge | `_rule_acknowledge` |
| §3 run 级 | `_rule_runs`（字体/bold清除/数学字号/半角逗号） |
| §4 样式级 | `_rule_styles`（Heading3 sz=24 等） |
| §5 检测器口径 | 嵌入各 `_rule_*` 内 |

---

## 8. 全仓补丁痕迹扫描结论（2025-11 重构）

| 文件 | 行数 | 补丁痕迹 | 动作 |
|---|---|---|---|
| postprocess.py | 1453 | post_process 27 步零散编号（1,2,3,5.5,8.5,12.5,12.6...27）；Stage 4 私有 helper 与 docx_common 重复 | **重排** 为 Stage A~F 6 组；helper 集中到 docx_common |
| style.py | 770 | 两处 `_ensure_pPr` 同名（段落用/style 用混淆）；`_set_spacing` 签名冲突；TOC 3 函数散落 | 段落用 `_ensure_pPr` 统一走 docx_common；style 用重命名为 `_ensure_style_pPr`；`_set_spacing` 在函数内改名 local |
| docx_common.py | 205 | — | **扩充**：公共 `_ensure_pPr / _ensure_child / _set_spacing / _set_indent / _set_jc / _run_clear_bold / _run_set_bold / _ptext / _pstyle` 集中 |
| flatten.py | 1060 | 6 处"兜底"注释（合理防御式），47 条 re.sub / .replace（tex 预处理管线，正常量级） | 不动 |
| tables.py | 664 | 4 处 pandoc 行为描述注释（非补丁） | 不动 |
| front_matter.py | 666 | `_mk_run` 两处 local def 同名（签名不同；local scope 无冲突）；`_set_spacing_before` 可复用 | 不动（local helper 属合理模式） |
| docx_structure.py | 294 | 无 | 不动 |

**重构原则**：
1. 只做等价变换 — XML 输出字节级 diff 必须为 0（结构/段落/bold_run/jc 分布全一致）
2. 不删功能代码，只消除重复定义
3. 以 `docx_common` 为单一事实源，跨文件复用低层工具

**验证**：15/15 规则闭环 + 逐段文本 0/1025 差异 + 13 项结构指标零回归（段 1025 / 表 30 / drawing 60 / OMML 1310 / bold_run 309 / jc_right 65 / jc_center 160 / jc_both 666）。

---

## 9. 维护手册

新规则：
1. 登记到 §2（按章节）或 §5（检测器口径）
2. 实现到 `postprocess.py` Stage F `_rule_*` 函数
3. 若涉及公共工具，追加到 `docx_common.py`
4. 验证：跑 `make docx` + FORMAT_RULES 15 项规则脚本 + XML 等价性脚本

补丁识别：
- 函数名含 `fix_/patch_/hotfix_/workaround_` → 合并入 `_rule_*`
- 注释含"补丁/临时/绕过/兜底/Pass N" → 检查是否被规则层覆盖，是则删
- 多函数同名同逻辑 → 集中到 docx_common
- post_process 编号超过 5.5/8.5 这种小数点 → Stage 分组重排

---

## 10. error.txt 86 条错误闭环（2025-11 第二轮）

对照重构前 `error.txt`（学校检测器报告，86 条硬错误）逐条复核：

| error.txt 编号 | 数量 | 问题 | 根因 | 修复点 |
|---|---|---|---|---|
| #1,7,15,23,31,39,47,55,57,59,61 | 11 | TOC1 首行缩进 2 字符 | 规则写错：原以为 TOC1 要 2 字符缩进；检测器要求**无缩进** | `_rule_styles`：TOC1 firstLine=0；TOC2/3 保留 480 体现层级；同步 `style.py:normalize_toc_entries` |
| #72, #345 | 2 | 代码5-1 caption 首行缩进 2 字符 | `_rule_body` 里长度阈值 `<40` 卡死（caption 实际 41 字） | 阈值放宽到 `<80` |
| #73, #346 | 2 | 代码5-1 caption 字形部分常规 | pandoc 产出 bold=None，未加粗 | `_rule_body` 的 is_code_algo_cap 分支加 `_run_set_bold` |
| #74 | 1 | 图5.3 caption 第 13 词 "−" 部分常规 | 已闭环（Image Caption 样式自带 bold） | — |
| #174~341 | 69 | 成果页 [N] 条目行距固定 20 磅 | 之前 `_normalize_for_inspector` 把所有 [N] 开头段设成 exact；成果页不在 bibliography 块 | 现在 `_rule_bibliography` 仅作用于 `bibliography` 块内；成果页 [N] 由 body 块规则处理（1.5 倍） |

**验证**：86/86 条 ✅ 全闭环 + 15/15 通用规则 ✅ 全通过。

---

## 11. 规则勘误

| 节 | 旧规则 | 新规则 | 依据 |
|---|---|---|---|
| §2.1 TOC1 | 首行缩进 2 字符（firstLine=480） | **无首行缩进**（firstLine=0） | error.txt #1,7,15,23,31,39,47,55,57,59,61 |
| §2.1 TOC2/3 | 首行缩进 2 字符 | 首行缩进 2 字符（保留；体现层级） | error.txt 未报错 |
| §2.3 代码/算法 caption 长度 | < 40 字 | < 80 字 | "代码5-1 UpdatePathBoundaryBySLPolygon 核心逻辑" = 41 字 |
