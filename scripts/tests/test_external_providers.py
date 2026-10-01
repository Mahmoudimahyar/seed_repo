"""Provider protocol doubles are NOT runtime certification of the upstream packages."""
from pathlib import Path
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.external import Sources, SourceError, dump, sha
from seedlib.external_tools import acquire_git, acquire_opensrc, verify_against_git, build_graph, graph_search, graph_status, normalize_graph
from test_external_sources import example_request


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.root=self.base/'project';self.root.mkdir()
        self.upstream=self.base/'upstream';self.upstream.mkdir()
        (self.upstream/'LICENSE').write_text('Fixture license for synthetic source.')
        (self.upstream/'lib.py').write_text('def retry():\n    return 3\n')
        self.store=Sources(self.root);self.request=example_request()

    def git(self,*args):
        p=subprocess.run(['git',*args],cwd=self.upstream,capture_output=True,text=True,check=True)
        return p.stdout.strip()

    def repository(self):
        self.git('init','-q'); self.git('add','LICENSE','lib.py')
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture')
        return self.git('rev-parse','HEAD')

    @unittest.skipUnless(shutil.which('git'),'git needed')
    def test_real_local_git_exact_commit_and_dirty_files_excluded(self):
        commit=self.repository();(self.upstream/'lib.py').write_text('dirty tree');(self.upstream/'untracked.txt').write_text('private')
        r=acquire_git(self.store,self.request,commit,local_repo=self.upstream,write=True)
        self.assertEqual(r['identity']['commit'],commit)
        self.assertEqual(r['identity']['origin'],'local-object')
        self.assertIn('retry',self.store.read('sample-v1','lib.py')['content'])
        with self.assertRaises(SourceError):self.store.read('sample-v1','untracked.txt')

    @unittest.skipUnless(shutil.which('git'),'git needed')
    def test_wrong_commit_fails_without_fallback(self):
        self.repository()
        with self.assertRaises(SourceError):acquire_git(self.store,self.request,'0'*40,local_repo=self.upstream,write=True)
        self.assertFalse((self.root/'.seed/external-sources.lock.json').exists())

    def test_git_preview_does_not_fetch_or_write(self):
        with patch('seedlib.external_tools.supervise') as runner:
            r=acquire_git(self.store,self.request,'a'*40)
            self.assertEqual(r['status'],'PREVIEW');runner.assert_not_called()
        self.assertFalse((self.root/'.seed-local').exists())

    def test_branch_name_is_not_a_commit_pin(self):
        for commit in ('main','v1.0.0','a'*7,'a'*40+';x'):
            with self.subTest(commit=commit),self.assertRaises(SourceError):acquire_git(self.store,self.request,commit)

    @unittest.skipUnless(shutil.which('git'),'git needed')
    def test_verification_requires_actual_tree_match(self):
        commit=self.repository();self.store.import_tree(self.request,self.upstream,True)
        old=self.store.get('sample-v1'); oldhash=sha(dump(old).encode())
        result=verify_against_git(self.store,'sample-v1',commit,local_repo=self.upstream,expected_record=oldhash,write=True)
        self.assertEqual(result['identity']['kind'],'git-commit')
        self.assertEqual(self.store.get('sample-v1')['mapping']['status'],'UNVERIFIED')

    @unittest.skipUnless(shutil.which('git'),'git needed')
    def test_version_mismatch_does_not_upgrade_source(self):
        commit=self.repository();(self.upstream/'lib.py').write_text('default branch content differs')
        self.store.import_tree(self.request,self.upstream,True)
        with self.assertRaisesRegex(SourceError,'match'):
            verify_against_git(self.store,'sample-v1',commit,local_repo=self.upstream,
                               expected_record=sha(dump(self.store.get('sample-v1')).encode()),write=True)
        self.assertEqual(self.store.get('sample-v1')['identity']['kind'],'content-snapshot')

    def opensrc_double(self,mode='ok'):
        path=self.base/'fake_opensrc.py'
        path.write_text('''import os, sys\nfrom pathlib import Path\nif '--version' in sys.argv:\n print('opensrc 0.7.3');raise SystemExit(0)\nassert 'OPENAI_API_KEY' not in os.environ\nassert 'NODE_OPTIONS' not in os.environ\nassert os.environ['GIT_ALLOW_PROTOCOL']=='https'\nassert '--verbose' in sys.argv\nassert 'sample@1.0.0' in sys.argv\nbase=Path(os.environ['OPENSRC_HOME'])/'repo'\nbase.mkdir(parents=True)\n(base/'LICENSE').write_text('Fixture license for synthetic source.')\n(base/'lib.py').write_text('def retry():\\n    return 3\\n')\n''' + ("print('/etc')\n" if mode=='escape' else "print('Could not find tag; default branch instead',file=sys.stderr)\nprint(base)\n"))
        return [sys.executable,str(path)]

    def test_opensrc_real_process_double_never_claims_version(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'do-not-forward','NODE_OPTIONS':'do-not-forward'}):
            r=acquire_opensrc(self.store,self.request,command=self.opensrc_double(),write=True)
        self.assertEqual(r['identity']['provider'],'opensrc');self.assertEqual(r['mapping'],'UNVERIFIED')
        self.assertTrue(r['warning']);self.assertIn('retry',self.store.read('sample-v1','lib.py')['content'])
        self.assertNotIn(str(self.base),dump(self.store.manifest()))

    def test_relative_reviewed_script_prefix_survives_disposable_cwd(self):
        command=self.opensrc_double()
        previous=Path.cwd()
        try:
            os.chdir(self.base)
            result=acquire_opensrc(self.store,self.request,[sys.executable,'fake_opensrc.py'],True)
        finally:
            os.chdir(previous)
        self.assertEqual(result['identity']['provider'],'opensrc')

    def test_floating_package_version_is_rejected_before_acquisition(self):
        for version in ('latest','main','HEAD','*'):
            request=copy.deepcopy(self.request);request['version']=version
            with self.subTest(version=version),self.assertRaises(SourceError):
                acquire_opensrc(self.store,request)
        self.assertFalse((self.root/'.seed-local').exists())

    @unittest.skipUnless(shutil.which('git'),'git needed')
    def test_mapping_review_cannot_reference_manifest_it_mutates(self):
        commit=self.repository();acquire_git(self.store,self.request,commit,self.upstream,True)
        with self.assertRaisesRegex(SourceError,'manifest'):
            self.store.review_mapping('sample-v1','.seed/external-sources.lock.json','fixture',
                                      self.store.bind('sample-v1')['record_sha256'],True)

    def test_opensrc_outside_cache_path_rejected(self):
        with self.assertRaises(SourceError):acquire_opensrc(self.store,self.request,command=self.opensrc_double('escape'),write=True)
        self.assertEqual(self.store.status()['status'],'NOT_CONFIGURED')

    def test_opensrc_missing_tool_is_blocked_not_installed(self):
        with self.assertRaisesRegex(SourceError,'available'):
            acquire_opensrc(self.store,self.request,command=['certainly-unavailable-seed-tool'],write=True)
        self.assertEqual(self.store.status()['status'],'NOT_CONFIGURED')

    def test_opensrc_preview_has_no_tool_calls(self):
        with patch('seedlib.external_tools.supervise') as runner:
            r=acquire_opensrc(self.store,self.request);self.assertEqual(r['status'],'PREVIEW');runner.assert_not_called()
        self.assertFalse((self.root/'.seed-local').exists())

    @unittest.skipUnless(shutil.which('git'),'git needed')
    def test_recorded_mapping_binds_evidence_and_changes_task_pin(self):
        commit=self.repository();acquire_git(self.store,self.request,commit,local_repo=self.upstream,write=True)
        old=self.store.bind('sample-v1')
        evidence=self.root/'mapping.md';evidence.write_text('Synthetic test: compare version, public artifact, source and license. Not actual approval.')
        self.store.review_mapping('sample-v1','mapping.md','fixture-owner',old['record_sha256'],True)
        self.assertTrue(self.store.bind('sample-v1',True)['require_reviewed_mapping'])
        with self.assertRaises(SourceError):self.store.check_bindings([old])
        evidence.write_text('Materially changed mapping evidence invalidates the prior record.')
        with self.assertRaises(SourceError):self.store.get('sample-v1')

    def graph_fixture(self):
        return {'nodes':[{'id':'a','label':'retry','source_file':'lib.py','source_location':'L1'},
                         {'id':'b','label':'sdk','source_file':None,'source_location':None}],
                'edges':[{'source':'a','target':'b','relation':'calls','confidence':'INFERRED'}],
                'input_tokens':0,'output_tokens':0,'failed_sources':[]}

    def test_graph_normalization_preserves_uncertainty(self):
        data=normalize_graph(self.graph_fixture(),self.upstream,{'lib.py'})
        self.assertEqual(data['edges'][0]['confidence'],'INFERRED')
        self.assertEqual(data['nodes'][1]['source_file'],None)
        self.assertFalse(data['nodes'][1]['location_verified'])

    def test_graph_external_locations_are_not_read_permissions(self):
        data=self.graph_fixture();data['nodes'][0]['source_file']='/etc/passwd'
        r=normalize_graph(data,self.upstream,{'lib.py'})
        self.assertIsNone(r['nodes'][0]['source_file']);self.assertEqual(r['dropped_locations'],1)

    def test_graph_rejects_semantic_tokens_and_malformed_shape(self):
        for value in ({**self.graph_fixture(),'input_tokens':1},{'nodes':'not-a-list','edges':[]}):
            with self.subTest(value=value),self.assertRaises(SourceError):normalize_graph(value,self.upstream,{'lib.py'})

    def test_graph_paths_and_node_ids_do_not_expose_staging_directory(self):
        data=self.graph_fixture();raw_id=str(self.upstream/'lib.py')+':retry'
        data['nodes'][0].update(id=raw_id,source_location=str(self.upstream/'lib.py')+':L1')
        data['edges'][0]['source']=raw_id
        graph=normalize_graph(data,self.upstream,{'lib.py'})
        self.assertNotIn(str(self.upstream),dump(graph))
        self.assertEqual(graph['edges'][0]['source'],graph['nodes'][0]['id'])
        self.assertTrue(graph['nodes'][0]['id'].startswith('n-'))

    def test_invalid_checkpoint_bindings_fail_with_controlled_error(self):
        for value in (['bad'],[None],[1],[{}],None):
            with self.subTest(value=value),self.assertRaises(SourceError):self.store.check_bindings(value)

    def test_graph_duplicate_ids_are_rejected(self):
        data=self.graph_fixture();data['nodes'].append(data['nodes'][0].copy())
        with self.assertRaises(SourceError):normalize_graph(data,self.upstream,{'lib.py'})

    def test_graph_missing_dependencies_remain_partial(self):
        data=self.graph_fixture();data['failed_sources']=['lib.py']
        r=normalize_graph(data,self.upstream,{'lib.py'})
        self.assertEqual(r['status'],'PARTIAL')

    def test_graph_missing_package_is_blocked_without_invalidation_of_source(self):
        self.store.import_tree(self.request,self.upstream,True)
        # Explicit failure-path unit double. Real installed-package acceptance is a separate checker.
        with patch('seedlib.external_tools.invoke',side_effect=SourceError('BLOCKED: graphifyy missing')):
            with self.assertRaises(SourceError):build_graph(self.store,'sample-v1',write=True)
        self.assertIn('retry',self.store.read('sample-v1','lib.py')['content'])

    def test_graph_preview_does_not_invoke_or_write(self):
        self.store.import_tree(self.request,self.upstream,True)
        with patch('seedlib.external_tools.invoke') as runner:
            r=build_graph(self.store,'sample-v1');runner.assert_not_called();self.assertEqual(r['status'],'PREVIEW')
        self.assertEqual(graph_status(self.store,'sample-v1')['status'],'NOT_BUILT')

if __name__=='__main__':unittest.main()
