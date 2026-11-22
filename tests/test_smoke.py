"""F0 füstteszt: a környezet működik, és a TVSZ-PDF szövegrétege tartalmazza a bekezdésszámokat."""
import re
from pathlib import Path

import pytest

TVSZ = Path(__file__).resolve().parents[1] / "data" / "raw" / "tvsz" / "BME_TVSZ.pdf"


def test_package_imports():
    import vikrag  # noqa: F401


@pytest.mark.skipif(not TVSZ.exists(), reason="a nyers TVSZ nincs letöltve (data/raw gitignore-olva)")
def test_tvsz_has_paragraph_numbers():
    import pymupdf

    doc = pymupdf.open(TVSZ)
    text = "\n".join(page.get_text() for page in doc)
    assert re.search(r"^\s*56\.\s*§", text, re.M), "hiányzik az 56. §"
    n_bekezdes = len(re.findall(r"^\s*\(\d+[a-z]?\)", text, re.M))
    assert n_bekezdes > 1000, f"túl kevés bekezdéskezdet: {n_bekezdes}"
