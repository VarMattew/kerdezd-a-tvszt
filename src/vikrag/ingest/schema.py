"""A korpusz egységes chunk-sémája."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field


@dataclass
class Chunk:
    chunk_id: str  # pl. "tvsz:53:2", "vik_bsc_zv:p2", "kp_bsc_info:targy:VIAUAC15"
    doc_id: str
    doc_title: str
    doc_short: str  # rövid dokumentumnév a hivatkozáshoz, pl. "TVSZ"
    scope: str  # egyetemi | VIK | szak:<név>
    kind: str  # rule (szabályzati egység) | curriculum (mintatanterv-sor) | page (tájékoztató szöveg)
    citation: str  # emberi olvasásra szánt pontos hivatkozás, pl. "TVSZ 53. § (2)"
    text: str  # a chunk szövege (lábjegyzetjelek nélkül)
    source_url: str = ""
    page_start: int | None = None  # 1-től számozva; HTML-nél None
    page_end: int | None = None
    annex: str = ""  # melléklet száma (pl. "3"), ahol újraindul a §-számozás
    chapter: str = ""  # pl. "III. FEJEZET A TANULMÁNYOK JOGI KERETEI"
    section: str = ""  # legközelebbi címsor, pl. "16. A felvétel és az átvétel"
    paragraph: str = ""  # pl. "53. §"
    paragraph_title: str = ""  # pl. "A felvétel jogi keretei"
    subsection: str = ""  # pl. "(2)"
    item: str = ""  # számozott pont, pl. "2." (paragrafus nélküli szabályzatoknál)
    part: str = ""  # hosszú egység darabolásakor, pl. "1/2"
    footnotes: list[str] = field(default_factory=list)  # módosító határozatok (hatályossági metaadat)
    crossrefs: list[str] = field(default_factory=list)  # hivatkozott egységek, pl. "tvsz:53:2"
    ocr: bool = False
    extra: dict = field(default_factory=dict)  # típusfüggő mezők (pl. mintatanterv: kredit, félév)

    def to_dict(self) -> dict:
        return asdict(self)

    def header(self) -> str:
        """Kontextusfejléc a beágyazáshoz (TERV 1.1): dokumentum › fejezet › cím › hivatkozás."""
        parts = [self.doc_short]
        for p in (self.chapter, self.section, self.paragraph_title):
            if p and p not in parts:
                parts.append(p)
        parts.append(self.citation)
        return " › ".join(parts)


def slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w/]+", "-", s, flags=re.UNICODE).strip("-")
    return s[:40]
