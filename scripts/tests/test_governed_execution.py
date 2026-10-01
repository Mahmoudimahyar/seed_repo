"""A declared governed command must consume its actual preflight and pinned references."""
from pathlib import Path
import copy
import json
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.common import dump,sha
from seedlib.governance import preflight,references
from seedlib.tasks import run,ordered_tasks

ROOT=Path(__file__).resolve().parents[2]

class GovernedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.workflow=json.loads((ROOT/'examples/governance/workflow.json').read_text())
        self.request=json.loads((ROOT/'examples/governance/request.json').read_text())
        for ref in [self.workflow['data_manifest'],*self.workflow['evaluation_refs'],self.workflow['recovery']['rollback_reference']]:
            target=self.root/ref;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/ref,target)
        (self.root/'docs/README.md').write_text('Synthetic input evidence for a local test only.')
        (self.root/'approval.md').write_text('Synthetic local approval fixture, never an authenticated user approval.')
        self.plan={'id':'governed','owner':'fixture','scope':'Synthetic governed command tests','approved':True,'approval_evidence':'approval.md',
                   'allowed_edit_paths':['src/**','docs/**'],'max_steps_per_run':2,'max_attempts_per_task':2,'require_governance':True,
                   'tasks':[{'id':'one','depends_on':[],'argv':['{python}','-c','print("read")'],'cwd':'.','timeout_seconds':3}]}
        self.bind()

    def bind(self):
        (self.root/'workflow.json').write_text(dump(self.workflow))
        for task in self.plan['tasks']:
            request=copy.deepcopy(self.request)
            request['execution_sha256']=sha(dump({'argv':task['argv'],'cwd':task['cwd']}).encode())
            task['governance']={'workflow':'workflow.json','workflow_sha256':sha((self.root/'workflow.json').read_bytes()),
                                'reference_sha256':references(self.root,self.workflow),'request':request}

    def test_valid_governed_command_has_preflight_evidence(self):
        report=run(self.root,self.plan,True)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['tasks']['one']['governance']['status'],'ALLOW')
        self.assertEqual(report['governance_usage'][self.workflow['id']]['calls_used'],1)

    def test_missing_manifest_blocks_standalone_preflight(self):
        (self.root/self.workflow['data_manifest']).unlink()
        self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')

    def test_missing_evaluation_reference_blocks(self):
        (self.root/self.workflow['evaluation_refs'][0]).unlink()
        self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')

    def test_missing_recovery_reference_blocks(self):
        (self.root/self.workflow['recovery']['rollback_reference']).unlink()
        self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')

    def test_mismatched_data_workflow_identity_blocks(self):
        path=self.root/self.workflow['data_manifest'];data=json.loads(path.read_text());data['workflow_id']='wrong';path.write_text(dump(data))
        self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')

    def test_stale_manifest_blocks_execution_before_command(self):
        path=self.root/self.workflow['data_manifest'];path.write_text(path.read_text()+'\n')
        result=run(self.root,self.plan,True)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['tasks']['one']['attempts'],0)
        self.assertFalse((self.root/'.seed-local/task-logs/one.log').exists())

    def test_changed_workflow_blocks_execution(self):
        (self.root/'workflow.json').write_text(dump(self.workflow)+'\n')
        self.assertEqual(run(self.root,self.plan,True)['status'],'BLOCKED')

    def test_incomplete_pin_set_blocks(self):
        self.plan['tasks'][0]['governance']['reference_sha256'].pop(self.workflow['evaluation_refs'][0])
        self.assertEqual(run(self.root,self.plan,True)['status'],'BLOCKED')

    def test_preflight_denial_prevents_governed_command(self):
        self.plan['tasks'][0]['argv']=['{python}','-c','from pathlib import Path; Path("should-not-exist").touch()']
        self.bind();self.plan['tasks'][0]['governance']['request']['action']='deploy'
        self.assertEqual(run(self.root,self.plan,True)['status'],'BLOCKED')
        self.assertFalse((self.root/'should-not-exist').exists())

    def test_command_cannot_change_after_request_binding(self):
        self.plan['tasks'][0]['argv']=['{python}','-c','print("changed command")']
        self.assertEqual(run(self.root,self.plan,True)['status'],'BLOCKED')

    def test_require_governance_cannot_omit_binding(self):
        self.plan['tasks'][0].pop('governance')
        with self.assertRaises(ValueError):ordered_tasks(self.plan)

    def test_ungoverned_task_is_explicitly_not_certified(self):
        self.plan['require_governance']=False;self.plan['tasks'][0].pop('governance')
        report=run(self.root,self.plan,True)
        self.assertEqual(report['tasks']['one']['governance']['status'],'NOT_CONFIGURED')

    def test_budget_counts_previous_calls(self):
        self.workflow['budgets']['max_calls']=1
        self.plan['tasks'].append({'id':'two','depends_on':['one'],'argv':['{python}','-c','print("second")'],'cwd':'.','timeout_seconds':3})
        self.bind()
        report=run(self.root,self.plan,True)
        self.assertEqual(report['tasks']['one']['status'],'PASS')
        self.assertEqual(report['tasks']['two']['status'],'BLOCKED')
        self.assertEqual(report['tasks']['two']['attempts'],0)

    def test_nonexistent_purpose_contract_blocks(self):
        self.workflow['purpose_ref']='docs/purpose.json'
        self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')

    def test_unknown_reference_is_not_partial_success(self):
        self.workflow['evaluation_refs'].append('missing-eval.json')
        with self.assertRaises(ValueError):references(self.root,self.workflow)
