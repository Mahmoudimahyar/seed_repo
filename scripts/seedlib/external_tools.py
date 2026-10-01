"""Thin, optional upstream adapters. No plugin installation or graph-first hooks.

Git provides exact commit snapshots; opensrc provides explicitly unverified acquisition.
Graphify's pinned AST library is called in an isolated Python worker, not its agent skill.
"""
from __future__ import annotations
import io
import os
from pathlib import Path
import re
import shutil
import tarfile
import uuid

from .common import atomic_json, bounded_int, dump, has_secret, now, read_json, safe_path, sha
from .external import (Sources, SourceError, CACHE, COMMIT, MAX_FILES, MAX_FILE_BYTES,
                       MAX_TREE_BYTES, copy_inventory, no_symlink_path,
                       relative, request_check, schema_check, tree_inventory, workspace)
from .processes import supervise

TOOLS_ROOT=Path(__file__).resolve().parents[2]
MAX_GRAPH_BYTES=16*1024*1024
CODE_EXTENSIONS={'.py','.js','.jsx','.ts','.tsx','.mjs','.cjs','.go','.rs','.java','.c','.h',
                 '.cpp','.hpp','.cc','.cs','.rb','.php','.swift','.kt','.kts','.scala','.sh',
                 '.sql','.vue','.svelte','.r','.R','.lua','.ex','.exs','.dart'}
# Keep resolution config as inert data but never send it through semantic extraction.


def tool_versions() -> dict:
    return read_json(TOOLS_ROOT/'quality/external-tools.json')


def command_prefix(command: list[str]) -> list[str]:
    if not isinstance(command,list) or not command or not all(isinstance(s,str) and s and '\x00' not in s for s in command):
        raise SourceError('Expected a reviewed command argument list')
    executable=shutil.which(command[0])
    if executable is None: raise SourceError('BLOCKED: optional provider executable is not available; no installation attempted')
    # A .cmd/.bat file introduces shell interpretation on Windows. Use node + its JS entry or native exe.
    if Path(executable).suffix.lower() in {'.cmd','.bat'}:
        raise SourceError('Use a native executable or explicit node + opensrc JS entry, not a batch wrapper')
    # Resolve explicitly supplied script paths before switching into the disposable cwd.
    # Flags and module names remain arguments; nothing from the downloaded tree is selected.
    arguments=[]
    for argument in command[1:]:
        path=Path(argument)
        if not argument.startswith('-') and path.is_file():
            argument=str(no_symlink_path(path))
        arguments.append(argument)
    return [str(Path(executable).absolute()),*arguments]


def invoke(store: Sources, command: list[str], args: list[str], work: Path, env: dict,
           timeout=120, max_output_bytes=2_000_000):
    result=supervise([*command_prefix(command),*args],cwd=work,env=env,timeout=timeout,
                     stop_file=safe_path(store.root,'.seed-local/STOP'),max_output_bytes=max_output_bytes)
    if result.status!='PASS':
        raise SourceError(f'{result.status}: optional provider command did not succeed ({result.reason or result.exit_code}); output withheld')
    return result


def unpack_git_archive(raw: bytes, destination: Path) -> None:
    """Do not use extractall on an external archive. Regular files/directories only."""
    destination.mkdir(parents=True,exist_ok=False);total=0;seen=set();count=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
        for member in archive:
            name=relative(member.name.rstrip('/'))
            if name.casefold() in seen: raise SourceError('Duplicate archive path')
            seen.add(name.casefold());target=safe_path(destination,name)
            if member.isdir(): target.mkdir(parents=True,exist_ok=True);continue
            if not member.isfile() or member.size>MAX_FILE_BYTES:
                raise SourceError('Unsupported archive entry or file size')
            count+=1;total+=member.size
            if count>MAX_FILES or total>MAX_TREE_BYTES: raise SourceError('Archive limits exceeded')
            source=archive.extractfile(member)
            if source is None: raise SourceError('Archive data missing')
            data=source.read(MAX_FILE_BYTES+1)
            if len(data)!=member.size: raise SourceError('Archive size mismatch')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            if os.name=='posix':target.chmod(0o755 if member.mode & 0o111 else 0o644)


