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
    resize_vertical_subfigure_drawings,
    split_vertical_subfigure_tables,
    style_code_block_tables,
    style_subfigure_captions,
    wrap_listings_and_algorithms,
)

# =============================================================================
# Stage 3 — post-process via python-docx
# =============================================================================


_CODE_ALGO_CAPTION_RE = re.compile(r"^(?:代码|算法)\s*\d+[\.-]\d+\s")


def _migrate_heading_bold_to_style(doc) -> None:
    """把 Heading1/Heading2 的 "bold + 黑体" 从 run-level 迁移到 style-level。

    动机：Word 更新 TOC 域时，按不同实现版本，可能会把源 heading paragraph
    里的 run-level 格式（<w:b/>、<w:rFonts eastAsia="黑体"/>）拷贝到 TOC 项里，
    覆盖 TOC 样式自身的粗体定义。现在的规范是 TOC1 保持加粗黑体，TOC2 保持宋体
    不加粗，所以这里要把 heading 的粗体收回到 style-level，避免二级目录被污染。

    修复路径：
    1. 在 Heading1 / Heading2 style 的 rPr 上补 <w:b/> 和 eastAsia="黑体"，
       保证正文 H1/H2 视觉仍为黑体加粗（靠段落样式继承）。
    2. 遍历所有 H1/H2 paragraph runs，移除 run-level <w:b/>、<w:bCs/> 以及
       rFonts 的 eastAsia="黑体" 属性；让 run 不再携带 bold 格式 override，
       这样 TOC2 不会被 heading 的直设格式带成加粗。

    这样 Word/WPS 在"更新目录域"时拷 run-level 属性也拷不到 bold。"""
    from docx.oxml import OxmlElement as _OxmlElement
    from docx.oxml.ns import qn as _qn

    styles_el = doc.styles.element
    for style_id in ("Heading1", "Heading2", "Heading3", "Heading4", "Heading5", "Heading6"):
        style = None
        for s in styles_el.findall(_qn("w:style")):
            if s.get(_qn("w:styleId")) == style_id:
                style = s
                break
        if style is None:
            continue
        rPr = style.find(_qn("w:rPr"))
        if rPr is None:
            rPr = _OxmlElement("w:rPr")
            style.append(rPr)
        # 确保 rFonts 上 eastAsia=黑体（中文），ascii/hAnsi 继承 Times New Roman
        rFonts = rPr.find(_qn("w:rFonts"))
        if rFonts is None:
            rFonts = _OxmlElement("w:rFonts")
            rPr.insert(0, rFonts)
        # H1/H2 用黑体加粗，H3+ 用宋体加粗（与 _apply_para 保持一致）
        rFonts.set(_qn("w:eastAsia"), "黑体" if style_id in ("Heading1", "Heading2") else "宋体")
        rFonts.set(_qn("w:ascii"), "Times New Roman")
        rFonts.set(_qn("w:hAnsi"), "Times New Roman")
        rFonts.set(_qn("w:cs"), "Times New Roman")
        # 清除 theme-based font 属性，防止 theme 覆盖具体值
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rFonts.get(_qn(attr)) is not None:
                del rFonts.attrib[_qn(attr)]
        # 确保 <w:b/> 和 <w:bCs/> 存在
        for tag in ("w:b", "w:bCs"):
            if rPr.find(_qn(tag)) is None:
                rPr.append(_OxmlElement(tag))
        # 颜色强制黑色（覆盖模板 themeColor accent1 的深蓝；也让 heading 里嵌入的公式为黑）
        color = rPr.find(_qn("w:color"))
        if color is None:
            color = _OxmlElement("w:color")
            rPr.append(color)
        color.set(_qn("w:val"), "000000")
        for attr in ("w:themeColor", "w:themeShade", "w:themeTint"):
            if color.get(_qn(attr)) is not None:
                del color.attrib[_qn(attr)]

    # 遍历所有 Heading N paragraph runs，剥除 run-level bold 和 eastAsia=黑体
    for p in doc.paragraphs:
        sname = p.style.name
        if not sname.startswith("Heading "):
            continue
        for r in p.runs:
            rPr = r._element.find(_qn("w:rPr"))
            if rPr is None:
                continue
            for tag in ("w:b", "w:bCs"):
                for old in rPr.findall(_qn(tag)):
                    rPr.remove(old)
            rFonts = rPr.find(_qn("w:rFonts"))
            if rFonts is not None:
                # 让 eastAsia 由 style 接管；ascii/hAnsi 保持 Times New Roman
                if rFonts.get(_qn("w:eastAsia")) in ("黑体", "宋体"):
                    del rFonts.attrib[_qn("w:eastAsia")]


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


