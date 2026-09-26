"""Provider adapters and resumable discovery -> import -> evidence workflow."""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote_plus

import pymupdf as fitz

from .core import MCP, Network, Run, digest, now, read_json, write_json


def doi(value):
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", str(value or "").strip(), flags=re.I).lower().rstrip(".,;")


def clean(value):
    return html.unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).strip()


# Preprint servers mint their own DOIs. They must not block a merge with the journal
# version of the same paper, which is what left preprint/published pairs duplicated.
PREPRINT_DOI = re.compile(r"^10\.(?:48550/arxiv\.|26434/|21203/rs\.|20944/preprints|2139/ssrn\.|31219/osf\.|1101/\d{4}\.\d{2}\.\d{2}\.)")


def norm_title(title):
    return re.sub(r"[^\w]", "", str(title or "").casefold())


def identity(p):
    if p.get("doi") or p.get("preprint_doi"):
        return "doi:" + doi(p.get("doi") or p.get("preprint_doi"))
    if p.get("arxiv"):
        return "arxiv:" + re.sub(r"v\d+$", "", p["arxiv"])
    return "title:" + re.sub(r"[^\w]", "", p["title"].casefold()) + ":" + str(p.get("year", ""))


# Host-assisted sources: these sites offer no bulk API and forbid automated
# harvesting, so the CLI emits ready-to-open search URLs and the host agent
# reads results with its browsing tools, saves the site's own export files,
# and merges them back with resume --input. Never scrape them programmatically.
WEB_SEARCH_URLS = {
    "scholar": lambda query, years: "https://scholar.google.com/scholar?hl=en" + (f"&as_ylo={years.split('-')[0]}&as_yhi={years.split('-')[-1]}" if years else "") + "&q=" + quote_plus(query),
    "researchgate": lambda query, years: "https://www.researchgate.net/search?q=" + quote_plus(query),
    "xmol": lambda query, years: "https://www.x-mol.com/paper/search/q?option=" + quote_plus(query),
}

WEB_SEARCH_EXPORT_HINTS = {
    "scholar": "Scholar 每条结果下 Cite → BibTeX 复制保存为 .bib；也可保存结果页 DOI/标题列表为 .md",
    "researchgate": "ResearchGate 条目 Export citation → RIS 保存为 .ris；或保存 DOI 列表为 .md",
    "xmol": "X-MOL 检索后逐条复制 DOI/标题保存为 .md（X-MOL 无批量引文导出；部分结果需登录可见）",
}


def _years_close(a, b, window=2):
    try:
        return abs(int(a.get("year")) - int(b.get("year"))) <= window
    except (TypeError, ValueError):
        return True


def merge_candidates(records):
    merged, index = [], {}
    for raw in records:
        p = dict(raw)
        p["doi"] = doi(p.get("doi"))
        if p["doi"] and PREPRINT_DOI.match(p["doi"]):
            p["preprint_doi"], p["doi"] = p["doi"], ""
            match = re.match(r"10\.48550/arxiv\.(.+)", p["preprint_doi"])
            if match and not p.get("arxiv"):
                p["arxiv"] = match[1]
        if not p.get("title"):
            continue
        aliases = [identity(p)]
        if p.get("preprint_doi"):
            aliases.append("doi:" + p["preprint_doi"])
        if p.get("arxiv"):
            aliases.append("arxiv:" + re.sub(r"v\d+$", "", p["arxiv"]))
        # Title alias ignores the year (preprint 2022, journal 2023) but only matches within two years.
        title = "title:" + norm_title(p["title"])
        aliases.append(title)
        found = None
        for alias in aliases:
            candidate = index.get(alias)
            if candidate is None or (alias == title and not _years_close(candidate, p)):
                continue
            found = candidate
            break
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


STOPWORDS = set("a an and are as at by for from in into is of on or the to with via using based toward towards".split())


def query_terms(query):
    """Quoted phrases stay whole; field prefixes and boolean operators are dropped."""
    terms = []
    for token in re.findall(r'"[^"]+"|\S+', str(query)):
        token = re.sub(r"^(?:all|ti|abs|au|cat):", "", token).strip('"()').casefold()
        if token and token not in STOPWORDS and token not in ("and", "or", "andnot") and len(token) > 1:
            terms.append(token)
    return terms