def git_snapshot(store,request,commit,work,env,local_repo=None):
    if not COMMIT.fullmatch(commit): raise SourceError('An exact lowercase 40-character Git commit is required; tags/branches never fall back')
    common=['-c','core.fsmonitor=false','-c',f'core.hooksPath={work / "empty-hooks"}',
            '-c','credential.helper=','-c','protocol.file.allow=never','-c','protocol.ext.allow=never',
            '-c','http.followRedirects=false']
    version=invoke(store,['git'],['--version'],work,env,15).stdout.decode().strip()
    if local_repo is not None:
        repo=no_symlink_path(local_repo)
        if not repo.is_dir():raise SourceError('Local Git repository is missing')
        origin='local-object';provider='git-local'
    else:
        if request['repository'] is None:raise SourceError('A public HTTPS repository is required')
        repo=work/'git';invoke(store,['git'],[*common,'init','--bare',str(repo)],work,env,15)
        invoke(store,['git'],[*common,'-C',str(repo),'fetch','--depth=1','--no-tags','--no-recurse-submodules',
                              request['repository'],commit],work,env,120)
        origin='remote-fetch';provider='git-https'
    args=[*common,'-C',str(repo)]
    actual=invoke(store,['git'],[*args,'rev-parse','--verify',commit+'^{commit}'],work,env,15).stdout.decode().strip()
    if actual!=commit:raise SourceError('Git resolved a different commit')
    selector=[] if request['subdirectory']=='.' else ['--',request['subdirectory']]
    listing=invoke(store,['git'],[*args,'ls-tree','-rz',commit,*selector],work,env,30).stdout
    if any(line.startswith(b'160000 ') for line in listing.split(b'\0')):
        raise SourceError('Selected tree contains submodules; select a narrower corpus or register each dependency separately')
    archive=invoke(store,['git'],[*args,'archive','--format=tar',commit,*selector],work,env,60,16_000_000).stdout
    unpack_git_archive(archive,work/'checkout')
    selected=safe_path(work/'checkout',request['subdirectory'])
    tree_inventory(selected)
    return selected,{'kind':'git-commit','provider':provider,'provider_version':version,
                     'commit':commit,'origin':origin}


def acquire_git(store: Sources,request:dict,commit:str,local_repo:Path|None=None,write=False) -> dict:
    request_check(request)
    if not isinstance(commit,str) or not COMMIT.fullmatch(commit):raise SourceError('An exact 40-character commit pin is required')
    if not write:return {'status':'PREVIEW','operation':'git-snapshot','source_id':request['id'],
                         'commit':commit,'network':local_repo is None,'mapping':'UNVERIFIED'}
    with store.writing(),workspace(store.root) as (work,env):
        selected,identity=git_snapshot(store,request,commit,work,env,local_repo)
        return store._register(request,selected,identity,
             'Git archive projection at an exact commit; export attributes apply. Package artifact/version mapping still needs review.')


def acquire_opensrc(store: Sources,request:dict,command=None,write=False) -> dict:
    request_check(request);command=command or ['opensrc']
    spec=request['package']+'@'+request['version']
    if not write:return {'status':'PREVIEW','operation':'opensrc','source_id':request['id'],
                         'spec':spec,'network':True,'mapping':'UNVERIFIED',
                         'note':'Public package acquisition only. No private credentials, plugin install, or automatic source-version claim.'}
    with store.writing(),workspace(store.root) as (work,env):
        expected=tool_versions()['opensrc']['version']
        version=invoke(store,command,['--version'],work,env,15).stdout.decode().strip()
        if version not in {expected,'opensrc '+expected}:raise SourceError('BLOCKED: opensrc version is not the reviewed adapter version')
        cache=work/'opensrc-cache';cache.mkdir()
        env={**env,'OPENSRC_HOME':str(cache)}
        result=invoke(store,command,['path',spec,'--verbose','--cwd',str(work)],work,env,120)
        lines=result.stdout.decode('utf-8').strip().splitlines()
        if len(lines)!=1:raise SourceError('opensrc did not return a single source path')
        candidate=Path(lines[0])
        if not candidate.is_absolute() or not candidate.is_relative_to(cache):
            raise SourceError('opensrc returned a path outside the dedicated cache')
        candidate=no_symlink_path(candidate)
        # opensrc's package path may already be the registry-declared monorepo package.
        # request.subdirectory is relative to that returned corpus for this provider.
        selected=safe_path(candidate,request['subdirectory'])
        return store._register(request,selected,{'kind':'content-snapshot','provider':'opensrc',
                  'provider_version':expected,'commit':None,'origin':'unverified'},
                  'opensrc may fall back to a default branch. This snapshot is UNVERIFIED even if no warning was printed; compare it with an exact Git snapshot before recording version mapping.')


