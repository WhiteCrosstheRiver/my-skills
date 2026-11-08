# -*- coding: utf-8 -*-
"""Book IR v2: structure-preserving EPUB/PDF -> book.json (+ img/), with a quality report.

Why a rewrite (vs extract_batch.py v1):
  * v1 matched <p|div|...>(.*?)</\\1> with a regex, so a <div> wrapping many <p> became ONE giant
    paragraph (or got cut at the first inner </div>); <br> line breaks and short chapters (<3 paras)
    were silently lost; full-width ！？ were not treated as sentence ends in PDFs.
  * v1 PDF paragraphs were "page text split on blank lines": running headers, page numbers and
    hyphenated line breaks leaked into the text, and front matter before the first TOC entry vanished.
  * v1 never looked at Zotero, though the skill promises "任意 Zotero 书籍".

Output keeps the v1 contract (chapters[].paras is a list of strings, chapters[].images uses
{"after": k, "src": "img/..."}), so build_book.py and existing distill.json files keep working.
New fields: extractor, author, language, format, zotero, quality.

CLI:
  python bookir.py extract <book.epub|book.pdf> <out_ir_dir> [--title T] [--no-images]
  python bookir.py zotero-list [--query Q] [--data-dir DIR] [--all-types]
  python bookir.py zotero-extract <ITEM_KEY> <out_ir_dir> [--data-dir DIR] [--prefer epub|pdf]
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import posixpath
import re
import shutil
import sqlite3
import statistics
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote

EXTRACTOR = "bookir/2"
CJK = r"　-〿぀-ヿ㐀-䶿一-鿿豈-﫿＀-￯"
RE_CJK_CHAR = re.compile(f"[{CJK}]")
WRAP = "\x01"
RE_WRAP_CJK = re.compile(f"(?<=[{CJK}])[ \\t]*{WRAP}[ \\t{WRAP}]*(?=[{CJK}])")
SENT_END = "。！？!?…」』”’）)】.:：;；\"'"
MIN_IMG_BYTES = 10 * 1024


# ---------------------------------------------------------------- text helpers
def clean_inline(text: str) -> str:
    """Collapse whitespace inside one block; keep explicit line breaks (\n from <br>)."""
    text = text.replace("­", "").replace("​", "").replace("﻿", "")
    # WRAP marks a newline of the *source file* (editor line wrapping, not a <br>). Between two CJK
    # characters it is an artifact and vanishes; elsewhere it is a word space. Typed spaces are kept
    # ("第一章 渡口"), only collapsed.
    text = RE_WRAP_CJK.sub("", text)
    text = re.sub(r"[ \t]*" + WRAP + r"[ \t]*", " ", text)
    lines = [re.sub(r"[ \t\r\f\v 　]+", " ", ln).strip() for ln in text.split("\n")]
    out = "\n".join(ln for ln in lines if ln)
    return out.strip()


def cjk_ratio(text: str) -> float:
    letters = [c for c in text if not c.isspace()]
    return (sum(1 for c in letters if RE_CJK_CHAR.match(c)) / len(letters)) if letters else 0.0


def join_lines(a: str, b: str) -> str:
    """Join two visual lines of running text (PDF): dehyphenate Latin, no space between CJK."""
    if not a:
        return b
    if not b:
        return a
    if re.search(r"[A-Za-z]-$", a) and re.match(r"[a-z]", b):
        return a[:-1] + b
    if RE_CJK_CHAR.match(a[-1]) or RE_CJK_CHAR.match(b[0]):
        return a + b
    return a + " " + b


def mojibake_ratio(text: str) -> float:
    if not text:
        return 0.0
    bad = sum(1 for c in text if c == "�" or (0xE000 <= ord(c) <= 0xF8FF))
    return bad / len(text)


# ---------------------------------------------------------------- EPUB
BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "li", "pre", "dt", "dd",
              "figcaption", "caption", "td", "th", "tr", "section", "article", "aside", "header",
              "footer", "table", "ul", "ol", "dl", "figure", "body", "center", "address", "hr", "nav"}
SKIP_TAGS = {"script", "style", "head", "title", "svg:title", "math", "noscript", "template"}
VOID = {"br", "img", "hr", "image", "meta", "link", "input", "col", "area", "base", "wbr", "source"}


class XhtmlBlocks(HTMLParser):
    """Flatten an XHTML document into an ordered stream of blocks.

    Every start/end of a block element flushes the pending inline text, so nested containers
    (div > div > p) yield one block per real paragraph instead of one blob. Events:
      ("text", kind, str)   kind in heading|para|quote|pre|item
      ("img", src)
      ("anchor", id)        element ids, so TOC fragments (#id) can be located in the stream
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events, self.buf, self.stack, self.skip = [], [], [], 0
        self.hidden_depth = 0

    def _kind(self):
        for tag in reversed(self.stack):
            if re.fullmatch(r"h[1-6]", tag):
                return "heading"
            if tag == "blockquote":
                return "quote"
            if tag == "pre":
                return "pre"
            if tag in ("li", "dt", "dd"):
                return "item"
        return "para"

    def flush(self):
        if self.buf:
            raw = "".join(self.buf)
            self.buf = []
            kind = self._kind()
            text = raw.strip("\n") if kind == "pre" else clean_inline(raw)
            if text:
                self.events.append(("text", kind, text))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in SKIP_TAGS:
            if tag not in VOID:
                self.skip += 1
            return
        if self.skip:
            return
        if a.get("id"):
            self.flush() if tag in BLOCK_TAGS else None
            self.events.append(("anchor", a["id"]))
        if tag in BLOCK_TAGS:
            self.flush()
            if tag == "hr":
                return
            if tag not in VOID:
                self.stack.append(tag)
        elif tag == "br":
            self.buf.append("\n")
        elif tag in ("img", "image"):
            src = a.get("src") or a.get("xlink:href") or a.get("href")
            if src:
                self.flush()
                self.events.append(("img", src))
        elif tag in ("rt", "rp"):  # ruby annotations: drop the reading, keep the base text
            self.skip += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        tag = tag.lower()
        # self-closing non-void block/skip tags (e.g. <div/>) must not leave the stack open
        if tag in BLOCK_TAGS and tag not in VOID and self.stack and self.stack[-1] == tag:
            self.stack.pop()
        if (tag in SKIP_TAGS or tag in ("rt", "rp")) and tag not in VOID and self.skip:
            self.skip -= 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in SKIP_TAGS or tag in ("rt", "rp"):
            if self.skip:
                self.skip -= 1
            return
        if self.skip:
            return
        if tag in BLOCK_TAGS:
            self.flush()
            if tag in self.stack:
                while self.stack:
                    if self.stack.pop() == tag:
                        break

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data if (self.stack and self.stack[-1] == "pre") else re.sub(r"\r?\n", WRAP, data))

    def close(self):
        super().close()
        self.flush()


