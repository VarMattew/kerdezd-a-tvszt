# Kérdezd a TVSZ-t! (`kerdezd-a-tvszt`) – Projektterv

> Repó: https://github.com/VarMattew/kerdezd-a-tvszt

> BME „AI in Practice” – félévközi feladat, 17. téma: *RAG assistant for university regulations*
> Utolsó frissítés: 2026-11-12 · **Határidő: 2026. december 7.** (kb. 3,5 hét)

---

## 0. Feladat és saját pontosítások

**Eredeti kiírás:** Chatbot a TVSZ, a kari szabályzatok és a nyilvános tárgyoldalak fölé, amely **a pontos bekezdést idézi**. Kiértékelő halmaz legalább 50 kérdéssel, a **retrieval és a válasz pontosságának** riportálásával. Adatforrás: nyilvános BME-dokumentumok.

**Szűkítés (saját döntés):**
- **Kizárólag a VIK-re érvényes szabályozás**: az egyetemi TVSZ (VIK-en is hatályos), a VIK kari szabályzatai és kiegészítései, a VIK-es szakok dokumentumai, valamint a VIK-es tárgyadatlapok.
- Más karok saját dokumentumai **nem** kerülnek be. A TVSZ-nek azokat a rendelkezéseit, amelyek kifejezetten más karra vonatkoznak, metaadattal jelöljük, és alapértelmezésként kiszűrjük.

**Leadandók:**
| # | Leadandó | Megvalósítás |
|---|---|---|
| 1 | Publikus Git repó | GitHub |
| 2 | Telepített URL | **Hugging Face Spaces** (Gradio) |
| 3 | README a használatról | `README.md` |
| 4 | Tapasztalatok, tanulságok (használt copilotok és ágensek, kulcsfontosságú promptok, kézi javítások) | `docs/NAPLO.md`, **az első naptól folyamatosan vezetve** |
| 5 | (opcionális) 3 perces demóvideó | a félév végén |

**Munkamód:** egy fő és Claude Code mint fejlesztőágens. Az ágenssel való közös munka dokumentálása maga is a feladat része (lásd 4. pont), ezért a naplót nem a végén rakjuk össze, hanem menet közben vezetjük.

---

## 1. Architektúra (az órai RAG-diasorra építve)

A diasor ívét követjük: naive → advanced → (könnyített) modular RAG. A második rész gyakorlati elemei (hibrid keresés + RRF, RAG-triád, reranking / lost in the middle) mind beépülnek.

```
                 ┌──────────────────────── OFFLINE (indexelés) ────────────────────────┐
 PDF / HTML ──►  │ letöltés ─► szerkezetfelismerő parser ─► bekezdés-chunkok + metaadat │
 (VIK + TVSZ)    │      ─► dúsítás (kontextusfejléc, kereszthivatkozás-gráf)            │
                 │      ─► BM25-index (magyar lemmatizálás)  +  dense index (FAISS)     │
                 └──────────────────────────────────────────────────────────────────────┘

                 ┌──────────────────────── ONLINE (kérdés) ────────────────────────────┐
 kérdés ──► [1] lekérdezés-feldolgozás: szleng-/rövidítésszótár, LLM-es átírás, routing
        ──► [2] hibrid keresés: BM25 top-50 ∥ dense top-50 ──► RRF (k=60)
        ──► [3] cross-encoder reranking ──► küszöbös zajszűrés ──► top 3–5
        ──► [4] kontextusbővítés: a hivatkozott §-ok bevonása (kereszthivatkozás-gráf)
        ──► [5] generálás kötött hivatkozásformátummal + szó szerinti idézettel
        ──► [6] hivatkozás-ellenőrzés (az idézet tényleg ott van?) ──► válasz / „nem tudom”
                 └──────────────────────────────────────────────────────────────────────┘
```

### 1.1 Indexelés (dia: *Indexing, Optimizing Indexing*)

**Granularitás:** a chunk a **bekezdés**: `§ → (bekezdés)`, ahol a felsorolás (`a), b) …` pontok) a bekezdésen belül marad. Ez a pontos idézés alapja. Ha egy bekezdés túl hosszú (kb. 400 token fölött), pontonként tovább bontjuk, a bekezdés bevezető mondatát pedig minden darab elé odaírjuk.

