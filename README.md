# Kérdezd a TVSZ-t! (`kerdezd-a-tvszt`)

RAG-alapú chatbot a **BME VIK-re érvényes** tanulmányi szabályzatokhoz (TVSZ, kari szabályzatok, tárgyadatlapok), amely minden válaszában **a pontos bekezdést idézi** (pl. `[TVSZ 56. § (1)]`).

> BME „AI in Practice” félévközi feladat (17. téma). Nem hivatalos tájékoztatás: mindig ellenőrizd az eredeti szabályzatot.

**Állapot:** fejlesztés alatt (F0 – alapok). A részletes terv: [TERV.md](TERV.md), a fejlesztési napló: [docs/NAPLO.md](docs/NAPLO.md).

- 🌐 Demó (Hugging Face Spaces): *hamarosan*
- 📊 Kiértékelés: *hamarosan*

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
```

Az OCR-hez Tesseract magyar nyelvi modell kell (Windows + MSYS2: `pacman -S mingw-w64-ucrt-x86_64-tesseract-ocr mingw-w64-ucrt-x86_64-tesseract-data-hun`). A tessdata útvonala a `TESSDATA_PREFIX` környezeti változóval állítható.

## Tapasztalatok és tanulságok

Lásd: [docs/NAPLO.md](docs/NAPLO.md). A végleges összefoglaló a projekt végén kerül ide.
