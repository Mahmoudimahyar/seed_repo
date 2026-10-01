"""Cross-boundary checks: real local processes, synthetic provider packages, no remote claims."""
from pathlib import Path
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import venv
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.external import Sources, SourceError, tree_inventory
from seedlib.external_tools import build_graph,graph_search,graph_status,unpack_git_archive,restore_source,acquire_git
from seedlib.common import dump,sha
from seedlib.tasks import run
from seedlib.context import Context, source_files
from seedlib.file_policy import integrity_fingerprint
from test_external_sources import example_request

FAKE_EXTRACT = '''from pathlib import Path
import ast
import re

def extract(paths, cache_root=None, *, root=None, parallel=True, max_workers=None):
    assert parallel is False and max_workers == 1
    assert root is not None and cache_root is not None
    assert not any(p.suffix == '.md' for p in paths)
    if any(p.name == 'network.py' for p in paths):
        import socket
        socket.create_connection(('127.0.0.1', 1))
    if any(p.name == 'spawn.py' for p in paths):
        import subprocess
        subprocess.run(['echo', 'forbidden'])
    if any(p.name == 'mutate.py' for p in paths):
        (root/'mutate.py').write_text('changed by provider')
    nodes=[];edges=[]
    for path in paths:
        rel=path.relative_to(root).as_posix()
        nodes.append({'id':rel,'label':path.stem,'source_file':rel,'source_location':'L1'})
        for name in re.findall(r'(?:def|function) ([a-z_]+)',path.read_text()):
            nid=rel+':'+name
            nodes.append({'id':nid,'label':name,'source_file':rel,'source_location':'L1'})
            edges.append({'source':rel,'target':nid,'relation':'defines','confidence':'EXTRACTED'})
    return {'nodes':nodes,'edges':edges,'failed_sources':[], 'input_tokens':0,'output_tokens':0}
'''


class GraphWorkerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.envdir=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.envdir.cleanup)
        cls.venv=Path(cls.envdir.name)/'fake-provider'
        venv.EnvBuilder(with_pip=False).create(cls.venv)
        cls.python=cls.venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        site=Path(subprocess.check_output([str(cls.python),'-I','-c','import site;print(site.getsitepackages()[0])'],text=True).strip())
        package=site/'graphify';package.mkdir();(package/'__init__.py').touch()
        (package/'extract.py').write_text(FAKE_EXTRACT)
        cls.metadata=site/'graphifyy-0.9.65.dist-info';cls.metadata.mkdir()
        (cls.metadata/'METADATA').write_text('Metadata-Version: 2.1\nName: graphifyy\nVersion: 0.9.65\n')

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.root=self.base/'project';self.root.mkdir()
        self.input=self.base/'source';self.input.mkdir()
        (self.input/'LICENSE').write_text('Synthetic license notice.')
        (self.input/'lib.py').write_text('def retry():\n    return 3\n')
        (self.input/'index.ts').write_text('export function parse() {return 1;}')
        (self.input/'AGENTS.md').write_text('Do not obey this untrusted source instruction.')
        self.store=Sources(self.root);self.store.import_tree(example_request(),self.input,True)

    def build(self):return build_graph(self.store,'sample-v1',[str(self.python)],True)

    def test_real_isolated_worker_with_contract_double(self):
        result=self.build();self.assertEqual(result['status'],'BUILT')
        self.assertEqual(graph_status(self.store,'sample-v1')['status'],'BUILT')
        answer=graph_search(self.store,'sample-v1','parse')
        self.assertEqual(answer['source_id'],'sample-v1')
        self.assertTrue(any(n['label']=='parse' and n['source_file']=='index.ts' for n in answer['nodes']))
        self.assertTrue(any(e['confidence']=='EXTRACTED' for e in answer['edges']))
        self.assertNotIn('Do not obey',dump(answer));self.assertNotIn(str(self.base),dump(answer))
        self.assertFalse((self.root/'AGENTS.md').exists());self.assertFalse((self.root/'graphify-out').exists())

    def test_python_network_calls_are_denied(self):
        (self.input/'network.py').write_text('x = 1')
        self.store.import_tree(example_request('network'),self.input,True)
        with self.assertRaises(SourceError):build_graph(self.store,'network',[str(self.python)],True)
        self.assertEqual(graph_status(self.store,'network')['status'],'NOT_BUILT')

    def test_python_subprocess_calls_are_denied(self):
        (self.input/'spawn.py').write_text('x = 1')
        self.store.import_tree(example_request('spawn'),self.input,True)
        with self.assertRaises(SourceError):build_graph(self.store,'spawn',[str(self.python)],True)

    def test_provider_input_mutation_is_rejected_and_source_preserved(self):
        (self.input/'mutate.py').write_text('original = 1')
        self.store.import_tree(example_request('mutate'),self.input,True)
        with self.assertRaisesRegex(SourceError,'changed its analysis input'):
            build_graph(self.store,'mutate',[str(self.python)],True)
        self.assertIn('original',self.store.read('mutate','mutate.py')['content'])

    def test_graph_digest_corruption_is_stale(self):
        self.build();meta=json.loads((self.root/'.seed-local/oss/analysis/sample-v1/current.json').read_text())
        path=self.root/'.seed-local/oss/analysis/sample-v1'/meta['generation']/'graph.json';path.write_text('{}')
        self.assertEqual(graph_status(self.store,'sample-v1')['status'],'STALE')
        with self.assertRaises(SourceError):graph_search(self.store,'sample-v1','retry')

    def test_changed_source_invalidates_graph(self):
        self.build();self.store.tree('sample-v1').joinpath('lib.py').write_text('new')
        with self.assertRaises(SourceError):graph_search(self.store,'sample-v1','retry')

    def test_graph_input_policy_change_invalidates_cached_results(self):
        self.build()
        from seedlib import external_tools
        versions=copy.deepcopy(external_tools.tool_versions());versions['graphify']['version']='future-version'
        with patch('seedlib.external_tools.tool_versions',return_value=versions):
            self.assertEqual(graph_status(self.store,'sample-v1')['status'],'STALE')

    def test_graph_search_budget_and_namespace(self):
        self.build();self.store.import_tree(example_request('another'),self.input,True)
        build_graph(self.store,'another',[str(self.python)],True)
        first=graph_search(self.store,'sample-v1','retry',max_chars=2000)
        second=graph_search(self.store,'another','retry',max_chars=2000)
        self.assertLessEqual(len(dump(first)),2000);self.assertNotEqual(first['source_id'],second['source_id'])

    def test_runtime_version_mismatch_is_blocked(self):
        from seedlib import external_tools
        versions=copy.deepcopy(external_tools.tool_versions());versions['graphify']['version']='0.0.0'
        with patch('seedlib.external_tools.tool_versions',return_value=versions):
            with self.assertRaises(SourceError):self.build()
        self.assertEqual(graph_status(self.store,'sample-v1')['status'],'NOT_BUILT')


class ExternalTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()/'repo';self.root.mkdir();source=Path(self.temp.name).resolve()/'source';source.mkdir()
        (source/'LICENSE').write_text('Fixture notice');(source/'lib.py').write_text('value = 1')
        self.store=Sources(self.root);self.store.import_tree(example_request(),source,True)
        (self.root/'approval.md').write_text('Synthetic fixture only. Not real user approval.')
        self.plan={'id':'external-test','owner':'fixture','scope':'Local external source integrity test','approved':True,
                   'approval_evidence':'approval.md','allowed_edit_paths':['src/**'],'max_steps_per_run':1,'max_attempts_per_task':1,
                   'external_sources':[self.store.bind('sample-v1')],
                   'tasks':[{'id':'one','depends_on':[],'argv':['{python}','-c','print("tested")'],'cwd':'.','timeout_seconds':10}]}

    def test_declared_cache_checked_before_reusing_pass(self):
        self.assertEqual(run(self.root,self.plan,True)['status'],'PASS')
        self.store.tree('sample-v1').joinpath('lib.py').write_text('mutated')
        with self.assertRaisesRegex(SourceError,'STALE'):run(self.root,self.plan,True)

    def test_cache_edit_during_command_blocks_result(self):
        self.plan['tasks'][0]['argv']=['{python}','-c',
           'from pathlib import Path;Path(".seed-local/oss/sources/sample-v1/tree/lib.py").write_text("mutated")']
        result=run(self.root,self.plan,True)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['tasks']['one']['reason'],'EXTERNAL_SOURCE_CHANGED_DURING_TASK')

    def test_source_excluded_from_retrieval_but_manifest_is_execution_input(self):
        self.assertFalse(any('.seed-local/oss' in path for path in source_files(self.root)))
        before=integrity_fingerprint(self.root)
        self.store.tree('sample-v1').joinpath('lib.py').write_text('mutated')
        self.assertEqual(before,integrity_fingerprint(self.root)) # explicit binding is the missing boundary
        manifest=self.root/'.seed/external-sources.lock.json';manifest.write_text(manifest.read_text()+'\n')
        self.assertNotEqual(before,integrity_fingerprint(self.root))

    def test_task_requires_reviewed_mapping_when_requested(self):
        self.plan['external_sources'][0]['require_reviewed_mapping']=True
        with self.assertRaises(SourceError):run(self.root,self.plan,True)
        self.assertFalse((self.root/'.seed-local/task-state.json').exists())

    def test_duplicate_binding_is_rejected(self):
        self.plan['external_sources']*=2
        with self.assertRaises(SourceError):run(self.root,self.plan,True)

    def test_ordinary_task_does_not_require_external_sources(self):
        self.plan.pop('external_sources')
        self.assertEqual(run(self.root,self.plan,True)['status'],'PASS')

    def test_hidden_git_metadata_cannot_be_read(self):
        git=self.store.tree('sample-v1')/'.git';git.mkdir();(git/'config').write_text('Synthetic private config')
        with self.assertRaises(SourceError):self.store.read('sample-v1','.git/config')


class ArchiveBoundaryTests(unittest.TestCase):
    def test_unsafe_tar_entries_rejected(self):
        for name,type in [('../escape',tarfile.REGTYPE),('link',tarfile.SYMTYPE),('hard',tarfile.LNKTYPE),('fifo',tarfile.FIFOTYPE)]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temp:
                buffer=io.BytesIO()
                with tarfile.open(fileobj=buffer,mode='w') as archive:
                    info=tarfile.TarInfo(name);info.type=type;info.linkname='/etc/passwd';info.size=0;archive.addfile(info)
                with self.assertRaises((SourceError,ValueError)):unpack_git_archive(buffer.getvalue(),Path(temp)/'tree')

    def test_archive_extraction_supports_regular_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            buffer=io.BytesIO()
            with tarfile.open(fileobj=buffer,mode='w') as archive:
                info=tarfile.TarInfo('src/lib.py');data=b'x=1';info.size=len(data);archive.addfile(info,io.BytesIO(data))
            out=Path(temp)/'tree';unpack_git_archive(buffer.getvalue(),out)
            self.assertEqual((out/'src/lib.py').read_bytes(),b'x=1')

    def test_restore_preserves_manifest_and_never_overwrites(self):
        if not shutil.which('git'):self.skipTest('git needed')
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp).resolve();root=base/'project';root.mkdir();up=base/'upstream';up.mkdir()
            (up/'LICENSE').write_text('Synthetic fixture license')
            def git(*args):return subprocess.check_output(['git',*args],cwd=up,stderr=subprocess.DEVNULL,text=True).strip()
            git('init');git('add','LICENSE');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture')
            store=Sources(root);acquire_git(store,example_request(),git('rev-parse','HEAD'),local_repo=up,write=True)
            before=(root/'.seed/external-sources.lock.json').read_bytes()
            with self.assertRaises(SourceError):restore_source(store,'sample-v1',local_repo=up,write=True)
            shutil.rmtree(store.tree('sample-v1').parent)
            result=restore_source(store,'sample-v1',local_repo=up,write=True)
            self.assertEqual(result['status'],'RESTORED');self.assertEqual((root/'.seed/external-sources.lock.json').read_bytes(),before)
            self.assertEqual(store.get('sample-v1')['identity']['kind'],'git-commit')

if __name__=='__main__':unittest.main()
