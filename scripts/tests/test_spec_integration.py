"""SDD boundary regressions using existing starter fixtures, not a second application framework."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_seed as fixtures
from seedlib import features, spec_trace
from seedlib.common import dump, safe_path
from seed_ci import run_traceability


class SpecIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.StarterTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.initialize()
        self.root = self.fixture.root
        self.write = self.fixture.write
        updates = features.register(self.root, id='export', owner='synthetic-fixture',
                                    doc_root='docs/features/export', code=['src/export.py'],
                                    tests=['tests/test_export.py'])
        for path, content in updates.items(): self.write(path, content)
        self.write('docs/features/export/requirements.md', '# Intended behavior\n\n## REQ-export-001: Preserve bytes\nRefuse overwrite and preserve the original file.\n')
        self.write('docs/features/export/test-plan.md', '# Stable planned checks\nPreserve a known destination before rejecting overwrite.\n')
        xml = '<testsuite tests="1"><testcase classname="export" name="preserves"/></testsuite>'
        self.plan = {'schema_version': 1, 'feature_id': 'export', 'command': {
            'argv': ['{python}', '-c', 'import sys; from pathlib import Path; Path(sys.argv[1]).write_text(' + repr(xml) + ')', '{junit}'],
            'cwd': '.', 'timeout_seconds': 5}, 'requirements': [{'id': 'REQ-export-001', 'method': 'automated',
                'tests': ['export::preserves'], 'reason': 'Synthetic reporter contract test, not a real application test.'}]}
        self.write('docs/features/export/verification.json', dump(self.plan))

    def test_invalid_requirement_mapping_blocks_scope_proposal(self):
        self.plan['requirements'][0]['id'] = 'REQ-export-999'
        self.write('docs/features/export/verification.json', dump(self.plan))
        issues = fixtures.seed.ready(self.root)
        self.assertTrue(any('requirement' in issue.lower() for issue in issues), issues)

    def test_duplicate_requirement_is_caught_by_static_validator(self):
        path = 'docs/features/export/requirements.md'
        self.write(path, safe_path(self.root, path).read_text() + '\n## REQ-export-001: Again\n')
        self.assertTrue(any('Duplicate requirement ID' in issue for issue in fixtures.seed.validate(self.root)))

    def test_planned_tests_need_not_exist_at_approval(self):
        self.fixture.approve_recorded_fixture()
        self.assertEqual(fixtures.seed.ready(self.root), [])
        self.assertFalse(safe_path(self.root, 'tests/test_export.py').exists())

    def test_result_updates_do_not_invalidate_approved_test_plan(self):
        self.fixture.approve_recorded_fixture()
        before = safe_path(self.root, 'docs/features/export/test-plan.md').read_bytes()
        self.assertEqual(spec_trace.run(self.root, 'export')['status'], 'PASS')
        self.assertEqual(fixtures.seed.ready(self.root), [])
        self.assertEqual(safe_path(self.root, 'docs/features/export/test-plan.md').read_bytes(), before)

    def test_mapping_change_does_invalidate_scope(self):
        self.fixture.approve_recorded_fixture()
        self.plan['requirements'][0]['tests'] = ['export::different']
        self.write('docs/features/export/verification.json', dump(self.plan))
        self.assertTrue(any('stale' in issue.lower() for issue in fixtures.seed.ready(self.root)))

    def test_current_doctor_reports_plan_not_test_conformance(self):
        view = fixtures.seed.doctor(self.root)['requirement_traceability']
        self.assertEqual(view['status'], 'PLANNED')
        self.assertNotIn('PASS', json.dumps(view))

    def test_technical_result_does_not_create_approval(self):
        code, _ = run_traceability(self.root, 0, {'status': 'PASS'})
        self.assertEqual(code, 0)
        self.assertTrue(fixtures.seed.ready(self.root))

    def test_no_mutable_evidence_cell_in_feature_test_plan_template(self):
        text = (fixtures.ROOT/'templates/feature/test-plan.md').read_text()
        self.assertNotIn('| Evidence |', text)
        self.assertNotIn('| NOT_RUN |', text)

    def test_ci_retains_coverage_without_uploading_private_raw_logs(self):
        code, report = run_traceability(self.root, 0, {'status': 'PASS'})
        self.assertEqual(code, 0)
        evidence = report['requirement_traceability']['features'][0]['evidence']
        self.assertEqual(evidence['coverage'][0]['status'], 'PASS')
        self.assertEqual(evidence['case_count'], 1)
        self.assertEqual(evidence['process']['exit_code'], 0)
        self.assertEqual(len(evidence['report_sha256']), 64)
        self.assertNotIn('stdout', evidence)
        self.assertNotIn('stderr', evidence)
        saved = json.loads((self.root/'.seed-ci-artifacts/report.json').read_text())
        self.assertEqual(saved['requirement_traceability'], report['requirement_traceability'])

    def test_profile_declares_automatic_trace_consumer(self):
        text = (fixtures.ROOT/'scripts/seed_ci.py').read_text()
        self.assertIn('code, report = run_traceability(Path.cwd(), code, report)', text)
        guide = (fixtures.ROOT/'docs/engineering/ci-cd.md').read_text()
        self.assertIn('automatically executes', guide)

if __name__ == '__main__':
    unittest.main()