def _unmono_code_styles(doc) -> None:
    """去掉 pandoc 给 inline code / code block 施加的等宽字体。

    pandoc 转 LaTeX `\\texttt{...}` 和 `\\begin{lstlisting}...` 时分别产出
    ``VerbatimChar`` 字符样式（Consolas）和 ``SourceCode`` 段落样式（link 到
    VerbatimChar）。用户规范要求全文统一宋体正文 + Times New Roman 西文，
    驼峰词 ``PathBoundsDecider`` 等 inline code 不要以 Consolas 等宽显示，
    代码块段落也统一回正文字形。

    做法：覆盖两个样式的 rFonts（ascii/hAnsi/cs = Times New Roman，eastAsia =
    宋体），清空 sz 让它继承段落大小。"""
    from docx.oxml import OxmlElement as _OxmlElement
    from docx.oxml.ns import qn as _qn

    styles_el = doc.styles.element
    targets = {"VerbatimChar", "SourceCode", "Verbatim"}
    for s in styles_el.findall(_qn("w:style")):
        sid = s.get(_qn("w:styleId"))
        if sid not in targets:
            continue
        rPr = s.find(_qn("w:rPr"))
        if rPr is None:
            rPr = _OxmlElement("w:rPr")
            s.append(rPr)
        rFonts = rPr.find(_qn("w:rFonts"))
        if rFonts is None:
            rFonts = _OxmlElement("w:rFonts")
            rPr.insert(0, rFonts)
        rFonts.set(_qn("w:ascii"), "Times New Roman")
        rFonts.set(_qn("w:hAnsi"), "Times New Roman")
        rFonts.set(_qn("w:cs"), "Times New Roman")
        rFonts.set(_qn("w:eastAsia"), "宋体")
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rFonts.get(_qn(attr)) is not None:
                del rFonts.attrib[_qn(attr)]
        # 清掉 sz，让段落/上下文决定字号
        for tag in ("w:sz", "w:szCs"):
            for old in rPr.findall(_qn(tag)):
                rPr.remove(old)

    # run-level 清洗：正文里若直接给 run 设了 Consolas/Courier（docx 有时写死），改为 Times New Roman
    mono_names = {"Consolas", "Courier New", "Courier", "DejaVu Sans Mono", "Monaco", "Menlo"}
    for p in doc.paragraphs:
        for r in p.runs:
            rPr = r._element.find(_qn("w:rPr"))
            if rPr is None:
                continue
            rFonts = rPr.find(_qn("w:rFonts"))
            if rFonts is None:
                continue
            changed = False
            for attr in ("w:ascii", "w:hAnsi", "w:cs"):
                val = rFonts.get(_qn(attr))
                if val in mono_names:
                    rFonts.set(_qn(attr), "Times New Roman")
                    changed = True
            if rFonts.get(_qn("w:eastAsia")) in mono_names:
                rFonts.set(_qn("w:eastAsia"), "宋体")
                changed = True
            _ = changed  # 显式标记一下方便调试

    # 表格 cell 里的 runs 同样处理（代码块被包进单格表）
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        rPr = r._element.find(_qn("w:rPr"))
                        if rPr is None:
                            continue
                        rFonts = rPr.find(_qn("w:rFonts"))
                        if rFonts is None:
                            continue
                        for attr in ("w:ascii", "w:hAnsi", "w:cs"):
                            val = rFonts.get(_qn(attr))
                            if val in mono_names:
                                rFonts.set(_qn(attr), "Times New Roman")
                        if rFonts.get(_qn("w:eastAsia")) in mono_names:
                            rFonts.set(_qn("w:eastAsia"), "宋体")


