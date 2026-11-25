"""Beszkennelt PDF-ből kereshető (szövegréteggel ellátott) PDF készítése Tesseract OCR-rel.

A data/sources.yaml-ban `ocr: true` jelölésű dokumentumokat dolgozza fel:
    data/raw/<id>.pdf  ->  data/raw/<id>.ocr.pdf
A parser ezután az .ocr.pdf változatot olvassa.

Használat:
    uv run python scripts/ocr_pdf.py                 # minden ocr: true dokumentum
    uv run python scripts/ocr_pdf.py --only tjsz --pages 1-5

Előfeltétel: Tesseract magyar nyelvi modellel. Windows + MSYS2 alatt:
    pacman -S mingw-w64-ucrt-x86_64-tesseract-ocr mingw-w64-ucrt-x86_64-tesseract-data-hun
A tessdata mappa a TESSDATA_PREFIX környezeti változóból jön, alapértelmezés: C:/msys64/ucrt64/share/tessdata
(A PyMuPDF beépített Tesseract-motorja végzi az OCR-t, csak a nyelvi modellfájlok kellenek.)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pymupdf
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TESSDATA = os.environ.get("TESSDATA_PREFIX", "C:/msys64/ucrt64/share/tessdata")
DPI = 300
LANG = "hun"


def ocr_page(args: tuple[str, int]) -> tuple[int, bytes]:
    src, pno = args
    with pymupdf.open(src) as doc:
        pix = doc[pno].get_pixmap(dpi=DPI)
    return pno, pix.pdfocr_tobytes(language=LANG, tessdata=TESSDATA)


def parse_pages(spec: str | None, n: int) -> list[int]:
    if not spec:
        return list(range(n))
    a, _, b = spec.partition("-")
    return list(range(int(a) - 1, int(b or a)))


def ocr_document(doc_id: str, pages: str | None, workers: int) -> Path:
    src = RAW / f"{doc_id}.pdf"
    dst = RAW / f"{doc_id}.ocr.pdf"
    with pymupdf.open(src) as d:
        pnos = parse_pages(pages, len(d))
    t0 = time.time()
    results: dict[int, bytes] = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, (pno, pdf_bytes) in enumerate(ex.map(ocr_page, [(str(src), p) for p in pnos]), 1):
            results[pno] = pdf_bytes
            if i % 10 == 0 or i == len(pnos):
                print(f"  {doc_id}: {i}/{len(pnos)} oldal ({time.time() - t0:.0f} s)", flush=True)
    out = pymupdf.open()
    for pno in sorted(results):
        with pymupdf.open("pdf", results[pno]) as page_doc:
            out.insert_pdf(page_doc)
    out.set_metadata({"title": f"{doc_id} (OCR: Tesseract {LANG}, {DPI} dpi)", "producer": "kerdezd-a-tvszt/scripts/ocr_pdf.py"})
    out.save(dst, garbage=3, deflate=True)
    return dst


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--pages", help="pl. 1-5 (1-től számozva)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    args = ap.parse_args()

    if not Path(TESSDATA, f"{LANG}.traineddata").exists():
        print(f"Hiányzik a {LANG}.traineddata itt: {TESSDATA}", file=sys.stderr)
        return 1
    docs = yaml.safe_load((ROOT / "data" / "sources.yaml").read_text(encoding="utf-8"))["documents"]
    ids = [d["id"] for d in docs if d.get("ocr")]
    if args.only:
        ids = [i for i in ids if i in set(args.only)]
    for doc_id in ids:
        dst = ocr_document(doc_id, args.pages, args.workers)
        print(f"Kész: {dst.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