**Hierarchikus metaadat** (a dia ajánlása szerint):
```json
{
  "chunk_id": "tvsz:56:9:b",
  "doc_id": "tvsz",
  "doc_title": "BME Tanulmányi és Vizsgaszabályzat",
  "doc_version": "2022-09-28 egységes szerkezet",
  "chapter": "III. FEJEZET A TANULMÁNYOK JOGI KERETEI",
  "section": "17. A hallgatói jogviszony létrejötte, beiratkozás és a regisztráció",
  "paragraph": "56. §",
  "paragraph_title": "A beiratkozás",
  "subsection": "(9)",
  "point": "b)",
  "page": 41,
  "source_url": "https://...",
  "scope": "egyetemi | VIK | szak:<név> | tárgy:<kód>",
  "citation": "TVSZ 56. § (9) b)",
  "text": "..."
}
```

**Kontextusfejléc a beágyazáshoz:** a beágyazott (embedded) szöveg elé odaírjuk a hierarchiát, például: `TVSZ › III. fejezet › A beiratkozás › 56. § (9)`. A rövid bekezdések („A (4) bekezdés szerinti kérelem ügyében a DTB jár el.”) e nélkül értelmetlenek volnának.

**Dense index:** FAISS `IndexFlatIP`. A korpusz várhatóan néhány ezer chunk, ennél a méretnél nincs szükség ANN-re (HNSW/PQ). Ezt a beszámolóban indokoljuk, a dia ANN-részére hivatkozva.

#### ⚠️ Feldolgozási buktatók (a TVSZ-PDF alapján)
**Aktuális forrás:** `data/raw/tvsz/BME_TVSZ.pdf`. Ez a XII./3./2024-2025. sz. szenátusi határozattal egybeszerkesztett változat, digitálisan aláírva 2025-07-16-án; 181 oldal, kb. 290 §.

1. ~~A bekezdésszámok hiányoznak a szövegrétegből~~ → **Az új verzióban megoldva:** a „(1)”, „(1a)” stb. jelölések benne vannak a szövegben (kb. 1250 bekezdéskezdet), így a bekezdések regexszel felismerhetők. A régi, 2022-es PDF-ben még csak rajzolt Word-számozás volt. Ez bekerül a naplóba is, mint tanulság. **Figyelni kell a beszúrt bekezdésekre** („(1a)”, „55/A. §”); az azonosítóséma ezeket is kezeli: `tvsz:55/A:1a`.
2. **A lábjegyzetszámok a szövegbe keverednek** („(1) 168, 169, 170A hallgatói jogviszony…”). A **betűméret** (kb. 7 pt vs. 12 pt) alapján kiszűrhetők. A lábjegyzetek („Módosította a … határozat. Hatályos …”) értékes **hatályossági metaadatok**, ezeket nem eldobjuk, hanem elmentjük.
3. Fejléc/lábléc (oldalszám), elválasztott szavak („regisztrá-\nció”), tartalomjegyzék → normalizálás, illetve kiszűrés.
4. A szöveg más §-okra hivatkozik („az 53. § (3) bekezdésben foglaltak szerint”) → regexszel kinyerjük, ezekből lesz a **kereszthivatkozás-gráf**.

### 1.2 Adatmódosítás / dúsítás (dia: *Data Modification*)
- **Belső dúsítás (internal augmentation):** chunkonként LLM-mel generált **2–3 hipotetikus hallgatói kérdés** (HyQE-szerű), amelyeket a dense indexben a chunkhoz kötünk. Ez **ablációs kísérlet**: ki/be kapcsolva mérjük.
- **Külső dúsítás:** egy kézzel összeállított **fogalomtár / szinonimaszótár** (`zh` → zárthelyi dolgozat, `Neptun` → TR / tanulmányi rendszer, `KTH` → Központi Tanulmányi Hivatal, `vizsgakurzus`, `aláírás` → félévközi követelmény teljesítése, `IV` → ismételt vizsga stb.). Ez a hallgatói szleng és a jogi szöveg közti szakadékot hidalja át.

