# Fejlesztési napló – ágenssel közös munka

> Leadandó: *„the experiences and lessons learned (e.g. which copilots and agents were used, the key prompts, and what had to be fixed by hand)”*
> Minden munkamenet végén új bejegyzés. A kulcsfontosságú promptok szó szerint szerepelnek.

**Használt eszközök (összesítő, folyamatosan bővül):**
| Eszköz | Mire |
|---|---|
| Claude Code (desktop app, Code fül), modell: Claude Opus 5.5 | tervezés, PDF-elemzés, projektváz, kódgenerálás |

---

## 2026-11-12 – F(-1)/F0: ötletelés, terv, projektváz

**Mit csináltunk**
1. Ötletelés a feladatról (RAG chatbot a TVSZ fölé, pontos bekezdéshivatkozással, ≥50 kérdéses kiértékelés).
2. Az ágens feldolgozta az órai RAG-diasort (`RAG.pdf`, 72 dia), és erre építve részletes tervet írt: [TERV.md](../TERV.md).
3. Az ágens megvizsgálta a TVSZ-PDF szerkezetét (PyMuPDF, span-szintű font/pozíció elemzés).
4. Döntések: csak VIK; Hugging Face Spaces (Gradio); ingyenes Groq/Gemini API, később lokális Qwen; határidő dec. 7. → ütemterv.
5. F0: git repó, mappastruktúra, `pyproject.toml` (uv), `.gitignore`, `.env.example`, `data/sources.yaml`, füstteszt.

**Kulcsfontosságú promptok (szó szerint)**
> „Ebbe a mappába fogunk dolgozni. A feladat a BME "AI in Practice" órájának a félévközi feladata. […] Ötleteljünk kicsit hogy hogyan lehetne ezt jól megcsinálni.”

> „[…] a mappába a TVSZ mellé betettem egy diasort is RAG.pdf néven amiben a tárgyból leadott RAG rendszerek részletei vannak és gyakorlatilag egy best practice eljárás hogy jól sikerüljön. Vegyük ezt a diát alapul a megvalósításhoz. […] készítsünk egy részletes tervet egy markdown fájlba.”

**Érdekes megfigyelések / ágens által talált problémák**
- A **régi** TVSZ-PDF-ben (2022-es egységes szerkezet) a bekezdésszámok („(1)”, „(2)”) **nem voltak benne a szövegrétegben**: Word-automatikus számozásként csak rajzolódtak, a helyükön egy `ArialMT` szóköz-span állt. Ez a pontos hivatkozást veszélyeztette volna (elrendezésalapú rekonstrukció kellett volna).
- A felhasználó talált egy **újabb** TVSZ-t (2025-07-16, XII./3./2024-2025), amelyben a bekezdésszámok már szöveges formában szerepelnek (~1250 bekezdéskezdet, beszúrt „(1a)” típusú bekezdésekkel). → A kockázat jelentősen csökkent.
- A lábjegyzetszámok továbbra is a szövegbe keverednek („(1) 168, 169, 170A hallgatói…”); betűméret alapján szűrhetők.

**Kézi beavatkozás**
- A felhasználó kézzel kereste meg és töltötte le a frissebb TVSZ-t; a határidőt (dec. 7.) kézzel írta be a tervbe.

**Kiegészítés (2026-11-22)**
- A projekt neve: **`kerdezd-a-tvszt`** (Kérdezd a TVSZ-t!). Repó: https://github.com/VarMattew/kerdezd-a-tvszt (a felhasználó hozta létre, az ágens állította be a remote-ot és küldte fel az első commitot).
- A TVSZ forrása a BME Szabályozástár (`szabalyozastar.bme.hu`), az URL bekerült a `data/sources.yaml`-ba.

**Tanulság**
- Mielőtt parsert írunk, érdemes megnézni a PDF szövegrétegét span-szinten: a vizuálisan látható szöveg (pl. sorszámozás) nem feltétlenül kinyerhető.
- A forrásdokumentum verziója nemcsak tartalmi, hanem technikai kérdés is: az újabb verzió könnyebben feldolgozható volt.

---

