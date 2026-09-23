"""Provider adapters and resumable discovery -> import -> evidence workflow."""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pymupdf as fitz

from .core import MCP, Network, Run, digest, now, read_json, write_json


def doi(value):
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", str(value or "").strip(), flags=re.I).lower().rstrip(".,;")


def clean(value):
    return html.unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).strip()


def identity(p):
    if p.get("doi"):
        return "doi:" + doi(p["doi"])
    if p.get("arxiv"):
        return "arxiv:" + re.sub(r"v\d+$", "", p["arxiv"])
    return "title:" + re.sub(r"[^\w]", "", p["title"].casefold()) + ":" + str(p.get("year", ""))


def merge_candidates(records):
    merged, index = [], {}
    for raw in records:
        p = dict(raw)
        p["doi"] = doi(p.get("doi"))
        if not p.get("title"):
            continue
        aliases = [identity(p)]
        if p.get("arxiv"):
            aliases.append("arxiv:" + re.sub(r"v\d+$", "", p["arxiv"]))
        title = "title:" + re.sub(r"[^\w]", "", p["title"].casefold()) + ":" + str(p.get("year", ""))
        aliases.append(title)
        found = next((index[k] for k in aliases if k in index), None)
        # Conflicting DOIs are never silently collapsed by a title match.
        if found is not None and found.get("doi") and p.get("doi") and found["doi"] != p["doi"]:
            found = None
        if found is None:
            found = p
            found.setdefault("sources", [])
            found.setdefault("pdf_urls", [])
            merged.append(found)
        else:
            for k, value in p.items():
                if k in ("sources", "pdf_urls"):
                    for v in value:
                        if v not in found.setdefault(k, []):
                            found[k].append(v)
                elif not found.get(k) and value:
                    found[k] = value
        for alias in aliases:
            if alias not in index or alias != title or not index[alias].get("doi"):
                index[alias] = found
    for p in merged:
        p["id"] = digest(identity(p))[:20]
    return merged