### 1.3 Lekérdezés-feldolgozás (dia: *Query manipulation*)
- **Szótáralapú kibővítés (query expansion)** az 1.2-es fogalomtárral (olcsó, determinisztikus).
- **LLM-es átírás (prompt-based rewriting):** a hallgatói kérdést szabályzati nyelvre fordítja, és többlépéses kérdésnél részkérdésekre bontja (*Recursive Search*).
- **Routing** (dia: *Modular RAG – Router*): könnyű osztályozás, amely eldönti, hogy a kérdés szabályzati, tárgyspecifikus (tárgykód / tárgynév felismerése) vagy a korpuszon kívüli. A tárgyspecifikus kérdéseknél metaadat-szűrés a tárgyadatlapokra.
- **Angol kérdések:** átírás magyarra, vagy közvetlen keresés többnyelvű embeddinggel. Ez ablációs kísérlet.

### 1.4 Keresés és rangsorolás (dia: *Hybrid Search & RRF*)
- **BM25** (`bm25s` vagy `rank_bm25`) **magyar lemmatizálással** (huspacy / `hu_core_news_lg`), vagy olcsóbb változatként Snowball Hungarian szótövezéssel. Mindkettőt mérjük.
- **Dense:** jelölt modellek: `BAAI/bge-m3` (alapértelmezett), `intfloat/multilingual-e5-large`, illetve kisebbek az HF Space CPU-hoz (`multilingual-e5-base`).
- **RRF** `k=60` értékkel (a dia szerint a 20–100 tartomány érdemben nem változtat; ezt egy mini-szenzitivitásvizsgálattal igazoljuk).
- A dia figyelmeztetése szerint akkor nyerünk a fúzióval, ha a két ranker **eltérő módon hibázik**. A BM25 a pontos kifejezésekben és §-számokban erős, a dense a parafrázisokban. Ezt a hibaelemzésben külön megmutatjuk.

### 1.5 Utófeldolgozás (dia: *Re-Ranking, Noise Filtering, Lost in the Middle*)
- **Cross-encoder reranker** az RRF top-30 jelöltjén: `BAAI/bge-reranker-v2-m3` (többnyelvű). CPU-s Space-en, ha lassú, kisebb modell vagy kevesebb jelölt.
- **Zajszűrés:** reranker-pontszám küszöbe. Ha egyetlen jelölt sincs a küszöb felett, **„nem találtam rá szabályt”** (*Adaptive retrieval*, absztinencia).
- **Csak 3–5 chunk kerül az LLM elé** (lost in the middle), a legrelevánsabb az elejére.
- **Kontextusbővítés a kereszthivatkozás-gráffal** (könnyített *Graph RAG*): ha egy kiválasztott bekezdés más §-ra hivatkozik, a hivatkozott bekezdést is hozzácsatoljuk („kapcsolódó rendelkezés” címkével, legfeljebb +2 chunk).

### 1.6 Generálás (dia: *Generation – Customization, Enhancing*)
- **Rendszerprompt:** csak a megadott kontextusból válaszolhat; minden állítás után kötelező a `[TVSZ 56. § (9)]` formátumú hivatkozás és egy rövid, **szó szerinti idézet**; ha a kontextus nem elég, ezt meg kell mondania.
- **Strukturált kimenet** (JSON: `answer`, `citations[{chunk_id, quote}]`, `confidence`). Így a hivatkozás géppel ellenőrizhető.
- **Hivatkozás-ellenőrzés generálás után:** megnézzük, hogy minden `quote` (normalizálva, fuzzy egyezéssel) tényleg benne van-e a hivatkozott chunkban. Ha nincs, a hivatkozást eldobjuk vagy figyelmeztetéssel jelöljük. (Ez a *Feedback-based enhancing* olcsó változata.)
- A válasz nyelve a kérdés nyelvét követi (magyar/angol).

