import json
from pathlib import Path

import httpx
import pytest
import pymupdf

from zotero_skills.core import Run, Network, digest, write_json, read_json
from zotero_skills.notes import SECTIONS, note_template, render_markdown, validate_note
from zotero_skills.search import Providers, WEB_SEARCH_URLS, collect_evidence, discover, exported_records, import_input_files, merge_candidates, oa_pdf_urls, prepare_selected


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


def test_host_assisted_providers_emit_urls_without_network(tmp_path):
    run = Run.create(tmp_path, "deep-search", {"topic": "电解液 势函数", "queries": ["machine learning potential electrolyte"], "providers": ["scholar", "researchgate", "xmol"], "years": "2018-2026", "citation_hops": 0, "library": 1})
    class Net:
        def get(self, *args, **kwargs): raise AssertionError("host-assisted providers must not send HTTP")
    result = discover(run, Net())
    manifest = read_json(run.path / "web_sources.json")
    urls = [s["url"] for s in manifest["searches"]]
    assert len(urls) == 3 and result["host_searches"] == 3
    assert "scholar.google.com/scholar" in urls[0] and "as_ylo=2018" in urls[0]
    assert "researchgate.net/search" in urls[1] and "x-mol.com/paper/search" in urls[2]
    assert run.state["status"] == "awaiting_selection"
    # Re-running discovery must not duplicate host search tasks.
    discover(run, Net())
    assert len(read_json(run.path / "web_sources.json")["searches"]) == 3


def test_web_query_escaping_and_yearless_url():
    url = WEB_SEARCH_URLS["scholar"]('machine learning "electrolyte" ', None)
    assert "q=machine+learning+%22electrolyte%22+" in url and "as_ylo" not in url


def test_resume_input_merges_and_resolves_exports(tmp_path):
    ris = tmp_path / "digest.ris"
    ris.write_text("TY  - JOUR\nTI  - Unresolved Export Title\nDO  - 10.1/ABC\nER  - \n", encoding="utf-8")
    run = Run.create(tmp_path, "deep-search", {"topic": "t", "queries": [], "providers": [], "citation_hops": 0, "library": 1})
    class Net:
        def get(self, url, params=None, **kwargs):
            return {"message": {"title": ["Resolved Title"], "published": {"date-parts": [[2021]]}, "abstract": "<p>Resolved abstract</p>"}}
    assert import_input_files(run, Net(), [ris]) == 1
    paper = run.state["candidates"][0]
    assert paper["title"] == "Resolved Title" and paper["verified_doi"] and paper["year"] == 2021
    assert paper["abstract"] == "Resolved abstract"
    # Merging the same file twice must not duplicate candidates.
    assert import_input_files(run, Net(), [ris]) == 0
    assert len(run.state["candidates"]) == 1


def test_topic_collection_nests_under_parent(tmp_path):
    calls = []
    class Client:
        def ensure_collection(self, name, library=1, parent=None):
            calls.append((name, parent))
            return "PARENT" if name == "Agent" else "TOPIC"
        def snapshot(self, *a): raise AssertionError("no item work expected")
    run = Run.create(tmp_path, "deep-search", {"topic": "专题", "parent_collection_name": "Agent", "library": 1})
    run.state["papers"] = [{"id": "p", "title": "Paper", "item_key": "ABCD1234", "status": "published"}]
    prepare_selected(run, Client(), None)
    assert calls == [("Agent", None), ("专题", "PARENT")] and run.state["config"]["collection"] == "TOPIC"


def test_empty_parent_creates_topic_at_root(tmp_path):
    calls = []
    class Client:
        def ensure_collection(self, name, library=1, parent=None):
            calls.append((name, parent)); return "TOPIC"
    run = Run.create(tmp_path, "deep-search", {"topic": "专题", "parent_collection_name": "", "library": 1})
    run.state["papers"] = [{"id": "p", "title": "Paper", "item_key": "ABCD1234", "status": "published"}]
    prepare_selected(run, Client(), None)
    assert calls == [("专题", None)]


def test_oa_resolver_parses_and_dedups_openalex_locations():
    class Net:
        def get(self, url, params=None, **kwargs):
            assert url.startswith("https://api.openalex.org/works/doi:")
            return {"best_oa_location": {"pdf_url": "https://repo/a.pdf", "is_oa": True},
                    "locations": [{"pdf_url": "https://repo/a.pdf"}, {"pdf_url": "https://pub/b.pdf"}, {"pdf_url": None}]}
    assert oa_pdf_urls({"doi": "10.1/ABC"}, Net()) == ["https://repo/a.pdf", "https://pub/b.pdf"]
    assert oa_pdf_urls({"doi": ""}, Net()) == []


def test_collect_evidence_falls_back_to_oa_chain(tmp_path):
    class Client:
        def snapshot(self, *args): return {"item": {"title": "Paper", "abstractNote": "abstract"}, "notes": [], "attachments": []}
        def attach(self, *args): return {"key": "ATT1"}
    class Net:
        def get(self, url, params=None, json_data=True, cache=True, headers=None):
            if url.startswith("https://api.openalex.org/"):
                return {"best_oa_location": {"pdf_url": "https://repo/real.pdf"}, "locations": []}
            if "test.invalid" in url:
                import httpx
                raise httpx.HTTPStatusError("404", request=None, response=httpx.Response(404))
            import io
            doc = pymupdf.open()
            pg = doc.new_page()
            for i in range(40):
                pg.insert_text((50, 50 + i * 14), f"OA full text page line {i} with evidence sentence.")
            
            buf = io.BytesIO(); doc.save(buf)
            return buf.getvalue()
    run = Run.create(tmp_path, "deep-search", {"library": 1})
    p = {"title": "Paper", "item_key": "ABCD1234", "doi": "10.1/abc", "pdf_urls": ["https://test.invalid/f"], "status": "imported"}
    run.state["papers"] = [p]
    result = collect_evidence(run, p, Client(), Net())
    assert result["level"] == "fulltext"
    assert any(s.get("url") == "https://repo/real.pdf" for s in result["sources"])
    assert any(s["provider"] == "oa-resolver" for s in p["sources"])
