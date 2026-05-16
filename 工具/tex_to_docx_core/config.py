from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = PACKAGE_DIR.parent
ROOT = TOOLS_DIR.parent
THESIS_DIR = ROOT / "毕业论文"
OUTPUT_DIR = ROOT / "outputs"
CSL_PATH = TOOLS_DIR / "gbt7714.csl"
SVG_DIR = Path(os.environ["SVG_DIR_OVERRIDE"]) if "SVG_DIR_OVERRIDE" in os.environ else ROOT / "图片" / "svg"
TEMPLATE_DOCX = (
    ROOT / "模板" / "湖北文理学院计算机工程学院2026届本科毕业论文模板样例.docx"
)

# 模板前置页：封面(0-14) + 原创性声明(15-24) + 版权授权书(25-35)；不含模板自带摘要和目录示例
TEMPLATE_PREAMBLE_RANGE = (0, 35)  # 闭区间，含 35

# 封面信息栏尽量贴近 `chapters/cover.tex` 的 `4em + 8cm` 结构。
COVER_LABEL_COL_W = 2000  # 约 3.5cm，容纳“论文题目/学生姓名/指导教师”
COVER_VALUE_COL_W = 4536  # 约 8.0cm，对齐 LaTeX 的 \makebox[8cm]

# 中文字号 → pt
FONT_SIZE = {
    "小五": 9.0,
    "五号": 10.5,
    "小四": 12.0,
    "四号": 14.0,
    "小三": 15.0,
    "三号": 16.0,
}

MACRO_SOURCES = [
    "info.tex",
    "_experiment_metrics.tex",
    "_experiment_context.tex",
    "_ablation_macros.tex",
    "_sensitivity_macros.tex",
]

BODY_CHAPTERS = [1, 3, 4, 5, 6, 7, 8, 9]  # chapter2 被导师屏蔽

# 后置章：致谢/成果，在参考文献之后（附录按用户要求不纳入）
POST_CHAPTERS = [
    ("acknowledgment.tex", "致谢"),
    ("achievements.tex", "本科期间的学习与科研成果"),
    ("appendix.tex", "附录"),
]

REFS_ANCHOR_TEXT = "参考文献"