### 1.7 LLM-szolgáltatók
- **Ingyenes API-k:** **Groq** (pl. Llama / Qwen / GPT-OSS modellek) és **Google Gemini** ingyenes kulcs.
- **Absztrakciós réteg** (`llm/` modul) egységes interfésszel, hogy a szolgáltató konfigurációból cserélhető legyen. **Fallback**: ha az egyik szolgáltatónál rate limitbe futunk, a kérés automatikusan a másikhoz megy.
- **Lokális modellek** (később, erősebb gépen): Qwen családból ~8–9B és ~14B (Ollama vagy vLLM, OpenAI-kompatibilis végponton), így ugyanaz a kód futtatja őket.
- **Gyorsítótár:** minden LLM-hívás (prompt-hash → válasz) lemezre kerül. A kiértékelés így megismételhető, és nem égeti a free tier kvótát.
- A bíró modell (a kiértékelésnél) lehetőleg **más modell legyen, mint a generáló**, hogy csökkentsük az önértékelési torzítást.
- **Modellválasztás (döntés):** „átlagos”, közepes modell. Az F3-ban, a `.env` kulcsokkal lekérdezzük a free tier aktuális modellkínálatát és rate limitjeit, és ez alapján választunk: a **generáló** egy közepes méretű nyílt modell Groqon, a **bíró** egy Flash-szintű Gemini (más szolgáltató, más modellcsalád). Rate limitek: minden hívás gyorsítótárazva; a kiértékelő futtató kérés/perc korláttal és újrapróbálkozással (backoff) dolgozik.
- **Kulcsok:** `.env` (gitignore-olva), a változónevek a `.env.example`-ben.

---

## 2. Adatgyűjtés (VIK-specifikus)

> A pontos dokumentumlistát az 1. fázisban állítjuk össze; az alábbi lista **kiindulási jelöltlista, ellenőrizendő**.
>
> **Kiindulópont:** https://etk.bme.hu/hallgatoknak/szabalyzatok/ (egyetemi szabályzatok gyűjtőoldala; nem teljes, a VIK-es anyagokat a vik.bme.hu és a portal.vik.bme.hu oldalakon kell tovább keresni).
> **Publikus = minden, ami bejelentkezés nélkül elérhető.**

| Kategória | Jelöltek | Formátum | Prioritás |
|---|---|---|---|
| Egyetemi, VIK-en hatályos | TVSZ (**megvan**: 2025-07-16-i egységes szerkezet) | PDF | **P0** |
| Egyetemi, angol | TVSZ angol változata (*Code of Studies*), csak ha van aktuális | PDF | P2 (opcionális) |
| Egyetemi, kapcsolódó | Térítési és juttatási szabályzat (TJSZ), ha a díjas / pót- / IV-kérdésekhez kell | PDF | P1 |
| VIK kari | kari kiegészítő rendelkezések, záróvizsga-szabályok, szakdolgozat- és diplomatervszabályzat, kreditátviteli (KKB) eljárásrend, specializáció-/ágazatválasztás szabályai | PDF/HTML | **P0** |
| VIK szakok | képzési programok, mintatantervek (mérnökinfo, villamosmérnök, üzemmérnök-info; BSc/MSc) | PDF | P1 |
| Tárgyadatlapok | portal.vik.bme.hu tárgyadatlapok (követelmények, kredit, előkövetelmény, értékelés) | HTML | P1 (lásd lent) |
| VIK GYIK / tanulmányi tájékoztatók | ha van nyilvános, szabályzatszerű tartalom | HTML | P2 |

**Gyűjtési elvek:**
- Letöltőszkript (`scripts/fetch.py`) egy `sources.yaml` alapján: URL, dokumentumtípus, scope, letöltés dátuma, SHA-256 hash. Így minden dokumentum reprodukálhatóan visszakereshető.
- Udvarias crawling: `robots.txt` betartása, lassított (rate-limitelt) kérések, saját user-agent. A tárgyadatlapoknál listaoldalról indulunk, nem teljes crawl.
- A nyers fájlok a `data/raw/` mappába kerülnek. Ha a licenc / közzététel kérdéses, a repóba csak a letöltőszkript és a feldolgozott chunkok kerülnek (a HF Space-hez úgyis a kész index kell).
- **Tárgyadatlapok:** a TVSZ-től eltérő parser kell. A chunkok mezőalapúak (`tárgy:VIMIAA01:követelmények`), a hivatkozás formája pedig „Tárgyadatlap VIMIAA01 › Követelmények”.

