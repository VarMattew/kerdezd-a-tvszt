"""Gold-bővítés (TERV 3.1, 4. lépés): a kérdésre szintén választ adó, de még nem gold chunkok felkutatása.

Minden megválaszolható kérdésre a három keresőmód (bm25, dense, hybrid) top-5 találatainak uniójából a nem-gold
chunkokat egy LLM megvizsgálja: tartalmazza-e a referenciaválasz lényegét. A javaslatok az eval/gold_suggestions.jsonl-ba
kerülnek; ezeket kézzel kell jóváhagyni (eval/review.jsonl „add_gold”, ill. kézzel írt kérdésnél a handwritten.jsonl).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from vikrag.llm.client import LLMError, chat, parse_json
from vikrag.retrieve.hybrid import HybridRetriever

ROOT = Path(__file__).resolve().parents[1]
PROMPT = """Egy kérdést, a helyes referenciaválaszt és több FORRÁS-részletet kapsz egy egyetemi szabályzatból.
Döntsd el forrásonként: önmagában (vagy a referenciaválasz egy lényegi részét tekintve) alátámasztja-e a forrás a referenciaválaszt?
Csak akkor jelöld, ha a forrás TÉNYLEG tartalmazza a válasz lényegi információját (ugyanazt a szabályt / számot / feltételt),
nem elég, ha csak a témához kapcsolódik.
KIMENET: kizárólag JSON: {"supporting": [forrásszámok listája], "reason": "rövid indoklás"}"""

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    qs = [json.loads(x) for x in (ROOT / "eval" / "questions.jsonl").open(encoding="utf-8")]
    r = HybridRetriever.load()
    out = (ROOT / "eval" / "gold_suggestions.jsonl").open("w", encoding="utf-8")
    for q in qs:
        if not q["answerable"]:
            continue
        cand, seen = [], set(q["gold_chunk_ids"])
        for mode in ("hybrid", "bm25", "dense"):
            for h in r.search(q["question"], k=5, mode=mode):
                cid = h.chunk["chunk_id"]
                if cid not in seen:
                    seen.add(cid)
                    cand.append(h.chunk)
        if not cand:
            continue
        src = "\n\n".join(f"FORRÁS {i}: {c['citation']}\n{c['text']}" for i, c in enumerate(cand, 1))
        msg = [{"role": "system", "content": PROMPT},
               {"role": "user", "content": f"KÉRDÉS: {q['question']}\nREFERENCIAVÁLASZ: {q['gold_answer']}\n\n{src}"}]
        try:
            resp = chat(msg, models=["gemini:gemini-3.5-flash", "groq:openai/gpt-oss-120b"], temperature=0, json_mode=True)
            d = parse_json(resp.text)
        except (LLMError, ValueError) as e:
            print(f"{q['id']}: HIBA {e}")
            continue
        sup = [cand[i - 1] for i in d.get("supporting", []) if isinstance(i, int) and 1 <= i <= len(cand)]
        rec = {"id": q["id"], "question": q["question"], "suggested": [c["chunk_id"] for c in sup],
               "citations": [c["citation"] for c in sup], "reason": d.get("reason", ""), "model": resp.model}
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.flush()
        print(f"{q['id']}: +{len(sup)} {rec['citations']}", flush=True)
        if not resp.cached:
            time.sleep(5)
