from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from .config import CSL_PATH, OUTPUT_DIR
from .flatten import flatten_tex
from .pandoc import run_pandoc
from .postprocess import post_process

DESCRIPTION = """tex_to_docx.py — 把 毕业论文/thesis.tex 转成符合学校《规范化要求》的 Word 文档。

流水线三阶段：
  1. 扁平化：合并各章 .tex，展开 info.tex / _experiment_metrics.tex 等自定义
     \\newcommand 宏；移除 figure 块（MVP 版不处理图）。
  2. pandoc 转 docx：数学公式走原生 OMML，citation 走 GB/T 7714-2015 CSL。
  3. python-docx 后处理：按《规范化要求》批改字体、字号、行距、首行缩进。

用法：
  uv run 工具/tex_to_docx.py                   # 输出 outputs/thesis.docx
  uv run 工具/tex_to_docx.py --no-bib          # 跳过参考文献处理（调试用）
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("-o", "--output", type=Path, default=OUTPUT_DIR / "thesis.docx")
    ap.add_argument("--no-bib", action="store_true", help="跳过 citeproc，便于调试排版")
    ap.add_argument(
        "--keep-flat", type=Path, help="把扁平化后的中间 tex 留到指定路径供检查"
    )
    args = ap.parse_args(argv)

    if not CSL_PATH.exists():
        print(f"[fatal] CSL 未就绪: {CSL_PATH}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    print("[1/3] 扁平化 LaTeX ...")
    flat = flatten_tex()
    with tempfile.TemporaryDirectory() as tmp:
        flat_path = Path(tmp) / "flat.tex"
        flat_path.write_text(flat, encoding="utf-8")
        if args.keep_flat:
            args.keep_flat.parent.mkdir(parents=True, exist_ok=True)
            args.keep_flat.write_text(flat, encoding="utf-8")
            print(f"       扁平化 tex → {args.keep_flat}")

        print(f"[2/3] pandoc 转 docx (citeproc={'off' if args.no_bib else 'on'}) ...")
        run_pandoc(flat_path, args.output, use_bib=not args.no_bib)

    print("[3/3] python-docx 后处理 ...")
    post_process(args.output)

    print(f"\n✔ 完成 → {args.output}")
    return 0
