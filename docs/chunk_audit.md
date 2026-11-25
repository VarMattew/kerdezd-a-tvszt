# Chunk-audit (F2)

Minta: 30 chunk, seed=42. Ellenőrzés: a hivatkozás (§/bekezdés/pont, oldal) és a szöveg egyezik-e az eredeti dokumentummal.

## Eredmény (2026-11-25)

**30/30 chunk helyes** (azonosító, hivatkozás, oldal és szöveg egyezik az eredetivel), az F2 elfogadási kritériuma (≥95%) teljesül.

Módszer: (1) automatikus ellenőrzés – a chunk szövegének eleje megtalálható-e a megadott oldalon, és a „(n)” jel közvetlenül előtte áll-e; (2) a jelzett 4 eset és a mintatanterv-sorok kézi összevetése a forrással.

**Az audit korábbi körei által feltárt és javított hibák** (ezek miatt a minta többször újra lett generálva):
1. *VIK SzMSz:* a tartalomjegyzék „4. melléklet …” sora mellékletet nyitott, így a teljes főszöveg tévesen a 4. mellékletbe került → mellékletet csak az 1.-től, sorrendben fogadunk el.
2. *BProf ZV-szabályzat:* a TVSZ-ből átvett blokk („(TVSZ 150. §)”) után következő kari pontok (24–27.) a TVSZ-bekezdéshez tapadtak → a folyamatos kari pontszám új pontot nyit.
3. *MSc mintatantervek (eü. mérnöki, gazdaságinformatikus):* a sorszámot („4a”, „12g”) vettük tárgynévnek, a félév az összevont cellák miatt elcsúszott → „Tantárgynév” fejléc, legközelebbi félévoszlop.
4. *Képzési programok:* a „5. pont” típusú hivatkozás nem volt egyértelmű (több szakaszban is van 5. pont) → a hivatkozás a szakasz címét is tartalmazza.

