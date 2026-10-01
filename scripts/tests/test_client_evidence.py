from pathlib import Path
import json
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.common import dump, sha
from seedlib.client_evidence import status, RECORD
ROOT=Path(__file__).resolve().parents[2]

class ClientEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.record=json.loads((ROOT/'templates/client-acceptance.json').read_text())
    def save(self):
        path=self.root/RECORD;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(dump(self.record))
    def evidence(self):
        path=self.root/'evidence.md';path.write_text('Synthetic fixture: no actual third-party client was run.\n')
        return {path.name:sha(path.read_bytes())}
    def test_missing_record_does_not_claim_connected(self):
        self.assertEqual(status(self.root)['status'],'NOT_VERIFIED')
    def test_blank_template_stays_incomplete(self):
        self.save();self.assertEqual(status(self.root)['status'],'RECORDED_INCOMPLETE')
    def test_pass_without_evidence_is_blocked(self):
        self.record['scenarios'][0]['status']='PASS';self.save();self.assertEqual(status(self.root)['status'],'BLOCKED')
    def test_pass_with_evidence_is_recorded_not_authenticated(self):
        for row in self.record['scenarios']:row.update(status='PASS',evidence_sha256=self.evidence())
        self.save();result=status(self.root);self.assertEqual(result['status'],'RECORDED_OUTCOMES')
        self.assertIn('not authenticated',result['boundary'])
    def test_duplicate_scenario_rejected(self):
        self.record['scenarios'][0]=self.record['scenarios'][1];self.save();self.assertEqual(status(self.root)['status'],'BLOCKED')
    def test_changed_evidence_is_stale(self):
        self.record['scenarios'][0].update(status='PASS',evidence_sha256=self.evidence());self.save()
        (self.root/'evidence.md').write_text('changed fixture');self.assertEqual(status(self.root)['status'],'BLOCKED')
    def test_failure_is_not_success(self):
        self.record['scenarios'][0].update(status='FAIL',evidence_sha256=self.evidence());self.save()
        self.assertEqual(status(self.root)['status'],'RECORDED_FAILURE')
    def test_private_evidence_is_not_loaded(self):
        self.record['scenarios'][0].update(status='PASS',evidence_sha256={'.env':'a'*64});self.save()
        self.assertEqual(status(self.root)['status'],'BLOCKED')
