"""A korpusz feldolgozása chunkokká: data/raw/* -> data/processed/chunks.jsonl (+ stats.json).

Használat:
    uv run python scripts/build_chunks.py
    uv run python scripts/build_chunks.py --only tvsz vik_bsc_zv   # csak ezek (a kimenet csak ezeket tartalmazza!)
"""
import argparse
import time

from vikrag.ingest.build import build, write

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    t0 = time.time()
    chunks = build(args.only, args.workers)
    stats = write(chunks)
    print(f"{stats['total_chunks']} chunk, {stats['total_chars'] / 1000:.0f}k karakter, "
          f"{stats['with_crossrefs']} kereszthivatkozással ({time.time() - t0:.0f} s)")
    for doc_id, d in stats["documents"].items():
        print(f"  {doc_id:28s} {d['chunks']:5d} chunk  {d['chars'] / 1000:6.0f}k  {d['kinds']}")
