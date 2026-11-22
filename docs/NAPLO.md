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
