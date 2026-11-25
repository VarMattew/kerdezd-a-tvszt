"""Sűrű (dense) vektoros index: többnyelvű embedding (alapértelmezés: BAAI/bge-m3) + FAISS – TERV 1.1, 1.4.

A korpusz néhány ezer chunk, ezért pontos keresést (IndexFlatIP, koszinusz a normalizált vektorokon) használunk;
ANN-re (HNSW/PQ) ekkora méretnél nincs szükség.
"""
from __future__ import annotations

import hashlib
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
    def build(
        cls,
        chunks: list[dict],
        model_name: str = DEFAULT_MODEL,
        with_header: bool = True,
        batch_size: int = 16,
        reuse: dict[str, np.ndarray] | None = None,
    ) -> "DenseIndex":
        """reuse: szöveghash -> vektor (egy korábbi index változatlan chunkjai; CPU-n a bge-m3 kb. 40 perc a teljes korpuszra)."""
        _, p_prefix = PREFIXES.get(model_name, ("", ""))
        texts = [p_prefix + index_text(c, with_header) for c in chunks]
        hashes = [text_hash(t) for t in texts]
        reuse = reuse or {}
        todo = [i for i, h in enumerate(hashes) if h not in reuse]
        print(f"  dense: {len(texts) - len(todo)} vektor újrahasznosítva, {len(todo)} új beágyazás")
        new = (
            get_model(model_name).encode(
                [texts[i] for i in todo], batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True, convert_to_numpy=True
            ).astype("float32")
            if todo
            else np.zeros((0, 1), "float32")
        )
        dim = new.shape[1] if todo else next(iter(reuse.values())).shape[0]
        emb = np.zeros((len(texts), dim), "float32")
        for j, i in enumerate(todo):
            emb[i] = new[j]
        for i, h in enumerate(hashes):
            if h in reuse:
                emb[i] = reuse[h]
        idx = faiss.IndexFlatIP(dim)
        idx.add(emb)
        obj = cls(idx, model_name)
        obj.hashes = hashes
        return obj

    def vectors_by_hash(self) -> dict[str, np.ndarray]:
        """A mentett index vektorai szöveghash szerint (a következő újraépítésnél újrahasznosíthatók)."""
        hashes = getattr(self, "hashes", None)
        if not hashes:
            return {}
        vecs = self.index.reconstruct_n(0, self.index.ntotal)
        return {h: vecs[i] for i, h in enumerate(hashes)}

    def search(self, query: str, k: int = 50) -> list[tuple[int, float]]:
        q_prefix, _ = PREFIXES.get(self.model_name, ("", ""))
        q = get_model(self.model_name).encode([q_prefix + query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
        scores, ids = self.index.search(q, k)
        return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]

    def save(self, path: Path = INDEX_DIR / "dense") -> None:
        path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path / "index.faiss"))
        meta = {"model": self.model_name, "n": self.index.ntotal, "hashes": getattr(self, "hashes", None)}
        (path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = INDEX_DIR / "dense") -> "DenseIndex":
        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        obj = cls(faiss.read_index(str(path / "index.faiss")), meta["model"])
        obj.hashes = meta.get("hashes")
        return obj


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()
