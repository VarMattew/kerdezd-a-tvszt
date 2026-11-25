"""A teljes korpusz feldolgozása: data/raw/* -> data/processed/chunks.jsonl.

Használat:  uv run python scripts/build_chunks.py [--only tvsz ...]
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

from .curriculum import extract_subjects, subject_text
from .html_pages import parse_html
from .pdf_lines import extract
from .schema import Chunk, slug
from .structure import Unit, parse

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

MAX_CHARS = 1800  # e fölött daraboljuk az egységet
TARGET_CHARS = 1200
MIN_CHARS = 20


# ───────────────────────────── darabolás ─────────────────────────────
def split_long(text: str) -> list[str]:
    """Hosszú szöveg darabolása felsorolási pontok / mondatok határán, kb. TARGET_CHARS méretű részekre."""
    if len(text) <= MAX_CHARS:
        return [text]
    pieces = re.split(r"(?<=[;:.])\s+(?=(?:[a-z]{1,4}\)|\d{1,3}[a-z]?\.)\s)", text)
    if max(len(p) for p in pieces) > MAX_CHARS:
        pieces = [s for p in pieces for s in re.split(r"(?<=[.;])\s+(?=[A-ZÁÉÍÓÖŐÚÜŰ(])", p)]
    if max(len(p) for p in pieces) > MAX_CHARS:  # felsorolásjelek ("•", "-") mentén
        pieces = [s for p in pieces for s in re.split(r"\s+(?=[•▪◦–-]\s)", p)]
    if max(len(p) for p in pieces) > MAX_CHARS:  # végső tartalék: szóhatáron vágás
        hard = []
        for p in pieces:
            while len(p) > TARGET_CHARS:
                cut = p.rfind(" ", 0, TARGET_CHARS)
                cut = cut if cut > 0 else TARGET_CHARS
                hard.append(p[:cut])
                p = p[cut:].lstrip()
            hard.append(p)
        pieces = hard
    parts, buf = [], ""
    for p in pieces:
        if buf and len(buf) + len(p) + 1 > TARGET_CHARS:
            parts.append(buf)
            buf = p
        else:
            buf = f"{buf} {p}".strip()
    if buf:
        parts.append(buf)
    return parts


def ocr_quality(text: str) -> float:
    """A „rendes” (betűkből álló, magánhangzót tartalmazó) szavak aránya; OCR-zaj szűrésére."""
    toks = text.split()
    if not toks:
        return 0.0
    good = sum(
        1
        for t in toks
        if re.fullmatch(r"[(„]?[A-Za-zÁÉÍÓÖŐÚÜŰáéíóöőúüű\-]{2,}[.,;:)”]?", t) and re.search(r"[aeiouáéíóöőúüű]", t, re.I)
    )
    return good / len(toks)


# ───────────────────────────── hivatkozások ─────────────────────────────
def unit_id(doc_id: str, u: Unit, idx: int) -> str:
    parts = []
    if u.annex:
        parts.append(f"m{u.annex}")
    if u.paragraph:
        parts.append(u.paragraph)
    elif u.embedded_tvsz:
        parts.append(f"tvsz{u.embedded_tvsz}")
    if u.item:
        parts.append(f"p{u.item}")
    if u.subsection:
        parts.append(u.subsection)
    if not parts:
        parts.append(f"s{idx}")
    return f"{doc_id}:" + ":".join(parts)


def unit_citation(short: str, u: Unit) -> str:
    c = [short]
    if u.annex:
        c.append(f"{u.annex}. sz. melléklet")
    if u.paragraph:
        c.append(f"{u.paragraph}. §")
    elif u.embedded_tvsz:
        c.append(f"[TVSZ {u.embedded_tvsz}. §-hoz]")
    if u.item:
        c.append(f"{u.item}. pont")
    if u.subsection:
        c.append(f"({u.subsection})")
    # paragrafus nélküli számozott pontnál a pontszám önmagában nem egyértelmű (több szakaszban is lehet „5. pont”)
    ambiguous_item = bool(u.item) and not u.paragraph and not u.embedded_tvsz
    if len(c) == 1 or (len(c) == 2 and u.annex) or ambiguous_item:
        if u.section:
            c.append(f"– {u.section}")
        elif u.chapter:
            c.append(f"– {u.chapter}")
    return " ".join(c)


EXTERNAL_LAW_RE = re.compile(r"(Nftv|N[fí]tv|törvény|rendelet|Vhr|Ákr|Jtr|Korm\.|EMMI|Ptk)\W*$", re.I)
REF_RE = re.compile(r"(\d{1,3}(?:/[A-Z])?)\.\s*§(?:-[a-záéíóöőúüű]+)?(?:\s*\((\d{1,2}[a-z]?)\)\s*bekezdés)?")
LOCAL_SUB_RE = re.compile(r"(?<![§\d]\s)\((\d{1,2}[a-z]?)\)\s*bekezdés")


def find_refs(text: str, doc_id: str, has_paragraphs: bool, cur_para: str) -> list[tuple[str, str, str]]:
    """(cél_doc, §, bekezdés) hármasok a szövegből."""
    refs = []
    for m in REF_RE.finditer(text):
        before = text[max(0, m.start() - 30): m.start()]
        if EXTERNAL_LAW_RE.search(before):
            continue
        if "TVSZ" in before or "TVSz" in before or "Tanulmányi és Vizsgaszabályzat" in before:
            target = "tvsz"
        elif has_paragraphs:
            target = doc_id
        else:
            continue
        refs.append((target, m.group(1), m.group(2) or ""))
    if has_paragraphs and cur_para:
        for m in LOCAL_SUB_RE.finditer(text):
            before = text[max(0, m.start() - 12): m.start()]
            if "§" in before:
                continue
            refs.append((doc_id, cur_para, m.group(1)))
    return refs


# ───────────────────────────── dokumentumtípusok ─────────────────────────────
def _base(doc: dict) -> dict:
    return dict(
        doc_id=doc["id"],
        doc_title=doc["title"],
        doc_short=doc.get("short", doc["title"]),
        scope=doc["scope"],
        source_url=doc["url"],
    )


def chunks_from_units(doc: dict, units: list[Unit], footnotes: dict[str, str], has_paragraphs: bool, ocr: bool, kind="rule"):
    out: list[Chunk] = []
    seen: Counter = Counter()
    short = doc.get("short", doc["title"])
    for idx, u in enumerate(units):
        text = u.text()
        if len(text) < MIN_CHARS:
            continue
        cid = unit_id(doc["id"], u, idx)
        seen[cid] += 1
        if seen[cid] > 1:
            cid = f"{cid}~{seen[cid]}"
        fns = [footnotes[r] for r in dict.fromkeys(u.refs) if r in footnotes]
        refs = find_refs(text, doc["id"], has_paragraphs, u.paragraph)
        parts = split_long(text)
        for pi, ptxt in enumerate(parts, 1):
            if ocr and ocr_quality(ptxt) < 0.55:
                continue  # OCR-zaj (űrlapok, táblázatok)
            part = f"{pi}/{len(parts)}" if len(parts) > 1 else ""
            out.append(
                Chunk(
                    **_base(doc),
                    chunk_id=f"{cid}#{pi}" if part else cid,
                    kind=kind,
                    citation=unit_citation(short, u) + (f" [{part}. rész]" if part else ""),
                    text=ptxt,
                    page_start=u.page_start or None,
                    page_end=u.page_end or None,
                    annex=u.annex,
                    chapter=u.chapter,
                    section=u.section,
                    paragraph=f"{u.paragraph}. §" if u.paragraph else "",
                    paragraph_title=u.paragraph_title,
                    subsection=f"({u.subsection})" if u.subsection else "",
                    item=f"{u.item}." if u.item else "",
                    part=part,
                    footnotes=fns,
                    ocr=ocr,
                    extra={"_refs": refs, "embedded_tvsz": u.embedded_tvsz} if u.embedded_tvsz else {"_refs": refs},
                )
            )
    return out


def process_pdf(doc: dict) -> list[Chunk]:
    ocr = bool(doc.get("ocr"))
    path = RAW / (f"{doc['id']}.ocr.pdf" if ocr else f"{doc['id']}.pdf")
    is_program = doc["id"].startswith("kp_")
    content = extract(str(path), ocr=ocr, skip_tables=is_program)
    has_paragraphs = sum(1 for ln in content.lines if re.match(r"^\d{1,3}(?:/[A-Z])?\s*\.\s*§", ln.text)) >= 2
    units = parse(content.lines, has_paragraphs=has_paragraphs)
    chunks = chunks_from_units(doc, units, content.footnotes, has_paragraphs, ocr)
    if is_program:
        program = doc["title"].replace(" képzési program (2026)", "")
        seen: Counter = Counter()
        for s in extract_subjects(str(path)):
            key = s.code or slug(s.name)
            seen[key] += 1
            cid = f"{doc['id']}:targy:{key}" + (f"~{seen[key]}" if seen[key] > 1 else "")
            chunks.append(
                Chunk(
                    **_base(doc),
                    chunk_id=cid,
                    kind="curriculum",
                    citation=f"{doc.get('short', doc['title'])} – mintatanterv: {s.code + ' ' if s.code else ''}{s.name}",
                    text=subject_text(s, program),
                    page_start=s.page,
                    page_end=s.page,
                    section="Mintatanterv" + (f" › {s.group}" if s.group else ""),
                    extra={
                        "code": s.code, "name": s.name, "semester": s.semester, "credits": s.credits,
                        "hours": f"{s.lecture}/{s.practice}/{s.lab}", "requirement": s.requirement,
                        "type": s.type, "department": s.department, "_refs": [],
                    },
                )
            )
    return chunks


def process_html(doc: dict) -> list[Chunk]:
    html = (RAW / f"{doc['id']}.html").read_text(encoding="utf-8")
    title, sections = parse_html(html)
    # a rövid, azonos szülőcím alatti szakaszokat összevonjuk, a hosszúakat daraboljuk
    groups: list[tuple[list[str], list[str]]] = []
    for s in sections:
        txt = s.text()
        if groups and len(" ".join(groups[-1][1])) + len(txt) < TARGET_CHARS and groups[-1][0][:-1] == s.path[:-1]:
            groups[-1][1].append((s.path[-1] + ": " if s.path and len(s.path) > 1 else "") + txt)
            continue
        groups.append((s.path, [txt]))
    out: list[Chunk] = []
    short = doc.get("short", doc["title"])
    for gi, (path, texts) in enumerate(groups, 1):
        text = "\n".join(texts)
        heading = " › ".join(p for p in path if p)
        parts = split_long(text)
        for pi, ptxt in enumerate(parts, 1):
            part = f"{pi}/{len(parts)}" if len(parts) > 1 else ""
            out.append(
                Chunk(
                    **_base(doc),
                    chunk_id=f"{doc['id']}:s{gi}" + (f"#{pi}" if part else ""),
                    kind="page",
                    citation=f"{short} – {path[-1] if path else title}" + (f" [{part}. rész]" if part else ""),
                    text=ptxt,
                    section=heading,
                    part=part,
                    extra={"_refs": find_refs(ptxt, doc["id"], False, "")},
                )
            )
    return out


def process(doc: dict) -> list[Chunk]:
    return process_pdf(doc) if doc["format"] == "pdf" else process_html(doc)


# ───────────────────────────── kereszthivatkozások feloldása ─────────────────────────────
def resolve_crossrefs(chunks: list[Chunk]) -> None:
    ids = {c.chunk_id for c in chunks}
    by_para: dict[str, list[str]] = defaultdict(list)
    for c in chunks:
        if c.paragraph and not c.annex:
            by_para[f"{c.doc_id}:{c.paragraph.rstrip('. §')}"].append(c.chunk_id)
    for c in chunks:
        resolved: list[str] = []
        for target, para, sub in c.extra.pop("_refs", []):
            base = f"{target}:{para}"
            cand = [f"{base}:{sub}", f"{base}:{sub}#1"] if sub else [base, f"{base}#1"]
            hit = next((x for x in cand if x in ids), None)
            if hit is None and base in by_para:
                hit = by_para[base][0] if not sub else None
            if hit and hit != c.chunk_id and hit not in resolved:
                resolved.append(hit)
        c.crossrefs = resolved[:8]


def build(only: list[str] | None = None, workers: int = 4) -> list[Chunk]:
    docs = yaml.safe_load((ROOT / "data" / "sources.yaml").read_text(encoding="utf-8"))["documents"]
    docs = [d for d in docs if (RAW / f"{d['id']}.{d['format']}").exists()]
    if only:
        docs = [d for d in docs if d["id"] in set(only)]
    if workers <= 1:
        results = []
        for d in docs:
            print(f"  feldolgozás: {d['id']}", flush=True)
            results.append(process(d))
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(process, docs))
    chunks = [c for r in results for c in r]
    resolve_crossrefs(chunks)
    dup = [k for k, v in Counter(c.chunk_id for c in chunks).items() if v > 1]
    assert not dup, f"duplikált chunk_id: {dup[:5]}"
    return chunks


def write(chunks: list[Chunk]) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    per_doc: dict = defaultdict(lambda: {"chunks": 0, "chars": 0, "kinds": Counter()})
    for c in chunks:
        d = per_doc[c.doc_id]
        d["chunks"] += 1
        d["chars"] += len(c.text)
        d["kinds"][c.kind] += 1
    stats = {
        "total_chunks": len(chunks),
        "total_chars": sum(len(c.text) for c in chunks),
        "with_crossrefs": sum(1 for c in chunks if c.crossrefs),
        "documents": {k: {**v, "kinds": dict(v["kinds"])} for k, v in sorted(per_doc.items())},
    }
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats
