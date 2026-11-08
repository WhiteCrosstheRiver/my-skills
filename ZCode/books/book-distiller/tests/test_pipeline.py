# -*- coding: utf-8 -*-
"""End-to-end tests: EPUB/PDF -> Book IR -> distill check -> HTML. Run: python -m pytest tests"""
import json
import os
import subprocess
import sys
import zipfile

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import bookir  # noqa: E402
from check_distill import check, merge  # noqa: E402

LONG = "河水在清晨流过渡口，船夫数着来往的人，他说每一个过河的人都带着一个没有说出口的问题。"


def make_epub(path):
    ch1 = f"""<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>x</title>
<style>p{{color:red}}</style></head><body>
<div class="chapter"><h2 id="c1">第一章 渡口</h2>
<div class="sec"><p>{LONG}</p><p>他在
<ruby>渡<rt>dù</rt></ruby>口
  坐了一整天。Siddhartha  sat
   by the river.</p>
<div><p>{LONG}第三段。</p></div></div>
<p>&#x4E00;段带实体&amp;符号的话。</p>
<img src="../Images/pic.png"/>
<h3 id="s2">第二节</h3><p>{LONG}第二节正文。</p></div></body></html>"""
    ch2 = """<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><body>
<h2>短诗</h2><p class="poem">河在流<br/>人在等<br/>船不来</p><p>完。</p></body></html>"""
    opf = """<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>渡口之书</dc:title><dc:creator>无名氏</dc:creator><dc:language>zh</dc:language></metadata>
<manifest><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
<item id="c1" href="Text/ch1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="Text/ch2.xhtml" media-type="application/xhtml+xml"/>
<item id="img" href="Images/pic.png" media-type="image/png"/></manifest>
<spine toc="ncx"><itemref idref="c1"/><itemref idref="c2"/></spine></package>"""
    ncx = """<?xml version="1.0"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap>
<navPoint id="n1" playOrder="1"><navLabel><text>第一章 渡口</text></navLabel><content src="Text/ch1.xhtml#c1"/>
  <navPoint id="n2" playOrder="2"><navLabel><text>第二节</text></navLabel><content src="Text/ch1.xhtml#s2"/></navPoint></navPoint>
<navPoint id="n3" playOrder="3"><navLabel><text>短诗</text></navLabel><content src="Text/ch2.xhtml"/></navPoint>
</navMap></ncx>"""
    container = """<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>"""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", container)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/toc.ncx", ncx)
        z.writestr("OEBPS/Text/ch1.xhtml", ch1)
        z.writestr("OEBPS/Text/ch2.xhtml", ch2)
        z.writestr("OEBPS/Images/pic.png", b"\x89PNG\r\n\x1a\n" + os.urandom(20000))


def test_epub_structure(tmp_path):
    src = tmp_path / "b.epub"
    make_epub(src)
    book = bookir.extract(str(src), str(tmp_path / "ir"))
    chs = book["chapters"]
    assert [c["title"] for c in chs] == ["第一章 渡口", "短诗"]  # level-1 TOC; fragment #c1 located
    p = chs[0]["paras"]
    assert p[0] == LONG                                  # nested divs did not merge paragraphs
    assert "渡口坐了一整天" in p[1] and "dù" not in p[1]  # CJK gaps removed, ruby reading dropped
    assert "Siddhartha sat by the river." in p[1]        # Latin spaces kept, collapsed
    assert p[2].endswith("第三段。")
    assert "一段带实体&符号的话。" == p[3]
    assert "第二节" in p and chs[0]["heads"] == [p.index("第二节")]
    assert chs[1]["paras"] == ["河在流\n人在等\n船不来", "完。"]  # short chapter kept, <br> kept
    assert chs[0]["images"][0]["after"] == 3 and os.path.exists(tmp_path / "ir" / chs[0]["images"][0]["src"])
    assert book["author"] == "无名氏" and book["extractor"] == "bookir/2"
    assert all("color:red" not in x for c in chs for x in c["paras"])


def make_pdf(path):
    import pymupdf
    doc = pymupdf.open()
    font = pymupdf.Font("helv")
    body = ("The ferryman counted the travellers who crossed the river every morn-\ning and wrote "
            "their questions in a small book that he kept dry under the bench.")
    toc = []
    for chap in range(3):
        for k in range(2):
            page = doc.new_page()
            page.insert_text((72, 40), "THE RIVER BOOK", fontsize=8)  # running head
            page.insert_text((300, 800), str(len(doc)), fontsize=8)  # page number
            y = 90
            if k == 0:
                page.insert_text((72, y), f"Chapter {chap + 1}", fontsize=20)
                toc.append([1, f"Chapter {chap + 1}", len(doc)])
                y += 50
            for para in range(3):
                tw = pymupdf.TextWriter(page.rect)
                rect = pymupdf.Rect(72, y, 520, y + 70)
                text = body if para < 2 else body.replace("bench.", "bench and then")
                if k == 1 and para == 0:
                    text = "rowed back alone. " + body
                tw.fill_textbox(rect, text, font=font, fontsize=11)
                tw.write_text(page)
                y += 90
            if k == 0:  # continuation at top of next page
                pass
    doc.set_toc(toc)
    doc.save(path)


def test_pdf_structure(tmp_path):
    pytest.importorskip("pymupdf")
    src = tmp_path / "b.pdf"
    make_pdf(src)
    book = bookir.extract(str(src), str(tmp_path / "ir"))
    chs = book["chapters"]
    assert [c["title"] for c in chs] == ["Chapter 1", "Chapter 2", "Chapter 3"]
    text = "\n".join(p for c in chs for p in c["paras"])
    assert "THE RIVER BOOK" not in text                 # running head removed
    assert "morning" in text and "morn-" not in text   # dehyphenated
    assert not any(p.strip().isdigit() for c in chs for p in c["paras"])  # page numbers removed
    # "bench and then" continues on the next page: joined, not a separate paragraph
    assert any("bench and then rowed back alone." in p for p in chs[0]["paras"])
    assert not any(p.startswith("rowed") for c in chs for p in c["paras"])
    assert book["quality"]["giant_paras"] == 0


def distill_for(book):
    p0 = book["chapters"][0]["paras"]
    return {
        "subtitle": "测试",
        "entry": {"0": {"q": "渡口意味着什么?", "route": ["渡口", "等待"], "keys": [{"text": "河是时间", "at": 0}, "人带着问题"], "time": 3}},
        "notes": {"0": [{"at": 0, "tag": "KEY", "text": "问题即渡口", "quote": "没有说出口的问题"},
                        {"at": 0, "tag": "MOTIF", "text": "第二条同段边注", "quote": "船夫数着来往的人"}],
                  "1": [[0, "KEY", "旧格式边注", "", "人在等\n船不来"]]},
        "quiz": {"0": [{"q": "q1", "a": ["x", "y"], "correct": 1, "fb": "f"}, {"q": "q2", "a": "open"}]},
        "concepts": [{"id": "ferry", "name": "渡口", "en": "ferry", "one": "过河处", "first": [0, 1]}],
    }


def test_check_distill_errors_and_fix(tmp_path):
    src = tmp_path / "b.epub"
    make_epub(src)
    book = bookir.extract(str(src), str(tmp_path / "ir"))
    D = distill_for(book)
    errs, warns, _ = check(book, json.loads(json.dumps(D)))
    assert not errs and any("not the earliest occurrence" in w for w in warns)  # [0,1] has it, [0,0] is earlier
    D["concepts"][0]["first"] = [1, 0]                    # 短诗 never mentions 渡口
    errs, _, _ = check(book, D)
    assert any("'first'" in e for e in errs)
    errs, _, _ = check(book, D, fix=True)
    assert not errs and D["concepts"][0]["first"] == [0, 0]
    bad = distill_for(book)
    bad["notes"]["0"][0]["quote"] = "这句话书里根本没有出现过"
    bad["notes"]["0"].append({"at": 99, "tag": "KEY", "text": "x", "quote": "y"})
    bad["concepts"].append({"id": "x", "name": "不存在的概念", "one": "?"})
    bad["notes"]["0"].append({"at": 1, "tag": "KEY", "text": "no quote"})
    errs, _, _ = check(book, bad)
    joined = "\n".join(errs)
    assert "invented or paraphrased" in joined and "out of range" in joined
    assert "not an exact substring" in joined and "missing 'quote'" in joined