## 2026-11-25 – F1: adatgyűjtés

**Mit csináltunk**
1. Az ágens feltérképezte a forrásoldalakat: ETK szabályzatok, BME Szabályozástár, vik.bme.hu „Hallgatóknak” és „Szabályzatok” oldalak, a VIK 2026/27-es képzési tájékoztatója, portal.vik.bme.hu.
2. Kb. 110 linkből kiválasztotta a hallgatókra vonatkozó, hatályos dokumentumokat (P0/P1/P2), ezek a `data/sources.yaml`-ba kerültek.
3. `scripts/fetch.py`: udvarias letöltő (saját User-Agent, 1,5 s szünet, formátum-ellenőrzés, `manifest.json` SHA-256-tal). Eredmény: **43 dokumentum**.
4. A letöltött PDF-ek gyors profilozása: oldalszám, szöveghossz, §- és bekezdésszámok, tárgykódok.

**Kulcsfontosságú prompt**
> „Igen, jöhet az F1”, vagyis az ágens a terv alapján önállóan végezte a forráskeresést.

**Érdekes megfigyelések / akadályok**
- **portal.vik.bme.hu: 403 minden kérésre**, a robots.txt-re is. Az ágens egy böngészőnek álcázott User-Agenttel próbálkozott volna, de ezt a Claude Code biztonsági ellenőrzője **jogosan letiltotta**, mert egy hozzáférési korlát megkerülése lett volna. → A tárgyadatlapok helyett a képzési programok mintatanterveit használjuk.
- **A Szabályozástár egy SPA**, az API-ja bejelentkezést kér (401). A közvetlen `/storage/...pdf` linkek viszont publikusak.
- **A VIK-dokumentumok a `/document/<id>/` URL-lel is letölthetők**, fájlnév nélkül. Ez egyszerűsíti a forráslistát, és elkerüli az ékezetes URL-ek kódolási gondjait.
- **A TJSZ beszkennelt PDF**, szövegréteg nélkül → OCR kell majd.
- **A kth.bme.hu tanúsítványlánca hiányos**: a curl (Windows schannel) elfogadta, a Python (certifi) nem. Megoldás: a `truststore` csomag az OS tanúsítványtárát használja, így nem kellett kikapcsolni az ellenőrzést.
- A képzési programokban mintatanterv-táblázatok vannak (pl. `VIAUAC15 Adatvezérelt rendszerek 2/2/0/v/5`), de nincsenek bennük részletes tantárgyleírások.
- A záróvizsga-szabályzatokban vannak „(n)” bekezdésjelölések, de nincs „§”. A parsernek többféle szerkezetet is kezelnie kell.

**Kézi beavatkozás**
- Az ágens a régi `data/raw/tvsz/BME_TVSZ.pdf` másolatot (bájtra azonos a letöltött `tvsz.pdf`-fel) törölte volna, de az auto mode ezt nem engedte; a felhasználóra bízva.

**Kiegészítés: a TJSZ OCR-ezése** (a felhasználó döntése: „OCR-ezzük”)
- A gépen nem volt Tesseract. Az ágens észrevette, hogy van MSYS2, és annak csomagkezelőjével telepítette a Tesseract 5.3.4-et és a magyar nyelvi modellt (`pacman -S mingw-w64-ucrt-x86_64-tesseract-ocr …-data-hun`).
- Kiderült, hogy a **PyMuPDF beépített Tesseract-motorral** rendelkezik, csak a `tessdata` nyelvi fájlok kellenek. Így nem kellett külön Python OCR-csomag (pl. pytesseract, EasyOCR/torch).
- `scripts/ocr_pdf.py`: 300 dpi-s renderelés, oldalanként párhuzamosan (6 folyamat), kereshető PDF a kimenet. 110 oldal kb. 80 másodperc alatt.
- Minőség: a mintaoldal szövege jól olvasható; a § és a bekezdésjelek felismerhetők. Tipikus hibák: szavanként szétesett sorkizárt sorok, „?” és „!” a lábjegyzetjelek helyén, összeragadt szavak. → Ezeket a parserben kell kezelni, és a TJSZ-idézetekhez fuzzy ellenőrzés kell.
- Egy félrevezető részlet: a PDF-be ágyazott egyik képréteg szinte üres maszk volt. A közvetlenül kinyert kép ezért értelmetlennek tűnt, a renderelt oldal viszont rendben volt. → Az OCR-t a renderelt oldalon kell futtatni, nem a beágyazott képen.

