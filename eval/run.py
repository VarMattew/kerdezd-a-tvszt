"""Kiértékelő futtató (TERV 3.6).

Példák:
    # csak retrieval, három módban, a dev halmazon (gyors, nincs LLM-hívás):
    uv run python eval/run.py --name e1_retrieval --modes bm25 dense hybrid --split dev
    # teljes RAG (generálás + LLM-bíró) a baseline konfigurációval:
    uv run python eval/run.py --name baseline --modes hybrid --answers --split test

Kimenet: results/<name>.json (kérdésenkénti részletek + összesítés) és egy sor a results/summary.csv-ben.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import yaml
from metrics import VERDICT_SCORE, aggregate, citation_metrics, retrieval_metrics
from vikrag.llm.client import DEFAULT_JUDGE, LLMError, chat, parse_json
from vikrag.pipeline import RAG, RAGConfig

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "eval" / "questions.jsonl"
RESULTS = ROOT / "results"
JUDGE_PROMPT = (ROOT / "prompts" / "judge_correctness_v1.md").read_text(encoding="utf-8")
R_KEYS = ["hit@1", "hit@3", "hit@5", "hit@10", "recall@5", "recall@10", "mrr", "ndcg@10"]


def load_questions(split: str) -> list[dict]:
    """Betölti a kérdéseket; ha egy gold azonosító időközben megváltozott (parser-javítás), a mentett szövegeleje alapján
    megkeresi az új azonosítót – így a gold-címkék nem romlanak el csendben."""
    from vikrag.index.common import load_chunks

    chunks = load_chunks()
    ids = {c["chunk_id"] for c in chunks}
    qs = [json.loads(line) for line in QUESTIONS.open(encoding="utf-8")]
    for q in qs:
        fixed = []
        for g, txt in zip(q["gold_chunk_ids"], q.get("gold_texts", [None] * len(q["gold_chunk_ids"]))):
            if g in ids or not txt:
                fixed.append(g)
                continue
            hit = next((c["chunk_id"] for c in chunks if c["text"].startswith(txt[:80])), None)
            if hit is None:
                print(f"  ⚠ {q['id']}: a gold chunk ({g}) nem található", file=sys.stderr)
            fixed.append(hit or g)
        q["gold_chunk_ids"] = fixed
        # ekvivalens gold-csoportok: indexlistákból azonosítólisták (az átképzés után is érvényes)
        q["groups"] = [[fixed[i] for i in grp] for grp in q.get("gold_groups", [])]
    return [q for q in qs if split == "all" or q["split"] == split]


def judge(q: dict, answer_text: str, models=DEFAULT_JUDGE) -> dict:
    ref = q["gold_answer"] if q["answerable"] else "A kérdés a szabályzatokból NEM megválaszolható."
    msg = [
        {"role": "system", "content": JUDGE_PROMPT},
        {"role": "user", "content": f"KÉRDÉS: {q['question']}\n\nREFERENCIAVÁLASZ: {ref}\n\nRENDSZER VÁLASZA: {answer_text}"},
    ]
    try:
        r = chat(msg, models=models, temperature=0.0, json_mode=True)
        d = parse_json(r.text)
        return {"verdict": d.get("verdict", "incorrect"), "reason": d.get("reason", ""), "judge_model": r.model, "cached": r.cached}
    except (LLMError, ValueError) as e:
        return {"verdict": None, "reason": f"bíró hiba: {e}", "judge_model": "", "cached": False}


def run_retrieval(rag: RAG, qs: list[dict], depth: int = 10) -> list[dict]:
    rows = []
    for q in qs:
        hits = rag.retrieve(q["question"], k=depth)
        ids = [h.chunk["chunk_id"] for h in hits]
        row = {"id": q["id"], "type": q["type"], "retrieved": ids, "ranks": [h.ranks for h in hits]}
        if q["answerable"]:
            row.update(retrieval_metrics(ids, q["gold_chunk_ids"], groups=q["groups"]))
            row.update({f"para_{k}": v for k, v in retrieval_metrics(ids, q["gold_chunk_ids"], level="para", groups=q["groups"]).items()})
        rows.append(row)
    return rows


def run_answers(rag: RAG, qs: list[dict], delay: float, judge_models=DEFAULT_JUDGE) -> list[dict]:
    rows = []
    for n, q in enumerate(qs, 1):
        res = rag.ask(q["question"])
        a = res.answer
        cited = [c.chunk_id for c in a.citations]
        row = {
            "id": q["id"], "type": q["type"], "answerable_gold": q["answerable"],
            "answer": a.answer, "answerable_pred": a.answerable, "model": a.model, "error": a.error,
            "citations": [asdict(c) for c in a.citations],
            "context": [h.chunk["chunk_id"] for h in res.hits],
            "queries": res.queries,
        }
        j = judge(q, a.answer if not a.error else f"[HIBA] {a.error}", models=judge_models)
        row.update({"verdict": j["verdict"], "judge_reason": j["reason"], "judge_model": j["judge_model"]})
        row["correctness"] = VERDICT_SCORE.get(j["verdict"]) if j["verdict"] else None
        if q["answerable"]:
            row["false_refusal"] = float(not a.answerable)
            if cited:
                row.update(citation_metrics(cited, q["gold_chunk_ids"], groups=q["groups"]))
                row.update({f"para_{k}": v for k, v in citation_metrics(cited, q["gold_chunk_ids"], level="para", groups=q["groups"]).items()})
            quotes = [c for c in a.citations if c.quote]
            row["quote_verified"] = sum(c.verified for c in quotes) / len(quotes) if quotes else None
            row["context_hit"] = float(any(x.split("#")[0] in {g.split("#")[0] for g in q["gold_chunk_ids"]} for x in row["context"]))
        else:
            row["abstain_correct"] = float(not a.answerable)
        rows.append(row)
        print(f"  [{n}/{len(qs)}] {q['id']} {q['type']:10s} {j['verdict'] or '??':9s} | {q['question'][:70]}", flush=True)
        if not (a.cached and j["cached"]):
            time.sleep(delay)
    return rows


def summarize(rows: list[dict], answers: bool) -> dict:
    ans = [r for r in rows if "hit@1" in r]
    s = {"n_questions": len(rows)}
    s["retrieval"] = aggregate(ans, R_KEYS)
    s["retrieval_para"] = aggregate(ans, [f"para_{k}" for k in R_KEYS])
    s["retrieval_by_type"] = {t: aggregate([r for r in ans if r["type"] == t], ["hit@5", "mrr"]) for t in sorted({r["type"] for r in ans})}
    return s


def summarize_answers(rows: list[dict]) -> dict:
    keys = ["correctness", "false_refusal", "cit_precision", "cit_recall", "para_cit_precision", "para_cit_recall",
            "quote_verified", "context_hit", "abstain_correct"]
    s = aggregate(rows, keys)
    s["verdicts"] = {v: sum(1 for r in rows if r["verdict"] == v) for v in ("correct", "partial", "incorrect", None)}
    s["by_type"] = {t: aggregate([r for r in rows if r["type"] == t], ["correctness"]) for t in sorted({r["type"] for r in rows})}
    return s


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--modes", nargs="+", default=["hybrid"], choices=["bm25", "dense", "hybrid"])
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--rrf-k", type=int, default=60)
    ap.add_argument("--answers", action="store_true", help="generálás + LLM-bíró (lassú, kvótát fogyaszt)")
    ap.add_argument("--delay", type=float, default=12.0, help="szünet kérdésenként, ha nem cache-ből jött")
    ap.add_argument("--cfg", nargs="*", default=[], metavar="KULCS=ÉRTÉK",
                    help="RAGConfig mezők, YAML-értékkel, pl. rerank=mminilm rewrite=both 'rrf_weights={bm25: 0.5}'")
    ap.add_argument("--judge", nargs="+", default=DEFAULT_JUDGE,
                    help="bíró modell(ek); egyetlen modellel a bíró nem cserélődik kvótahiány esetén (a hiányzó ítélet None)")
    args = ap.parse_args()

    qs = load_questions(args.split)
    RESULTS.mkdir(exist_ok=True)
    out = {"name": args.name, "split": args.split, "date": datetime.now().isoformat(timespec="seconds"), "runs": {}}
    for mode in args.modes:
        overrides = {k: yaml.safe_load(v) for k, v in (x.split("=", 1) for x in args.cfg)}
        cfg = RAGConfig(mode=mode, top_k=args.top_k, rrf_k=args.rrf_k, **overrides)
        rag = RAG(cfg)
        print(f"== {mode}: retrieval ({len(qs)} kérdés)")
        rrows = run_retrieval(rag, qs)
        run = {"config": asdict(cfg), "summary": summarize(rrows, args.answers), "retrieval_rows": rrows}
        if args.answers:
            print(f"== {mode}: válaszok + bíró")
            arows = run_answers(rag, qs, args.delay, args.judge)
            run["answer_summary"] = summarize_answers(arows)
            run["answer_rows"] = arows
        out["runs"][mode] = run
        print(json.dumps({"retrieval": run["summary"]["retrieval"], "para": run["summary"]["retrieval_para"]}, ensure_ascii=False))
        if args.answers:
            print(json.dumps(run["answer_summary"], ensure_ascii=False))
    (RESULTS / f"{args.name}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    summary_csv = RESULTS / "summary.csv"
    new_file = not summary_csv.exists()
    with summary_csv.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["date", "name", "split", "mode", "top_k", "n", "hit@1", "hit@5", "recall@10", "mrr", "ndcg@10",
                        "correctness", "cit_precision", "cit_recall", "abstain_correct"])
        for mode, run in out["runs"].items():
            r, a = run["summary"]["retrieval"], run.get("answer_summary", {})
            w.writerow([out["date"], args.name, args.split, mode, args.top_k, len(qs),
                        r.get("hit@1"), r.get("hit@5"), r.get("recall@10"), r.get("mrr"), r.get("ndcg@10"),
                        a.get("correctness"), a.get("cit_precision"), a.get("cit_recall"), a.get("abstain_correct")])
    print(f"Mentve: results/{args.name}.json")
