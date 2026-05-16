from __future__ import annotations

import pytest
from pathlib import Path
from docx import Document

DOCX_PATH = Path(__file__).resolve().parents[2] / "outputs" / "thesis.docx"


@pytest.fixture(scope="session")
def doc():
    if not DOCX_PATH.exists():
        pytest.skip(f"thesis.docx not found at {DOCX_PATH}")
    return Document(str(DOCX_PATH))