def score_candidates(candidates, queries):
    """Transparent relevance score for triage; the host still decides inclusion."""
    import math
    term_sets = [t for t in (query_terms(q) for q in queries or []) if t]
    for p in candidates:
        title, abstract = str(p.get("title", "")).casefold(), str(p.get("abstract", "")).casefold()
        cover = lambda text: max((sum(t in text for t in terms) / len(terms) for terms in term_sets), default=0)
        providers = {s.get("provider") for s in p.get("sources", []) if isinstance(s, dict)}
        cites = p.get("citation_count") or 0
        score = 3 * cover(title) + 1.5 * cover(abstract) + 0.4 * min(max(len(providers) - 1, 0), 3)
        score += 0.3 * math.log10(1 + cites) + (0.3 if abstract else 0) + (0.2 if p.get("pdf_urls") else 0)
        if any(s.get("provider") == "citation-expansion" for s in p.get("sources", []) if isinstance(s, dict)):
            score += 0.5
        p["score"] = round(score, 2)
    return sorted(candidates, key=lambda p: -p.get("score", 0))


def write_ranked(run):
    """A compact, ranked reading list: the host judges relevance from this, not raw JSON."""
    config = run.state["config"]
    ranked = score_candidates(run.state.get("candidates", []), config.get("queries") or [config.get("topic", "")])
    lines = ["# 候选文献（按相关度排序）", "", f"共 {len(ranked)} 条。分数只是分诊提示（题名/摘要命中检索词、多源命中、被引、是否有摘要/PDF），入选由你判断。", ""]
    for rank, p in enumerate(ranked, 1):
        providers = "+".join(sorted({s.get("provider", "?") for s in p.get("sources", []) if isinstance(s, dict)}))
        flags = " · ".join(x for x in [str(p.get("year") or "?"), (p.get("venue") or "")[:40], providers, f"{p.get('citation_count')} cites" if p.get("citation_count") else "", "摘要" if p.get("abstract") else "无摘要", "PDF" if p.get("pdf_urls") else ""] if x)
        lines.append(f"{rank}. [{p['score']}] **{p['title']}** — {flags} — id `{p['id']}`")
        if p.get("abstract"):
            lines.append("   > " + re.sub(r"\s+", " ", p["abstract"])[:280])
    (run.path / "candidates_ranked.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ranked


class Providers:
    def __init__(self, net):
        self.net = net

    def semantic(self, query, limit, years=None):
        # /paper/search is relevance-ranked (max 1000 results). The previous bulk endpoint
        # sorted keyword matches by citation count, so old classics buried on-topic work.
        import os
        headers = {"x-api-key": os.environ["SEMANTIC_SCHOLAR_API_KEY"]} if os.environ.get("SEMANTIC_SCHOLAR_API_KEY") else None
        out, offset = [], 0
        while len(out) < limit and offset < 1000:
            size = min(100, limit - len(out), 1000 - offset)
            params = {"query": query, "offset": offset, "limit": size, "fields": "title,year,authors,abstract,externalIds,url,venue,openAccessPdf,citationCount"}
            if years:
                params["year"] = years
            data = self.net.get("https://api.semanticscholar.org/graph/v1/paper/search", params, headers=headers)
            rows = data.get("data") or []
            for x in rows:
                if not x.get("title"):
                    continue
                ids = x.get("externalIds") or {}
                pdf = (x.get("openAccessPdf") or {}).get("url")
                out.append({"title": x["title"], "year": x.get("year"), "authors": [a["name"] for a in x.get("authors") or []], "abstract": x.get("abstract") or "", "doi": ids.get("DOI", ""), "arxiv": ids.get("ArXiv", ""), "url": x.get("url", ""), "venue": x.get("venue", ""), "citation_count": x.get("citationCount", 0), "semantic_id": x.get("paperId"), "pdf_urls": ([pdf] if pdf else []) + (["https://arxiv.org/pdf/" + ids["ArXiv"]] if ids.get("ArXiv") else []), "sources": [{"provider": "semantic", "query": query, "url": x.get("url"), "at": now()}]})
            offset += len(rows)
            if not rows or data.get("next") is None:
                break
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
            if re.search(r"\b(?:all|ti|au|cat|abs):", query):
                expression = query
            else:
                # The whole query as one exact phrase missed papers that word it differently.
                terms = query_terms(query) or [query.replace('"', '')]
                expression = " AND ".join("all:" + ('"' + t + '"' if " " in t else t) for t in terms)
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

    def citations(self, paper, limit=20, directions=("references", "citations")):
        """Backward (references) and forward (citing papers) snowballing via Semantic Scholar."""
        ident = paper.get("semantic_id") or ("DOI:" + paper["doi"] if paper.get("doi") else ("ARXIV:" + paper["arxiv"] if paper.get("arxiv") else None))
        if not ident:
            return []
        out = []
        for direction in directions:
            key = "citedPaper" if direction == "references" else "citingPaper"
            data = self.net.get(f"https://api.semanticscholar.org/graph/v1/paper/{ident}/{direction}", {"fields": "title,year,authors,externalIds,abstract,openAccessPdf,citationCount,venue", "limit": min(limit, 100)})
            for row in data.get("data") or []:
                p = row.get(key) or {}
                if not p.get("title"):
                    continue
                ids = p.get("externalIds") or {}
                pdf = (p.get("openAccessPdf") or {}).get("url")
                out.append({"title": p["title"], "year": p.get("year"), "authors": [a["name"] for a in (p.get("authors") or [])], "doi": ids.get("DOI", ""), "arxiv": ids.get("ArXiv", ""), "abstract": p.get("abstract") or "", "venue": p.get("venue", ""), "citation_count": p.get("citationCount", 0), "semantic_id": p.get("paperId"), "pdf_urls": [pdf] if pdf else [], "sources": [{"provider": "citation-expansion", "direction": direction, "seed": identity(paper), "at": now()}]})
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


def oa_pdf_urls(paper, net):
    """Compatibility helper: only explicitly open-access OpenAlex locations."""
    from .download import openalex
    try:
        return list(dict.fromkeys(row['url'] for row in openalex(paper, net)))
    except Exception:
        return []


FULLTEXT_MIN_CHARS = 8000
FULLTEXT_MIN_PAGES = 3


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
    from .download import download_pdf, local_pdfs
    if not local_pdfs(snap):
        result = download_pdf(paper, directory, mcp, net, library, snapshot=snap)
        failures.extend(a for a in result['attempts'] if a.get('status') in ('failed', 'not_pdf', 'unconfigured'))
        if result['status'] == 'downloaded':
            attachment_key = result['attachment_key']
            found = extract_pdf(result['path'])
            for page in found:
                page['source'] = attachment_key
            pages = found
            source = result.get('source', {})
            sources.append({'id': attachment_key, 'type': 'pdf', 'url': source.get('url'),
                            'path': result['path'], 'sha256': result['sha256']})
            paper['pdf_attachment_key'] = attachment_key
            paper.setdefault('sources', []).append({'provider': 'oa-resolver' if source.get('provider') != 'primary' else 'primary',
                                                     'download_source': source, 'at': now()})
    paper.pop('evidence_refresh_required', None)
    text_size = sum(len(p["text"].strip()) for p in pages)
    abstract = paper.get("abstract") or snap["item"].get("abstractNote", "")
    # 1000 characters is a cover page or a first page, not a paper. Short extractions are
    # "partial": citable page by page, but the note must disclose what was not read.
    readable_pages = sum(1 for p in pages if len(p["text"].strip()) >= 200)
    if text_size >= FULLTEXT_MIN_CHARS and readable_pages >= FULLTEXT_MIN_PAGES:
        level, state = "fulltext", "readable"
    elif text_size >= 1000:
        level, state = "partial", "short_text"
    else:
        level = "abstract" if abstract else "metadata"
        state = "scan_or_short_text" if pages else "unavailable"
    # Existing notes, including human edits to generated notes, are context only.
    # They never substitute for primary-source evidence in claims.json.
    notes = snap["notes"]
    evidence = {"schema": 1, "item_key": paper["item_key"], "library_id": library, "title": paper["title"], "doi": paper.get("doi"), "abstract": abstract, "level": level, "fulltext_status": state, "retrieved_at": now(), "sources": sources, "pages": pages, "user_notes": notes, "annotations": [a for att in snap["attachments"] for a in att.get("annotations", [])], "metadata": snap["item"], "discovery_sources": paper.get("sources", []), "download_failures": failures}
    write_json(directory / "evidence.json", evidence)
    (directory / "fulltext.txt").write_text("\n\n".join(f"[{p['source']} p.{p['page']}]\n{p['text']}" for p in pages) or abstract, encoding="utf-8")
    paper.update(evidence_level=level, fulltext_status=state, text_chars=text_size, text_pages=readable_pages, download_failures=failures, evidence_hash=digest(json.dumps(evidence, sort_keys=True, ensure_ascii=False)), status="awaiting_analysis")
    run.save()
    return evidence


def import_input_files(run, net, files):
    """Merge host-collected export files (bib/ris/md) into the candidate pool."""
    records = list(run.state.get("candidates", []))
    done = set(run.state.get("queries_done", []))
    added = 0
    for filename in files:
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
        added += len(rows)
        done.add(task)
    run.state["queries_done"] = sorted(done)
    run.state["candidates"] = merge_candidates(records)
    run.save()
    write_json(run.path / "candidates.json", run.state["candidates"])
    return added


PROBE_URLS = {
    "semantic": ("https://api.semanticscholar.org/graph/v1/paper/search/bulk", {"query": "test", "limit": 1}),
    "crossref": ("https://api.crossref.org/works", {"rows": 1}),
    "arxiv": ("https://export.arxiv.org/api/query", {"search_query": "all:test", "max_results": 1}),
    "europepmc": ("https://www.ebi.ac.uk/europepmc/webservices/rest/search", {"query": "test", "format": "json", "pageSize": 1}),
    "openalex": ("https://api.openalex.org/works", {"per_page": 1}),
    "scholar": ("https://scholar.google.com/scholar", {"hl": "en", "q": "test"}),
    "researchgate": ("https://www.researchgate.net/search", {"q": "test"}),
    "xmol": ("https://www.x-mol.com/paper/search/q", {"option": "test"}),
}


def probe_sources(net, providers=None):
    """One light GET per source: classify reachability, never scrape results."""
    import os
    out = {}
    for name, (url, params) in PROBE_URLS.items():
        if providers and name not in providers:
            continue
        try:
            value = net.get(url, params, json_data=False, cache=False)
            ok = len(value) > 0
            out[name] = "ok" if ok else "empty"
        except Exception as exc:
            import re as _re
            m = _re.search(r"'(\d{3}) ", str(exc))
            status = m.group(1) if m else ""
            if status == "429":
                out[name] = "reachable (rate limited)"
            elif status in ("403", "404"):
                out[name] = "blocked for automation (host browser may still work)"
            elif status:
                out[name] = "reachable (HTTP " + status + ")"
            else:
                out[name] = type(exc).__name__ + ":" + str(exc)[:60]
    if not os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        out.setdefault("_hints", []).append("SEMANTIC_SCHOLAR_API_KEY 未配置，Semantic Scholar 匿名额度易限流")
    if not os.environ.get("OPENALEX_API_KEY"):
        out.setdefault("_hints", []).append("OPENALEX_API_KEY 未配置，openalex 源不可用")
    return out


def record_host_searches(run):
    """Emit search URLs for host-assisted providers; no HTTP is sent to them."""
    config = run.state["config"]
    done = set(run.state.get("queries_done", []))
    searches = run.state.setdefault("host_searches", [])
    for provider, url_for in WEB_SEARCH_URLS.items():
        if provider not in config.get("providers", []):
            continue
        for query in config.get("queries") or [config["topic"]]:
            task = provider + ":" + query
            if task in done:
                continue
            searches.append({"provider": provider, "query": query, "url": url_for(query, config.get("years")), "export_hint": WEB_SEARCH_EXPORT_HINTS[provider]})
            done.add(task)
            run.event("host_search_required", provider=provider, query=query)
    run.state["queries_done"] = sorted(done)
    if searches:
        write_json(run.path / "web_sources.json", {
            "schema": 1,
            "topic": config.get("topic"),
            "instructions": "宿主用浏览器或网页读取工具逐条打开 url，阅读结果并把间接相关的条目一并保留；用各站自带的导出/引用功能保存为文件，然后 resume --run PATH --input FILE 合并。这些站点禁止程序化抓取，只能宿主协作完成。",
            "export_hints": WEB_SEARCH_EXPORT_HINTS,
            "searches": searches,
        })
    run.save()


def discover(run, net):
    config = run.state["config"]
    providers = Providers(net)
    records = list(run.state.get("candidates", []))
    done = set(run.state.get("queries_done", []))
    for provider in config.get("providers", ["semantic", "crossref", "arxiv"]):
        if provider in WEB_SEARCH_URLS:
            continue
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
                status = re.search(r"'(\d{3}) ", str(exc))
                run.event("query_failed", provider=provider, query=query, error=type(exc).__name__, http_status=status[1] if status else None)
    record_host_searches(run)
    added = import_input_files(run, net, config.get("inputs", []))
    if added:
        records = list(run.state["candidates"])
    run.state["candidates"] = merge_candidates(records)
    if config.get("citation_hops", 0) and not run.state.get("citations_done"):
        # Seed from the most relevant hits, not whichever records happened to merge first.
        seeds = score_candidates(list(run.state["candidates"]), config.get("queries") or [config.get("topic", "")])[:5]
        records = list(run.state["candidates"])
        for seed in seeds:
            try:
                records.extend(providers.citations(seed))
            except Exception as exc:
                run.event("citation_expansion_failed", seed=identity(seed), error=type(exc).__name__)
        run.state["candidates"] = merge_candidates(records)
        run.state["citations_done"] = True
    run.state["status"] = "awaiting_selection"
    write_ranked(run)
    run.save()
    write_json(run.path / "candidates.json", run.state["candidates"])
    pending = len(run.state.get("host_searches", []))
    return {"run": str(run.path), "status": run.state["status"], "candidates": len(run.state["candidates"]), "host_searches": pending, "ranked": str(run.path / "candidates_ranked.md"), **({"next": "Open each url in web_sources.json with the host's browsing tools, save the sites' own exports, then resume --run PATH --input FILE; afterwards write selection.json with included [{id, reason}] and excluded [{id, reason}] and resume --selection FILE."} if pending else {"next": "Read candidates_ranked.md; write selection.json (mark core papers with reason \"core: ...\") with included [{id, reason}] and excluded [{id, reason}], then resume --selection FILE."})}


def snowball(run, net, limit=20):
    """Forward/backward snowballing from the papers already selected (or the top-ranked
    candidates before selection). New candidates are merged and re-ranked."""
    providers = Providers(net)
    seeds = run.state.get("papers") or score_candidates(list(run.state.get("candidates", [])), run.state["config"].get("queries") or [run.state["config"].get("topic", "")])[:5]
    before = {p["id"] for p in run.state.get("candidates", [])}
    records = list(run.state.get("candidates", []))
    failures = 0
    for seed in seeds:
        try:
            records.extend(providers.citations(seed, limit=limit))
        except Exception as exc:
            failures += 1
            run.event("citation_expansion_failed", seed=identity(seed), error=type(exc).__name__)
    run.state["candidates"] = merge_candidates(records)
    write_ranked(run)
    run.save()
    write_json(run.path / "candidates.json", run.state["candidates"])
    new = [p for p in run.state["candidates"] if p["id"] not in before]
    return {"run": str(run.path), "seeds": len(seeds), "failed_seeds": failures, "new_candidates": len(new), "ranked": str(run.path / "candidates_ranked.md"), "next": "Review the new candidates; to import them, write an updated selection.json (keep earlier inclusions) and resume --selection."}


def triage(run):
    """Group papers by the evidence actually obtained, so note depth follows the source."""
    from .notes import DEFAULT_TIER
    papers = [p for p in run.state.get("papers", []) if p.get("evidence_level")]
    order = ["fulltext", "partial", "abstract", "metadata"]
    groups = {level: [p for p in papers if p["evidence_level"] == level] for level in order}
    label = {"fulltext": "全文", "partial": "部分全文", "abstract": "仅摘要", "metadata": "仅元数据"}
    work = {"deep": "精读笔记（9 栏，带数字与页码证据）", "brief": "简报（5 栏，≤1800 字）", "stub": "占位条目（3 栏，≤600 字）"}
    lines = ["# 证据分诊", "", "笔记深度由已取得的证据决定，而不是一律填 13 栏。先尽量把「仅摘要/仅元数据」升级为全文，再动笔。", "", "| 证据 | 篇数 | 默认笔记 |", "|---|---|---|"]
    for level in order:
        lines.append(f"| {label[level]} | {len(groups[level])} | {work[DEFAULT_TIER[level]]} |")
    readable = groups["fulltext"] + groups["partial"]
    core = [p for p in readable if str(p.get("inclusion_reason", "")).casefold().startswith("core")]
    if core:
        # selection.json reasons starting with "core" mark the review's anchors; other full texts get briefs.
        lines += ["", f"## 建议精读（core，{len(core)} 篇）", "", "其余 %d 篇全文条目建议 `note-template --tier brief`。" % (len(readable) - len(core)), ""]
        lines += [f"- {p.get('title', '')[:90]} — `{p['id']}`" for p in core]
    missing = groups["abstract"] + groups["metadata"] + groups["partial"]
    if missing:
        lines += ["", "## 可升级为全文的条目", "", "通过机构访问、作者主页或预印本取得 PDF 后：附到 Zotero 条目并运行 `resume --run PATH --refresh-evidence`；或写 verified links JSON 用 `fetch-pdfs --run PATH --links FILE`，再 `resume --run PATH`。", ""]
        for p in missing:
            link = "https://doi.org/" + p["doi"] if p.get("doi") else (p.get("url") or "")
            lines.append(f"- [{label[p['evidence_level']]}] {p.get('title', '')[:90]} — `{p['id']}` {link}")
    (run.path / "triage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {level: len(groups[level]) for level in order}


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
        # Topic collections nest under a dedicated parent (default "Agent") so the
        # user's own collection tree stays untouched; empty value opts out to root.
        parent = mcp.ensure_collection(config["parent_collection_name"], config.get("library", 1)) if config.get("parent_collection_name") else None
        config["collection"] = mcp.ensure_collection(config.get("collection_name") or config["topic"], config.get("library", 1), parent=parent)
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
                paper["import_created"] = result.get("created", True)
                paper["supplemented_fields"] = result.get("supplemented", [])
                paper["status"] = "imported"
                run.save()
            # fetch-pdfs flags items whose new PDF must replace abstract-level evidence.
            if paper["status"] not in ["awaiting_analysis", "published"] or paper.get("evidence_refresh_required"):
                collect_evidence(run, paper, mcp, net)
        except Exception as exc:
            paper["status"] = "error"
            paper["error"] = type(exc).__name__ + ": " + str(exc)
            run.save()
    run.state["status"] = "complete" if all(p["status"] == "published" for p in run.state["papers"]) else "awaiting_analysis" if all(p["status"] in ["awaiting_analysis", "published"] for p in run.state["papers"]) else "partial_failure"
    counts = triage(run)
    run.save()
    return {"run": str(run.path), "status": run.state["status"], "evidence": counts, "triage": str(run.path / "triage.md"), "papers": [{"id": p["id"], "key": p.get("item_key"), "status": p["status"], "evidence": p.get("evidence_level")} for p in run.state["papers"]], "next": "Read triage.md first. Upgrade what you can to full text, then write one note per paper at the depth its evidence supports (references/notes.md); publish-note --run PATH --paper ID."}
