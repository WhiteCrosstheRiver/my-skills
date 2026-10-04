# -*- coding: utf-8 -*-
"""v2 图片抽取:在不动 paras 的前提下给 book.json 旁挂 per-chapter images 列表。
- EPUB:重放 v1 章节装配逻辑(逐字节一致),img 标签按正文顺序锚定"第 k 段之后"
- PDF:重放 v1 章节切分,get_text("dict") 的图像块按页内 y 序 + 前置文本块锚定
- 过滤:<10KB、短边<100px、全书出现>3 次(页眉/花线);>4MB 用 PIL 缩到长边 1600
用法:
  python extract_images_v2.py --verify <ir_idx_dir>   # 只验证 paras 与 v1 一致,不写
  python extract_images_v2.py --apply  <ir_idx_dir>   # 写入 book.json v2 + img/ 文件
"""
import zipfile, re, os, sys, json, html, io, struct, posixpath, hashlib

IMG_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
MIN_BYTES = 10 * 1024
MIN_SIDE = 100
MAX_BYTES = 4 * 1024 * 1024

def _img_re():
    return re.compile(r'<img\b[^>]*?src="([^"]+)"|<image\b[^>]*?xlink:href="([^"]+)"', re.I)

def _clean_src(s):
    return html.unescape(s.split("#")[0].split("?")[0]).strip()

# ---------- 尺寸/字节工具 ----------
def _png_size(b):
    if b[:8] == b'\x89PNG\r\n\x1a\n' and len(b) > 24:
        return struct.unpack(">II", b[16:24])
    return None

def _jpg_size(b):
    i = 2
    while i < len(b) - 9:
        if b[i] != 0xFF: i += 1; continue
        mk = b[i + 1]
        if 0xC0 <= mk <= 0xCF and mk not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", b[i + 5:i + 9]); return (w, h)
        i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    return None

def _gif_size(b):
    if b[:4] == b'GIF8' and len(b) > 10:
        w, h = struct.unpack("<HH", b[6:10]); return (w, h)
    return None

def _dim(b, ext=""):
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(b)); return im.size
    except Exception:
        pass
    return _png_size(b) or _jpg_size(b) or _gif_size(b)

def _shrink(b):
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(b))
        im.thumbnail((1600, 1600))
        ob = io.BytesIO()
        (im.convert("RGB") if im.mode not in ("RGB", "L") else im).save(ob, "JPEG", quality=80)
        return ob.getvalue(), ".jpg"
    except Exception:
        return None, None

# ---------- EPUB v2 ----------
def _epub_doc_paras_images(body):
    """与 v1 epub_paras 同源的段落流 + 顺带图片锚点。返回 (paras, imgs[(after, src)])
    图片无论是否在产出段落内都扫(常见 <div><img/></div> 无文字);锚点=当前已产出段落数"""
    paras, imgs = [], []
    pos = 0
    for m in re.finditer(r"<(p|div|h[1-6]|blockquote)[^>]*>(.*?)</\1>", body, re.S):
        for im in _img_re().finditer(body[pos:m.start()]):
            imgs.append((len(paras), _clean_src(im.group(1) or im.group(2))))
        t = re.sub(r"<[^>]+>", "", m.group(2))
        t = html.unescape(t).strip()
        t2 = re.sub(r"[ \t\r\n]+", "", t) if re.search(r"[\u4e00-\u9fff]", t) else re.sub(r"\s+", " ", t).strip()
        if t2 and len(t2) > 1:
            paras.append(t2)
        for im in _img_re().finditer(m.group(2)):
            imgs.append((len(paras), _clean_src(im.group(1) or im.group(2))))
        pos = m.end()
    for im in _img_re().finditer(body[pos:]):
        imgs.append((len(paras), _clean_src(im.group(1) or im.group(2))))
    return paras, imgs