**Döntések a terjedelemről:**
- **Tárgyadatlapok – fokozatos bővítés, időkorláttal:**
  1. először a fő BSc-szakok (mérnökinformatikus, villamosmérnök) mintatantervének **kötelező tárgyai** (kb. 60–100 tárgy);
  2. ha a scraper egységes HTML-en stabilan fut, **az összes VIK-tárgy** adatlapja is bekerül. Ez a parser megírása után már olcsó, a demóban pedig jól mutat. Az index ettől még kicsi marad (néhány ezer + néhány ezer chunk).
  - Időkorlát: ha a scraper 1 nap alatt nem áll össze, maradunk az 1. lépésnél.
  - A kiértékelő halmaz tárgyadatlapos kérdései (~15%) mindkét esetben ugyanabból a halmazból jönnek, így az eredmények összehasonlíthatók.
- **Angol nyelv:** a korpusz **magyar**. Angol dokumentumot csak akkor vonunk be, ha könnyen elérhető és aktuális (P2). Az angol kérdéseket a többnyelvű embedding és az angol nyelvű válaszgenerálás kezeli, az eredményt a kiértékelésben külön mérjük.

---

## 3. Kiértékelés

Kétféle kiértékelést kombinálunk: **(A) ground truth alapú** (a feladat ezt kéri: retrieval- és válaszpontosság), és **(B) referencia nélküli RAG-triád** (a dia ajánlása, Ragas/TruLens-szerű).

### 3.1 Kiértékelő halmaz (cél: 80–100 kérdés, minimum 50)

| Típus | Leírás | Arány |
|---|---|---|
| Egyszerű tény | egy bekezdésből megválaszolható | ~30% |
| Számadat / határidő | dátum, kreditszám, hányszor, meddig | ~15% |
| Több forrás | TVSZ + VIK-es kiegészítés együtt, vagy két § | ~15% |
| Tárgyadatlap | követelmény, kredit, előkövetelmény | ~15% |
| Hallgatói nyelv | szleng, pontatlan megfogalmazás | ~10% |
| Megválaszolhatatlan | a korpuszban nincs rá szabály → absztinencia | ~10% |
| Angol nyelvű | | ~5% |

**Formátum** (`eval/questions.jsonl`):
```json
{"id": "q017", "question": "Hányszor vizsgázhatok egy tárgyból egy félévben?",
 "type": "numeric", "lang": "hu",
 "gold_chunk_ids": ["tvsz:..."], "gold_answer": "...",
 "answerable": true, "difficulty": "easy", "notes": "..."}
```

**Készítés módja (a beszámolóban leírjuk):**
1. Rétegzett mintavétel a chunkokból (fejezetenként, dokumentumtípusonként).
2. LLM generál kérdésjelölteket és válaszvázlatot.
3. **Kézi ellenőrzés és átírás:** javítás, hallgatói nyelvre fogalmazás, a **lexikai átfedés csökkentése** (ne a bekezdés szavait ismételje a kérdés, mert az a BM25-öt mesterségesen előnyhöz juttatja).
4. A gold chunkok kézi bővítése, ha több bekezdés is megválaszolja.
5. ~10–15 kérdést **teljesen kézzel írunk** (valós hallgatói kérdések mintájára), kontrollcsoportként.
6. **Dev/test felosztás** (pl. 30/70). A hangolás (küszöb, top-k, promptok) csak a dev halmazon történik, a végső számok a test halmazról jönnek.

### 3.2 (A) Retrieval-metrikák (ground truth)
- **Recall@k** (k = 1, 3, 5, 10), **MRR**, **nDCG@10**: bekezdésszinten (szigorú) és §-szinten (laza).
- **Hit rate a végső kontextusban** (a reranking és szűrés után ténylegesen az LLM elé került 3–5 chunk között ott van-e a gold).

