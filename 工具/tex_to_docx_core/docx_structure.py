from __future__ import annotations

import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .config import REFS_ANCHOR_TEXT, THESIS_DIR
from .docx_common import _make_page_break_para

# 无编号章：摘要/Abstract/参考文献/致谢/成果 —— 不计入 \chapter 编号
NON_NUMBERED_HEADINGS_1 = {
    "摘要",
    "Abstract",
    "参考文献",
    "致谢",
    "致 谢",
    "本科期间的学习与科研成果",
}

# 这些章单独起一页
PAGE_BREAK_BEFORE_HEADINGS = {
    "参考文献",
    "致谢",
    "本科期间的学习与科研成果",
}
# 全部 Heading 1 都要分页（除了首个"摘要"——它紧跟目录 TOC 分页）
PAGE_BREAK_ALL_H1 = True


def _relocate_bibliography(doc) -> None:
    """pandoc citeproc 把参考文献条目放在文档末尾；把它们整体搬到 anchor 一级标题之后。"""
    body = doc.element.body
    # 1. 找 anchor（文字为"参考文献"的 Heading 1）
    anchor = None
    for p in doc.paragraphs:
        if (
            p.style
            and p.style.name == "Heading 1"
            and p.text.strip() == REFS_ANCHOR_TEXT
        ):
            anchor = p._element
            break
    if anchor is None:
        return  # 没埋 anchor，放弃搬运

    # 2. 收集所有 Bibliography 段（pandoc 给参考文献条目的样式名）
    bib_elems = [
        p._element for p in doc.paragraphs if p.style and p.style.name == "Bibliography"
    ]
    if not bib_elems:
        return

    # 3. 搬运：先 detach，再按序 insert 到 anchor 之后
    for el in bib_elems:
        el.getparent().remove(el)

    # anchor 在 body 里的下标
    children = list(body)
    anchor_idx = children.index(anchor)
    for offset, el in enumerate(bib_elems, start=1):
        body.insert(anchor_idx + offset, el)


def _extract_thesis_titles() -> tuple[str, str]:
    """从 info.tex 提取中英文论文题目。"""
    info = THESIS_DIR / "info.tex"
    if not info.exists():
        return ("论文题目", "Thesis Title")
    text = info.read_text(encoding="utf-8")

    def _find(cmd: str) -> str:
        m = re.search(rf"\\newcommand\{{\\{cmd}\}}\{{([^}}]*)\}}", text)
        return m.group(1) if m else ""

    zh_a = _find("thesisTitleZhA")
    zh_b = _find("thesisTitleZhB")
    zh = (zh_a + zh_b).strip() or "论文题目"
    en = _find("thesisTitleEn").replace("\\\\", " ").replace("  ", " ").strip()
    return zh, en or "Thesis Title"


def insert_page_breaks_before_headings(doc) -> None:
    """在所有 Heading 1 之前插入分页符（首个除外），对齐规范"每个一级标题前插入分页符"。"""
    h1_list = [p for p in doc.paragraphs if p.style and p.style.name == "Heading 1"]
    for i, p in enumerate(h1_list):
        if i == 0:
            # 首个 Heading 1（通常是"摘要"）紧跟目录 TOC 分页，不重复加
            continue
        # 若前一段已有分页符则跳过（避免 prepend_front_matter 之后重复）
        prev_el = p._element.getprevious()
        if prev_el is not None:
            has_break = any(
                br.get(qn("w:type")) == "page" for br in prev_el.iter(qn("w:br"))
            )
            if has_break:
                continue
        page_break_p = _make_page_break_para(doc)
        p._element.addprevious(page_break_p)


def demote_heading4_to_heading3(doc) -> None:
    """规范"最多三级标题，不得出现四级标题"：把 Heading 4 样式降级为 Heading 3。"""
    try:
        h3_style = doc.styles["Heading 3"]
    except KeyError:
        return
    for p in doc.paragraphs:
        if p.style and p.style.name == "Heading 4":
            p.style = h3_style


def normalize_special_h1_text(doc) -> None:
    """致谢 → 致 谢（中间空一字符，对齐规范"致 谢"要求）。"""
    for p in doc.paragraphs:
        if p.style and p.style.name == "Heading 1" and p.text.strip() == "致谢":
            if p.runs:
                for r in p.runs:
                    r.text = r.text.replace("致谢", "致 谢")


