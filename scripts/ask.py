"""Parancssori kérdezés: uv run python scripts/ask.py "Hányszor vizsgázhatok egy tárgyból?" [--mode hybrid] [--k 5] [--no-llm]"""
import argparse
import sys

from vikrag.pipeline import RAG, RAGConfig

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--mode", default="hybrid", choices=["bm25", "dense", "hybrid"])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--no-llm", action="store_true", help="csak a keresés eredménye")
    args = ap.parse_args()

    rag = RAG(RAGConfig(mode=args.mode, top_k=args.k))
    res = rag.ask(args.question, generate=not args.no_llm)
    print("\n── Találatok ──")
    for i, h in enumerate(res.hits, 1):
        print(f"[S{i}] {h.chunk['citation']}  (rangok: {h.ranks}, pontszám: {h.score:.4f})")
        print(f"     {h.chunk['text'][:160]}…")
    if res.answer:
        a = res.answer
        print(f"\n── Válasz ({a.model}{', cache' if a.cached else ''}) ──")
        print(a.answer if not a.error else f"HIBA: {a.error}")
        for c in a.citations:
            mark = "✓" if c.verified else "✗"
            print(f"  {mark} [{c.citation}] „{c.quote}” (egyezés: {c.quote_score:.0f})")
    print(f"\nidő: {res.timings}")
