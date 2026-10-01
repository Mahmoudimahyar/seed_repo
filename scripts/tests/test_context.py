from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.context import Context,build

class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.ctx=Context(self.root)
        self.write('README.md','# Demo\n\n[API](src/api.py)\n\n## Login\nLogin authenticates a user.\n')
        self.write('src/api.py','def login(user):\n    return user\n\nclass Account:\n    def reset(self):\n        pass\n')
        self.write('tests/test_api.py','def test_login():\n    assert True\n')
    def write(self,p,text):
        dest=self.root/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
    def test_missing_index_is_blocked(self):
        with self.assertRaisesRegex(ValueError,'NO_INDEX'):self.ctx.status()
    def test_build_and_query_python_symbol(self):
        report=build(self.root);self.assertEqual(report['files'],3)
        result=self.ctx.symbol('login');self.assertEqual(result['items'][0]['start'],1)
        self.assertEqual(self.ctx.symbol('reset')['items'][0]['name'],'Account.reset')
    def test_exact_file_has_graph_link(self):
        build(self.root);links=self.ctx.related('README.md')['edges']
        self.assertTrue(any(e['dst']=='src/api.py' and e['kind']=='references' for e in links))
    def test_declared_tests_are_not_coverage_claim(self):
        self.write('.seed/context-links.json',json.dumps([{'source':'tests/test_api.py','target':'src/api.py','relation':'tests'}]))
        build(self.root)
        self.assertTrue(any(e['provenance']=='user-declared-not-proven-coverage' for e in self.ctx.related('src/api.py')['edges']))
    def test_section_to_exact_symbol_mapping(self):
        self.write('.seed/context-links.json',json.dumps([{'source':'README.md#section:Login','target':'src/api.py#symbol:login','relation':'documents'}]))
        build(self.root)
        symbol=self.ctx.symbol('login')['items'][0]['id']
        self.assertTrue(any(e['kind']=='documents' for e in self.ctx.related(symbol)['edges']))
    def test_unknown_symbol_reference_is_rejected(self):
        self.write('.seed/context-links.json',json.dumps([{'source':'README.md','target':'src/api.py#symbol:absent','relation':'documents'}]))
        with self.assertRaises(ValueError):build(self.root)
    def test_secret_files_not_read(self):
        self.write('.env','API_KEY=secret');self.write('private/note.md','private secret')
        self.write('credentials-demo.json','{"secret":true}')
        build(self.root)
        for p in ('.env','private/note.md','credentials-demo.json'):
            with self.assertRaises(ValueError):self.ctx.read(p)
    def test_secret_pattern_in_normal_file_excluded(self):
        self.write('docs/leak.md','ghp_'+'a'*40);build(self.root)
        with self.assertRaises(ValueError):self.ctx.read('docs/leak.md')
    def test_stale_file_is_not_returned(self):
        build(self.root);self.write('src/api.py','def changed():\n    pass\n')
        self.assertEqual(self.ctx.status()['status'],'STALE')
        with self.assertRaisesRegex(ValueError,'STALE_INDEX'):self.ctx.search('login')
        build(self.root);self.assertFalse(self.ctx.symbol('login')['items'])
    def test_new_file_marks_stale(self):
        build(self.root);self.write('new.py','x=1');self.assertEqual(self.ctx.status()['status'],'STALE')
    def test_removed_file_is_removed_on_rebuild(self):
        build(self.root);(self.root/'src/api.py').unlink();r=build(self.root)
        self.assertEqual(r['removed_files'],1);self.assertFalse(self.ctx.symbol('login')['items'])
    def test_traversal_refused(self):
        build(self.root)
        with self.assertRaises(ValueError):self.ctx.read('../outside')
    def test_limits_refuse_oversized_or_wrong_type(self):
        build(self.root)
        for value in (0,21,True,'6'):
            with self.assertRaises(ValueError):self.ctx.search('login',value)
        with self.assertRaises(ValueError):self.ctx.related('README.md',3)
    def test_query_budget(self):
        build(self.root);self.assertLessEqual(self.ctx.search('login',max_chars=500)['returned_chars'],500)
    def test_wrong_name_empty_not_hallucinated(self):
        build(self.root);self.assertEqual(self.ctx.symbol('absent')['items'],[])
    def test_generic_languages_text_not_fake_ast(self):
        self.write('src/ui.ts','export function render() { return 1; }');build(self.root)
        self.assertFalse(self.ctx.symbol('render')['items']);self.assertTrue(self.ctx.search('render')['items'])
    def test_syntax_error_still_has_chunks(self):
        self.write('bad.py','def broken(');build(self.root);self.assertTrue(self.ctx.search('broken')['items'])
    def test_explicit_exclusions(self):
        self.write('.seed/context-ignore.txt','tests/**\n');build(self.root)
        with self.assertRaises(ValueError):self.ctx.read('tests/test_api.py')
    def test_bad_declared_link_rejects_transaction(self):
        build(self.root);self.write('.seed/context-links.json',json.dumps([{'source':'README.md','target':'absent','relation':'tests'}]))
        with self.assertRaises(ValueError):build(self.root)
    @unittest.skipUnless(os.name=='posix','POSIX symlink test')
    def test_symlink_not_indexed(self):
        (self.root/'outside.py').symlink_to(self.root/'src/api.py');build(self.root)
        with self.assertRaises(ValueError):self.ctx.read('outside.py')
    def test_source_read_provenance(self):
        build(self.root);data=self.ctx.read('src/api.py',1,2)
        self.assertIn('sha256:',data['provenance']);self.assertIn('return user',data['content'])
    def test_index_does_not_change_own_freshness(self):
        build(self.root);self.assertEqual(self.ctx.status()['status'],'FRESH');self.assertEqual(self.ctx.status()['status'],'FRESH')
