"""Cross-encoder újrarangsorolás (TERV 1.5, órai dia: Re-Ranking) és zajszűrés.

A fúzió utáni első N jelöltet egy cross-encoder (kérdés, chunk) párként pontozza. A pontszámok lemezes
gyorsítótárba kerülnek (SQLite; kulcs: modell + kérdés + chunk-szöveg hash), mert CPU-n a nagy modell
~0,7 s/pár – így a kísérletek megismételhetők.
"""
from __future__ import annotations

import hashlib
import sqlite3
from functools import lru_cache
from pathlib import Path

from ..index.common import index_text

ROOT = Path(__file__).resolve().parents[3]
CACHE_DB = ROOT / ".cache" / "rerank.sqlite"  # v2: valószínűségek (a v1 kétszer szigmoidolt)
RERANKERS = {
    "bge-m3": "BAAI/bge-reranker-v2-m3",  # 568M, többnyelvű, pontos, de lassú CPU-n
    "mminilm": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",  # 118M, többnyelvű, ~15x gyorsabb
}


@lru_cache(maxsize=2)
def _model(name: str, max_length: int):
    import torch
    from sentence_transformers import CrossEncoder

    # az aktivációt kifejezetten megadjuk: a bge-reranker alapból szigmoidot használ, az mMiniLM nyers logitot adna
    return CrossEncoder(name, max_length=max_length, activation_fn=torch.nn.Sigmoid())


class Reranker:
    def __init__(self, model: str = "bge-m3", max_length: int = 512, with_header: bool = True):
        self.name = RERANKERS.get(model, model)
        self.max_length = max_length
        self.with_header = with_header
        CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(CACHE_DB)
        self.db.execute("CREATE TABLE IF NOT EXISTS s (k TEXT PRIMARY KEY, v REAL)")

    def _key(self, query: str, text: str) -> str:
        return hashlib.sha1(f"{self.name}|{self.max_length}|{query}\x00{text}".encode("utf-8")).hexdigest()

    def score(self, query: str, chunks: list[dict]) -> list[float]:
        """Relevancia-valószínűség (0–1) chunkonként."""
        texts = [index_text(c, self.with_header) for c in chunks]
        keys = [self._key(query, t) for t in texts]
        found = {}
        for i in range(0, len(keys), 500):
            part = keys[i : i + 500]
            q = f"SELECT k, v FROM s WHERE k IN ({','.join('?' * len(part))})"
            found.update(dict(self.db.execute(q, part).fetchall()))
        todo = [i for i, k in enumerate(keys) if k not in found]
        if todo:
            raw = _model(self.name, self.max_length).predict([(query, texts[i]) for i in todo], batch_size=8)
            for i, r in zip(todo, raw):
                # szigmoid aktiváció (lásd _model): ez már valószínűség
                found[keys[i]] = float(r)
            self.db.executemany("INSERT OR REPLACE INTO s VALUES (?, ?)", [(keys[i], found[keys[i]]) for i in todo])
            self.db.commit()
        return [found[k] for k in keys]
