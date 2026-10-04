"""Shared brief/report contract for execution, import and standalone verification."""
import json
import math
from pathlib import Path

STATUSES = {'success', 'partial', 'blocked', 'infeasible', 'failed'}


def validate_brief(b):
    for key in ['goal', 'route', 'start_state', 'success_criteria', 'constraints', 'authorization', 'stop_and_report_if', 'budget']:
        if key not in b: raise ValueError('Missing brief field: ' + key)
    if b['route'] not in {'browser', 'desktop'}: raise ValueError('Route must require UI')
    if b.get('intent', 'mutate') not in {'inspect', 'mutate'}: raise ValueError('Invalid intent')
    if b.get('verification', 'independent') not in {'observed', 'independent'}: raise ValueError('Invalid verification policy')
    if b.get('verification') == 'observed' and b.get('intent') != 'inspect':
        raise ValueError('Observed acceptance is available only for explicitly read-only inspection')
    ids = [c['id'] for c in b['success_criteria']]
    if not ids or any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('Nonempty unique criteria required')
    if not b['constraints'].get('allowed_domains') and not b['constraints'].get('allowed_apps'):
        raise ValueError('Explicit allowed targets required')
    budget = b['budget']
    if type(budget['max_actions']) is not int or type(budget['max_minutes']) not in {int, float} or not 1 <= budget['max_actions'] <= 100 or not 0 < budget['max_minutes'] <= 30:
        raise ValueError('Invalid budget')
    if b['route'] == 'browser':
        from urllib.parse import urlparse
        url = b['start_state'].get('url', '')
        parsed = urlparse(url)
        if parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password or parsed.hostname not in b['constraints'].get('allowed_domains', []):
            raise ValueError('Start URL outside allowed domains')
        if b['start_state'].get('browser') != 'headless':
            raise ValueError('Standalone worker supports a fresh headless browser only; no silent session substitution')
    elif not b['constraints'].get('allowed_apps'):
        raise ValueError('Desktop handoff requires explicit allowed apps')
    if len(json.dumps(b, ensure_ascii=False)) > 16000: raise ValueError('Brief oversized')
    if any(c['id'] not in ids for c in b.get('checks', [])): raise ValueError('Unknown checker criterion')
    fields = b.get('output_fields', {})
    if not isinstance(fields, dict) or any(not isinstance(k, str) or not k or not isinstance(v, str) or v not in {'string', 'number', 'boolean', 'object', 'array'} for k, v in fields.items()):
        raise ValueError('output_fields must map exact keys to JSON types')


def validate_report(r, b):
    for key in ['run_id', 'status', 'summary', 'route', 'criteria', 'outputs', 'blocker', 'actions_used', 'final_screenshot', 'next_attempt_hint']:
        if key not in r: raise ValueError('Missing report field: ' + key)
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
    if not isinstance(out, dict) or 'final_url' not in out or not isinstance(out.get('files'), list) or not isinstance(out.get('values'), dict):
        raise ValueError('Invalid outputs')
    fields = b.get('output_fields', {})
    types = {'string': lambda v: isinstance(v, str), 'number': lambda v: type(v) in {int, float} and (type(v) is int or math.isfinite(v)),
             'boolean': lambda v: type(v) is bool, 'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list)}
    if fields:
        if set(out['values']) - set(fields): raise ValueError('Unexpected output key')
        if r['status'] == 'success' and set(out['values']) != set(fields): raise ValueError('Missing requested output key')
        if any(not (v is None and r['status'] != 'success') and not types[fields[k]](v) for k, v in out['values'].items()):
            raise ValueError('Wrong output value type')
    from urllib.parse import urlparse
    final_url = out.get('final_url')
    if final_url is not None:
        if not isinstance(final_url, str): raise ValueError('Invalid final URL')
        parsed = urlparse(final_url)
        if parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password or parsed.hostname not in b['constraints'].get('allowed_domains', []):
            raise ValueError('Final URL outside allowed domains')
    if not isinstance(r['next_attempt_hint'], str) or len(r['next_attempt_hint']) > 2000:
        raise ValueError('Invalid next attempt hint')
    if len(json.dumps(r, ensure_ascii=False, allow_nan=False).encode('utf-8')) > 65536:
        raise ValueError('Report exceeded 64 KiB; narrow the requested evidence')
    roots = [Path(x).resolve() for x in b['constraints'].get('allowed_output_roots', [])]
    for file in out['files'] + ([r['final_screenshot']] if r.get('final_screenshot') else []):
        path = Path(file)
        if not path.is_absolute() or not any(path.resolve().is_relative_to(root) for root in roots):
            raise ValueError('Output file outside allowed roots')
    return r
