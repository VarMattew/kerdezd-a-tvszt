"""A feldolgozó (F2) egységtesztjei: szövegtisztítás, szerkezetfelismerés, hivatkozások."""
import json
from pathlib import Path

import pytest

from vikrag.ingest.build import find_refs, ocr_quality, split_long, unit_citation, unit_id
from vikrag.ingest.pdf_lines import Line
from vikrag.ingest.structure import join_lines, parse

CHUNKS = Path(__file__).resolve().parents[1] / "data" / "processed" / "chunks.jsonl"


def L(text, bold=False, page=4, y=0.0):
    # alapértelmezés: nem az 1. oldal (ott az egységek előtti félkövér sorok a dokumentum címét adják)
    return Line(text=text, page=page, x=70, y=y, size=12, bold=bold)


def test_join_lines_dehyphenates_but_keeps_compounds():
    assert join_lines(["legalább tizennyolc kredittel rendelke-", "zik; és"]) == "legalább tizennyolc kredittel rendelkezik; és"
    assert join_lines(["specializáció-", "és ágazatválasztás"]) == "specializáció- és ágazatválasztás"


def test_parse_paragraph_structure():
    lines = [
        L("III. FEJEZET", bold=True), L("A TANULMÁNYOK JOGI KERETEI", bold=True),
        L("16. A felvétel és az átvétel", bold=True),
        L("53. § [ A felvétel jogi keretei ]", bold=True),
        L("(1) A felvétel feltételeit a Felvételi Szabályzat határozza meg."),
        L("(2) A felvételt nyert jelentkező számára az Egyetem köteles"),
        L("biztosítani a beiratkozás lehetőségét."),
        L("54. § [ Az átvétel feltételei ]", bold=True),
        L("(1) A kérelmező átvehető, ha"),
        L("a) legalább 2,75 átlaggal rendelkezik."),
    ]
    units = parse(lines)
    assert [(u.paragraph, u.subsection) for u in units] == [("53", "1"), ("53", "2"), ("54", "1")]
    u = units[1]
    assert u.chapter == "III. FEJEZET A TANULMÁNYOK JOGI KERETEI"
    assert u.section == "16. A felvétel és az átvétel"
    assert u.paragraph_title == "A felvétel jogi keretei"
    assert u.text().endswith("biztosítani a beiratkozás lehetőségét.")
    assert "a) legalább 2,75" in units[2].text()  # a felsorolás a bekezdésen belül marad
    assert unit_id("tvsz", u, 1) == "tvsz:53:2"
    assert unit_citation("TVSZ", u) == "TVSZ 53. § (2)"


def test_parse_numbered_items_without_paragraphs():
    lines = [
        L("A SZAKDOLGOZAT", bold=True, page=2),
        L("2. A Szakdolgozat-készítés a specializációhoz rendelt tantárgy.", page=2),
        L("(TVSZ 138. §)", page=2),
        L("(1) A hallgatónak szakdolgozatot kell készítenie.", page=2),
    ]
    units = parse(lines)
    assert unit_id("zv", units[0], 0) == "zv:p2"
    assert unit_citation("BSc ZV", units[1]) == "BSc ZV [TVSZ 138. §-hoz] (1)"


def test_faculty_item_after_embedded_tvsz_block_starts_new_item():
    lines = [
        L("23. A záróvizsga két tantárgyból áll."),
        L("(TVSZ 150. §)"),
        L("(3) A záróvizsga-tantárgyakat a tanterv határozza meg."),
        L("24. Az első tantárgy vizsgájára a záróvizsga-időszak előtt kerül sor."),
    ]
    units = parse(lines)
    assert [(u.item, u.embedded_tvsz, u.subsection) for u in units] == [("23", "", ""), ("", "150", "3"), ("24", "", "")]


def test_split_long_respects_limit():
    text = " ".join(f"{i}. pont: " + "szöveg " * 40 + "vége;" for i in range(1, 15))
    parts = split_long(text)
    assert len(parts) > 1 and all(len(p) <= 1900 for p in parts)
    assert " ".join(parts).split() == text.split()


def test_find_refs_internal_external_and_tvsz():
    t = "az 53. § (3) bekezdésben foglaltak, az Nftv. 39. § (1) bekezdés és a (4) bekezdés szerint"
    refs = find_refs(t, "tvsz", True, "55")
    assert ("tvsz", "53", "3") in refs
    assert not any(p == "39" for _, p, _ in refs)
    assert ("tvsz", "55", "4") in refs
    assert ("tvsz", "123", "6") in find_refs("a TVSZ 123. § (6) bekezdés szerint", "tjsz", True, "1")


def test_ocr_quality_separates_text_from_noise():
    assert ocr_quality("A hallgatók különeljárási díjat kötelesek fizetni az alábbi esetekben") > 0.8
    assert ocr_quality("2REzfDBos zss 8 andsű gúas a nb EB mm AFORZzZHRORS 253g s -ő-E SS") < 0.55


@pytest.mark.skipif(not CHUNKS.exists(), reason="a chunks.jsonl még nincs legyártva")
def test_built_corpus_sanity():
    chunks = [json.loads(line) for line in CHUNKS.open(encoding="utf-8")]
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))
    by_id = {c["chunk_id"]: c for c in chunks}
    c = by_id["tvsz:54:4"]
    assert c["citation"] == "TVSZ 54. § (4)" and "2,75" in c["text"]
    assert c["paragraph_title"] == "Az átvétel feltételei"
    assert any(x.get("kind") == "curriculum" for x in chunks)
    assert all(len(c["text"]) <= 1900 for c in chunks)
