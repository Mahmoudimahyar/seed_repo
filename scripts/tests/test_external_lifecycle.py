"""Opt-in external research must not contaminate public exports, approvals or optional setup."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import seed
from package_release import package
from seedlib import approvals
from seedlib.external import Sources,SourceError,MANIFEST
from seedlib.common import dump
from test_distribution_lifecycle import template_fixture
from test_external_sources import example_request
import test_seed as fixture


class ExternalDistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.root=self.base/'repo';self.root.mkdir()
        template_fixture(self.root)
        self.source=self.base/'source';self.source.mkdir()
        (self.source/'LICENSE').write_text('Synthetic licensed research fixture.')
        (self.source/'lib.py').write_text('def fixture(): return 1\n')
        self.store=Sources(self.root)

    def test_disabled_capability_has_no_dependencies_or_runtime_side_effects(self):
        self.assertEqual(self.store.status()['status'],'NOT_CONFIGURED')
        self.assertFalse((self.root/'.seed-local/oss').exists())
        self.assertEqual(seed.validate(self.root,public=True),[])

    def test_private_cache_is_omitted_from_validated_export(self):
        local=self.root/'.seed-local/oss/work/private-source.txt'
        local.parent.mkdir(parents=True);local.write_text('Synthetic private investigation.')
        result=package(self.root,self.base/'export')
        with zipfile.ZipFile(result['path']) as archive:
            self.assertFalse(any('.seed-local/' in name for name in archive.namelist()))
            sources=json.loads(archive.read('seed-repo/'+MANIFEST))
            self.assertEqual(sources['sources'],{})

    def test_template_with_registered_sources_is_not_publicly_packaged(self):
        self.store.import_tree(example_request(),self.source,True)
        problems=seed.validate(self.root,public=True)
        self.assertTrue(any('external' in p.lower() for p in problems),problems)
        with self.assertRaises(ValueError):package(self.root,self.base/'export')

    def test_doctor_marks_cached_task_stale_after_external_input_changes(self):
        from seedlib.status import summary
        from seedlib.tasks import run
        self.store.import_tree(example_request(),self.source,True)
        (self.root/'approval-test.txt').write_text('Synthetic task approval fixture only.')
        plan={'id':'external-doctor','owner':'synthetic-test-owner','approved':True,'approval_evidence':'approval-test.txt',
              'scope':'Synthetic verification fixture','allowed_edit_paths':['scratch.txt'],
              'max_steps_per_run':1,'max_attempts_per_task':1,
              'external_sources':[self.store.bind('sample-v1')],
              'tasks':[{'id':'probe','depends_on':[],'argv':['{python}','-c','print("fixture")'],
                        'cwd':'.','timeout_seconds':10}]}
        self.assertEqual(run(self.root,plan,True)['status'],'PASS')
        self.assertEqual(summary(self.root)['task_execution']['status'],'RECORDED_CURRENT')
        (self.store.tree('sample-v1')/'lib.py').write_text('changed')
        self.assertEqual(summary(self.root)['task_execution']['status'],'STALE')

    def test_doctor_does_not_claim_external_provider_installed(self):
        from seedlib.status import summary
        result=summary(self.root)
        self.assertEqual(result['integrations']['external_sources']['status'],'NOT_CONFIGURED')
        self.store.import_tree(example_request(),self.source,True)
        result=summary(self.root)['integrations']['external_sources']
        self.assertEqual(result['sources'][0]['mapping'],'UNVERIFIED')
        self.assertEqual(result['sources'][0]['graph'],'NOT_BUILT')
        (self.store.tree('sample-v1')/'lib.py').write_text('modified')
        self.assertEqual(summary(self.root)['integrations']['external_sources']['sources'][0]['freshness'],'STALE')


class ExternalApprovalTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.StarterTests('runTest');self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups);self.root=self.fixture.root
        self.fixture.initialize();self.ready=self.fixture.approve_recorded_fixture()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.source=Path(self.temp.name).resolve()
        (self.source/'LICENSE').write_text('Synthetic source license.')
        (self.source/'lib.py').write_text('def fixture():return 1\n')
        self.store=Sources(self.root)

    def test_empty_external_registry_does_not_change_existing_approval(self):
        path=self.root/MANIFEST;path.parent.mkdir(exist_ok=True)
        path.write_text(dump({'schema_version':1,'sources':{}}))
        self.assertEqual(seed.ready(self.root),[])

    def test_new_source_manifest_changes_proposed_scope_binding(self):
        old=approvals.propose(self.root,self.ready,seed.load_state(self.root))
        self.store.import_tree(example_request(),self.source,True)
        new=approvals.propose(self.root,self.ready,seed.load_state(self.root))
        self.assertNotEqual(old,new)
        self.assertIn(MANIFEST,new['manifest']['files'])
        self.assertTrue(seed.ready(self.root))

    def test_recorded_scope_binding_does_not_require_cache_on_clean_checkout(self):
        self.store.import_tree(example_request(),self.source,True)
        state=seed.load_state(self.root)
        before=approvals.propose(self.root,self.ready,state)
        shutil.rmtree(self.store.tree('sample-v1').parent)
        after=approvals.propose(self.root,self.ready,state)
        self.assertEqual(before,after)
        with self.assertRaises(SourceError):self.store.bind('sample-v1')


if __name__=='__main__':unittest.main()
