"""Képzési programok mintatanterv-táblázatai -> tantárgyanként egy rekord.

A táblázatsorokat a PyMuPDF `find_tables` adja; a cellák szövegét a cella-bbox alapján újra kiolvassuk
(`get_textbox`), mert a táblázatkinyerő elhagyja a szóközöket.
Óraszám-formátum: "ea/gy/lab/követelmény/kredit", pl. "2/2/0/v/5".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pymupdf

HOURS_RE = re.compile(r"^(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*([a-zé]{1,2})\s*/\s*(\d+)$")
PAGE_HINT_RE = re.compile(r"\d+\s*/\s*\d+\s*/\s*\d+\s*/\s*[a-zé]{1,2}\s*/\s*\d+|\d+\s*\+\s*\d+\s*/\s*hét")
# B formátum (gazdaságinformatikus BSc, BProf): "Tantárgy neve | Előtanulmányi feltétel | Tárgyfelelős |
# Értékelés módja | Tanóra típusa | Besorolás | Óraszám (2+1/hét) | Kredit", félévenkénti elválasztó sorokkal
HOURS_B_RE = re.compile(r"^(\d+)\s*\+\s*(\d+)\s*/\s*hét$")
EVAL_B = {"koll.": "koll", "gyj.": "gyj", "a.": "a", "f.": "f", "v.": "v"}
SEMESTER_WORDS = {"ELSŐ": "1", "MÁSODIK": "2", "HARMADIK": "3", "NEGYEDIK": "4", "ÖTÖDIK": "5", "HATODIK": "6", "HETEDIK": "7", "NYOLCADIK": "8"}
CODE_RE = re.compile(r"^(?:BME)?[A-Z]{4}[A-Z0-9]{2,5}$")
REQ = {
    "v": "vizsga", "f": "félévközi érdemjegy", "a": "aláírás", "é": "évközi jegy", "s": "szigorlat",
    "koll": "kollokvium (vizsga)", "gyj": "gyakorlati jegy (félévközi érdemjegy)",
}


@dataclass
class Subject:
    code: str
    name: str
    semester: str
    lecture: int
    practice: int
    lab: int
    requirement: str
    credits: int
    group: str
    type: str
    department: str
    page: int
    prereq: str = ""
    responsible: str = ""
    lesson_type: str = ""


def _cell_text(page: pymupdf.Page, bbox) -> str:
    if bbox is None:
        return ""
    t = page.get_textbox(pymupdf.Rect(bbox))
    t = t.replace("­", "")
    t = re.sub(r"(?<=[a-záéíóöőúüű])-\s*\n\s*(?=[a-záéíóöőúüű])", "", t)  # elválasztás: "laborató-\nrium"
    t = re.sub(r"-\s*\n\s*", "-", t)
    return " ".join(t.split())


def extract_subjects(path: str) -> list[Subject]:
    doc = pymupdf.open(path)
    out: list[Subject] = []
    header_map: dict[int, str] = {}
    group_stack: list[str] = []
    b_semester = ""  # B formátum: az aktuális „N. FÉLÉV” elválasztó sor
    for pno, page in enumerate(doc, 1):
        # a find_tables lassú: csak a mintatanterv-oldalakon futtatjuk (van óraszám-mintázat a szövegben)
        if not PAGE_HINT_RE.search(page.get_text()):
            continue
        try:
            # use_layout=False: a PyMuPDF 1.27+ ONNX-elrendezésmodellje lassú és egyes oldalakon szegmentációs
            # hibával összeomlik (kp_msc_ai); a vonalalapú felismerés a mintatanterveken ugyanazt adja
            tables = page.find_tables(use_layout=False).tables
        except Exception:  # noqa: BLE001
            continue
        for tab in tables:
            rows = [[_cell_text(page, c) for c in r.cells] for r in tab.rows]
            if not rows:
                continue
            # fejléc: az első sorok közül az, amelyikben "Tárgykód"/"Tárgynév" van, és utána a félévszámok
            hdr_idx = next(
                (i for i, r in enumerate(rows[:3]) if any(c in ("Tárgynév", "Tárgykód", "Tantárgynév", "Tantárgykód") for c in r)),
                None,
            )
            if hdr_idx is not None:
                header_map = {}
                for i in range(hdr_idx, min(hdr_idx + 2, len(rows))):
                    for j, c in enumerate(rows[i]):
                        if c and c not in ("Szemeszter",):
                            header_map[j] = c
                body = rows[hdr_idx + 1:]
            else:
                body = rows
            for r in body:
                nonempty = [c for c in r if c]
                if not nonempty:
                    continue
                # ── B formátum ──
                hb = next((j for j, c in enumerate(r) if HOURS_B_RE.match(c)), None)
                if hb is None and len(nonempty) <= 2:
                    m = re.match(r"^([A-ZÁÉÍÓÖŐÚÜŰ]+)\s+FÉLÉV", nonempty[0])
                    if m and m.group(1) in SEMESTER_WORDS:
                        b_semester, group_stack = SEMESTER_WORDS[m.group(1)], []
                        continue
                    if nonempty[0].upper().startswith("SPECIALIZÁCIÓ"):
                        group_stack = [re.sub(r"\(\d+\)", "", nonempty[0]).strip()]
                        continue
                if hb is not None:
                    hm = HOURS_B_RE.match(r[hb])
                    after = [c for c in r[hb + 1:] if c]
                    credits = int(after[0]) if after and after[0].isdigit() else 0
                    ev_j = next((j for j, c in enumerate(r) if c in EVAL_B), None)
                    name = re.sub(r"\(\d+\)", "", nonempty[0]).strip()
                    mid = [c for c in r[1:ev_j] if c] if ev_j is not None else []
                    prereq = re.sub(r"\(\d+\)", "", mid[0]).strip() if mid else ""
                    responsible = re.sub(r"\(\d+\)", "", mid[1]).strip() if len(mid) > 1 else ""
                    tail = [c for c in r[(ev_j or 0) + 1: hb] if c]
                    out.append(
                        Subject(
                            code="", name=name, semester=b_semester,
                            lecture=int(hm.group(1)), practice=int(hm.group(2)), lab=0,
                            requirement=EVAL_B.get(r[ev_j], "") if ev_j is not None else "", credits=credits,
                            group=" › ".join(group_stack), type=tail[1] if len(tail) > 1 else "",
                            department="", page=pno, prereq=prereq, responsible=responsible,
                            lesson_type=tail[0] if tail else "",
                        )
                    )
                    continue
                # ── A formátum ──
                hours_j = next((j for j, c in enumerate(r) if HOURS_RE.match(c)), None)
                if hours_j is None:
                    if len(nonempty) == 1 and len(nonempty[0]) > 3 and not nonempty[0].isdigit():
                        label = nonempty[0]
                        # ágazat a specializáció alá kerül, egyébként új csoport
                        if group_stack and ("ágazat" in label.lower() and "/" in label):
                            group_stack = group_stack[:1] + [label]
                        else:
                            group_stack = [label]
                    continue
                h = HOURS_RE.match(r[hours_j])
                col = {lab: j for j, lab in header_map.items()}
                code_col = col.get("Tárgykód", col.get("Tantárgykód"))
                code = r[code_col] if code_col is not None and code_col < len(r) else ""
                code = code.replace(" ", "") if re.fullmatch(r"[A-Z0-9][A-Z0-9 \-]{4,}", code) else ""
                name_col = col.get("Tárgynév", col.get("Tantárgynév"))
                name = r[name_col] if name_col is not None and name_col < len(r) else ""
                if not name or re.fullmatch(r"\d+[a-z]?|[\d/]+[a-z/\d]*", name):  # tartalék: első szöveges cella
                    name = ""
                    for j, c in enumerate(r):
                        if not c or HOURS_RE.match(c) or re.fullmatch(r"[\d\s\-–]+[a-z]?", c) or c in ("↓", "generikus"):
                            continue
                        if c.replace(" ", "") == code or header_map.get(j, "").lower() in ("típus", "tanszék"):
                            continue
                        name = c
                        break
                name = re.sub(r"(?<=[a-záéíóöőúüű])\d+$", "", name).strip()  # lábjegyzetszám a név végén
                # félév: a fejléc ugyanazon oszlopa, vagy (összevont cellák miatt) a legközelebbi számozott oszlop
                sem_re = r"\d+(\s*v\s*\d+)?|őszi|tavaszi"
                semester = header_map.get(hours_j, "")
                if not re.fullmatch(sem_re, semester):
                    near = sorted((abs(j - hours_j), lab) for j, lab in header_map.items() if re.fullmatch(sem_re, lab))
                    semester = near[0][1] if near and near[0][0] <= 2 else ""
                typ = next((r[j] for j, lab in header_map.items() if lab.lower() == "típus" and j < len(r)), "")
                dep = next((r[j] for j, lab in header_map.items() if lab.lower() == "tanszék" and j < len(r)), "")
                out.append(
                    Subject(
                        code=code.replace(" ", ""),
                        name=name,
                        semester=semester,
                        lecture=int(h.group(1)),
                        practice=int(h.group(2)),
                        lab=int(h.group(3)),
                        requirement=h.group(4),
                        credits=int(h.group(5)),
                        group=" › ".join(group_stack),
                        type=typ,
                        department=dep,
                        page=pno,
                    )
                )
    return out


def subject_text(s: Subject, program: str) -> str:
    if s.semester in ("őszi", "tavaszi"):
        sem = f"{s.semester} félévben meghirdetve"
    else:
        sem = " ".join(s.semester.replace("v", " vagy ").split()) if s.semester else "nincs megadva"
    hours = (
        f"Heti óraszám: {s.lecture}+{s.practice} ({s.lesson_type})."
        if s.lesson_type
        else f"Heti óraszám: {s.lecture} előadás, {s.practice} gyakorlat, {s.lab} laboratórium."
    )
    parts = [
        f"{s.code + ' – ' if s.code else ''}{s.name} ({program}, mintatanterv).",
        f"Ajánlott félév: {sem}.",
        hours,
        f"Követelmény: {REQ.get(s.requirement, s.requirement)} ({s.requirement}).",
        f"Kredit: {s.credits}.",
    ]
    if s.prereq:
        parts.append(f"Előtanulmányi feltétel: {s.prereq}.")
    if s.responsible:
        parts.append(f"Tárgyfelelős: {s.responsible}.")
    if s.type:
        parts.append(f"Típus: {s.type}.")
    if s.department:
        parts.append(f"Tanszék: {s.department}.")
    if s.group:
        parts.append(f"Tantárgycsoport: {s.group}.")
    return " ".join(parts)
