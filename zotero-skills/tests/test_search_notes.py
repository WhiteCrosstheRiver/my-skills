import json
from pathlib import Path

import httpx
import pytest
import pymupdf

from zotero_skills.core import Run, Network, digest, write_json, read_json
from zotero_skills.notes import SECTIONS, note_template, render_markdown, validate_note
from zotero_skills.search import Providers, collect_evidence, exported_records, merge_candidates, prepare_selected


def evidence(level="fulltext"):
    return {"item_key": "TEST0001", "library_id": 1, "title": "A test paper", "level": level, "abstract": "A short abstract with a clear limitation.", "metadata": {"title": "A test paper"}, "pages": [{"source": "PDF00001", "page": 2, "text": "The method reduces the test error by 20 percent under fixed conditions."}] if level == "fulltext" else []}


def valid_note(e):
    s = note_template(e).replace("status: draft", "status: complete")
    s = s.replace("待填写：依据 evidence.json，缺失信息明确说明。", "逐项阅读所得；全文不可得时仅使用摘要。[C1]")
    ref = {"source": "PDF00001", "page": 2, "excerpt": "reduces the test error by 20 percent"} if e["level"] == "fulltext" else {"source": "abstract", "excerpt": "abstract with a clear limitation"}
    return s, [{"id": "C1", "kind": "reported", "statement": "A limited result", "evidence": [ref]}]


def test_cross_provider_merge_retains_provenance_and_pdf():
    rows = [{"title": "A Paper", "doi": "https://doi.org/10.1/ABC", "year": 2020, "sources": ["a"]}, {"title": "A Paper", "doi": "10.1/abc", "year": 2020, "pdf_urls": ["https://x/p.pdf"], "sources": ["b"]}]
    out = merge_candidates(rows)
    assert len(out) == 1 and out[0]["sources"] == ["a", "b"]
    assert out[0]["pdf_urls"] == ["https://x/p.pdf"]


def test_title_collision_does_not_merge_different_dois():
    assert len(merge_candidates([{"title": "Same", "year": 2020, "doi": "10.1/a"}, {"title": "Same", "year": 2020, "doi": "10.1/b"}])) == 2


def test_semantic_pagination():
    class Net:
        def __init__(self): self.calls = []
        def get(self, url, params, **kwargs):
            self.calls.append(params)
            start = 1000 if params.get("token") else 0
            return {"data": [{"title": f"Paper {i}", "externalIds": {"DOI": f"10.1/{i}"}} for i in range(start, start + 1000)], "token": "page2" if start == 0 else None}
    net = Net()
    results = Providers(net).semantic("topic", 1201)
    assert len(results) == 1201 and results[-1]["title"] == "Paper 1200"
    assert len(net.calls) == 2 and net.calls[1]["token"] == "page2"


def test_crossref_pagination():
    class Net:
        def get(self, url, params):
            n = 0 if params["cursor"] == "*" else 100
            return {"message": {"items": [{"title": [str(i)], "DOI": f"10.1/{i}"} for i in range(n, n + params["rows"])], "next-cursor": "second"}}
    assert len(Providers(Net()).crossref("topic", 151)) == 151


def test_note_provenance_and_evidence_tiers():
    for level in ["fulltext", "abstract", "metadata"]:
        e = evidence(level)
        note, claims = valid_note(e)
        validate_note(note, claims, e)


def test_rejects_fabricated_excerpt_and_stale_source():
    e = evidence()
    note, claims = valid_note(e)
    claims[0]["evidence"][0]["excerpt"] = "This fabricated result never occurred."
    with pytest.raises(ValueError, match="Unverifiable"):
        validate_note(note, claims, e)


def test_rejects_library_mismatch_and_undefined_claim():
    e = evidence()
    note, claims = valid_note(e)
    with pytest.raises(ValueError, match="library_id"):
        validate_note(note.replace("library_id: 1", "library_id: 2"), claims, e)
    with pytest.raises(ValueError, match="Undefined"):
        validate_note(note + "\n[C999]", claims, e)
    note, claims = valid_note(e)
    e["abstract"] = "Revised evidence"
    with pytest.raises(ValueError, match="source_hash"):
        validate_note(note, claims, e)


