#!/usr/bin/env python3
"""Create a clean template ZIP and checksum. Never publishes or modifies GitHub."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
import zipfile
from seed import validate,repo_files,sensitive_filename
from seedlib.file_policy import local_configuration,export_problems


def package(root: Path,out: Path):
    root=root.resolve();state=json.loads((root/'seed.json').read_text());version=(root/'VERSION').read_text().strip()
    if state['kind']!='template':raise ValueError('Publish the starter checkout, not an initialized private app')
    if state['distribution_version']!=version or not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z0-9.]+)?',version):raise ValueError('Version mismatch or unsafe release version')
    problems=validate(root,public=True)
    if problems:raise ValueError('Static validation failed:\n'+'\n'.join(problems))
    candidates=list(repo_files(root))
    problems=export_problems(root,[p.relative_to(root).as_posix() for p in candidates])
    if problems:raise ValueError('Distribution policy failed: '+'; '.join(problems))
    files=[]
    for path in candidates:
        rel=path.relative_to(root).as_posix()
        if path.is_symlink() or sensitive_filename(path.name) or local_configuration(rel):raise ValueError('Sensitive/symlink file in export')
        if path.suffix.lower() in {'.zip','.whl','.skill','.sqlite','.db','.ttf','.otf','.woff','.woff2'}:
            raise ValueError('Review and remove non-source/archive/font asset before packaging: '+rel)
        if rel=='MANIFEST.sha256':continue
        files.append((rel,path.read_bytes()))
    manifest=''.join(hashlib.sha256(data).hexdigest()+'  '+rel+'\n' for rel,data in sorted(files)).encode()
    out=out.resolve();out.mkdir(parents=True,exist_ok=True);target=out/f'seed-repo-{version}.zip'
    if target.exists():raise ValueError('Refusing to overwrite an existing release archive')
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for rel,data in sorted(files)+[('MANIFEST.sha256',manifest)]:
            info=zipfile.ZipInfo('seed-repo/'+rel,date_time=(2026,9,20,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,data)
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(target.suffix+'.sha256').write_text(digest+'  '+target.name+'\n')
    return {'path':str(target),'files':len(files)+1,'sha256':digest,
            'scope':'Byte integrity and clean source export; no signature, security audit, client certification or GitHub publication.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=Path('.seed-local/releases'));args=p.parse_args()
    try:print(json.dumps(package(Path(__file__).resolve().parents[1],args.out),indent=2))
    except (OSError,ValueError,TypeError) as e:print('BLOCKED: '+str(e),file=sys.stderr);raise SystemExit(2)
