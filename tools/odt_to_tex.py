#!/usr/bin/env python3
"""Convert 感悟论语.odt into the LaTeX body of the book."""

import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ODT_XML = Path("/tmp/lunyu-odt/content.xml")
ODT_PIC = Path("/tmp/lunyu-odt/Pictures")
FIG = ROOT / "figures"
CHAPTERS = ROOT / "chapters"

VOLUME_FILE = {
    "品性与修养": "品性与修养.tex",
    "学习与科研": "学习与科研.tex",
    "职场": "职场.tex",
    "习惯": "习惯.tex",
    "家庭": "家庭.tex",
    "生活与社会": "生活与社会.tex",
    "论语学习与解读": "论语学习与解读.tex",
    "附录一：《论语》章句分类": "附录一.tex",
    "附录二：孔门弟子": "附录二.tex",
}

TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
DRAW = "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}"
XLINK = "{http://www.w3.org/1999/xlink}"
STYLE = "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}"
SVG = "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}"
OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"

# plant file, caption under the plate, quotation, source, running part name
PARTS = {
    "品性与修养": (
        "pine",
        "松柏",
        "岁寒，然后知松柏之后凋也。",
        "《论语·子罕》",
        "品性与修养",
    ),
    "学习与科研": (
        "bamboo",
        "绿竹 · 《诗·卫风·淇奥》",
        "如切如磋，如琢如磨。",
        "《论语·学而》",
        "学习与科研",
    ),
    "职场": (
        "plum",
        "梅",
        "磨而不磷，涅而不缁。",
        "《论语·阳货》",
        "职场",
    ),
    "习惯": (
        "peach",
        "桃夭 · 《诗·周南》",
        "性相近也，习相远也。",
        "《论语·阳货》",
        "习惯",
    ),
    "家庭": (
        "xingcai",
        "荇菜 · 《诗·周南·关雎》",
        "父母在，不远游，游必有方。",
        "《论语·里仁》",
        "家庭",
    ),
    "生活与社会": (
        "mugua",
        "木瓜 · 《诗·卫风·木瓜》",
        "有朋自远方来，不亦乐乎？",
        "《论语·学而》",
        "生活与社会",
    ),
    "论语学习与解读": (
        "tangdi",
        "唐棣之华 · 《论语·子罕》",
        "未之思也，夫何远之有？",
        "《论语·子罕》",
        "论语学习与解读",
    ),
    "附录一：《论语》章句分类": (
        "pine",
        "松柏",
        "诗三百，一言以蔽之，曰：思无邪。",
        "《论语·为政》",
        "附录",
    ),
    "附录二：孔门弟子": (
        "bamboo",
        "绿竹",
        "三人行，必有我师焉。",
        "《论语·述而》",
        "附录",
    ),
}

QUOTE_STYLES = {"Quotations"}
DATE_STYLES = {"Time_20_stamp"}
CAPTION_STYLES = {"Centered_20_figure_20_caption"}
PART_STYLES = {"Heading_20_1_20_part"}

SOURCE_RE = re.compile(r"^《[^》]{1,40}》$")


def local(tag):
    return tag.split("}")[-1] if tag else ""


def load_parents(path):
    parents = {}
    tree = ET.parse(path)
    for el in tree.getroot().iter(STYLE + "style"):
        if el.get(STYLE + "family") != "paragraph":
            continue
        parents[el.get(STYLE + "name")] = el.get(STYLE + "parent-style-name")
    return parents


def chain(parents, name, seen=None):
    seen = seen or set()
    out = []
    while name and name not in seen:
        seen.add(name)
        out.append(name)
        name = parents.get(name)
    return out


def kind_of(parents, style):
    names = set(chain(parents, style))
    if names & CAPTION_STYLES:
        return "caption"
    if names & DATE_STYLES:
        return "date"
    if names & QUOTE_STYLES:
        return "quote"
    return "body"


def esc(text):
    if not text:
        return ""
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