### 3.3 (A) Válaszmetrikák (ground truth)
- **Válaszhelyesség:** LLM-bíró pontozási szempontrendszerrel (helyes / részben helyes / helytelen), a gold válaszhoz viszonyítva.
- **Hivatkozási precizitás:** a hivatkozott chunkok közül hány van a gold halmazban.
- **Hivatkozási felidézés (recall):** a gold chunkok közül hányat hivatkozott a modell.
- **Idézethűség:** a szó szerinti idézetek hány százaléka található meg ténylegesen a forrásban (a 1.6-os ellenőrző adja).
- **Absztinencia:** a megválaszolhatatlan kérdéseken a helyes „nem tudom” aránya, a megválaszolhatókon a téves elutasítás aránya.

### 3.4 (B) RAG-triád (a dia szerint, referencia nélkül)
- **Groundedness / Faithfulness:** `G = |V| / |S|` (a válasz állításokra bontva, ezek közül hány támasztható alá a kontextusból).
- **Answer Relevance:** `AR = (1/n) Σ sim(q, q_i)` (a válaszból visszagenerált kérdések hasonlósága az eredeti kérdéshez).
- **Context Relevance:** `CR = releváns mondatok / összes mondat` a kontextusban.
- Megvalósítás: a **Ragas** könyvtárral vagy saját implementációval a dia képletei szerint. A saját változat átláthatóbb, és jobban kezeli a magyar nyelvet.

### 3.5 A bíró validálása (a dia WikiEval-diájának mintájára)
- ~20–25 kérdés válaszát **kézzel is pontozzuk**, és megmérjük az LLM-bíró egyezését (százalékos egyezés / Cohen-kappa).
- Így alátámasztható, hogy az automatikus számok megbízhatók.

### 3.6 Kísérletek / ablációk (a beszámoló gerince)

| # | Kísérlet | Változók |
|---|---|---|
| E1 | Retriever-összehasonlítás | BM25 · dense · hibrid (RRF) · hibrid + reranker |
| E2 | Chunkolás | bekezdésalapú · fix 512 token · rekurzív felosztás |
| E3 | Kontextusfejléc | be / ki |
| E4 | Lemmatizálás a BM25-ben | nincs · Snowball · huspacy |
| E5 | Embedding modell | bge-m3 · e5-large · e5-base |
| E6 | Lekérdezés-feldolgozás | nincs · szótár · LLM-átírás · mindkettő |
| E7 | HyQE-dúsítás | be / ki |
| E8 | Kereszthivatkozás-bővítés | be / ki |
| E9 | top-k az LLM-nek | 3 · 5 · 10 · 20 (lost in the middle) |
| E10 | RRF k | 20 · 60 · 100 |
| E11 | Generáló LLM | Groq-modell(ek) · Gemini · lokális Qwen ~9B · ~14B |

**Prioritás a határidő miatt:** kötelező: E1, E2, E3, E6, E9 (és E11 a két API-modellel). Ha belefér: E4, E5, E7, E8, E10, illetve E11 a lokális modellekkel.

A kísérleteket egyetlen konfigurációvezérelt futtató (`eval/run.py --config configs/e1_hybrid.yaml`) hajtja végre. Az eredmények `results/*.json` fájlokba és egy összesítő táblába kerülnek, ebből készülnek a beszámoló ábrái.

---

## 4. Tapasztalatnapló (leadandó!)

`docs/NAPLO.md`, amelyet minden munkamenet végén frissítünk:
- **dátum / fázis / mit csináltunk**;
- **használt eszközök:** Claude Code (melyik modell, mely funkciók: tervezés, subagentek, böngésző, kódgenerálás), egyéb copilotok;
- **kulcsfontosságú promptok** szó szerint (a fejlesztéshez használt promptok és a rendszer saját promptjai), a promptok verziózva a `prompts/` mappában;
- **mit kellett kézzel javítani** és miért (pl. parserhibák, hibás bekezdésszámozás, rossz gold címkék, hallucinált hivatkozások);
- **tanulságok:** mi működött, mi nem, mi lepett meg.

Ebből áll össze a végén a README „Experiences and lessons learned” fejezete.

---

## 5. Telepítés: Hugging Face Spaces

