"""Sűrű (dense) vektoros index: többnyelvű embedding (alapértelmezés: BAAI/bge-m3) + FAISS – TERV 1.1, 1.4.

A korpusz néhány ezer chunk, ezért pontos keresést (IndexFlatIP, koszinusz a normalizált vektorokon) használunk;
ANN-re (HNSW/PQ) ekkora méretnél nincs szükség.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import faiss
import numpy as np

from .common import INDEX_DIR, index_text

DEFAULT_MODEL = "BAAI/bge-m3"
# az e5-modellek előtagot várnak („query: ” / „passage: ”), a bge-m3 nem
PREFIXES = {"intfloat/multilingual-e5-large": ("query: ", "passage: "), "intfloat/multilingual-e5-base": ("query: ", "passage: ")}


@lru_cache(maxsize=2)
def get_model(name: str = DEFAULT_MODEL):
    from sentence_transformers import SentenceTransformer

    m = SentenceTransformer(name, device="cpu")
    m.max_seq_length = 512
    return m


class DenseIndex:
    def __init__(self, index: faiss.Index, model_name: str):
        self.index = index
        self.model_name = model_name

    @classmethod
    def build(cls, chunks: list[dict], model_name: str = DEFAULT_MODEL, with_header: bool = True, batch_size: int = 16) -> "DenseIndex":
        _, p_prefix = PREFIXES.get(model_name, ("", ""))
        texts = [p_prefix + index_text(c, with_header) for c in chunks]
        emb = get_model(model_name).encode(
            texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True, convert_to_numpy=True
        ).astype("float32")
        idx = faiss.IndexFlatIP(emb.shape[1])
        idx.add(emb)
        return cls(idx, model_name)

    def search(self, query: str, k: int = 50) -> list[tuple[int, float]]:
        q_prefix, _ = PREFIXES.get(self.model_name, ("", ""))
        q = get_model(self.model_name).encode([q_prefix + query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
        scores, ids = self.index.search(q, k)
        return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]

    def save(self, path: Path = INDEX_DIR / "dense") -> None:
        path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path / "index.faiss"))
        (path / "meta.json").write_text(json.dumps({"model": self.model_name, "n": self.index.ntotal}), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = INDEX_DIR / "dense") -> "DenseIndex":
        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        return cls(faiss.read_index(str(path / "index.faiss")), meta["model"])