def epub_chapters_v2(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    opf = next((n for n in names if n.endswith(".opf")), None)
    ox = z.read(opf).decode("utf-8", "ignore")
    base = os.path.dirname(opf).replace("\\", "/")
    id2href = {}
    for m in re.finditer(r'<item\b[^>]*>', ox):
        i = re.search(r'id="([^"]+)"', m.group(0)); h = re.search(r'href="([^"]+)"', m.group(0))
        if i and h:
            id2href[i.group(1)] = posixpath.normpath(posixpath.join(base, h.group(1))).replace("\\", "/")
    spine = []
    sp = re.search(r'<spine[^>]*>(.*?)</spine>', ox, re.S)
    if sp:
        for m in re.finditer(r'itemref[^>]*idref="([^"]+)"', sp.group(1)):
            if m.group(1) in id2href: spine.append(id2href[m.group(1)])
    if not spine:
        spine = sorted(n for n in names if re.search(r"\.(x?html|htm)$", n))
    # toc titles(v1 同款,只为复刻合并分支)
    toc_titles = {}
    ncx = next((n for n in names if n.endswith(".ncx")), None)
    if ncx:
        nb = os.path.dirname(ncx).replace("\\", "/")
        for m in re.finditer(r'<navPoint.*?<text>(.*?)</text>.*?content src="([^"]+)"', z.read(ncx).decode("utf-8", "ignore"), re.S):
            src = posixpath.normpath(posixpath.join(nb, m.group(2).split("#")[0])).replace("\\", "/")
            toc_titles[src] = html.unescape(m.group(1)).strip()
    if not toc_titles:
        nav = next((n for n in names if n.endswith("nav.xhtml") or re.search(r"nav\d*\.x?html$", n)), None)
        if nav:
            nx = z.read(nav).decode("utf-8", "ignore")
            nb = os.path.dirname(nav).replace("\\", "/")
            for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', nx, re.S):
                t = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
                src = posixpath.normpath(posixpath.join(nb, m.group(1).split("#")[0])).replace("\\", "/")
                toc_titles.setdefault(src, t)
    chapters, seen_titles = [], set()
    raw_imgs = []  # (chapter_idx, after, zip_src)
    pending_head = []  # 被跳过文档的图,挂到下一章开头
    for n in spine:
        if n not in names or len(z.read(n)) > 3_000_000: continue
        x = z.read(n)
        for enc in ("utf-8", "gbk", "utf-16"):
            try: x = x.decode(enc); break
            except UnicodeDecodeError: continue
        else: x = x.decode("utf-8", "ignore")
        bm = re.search(r"<body[^>]*>(.*)</body>", x, re.S)
        body = bm.group(1) if bm else x
        paras, imgs = _epub_doc_paras_images(body)
        if len(paras) < 3:
            all_prev = sum(len(c["paras"]) for c in chapters)
            for after, src in imgs:
                if chapters:
                    raw_imgs.append((len(chapters) - 1, all_prev, posixpath.normpath(posixpath.join(posixpath.dirname(n), src)).replace("\\", "/")))
                else:
                    pending_head.append(posixpath.normpath(posixpath.join(posixpath.dirname(n), src)).replace("\\", "/"))
            continue
        ci = None
        if len(paras) < 12 and chapters and len(toc_titles) == 0:
            ci = len(chapters) - 1
            chapters[ci]["paras"] += paras
        else:
            title = toc_titles.get(n) or re.sub(r"\.(x?html|htm)$", "", os.path.basename(n))
            if title in seen_titles: title = title + f" ({len(chapters)+1})"
            seen_titles.add(title)
            chapters.append({"title": title, "paras": paras})
            ci = len(chapters) - 1
        base_count = sum(len(c["paras"]) for c in chapters[:ci])
        for src in pending_head:
            raw_imgs.append((ci, -1, src))
        pending_head = []
        for after, src in imgs:
            raw_imgs.append((ci, base_count + after, posixpath.normpath(posixpath.join(posixpath.dirname(n), src)).replace("\\", "/")))
    return chapters, raw_imgs, z

# ---------- PDF v2 ----------
def _norm_snip(s, n=12):
    s = re.sub(r"\s+", "", s)
    return s[:n]

def pdf_chapters_v2(path):
    import pymupdf
    doc = pymupdf.open(path)
    pages = [p.get_text("text") for p in doc]
    toc = doc.get_toc()
    spans = []  # (chapter_idx, [(page_no0, start_off, end_off)]) 之后用于锚定
    chapters = []
    if toc and len(toc) >= 2:
        lv1 = [t for t in toc if t[0] == 1] or toc
        for i, (lvl, title, pg) in enumerate(lv1):
            end = lv1[i + 1][2] - 1 if i + 1 < len(lv1) else len(pages)
            a, b = max(0, pg - 1), max(pg, end)
            txt = "\n".join(pages[a:b])
            paras = [re.sub(r"\s+", " ", s).strip() for s in re.split(r"\n\s*\n|(?<=[。!?…」])\n", txt) if s.strip() and len(s.strip()) > 1]
            if len(paras) >= 2:
                spans.append((a, b))
                chapters.append({"title": title.strip() or f"第{i+1}章", "paras": paras, "_pages": (a, b)})
    if not chapters:
        for i in range(0, len(pages), 8):
            txt = "\n".join(pages[i:i + 8])
            paras = [re.sub(r"\s+", " ", s).strip() for s in re.split(r"\n\s*\n", txt) if s.strip() and len(s.strip()) > 1]
            if paras:
                chapters.append({"title": f"第 {i//8+1} 部分 (pp.{i+1}-{min(i+8,len(pages))})", "paras": paras, "_pages": (i, min(i + 8, len(pages)))})
    # 全书 xref 出现次数(页眉去重)
    xref_count = {}
    for p in doc:
        for im in p.get_images(full=True):
            xref_count[im[0]] = xref_count.get(im[0], 0) + 1
    raw_imgs = []  # (chapter_idx, after, bytes, ext, w, h)
    seen_hash = {}
    for ci, ch in enumerate(chapters):
        a, b = ch["_pages"]
        base_count = sum(len(c["paras"]) for c in chapters[:ci])
        ch_paras = ch["paras"]
        for pno in range(a, b):
            try: d = doc[pno].get_text("dict")
            except Exception: continue
            tblocks, iblocks = [], []
            for blk in d["blocks"]:
                if blk["type"] == 0:
                    t = " ".join("".join(s["text"] for s in ln["spans"]) for ln in blk["lines"]).strip()
                    if t: tblocks.append((blk["bbox"][1], t))
                else:
                    iblocks.append(blk)
            for blk in iblocks:
                bts = blk.get("image")
                if not bts: continue
                w, h = blk.get("width") or 0, blk.get("height") or 0
                y0 = blk["bbox"][1]
                cand = [t for (ty, t) in tblocks if ty <= y0 + 10]
                anchor = None
                if cand:
                    snip = _norm_snip(cand[-1])
                    if len(snip) >= 6:
                        for k in range(len(ch_paras) - 1, -1, -1):
                            if snip in ch_paras[k]: anchor = k; break
                if anchor is None:
                    # 回退:含本页文本片段的最后一个段落
                    ptxt = _norm_snip(pages[pno], 16) if False else None
                    anchor = None
                    for k in range(len(ch_paras) - 1, -1, -1):
                        if _norm_snip(pages[pno]) and _norm_snip(pages[pno])[:10] and _norm_snip(pages[pno])[:10] in _norm_snip(ch_paras[k]):
                            anchor = k; break
                if anchor is None:
                    anchor = max(0, len(ch_paras) - 1)
                hsh = hashlib.md5(bts).hexdigest()
                seen_hash[hsh] = seen_hash.get(hsh, 0) + 1
                raw_imgs.append((ci, base_count + anchor, bts, blk.get("ext", "png"), w, h, hsh))
    return chapters, raw_imgs, doc, seen_hash

# ---------- 组装 ----------
def build_v2(idx_dir, apply=True):
    bp = os.path.join(idx_dir, "book.json")
    book = json.load(open(bp, encoding="utf8"))
    src = book["source"]
    fmt = os.path.splitext(src)[1].lower()
    imgdir = os.path.join(idx_dir, "img")
    kept = {}   # out_name -> bytes
    per_ch = None
    if fmt == ".epub":
        chapters, raw, z = epub_chapters_v2(src)
        names = set(z.namelist())
        # 出现次数(按内容 hash)去页眉
        hashcount = {}
        resolved = []
        for ci, after, zp in raw:
            if zp not in names: continue
            b = z.read(zp)
            hsh = hashlib.md5(b).hexdigest()
            hashcount[hsh] = hashcount.get(hsh, 0) + 1
            resolved.append((ci, after, zp, b, hsh))
        resolved = [r for r in resolved if hashcount[r[4]] <= 3]
        # 分配文件名
        entries = []
        n = 0
        for ci, after, zp, b, hsh in resolved:
            ext = os.path.splitext(zp)[1].lower() or ".jpg"
            kb = len(b)
            dim = _dim(b, ext)
            if kb < MIN_BYTES or (dim and min(dim) < MIN_SIDE): continue
            if kb > MAX_BYTES:
                nb, next_ = _shrink(b)
                if not nb: continue
                b, ext = nb, next_
            n += 1
            name = f"i{n:05d}{ext}"
            entries.append({"ch": ci, "after": after, "src": f"img/{name}", "w": (dim[0] if dim else None), "h": (dim[1] if dim else None), "bytes": len(b)})
            kept[name] = b
        per_ch = chapters
    else:
        chapters, raw, doc, hashcount = pdf_chapters_v2(src)
        entries = []
        n = 0
        for ci, after, b, ext, w, h, hsh in raw:
            if hashcount.get(hsh, 0) > 3: continue
            kb = len(b)
            if kb < MIN_BYTES or (w and min(w, h) < MIN_SIDE): continue
            if not w: w, h = (_dim(b, ext) or (None, None))[:2] or (None, None)
            if kb > MAX_BYTES:
                nb, next_ = _shrink(b)
                if not nb: continue
                b, ext = nb, next_
            n += 1
            name = f"i{n:05d}.{ext}"
            entries.append({"ch": ci, "after": after, "src": f"img/{name}", "w": w, "h": h, "bytes": len(b)})
            kept[name] = b
        per_ch = chapters
    # 校验 paras 与 v1 一致
    v1 = book["chapters"]
    ok = len(v1) == len(per_ch) and all(
        v1[i]["title"] == per_ch[i]["title"] and v1[i]["paras"] == per_ch[i]["paras"]
        for i in range(len(v1)))
    if not ok:
        return False, 0, f"paras mismatch: v1 {len(v1)} ch vs v2 {len(per_ch)} ch"
    # 组装 images 旁挂
    by_ch = {}
    for e in entries: by_ch.setdefault(e["ch"], []).append(e)
    total = 0
    for ci, ch in enumerate(book["chapters"]):
        imgs = by_ch.get(ci, [])
        if imgs:
            ch["images"] = [{"after": e["after"], "src": e["src"], "w": e["w"], "h": e["h"], "bytes": e["bytes"]} for e in imgs]
            total += sum(e["bytes"] for e in imgs)
        elif "images" in ch:
            del ch["images"]
    book["images_total"] = total
    if apply:
        if kept:
            os.makedirs(imgdir, exist_ok=True)
            for name, b in kept.items():
                open(os.path.join(imgdir, name), "wb").write(b)
        json.dump(book, open(bp, "w", encoding="utf8"), ensure_ascii=False)
    return True, total, f"{len(entries)} images, {total/1024/1024:.1f} MB"

if __name__ == "__main__":
    apply = "--apply" in sys.argv
    d = sys.argv[-1]
    ok, total, msg = build_v2(d, apply=apply)
    print(("APPLIED " if apply else "VERIFY  ") + ("OK " if ok else "FAIL ") + d, "|", msg)
