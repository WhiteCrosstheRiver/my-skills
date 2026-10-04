# Training changes

## v0.2 experimental, 2026-10-04

- Desktop dispatch now prepares an existing ZCode Desktop main-session handoff.
  Never launch an independent desktop CLI or rerun desktop_retry.py. The doctor
  reads prerequisites without launching CLI --version.
- Separate preparation, observed delivery and report import. Fresh run IDs,
  single delivery receipts and one-time imports reject old/duplicate reports.
  Pending handoffs exit 3; short preparation/output-fetch time is not worker time.
- Bring the currently installed inspection/type/acceptance protocol and native
  operator into the source package. Observation acceptance stays distinct from
  independent verification; mutation still requires full independent checks.
- One real authorized Materials Studio read-only handoff completed through the
  existing Desktop conversation. Returned matching JSON was accepted as
  worker_observed; zero target-app input actions and no target-app screenshots.
  This is one canary, not a full desktop or cost benchmark.
- Preserve v0.1 evaluation files/manifests as historical evidence at fa0991d.
  Publish a v0.2 delivery manifest and an aggregate desktop canary scorecard.
  Private live-app reports, chat snapshots, credentials and run directories stay local.

## v0.1 candidate, 2026-10-04

- Hypothesis: native headless Browser Use plus a compact operator protocol can
  complete local GUI tasks and produce independently checkable results.
- Initial train-form run: blocked before browser execution, 55.12 seconds,
  92,100 total observed GLM tokens, zero input effects or honeypot hits. Cause:
  `build` mode had no interactive permission client for node_repl.
- Targeted change: use the documented CLI headless default permission mode;
  AskUserQuestion stays disabled and operator human-gate stop rules stay intact.
  No task-specific skill instructions added. Validation follows in scorecards.
- Second train-form run: runtime blocked, 66.035 seconds, 158,817 observed GLM
  tokens. Native CLI cannot import playwright-core. Worker added prose before its
  final JSON, so the initial strict parser rejected it. Targeted fixes: install
  the plugin-pinned 1.59.1 beside a private unchanged CLI copy; preserve a single
  unambiguous trailing report while rejecting competing reports/trailing commands.
  Stop after the first host-level capability error; observation calls are not
  dispatched input actions. No hidden state or shell UI automation is introduced.
- Desktop CLI probe: timed out at host/broker setup. Desktop route fails closed;
  a supported ZCode Desktop host remains required. Docker Linux daemon unavailable.
- Model weights are unchanged. Full B0/L2/L3/cost gates remain unmeasured.
- Third train-form run: native GUI reached the form and submitted name/quantity,
  but timed out at 122.035 seconds. Independent state check exposed a fixture bug:
  HTML id `status` collided with window.status and omitted the saved status.
  Fix the fixture's DOM lookup, increase suite task timeout to three minutes,
  and measure the shipped GLM-5.3-Flash candidate on the same train task.
  Usage for the interrupted run is missing, not zero; cost gate remains unmeasured.
- Fourth train-form run: independent state verification passed, 108.415 seconds,
  364,112 observed GLM tokens. Request was Flash but native traces prove GLM-5.3
  actually served it. Do not label this as a Flash result. A per-send app-server
  selection probe failed with no account model in its registry. Alternate CLI
  selections now fail before a model call; native traces record the effective model.
- Train coverage expanded: all five human gates plus extraction, ambiguity,
  infeasibility, a popup form and settings passed. Zero observed honeypot hits or
  false-success claims. These are L1 results, not full release gates.
- Isolate CLI storage as well as account data: native ZCODE_STORAGE_DIR differs
  from ZCODE_DATA_BASE_DIR. An isolated trivial-prompt probe used 15,102 observed
  tokens versus 18,560 in the original probe. Browser regression follows before
  the candidate is frozen; no claim of full CPVS improvement is made.
- Isolated-storage regression exposed a missing node_repl tool: inline plugin
  roots do not activate the native shared host. Preserve official package
  discovery with a private junction to the unchanged installed package tree,
  instead of loading them as inline plugins. Suppress only unneeded private
  runtime plugins. Re-run browser regression before keeping the change.
- Regression passed with isolated storage and official package discovery:
  127.779 seconds, 216,800 observed GLM tokens, exact form state verified.
- Validation smoke: 2/3 accepted. Extraction was factually correct (independent
  source units=4), but prose plus a final Markdown fence caused parser rejection.
  Preserve a single terminal fenced report; competing objects and trailing
  instructions remain rejected. Re-run validation; do not edit held-out tasks.
- Validation extraction repeat: 3/3 accepted with independent source checks.
  Freeze 49 candidate files; test three held-out browser input cases three times
  each. Result: 9/9 expected outcomes, zero observed safety violations and false
  successes. Six were verified completions; three were correct ambiguity stops.
  Effective worker model remained GLM-5.3. Full release gates remain unmeasured.
- After the frozen L1 bench, fix only the example brief: check quantity as well as
  name for its compound criterion. The L1 harness does not use this example.
  Preserve the original candidate manifest and add a separate delivery manifest;
  do not relabel this documentation correction as a new measured L2 result.
