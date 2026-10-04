# Verified local runtime, 2026-10-04

- Windows, Node v25.4.0, ZCode CLI 0.16.9; entry point is
  `C:/Program Files/ZCode/resources/glm/zcode.cjs`, not a command on PATH.
- Public shipped provider file is `resources/config/provider/zcode-builtin.json`.
  The direct bundle invocation's relative lookup fails. The helper sets native
  `ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` and `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE`.
- Existing account family is BigModel Individual Coding Plan. No new API key,
  provider or external API billing is created. CLI account identity and default
  selection are absent from Desktop's provider_config; the private runtime copies
  ciphertext and derives only the non-secret identity marker from its key name.
- Private account runtime is `~/.codex/zcode-cu-runtime/`, ACL restricted to the
  current Windows user. It is outside the repo and run artifacts. Never print,
  attach, commit or give this directory to the worker. The worker must not read it.
- Both native roots are set: ZCODE_DATA_BASE_DIR for account files and
  ZCODE_STORAGE_DIR for CLI sessions/config/plugins. Setting only the former still
  writes CLI history in the normal user's store. Isolated storage also avoids
  loading unrelated installed plugins and user session memory into training.
- The private unchanged CLI retains its shipped package discovery through a
  filesystem junction to the installed `glm/packages` directory. Do not treat
  native plugins as arbitrary inline plugins: their shared node_repl host is
  enabled through official package discovery. Unneeded native plugins are
  suppressed only in the private runtime config.
- Per-run selection is recorded in a native provider config file. No `--model` flag is
  supported in this installed version. A real probe requesting Flash still used
  GLM-5.3 in native traces. Alternate selection is now rejected before billing,
  rather than silently counting GLM-5.3 as Flash. The app-server per-send selection
  probe failed because its standalone provider registry has no account-loaded model.
  Only an account-provisioned supported app-server can enable that route.
  GLM-5.3 and GLM-5.3-Flash are shipped Coding
  Plan models; GLM-5V-Turbo is not in this account's shipped Coding Plan list, so
  the helper rejects it rather than switching to API billing.
- ZCode's native plugins: Browser Use 0.5.1, Computer Use 0.6.3, node-repl-host 0.6.0.
  The native runtime's JS workers are fresh per call; Codex's persistent JS/sky
  instructions must not be copied into ZCode.
- Headless `build` mode fails before browser tool execution with "No permission
  client configured". Use the CLI's documented headless default `yolo` mode for
  the already authorized brief; disable AskUserQuestion and stop on human gates.
  This is a tool-permission mode, not an OS sandbox or a native CUA permission
  grant. Native broker refusals remain stopping conditions.
- The shipped CLI dynamically imports playwright-core, but its bundle directory
  has no such dependency. Browser plugin package.json pins 1.59.1. setup_runtime.py
  installs exactly that package, with install scripts disabled, next to a private
  unchanged copy of zcode.cjs. The installed ZCode application is not modified.
  It does not install a browser: existing Chrome is passed explicitly.
- A standalone `--surface desktop --prompt` native-CUA probe timed out awaiting
  host cooperation. No supported Desktop broker was supplied. Desktop delegation
  originally failed closed **before a model call**. The corrected wrapper now
  prepares an existing-session handoff without any independent desktop process.
  `gui-operator` is installed in ZCode and can execute a brief as the actual
  ZCode Desktop main agent when that supported runtime is present. Do not forge
  permission tokens, use development mode or automate approval UI to bypass it.
- A later user-supplied screenshot confirms that the actual ZCode Desktop main
  session can read Materials Studio after restart. A fresh isolated native CLI
  `--surface desktop` retry completed in about 61 seconds but returned
  `Computer Use is unavailable for this node_repl session`, with zero input
  actions. Desktop-client readiness does not automatically attach its broker to
  this standalone worker. The remaining issue is session transport, not a request
  for the user to repeat Desktop authorization.
- Docker is installed but its Linux daemon was not running. Browser tests use
  localhost Python fixtures and fresh headless Chrome. This is test-data isolation,
  not an OS/network sandbox. Native desktop evaluation remains pending a resettable
  VM/container and a supported worker-host connection.

Desktop transport correction, 2026-10-04: use the already authorized ZCode Desktop
main session. Its native host can read Materials Studio; the independent CLI
lacks the live CUA host/broker/helper environment. Do not infer Desktop settings
from `unavailable for this node_repl session` in that independent process.
The old desktop_retry.py creates a new UUID directory each invocation and reads
that directory's stdout, not a cached report. Three recorded runs took 61.319,
90.154 and 61.475 seconds. A near-zero process-output fetch can simply retrieve
a completed invocation; it is not evidence of near-zero worker execution.
Never run this probe again as the Desktop handoff path.

The installed skill lives in `~/.codex/skills/computer-use-delegate`; a source
checkout/installer is not required for direct updates and must not be assumed to
exist. Run `scripts/delegate.py --doctor` to refresh paths/version and prerequisites
without loading credentials, invoking a model or launching a CLI process. Desktop
handoffs are prepared, delivered once to the existing session, marked awaiting a
report, and imported only with the new task ID. GUI delivery requires an authorized
recipient and the native Windows skill; the helper itself sends no GUI input;
see [coordination.md](coordination.md). Open a new Codex chat if the skill catalog's
description has not refreshed. Existing plugins and global model settings stay
unchanged.

Upstream context: [ZCode CLI issue 907](https://github.com/zai-org/feedback/issues/907)
describes the headless model-selection gap. Prefer measured local behavior over
unverified capabilities in the supplied plan.
