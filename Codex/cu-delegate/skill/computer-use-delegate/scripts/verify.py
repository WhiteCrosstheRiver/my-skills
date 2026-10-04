"""Independent checks. This process never accepts checker definitions from a worker."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from runtime import dump, load
from protocol import validate_brief, validate_report


def dig(value, path):
    for key in path.split('.') if path else []:
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def json_equal(actual, expected):
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(json_equal(actual[k], expected[k]) for k in actual)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(json_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def verify(brief, report):
    validate_brief(brief)
    validate_report(report, brief)
    criteria = brief['success_criteria']
    claims = {c['id']: c for c in report.get('criteria', [])}
    results = []
    for check in brief.get('checks', []):
        try:
            kind = check['kind']
            if kind == 'json_url':
                url = check['url']
                parsed = urlparse(url)
                if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
                    raise ValueError('Invalid checker URL')
                with urlopen(Request(url, headers={'Accept': 'application/json'}), timeout=10) as res:
                    data = json.loads(res.read(1024 * 1024))
                actual = dig(data, check.get('path', ''))
                expected = dig(report, check['matches_report_path']) if 'matches_report_path' in check else check['equals']
                passed = json_equal(actual, expected)
            elif kind == 'json_file':
                actual = dig(load(check['file']), check.get('path', ''))
                expected = dig(report, check['matches_report_path']) if 'matches_report_path' in check else check['equals']
                passed = json_equal(actual, expected)
            elif kind == 'file_contains':
                actual = check['contains'] in Path(check['file']).read_text(encoding=check.get('encoding', 'utf-8'))
                passed = actual is True
            elif kind == 'file_sha256':
                actual = hashlib.sha256(Path(check['file']).read_bytes()).hexdigest()
                passed = actual == check['equals']
            else:
                raise ValueError('Unsupported checker kind')
            results.append({'id': check['id'], 'passed': passed, 'actual': actual})
        except Exception as exc:
            results.append({'id': check['id'], 'passed': False, 'error': type(exc).__name__})
    covered = {r['id'] for r in results}
    all_checked = all(c['id'] in covered for c in criteria)
    machine_pass = bool(results) and all_checked and all(r['passed'] for r in results)
    claimed = report.get('status') == 'success' and bool(criteria) and all(
        claims.get(c['id'], {}).get('met') is True and
        isinstance(claims[c['id']].get('evidence'), str) and claims[c['id']]['evidence'].strip()
        for c in criteria)
    failed_checks = any(not r['passed'] and 'error' not in r for r in results)
    check_errors = any('error' in r for r in results)
    observed_allowed = brief.get('intent') == 'inspect' and brief.get('verification') == 'observed'
    verified = bool(claimed and machine_pass)
    observed = bool(claimed and observed_allowed and not failed_checks and not check_errors)
    if verified: outcome = 'independently_verified'
    elif claimed and failed_checks: outcome = 'failed_checks'
    elif claimed and check_errors: outcome = 'verification_error'
    elif observed: outcome = 'worker_observed'
    elif claimed: outcome = 'verification_incomplete'
    else: outcome = report.get('status', 'failed')
    return {'verified_success': verified, 'accepted': verified or observed, 'outcome': outcome,
            'verification_level': 'independent' if verified else 'worker_observed' if observed else 'incomplete',
            'false_success_claim': bool(claimed and failed_checks),
            'unchecked_criteria': [c['id'] for c in criteria if c['id'] not in covered],
            'check_errors': [r['id'] for r in results if 'error' in r],
            'checks': results}


def main():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser()
    p.add_argument('--brief', required=True); p.add_argument('--report', required=True)
    p.add_argument('--output')
    a = p.parse_args()
    result = verify(load(a.brief), load(a.report))
    if a.output: dump(a.output, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['accepted'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
