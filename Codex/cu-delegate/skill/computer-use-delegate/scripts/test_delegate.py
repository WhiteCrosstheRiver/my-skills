"""Protocol regressions; synthetic data only, no GUI or model calls."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from delegate import validate_brief, validate_report, prepare_handoff, mark_handoff_sent, accept_handoff, run, doctor
from verify import verify


def brief():
    return {'goal': 'Read fixture labels', 'route': 'browser', 'intent': 'inspect',
            'verification': 'observed', 'start_state': {'url': 'http://127.0.0.1/', 'browser': 'headless'},
            'success_criteria': [{'id': 'name', 'description': 'Exact visible name'},
                                 {'id': 'count', 'description': 'Exact visible count'}],
            'constraints': {'allowed_domains': ['127.0.0.1'], 'allowed_apps': [], 'allowed_output_roots': []},
            'authorization': 'Read synthetic fixture only', 'stop_and_report_if': ['login', 'permission refusal'],
            'budget': {'max_actions': 5, 'max_minutes': 1}, 'output_fields': {'name': 'string', 'count': 'number'}}


def report(b):
    return {'run_id': b['run_id'], 'route': b['route'], 'status': 'success', 'summary': 'Fixture inspected',
            'criteria': [{'id': 'name', 'met': True, 'evidence': 'Name: Test fixture'},
                         {'id': 'count', 'met': True, 'evidence': 'Count: 64'}],
            'outputs': {'files': [], 'values': {'name': 'Test fixture', 'count': 64},
                        'final_url': b['start_state'].get('url')},
            'blocker': None, 'actions_used': 1, 'final_screenshot': None, 'next_attempt_hint': ''}


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.b = brief(); self.b['run_id'] = 'synthetic-test'
        self.r = report(self.b)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / 'state.json'
        self.state.write_text(json.dumps({'name': 'Test fixture', 'count': 64}), encoding='utf-8')

    def check(self, criterion, key, expected):
        return {'id': criterion, 'kind': 'json_file', 'file': str(self.state), 'path': key, 'equals': expected}

    def test_observed_inspection_is_accepted_but_not_verified(self):
        validate_brief(self.b); validate_report(self.r, self.b)
        v = verify(self.b, self.r)
        self.assertTrue(v['accepted']); self.assertFalse(v['verified_success'])
        self.assertEqual(v['outcome'], 'worker_observed')

    def test_mutation_cannot_opt_into_observation_only(self):
        self.b['intent'] = 'mutate'
        with self.assertRaises(ValueError): validate_brief(self.b)
        with self.assertRaises(ValueError): verify(self.b, self.r)

    def test_mutation_without_checks_remains_unaccepted(self):
        self.b.update(intent='mutate', verification='independent')
        v = verify(self.b, self.r)
        self.assertFalse(v['accepted']); self.assertFalse(v['false_success_claim'])
        self.assertEqual(v['outcome'], 'verification_incomplete')

    def test_partial_coverage_is_not_a_disproved_claim(self):
        self.b.update(intent='mutate', verification='independent')
        self.b['checks'] = [self.check('name', 'name', 'Test fixture')]
        v = verify(self.b, self.r)
        self.assertFalse(v['accepted']); self.assertFalse(v['false_success_claim'])
        self.assertEqual(v['unchecked_criteria'], ['count'])

    def test_failed_check_overrides_observed_acceptance(self):
        self.b['checks'] = [self.check('count', 'count', 99)]
        v = verify(self.b, self.r)
        self.assertFalse(v['accepted']); self.assertTrue(v['false_success_claim'])
        self.assertEqual(v['outcome'], 'failed_checks')

    def test_checker_error_is_not_contradictory_evidence(self):
        self.b['checks'] = [self.check('count', 'count', 64)]
        self.b['checks'][0]['file'] = str(Path(self.temp.name) / 'missing.json')
        v = verify(self.b, self.r)
        self.assertFalse(v['accepted']); self.assertFalse(v['false_success_claim'])
        self.assertEqual(v['outcome'], 'verification_error')

    def test_standalone_verifier_uses_same_identity_contract(self):
        self.r['run_id'] = 'wrong'
        with self.assertRaises(ValueError): verify(self.b, self.r)

    def test_standalone_verifier_prints_unicode_in_legacy_environment(self):
        self.r['outputs']['values']['name'] = 'Test Å'
        folder = Path(self.temp.name)
        (folder / 'brief.json').write_text(json.dumps(self.b), encoding='utf-8')
        (folder / 'report.json').write_text(json.dumps(self.r), encoding='utf-8')
        completed = subprocess.run([sys.executable, str(Path(__file__).with_name('verify.py')),
                                    '--brief', str(folder / 'brief.json'), '--report', str(folder / 'report.json')],
                                   capture_output=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'ascii'})
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)['accepted'])

    def test_complete_checks_verify_mutation_and_preserve_types(self):
        self.b.update(intent='mutate', verification='independent')
        self.b['checks'] = [self.check('name', 'name', 'Test fixture'), self.check('count', 'count', 64)]
        v = verify(self.b, self.r)
        self.assertTrue(v['verified_success']); self.assertEqual(v['outcome'], 'independently_verified')
        self.b['checks'][-1]['equals'] = True
        self.assertFalse(verify(self.b, self.r)['accepted'])

    def test_wrong_identity_or_missing_evidence_rejected(self):
        for mutate in [lambda r: r.update(run_id='other'), lambda r: r['criteria'][0].update(evidence='')]:
            r = copy.deepcopy(self.r); mutate(r)
            with self.assertRaises(ValueError): validate_report(r, self.b)

    def test_exact_output_keys_and_types_enforced(self):
        for values in [{'name': 'Test fixture'}, {'name': 'Test fixture', 'count': True},
                       {'name': 'Test fixture', 'count': float('nan')},
                       {'name': 'Test fixture', 'count': 64, 'unexpected': 'x'}]:
            r = copy.deepcopy(self.r); r['outputs']['values'] = values
            with self.assertRaises(ValueError): validate_report(r, self.b)

    def test_blocked_unknown_values_preserve_native_error(self):
        self.r.update(status='blocked', blocker={'type': 'env', 'detail': 'Native bridge unavailable'})
        for row in self.r['criteria']: row.update(met=False, evidence='Not observable')
        self.r['outputs']['values'] = {'name': None, 'count': None}
        validate_report(self.r, self.b)
        v = verify(self.b, self.r)
        self.assertFalse(v['accepted']); self.assertEqual(v['outcome'], 'blocked')
        self.r['outputs']['values']['count'] = 'wrong type'
        with self.assertRaises(ValueError): validate_report(self.r, self.b)

    def test_external_url_and_file_rejected(self):
        r = copy.deepcopy(self.r); r['outputs']['final_url'] = 'https://outside.example/'
        with self.assertRaises(ValueError): validate_report(r, self.b)
        r = copy.deepcopy(self.r); r['outputs']['files'] = [str(self.state)]
        with self.assertRaises(ValueError): validate_report(r, self.b)

    def test_handoff_is_unexecuted_and_checks_stay_private(self):
        self.b['route'] = 'desktop'; self.b['start_state'] = {'app': 'Synthetic app'}
        self.b['constraints']['allowed_apps'] = ['Synthetic app']
        self.b['checks'] = [self.check('name', 'name', 'Test fixture')]
        with patch('delegate.discover', side_effect=AssertionError('No runtime/model access allowed')):
            result = prepare_handoff(self.b, self.temp.name)
        self.assertEqual(result['execution'], 'not_started'); self.assertFalse(result['accepted'])
        folder = Path(result['run_dir'])
        self.assertNotIn('json_file', (folder / 'handoff-prompt.txt').read_text(encoding='utf-8'))
        b = json.loads((folder / 'brief.json').read_text(encoding='utf-8'))
        r = report(b); source = folder / 'returned.json'
        source.write_text(json.dumps(r), encoding='utf-8')
        with self.assertRaises(ValueError): accept_handoff(folder, source)
        mark_handoff_sent(folder, 'Existing synthetic Desktop conversation')
        adopted = accept_handoff(folder, source)
        self.assertEqual(adopted['outcome'], 'worker_observed')
        r['run_id'] = 'wrong'; source.write_text(json.dumps(r), encoding='utf-8')
        with self.assertRaises(ValueError): accept_handoff(folder, source)

    def test_desktop_default_prepares_handoff_without_runtime_or_process(self):
        self.b['route'] = 'desktop'; self.b['start_state'] = {'app': 'Synthetic app'}
        self.b['constraints']['allowed_apps'] = ['Synthetic app']
        with patch('delegate.discover', side_effect=AssertionError('No model setup allowed')), \
             patch('delegate.subprocess.Popen', side_effect=AssertionError('No CLI process allowed')):
            result = run(self.b, self.temp.name)
        self.assertEqual(result['status'], 'handoff_prepared'); self.assertFalse(result['accepted'])
        self.assertEqual(result['execution'], 'not_started')
        self.assertEqual(result['timing_scope'], 'handoff_preparation_only')

    def test_fresh_handoffs_reject_old_reports_and_duplicate_delivery(self):
        self.b['route'] = 'desktop'; self.b['start_state'] = {'app': 'Synthetic app'}
        self.b['constraints']['allowed_apps'] = ['Synthetic app']
        first = prepare_handoff(self.b, self.temp.name)
        second = prepare_handoff(self.b, self.temp.name)
        self.assertNotEqual(first['run_dir'], second['run_dir'])
        old_brief = json.loads((Path(first['run_dir']) / 'brief.json').read_text(encoding='utf-8'))
        old_report = Path(self.temp.name) / 'old.json'
        old_report.write_text(json.dumps(report(old_brief)), encoding='utf-8')
        mark_handoff_sent(second['run_dir'], 'Existing Desktop main session')
        with self.assertRaises(ValueError): mark_handoff_sent(second['run_dir'], 'Same recipient')
        with self.assertRaises(ValueError): accept_handoff(second['run_dir'], old_report)
        self.assertEqual(json.loads((Path(second['run_dir']) / 'metadata.json').read_text(encoding='utf-8'))['execution'], 'awaiting_report')

    def test_doctor_never_launches_cli(self):
        with patch('delegate.subprocess.run', side_effect=AssertionError('No CLI process allowed')), \
             patch('delegate.subprocess.Popen', side_effect=AssertionError('No CLI process allowed')):
            result = doctor()
        self.assertIsNone(result['version'])
        self.assertEqual(result['routes']['desktop']['transport'], 'existing_zcode_desktop_session')


if __name__ == '__main__':
    unittest.main()
