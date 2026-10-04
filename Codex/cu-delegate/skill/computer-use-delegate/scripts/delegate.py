"""Bounded one-shot ZCode worker. Stdlib only; compact output, private traces."""
import argparse
import hashlib
import json
import os
import subprocess
import time
import uuid
import sys
from pathlib import Path
from runtime import discover, chrome_path, private_runtime, make_personal, dump, load, parse_object, parse_report, prepare_launcher
from verify import verify

SKILL = Path(__file__).resolve().parent.parent
STATUSES = {'success', 'partial', 'blocked', 'infeasible', 'failed'}


def validate_brief(b):
    for key in ['goal', 'route', 'start_state', 'success_criteria', 'constraints', 'authorization', 'stop_and_report_if', 'budget']:
        if key not in b: raise ValueError('Missing brief field: ' + key)
    if b['route'] not in {'browser', 'desktop'}: raise ValueError('Route must require UI')
    ids = [c['id'] for c in b['success_criteria']]
    if not ids or len(ids) != len(set(ids)): raise ValueError('Nonempty unique criteria required')
    if not b['constraints'].get('allowed_domains') and not b['constraints'].get('allowed_apps'):
        raise ValueError('Explicit allowed targets required')
    budget = b['budget']
    if not 1 <= budget['max_actions'] <= 100 or not 0 < budget['max_minutes'] <= 30:
        raise ValueError('Invalid budget')
    if b['route'] == 'browser':
        from urllib.parse import urlparse
        url = b['start_state'].get('url', '')
        if urlparse(url).hostname not in b['constraints']['allowed_domains']:
            raise ValueError('Start URL outside allowed domains')
        if b['start_state'].get('browser') != 'headless':
            raise ValueError('Standalone worker supports a fresh headless browser only; no silent session substitution')
    if len(json.dumps(b, ensure_ascii=False)) > 16000: raise ValueError('Brief oversized')
    if any(c['id'] not in ids for c in b.get('checks', [])): raise ValueError('Unknown checker criterion')


def validate_report(r, b):
    if r.get('run_id') != b['run_id'] or r.get('route') != b['route']:
        raise ValueError('Wrong run/route in worker report')
    if r.get('status') not in STATUSES: raise ValueError('Unknown status')
    if not isinstance(r.get('summary'), str) or len(r['summary']) > 2000: raise ValueError('Invalid summary')
    expected = {c['id'] for c in b['success_criteria']}
    rows = r.get('criteria', [])
    if {c.get('id') for c in rows} != expected or len(rows) != len(expected): raise ValueError('Criteria mismatch')
    for row in rows:
        if type(row.get('met')) is not bool or not isinstance(row.get('evidence'), str): raise ValueError('Invalid criterion evidence')
        if row['met'] and not row['evidence'].strip(): raise ValueError('Claim without evidence')
        if len(row['evidence']) > 4096: raise ValueError('Oversized evidence')
    if type(r.get('actions_used')) is not int or not 0 <= r['actions_used'] <= b['budget']['max_actions']:
        raise ValueError('Invalid action count')
    if r['status'] == 'success' and not all(c['met'] for c in rows): raise ValueError('Success with unmet criteria')
    if r['status'] == 'blocked' and not isinstance(r.get('blocker'), dict): raise ValueError('Missing blocker')
    out = r.get('outputs')
    if not isinstance(out, dict) or not isinstance(out.get('files'), list) or not isinstance(out.get('values'), dict):
        raise ValueError('Invalid outputs')
    roots = [Path(x).resolve() for x in b['constraints'].get('allowed_output_roots', [])]
    for file in out['files'] + ([r['final_screenshot']] if r.get('final_screenshot') else []):
        path = Path(file)
        if not path.is_absolute() or not any(path.resolve().is_relative_to(root) for root in roots):
            raise ValueError('Output file outside allowed roots')
    return r


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
        if b['route'] == 'desktop':
            # Desktop surface needs runtime-preference + permission-broker handshake.
            # A plain --prompt process cannot impersonate its Desktop host.
            raise RuntimeError('Native desktop control needs a supported ZCode Desktop host/broker; standalone CLI readiness is unverified')
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
        worker_brief = {k: v for k, v in b.items() if k != 'checks'}
        prompt = ('Read and follow gui-operator skill at ' + str(operator) +
                  '. Execute this brief as the main agent. Return exactly one JSON report. '
                  'Independent checker definitions are withheld. No shell, hidden state, subagents, permission questions or workflow tools.\n' +
                  json.dumps(worker_brief, ensure_ascii=False))
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
            'verified_success': verification['verified_success'], 'usage': usage, 'elapsed_seconds': meta['elapsed_seconds']}


def main():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser()
    p.add_argument('--brief'); p.add_argument('--runs', default='zcode-cu-runs')
    p.add_argument('--model'); p.add_argument('--doctor', action='store_true')
    a = p.parse_args()
    if a.doctor:
        info = discover()
        version = subprocess.run([info['node'], info['entrypoint'], '--version'], capture_output=True, text=True, timeout=15)
        print(json.dumps({**info, 'version': version.stdout.strip(), 'browser_executable': chrome_path(),
                          'desktop_headless_ready': False}, ensure_ascii=False, indent=2)); return 0
    if not a.brief: p.error('--brief is required')
    result = run(load(a.brief), a.runs, a.model)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['verified_success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
