"""Contract/negative tests for optional SDD traceability; fixture XML is not app evidence."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from seedlib import spec_trace as trace
from seedlib.common import atomic_json, safe_path


class SpecTraceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.feature = {'id': 'export', 'owner': 'synthetic-fixture', 'status': 'active',
                        'reason': 'A narrowly scoped synthetic test feature.',
                        'doc_root': 'docs/features/export', 'ui': False,
                        'code': ['src/export.py'], 'tests': ['tests/test_export.py']}
        self.write('docs/project/features.json', json.dumps({'schema_version': 1, 'features': [self.feature]}))
        self.write('docs/features/export/requirements.md',
                   '# Export requirements\n\n## REQ-export-001: Preserve destination\n'
                   'Refuse unapproved overwrite; preserve existing bytes.\n')
        self.write('docs/features/export/test-plan.md',
                   '# Verification plan\nUse a byte-preservation assertion on the destination.\n')
        self.plan = {'schema_version': 1, 'feature_id': 'export',
                     'command': {'argv': ['{python}', '-c',
                        'from pathlib import Path; import sys; Path(sys.argv[1]).write_text(' + repr(self.xml()) + ')',
                        '{junit}'], 'cwd': '.', 'timeout_seconds': 5},
                     'requirements': [{'id': 'REQ-export-001', 'method': 'automated',
                                       'tests': ['tests.test_export::test_preserves'],
                                       'reason': 'Checks preserved bytes through the public API.'}]}
        self.save()

    def write(self, ref, text):
        path = safe_path(self.root, ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def save(self):
        self.write('docs/features/export/verification.json', json.dumps(self.plan))

    @staticmethod
    def xml(body='', extra=''):
        return ('<testsuites><testsuite name="fixture"><testcase classname="tests.test_export" '
                'name="test_preserves">' + body + '</testcase>' + extra + '</testsuite></testsuites>')

    def report_case(self, body='', extra='', exit_code=0):
        self.plan['command']['argv'] = ['{python}', '-c',
            'from pathlib import Path; import sys; Path(sys.argv[1]).write_text(' + repr(self.xml(body, extra)) + '); '
            'raise SystemExit(' + str(exit_code) + ')', '{junit}']
        self.save()
        return trace.run(self.root, 'export')

    def test_plan_does_not_require_tests_to_exist_before_implementation(self):
        report = trace.plan_status(self.root, 'export')
        self.assertEqual(report['status'], 'PLANNED')
        self.assertFalse((self.root / 'tests/test_export.py').exists())
        self.assertFalse((self.root / '.seed-local').exists())

    def test_missing_map_is_not_success(self):
        (self.root / 'docs/features/export/verification.json').unlink()
        self.assertEqual(trace.plan_status(self.root, 'export')['status'], 'NOT_CONFIGURED')

    def test_unknown_feature_rejected(self):
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'other')

    def test_deferred_feature_cannot_be_executed(self):
        self.feature['status'] = 'deferred'
        self.write('docs/project/features.json', json.dumps({'schema_version': 1, 'features': [self.feature]}))
        with self.assertRaises(ValueError): trace.run(self.root, 'export')

    def test_unknown_policy_field_is_rejected(self):
        self.plan['ignore_missing_tests'] = True; self.save()
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_requirement_id_wrong_feature_namespace(self):
        self.plan['requirements'][0]['id'] = 'REQ-other-001'; self.save()
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_duplicate_map_ids_are_rejected(self):
        self.plan['requirements'].append(deepcopy(self.plan['requirements'][0])); self.save()
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_duplicate_declared_requirement_is_rejected(self):
        ref = 'docs/features/export/requirements.md'
        self.write(ref, safe_path(self.root, ref).read_text() + '\n## REQ-export-001: duplicate\n')
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_unmapped_declared_requirement_is_rejected(self):
        ref = 'docs/features/export/requirements.md'
        self.write(ref, safe_path(self.root, ref).read_text() + '\n## REQ-export-002: another\n')
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_reference_without_declaration_is_rejected(self):
        self.plan['requirements'][0]['id'] = 'REQ-export-002'; self.save()
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_fenced_examples_not_counted_as_requirements(self):
        ref = 'docs/features/export/requirements.md'
        self.write(ref, safe_path(self.root, ref).read_text() +
                   '\n```md\n## REQ-export-999: example\n```\n')
        self.assertEqual(trace.plan_status(self.root, 'export')['status'], 'PLANNED')

    def test_namespace_id_lint_without_map(self):
        (self.root / 'docs/features/export/verification.json').unlink()
        ref = 'docs/features/export/requirements.md'
        self.write(ref, safe_path(self.root, ref).read_text() + '\n## REQ-export-001: duplicate\n')
        with self.assertRaises(ValueError): trace.lint_feature(self.root, self.feature)

    def test_legacy_prose_without_map_remains_valid(self):
        (self.root / 'docs/features/export/verification.json').unlink()
        self.write('docs/features/export/requirements.md', '# Requirements\nPreserve existing destination data.\n')
        trace.lint_feature(self.root, self.feature)

    def test_argv_must_reserve_fresh_report_path(self):
        self.plan['command']['argv'] = ['{python}', '-c', 'print("done")']; self.save()
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_cwd_traversal_rejected(self):
        self.plan['command']['cwd'] = '../'; self.save()
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_runner_cannot_live_in_private_runtime_folder(self):
        self.plan['command']['cwd'] = '.seed-local'; self.save()
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_repeated_arguments_permitted(self):
        self.plan['command']['argv'] += ['--flag', '--flag']; self.save()
        self.assertEqual(trace.plan_status(self.root, 'export')['status'], 'PLANNED')

    def test_exact_junit_case_is_collected(self):
        self.assertEqual(trace.parse_junit(self.xml().encode()), {'tests.test_export::test_preserves': 'PASS'})

    def test_duplicate_junit_ids_are_rejected(self):
        xml = self.xml(extra='<testcase classname="tests.test_export" name="test_preserves"/>')
        with self.assertRaises(ValueError): trace.parse_junit(xml.encode())

    def test_xml_doctype_and_entities_rejected(self):
        with self.assertRaises(ValueError):
            trace.parse_junit(b'<!DOCTYPE a [<!ENTITY x "xx">]><testsuite/>')

    def test_empty_junit_is_not_a_passing_suite(self):
        with self.assertRaises(ValueError): trace.parse_junit(b'<testsuite tests="0"/>')

    def test_invalid_xml_is_rejected(self):
        with self.assertRaises(ValueError): trace.parse_junit(b'not XML')

    def test_suite_level_error_is_rejected(self):
        xml = self.xml().replace('<testsuite name="fixture">', '<testsuite name="fixture"><error/>')
        with self.assertRaises(ValueError): trace.parse_junit(xml.encode())

    def test_passed_record_is_fresh(self):
        report = self.report_case()
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(trace.check(self.root, report['report_path'])['status'], 'PASS')
        self.assertEqual(report['coverage'][0]['status'], 'PASS')

    def test_failure_and_error_never_pass(self):
        for body in ('<failure message="failure"/>', '<error message="error"/>'):
            with self.subTest(body=body): self.assertEqual(self.report_case(body)['status'], 'FAIL')

    def test_skipped_mapped_test_blocks(self):
        report = self.report_case('<skipped/>')
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertEqual(report['coverage'][0]['status'], 'SKIPPED')

    def test_missing_named_test_blocks_even_when_other_tests_pass(self):
        self.plan['requirements'][0]['tests'] = ['tests.test_export::test_missing']; self.save()
        report = self.report_case()
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertEqual(report['coverage'][0]['status'], 'NOT_RUN')

    def test_unmapped_supporting_failure_fails(self):
        self.assertEqual(self.report_case(extra='<testcase name="helper"><failure/></testcase>')['status'], 'FAIL')

    def test_success_xml_cannot_override_command_failure(self):
        self.assertEqual(self.report_case(exit_code=1)['status'], 'FAIL')

    def test_success_command_without_xml_is_blocked(self):
        self.plan['command']['argv'] = ['{python}', '-c', 'print("no report")', '{junit}']; self.save()
        self.assertEqual(trace.run(self.root, 'export')['status'], 'BLOCKED')

    def test_timeout_is_not_coverage(self):
        self.plan['command']['argv'] = ['{python}', '-c', 'import time; time.sleep(5)', '{junit}']
        self.plan['command']['timeout_seconds'] = 1; self.save()
        self.assertNotEqual(trace.run(self.root, 'export')['status'], 'PASS')

    def test_prior_xml_never_substitutes_for_fresh_run(self):
        first = self.report_case()
        self.plan['command']['argv'] = ['{python}', '-c', 'print("no new result")', '{junit}']; self.save()
        second = trace.run(self.root, 'export')
        self.assertNotEqual(first['report_path'], second['report_path'])
        self.assertEqual(second['status'], 'BLOCKED')

    def test_editing_code_invalidates_result_not_scope(self):
        report = self.report_case()
        self.write('src/export.py', 'def export(): return "changed"\n')
        self.assertEqual(trace.check(self.root, report['report_path'])['status'], 'STALE')

    def test_editing_plan_invalidates_result(self):
        report = self.report_case()
        self.plan['requirements'][0]['reason'] += ' Revised.'; self.save()
        self.assertEqual(trace.check(self.root, report['report_path'])['status'], 'STALE')

    def test_corrupted_junit_invalidates_result(self):
        report = self.report_case()
        self.write(report['junit_path'], self.xml('<failure/>'))
        self.assertEqual(trace.check(self.root, report['report_path'])['status'], 'STALE')

    def test_source_mutation_during_test_is_stale(self):
        self.plan['command']['argv'][-2] += '; Path("surprise.txt").write_text("changed input")'; self.save()
        self.assertEqual(trace.run(self.root, 'export')['status'], 'STALE')

    def test_multiple_tests_for_one_requirement(self):
        self.plan['requirements'][0]['tests'].append('helper'); self.save()
        self.assertEqual(self.report_case(extra='<testcase name="helper"/>')['status'], 'PASS')

    def test_same_test_can_support_multiple_requirements(self):
        ref = 'docs/features/export/requirements.md'
        self.write(ref, safe_path(self.root, ref).read_text() + '\n## REQ-export-002: Preserve other data\n')
        other = deepcopy(self.plan['requirements'][0]); other['id'] = 'REQ-export-002'
        self.plan['requirements'].append(other); self.save()
        self.assertEqual(self.report_case()['status'], 'PASS')

    def test_manual_checks_cannot_be_claimed_by_automated_adapter(self):
        self.plan['requirements'][0].update(method='manual', tests=[], reason='Qualified reviewer must assess keyboard usability.')
        self.save()
        report = self.report_case()
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertEqual(report['coverage'][0]['status'], 'NOT_RUN')

    def test_post_release_observation_not_claimed_as_tested(self):
        self.plan['requirements'][0].update(method='post_release', tests=[], reason='Adoption is measured after release using actual usage.')
        self.save()
        self.assertEqual(self.report_case()['status'], 'NOT_APPLICABLE')

    def test_outcomes_never_written_into_approved_docs(self):
        before = {p: p.read_bytes() for p in (self.root/'docs').rglob('*') if p.is_file()}
        trace.run(self.root, 'export')
        # Execution results must not be written into approved input artifacts.
        after = {p: p.read_bytes() for p in (self.root/'docs').rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_stop_file_blocks_before_command(self):
        self.write('.seed-local/STOP', 'halt')
        self.assertEqual(self.report_case()['status'], 'BLOCKED')

    def test_status_report_does_not_contain_xml_output(self):
        report = self.report_case('<failure message="test detail"/>')
        self.assertNotIn('test detail', json.dumps(report))

    def test_editing_stored_status_is_detected(self):
        report = self.report_case('<failure/>')
        report['status'] = 'PASS'
        atomic_json(safe_path(self.root, report['report_path']), report)
        self.assertEqual(trace.check(self.root, report['report_path'])['status'], 'BLOCKED')

    @unittest.skipUnless(os.name == 'posix', 'POSIX symlink boundary')
    def test_symlinked_junit_rejected(self):
        self.write('outside.xml', self.xml())
        self.plan['command']['argv'] = ['{python}', '-c',
            'from pathlib import Path; import sys; Path(sys.argv[1]).symlink_to(Path("outside.xml").resolve())', '{junit}']
        self.save()
        self.assertEqual(trace.run(self.root, 'export')['status'], 'BLOCKED')

    def test_old_non_namespaced_headings_remain_prose_without_map(self):
        (self.root / 'docs/features/export/verification.json').unlink()
        self.write('docs/features/export/requirements.md', '# Requirements\n\n## REQ-001: old style\nPreserve data.\n')
        trace.lint_feature(self.root, self.feature)

    def test_junit_counter_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            trace.parse_junit(self.xml().replace('name="fixture"', 'name="fixture" tests="2"').encode())

    def test_notrun_status_is_not_pass(self):
        report = self.xml().replace('name="test_preserves"', 'name="test_preserves" status="notrun"')
        self.assertEqual(trace.parse_junit(report.encode())['tests.test_export::test_preserves'], 'SKIPPED')

    def test_flaky_retry_extensions_are_not_silently_accepted(self):
        with self.assertRaises(ValueError): trace.parse_junit(self.xml('<flakyFailure/>').encode())

    def test_unknown_junit_status_rejected(self):
        report = self.xml().replace('name="test_preserves"', 'name="test_preserves" status="unknown"')
        with self.assertRaises(ValueError): trace.parse_junit(report.encode())

    def test_oversized_junit_rejected(self):
        with self.assertRaises(ValueError): trace.parse_junit(b' ' * (trace.MAX_XML_BYTES + 1))

    def test_no_configured_maps_means_no_traceability_claim(self):
        (self.root / 'docs/features/export/verification.json').unlink()
        self.assertEqual(trace.run_configured(self.root)['status'], 'NOT_CONFIGURED')

    def test_ci_executes_registered_map(self):
        from seed_ci import run_traceability
        report = {'schema_version': 1, 'status': 'PASS', 'checks': []}
        code, output = run_traceability(self.root, 0, report)
        self.assertEqual(code, 0)
        self.assertEqual(output['requirement_traceability']['status'], 'PASS')

    def test_ci_does_not_run_after_other_checks_block(self):
        from seed_ci import run_traceability
        code, output = run_traceability(self.root, 2, {'status': 'BLOCKED'})
        self.assertEqual(code, 2)
        self.assertEqual(output['requirement_traceability']['status'], 'NOT_RUN')
        self.assertFalse((self.root / trace.BASE).exists())

    def test_ci_skipped_critical_test_blocks_technical_acceptance(self):
        from seed_ci import run_traceability
        self.plan['command']['argv'][2] = self.plan['command']['argv'][2].replace(repr(self.xml()), repr(self.xml('<skipped/>')))
        self.save()
        code, report = run_traceability(self.root, 0, {'status': 'PASS'})
        self.assertEqual(code, 2)
        self.assertEqual(report['status'], 'BLOCKED')

    def test_ci_no_maps_does_not_add_framework_requirement(self):
        from seed_ci import run_traceability
        (self.root / 'docs/features/export/verification.json').unlink()
        code, report = run_traceability(self.root, 0, {'status': 'PASS'})
        self.assertEqual(code, 0)
        self.assertEqual(report['requirement_traceability']['status'], 'NOT_CONFIGURED')

    def test_unsafe_report_reference_rejected(self):
        with self.assertRaises(ValueError): trace.check(self.root, '../report.json')

    def test_external_dependency_edits_stale_saved_test_evidence(self):
        report = self.report_case()
        self.write('requirements.txt', 'a-new-dependency==1.2.3\n')
        self.assertEqual(trace.check(self.root, report['report_path'])['status'], 'STALE')

    def test_named_mappings_must_not_use_wildcard_matching(self):
        self.plan['requirements'][0]['tests'] = ['tests.test_export::*']; self.save()
        report = self.report_case()
        self.assertEqual(report['status'], 'BLOCKED')

    def test_duplicate_test_refs_within_requirement_rejected(self):
        self.plan['requirements'][0]['tests'] *= 2; self.save()
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_utf16_xml_is_not_an_entity_bypass(self):
        with self.assertRaises(ValueError): trace.parse_junit(self.xml().encode('utf-16'))

    def test_feature_namespace_cannot_be_extended(self):
        self.write('docs/features/export/requirements.md', '# Rules\n\n## REQ-export-other-001: Not this namespace\n')
        self.plan['requirements'][0]['id'] = 'REQ-export-other-001'; self.save()
        with self.assertRaises(ValueError): trace.plan_status(self.root, 'export')

    def test_junit_failure_counter_cannot_disagree_with_cases(self):
        xml = self.xml().replace('name="fixture"', 'name="fixture" failures="1"')
        with self.assertRaises(ValueError): trace.parse_junit(xml.encode())

    def test_junit_skip_counter_cannot_hide_skip(self):
        xml = self.xml('<skipped/>').replace('name="fixture"', 'name="fixture" skipped="0"')
        with self.assertRaises(ValueError): trace.parse_junit(xml.encode())

if __name__ == '__main__':
    unittest.main()
