from __future__ import annotations

import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor


def _set_rfonts(run, *, ascii_: str | None = None, cjk: str | None = None) -> None:
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    if ascii_:
        rFonts.set(qn("w:ascii"), ascii_)
        rFonts.set(qn("w:hAnsi"), ascii_)
        rFonts.set(qn("w:cs"), ascii_)
    if cjk:
        rFonts.set(qn("w:eastAsia"), cjk)


def _set_first_line_chars(paragraph, chars: int) -> None:
    """按"字符"设置首行缩进；比 pt 更贴近中文排版习惯。"""
    pPr = paragraph._element.get_or_add_pPr()
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLineChars"), str(chars * 100))
    # 清掉 pt 级 firstLine 冲突
    for attr in ("firstLine", "firstLineChars"):
        if attr == "firstLine" and qn(f"w:{attr}") in ind.attrib:
            del ind.attrib[qn(f"w:{attr}")]
    ind.set(qn("w:firstLineChars"), str(chars * 100))


def _is_monospace_run(run) -> bool:
    """判断 run 原始字体是否 Courier/Consolas 类（pandoc 给 \\texttt 的产物）。"""
    rPr = run._element.find(qn("w:rPr"))
    if rPr is None:
        return False
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        return False
    ascii_font = (rFonts.get(qn("w:ascii")) or "").lower()
    return any(k in ascii_font for k in ("courier", "consolas", "mono"))


def _apply_para(
    p,
    *,
    cjk_font: str,
    ascii_font: str,
    size_pt: float,
    bold: bool = False,
    align=None,
    line_spacing: float = 1.5,
    first_line_chars: int = 0,
    space_before: float = 0.0,
    space_after: float = 0.0,
    color_rgb: tuple[int, int, int] = (0, 0, 0),
) -> None:
    pf = p.paragraph_format
    pf.line_spacing = line_spacing
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    if first_line_chars > 0:
        _set_first_line_chars(p, first_line_chars)
    for run in p.runs:
        if _is_monospace_run(run):
            run.font.size = Pt(size_pt)
            run.font.color.rgb = RGBColor(*color_rgb)
            continue
        run.font.size = Pt(size_pt)
        run.font.bold = bold if not run.font.bold else run.font.bold
        run.font.color.rgb = RGBColor(*color_rgb)
        _set_rfonts(run, ascii_=ascii_font, cjk=cjk_font)


def _heading_level(style_name: str) -> int | None:
    m = re.match(r"Heading\s+(\d+)", style_name)
    return int(m.group(1)) if m else None


def _make_page_break_para(doc):
    """构造一个纯分页符段落 XML 元素。"""
    from docx.oxml import OxmlElement

    p = OxmlElement("w:p")
    r = OxmlElement("w:r")
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    r.append(br)
    p.append(r)
    return p
