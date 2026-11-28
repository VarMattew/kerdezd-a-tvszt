"""Lekérdezés-feldolgozás (TERV 1.3, órai dia: Query manipulation).

- szótáras bővítés: a hallgatói szleng / rövidítés mellé a szabályzati kifejezést fűzzük (data/glossary.yaml);
- LLM-átírás: a kérdést a szabályzatok hivatalos magyar szóhasználatára írjuk át (angol kérdésnél fordítás is).
A kereső mindkét változatot (és az eredetit) is lefuttathatja, a rangsorokat RRF egyesíti (multi-query fúzió).
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from ..llm.client import LLMError, chat, parse_json

ROOT = Path(__file__).resolve().parents[3]
GLOSSARY_PATH = ROOT / "data" / "glossary.yaml"
REWRITE_PROMPT = ROOT / "prompts" / "query_rewrite_v1.md"
DEFAULT_REWRITER = ["groq:openai/gpt-oss-20b", "groq:qwen/qwen3.8-27b"]
_LETTER = "a-záéíóöőúüű0-9"


@lru_cache(maxsize=1)
def load_glossary() -> list[tuple[re.Pattern, str]]:
    raw = yaml.safe_load(GLOSSARY_PATH.read_text(encoding="utf-8")) or {}
    return [(re.compile(rf"(?<![{_LETTER}]){k}"), str(v)) for k, v in raw.items()]


def glossary_terms(query: str) -> list[str]:
    q = query.lower()
    out: list[str] = []
    for pat, exp in load_glossary():
        if pat.search(q) and exp not in out:
            out.append(exp)
    return out


def expand_glossary(query: str) -> str:
    """Az eredeti kérdés + a felismert szlengkifejezések szabályzati megfelelői."""
    terms = glossary_terms(query)
    return f"{query} ({'; '.join(terms)})" if terms else query


def llm_rewrite(query: str, models: list[str] | None = None) -> str:
    """Hivatalos szóhasználatú magyar keresőkérdés; hiba esetén az eredeti kérdés (a keresés nem állhat le miatta)."""
    msg = [{"role": "system", "content": REWRITE_PROMPT.read_text(encoding="utf-8")}, {"role": "user", "content": query}]
    try:
        r = chat(msg, models=models or DEFAULT_REWRITER, temperature=0.0, json_mode=True)
        q = str(parse_json(r.text).get("query", "")).strip()
        return q or query
    except (LLMError, ValueError):
        return query


def query_variants(query: str, rewrite: str = "none", rewriter: list[str] | None = None) -> dict[str, str]:
    """rewrite: none | glossary | llm | both  ->  {"orig": ..., ["gloss": ...], ["llm": ...]}"""
    v = {"orig": query}
    if rewrite in ("glossary", "both"):
        g = expand_glossary(query)
        if g != query:
            v["gloss"] = g
    if rewrite in ("llm", "both"):
        r = llm_rewrite(query, rewriter)
        if r.strip().lower() != query.strip().lower():
            v["llm"] = r
    return v