class Converter:
    def __init__(self, parents):
        self.parents = parents
        self.images = {}
        self.nimg = 0
        self.lines = []
        self.volumes = []
        self.volume_name = None
        self.stats = {"chapter": 0, "part": 0, "section": 0, "quote": 0, "figure": 0}

    def begin_volume(self, filename):
        if self.volume_name is not None:
            self.volumes.append((self.volume_name, self.lines))
        self.volume_name = filename
        self.lines = [
            f"% {filename}",
            "% Auto-generated from 感悟论语.odt by tools/odt_to_tex.py",
            "",
        ]

    def emit(self, s=""):
        self.lines.append(s)

    def image_path(self, href):
        src_name = href.split("/")[-1]
        if src_name in self.images:
            return self.images[src_name]
        src = ODT_PIC / src_name
        self.nimg += 1
        ext = src.suffix.lower() or ".png"
        dest_name = f"fig{self.nimg:02d}{ext}"
        dest = FIG / dest_name
        if src.exists():
            shutil.copy(src, dest)
        self.images[src_name] = f"figures/{dest_name}"
        return self.images[src_name]

    def frames(self, el):
        paths = []
        for fr in el.iter(DRAW + "frame"):
            img = None
            for child in fr.iter(DRAW + "image"):
                img = child
                break
            if img is None:
                continue
            href = img.get(XLINK + "href")
            if not href:
                continue
            paths.append(self.image_path(href))
        return paths

    def inline(self, el, allow_notes=True):
        out = []
        if el.text:
            out.append(esc(el.text))
        for child in list(el):
            tag = local(child.tag)
            if tag == "span":
                style = child.get(TEXT + "style-name") or ""
                inner = self.inline(child, allow_notes)
                if style == "Strong_20_Emphasis" and inner.strip():
                    out.append(r"\textbf{" + inner + "}")
                elif style == "T9" and inner.strip() and "footnote" not in inner:
                    out.append(r"\textsuperscript{" + inner + "}")
                else:
                    out.append(inner)
            elif tag == "line-break":
                out.append(r"\\ ")
            elif tag == "s":
                n = int(child.get(TEXT + "c") or "1")
                out.append(r"\ " * max(n, 1))
            elif tag == "tab":
                out.append(r"\quad ")
            elif tag == "note" and allow_notes:
                body = child.find(TEXT + "note-body")
                if body is not None:
                    bits = []
                    for p in body.iter(TEXT + "p"):
                        bits.append(self.inline(p, allow_notes=False).strip())
                    note = " ".join(b for b in bits if b)
                    if note:
                        out.append(r"\footnote{" + note + "}")
            elif tag == "a":
                out.append(self.inline(child, allow_notes))
            elif tag in ("frame", "bookmark-start", "bookmark-end", "soft-page-break", "note-citation", "note"):
                pass
            else:
                out.append(self.inline(child, allow_notes))
            if child.tail:
                out.append(esc(child.tail))
        return "".join(out)

    def paragraph_text(self, el):
        return re.sub(r"[ \t]+\n", "\n", self.inline(el).strip())

    def heading_text(self, el):
        raw = "".join(el.itertext())
        raw = re.sub(r"\s+", " ", raw).strip()
        return esc(raw)

    def figure_block(self, paths, caption=None):
        self.stats["figure"] += len(paths)
        if self.volume_name == "附录二.tex" and caption and len(paths) == 1:
            self.emit(r"\discipleportrait{" + paths[0] + "}{" + caption + "}")
            self.emit()
            return
        self.emit(r"\begin{center}")
        for path in paths:
            self.emit(
                r"\includegraphics[width=\textwidth,height=0.62\textheight,keepaspectratio]{"
                + path
                + "}"
            )
        if caption:
            self.emit(r"{\captiontext " + caption + r"\par}")
        self.emit(r"\end{center}")
        self.emit()

    def classic_block(self, paragraphs):
        self.stats["quote"] += 1
        self.emit(r"\begin{classic}")
        for i, text in enumerate(paragraphs):
            if i:
                self.emit("")
            self.emit(text)
        self.emit(r"\end{classic}")
        self.emit()

    def list_block(self, el, depth=0):
        items = []
        for li in el.findall(TEXT + "list-item"):
            chunks = []
            nested = []
            for child in list(li):
                tag = local(child.tag)
                if tag in ("p", "h"):
                    text = self.paragraph_text(child)
                    paths = self.frames(child)
                    if paths:
                        chunks.append(("fig", paths, text))
                    elif text:
                        chunks.append(("text", text))
                elif tag == "list":
                    nested.append(child)
            items.append((chunks, nested))
        if not items:
            return
        self.emit(r"\begin{itemize}")
        for chunks, nested in items:
            parts = []
            figs = []
            for chunk in chunks:
                if chunk[0] == "text":
                    parts.append(chunk[1])
                else:
                    if chunk[2]:
                        parts.append(chunk[2])
                    figs.append(chunk[1])
            body = r"\par ".join(parts)
            stripped = re.sub(r"\\[a-zA-Z]+", "", body).lstrip()
            if stripped.startswith("《") or stripped.startswith("「"):
                body = r"{\kaishu " + body + "}"
            if body.strip():
                self.emit(r"\item " + body)
            elif nested:
                self.emit(r"\item[]")
            else:
                continue
            for paths in figs:
                self.figure_block(paths)
            for sub in nested:
                self.list_block(sub, depth + 1)
        self.emit(r"\end{itemize}")
        self.emit()

    def emit_part(self, title):
        meta = PARTS.get(title)
        if meta is None:
            # Fall back so an unexpected part title still builds.
            meta = ("pine", "", "", "", title)
            print("WARN unknown part:", title)
        plant, cap, quote, src, short = meta
        self.stats["part"] += 1
        self.emit(r"\setpartplant{artwork/" + plant + ".png}")
        self.emit("  {" + esc(cap) + "}")
        self.emit("  {" + esc(quote) + "}")
        self.emit("  {" + esc(src) + "}")
        self.emit("  {" + esc(short) + "}")
        if title.startswith("附录"):
            self.emit(r"\part*{" + title + "}")
            self.emit(r"\addcontentsline{toc}{part}{" + title + "}")
        else:
            self.emit(r"\part{" + title + "}")
        self.emit()

    def emit_heading(self, el):
        title = self.heading_text(el)
        if not title:
            return
        level = int(el.get(TEXT + "outline-level") or "1")
        style = el.get(TEXT + "style-name") or ""
        names = set(chain(self.parents, style))
        if level == 1 and (names & PART_STYLES or title in PARTS):
            self.emit_part(title)
        elif level <= 2:
            self.stats["chapter"] += 1
            self.emit(r"\chapter{" + title + "}")
            self.emit()
        else:
            self.stats["section"] += 1
            self.emit(r"\section{" + title + "}")
            self.emit()

    def convert(self, text_el):
        self.begin_volume("卷首.tex")
        blocks = [
            el
            for el in list(text_el)
            if local(el.tag) not in ("sequence-decls", "forms", "table-of-content")
        ]
        # Drop the manuscript's own title block; the book supplies cover and title pages.
        start = 0
        for i, el in enumerate(blocks):
            if local(el.tag) == "h":
                start = i
                break
        blocks = blocks[start:]
        i = 0
        while i < len(blocks):
            el = blocks[i]
            tag = local(el.tag)
            if tag == "h":
                title = self.heading_text(el)
                level = int(el.get(TEXT + "outline-level") or "1")
                style = el.get(TEXT + "style-name") or ""
                names = set(chain(self.parents, style))
                is_part = level == 1 and (names & PART_STYLES or title in PARTS)
                if is_part:
                    self.begin_volume(VOLUME_FILE.get(title, title + ".tex"))
                self.emit_heading(el)
                i += 1
                continue
            if tag == "list":
                self.list_block(el)
                i += 1
                continue
            if tag == "frame":
                paths = self.frames(el)
                if paths:
                    self.figure_block(paths)
                i += 1
                continue
            if tag != "p":
                i += 1
                continue
            style = el.get(TEXT + "style-name") or ""
            k = kind_of(self.parents, style)
            paths = self.frames(el)
            text = self.paragraph_text(el)
            if paths and not text:
                caption = None
                if i + 1 < len(blocks) and local(blocks[i + 1].tag) == "p":
                    nxt = blocks[i + 1]
                    if kind_of(self.parents, nxt.get(TEXT + "style-name") or "") == "caption":
                        caption = self.paragraph_text(nxt)
                        i += 1
                self.figure_block(paths, caption)
                i += 1
                continue
            if k == "caption":
                if text:
                    self.emit(r"\begin{center}{\captiontext " + text + r"\par}\end{center}")
                    self.emit()
                i += 1
                continue
            if k == "date":
                if text:
                    self.emit(r"\entrydate{" + text + "}")
                    self.emit()
                i += 1
                continue
            if k == "quote":
                group = []
                while i < len(blocks) and local(blocks[i].tag) == "p":
                    st = blocks[i].get(TEXT + "style-name") or ""
                    if kind_of(self.parents, st) != "quote":
                        break
                    t = self.paragraph_text(blocks[i])
                    if not t:
                        i += 1
                        continue
                    if SOURCE_RE.match(t):
                        if group:
                            self.classic_block(group)
                            group = []
                        self.emit(r"\quotsource{" + t + "}")
                        self.emit()
                    else:
                        group.append(t)
                    i += 1
                if group:
                    self.classic_block(group)
                continue
            if text or paths:
                if text:
                    self.emit(text)
                    self.emit()
                if paths:
                    self.figure_block(paths)
            i += 1
        if self.volume_name is not None:
            self.volumes.append((self.volume_name, self.lines))
            self.volume_name = None
        return self.volumes