def test_merge_parts_and_build(tmp_path):
    src = tmp_path / "b.epub"
    make_epub(src)
    ir = tmp_path / "ir"
    book = bookir.extract(str(src), str(ir))
    D = distill_for(book)
    parts = tmp_path / "parts"
    parts.mkdir()
    (parts / "book.json").write_text(json.dumps({"subtitle": "测试", "concepts": D["concepts"]}, ensure_ascii=False), encoding="utf-8")
    (parts / "ch-000.json").write_text(json.dumps({"chapter": 0, "entry": D["entry"]["0"], "notes": D["notes"]["0"], "quiz": D["quiz"]["0"]}, ensure_ascii=False), encoding="utf-8")
    (parts / "ch-001.json").write_text(json.dumps({"chapter": 1, "notes": D["notes"]["1"],
                                                   "concepts": [{"id": "ferry2", "name": "渡口", "one": "dup", "rel": ["河"]}]}, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "d.json"
    r = subprocess.run([sys.executable, os.path.join(HERE, "check_distill.py"), "merge", str(ir), str(parts), str(out)], capture_output=True, text=True, encoding="utf-8")
    rep = json.loads(r.stdout)
    assert rep["ok"], rep
    merged = json.loads(out.read_text(encoding="utf-8"))
    assert len(merged["concepts"]) == 1 and merged["concepts"][0]["rel"] == ["河"]
    html_path = tmp_path / "out" / "x.html"
    r = subprocess.run([sys.executable, os.path.join(HERE, "build_book.py"), str(ir), str(out), str(html_path), "<渡口>"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    h = html_path.read_text(encoding="utf-8")
    assert "&lt;渡口&gt;" in h and "<title><渡口>" not in h
    assert "data:image/png;base64" in h
    # a broken distill is refused
    merged["notes"]["0"][0]["quote"] = "编造"
    out.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, os.path.join(HERE, "build_book.py"), str(ir), str(out), str(html_path)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "quote" in r.stderr


def test_read_ir_pages_whole_chapter(tmp_path):
    src = tmp_path / "b.epub"
    make_epub(src)
    ir = tmp_path / "ir"
    bookir.extract(str(src), str(ir))
    r = subprocess.run([sys.executable, os.path.join(HERE, "read_ir.py"), "chapter", str(ir), "0", "--max-chars", "60"],
                       capture_output=True, text=True, encoding="utf-8")
    assert "[0.0]" in r.stdout and "--from 1" in r.stdout
    r = subprocess.run([sys.executable, os.path.join(HERE, "read_ir.py"), "find", str(ir), "船不来"], capture_output=True, text=True, encoding="utf-8")
    assert "[1.0]" in r.stdout


def _para(text):
    return {"kind": "para", "text": text, "size": 10, "page": 1}


def test_formula_fragments_collapse_but_prose_survives():
    prose = "The energy calculated from this equation is the expectation value of the operator."
    glyphs = ["X", "n i¼1", "H", "(5.23)"]
    out = bookir._collapse_fragments([_para(prose)] + [_para(g) for g in glyphs] + [_para(prose)])
    assert [b["kind"] for b in out] == ["para", "fragment", "para"]
    assert out[1]["text"] == "X n i¼1 H (5.23)"          # kept and searchable, not deleted
    short_run = bookir._collapse_fragments([_para(prose), _para("H"), _para(prose)])
    assert [b["kind"] for b in short_run] == ["para", "para", "para"]  # an isolated short line stays


def test_real_short_sentences_are_not_fragments():
    for t in ["He was gone.", "他走了,没有回头。" * 2, "Then the river spoke to him quietly"]:
        assert not bookir._is_fragment(_para(t)), t


def test_no_toc_prefers_chapter_titles_over_section_heads():
    def head(t, size):
        return {"kind": "heading", "text": t, "size": size, "page": 1}
    s = [head("Chapter 1 Basics", 20), head("1.1 Definitions", 14), head("1.2 Units", 14), head("Chapter 2 More", 20),
         head("2.1 Theory", 14), head("Chapter 3 End", 20)]
    assert [t for _, t in bookir._heading_cuts(s)] == ["Chapter 1 Basics", "Chapter 2 More", "Chapter 3 End"]
    tiers = [head("Basics", 20), head("Sec a", 14), head("Theory", 20), head("Sec b", 14), head("End", 20)]
    assert [t for _, t in bookir._heading_cuts(tiers)] == ["Basics", "Theory", "End"]


def test_per_chapter_running_head_removed():
    def page(*texts):
        return [{"kind": "text", "lines": [{"text": t}], "rel_top": 0.04, "rel_bot": 0.06} for t in texts]
    pages = [page("5 Ab initio Calculations")] * 3 + [page("One-off caption")] + [[] for _ in range(500)]
    found = bookir._page_furniture(pages)
    assert bookir._furniture_key("5 Ab initio Calculations") in found           # 3 of 504 pages
    assert bookir._furniture_key("One-off caption") not in found
