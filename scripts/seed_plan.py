#!/usr/bin/env python3
"""Optional, offline decision planning. Mutations require --write; no tasks are executed."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys

from seedlib.common import dump, read_json, safe_path
from seedlib.planning import PlanningStore, checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='command', required=True)
    mutations = {'create', 'revise-map', 'add', 'revise', 'select', 'claim', 'renew', 'release', 'resolve', 'import-snapshot'}
    for command in ('create','revise-map','add','revise','select','claim','renew','release','resolve',
                    'get','handoff','next','history','export','import-snapshot'):
        cmd = sub.add_parser(command)
        if command in mutations: cmd.add_argument('--write', action='store_true')
        if command not in {'create','revise-map','import-snapshot'}:
            cmd.add_argument('--map', required=command not in {'handoff','next'})
        if command in {'add','create','revise','revise-map','import-snapshot'}:
            cmd.add_argument('--file', required=True)
        if command in {'get','claim','renew','release','resolve'}:
            cmd.add_argument('--ticket', required=True)
        if command in {'handoff','history'}: cmd.add_argument('--ticket')
        if command in {'handoff','next','history'}: cmd.add_argument('--limit', type=int, default=8)
        if command in {'revise','revise-map','claim','resolve'}:
            cmd.add_argument('--expected-revision', type=int, required=True)
        if command == 'claim': cmd.add_argument('--owner', required=True)
        if command in {'claim','renew'}: cmd.add_argument('--ttl', type=int, default=300)
        if command in {'renew','release','resolve'}:
            cmd.add_argument('--claim-file', required=True, help='Private JSON output of claim; never commit it')
        if command == 'resolve':
            cmd.add_argument('--record', required=True, help='Existing accepted/rejected decision-schema record')
            cmd.add_argument('--terminal', choices=['resolved','out-of-scope','superseded'], default='resolved')
            cmd.add_argument('--replacement')
        if command in {'export','claim','handoff'}: cmd.add_argument('--out', help='New local file; never overwrite')
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        store = PlanningStore(root)
        value = None
        if hasattr(args, 'file'):
            path = safe_path(root, args.file)
            if not path.is_file() or path.stat().st_size > 10_000_000:
                raise ValueError('Input must be an existing JSON file below 10 MB')
            value = read_json(path)
            kind = 'planning-snapshot' if args.command=='import-snapshot' else 'decision-map' if args.command in {'create','revise-map'} else 'decision-ticket'
            checked(kind, value)
        if args.command in mutations and not args.write:
            print(dump({'status':'PREVIEW', 'operation':args.command,
                        'note':'Schema checked when supplied. No state changes. --write performs conflict/freshness checks; it never grants authority.'}), end='')
            return 0
        output = safe_path(root,args.out) if getattr(args,'out',None) else None
        if output and output.exists(): raise ValueError('Refusing to overwrite output')
        if args.command=='claim' and output and not output.is_relative_to(safe_path(root,'.seed-local')):
            raise ValueError('Claim files must stay in ignored .seed-local storage')
        token = None
        if hasattr(args,'claim_file'):
            claim_path = safe_path(root,args.claim_file)
            if not claim_path.is_relative_to(safe_path(root,'.seed-local')):
                raise ValueError('Use an ignored .seed-local claim file')
            claim = read_json(claim_path)
            if claim.get('map_id') != args.map or claim.get('ticket_id') != args.ticket:
                raise ValueError('Claim belongs to another map/ticket')
            token = claim['token']
        command = args.command
        if command=='create': result=store.create(value)
        elif command=='revise-map': result=store.revise_map(value,args.expected_revision)
        elif command=='add': result=store.add(args.map,value)
        elif command=='revise': result=store.revise(args.map,value,args.expected_revision)
        elif command=='select': result=store.select(args.map)
        elif command=='get': result=store.get(args.map,args.ticket)
        elif command in {'handoff','next'}: result=store.handoff(args.map,getattr(args,'ticket',None),args.limit)
        elif command=='history': result=store.history(args.map,args.ticket,args.limit)
        elif command=='claim': result=store.claim(args.map,args.ticket,args.owner,args.expected_revision,args.ttl)
        elif command=='renew': result=store.renew(args.map,args.ticket,token,args.ttl)
        elif command=='release': result=store.release(args.map,args.ticket,token)
        elif command=='resolve': result=store.resolve(args.map,args.ticket,args.record,args.expected_revision,token,args.terminal,args.replacement)
        elif command=='export': result=store.export(args.map)
        else: result=store.import_snapshot(value)
        if output:
            output.parent.mkdir(parents=True,exist_ok=True)
            fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as handle: handle.write(dump(result))
            # Avoid unnecessarily printing a lease token when it was stored in a private file.
            if command=='claim': result={k:v for k,v in result.items() if k!='token'}
        print(dump(result),end='')
        return 0
    except ImportError:
        print('BLOCKED: install requirements-governance.txt to validate planning contracts',file=sys.stderr)
        return 2
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('BLOCKED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__': raise SystemExit(main())