class Providers:
    def __init__(self, net):
        self.net = net

    def semantic(self, query, limit, years=None):
        token, out = None, []
        while len(out) < limit:
            params = {"query": query, "fields": "title,year,authors,abstract,externalIds,url,venue,openAccessPdf,citationCount", "sort": "citationCount:desc"}
            if years:
                params["year"] = years
            if token:
                params["token"] = token
            import os
            headers = {"x-api-key": os.environ["SEMANTIC_SCHOLAR_API_KEY"]} if os.environ.get("SEMANTIC_SCHOLAR_API_KEY") else None
            data = self.net.get("https://api.semanticscholar.org/graph/v1/paper/search/bulk", params, headers=headers)
            for x in data.get("data", []):
                ids = x.get("externalIds") or {}
                pdf = (x.get("openAccessPdf") or {}).get("url")
                out.append({"title": x["title"], "year": x.get("year"), "authors": [a["name"] for a in x.get("authors", [])], "abstract": x.get("abstract") or "", "doi": ids.get("DOI", ""), "arxiv": ids.get("ArXiv", ""), "url": x.get("url", ""), "venue": x.get("venue", ""), "citation_count": x.get("citationCount", 0), "semantic_id": x.get("paperId"), "pdf_urls": ([pdf] if pdf else []) + (["https://arxiv.org/pdf/" + ids["ArXiv"]] if ids.get("ArXiv") else []), "sources": [{"provider": "semantic", "query": query, "url": x.get("url"), "at": now()}]})
            new_token = data.get("token")
            if not data.get("data") or not new_token or new_token == token:
                break
            token = new_token
        return out[:limit]

    def crossref(self, query, limit, years=None):
        cursor, out = "*", []
        while len(out) < limit:
            params = {"query.bibliographic": query, "rows": min(limit - len(out), 100), "cursor": cursor, "sort": "relevance", "order": "desc"}
            if years:
                lo, _, hi = years.partition("-")
                params["filter"] = f"from-pub-date:{lo},until-pub-date:{hi or lo}"
            data = self.net.get("https://api.crossref.org/works", params)["message"]
            for x in data.get("items", []):
                parts = (x.get("published") or x.get("issued") or {}).get("date-parts", [[]])[0]
                out.append({"title": clean((x.get("title") or [""])[0]), "year": parts[0] if parts else None, "authors": [(a.get("given", "") + " " + a.get("family", a.get("name", ""))).strip() for a in x.get("author", [])], "abstract": clean(x.get("abstract", "")), "doi": x.get("DOI", ""), "url": x.get("URL", ""), "venue": (x.get("container-title") or [""])[0], "pdf_urls": [l["URL"] for l in x.get("link", []) if l.get("content-type") == "application/pdf"], "sources": [{"provider": "crossref", "query": query, "url": x.get("URL"), "at": now()}]})
            new_cursor = data.get("next-cursor")
            if not data.get("items") or not new_cursor or new_cursor == cursor:
                break
            cursor = new_cursor
        return out[:limit]

    def arxiv(self, query, limit, years=None):
        ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
        out, start = [], 0
        if query.startswith("id:"):
            base = {"id_list": query[3:]}
        else:
            expression = query if re.search(r"\b(?:all|ti|au|cat|abs):", query) else 'all:"' + query.replace('"', '') + '"'
            if years:
                lo, _, hi = years.partition("-")
                expression += f" AND submittedDate:[{lo}01010000 TO {hi or lo}12312359]"
            base = {"search_query": expression, "sortBy": "relevance"}
        while len(out) < limit:
            raw = self.net.get("https://export.arxiv.org/api/query", {**base, "start": start, "max_results": min(100, limit - len(out))}, json_data=False)
            entries = ET.fromstring(raw).findall("a:entry", ns)
            for x in entries:
                url = x.findtext("a:id", "", ns).replace("http:", "https:")
                if "/api/errors" in url:
                    raise RuntimeError(x.findtext("a:summary", "arXiv API error", ns))
                ident = url.split("/abs/")[-1]
                out.append({"title": " ".join(x.findtext("a:title", "", ns).split()), "year": int(x.findtext("a:published", "0000", ns)[:4]), "authors": [a.findtext("a:name", "", ns) for a in x.findall("a:author", ns)], "abstract": " ".join(x.findtext("a:summary", "", ns).split()), "doi": x.findtext("x:doi", "", ns), "arxiv": re.sub(r"v\d+$", "", ident), "url": url, "venue": x.findtext("x:journal_ref", "arXiv", ns), "pdf_urls": ["https://arxiv.org/pdf/" + ident], "sources": [{"provider": "arxiv", "query": query, "url": url, "at": now()}]})
            start += len(entries)
            if not entries or "id_list" in base:
                break
        return out[:limit]

    def europepmc(self, query, limit, years=None):
        cursor, out = "*", []
        if years:
            lo, _, hi = years.partition("-")
            query += f" FIRST_PDATE:[{lo}-01-01 TO {hi or lo}-12-31]"
        while len(out) < limit:
            data = self.net.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", {"query": query, "format": "json", "resultType": "core", "pageSize": min(100, limit - len(out)), "cursorMark": cursor})
            items = data.get("resultList", {}).get("result", [])
            for x in items:
                out.append({"title": clean(x.get("title")), "year": x.get("pubYear"), "authors": [a.get("fullName", "") for a in x.get("authorList", {}).get("author", [])], "abstract": clean(x.get("abstractText")), "doi": x.get("doi", ""), "pmid": x.get("pmid", ""), "url": "https://europepmc.org/article/" + x.get("source", "MED") + "/" + x.get("id", ""), "pdf_urls": [u["url"] for u in x.get("fullTextUrlList", {}).get("fullTextUrl", []) if u.get("documentStyle") == "pdf" and u.get("availabilityCode") == "OA"], "sources": [{"provider": "europepmc", "query": query, "at": now()}]})
            next_cursor = data.get("nextCursorMark")
            if not items or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        return out[:limit]

    def openalex(self, query, limit, years=None):
        import os
        key = os.environ.get("OPENALEX_API_KEY")
        if not key:
            raise RuntimeError("OpenAlex optional adapter requires OPENALEX_API_KEY")
        out, cursor = [], "*"
        while len(out) < limit:
            params = {"search": query, "per_page": min(100, limit - len(out)), "cursor": cursor, "api_key": key}
            if years:
                params["filter"] = "publication_year:" + years
            data = self.net.get("https://api.openalex.org/works", params)
            for x in data.get("results", []):
                inv = x.get("abstract_inverted_index") or {}
                positions = {pos: word for word, inds in inv.items() for pos in inds}
                out.append({"title": x.get("title"), "year": x.get("publication_year"), "authors": [a["author"]["display_name"] for a in x.get("authorships", [])], "abstract": " ".join(positions[i] for i in sorted(positions)), "doi": doi(x.get("doi")), "url": x.get("id"), "pdf_urls": [loc["pdf_url"] for loc in x.get("locations", []) if loc.get("pdf_url") and loc.get("is_oa")], "sources": [{"provider": "openalex", "query": query, "url": x.get("id"), "at": now()}]})
            new_cursor = data.get("meta", {}).get("next_cursor")
            if not data.get("results") or not new_cursor or new_cursor == cursor:
                break
            cursor = new_cursor
        return out[:limit]

    def citations(self, paper, limit=10):
        ident = paper.get("semantic_id") or ("DOI:" + paper["doi"] if paper.get("doi") else None)
        if not ident:
            return []
        data = self.net.get(f"https://api.semanticscholar.org/graph/v1/paper/{ident}/references", {"fields": "title,year,authors,externalIds,abstract,openAccessPdf", "limit": min(limit, 100)})
        out = []
        for row in data.get("data") or []:
            p = row.get("citedPaper") or {}
            if not p.get("title"):
                continue
            ids = p.get("externalIds") or {}
            pdf = (p.get("openAccessPdf") or {}).get("url")
            out.append({"title": p["title"], "year": p.get("year"), "authors": [a["name"] for a in (p.get("authors") or [])], "doi": ids.get("DOI", ""), "arxiv": ids.get("ArXiv", ""), "abstract": p.get("abstract") or "", "pdf_urls": [pdf] if pdf else [], "sources": [{"provider": "citation-expansion", "seed": identity(paper), "at": now()}]})
        return out


