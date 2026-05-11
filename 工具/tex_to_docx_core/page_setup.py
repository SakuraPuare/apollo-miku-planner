from __future__ import annotations

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def _set_page_margins_a4(doc) -> None:
    """A4 幅面 + 上下 2.54cm / 左右 3.17cm（规范 V1/V2/V3）。"""
    from docx.shared import Cm

    for s in doc.sections:
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)
        s.top_margin = Cm(2.54)
        s.bottom_margin = Cm(2.54)
        s.left_margin = Cm(3.17)
        s.right_margin = Cm(3.17)


def setup_page_numbers_and_sections(doc) -> None:
    """规范 P5：页码页脚 五号 TNR 居中。整个文档单节阿拉伯页码起 1。
    (P1-P4 罗马/阿拉伯切换需要 Word 打开后手动调整，因为 python-docx 动态分节 API 不稳。)"""
    _enable_update_fields_on_open(doc)

    sect = doc.sections[0]
    footer = sect.footer
    footer.is_linked_to_previous = False
    # 清空现有 footer runs
    if footer.paragraphs:
        p = footer.paragraphs[0]
        for r in list(p.runs):
            r._element.getparent().remove(r._element)
    else:
        p = footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 插入 PAGE 域
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), " PAGE ")
    inner_r = OxmlElement("w:r")
    inner_rPr = OxmlElement("w:rPr")
    rF = OxmlElement("w:rFonts")
    rF.set(qn("w:ascii"), "Times New Roman")
    rF.set(qn("w:hAnsi"), "Times New Roman")
    rF.set(qn("w:eastAsia"), "Times New Roman")
    inner_rPr.append(rF)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "21")  # 五号 10.5pt
    inner_rPr.append(sz)
    szCs = OxmlElement("w:szCs")
    szCs.set(qn("w:val"), "21")
    inner_rPr.append(szCs)
    inner_r.append(inner_rPr)
    inner_t = OxmlElement("w:t")
    inner_t.text = "1"
    inner_r.append(inner_t)
    fld.append(inner_r)
    p._element.append(fld)


def _enable_update_fields_on_open(doc) -> None:
    """让 Word/WPS 打开文档时更新 TOC/PAGE 等域，减少目录页码不一致。"""
    settings = doc.settings.element
    update_fields = settings.find(qn("w:updateFields"))
    if update_fields is None:
        update_fields = OxmlElement("w:updateFields")
        settings.append(update_fields)
    update_fields.set(qn("w:val"), "true")