def _decode(raw: bytes) -> str:
    m = re.search(rb'encoding=["\']([\w-]+)["\']', raw[:200]) or re.search(rb'charset=["\']?([\w-]+)', raw[:2000])
    encs = ([m.group(1).decode("ascii", "ignore")] if m else []) + ["utf-8", "gb18030", "big5", "utf-16"]
    for enc in encs:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "ignore")


def _strip_ns(tag):
    return tag.rsplit("}", 1)[-1].lower()


def _norm(base_dir, href):
    href = unquote(href.split("#", 1)[0])
    return posixpath.normpath(posixpath.join(base_dir, href)) if href else ""


def _xml(raw: bytes):
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        txt = _decode(raw)
        txt = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", txt)
        txt = re.sub(r"<\?xml[^>]*\?>", "", txt)
        return ET.fromstring(txt.encode("utf-8"))


def epub_package(z: zipfile.ZipFile):
    names = set(z.namelist())
    opf = None
    if "META-INF/container.xml" in names:
        try:
            root = _xml(z.read("META-INF/container.xml"))
            for el in root.iter():
                if _strip_ns(el.tag) == "rootfile" and el.get("full-path"):
                    opf = el.get("full-path")
                    break
        except ET.ParseError:
            pass
    if not opf or opf not in names:
        opf = next((n for n in z.namelist() if n.lower().endswith(".opf")), None)
    if not opf:
        raise ValueError("EPUB has no OPF package document")
    root = _xml(z.read(opf))
    base = posixpath.dirname(opf)
    meta, manifest, spine, toc_id = {}, {}, [], None
    for el in root.iter():
        t = _strip_ns(el.tag)
        if t in ("title", "creator", "language", "publisher", "date", "identifier") and (el.text or "").strip():
            meta.setdefault(t, []).append(el.text.strip())
        elif t == "item" and el.get("href"):
            manifest[el.get("id")] = {"href": _norm(base, el.get("href")), "type": el.get("media-type", ""),
                                      "props": el.get("properties", "")}
        elif t == "spine":
            toc_id = el.get("toc")
        elif t == "itemref" and el.get("idref") in manifest:
            spine.append(manifest[el.get("idref")]["href"])
    return {"opf": opf, "meta": meta, "manifest": manifest, "spine": spine, "toc_id": toc_id, "names": names}


def epub_toc(z, pkg):
    """[(level, title, doc_path, fragment)] in reading order. EPUB3 nav first, then NCX."""
    entries = []
    nav = next((m["href"] for m in pkg["manifest"].values() if "nav" in m["props"].split()), None)
    if nav and nav in pkg["names"]:
        try:
            entries = _nav_entries(z.read(nav), posixpath.dirname(nav))
        except Exception:
            entries = []
    if not entries:
        ncx = pkg["manifest"].get(pkg["toc_id"] or "", {}).get("href")
        if not ncx or ncx not in pkg["names"]:
            ncx = next((m["href"] for m in pkg["manifest"].values() if m["type"] == "application/x-dtbncx+xml"), None)
        if ncx and ncx in pkg["names"]:
            try:
                root = _xml(z.read(ncx))
                base = posixpath.dirname(ncx)

                def walk(node, level):
                    for np in node:
                        if _strip_ns(np.tag) != "navpoint":
                            continue
                        label = "".join(t for el in np.iter() if _strip_ns(el.tag) == "text" for t in [el.text or ""] )
                        # first <text> belongs to this navPoint's own label
                        lab = next((el for el in np if _strip_ns(el.tag) == "navlabel"), None)
                        if lab is not None:
                            label = "".join((el.text or "") for el in lab.iter() if _strip_ns(el.tag) == "text")
                        content = next((el for el in np if _strip_ns(el.tag) == "content"), None)
                        src = content.get("src", "") if content is not None else ""
                        if src:
                            frag = unquote(src.split("#", 1)[1]) if "#" in src else ""
                            entries.append((level, clean_inline(label), _norm(base, src), frag))
                        walk(np, level + 1)

                navmap = next((el for el in root.iter() if _strip_ns(el.tag) == "navmap"), None)
                if navmap is not None:
                    walk(navmap, 1)
            except ET.ParseError:
                entries = []
    return [e for e in entries if e[1]]