def _force_hyperlinks_black(doc) -> None:
    """论文规范要求全文黑色，包括参考文献里的 DOI/URL 超链接。
    pandoc 默认超链接是 Word 的 Hyperlink 字符样式（蓝+下划线）；
    这里对所有 ``<w:hyperlink>`` 内部 run 的 ``<w:color>`` 强制设为 000000，
    同时把字符样式从 Hyperlink 解绑，避免 Word 重置颜色。"""
    from docx.oxml import OxmlElement as _OxmlElement
    from docx.oxml.ns import qn as _qn

    hyps = doc.element.body.findall('.//' + _qn('w:hyperlink'))
    for h in hyps:
        for r in h.findall('.//' + _qn('w:r')):
            rPr = r.find(_qn('w:rPr'))
            if rPr is None:
                rPr = _OxmlElement('w:rPr')
                r.insert(0, rPr)
            # 解绑 Hyperlink 字符样式，让颜色设定不被样式重置
            for rStyle in list(rPr.findall(_qn('w:rStyle'))):
                if rStyle.get(_qn('w:val')) in ('Hyperlink', 'FootnoteReference'):
                    rPr.remove(rStyle)
            # 强制 color=000000
            color = rPr.find(_qn('w:color'))
            if color is None:
                color = _OxmlElement('w:color')
                rPr.append(color)
            color.set(_qn('w:val'), '000000')
            # 去掉下划线（themeColor 可能也带蓝），保留纯黑文本
            for u in list(rPr.findall(_qn('w:u'))):
                rPr.remove(u)


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

    # 5.5 摘要/Abstract 段前各插一个空行（题目与正文之间留一行过渡）
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
    #      先把带竖排 marker 的 1×N 表转 N×1，再把竖排图放大到文本宽，再打样式
    split_vertical_subfigure_tables(doc)
    resize_vertical_subfigure_drawings(doc)
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

    # 23. 超链接（DOI/URL 等）强制黑色，满足"全文黑色"规范
    _force_hyperlinks_black(doc)

    # 24. H1/H2 的 bold+黑体 从 run-level 迁移到 style-level
    #     防止 Word 更新 TOC 域时把直设格式拷到 TOC2
    _migrate_heading_bold_to_style(doc)

    # 25. 去掉 pandoc 给 inline code (\texttt) 和代码块的 Consolas 等宽字体
    #     用户要求代码展示不用等宽，统一回正文字形
    _unmono_code_styles(doc)

    doc.save(str(docx_path))


def _insert_blank_before_abstract(doc) -> None:
    """在"摘要："/"Abstract:"所在段之前各插入一个空段，让论文题目与摘要正文之间留一空行过渡。
    幂等：若紧前一段已经是空段则跳过。"""
    from docx.oxml.ns import qn as _qn
    from docx.oxml import OxmlElement as _OxmlElement

    prefixes = ("摘要：", "摘要:", "Abstract:", "Abstract：")
    body = doc.element.body
    children = list(body)
    inserted = set()
    for idx, child in enumerate(children):
        if child.tag != _qn("w:p"):
            continue
        txt = "".join(
            (t.text or "") for t in child.findall(".//" + _qn("w:t"))
        ).lstrip()
        matched = next((pfx for pfx in prefixes if txt.startswith(pfx)), None)
        if matched is None:
            continue
        kind = "zh" if matched.startswith("摘要") else "en"
        if kind in inserted:
            continue
        if idx > 0:
            prev = children[idx - 1]
            if prev.tag == _qn("w:p"):
                prev_txt = "".join(
                    (t.text or "") for t in prev.findall(".//" + _qn("w:t"))
                )
                if not prev_txt.strip():
                    inserted.add(kind)
                    continue
        blank = _OxmlElement("w:p")
        child.addprevious(blank)
        inserted.add(kind)
