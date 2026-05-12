from __future__ import annotations

import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor


# =============================================================================
# pPr / rPr 公共工具（其他模块统一引用，避免各自再定义）
# =============================================================================


def _ensure_pPr(p_el):
    """返回段落 w:pPr，没有则插到段首。"""
    pPr = p_el.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p_el.insert(0, pPr)
    return pPr


def _ensure_child(parent, tag: str):
    """获取或创建 parent 的直接子元素 tag（如 "w:spacing"）。"""
    el = parent.find(qn(tag))
    if el is None:
        el = OxmlElement(tag)
        parent.append(el)
    return el


def _set_spacing(pPr, *, before=None, after=None, line=None, lineRule=None):
    """设置 w:spacing 的 before/after/line/lineRule；未传值不动。"""
    sp = _ensure_child(pPr, "w:spacing")
    if before is not None:
        sp.set(qn("w:before"), str(before))
        sp.set(qn("w:beforeLines"), "0")
        sp.set(qn("w:beforeAutospacing"), "0")
    if after is not None:
        sp.set(qn("w:after"), str(after))
        sp.set(qn("w:afterLines"), "0")
        sp.set(qn("w:afterAutospacing"), "0")
    if line is not None:
        sp.set(qn("w:line"), str(line))
    if lineRule is not None:
        sp.set(qn("w:lineRule"), lineRule)
    return sp


def _set_indent(pPr, *, firstLineChars=None, firstLine=None, clear_left: bool = False):
    """设置 w:ind 首行缩进；clear_left=True 时清 left/leftChars/right/rightChars。"""
    ind = _ensure_child(pPr, "w:ind")
    if clear_left:
        for attr in ("leftChars", "left", "rightChars", "right"):
            k = qn(f"w:{attr}")
            if k in ind.attrib:
                del ind.attrib[k]
    if firstLineChars is not None:
        ind.set(qn("w:firstLineChars"), str(firstLineChars))
    if firstLine is not None:
        ind.set(qn("w:firstLine"), str(firstLine))
    return ind


def _set_jc(pPr, val: str):
    """段落对齐：left/center/right/both。"""
    jc = _ensure_child(pPr, "w:jc")
    jc.set(qn("w:val"), val)
    return jc


def _run_clear_bold(r_el):
    """清除 run 的 w:b / w:bCs。"""
    rPr = r_el.find(qn("w:rPr"))
    if rPr is None:
        return
    for tag in ("w:b", "w:bCs"):
        for old in list(rPr.findall(qn(tag))):
            rPr.remove(old)


def _run_set_bold(r_el):
    """强制 run 为加粗（保证无 val=0 残留）。"""
    rPr = r_el.find(qn("w:rPr"))
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        r_el.insert(0, rPr)
    for tag in ("w:b", "w:bCs"):
        for old in list(rPr.findall(qn(tag))):
            rPr.remove(old)
        rPr.append(OxmlElement(tag))


def _run_is_bold(r_el) -> bool:
    """判断 run 是否 run-level bold=True（忽略样式继承）。"""
    rPr = r_el.find(qn("w:rPr"))
    if rPr is None:
        return False
    b = rPr.find(qn("w:b"))
    if b is None:
        return False
    val = b.get(qn("w:val"))
    return val != "0" and val != "false"


def _all_runs_bold(p_el) -> bool:
    """判断段内所有非空 run 是否 run-level 全加粗。
    用于识别 pandoc 从 \\textbf{...} 生成的整段粗体 caption：
    整段所有非空 run 的 rPr 都有 <w:b/>（或 w:b val≠"0"），
    区分于正文段中"算法5-1 给出..."这种正文引用（run 不加粗）。
    """
    t_q = qn("w:t")
    r_q = qn("w:r")
    has_text = False
    for r_el in p_el.findall(r_q):
        txt = "".join((t.text or "") for t in r_el.findall(t_q))
        if not txt.strip():
            continue
        has_text = True
        if not _run_is_bold(r_el):
            return False
    return has_text


def _ptext(p_el) -> str:
    """返回段落全部 w:t 文字拼接。"""
    return "".join((t.text or "") for t in p_el.findall(".//" + qn("w:t")))


def _pstyle(p_el) -> str:
    """返回段落 w:pStyle/@val，没则返回空串。"""
    pPr = p_el.find(qn("w:pPr"))
    if pPr is None:
        return ""
    pStyle = pPr.find(qn("w:pStyle"))
    if pStyle is None:
        return ""
    return pStyle.get(qn("w:val")) or ""


# =============================================================================
# 字体 / 段落格式
# =============================================================================


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
