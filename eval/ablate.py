"""Retrieval-ablációk egyetlen folyamatban (F5/F6): a keresőindexek és modellek egyszer töltődnek be, a
konfigurációk (configs/*.yaml) sorban futnak; csak retrieval-metrikák, LLM-hívás csak a lekérdezés-átíráshoz
(gyorsítótárazva). Kimenet: results/<name>.json + markdown táblázat a konzolra.

    uv run python eval/ablate.py configs/f5_retrieval.yaml --split dev
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
from metrics import aggregate, retrieval_metrics
from run import RESULTS, load_questions

from vikrag.pipeline import RAG, RAGConfig
from vikrag.retrieve.hybrid import HybridRetriever

KEYS = ["hit@1", "hit@5", "hit@10", "recall@5", "mrr", "ndcg@10"]


def evaluate(rag: RAG, qs: list[dict]) -> tuple[dict, dict, list[dict]]:
    rows = []
    for q in qs:
        if not q["answerable"]:
            continue
        hits, queries = rag.ranked(q["question"], k=10)
        ids = [h.chunk["chunk_id"] for h in hits]
        rows.append({"id": q["id"], "type": q["type"], "retrieved": ids, "queries": queries,
                     **retrieval_metrics(ids, q["gold_chunk_ids"], groups=q["groups"])})
    by_type = {t: aggregate([r for r in rows if r["type"] == t], ["hit@5", "mrr"]) for t in sorted({r["type"] for r in rows})}
    return aggregate(rows, KEYS), by_type, rows


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--only", nargs="*", help="csak ezek a konfigurációnevek")
    args = ap.parse_args()
    spec = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    qs = load_questions(args.split)
    retriever = HybridRetriever.load()
    out = {"config_file": args.config, "split": args.split, "date": datetime.now().isoformat(timespec="seconds"), "runs": {}}
    types = sorted({q["type"] for q in qs if q["answerable"]})
    print(f"| konfiguráció | {' | '.join(KEYS)} | {' | '.join(t[:5] for t in types)} | s/kérdés |")
    print("|---" * (len(KEYS) + len(types) + 2) + "|")
    for name, overrides in spec["configs"].items():
        if args.only and name not in args.only:
            continue
        cfg = RAGConfig(**{**spec.get("base", {}), **(overrides or {})})
        rag = RAG(cfg, retriever=retriever)
        t = time.time()
        summ, by_type, rows = evaluate(rag, qs)
        dt = (time.time() - t) / max(len(rows), 1)
        out["runs"][name] = {"config": cfg.__dict__, "summary": summ, "by_type": by_type, "rows": rows}
        cells = " | ".join(f"{summ[k]:.3f}" for k in KEYS)
        tcells = " | ".join(f"{by_type.get(t, {}).get('hit@5', 0):.2f}" for t in types)
        print(f"| {name} | {cells} | {tcells} | {dt:.1f} |", flush=True)
    RESULTS.mkdir(exist_ok=True)
    stem = Path(args.config).stem
    (RESULTS / f"{stem}_{args.split}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Mentve: results/{stem}_{args.split}.json")
