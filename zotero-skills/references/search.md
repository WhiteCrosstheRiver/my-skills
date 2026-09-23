# Deep search

The CLI is a resumable workflow, not a second LLM. Run it from the skill folder:

```text
python scripts/zotero_cli.py deep-search --topic "机器学习原子势" --query "machine learning interatomic potentials" --query "equivariant interatomic potentials" --query "atomic cluster expansion" --limit 100 --collection-name "机器学习原子势"
```

`--providers semantic crossref arxiv` is the default. Europe PMC is useful for biomedical topics. OpenAlex is optional and requires `OPENALEX_API_KEY`; Semantic Scholar accepts `SEMANTIC_SCHOLAR_API_KEY`. Rate limits and outage failures remain in run.json; inspect them before claiming search coverage. `--years 2020-2026`, `--candidate-limit`, `--citation-hops 0|1` control discovery. With arXiv only, `--query id:ID1,ID2` is a reproducible seed lookup, not a broad search.

Read candidates.json. Write selection.json with `included: [{id, reason}]` and `excluded: [{id, reason}]`; reasons must describe relevance, not citation count alone. Record query scope and missing providers. Then:

```text
python scripts/zotero_cli.py resume --run PATH --selection PATH/selection.json
```

This imports/reuses papers, adds collection membership, retrieves PDFs and writes per-paper evidence.json plus complete page-labeled fulltext.txt. For each paper follow notes.md and publish it. `resume --run PATH --discover` retries failed discovery requests; it preserves successful cached queries.

Export adapters: `--input scholar.bib`, `--input digest.ris`, `--input digest.md`. Markdown discovery uses DOI identifiers and resolves them; don't treat third-party summaries as paper full text. Google Scholar provides no bulk API; Paper Digest supports exports. Browse supplemental results with the host's browser when appropriate, then save structured exports or identifier lists. Do not automate forbidden scraping or bypass access controls.

PDF attempts use provider links and official arXiv links. Existing PDFs are preferred. All failed attempts remain in evidence. Preserve TLS validation using the OS trust store; do not work around certificate failures by disabling verification. For accessible full text missed by providers, obtain it through the host's authorized tools and attach it, then refresh evidence. Avoid claiming exhaustive coverage from finite search limits.
