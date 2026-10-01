"""Cross-layer tests for feature registration, approval, status and CI applicability."""
from pathlib import Path
import copy
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_seed as fixtures
import test_planning as planning_fixture
from seedlib import approvals, features
from seedlib.acceptance import profile, scope_status
from seedlib.common import dump, read_json
from seedlib.context import Context, build
from seedlib.planning import PlanningStore, DB_PATH
from seedlib.tasks import run


class FeatureAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.StarterTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.fixture.initialize(ui=True)
        self.fixture.write('quality/scope-policy.json', (fixtures.ROOT/'quality/scope-policy.json').read_text())

    def add_feature(self, ui=True):
        for filename in ['requirements.md', 'test-plan.md'] + (['ui-flow.md'] if ui else []):
            self.fixture.write('docs/features/auth/' + filename, '# Synthetic contract\n\nCheck login success, failure and persistence under the documented approval.')
        writes = features.register(self.root, id='auth', owner='fixture-owner', doc_root='docs/features/auth',
                                   ui=ui, code=['src/auth.py'], tests=['tests/test_auth.py'])
        fixtures.seed.write_plan(self.root, writes, set(writes))

    def approve(self):
        return self.fixture.approve_recorded_fixture()

    def test_registration_preview_does_not_write(self):
        before = (self.root/features.REGISTRY).read_bytes()
        features.register(self.root, id='example', owner='fixture', doc_root='docs/features/example')
        self.assertEqual(before, (self.root/features.REGISTRY).read_bytes())

    def test_unregistered_feature_blocks_old_approval(self):
        self.approve()
        self.fixture.write('docs/features/unregistered/ui-flow.md', 'A material new flow the user has not yet reviewed or approved.')
        self.assertTrue(any('Unregistered' in issue for issue in fixtures.seed.ready(self.root)))

    def test_flow_change_stales_bound_scope(self):
        self.add_feature(); self.approve()
        self.fixture.write('docs/features/auth/ui-flow.md', 'A different flow uploads personal files to an unapproved external provider.')
        self.assertTrue(fixtures.seed.ready(self.root))

    def test_new_feature_document_also_stales_scope(self):
        self.add_feature(); self.approve()
        self.fixture.write('docs/features/auth/api.md', 'A new API contract with changed public behavior and new authorization requirements.')
        self.assertTrue(fixtures.seed.ready(self.root))

    def test_deleted_feature_document_stales_scope(self):
        self.add_feature(); self.approve()
        (self.root/'docs/features/auth/test-plan.md').unlink()
        self.assertTrue(fixtures.seed.ready(self.root))

    def test_code_edits_are_not_spec_approval_changes(self):
        self.add_feature(); self.approve()
        self.fixture.write('src/auth.py', 'def login():\n    return True\n')
        self.assertEqual(fixtures.seed.ready(self.root), [])

    def test_feature_without_test_mapping_is_blocked(self):
        self.add_feature()
        registry = read_json(self.root/features.REGISTRY)
        registry['features'][0]['tests'] = []
        self.fixture.write(features.REGISTRY, dump(registry))
        with self.assertRaisesRegex(ValueError, 'test-file'):
            features.scope(self.root, fixtures.seed.load_state(self.root))

    def test_active_ui_requires_flow(self):
        self.add_feature(); (self.root/'docs/features/auth/ui-flow.md').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing active'):
            features.scope(self.root, fixtures.seed.load_state(self.root))

    def test_non_ui_feature_does_not_require_flow(self):
        self.add_feature(ui=False); self.approve()
        self.assertEqual(fixtures.seed.ready(self.root), [])

    def test_deferred_feature_does_not_activate_incomplete_docs(self):
        self.add_feature()
        registry = read_json(self.root/features.REGISTRY)
        registry['features'][0].update(status='deferred', reason='The user deliberately excluded auth from this local-only release.')
        self.fixture.write(features.REGISTRY, dump(registry))
        self.fixture.write('docs/features/auth/ui-flow.md', '__FILL__')
        self.approve()
        self.assertEqual(fixtures.seed.ready(self.root), [])

    def test_deferred_state_change_requires_reapproval(self):
        self.add_feature(); self.approve()
        registry = read_json(self.root/features.REGISTRY)
        registry['features'][0].update(status='deferred', reason='A proposed new scope excludes this previously approved feature.')
        self.fixture.write(features.REGISTRY, dump(registry))
        self.assertTrue(fixtures.seed.ready(self.root))

    def test_ui_capability_cannot_be_silently_added(self):
        self.add_feature()
        state = fixtures.seed.load_state(self.root); state['capabilities']['ui'] = False
        with self.assertRaisesRegex(ValueError, 'UI capability'):
            features.scope(self.root, state)

    def test_duplicate_feature_rejected(self):
        self.add_feature()
        with self.assertRaises(ValueError):
            features.register(self.root, id='auth', owner='another', doc_root='docs/features/auth')

    def test_feature_links_feed_real_context_graph(self):
        self.add_feature(); self.approve()
        self.fixture.write('src/auth.py', 'def login():\n    return True\n')
        self.fixture.write('tests/test_auth.py', 'def test_login():\n    assert True\n')
        build(self.root)
        edges = Context(self.root).related('src/auth.py')['edges']
        self.assertEqual({e['kind'] for e in edges if e['kind'] in {'documents','tests'}}, {'documents','tests'})
        self.assertTrue(all(e['provenance']=='user-declared-not-proven-coverage' for e in edges if e['kind']=='tests'))

    def test_migration_clears_prior_approval(self):
        record = self.approve(); record['gates'] = [g for g in record['gates'] if g['id']!='features']
        self.fixture.write('docs/project/readiness.json', dump(record))
        (self.root/features.REGISTRY).unlink()
        writes = features.migrate(self.root)
        self.assertFalse(json.loads(writes['docs/project/readiness.json'])['approval']['approved'])
        self.assertFalse((self.root/features.REGISTRY).exists())
        fixtures.seed.write_plan(self.root,writes,set(writes))
        self.assertTrue(fixtures.seed.ready(self.root))

    def test_repeat_migration_does_not_reset_scope(self):
        with self.assertRaises(ValueError): features.migrate(self.root)

    def test_app_profile_requires_no_mcp_when_disabled(self):
        info = profile(self.root)
        self.assertEqual(info['profile'], 'application')
        self.assertFalse(info['mcp_required'])
        self.assertTrue(info['starter_regressions_required'])

    def test_enabled_mcp_is_required(self):
        state = fixtures.seed.load_state(self.root)
        state['integrations']['mcp'] = {'enabled':True,'reason':'An approved client uses the graph retrieval integration.'}
        self.fixture.write('seed.json',dump(state))
        self.assertTrue(profile(self.root)['mcp_required'])

    def test_legacy_unspecified_profile_fails_closed(self):
        state = fixtures.seed.load_state(self.root); state.pop('integrations')
        self.fixture.write('seed.json',dump(state))
        with self.assertRaises(ValueError): profile(self.root)

    def test_maintainer_tests_all_integrations(self):
        state = fixtures.seed.load_state(self.root); state.update(kind='template',project=None)
        self.fixture.write('seed.json',dump(state))
        self.assertTrue(profile(self.root)['mcp_required'])
        self.assertEqual(scope_status(self.root)['status'], 'NOT_APPLICABLE')

    def test_technical_success_is_not_scope_acceptance(self):
        self.fixture.write('check.json',dump({'schema_version':1,'checks':[{'id':'demo','argv':['{python}','-c','print("ok")']}]}))
        code, _ = fixtures.ci.run_checks(self.root, 'check.json')
        self.assertEqual(code,0)
        self.assertEqual(scope_status(self.root)['status'],'BLOCKED')

    def test_doctor_blocks_malformed_task_evidence(self):
        self.fixture.write('.seed-local/task-state.json','[]')
        self.assertEqual(fixtures.seed.doctor(self.root)['task_execution']['status'],'BLOCKED')

    def test_doctor_blocks_malformed_technical_evidence(self):
        self.fixture.write('.seed-ci-artifacts/report.json','not valid json')
        self.assertEqual(fixtures.seed.doctor(self.root)['technical_checks']['status'],'BLOCKED')

    def test_doctor_derives_approval_phase(self):
        self.approve()
        report = fixtures.seed.doctor(self.root)
        self.assertEqual(report['declared_phase_hint'],'discovery')
        self.assertEqual(report['phase'],'APPROVED_FOR_SCOPED_WORK')
        self.assertEqual(report['scope_acceptance']['status'],'PASS')

    def test_doctor_does_not_infer_complete_app_from_command_pass(self):
        record=self.approve()
        plan={'id':'test','owner':'fixture','scope':record['scope'],'approved':True,
              'approval_evidence':'docs/project/approval.md','allowed_edit_paths':['src/**'],
              'max_steps_per_run':1,'max_attempts_per_task':1,
              'readiness_sha256':record['approval']['binding']['sha256'],
              'tasks':[{'id':'check','depends_on':[],'argv':['{python}','-c','print("pass")'],'cwd':'.','timeout_seconds':5}]}
        self.assertEqual(run(self.root,plan,True)['status'],'PASS')
        report=fixtures.seed.doctor(self.root)
        self.assertEqual(report['phase'],'EXECUTION_RECORDED')
        self.assertEqual(report['task_execution']['recorded_result'],'PASS')
        self.fixture.write('requirements.txt','changed dependency version')
        self.assertEqual(fixtures.seed.doctor(self.root)['task_execution']['status'],'STALE')

    @unittest.skipUnless(shutil.which('git'), 'Git needed for actual diff classification')
    def test_documentation_only_exception_checks_real_diff(self):
        def git(*args):
            p=subprocess.run(['git',*args],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);return p.stdout.strip()
        git('init','-b','main');git('config','user.name','Synthetic Fixture');git('config','user.email','fixture@example.invalid')
        git('add','.');git('commit','-m','fixture');base=git('rev-parse','HEAD')
        self.fixture.write('docs/project/prd.md','Unapproved discovery work, not permission to implement an application.')
        self.assertEqual(scope_status(self.root,base=base)['status'],'NOT_APPLICABLE')
        self.fixture.write('src/app.py','print("implementation before approval")')
        self.assertEqual(scope_status(self.root,base=base)['status'],'BLOCKED')

    def test_clean_ci_can_verify_exported_planning_snapshot(self):
        f=planning_fixture.PlanningTests('runTest');f.setUp();self.addCleanup(f.doCleanups)
        f.add();f.resolve()
        for name in ('facts.md','policy.md','human.md','answers/privacy.json'):
            self.fixture.write(name,(f.root/name).read_text())
        self.fixture.write('docs/project/decisions-export.json',dump(f.store.export('organizer')))
        record=self.approve()
        record['planning']=[{'map_id':'organizer','requirements':[{'ticket_id':'privacy','allowed_outcomes':['accepted']}],
                            'snapshot':'docs/project/decisions-export.json'}]
        proposal=approvals.propose(self.root,record,fixtures.seed.load_state(self.root))
        self.fixture.write('docs/project/approval.md','Synthetic recorded approval of exact fixture fingerprint: '+proposal['sha256'])
        record=approvals.record(self.root,record,fixtures.seed.load_state(self.root),'fixture','docs/project/approval.md',proposal)
        self.fixture.write('docs/project/readiness.json',dump(record))
        self.assertFalse((self.root/DB_PATH).exists())
        self.assertEqual(scope_status(self.root)['status'],'PASS')
        self.assertFalse((self.root/DB_PATH).exists())
        self.fixture.write('policy.md','A materially different policy forbids the previously accepted plan.')
        self.assertEqual(scope_status(self.root)['status'],'BLOCKED')
