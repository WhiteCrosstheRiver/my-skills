"""Opt-in integration tests. Only create/modify clearly labelled test items.

Run: ZOTERO_SKILLS_LIVE=1 python -m pytest tests/test_live.py -q
No deletion of user records and no permanent erase anywhere in this suite.
"""
import json
import os
import uuid

import pytest

from zotero_skills.core import MCP, Run, default_output, read_json, write_json
from zotero_skills.notes import note_template, publish
from zotero_skills.search import collect_evidence, prepare_selected

pytestmark = pytest.mark.skipif(os.environ.get("ZOTERO_SKILLS_LIVE") != "1", reason="Opt-in live Zotero writes")


def test_live_import_missing_pdf_idempotence_and_manual_notes():
    mcp = MCP()
    token = uuid.uuid4().hex[:10]
    collection = mcp.ensure_collection("Zotero Skills Tests - Integration")
    run = Run.create(default_output() / "validation", "deep-search", {"library": 1, "collection": collection})
    paper = {"id": token, "title": "[Zotero Skills TEST] missing PDF " + token, "year": 2026, "authors": ["Synthetic Test"], "abstract": "本条为程序验收的合成数据，不是实际学术论文。全文不可得，仅验证元数据、断点续跑与笔记保全。", "pdf_urls": ["https://fixture.invalid/not-a-pdf"], "status": "selected"}
    run.state["papers"] = [paper]
    run.save()
    imported = mcp.import_paper(paper, collection)
    paper["item_key"] = imported["itemKey"]
    paper["status"] = "imported"
    run.save()  # Simulate process stopping after committed import.
    class InvalidPDF:
        def get(self, *args, **kwargs): return b"<html>Unavailable PDF</html>"
    prepare_selected(Run(run.path), mcp, InvalidPDF())
    run = Run(run.path)
    paper = run.state["papers"][0]
    e = read_json(run.paper_dir(paper) / "evidence.json")
    assert e["level"] == "abstract" and e["download_failures"]
    assert mcp.import_paper(paper, collection)["itemKey"] == paper["item_key"]
    human = mcp.js("const p=await Zotero.Items.getByLibraryAndKeyAsync(1,P.key);const n=new Zotero.Item('note');n.libraryID=1;n.parentItemID=p.id;n.setNote('<p>人工测试备注：必须保留。</p>');await n.saveTx();return n.key;", key=paper["item_key"])
    note = note_template(e).replace("status: draft", "status: complete").replace("待填写：依据 evidence.json，缺失信息明确说明。", "本条为合成测试数据；全文不可得，仅据摘要验证程序流程，不作学术结论。[C1]")
    directory = run.paper_dir(paper)
    (directory / "note.md").write_text(note, encoding="utf-8")
    write_json(directory / "claims.json", [{"id": "C1", "kind": "metadata", "statement": "合成测试数据不是实际论文", "evidence": [{"source": "abstract", "excerpt": "本条为程序验收的合成数据"}]}])
    first = publish(run, paper["id"], mcp)
    second = publish(run, paper["id"], mcp)
    assert first["note_key"] == second["note_key"] and second["reused"]
    assert first["markdown_attachment_key"] == second["markdown_attachment_key"]
    mcp.js("const n=await Zotero.Items.getByLibraryAndKeyAsync(1,P.key);n.setNote(n.getNote()+'<p>用户追加的测试内容。</p>');await n.saveTx();return true;", key=first["note_key"])
    third = publish(run, paper["id"], mcp)
    assert third["note_key"] != first["note_key"]
    snap = mcp.snapshot(paper["item_key"])
    assert any(n["key"] == human and "必须保留" in n["html"] for n in snap["notes"])
    assert any(n["key"] == first["note_key"] and "用户追加" in n["html"] for n in snap["notes"])
    assert not any(a["contentType"] == "application/pdf" for a in snap["attachments"])
    write_json(run.path / "acceptance.json", {"passed": True, "checks": ["real_import", "metadata_survives_failed_pdf", "resume_after_import", "import_idempotence", "note_idempotence", "md_idempotence", "manual_note_preserved", "manual_edit_preserved"], "item_key": paper["item_key"]})
