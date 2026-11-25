"""Közös segédfüggvények az indexekhez: chunkok betöltése, a beágyazandó/indexelendő szöveg előállítása."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
INDEX_DIR = ROOT / "data" / "index"


@lru_cache(maxsize=2)
def load_chunks(path: str | None = None) -> list[dict]:
    p = Path(path) if path else CHUNKS_PATH
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def context_header(c: dict) -> str:
    """A TERV 1.1 szerinti kontextusfejléc: dokumentum › fejezet › cím › §-cím › hivatkozás."""
    parts = [c["doc_short"]]
    for key in ("chapter", "section", "paragraph_title"):
        v = c.get(key) or ""
        if v and v not in parts:
            parts.append(v)
    parts.append(c["citation"])
    return " › ".join(parts)


def index_text(c: dict, with_header: bool = True) -> str:
    """Az indexelt szöveg: (opcionálisan) kontextusfejléc + a chunk szövege. A fejléc ki/be kapcsolása az E3 kísérlet."""
    return f"{context_header(c)}\n{c['text']}" if with_header else c["text"]
