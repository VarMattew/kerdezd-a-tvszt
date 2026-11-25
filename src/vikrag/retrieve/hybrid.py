"""Hibrid keresés: BM25 ∥ dense -> Reciprocal Rank Fusion (Cormack et al., 2009) – TERV 1.4, órai dia: RRF.

RRF_score(d) = Σ_r 1 / (k + rank_r(d)),  rank 1-től számozva; k = 60 (a 20–100 tartomány érdemben nem változtat).
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


def rrf(rankings: dict[str, list[tuple[int, float]]], k: int = 60) -> list[tuple[int, float, dict, dict]]:
    fused: dict[int, float] = {}
    ranks: dict[int, dict] = {}
    raw: dict[int, dict] = {}
    for name, lst in rankings.items():
        for r, (i, s) in enumerate(lst, 1):
            fused[i] = fused.get(i, 0.0) + 1.0 / (k + r)
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
