"""Evidence validation and idempotent, version-preserving note publication."""
from __future__ import annotations

import json
import re
from pathlib import Path

import bleach
import yaml
from markdown_it import MarkdownIt

from .core import digest, now, read_json, write_json


SECTIONS = ["文献身份与摘要", "背景与研究问题", "核心贡献", "实验与论证思路", "关键方法与过程", "公式与参数", "结果与对照", "结论与适用边界", "局限与矛盾", "作者与团队", "代码、数据与复现", "研究启发", "证据索引与生成记录"]
MD = MarkdownIt("commonmark", {"html": False, "breaks": False}).enable("table").enable("strikethrough")


def split_frontmatter(text):
    if not text.startswith("---\n"):
        raise ValueError("Missing YAML frontmatter")
    chunks = text.split("\n---\n", 1)
    if len(chunks) != 2:
        raise ValueError("Unclosed YAML frontmatter")
    metadata = yaml.safe_load(chunks[0][4:])
    if not isinstance(metadata, dict):
        raise ValueError("Frontmatter must be a mapping")
    return metadata, chunks[1]


def render_markdown(text):
    return bleach.clean(MD.render(text), tags={"p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "em", "s", "blockquote", "ul", "ol", "li", "pre", "code", "table", "thead", "tbody", "tr", "th", "td", "a", "hr", "sup", "sub"}, attributes={"a": ["href", "title"]}, protocols={"http", "https", "zotero", "mailto"}, strip=True)


def validate_note(note, claims, evidence):
    metadata, body = split_frontmatter(note)
    errors = []
    if metadata.get("schema") != 1:
        errors.append("Unsupported note schema")
    if metadata.get("library_id") != evidence["library_id"]:
        errors.append("library_id does not match evidence")
    normalize_doi = lambda s: re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", str(s or "").strip(), flags=re.I).lower()
    if normalize_doi(metadata.get("doi")) != normalize_doi(evidence.get("doi")):
        errors.append("doi does not match evidence")
    if metadata.get("item_key") != evidence["item_key"]:
        errors.append("item_key does not match evidence")
    if metadata.get("evidence_level") != evidence["level"]:
        errors.append("evidence_level does not match available evidence")
    if metadata.get("status") != "complete":
        errors.append("Analysis must be explicitly marked complete by the authoring agent")
    for field in ["generated_at", "source_hash", "analyst"]:
        if not metadata.get(field):
            errors.append("Missing provenance field: " + field)
    expected_hash = digest(json.dumps(evidence, sort_keys=True, ensure_ascii=False))
    if metadata.get("source_hash") != expected_hash:
        errors.append("Evidence changed after drafting: source_hash mismatch")
    for heading in SECTIONS:
        if not re.search(r"^##\s+" + re.escape(heading) + r"\s*$", body, re.M):
            errors.append("Missing section: " + heading)
        else:
            section = re.search(r"^##[^\S\n]+" + re.escape(heading) + r"[^\S\n]*\n(.*?)(?=^##\s|\Z)", body, re.M | re.S)
            if not section or not section[1].strip():
                errors.append("Empty section: " + heading)
    if re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b|待填写|在此填写", body, re.I):
        errors.append("Unfinished placeholder found")
    # No filler quota: missing evidence is explicitly reported rather than invented.
    if not claims or not isinstance(claims, list):
        errors.append("claims.json must be a nonempty list")
        claims = []
    pages = {(p["source"], p["page"]): p["text"] for p in evidence.get("pages", [])}
    external = {s["id"]: s for s in evidence.get("external_sources", [])}
    seen = set()
    for claim in claims:
        cid = claim.get("id")
        if not cid or cid in seen or f"[{cid}]" not in body:
            errors.append("Invalid, duplicate or unreferenced claim: " + str(cid))
        seen.add(cid)
        if claim.get("kind") not in ["reported", "inference", "limitation", "metadata"]:
            errors.append("Unknown claim kind: " + str(cid))
        if not claim.get("statement") or not claim.get("evidence"):
            errors.append("Claim needs a statement and evidence: " + str(cid))
        for ref in claim.get("evidence", []):
            source, page = ref.get("source"), ref.get("page")
            if source == "abstract":
                text = evidence.get("abstract", "")
            elif source == "metadata":
                text = json.dumps(evidence["metadata"], ensure_ascii=False)
            elif source in external:
                text = external[source].get("text", "")
            else:
                text = pages.get((source, page), "")
            excerpt = ref.get("excerpt", "")
            normalize = lambda s: re.sub(r"\s+", "", s).casefold()
            if not text or len(excerpt.strip()) < 8 or normalize(excerpt) not in normalize(text):
                errors.append(f"Unverifiable excerpt for {cid}: {source} p.{page}")
            if evidence["level"] != "fulltext" and source not in ["abstract", "metadata", *external]:
                errors.append("Full-text claim without full-text evidence: " + str(cid))
    for cid in set(re.findall(r"\[(C\d+)\]", body)) - seen:
        errors.append("Undefined claim reference: " + cid)
    if evidence["level"] != "fulltext" and not re.search("全文.*(?:不可得|缺失|未取得|无法)|仅.*(?:摘要|元数据)", body):
        errors.append("Missing full-text limitation disclosure")
    if errors:
        raise ValueError("\n".join(errors))
    return metadata, body


def note_template(evidence):
    meta = {"schema": 1, "item_key": evidence["item_key"], "library_id": evidence["library_id"], "doi": evidence.get("doi"), "evidence_level": evidence["level"], "status": "draft", "generated_at": now(), "source_hash": digest(json.dumps(evidence, sort_keys=True, ensure_ascii=False)), "analyst": "Codex / Claude Code"}
    return "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\n\n# " + evidence["title"] + "\n\n" + "\n\n".join("## " + h + "\n\n待填写：依据 evidence.json，缺失信息明确说明。" for h in SECTIONS) + "\n"


def publish(run, paper_id, mcp):
    paper = next(p for p in run.state["papers"] if p["id"] == paper_id)
    directory = run.paper_dir(paper)
    evidence = read_json(directory / "evidence.json")
    note = (directory / "note.md").read_text(encoding="utf-8")
    claims = read_json(directory / "claims.json")
    metadata, body = validate_note(note, claims, evidence)
    content_hash = digest(note)
    claims_hash = digest(json.dumps(claims, sort_keys=True, ensure_ascii=False))
    version_hash = digest(content_hash + claims_hash + metadata['source_hash'])
    html = render_markdown(body)
    library = run.state["config"].get("library", 1)
    marker = "zotero-skills:note:" + content_hash
    # Every content version is immutable. A timed-out create is found by its marker.
    result = mcp.js("""
const parent=await Zotero.Items.getByLibraryAndKeyAsync(P.library,P.key);if(!parent||parent.deleted)throw new Error('Parent missing');
for(const id of parent.getNotes()) {const n=await Zotero.Items.getAsync(id);if(n.hasTag(P.marker)) {if(n.getNote().trim()===P.html.trim())return {key:n.key,reused:true};}}
const n=new Zotero.Item('note');n.libraryID=P.library;n.parentItemID=parent.id;n.setNote(P.html);n.addTag('zotero-skills:distilled');n.addTag(P.marker);await n.saveTx();return {key:n.key,reused:false};
""", key=paper["item_key"], library=library, marker=marker, html=html)
    attachment = mcp.attach(paper["item_key"], directory / "note.md", "精读 Markdown · " + content_hash[:10], library)
    snap = mcp.snapshot(paper["item_key"], library)
    stored = next((n for n in snap["notes"] if n["key"] == result["key"]), None)
    if not stored or not all(h in stored["html"] for h in SECTIONS):
        raise RuntimeError("Published note readback failed")
    if not any(a["key"] == attachment["key"] for a in snap["attachments"]):
        raise RuntimeError("Markdown attachment readback failed")
    manifest = {"schema": 1, "published_at": now(), "library_id": library, "item_key": paper["item_key"], "note_key": result["key"], "markdown_attachment_key": attachment["key"], "content_hash": content_hash, "evidence_hash": metadata["source_hash"], "evidence_level": evidence["level"], "claims": claims, "note_path": str(directory / "note.md"), "evidence_path": str(directory / "evidence.json"), "reused": result["reused"]}
    manifest.update(claims_hash=claims_hash, version_hash=version_hash)
    write_json(directory / "publication.json", manifest)
    archive = run.path.parents[1] / "notes" / str(library) / paper["item_key"] / version_hash
    archive.mkdir(parents=True, exist_ok=True)
    for name in ["note.md", "claims.json", "evidence.json", "publication.json"]:
        target = archive / name
        if target.exists():
            if name != 'publication.json' and target.read_bytes() != (directory / name).read_bytes():
                raise RuntimeError('Archived version was modified: ' + str(target))
        else:
            target.write_bytes((directory / name).read_bytes())
    paper.update(status="published", note_key=result["key"], note_hash=content_hash, markdown_attachment_key=attachment["key"])
    if all(p["status"] == "published" for p in run.state["papers"]):
        run.state["status"] = "complete"
    run.save()
    return manifest