- **Gradio** alapú Space (CPU basic, ingyenes).
- **Az index offline készül**, és a Space-hez a kész artefaktok kerülnek (chunkok JSONL, FAISS-index, BM25-index). A Space csak a lekérdezés embeddingjét és a rerankinget számolja.
  - Ha a `bge-m3` és a reranker CPU-n túl lassú vagy túl sok memóriát igényel: kisebb embeddingmodell, kevesebb rerank-jelölt, vagy az index/modell külön HF Dataset / Model repóban.
- **API-kulcsok** HF Space *Secrets*-ként (`GROQ_API_KEY`, `GEMINI_API_KEY`), soha nem a repóban.
- **Felület:**
  - chatablak, a válaszban **kattintható hivatkozás-chipekkel**;
  - oldalpanel: a hivatkozott bekezdés teljes szövege, **kiemelt idézettel**, a dokumentum, a verzió és az oldalszám feltüntetésével, valamint link az eredeti PDF-re vagy oldalra;
  - „Hogyan találtam meg?” lenyíló panel: BM25- és dense-rangok, RRF- és reranker-pontszám, és hogy mi került a kontextusba (látványos, és a demóvideóhoz is jó);
  - példakérdések gombjai;
  - figyelmeztetés: „Nem hivatalos tájékoztatás, mindig ellenőrizd az eredeti szabályzatot.”
  - opcionálisan egy „Kiértékelés” fül a fő eredményekkel (táblák, diagramok).
- **Rate limitek** kezelése: gyorsítótár, sorbaállítás, barátságos hibaüzenet.
- **CI:** GitHub Action, amely push után szinkronizálja a repót a Space-szel (vagy a Space közvetlenül a GitHub-repóra mutat).

---

## 6. Repó-struktúra

```
HF/
├── README.md                 # használat, architektúra, eredmények, tanulságok
├── TERV.md                   # ez a fájl
├── docs/
│   ├── NAPLO.md              # ágenses munka naplója (leadandó)
│   └── figures/
├── data/
│   ├── sources.yaml          # dokumentumlista: URL, scope, verzió
│   ├── raw/                  # letöltött PDF/HTML (gitignore-olható)
│   └── processed/chunks.jsonl
├── src/vikrag/
│   ├── ingest/               # fetch, pdf_parser (TVSZ-szerkezet), html_parser (tárgyadatlap)
│   ├── index/                # bm25, dense, crossref_graph
│   ├── retrieve/             # query_proc, hybrid+rrf, rerank, filter
│   ├── generate/             # prompts, citation_check
│   ├── llm/                  # groq, gemini, openai-compatible (lokális), cache
│   └── pipeline.py
├── prompts/                  # verziózott promptok
├── eval/
│   ├── questions.jsonl
│   ├── build_questions.py
│   ├── metrics.py            # recall@k, MRR, nDCG, citation P/R, triád
│   └── run.py
├── configs/                  # kísérleti konfigok
├── results/
├── app.py                    # Gradio (HF Space belépési pont)
├── requirements.txt
└── tests/                    # parser-tesztek (bekezdésszámozás!), metrika-tesztek
```

---

## 7. Ütemterv (félév végéig, december 7.)