def test_template_cannot_be_published():
    e = evidence()
    with pytest.raises(ValueError, match="complete|placeholder"):
        validate_note(note_template(e), [], e)


def test_whitespace_only_sections_are_not_complete():
    e = evidence(); note, claims = valid_note(e)
    note = note.replace('## 核心贡献\n\n逐项阅读所得；全文不可得时仅使用摘要。[C1]', '## 核心贡献\n\n   ')
    with pytest.raises(ValueError, match='Empty section'): validate_note(note, claims, e)


def test_render_chinese_table_code_safe_html():
    result = render_markdown("# 中文\n\n| 参数 | 值 |\n|---|---|\n| 学习率 | 0.01 |\n\n```python\nx = 1\n```\n\n<script>alert(1)</script>\n[bad](javascript:alert(1))")
    assert "<table>" in result and "<pre><code>" in result and "中文" in result
    assert "<script>" not in result and 'href="javascript:' not in result


def test_exports(tmp_path):
    bib = tmp_path / "中文.bib"
    bib.write_text('@article{a,title={A {Nested} Title},author={Jane Smith and John Doe},year={2020},doi={10.1/ABC}}', encoding="utf-8")
    assert exported_records(bib)[0]["title"] == "A Nested Title"
    ris = tmp_path / "x.ris"
    ris.write_text("TY  - JOUR\nTI  - A paper\nAU  - Smith, Jane\nDO  - 10.1/ABC\nER  - \n", encoding="utf-8")
    assert exported_records(ris)[0]["doi"] == "10.1/abc"
    md = tmp_path / "x.md"
    md.write_text("A summary https://doi.org/10.1234/abc", encoding="utf-8")
    assert exported_records(md)[0]["needs_resolution"]


def test_no_pdf_retains_metadata_and_failure(tmp_path):
    class Client:
        def snapshot(self, *args): return {"item": {"title": "Paper", "abstractNote": "available abstract"}, "notes": [], "attachments": []}
    class Net:
        def get(self, *args, **kwargs): return b"<html>not a pdf</html>"
    run = Run.create(tmp_path, "deep-search", {"library": 1})
    p = {"title": "Paper", "item_key": "ABCD1234", "pdf_urls": ["https://test.invalid/file"]}
    run.state["papers"] = [p]
    result = collect_evidence(run, p, Client(), Net())
    assert result["level"] == "abstract" and result["download_failures"]
    assert p["status"] == "awaiting_analysis"


def test_resume_skips_completed_import_and_evidence(tmp_path):
    class Client:
        def import_paper(self, *args): raise AssertionError("must not repeat import")
        def snapshot(self, *args): raise AssertionError("must not re-fetch finished evidence")
    run = Run.create(tmp_path, "deep-search", {"collection": "COLL0001"})
    run.state["papers"] = [{"id": "p", "title": "Paper", "item_key": "ABCD1234", "status": "awaiting_analysis"}]
    result = prepare_selected(run, Client(), None)
    assert result["status"] == "awaiting_analysis"


def test_atomic_state_chinese_path(tmp_path):
    path = tmp_path / "中文目录" / "数据.json"
    write_json(path, {"中文": [1, 2]})
    assert read_json(path) == {"中文": [1, 2]}
    assert not list(path.parent.glob("*.tmp"))


def test_get_retries_rate_limit_without_replaying_post(tmp_path, monkeypatch):
    monkeypatch.setattr("zotero_skills.core.time.sleep", lambda _: None)
    net = Network(tmp_path)
    counts = []
    def reply(request):
        counts.append(request.method)
        return httpx.Response(429, headers={"Retry-After": "0"}) if len(counts) == 1 else httpx.Response(200, json={"ok": True})
    net.client = httpx.Client(transport=httpx.MockTransport(reply))
    assert net.get("https://example.invalid/test") == {"ok": True}
    assert counts == ["GET", "GET"]


def test_pdf_page_locators(tmp_path):
    from zotero_skills.search import extract_pdf
    path = tmp_path / "论文.pdf"
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 50), "A real first page")
    doc.new_page().insert_text((50, 50), "A real second page")
    doc.save(path)
    pages = extract_pdf(path)
    assert pages[1]["page"] == 2 and "second" in pages[1]["text"]
