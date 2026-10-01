from pathlib import Path
import json
import os
import sys
import shutil
import subprocess
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.common import dump
from seedlib.context import Context, build
from seedlib.file_policy import integrity_files, integrity_fingerprint
from check_mcp import fixture, TOOLS

class RetrievalIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
    def write(self,path,text):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')

    def test_semantic_mcp_fixture_has_real_evidence(self):
        fixture(self.root);ctx=Context(self.root)
        self.assertEqual(len(TOOLS),6)
        symbol=ctx.symbol('login')['items'][0]
        self.assertEqual((symbol['path'],symbol['start']),('src/api.py',1))
        self.assertTrue(any(e['kind']=='documents' for e in ctx.related(symbol['id'])['edges']))
        self.assertTrue(any(e['kind']=='tests' for e in ctx.related('src/api.py')['edges']))
        self.assertTrue(any('CONTRACT_MARKER' in e['excerpt'] for e in ctx.search('CONTRACT_MARKER')['items']))
        self.assertEqual(ctx.read('src/api.py',1,2)['content'],'def login(user):\n    return user\n')

    def test_escaped_unicode_pages_reconstruct_exact_source(self):
        text=json.dumps({'x':'\"\\\t漢字'*600},ensure_ascii=False)+'\n'
        self.write('big.json',text);build(self.root);ctx=Context(self.root)
        args={'path':'big.json','start':1,'end':1,'max_chars':2000};pieces=[];last=0
        for _ in range(100):
            page=ctx.read(**args)
            self.assertLessEqual(len(dump(page)),2000)
            self.assertEqual(page['content_offset_chars'],last)
            pieces.append(page['content']);last+=len(page['content'])
            if not page['continuation']:break
            args=page['continuation']
        self.assertIsNone(page['continuation'])
        self.assertEqual(''.join(pieces),text)

    def test_changed_source_rejects_old_continuation_after_reindex(self):
        self.write('large.json','x'*5000);build(self.root);ctx=Context(self.root)
        continuation=ctx.read('large.json',1,1,max_chars=2000)['continuation']
        self.write('large.json','y'*5000);build(self.root)
        with self.assertRaisesRegex(ValueError,'STALE_SOURCE'):ctx.read(**continuation)

    def test_search_and_relation_json_budgets_hold(self):
        fixture(self.root);ctx=Context(self.root)
        for budget in [500,1000,2000,12000]:
            for result in [ctx.search('login',max_chars=budget),ctx.related('src/api.py',max_chars=budget),ctx.symbol('login',max_chars=budget)]:
                self.assertLessEqual(len(dump(result)),budget)

    def test_mirrors_are_not_duplicate_context(self):
        self.write('.agents/skills/example/SKILL.md','# Example\nCanonical specialskilltoken instructions.\n')
        self.write('.claude/skills/example/SKILL.md','# Example\nCanonical specialskilltoken instructions.\n')
        build(self.root);items=Context(self.root).search('specialskilltoken')['items']
        self.assertTrue(items)
        self.assertTrue(all(not row['path'].startswith('.claude/skills/') for row in items))

    def test_integrity_includes_private_large_binary_lock_and_excluded_inputs(self):
        self.write('.seed/context-ignore.txt','evals/**\nrequirements.txt\n')
        for name,value in [('requirements.txt','dependency==1'),('package-lock.json','{}'),('.env','SYNTHETIC_LOCAL=not-a-real-secret'),('evals/data.json','[]')]:self.write(name,value)
        (self.root/'large.bin').write_bytes(b'\0'*2_000_000)
        hashes=integrity_files(self.root)
        for name in ['requirements.txt','package-lock.json','.env','evals/data.json','large.bin']:self.assertIn(name,hashes)
        self.assertNotIn('not-a-real-secret',dump(hashes))
        before=integrity_fingerprint(self.root);self.write('.env','SYNTHETIC_LOCAL=changed')
        self.assertNotEqual(before,integrity_fingerprint(self.root))

    def test_runtime_logs_do_not_stale_integrity(self):
        self.write('src/main.py','print(1)');before=integrity_fingerprint(self.root)
        self.write('.seed-local/private-log.json','{}');self.write('.seed-ci-artifacts/report.json','{}')
        self.assertEqual(before,integrity_fingerprint(self.root))

    @unittest.skipUnless(os.name=='posix','POSIX executable-bit evidence')
    def test_executable_mode_change_is_an_integrity_change(self):
        self.write('program.sh','echo example');before=integrity_fingerprint(self.root)
        (self.root/'program.sh').chmod(0o755)
        self.assertNotEqual(before,integrity_fingerprint(self.root))

    @unittest.skipUnless(shutil.which('git'), 'Real Git tracked-source test')
    def test_tracked_source_survives_build_folder_exclusion(self):
        self.write('src/build/config.txt','tracked relevant input')
        subprocess.run(['git','init','-q'],cwd=self.root,check=True)
        subprocess.run(['git','add','-f','src/build/config.txt'],cwd=self.root,check=True)
        before=integrity_fingerprint(self.root)
        self.assertIn('src/build/config.txt',integrity_files(self.root))
        self.write('src/build/config.txt','changed relevant input')
        self.assertNotEqual(before,integrity_fingerprint(self.root))

    @unittest.skipUnless(shutil.which('git'), 'Real Git tracked-runtime test')
    def test_tracked_runtime_evidence_is_rejected_not_self_hashed(self):
        self.write('.seed-local/task-state.json','{}')
        subprocess.run(['git','init','-q'],cwd=self.root,check=True)
        subprocess.run(['git','add','-f','.seed-local/task-state.json'],cwd=self.root,check=True)
        with self.assertRaisesRegex(ValueError,'runtime state must not be tracked'):
            integrity_fingerprint(self.root)
