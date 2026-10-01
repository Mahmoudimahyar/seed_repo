from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import os
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'seed_ci.py'
spec = importlib.util.spec_from_file_location('seed_ci', SCRIPT)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)

class SeedCITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def check(self, name='unit', code='print("ok")', **overrides):
        value = {'id': name, 'argv': [sys.executable, '-c', code], 'cwd': '.',
                 'timeout_seconds': 5, 'not_applicable': None}
        value.update(overrides)
        return value

    def run_config(self, checks):
        path = self.root / 'checks.json'
        path.write_text(json.dumps({'schema_version': 1, 'checks': checks}))
        return ci.run_checks(self.root, 'checks.json')

    def test_success_and_evidence(self):
        code, report = self.run_config([self.check()])
        self.assertEqual(code, 0)
        self.assertEqual(report['checks'][0]['status'], 'PASS')
        self.assertEqual(report['checks'][0]['exit_code'], 0)
        self.assertEqual(len(report['config_sha256']), 64)
        self.assertTrue((self.root / '.seed-ci-artifacts/report.json').exists())

    def test_failure_exit_status_is_preserved(self):
        code, report = self.run_config([self.check(code='raise SystemExit(7)')])
        self.assertEqual(code, 1)
        self.assertEqual(report['checks'][0]['exit_code'], 7)

    def test_missing_command_is_blocked(self):
        code, report = self.run_config([self.check(argv=['seed-nonexistent-executable-12'])])
        self.assertEqual(code, 2)
        self.assertEqual(report['checks'][0]['status'], 'BLOCKED')

    def test_unconfigured_check_is_not_success(self):
        code, report = self.run_config([self.check(argv=None)])
        self.assertEqual(code, 2)
        self.assertIn('UNCONFIGURED', report['checks'][0]['reason'])

    def test_timeout_fails(self):
        code, report = self.run_config([self.check(code='import time; time.sleep(10)', timeout_seconds=0.05)])
        self.assertEqual(code, 1)
        self.assertEqual(report['checks'][0]['reason'], 'TIMEOUT')

    def test_failed_setup_does_not_run_following_commands(self):
        code, report = self.run_config([self.check('setup', 'raise SystemExit(1)'), self.check('unit')])
        self.assertNotEqual(code, 0)
        self.assertEqual(report['checks'][1]['status'], 'NOT_RUN')

    def test_independent_checks_continue_after_failure(self):
        code, report = self.run_config([self.check('unit', 'raise SystemExit(1)'), self.check('build')])
        self.assertEqual(code, 1)
        self.assertEqual(report['checks'][1]['status'], 'PASS')

    def test_not_applicable_needs_real_decision(self):
        code, report = self.run_config([self.check(argv=None, not_applicable={'reason':'No browser in this CLI project', 'decision':'missing.md'})])
        self.assertEqual(code, 2)

    def test_documented_non_applicability_with_real_test(self):
        (self.root / 'decision.md').write_text('Approved CLI scope')
        code, report = self.run_config([self.check(), self.check('browser', argv=None,
            not_applicable={'reason':'Approved CLI has no browser interface', 'decision':'decision.md'})])
        self.assertEqual(code, 0)
        self.assertEqual(report['checks'][1]['status'], 'NOT_APPLICABLE')

    def test_all_non_applicable_is_rejected(self):
        (self.root / 'decision.md').write_text('Scope')
        code, _ = self.run_config([self.check(argv=None, not_applicable={'reason':'No browser in this project', 'decision':'decision.md'})])
        self.assertEqual(code, 2)

    def test_no_checks_is_rejected(self):
        self.assertEqual(self.run_config([])[0], 2)

    def test_duplicate_ids_rejected(self):
        self.assertEqual(self.run_config([self.check(), self.check()])[0], 2)

    def test_unsafe_log_identifier_rejected(self):
        self.assertEqual(self.run_config([self.check('../escape')])[0], 2)

    def test_outside_cwd_rejected(self):
        self.assertEqual(self.run_config([self.check(cwd='..')])[0], 2)

    def test_argv_shell_string_rejected(self):
        self.assertEqual(self.run_config([self.check(argv='echo ok')])[0], 2)

    def test_empty_argv_rejected(self):
        self.assertEqual(self.run_config([self.check(argv=[])])[0], 2)

    def test_conflicting_na_and_command_rejected(self):
        self.assertEqual(self.run_config([self.check(not_applicable={'reason':'not valid', 'decision':'x'})])[0], 2)

    def test_invalid_timeout_rejected(self):
        for timeout in [0, -1, 3601, True, '10']:
            with self.subTest(timeout=timeout):
                self.assertEqual(self.run_config([self.check(timeout_seconds=timeout)])[0], 2)

    def test_missing_config_reports_blocked(self):
        code, report = ci.run_checks(self.root, 'missing.json')
        self.assertEqual(code, 2)
        self.assertEqual(report['status'], 'BLOCKED')

    def test_bad_json_reports_blocked(self):
        (self.root / 'checks.json').write_text('{')
        self.assertEqual(ci.run_checks(self.root, 'checks.json')[0], 2)

    def test_non_dictionary_config_reports_blocked(self):
        (self.root / 'checks.json').write_text('[]')
        self.assertEqual(ci.run_checks(self.root, 'checks.json')[0], 2)

    def test_argv_is_not_shell_interpreted(self):
        malicious = ';touch unwanted-file'
        code, report = self.run_config([self.check(argv=[sys.executable, '-c', 'import sys; print(sys.argv[1])', malicious])])
        self.assertEqual(code, 0)
        self.assertFalse((self.root / 'unwanted-file').exists())
        self.assertIn(malicious, (self.root / report['checks'][0]['log']).read_text())

    def test_log_contains_stdout_and_stderr(self):
        _, report = self.run_config([self.check(code='import sys; print("out"); print("err", file=sys.stderr)')])
        data=(self.root / report['checks'][0]['log']).read_text()
        self.assertIn('out',data)
        self.assertIn('err',data)

    @unittest.skipUnless(os.name == 'posix', 'symlink test requires POSIX')
    def test_evidence_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / '.seed-ci-artifacts').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                ci.run_checks(self.root, 'checks.json')

    def test_valid_titles(self):
        for title in ['feat(api): add validation', 'fix: handle errors', 'feat(schema)!: remove legacy field', 'chore(release): 1.2.0']:
            with self.subTest(title=title): self.assertTrue(ci.valid_title(title))

    def test_invalid_titles(self):
        for title in ['', 'update things', 'feat: ', 'fix: a\nrun stuff', 'feat: '+'x'*121]:
            with self.subTest(title=title): self.assertFalse(ci.valid_title(title))

if __name__ == '__main__':
    unittest.main()
