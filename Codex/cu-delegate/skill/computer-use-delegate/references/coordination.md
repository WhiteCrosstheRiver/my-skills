# Coordinating UI research with implementation

Use one UI owner and separate implementation work. For a request such as comparing
Materials Studio with AtomX, prepare a small inspection outcome: exact app/window,
the feature group to inspect, fixture identity, excluded groups (for example MS
Calc), and the fields needed to implement it. Preserve the user's existing scope.
Codex owns repository changes; the operator owns native observations and input.
Do not ask a GUI worker to edit source through a terminal or an editor UI.

## Browser research

Use `intent: "inspect"`, `verification: "observed"` and an `output_fields` map, for
example `{"feature_name":"string","controls":"array","units":"string"}`.
Criteria should request quoted visible labels/values plus page or dialog context.
Batch related questions on the same page into one brief rather than launching one
model session per field. Have the worker stop once these answers are present;
unrequested exhaustive exploration is expensive and makes reports harder to check.

Use independent comparison against trusted files/JSON when practical. Checking that
an input file hash is unchanged proves preservation, not extraction accuracy. A
fresh verifier can increase confidence in visual evidence but does not upgrade it
to independent machine-state verification.

## Native Desktop handoff

Use the already-open ZCode Desktop main conversation that the user authorized.
Its native Computer Use host already owns the desktop bridge; a standalone CLI
does not acquire that bridge by using `--surface desktop`. Never run desktop_retry.py
or create another CLI process to retry this route. Preparing a handoff only writes
new files; it does not execute UI, send a message or prove the task completed.

```powershell
python "<skill-dir>/scripts/delegate.py" --brief "<desktop-brief.json>" --runs "<workspace>/zcode-cu-runs" --prepare-handoff
```

The returned directory contains `brief.json` with a fresh run ID and
`handoff-prompt.txt`, excluding independent check definitions. Default desktop
invocation also prepares these files. It returns `handoff_prepared`,
`execution: not_started`, `timing_scope: handoff_preparation_only`; exit 3 means
pending, not success. Never read an earlier run's report as this task's result.

Deliver once through a supported existing-session host integration. If the user
authorized the existing ZCode conversation and native Windows computer use is
available, use that native skill to select the actual ZCode window/conversation,
confirm it is idle and the input is empty, enter the prepared prompt, and send it
once. This is an explicit chat handoff, not a forged broker connection. Do not
automate a terminal, security settings, credentials or permission dialogs. Do not
operate Materials Studio with the Codex controller: its observations belong to
the ZCode worker. If the recipient is ambiguous, busy or inaccessible, stop with
the prepared handoff; do not create a new CLI or retry sending uncertain input.

After observing that the prompt was sent, record delivery (this command records
the receipt only; it cannot send chat input):

```powershell
python "<skill-dir>/scripts/delegate.py" --run-dir "<handoff-run-dir>" --mark-sent --target-session "<exact existing recipient label>"
```

Metadata becomes `awaiting_report`. A second mark-sent is rejected. Wait for this
session's reply; never use the previous visible answer as evidence. If the reply
errors, stop and report that session's error instead of launching another worker.
For a one-shot read-only test, request current title/menu observations only, no
focus/clicks/screenshots/document changes in the target app, and stop afterward.

For ZCode chat delivery, observe the exact conversation title and an empty input,
then verify the entire new task ID is present in the input before sending. Electron
editors may accept set_value without retaining it: if the observed value stays
empty, focus the known editor and use native type_text, then verify its value and
enabled Send control. After clicking Send, allow the asynchronous UI to settle
and reobserve; immediate unchanged text does not authorize another Send. Record
delivery only after the prompt is a conversation message and the empty input /
generation indicator establishes it was submitted. Do not click mode, model,
permission, account or security controls to make the transport work.

When a report from the actual main session is available, import it:

```powershell
python "<skill-dir>/scripts/delegate.py" --run-dir "<handoff-run-dir>" --accept-report "<returned-report.json>"
```

Import requires a recorded delivery, validates identity, criteria, requested types,
allowed URLs/files and action budget, then applies the original acceptance policy.
An already imported report cannot be replaced/replayed. External report provenance
and token usage are not attested. A copied success claim alone cannot certify a
mutation. Do not run another controller while a supported operator owns the GUI;
if ownership or the effect of a last action is unknown, observe before proceeding.

Native child execution, if separately requested in future, must be created by the
actual Desktop host and inherit its live `ZCODE_CUA_NODE_REPL_HOST`,
`ZCODE_CUA_PERMISSION_BROKER_SOCKET` and `ZCODE_CUA_PRODUCT_HELPER` environment.
Names or guessed values in Codex's environment do not establish a host connection.
Do not extract private process memory, forge endpoints, expose variable values in
briefs/logs, or claim that environment presence alone proves permission. This skill
uses existing-session handoff and does not implement an independent desktop child.

## Implementation handoff

Return confirmed labels and interactions, uncertainties, and the remaining
inspection needed. Tie them to the inspected fixture and feature group. Continue
independent code work during a yielded browser call; pause only work depending on
its result. After code changes, test the actual app against the observations.
Keep screenshots at the operator unless a concrete visual ambiguity needs review.
