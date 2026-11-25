"""Válaszgenerálás forrásjelölésekkel + generálás utáni hivatkozás-ellenőrzés (TERV 1.6).

A modell [S1]..[Sk] jelöléseket és szó szerinti idézeteket ad; ellenőrizzük, hogy az idézet tényleg szerepel-e a
hivatkozott chunkban (fuzzy egyezés: OCR-es szövegnél és apró eltéréseknél is működjön). A jelöléseket végül a
pontos hivatkozásra cseréljük (pl. [TVSZ 54. § (4)]).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz

from ..llm.client import DEFAULT_GENERATOR, LLMError, chat, parse_json

PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
QUOTE_MIN_SCORE = 85  # partial_ratio küszöb (0–100)


def load_prompt(name: str = "answer_v1") -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        where = " › ".join(x for x in (c.get("chapter"), c.get("section"), c.get("paragraph_title")) if x)
        ocr = " (OCR-ből származó szöveg)" if c.get("ocr") else ""
        blocks.append(f"[S{i}] {c['citation']}{ocr}\n({where})\n{c['text']}")
    return "\n\n".join(blocks)


@dataclass
class Citation:
    source: str  # "S2"
    chunk_id: str
    citation: str  # "TVSZ 54. § (4)"
    quote: str
    quote_score: float  # 0–100, a forrásban való előfordulás mértéke
    verified: bool


@dataclass
class Answer:
    question: str
    answerable: bool
    answer_raw: str  # [S1] jelölésekkel
    answer: str  # pontos hivatkozásokkal
    citations: list[Citation] = field(default_factory=list)
    model: str = ""
    cached: bool = False
    error: str = ""


def display_citation(c: dict) -> str:
    """A felhasználónak mutatott hivatkozás a darabolási jelölés („[2/3. rész]”) nélkül."""
    return re.sub(r"\s*\[\d+/\d+\. rész\]$", "", c["citation"])


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("„", '"').replace("”", '"').replace("–", "-")).strip().lower()


def verify_quote(quote: str, text: str) -> float:
    if not quote.strip():
        return 0.0
    q, t = _norm(quote), _norm(text)
    if q in t:
        return 100.0
    return float(fuzz.partial_ratio(q, t))


def generate_answer(question: str, chunks: list[dict], models=DEFAULT_GENERATOR, prompt: str = "answer_v1") -> Answer:
    messages = [
        {"role": "system", "content": load_prompt(prompt)},
        {"role": "user", "content": f"FORRÁSOK:\n\n{format_context(chunks)}\n\nKÉRDÉS: {question}"},
    ]
    try:
        resp = chat(messages, models=models, temperature=0.0, json_mode=True)
        data = parse_json(resp.text)
    except (LLMError, ValueError) as e:
        return Answer(question, False, "", "", error=str(e))

    by_src = {f"S{i}": c for i, c in enumerate(chunks, 1)}
    cits: list[Citation] = []
    for item in data.get("citations", []) or []:
        src = str(item.get("source", "")).strip().strip("[]")
        c = by_src.get(src)
        if not c:
            continue
        score = verify_quote(str(item.get("quote", "")), c["text"])
        cits.append(Citation(src, c["chunk_id"], display_citation(c), str(item.get("quote", "")), score, score >= QUOTE_MIN_SCORE))

    raw = str(data.get("answer", ""))

    def repl(m: re.Match) -> str:
        c = by_src.get(m.group(1))
        return f"[{display_citation(c)}]" if c else ""

    answer = re.sub(r"\[(S\d+)\]", repl, raw)
    # a szövegben jelölt, de az idézetlistából hiányzó források is hivatkozásnak számítanak (idézet nélkül)
    for s in dict.fromkeys(re.findall(r"\[(S\d+)\]", raw)):
        if s in by_src and not any(x.source == s for x in cits):
            c = by_src[s]
            cits.append(Citation(s, c["chunk_id"], display_citation(c), "", 0.0, False))
    return Answer(question, bool(data.get("answerable", bool(cits))), raw, answer, cits, resp.model, resp.cached)
