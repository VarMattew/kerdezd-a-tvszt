"""Kiértékelési metrikák (TERV 3.2–3.3).

Retrieval (ground truth): hit@k, recall@k, MRR, nDCG@10 – szigorúan chunk-szinten és lazán paragrafus-szinten
(ugyanazon § / kari pont más bekezdése vagy darabja is találatnak számít).
Válasz: helyesség (LLM-bíró), hivatkozási precizitás és felidézés, idézethűség, absztinencia.
"""
from __future__ import annotations

import math
from statistics import mean


def para_key(chunk_id: str) -> str:
    """Paragrafus-szintű kulcs: tvsz:54:4 -> tvsz:54 ; tjsz:m3:2:1 -> tjsz:m3:2 ; kp_x:targy:CODE -> változatlan."""
    base = chunk_id.split("#")[0].split("~")[0]
    doc, *rest = base.split(":")
    if not rest:
        return doc
    if rest[0] == "targy" or rest[0].startswith("s"):
        return base
    keep = 2 if rest[0].startswith("m") and len(rest) > 1 else 1
    return ":".join([doc, *rest[:keep]])


def strip_part(chunk_id: str) -> str:
    return chunk_id.split("#")[0]


def _key_fn(level: str, groups: list[list[str]] | None):
    """Kulcsfüggvény: az ekvivalens gold chunkokat (pl. a ZV-szabályzat szó szerinti TVSZ-másolatait) egy kulcsra
    képezi, így egy szöveg több példánya nem rontja a recall-t és nem számít többször."""
    base = para_key if level == "para" else strip_part
    canon = {x: grp[0] for grp in (groups or []) for x in grp}
    return lambda x: base(canon.get(x, x))


def _rels(retrieved: list[str], gold: list[str], level: str, groups=None) -> tuple[list[bool], set[str]]:
    f = _key_fn(level, groups)
    g = {f(x) for x in gold}
    seen, rels = set(), []
    for r in retrieved:
        k = f(r)
        rels.append(k in g and k not in seen)  # egy gold egységet csak egyszer számolunk
        if k in g:
            seen.add(k)
    return rels, g


def retrieval_metrics(retrieved: list[str], gold: list[str], ks=(1, 3, 5, 10), level: str = "chunk",
                      groups: list[list[str]] | None = None) -> dict:
    rels, g = _rels(retrieved, gold, level, groups)
    out = {}
    for k in ks:
        found = sum(rels[:k])
        out[f"hit@{k}"] = float(found > 0)
        out[f"recall@{k}"] = found / len(g) if g else 0.0
    first = next((i for i, r in enumerate(rels, 1) if r), None)
    out["mrr"] = 1.0 / first if first else 0.0
    dcg = sum(1.0 / math.log2(i + 1) for i, r in enumerate(rels[:10], 1) if r)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(g), 10) + 1))
    out["ndcg@10"] = dcg / idcg if idcg else 0.0
    return out


def citation_metrics(cited: list[str], gold: list[str], level: str = "chunk",
                     groups: list[list[str]] | None = None) -> dict:
    f = _key_fn(level, groups)
    c, g = {f(x) for x in cited}, {f(x) for x in gold}
    return {
        "cit_precision": len(c & g) / len(c) if c else 0.0,
        "cit_recall": len(c & g) / len(g) if g else 0.0,
    }


VERDICT_SCORE = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}


def aggregate(rows: list[dict], keys: list[str]) -> dict:
    return {k: round(mean(r[k] for r in rows if r.get(k) is not None), 4) for k in keys if any(r.get(k) is not None for r in rows)}