def _nav_entries(raw, base):
    class Nav(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.out, self.depth, self.in_toc, self.navdepth, self.a, self.text = [], 0, False, 0, None, []

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "nav":
                self.navdepth += 1
                if "toc" in (a.get("epub:type", "") + " " + a.get("role", "")).lower() or not self.out:
                    self.in_toc = self.in_toc or "toc" in (a.get("epub:type", "") + a.get("role", "")).lower()
            if tag == "ol":
                self.depth += 1
            if tag == "a" and self.navdepth:
                self.a, self.text = a.get("href", ""), []

        def handle_endtag(self, tag):
            if tag == "ol":
                self.depth -= 1
            if tag == "a" and self.a is not None:
                href = self.a
                frag = unquote(href.split("#", 1)[1]) if "#" in href else ""
                self.out.append((max(1, self.depth), clean_inline("".join(self.text)), _norm(base, href), frag, self.in_toc))
                self.a = None
            if tag == "nav":
                self.navdepth -= 1
                if self.in_toc and any(o[4] for o in self.out):
                    self.in_toc = False

        def handle_data(self, d):
            if self.a is not None:
                self.text.append(d)

    p = Nav()
    p.feed(_decode(raw))
    toc = [o for o in p.out if o[4]] or p.out  # prefer the epub:type="toc" nav over landmarks/page-list
    return [(lvl, t, d, f) for lvl, t, d, f, _ in toc]


def extract_epub(path, with_images=True):
    z = zipfile.ZipFile(path)
    pkg = epub_package(z)
    spine = [s for s in pkg["spine"] if s in pkg["names"]] or sorted(
        n for n in pkg["names"] if re.search(r"\.(x?html?)$", n, re.I))
    toc = epub_toc(z, pkg)
    # 1) linear block stream over the whole spine
    stream, anchors, doc_start = [], {}, {}
    for doc in spine:
        doc_start[doc] = len(stream)
        anchors[(doc, "")] = len(stream)
        p = XhtmlBlocks()
        try:
            p.feed(_decode(z.read(doc)))
            p.close()
        except Exception as exc:  # keep going: one broken XHTML file must not kill the book
            stream.append({"kind": "warn", "text": f"parse error in {doc}: {exc}"})
            continue
        for ev in p.events:
            if ev[0] == "anchor":
                anchors.setdefault((doc, ev[1]), len(stream))
            elif ev[0] == "img":
                stream.append({"kind": "img", "src": _norm(posixpath.dirname(doc), ev[1]), "doc": doc})
            else:
                stream.append({"kind": ev[1], "text": ev[2], "doc": doc})
    # 2) chapter boundaries from the TOC (choose a level that actually partitions the book)
    cuts = _toc_cuts(toc, anchors, doc_start, len(stream))
    if not cuts:  # no usable TOC: one chapter per spine document, headings as titles
        cuts = []
        for doc in spine:
            i = doc_start.get(doc, 0)
            title = next((b["text"] for b in stream[i:i + 6] if b.get("doc") == doc and b["kind"] == "heading"), None)
            cuts.append((i, title or posixpath.splitext(posixpath.basename(doc))[0]))
    chapters = _cut_stream(stream, cuts)
    images = []
    if with_images:
        sizes = {i.filename: i.file_size for i in z.infolist()}
        counts = Counter(b["src"] for b in stream if b["kind"] == "img")
        for ch in chapters:
            for im in ch.get("_imgs", []):
                src = im["src"]
                if src not in sizes or sizes[src] < MIN_IMG_BYTES or counts[src] > 3:
                    continue
                images.append((ch, im, src))
    meta = pkg["meta"]
    info = {"title": (meta.get("title") or [""])[0], "author": "、".join(meta.get("creator", [])),
            "language": (meta.get("language") or [""])[0], "toc_entries": len(toc)}
    return chapters, images, (lambda src: z.read(src)), info


def _toc_cuts(toc, anchors, doc_start, n):
    if not toc:
        return []
    located = []
    for lvl, title, doc, frag in toc:
        pos = anchors.get((doc, frag), anchors.get((doc, ""), None)) if frag else anchors.get((doc, ""))
        if pos is None and doc in doc_start:
            pos = doc_start[doc]
        if pos is not None:
            located.append((lvl, pos, title))
    if not located:
        return []
    levels = sorted({l for l, _, _ in located})
    best = None
    for lvl in levels:  # shallowest level with >=2 distinct cut positions
        pos = sorted({p for l, p, _ in located if l <= lvl})
        if len(pos) >= 2:
            best = lvl
            break
    if best is None:
        best = levels[-1]
    cuts, seen = [], set()
    for l, p, t in sorted(((l, p, t) for l, p, t in located if l <= best), key=lambda x: (x[1], x[0])):
        if p in seen:
            # same position: keep the outer title, e.g. "第一部 · 第一章" collapses to the first one
            continue
        seen.add(p)
        cuts.append((p, t))
    return cuts


def _cut_stream(stream, cuts):
    cuts = sorted(cuts)
    if not cuts or cuts[0][0] > 0:
        cuts = [(0, None)] + cuts
    chapters = []
    for i, (start, title) in enumerate(cuts):
        end = cuts[i + 1][0] if i + 1 < len(cuts) else len(stream)
        blocks = stream[start:end]
        paras, imgs, kinds = [], [], []
        for b in blocks:
            if b["kind"] == "img":
                imgs.append({"after": len(paras) - 1, **{k: b[k] for k in ("src", "data", "ext", "w", "h") if k in b}})
            elif b["kind"] not in ("warn", "page"):
                paras.append(b["text"])
                kinds.append(b["kind"])
        # drop a leading heading that only repeats the chapter title
        if title and paras and kinds[0] == "heading" and _same_title(paras[0], title):
            paras.pop(0)
            kinds.pop(0)
            for im in imgs:
                im["after"] = max(-1, im["after"] - 1)
        if title is None:
            if not paras and not imgs:
                continue
            title = "卷首 · Front matter"
        if not paras and not imgs:
            continue
        ch = {"title": title, "paras": paras, "kinds": kinds, "_imgs": imgs}
        chapters.append(ch)
    return chapters


def _same_title(a, b):
    na, nb = re.sub(r"\W", "", a).lower(), re.sub(r"\W", "", b).lower()
    return bool(na) and (na == nb or (len(na) <= 60 and (na in nb or nb in na)))


# ---------------------------------------------------------------- PDF
def extract_pdf(path, with_images=True):
    import pymupdf

    doc = pymupdf.open(path)
    if doc.needs_pass:
        raise ValueError("encrypted PDF")
    pages = []
    for pno, page in enumerate(doc):
        d = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_MEDIABOX_CLIP)
        H = page.rect.height or 1
        blocks = []
        for b in d["blocks"]:
            if b["type"] == 1:
                if with_images and b.get("image") and len(b["image"]) >= MIN_IMG_BYTES and min(b.get("width", 0), b.get("height", 0)) >= 100:
                    blocks.append({"kind": "img", "y": b["bbox"][1], "data": b["image"], "ext": b.get("ext", "png"),
                                   "w": b.get("width"), "h": b.get("height")})
                continue
            lines = []
            for ln in b["lines"]:
                t = "".join(s["text"] for s in ln["spans"])
                if not t.strip():
                    continue
                size = max((s["size"] for s in ln["spans"] if s["text"].strip()), default=0)
                lines.append({"text": t.strip(), "size": round(size, 1), "x0": ln["bbox"][0], "y0": ln["bbox"][1], "y1": ln["bbox"][3]})
            if lines:
                blocks.append({"kind": "text", "lines": lines, "y": b["bbox"][1], "y1": b["bbox"][3], "rel_top": b["bbox"][1] / H, "rel_bot": b["bbox"][3] / H})
        pages.append(blocks)
    total_chars = sum(len(l["text"]) for p in pages for b in p if b["kind"] == "text" for l in b["lines"])
    info = {"pages": len(pages), "chars_per_page": round(total_chars / max(1, len(pages)), 1),
            "title": (doc.metadata or {}).get("title", ""), "author": (doc.metadata or {}).get("author", ""), "language": ""}
    if total_chars / max(1, len(pages)) < 40:
        raise ScanError(f"scanned/image-only PDF ({info['chars_per_page']} text chars per page); needs OCR")
    furniture = _page_furniture(pages)
    sizes = Counter(l["size"] for p in pages for b in p if b["kind"] == "text" for l in b["lines"] for _ in range(len(l["text"])))
    body_size = sizes.most_common(1)[0][0] if sizes else 10
    # linear stream with page markers
    stream = []
    for pno, blocks in enumerate(pages):
        stream.append({"kind": "page", "page": pno + 1})
        for b in blocks:
            if b["kind"] == "img":
                stream.append({"kind": "img", "data": b["data"], "ext": b["ext"], "w": b["w"], "h": b["h"], "page": pno + 1})
                continue
            margin = _in_margin(b)
            lines = [l for l in b["lines"] if not (margin and _furniture_key(l["text"]) in furniture)]
            lines = [l for l in lines if not (margin and re.fullmatch(r"[-–—\s]*[\divxlcIVXLC]{1,6}[-–—\s]*", l["text"]))]
            if not lines:
                continue
            for para in _split_block(lines):
                big = para["size"] >= body_size * 1.25 and len(para["text"]) <= 80
                stream.append({"kind": "heading" if big else "para", "text": para["text"], "page": pno + 1,
                               "size": para["size"], "cont": para["cont"]})
    stream = _collapse_fragments(_merge_continuations(stream))
    toc = [(l, clean_inline(t), p) for l, t, p, *_ in doc.get_toc(simple=False)] if doc.get_toc() else []
    cuts = _pdf_cuts(stream, toc)
    if not cuts:
        cuts = _heading_cuts(stream)
    if not cuts:  # last resort: fixed page windows, honestly titled
        cuts = [(i, f"第 {k + 1} 部分 (pp.{b['page']}-)") for k, (i, b) in
                enumerate((i, b) for i, b in enumerate(stream) if b["kind"] == "page" and (b["page"] - 1) % 10 == 0)]
    chapters = _cut_stream([b for b in stream], cuts) if cuts else []
    images = []
    for ch in chapters:
        for im in ch.get("_imgs", []):
            images.append((ch, im, None))
    info["toc_entries"] = len(toc)
    return chapters, images, None, info


