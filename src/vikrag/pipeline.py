"""A teljes RAG-folyamat (TERV 1.3–1.6), minden advanced elem konfigurációból ki/be kapcsolható (F5):

  kérdés ─► lekérdezés-változatok (eredeti · szótáras bővítés · LLM-átírás)
         ─► BM25 ∥ dense változatonként ─► súlyozott RRF
         ─► cross-encoder újrarangsorolás (első N jelölt) ─► zajszűrés (küszöb)
         ─► top-k ─► kereszthivatkozás-bővítés ─► kontextus-sorrend (lost in the middle)
         ─► válasz pontos hivatkozással + idézet-ellenőrzés
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from .generate.answer import Answer, generate_answer
from .llm.client import DEFAULT_GENERATOR
from .retrieve.hybrid import Hit, HybridRetriever
from .retrieve.query import query_variants


# Az alapértékek a F5-ben kiválasztott konfiguráció (configs/final.yaml). A F3-as baseline: configs/baseline.yaml
# (rewrite=none, rerank="", min_score=0).
BASELINE = {"rewrite": "none", "rerank": "", "min_score": 0.0}


@dataclass
class RAGConfig:
    mode: str = "hybrid"  # bm25 | dense | hybrid
    candidates: int = 50  # rangsoronként ennyi jelölt megy a fúzióba
    rrf_k: int = 60
    rrf_weights: dict[str, float] = field(default_factory=dict)  # pl. {"bm25": 0.5}; „bm25:orig”: 0 = az eredeti kérdésre nincs BM25
    rewrite: str = "both"  # none | glossary | llm | both
    rerank: str = "bge-m3"  # "" = nincs; bge-m3 | mminilm | HF-modellnév
    rerank_candidates: int = 15
    rerank_query: str = "llm"  # orig | llm – melyik kérdésváltozattal pontoz a cross-encoder
    min_score: float = 0.05  # zajszűrés: ennél kisebb reranker-valószínűségű chunk nem kerül az LLM elé
    min_keep: int = 1  # ...de legalább ennyi marad
    top_k: int = 5  # ennyi chunk kerül az LLM elé (lost in the middle: 3–5)
    crossref: int = 0  # a top chunkok kereszthivatkozásaiból legfeljebb ennyit fűzünk a kontextushoz
    order: str = "rank"  # rank | sandwich (a legjobbak a kontextus elején és végén)
    models: list[str] = field(default_factory=lambda: list(DEFAULT_GENERATOR))
    prompt: str = "answer_v1"


@dataclass
class RAGResult:
    question: str
    hits: list[Hit]
    answer: Answer | None
    timings: dict
    queries: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "queries": self.queries,
            "hits": [{"chunk_id": h.chunk["chunk_id"], "citation": h.chunk["citation"], "score": h.score, "ranks": h.ranks,
                      "scores": h.scores} for h in self.hits],
            "answer": asdict(self.answer) if self.answer else None,
            "timings": self.timings,
        }


def sandwich(items: list) -> list:
    """1,2,3,4,5 -> 1,3,5,4,2: a legrelevánsabbak a kontextus két szélére kerülnek (Liu et al., Lost in the Middle)."""
    return items[0::2] + items[1::2][::-1]


class RAG:
    def __init__(self, config: RAGConfig | None = None, retriever: HybridRetriever | None = None):
        self.config = config or RAGConfig()
        self.retriever = retriever or HybridRetriever.load(
            use_bm25=self.config.mode in ("bm25", "hybrid"), use_dense=self.config.mode in ("dense", "hybrid")
        )
        self._reranker = None
        self._by_id = {c["chunk_id"]: i for i, c in enumerate(self.retriever.chunks)}

    @property
    def reranker(self):
        if self._reranker is None and self.config.rerank:
            from .retrieve.rerank import Reranker

            self._reranker = Reranker(self.config.rerank)
        return self._reranker

    def ranked(self, question: str, k: int | None = None) -> tuple[list[Hit], dict]:
        """A végső rangsor (zajszűrés nélkül) – a retrieval-metrikák ezt mérik."""
        c = self.config
        k = k or c.top_k
        queries = query_variants(question, c.rewrite)
        depth = max(k, c.rerank_candidates if c.rerank else k)
        hits = self.retriever.search_multi(queries, k=depth, mode=c.mode, candidates=c.candidates, rrf_k=c.rrf_k,
                                           weights=c.rrf_weights or None)
        if self.reranker and hits:
            rq = queries.get("llm", question) if c.rerank_query == "llm" else question
            scores = self.reranker.score(rq, [h.chunk for h in hits])
            for r, (h, s) in enumerate(zip(hits, scores), 1):
                h.scores["rerank"] = s
                h.ranks["fused"] = r
            hits = sorted(hits, key=lambda h: -h.scores["rerank"])
            for r, h in enumerate(hits, 1):
                h.ranks["rerank"] = r
                h.score = h.scores["rerank"]
        return hits[:k], queries

    def retrieve(self, question: str, k: int | None = None) -> list[Hit]:
        return self.ranked(question, k)[0]

    def context(self, hits: list[Hit]) -> list[Hit]:
        """Zajszűrés + kereszthivatkozás-bővítés + sorrend: ami ténylegesen az LLM elé kerül."""
        c = self.config
        if c.min_score > 0 and hits and "rerank" in hits[0].scores:
            kept = [h for h in hits if h.scores["rerank"] >= c.min_score]
            hits = kept if len(kept) >= c.min_keep else hits[: c.min_keep]
        if c.crossref:
            have = {h.chunk["chunk_id"] for h in hits}
            extra = []
            for h in hits[:3]:
                for ref in h.chunk.get("crossrefs", []):
                    if ref not in have and ref in self._by_id and len(extra) < c.crossref:
                        have.add(ref)
                        i = self._by_id[ref]
                        extra.append(Hit(i, self.retriever.chunks[i], 0.0, {"crossref_of": h.chunk["chunk_id"]}))
            hits = hits + extra
        if c.order == "sandwich":
            hits = sandwich(hits)
        return hits

    def ask(self, question: str, generate: bool = True) -> RAGResult:
        t0 = time.time()
        hits, queries = self.ranked(question)
        ctx = self.context(hits)
        t1 = time.time()
        ans = generate_answer(question, [h.chunk for h in ctx], self.config.models, self.config.prompt) if generate else None
        return RAGResult(question, ctx, ans, {"retrieval_s": round(t1 - t0, 2), "generation_s": round(time.time() - t1, 2)},
                         queries)
