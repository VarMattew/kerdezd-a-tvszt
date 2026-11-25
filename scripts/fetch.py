"""Letölti a data/sources.yaml-ban felsorolt dokumentumokat a data/raw/ mappába.

Használat:
    uv run python scripts/fetch.py               # minden prioritás
    uv run python scripts/fetch.py --max-priority P0
    uv run python scripts/fetch.py --force       # meglévő fájlok újraletöltése
    uv run python scripts/fetch.py --only tvsz tjsz

Eredmény: data/raw/<id>.<pdf|html> + data/raw/manifest.json (sha256, méret, időpont, végső URL).
Udvarias letöltés: kérések között szünet, saját User-Agent, nincs crawl (csak a listában szereplő URL-ek).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import truststore
import yaml

# Az OS tanúsítványtárát használjuk (Windows alatt a certifi-ből hiányzik pl. a kth.bme.hu köztes tanúsítványa).
truststore.inject_into_ssl()

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.yaml"
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.json"
USER_AGENT = "kerdezd-a-tvszt/0.1 (BME AI in Practice student project; regulation RAG)"
DELAY_S = 1.5
PRIORITIES = ["P0", "P1", "P2"]


def load_sources() -> list[dict]:
    with SOURCES.open(encoding="utf-8") as f:
        return yaml.safe_load(f)["documents"]


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def validate(content: bytes, fmt: str, content_type: str) -> str | None:
    """Hibaüzenetet ad vissza, ha a letöltött tartalom nem a várt formátumú."""
    if fmt == "pdf" and not content.startswith(b"%PDF"):
        return f"nem PDF (Content-Type: {content_type})"
    if fmt == "html" and b"<html" not in content[:2000].lower():
        return f"nem HTML (Content-Type: {content_type})"
    return None


def fetch_one(session: requests.Session, doc: dict) -> dict:
    resp = session.get(doc["url"], timeout=60)
    resp.raise_for_status()
    content = resp.content
    ctype = resp.headers.get("Content-Type", "")
    err = validate(content, doc["format"], ctype)
    if err:
        raise ValueError(err)
    path = RAW / f"{doc['id']}.{doc['format']}"
    path.write_bytes(content)
    return {
        "id": doc["id"],
        "file": path.relative_to(ROOT).as_posix(),
        "url": doc["url"],
        "final_url": resp.url,
        "content_type": ctype,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-priority", choices=PRIORITIES, default="P2")
    ap.add_argument("--only", nargs="*", help="csak ezek az id-k")
    ap.add_argument("--force", action="store_true", help="meglévő fájlok újraletöltése")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    allowed = PRIORITIES[: PRIORITIES.index(args.max_priority) + 1]
    docs = [d for d in load_sources() if d["priority"] in allowed]
    if args.only:
        docs = [d for d in docs if d["id"] in set(args.only)]

    manifest = load_manifest()
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    failures = []
    for i, doc in enumerate(docs, 1):
        path = RAW / f"{doc['id']}.{doc['format']}"
        if path.exists() and doc["id"] in manifest and not args.force:
            print(f"[{i}/{len(docs)}] {doc['id']}: megvan, kihagyva")
            continue
        try:
            entry = fetch_one(session, doc)
            manifest[doc["id"]] = entry
            print(f"[{i}/{len(docs)}] {doc['id']}: OK ({entry['bytes'] / 1024:.0f} KiB)")
        except Exception as exc:  # noqa: BLE001 – a hibát listázzuk, a többi letöltés folytatódik
            failures.append((doc["id"], str(exc)))
            print(f"[{i}/{len(docs)}] {doc['id']}: HIBA – {exc}", file=sys.stderr)
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(DELAY_S)

    print(f"\nKész: {len(docs) - len(failures)}/{len(docs)} sikeres.")
    for doc_id, err in failures:
        print(f"  ✗ {doc_id}: {err}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
