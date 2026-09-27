# Deep search

The CLI is a resumable workflow, not a second LLM. Run it from the skill folder.

## 1. Plan the queries before running anything

A single phrase finds only papers worded like that phrase. Map terminology and research questions first. Broad domains may start with 8–16 short queries and grow according to coverage; this is not a quota. Include English terms, acronyms and older terminology even for a Chinese input. Cover different **axes**, not just synonyms:

- core method names and their common abbreviations (e.g. "equivariant interatomic potential", "MACE", "NequIP")
- the problem stated without method words ("DFT accuracy molecular dynamics large systems")
- the application domain × method ("machine learning potential electrolyte")
- the competing or older approach, so that comparisons are found ("classical force field polarizable electrolyte")
- review/benchmark queries ("benchmark machine learning potentials")

Keep each query short (3–6 content words). Use quotes only around true fixed phrases.

The host can persist a plan with `facets: [{name, queries: [...]}]`, plus optional `topic`, `scope`, `questions` and `stop_rule`. Run `deep-search --topic DOMAIN --plan FILE`. Topic-only calls write an `awaiting_query_plan` scaffold; fill it and immediately continue with `resume --run PATH --plan FILE --discover`. Do not hand the ordinary planning work back to the user.

For electrolyte MLIPs, separate model families (GAP, DeePMD, equivariant/universal models), active learning, liquid structure/solvation, transport, organic/aqueous/concentrated liquids, ionic liquids/deep eutectics, interfaces/SEI/reactivity, long-range charge, uncertainty/transferability and experimental validation. Treat adjacent systems as labelled branches rather than mixing their conclusions. This example illustrates domain decomposition, not a universal checklist.

```text
python scripts/zotero_cli.py deep-search --topic "机器学习原子势" \
  --query "machine learning interatomic potentials" --query "equivariant interatomic potential" \
  --query "atomic cluster expansion" --query "benchmark machine learning potentials" \
  --years 2018-2026 --limit 150 --collection-name "机器学习原子势"
```

Providers: `semantic crossref arxiv` by default (Europe PMC for biomedical topics; OpenAlex with `OPENALEX_API_KEY`). Semantic Scholar uses relevance search and falls back after HTTP 429 to bulk retrieval; the fallback is recorded because bulk order is not relevance order. arXiv uses AND between terms, so overlong queries can still be restrictive. `--citation-hops 1` runs backward/forward expansion with configurable `--citation-seeds` (8) and `--citation-limit` (50 per direction). Seeds span query hits; citation calls support pagination and API-key authentication.

Adapter pagination/endpoint semantics: [Semantic Scholar official API documentation](https://api.semanticscholar.org/api-docs/snippets) and [official pagination tutorial](https://www.semanticscholar.org/product/api/tutorial). Bulk retrieval can also be rate limited; a fallback is not a guarantee of availability.

Defaults: 150 candidates per provider/query, 200 selected papers. These are execution budgets, not domain-size assumptions. Inspect `coverage.md`/`.json`: failures, zero hits, cap hits, unique additions, research facets, pending browser work and evidence levels. A full page suggests truncation, not exhaustion. Extend without restarting:

```text
resume --run PATH --query "deep potential electrolyte transport" --query "electrolyte force field transferability"
resume --run PATH --candidate-limit 300 --discover
resume --run PATH --limit 400 --selection selection.json
coverage --run PATH
```

Failed queries stay in `run.json` with their HTTP status; read them before claiming coverage and retry with `resume --run PATH --discover`.

## 2. Host-assisted sources

`scholar` and `xmol` are on by default; `researchgate` is opt-in (login walls and bot checks cost more than they add). These sites have no bulk API and forbid scraping, so the CLI never sends them HTTP. It writes `web_sources.json` with one search URL per provider per query. Open each URL with your browsing tools, save the site's own export (Scholar Cite → BibTeX; X-MOL: copy DOIs/titles into a `.md` list), then merge:

```text
python scripts/zotero_cli.py resume --run PATH --input scholar.bib --input xmol.md
```

Merged entries are DOI-resolved via Crossref and deduplicated. If a URL could not be read (login, captcha), record that instead of pretending it was covered.

Record outcomes with `resume --run PATH --host-status FILE`: a JSON list of `{provider, query, status, note}`. Status is `completed`, `blocked` or `empty`; note identifies inspected results/export or the access failure. Generated links and imported exports alone do not prove every query was completed.

## 3. Select from the ranked list

Read `candidates_ranked.md`, not the raw JSON. It lists every candidate with a transparent score (query-term hits in title/abstract, number of providers that found it, citations, whether an abstract/PDF exists) plus an abstract snippet. The score is triage only; you decide.

The ranked snippet is only a navigation aid: do not exclude on a truncated abstract. `screening-batch --run PATH --size 40` writes the next unassessed records with full abstracts. Save each batch's decisions as `included`/`excluded`/`deferred` lists, then `screening-batch --run PATH --decisions FILE` merges decisions into cumulative `selection.json` and returns the next batch, without importing anything. This also supports all-excluded batches. Revisit deferred items separately. After screening, `resume --selection PATH/selection.json` imports the relevant set; a batch size does not cap total inclusions.

Preprints and their journal versions are merged (arXiv/ChemRxiv/bioRxiv/SSRN DOIs are kept as `preprint_doi`), so one paper appears once.

Selection rules:

1. **Include** everything on-topic, plus adjacent work that could change the review's framing (neighbouring methods, competing approaches, key applications). Recall matters at import time: an extra library item is cheap.
2. **Exclude** noise with a specific reason each (off-domain keyword hits, errata, editorials). No blanket reasons for on-topic items.
3. Mark anchors with `"core": true` and optional `"facets": ["solvation"]`; legacy `reason: core: ...` works too. Select anchors per question and branch: foundations, mechanisms, quantitative tests, disagreements. There is no fixed total of 3, 10 or 20 anchors. Peripheral papers can receive briefs; don't downgrade core full texts for convenience.
4. `--limit` caps inclusions; raise it to fit the relevant pool. Screen every candidate in manageable batches. Missing decisions are `unassessed`, never implicit exclusions. Put genuinely pending decisions into `deferred: [{id, reason}]`. Never use 'first batch/core only/budget' as a relevance exclusion. Continue subsequent batches autonomously within the user's scope. Keep all prior inclusions when updating selection.json; the CLI rejects silent removal.

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

After selection, run `resume --run PATH --snowball`. It expands a budgeted, diverse seed set and re-ranks. Completed seed/direction tasks are checkpointed; failures remain retryable. Add worthwhile papers (retain earlier inclusions) and continue. Inspect anchor bibliographies if a citation API fails. Stop when major questions and disagreements have evidence and successive expansions add no important on-topic branch, or the user's budget is reached. Failure-induced low yield is not saturation. Record the stopping reason and unresolved gaps.

## 5. Full text before notes

Read `triage.md`. For every `abstract`/`metadata`/`partial` item, try legal routes first: institutional access, author pages, preprint servers, PMC. Attach the PDF in Zotero and run `resume --run PATH --refresh-evidence`, or write a verified links file (`item_key`, `url`, `source`, `version`) for `fetch-pdfs --run PATH --links FILE` and then `resume --run PATH` (downloaded items are re-collected automatically). Then write notes per [notes.md](notes.md).

Preserve TLS validation (the OS trust store is used); never disable certificate checks. Do not bypass paywalls or access controls. Never claim exhaustive coverage from finite search limits; report queries, providers, failures and the date searched.
