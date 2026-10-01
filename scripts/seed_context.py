#!/usr/bin/env python3
"""Index and query local repository evidence without a model or network."""
from pathlib import Path
import argparse
import json
import sys
from seedlib.context import Context, build
from seedlib.common import dump, safe_path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('index');sub.add_parser('status')
    s=sub.add_parser('search');s.add_argument('query');s.add_argument('--limit',type=int,default=6)
    s=sub.add_parser('symbol');s.add_argument('name')
    s=sub.add_parser('related');s.add_argument('target');s.add_argument('--hops',type=int,default=1)
    s=sub.add_parser('read');s.add_argument('path');s.add_argument('--max-chars',type=int,default=12000);s.add_argument('--offset-chars',type=int,default=0);s.add_argument('--expected-sha256');s.add_argument('--start',type=int,default=1);s.add_argument('--end',type=int,default=80)
    s=sub.add_parser('config');s.add_argument('--client',choices=['claude','cursor','codex'],required=True)
    args=p.parse_args();root=args.root.resolve();ctx=Context(root)
    try:
        if args.command=='index':result=build(root)
        elif args.command=='status':result=ctx.status()
        elif args.command=='search':result=ctx.search(args.query,args.limit)
        elif args.command=='symbol':result=ctx.symbol(args.name)
        elif args.command=='related':result=ctx.related(args.target,args.hops)
        elif args.command=='read':result=ctx.read(args.path,args.start,args.end,args.max_chars,args.offset_chars,args.expected_sha256)
        else:
            script=str(safe_path(Path(__file__).resolve().parents[1],'scripts/seed_mcp.py'))
            entry={'command':sys.executable,'args':[script,'--root',str(root)]}
            if args.client=='codex':
                print('[mcp_servers.seed-context]\ncommand = '+json.dumps(sys.executable)+'\nargs = '+json.dumps(entry['args']))
                return 0
            result={'mcpServers':{'seed-context':entry}}
        print(dump(result),end='');return 0
    except (OSError,ValueError,TypeError,json.JSONDecodeError) as e:
        print('BLOCKED: '+str(e),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
