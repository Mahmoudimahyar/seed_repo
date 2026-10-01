#!/usr/bin/env python3
"""Private process entry point for the pinned Graphify AST API; not an agent/plugin installer.

Called with python -I and a credential-free environment. Audit hooks cover Python socket/
process APIs, not native syscalls. Use OS isolation when processing hostile source/tooling.
"""
from importlib.metadata import version
import json
from pathlib import Path
import sys


def guard(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn','os.exec','os.spawn'}:
        raise PermissionError('Network/process API disabled in the AST-only worker')


def main():
    job=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    if version('graphifyy')!=job['expected_version']:
        raise RuntimeError('Graphify version differs from the reviewed adapter policy')
    sys.addaudithook(guard)
    from graphify.extract import extract
    root=Path(job['input_root']).resolve()
    paths=[]
    for name in job['files']:
        path=root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError('Invalid AST input')
        paths.append(path)
    # No detect(), semantic modules, assistant skill, clustering or model-backed naming.
    result=extract(paths,root=root,cache_root=Path(job['cache_root']),parallel=False,max_workers=1)
    payload=json.dumps(result,ensure_ascii=False,allow_nan=False).encode('utf-8')
    if len(payload)>16*1024*1024:raise ValueError('Graph extraction exceeds output limit')
    Path(job['output']).write_bytes(payload)
    print(json.dumps({'status':'EXTRACTED','files':len(paths),'semantic_model':False}))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Do not echo foreign source, absolute paths or potential credentials into agent context.
        print('BLOCKED: AST worker failed: '+type(exc).__name__,file=sys.stderr)
        raise SystemExit(2)
