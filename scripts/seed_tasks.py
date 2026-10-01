#!/usr/bin/env python3
"""Preview or execute a reviewed local task DAG; resume via recorded checkpoints."""
import argparse
from pathlib import Path
import sys
from seedlib.common import read_json,safe_path,dump
from seedlib.tasks import run

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--plan',required=True);p.add_argument('--execute',action='store_true');args=p.parse_args()
    try:
        result=run(args.root,read_json(safe_path(args.root,args.plan)),args.execute)
        print(dump(result),end='');raise SystemExit(0 if result['status'] in {'PASS','PREVIEW','CHECKPOINT'} else 2)
    except (OSError,ValueError,KeyError,ImportError) as e:
        print('BLOCKED: '+str(e),file=sys.stderr);raise SystemExit(2)
