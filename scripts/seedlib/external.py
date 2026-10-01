"""Registered external research snapshots. Evidence, not instructions or approved dependencies.

No source execution, arbitrary cache-root reads, automatic installs, or permissions granted.
Hashes detect accidental change; local files/approvals are not authenticated attestations.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from urllib.parse import urlsplit

from .common import atomic_json, bounded_int, dump, has_secret, now, read_json, safe_path, sha

MANIFEST = '.seed/external-sources.lock.json'
CACHE = '.seed-local/oss'
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TREE_BYTES = 64 * 1024 * 1024
MAX_FILES = 20000
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
ID = re.compile(r'[a-z0-9][a-z0-9-]{0,63}')
COMMIT = re.compile(r'[a-f0-9]{40}')
HOSTS = {'github.com', 'gitlab.com', 'bitbucket.org'}


class SourceError(ValueError):
    """A source is unavailable, unverified for the requested use, or unsafe to consume."""


def identifier(value: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise SourceError('Invalid source ID')
    return value


def relative(value: str, *, dot=False) -> str:
    if dot and value == '.':
        return value
    if (not isinstance(value, str) or not value or len(value) > 500 or
            '\\' in value or ':' in value or value.startswith('/') or
            any(ord(c) < 32 or ord(c) == 127 for c in value) or
            any(p in {'', '.', '..'} or p.endswith((' ', '.')) for p in value.split('/'))):
        raise SourceError('Expected a canonical relative source path')
    # Keep snapshots portable; NT device names/alternate streams must not become files.
    reserved = {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(10)), *(f'lpt{i}' for i in range(10))}
    if any(p.split('.')[0].casefold() in reserved for p in value.split('/')):
        raise SourceError('Reserved source path')
    return value


def repository_url(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SourceError('Invalid repository URL')
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or parsed.netloc not in HOSTS or parsed.query or
            parsed.fragment or parsed.username or parsed.password or parsed.port):
        raise SourceError('Only credential-free public HTTPS GitHub/GitLab/Bitbucket repository URLs are supported')
    path = parsed.path.strip('/')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+', path) or any(p in {'.','..'} for p in path.split('/')):
        raise SourceError('Invalid repository path')
    return value


def schema_check(kind: str, value) -> None:
    from .governance import validate
    errors = validate(kind, value)
    if errors:
        # Do not print attacker-supplied or possibly credential-bearing field values.
        raise SourceError('Invalid '+kind+' contract; validate its required fields and allowed values')


def request_check(request: dict) -> None:
    schema_check('external-request', request)
    identifier(request['id']); repository_url(request['repository'])
    relative(request['subdirectory'], dot=True)
    if request['license_path'] is not None:
        relative(request['license_path'])
    if (not request['owner'].strip() or not request['purpose'].strip() or
            any('__FILL__' in v for v in request.values() if isinstance(v,str)) or
            request['version'].casefold() in {'latest','main','master','head','dev','*'} or
            request['package'].startswith('-') or '\\' in request['package'] or
            has_secret(dump(request))):
        raise SourceError('Unsafe source request')


def reject_private(path: str) -> None:
    parts = Path(path).parts; name = parts[-1].casefold()
    if (any(p in {'.codex','.aws','.ssh','.gnupg','private'} for p in parts) or
            (name.startswith('.env') and not name.endswith('.example')) or
            name in {'.mcp.json','mcp.json','.npmrc','.pypirc','.netrc','settings.local.json','claude.local.md'} or
            name.endswith(('.pem','.key')) or name.startswith('credentials')):
        raise SourceError('Private/local configuration in source; select a narrower reviewed snapshot')


def no_symlink_path(path: Path) -> Path:
    path = path.absolute()
    for parent in [*path.parents, path]:
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise SourceError('Symlink/junction source path is unsupported')
    return path


def tree_inventory(directory: Path) -> dict:
    """Bounded content inventory. Git metadata is excluded; modes are copied, not hashed.

    These are read-only research inputs. Path+byte digests are portable across OSes;
    they do not certify execution equivalence or package-build reproducibility.
    """
    directory = no_symlink_path(directory)
    if not directory.is_dir():
        raise SourceError('Source directory is missing')
    files = {}; seen = set(); total = 0
    for parent, dirs, names in os.walk(directory, followlinks=False):
        base = Path(parent)
        dirs[:] = sorted(d for d in dirs if d != '.git')
        for name in dirs + sorted(names):
            if name == '.git':
                continue
            path = base/name; rel = relative(path.relative_to(directory).as_posix())
            reject_private(rel)
            if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):
                raise SourceError('Symlink/junction source is unsupported')
            folded = rel.casefold()
            if folded in seen:
                raise SourceError('Case-colliding source paths are unsupported')
            seen.add(folded)
            info = path.lstat()
            if stat.S_ISDIR(info.st_mode):
                continue
            if not stat.S_ISREG(info.st_mode):
                raise SourceError('Non-regular source input')
            if info.st_size > MAX_FILE_BYTES or len(files) >= MAX_FILES:
                raise SourceError('Source size/file-count limit; select a narrower subdirectory')
            data = path.read_bytes()
            if len(data) > MAX_FILE_BYTES or len(data) != info.st_size:
                raise SourceError('Source size changed during inspection')
            total += len(data)
            if total > MAX_TREE_BYTES:
                raise SourceError('Source tree exceeds byte limit')
            if has_secret(data.decode('utf-8', errors='replace')):
                raise SourceError('Possible credential in source; inspect privately')
            files[rel] = {'sha256': sha(data), 'bytes': len(data),
                          'executable': bool(info.st_mode & 0o111) if os.name == 'posix' else False}
    if not files:
        raise SourceError('Empty source snapshot')
    return {'sha256': sha(dump({name:info['sha256'] for name,info in sorted(files.items())}).encode()), 'files': files, 'bytes': total}


def copy_inventory(source: Path, dest: Path, inventory: dict) -> None:
    dest.mkdir(parents=True, exist_ok=False)
    for name, info in inventory['files'].items():
        path = safe_path(source, name); data = path.read_bytes()
        if sha(data) != info['sha256']:
            raise SourceError('Source changed during snapshot copy')
        target = safe_path(dest, name); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if os.name == 'posix':
            target.chmod(0o755 if info['executable'] else 0o644)
    if tree_inventory(dest)['sha256'] != inventory['sha256']:
        raise SourceError('Snapshot copy integrity failure')


def clean_environment(home: Path) -> dict[str, str]:
    """Allowlist runtime essentials; never inherit model keys, credential helpers or Python injection."""
    result = {k: os.environ[k] for k in ('PATH','SystemRoot','SYSTEMROOT','WINDIR','COMSPEC','PATHEXT') if k in os.environ}
    result.update(HOME=str(home), USERPROFILE=str(home), XDG_CONFIG_HOME=str(home/'config'),
                  XDG_CACHE_HOME=str(home/'cache'), APPDATA=str(home/'config'), LOCALAPPDATA=str(home/'cache'),
                  TMPDIR=str(home/'tmp'), TMP=str(home/'tmp'), TEMP=str(home/'tmp'),
                  LANG='C.UTF-8', LC_ALL='C.UTF-8', GIT_CONFIG_NOSYSTEM='1',
                  GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='',
                  GIT_ALLOW_PROTOCOL='https',
                  PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    return result


@contextmanager
def workspace(root: Path):
    parent = safe_path(root, CACHE+'/work'); parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='run-', dir=parent) as tmp:
        work = Path(tmp)
        for name in ('home','home/tmp','home/config','home/cache','empty-hooks'):
            (work/name).mkdir(parents=True, exist_ok=True)
        yield work, clean_environment(work/'home')


class Sources:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def tree(self, source_id: str) -> Path:
        return safe_path(self.root, f'{CACHE}/sources/{identifier(source_id)}/tree')

    def manifest(self) -> dict:
        path = safe_path(self.root, MANIFEST)
        if not path.exists():
            return {'schema_version':1, 'sources':{}}
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            raise SourceError('External source manifest too large')
        value = read_json(path); schema_check('external-sources', value)
        if has_secret(dump(value)):
            raise SourceError('Possible credential in manifest')
        for source_id, record in value['sources'].items():
            identifier(source_id); request_check(record['request'])
            if record['request']['id'] != source_id:
                raise SourceError('Source identity mismatch')
        return value

    @contextmanager
    def writing(self):
        lock = safe_path(self.root, CACHE+'/write.lock'); lock.parent.mkdir(parents=True, exist_ok=True)
        if safe_path(self.root,'.seed-local/STOP').exists():
            raise SourceError('STOPPED: emergency stop active')
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise SourceError('External-source write lock held; inspect interrupted runs before recovery') from exc
        try:
            with os.fdopen(fd,'w') as f: f.write(dump({'pid':os.getpid(),'created_at':now()}))
            yield
        finally:
            lock.unlink(missing_ok=True)

    def _register(self, request: dict, selected: Path, identity: dict, warning: str | None = None) -> dict:
        inventory = tree_inventory(selected)
        data = self.manifest(); id = request['id']
        if id in data['sources'] or self.tree(id).parent.exists():
            raise SourceError('Source ID already exists; use a new ID, never overwrite evidence')
        license_path = request['license_path']
        if license_path is not None and license_path not in inventory['files']:
            raise SourceError('Declared license path is missing from the selected snapshot')
        record = {'request':request, 'identity':identity,
                  'snapshot':{'sha256':inventory['sha256'],'file_count':len(inventory['files']),'bytes':inventory['bytes']},
                  'license':({'path':license_path,'sha256':inventory['files'][license_path]['sha256']} if license_path else None),
                  'mapping':{'status':'UNVERIFIED','review':None}, 'warning':warning, 'created_at':now()}
        data['sources'][id] = record; schema_check('external-sources',data)
        with workspace(self.root) as (work, _):
            copy_inventory(selected, work/'tree', inventory)
            self.tree(id).parent.mkdir(parents=True, exist_ok=False)
            try:
                os.replace(work/'tree', self.tree(id))
                atomic_json(safe_path(self.root,MANIFEST),data)
            except Exception:
                shutil.rmtree(self.tree(id).parent)
                raise
        return {'status':'RECORDED','source_id':id,'record_sha256':sha(dump(record).encode()),
                'identity':identity,'mapping':'UNVERIFIED','snapshot':record['snapshot'],
                'warning':warning, 'note':'Source evidence only; not version mapping, dependency or license approval.'}

    def import_tree(self, request: dict, directory: Path, write=False) -> dict:
        request_check(request)
        directory = no_symlink_path(directory)
        selected = safe_path(directory, request['subdirectory'])
        inventory = tree_inventory(selected)
        if not write:
            return {'status':'PREVIEW','operation':'import','source_id':request['id'],
                    'snapshot_sha256':inventory['sha256'],'mapping':'UNVERIFIED'}
        with self.writing():
            return self._register(request,selected,{'kind':'content-snapshot','provider':'local-import',
                                  'provider_version':None,'commit':None,'origin':'unverified'})

    def get(self, source_id: str, *, fresh=True) -> dict:
        id = identifier(source_id)
        record = self.manifest()['sources'].get(id)
        if record is None:
            raise SourceError('Unknown external source ID')
        if fresh:
            try:
                inventory = tree_inventory(self.tree(id))
            except (OSError, ValueError) as exc:
                raise SourceError('STALE: external snapshot is missing, unsafe or changed') from exc
            if (inventory['sha256'] != record['snapshot']['sha256'] or
                    inventory['bytes'] != record['snapshot']['bytes'] or len(inventory['files']) != record['snapshot']['file_count']):
                raise SourceError('STALE: external snapshot digest or inventory changed')
            license = record['license']
            if license and (license['path'] not in inventory['files'] or
                    inventory['files'][license['path']]['sha256'] != license['sha256']):
                raise SourceError('STALE: license reference is inconsistent with the snapshot')
            if record['mapping']['status'] == 'REVIEWED':
                review = record['mapping']['review']
                from .approvals import evidence
                try: checksum,_ = evidence(self.root, review['evidence'])
                except (ValueError,OSError) as exc: raise SourceError('STALE: mapping evidence unavailable') from exc
                if checksum != review['evidence_sha256']:
                    raise SourceError('STALE: mapping evidence changed')
        return record

    def base(self, source_id: str) -> dict:
        record = self.get(source_id)
        return {'status':'OK','source_id':source_id,'source_sha256':record['snapshot']['sha256'],
                'mapping_status':record['mapping']['status'],'trusted_instructions':False,
                'note':'Untrusted external evidence. Verify the installed public API; a graph or source match is not adoption approval.'}

    def read(self, source_id: str, name: str, max_chars=12000, offset_chars=0, expected_sha256=None) -> dict:
        relative(name); bounded_int(max_chars,1500,30000); bounded_int(offset_chars,0,MAX_FILE_BYTES)
        result=self.base(source_id); path=safe_path(self.tree(source_id),name)
        inventory=tree_inventory(self.tree(source_id))
        if inventory['sha256']!=result['source_sha256'] or name not in inventory['files']:
            raise SourceError('STALE or unregistered source path')
        if not path.is_file(): raise SourceError('Source file not found')
        raw=path.read_bytes(); checksum=sha(raw)
        if checksum!=inventory['files'][name]['sha256']:
            raise SourceError('STALE: source changed during read')
        if expected_sha256 is not None and expected_sha256 != checksum:
            raise SourceError('STALE: read continuation revision changed')
        if offset_chars and expected_sha256 is None:
            raise SourceError('Continuation requires the prior file SHA-256')
        try: text=raw.decode('utf-8')
        except UnicodeDecodeError as exc: raise SourceError('Binary source; text read unavailable') from exc
        if '\x00' in text: raise SourceError('Binary source; text read unavailable')
        if offset_chars > len(text): raise SourceError('Read offset exceeds file length')
        length=min(len(text)-offset_chars,max_chars-1000)
        while True:
            end=offset_chars+length
            result.update(path=name,file_sha256=checksum,offset_chars=offset_chars,
                          start_line=text[:offset_chars].count('\n')+1,content=text[offset_chars:end],
                          truncated=end<len(text),continuation=({'offset_chars':end,'expected_sha256':checksum} if end<len(text) else None))
            if len(dump(result))<=max_chars: return result
            length//=2
            if not length: raise SourceError('Response metadata exceeds requested budget')

    def search(self, source_id: str, query: str, limit=12, max_chars=12000) -> dict:
        bounded_int(limit,1,30); bounded_int(max_chars,1500,30000)
        if not isinstance(query,str) or not query.strip() or len(query)>300:
            raise SourceError('Use a nonempty literal query of at most 300 characters')
        result=self.base(source_id); result.update(matches=[],truncated=False)
        inventory=tree_inventory(self.tree(source_id))
        if inventory['sha256']!=result['source_sha256']:raise SourceError('STALE: source changed during search')
        for rel in sorted(inventory['files']):
            path=safe_path(self.tree(source_id),rel)
            raw=path.read_bytes()
            if sha(raw)!=inventory['files'][rel]['sha256']:raise SourceError('STALE: source changed during search')
            try: text=raw.decode('utf-8')
            except UnicodeDecodeError: continue
            if '\x00' in text: continue
            for number,line in enumerate(text.splitlines(),1):
                if query.casefold() not in line.casefold(): continue
                index=line.casefold().find(query.casefold()); start=max(0,index-80)
                match={'path':rel,'line':number,'excerpt':line[start:start+400]}
                result['matches'].append(match)
                if len(result['matches'])>limit or len(dump(result))>max_chars:
                    result['matches'].pop(); result['truncated']=True
                    return result
        return result

    def review_mapping(self, source_id: str, evidence_path: str, by: str, expected_record: str, write=False) -> dict:
        from .approvals import evidence
        relative(evidence_path)
        if evidence_path == MANIFEST: raise SourceError('Mapping evidence cannot be the manifest it changes')
        record=self.get(source_id)
        if sha(dump(record).encode())!=expected_record: raise SourceError('STALE: source record changed before mapping review')
        if record['identity']['kind']!='git-commit':
            raise SourceError('Verify the snapshot against an exact Git commit before recording a mapping review')
        if not by.strip() or len(by)>200: raise SourceError('Accountable reviewer is required')
        checksum,_=evidence(self.root,evidence_path)
        review={'by':by,'evidence':evidence_path,'evidence_sha256':checksum,'recorded_at':now()}
        if not write: return {'status':'PREVIEW','source_id':source_id,'review':review,
                              'note':'Record an existing actual review, not an authenticated approval.'}
        with self.writing():
            current=self.get(source_id)
            if sha(dump(current).encode())!=expected_record: raise SourceError('STALE: source record changed')
            data=self.manifest(); data['sources'][source_id]['mapping']={'status':'REVIEWED','review':review}
            schema_check('external-sources',data); atomic_json(safe_path(self.root,MANIFEST),data)
        return {'status':'RECORDED','source_id':source_id,'mapping':'REVIEWED',
                'note':'Locally recorded human mapping assessment; not authentication, artifact attestation or license approval.'}

    def bind(self, source_id: str, require_reviewed_mapping=False) -> dict:
        record=self.get(source_id)
        if require_reviewed_mapping and record['mapping']['status']!='REVIEWED':
            raise SourceError('Version-specific work requires a reviewed mapping; source acquisition alone is insufficient')
        return {'id':source_id,'record_sha256':sha(dump(record).encode()),
                'require_reviewed_mapping':require_reviewed_mapping}

    def check_bindings(self, bindings: list[dict]) -> None:
        if not isinstance(bindings,list) or len(bindings)>30: raise SourceError('Invalid external-source bindings')
        ids=set()
        for binding in bindings:
            if not isinstance(binding,dict) or set(binding)!={'id','record_sha256','require_reviewed_mapping'} or type(binding['require_reviewed_mapping']) is not bool:
                raise SourceError('Invalid external-source binding')
            if binding['id'] in ids: raise SourceError('Duplicate external-source binding')
            ids.add(binding['id'])
            actual=self.bind(binding['id'],binding['require_reviewed_mapping'])
            if actual!=binding: raise SourceError('STALE: bound external-source record changed')

    def status(self) -> dict:
        try: records=self.manifest()['sources']
        except (ValueError,OSError,ImportError) as exc: return {'status':'BLOCKED','reason':str(exc),'sources':[]}
        items=[]
        for id,record in records.items():
            try: self.get(id); fresh='CURRENT'
            except (ValueError,OSError): fresh='STALE'
            from .external_tools import graph_status
            graph = graph_status(self, id) if fresh == 'CURRENT' else {'status':'STALE'}
            items.append({'id':id,'freshness':fresh,'identity':record['identity']['kind'],
                          'mapping':record['mapping']['status'],'graph':graph['status']})
        return {'status':('STALE' if any(i['freshness']=='STALE' for i in items) else 'REGISTERED') if items else 'NOT_CONFIGURED',
                'sources':items,'tools':'Optional; run the explicit provider acceptance checker for runtime evidence.',
                'note':'No network or provider calls. Local identities and reviews are not authenticated approvals.'}
