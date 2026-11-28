"""Hibrid keresés: BM25 ∥ dense -> Reciprocal Rank Fusion (Cormack et al., 2009) – TERV 1.4, órai dia: RRF.

RRF_score(d) = Σ_r w_r / (k + rank_r(d)),  rank 1-től számozva; k = 60 (a 20–100 tartomány érdemben nem változtat).
F5: súlyozott RRF (w_r: rangsoronkénti súly, pl. gyengébb BM25 → kisebb súly) és több lekérdezésváltozat
(eredeti / szótárral bővített / LLM-mel átírt) rangsorainak egyesítése.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..index.bm25 import BM25Index
from ..index.common import load_chunks
from ..index.dense import DenseIndex


@dataclass
class Hit:
    idx: int  # chunk-index a chunks.jsonl-ban
    chunk: dict
    score: float  # a végső rangsor pontszáma (RRF vagy az egyedüli ranker pontszáma)
    ranks: dict = field(default_factory=dict)  # {"bm25": 3, "dense": 1} – a felületen és a hibaelemzésben jelenik meg
    scores: dict = field(default_factory=dict)


def rrf(rankings: dict[str, list[tuple[int, float]]], k: int = 60, weights: dict[str, float] | None = None) -> list[tuple[int, float, dict, dict]]:
    """weights: rangsornév -> súly; a „bm25:llm” nevű rangsor súlyát a „bm25” kulcs adja, ha nincs saját."""
    fused: dict[int, float] = {}
    ranks: dict[int, dict] = {}
    raw: dict[int, dict] = {}
    weights = weights or {}
    for name, lst in rankings.items():
        w = weights.get(name, weights.get(name.split(":")[0], 1.0))
        if w <= 0:
            continue
        for r, (i, s) in enumerate(lst, 1):
            fused[i] = fused.get(i, 0.0) + w / (k + r)
            ranks.setdefault(i, {})[name] = r
            raw.setdefault(i, {})[name] = s
    order = sorted(fused, key=lambda i: -fused[i])
    return [(i, fused[i], ranks[i], raw[i]) for i in order]


class HybridRetriever:
    def __init__(self, bm25: BM25Index | None = None, dense: DenseIndex | None = None, chunks: list[dict] | None = None):
        self.chunks = chunks or load_chunks()
        self.bm25 = bm25
        self.dense = dense

    @classmethod
    def load(cls, use_bm25: bool = True, use_dense: bool = True) -> "HybridRetriever":
        return cls(BM25Index.load() if use_bm25 else None, DenseIndex.load() if use_dense else None)

    def search(self, query: str, k: int = 20, mode: str = "hybrid", candidates: int = 50, rrf_k: int = 60) -> list[Hit]:
        """mode: 'bm25' | 'dense' | 'hybrid' (E1 kísérlet)."""
        rankings = {}
        if mode in ("bm25", "hybrid") and self.bm25:
            rankings["bm25"] = self.bm25.search(query, candidates)
        if mode in ("dense", "hybrid") and self.dense:
            rankings["dense"] = self.dense.search(query, candidates)
        if len(rankings) == 1:
            name, lst = next(iter(rankings.items()))
            return [Hit(i, self.chunks[i], s, {name: r}, {name: s}) for r, (i, s) in enumerate(lst[:k], 1)]
        return [Hit(i, self.chunks[i], s, rk, raw) for i, s, rk, raw in rrf(rankings, rrf_k)[:k]]

    def search_multi(self, queries: dict[str, str], k: int = 20, mode: str = "hybrid", candidates: int = 50,
                     rrf_k: int = 60, weights: dict[str, float] | None = None) -> list[Hit]:
        """Több lekérdezésváltozat × ranker, súlyozott RRF-fel egyesítve. A rangsorok neve „ranker:változat”."""
        if len(queries) == 1 and not weights:
            return self.search(next(iter(queries.values())), k, mode, candidates, rrf_k)
        rankings = {}
        for vname, q in queries.items():
            if mode in ("bm25", "hybrid") and self.bm25:
                rankings[f"bm25:{vname}"] = self.bm25.search(q, candidates)
            if mode in ("dense", "hybrid") and self.dense:
                rankings[f"dense:{vname}"] = self.dense.search(q, candidates)
        return [Hit(i, self.chunks[i], s, rk, raw) for i, s, rk, raw in rrf(rankings, rrf_k, weights)[:k]]
