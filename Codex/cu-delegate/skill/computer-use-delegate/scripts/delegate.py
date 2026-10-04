"""Bounded one-shot ZCode worker. Stdlib only; compact output, private traces."""
import argparse
import hashlib
import json
import os
import subprocess
import time
import uuid
import sys
from datetime import datetime, timezone
from pathlib import Path
from runtime import discover, chrome_path, private_runtime, make_personal, dump, load, parse_object, parse_report, prepare_launcher
from verify import verify

SKILL = Path(__file__).resolve().parent.parent
from protocol import validate_brief, validate_report


def worker_prompt(b):
    operator = Path.home() / '.zcode/skills/gui-operator/SKILL.md'
    worker_brief = {k: v for k, v in b.items() if k != 'checks'}
    inspection = ('This is read-only inspection: navigation and opening/closing inspection dialogs are allowed; '
                  'do not change/save document data or submit mutating forms. ') if b.get('intent') == 'inspect' else ''
    desktop = ('Use this existing ZCode Desktop main session and its attached native Computer Use host. '
               'Do not start a CLI, subagent or workflow. Make fresh observations for this run_id; '
               'do not copy an earlier conversation answer. Stop after this brief. ') if b['route'] == 'desktop' else ''
    return ('Read and follow gui-operator skill at ' + str(operator) +
            '. Execute this brief as the main agent. Return exactly one JSON report. ' + inspection + desktop +
            'Independent checker definitions are withheld. No shell, hidden state, subagents, permission questions or workflow tools.\n' +
            json.dumps(worker_brief, ensure_ascii=False))


def prepare_handoff(brief, runs):
    """Prepare a main-session brief; no GUI action, credential access or model call."""
    validate_brief(brief)
    if brief['route'] != 'desktop': raise ValueError('Handoff is for a supported native Desktop main session')
    started = time.monotonic()
    b = {**brief, 'run_id': uuid.uuid4().hex}
    run_dir = Path(runs).resolve() / b['run_id']
    run_dir.mkdir(parents=True, exist_ok=False)
    dump(run_dir / 'brief.json', b)
    (run_dir / 'handoff-prompt.txt').write_text(worker_prompt(b), encoding='utf-8')
    dump(run_dir / 'metadata.json', {'run_id': b['run_id'], 'execution': 'not_started',
                                    'transport': 'existing_zcode_desktop_session',
                                    'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
                                    'timing_scope': 'handoff_preparation_only',
                                    'model_calls': 0, 'handoff': True, 'usage': None})
    return {'run_dir': str(run_dir), 'status': 'handoff_prepared', 'accepted': False,
            'verified_success': False, 'execution': 'not_started', 'outcome': 'handoff_prepared',
            'elapsed_seconds': round(time.monotonic() - started, 6),
            'timing_scope': 'handoff_preparation_only',
            'prompt_path': str(run_dir / 'handoff-prompt.txt'),
            'next_step': 'Deliver once to the existing authorized ZCode Desktop main session, record mark-sent, then import its matching report. Never launch a standalone desktop CLI.'}


def mark_handoff_sent(run_dir, target_session):
    """Record a completed authorized delivery; this function does not send input."""
    run_dir = Path(run_dir).resolve()
    meta = load(run_dir / 'metadata.json')
    if not meta.get('handoff') or meta.get('execution') != 'not_started':
        raise ValueError('Handoff was already sent/imported or is not prepared; do not send again')
    if not isinstance(target_session, str) or not target_session.strip() or len(target_session) > 500:
        raise ValueError('Exact existing recipient/session label required')
    dump(run_dir / 'metadata.json', {**meta, 'execution': 'awaiting_report',
                                    'sent_at_utc': datetime.now(timezone.utc).isoformat(),
                                    'target_session': target_session})
    return {'run_dir': str(run_dir), 'run_id': meta['run_id'], 'execution': 'awaiting_report',
            'accepted': False, 'verified_success': False}


def accept_handoff(run_dir, report_path):
    run_dir = Path(run_dir).resolve()
    meta = load(run_dir / 'metadata.json')
    if not meta.get('handoff'): raise ValueError('Run is not a prepared handoff')
    if meta.get('execution') != 'awaiting_report':
        raise ValueError('Require one recorded delivery before import; completed reports cannot be replayed')
    b = load(run_dir / 'brief.json'); validate_brief(b)
    if Path(report_path).stat().st_size > 65536: raise ValueError('Report exceeded 64 KiB')
    report = validate_report(load(report_path), b)
    verification = verify(b, report)
    dump(run_dir / 'report.json', report); dump(run_dir / 'verification.json', verification)
    # An imported report establishes no automatic proof of its producer or token usage.
    dump(run_dir / 'metadata.json', {**meta, 'execution': 'report_imported',
                                    'imported_at_utc': datetime.now(timezone.utc).isoformat(),
                                    'report_source': 'external_unattested'})
    return {'run_dir': str(run_dir), 'status': report['status'], 'summary': report['summary'],
            'accepted': verification['accepted'], 'verified_success': verification['verified_success'],
            'outcome': verification['outcome'], 'usage': None}


