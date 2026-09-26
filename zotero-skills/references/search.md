# Deep search

The CLI is a resumable workflow, not a second LLM. Run it from the skill folder.

## 1. Plan the queries before running anything

A single phrase finds only papers worded like that phrase. Before `deep-search`, write 4–8 queries that cover different **axes**, not synonyms of one phrase:

- core method names and their common abbreviations (e.g. "equivariant interatomic potential", "MACE", "NequIP")
- the problem stated without method words ("DFT accuracy molecular dynamics large systems")
- the application domain × method ("machine learning potential electrolyte")
- the competing or older approach, so that comparisons are found ("classical force field polarizable electrolyte")
- review/benchmark queries ("benchmark machine learning potentials")

Keep each query short (3–6 content words). Use quotes only around true fixed phrases.

```text
python scripts/zotero_cli.py deep-search --topic "机器学习原子势" \
  --query "machine learning interatomic potentials" --query "equivariant interatomic potential" \
  --query "atomic cluster expansion" --query "benchmark machine learning potentials" \
  --years 2018-2026 --limit 150 --collection-name "机器学习原子势"
```

Providers: `semantic crossref arxiv` by default (Europe PMC for biomedical topics; OpenAlex with `OPENALEX_API_KEY`; Semantic Scholar is less rate-limited with `SEMANTIC_SCHOLAR_API_KEY`). Semantic Scholar uses its relevance-ranked search (up to 1000 results per query). arXiv queries are sent as an AND of terms, not one exact phrase. `--citation-hops 1` (default) runs backward **and** forward citation expansion from the 5 most relevant hits.

Failed queries stay in `run.json` with their HTTP status; read them before claiming coverage and retry with `resume --run PATH --discover`.

## 2. Host-assisted sources

`scholar` and `xmol` are on by default; `researchgate` is opt-in (login walls and bot checks cost more than they add). These sites have no bulk API and forbid scraping, so the CLI never sends them HTTP. It writes `web_sources.json` with one search URL per provider per query. Open each URL with your browsing tools, save the site's own export (Scholar Cite → BibTeX; X-MOL: copy DOIs/titles into a `.md` list), then merge:

```text
python scripts/zotero_cli.py resume --run PATH --input scholar.bib --input xmol.md
```

Merged entries are DOI-resolved via Crossref and deduplicated. If a URL could not be read (login, captcha), record that instead of pretending it was covered.

## 3. Select from the ranked list

Read `candidates_ranked.md`, not the raw JSON. It lists every candidate with a transparent score (query-term hits in title/abstract, number of providers that found it, citations, whether an abstract/PDF exists) plus an abstract snippet. The score is triage only; you decide.

Preprints and their journal versions are merged (arXiv/ChemRxiv/bioRxiv/SSRN DOIs are kept as `preprint_doi`), so one paper appears once.

Selection rules:

1. **Include** everything on-topic, plus adjacent work that could change the review's framing (neighbouring methods, competing approaches, key applications). Recall matters at import time: an extra library item is cheap.
2. **Exclude** noise with a specific reason each (off-domain keyword hits, errata, editorials). No blanket reasons for on-topic items.
3. Mark the **core set** in the reasons: the 10–20 papers that the review will lean on (foundational methods, strongest results, direct disagreements). Write `"reason": "core: …"`. These get deep notes; the rest get briefs. Import breadth and reading depth are separate decisions.
4. `--limit` caps how many can be included. Set it to the size of the relevant pool, not a demo number.

`selection.json`:

```json
{"included": [{"id": "…", "reason": "core: first equivariant potential with data-efficiency results"},
              {"id": "…", "reason": "application of ACE to Li electrolytes; adjacent domain"}],
 "excluded": [{"id": "…", "reason": "astronomy 'potential' keyword hit"}]}
```

```text
python scripts/zotero_cli.py resume --run PATH --selection PATH/selection.json
```

This imports or reuses items (existing fields, notes and attachments are never overwritten), retrieves PDFs through open-access resolvers, writes per-paper `evidence.json` and page-labelled `fulltext.txt`, and writes `triage.md`.

## 4. Snowball from what you chose

After selection, run `resume --run PATH --snowball`. It expands references and citing papers of the selected set, re-ranks, and reports how many candidates are new. Add worthwhile ones to `selection.json` (keep earlier inclusions) and `resume --selection` again. One round is usually enough; stop when a round adds few on-topic papers.

## 5. Full text before notes

Read `triage.md`. For every `abstract`/`metadata`/`partial` item, try legal routes first: institutional access, author pages, preprint servers, PMC. Attach the PDF in Zotero and run `resume --run PATH --refresh-evidence`, or write a verified links file (`item_key`, `url`, `source`, `version`) for `fetch-pdfs --run PATH --links FILE` and then `resume --run PATH` (downloaded items are re-collected automatically). Then write notes per [notes.md](notes.md).

Preserve TLS validation (the OS trust store is used); never disable certificate checks. Do not bypass paywalls or access controls. Never claim exhaustive coverage from finite search limits; report queries, providers, failures and the date searched.
