---
name: project-explainer-3b1b
description: Turn a research project's working files (plans, ledgers, logs, data, figures) into a single shareable, multilingual HTML explainer styled after 3Blue1Brown — dark canvas, Manim palette, KaTeX math, animated vector charts and interactive physics scenes. Use when the user asks to summarize, visualize, present or share a project's motivation, objectives, principles, progress, key data and remaining work, especially for advisors, collaborators or international readers. Triggers include "explain my project as a page", "3b1b style summary", "project overview HTML", "share progress with my teacher/labmates".
---

# Project explainer (3Blue1Brown style)

Produces **one self-contained `.html` file** that explains a research project the way a 3Blue1Brown video would: one idea per screen, visual first, every number drawn as a vector graphic, math typeset properly. Content is plain JSON; the engine in `assets/template.html` renders it. No build tools, no frameworks.

```
assets/template.html          engine + styles (generic; add scenes here)
references/report-schema.md   every block type, with JSON examples
scripts/init.ps1              create <project>/.explainer workspace, vendor the engine
scripts/build.py | build.ps1  report.json -> single HTML (inlines figures, resolves $include)
scripts/check.py | check.ps1  what changed since the last update, and which sections it feeds
```

## First decide: create or update?

Look for `<project>/.explainer/`. **If it exists, this is an update: follow "Incremental update" below and do not re-read the whole project or rewrite report.json.** Only create from scratch when there is no workspace (or the user explicitly asks for a fresh page).

### The workspace (hidden, kept forever)

```
<project>/<name>_explainer.html     the page people open and share
<project>/.explainer/               hidden on Windows (attribute) and Unix (dot)
  report.json          all content, multilingual; the only thing edited by hand
  data/*.json          arrays extracted from project files, pulled in with {"$include": "data/x.json"}
  extract/*            scripts that regenerate data/ from the raw files (never retype data)
  assets/*             figures inlined at build time (copy, do not link into the ledger)
  sources.json         hand-written map: source file -> sections it feeds; watched folders; extracts
  fingerprints.json    written by check -Stamp: size/lines/sha256 of each source at the last update
  engine/              vendored template + build/check scripts, so the page rebuilds without the skill
  CHANGELOG.md         one dated line per update
  README.md            the three update commands
```

Create it with `powershell -File scripts/init.ps1 -Project <root>`; after improving the skill's template, push it into a project with `-RefreshEngine`.

## Incremental update (the normal case, saves most of the tokens)

1. `powershell -File .explainer/engine/check.ps1 -Dir .explainer` (or `python .explainer/engine/check.py --dir .explainer`). It lists:
   - `APPENDED ... read from line N`: read **only from line N** (Read with `offset`), not the whole log
   - `CHANGED` / `NEW` sources and `NEW FILE`s in watched folders: read just these
   - `RE-RUN` extracts: run them; the data files update and the charts follow at build
   - the **sections to revisit**
   If it says `none`, stop: the page is current.
2. Read the delta. Decide which facts moved (a check passed, a count grew, a stage changed state, a new failure).
3. Edit **only the affected blocks** in `report.json` with targeted Edit calls: chip values, a `progress` point, a `roadmap` state, a table row, a new `timeline` item. Update every language in the same edit. Never rewrite the file.
4. New kind of evidence, such as a new figure or record type? Add it to `sources.json` (and an extract script if it has data) so the next check tracks it.
5. Rebuild with `.explainer/engine/build.ps1` (seconds, no tokens), spot-check the changed sections in a browser, and switch languages once.
6. `check.ps1 -Dir .explainer -Stamp` to record the new baseline; append one line to `CHANGELOG.md` (date, what changed, which sections).

## Create from scratch

1. **Read the project before writing anything.** Find, in this order: the current master plan, the latest status/daily log, the original proposal (for motivation), experiment records with numbers, data manifests/CSVs, existing figures. Big ledgers: read heads/tails and grep; never guess. Note the source file of every number you will use.
2. **Separate four kinds of fact** and keep them visibly separate on the page:
   - *done & verified* (measured, passed a check) — `state:"done"`
   - *in progress* (submitted, running, interim) — `state:"doing"`
   - *planned* (in the plan, not started) — `state:"todo"` / dashed `plan` points
   - *failed / deferred* — `state:"fail"` / `"skip"`. Failures are part of the story; never hide them.
