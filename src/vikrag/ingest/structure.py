"""Szabályzat-szerkezet felismerése soralapon: fejezet › cím › § › (bekezdés) / számozott pont.

Egy „egység” (unit) a legkisebb hivatkozható szövegrész:
- §-os szabályzatban: a bekezdés „(n)”, vagy ha a §-nak nincs bekezdése, maga a §;
- § nélküli kari szabályzatban: a számozott pont („2.”), a „(n)” bekezdés, vagy a címsor alatti szöveg.
Az „a)”, „b)” felsorolási pontok a bekezdésen belül maradnak (TERV 1.1).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .pdf_lines import Line

CHAPTER_RE = re.compile(r"^([IVXL]+\.)\s*FEJEZET\b\s*(.*)$", re.I)
PARA_RE = re.compile(r"^(\d{1,3}(?:/[A-Z])?)\s*\.\s*§\s*(.*)$")
TVSZ_EMBED_RE = re.compile(r"^\(TVSZ\s+(\d{1,3}(?:/[A-Z])?)\.\s*§[^)]*\)\s*(.*)$")
SUB_RE = re.compile(r"^\((\d{1,2}[a-z]?)\)\s*(.*)$")
ITEM_RE = re.compile(r"^(\d{1,2})\.\s+(\S.*)$")
ANNEX_RE = re.compile(r"^(\d{1,2})\.\s*(?:SZÁMÚ\s+|SZ\.\s*)?MELLÉKLET\b\s*(.*)$", re.I)


@dataclass
class Unit:
    annex: str = ""  # melléklet száma, pl. "3" (a mellékletekben újraindul a §-számozás)
    chapter: str = ""
    section: str = ""
    paragraph: str = ""  # "53"  (§ nélkül)
    paragraph_title: str = ""
    embedded_tvsz: str = ""  # ZV-szabályzatokban: "(TVSZ 138. §)" -> "138"
    subsection: str = ""  # "2" vagy "1a"
    item: str = ""  # "2"
    lines: list[str] = field(default_factory=list)
    refs: list[str] = field(default_factory=list)
    page_start: int = 0
    page_end: int = 0

    def text(self) -> str:
        return join_lines(self.lines)


def join_lines(lines: list[str]) -> str:
    """Sorok összefűzése magyar elválasztás-kezeléssel ("rendelke-" + "zik" -> "rendelkezik")."""
    out = ""
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if not out:
            out = ln
            continue
        m = re.search(r"(\w)-$", out)
        nxt_first = ln.split()[0]
        if m and nxt_first[:1].islower() and nxt_first not in {"és", "vagy", "illetve", "valamint", "s"}:
            out = out[:-1] + ln  # elválasztott szó
        else:
            out = out + " " + ln
    out = re.sub(r"\[\s*", "[", out)
    out = re.sub(r"\s*\]", "]", out)
    return re.sub(r"\s{2,}", " ", out).strip()


def parse(lines: list[Line], *, has_paragraphs: bool | None = None) -> list[Unit]:
    if has_paragraphs is None:
        has_paragraphs = sum(1 for ln in lines if PARA_RE.match(ln.text)) >= 2

    units: list[Unit] = []
    ctx = Unit()
    cur: Unit | None = None
    pending_heading: list[Line] = []
    await_chapter_title = False  # "I. FEJEZET" után a következő félkövér sor a fejezet neve
    await_para_title = False  # OCR-nél a "3.§" után külön sorban álló cím
    last_item = 0  # az utolsó számozott (kari) pont sorszáma

    def flush_heading():
        nonlocal pending_heading
        if pending_heading:
            ctx.section = join_lines([h.text for h in pending_heading])
            pending_heading = []

    def start(**kw) -> Unit:
        nonlocal cur
        u = Unit(
            annex=ctx.annex,
            chapter=ctx.chapter,
            section=ctx.section,
            paragraph=ctx.paragraph,
            paragraph_title=ctx.paragraph_title,
            embedded_tvsz=ctx.embedded_tvsz,
        )
        for k, v in kw.items():
            setattr(u, k, v)
        units.append(u)
        cur = u
        return u

    def add(ln: Line, text: str | None = None):
        nonlocal cur
        if cur is None:
            start()
        if not cur.page_start:
            cur.page_start = ln.page
        cur.page_end = ln.page
        cur.lines.append(ln.text if text is None else text)
        cur.refs.extend(ln.refs)

    for ln in lines:
        t = ln.text

        if await_chapter_title:
            await_chapter_title = False
            looks_like_title = (ln.bold or t.isupper()) and not PARA_RE.match(t) and not re.match(r"^\d+\.", t)
            if looks_like_title:
                if ctx.chapter:
                    ctx.chapter = f"{ctx.chapter} {t}".strip()
                else:  # melléklet címe
                    ctx.section = f"{ctx.section} {t}".strip()
                continue
        if await_para_title:
            await_para_title = False
            if len(t) < 100 and not SUB_RE.match(t) and not PARA_RE.match(t) and not t.endswith((".", ",", ";", ":")):
                ctx.paragraph_title = t
                if cur is not None:
                    cur.paragraph_title = t
                continue

        m = ANNEX_RE.match(t)
        # a mellékletek sorrendben jönnek: az első elfogadott az 1. melléklet (így a tartalomjegyzék
        # „4. melléklet …” sora nem nyit mellékletet a főszöveg közepén)
        if m and len(t) < 140 and (ln.bold or "MELLÉKLET" in t) and (m.group(1) == "1" or ctx.annex):
            flush_heading()
            ctx.annex = m.group(1)
            ctx.chapter = ""
            ctx.section = m.group(2).strip()
            ctx.paragraph = ctx.paragraph_title = ctx.embedded_tvsz = ""
            await_chapter_title = not ctx.section  # a melléklet címe gyakran a következő sorban van
            cur = None
            continue

        m = CHAPTER_RE.match(t)
        if m and (ln.bold or t.isupper()):
            flush_heading()
            ctx.chapter = f"{m.group(1)} FEJEZET {m.group(2)}".strip()
            await_chapter_title = not m.group(2).strip()
            ctx.section = ctx.paragraph = ctx.paragraph_title = ctx.embedded_tvsz = ""
            cur = None
            continue

        m = PARA_RE.match(t) if has_paragraphs else None
        # valódi §-fejléc: "53. § [Cím]", félkövér "1. § Cím", vagy üres (OCR: a cím a következő sorban);
        # NEM fejléc a sor elejére tört hivatkozás: "45. § (2a) bekezdésében foglalt …"
        rest = m.group(2).strip() if m else ""
        if m and (rest.startswith("[") or (ln.bold and not rest.startswith("(")) or not rest):
            flush_heading()
            ctx.paragraph = m.group(1)
            title = m.group(2).strip()
            if title.startswith("["):
                title = title.strip("[] ")
            elif title and ln.bold:  # "1. § A szabályzat hatálya" típusú cím
                pass
            else:
                title = title  # nincs külön cím
            ctx.paragraph_title = re.sub(r"\s+", " ", title)
            await_para_title = not ctx.paragraph_title
            ctx.embedded_tvsz = ""
            start(page_start=ln.page, page_end=ln.page)
            cur.refs.extend(ln.refs)
            continue

        m = TVSZ_EMBED_RE.match(t)
        if m:
            flush_heading()
            ctx.embedded_tvsz = m.group(1)
            cur = None
            if m.group(2):
                add(ln, m.group(2))
            continue

        m = SUB_RE.match(t)
        # a sor elejére tört hivatkozás ("(3) bekezdés b) pontjában …") nem új bekezdés: az új bekezdés nagybetűvel kezdődik
        if m and m.group(2)[:1].islower():
            m = None
        if m and not ln.bold:
            flush_heading()
            parent_item = cur.item if (cur and not has_paragraphs and not ctx.embedded_tvsz) else ""
            start(subsection=m.group(1), item=parent_item, page_start=ln.page, page_end=ln.page)
            cur.lines.append(m.group(2))
            cur.refs.extend(ln.refs)
            continue

        # címsor: félkövér rövid sor, vagy (§ nélküli dokumentumban) római számos / nagybetűs cím
        is_heading = ln.bold and len(t) < 160 and not t.endswith((",", ";"))
        if is_heading and not units and ln.page == 1:
            continue  # az első oldal egységek előtti félkövér sorai a dokumentum címét adják
        if is_heading:
            if pending_heading and pending_heading[-1].page == ln.page and ln.y - pending_heading[-1].y < 3 * ln.size:
                pending_heading.append(ln)
            else:
                flush_heading()
                pending_heading = [ln]
            if has_paragraphs:
                ctx.paragraph = ctx.paragraph_title = ""
            ctx.embedded_tvsz = ""
            cur = None
            continue
        flush_heading()

        m = ITEM_RE.match(t) if not has_paragraphs else None
        # a kari pontok folyamatosan számozódnak; a TVSZ-ből átvett blokk („(TVSZ 150. §)”) után a soron
        # következő pontszám új kari pontot nyit, egyéb számozott sor a TVSZ-blokkon belül felsorolás marad
        if m and (not ctx.embedded_tvsz or int(m.group(1)) == last_item + 1):
            ctx.embedded_tvsz = ""
            last_item = int(m.group(1))
            start(item=m.group(1), page_start=ln.page, page_end=ln.page)
            cur.lines.append(m.group(2))
            cur.refs.extend(ln.refs)
            continue

        add(ln)

    flush_heading()
    return [u for u in units if len(u.text()) >= 3]
