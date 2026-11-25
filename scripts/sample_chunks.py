"""Rétegzett véletlen minta a chunkokból kézi ellenőrzéshez (F2 elfogadási kritérium: ≥95% helyes azonosító).

Használat:  uv run python scripts/sample_chunks.py --n 30 --seed 42 > docs/chunk_audit.md
A kimenet egy Markdown-táblázat-sor lista; a „Helyes?” oszlopot kézzel kell kitölteni az eredeti PDF alapján.
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    chunks = [json.loads(x) for x in (ROOT / "data/processed/chunks.jsonl").open(encoding="utf-8")]
    rng = random.Random(args.seed)
    # rétegzés: dokumentumcsoport (TVSZ / TJSZ / kari szabályzat / képzési program / HTML) szerint
    strata = defaultdict(list)
    for c in chunks:
        key = c["doc_id"] if c["doc_id"] in ("tvsz", "tjsz") else ("kp" if c["doc_id"].startswith("kp_") else c["kind"])
        strata[key].append(c)
    quota = {"tvsz": 10, "tjsz": 5, "kp": 5, "rule": 6, "page": 4}
    sample = []
    for k, q in quota.items():
        sample += rng.sample(strata.get(k, []), min(q, len(strata.get(k, []))))
    print("# Chunk-audit (F2)\n")
    print(f"Minta: {len(sample)} chunk, seed={args.seed}. Ellenőrzés: a hivatkozás (§/bekezdés/pont, oldal) "
          "és a szöveg egyezik-e az eredeti dokumentummal.\n")
    for i, c in enumerate(sample, 1):
        print(f"## {i}. `{c['chunk_id']}` — {c['citation']}")
        print(f"- dokumentum: {c['doc_title']}, oldal: {c['page_start']}–{c['page_end']}")
        print(f"- fejezet / cím: {c['chapter'] or '–'} / {c['section'] or '–'} / {c['paragraph_title'] or '–'}")
        print(f"- szöveg: {c['text'][:400]}{'…' if len(c['text']) > 400 else ''}")
        print("- **Ellenőrzés:** ⏳\n")
