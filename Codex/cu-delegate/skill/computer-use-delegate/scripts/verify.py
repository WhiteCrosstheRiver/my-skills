"""Independent checks. This process never accepts checker definitions from a worker."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from runtime import dump, load


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
    claimed = report.get('status') == 'success' and all(claims.get(c['id'], {}).get('met') is True for c in criteria)
    return {'verified_success': claimed and machine_pass,
            'verification_level': 'independent' if all_checked and results else 'incomplete',
            'false_success_claim': claimed and bool(results) and not machine_pass,
            'checks': results}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--brief', required=True); p.add_argument('--report', required=True)
    p.add_argument('--output')
    a = p.parse_args()
    result = verify(load(a.brief), load(a.report))
    if a.output: dump(a.output, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['verified_success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
