from __future__ import annotations

import subprocess
from pathlib import Path

from .config import CSL_PATH, THESIS_DIR

# =============================================================================
# Stage 2 — pandoc
# =============================================================================


def run_pandoc(tex_path: Path, out_path: Path, *, use_bib: bool) -> None:
    cmd = [
        "pandoc",
        str(tex_path),
        "--from",
        "latex",
        "--to",
        "docx",
        "--wrap",
        "none",
        # book class 的 \chapter 天然映射到 Heading 1
        "--top-level-division=chapter",
        "-o",
        str(out_path),
    ]
    if use_bib:
        cmd += [
            "--citeproc",
            "--bibliography",
            str(THESIS_DIR / "references.bib"),
            "--csl",
            str(CSL_PATH),
        ]
    subprocess.run(cmd, check=True)
