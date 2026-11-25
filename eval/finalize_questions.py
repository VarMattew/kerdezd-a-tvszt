"""A végleges kiértékelő halmaz összeállítása (TERV 3.1, 3–6. lépés).

Bemenetek:
  eval/candidates.jsonl  – LLM-generált jelöltek (build_questions.py)
  eval/review.jsonl      – kézi átnézés döntései: {"cand_id", "decision": accept|edit|reject, ["question"], ["gold_answer"],
                           ["gold_chunk_ids"] (felülírja), ["add_gold"] (bővíti), ["type"], "note"}
  eval/handwritten.jsonl – teljesen kézzel írt kérdések (valósághű + megválaszolhatatlan)
  eval/gold_additions.jsonl – jóváhagyott gold-bővítések: {"question", "add_gold": [...], "note"}
Kimenet: eval/questions.jsonl (q001…), dev/test felosztás (30/70, típus szerint rétegezve, rögzített seed).

A jelöltek a generáláskori chunklistára hivatkoznak (--old-chunks, alapértelmezés: a git-ben a generáláskor érvényes
változat). Az azonosítókat szöveg alapján átképezzük a jelenlegi chunklistára (a parser időközben javult).
Minden gold-hoz eltároljuk a szöveg elejét is (gold_texts), így egy későbbi parser-változás után is visszakereshető.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.open(encoding="utf-8") if x.strip()] if p.exists() else []


def old_chunks_from_git(rev: str) -> dict[str, dict]:
    raw = subprocess.run(["git", "show", f"{rev}:data/processed/chunks.jsonl"], cwd=ROOT, capture_output=True, check=True).stdout
    return {c["chunk_id"]: c for c in (json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip())}


def remap(old_id: str, old: dict[str, dict], new: dict[str, dict], by_doc: dict[str, list[dict]]) -> tuple[str | None, float]:
    o = old.get(old_id)
    if o is None:
        return (old_id, 100.0) if old_id in new else (None, 0.0)
    n = new.get(old_id)
    if n and n["text"] == o["text"]:
        return old_id, 100.0
    best, score = None, 0.0
    for c in by_doc[o["doc_id"]]:
        s = fuzz.ratio(o["text"], c["text"])
        if s > score:
            best, score = c["chunk_id"], s
    return (best, score) if score >= 85 else (None, score)


def equivalence_groups(texts: list[str], threshold: float = 90) -> list[list[int]]:
    """A (közel) szó szerint azonos gold szövegek indexcsoportjai (pl. TVSZ § és a ZV-szabályzatbeli másolata)."""
    groups: list[list[int]] = []
    for i, t in enumerate(texts):
        for grp in groups:
            if fuzz.ratio(texts[grp[0]], t) >= threshold:
                grp.append(i)
                break
        else:
            groups.append([i])
    return groups


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-chunks-rev", default="1dbfc22", help="git-revízió, amelynek chunklistájából a jelöltek készültek")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--dev-ratio", type=float, default=0.3)
    args = ap.parse_args()

    new = {c["chunk_id"]: c for c in load_jsonl(ROOT / "data" / "processed" / "chunks.jsonl")}
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for c in new.values():
        by_doc[c["doc_id"]].append(c)
    old = old_chunks_from_git(args.old_chunks_rev)
    reviews = {r["cand_id"]: r for r in load_jsonl(EVAL / "review.jsonl")}

    out, problems = [], []
    for cand in load_jsonl(EVAL / "candidates.jsonl"):
        r = reviews.get(cand["cand_id"])
        if not r or r["decision"] == "reject":
            continue
        gold = []
        for g in cand["gold_chunk_ids"]:
            nid, s = remap(g, old, new, by_doc)
            if nid is None:
                problems.append(f"{cand['cand_id']}: {g} nem képezhető át (legjobb egyezés {s:.0f})")
            else:
                gold.append(nid)
        if "gold_chunk_ids" in r:
            gold = r["gold_chunk_ids"]
        gold += [g for g in r.get("add_gold", []) if g not in gold]
        q = {
            "type": r.get("type", cand["type"]),
            "lang": r.get("lang", cand["lang"]),
            "origin": "llm+review" if r["decision"] == "accept" else "llm+edited",
            "question": r.get("question", cand["question"]),
            "gold_answer": r.get("gold_answer", cand["gold_answer"]),
            "gold_chunk_ids": gold,
            "answerable": True,
            "cand_id": cand["cand_id"],
            "review_note": r.get("note", ""),
        }
        out.append(q)
    out += load_jsonl(EVAL / "handwritten.jsonl")

    # kézzel jóváhagyott gold-bővítések (expand_gold.py javaslataiból), a kérdés szövege szerint
    additions = {a["question"]: a["add_gold"] for a in load_jsonl(EVAL / "gold_additions.jsonl")}
    for q in out:
        for g in additions.get(q["question"], []):
            if g not in q["gold_chunk_ids"]:
                q["gold_chunk_ids"].append(g)

    for q in out:
        missing = [g for g in q["gold_chunk_ids"] if g not in new]
        if missing:
            problems.append(f"{q['question'][:50]}: ismeretlen gold {missing}")
        q["gold_texts"] = [new[g]["text"][:150] for g in q["gold_chunk_ids"] if g in new]
        q["gold_citations"] = [new[g]["citation"] for g in q["gold_chunk_ids"] if g in new]
        q["gold_groups"] = equivalence_groups([new[g]["text"] if g in new else g for g in q["gold_chunk_ids"]])

    # dev/test felosztás típusonként rétegezve
    rng = random.Random(args.seed)
    by_type: dict[str, list[dict]] = defaultdict(list)
    for q in out:
        by_type[q["type"]].append(q)
    for qs in by_type.values():
        rng.shuffle(qs)
        n_dev = round(len(qs) * args.dev_ratio)
        for i, q in enumerate(qs):
            q["split"] = "dev" if i < n_dev else "test"
    out.sort(key=lambda q: (q["type"], q["question"]))
    for i, q in enumerate(out, 1):
        q["id"] = f"q{i:03d}"
    with (EVAL / "questions.jsonl").open("w", encoding="utf-8") as f:
        for q in out:
            f.write(json.dumps({"id": q.pop("id"), **q}, ensure_ascii=False) + "\n")

    counts = defaultdict(lambda: defaultdict(int))
    for q in out:
        counts[q["type"]][q["split"]] += 1
    print(f"{len(out)} kérdés -> eval/questions.jsonl")
    for t, c in sorted(counts.items()):
        print(f"  {t:13s} dev {c['dev']:3d}  test {c['test']:3d}")
    for p in problems:
        print("  ⚠", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
