"""Excerpt verification against real-world PDF text, and sync-only attachments."""
from zotero_skills.core import Run
from zotero_skills.notes import excerpt_found
from zotero_skills.search import collect_evidence, triage


PAGE = ("We propose a polarizable potential. The meth-\nod reduces the mean abso-\nlute error by 37 %\n"
        "relative to the ﬁxed-charge baseline (“DFT reference”), see state-of-the-\nart models.")


def test_excerpt_tolerates_hyphenation_ligatures_and_quotes():
    assert excerpt_found("The method reduces the mean absolute error by 37 %", PAGE)
    assert excerpt_found('relative to the fixed-charge baseline ("DFT reference")', PAGE)
    assert excerpt_found("see state-of-the-art models", PAGE)  # real compound keeps its hyphen


def test_excerpt_elision_requires_every_piece_in_order():
    assert excerpt_found("We propose a polarizable potential … fixed-charge baseline", PAGE)
    assert not excerpt_found("fixed-charge baseline … We propose a polarizable potential", PAGE)
    assert not excerpt_found("We propose a polarizable potential … by 99 % overall", PAGE)


def test_excerpt_rejects_paraphrase_and_tiny_pieces():
    assert not excerpt_found("The approach lowers the error by 37 %", PAGE)
    assert not excerpt_found("We … 37", PAGE)


def test_excerpt_may_run_onto_next_page_but_must_start_on_cited_page():
    p1, p2 = "Results are summarized in Table 2, where the energy", "error drops to 1.2 meV/atom."
    assert excerpt_found("where the energy error drops to 1.2 meV/atom", p1, p2)
    assert not excerpt_found("error drops to 1.2 meV/atom", p1, p2)


def test_unsynced_attachment_is_not_replaced_by_a_download(tmp_path):
    class Client:
        def fetch_missing_files(self, key, library):
            return [{"key": "ATT9", "contentType": "application/pdf", "status": "not_synced",
                     "error": "couldn't read your saved credentials"}]
        def snapshot(self, *args):
            return {"item": {"title": "Paper", "abstractNote": "abstract text"}, "notes": [],
                    "attachments": [{"key": "ATT9", "contentType": "application/pdf", "path": False, "title": "Full Text PDF"}]}
        def attach(self, *args):
            raise AssertionError("must not attach a duplicate of a file that is only on the sync server")

    class Net:
        def get(self, *args, **kwargs):
            raise AssertionError("must not search for an OA copy of an unsynced attachment")

    run = Run.create(tmp_path, "distill", {"library": 1})
    p = {"id": "p1", "title": "Paper", "item_key": "ABCD1234", "pdf_urls": []}
    run.state["papers"] = [p]
    e = collect_evidence(run, p, Client(), Net())
    assert e["level"] == "abstract"
    assert p["fulltext_blocker"] == "zotero_file_sync"
    assert any(f["status"] == "not_synced" for f in e["download_failures"])
    triage(run)
    text = (run.path / "triage.md").read_text(encoding="utf-8")
    assert "同步服务器" in text and "重复附加" in text
