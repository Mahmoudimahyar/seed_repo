#!/usr/bin/env python3
"""Validate governance contracts and evaluate read-only local action preflight."""
from pathlib import Path
import argparse
import sys
from seedlib.common import dump,read_json,safe_path
from seedlib.governance import KINDS,validate,preflight,references


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    sub=p.add_subparsers(dest='command',required=True)
    v=sub.add_parser('validate');v.add_argument('--kind',choices=sorted(KINDS),required=True);v.add_argument('file')
    v=sub.add_parser('preflight');v.add_argument('--workflow',required=True);v.add_argument('--request',required=True)
    v=sub.add_parser('references');v.add_argument('--workflow',required=True)
    sub.add_parser('stop')
    v=sub.add_parser('resume');v.add_argument('--acknowledge',action='store_true')
    args=p.parse_args();root=args.root.resolve()
    try:
        if args.command=='validate':
            errors=validate(args.kind,read_json(safe_path(root,args.file)))
            print(dump({'status':'FAIL' if errors else 'PASS','errors':errors}),end='');return 1 if errors else 0
        if args.command=='references':
            print(dump(references(root,read_json(safe_path(root,args.workflow)))),end='');return 0
        if args.command=='preflight':
            result=preflight(root,read_json(safe_path(root,args.workflow)),read_json(safe_path(root,args.request)))
            print(dump(result),end='');return 0 if result['status']=='ALLOW' else 2
        stop=safe_path(root,'.seed-local/STOP')
        if args.command=='stop':
            stop.parent.mkdir(parents=True,exist_ok=True);stop.touch();print('STOPPED: local managed tasks will not start another action. Kill/revoke running operations through their executor when needed.')
        elif not args.acknowledge:raise ValueError('Explicit --acknowledge required after reviewing the stop cause')
        else:stop.unlink(missing_ok=True);print('Local stop cleared. This is not permission to bypass other gates.')
        return 0
    except ImportError:
        print('BLOCKED: install requirements-governance.txt',file=sys.stderr);return 2
    except (ValueError,OSError,TypeError) as e:
        print('BLOCKED: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
