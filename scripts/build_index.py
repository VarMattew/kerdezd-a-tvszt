"""A keresőindexek felépítése a data/processed/chunks.jsonl-ból -> data/index/{bm25,dense}.

A dense index újraépítésekor a változatlan szövegű chunkok vektorait a meglévő indexből vesszük át
(szöveghash alapján), így csak az új/módosult chunkokat kell beágyazni (a bge-m3 CPU-n ~40 perc a teljes korpuszra).

Használat:
    uv run python scripts/build_index.py            # mindkettő
    uv run python scripts/build_index.py --only bm25
    uv run python scripts/build_index.py --model intfloat/multilingual-e5-base --out data/index/dense_e5base
    uv run python scripts/build_index.py --no-reuse # teljes újraszámolás
"""
import argparse
import json
import time
from pathlib import Path

from vikrag.index.bm25 import BM25Index
from vikrag.index.common import INDEX_DIR, index_text, load_chunks
from vikrag.index.dense import DEFAULT_MODEL, PREFIXES, DenseIndex, text_hash


def reuse_map(path: Path, model: str) -> dict:
    if not (path / "meta.json").exists():
        return {}
    old = DenseIndex.load(path)
    if old.model_name != model:
        return {}
    if not getattr(old, "hashes", None):  # régi index hash nélkül: a korábbi chunklistából számoljuk
        prev = INDEX_DIR / "chunks_prev.jsonl"
        if not prev.exists():
            return {}
        prev_chunks = [json.loads(x) for x in prev.open(encoding="utf-8")]
        if len(prev_chunks) != old.index.ntotal:
            return {}
        _, p = PREFIXES.get(model, ("", ""))
        old.hashes = [text_hash(p + index_text(c)) for c in prev_chunks]
    return old.vectors_by_hash()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["bm25", "dense"])
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-reuse", action="store_true")
    args = ap.parse_args()
    chunks = load_chunks()
    print(f"{len(chunks)} chunk")
    if args.only in (None, "bm25"):
        t = time.time()
        BM25Index.build(chunks).save(INDEX_DIR / "bm25")
        print(f"BM25 kész ({time.time() - t:.0f} s)")
    if args.only in (None, "dense"):
        t = time.time()
        out = args.out or INDEX_DIR / "dense"
        reuse = {} if args.no_reuse else reuse_map(out, args.model)
        DenseIndex.build(chunks, args.model, reuse=reuse).save(out)
        print(f"Dense ({args.model}) kész ({time.time() - t:.0f} s)")
