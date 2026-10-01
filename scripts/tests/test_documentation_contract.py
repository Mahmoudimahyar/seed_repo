"""Small source-linked documentation checks, not a semantic truth oracle."""
import ast
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from check_mcp import TOOLS
ROOT=Path(__file__).resolve().parents[2]

class DocumentationContractTests(unittest.TestCase):
    def test_current_release_is_linked(self):
        version=(ROOT/'VERSION').read_text().strip()
        self.assertTrue((ROOT/f'docs/releases/{version}.md').is_file())
        self.assertIn(version,(ROOT/'README.md').read_text())
        self.assertIn(version,(ROOT/'docs/maintainers/publishing.md').read_text())
    def test_evaluation_entry_does_not_deny_shipped_tools(self):
        text=(ROOT/'evals/README.md').read_text()
        for name in ['run_candidate.py','seed_eval.py','ABSTAINED']:
            if name=='ABSTAINED':continue
            self.assertIn(name,text)
        self.assertNotIn('There is no\nrunner',text)
    def test_mcp_tool_list_matches_actual_server_definitions(self):
        module=ast.parse((ROOT/'scripts/seed_mcp.py').read_text())
        factory=next(node for node in module.body if isinstance(node,ast.FunctionDef) and node.name=='create_server')
        defined={node.name for node in factory.body if isinstance(node,ast.FunctionDef)}
        self.assertEqual(defined,TOOLS)
        text=(ROOT/'docs/integrations/mcp.md').read_text()
        for name in defined:self.assertIn(name,text)
        self.assertNotIn('all five tools',text)
    def test_policy_coverage_is_required_and_documented(self):
        schema=json.loads((ROOT/'schemas/promotion-policy.schema.json').read_text())
        self.assertFalse(schema['additionalProperties']);self.assertIn('min_coverage',schema['required'])
        self.assertIn('min_coverage',(ROOT/'docs/workflows/benchmarking.md').read_text())
    def test_template_checks_retain_actual_suite(self):
        checks=json.loads((ROOT/'quality/template-checks.json').read_text())['checks']
        self.assertTrue(any('unittest' in c.get('argv',[]) and 'scripts/tests' in c.get('argv',[]) for c in checks))
    def test_export_policy_lists_itself_and_forbids_client_config(self):
        files=json.loads((ROOT/'quality/export-policy.json').read_text())['files']
        self.assertIn('quality/export-policy.json',files)
        self.assertFalse(any(name.startswith('.codex/') or name=='.mcp.json' for name in files))
