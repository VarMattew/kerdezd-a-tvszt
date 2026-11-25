"""A teljes RAG-folyamat (baseline, F3): hibrid keresés -> top-k kontextus -> válasz pontos hivatkozással.

Az advanced elemek (reranker, zajszűrés, lekérdezés-átírás, kereszthivatkozás-bővítés) az F5-ben kerülnek ide,
konfigurációból ki/be kapcsolhatóan.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from .generate.answer import Answer, generate_answer
from .llm.client import DEFAULT_GENERATOR
from .retrieve.hybrid import Hit, HybridRetriever


@dataclass
class RAGConfig:
    mode: str = "hybrid"  # bm25 | dense | hybrid
    candidates: int = 50  # rangsoronként ennyi jelölt megy a fúzióba
    rrf_k: int = 60
    top_k: int = 5  # ennyi chunk kerül az LLM elé (lost in the middle: 3–5)
    models: list[str] = field(default_factory=lambda: list(DEFAULT_GENERATOR))
    prompt: str = "answer_v1"


@dataclass
class RAGResult:
    question: str
    hits: list[Hit]
    answer: Answer | None
    timings: dict

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "hits": [{"chunk_id": h.chunk["chunk_id"], "citation": h.chunk["citation"], "score": h.score, "ranks": h.ranks} for h in self.hits],
            "answer": asdict(self.answer) if self.answer else None,
            "timings": self.timings,
        }


class RAG:
    def __init__(self, config: RAGConfig | None = None, retriever: HybridRetriever | None = None):
        self.config = config or RAGConfig()
        self.retriever = retriever or HybridRetriever.load(
            use_bm25=self.config.mode in ("bm25", "hybrid"), use_dense=self.config.mode in ("dense", "hybrid")
        )

    def retrieve(self, question: str, k: int | None = None) -> list[Hit]:
        c = self.config
        return self.retriever.search(question, k=k or c.top_k, mode=c.mode, candidates=c.candidates, rrf_k=c.rrf_k)

    def ask(self, question: str, generate: bool = True) -> RAGResult:
        t0 = time.time()
        hits = self.retrieve(question)
        t1 = time.time()
        ans = generate_answer(question, [h.chunk for h in hits], self.config.models, self.config.prompt) if generate else None
        return RAGResult(question, hits, ans, {"retrieval_s": round(t1 - t0, 2), "generation_s": round(time.time() - t1, 2)})
