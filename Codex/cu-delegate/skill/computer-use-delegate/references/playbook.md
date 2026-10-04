# Failure handling

| Code | Evidence | Next step |
| --- | --- | --- |
| R2 | API/CLI could satisfy the actual goal | Take the script route; keep explicit UI testing on UI |
| B1 | Missing inputs / check IDs | Add only missing facts; do not restate the protocol |
| B2 | Action/time budget exhausted | Split at one independently observable end state |
| W1 | Wrong element / ambiguous matches | Ground in a fresh tree, narrow by visible context |
| W3 | Three actions without progress | Stop; one changed strategy after fresh observation |
| W4/V1 | Claim rejected by independent check | Preserve the false claim, do not accept success |
| E1 | Repeated brief / third retry | Stop: total three attempts maximum |
| S1 | Human gate / honeypot | No automatic retry; prepare a concrete reviewable handoff |
| X1 | Config path missing | Run doctor; use shipped config paths, not guessed CLI flags |
| X1 | No selected model / entitlement | Check private runtime setup; never switch to paid API silently |
| X1 | Native Desktop broker absent | Report desktop unavailable from this headless session; use supported ZCode Desktop runtime |
| X1 | Busy / refused / locked | Stop; do not steal a live controller or bypass a refusal |

Only on failure, read at most the final 40 diagnostic log lines, redacting secrets.
Partial output does not authorize completing external side effects. A timeout leaves
input outcome unknown: inspect state before retrying. Wrapper time limit and process
cleanup are hard bounds; the model's action limit is cooperative, not a security sandbox.
