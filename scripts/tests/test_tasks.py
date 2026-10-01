from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.tasks import ordered_tasks,run

class TaskTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        (self.root/'approval.md').write_text('Synthetic test approval only, not an actual user approval.')
        self.plan={'id':'demo','owner':'test-owner','scope':'Synthetic local smoke tests','approved':True,'approval_evidence':'approval.md',
                   'allowed_edit_paths':['src/**'],'max_steps_per_run':1,'max_attempts_per_task':2,
                   'tasks':[{'id':'one','depends_on':[],'argv':['{python}','-c','print("one")'],'cwd':'.','timeout_seconds':5},
                            {'id':'two','depends_on':['one'],'argv':['{python}','-c','print("two")'],'cwd':'.','timeout_seconds':5}]}
    def test_preview_does_not_create_state(self):
        self.assertEqual(run(self.root,self.plan)['status'],'PREVIEW');self.assertFalse((self.root/'.seed-local').exists())
    def test_checkpoint_and_resume(self):
        self.assertEqual(run(self.root,self.plan,True)['status'],'CHECKPOINT')
        state=run(self.root,self.plan,True);self.assertEqual(state['status'],'PASS');self.assertEqual(state['tasks']['one']['attempts'],1)
    def test_modified_plan_not_silently_resumed(self):
        run(self.root,self.plan,True);self.plan['scope']='Different approved scope'
        with self.assertRaisesRegex(ValueError,'Plan changed'):run(self.root,self.plan,True)
    def test_modified_source_requires_review(self):
        run(self.root,self.plan,True);(self.root/'new.py').write_text('x=1')
        with self.assertRaisesRegex(ValueError,'Source changed'):run(self.root,self.plan,True)
    def test_unapproved_plan_blocks(self):
        self.plan['approved']=False
        with self.assertRaises(ValueError):run(self.root,self.plan,True)
    def test_cycle_blocks(self):
        self.plan['tasks'][0]['depends_on']=['two']
        with self.assertRaises(ValueError):ordered_tasks(self.plan)
    def test_unknown_dependency_blocks(self):
        self.plan['tasks'][0]['depends_on']=['unknown']
        with self.assertRaises(ValueError):ordered_tasks(self.plan)
    def test_failure_prevents_dependent(self):
        self.plan['tasks'][0]['argv']=['{python}','-c','raise SystemExit(1)']
        result=run(self.root,self.plan,True);self.assertEqual(result['status'],'FAIL');self.assertNotIn('two',result['tasks'])
    def test_repair_budget_stops_repeating(self):
        self.plan['tasks'][0]['argv']=['{python}','-c','raise SystemExit(1)']
        run(self.root,self.plan,True);run(self.root,self.plan,True)
        self.assertEqual(run(self.root,self.plan,True)['status'],'BLOCKED')
    def test_lease_prevents_second_writer(self):
        (self.root/'.seed-local').mkdir();(self.root/'.seed-local/task-run.lock').write_text('{}')
        with self.assertRaises(ValueError):run(self.root,self.plan,True)
    def test_emergency_stop(self):
        (self.root/'.seed-local').mkdir();(self.root/'.seed-local/STOP').touch()
        self.assertEqual(run(self.root,self.plan,True)['status'],'STOPPED')
    def test_unexpected_source_edits_fail_after_execution(self):
        self.plan['tasks'][0]['argv']=['{python}','-c','from pathlib import Path; Path("outside.py").write_text("x=1")']
        r=run(self.root,self.plan,True);self.assertEqual(r['tasks']['one']['reason'],'OUT_OF_SCOPE_EDITS')
        self.assertTrue((self.root/'outside.py').exists()) # detection is not a sandbox; never claim prevention
    def test_missing_approval_evidence_blocks(self):
        (self.root/'approval.md').unlink()
        with self.assertRaises(ValueError):run(self.root,self.plan,True)
    def test_duplicate_id_blocks(self):
        self.plan['tasks'][1]['id']='one'
        with self.assertRaises(ValueError):ordered_tasks(self.plan)
