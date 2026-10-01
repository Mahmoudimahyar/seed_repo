from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('seed', ROOT / 'scripts/seed.py')
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)
cispec = importlib.util.spec_from_file_location('ci_portable', ROOT / 'scripts/seed_ci.py')
ci = importlib.util.module_from_spec(cispec)
cispec.loader.exec_module(ci)


class StarterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        # Independent fixture: also works when tests run in an initialized downstream repo.
        for dirname in ('templates', '.agents', '.claude', '.seed'):
            shutil.copytree(ROOT / dirname, self.root / dirname)
        (self.root / 'quality').mkdir()
        for filename in ('template-checks.json','application-checks.example.json'):
            shutil.copyfile(ROOT/'quality'/filename, self.root/'quality'/filename)
        shutil.copyfile(self.root/'quality/template-checks.json', self.root/'quality/seed-checks.json')
        self.write('seed.json', seed.json_text({
            'schema_version':1,'distribution_version':'0.1.0-rc.1','kind':'template',
            'project':None,'phase':'discovery', 'capabilities':self.caps(),
            'retrieval':{'status':'not_configured','provider':None},
        }))
        for name in seed.REQUIRED:
            path = self.root / name
            if not path.exists():
                self.write(name, '# Example fixture\n\nA minimally populated fixture document.\n')

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def caps(self, **kwargs):
        return {key:kwargs.get(key,False) for key in seed.CAPABILITIES}

    def initialize(self, **caps):
        plan = seed.init_plan(self.root,'sample-tool','cli',self.caps(**caps))
        seed.write_plan(self.root, plan, {'seed.json','quality/seed-checks.json'})
        return plan

    def approve_recorded_fixture(self):
        record = seed.read_json(self.root,'docs/project/readiness.json')
        record['scope'] = 'Build a narrowly scoped CLI, using the approved fixture specification.'
        record['blocking_gaps'] = []
        for gate in record['gates']:
            gate['status'] = 'satisfied'
            for ref in gate['evidence']:
                if ref == 'docs/project/features.json':
                    continue
                self.write(ref, '# Specification fixture\n\nObserved expected behavior and independent test plan are documented.\n')
        self.write('docs/project/approval.md', '# Approval fixture\n\nThis is a synthetic test fixture, not an actual human approval.\n')
        from seedlib import approvals
        proposal = approvals.propose(self.root, record, seed.load_state(self.root))
        self.write('docs/project/approval.md', '# Synthetic approval fixture\n\nNot a real authorization. The fixture approves fingerprint: ' + proposal['sha256'] + '\n')
        record = approvals.record(self.root, record, seed.load_state(self.root),
                                  'synthetic-test-approver','docs/project/approval.md',proposal)
        self.write('docs/project/readiness.json',seed.json_text(record))
        return record

    def test_doctor_is_offline_summary_not_connectivity_claim(self):
        self.write('.env','secret content must not be needed')
        before = (self.root/'.env').read_bytes()
        value = seed.doctor(self.root)
        self.assertEqual(value['kind'],'template')
        self.assertIn('NOT_VERIFIED',value['mcp_connectivity'])
        self.assertEqual(before,(self.root/'.env').read_bytes())

    def test_mcp_config_presence_is_not_verification(self):
        self.write('.mcp.json','{"mcpServers": {}}')
        value = seed.doctor(self.root)
        self.assertTrue(value['mcp_config_present'])
        self.assertIn('NOT_VERIFIED',value['mcp_connectivity'])

    def test_init_plan_does_not_write(self):
        plan = seed.init_plan(self.root,'sample-tool','cli',self.caps())
        self.assertIn('docs/project/prd.md',plan)
        self.assertFalse((self.root/'docs/project/prd.md').exists())
        self.assertEqual(seed.load_state(self.root)['kind'],'template')

    def test_cli_omits_unrequested_capabilities(self):
        plan = self.initialize()
        self.assertEqual(seed.load_state(self.root)['kind'],'project')
        for name in ('site-map','design-system','marketing','sales','ai'):
            self.assertNotIn(f'docs/project/{name}.md',plan)

    def test_capabilities_are_independent_opt_ins(self):
        plan = self.initialize(ui=True,ai=True)
        self.assertIn('docs/project/site-map.md',plan)
        self.assertIn('docs/project/ai.md',plan)
        self.assertNotIn('docs/project/marketing.md',plan)
        self.assertNotIn('docs/project/sales.md',plan)

    def test_marketing_and_sales_are_not_inferred_from_product_mode(self):
        plan = seed.init_plan(self.root,'sample-product','product',self.caps())
        self.assertNotIn('docs/project/marketing.md',plan)
        self.assertNotIn('docs/project/sales.md',plan)

    def test_marketing_sales_only_when_requested(self):
        plan = self.initialize(marketing=True,sales=True)
        self.assertIn('docs/project/marketing.md',plan)
        self.assertIn('docs/project/sales.md',plan)
        self.assertNotIn('docs/project/site-map.md',plan)

    def test_application_commands_are_unconfigured_after_init(self):
        self.initialize()
        config = seed.read_json(self.root,'quality/seed-checks.json')
        self.assertTrue(all(c['argv'] is None for c in config['checks']))
        result, evidence = ci.run_checks(self.root,'quality/seed-checks.json')
        self.assertEqual(result,2)
        self.assertEqual(evidence['status'],'BLOCKED')

    def test_template_check_configuration_is_preserved(self):
        previous = (self.root/'quality/seed-checks.json').read_text()
        self.initialize()
        self.assertEqual(previous,(self.root/'quality/template-checks.json').read_text())

    def test_second_init_is_refused(self):
        self.initialize()
        with self.assertRaisesRegex(ValueError,'Already initialized'):
            self.initialize()

    def test_existing_document_is_not_overwritten(self):
        self.write('docs/project/prd.md','User-authored content')
        before = (self.root/'seed.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'Refusing to overwrite'):
            self.initialize()
        self.assertEqual((self.root/'docs/project/prd.md').read_text(),'User-authored content')
        self.assertEqual(before,(self.root/'seed.json').read_bytes())

    def test_custom_ci_is_not_overwritten(self):
        self.write('quality/seed-checks.json','{"custom":true}')
        with self.assertRaisesRegex(ValueError,'customized'):
            self.initialize()

    def test_invalid_names_and_modes_are_refused(self):
        for name,mode in [('../escape','cli'),('Bad Name','cli'),('a'*64,'cli'),('good','unknown')]:
            with self.subTest(name=name,mode=mode), self.assertRaises(ValueError):
                seed.init_plan(self.root,name,mode,self.caps())

    def test_nonboolean_capabilities_are_refused(self):
        with self.assertRaises(ValueError):
            seed.init_plan(self.root,'good','cli',self.caps(ui='yes'))

    def test_path_escape_refused(self):
        for value in ('../outside',str(self.root.parent/'outside')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                seed.safe_path(self.root,value)

    @unittest.skipUnless(os.name == 'posix','POSIX symlink fixture')
    def test_symlink_parent_refused_before_initialization(self):
        with tempfile.TemporaryDirectory() as outside:
            shutil.rmtree(self.root/'docs')
            (self.root/'docs').symlink_to(outside,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Symlink'):
                self.initialize()
            self.assertEqual(list(Path(outside).iterdir()),[])

    def test_write_plan_checks_all_known_conflicts_before_writing(self):
        self.write('occupied.md','keep')
        with self.assertRaises(ValueError):
            seed.write_plan(self.root,{'new.md':'new','occupied.md':'replace'},set())
        self.assertFalse((self.root/'new.md').exists())
        self.assertEqual((self.root/'occupied.md').read_text(),'keep')

    def test_skill_sync_is_idempotent(self):
        plan = seed.skill_plan(self.root)
        seed.write_plan(self.root,plan,set(plan))
        self.assertEqual(plan,seed.skill_plan(self.root))

    def test_skill_source_update_refreshes_known_mirror(self):
        path = self.root/'.agents/skills/seed-debug/SKILL.md'
        path.write_text(path.read_text()+'\nA new source rule.\n')
        plan = seed.skill_plan(self.root)
        self.assertIn('A new source rule.',plan['.claude/skills/seed-debug/SKILL.md'])

    def test_manual_mirror_edit_is_preserved(self):
        path = self.root/'.claude/skills/seed-debug/SKILL.md'
        path.write_text(path.read_text()+'\nA local deliberate edit.\n')
        with self.assertRaisesRegex(ValueError,'Manually changed'):
            seed.skill_plan(self.root)
        self.assertIn('local deliberate edit',path.read_text())

    def test_template_not_ready_for_app_build(self):
        self.assertTrue(seed.ready(self.root))

    def test_new_project_blocked_until_actual_recorded_approval(self):
        self.initialize()
        issues = seed.ready(self.root)
        self.assertTrue(any('approval' in x for x in issues))
        self.assertTrue(any('Blocking gaps' in x for x in issues))

    def test_recorded_readiness_fixture_passes(self):
        self.initialize()
        self.approve_recorded_fixture()
        self.assertEqual(seed.ready(self.root),[])

    def test_missing_gate_is_not_ready(self):
        self.initialize()
        record = self.approve_recorded_fixture()
        record['gates'] = record['gates'][1:]
        self.write('docs/project/readiness.json',seed.json_text(record))
        self.assertTrue(any('absent' in x for x in seed.ready(self.root)))

    def test_duplicate_gate_is_not_ready(self):
        self.initialize()
        record = self.approve_recorded_fixture()
        record['gates'].append(record['gates'][0])
        self.write('docs/project/readiness.json',seed.json_text(record))
        self.assertTrue(any('Duplicate' in x for x in seed.ready(self.root)))

    def test_placeholder_evidence_is_not_ready(self):
        self.initialize()
        self.approve_recorded_fixture()
        self.write('docs/project/prd.md','# Long unfilled specification\n\n__FILL__ must be resolved before approval.')
        self.assertTrue(any('Unfilled' in x for x in seed.ready(self.root)))

    def test_missing_approval_evidence_is_not_ready(self):
        self.initialize()
        self.approve_recorded_fixture()
        (self.root/'docs/project/approval.md').unlink()
        self.assertTrue(any('Approval evidence' in x for x in seed.ready(self.root)))

    def test_secret_file_cannot_be_readiness_evidence(self):
        self.initialize()
        record = self.approve_recorded_fixture()
        self.write('.env','a secret file that must not be used as approval evidence')
        record['approval']['evidence'] = '.env'
        self.write('docs/project/readiness.json',seed.json_text(record))
        self.assertTrue(any('secret/local' in x for x in seed.ready(self.root)))

    def test_ui_and_ai_require_additional_gates(self):
        self.initialize(ui=True,ai=True)
        record = self.approve_recorded_fixture()
        record['gates'] = [g for g in record['gates'] if g['id'] not in {'site-map','ai'}]
        self.write('docs/project/readiness.json',seed.json_text(record))
        issues = seed.ready(self.root)
        self.assertIn('Required gate absent: site-map',issues)
        self.assertIn('Required gate absent: ai',issues)

    def test_dependency_and_gap_decisions_are_required(self):
        self.initialize()
        record = self.approve_recorded_fixture()
        record['gates'] = [g for g in record['gates'] if g['id'] not in {'dependencies','gaps'}]
        self.write('docs/project/readiness.json',seed.json_text(record))
        issues = seed.ready(self.root)
        self.assertIn('Required gate absent: dependencies',issues)
        self.assertIn('Required gate absent: gaps',issues)

    def test_requested_marketing_sales_need_recorded_scope(self):
        self.initialize(marketing=True,sales=True)
        record = self.approve_recorded_fixture()
        record['gates'] = [g for g in record['gates'] if g['id'] != 'sales']
        self.write('docs/project/readiness.json',seed.json_text(record))
        self.assertIn('Required gate absent: sales',seed.ready(self.root))

    def test_invalid_json_detected(self):
        self.write('broken.json','{')
        self.assertTrue(any('Invalid JSON: broken.json' in x for x in seed.validate(self.root)))

    def test_missing_required_file_detected(self):
        (self.root/'LICENSE').unlink()
        self.assertTrue(any('Missing required file: LICENSE' in x for x in seed.validate(self.root)))

    def test_broken_local_link_detected(self):
        self.write('README.md','[Missing](no-such-file.md)')
        self.assertTrue(any('Broken local link' in x for x in seed.validate(self.root)))

    def test_example_links_inside_code_are_ignored(self):
        self.write('README.md','```text\n[Missing](no-such-file.md)\n```\n')
        self.assertFalse(any('Broken local link: README.md' in x for x in seed.validate(self.root)))

    def test_public_check_flags_but_does_not_echo_secret_file(self):
        secret = 'do-not-print-the-secret-contents'
        self.write('.env',secret)
        issues = seed.validate(self.root,public=True)
        self.assertTrue(any('sensitive filename' in x for x in issues))
        self.assertNotIn(secret,'\n'.join(issues))
        self.assertFalse(any('sensitive filename' in x for x in seed.validate(self.root)))

    def test_obvious_token_detection_does_not_echo_token(self):
        token = 'ghp_' + 'x'*36
        self.write('leak.txt',token)
        issues = seed.validate(self.root)
        self.assertTrue(any('Possible credential' in x for x in issues))
        self.assertNotIn(token,'\n'.join(issues))

    def test_python_interpreter_placeholder_runs(self):
        self.write('checks.json',seed.json_text({'schema_version':1,'checks':[
            {'id':'python','argv':['{python}','-c','print("portable")'],'timeout_seconds':10}
        ]}))
        code, report = ci.run_checks(self.root,'checks.json')
        self.assertEqual(code,0)
        self.assertEqual(report['checks'][0]['status'],'PASS')

    def test_cli_preview_and_apply_end_to_end(self):
        shutil.copytree(ROOT/'scripts/seedlib',self.root/'scripts/seedlib')
        for name in ('seed.py','seed_ci.py'):
            path = self.root/'scripts'/name
            path.parent.mkdir(exist_ok=True)
            shutil.copyfile(ROOT/'scripts'/name,path)
        args = [sys.executable,str(self.root/'scripts/seed.py'),'init','--name','smoke-tool','--mode','cli']
        preview = subprocess.run(args,cwd=self.root,capture_output=True,text=True,timeout=15)
        self.assertEqual(preview.returncode,0,preview.stderr)
        self.assertFalse((self.root/'docs/project/prd.md').exists())
        apply = subprocess.run(args+['--write'],cwd=self.root,capture_output=True,text=True,timeout=15)
        self.assertEqual(apply.returncode,0,apply.stderr)
        self.assertTrue((self.root/'docs/project/prd.md').exists())
        ready_result = subprocess.run([sys.executable,str(self.root/'scripts/seed.py'),'ready'],cwd=self.root,capture_output=True,text=True,timeout=15)
        self.assertEqual(ready_result.returncode,2)

    def test_distribution_action_pins_match_workflow(self):
        workflow = (ROOT/'.github/workflows/seed-ci.yml').read_text()
        pins = json.loads((ROOT/'quality/action-pins.json').read_text())['actions']
        for name, reference in pins.items():
            with self.subTest(action=name):
                self.assertIn(name+'@'+reference['sha'],workflow)

    def test_distribution_workflow_has_required_safety_properties(self):
        workflow = (ROOT/'.github/workflows/seed-ci.yml').read_text()
        for expected in ('merge_group:','contents: read','persist-credentials: false','name: seed-ci-required','if: always()','needs: [checks, mcp, scope]','python scripts/check_mcp.py','MCP_RESULT: ${{ needs.mcp.result }}'):
            self.assertIn(expected,workflow)
        self.assertNotIn('pull_request_target:',workflow)
        self.assertNotIn('secrets.',workflow)


if __name__ == '__main__':
    unittest.main()
