from pathlib import Path
import sys
import unittest

try:
    from docx import Document
    from docx.oxml.ns import qn
except ModuleNotFoundError:  # pragma: no cover - depends on local tool env
    Document = None
    qn = None
    _ensure_toc2_not_bold = None
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from 工具.tex_to_docx_core.style import _ensure_toc2_not_bold


def _style_by_id(doc, style_id):
    for style in doc.styles.element.findall(qn("w:style")):
        if style.get(qn("w:styleId")) == style_id:
            return style
    return None


def _rpr(style):
    return style.find(qn("w:rPr"))


@unittest.skipIf(Document is None, "python-docx is required for TOC style tests")
class TocStyleTests(unittest.TestCase):
    def test_toc1_is_bold_and_toc2_is_not_bold(self):
        doc = Document()

        _ensure_toc2_not_bold(doc)

        toc1 = _style_by_id(doc, "TOC1")
        toc2 = _style_by_id(doc, "TOC2")
        self.assertIsNotNone(toc1)
        self.assertIsNotNone(toc2)

        toc1_rpr = _rpr(toc1)
        toc2_rpr = _rpr(toc2)

        for tag in ("w:b", "w:bCs"):
            with self.subTest(style="TOC1", tag=tag):
                bold = toc1_rpr.find(qn(tag))
                self.assertIsNotNone(bold)
                self.assertNotEqual(bold.get(qn("w:val")), "0")

            with self.subTest(style="TOC2", tag=tag):
                bold = toc2_rpr.find(qn(tag))
                self.assertIsNotNone(bold)
                self.assertEqual(bold.get(qn("w:val")), "0")