3. **Outline the sections** (adapt names to the project):
   1. Hero — title, one-sentence pitch, 3–5 honest status chips, an animated scene
   2. Motivation — the original question and why it matters; one interactive "intuition" scene if the physics allows
   3. Objectives — the concrete questions and the deliverables (e.g. planned main figures)
   4. Principles — the method as a pipeline, then 3–5 key equations with one-line plain-language captions
   5. Journey — dated timeline including pivots and what was learned
   6. Key data — the real plots (see below), each with source and caveat
   7. Progress board — stage roadmap, checks/gates with pass/fail, milestones
   8. Remaining work and open decisions
   9. Honest bottom line — what can and cannot be claimed today
4. **Set up the workspace** with `scripts/init.ps1`, then write `.explainer/report.json` (schema in `references/report-schema.md`). Long numeric arrays: write a small script in `extract/` that produces `data/x.json` from the raw file and reference it with `{"$include": "data/x.json"}`. Copy project figures into `assets/`.
5. **Fill `sources.json`**: every file you used, with the sections it feeds (`"kind": "append"` for logs that only grow), the folders where new records appear (`watch`), and the extracts with their inputs.
6. **Build**: `powershell -File .explainer/engine/build.ps1 -Report .explainer/report.json -Out <name>_explainer.html` (or `python .explainer/engine/build.py ...`).
7. **Verify in a browser**. A local file can't run scripts in Claude's browser pane, so serve the folder on localhost. Switch every language, toggle the theme, check each chart against its source numbers, check phone width (375 px) for horizontal scroll, and read the console for errors. Fix and rebuild.
8. **Stamp**: `check.ps1 -Dir .explainer -Stamp`, then add the first CHANGELOG line.

## Plots: which block for which data

| Data shape | Block |
|---|---|
| a few categories × 1–3 series, optional pass threshold | `bar` (use `scale:"log"` for values spanning decades) |
| many per-sample values by group (QA scores, errors) | `strip` (jittered dots, threshold line) |
| one value vs targets/thresholds | `numberline` (the classic 3b1b number line) |
| durations / survival / ranges per system | `ranges` (`end:"crash"` or `"continue"`) |
| a count growing over time, with planned future | `progress` |
| method flow | `pipeline`; stages → `roadmap`; history → `timeline` |
| existing figure from the project (SVG preferred) | `figure` with `"file"`; `invert:true` adapts white-background plots to dark mode |

Prefer redrawing from data over embedding raster images. Every chart gets a `source` (file path) and a `caption` that states the caveat (snapshot date, interim model, unequilibrated, etc.).

## 3Blue1Brown style rules

- Dark canvas, Manim colours: blue `#58C4DD`, teal, green, yellow, gold, red, purple. Use colour *semantically and consistently* across the page (e.g. cation = yellow, anion = red, solvent = blue; done = green, running = yellow, failed = red).
- Serif (Computer-Modern-like) for titles and math, clean sans for body.
- One idea per block; short paragraphs; build intuition before the formula, then caption the formula in plain words.
- Motion has meaning: lines draw in, bars grow, points pop — only on first reveal; reduced-motion users get static frames.
- Interactive scenes (`scene` block) are where the page earns its 3b1b feel: a slider or button that changes one parameter and shows the consequence. Built-ins: `nanotube` (ions in a tube, field on/off breaks pairs) and `coulombTilt` (Coulomb well tilted by a field). Add a new scene in `SCENES` inside the template when the project needs a different intuition; keep it under ~120 lines, theme-aware (`var(--…)`), paused off-screen.

## Multilingual

Readers may be international. Every user-visible string is either a plain string (same in all languages) or an object `{"en": "...", "zh": "..."}`; list the languages in `meta.languages`. English is the fallback for any missing key. To add a language (e.g. `ja`, `de`): add it to `meta.languages`, add its strings to each object, and add a `ui.<lang>` block for interface words (see schema). Write each language natively — do not leave machine-literal translations of technical terms; keep established English terms (DFT, qNEP, CP2K) untranslated. Language choice persists and `?lang=zh` works in links.

## Honesty rules (non-negotiable)

- Only numbers that exist in the project files. If a value is a range or approximate in the source, show it as such.
- Interim results are labelled interim; snapshots carry their date; planned items are dashed/hollow and say "planned".
- If no physical result exists yet, say so plainly on the page (a `callout` in the bottom line). The page is for advisors — overselling costs more than it gains.
- Credit sources in `sources`; do not invent citations.

## Sharing

The output is a single file that works offline except KaTeX (loaded from cdnjs; without network the formulas fall back to raw TeX). It can be emailed, put on a lab drive, or published as a private artifact on request. Research may be unpublished — ask before publishing anywhere.
