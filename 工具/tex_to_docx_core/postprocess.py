from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from .config import FONT_SIZE
from .docx_common import _apply_para, _heading_level
from .docx_structure import (
    _relocate_bibliography,
    add_heading_numbers,
    demote_heading4_to_heading3,
    insert_page_breaks_before_headings,
    insert_thesis_title_pages,
    normalize_special_h1_text,
)
from .front_matter import (
    compress_declaration_and_authorization,
    fill_cover_info,
    prepend_front_matter,
    tab_align_cover_and_signature_rows,
)
from .page_setup import _set_page_margins_a4, setup_page_numbers_and_sections
from .style import (
    bolden_abstract_prefixes,
    enable_latin_word_break,
    fold_abstract_heading_into_body,
    justify_body_paragraphs,
    normalize_bibliography_text,
    normalize_text_punctuation,
    normalize_all_fonts,
    normalize_paragraph_spacing,
    normalize_toc_entries,
)
from .tables import (
    add_equation_numbers,
    apply_table_body_font_size,
    apply_three_line_tables,
    center_all_images,
    center_all_table_cells,
    flatten_list_indent,
    style_code_block_tables,
    style_subfigure_captions,
    wrap_listings_and_algorithms,
)

# =============================================================================
# Stage 3 — post-process via python-docx
# =============================================================================


_CODE_ALGO_CAPTION_RE = re.compile(r"^(?:代码|算法)\s*\d+[\.-]\d+\s")


def _style_code_algorithm_captions(doc) -> None:
    """代码题 / 算法题标题段刷成表题规格（小四黑体加粗居中，段前6pt段后0）。
    flatten 阶段用 `\\noindent\\textbf{代码X-Y ...}` / `...{算法X.Y ...}` 生成整段粗体标题段，
    pandoc 不落 Caption 样式，主循环的表题分支覆盖不到，这里独立识别补刷。
    判定：段文字匹配 ^(代码|算法)N[-.]N 且段内所有非空 run 均粗体，过滤正文中"算法 5.1"这种局部加粗片段。
    """
    for p in doc.paragraphs:
        text = p.text.strip()
        if not _CODE_ALGO_CAPTION_RE.match(text):
            continue
        runs_with_text = [r for r in p.runs if (r.text or "").strip()]
        if not runs_with_text:
            continue
        if not all(r.bold for r in runs_with_text):
            continue
        _apply_para(
            p,
            cjk_font="黑体",
            ascii_font="Times New Roman",
            size_pt=FONT_SIZE["小四"],
            bold=True,
            align=WD_ALIGN_PARAGRAPH.CENTER,
            space_before=6.0,
            space_after=0.0,
        )