class ScanError(ValueError):
    pass


def _furniture_key(text):
    return re.sub(r"\d+", "#", re.sub(r"\s+", "", text))[:60]


def _in_margin(b):
    """A running head/footer is a small block lying wholly in the top or bottom band of the page.
    Testing single lines instead deleted real first lines of body text that happened to repeat."""
    return b["kind"] == "text" and len(b["lines"]) <= 2 and (b["rel_bot"] < 0.12 or b["rel_top"] > 0.88)


def _page_furniture(pages):
    """Lines that repeat at the top/bottom of many pages: running heads, footers, page numbers."""
    c = Counter()
    for blocks in pages:
        keys = set()
        for b in blocks:
            if _in_margin(b):
                for l in b["lines"]:
                    keys.add(_furniture_key(l["text"]))
        c.update(keys)
    # Absolute count, not a share of the book: a per-chapter running head recurs on only a few pages
    # of a long book, and a small block wholly inside the margin band is rarely real text.
    return {k for k, v in c.items() if k and v >= 3}


def _split_block(lines):
    """A PyMuPDF block may hold several paragraphs; split on first-line indents and big gaps."""
    paras, cur = [], None
    xs = sorted(l["x0"] for l in lines)
    left = xs[len(xs) // 4] if xs else 0
    heights = [l["y1"] - l["y0"] for l in lines]
    lh = statistics.median(heights) if heights else 10
    prev = None
    for l in lines:
        indent = l["x0"] - left > lh * 0.9
        gap = prev is not None and (l["y0"] - prev["y1"]) > lh * 0.8
        prev_ends = prev is not None and prev["text"][-1:] in SENT_END
        size_change = prev is not None and abs(l["size"] - prev["size"]) > 1.0
        if cur is None or gap or size_change or (indent and prev_ends) or (indent and RE_CJK_CHAR.match(l["text"][:1] or "")):
            if cur:
                paras.append(cur)
            cur = {"text": l["text"], "size": l["size"], "cont": not paras and not indent}
        else:
            cur["text"] = join_lines(cur["text"], l["text"])
        prev = l
    if cur:
        paras.append(cur)
    for p in paras:
        p["text"] = clean_inline(p["text"])
    return [p for p in paras if p["text"]]


def _merge_continuations(stream):
    """Re-join a paragraph split by a page break (or a column/block break)."""
    out, last_para = [], None
    for b in stream:
        if b["kind"] == "para" and last_para is not None and b.get("cont"):
            prev = out[last_para]
            if prev["text"][-1:] not in SENT_END and abs(prev.get("size", 0) - b.get("size", 0)) <= 1.0 and \
                    (re.match(r"[a-z(“\"'‘,，、]", b["text"]) or re.search(r"(?:^|\s)[a-z]+$", prev["text"])  # "...Is the" + "Way."
                     or (RE_CJK_CHAR.match(b["text"][:1]) and RE_CJK_CHAR.match(prev["text"][-1:]))):
                prev["text"] = join_lines(prev["text"], b["text"])
                continue
        if b["kind"] == "heading" and out and out[-1]["kind"] == "heading" and out[-1]["page"] == b["page"] \
                and abs(out[-1].get("size", 0) - b.get("size", 0)) <= 0.5:
            out[-1]["text"] = join_lines(out[-1]["text"], b["text"])  # one title wrapped over two lines
            continue
        if b["kind"] in ("para", "heading"):
            out.append(b)
            last_para = len(out) - 1 if b["kind"] == "para" else None
        else:
            out.append(b)
    return out


def _is_fragment(b):
    """A glyph run from a formula, table cell or figure label rather than a sentence."""
    if b["kind"] != "para":
        return False
    t = b["text"]
    if len(t) > 40:
        return False
    if t[-1:] in "。！？.!?" and len(t.split()) + len(re.findall(r"[一-鿿]", t)) >= 3:
        return False  # a short real sentence: "He was gone."
    if len(t) <= 3:
        return True
    words = re.findall(r"[A-Za-z]{4,}|[一-鿿]{3,}", t)
    return len(words) <= 1 or sum(len(w) for w in words) < 0.5 * len(t)


def _collapse_fragments(stream):
    """Merge runs of >=3 fragments into one paragraph marked kind=fragment.

    PDF text layers shatter equations and figures into hundreds of one-glyph blocks ("X", "n i¼1").
    They are not recoverable as math, but deleting them would break fidelity and search; left alone
    they swamp the paragraph numbering and the reader. Page markers inside a run do not end it.
    """
    out, run = [], []

    def flush():
        real = [b for b in run if b["kind"] == "para"]
        if len(real) >= 3:
            first = real[0]
            out.append({**first, "kind": "fragment", "text": " ".join(b["text"] for b in real)})
            out.extend(b for b in run if b["kind"] != "para")
        else:
            out.extend(run)
        run.clear()

    for b in stream:
        if _is_fragment(b) or (run and b["kind"] == "page"):
            run.append(b)
        else:
            flush()
            out.append(b)
    flush()
    return out


def _heading_cuts(stream):
    """Chapter cuts for a PDF without a TOC: explicit chapter titles, else the largest heading tier."""
    heads = [(i, b) for i, b in enumerate(stream) if b["kind"] == "heading"]
    named = [(i, b["text"]) for i, b in heads if re.match(r"(chapter|part)\s+[\divxlc]+(?![a-z])|第[一二三四五六七八九十百零\d]+[章部篇]", b["text"], re.I)]
    def balanced(cuts):
        marks = [c[0] for c in cuts] + [len(stream)]
        return max(b - a for a, b in zip(marks, marks[1:])) <= 0.5 * len(stream)

    if len(named) >= 3 and balanced(named):
        return named
    sizes = sorted({b["size"] for _, b in heads}, reverse=True)
    first_valid = []
    for k in range(1, len(sizes) + 1):
        tier = set(sizes[:k])
        cuts = [(i, b["text"]) for i, b in heads if b["size"] in tier]
        if len(cuts) > 80:
            break
        if len(cuts) < 3:
            continue
        first_valid = first_valid or cuts
        # The largest tier can be just a few part titles: accept it only if it divides the book.
        if balanced(cuts):
            return cuts
    return first_valid


def _pdf_cuts(stream, toc):
    if not toc:
        return []
    page_pos = {b["page"]: i for i, b in enumerate(stream) if b["kind"] == "page"}
    levels = sorted({l for l, _, _ in toc})
    best = levels[0]
    for lvl in levels:
        if len({p for l, _, p in toc if l <= lvl}) >= 2:
            best = lvl
            break
    cuts, seen = [], set()
    for l, title, page in toc:
        if l > best or page not in page_pos:
            continue
        start = page_pos[page]
        end = page_pos.get(page + 1, len(stream))
        pos = start
        key = re.sub(r"\W", "", title).lower()
        for j in range(start, end):  # cut at the heading itself, not at the page top
            b = stream[j]
            if b["kind"] in ("para", "heading") and key and _same_title(b["text"], title):
                pos = j
                break
        if pos in seen:
            continue
        seen.add(pos)
        cuts.append((pos, title))
    return cuts


# ---------------------------------------------------------------- quality + writing
def quality(chapters, info, fmt):
    paras = [p for c in chapters for p in c["paras"]]
    lens = [len(p) for p in paras] or [0]
    text = "".join(paras)
    q = {"chapters": len(chapters), "paras": len(paras), "chars": len(text),
         "median_para_chars": int(statistics.median(lens)), "max_para_chars": max(lens),
         "giant_paras": sum(1 for x in lens if x > 4000), "tiny_para_ratio": round(sum(1 for x in lens if x < 8) / max(1, len(lens)), 3),
         "cjk_ratio": round(cjk_ratio(text[:200000]), 3), "mojibake_ratio": round(mojibake_ratio(text), 4),
         "toc_entries": info.get("toc_entries", 0), "warnings": []}
    w = q["warnings"]
    if q["paras"] < 20:
        w.append("very little text (<20 paragraphs): check for image-only book or DRM")
    if q["giant_paras"]:
        w.append(f"{q['giant_paras']} paragraphs >4000 chars: paragraph structure probably lost")
    if q["mojibake_ratio"] > 0.01:
        w.append("encoding problems: >1% replacement/private-use characters")
    if len(chapters) == 1 and q["paras"] > 200:
        w.append("single chapter for a long book: TOC missing, consider splitting by headings manually")
    if not info.get("toc_entries"):
        w.append("no TOC in source; chapters inferred from documents/headings")
    longest = max((len(c["paras"]) for c in chapters), default=0)
    if chapters and longest > 0.7 * q["paras"] and len(chapters) > 3:
        w.append("one chapter holds >70% of the text: chapter split is unreliable")
    frag = sum(1 for c in chapters for k in c.get("kinds", []) if k == "fragment")
    q["fragment_paras"] = frag
    if frag > 0.05 * max(1, len(paras)):
        w.append(f"equation/figure heavy: {frag} collapsed fragments; formulas are NOT readable from this PDF's text layer, do not quote or explain them from the text")
    if info.get("chars_per_page") and info["chars_per_page"] < 300:
        w.append(f"only {info['chars_per_page']} text chars per page: partly scanned or mostly figures; check coverage")
    q["ok"] = q["paras"] >= 20 and q["mojibake_ratio"] <= 0.05
    return q


def write_ir(chapters, images, reader, info, src_path, out_dir, title=None, fmt=None, zotero=None):
    os.makedirs(out_dir, exist_ok=True)
    img_dir = os.path.join(out_dir, "img")
    written = 0
    for k, (ch, im, src) in enumerate(images):
        try:
            if src is not None:
                data = reader(src)
                ext = posixpath.splitext(src)[1].lower() or ".jpg"
            else:
                data, ext = im.pop("data", None) or b"", "." + im.pop("ext", "png")
            if not data:
                continue
            name = f"i{k:04d}-{hashlib.sha1(data).hexdigest()[:8]}{ext}"
            os.makedirs(img_dir, exist_ok=True)
            with open(os.path.join(img_dir, name), "wb") as f:
                f.write(data)
            ch.setdefault("images", []).append({"after": im["after"], "src": "img/" + name, "bytes": len(data),
                                                **({"w": im["w"], "h": im["h"]} if im.get("w") else {})})
            written += 1
        except KeyError:
            continue
    out_ch = []
    for c in chapters:
        rec = {"title": c["title"], "paras": c["paras"]}
        if any(k == "heading" for k in c.get("kinds", [])):
            rec["heads"] = [i for i, k in enumerate(c["kinds"]) if k == "heading"]
        if any(k == "fragment" for k in c.get("kinds", [])):
            rec["frags"] = [i for i, k in enumerate(c["kinds"]) if k == "fragment"]
        if c.get("images"):
            rec["images"] = c["images"]
        out_ch.append(rec)
    q = quality(chapters, info, fmt)
    q["images"] = written
    t = title or info.get("title") or os.path.splitext(os.path.basename(src_path))[0]
    slug = re.sub(r'[\\/:*?"<>|]', " ", t).strip()[:80]
    book = {"extractor": EXTRACTOR, "title": t, "slug": slug, "author": info.get("author", ""),
            "language": info.get("language", ""), "format": fmt, "source": src_path,
            "source_sha1": _sha1(src_path), "zotero": zotero, "chapters": out_ch,
            "total_paras": sum(len(c["paras"]) for c in out_ch), "quality": q}
    with open(os.path.join(out_dir, "book.json"), "w", encoding="utf-8") as f:
        json.dump(book, f, ensure_ascii=False)
    return book


def _sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(path, out_dir, title=None, with_images=True, zotero=None):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".epub":
        chapters, images, reader, info = extract_epub(path, with_images)
    elif ext == ".pdf":
        chapters, images, reader, info = extract_pdf(path, with_images)
    else:
        raise ValueError(f"unsupported format {ext}; convert AZW3/MOBI to EPUB first (e.g. calibre ebook-convert)")
    if zotero:
        info["title"] = zotero.get("title") or info.get("title")
        info["author"] = zotero.get("author") or info.get("author")
    return write_ir(chapters, images, reader, info, os.path.abspath(path), out_dir, title, ext[1:], zotero)


# ---------------------------------------------------------------- Zotero (read-only, local sqlite)
def zotero_data_dir(explicit=None):
    if explicit:
        return explicit
    if os.environ.get("ZOTERO_DATA_DIR"):
        return os.environ["ZOTERO_DATA_DIR"]
    home = os.path.expanduser("~")
    for prof_root in [os.path.join(os.environ.get("APPDATA", ""), "Zotero", "Zotero", "Profiles"),
                      os.path.join(home, "Library", "Application Support", "Zotero", "Profiles"),
                      os.path.join(home, ".zotero", "zotero")]:
        if os.path.isdir(prof_root):
            for prof in os.listdir(prof_root):
                prefs = os.path.join(prof_root, prof, "prefs.js")
                if os.path.exists(prefs):
                    m = re.search(r'extensions\.zotero\.dataDir",\s*"(.+?)"\)', open(prefs, encoding="utf-8", errors="ignore").read())
                    if m:
                        return m.group(1).replace("\\\\", "\\")
    return os.path.join(home, "Zotero")


def _base_attachment_path():
    for prof_root in [os.path.join(os.environ.get("APPDATA", ""), "Zotero", "Zotero", "Profiles"),
                      os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Zotero", "Profiles")]:
        if os.path.isdir(prof_root):
            for prof in os.listdir(prof_root):
                prefs = os.path.join(prof_root, prof, "prefs.js")
                if os.path.exists(prefs):
                    m = re.search(r'extensions\.zotero\.baseAttachmentPath",\s*"(.+?)"\)', open(prefs, encoding="utf-8", errors="ignore").read())
                    if m:
                        return m.group(1).replace("\\\\", "\\")
    return None


def _open_db(data_dir):
    """Read a snapshot copy: Zotero holds an exclusive lock on zotero.sqlite while running."""
    src = os.path.join(data_dir, "zotero.sqlite")
    if not os.path.exists(src):
        raise FileNotFoundError(f"no zotero.sqlite in {data_dir} (set --data-dir or ZOTERO_DATA_DIR)")
    tmp = os.path.join(tempfile.gettempdir(), "bookir-zotero-snapshot.sqlite")
    shutil.copyfile(src, tmp)
    for suffix in ("-wal",):
        if os.path.exists(src + suffix):
            shutil.copyfile(src + suffix, tmp + suffix)
    return sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)


BOOK_TYPES = ("book", "bookSection")
FILE_TYPES = {"application/epub+zip": "epub", "application/pdf": "pdf"}


def zotero_books(data_dir=None, query=None, all_types=False):
    data_dir = zotero_data_dir(data_dir)
    db = _open_db(data_dir)
    base = _base_attachment_path()
    field = lambda name: f"""(select v.value from itemData d join fields f using(fieldID) join itemDataValues v using(valueID)
                              where d.itemID=p.itemID and f.fieldName='{name}')"""
    sql = f"""
    select p.key, t.typeName, {field('title')}, {field('date')},
           (select group_concat(coalesce(c.lastName,'')||char(31)||coalesce(c.firstName,''), char(30)) from
              (select c.lastName, c.firstName from itemCreators ic join creators c using(creatorID)
               where ic.itemID=p.itemID order by ic.orderIndex) c),
           a.key, ia.contentType, ia.path, ia.linkMode
    from items p join itemTypes t using(itemTypeID)
    join itemAttachments ia on ia.parentItemID=p.itemID join items a on a.itemID=ia.itemID
    where ia.contentType in ('application/epub+zip','application/pdf')
      and p.itemID not in (select itemID from deletedItems) and a.itemID not in (select itemID from deletedItems)
    """
    rows = db.execute(sql).fetchall()
    books = {}
    for key, typ, title, date, creators, akey, ctype, apath, link in rows:
        if not all_types and typ not in BOOK_TYPES:
            continue
        creators = _names(creators)
        if query and query.lower() not in f"{title} {creators}".lower():
            continue
        path = None
        if apath:
            if apath.startswith("storage:"):
                path = os.path.join(data_dir, "storage", akey, apath[len("storage:"):])
            elif apath.startswith("attachments:") and base:
                path = os.path.join(base, apath[len("attachments:"):])
            else:
                path = apath
        b = books.setdefault(key, {"item_key": key, "type": typ, "title": title or "", "date": date or "",
                                   "author": creators or "", "files": []})
        b["files"].append({"attachment_key": akey, "format": FILE_TYPES[ctype], "path": path,
                           "exists": bool(path and os.path.exists(path)), "link_mode": link})
    return list(books.values())


def _names(packed):
    """'Last\\x1fFirst\\x1e...' -> '黑塞、Donald A. Neamen' (CJK: 姓名 joined; Latin: First Last)."""
    out = []
    for one in (packed or "").split("\x1e"):
        last, _, first = one.partition("\x1f")
        last, first = last.strip(), first.strip()
        if RE_CJK_CHAR.search(last + first):
            out.append(last + first)
        else:
            out.append(" ".join(x for x in (first, last) if x))
    return "、".join(x for x in out if x)


def pick_file(book, prefer="epub"):
    order = [prefer, "pdf" if prefer == "epub" else "epub"]
    files = [f for f in book["files"] if f["exists"]]
    for fmt in order:
        cand = [f for f in files if f["format"] == fmt]
        if cand:
            return max(cand, key=lambda f: os.path.getsize(f["path"]))
    return None


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("source")
    e.add_argument("out")
    e.add_argument("--title")
    e.add_argument("--no-images", action="store_true")
    zl = sub.add_parser("zotero-list")
    zl.add_argument("--query")
    zl.add_argument("--data-dir")
    zl.add_argument("--all-types", action="store_true", help="include non-book items (reports, theses...)")
    zl.add_argument("--json", action="store_true")
    zx = sub.add_parser("zotero-extract")
    zx.add_argument("item_key")
    zx.add_argument("out")
    zx.add_argument("--data-dir")
    zx.add_argument("--prefer", choices=["epub", "pdf"], default="epub")
    zx.add_argument("--no-images", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        if a.cmd == "extract":
            book = extract(a.source, a.out, a.title, not a.no_images)
        elif a.cmd == "zotero-list":
            books = zotero_books(a.data_dir, a.query, a.all_types)
            if a.json:
                print(json.dumps(books, ensure_ascii=False, indent=1))
            else:
                for b in books:
                    fmts = ",".join(sorted({f["format"] + ("" if f["exists"] else "(missing)") for f in b["files"]}))
                    print(f"{b['item_key']}  [{fmts}]  {b['title'][:60]} — {b['author'][:30]}")
                print(f"{len(books)} items with EPUB/PDF attachments", file=sys.stderr)
            return 0
        else:
            books = {b["item_key"]: b for b in zotero_books(a.data_dir, all_types=True)}
            b = books.get(a.item_key)
            if not b:
                print(f"error: item {a.item_key} has no EPUB/PDF attachment in Zotero", file=sys.stderr)
                return 2
            f = pick_file(b, a.prefer)
            if not f:
                print("error: attachment files are not on this machine: " + "; ".join(str(x["path"]) for x in b["files"]), file=sys.stderr)
                return 2
            book = extract(f["path"], a.out, b["title"] or None, not a.no_images,
                           zotero={"item_key": b["item_key"], "attachment_key": f["attachment_key"], "title": b["title"], "author": b["author"], "date": b["date"]})
    except ScanError as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}, ensure_ascii=False))
        return 3
    q = book["quality"]
    print(json.dumps({"ok": q["ok"], "ir": os.path.abspath(a.out), "title": book["title"], "format": book["format"],
                      **{k: q[k] for k in ("chapters", "paras", "chars", "median_para_chars", "giant_paras", "images", "toc_entries")},
                      "warnings": q["warnings"]}, ensure_ascii=False, indent=1))
    return 0 if q["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