def exported_records(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".bib":
        import bibtexparser
        rows = bibtexparser.loads(text).entries
        return [{"title": clean(x.get("title", "")).replace("{", "").replace("}", ""), "doi": doi(x.get("doi")), "year": x.get("year"), "authors": x.get("author", "").split(" and "), "abstract": clean(x.get("abstract", "")), "url": x.get("url", ""), "sources": [{"provider": "bibtex-export", "file": path.name}]} for x in rows]
    if path.suffix.lower() == ".ris":
        import rispy
        rows = rispy.loads(text)
        return [{"title": x.get("title", x.get("primary_title", "")), "doi": doi(x.get("doi")), "year": str(x.get("year", x.get("publication_year", "")))[:4], "authors": x.get("authors", []), "abstract": x.get("abstract", ""), "url": (x.get("urls") or [""])[0], "sources": [{"provider": "ris-export", "file": path.name}]} for x in rows]
    # A Markdown export is a discovery list, never trusted as full-paper evidence.
    ids = list(dict.fromkeys(doi(v) for v in re.findall(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.I)))
    return [{"title": "", "doi": value, "needs_resolution": True, "sources": [{"provider": "markdown-export", "file": path.name}]} for value in ids]


def extract_pdf(path):
    pages = []
    with fitz.open(path) as doc:
        if doc.is_encrypted:
            raise ValueError("Encrypted PDF")
        for i, page in enumerate(doc):
            # Preserve publisher content-stream reading order. Sorting glyphs by
            # y/x interleaves two-column papers and can attach numbers to wrong claims.
            pages.append({"page": i + 1, "text": page.get_text(sort=False)})
    return pages


def collect_evidence(run, paper, mcp, net):
    directory = run.paper_dir(paper)
    library = run.state["config"].get("library", 1)
    snap = mcp.snapshot(paper["item_key"], library)
    pages, sources, failures = [], [], list(paper.get("download_failures", []))
    # Read every existing PDF, including supplements; don't mistake a note for a full text.
    for attachment in snap["attachments"]:
        file = attachment.get("path")
        if attachment.get("contentType") == "application/pdf" and file and Path(file).exists():
            try:
                found = extract_pdf(file)
                for p in found:
                    p["source"] = attachment["key"]
                pages.extend(found)
                sources.append({"id": attachment["key"], "type": "pdf", "path": file, "title": attachment["title"], "sha256": digest(Path(file).read_bytes())})
            except Exception as exc:
                failures.append({"source": attachment["key"], "reason": type(exc).__name__ + ": " + str(exc)})
    if not pages:
        urls = list(dict.fromkeys(paper.get("pdf_urls", []) + (["https://arxiv.org/pdf/" + paper["arxiv"]] if paper.get("arxiv") else [])))
        for url in urls:
            try:
                content = net.get(url, json_data=False, cache=False)
                if b"%PDF-" not in content[:1024]:
                    raise ValueError("Response is not a PDF")
                pdf = directory / "paper.pdf"
                pdf.write_bytes(content)
                found = extract_pdf(pdf)
                attachment = mcp.attach(paper["item_key"], pdf, paper["title"], library)
                for p in found:
                    p["source"] = attachment["key"]
                pages = found
                sources.append({"id": attachment["key"], "type": "pdf", "url": url, "path": str(pdf), "sha256": digest(content)})
                paper["pdf_attachment_key"] = attachment["key"]
                break
            except Exception as exc:
                failures.append({"url": url, "reason": type(exc).__name__ + ": " + str(exc)})
    text_size = sum(len(p["text"].strip()) for p in pages)
    abstract = paper.get("abstract") or snap["item"].get("abstractNote", "")
    level = "fulltext" if text_size >= 1000 else "abstract" if abstract else "metadata"
    state = "readable" if text_size >= 1000 else "scan_or_short_text" if pages else "unavailable"
    # Existing notes, including human edits to generated notes, are context only.
    # They never substitute for primary-source evidence in claims.json.
    notes = snap["notes"]
    evidence = {"schema": 1, "item_key": paper["item_key"], "library_id": library, "title": paper["title"], "doi": paper.get("doi"), "abstract": abstract, "level": level, "fulltext_status": state, "retrieved_at": now(), "sources": sources, "pages": pages, "user_notes": notes, "annotations": [a for att in snap["attachments"] for a in att.get("annotations", [])], "metadata": snap["item"], "discovery_sources": paper.get("sources", []), "download_failures": failures}
    write_json(directory / "evidence.json", evidence)
    (directory / "fulltext.txt").write_text("\n\n".join(f"[{p['source']} p.{p['page']}]\n{p['text']}" for p in pages) or abstract, encoding="utf-8")
    paper.update(evidence_level=level, fulltext_status=state, download_failures=failures, evidence_hash=digest(json.dumps(evidence, sort_keys=True, ensure_ascii=False)), status="awaiting_analysis")
    run.save()
    return evidence


def discover(run, net):
    config = run.state["config"]
    providers = Providers(net)
    records = list(run.state.get("candidates", []))
    done = set(run.state.get("queries_done", []))
    for provider in config.get("providers", ["semantic", "crossref", "arxiv"]):
        for query in config.get("queries") or [config["topic"]]:
            task = provider + ":" + query
            if task in done:
                continue
            try:
                rows = getattr(providers, provider)(query, config.get("candidate_limit", 100), config.get("years"))
                records.extend(rows)
                run.state["candidates"] = merge_candidates(records)
                done.add(task)
                run.state["queries_done"] = sorted(done)
                run.event("query_completed", provider=provider, query=query, count=len(rows))
            except Exception as exc:
                # No request URL in diagnostics: optional provider keys can be query parameters.
                run.event("query_failed", provider=provider, query=query, error=type(exc).__name__)
    for filename in config.get("inputs", []):
        task = "file:" + str(filename)
        if task in done:
            continue
        rows = exported_records(filename)
        for row in rows:
            if row.get("doi"):
                try:
                    # Resolve identity, rather than inheriting an unverified export description.
                    x = net.get("https://api.crossref.org/works/" + row["doi"])["message"]
                    row["title"] = clean((x.get("title") or [row.get("title", "")])[0])
                    row["verified_doi"] = True
                    row["year"] = (x.get("published", {}).get("date-parts") or [[row.get("year")]])[0][0]
                    row["abstract"] = clean(x.get("abstract")) or row.get("abstract", "")
                except Exception:
                    row["verified_doi"] = False
        records.extend(rows)
        done.add(task)
        run.state["queries_done"] = sorted(done)
        run.state["candidates"] = merge_candidates(records)
        run.save()
    run.state["candidates"] = merge_candidates(records)
    if config.get("citation_hops", 0) and not run.state.get("citations_done"):
        for seed in run.state["candidates"][:min(3, len(run.state["candidates"]))]:
            try:
                records.extend(providers.citations(seed, limit=10))
            except Exception as exc:
                run.event("citation_expansion_failed", seed=identity(seed), error=type(exc).__name__)
        run.state["candidates"] = merge_candidates(records)
        run.state["citations_done"] = True
    run.state["status"] = "awaiting_selection"
    run.save()
    write_json(run.path / "candidates.json", run.state["candidates"])
    return {"run": str(run.path), "status": run.state["status"], "candidates": len(run.state["candidates"]), "next": "Read candidates.json; write selection.json with included [{id, reason}] and excluded [{id, reason}], then resume --selection FILE."}


def prepare_selected(run, mcp, net, selection=None):
    config = run.state["config"]
    if selection:
        selected = read_json(selection)
        candidates = {p["id"]: p for p in run.state["candidates"]}
        included = selected.get("included", [])
        if not included or any(p.get("id") not in candidates or not p.get("reason") for p in included):
            raise ValueError("Selection requires known candidate IDs and a reason for each included paper")
        if len({p["id"] for p in included}) != len(included):
            raise ValueError("Duplicate selected IDs")
        if len(included) > config.get("limit", 100):
            raise ValueError("Selection exceeds --limit")
        prior = {p["id"]: p for p in run.state["papers"]}
        run.state["papers"] = [prior.get(p["id"], {**candidates[p["id"]], "inclusion_reason": p["reason"], "status": "selected"}) for p in included]
        write_json(run.path / "selection.json", selected)
        run.save()
    if not run.state["papers"]:
        raise ValueError("No selected papers; supply --selection")
    if not config.get("collection"):
        config["collection"] = mcp.ensure_collection(config.get("collection_name") or config["topic"], config.get("library", 1))
        run.save()
    for paper in run.state["papers"]:
        try:
            if not paper.get("item_key"):
                if paper.get("doi") and not paper.get("metadata_checked"):
                    try:
                        x = net.get("https://api.crossref.org/works/" + doi(paper["doi"]))["message"]
                        paper["discovered_year"] = paper.get("year")
                        parts = (x.get("published") or x.get("issued") or {}).get("date-parts", [[]])[0]
                        paper.update(title=clean((x.get("title") or [paper["title"]])[0]), year=parts[0] if parts else paper.get("year"), authors=[(a.get("given", "") + " " + a.get("family", a.get("name", ""))).strip() for a in x.get("author", [])] or paper.get("authors", []), venue=(x.get("container-title") or [paper.get("venue", "")])[0])
                        paper["abstract"] = paper.get("abstract") or clean(x.get("abstract"))
                        paper.setdefault("sources", []).append({"provider": "crossref-identity", "doi": paper["doi"], "at": now()})
                        paper["metadata_checked"] = True
                    except Exception as exc:
                        paper["metadata_check_error"] = type(exc).__name__
                result = mcp.import_paper(paper, config["collection"], config.get("library", 1))
                paper["item_key"] = result["itemKey"]
                paper["status"] = "imported"
                run.save()
            if paper["status"] not in ["awaiting_analysis", "published"]:
                collect_evidence(run, paper, mcp, net)
        except Exception as exc:
            paper["status"] = "error"
            paper["error"] = type(exc).__name__ + ": " + str(exc)
            run.save()
    run.state["status"] = "complete" if all(p["status"] == "published" for p in run.state["papers"]) else "awaiting_analysis" if all(p["status"] in ["awaiting_analysis", "published"] for p in run.state["papers"]) else "partial_failure"
    run.save()
    return {"run": str(run.path), "status": run.state["status"], "papers": [{"id": p["id"], "key": p.get("item_key"), "status": p["status"], "evidence": p.get("evidence_level")} for p in run.state["papers"]], "next": "Read every evidence.json/fulltext.txt, write note.md and claims.json following references/notes.md; publish-note --run PATH --paper ID."}