def post_process(docx_path: Path) -> None:
    doc = Document(str(docx_path))

    # 1. 先把参考文献条目搬到 anchor 标题之后
    _relocate_bibliography(doc)

    # 2. Heading 4 → Heading 3（规范"最多三级标题"）
    demote_heading4_to_heading3(doc)

    # 3. 致谢 → 致 谢（规范文字要求）
    normalize_special_h1_text(doc)

    # 4. 给 Heading 1/2/3 加章节编号前缀（"1 绪论" / "1.1 xxx"）
    add_heading_numbers(doc)

    # 5. 所有 Heading 1 前插分页符（首个除外）
    insert_page_breaks_before_headings(doc)

    # 5.5 Abstract 段前插一个空行（规范要求：中英文摘要之间留一空行过渡）
    _insert_blank_before_abstract(doc)

    for p in doc.paragraphs:
        style = p.style.name if p.style else ""
        text = p.text.strip()
        lvl = _heading_level(style)

        if lvl == 1:
            # 致谢单独规格：三号黑体加粗居中（规范要求）
            if text in ("致 谢", "致谢"):
                _apply_para(
                    p,
                    cjk_font="黑体",
                    ascii_font="Times New Roman",
                    size_pt=FONT_SIZE["三号"],
                    bold=True,
                    align=WD_ALIGN_PARAGRAPH.CENTER,
                    space_before=12.0,
                    space_after=6.0,
                )
            else:
                # 其它章 / 摘要 / Abstract / 参考文献 / 成果 — 四号黑体加粗左对齐
                _apply_para(
                    p,
                    cjk_font="黑体",
                    ascii_font="Times New Roman",
                    size_pt=FONT_SIZE["四号"],
                    bold=True,
                    align=WD_ALIGN_PARAGRAPH.LEFT,
                    space_before=12.0,
                    space_after=6.0,
                )
        elif lvl == 2:
            _apply_para(
                p,
                cjk_font="黑体",
                ascii_font="Times New Roman",
                size_pt=FONT_SIZE["小四"],
                bold=True,
                align=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=6.0,
                space_after=3.0,
            )
        elif lvl == 3 or lvl == 4:
            # Heading 4 视觉上下沉为三级标题样式（规范"最多三级"）
            _apply_para(
                p,
                cjk_font="宋体",
                ascii_font="Times New Roman",
                size_pt=FONT_SIZE["小四"],
                bold=True,
                align=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=3.0,
                space_after=3.0,
            )
        elif style in ("Caption", "Image Caption", "Table Caption"):
            # 图题/表题：小四黑体加粗居中（用户要求黑体），显式清除 Caption 样式的 italic 继承
            # 区分图题 vs 表题：按段落首字符"图"/"表"判定
            #   - 图题：段前 0、段后 6 磅（图在上、图题在下、与正文留白）
            #   - 表题：段前 6 磅、段后 0（表题在上、表在下、与正文留白）
            is_table_cap = text.startswith("表")
            _apply_para(
                p,
                cjk_font="黑体",
                ascii_font="Times New Roman",
                size_pt=FONT_SIZE["小四"],
                bold=True,
                align=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=6.0 if is_table_cap else 0.0,
                space_after=0.0 if is_table_cap else 6.0,
            )
            for run in p.runs:
                run.font.italic = False  # 根除 pandoc Caption 样式默认 italic
        elif style == "Captioned Figure":
            # 图本体段，居中；不覆盖图片本身的 run
            pf = p.paragraph_format
            pf.line_spacing = 1.5
            pf.space_before = Pt(3.0)
            pf.space_after = Pt(3.0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif style.lower().startswith(("bibliograph", "reference")):
            # pandoc 参考文献：中文宋体小四 / 英文 TNR 小四 / 固定行距 20 磅（规范 R5）
            _apply_para(
                p,
                cjk_font="宋体",
                ascii_font="Times New Roman",
                size_pt=FONT_SIZE["小四"],
                bold=False,
                align=WD_ALIGN_PARAGRAPH.JUSTIFY,
            )
            # 覆盖 line_spacing 为 固定 20 磅
            from docx.enum.text import WD_LINE_SPACING

            pf = p.paragraph_format
            pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
            pf.line_spacing = Pt(20)
        else:
            # 正文
            _apply_para(
                p,
                cjk_font="宋体",
                ascii_font="Times New Roman",
                size_pt=FONT_SIZE["小四"],
                bold=False,
                first_line_chars=2 if text else 0,
            )

    # 表格单元格也统一样式
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _apply_para(
                        p,
                        cjk_font="宋体",
                        ascii_font="Times New Roman",
                        size_pt=FONT_SIZE["小四"],
                        bold=False,
                        align=WD_ALIGN_PARAGRAPH.CENTER,
                        line_spacing=1.0,
                    )

    # 6.5. 子图图注刷成图题规格（黑体小四加粗，前缀 a)/b)/c)）
    #      必须在通用 cell 样式循环之后，否则会被刷回宋体不加粗
    style_subfigure_captions(doc)

    # 7. 主样式循环完成后：插入中英文论文题目页（避免被 Normal 样式覆盖字号）
    insert_thesis_title_pages(doc)

    # 8. 最后搬模板封面+声明+授权+目录到正文之前（模板段直接带自己的样式，不被循环覆盖）
    prepend_front_matter(doc)

    # 8.5. 封面信息填充（题目、学院、专业、班级、学号、姓名、指导教师、日期）
    fill_cover_info(doc)

    # 9. 页面尺寸 / 页边距 / 分节 / 页码页脚
    _set_page_margins_a4(doc)
    setup_page_numbers_and_sections(doc)

    # 10. 表格三线化 + 整表居中；图片段居中
    apply_three_line_tables(doc)
    center_all_images(doc)

    # 11. 公式编号：独立公式右对齐 "（N-M）"
    add_equation_numbers(doc)

    # 12. 代码清单 + 算法伪代码 → 单格全外框表（必须在三线表 pass 之后）
    wrap_listings_and_algorithms(doc)

    # 12.5 代码块表格：五号字、不首行缩进、左对齐（必须在 wrap_listings 之后）
    style_code_block_tables(doc)

    # 12.6 所有表格 cell 水平 + 垂直居中（代码块只设垂直居中，水平保持 left）
    center_all_table_cells(doc)

    # 12.7 数据型表格 cell 字号统一五号（10.5pt）；子图布局表/代码块表/封面表跳过
    apply_table_body_font_size(doc)

    # 12.8 代码题/算法题标题段刷成表题规格（小四黑体加粗居中 + 段前6pt段后0）
    _style_code_algorithm_captions(doc)

    # 13. 列表自动编号顶格（清 numbering.xml 所有 lvl 的 ind left/hanging）
    flatten_list_indent(doc)

    # 14. 压缩声明+授权同页
    compress_declaration_and_authorization(doc)

    # 15. 封面/签名页"左标签 + 右字段"用 tab 左右对齐
    tab_align_cover_and_signature_rows(doc)

    # 16. 折叠 H1 "摘要" / "Abstract" 独立标题段（锚点已消费完，版面保留段首粗体前缀形式）
    fold_abstract_heading_into_body(doc)

    # 16.5. 摘要/Abstract/关键词段首前缀加粗 + eastAsia 改黑体
    #       必须放在所有 _apply_para 遍历（主循环）之后，否则黑体会被宋体覆盖
    bolden_abstract_prefixes(doc)

    # 17. 中文正文里的半角单双引号修成全角，避开代码块
    normalize_text_punctuation(doc)

    # 18. 参考文献英文小圆点后补空格
    normalize_bibliography_text(doc)

    # 19. 最后一道闸：全文档字体正则化（宋体 + Times New Roman）
    #     CJK_SAFE 含"黑体"，不会覆盖刚设好的前缀黑体
    normalize_all_fonts(doc)

    # 20. 正文段两端对齐（jc=both），放在最后保证所有段都已定型
    justify_body_paragraphs(doc)

    # 21. 段间距/首行缩进/snapToGrid 全局规格化（最后执行，覆盖所有段）
    normalize_paragraph_spacing(doc)

    # 21.5 允许 PathBoundsDecider 这类长驼峰词从中间拆行
    enable_latin_word_break(doc)

    # 22. 目录项缩进/段后按检测报告口径收口
    normalize_toc_entries(doc)

    doc.save(str(docx_path))


def _insert_blank_before_abstract(doc) -> None:
    """在 "Abstract:"/"Abstract：" 所在段之前插入一个空段，形成中英文摘要之间的过渡空行。
    幂等：若紧前一段已经是空段则跳过。"""
    from docx.oxml.ns import qn as _qn
    from docx.oxml import OxmlElement as _OxmlElement

    body = doc.element.body
    children = list(body)
    for idx, child in enumerate(children):
        if child.tag != _qn("w:p"):
            continue
        txt = "".join(
            (t.text or "") for t in child.findall(".//" + _qn("w:t"))
        ).lstrip()
        if not (txt.startswith("Abstract:") or txt.startswith("Abstract：")):
            continue
        # 幂等检查：上一段如果已经是空段（无 w:t 或全空）则跳过
        if idx > 0:
            prev = children[idx - 1]
            if prev.tag == _qn("w:p"):
                prev_txt = "".join(
                    (t.text or "") for t in prev.findall(".//" + _qn("w:t"))
                )
                if not prev_txt.strip():
                    return
        blank = _OxmlElement("w:p")
        child.addprevious(blank)
        return
