"""Evidence-sized notes, preprint merging, relevance ranking and triage."""
import pytest

from zotero_skills.core import Run, read_json
from zotero_skills.notes import ALLOWED_TIERS, PLACEHOLDER, TIER_SECTIONS, note_template, validate_note
from zotero_skills.search import Providers, merge_candidates, query_terms, score_candidates, triage
from test_search_notes import evidence


def fill(e, tier=None, text="逐项阅读所得；全文不可得时仅使用摘要。[C1]"):
    note = note_template(e, tier).replace("status: draft", "status: complete").replace(PLACEHOLDER, text)
    ref = {"source": "PDF00001", "page": 2, "excerpt": "reduces the test error by 20 percent"} if e["level"] in ("fulltext", "partial") else {"source": "abstract", "excerpt": "abstract with a clear limitation"}
    return note, [{"id": "C1", "kind": "reported", "statement": "A limited result", "evidence": [ref]}]


def test_default_tier_follows_evidence():
    for level, sections in [("fulltext", TIER_SECTIONS["deep"]), ("abstract", TIER_SECTIONS["brief"]), ("metadata", TIER_SECTIONS["stub"])]:
        template = note_template(evidence(level))
        assert all("## " + h in template for h in sections)
        assert "## 公式与参数" not in template  # no empty formula section for an abstract


def test_abstract_cannot_be_written_as_deep_reading():
    e = evidence("abstract")
    with pytest.raises(ValueError, match="not allowed"):
        note_template(e, "deep")
    note, claims = fill(evidence("fulltext"), "deep", "逐项阅读所得 20 percent。[C1]")
    forged = note.replace("evidence_level: fulltext", "evidence_level: abstract")
    with pytest.raises(ValueError, match="not allowed"):
        validate_note(forged, claims, e)


def test_fulltext_may_be_briefed_on_purpose():
    e = evidence("fulltext")
    note, claims = fill(e, "brief", "逐项阅读所得。[C1]")
    validate_note(note, claims, e)


def test_brief_padding_is_rejected():
    e = evidence("abstract")
    note, claims = fill(e)
    validate_note(note, claims, e)
    padded = note.replace("## 可信度与待核\n\n", "## 可信度与待核\n\n" + "未报告。" * 500)
    with pytest.raises(ValueError, match="limit 1800"):
        validate_note(padded, claims, e)


def test_takeaway_must_be_short_and_cliche_free():
    e = evidence("abstract")
    note, claims = fill(e)
    cliche = note.replace("## 一句话结论\n\n逐项阅读所得", "## 一句话结论\n\n本文提出了一种新颖的方法，逐项阅读所得", 1)
    with pytest.raises(ValueError, match="Cliché"):
        validate_note(cliche, claims, e)
    long = note.replace("## 一句话结论\n\n", "## 一句话结论\n\n" + "很长" * 100, 1)
    with pytest.raises(ValueError, match="one sentence"):
        validate_note(long, claims, e)


def test_deep_results_need_numbers():
    e = evidence("fulltext")
    note, claims = fill(e, "deep", "逐项阅读所得。[C1]")
    with pytest.raises(ValueError, match="关键结果"):
        validate_note(note, claims, e)
    ok = note.replace("## 关键结果\n\n逐项阅读所得。", "## 关键结果\n\n测试误差降低 20%（固定条件，p.2）。")
    validate_note(ok, claims, e)


def test_partial_text_is_citable_but_disclosed():
    e = evidence("fulltext"); e["level"] = "partial"
    note, claims = fill(e, "deep", "只取得部分全文（第 2 页），误差降低 20%。[C1]")
    validate_note(note, claims, e)
    silent = note.replace("只取得部分全文（第 2 页），", "")
    with pytest.raises(ValueError, match="disclosure"):
        validate_note(silent, claims, e)
    assert ALLOWED_TIERS["partial"] == ["deep", "brief"]


def test_preprint_and_journal_versions_merge():
    rows = [
        {"title": "Equivariant Potentials", "year": 2022, "doi": "10.48550/arXiv.2101.03164", "sources": ["s2"]},
        {"title": "Equivariant potentials", "year": 2023, "doi": "10.1038/s41467-022-29939-5", "sources": ["crossref"]},
        {"title": "Equivariant Potentials", "year": 2015, "doi": "", "sources": ["old"]},
    ]
    out = merge_candidates(rows)
    assert len(out) == 2  # the 2015 homonym stays separate
    paper = next(p for p in out if p["doi"])
    assert paper["doi"] == "10.1038/s41467-022-29939-5" and paper["preprint_doi"].startswith("10.48550/arxiv.")
    assert paper["arxiv"] == "2101.03164" and paper["sources"] == ["s2", "crossref"]


def test_arxiv_query_is_not_one_exact_phrase():
    class Net:
        def get(self, url, params, **kwargs):
            self.expression = params["search_query"]
            return b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    net = Net()
    Providers(net).arxiv('machine learning "interatomic potential" for electrolytes', 10)
    assert net.expression == 'all:machine AND all:learning AND all:"interatomic potential" AND all:electrolytes'
    assert query_terms("ti:graph AND neural") == ["graph", "neural"]


def test_ranking_prefers_on_topic_over_highly_cited():
    rows = [
        {"id": "classic", "title": "Deep learning", "abstract": "A review.", "citation_count": 90000, "sources": [{"provider": "semantic"}]},
        {"id": "ontopic", "title": "Machine learning interatomic potentials for electrolytes", "abstract": "We train interatomic potentials.", "citation_count": 12, "sources": [{"provider": "semantic"}, {"provider": "crossref"}]},
    ]
    ranked = score_candidates(rows, ["machine learning interatomic potentials electrolytes"])
    assert [p["id"] for p in ranked] == ["ontopic", "classic"]


def test_citation_expansion_goes_both_ways():
    class Net:
        def __init__(self): self.urls = []
        def get(self, url, params, **kwargs):
            self.urls.append(url)
            key = "citedPaper" if url.endswith("/references") else "citingPaper"
            return {"data": [{key: {"title": url.rsplit("/", 1)[-1], "externalIds": {}}}]}
    net = Net()
    out = Providers(net).citations({"doi": "10.1/x"})
    assert [p["title"] for p in out] == ["references", "citations"]
    assert {p["sources"][0]["direction"] for p in out} == {"references", "citations"}


def test_triage_report_lists_upgradable_items(tmp_path):
    run = Run.create(tmp_path, "deep-search", {"library": 1})
    run.state["papers"] = [
        {"id": "a", "title": "Full", "evidence_level": "fulltext"},
        {"id": "b", "title": "Only abstract", "evidence_level": "abstract", "doi": "10.1/b"},
        {"id": "c", "title": "Bare", "evidence_level": "metadata"},
    ]
    counts = triage(run)
    assert counts == {"fulltext": 1, "partial": 0, "abstract": 1, "metadata": 1}
    text = (run.path / "triage.md").read_text(encoding="utf-8")
    assert "https://doi.org/10.1/b" in text and "Full —" not in text