def insert_thesis_title_pages(doc) -> None:
    """在"摘要"Heading 1 前插入中文论文题目段；在"Abstract"前插入英文论文题目段。
    题目：三号(16pt) 黑体/TNR 加粗居中，单独成页（前加分页符）。"""
    zh_title, en_title = _extract_thesis_titles()

    def _make_title_p(text: str, cjk: str, ascii_: str) -> OxmlElement:
        p = OxmlElement("w:p")
        pPr = OxmlElement("w:pPr")
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), "center")
        pPr.append(jc)
        sp = OxmlElement("w:spacing")
        sp.set(qn("w:before"), "120")  # 6pt
        sp.set(qn("w:after"), "31")  # 1.54pt
        pPr.append(sp)
        p.append(pPr)
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        rFonts = OxmlElement("w:rFonts")
        rFonts.set(qn("w:ascii"), ascii_)
        rFonts.set(qn("w:hAnsi"), ascii_)
        rFonts.set(qn("w:eastAsia"), cjk)
        rPr.append(rFonts)
        b = OxmlElement("w:b")
        rPr.append(b)
        bcs = OxmlElement("w:bCs")
        rPr.append(bcs)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "32")  # 三号 16pt → sz=32 half-points
        rPr.append(sz)
        szCs = OxmlElement("w:szCs")
        szCs.set(qn("w:val"), "32")
        rPr.append(szCs)
        r.append(rPr)
        t = OxmlElement("w:t")
        t.text = text
        t.set(qn("xml:space"), "preserve")
        r.append(t)
        p.append(r)
        return p

    for anchor_text in ("摘要", "Abstract"):
        anchor = next(
            (
                p
                for p in doc.paragraphs
                if p.style
                and p.style.name == "Heading 1"
                and p.text.strip() == anchor_text
            ),
            None,
        )
        if anchor is None:
            continue
        if anchor_text == "摘要":
            title_p = _make_title_p(zh_title, "黑体", "Times New Roman")
        else:
            title_p = _make_title_p(en_title, "Times New Roman", "Times New Roman")
        anchor._element.addprevious(title_p)


def _prepend_run_text(p, text: str) -> None:
    """在段落首 run 开头插入文字；无 run 则新建一个（继承段落样式）。"""
    if p.runs:
        r = p.runs[0]
        r.text = text + (r.text or "")
    else:
        p.add_run(text)


def add_heading_numbers(doc) -> None:
    """按章节层次给 Heading 1/2/3/4 前缀自动编号，对齐模板"1 / 1.1 / 1.1.1"风格。
    摘要/Abstract/参考文献/致谢/成果 等无编号章跳过（但会重置子计数器）。"""
    chap = sec = subsec = subsubsec = 0
    for p in doc.paragraphs:
        sn = p.style.name if p.style else ""
        text = p.text.strip()
        if sn == "Heading 1":
            if text in NON_NUMBERED_HEADINGS_1:
                sec = subsec = subsubsec = 0
                continue
            chap += 1
            sec = subsec = subsubsec = 0
            _prepend_run_text(p, f"{chap} ")
        elif sn == "Heading 2" and chap > 0:
            sec += 1
            subsec = subsubsec = 0
            _prepend_run_text(p, f"{chap}.{sec} ")
        elif sn == "Heading 3" and chap > 0 and sec > 0:
            subsec += 1
            subsubsec = 0
            _prepend_run_text(p, f"{chap}.{sec}.{subsec} ")
        elif sn == "Heading 4" and chap > 0 and sec > 0 and subsec > 0:
            subsubsec += 1
            _prepend_run_text(p, f"{chap}.{sec}.{subsec}.{subsubsec} ")


def _make_toc_block(doc) -> list:
    """构造 Word 原生 TOC 域 + 前置的"目录"标题段。返回段 XML 列表。"""
    from docx.oxml import OxmlElement

    els = []

    # "目  录" 标题段
    title_p = OxmlElement("w:p")
    title_pPr = OxmlElement("w:pPr")
    title_jc = OxmlElement("w:jc")
    title_jc.set(qn("w:val"), "center")
    title_pPr.append(title_jc)
    title_p.append(title_pPr)
    title_r = OxmlElement("w:r")
    title_rPr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    rf.set(qn("w:eastAsia"), "黑体")
    rf.set(qn("w:ascii"), "黑体")
    title_rPr.append(rf)
    b = OxmlElement("w:b")
    title_rPr.append(b)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "32")
    title_rPr.append(sz)
    title_r.append(title_rPr)
    title_t = OxmlElement("w:t")
    title_t.text = "目  录"
    title_r.append(title_t)
    title_p.append(title_r)
    els.append(title_p)

    # TOC 域段
    toc_p = OxmlElement("w:p")
    # begin
    r1 = OxmlElement("w:r")
    fc1 = OxmlElement("w:fldChar")
    fc1.set(qn("w:fldCharType"), "begin")
    r1.append(fc1)
    toc_p.append(r1)
    # instrText
    r2 = OxmlElement("w:r")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = ' TOC \\o "1-2" \\h \\z \\u '
    r2.append(it)
    toc_p.append(r2)
    # separate
    r3 = OxmlElement("w:r")
    fc2 = OxmlElement("w:fldChar")
    fc2.set(qn("w:fldCharType"), "separate")
    r3.append(fc2)
    toc_p.append(r3)
    # 占位文字
    r4 = OxmlElement("w:r")
    t4 = OxmlElement("w:t")
    t4.text = "（打开文档后右键目录→更新域 即可生成实际目录）"
    r4.append(t4)
    toc_p.append(r4)
    # end
    r5 = OxmlElement("w:r")
    fc3 = OxmlElement("w:fldChar")
    fc3.set(qn("w:fldCharType"), "end")
    r5.append(fc3)
    toc_p.append(r5)
    els.append(toc_p)

    # 分页符，让正文（摘要）落到下一页
    els.append(_make_page_break_para(doc))
    return els
