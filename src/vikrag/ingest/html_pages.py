"""VIK HTML-oldalak -> címsorok szerinti szakaszok (egységek)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

HEAD_TAGS = ["h1", "h2", "h3", "h4", "h5"]
MARK = "␞H"  # címsor-jelölő a szövegfolyamban


@dataclass
class HtmlSection:
    path: list[str]  # címsor-útvonal, pl. ["Tanulmányi ügyek", "A hallgatói követelményrendszer"]
    paragraphs: list[str] = field(default_factory=list)

    def text(self) -> str:
        return "\n".join(self.paragraphs)


def parse_html(html: str) -> tuple[str, list[HtmlSection]]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.find("div", class_="main-page-container") or soup.find("main") or soup.body
    for tag in root.find_all(["script", "style", "nav", "form"]):
        tag.decompose()
    title = ""
    first_h = root.find(HEAD_TAGS)
    if first_h:
        title = " ".join(first_h.get_text(" ", strip=True).split())
    # táblázatsor -> egy szövegsor ("2026. szeptember 7. (hétfő) – Az első tanítási nap")
    for tr in root.find_all("tr"):
        cells = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all(["td", "th"])]
        tr.replace_with("\n" + " – ".join(c for c in cells if c) + "\n")
    for h in root.find_all(HEAD_TAGS):
        level = int(h.name[1])
        h.replace_with(f"\n{MARK}{level}:{' '.join(h.get_text(' ', strip=True).split())}\n")
    # „ál-címsorok”: rövid bekezdés, amelynek teljes szövege félkövér vagy aláhúzott (pl. a képzési tájékoztatóban)
    for p in root.find_all("p"):
        txt = " ".join(p.get_text(" ", strip=True).split())
        if not txt or len(txt) > 120 or txt.endswith((".", ",", ";")):
            continue
        bold = "".join(t.get_text("", strip=True) for t in p.find_all(["b", "strong"]))
        under = "".join(
            t.get_text("", strip=True) for t in p.find_all("span", style=re.compile("underline"))
        )
        flat = txt.replace(" ", "")
        if bold.replace(" ", "") == flat:
            p.replace_with(f"\n{MARK}3:{txt}\n")
        elif under.replace(" ", "") == flat:
            p.replace_with(f"\n{MARK}4:{txt}\n")
    for br in root.find_all("br"):
        br.replace_with("\n")
    for blk in root.find_all(["p", "li", "tr", "div", "dd", "dt"]):
        blk.insert_after("\n")

    sections: list[HtmlSection] = []
    stack: list[tuple[int, str]] = []
    cur = HtmlSection(path=[])
    for raw in root.get_text("").split("\n"):
        line = " ".join(raw.split())
        if not line:
            continue
        if line.startswith(MARK):
            level_s, _, head = line[len(MARK):].partition(":")
            level = int(level_s)
            if cur.paragraphs:
                sections.append(cur)
            stack = [(lv, h) for lv, h in stack if lv < level] + [(level, head)]
            cur = HtmlSection(path=[h for _, h in stack if h != title] or [title])
            continue
        if re.fullmatch(r"[\W\d]{0,3}", line):
            continue
        cur.paragraphs.append(line)
    if cur.paragraphs:
        sections.append(cur)
    return title, sections
