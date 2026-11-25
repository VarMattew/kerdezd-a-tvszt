"""Kiértékelő kérdésjelöltek generálása rétegzett chunkmintából (TERV 3.1, 1–2. lépés).

A jelölteket egy HARMADIK modell készíti (nem a válaszgeneráló és nem a bíró), hogy csökkenjen az önértékelési torzítás.
Kimenet: eval/candidates.jsonl – ezt kézzel átnézzük, a végleges halmaz az eval/questions.jsonl.

Használat:  uv run python eval/build_questions.py [--seed 7] [--model groq:openai/gpt-oss-120b]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

from vikrag.index.common import load_chunks
from vikrag.llm.client import LLMError, chat, parse_json

ROOT = Path(__file__).resolve().parents[1]
PROMPT = (ROOT / "prompts" / "question_gen_v1.md").read_text(encoding="utf-8")

STYLES = {
    "fact": "- Stílus: semleges, rendes magyar mondat.",
    "numeric": "- A kérdés egy SZÁMRA, HATÁRIDŐRE, DÁTUMRA, ÖSSZEGRE vagy MENNYISÉGRE kérdezzen rá, amely a forrásban szerepel.",
    "multi": "- KÉT forrást kapsz. A kérdés megválaszolásához MINDKETTŐ kell (pl. az egyik hivatkozik a másikra, vagy kiegészítik egymást). A válasz mindkettőre támaszkodjon.",
    "curriculum": "- A forrás egy mintatanterv-sor. Kérdezz a tárgy kreditjére, ajánlott félévére, követelménytípusára (vizsga / félévközi jegy), óraszámára vagy előtanulmányi feltételére – a hallgató a tárgy NEVÉVEL (vagy kódjával) és a szakjával hivatkozzon rá.",
    "slang": "- Stílus: laza, hallgatói nyelv (pl. „zh”, „pótzh”, „IV-zni”, „bukta”, „aláírás”, „Neptun”, „passzivál”, „kredit”), tegeződve, mintha egy Facebook-csoportba írná. A kérdés legyen akár pontatlanul megfogalmazott, de a forrásból megválaszolható.",
    "english": "- A kérdést és a választ ANGOLUL írd (egy külföldi/angol nyelvű hallgató kérdezi), a magyar szakkifejezéseket fordítsd le.",
}

# rétegzés: (típus, chunkcsoport, darabszám) – a célszám kb. 30%-kal túl van húzva a kézi szűrés miatt
PLAN = [
    ("fact", "tvsz", 14), ("fact", "tjsz", 5), ("fact", "kari", 8), ("fact", "page", 4),
    ("numeric", "tvsz", 6), ("numeric", "tjsz", 3), ("numeric", "kari", 3), ("numeric", "tanev", 3),
    ("multi", "pair", 15),
    ("curriculum", "curr", 15),
    ("slang", "tvsz", 8), ("slang", "kari", 4),
    ("english", "tvsz", 4), ("english", "kari", 2),
]
NUMERIC_RE = re.compile(r"\d+\s*(kredit|nap|munkanap|hét|Ft|forint|%|félév|alkalom|óra)|\d{4}\.\s*\w+\s+\d")
STUDENT_DOCS_EXCLUDE = {"vik_szmsz", "kepzesi_kodex"}  # szervezeti, nem hallgatói kérdések


def group(c: dict) -> str:
    if c["doc_id"] == "tvsz":
        return "tvsz"
    if c["doc_id"] == "tjsz":
        return "tjsz"
    if c["doc_id"] in ("tanev_2026_27", "vik_tanev_kieg_1", "vik_tanev_kieg_2"):
        return "tanev"
    if c["kind"] == "curriculum":
        return "curr"
    if c["kind"] == "page":
        return "page"
    if c["doc_id"].startswith("kp_") or c["doc_id"] in STUDENT_DOCS_EXCLUDE:
        return "other"
    return "kari"


def eligible(c: dict) -> bool:
    if c["kind"] == "curriculum":
        return bool(c["extra"].get("name")) and len(c["extra"]["name"]) > 3
    return 150 <= len(c["text"]) <= 1500 and "Hatályon kívül" not in c["text"][:80]


def sample(chunks: list[dict], rng: random.Random) -> list[tuple[str, list[dict]]]:
    pools: dict[str, list[dict]] = {}
    for c in chunks:
        if eligible(c):
            pools.setdefault(group(c), []).append(c)
    by_id = {c["chunk_id"]: c for c in chunks}
    used: set[str] = set()
    out = []
    for typ, grp, n in PLAN:
        if grp == "pair":
            cands = [
                (c, by_id[x])
                for c in pools["tvsz"] + pools["kari"] + pools["tjsz"]
                for x in c["crossrefs"][:2]
                if x in by_id and eligible(by_id[x]) and x != c["chunk_id"]
            ]
            rng.shuffle(cands)
            for a, b in cands:
                if len([o for o in out if o[0] == "multi"]) >= n:
                    break
                if a["chunk_id"] in used or b["chunk_id"] in used:
                    continue
                used |= {a["chunk_id"], b["chunk_id"]}
                out.append(("multi", [a, b]))
            continue
        pool = [c for c in pools.get(grp, []) if c["chunk_id"] not in used]
        if typ == "numeric":
            pool = [c for c in pool if NUMERIC_RE.search(c["text"])]
        for c in rng.sample(pool, min(n, len(pool))):
            used.add(c["chunk_id"])
            out.append((typ, [c]))
    return out


def source_block(chunks: list[dict]) -> str:
    return "\n\n".join(f"FORRÁS {i}: {c['citation']}\n{c['text']}" for i, c in enumerate(chunks, 1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default="groq:openai/gpt-oss-120b")
    ap.add_argument("--delay", type=float, default=7.0, help="szünet hívások között (Groq: 8000 token/perc)")
    ap.add_argument("--out", type=Path, default=ROOT / "eval" / "candidates.jsonl")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    items = sample(load_chunks(), rng)
    print(f"{len(items)} jelölt generálása ({args.model})")
    with args.out.open("w", encoding="utf-8") as f:
        for n, (typ, srcs) in enumerate(items, 1):
            messages = [
                {"role": "system", "content": PROMPT.format(style=STYLES[typ])},
                {"role": "user", "content": source_block(srcs)},
            ]
            try:
                resp = chat(messages, models=[args.model, "gemini:gemini-3.5-flash"], temperature=0.7, json_mode=True)
                d = parse_json(resp.text)
            except (LLMError, ValueError) as e:
                print(f"[{n}] HIBA: {e}")
                continue
            rec = {
                "cand_id": f"c{n:03d}",
                "type": typ,
                "lang": "en" if typ == "english" else "hu",
                "question": d.get("question", ""),
                "gold_answer": d.get("answer", ""),
                "gold_chunk_ids": [c["chunk_id"] for c in srcs],
                "gold_citations": [c["citation"] for c in srcs],
                "usable": bool(d.get("usable", True)),
                "gen_reason": d.get("reason", ""),
                "gen_model": resp.model,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{n}/{len(items)}] {typ:10s} {'✓' if rec['usable'] else '✗'} {rec['question'][:90]}")
            if not resp.cached:
                time.sleep(args.delay)