def verify_against_git(store:Sources,source_id:str,commit:str,*,expected_record:str,
                       local_repo:Path|None=None,subdirectory:str|None=None,write=False) -> dict:
    record=store.get(source_id)
    if sha(dump(record).encode())!=expected_record:raise SourceError('STALE: source record changed before verification')
    if not COMMIT.fullmatch(commit):raise SourceError('Exact Git commit required')
    request=dict(record['request'])
    if subdirectory is not None:request['subdirectory']=relative(subdirectory,dot=True)
    if not write:return {'status':'PREVIEW','operation':'verify-against-git','source_id':source_id,
                         'commit':commit,'subdirectory':request['subdirectory'],'network':local_repo is None}
    with store.writing(),workspace(store.root) as (work,env):
        selected,identity=git_snapshot(store,request,commit,work,env,local_repo)
        if tree_inventory(selected)['sha256']!=record['snapshot']['sha256']:
            raise SourceError('Source bytes do not match the requested Git snapshot; no fallback or approval recorded')
        current=store.get(source_id)
        if sha(dump(current).encode())!=expected_record:raise SourceError('STALE: source record changed')
        data=store.manifest();entry=data['sources'][source_id]
        entry.update(identity=identity,request=request,mapping={'status':'UNVERIFIED','review':None},
                     warning='Byte equality with a Git archive was checked. Published package artifact/version mapping and license are still not approved.')
        schema_check('external-sources',data);atomic_json(safe_path(store.root,'.seed/external-sources.lock.json'),data)
        return {'status':'VERIFIED_SNAPSHOT','source_id':source_id,'identity':identity,
                'record_sha256':sha(dump(entry).encode()),'mapping':'UNVERIFIED'}


def normalize_graph(raw:dict,input_root:Path,selected:set[str]) -> dict:
    """Project only bounded data fields. Graph labels are untrusted, not calibrated confidence."""
    if not isinstance(raw,dict) or not isinstance(raw.get('nodes'),list) or not isinstance(raw.get('edges'),list):
        raise SourceError('Unsupported Graphify extraction shape')
    if raw.get('input_tokens',0)!=0 or raw.get('output_tokens',0)!=0:
        raise SourceError('Unexpected semantic/model activity in code-only adapter')
    if len(raw['nodes'])>100000 or len(raw['edges'])>200000 or has_secret(dump(raw)):
        raise SourceError('Graph exceeds limits or contains possible credentials')
    dropped=0;truncated=0
    def text(value,cap=500):
        nonlocal truncated
        if not isinstance(value,str):return ''
        value=value.replace(str(input_root),'<source>')
        clean=''.join(c for c in value if ord(c)>=32 and ord(c)!=127)
        if len(clean)>cap:truncated+=1
        return clean[:cap]
    def location(value):
        nonlocal dropped
        if not value:return None
        try:
            path=Path(value)
            rel=path.relative_to(input_root).as_posix() if path.is_absolute() else relative(value)
            if rel not in selected:raise ValueError('Unselected file')
            return rel
        except (ValueError,TypeError):dropped+=1;return None
    nodes=[];ids={};covered=set()
    for node in raw['nodes']:
        if not isinstance(node,dict) or not isinstance(node.get('id'),str) or not 1<=len(node['id'])<=2000:
            raise SourceError('Invalid graph node')
        nid=node['id']
        if nid in ids:raise SourceError('Duplicate graph node ID')
        ids[nid]='n-'+sha(nid.replace(str(input_root),'<source>').encode())
        source=location(node.get('source_file'))
        if source:covered.add(source)
        loc=text(node.get('source_location'),100) or None
        nodes.append({'id':ids[nid],'label':text(node.get('label')), 'source_file':source,
                      'source_location':loc,'location_verified':source is not None})
    edges=[];dangling=0
    for edge in raw['edges']:
        if not isinstance(edge,dict):raise SourceError('Invalid graph edge')
        if edge.get('source') not in ids or edge.get('target') not in ids:
            dangling+=1;continue
        confidence=edge.get('confidence')
        if confidence not in {'EXTRACTED','INFERRED','AMBIGUOUS'}:confidence='UNKNOWN'
        edges.append({'source':ids[edge['source']],'target':ids[edge['target']],
                      'relation':text(edge.get('relation'),100),'confidence':confidence,
                      'source_file':location(edge.get('source_file')),
                      'source_location':text(edge.get('source_location'),100) or None})
    failures=raw.get('failed_sources',[])
    if not isinstance(failures,list):raise SourceError('Invalid Graphify failure report')
    return {'schema_version':1,'status':'PARTIAL' if failures or selected-covered or dangling else 'BUILT',
            'nodes':nodes,'edges':edges,'input_file_count':len(selected),'located_file_count':len(covered),
            'unlocated_files':sorted(selected-covered),'failed_source_count':len(failures),
            'dangling_edges_omitted':dangling,'dropped_locations':dropped,'truncated_labels':truncated,
            'note':'Structural extraction only; location_verified means an in-snapshot file, not semantic correctness or a verified line. Confidence labels are not calibrated probabilities.'}