---

## 2026-11-25 – F2: szerkezetfelismerő feldolgozás (parser)

**Mit csináltunk**
1. Az ágens span-szinten (betűméret, félkövér, x/y pozíció) megvizsgálta a különböző dokumentumtípusokat: TVSZ, ZV-szabályzat, specializációválasztási szabályzat, szakmai gyakorlat, nyelvi kreditek, képzési program, OCR-es TJSZ. Ebből egy **közös, soralapú szerkezetfelismerőt** tervezett, a különböző formátumokra kis kiegészítésekkel.
2. Modulok: `pdf_lines` → `structure` → `build`, valamint `curriculum` (mintatantervek) és `html_pages`. Mindegyiket először egy dokumentumon próbálta ki, és csak utána futtatta az egész korpuszon.
3. 8 teszt (`tests/test_ingest.py`), köztük egy, amely a felépített korpuszon néz meg ellenőrző pontokat (pl. `tvsz:54:4` = „TVSZ 54. § (4)”, szövegben „2,75”).
4. 30 chunk rétegzett auditja (`scripts/sample_chunks.py` + `scripts/audit_chunks.py`) → **30/30 helyes**.

**Kulcsfontosságú prompt**
> „Igen, jöhet az F2”, vagyis az ágens a terv alapján önállóan dolgozott; a felhasználói döntések korábban születtek (OCR, terjedelem).

**Hibák, amelyeket az ágens maga talált és javított (iteratív hibakeresés)**
- **Kiskapitális fejezetcímek:** „I. F EJEZET”, „Á LTALÁNOS” → a spanokat a vizuális rés alapján fűzi össze, nem mindig szóközzel.
- **TJSZ-mellékletek:** a §-számozás mellékletenként újraindul → a melléklet külön szint lett (`tjsz:m3:…`). Az OCR-rel beolvasott űrlapok értelmetlen szövegét egy „szóminőség” szűrő dobja ki.
- **Csendes összeomlás:** a build egy képzési programnál kilépett, kimenet nélkül. Kiderült, hogy a PyMuPDF 1.27 `find_tables` függvénye egy **ONNX elrendezésmodellt** használ, amely szegmentációs hibával összeomlott (és lassú is). → `use_layout=False`: ugyanaz az eredmény, 5–12× gyorsabban. *Tanulság:* a `cmd | tail` csővezeték elnyelte a hibakódot (exit 0), ezért a kimenetet ezentúl fájlba írjuk, és a valódi kilépési kódot nézzük.
- **Három különböző mintatanterv-formátum**, ezek közül kettőt a hibás vagy hiányzó rekordok számlálása mutatott meg.
- Az audit során 4 további hiba: a SzMSz tartalomjegyzéke mellékletet nyitott; a ZV-szabályzatban a kari pontok a TVSZ-blokkhoz tapadtak; az MSc mintatantervekben sorszám került a tárgynév helyére; az „5. pont” hivatkozás nem volt egyértelmű. Részletek: `docs/chunk_audit.md`.
- Egy teszthiba: az ágens első tesztje rossz feltevésre épült (1. oldali címsor). A hiba a tesztben volt, nem a kódban, ezért a tesztet javította.

**Kézi beavatkozás**
- Nem volt szükség rá. A felhasználó a parser tervezésébe nem szólt bele, az elfogadási kritériumot (≥95% helyes azonosító) a terv rögzítette.

**Tanulság (F2)**
- Az iteratív „kipróbálás egy dokumentumon → statisztika az egész korpuszon → gyanús esetek megnézése” ciklus sokkal több hibát talált, mint az elsőre megírt kód tesztelése.
- Az automatikus audit hamis riasztásokat is ad (azonos kezdetű bekezdések, lábjegyzetjelek); ezeket kézzel kell átnézni.

