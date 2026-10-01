"""Prediction protocol, cost/coverage and provenance must survive the whole pipeline."""
from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.common import dump,sha
from seedlib.predictions import envelope,normalize
from seedlib.evaluation import evaluate,compare,load_cases
from run_candidate import run

ROOT=Path(__file__).resolve().parents[2]

class PredictionProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.cases=[{'id':'x','input':'text','expected':'text','group':'g','split':'release','slices':['all'],'label_status':'verified'}]
        self.candidate={'candidate':'test','configuration':{'model':'exact-fixture','revision':'1'},'kind':'external','argv':['{python}','-c','import json; print(json.dumps({"prediction":"text","cost_usd":0}))']}
        self.config={'candidate':'test','configuration':self.candidate['configuration'],'scorer':'exact_json'}
        self.row={'id':'x','prediction':'text','cost_usd':0,'latency_ms':1}
        self.saved=envelope([self.row],'a'*64,self.candidate)
        self.policy={'min_cases':1,'min_accuracy':1,'min_accuracy_lower_95':0,'max_regressions':0,
                     'max_p95_latency_ms':1000,'max_total_cost_usd':1,'min_slice_accuracy':1,'min_coverage':1}

    def score(self, saved=None, cfg=None):
        return evaluate(self.cases,self.saved if saved is None else saved,'a'*64,cfg or self.config)

    def test_saved_envelope_is_bound(self):
        result=self.score();self.assertEqual(result['provenance']['status'],'BOUND_RUN')
        self.assertEqual(compare(result,result,self.policy)['status'],'ELIGIBLE_FOR_REVIEW')

    def test_raw_predictions_remain_exploration_only(self):
        result=self.score([self.row]);self.assertEqual(result['metrics']['accuracy'],1)
        self.assertEqual(compare(result,result,self.policy)['status'],'REJECT')

    def test_prediction_tampering_rejected(self):
        self.saved['predictions'][0]['prediction']='something else'
        with self.assertRaises(ValueError):self.score()

    def test_manifest_tampering_rejected(self):
        self.saved['manifest']['count']=99
        with self.assertRaises(ValueError):self.score()

    def test_candidate_relabel_rejected(self):
        cfg={**self.config,'candidate':'another model'}
        with self.assertRaises(ValueError):self.score(cfg=cfg)

    def test_configuration_relabel_rejected(self):
        cfg={**self.config,'configuration':{'model':'same name','revision':'2'}}
        with self.assertRaises(ValueError):self.score(cfg=cfg)

    def test_dataset_relabel_rejected(self):
        with self.assertRaises(ValueError):evaluate(self.cases,self.saved,'b'*64,self.config)

    def test_error_is_not_a_covered_prediction(self):
        result=self.score(envelope([{'id':'x','status':'ERROR','error_code':'TIMEOUT','latency_ms':1}], 'a'*64,self.candidate))
        self.assertEqual(result['metrics']['coverage'],0)
        self.assertEqual(result['results'][0]['reason'],'EXECUTION_ERROR')
        self.assertIsNone(result['metrics']['total_cost_usd'])

    def test_abstention_has_explicit_coverage(self):
        rows=run(self.root,self.cases,{**self.candidate,'argv':['{python}','-c','print(\'{"abstained":true,"cost_usd":0}\')']},True)
        result=self.score(envelope(rows,'a'*64,self.candidate))
        self.assertEqual(result['metrics']['coverage'],0)
        self.assertEqual(result['results'][0]['reason'],'ABSTAINED')

    def test_conflicting_status_rejected(self):
        with self.assertRaises(ValueError):normalize({'status':'PREDICTED','abstained':True,'prediction':'x'})

    def test_abstention_cannot_hide_a_prediction(self):
        with self.assertRaises(ValueError):normalize({'status':'ABSTAINED','prediction':'x'})

    def test_unknown_result_field_rejected(self):
        with self.assertRaises(ValueError):normalize({'prediction':'x','judge_override':True})

    def test_string_booleans_rejected(self):
        with self.assertRaises(ValueError):normalize({'prediction':'x','abstained':'false'})

    def test_error_diagnostics_cannot_be_secret_bearing_messages(self):
        with self.assertRaises(ValueError):normalize({'status':'ERROR','error_code':'a credential-like diagnostic with spaces'})

    def test_nonfinite_prediction_rejected(self):
        with self.assertRaises(ValueError):normalize({'prediction':{'nested':float('nan')}})

    def test_bound_run_with_low_coverage_fails_that_requirement(self):
        candidate=self.score(envelope([{'id':'x','status':'ABSTAINED','cost_usd':0,'latency_ms':1}], 'a'*64,self.candidate))
        policy={**self.policy,'min_accuracy':0,'min_slice_accuracy':0,'max_regressions':1}
        comparison=compare(self.score(),candidate,policy)
        self.assertEqual(comparison['status'],'REJECT')
        self.assertIn('Coverage below minimum',comparison['reasons'])
        self.assertFalse(any('provenance' in reason.lower() for reason in comparison['reasons']))

    def test_unknown_policy_fields_rejected(self):
        with self.assertRaises(ValueError):compare(self.score(),self.score(),{**self.policy,'magic':True})

    def test_missing_coverage_requirement_rejected(self):
        self.policy.pop('min_coverage')
        with self.assertRaises(ValueError):compare(self.score(),self.score(),self.policy)

    def test_invalid_probability_rejected(self):
        with self.assertRaises(ValueError):compare(self.score(),self.score(),{**self.policy,'min_coverage':1.1})

    def test_invalid_count_rejected(self):
        with self.assertRaises(ValueError):compare(self.score(),self.score(),{**self.policy,'min_cases':1.5})

    def test_adapter_failure_is_saved_and_does_not_retry(self):
        cfg={**self.candidate,'argv':['{python}','-c','raise SystemExit(4)']}
        rows=run(self.root,self.cases+[dict(self.cases[0],id='other')],cfg,True)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],'ERROR')
        self.assertIsNone(rows[0]['cost_usd'])

    def test_invalid_provider_json_not_echoed(self):
        rows=run(self.root,self.cases,{**self.candidate,'argv':['{python}','-c','print("private unstructured output")']},True)
        self.assertEqual(rows[0]['error_code'],'INVALID_OUTPUT')
        self.assertNotIn('private unstructured',dump(rows))

    def test_external_response_cannot_change_case_id(self):
        rows=run(self.root,self.cases,{**self.candidate,'argv':['{python}','-c','print(\'{"id":"other","prediction":"text"}\')']},True)
        self.assertEqual(rows[0]['status'],'ERROR');self.assertEqual(rows[0]['id'],'x')

    def test_cli_generates_and_scores_single_bound_artifact(self):
        (self.root/'.seed-local').mkdir()
        (self.root/'cases.jsonl').write_text(json.dumps(self.cases[0])+'\n')
        (self.root/'candidate.json').write_text(dump(self.candidate))
        (self.root/'score.json').write_text(dump(self.config))
        args=[sys.executable,str(ROOT/'scripts/run_candidate.py'),'--root',str(self.root),'--cases','cases.jsonl','--candidate','candidate.json','--out','.seed-local/predictions.json','--allow-external']
        result=subprocess.run(args,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse((self.root/'.seed-local/predictions.json.metadata.json').exists())
        result=subprocess.run([sys.executable,str(ROOT/'scripts/seed_eval.py'),'--root',str(self.root),'score','--cases','cases.jsonl','--predictions','.seed-local/predictions.json','--config','score.json','--out','.seed-local/score.json'],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        saved=json.loads((self.root/'.seed-local/score.json').read_text())
        self.assertEqual(saved['provenance']['status'],'BOUND_RUN')
        self.assertEqual(saved['metrics']['accuracy'],1)
