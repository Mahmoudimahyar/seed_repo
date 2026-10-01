from pathlib import Path
import json
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from seedlib.evaluation import load_cases,evaluate,compare,consensus,wilson,entity_set
from run_candidate import run
from seedlib.predictions import envelope

class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases=[{'id':'1','input':'Contact a@b.org','expected':[{'type':'email','start':8,'end':15,'text':'a@b.org'}],
                      'split':'release','group':'g1','label_status':'verified','slices':['email']}]
        self.config={'candidate':'test','configuration':{'version':'1'},'scorer':'entities'}
        self.pred=[{'id':'1','prediction':self.cases[0]['expected'],'cost_usd':0,'latency_ms':1}]
    def score(self):
        run=envelope(self.pred,'a'*64,{'candidate':self.config['candidate'],'configuration':self.config['configuration']})
        return evaluate(self.cases,run,'a'*64,self.config)
    def test_exact_entities(self):self.assertEqual(self.score()['metrics']['f1'],1)
    def test_source_hallucination_fails(self):
        self.pred[0]['prediction']=[{'type':'email','start':8,'end':15,'text':'x@y.org'}]
        self.assertEqual(self.score()['results'][0]['reason'],'INVALID_OUTPUT')
    def test_missing_prediction_not_dropped(self):
        self.pred=[];self.assertEqual(self.score()['metrics']['accuracy'],0)
    def test_abstention_counts_as_not_completed(self):
        self.pred=[{'id':'1','abstained':True}];r=self.score();self.assertEqual(r['metrics']['coverage'],0)
    def test_unknown_cost_not_free(self):
        del self.pred[0]['cost_usd'];self.assertIsNone(self.score()['metrics']['total_cost_usd'])
    def test_duplicate_id_rejected(self):
        self.pred*=2
        with self.assertRaises(ValueError):self.score()
    def test_unknown_prediction_id_rejected(self):
        self.pred[0]['id']='other'
        with self.assertRaises(ValueError):self.score()
    def test_provisional_not_ground_truth(self):
        self.cases[0]['label_status']='provisional'
        with self.assertRaises(ValueError):self.score()
    def test_full_agreement_remains_provisional(self):
        r=consensus([{'id':'a','model':'a','prediction':'x'},{'id':'a','model':'b','prediction':'x'}])[0]
        self.assertEqual(r['label_status'],'provisional');self.assertTrue(r['agreement_audit_required'])
    def test_disagreement_needs_review(self):
        r=consensus([{'id':'a','model':'a','prediction':1},{'id':'a','model':'b','prediction':2}])[0]
        self.assertTrue(r['review_required'])
    def test_model_cannot_vote_twice(self):
        with self.assertRaises(ValueError):consensus([{'id':'a','model':'x','prediction':1}]*2)
    def test_wilson_not_perfect_from_one_case(self):self.assertLess(wilson(1,1)[0],.5)
    def test_empty_dataset_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'d.jsonl';p.write_text('')
            with self.assertRaises(ValueError):load_cases(p)
    def test_group_leakage_rejected(self):
        c={**self.cases[0],'id':'2','split':'development'}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'d.jsonl';p.write_text('\n'.join(json.dumps(x) for x in self.cases+[c]))
            with self.assertRaises(ValueError):load_cases(p)
    def policy(self):return {'min_coverage':1,'min_cases':1,'min_accuracy':1,'min_accuracy_lower_95':0,'max_regressions':0,'max_p95_latency_ms':100,'max_total_cost_usd':1,'min_slice_accuracy':1}
    def test_eligible_only_for_review(self):
        r=compare(self.score(),self.score(),self.policy());self.assertEqual(r['status'],'ELIGIBLE_FOR_REVIEW');self.assertFalse(r['automatic_promotion'])
    def test_mismatched_data_rejected(self):
        r=self.score();r['dataset_sha256']='b'*64
        with self.assertRaises(ValueError):compare(self.score(),r,self.policy())
    def test_demo_cannot_promote(self):
        self.cases[0]['label_status']='synthetic_reference';r=compare(self.score(),self.score(),self.policy());self.assertEqual(r['status'],'REJECT')
    def test_regression_rejected(self):
        old=self.score();self.pred[0]['prediction']=[]
        self.assertEqual(compare(old,self.score(),self.policy())['status'],'REJECT')
    def test_negative_cost_invalid(self):
        self.pred[0]['cost_usd']=-1
        with self.assertRaises(ValueError):self.score()
    def test_nonfinite_cost_invalid(self):
        self.pred[0]['cost_usd']=float('nan')
        with self.assertRaises(ValueError):self.score()
    def test_external_adapter_requires_consent(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):run(Path(d),self.cases,{'kind':'external'})
    def test_builtin_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(run(Path(d),self.cases,{'kind':'builtin','implementation':'regex-email'})[0]['prediction'],self.cases[0]['expected'])
