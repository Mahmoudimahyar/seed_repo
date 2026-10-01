"""Task-specific, exact-reference evaluation with measured cost/coverage evidence.

This is a small adapter for local fixtures or externally generated predictions, not
an LLM judge, benchmark-label authority, provider gateway, or auto-deployment daemon.
"""
from __future__ import annotations
from collections import defaultdict
import json
import math
from pathlib import Path
import re
from .common import read_json,dump,sha,finite_number,now
from .predictions import unpack


def load_cases(path: Path) -> tuple[list[dict],str]:
    raw=path.read_bytes()
    cases=[json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    if not cases:raise ValueError('Dataset is empty')
    seen=set();groups={}
    for row in cases:
        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or row['id'] in seen:
            raise ValueError('Every case needs a unique string ID')
        seen.add(row['id'])
        for field in ('input','expected','split','group','label_status','slices'):
            if field not in row:raise ValueError('Missing case field: '+field)
        if row['split'] not in {'development','release','regression','challenge'}:raise ValueError('Unknown split')
        if row['label_status'] not in {'verified','synthetic_reference','provisional','unresolved'}:raise ValueError('Unknown label provenance')
        if not isinstance(row['group'],str) or not isinstance(row['slices'],list) or not all(isinstance(x,str) for x in row['slices']):
            raise ValueError('Invalid group or slices')
        if row['group'] in groups and groups[row['group']]!=row['split']:
            raise ValueError('Group leakage across splits')
        groups[row['group']]=row['split']
    return cases,sha(raw)


def entity_set(value,text: str) -> set[tuple]:
    if not isinstance(value,list):raise ValueError('Entities must be an array')
    out=set()
    for entity in value:
        if not isinstance(entity,dict) or set(entity)!={'type','start','end','text'}:raise ValueError('Invalid entity schema')
        a,b=entity['start'],entity['end']
        if type(a) is not int or type(b) is not int or not 0<=a<b<=len(text):raise ValueError('Invalid source span')
        if entity['text']!=text[a:b] or not isinstance(entity['type'],str):raise ValueError('Entity not supported by source span')
        key=(entity['type'],a,b,entity['text'])
        if key in out:raise ValueError('Duplicate entity')
        out.add(key)
    return out


def wilson(successes: int,n: int,z=1.959963984540054) -> list[float]:
    if n<1:return [0.0,1.0]
    p=successes/n;d=1+z*z/n
    middle=(p+z*z/(2*n))/d
    spread=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,middle-spread),min(1,middle+spread)]


def evaluate(cases: list[dict],predictions: list[dict],dataset_sha: str,config: dict) -> dict:
    if config.get('scorer') not in {'exact_json','entities'}:raise ValueError('Unsupported scorer')
    if not isinstance(config.get('candidate'),str) or not isinstance(config.get('configuration'),dict):raise ValueError('Candidate and full configuration metadata required')
    if any(case['label_status'] in {'provisional','unresolved'} for case in cases):
        raise ValueError('Unverified labels cannot grade an acceptance benchmark')
    if not cases: raise ValueError('Cannot score an empty dataset')
    predictions, provenance = unpack(predictions, dataset_sha, config)
    ids={row['id'] for row in cases};by_id={}
    for item in predictions:
        if not isinstance(item,dict) or item.get('id') not in ids or item['id'] in by_id:
            raise ValueError('Duplicate or unknown prediction ID')
        if 'prediction' not in item and not item.get('abstained'):raise ValueError('Prediction or explicit abstention required')
        for key in ('cost_usd','latency_ms'):
            if item.get(key) is not None:finite_number(item[key])
        by_id[item['id']]=item
    results=[];tp=fp=fn=0;costs=[];latencies=[];cost_known=True;latency_known=True
    slices=defaultdict(list)
    for case in cases:
        item=by_id.get(case['id']);reason=None;success=False
        if item is None:reason='MISSING_PREDICTION';cost_known=False;latency_known=False
        else:
            if item.get('cost_usd') is None:cost_known=False
            else:costs.append(item['cost_usd'])
            if item.get('latency_ms') is None:latency_known=False
            else:latencies.append(item['latency_ms'])
        if item and item['status']=='ERROR': reason='EXECUTION_ERROR'
        if config['scorer']=='entities':
            expected=entity_set(case['expected'],case['input'])
            actual=set()
            if item is not None and item['status']=='PREDICTED':
                try:actual=entity_set(item['prediction'],case['input'])
                except (ValueError,TypeError):reason='INVALID_OUTPUT'
            elif item and item['status']=='ABSTAINED':reason='ABSTAINED'
            tp+=len(actual & expected);fp+=len(actual-expected);fn+=len(expected-actual)
            success=reason is None and actual==expected
        elif item and item['status']=='PREDICTED':
            success=(type(item['prediction']) is type(case['expected']) and json.dumps(item['prediction'],sort_keys=True,allow_nan=False)==json.dumps(case['expected'],sort_keys=True,allow_nan=False))
        elif item and item['status']=='ABSTAINED':reason='ABSTAINED'
        if not success and reason is None:reason='INCORRECT'
        result={'id':case['id'],'correct':success,'reason':reason,'slices':case['slices']}
        results.append(result)
        for name in set(case['slices']):slices[name].append(success)
    n=len(cases);wins=sum(x['correct'] for x in results)
    metrics={'n':n,'accuracy':wins/n,'accuracy_95ci':wilson(wins,n),
             'coverage':sum(x['reason'] not in {'MISSING_PREDICTION','ABSTAINED','INVALID_OUTPUT','EXECUTION_ERROR'} for x in results)/n,
             'total_cost_usd':sum(costs) if cost_known else None,
             'p95_latency_ms':sorted(latencies)[math.ceil(.95*n)-1] if latency_known else None,
             'slices':{name:{'n':len(v),'accuracy':sum(v)/len(v)} for name,v in sorted(slices.items())}}
    if config['scorer']=='entities':
        metrics.update(precision=tp/(tp+fp) if tp+fp else (1.0 if not fn else 0.0),
                       recall=tp/(tp+fn) if tp+fn else 1.0,
                       f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.0)
    return {'schema_version':1,'candidate':config['candidate'],'configuration':config['configuration'],
            'config_sha256':sha(dump(config).encode()),'scorer':config['scorer'],'dataset_sha256':dataset_sha,
            'generated_at':now(),'metrics':metrics,'results':results,
            'data_status':'synthetic_demo' if any(c['label_status']=='synthetic_reference' for c in cases) else 'verified_as_declared',
            'split':sorted({c['split'] for c in cases}), 'provenance':provenance,
            'limits':'Labels/provenance are supplied by dataset owners, not independently authenticated. Wilson interval assumes representative independent binary cases; no perfection or production reliability claim.'}


