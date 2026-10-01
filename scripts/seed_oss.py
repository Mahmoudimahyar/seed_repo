#!/usr/bin/env python3
"""Optional external-source research: preview acquisition, verify identity, read bounded evidence.

Mutations require --write. Public Git/opensrc acquisition may use network; no installation.
Run --help or consult docs/workflows/external-source-research.md before enabling providers.
"""
import argparse
import json
from pathlib import Path
import sys
from seedlib.common import dump, read_json, safe_path
from seedlib.external import Sources, SourceError
from seedlib.external_tools import acquire_git, acquire_opensrc, verify_against_git, build_graph, graph_search, graph_status


def parse_command(value):
    command=json.loads(value)
    if not isinstance(command,list) or not command or not all(isinstance(x,str) and x for x in command):
        raise ValueError('Use a JSON argument list, not a shell command string')
    return command


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('status')
    imp=sub.add_parser('import');imp.add_argument('--request',required=True);imp.add_argument('--directory',required=True,type=Path);imp.add_argument('--write',action='store_true')
    fetch=sub.add_parser('fetch');fetch.add_argument('--request',required=True)
    fetch.add_argument('--provider',choices=['git','opensrc'],required=True)
    fetch.add_argument('--commit');fetch.add_argument('--local-repo',type=Path)
    fetch.add_argument('--command-json',type=parse_command,help='Reviewed opensrc command prefix, e.g. ["node","/path/to/opensrc.js"]')
    fetch.add_argument('--write',action='store_true')
    verify=sub.add_parser('verify');verify.add_argument('source_id');verify.add_argument('--commit',required=True)
    verify.add_argument('--local-repo',type=Path);verify.add_argument('--subdirectory')
    verify.add_argument('--expected-record',required=True);verify.add_argument('--write',action='store_true')
    restore=sub.add_parser('restore');restore.add_argument('source_id');restore.add_argument('--local-repo',type=Path);restore.add_argument('--write',action='store_true')
    info=sub.add_parser('inspect');info.add_argument('source_id')
    search=sub.add_parser('search');search.add_argument('source_id');search.add_argument('query')
    search.add_argument('--limit',type=int,default=12);search.add_argument('--max-chars',type=int,default=12000)
    read=sub.add_parser('read');read.add_argument('source_id');read.add_argument('path')
    read.add_argument('--max-chars',type=int,default=12000);read.add_argument('--offset-chars',type=int,default=0);read.add_argument('--expected-sha256')
    graph=sub.add_parser('graph');graph.add_argument('source_id');graph.add_argument('--python-command-json',type=parse_command)
    graph.add_argument('--timeout',type=int,default=120);graph.add_argument('--write',action='store_true')
    graphquery=sub.add_parser('graph-search');graphquery.add_argument('source_id');graphquery.add_argument('query')
    graphquery.add_argument('--limit',type=int,default=6);graphquery.add_argument('--max-chars',type=int,default=12000)
    review=sub.add_parser('record-mapping');review.add_argument('source_id');review.add_argument('--evidence',required=True)
    review.add_argument('--by',required=True);review.add_argument('--expected-record',required=True);review.add_argument('--write',action='store_true')
    bind=sub.add_parser('bind');bind.add_argument('source_id');bind.add_argument('--require-reviewed-mapping',action='store_true')
    args=parser.parse_args();store=Sources(args.root)
    try:
        if args.action=='status':result=store.status()
        elif args.action=='import':result=store.import_tree(read_json(safe_path(store.root,args.request)),args.directory,args.write)
        elif args.action=='fetch':
            request=read_json(safe_path(store.root,args.request))
            if args.provider=='git':
                if not args.commit:raise SourceError('Git acquisition requires --commit')
                result=acquire_git(store,request,args.commit,args.local_repo,args.write)
            else:
                if args.local_repo or args.commit:raise SourceError('Use verify after opensrc to check an exact commit; fetch does not imply one')
                result=acquire_opensrc(store,request,args.command_json,args.write)
        elif args.action=='verify':result=verify_against_git(store,args.source_id,args.commit,expected_record=args.expected_record,local_repo=args.local_repo,subdirectory=args.subdirectory,write=args.write)
        elif args.action=='restore':
            from seedlib.external_tools import restore_source
            result=restore_source(store,args.source_id,local_repo=args.local_repo,write=args.write)
        elif args.action=='inspect':result={'record':store.get(args.source_id),'binding':store.bind(args.source_id),'graph':graph_status(store,args.source_id)}
        elif args.action=='search':result=store.search(args.source_id,args.query,args.limit,args.max_chars)
        elif args.action=='read':result=store.read(args.source_id,args.path,args.max_chars,args.offset_chars,args.expected_sha256)
        elif args.action=='graph':result=build_graph(store,args.source_id,args.python_command_json,args.write,args.timeout)
        elif args.action=='graph-search':result=graph_search(store,args.source_id,args.query,args.limit,args.max_chars)
        elif args.action=='record-mapping':result=store.review_mapping(args.source_id,args.evidence,args.by,args.expected_record,args.write)
        elif args.action=='bind':result=store.bind(args.source_id,args.require_reviewed_mapping)
        else:raise SourceError('Unknown action')
        print(dump(result),end='')
        return 2 if result.get('status') in {'BLOCKED','STALE'} else 0
    except (ValueError,OSError,KeyError,TypeError,ImportError) as exc:
        print(dump({'status':'BLOCKED','reason':str(exc),'note':'No success or version compatibility inferred.'}),end='')
        return 2


if __name__=='__main__':raise SystemExit(main())
