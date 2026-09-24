# Deep search

The CLI is a resumable workflow, not a second LLM. Run it from the skill folder:

```text
python scripts/zotero_cli.py deep-search --topic "机器学习原子势" --query "machine learning interatomic potentials" --query "equivariant interatomic potentials" --query "atomic cluster expansion" --limit 100 --collection-name "机器学习原子势"
```

`--providers semantic crossref arxiv` is the default. Europe PMC is useful for biomedical topics. OpenAlex is optional and requires `OPENALEX_API_KEY`; Semantic Scholar accepts `SEMANTIC_SCHOLAR_API_KEY`. Rate limits and outage failures remain in run.json; inspect them before claiming search coverage. `--years 2018-2026` (hyphen form; other separators are normalized), `--candidate-limit`, `--citation-hops 0|1` control discovery. With arXiv only, `--query id:ID1,ID2` is a reproducible seed lookup, not a broad search.

**Host-assisted sources (default on): `scholar`, `xmol`; `researchgate` is available but opt-in only — its login walls, email-token verification and anti-bot checks cost more than the marginal coverage it adds over Crossref/Semantic Scholar.** These sites offer no bulk API and forbid programmatic scraping, so the CLI never sends them HTTP. Instead it writes `web_sources.json` into the run directory: one ready-to-open search URL per provider per query (Scholar with year bounds), plus per-site export hints. The host agent opens each URL with its own browsing/reading tools, reads the results, saves the site's own citation exports (Scholar Cite→BibTeX, ResearchGate Export citation→RIS, X-MOL: copy DOIs/titles into a .md list; some results require login) or DOI lists, then merges them:

```text
python scripts/zotero_cli.py resume --run PATH --input scholar.bib --input digest.ris
```

Merged entries are DOI-resolved against Crossref and deduplicated into candidates.json; re-merging the same file is a no-op. Search coverage is only complete after every `web_sources.json` URL has been read this way or its failure is recorded.

**Selection policy: recall before precision — 应得尽得，全量入库。** Indirectly related candidates (adjacent materials, neighboring methods, applied-domain variants) often open new research directions; do not exclude them as redundancy. **The default is to import every relevant candidate into Zotero**; the candidate pool exists to be collected, not to be skimmed for a hand-picked few. Rules:

1. `--limit` is the discovery/selection budget — set it high enough to cover the whole relevant candidate pool (`--limit 500` for a normal topic scan), never a convenience cap for a demo. A pool of N relevant candidates must yield ~N imported items, not a curated subset.
2. Reserve `excluded` for **true noise only** (off-domain keyword hits, duplicate records, editor letters, non-scientific items). Every exclusion gets an individual, specific reason; batch exclusions with a blanket rationale are not acceptable for on-topic candidates. When in doubt, include — an extra library item costs nothing, a missing one silently biases later reviews.
3. Distill/review depth is decoupled from import: import everything relevant first, then choose which items to distill into notes. "固定集合专题综述" describes the **distilled** subset, never the library scope; the full pool stays in the collection for future expansion and snowballing.
4. After import, verify: the Zotero collection item count must equal (included − pre-existing duplicates); report the number. A large gap between pool size and imported count requires justification in the run report.

Read candidates.json. Write selection.json with `included: [{id, reason}]` and `excluded: [{id, reason}]`; reasons must describe relevance, not citation count alone. Record query scope and missing providers. Then:

```text
python scripts/zotero_cli.py resume --run PATH --selection PATH/selection.json
```

This imports/reuses papers, adds collection membership, retrieves PDFs and writes per-paper evidence.json plus complete page-labeled fulltext.txt. For each paper follow notes.md and publish it. `resume --run PATH --discover` retries failed discovery requests; it preserves successful cached queries.

Export adapters: `--input scholar.bib`, `--input digest.ris`, `--input digest.md`. Markdown discovery uses DOI identifiers and resolves them; don't treat third-party summaries as paper full text. Google Scholar and X-MOL provide no bulk API. Browse supplemental results with the host's browser when appropriate, then save structured exports or identifier lists. Do not automate forbidden scraping or bypass access controls.

PDF attempts use provider links and official arXiv links. Existing PDFs are preferred. All failed attempts remain in evidence. Preserve TLS validation using the OS trust store; do not work around certificate failures by disabling verification. When every open-access resolver is exhausted, a last-resort `scihub` chain resolves a live mirror list (updated as links die and return) before falling back to a hardcoded set, then queries each mirror for the DOI and follows the embedded `#pdf` link; mirror bot-check pages are skipped automatically and every attempt is recorded in the download report. For accessible full text missed by providers, obtain it through the host's authorized tools and attach it, then refresh evidence. Avoid claiming exhaustive coverage from finite search limits.
