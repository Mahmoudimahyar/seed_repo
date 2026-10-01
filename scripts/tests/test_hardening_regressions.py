"""Synthetic regressions for the v0.3.0 integration audit; no real secrets/approvals."""
from pathlib import Path
import copy
import json
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import seed
from run_candidate import run as predict
from seedlib.context import Context, build
from seedlib.evaluation import compare, evaluate
from seedlib.tasks import run, ordered_tasks

ROOT = Path(__file__).resolve().parents[2]

class IntegrationRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def plan(self, code='print("ok")'):
        self.write('approval.md', 'Synthetic approval only for an isolated regression fixture.')
        return {'id': 'test', 'owner': 'fixture', 'scope': 'Synthetic regression scope',
                'approved': True, 'approval_evidence': 'approval.md', 'allowed_edit_paths': ['src/**'],
                'max_steps_per_run': 1, 'max_attempts_per_task': 2,
                'tasks': [{'id': 'one', 'depends_on': [], 'argv': ['{python}', '-c', code],
                           'cwd': '.', 'timeout_seconds': 5}]}

    def test_F02_requirements_write_detected(self):
        result = run(self.root, self.plan('from pathlib import Path; Path("requirements.txt").write_text("x==1")'), True)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('requirements.txt', result['tasks']['one']['unexpected_paths'])

    def test_F02_retrieval_exclusion_does_not_hide_execution_edits(self):
        self.write('.seed/context-ignore.txt', 'evals/**\n')
        self.write('evals/release.json', '{}')
        result = run(self.root, self.plan('from pathlib import Path; Path("evals/release.json").write_text("{\\\"x\\\":1}")'), True)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('evals/release.json', result['tasks']['one']['unexpected_paths'])

    def test_F02_dependency_change_invalidates_resume(self):
        self.write('requirements.txt', 'example==1')
        plan = self.plan()
        self.assertEqual(run(self.root, plan, True)['status'], 'PASS')
        self.write('requirements.txt', 'example==2')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            run(self.root, plan, True)

    def test_F14_repeated_arguments_are_legal(self):
        plan = self.plan()
        plan['tasks'][0]['argv'] = ['echo', 'same', 'same']
        self.assertEqual(len(ordered_tasks(plan)), 1)

    def test_F10_module_level_ranges_are_searchable(self):
        self.write('module.py', 'def helper():\n    return 1\n' + '# spacer\n' * 40 + 'SPECIAL_CONSTANT = 29\n')
        build(self.root)
        result = Context(self.root).search('SPECIAL_CONSTANT')
        self.assertTrue(any('SPECIAL_CONSTANT' in row['excerpt'] for row in result['items']))

    def test_F11_semantic_links_survive_containment(self):
        self.write('module.py', '\n'.join(f'def item_{i}():\n    return {i}' for i in range(60)))
        self.write('tests/test_module.py', 'assert True\n')
        self.write('.seed/context-links.json', json.dumps([{'source': 'tests/test_module.py', 'target': 'module.py', 'relation': 'tests'}]))
        build(self.root)
        result = Context(self.root).related('module.py', limit=20)
        self.assertTrue(any(e['kind'] == 'tests' for e in result['edges']))

    def test_F12_long_single_line_is_bounded(self):
        self.write('big.json', json.dumps({'text': 'x' * 220_000}))
        build(self.root)
        result = Context(self.root).read('big.json', 1, 1)
        self.assertLessEqual(len(json.dumps(result, ensure_ascii=False)), 30000)
        self.assertTrue(result['truncated'])
        self.assertIsNotNone(result['continuation'])

    def test_F06_external_abstention_survives_adapter(self):
        cases = [{'id': 'a', 'input': 'text'}]
        cfg = {'kind': 'external', 'argv': ['{python}', '-c', 'import json; print(json.dumps({"prediction":None,"abstained":True,"cost_usd":0}))']}
        rows = predict(self.root, cases, cfg, allow_external=True)
        self.assertTrue(rows[0].get('abstained'))

    def test_F07_coverage_policy_is_enforced(self):
        cases = [{'id': str(i), 'input': 'x', 'expected': 'x', 'split': 'release', 'group': str(i), 'label_status': 'verified', 'slices': ['all']} for i in range(2)]
        config = {'candidate': 'demo', 'configuration': {}, 'scorer': 'exact_json'}
        incumbent = evaluate(cases, [{'id': str(i), 'prediction': 'x', 'cost_usd': 0, 'latency_ms': 1} for i in range(2)], 'a'*64, config)
        candidate = evaluate(cases, [{'id': '0', 'prediction': 'x', 'cost_usd': 0, 'latency_ms': 1}, {'id': '1', 'abstained': True, 'cost_usd': 0, 'latency_ms': 1}], 'a'*64, config)
        policy = {'min_cases': 1, 'min_accuracy': 0, 'min_accuracy_lower_95': 0, 'max_regressions': 2, 'max_p95_latency_ms': 100, 'max_total_cost_usd': 1, 'min_slice_accuracy': 0, 'min_coverage': 1}
        self.assertEqual(compare(incumbent, candidate, policy)['status'], 'REJECT')

    def test_F07_unknown_policy_field_rejected(self):
        cases = [{'id': '0', 'input': 'x', 'expected': 'x', 'split': 'release', 'group': 'x', 'label_status': 'verified', 'slices': []}]
        result = evaluate(cases, [{'id': '0', 'prediction': 'x', 'cost_usd': 0, 'latency_ms': 1}], 'a'*64, {'candidate': 'test', 'configuration': {}, 'scorer': 'exact_json'})
        policy = {'min_cases': 1, 'min_accuracy': 0, 'min_accuracy_lower_95': 0, 'max_regressions': 1, 'max_p95_latency_ms': 100, 'max_total_cost_usd': 1, 'min_slice_accuracy': 0, 'unsupported_guard': True}
        with self.assertRaises(ValueError):
            compare(result, result, policy)
