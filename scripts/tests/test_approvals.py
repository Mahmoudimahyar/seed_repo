"""Readiness must describe the exact reviewed scope, not only boolean checkboxes."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_seed as fixture
from seedlib import approvals
from seedlib.common import dump, sha


class ApprovalBindingTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.StarterTests('runTest'); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.fixture.initialize()
        self.record=self.fixture.approve_recorded_fixture()

    def ready(self): return fixture.seed.ready(self.root)
    def save(self): self.fixture.write('docs/project/readiness.json',dump(self.record))

    def test_approved_revision_passes(self): self.assertEqual(self.ready(),[])

    def test_spec_change_revokes_recorded_readiness(self):
        self.fixture.write('docs/project/prd.md','A materially changed specification with a hosted API instead of a local parser.')
        self.assertTrue(any('binding' in i.lower() for i in self.ready()))

    def test_scope_change_invalidates(self):
        self.record['scope']='Ship another application scope with different intended user behavior.';self.save()
        self.assertTrue(self.ready())

    def test_capability_change_invalidates(self):
        state=fixture.seed.load_state(self.root);state['capabilities']['ui']=True
        self.fixture.write('seed.json',dump(state));self.assertTrue(self.ready())

    def test_unrelated_notes_do_not_invalidate_scope(self):
        self.fixture.write('other-notes.md','This is unrelated to any approved evidence or decision.')
        self.assertEqual(self.ready(),[])

    def test_approval_evidence_change_is_detected(self):
        self.fixture.write('docs/project/approval.md','Altered proof with no real user approval despite earlier recorded acceptance.')
        self.assertTrue(self.ready())

    def test_binding_recomputed_without_new_evidence_does_not_pass(self):
        self.fixture.write('docs/project/prd.md','Different proposed behavior requires separate user acceptance and data permission.')
        proposal=approvals.propose(self.root,self.record,fixture.seed.load_state(self.root))
        self.record['approval']['binding']=proposal;self.save()
        self.assertTrue(self.ready())

    def test_cannot_record_against_stale_proposal(self):
        old=self.record['approval']['binding']
        self.fixture.write('docs/project/prd.md','A changed request with another runtime and external system requirement.')
        with self.assertRaises(ValueError):
            approvals.record(self.root,self.record,fixture.seed.load_state(self.root),'maintainer','docs/project/approval.md',old)

    def test_record_preview_does_not_change_files(self):
        before=(self.root/'docs/project/readiness.json').read_bytes()
        proposal=approvals.propose(self.root,self.record,fixture.seed.load_state(self.root))
        result=approvals.record(self.root,self.record,fixture.seed.load_state(self.root),'synthetic-test-approver','docs/project/approval.md',proposal)
        self.assertTrue(result['approval']['approved']);self.assertEqual(before,(self.root/'docs/project/readiness.json').read_bytes())

    def test_old_schema_requires_explicit_migration_and_reapproval(self):
        self.record['schema_version']=1;self.save();self.assertTrue(self.ready())
        migrated=approvals.migrate(self.record)
        self.assertEqual(migrated['schema_version'],2)
        self.assertFalse(migrated['approval']['approved'])
        self.assertIsNone(migrated['approval']['binding'])

    def test_malformed_approval_fails_closed(self):
        self.record['approval'] = None; self.save()
        self.assertTrue(self.ready())

    def test_missing_binding_fails(self):
        self.record['approval'].pop('binding');self.save();self.assertTrue(self.ready())

    def test_approval_cannot_be_its_own_gate_evidence(self):
        self.record['gates'][0]['evidence']=['docs/project/approval.md'];self.save()
        self.assertTrue(self.ready())

    def test_missing_referenced_planning_store_blocks(self):
        self.record['planning']=[{'map_id':'nonexistent','requirements':[{'ticket_id':'privacy','allowed_outcomes':['accepted']}]}]
        self.save();self.assertTrue(self.ready())

    def test_malformed_planning_references_fail_closed(self):
        self.record['planning']='wrong';self.save();self.assertTrue(self.ready())

    def test_private_approval_file_is_not_hashed_or_echoed(self):
        self.fixture.write('.env','private-do-not-echo')
        with self.assertRaises(ValueError):
            approvals.record(self.root,self.record,fixture.seed.load_state(self.root),'owner','.env',self.record['approval']['binding'])

    def test_missing_gate_or_blocker_cannot_be_silently_sealed(self):
        self.record['blocking_gaps']=['Unresolved privacy'];self.save()
        self.assertTrue(self.ready())

if __name__=='__main__':unittest.main()
