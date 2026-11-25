"""A keresőindexek felépítése a data/processed/chunks.jsonl-ból -> data/index/{bm25,dense}.

Használat:
    uv run python scripts/build_index.py            # mindkettő
    uv run python scripts/build_index.py --only bm25
    uv run python scripts/build_index.py --model intfloat/multilingual-e5-base --out data/index/dense_e5base
"""
import argparse
import time
from pathlib import Path

from vikrag.index.bm25 import BM25Index
from vikrag.index.common import INDEX_DIR, load_chunks
from vikrag.index.dense import DEFAULT_MODEL, DenseIndex

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["bm25", "dense"])
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    chunks = load_chunks()
    print(f"{len(chunks)} chunk")
    if args.only in (None, "bm25"):
        t = time.time()
        BM25Index.build(chunks).save(INDEX_DIR / "bm25")
        print(f"BM25 kész ({time.time() - t:.0f} s)")
    if args.only in (None, "dense"):
        t = time.time()
        DenseIndex.build(chunks, args.model).save(args.out or INDEX_DIR / "dense")
        print(f"Dense ({args.model}) kész ({time.time() - t:.0f} s)")
