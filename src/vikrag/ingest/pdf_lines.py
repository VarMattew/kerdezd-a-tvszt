"""PDF -> tiszta sorok listája.

Feladatok:
- a spanok újracsoportosítása alapvonal szerint (a sorkizárt sorokat és az OCR-szöveget a PyMuPDF szétszedi),
- lábjegyzetjelek leválasztása (kis betűméretű számok a sor belsejében) és a lábjegyzetszövegek gyűjtése,
- fej-/lábléc, oldalszám, tartalomjegyzék-sorok eldobása,
- OCR-zaj tisztítása (lábjegyzetjelek helyén maradt „?” / „!”),
- táblázatok területének kihagyása (azokat külön dolgozzuk fel).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import pymupdf

FOOTNOTE_TEXT_RE = re.compile(
    r"^(\d{1,3})\s*[.)]?\s+((?:Módosította|Beiktatta|Hatályon kívül|Megállapította|Hatályos|Módosította|Hatálytalan|Kiegészítette|Törölte)\b.*)$"
)
OCR_FOOTNOTE_RE = re.compile(
    r"^\d{0,3}\s*(Módosította|Beiktatta|Törölte|Hatályon kívül helyezte|Megállapította|Kiegészítette)\b.*(határozat|Hatályos)"
)
TOC_RE = re.compile(r"\.{5,}\s*\d+\s*$|…{3,}\s*\d+\s*$")
DIGITS_RE = re.compile(r"^\d{1,3}(?:\s*,\s*\d{1,3})*$")


@dataclass
class Line:
    text: str
    page: int  # 1-től
    x: float
    y: float
    size: float
    bold: bool
    refs: list[str] = field(default_factory=list)  # lábjegyzetjelek


@dataclass
class PdfContent:
    lines: list[Line]
    footnotes: dict[str, str]  # lábjegyzetszám -> szöveg
    page_count: int


def _body_size(page_spans: list[dict]) -> float:
    c: Counter = Counter()
    for s in page_spans:
        c[round(s["size"])] += len(s["text"].strip())
    return float(c.most_common(1)[0][0]) if c else 12.0


def _clean_ocr(text: str) -> str:
    # lábjegyzetjelek maradványai: szó végén / önállóan álló ? és ! jelek, pl. "önköltség?" "rendelkezik.!!" "!5"
    text = re.sub(r"(?<=[\w.,;:)”\"])[?!]+\d*(?=\s|$)", "", text)
    text = re.sub(r"(?:(?<=\s)|^)[?!\"]+\d*(?=\s|$)", "", text)
    text = text.replace("—", "").replace(" ", " ")
    return re.sub(r"\s{2,}", " ", text).strip()


def extract(path: str, ocr: bool = False, skip_tables: bool = False) -> PdfContent:
    doc = pymupdf.open(path)
    raw_lines: list[Line] = []
    footnotes: dict[str, str] = {}

    for pno, page in enumerate(doc, 1):
        h = page.rect.height
        table_rects = []
        if skip_tables:
            try:
                table_rects = [pymupdf.Rect(t.bbox) for t in page.find_tables(use_layout=False).tables]
            except Exception:  # noqa: BLE001
                table_rects = []

        spans = []
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                for s in ln["spans"]:
                    if not s["text"].strip():
                        continue
                    r = pymupdf.Rect(s["bbox"])
                    if any(tr.intersects(r) and tr.contains(r.tl) for tr in table_rects):
                        continue
                    spans.append(s)
        if not spans:
            continue
        body = _body_size(spans)

        # alapvonal szerinti csoportosítás (tűrés a betűméret ~40%-a, így a felső indexű jel is a sorba kerül)
        spans.sort(key=lambda s: (round(s["bbox"][3]), s["bbox"][0]))
        groups: list[list[dict]] = []
        for s in sorted(spans, key=lambda s: s["bbox"][3]):
            y = s["bbox"][3]
            tol = max(2.5, 0.45 * body)
            if groups and abs(groups[-1][0]["_y"] - y) <= tol:
                groups[-1].append(s)
            else:
                s["_y"] = y
                groups.append([s])
            s.setdefault("_y", groups[-1][0]["_y"])

        last_fn: str | None = None
        for g in groups:
            g.sort(key=lambda s: s["bbox"][0])
            refs = []
            sizes = [s["size"] for s in g]
            is_small_line = max(sizes) < body * 0.85
            text, prev_x1, prev_trailing_space = "", None, False
            for s in g:
                raw = s["text"]
                piece = raw.strip()
                small = s["size"] <= body * 0.7
                if small and DIGITS_RE.match(piece) and not is_small_line:
                    refs.extend(x.strip() for x in piece.split(","))
                    continue
                # a spanokat csak akkor választjuk el szóközzel, ha vizuálisan is van köztük rés
                # (kiskapitális szedés: "F" + "EJEZET" -> "FEJEZET")
                gap = s["bbox"][0] - prev_x1 if prev_x1 is not None else 99.0
                if text and (gap > 0.8 or raw[:1].isspace() or prev_trailing_space):
                    text += " "
                text += piece
                prev_x1, prev_trailing_space = s["bbox"][2], raw[-1:].isspace()
            text = re.sub(r"\s{2,}", " ", text).strip()
            if ocr:
                text = _clean_ocr(text)
            if not text:
                continue
            y0 = min(s["bbox"][1] for s in g)
            x0 = g[0]["bbox"][0]

            # lábjegyzet: kis betűs sor az oldal alsó részén, számmal kezdve (vagy OCR-nél a tipikus szöveggel)
            m = FOOTNOTE_TEXT_RE.match(text)
            first_small_num = g[0]["size"] <= body * 0.7 and DIGITS_RE.match(g[0]["text"].strip() or "x")
            if y0 > h * 0.45 and (m or (is_small_line and first_small_num)):
                if m:
                    num, ftxt = m.group(1), m.group(2)
                else:
                    num, ftxt = g[0]["text"].strip(), " ".join(t.strip() for t in [s["text"] for s in g[1:]])
                footnotes[num] = ftxt.strip()
                last_fn = num
                continue
            if last_fn and is_small_line and y0 > h * 0.6:  # lábjegyzet folytatósora
                footnotes[last_fn] += " " + text
                continue
            last_fn = None
            # OCR: a lábjegyzetszám gyakran elvész, de a lábjegyzet szövege felismerhető
            if ocr and y0 > h * 0.45 and OCR_FOOTNOTE_RE.match(text):
                footnotes[f"ocr-{pno}-{len(footnotes)}"] = text
                continue

            # oldalszám és tartalomjegyzék
            if DIGITS_RE.match(text) and (y0 < h * 0.12 or y0 > h * 0.88):
                continue
            if TOC_RE.search(text):
                continue

            # OCR-nél a félkövér jelzés megbízhatatlan, ott nem használjuk
            bold = not ocr and all(
                (s["flags"] & 16) or "Bold" in s["font"] for s in g if s["text"].strip() and s["size"] > body * 0.7
            )
            raw_lines.append(Line(text=text, page=pno, x=x0, y=y0, size=max(sizes), bold=bold, refs=refs))

    # ismétlődő fej-/láblécek: a dokumentum oldalainak legalább 40%-án szó szerint előforduló sorok
    n_pages = len(doc)
    if n_pages >= 4:
        counts = Counter(ln.text for ln in raw_lines)
        repeated = {t for t, c in counts.items() if c >= max(3, 0.4 * n_pages) and len(t) < 120}
        raw_lines = [ln for ln in raw_lines if ln.text not in repeated]
    return PdfContent(lines=raw_lines, footnotes=footnotes, page_count=n_pages)