---

## 2026-11-25 – F3: baseline RAG és modellválasztás

**Mit csináltunk**
1. Az ágens a `.env` kulcsaival lekérdezte a Groq és a Gemini modellkínálatát (a kulcsokat soha nem írta ki, és fejlécben küldte őket, nem URL-ben), majd 6 jelöltet kipróbált ugyanazzal a magyar JSON-kérdéssel.
2. **RAG nélküli próba – meglepően tanulságos:** a „Mi a TVSZ rövidítés jelentése a BME-n?” kérdésre mindhárom Groq-modell (qwen3.8-27b, gpt-oss-20b, gpt-oss-120b) **hallucinált** („Tudományos és Technológiai Szakosztály”, „Távközlési és Villamosmérnöki Szakképzés”…). Csak a gemini-3.5-flash válaszolt helyesen. → Erős motiváció a RAG-ra, a beszámolóba is bekerül.
3. **Döntés:** generáló = `groq:qwen/qwen3.8-27b` (közepes méret, ~0,4 s), tartalék: `groq:openai/gpt-oss-120b` → `gemini:gemini-3.5-flash`; bíró = `gemini:gemini-3.5-flash` (másik szolgáltató, másik modellcsalád).
4. **Korlát:** a Groq free tier modellenként **8000 token/perc** → egy RAG-hívás ~2–3k token, kb. 3 kérdés/perc. A Gemini „latest” aliasai a próbakor 503-at adtak (túlterhelés). → Lemezes LLM-gyorsítótár, újrapróbálkozás és tartalék lánc.
5. Megvalósítás: BM25 (bm25s + Snowball Hungarian, stopszavak, a tárgykódok egy tokenként), dense (`BAAI/bge-m3` + FAISS IndexFlatIP), RRF (k=60), LLM-kliens (Groq / Gemini / lokális OpenAI-kompatibilis), válaszgenerálás `[S1]` jelölésekkel és szó szerinti idézetekkel, generálás utáni idézet-ellenőrzés (rapidfuzz), CLI (`scripts/ask.py`).
6. A rendszerprompt verziózott fájlban van: `prompts/answer_v1.md`.
7. **Első végponttól végpontig tartó próba** (4 kérdés), minden válasz helyes, ellenőrzött idézettel:
   - „Mennyibe kerül a harmadik vizsga?” → 4500 Ft [TJSZ 2. sz. melléklet 1. § (1)] + [TVSZ 123. § (6)]: a modell két dokumentumot kapcsolt össze, és mindkét idézet 100%-os egyezésű.
   - Szleng („bebukom a zh-t … aláírás”) → TVSZ 114. § (3)–(4), a dense keresés találta meg, a BM25 nem.
   - Angol kérdés → angol válasz magyar forrásidézettel (BSc ZV-szabályzat 2. pont: 173 kredit).
   - Korpuszon kívüli kérdés (menza nyitvatartása) → helyes „nem tudom”.

**Akadályok és tanulságok**
- **A bge-m3 indexelés CPU-n 43 percig tartott** (5217 chunk, 8 GB RAM, nincs GPU). A lekérdezés viszont csak ~0,17 s. → Az index offline készül, a HF Space csak a kérdést ágyazza be. Az embeddingmodell-összehasonlítás (E5) drága, ott kisebb modellekkel érdemes kísérletezni.
- A hibrid keresés a mintakérdéseken nem mindig jobb, mint a jobbik egyedi ranker. Ezt az F4 kiértékelése számszerűsíti, a reranker (F5) pedig várhatóan javít rajta.
- A `python-dotenv` `load_dotenv()` paraméter nélkül nem működik stdin-ről futtatott szkriptben (`find_dotenv` AssertionError) → mindig explicit útvonalat adunk meg.

**Tanulság (F1)**
- A „publikus” forrás sem mindig érhető el gépi úton. Érdemes korán ellenőrizni, és pótforrást keresni.
- Az ágens biztonsági korlátai a gyakorlatban is előjöttek: tilt, ha egy hozzáférési korlátot kerülne meg, és ha a felhasználó által odatett fájlt törölne.
