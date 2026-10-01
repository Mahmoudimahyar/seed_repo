from pathlib import Path
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.governance import validate,preflight
ROOT=Path(__file__).resolve().parents[2]

class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.workflow=json.loads((ROOT/'examples/governance/workflow.json').read_text())
        self.request=json.loads((ROOT/'examples/governance/request.json').read_text())
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for relative in [self.workflow['data_manifest'], *self.workflow['evaluation_refs'], self.workflow['recovery']['rollback_reference']]:
            target=self.root/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/relative,target)
        (self.root/'docs').mkdir(exist_ok=True);(self.root/'docs/README.md').write_text('local evidence')
    def test_workflow_valid(self):self.assertEqual(validate('workflow',self.workflow),[])
    def test_missing_owner_fails(self):
        del self.workflow['human_owner'];self.assertTrue(validate('workflow',self.workflow))
    def test_unknown_fields_fail(self):
        self.workflow['magic']=True;self.assertTrue(validate('workflow',self.workflow))
    def test_empty_contract_fails(self):self.assertTrue(validate('workflow',{}))
    def test_placeholder_fails(self):
        self.workflow['human_owner']='__FILL__';self.assertTrue(validate('workflow',self.workflow))
    def test_valid_read_allowed(self):self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'ALLOW')
    def test_readonly_cannot_write(self):
        self.request['mutates']=True;self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')
    def test_action_not_in_envelope(self):
        self.request['action']='deploy';self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')
    def test_host_not_in_envelope(self):
        self.request['hosts']=['example.org'];self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')
    def test_traversal_fails(self):
        self.request['paths']=['docs/../private/secrets'];self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')
    def test_secret_fails_even_under_allowed_glob(self):
        self.request['paths']=['docs/.env'];self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')
    def test_exhausted_call_budget(self):
        self.request['calls_used']=100;self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')
    def test_exhausted_time_budget(self):
        self.request['elapsed_seconds']=601;self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')
    def test_cost_forecast_exceeds_budget(self):
        self.request['projected_cost_usd']=0.01;self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')
    def test_emergency_stop_needs_no_reason(self):
        (self.root/'.seed-local').mkdir();(self.root/'.seed-local/STOP').touch()
        self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'STOPPED')
    def test_approval_required_without_approval_blocks(self):
        self.workflow['autonomy']='approval_required';self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')
    def test_no_universal_approval_boolean(self):
        self.request['approval']=True;self.assertTrue(validate('action-request',self.request))
    def test_approval_requires_exact_request_hash(self):
        self.workflow['autonomy']='approval_required'
        self.request['approval']={'by':'human','request_sha256':'0'*64,'expires_at':'2099-01-01T00:00:00Z','evidence_path':'docs/README.md'}
        self.assertEqual(preflight(self.root,self.workflow,self.request)['status'],'BLOCKED')
    def test_decision_empty_invalid(self):self.assertTrue(validate('decision',{}))
    def test_schema_name_not_path(self):
        with self.assertRaises(ValueError):validate('../outside',{})