def doctor():
    info = discover()
    packages = Path(info['packages'])
    browser = chrome_path()
    operator = Path.home() / '.zcode/skills/gui-operator/SKILL.md'
    browser_plugin = (packages / 'browser-use-plugin/package.json').is_file()
    desktop_plugin = (packages / 'zcode-cua-plugin/package.json').is_file()
    root = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'zcode-cu-runtime'
    dependency = root / 'launcher/node_modules/playwright-core/package.json'
    pinned = load(packages / 'browser-use-plugin/package.json')['devDependencies']['playwright-core'] if browser_plugin else None
    dependency_ready = dependency.is_file() and load(dependency).get('version') == pinned
    return {**info, 'version': None, 'version_source': 'not_probed_no_cli_process', 'browser_executable': browser,
            'desktop_headless_ready': False,
            'routes': {
                'browser': {'prerequisites_present': bool(browser and browser_plugin and operator.is_file() and dependency_ready),
                            'plugin_present': browser_plugin, 'operator_present': operator.is_file(),
                            'pinned_dependency_present': dependency_ready, 'live_test_required': True},
                'desktop': {'plugin_present': desktop_plugin, 'transport': 'existing_zcode_desktop_session',
                            'reason': 'Desktop briefs use an existing authorized Desktop main session; standalone desktop CLI is disabled.',
                            'host_environment_presence': {key: bool(os.environ.get(key)) for key in
                                ['ZCODE_CUA_NODE_REPL_HOST', 'ZCODE_CUA_PERMISSION_BROKER_SOCKET', 'ZCODE_CUA_PRODUCT_HELPER']},
                            'environment_scope': 'current Python parent only; not a test of the Desktop session',
                            'handoff_supported': operator.is_file(), 'live_test_required': True}},
            'credential_check': 'not_performed', 'model_calls': 0}


def failed_report(b, detail, status='blocked'):
    return {'run_id': b['run_id'], 'route': b['route'], 'status': status, 'summary': detail,
            'criteria': [{'id': c['id'], 'met': False, 'evidence': ''} for c in b['success_criteria']],
            'outputs': {'files': [], 'values': {}, 'final_url': None}, 'blocker': {'type': 'env', 'detail': detail},
            'actions_used': 0, 'final_screenshot': None, 'next_attempt_hint': ''}


def kill_tree(proc):
    if proc.poll() is None:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True, timeout=15)
        else:
            import signal
            os.killpg(proc.pid, signal.SIGTERM)
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired: proc.kill()


def observed_models(run_dir):
    models = set()
    for log in (Path(run_dir) / 'worker-traces').glob('*.jsonl'):
        for line in log.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                event = json.loads(line)
                context = event.get('context', {})
                if event.get('event') == 'model.sdk.stream.completed' and context.get('modelId'):
                    models.add((context.get('providerId'), context['modelId']))
            except ValueError: pass
    return [{'providerId': p, 'modelId': m} for p, m in sorted(models)]


