#!/usr/bin/env python3
"""Opt-in real-provider acceptance. Never installs tools or uses test doubles.

Graphify check is local AST only. opensrc check needs --allow-network and public package access.
A PASS covers this small scenario on this installation, not security or general model quality.
"""
import argparse
import json
from pathlib import Path
import tempfile
from seedlib.common import dump
from seedlib.external import Sources, SourceError
from seedlib.external_tools import acquire_opensrc, build_graph, graph_search, tool_versions
from seed_oss import parse_command


def check(provider,command=None,allow_network=False):
    if provider=='opensrc' and not allow_network:
        return {'status':'BLOCKED','provider':provider,'reason':'Public registry/repository access requires --allow-network'}
    with tempfile.TemporaryDirectory(prefix='seed-external-acceptance-') as temp:
        base=Path(temp).resolve();project=base/'project';project.mkdir();store=Sources(project)
        request={'id':'acceptance','package':'fixture','version':'1.0.0','repository':None,'subdirectory':'.',
                 'purpose':'Temporary integration acceptance fixture, not an application requirement.',
                 'owner':'local-checker','license_path':None}
        if provider=='graphify':
            source=base/'source';source.mkdir()
            (source/'helper.py').write_text('def retry(value):\n    return value\n')
            (source/'app.py').write_text('from helper import retry\ndef fetch(value):\n    return retry(value)\n')
            (source/'index.ts').write_text('export function parse(value: string) { return value; }\n')
            (source/'AGENTS.md').write_text('FOREIGN_INSTRUCTION_MUST_NOT_BECOME_AUTHORITY')
            store.import_tree(request,source,True)
            result=build_graph(store,'acceptance',command,True)
            if result['status']!='BUILT':raise SourceError('Fixture extraction is partial; missing support must be fixed, not skipped')
            answer=graph_search(store,'acceptance','retry')
            if not any(n['label']=='retry' and n['source_file']=='helper.py' for n in answer['nodes']):
                raise SourceError('Graph did not locate the expected Python symbol')
            ts=graph_search(store,'acceptance','parse')
            if not any(n['label']=='parse' and n['source_file']=='index.ts' for n in ts['nodes']):
                raise SourceError('Graph did not locate the expected TypeScript symbol')
            if 'FOREIGN_INSTRUCTION' in dump(answer)+dump(ts):raise SourceError('Document entered code-only graph')
            store.tree('acceptance').joinpath('helper.py').write_text('changed')
            try:graph_search(store,'acceptance','retry')
            except SourceError:pass
            else:raise SourceError('Stale source was accepted')
            return {'status':'PASS','provider':'graphify','version':tool_versions()['graphify']['version'],
                    'checks':['actual AST API','Python location','TypeScript location','no doc extraction','stale rejection'],
                    'boundary':'Real installed package on a synthetic local fixture. No general performance, OS sandbox or native-client certification.'}
        request.update(package='zod',version='3.22.0',repository='https://github.com/colinhacks/zod')
        result=acquire_opensrc(store,request,command,True)
        record=store.get('acceptance')
        if record['mapping']['status']!='UNVERIFIED':raise SourceError('Acquisition incorrectly claimed version mapping')
        evidence=store.search('acceptance','ZodError')
        if not evidence['matches']:raise SourceError('Acquisition returned no expected package source evidence')
        return {'status':'PASS','provider':'opensrc','version':tool_versions()['opensrc']['version'],
                'checks':['real public package acquisition','bounded source search','mapping remains unverified'],
                'snapshot_sha256':record['snapshot']['sha256'],
                'boundary':'Acquisition check only. No verification of tag/artifact equality, client behavior or integration suitability.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--provider',required=True,choices=['graphify','opensrc'])
    p.add_argument('--command-json',type=parse_command);p.add_argument('--allow-network',action='store_true');args=p.parse_args()
    try:result=check(args.provider,args.command_json,args.allow_network)
    except (OSError,ValueError,ImportError,KeyError) as exc:result={'status':'BLOCKED','provider':args.provider,'reason':str(exc)}
    print(dump(result),end='');raise SystemExit(0 if result['status']=='PASS' else 2)