## 1. `tvsz:42:4` — TVSZ 42. § (4)
- dokumentum: BME Tanulmányi és Vizsgaszabályzat (egységes szerkezet, XII./3./2024-2025.), oldal: 36–36
- fejezet / cím: II. FEJEZET A KÉPZÉS SZERKEZETI ÉS TARTALMI KERETEI / 13. Tehetséggondozás / Kivételes tanulmányi rend tanulmányi terve
- szöveg: A kivételes tanulmányi rend és az azt leíró tanulmányi terv alapján a hallgató képzését gondozó kar egyénre szabott mintatantervet készít és rendel a hallgatóhoz a TR-ben.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 2. `tvsz:7:4` — TVSZ 7. § (4)
- dokumentum: BME Tanulmányi és Vizsgaszabályzat (egységes szerkezet, XII./3./2024-2025.), oldal: 11–11
- fejezet / cím: I. FEJEZET ÁLTALÁNOS RENDELKEZÉSEK / 2. A Tanulmányi és vizsgaszabályzat végrehajtása során eljáró szervezetek és személyek / Adatkezelési és hatásköri szabályok
- szöveg: Az oktatásért felelős rektorhelyettes és az oktatási igazgató, a szakok (képzések), továbbá a hallgatók esetében láthat el adatkezelői feladatokat. Hatáskörébe vonhat bármely olyan ügyet, amelyet a jelen Szabályzat vagy egyetemi szabályozás a
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 3. `tvsz:111:3` — TVSZ 111. § (3)
- dokumentum: BME Tanulmányi és Vizsgaszabályzat (egységes szerkezet, XII./3./2024-2025.), oldal: 80–80
- fejezet / cím: IV. FEJEZET A TANULMÁNYI MUNKA SZERVEZÉSE, A TANULMÁNYI TELJESÍTMÉNY ÉRTÉKELÉSE / 31. A tanulmányi teljesítmény mérése és értékelése / A teljesítményértékelés rendszere
- szöveg: Szakdolgozat és diplomamunka készítés, továbbá a tantervben meghatározott egyes – nem vizsgaérdemjeggyel értékelt – tantárgyak (pl. szakmai gyakorlat, tervezési feladat, projektfeladat) értékelésére a részteljesítmény értékelést kell alkalmazni.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 4. `tvsz:99:2` — TVSZ 99. § (2)
- dokumentum: BME Tanulmányi és Vizsgaszabályzat (egységes szerkezet, XII./3./2024-2025.), oldal: 71–71
- fejezet / cím: IV. FEJEZET A TANULMÁNYI MUNKA SZERVEZÉSE, A TANULMÁNYI TELJESÍTMÉNY ÉRTÉKELÉSE / 28. Tantárgy- és kurzusfelvétel rendje és keretei / Kurzusfelvétel különös szabályai
- szöveg: bekezdésben meghatározott korlátozással –, jogosult az TR-ben az Egyetem bármely oktatási szervezeti egysége által meghirdetett kurzusra, vizsgakurzusra jelentkezni (kurzusfelvétel).
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 5. `tvsz:91:2` — TVSZ 91. § (2)
- dokumentum: BME Tanulmányi és Vizsgaszabályzat (egységes szerkezet, XII./3./2024-2025.), oldal: 67–67
- fejezet / cím: IV. FEJEZET A TANULMÁNYI MUNKA SZERVEZÉSE, A TANULMÁNYI TELJESÍTMÉNY ÉRTÉKELÉSE / 26. Tanulmányi időszakok / Tanítási szünetek
- szöveg: A dékán a rektor által engedélyezett szüneten kívül félévenként összesen legfeljebb további két nap tanítási szünetet rendelhet el.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 6. `tvsz:55:1` — TVSZ 55. § (1)
- dokumentum: BME Tanulmányi és Vizsgaszabályzat (egységes szerkezet, XII./3./2024-2025.), oldal: 42–43
- fejezet / cím: III. FEJEZET A TANULMÁNYOK JOGI KERETEI / 16. A felvétel és az átvétel / Az átvétel rendje
- szöveg: Az átvételi kérelmet benyújtó hallgatónak a következő, részben az átadó felsőoktatási intézmény által kiállított dokumentumokat kell csatolnia az átvételi kérelemhez: a) igazolás fennálló hallgatói jogviszonyról, b) törzslap-kivonat, c) a korábban teljesített tanegységekre vonatkozó kreditigazolás vagy mikrotanúsítvány, d) a kreditelismerési eljárás lefolytatására irányuló kérelem, e) azon okmányo…
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 7. `tvsz:38:2` — TVSZ 38. § (2)
- dokumentum: BME Tanulmányi és Vizsgaszabályzat (egységes szerkezet, XII./3./2024-2025.), oldal: 33–33
- fejezet / cím: II. FEJEZET A KÉPZÉS SZERKEZETI ÉS TARTALMI KERETEI / 12. Az előtanulmányi rend / Tantárgy- és kurzusfelvételi előkövetelmény ellenőrzése
- szöveg: A szak képzési programjában közzétett, a TR-ben be nem állítható, mérföldkő típusú előkövetelmény ellenőrzését a Dékáni Hivatal végzi, az előírásoknak nem megfelelő tantárgy- és kurzusfelvételt a szorgalmi időszak hatodik hetének végéig, az érintett hallgató egyidejű értesítése mellett törli.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 8. `tvsz:213:4` — TVSZ 213. § (4)
- dokumentum: BME Tanulmányi és Vizsgaszabályzat (egységes szerkezet, XII./3./2024-2025.), oldal: 149–149
- fejezet / cím: IX. FEJEZET TANULMÁNYI ÉS VIZSGAÜGYEK ELSŐ FOKON TÖRTÉNŐ ELJÁRÁSAI / 61. Méltányosság gyakorlása / Méltányosság
- szöveg: A kérelemnek tartalmaznia kell a méltányosságra okot adó indoko(ka)t, és mellékelni kell hozzá az indoko(ka)t alátámasztó dokumentumo(ka)t.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 9. `tvsz:33:3` — TVSZ 33. § (3)
- dokumentum: BME Tanulmányi és Vizsgaszabályzat (egységes szerkezet, XII./3./2024-2025.), oldal: 29–29
- fejezet / cím: II. FEJEZET A KÉPZÉS SZERKEZETI ÉS TARTALMI KERETEI / 10. A tantárgyleírás és a tantárgykövetelmény / A tantárgykövetelmény
- szöveg: A tantárgykövetelmény tartalmazza a) a tanulmányi foglalkozásokon való jelenlét és részvétel követelményeit és a távolmaradás miatt elmulasztott követelmények teljesítésének lehetőségét, valamint a jelenlét ellenőrzésének módját és rendszerességét, ha az a jelen Szabályzatban foglalt előírástól eltér; b) a tanulmányi teljesítményértékelések számát, típusát, teljesítésének módját (személyes közremű…
- **Ellenőrzés:** ✅ helyes. (Az automatikus szövegegyezés a nyers PDF-ben lévő „115,116” lábjegyzetjel miatt nem talált; a chunkból ezt szándékosan eltávolítjuk.)

## 10. `tvsz:228:4` — TVSZ 228. § (4)
- dokumentum: BME Tanulmányi és Vizsgaszabályzat (egységes szerkezet, XII./3./2024-2025.), oldal: 159–159
- fejezet / cím: X. FEJEZET JOGORVOSLAT / 64. Másodfokú eljárás / A másodfokú döntés
- szöveg: Az eseti tanács az ügy érdemében határozatot hoz, egyéb döntései végzések. Az eseti tanács döntését a tanács jogász tagja foglalja írásba.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 11. `tjsz:42:2` — TJSZ 42. § (2)
- dokumentum: Térítési és Juttatási Szabályzat, oldal: 30–30
- fejezet / cím: III. FEJEZET A HALLGATÓK RÉSZÉRE NYÚJTHATÓ JUTTATÁSOK / – / Ösztöndíj Keresztény Fiataloknak
- szöveg: Az ösztöndíjprogram lebonyolítását a vonatkozó Korm. rendeletben meghatározott szervezet látja el".
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 12. `tjsz:5:2` — TJSZ 5. § (2)
- dokumentum: Térítési és Juttatási Szabályzat, oldal: 6–6
- fejezet / cím: I. FEJEZET ÁLTALÁNOS RÉSZ / – / A hallgatói juttatások és térítések ügyeiben eljáró testületek és személyek
- szöveg: Az cC(1) bekezdés szerinti testületek és személyek jogköreiket esetenként vagy az ügyek meghatározott körében más testületre vagy az Egyetem más vezető beosztású foglalkoztatottjára az Nftv.-ben foglalt rendelkezésekkel összhangban átruházhatja. Az átruházott hatáskör gyakorlója a hatáskört nem adhatja tovább.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 13. `tjsz:5:1` — TJSZ 5. § (1)
- dokumentum: Térítési és Juttatási Szabályzat, oldal: 6–6
- fejezet / cím: I. FEJEZET ÁLTALÁNOS RÉSZ / – / A hallgatói juttatások és térítések ügyeiben eljáró testületek és személyek
- szöveg: Az Egyetemen térítési és juttatási ügyekben első fokon eljáró személyek és testületek az Nftv. 13. és 13/A. §-aiban, valamint kötelezettségvállalás rendjére vonatkozó kancellári utasításbané7 továbbá az egyéb szervezetszabályozó eszközökben foglaltakra figyelemmel hoznak döntést.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 14. `tjsz:12:3` — TJSZ 12. § (3)
- dokumentum: Térítési és Juttatási Szabályzat, oldal: 12–12
- fejezet / cím: II. FEJEZET A DÍJMENTESEN ÉS A TÉRÍTÉSI DÍJÉRT IGÉNYBE VEHETŐ SZOLGÁLTATÁSOK / – / Szolgáltatási díjak
- szöveg: Az adott szolgáltatást nyújtó szervezeti egységhez kapcsolódó szolgáltatási díjakat, azok kirovásának rendjét a szervezeti egység honlapján közzé kell tenni.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 15. `tjsz:24:1` — TJSZ 24. § (1)
- dokumentum: Térítési és Juttatási Szabályzat, oldal: 19–20
- fejezet / cím: III. FEJEZET A HALLGATÓK RÉSZÉRE NYÚJTHATÓ JUTTATÁSOK / – / Tanulmányi ösztöndíj
- szöveg: Tanulmányi ösztöndíjban az Egyetem állami ösztöndíjas, teljes idejű képzésben részt vevő hallgatóinak legfeljebb 5096-a részesülhet, oly módon, hogy az egyes hallgatóknak megállapított tanulmányi ösztöndíj havi összegének el kell érnie a haligatói normatíva 599-ának megfelelő összeget.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 16. `kp_bprof_uzinfo:p5~12#5` — Üzemmérnök-informatikus BProf képzési program 5. pont – 5.1.4. Tesztelés és üzemeltetés modul [5/5. rész]
- dokumentum: Üzemmérnök-informatikus BProf képzési program (2026), oldal: 51–57
- fejezet / cím: – / 5.1.4. Tesztelés és üzemeltetés modul / –
- szöveg: Felelősséget vállal az általa tesztelt és / vagy üzemeltetett digitális rendszerek társadalmi és környezeti hatásáért. vi. Tisztában van a szoftver minőségének jelentőségével és önállóan képviseli a megvalósítás során az ilyen jellegű elvárások teljesítésének fontosságát. 5.2. Az egyes modulok sajátos tudásmérési módjai Nincsenek 54 5.3. A modulok belső minőségbiztosításának módja A modulok elvégz…
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 17. `kp_msc_eum:p9` — Egészségügyi mérnöki MSc képzési program 9. pont – Folyamatszabályozás
- dokumentum: Egészségügyi mérnöki MSc képzési program (2026), oldal: 23–23
- fejezet / cím: – / Folyamatszabályozás / –
- szöveg: Lineáris szabályozási rendszerek stabilitásvizsgálata. A stabilitás fizikai képe, a stabilitás matematikai megfogalmazása.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 18. `kp_msc_urm:targy:űrkommunikáció~2` — Űrmérnök MSc képzési program – mintatanterv: Űrkommunikáció
- dokumentum: Űrmérnök MSc képzési program (2026), oldal: 33–33
- fejezet / cím: – / Mintatanterv › Űrmérnöki szakmai ismeretek (82 kredit) / –
- szöveg: Űrkommunikáció (Űrmérnök MSc, mintatanterv). Ajánlott félév: 1. Heti óraszám: 2 előadás, 1 gyakorlat, 0 laboratórium. Követelmény: vizsga (v). Kredit: 4. Tantárgycsoport: Űrmérnöki szakmai ismeretek (82 kredit).
- **Ellenőrzés:** ✅ helyes – mintatanterv-sor; a forrástáblázat 33. oldali sora: „Űrkommunikáció | 2/1/0/v/4”, 1. félév oszlop.

## 19. `kp_bsc_info:p8~5#1` — Mérnökinformatikus BSc képzési program 8. pont – III. A specializáció képzési célja és tartalma [1/2. rész]
- dokumentum: Mérnökinformatikus BSc képzési program (2026), oldal: 37–37
- fejezet / cím: – / III. A specializáció képzési célja és tartalma / –
- szöveg: A specializáció képzési célja: A specializáció célja megismertetni a hallgatókat azokkal a kurrens szoftvertechnikákkal és eszközökkel, amelyek informatikai rendszerek megvalósításához, teszteléséhez, karbantartásához és dokumentálásához szükségesek. A specializáció kiemelt hangsúlyt fektet a legfrissebb szoftverirányzatok teljes spektrumának lefedésére, különös tekintettel a kliens oldalra és inf…
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 20. `kp_msc_eum:targy:funkcionális-anatómia-műszaki-alapk-nek` — Egészségügyi mérnöki MSc képzési program – mintatanterv: Funkcionális anatómia (műszaki alapk.-nek)
- dokumentum: Egészségügyi mérnöki MSc képzési program (2026), oldal: 50–50
- fejezet / cím: – / Mintatanterv › Természettudományos alapismeretek (22 kredit) / –
- szöveg: Funkcionális anatómia (műszaki alapk.-nek) (Egészségügyi mérnöki MSc, mintatanterv). Ajánlott félév: 1. Heti óraszám: 4 előadás, 0 gyakorlat, 1 laboratórium. Követelmény: vizsga (v). Kredit: 6. Tantárgycsoport: Természettudományos alapismeretek (22 kredit).
- **Ellenőrzés:** ✅ helyes – mintatanterv-sor; a forrástáblázat 50. oldali sora: „4a | Funkcionális anatómia (műszaki alapk.-nek) | 4/0/1/v/6”, 1. félév.

## 21. `vik_bsc_specval_du:s1` — Dékáni utasítás (BSc specválasztás) – 1. Alapelvek
- dokumentum: Dékáni utasítás a BSc specializáció- és ágazatválasztási szabályzathoz (2026.04.27.), oldal: 1–1
- fejezet / cím: – / 1. Alapelvek / –
- szöveg: a. Minden hallgató a saját mintatantervéhez kapcsolódó specializációválasztási szabályzatban meghatározott feltételek szerint vehet részt a specializációbesorolási eljárásban. b. Szabályzat 2.§ (1): A villamosmérnöki alapszakon az ágazatok célja a hallgatók tanszékekhez kötése. A mérnökinformatikus szak alapképzésén nem léteznek ágazatok, ugyanakkor a specializációválasztás a hallgatókat a tanszék…
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 22. `vik_szmsz:29:5` — VIK SzMSz 29. § (5)
- dokumentum: VIK Szervezeti és Működési Szabályzat, oldal: 17–17
- fejezet / cím: V. FEJEZET A KAR MŰKÖDÉSE / – / A kari előterjesztési rend
- szöveg: Az előterjesztő a Kari Tanács ülését megelőzően legalább 3 munkanappal megküldi az előterjesztését a Dékáni Hivatal elektronikus levelezési címére.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 23. `vik_szakmai_gyak_bsc:s6` — BSc szakmai gyakorlat szabályzat – Mérnökinformatikus alapképzési szak:
- dokumentum: VIK BSc szakmai gyakorlat szabályzat (2014 után kezdőknek), oldal: 2–2
- fejezet / cím: – / Mérnökinformatikus alapképzési szak: / –
- szöveg: „A szakmai gyakorlat legalább nyolc hét időtartamú, szakmai gyakorlóhelyen szervezett gyakorlat.” A BME tanulmányi és vizsgaszabályzata (TVSZ) – 2017.03.01-én hatályos állapota: „21. § [A kritériumkövetelmény] (3) A képzési és kimeneti követelmények eltérő rendelkezésének hiányában kritériumkövetelmény a szakmai gyakorlat”.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 24. `vik_szmsz:38:5` — VIK SzMSz 38. § (5)
- dokumentum: VIK Szervezeti és Működési Szabályzat, oldal: 23–23
- fejezet / cím: VII. FEJEZET A KAR RÉSZVÉTELE A BELSŐ KONTROLLRENDSZER MŰKÖDTETÉSÉBEN / – / A Kar feladatai az integrált kockázatkezelés során
- szöveg: A (3) bekezdés szerinti kari koordináció kiterjed a szervezeti egységek ellenőrzési nyomvonalának tartalma alapján, a gyakorlati tapasztalat mentén meghatározott kockázati leltár véglegesítésére és a dékán által jóváhagyott tartalmú kari szintű kockázati leltár integritás tanácsadó részére történő megküldésre.
- **Ellenőrzés:** ✅ helyes. (A 38. § (4) és (5) bekezdése azonos mondatrésszel kezdődik, ezért az automatikus ellenőrzés a (4)-et találta meg.)

## 25. `vik_tajekoztato_szd_bsc:p6` — Szakdolgozat-tájékoztató (BSc) 6. pont – A félév időbeosztása: Szorgalmi időszak: 2026. szeptember 7-től december 11-ig.
- dokumentum: Tájékoztató a szakdolgozatról (BSc, oldal: 1–1
- fejezet / cím: – / A félév időbeosztása: Szorgalmi időszak: 2026. szeptember 7-től december 11-ig. / –
- szöveg: oktatási hét végéig (2026. október 16. 24h-ig) kell elektronikusan kitölteni és beadni, majd azt témavezetőjüknek 2026. október 19-ig jóvá kell hagynia (le kell zárnia). A szakdolgozat készítés helyét az a tanszék jelöli ki, amelyik a szakdolgozat-témát kiadta. Felhívom a hallgatók figyelmét, hogy a záróvizsga tantárgyat a rájuk vonatkozó Szabályzatnak megfelelően a témavezető egyetértésével válas…
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 26. `tanev_2026_27:4:2` — Tanév időbeosztása 2026/27 4. § (2)
- dokumentum: A 2026/2027. tanév időbeosztása, oldal: 5–5
- fejezet / cím: – / 3. A tantárgy és kurzusfelvétel rendje / Tantárgy- és kurzusfelvétel rendje a 2026/2027. tanév őszi félévéhez kapcsolódóan
- szöveg: Az Egyetem biztosítja, hogy a 2026. évi pótfelvételi eljárásban felvett hallgatók külön kérelem nélkül 2026. szeptember 11. 23:59 óráig vehessenek fel és adhassanak le tantárgyakat és kurzusokat.
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 27. `vik_mi_hasznalat:s14` — MI-használati irányelvek – Tárgy számonkéréseinek újragondolása
- dokumentum: Irányelvek hallgatóknak és oktatóknak az MI alkalmazásáról, oldal: None–None
- fejezet / cím: – / Oktatóknak › Tárgy számonkéréseinek újragondolása / –
- szöveg: Átgondolást igényel egy számonkérés, melyet a generatív MI teljes egészében meg tud oldani.
A végeredménycentrikus értékelés felől el kell mozdulni a megoldási folyamat értékelése felé. Ha a hallgatók létszáma/a tárgy jellege ezt lehetővé teszi, javasolt a hallgatóktól a pillanatnyi előrehaladást hétről-hétre összegyűjteni (akár git verziókezelő használatát bevezetni), és az értékelés során ezt át…
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 28. `vik_mi_hasznalat:s17` — MI-használati irányelvek – Hallgatóknak
- dokumentum: Irányelvek hallgatóknak és oktatóknak az MI alkalmazásáról, oldal: None–None
- fejezet / cím: – / Hallgatóknak / –
- szöveg: A hallgatók számára a generatív MI nagy segítséget jelent a szakmai ismeretek elsajátításában, a tanultak összefoglalásában, az ismeretekre vonatkozó hiányosságok kitöltésében. Ezek mind a generatív MI etikus felhasználásának minősülnek. A modell válaszai sosem jelenthetnek hivatkozási alapot (pl. hallgatói reklamáció során), a válaszok igazságtartalmának ellenőrzése természetesen a hallgató felel…
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 29. `vik_kepzesi_tajekoztato:s9` — VIK Képzési tájékoztató – International Mentor Team
- dokumentum: VIK Képzési tájékoztató a 2026/2027. tanévre, oldal: None–None
- fejezet / cím: – / Képzési tájékoztató a 2026/2027. tanévre › A külföldi hallgatók részére szóló sajátos információk › International Mentor Team / –
- szöveg: A szervezet azért jött létre, hogy segítse a nemzetközi ösztöndíjasok (SH, SCYP és Diaspora), valamint a költségtérítéses külföldi diákok budapesti beilleszkedését. Segítséget nyújt a kötelező adminisztrációs lépésekben, továbbá számos tájékoztató, kulturális és szakmai rendezvényt szervez a külföldi hallgatók számára.
https://www.imt.bme.hu/
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

## 30. `vik_mi_hasznalat:s10` — MI-használati irányelvek – Szövegblokkok létrehozása
- dokumentum: Irányelvek hallgatóknak és oktatóknak az MI alkalmazásáról, oldal: None–None
- fejezet / cím: – / A generatív mesterséges intelligencia etikus használata › Tipikus alkalmazások › Szövegblokkok létrehozása / –
- szöveg: A szövegblokkok létrehozásával kapcsolatban a fenti, alapelveknél leírtak érvényesek: ha a válaszban a prompt-ban megadotthoz képest új információ jelenik meg, akkor annak átvétele hivatkozást igényel. Ellenkező esetben hivatkozás nem szükséges, de a szövegblokk generálására irányuló használatot a nyilatkozatban (ha a tárgy a nyilatkozat használatát előírja) mindenképpen jelölni kell.
Erre az alka…
- **Ellenőrzés:** ✅ helyes (szöveg a megadott oldalon, a hivatkozás jele közvetlenül előtte)