def compare(incumbent: dict,candidate: dict,policy: dict) -> dict:
    from .governance import validate
    errors=validate('promotion-policy',policy)
    if errors:raise ValueError('Invalid or unsupported promotion policy: '+'; '.join(errors))
    reasons=[]
    if incumbent['dataset_sha256']!=candidate['dataset_sha256'] or incumbent['scorer']!=candidate['scorer']:
        raise ValueError('Candidates must share exactly the same dataset and scorer')
    a={r['id']:r for r in incumbent['results']};b={r['id']:r for r in candidate['results']}
    if set(a)!=set(b):raise ValueError('Paired case IDs differ')
    regressions=[i for i in a if a[i]['correct'] and not b[i]['correct']]
    m=candidate['metrics']
    if candidate.get('provenance',{}).get('status')!='BOUND_RUN' or incumbent.get('provenance',{}).get('status')!='BOUND_RUN':
        reasons.append('Generating run provenance is not bound for both reports')
    if candidate['data_status']!='verified_as_declared':reasons.append('Synthetic examples do not authorize promotion')
    if candidate['split']!=['release']:reasons.append('A held-out release split is required')
    for key in ('min_cases','min_accuracy','min_accuracy_lower_95','max_regressions','max_p95_latency_ms','max_total_cost_usd','min_slice_accuracy'):
        if key not in policy:raise ValueError('Explicit promotion policy missing '+key)
        finite_number(policy[key])
    if m['coverage']<policy['min_coverage']:reasons.append('Coverage below minimum')
    if m['n']<policy['min_cases']:reasons.append('Insufficient sample size')
    if m['accuracy']<policy['min_accuracy']:reasons.append('Accuracy below minimum')
    if m['accuracy_95ci'][0]<policy['min_accuracy_lower_95']:reasons.append('Uncertainty bound below minimum')
    if len(regressions)>policy['max_regressions']:reasons.append('Paired regressions exceed policy')
    if any(s['accuracy']<policy['min_slice_accuracy'] for s in m['slices'].values()):reasons.append('Slice regression')
    for field,limit in [('p95_latency_ms','max_p95_latency_ms'),('total_cost_usd','max_total_cost_usd')]:
        if m[field] is None or m[field]>policy[limit]:reasons.append(field+' unknown or above limit')
    return {'status':'REJECT' if reasons else 'ELIGIBLE_FOR_REVIEW','reasons':reasons,
            'regressions':regressions,'incumbent':incumbent['candidate'],'candidate':candidate['candidate'],
            'dataset_sha256':candidate['dataset_sha256'],'policy_sha256':sha(dump(policy).encode()),
            'automatic_promotion':False,'note':'No configuration changed. This conservative screen is not a formal equivalence or non-inferiority proof. Use protected review, shadow/canary and rollback for production.'}


def consensus(predictions: list[dict]) -> list[dict]:
    """Normalized grouping for provisional labels; agreement never yields gold."""
    grouped=defaultdict(dict)
    for row in predictions:
        if not {'id','model','prediction'}<=set(row):raise ValueError('Consensus rows need id, model, prediction')
        if row['model'] in grouped[row['id']]:raise ValueError('Duplicate model vote')
        grouped[row['id']][row['model']]=row['prediction']
    output=[]
    for case,values in sorted(grouped.items()):
        counts=defaultdict(list)
        for model,prediction in values.items():counts[json.dumps(prediction,sort_keys=True)].append(model)
        winner,members=max(counts.items(),key=lambda kv:len(kv[1]))
        agreed=len(counts)==1
        output.append({'id':case,'label_status':'provisional','proposed_label':json.loads(winner),
                       'agreement':agreed,'models':sorted(values),'review_required':not agreed,
                       'agreement_audit_required':agreed,'note':'Agreement is not independent evidence of truth; audit agreements too.'})
    return output