def ensure_odt_extracted():
    if ODT_XML.exists() and ODT_PIC.exists():
        return
    odt = ROOT / "感悟论语.odt"
    if not odt.exists():
        raise SystemExit(f"missing {odt}")
    ODT_XML.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(odt) as zf:
        zf.extractall(ODT_XML.parent)


def main():
    ensure_odt_extracted()
    FIG.mkdir(parents=True, exist_ok=True)
    parents = {}
    parents.update(load_parents("/tmp/lunyu-odt/styles.xml"))
    parents.update(load_parents("/tmp/lunyu-odt/content.xml"))
    tree = ET.parse(ODT_XML)
    text = tree.getroot().find(f"{OFFICE}body").find(f"{OFFICE}text")
    conv = Converter(parents)
    # Keep the two opening plates under stable names.
    specials = {
        "10000001000001F800000270D8F35D46.png": "confucius.png",
        "100000000000054D000005157124E166.jpg": "stone-analects.jpg",
    }
    for src_name, dest_name in specials.items():
        src = ODT_PIC / src_name
        if src.exists():
            shutil.copy(src, FIG / dest_name)
    CHAPTERS.mkdir(parents=True, exist_ok=True)
    written = []
    for name, lines in conv.convert(text):
        path = CHAPTERS / name
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        written.append(path.name)
    stale = ROOT / "body.tex"
    if stale.exists():
        stale.unlink()
    print("wrote", ", ".join(written))
    print(conv.stats)


if __name__ == "__main__":
    main()