def build_graph(store:Sources,source_id:str,python_command=None,write=False,timeout=120) -> dict:
    import sys
    bounded_int(timeout,1,600)
    command=python_command or [sys.executable]
    record=store.get(source_id)
    if not write:return {'status':'PREVIEW','operation':'graphify-ast','source_id':source_id,
                         'network_requested':False,'semantic_model':False,
                         'note':'Optional isolated library adapter; no graphify install, skills, hooks, community naming or first-party graph replacement.'}
    with store.writing(),workspace(store.root) as (work,env):
        inventory=tree_inventory(store.tree(source_id))
        # Copy to a disposable analysis input so an upstream cache write cannot alter the registered snapshot.
        copy_inventory(store.tree(source_id),work/'input',inventory)
        selected={p for p in inventory['files'] if Path(p).suffix in CODE_EXTENSIONS}
        if not selected:raise SourceError('No supported code file candidates; use exact search instead')
        worker=TOOLS_ROOT/'scripts/external_graphify_worker.py'
        config={'input_root':str(work/'input'),'cache_root':str(work/'cache'),
                'output':str(work/'raw.json'),'files':sorted(selected),
                'expected_version':tool_versions()['graphify']['version']}
        atomic_json(work/'job.json',config)
        result=invoke(store,command,['-I',str(worker),str(work/'job.json')],work,env,timeout)
        rawpath=safe_path(work,'raw.json')
        if not rawpath.is_file() or rawpath.stat().st_size>MAX_GRAPH_BYTES:
            raise SourceError('Graphify did not produce bounded extraction data')
        graph=normalize_graph(read_json(rawpath),work/'input',selected)
        if tree_inventory(work/'input')['sha256']!=inventory['sha256']:
            raise SourceError('Graphify changed its analysis input; result not accepted')
        # A concurrent external edit cannot be hidden by operating on the working copy.
        current=store.get(source_id)
        if sha(dump(current).encode())!=sha(dump(record).encode()):raise SourceError('STALE: source record changed during graph build')
        generation=uuid.uuid4().hex
        directory=safe_path(store.root,f'{CACHE}/analysis/{source_id}/{generation}')
        directory.mkdir(parents=True,exist_ok=False)
        atomic_json(directory/'graph.json',graph)
        digest=sha((directory/'graph.json').read_bytes())
        metadata={'schema_version':1,'source_id':source_id,'source_sha256':record['snapshot']['sha256'],
                  'generation':generation,'graph_sha256':digest,'tool':'graphifyy',
                  'tool_version':tool_versions()['graphify']['version'],'worker_sha256':sha(worker.read_bytes()),
                  'tool_policy_sha256':sha(dump(tool_versions()['graphify']).encode()),
                  'adapter_sha256':sha(Path(__file__).read_bytes()),'status':graph['status'],
                  'created_at':now(),'duration_seconds':result.duration_seconds,
                  'network_boundary':'No semantic entry point; credentials stripped and Python network/process audit guard. Not an OS/native-code sandbox.'}
        atomic_json(safe_path(store.root,f'{CACHE}/analysis/{source_id}/current.json'),metadata)
        return {'status':graph['status'],'source_id':source_id,'graph_sha256':digest,
                'nodes':len(graph['nodes']),'edges':len(graph['edges']),
                'unlocated_files':graph['unlocated_files'][:20],'failed_source_count':graph['failed_source_count'],
                'note':graph['note']}


