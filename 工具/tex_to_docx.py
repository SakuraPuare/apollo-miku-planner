#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-docx>=1.1.2",
# ]
# ///
"""tex_to_docx.py — 把 毕业论文/thesis.tex 转成符合学校《规范化要求》的 Word 文档。

用法：
  uv run 工具/tex_to_docx.py                   # 输出 outputs/thesis.docx
  uv run 工具/tex_to_docx.py --no-bib          # 跳过参考文献处理（调试用）
"""

from __future__ import annotations

import sys

from tex_to_docx_core.cli import main


if __name__ == "__main__":
    sys.exit(main())
