"""BM25 kulcsszavas index magyar szótövezéssel (Snowball Hungarian, PyStemmer) – TERV 1.4."""
from __future__ import annotations

import re
from pathlib import Path

import bm25s
import numpy as np
import Stemmer

from .common import INDEX_DIR, index_text, load_chunks

# rövid magyar stopszólista (névelők, kötőszavak, gyakori névmások) – a jogi szöveg kulcsszavait nem érinti
HU_STOPWORDS = sorted(set("""
a az egy és vagy is nem de hogy ha akkor mint már még csak meg el ki be fel le
ez ezt ennek ezen ezek azok azt annak arra arról erre erről abban ebben azon
van volt lesz lehet kell nincs vannak
aki ami amely amelyet amelynek akinek amelyek amit akik
illetve valamint továbbá azaz pedig sem se
én te ő mi ti ők
""".split()))

_stemmer = Stemmer.Stemmer("hungarian")
# tárgykódok (VIAUAC15) egyben maradnak; §-számok (55/a) és szavak külön tokenek
TOKEN_RE = re.compile(r"[a-záéíóöőúüű]+\d[a-z0-9]*|\d+(?:/[a-z])?|[a-záéíóöőúüű]+", re.I)


def tokenize(text: str, stem: bool = True) -> list[str]:
    toks = [t.lower() for t in TOKEN_RE.findall(text)]
    toks = [t for t in toks if t not in HU_STOPWORDS]
    return _stemmer.stemWords(toks) if stem else toks


class BM25Index:
    def __init__(self, retriever: bm25s.BM25, stem: bool = True):
        self.retriever = retriever
        self.stem = stem

    @classmethod
    def build(cls, chunks: list[dict], stem: bool = True, with_header: bool = True) -> "BM25Index":
        corpus = [tokenize(index_text(c, with_header), stem) for c in chunks]
        r = bm25s.BM25(k1=1.2, b=0.75)
        r.index(corpus, show_progress=False)
        return cls(r, stem)

    def search(self, query: str, k: int = 50) -> list[tuple[int, float]]:
        q = tokenize(query, self.stem)
        if not q:
            return []
        scores = self.retriever.get_scores(q)
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top if scores[i] > 0]

    def save(self, path: Path = INDEX_DIR / "bm25") -> None:
        self.retriever.save(str(path))

    @classmethod
    def load(cls, path: Path = INDEX_DIR / "bm25", stem: bool = True) -> "BM25Index":
        return cls(bm25s.BM25.load(str(path)), stem)


if __name__ == "__main__":
    idx = BM25Index.build(load_chunks())
    print(idx.search("hányszor lehet vizsgázni egy tárgyból", 5))