def load_graph(store:Sources,source_id:str):
    record=store.get(source_id)
    metadata_path=safe_path(store.root,f'{CACHE}/analysis/{source_id}/current.json')
    if metadata_path.stat().st_size>100_000:raise SourceError('Derived graph metadata exceeds its bound')
    meta=read_json(metadata_path)
    if not isinstance(meta,dict) or not re.fullmatch('[a-f0-9]{32}',str(meta.get('generation',''))):
        raise SourceError('Invalid graph generation')
    worker=TOOLS_ROOT/'scripts/external_graphify_worker.py'
    if (meta.get('source_id')!=source_id or meta.get('source_sha256')!=record['snapshot']['sha256'] or
        meta.get('worker_sha256')!=sha(worker.read_bytes()) or meta.get('adapter_sha256')!=sha(Path(__file__).read_bytes()) or
        meta.get('tool_policy_sha256')!=sha(dump(tool_versions()['graphify']).encode())):
        raise SourceError('STALE: graph source, extraction code or policy changed')
    path=safe_path(store.root,f'{CACHE}/analysis/{source_id}/{meta["generation"]}/graph.json')
    if not path.is_file() or path.stat().st_size>MAX_GRAPH_BYTES or sha(path.read_bytes())!=meta.get('graph_sha256'):
        raise SourceError('STALE: derived graph changed or disappeared')
    return meta,read_json(path)


def graph_status(store:Sources,source_id:str) -> dict:
    store.get(source_id)
    if not safe_path(store.root,f'{CACHE}/analysis/{source_id}/current.json').exists():return {'status':'NOT_BUILT'}
    try:
        meta,graph=load_graph(store,source_id)
        return {'status':graph['status'],'graph_sha256':meta['graph_sha256'],
                'tool_version':meta['tool_version'],'nodes':len(graph['nodes']),'edges':len(graph['edges'])}
    except (ValueError,OSError,KeyError):return {'status':'STALE'}


def graph_search(store:Sources,source_id:str,query:str,limit=6,max_chars=12000) -> dict:
    bounded_int(limit,1,20);bounded_int(max_chars,2000,30000)
    if not query.strip() or len(query)>300:raise SourceError('Use a short nonempty literal graph query')
    meta,graph=load_graph(store,source_id)
    words=query.casefold().split()
    scored=[(sum(w in (n['label']+' '+(n['source_file'] or '')).casefold() for w in words),n) for n in graph['nodes']]
    chosen=[n for score,n in sorted(scored,key=lambda pair:(-pair[0],pair[1]['id'])) if score][:limit]
    ids={n['id'] for n in chosen}
    edges=[e for e in graph['edges'] if e['source'] in ids or e['target'] in ids]
    edges.sort(key=lambda e:(e['relation'] in {'contains','defines'},e['relation'],e['source'],e['target']))
    result=store.base(source_id)
    result.update(graph_status=graph['status'],graph_sha256=meta['graph_sha256'],nodes=[],edges=[],neighbors=[],truncated=False,
                  note=graph['note']+' Nodes are namespaced by source_id; query text is not sent to a model.')
    neighbors={end for e in edges[:30] for end in (e['source'],e['target'])}-ids
    cards=[n for n in graph['nodes'] if n['id'] in neighbors][:12]
    for key,items in [('nodes',chosen),('edges',edges),('neighbors',cards)]:
        for item in items:
            result[key].append(item)
            if len(dump(result))>max_chars or (key=='edges' and len(result[key])>30):
                result[key].pop();result['truncated']=True;break
    return result


def restore_source(store:Sources,source_id:str,*,local_repo:Path|None=None,write=False) -> dict:
    """Rehydrate a missing exact snapshot without modifying its tracked manifest/review."""
    record=store.get(source_id,fresh=False)
    if record['identity']['kind']!='git-commit':
        raise SourceError('Unverified snapshots cannot be reconstructed by version name; supply and verify the original bytes')
    if store.tree(source_id).parent.exists():
        raise SourceError('Cache already exists. Inspect/quarantine stale material manually; restoration never overwrites it')
    if not write:return {'status':'PREVIEW','operation':'restore','source_id':source_id,'network':local_repo is None}
    before=sha(dump(record).encode())
    with store.writing(),workspace(store.root) as (work,env):
        source,_=git_snapshot(store,record['request'],record['identity']['commit'],work,env,local_repo)
        inventory=tree_inventory(source)
        if inventory['sha256']!=record['snapshot']['sha256']:
            raise SourceError('Restored source does not match the recorded snapshot')
        if sha(dump(store.get(source_id,fresh=False)).encode())!=before:
            raise SourceError('STALE: manifest changed during restoration')
        copy_inventory(source,work/'restored',inventory)
        store.tree(source_id).parent.mkdir(parents=True,exist_ok=False)
        os.replace(work/'restored',store.tree(source_id))
    return {'status':'RESTORED','source_id':source_id,'source_sha256':inventory['sha256'],
            'note':'Existing manifest and mapping review were not changed. Rebuild derived analysis separately.'}
