# -*- coding: utf-8 -*-
"""批量扫描 书籍文件夹 → 选最佳格式 → 抽取 Book IR → manifest.json
用法: python extract_batch.py [源目录] [输出根目录]
"""
import zipfile, re, json, html, os, sys, io, traceback

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\baidunetdiskdownload\书籍"
ROOT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.expanduser("~"), "Desktop", "蒸馏书库")
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch")
os.makedirs(WORK, exist_ok=True)

def pick_file(folder):
    best = None; best_rank = -1
    rank = {".epub": 4, ".pdf": 3, ".azw3": 1, ".mobi": 1}
    for dirpath, _, files in os.walk(folder):
        if any(x in dirpath for x in ("_MACOSX",)) : continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            r = rank.get(ext, 0)
            if r > best_rank:
                best_rank = r; best = os.path.join(dirpath, f)
            elif r == best_rank and r > 0 and len(f) > len(os.path.basename(best)):
                best = os.path.join(dirpath, f)
    return (best, best_rank) if best_rank >= 3 else None

def epub_paras(z, name):
    x = z.read(name)
    for enc in ("utf-8", "gbk", "utf-16"):
        try: x = x.decode(enc); break
        except UnicodeDecodeError: continue
    else: x = x.decode("utf-8", "ignore")
    body = re.search(r"<body[^>]*>(.*)</body>", x, re.S)
    body = body.group(1) if body else x
    out = []
    for m in re.finditer(r"<(p|div|h[1-6]|blockquote)[^>]*>(.*?)</\1>", body, re.S):
        t = re.sub(r"<[^>]+>", "", m.group(2))
        t = html.unescape(t).strip()
        if m.group(1).startswith("h"): t = t.strip()
        t2 = re.sub(r"[ \t\r\n]+", "", t) if re.search(r"[\u4e00-\u9fff]", t) else re.sub(r"\s+", " ", t).strip()
        if t2 and len(t2) > 1: out.append(t2)
    return out

