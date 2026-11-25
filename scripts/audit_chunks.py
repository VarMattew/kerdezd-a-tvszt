"""Az audit-minta (scripts/sample_chunks.py, azonos seed) automatikus összevetése a forrásdokumentumokkal.

Minden mintachunkra: a szöveg eleje megtalálható-e a megadott oldalon (OK/MISS), a vége megvan-e a dokumentumban,
és a „(n)” bekezdésjel közvetlenül a szöveg előtt áll-e. A MISS eseteket kézzel kell megnézni (lásd docs/chunk_audit.md).
Használat:  uv run python scripts/audit_chunks.py
"""
import json
import random
import re
from collections import defaultdict
import pymupdf
from bs4 import BeautifulSoup
cs = [json.loads(l) for l in open("data/processed/chunks.jsonl", encoding="utf-8")]
rng = random.Random(42)
strata = defaultdict(list)
for c in cs:
    k = c["doc_id"] if c["doc_id"] in ("tvsz", "tjsz") else ("kp" if c["doc_id"].startswith("kp_") else c["kind"])
    strata[k].append(c)
sample = []
for k, q in {"tvsz": 10, "tjsz": 5, "kp": 5, "rule": 6, "page": 4}.items():
    sample += rng.sample(strata[k], min(q, len(strata[k])))
norm = lambda s: re.sub(r"[^a-záéíóöőúüű0-9]", "", s.lower())
for i, c in enumerate(sample, 1):
    src = f"data/raw/{c['doc_id']}{'.ocr' if c['ocr'] else ''}.{'pdf' if c['page_start'] else 'html'}"
    if c["page_start"]:
        d = pymupdf.open(src)
        pages = range(c["page_start"] - 1, (c["page_end"] or c["page_start"]))
        raw = "".join(d[p].get_text() for p in pages)
        alltxt = "".join(p.get_text() for p in d)
    else:
        raw = alltxt = BeautifulSoup(open(src, encoding="utf-8").read(), "html.parser").get_text(" ")
    nt, nraw = norm(c["text"]), norm(raw)
    probe = nt[:50]; probe_end = nt[-40:]
    on_page = probe in nraw
    end_ok = probe_end in nraw or probe_end in norm(alltxt)
    # a bekezdésjel közvetlenül a szöveg előtt?
    sub_ok = None
    if c["subsection"] and not c["part"].startswith(("2", "3", "4")):
        k = nraw.find(probe)
        sub_ok = k >= 0 and norm(c["subsection"]) in nraw[max(0, k - 12):k]
    print(f"{i:2d} {'OK ' if on_page else 'MISS'} end={'OK' if end_ok else 'MISS'} sub={sub_ok} | {c['chunk_id']} | {c['citation']} | p{c['page_start']}")
