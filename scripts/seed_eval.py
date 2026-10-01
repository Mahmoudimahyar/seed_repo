#!/usr/bin/env python3
"""Evaluate saved predictions, compare configurations, and group provisional labels."""
from pathlib import Path
import argparse
import json
import sys
from seedlib.evaluation import load_cases,evaluate,compare,consensus
from seedlib.common import read_json,atomic_json,safe_path,dump


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('score');s.add_argument('--cases',required=True);s.add_argument('--predictions',required=True);s.add_argument('--config',required=True)
    s=sub.add_parser('compare');s.add_argument('--incumbent',required=True);s.add_argument('--candidate',required=True);s.add_argument('--policy',required=True)
    s=sub.add_parser('consensus');s.add_argument('--predictions',required=True)
    for parser in sub.choices.values():parser.add_argument('--out',required=True)
    args=p.parse_args();root=args.root.resolve()
    try:
        load=lambda name:read_json(safe_path(root,name))
        if args.command=='score':
            cases,sha=load_cases(safe_path(root,args.cases));result=evaluate(cases,load(args.predictions),sha,load(args.config))
        elif args.command=='compare':result=compare(load(args.incumbent),load(args.candidate),load(args.policy))
        else:result={'labels':consensus(load(args.predictions)),'status':'PROVISIONAL_ONLY'}
        out=safe_path(root,args.out)
        if out.exists():raise ValueError('Refusing to overwrite prior evaluation evidence')
        atomic_json(out,result);print(dump(result),end='')
        return 1 if result.get('status')=='REJECT' else 0
    except (OSError,ValueError,KeyError,TypeError) as e:
        print('BLOCKED: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
