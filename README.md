# Kérdezd a TVSZ-t! (`kerdezd-a-tvszt`)

RAG-alapú chatbot a **BME VIK-re érvényes** tanulmányi szabályzatokhoz (TVSZ, kari szabályzatok, tárgyadatlapok), amely minden válaszában **a pontos bekezdést idézi** (pl. `[TVSZ 56. § (1)]`).

> BME „AI in Practice” félévközi feladat (17. téma). Nem hivatalos tájékoztatás: mindig ellenőrizd az eredeti szabályzatot.

**Állapot:** fejlesztés alatt (F5 kész: lekérdezés-átírás + reranker + zajszűrés; test: retrieval hit@5 0,96, válaszhelyesség 0,95). A részletes terv: [TERV.md](TERV.md), a fejlesztési napló: [docs/NAPLO.md](docs/NAPLO.md).

- 🌐 Demó (Hugging Face Spaces): *hamarosan*
- 📊 Kiértékelés: 86 kérdés ([eval/questions.jsonl](eval/questions.jsonl)), eredmények: [results/](results/); a baseline-számok a [TERV 3.1](TERV.md#31-kiértékelő-halmaz-cél-80100-kérdés-minimum-50) alatt

## Fejlesztői környezet

```bash
uv sync
cp .env.example .env   # majd töltsd ki az API-kulcsokat
uv run pytest
```

Adatok letöltése és a beszkennelt dokumentumok OCR-ezése:

```bash
uv run python scripts/fetch.py
uv run python scripts/ocr_pdf.py
uv run python scripts/build_chunks.py   # -> data/processed/chunks.jsonl
uv run python scripts/build_index.py    # -> data/index/ (BM25 + bge-m3; CPU-n ~40 perc)
```

Kérdezés parancssorból (a `.env`-ben kell a `GROQ_API_KEY` és a `GEMINI_API_KEY`):

```bash
uv run python scripts/ask.py "Mennyibe kerül a harmadik vizsga ugyanabból a tárgyból?"
uv run python scripts/ask.py "Bebuktam a zh-t, mi lesz az aláírással?" --baseline   # F3-as baseline-nal
```

Az alapértelmezett folyamat (`configs/final.yaml`): szótáras + LLM-es lekérdezés-átírás → BM25 ∥ bge-m3 → RRF → `bge-reranker-v2-m3` → zajszűrés → válasz pontos hivatkozással. Minden lépés kapcsolható (`RAGConfig`); a reranker CPU-n kérdésenként kb. 10 s.

Kiértékelés (`results/<név>.json` + `results/summary.csv`):

```bash
uv run python eval/run.py --name retrieval --split all --modes bm25 dense hybrid   # csak keresés, LLM nélkül
uv run python eval/run.py --name answers --split test --answers                   # generálás + LLM-bíró (kvótát fogyaszt)
uv run python eval/run.py --name baseline --split test --answers --cfg rewrite=none rerank="" min_score=0
uv run python eval/ablate.py configs/f5_shortlist.yaml --split test                # retrieval-ablációk
```

A kiértékelő halmaz újraépítése: `eval/build_questions.py` (jelöltek) → kézi átnézés (`eval/review.jsonl`, `eval/handwritten.jsonl`, `eval/gold_additions.jsonl`) → `eval/finalize_questions.py`.

Az OCR-hez Tesseract magyar nyelvi modell kell (Windows + MSYS2: `pacman -S mingw-w64-ucrt-x86_64-tesseract-ocr mingw-w64-ucrt-x86_64-tesseract-data-hun`). A tessdata útvonala a `TESSDATA_PREFIX` környezeti változóval állítható.

## Tapasztalatok és tanulságok

Lásd: [docs/NAPLO.md](docs/NAPLO.md). A végleges összefoglaló a projekt végén kerül ide.