| Fázis | Időszak (2026) | Tartalom | Kész, ha… |
|---|---|---|---|
| **F0 – Alapok** | nov. 12. | repó, környezet, NAPLO indul, `sources.yaml` váz | a helyi repó és a környezet kész, az első naplóbejegyzés megvan; a GitHub-repó él |
| **F1 – Adatgyűjtés** | nov. 13–15. | VIK-dokumentumok felkutatása (ETK-oldal, vik.bme.hu, portal) és letöltése | a `sources.yaml` teljes (P0+P1), a nyers fájlok megvannak |
| **F2 – Parser** | nov. 15–18. | TVSZ-parser (bekezdések, lábjegyzetek, kereszthivatkozások), kari dokumentumok és tárgyadatlap-parser | `chunks.jsonl` kész; 30 véletlen chunk kézi ellenőrzése: a §/bekezdés-azonosító ≥95%-ban helyes |
| **F3 – Baseline RAG** | nov. 18–20. | BM25 + dense + RRF + egyszerű generálás, CLI, modellválasztás | végponttól végpontig működik egy kérdésre hivatkozással |
| **F7a – Korai telepítés** | nov. 21. | minimális Gradio-felület a HF Space-en | a publikus URL él (telepítési gondok korán kiderülnek) |
| **F4 – Kiértékelő halmaz** | nov. 20–24. | 80–100 kérdés, dev/test felosztás, metrikakód | `questions.jsonl` kézzel ellenőrizve, baseline-számok megvannak |
| **F5 – Advanced RAG** | nov. 24–28. | reranker, zajszűrés, lekérdezés-feldolgozás, kereszthivatkozás, hivatkozás-ellenőrzés | minden komponens be- és kikapcsolható, mért javulással |
| **F6 – Kísérletek** | nov. 28. – dec. 2. | kötelező kísérletek, RAG-triád, bíró-validálás | eredménytáblák és ábrák |
| **F7b – Végleges felület** | dec. 1–3. | teljes UI (hivatkozás-panel, „Hogyan találtam meg?”, kiértékelés-fül), CI | a végleges URL működik |
| **F8 – Lokális modellek** | ha elérhető az erősebb gép (legkésőbb dec. 3.) | Qwen ~9B / ~14B kiértékelése (E11) | az összehasonlító tábla kész; **opcionális** |
| **F9 – Lezárás** | dec. 4–7. | README, tanulságok, demóvideó (3 perc), tartalék idő | minden leadandó kész |

**Vágási sorrend, ha csúszunk:** F8 → opcionális kísérletek → összes tárgyadatlap (marad a kötelező tárgyakra szűkített halmaz) → HyQE-dúsítás. **Nem vágható:** pontos hivatkozás, ≥50 kérdéses kiértékelés, működő HF Space, napló/README.

---

## 8. Kockázatok

| Kockázat | Hatás | Kezelés |
|---|---|---|
| A bekezdésszámok rekonstrukciója hibás | a pontos hivatkozás, a feladat lényege sérül | elrendezésalapú parser + egységtesztek + kézi minta; ha van DOCX/HTML forrás, azt használjuk |
| Elavult szabályzatverzió | téves válasz | verzió- és dátum-metaadat, a legfrissebb egységes szerkezet beszerzése, a dátum kijelzése a felületen |
| Free tier rate limit | lassú vagy elakadó kiértékelés és demó | gyorsítótár, fallback két szolgáltató között, batch-futtatás éjszaka |
| HF Space CPU / memória | lassú válasz | előre számolt index, kisebb modellek, kevesebb rerank-jelölt |
| Eval-halmaz torzítása (LLM-generált kérdések) | túl optimista számok | kézi átírás, kézzel írt kontrollkérdések, dev/test felosztás |
| LLM-bíró torzítása | megbízhatatlan válaszmetrikák | más bíró-modell, kézi validálás egy mintán |
| Széttagolt VIK-dokumentumok | sok gyűjtőmunka | prioritási sorrend (P0 → P1 → P2), a P2 elhagyható |

---

## 9. Döntések és nyitott kérdések

| # | Kérdés | Állapot |
|---|---|---|
| 1 | Van-e frissebb TVSZ? | ✅ Megvan (2025-07-16, XII./3./2024-2025), a bekezdésszámok benne vannak a szövegrétegben. Gyűjtőoldal: etk.bme.hu/hallgatoknak/szabalyzatok |
| 2 | Mi számít publikusnak? | ✅ Minden, ami bejelentkezés nélkül elérhető |
| 3 | Tárgyadatlapok köre | ✅ Fokozatos: kötelező tárgyak → ha a scraper stabil, az összes VIK-tárgy (2. fejezet) |
| 4 | Angol dokumentumok | ✅ Magyar korpusz; angol dokumentum csak opcionálisan (P2); angol kérdések többnyelvű embeddinggel |
| 5 | Alapértelmezett modellek | ⏳ Közepes modell; az F3-ban a `.env` kulcsokkal választjuk ki (generáló: Groq, bíró: Gemini) |
| 6 | Pontosan mely VIK-es szabályzatok nyilvánosak? | ⏳ F1 |