def run(brief, runs, model=None):
    validate_brief(brief)
    if brief['route'] == 'desktop':
        return prepare_handoff(brief, runs)
    b = dict(brief)
    b['run_id'] = uuid.uuid4().hex
    run_dir = Path(runs).resolve() / b['run_id']
    run_dir.mkdir(parents=True, exist_ok=False)
    dump(run_dir / 'brief.json', b)
    started = time.monotonic()
    skill_hash = hashlib.sha256((SKILL / 'SKILL.md').read_bytes()).hexdigest()
    operator_path = Path.home() / '.zcode/skills/gui-operator/SKILL.md'
    operator_hash = hashlib.sha256(operator_path.read_bytes()).hexdigest() if operator_path.is_file() else None
    usage = None; exit_code = None; envelope = {}; report = None; error = None
    lock = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'zcode-cu-worker.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    fd = None; proc = None
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, json.dumps({'pid': os.getpid(), 'run_id': b['run_id']}).encode())
        info = discover()
        env, provider_id, selected = private_runtime(info, model)
        launcher = prepare_launcher(info, env)
        personal = run_dir / 'provider-selection.json'
        make_personal(personal, provider_id, selected)
        env['ZCODE_PERSONAL_PROVIDER_CONFIG_FILE'] = str(personal)
        env['ZCODE_LOG_DIR'] = str(run_dir / 'worker-traces')
        browser_exe = chrome_path()
        if not browser_exe: raise RuntimeError('No installed Chrome/Edge available')
        # Load operator by absolute path; also installed for normal ZCode discovery.
        operator = Path.home() / '.zcode/skills/gui-operator/SKILL.md'
        if not operator.is_file(): raise RuntimeError('Install gui-operator before invoking the worker')
        prompt = worker_prompt(b)
        command = [info['node'], launcher, '--cwd', str(run_dir), '--browser-use', 'headless',
                   '--browser-executable', browser_exe, '--mode', 'yolo', '--disallowed-tools',
                   'Bash,Write,Edit,Agent,CreateWorkflow,AskUserQuestion,WebFetch,WebSearch',
                   '--prompt', prompt, '--json']
        with (run_dir / 'worker.stdout.json').open('wb') as stdout, (run_dir / 'worker.stderr.log').open('wb') as stderr:
            proc = subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                    start_new_session=os.name != 'nt')
            try: exit_code = proc.wait(timeout=b['budget']['max_minutes'] * 60)
            except subprocess.TimeoutExpired:
                kill_tree(proc)
                raise RuntimeError('Worker exceeded its wall-clock budget; input outcome may be unknown')
        stdout_path = run_dir / 'worker.stdout.json'
        if stdout_path.stat().st_size > 2 * 1024 * 1024:
            raise RuntimeError('Worker envelope exceeded the compact report limit')
        raw = stdout_path.read_text(encoding='utf-8-sig')
        try: envelope = parse_object(raw)
        except Exception:
            raise RuntimeError('Worker did not return a valid JSON envelope; inspect bounded local diagnostics')
        usage = envelope.get('usage')
        if exit_code != 0: raise RuntimeError('ZCode exited unsuccessfully; usage retained if supplied')
        report = validate_report(parse_report(envelope.get('response', '')), b)
    except FileExistsError:
        error = 'Another delegation owns the local worker lock; do not run GUI workers concurrently'
    except Exception as exc:
        error = str(exc)[:1000]
    finally:
        if proc is not None and proc.poll() is None: kill_tree(proc)
        if fd is not None:
            os.close(fd); lock.unlink(missing_ok=True)
    if report is None: report = failed_report(b, error or 'No report', 'failed' if proc else 'blocked')
    dump(run_dir / 'report.json', report)
    verification = verify(b, report)
    dump(run_dir / 'verification.json', verification)
    meta = {'run_id': b['run_id'], 'elapsed_seconds': round(time.monotonic() - started, 3),
            'exit_code': exit_code, 'usage': usage, 'usage_missing': usage is None,
            'model_selection': {'providerId': provider_id, 'modelId': selected} if 'selected' in locals() else None,
            'model_selection_source': 'per-run config; effective model checked in native traces',
            'observed_models': observed_models(run_dir),
            'session_id': envelope.get('sessionId'), 'trace_id': envelope.get('traceId'),
            'skill_sha256': skill_hash, 'operator_sha256': operator_hash,
            'action_budget_enforcement': 'cooperative', 'wall_clock_enforcement': 'process-tree timeout',
            'dollar_cost': None, 'quota_used': None, 'error': error}
    dump(run_dir / 'metadata.json', meta)
    return {'run_dir': str(run_dir), 'status': report['status'], 'summary': report['summary'],
            'verified_success': verification['verified_success'], 'accepted': verification['accepted'],
            'outcome': verification['outcome'], 'usage': usage, 'elapsed_seconds': meta['elapsed_seconds']}


def main():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser()
    p.add_argument('--brief'); p.add_argument('--runs', default='zcode-cu-runs')
    p.add_argument('--model'); p.add_argument('--doctor', action='store_true')
    p.add_argument('--prepare-handoff', action='store_true')
    p.add_argument('--mark-sent', action='store_true'); p.add_argument('--target-session')
    p.add_argument('--accept-report'); p.add_argument('--run-dir')
    a = p.parse_args()
    if a.doctor:
        print(json.dumps(doctor(), ensure_ascii=False, indent=2)); return 0
    if a.mark_sent:
        if not a.run_dir or not a.target_session or a.brief or a.accept_report or a.prepare_handoff:
            p.error('--mark-sent requires only --run-dir and --target-session')
        print(json.dumps(mark_handoff_sent(a.run_dir, a.target_session), ensure_ascii=False)); return 3
    if a.accept_report:
        if not a.run_dir or a.prepare_handoff or a.brief: p.error('--accept-report requires only --run-dir')
        result = accept_handoff(a.run_dir, a.accept_report)
        print(json.dumps(result, ensure_ascii=False)); return 0 if result['accepted'] else 2
    if not a.brief: p.error('--brief is required')
    if a.prepare_handoff:
        result = prepare_handoff(load(a.brief), a.runs)
        print(json.dumps(result, ensure_ascii=False)); return 3
    result = run(load(a.brief), a.runs, a.model)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['accepted'] else 3 if result.get('execution') == 'not_started' else 2


if __name__ == '__main__':
    raise SystemExit(main())