def extract_epub(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    opf = None
    for n in names:
        if n.endswith(".opf"): opf = n; break
    spine, toc_titles = [], {}
    if opf:
        ox = z.read(opf).decode("utf-8", "ignore")
        base = os.path.dirname(opf)
        manifest = dict(re.findall(r'<item[^>]*id="([^"]+)"[^>]*href="([^"]+)"', ox) +
                        re.findall(r'<item[^>]*href="([^"]+)"[^>]*id="([^"]+)"', ox)[::-1] and [])
        id2href = {}
        for m in re.finditer(r'<item\b[^>]*>', ox):
            tag = m.group(0)
            i = re.search(r'id="([^"]+)"', tag); h = re.search(r'href="([^"]+)"', tag)
            if i and h: id2href[i.group(1)] = h.group(1)
        sp = re.search(r'<spine[^>]*>(.*?)</spine>', ox, re.S)
        if sp:
            for m in re.finditer(r'itemref[^>]*idref="([^"]+)"', sp.group(1)):
                href = id2href.get(m.group(1))
                if href: spine.append(os.path.normpath(os.path.join(base, href)).replace("\\", "/"))
        ncx = id2href.get("ncx")
        if ncx:
            ncx = os.path.normpath(os.path.join(base, ncx)).replace("\\", "/")
        if not (ncx and ncx in names):
            ncx = next((n for n in names if n.endswith(".ncx")), None)
        if ncx:
            try: nx = z.read(ncx).decode("utf-8", "ignore")
            except KeyError: nx = ""
            nb = os.path.dirname(ncx)
            for m in re.finditer(r'<navPoint.*?<text>(.*?)</text>.*?content src="([^"]+)"', nx, re.S):
                t = html.unescape(m.group(1)).strip()
                src = os.path.normpath(os.path.join(nb, m.group(2).split("#")[0])).replace("\\", "/")
                if t: toc_titles[src] = t
        if not toc_titles:  # EPUB3 nav
            nav = next((n for n in names if n.endswith("nav.xhtml") or re.search(r"nav\d*\.x?html$", n)), None)
            if nav:
                nx = z.read(nav).decode("utf-8", "ignore")
                nb = os.path.dirname(nav)
                for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', nx, re.S):
                    t = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
                    src = os.path.normpath(os.path.join(nb, m.group(1).split("#")[0])).replace("\\", "/")
                    if t: toc_titles.setdefault(src, t)
    if not spine:
        spine = sorted(n for n in names if re.search(r"\.(x?html|htm)$", n))
    chapters, seen = [], set()
    for n in spine:
        if n not in names or len(z.read(n)) > 3_000_000: continue
        paras = epub_paras(z, n)
        if len(paras) < 3: continue
        if len(paras) < 12 and chapters and len(toc_titles) == 0:  # fragment: merge into previous
            chapters[-1]["paras"] += paras; continue
        title = toc_titles.get(n) or re.sub(r"\.(x?html|htm)$", "", os.path.basename(n))
        if title in seen: title = title + f" ({len(chapters)+1})"
        seen.add(title)
        chapters.append({"title": title, "paras": paras})
    return chapters

def extract_pdf(path):
    import pymupdf
    doc = pymupdf.open(path)
    pages = []
    for p in doc:
        t = p.get_text("text")
        pages.append(t)
    # 按目录切章:优先 pdf toc,否则按页堆叠,每 ~8 页一章
    toc = doc.get_toc()
    chapters = []
    if toc and len(toc) >= 2:
        lv1 = [t for t in toc if t[0] == 1] or toc
        for i, (lvl, title, pg) in enumerate(lv1):
            end = lv1[i+1][2]-1 if i+1 < len(lv1) else len(pages)
            txt = "\n".join(pages[max(0,pg-1):max(pg, end)])
            paras = [re.sub(r"\s+", " ", s).strip() for s in re.split(r"\n\s*\n|(?<=[。!?…」])\n", txt) if s.strip() and len(s.strip()) > 1]
            if len(paras) >= 2: chapters.append({"title": title.strip() or f"第{i+1}章", "paras": paras})
    if not chapters:
        for i in range(0, len(pages), 8):
            txt = "\n".join(pages[i:i+8])
            paras = [re.sub(r"\s+", " ", s).strip() for s in re.split(r"\n\s*\n", txt) if s.strip() and len(s.strip()) > 1]
            if paras: chapters.append({"title": f"第 {i//8+1} 部分 (pp.{i+1}-{min(i+8,len(pages))})", "paras": paras})
    return chapters

def main():
    manifest = []
    outroot = ROOT
    os.makedirs(outroot, exist_ok=True)
    folders = sorted(d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d)))
    for idx, d in enumerate(folders):
        fpath = os.path.join(SRC, d)
        slug = re.sub(r'[\\/:*?"<>|]', " ", d).strip()[:80]
        out_html = os.path.join(outroot, slug + ".html")
        rec = {"folder": d, "slug": slug, "out": out_html, "status": "pending"}
        if os.path.exists(out_html):
            rec["status"] = "done"
            manifest.append(rec); continue
        picked = pick_file(fpath)
        if not picked:
            rec["status"] = "no_book"; manifest.append(rec); continue
        path = picked[0]
        rec["file"] = path; rec["fmt"] = os.path.splitext(path)[1].lower()
        irdir = os.path.join(WORK, "ir", f"{idx:04d}")
        try:
            if rec["fmt"] == ".epub": chapters = extract_epub(path)
            else: chapters = extract_pdf(path)
            total = sum(len(c["paras"]) for c in chapters)
            if total < 20:
                rec["status"] = "extract_fail"; manifest.append(rec); continue
            os.makedirs(irdir, exist_ok=True)
            json.dump({"title": d, "slug": slug, "idx": idx, "source": path,
                       "chapters": chapters, "total_paras": total},
                      open(os.path.join(irdir, "book.json"), "w", encoding="utf8"), ensure_ascii=False)
            rec["status"] = "ir_ready"; rec["ir"] = irdir
            rec["n_ch"] = len(chapters); rec["n_paras"] = total
        except Exception as e:
            rec["status"] = "extract_fail"; rec["err"] = str(e)[:200]
        manifest.append(rec)
        print(f"[{idx+1}/{len(folders)}] {rec['status']:>12} {d[:40]}")
    json.dump(manifest, open(os.path.join(WORK, "manifest.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(r["status"] for r in manifest))

if __name__ == "__main__":
    main()
