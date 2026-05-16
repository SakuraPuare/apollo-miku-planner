from __future__ import annotations

import os
import re
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
COVER_LABEL_COL_W = 2000  # 约 3.5cm，容纳"论文题目/学生姓名/指导教师"
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

# 后置章文件名 → 默认标题的映射
_POST_CHAPTER_TITLES = {
    "acknowledgment.tex": "致谢",
    "achievements.tex": "本科期间的学习与科研成果",
    "appendix.tex": "附录",
}


def _parse_thesis_tex_inputs() -> tuple[list[int], list[tuple[str, str]]]:
    """从 thesis.tex 解析启用的正文章和后置章，注释行跳过。"""
    thesis_tex = THESIS_DIR / "thesis.tex"
    if not thesis_tex.exists():
        return [1, 3, 4, 5, 6, 7, 8, 9], []

    text = thesis_tex.read_text(encoding="utf-8")
    body = []
    post = []
    # 后置章区域标记：printbibliography 之后的 \input
    past_bib = False
    for line in text.splitlines():
        stripped = line.strip()
        if r"\printbibliography" in stripped:
            past_bib = True
            continue
        # 跳过注释行
        if stripped.startswith("%"):
            continue
        m = re.match(r"\\input\{chapters/chapter(\d+)\}", stripped)
        if m and not past_bib:
            body.append(int(m.group(1)))
            continue
        m = re.match(r"\\input\{chapters/(\w+)\}", stripped)
        if m and past_bib:
            fname = m.group(1) + ".tex"
            if fname in _POST_CHAPTER_TITLES:
                post.append((fname, _POST_CHAPTER_TITLES[fname]))

    return body, post


BODY_CHAPTERS, POST_CHAPTERS = _parse_thesis_tex_inputs()

REFS_ANCHOR_TEXT = "参考文献"
