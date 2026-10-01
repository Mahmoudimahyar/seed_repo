"""Local graph-assisted retrieval: sections, Python AST symbols, and explicit links.

No LLM, embeddings, network access, imports of indexed code, or filesystem writes
through retrieval. SQLite is a derived index; current source is authoritative.
"""
from __future__ import annotations
import ast
from collections import deque
from contextlib import closing
import fnmatch
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import unquote
from .common import safe_path, is_private, has_secret, sha, dump, now, bounded_int

SUFFIXES = {'.md', '.mdx', '.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.yaml',
            '.yml', '.toml', '.go', '.rs', '.java', '.sql', '.sh', '.css', '.html'}
MAX_FILE = 300_000
INDEX_SCHEMA = '2'
MAX_FILES = 10_000
DATABASE = '.seed-local/context.sqlite'


def exclusions(root: Path) -> list[str]:
    p = safe_path(root, '.seed/context-ignore.txt')
    return [s.strip() for s in p.read_text(encoding='utf-8').splitlines()
            if s.strip() and not s.lstrip().startswith('#')] if p.exists() else []


def source_files(root: Path) -> dict[str, bytes]:
    """Conservative exclusions, plus explicit glob rules. Does not implement gitignore."""
    result = {}
    patterns = exclusions(root)
    for parent, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(parent)/d).is_symlink()
                         and not is_private((Path(parent)/d).relative_to(root).as_posix())
                         and not any(fnmatch.fnmatch((Path(parent)/d).relative_to(root).as_posix()+'/', p)
                                     for p in patterns))
        for name in sorted(names):
            path = Path(parent)/name
            rel = path.relative_to(root).as_posix()
            if rel.startswith('.claude/skills/') or rel == '.seed/skill-mirrors.json':
                continue  # Canonical skills are indexed once, never as generated mirrors.
            if path.is_symlink() or is_private(rel) or path.suffix not in SUFFIXES:
                continue
            if any(fnmatch.fnmatch(rel, pattern) for pattern in patterns):
                continue
            if path.stat().st_size > MAX_FILE:
                continue
            data = path.read_bytes()
            try:
                text = data.decode('utf-8')
            except UnicodeError:
                continue
            if '\x00' in text or has_secret(text):
                continue
            result[rel] = data
            if len(result) > MAX_FILES:
                raise ValueError('Index file limit exceeded; narrow .seed/context-ignore.txt')
    return result


def fingerprint(files: dict[str, bytes]) -> str:
    return sha(dump({p:sha(data) for p,data in sorted(files.items())}).encode())


def extract(path: str, text: str) -> tuple[list[dict], list[tuple]]:
    lines = text.splitlines() or ['']
    nodes = []
    edges = []
    def add(kind, name, start, end):
        node_id = f'{path}::{kind}:{name}:{start}'
        nodes.append({'id':node_id, 'path':path, 'kind':kind, 'name':name,
                      'start':start, 'end':end, 'text':'\n'.join(lines[start-1:end])})
        edges.append((path, node_id, 'contains', 'parser'))
        return node_id
    nodes.append({'id':path,'path':path,'kind':'file','name':path,'start':1,
                  'end':len(lines),'text':'\n'.join(lines[:25])})
    if Path(path).suffix == '.py':
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        if tree:
            def visit(body, prefix=''):
                for node in body:
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        qualified = prefix + node.name
                        add('symbol', qualified, node.lineno, node.end_lineno or node.lineno)
                        visit(node.body, qualified+'.')
            visit(tree.body)
            # Definitions alone miss constants, imports, conditionals, and decorators.
            covered = set()
            for node in nodes[1:]:
                covered.update(range(node['start'], node['end'] + 1))
            start = 1
            while start <= len(lines):
                if start in covered:
                    start += 1
                    continue
                end = start
                while end + 1 <= len(lines) and end + 1 not in covered and end - start < 79:
                    end += 1
                add('chunk', f'module-lines-{start}', start, end)
                start = end + 1
    if Path(path).suffix in {'.md','.mdx'}:
        headings = []
        fence = False
        for i,line in enumerate(lines,1):
            if line.lstrip().startswith(('```','~~~')):
                fence = not fence
            if not fence and re.match(r'^#{1,6} ',line):
                headings.append((i,line.lstrip('# ').strip()))
        for j,(line,title) in enumerate(headings):
            end = headings[j+1][0]-1 if j+1 < len(headings) else len(lines)
            # Bound unusually large sections; do not present truncated sections as complete.
            for start in range(line,end+1,80):
                add('section',title,start,min(end,start+79))
    if len(nodes) == 1:
        for start in range(1,len(lines)+1,80):
            add('chunk',f'lines-{start}',start,min(len(lines),start+79))
    return nodes,edges


def build(root: Path) -> dict:
    root = root.resolve()
    files = source_files(root)
    db_path = safe_path(root,DATABASE)
    db_path.parent.mkdir(parents=True,exist_ok=True)
    # One transaction makes a successful index update visible atomically to readers.
    with closing(sqlite3.connect(db_path)) as db, db:
        db.executescript('''CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY,digest TEXT);
        CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY,path TEXT,kind TEXT,name TEXT,start INTEGER,end INTEGER,text TEXT);
        CREATE TABLE IF NOT EXISTS edges(src TEXT,dst TEXT,kind TEXT,provenance TEXT, UNIQUE(src,dst,kind));''')
        old = dict(db.execute('SELECT path,digest FROM files'))
        db.execute('DELETE FROM edges')
        db.execute('DELETE FROM nodes')
        db.execute('DELETE FROM files')
        for path,data in sorted(files.items()):
            text=data.decode('utf-8')
            db.execute('INSERT INTO files VALUES (?,?)',(path,sha(data)))
            nodes,edges=extract(path,text)
            db.executemany('INSERT INTO nodes VALUES (:id,:path,:kind,:name,:start,:end,:text)',nodes)
            db.executemany('INSERT OR IGNORE INTO edges VALUES (?,?,?,?)',edges)
            if Path(path).suffix in {'.md','.mdx'}:
                for target in re.findall(r'(?<!!)\[[^\]\n]+\]\(([^)\s]+)\)',text):
                    if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):
                        continue
                    plain=unquote(target.split('#')[0].split('?')[0])
                    resolved=(root/plain.lstrip('/') if plain.startswith('/') else (root/path).parent/plain).resolve()
                    if resolved.is_relative_to(root):
                        dst=resolved.relative_to(root).as_posix()
                        if dst in files:
                            db.execute('INSERT OR IGNORE INTO edges VALUES (?,?,?,?)',(path,dst,'references','explicit-markdown-link'))
        links_path=safe_path(root,'.seed/context-links.json')
        from .features import links as feature_links
        declared=feature_links(root, files)
        if links_path.exists():
            links=json.loads(links_path.read_text(encoding='utf-8'))
            if not isinstance(links,list): raise ValueError('context-links.json must be an array')
            declared.extend(links)
        if declared:
            for link in declared:
                if set(link) != {'source','target','relation'} or link['relation'] not in {'documents','tests','implements','decides','depends_on'}:
                    raise ValueError('Invalid explicit context link')
                def endpoint(value):
                    if not isinstance(value,str):raise ValueError('Context endpoints must be strings')
                    if value in files:return value
                    path,separator,selector=value.partition('#')
                    kind,colon,name=selector.partition(':')
                    if not separator or not colon or kind not in {'symbol','section'} or path not in files:
                        raise ValueError('Context endpoint must reference an indexed file, #symbol:Name or #section:Heading')
                    rows=db.execute('SELECT id FROM nodes WHERE path=? AND kind=? AND name=? ORDER BY start',(path,kind,name)).fetchall()
                    if len(rows)!=1:raise ValueError('Unknown or ambiguous context endpoint; choose one bounded section/symbol')
                    return rows[0][0]
                src,dst=endpoint(link['source']),endpoint(link['target'])
                db.execute('INSERT OR IGNORE INTO edges VALUES (?,?,?,?)',
                           (src,dst,link['relation'],'user-declared-not-proven-coverage'))
        policy_hash=sha(dump(exclusions(root)).encode())
        metadata={'fingerprint':fingerprint(files),'policy_hash':policy_hash,'built_at':now(),
                  'root':str(root),'schema_version':INDEX_SCHEMA}
        db.executemany('INSERT OR REPLACE INTO metadata VALUES (?,?)',metadata.items())
        counts={k:db.execute('SELECT COUNT(*) FROM '+k).fetchone()[0] for k in ('files','nodes','edges')}
    return {'status':'INDEXED',**counts,'changed_files':sum(old.get(p)!=sha(b) for p,b in files.items()),
            'removed_files':len(set(old)-set(files)), 'index_fingerprint':metadata['fingerprint'],
            'update_strategy':'transactional full rebuild; change counts are not incremental parsing'}


class Context:
    def __init__(self,root: Path):
        self.root=root.resolve()

    def connect(self):
        p=safe_path(self.root,DATABASE)
        if not p.is_file(): raise ValueError('NO_INDEX: run scripts/seed_context.py index')
        db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
        db.row_factory=sqlite3.Row
        return db

    def status(self) -> dict:
        with closing(self.connect()) as db:
            meta=dict(db.execute('SELECT key,value FROM metadata'))
            fresh=(meta.get('schema_version')==INDEX_SCHEMA and meta.get('root')==str(self.root) and
                   meta.get('fingerprint')==fingerprint(source_files(self.root)) and
                   meta.get('policy_hash')==sha(dump(exclusions(self.root)).encode()))
            return {'status':'FRESH' if fresh else 'STALE','built_at':meta.get('built_at'),
                    'index_fingerprint':meta.get('fingerprint'),
                    'scope':'Markdown sections, Python AST definitions, generic chunks and declared links; no compiler call graph or embeddings'}

    def fresh(self):
        status=self.status()
        if status['status']!='FRESH': raise ValueError('STALE_INDEX: reindex before relying on results')
        return status

    def _page(self, status, key, rows, offset, limit, max_chars, extra):
        bounded_int(offset, 0, 100_000)
        bounded_int(max_chars, 500, 30000)
        response = {**status, **extra, key: [], 'truncated': False, 'continuation': None,
                    'budget_unit': 'serialized JSON characters, not tokens', 'returned_chars': 0}
        selected = rows[offset:offset + limit]
        for row in selected:
            response[key].append(row)
            response['truncated'] = offset + len(response[key]) < len(rows)
            response['continuation'] = {'offset': offset + len(response[key])} if response['truncated'] else None
            if len(dump(response)) + 10 > max_chars:
                response[key].pop()
                break
        response['truncated'] = offset + len(response[key]) < len(rows)
        response['continuation'] = ({'offset': offset + len(response[key])}
                                    if response['truncated'] and response[key] else None)
        if response['truncated'] and not response[key]:
            response['note'] = 'No item fits this budget; increase max_chars or use a specific source locator.'
        response['returned_chars'] = len(dump(response)) + 10
        if len(dump(response)) > max_chars:
            response = {'status':status['status'],'index_fingerprint':status['index_fingerprint'],
                        key:[],'truncated':bool(rows),'continuation':None,
                        'reason':'BUDGET_TOO_SMALL_FOR_ITEM','returned_chars':0}
            response['returned_chars']=len(dump(response))+10
        return response

    def search(self, query: str, limit=6, max_chars=12000, offset=0) -> dict:
        bounded_int(limit,1,20); bounded_int(max_chars,500,30000)
        if not isinstance(query,str) or not query.strip() or len(query)>1000:
            raise ValueError('Invalid query')
        status=self.fresh()
        words=set(re.findall(r'[\w]+',query.casefold()))
        ranked=[]
        with closing(self.connect()) as db:
            for row in db.execute('SELECT * FROM nodes'):
                result=dict(row); name=result['name'].casefold(); text=result['text'].casefold()
                score=sum(5 for word in words if word in name)+sum(1 for word in words if word in text)
                if query.casefold()==name: score+=30
                # Old release narratives should not outrank current operating instructions.
                if result['path'].startswith(('docs/releases/','docs/research/')): score *= .75
                if score: ranked.append((score,result))
        ranked.sort(key=lambda item:(-item[0],item[1]['path'],item[1]['start']))
        items=[]
        for score,result in ranked:
            text=result.pop('text')
            # Center the locator on an actual match rather than only the first 1800 chars.
            positions=[text.casefold().find(word) for word in words if word in text.casefold()]
            start=max(0,min(positions,default=0)-180)
            size=min(1800,max(80,max_chars//3))
            result.update(excerpt=text[start:start+size], excerpt_offset=start, score=score,
                          provenance='parser/lexical-match', excerpt_may_be_truncated=True)
            items.append(result)
        return self._page(status,'items',items,offset,limit,max_chars,{'query':query})

    def symbol(self, name: str, limit=10, max_chars=12000, offset=0) -> dict:
        bounded_int(limit,1,20); status=self.fresh()
        if not isinstance(name,str) or not name or len(name)>300:
            raise ValueError('Invalid symbol name')
        with closing(self.connect()) as db:
            rows=[dict(row) for row in db.execute("SELECT id,path,kind,name,start,end FROM nodes WHERE kind='symbol' AND (name=? OR name LIKE ?) ORDER BY path,start",(name,'%.'+name))]
        return self._page(status,'items',rows,offset,limit,max_chars,
                          {'resolution':'Python definitions only; no inferred call targets'})

    def related(self, target: str, hops=1, limit=20, max_chars=12000, offset=0) -> dict:
        bounded_int(hops,1,2); bounded_int(limit,1,50); status=self.fresh()
        queue=deque([(target,0)]); seen={target}; edges={}; exploration_limited=False
        weights={'tests':0,'documents':1,'implements':2,'decides':3,'depends_on':4,'references':5,'contains':6}
        with closing(self.connect()) as db:
            if not db.execute('SELECT 1 FROM nodes WHERE id=?',(target,)).fetchone():
                return {**status,'edges':[],'unknown_target':True}
            while queue:
                node,depth=queue.popleft()
                if depth>=hops: continue
                neighbors=[dict(row) for row in db.execute('SELECT * FROM edges WHERE src=? OR dst=?',(node,node))]
                neighbors.sort(key=lambda edge:(weights.get(edge['kind'],9),edge['src'],edge['dst']))
                for edge in neighbors:
                    key=(edge['src'],edge['dst'],edge['kind'])
                    edges[key]=edge
                    other=edge['dst'] if edge['src']==node else edge['src']
                    if other not in seen:
                        seen.add(other); queue.append((other,depth+1))
                    if len(edges)>=5000:
                        exploration_limited=True; break
                if exploration_limited: break
        ordered=sorted(edges.values(),key=lambda edge:(weights.get(edge['kind'],9),edge['src'],edge['dst']))
        return self._page(status,'edges',ordered,offset,limit,max_chars,
                          {'exploration_limited':exploration_limited,
                           'note':'Declared test links are traceability, not coverage proof.'})

    def read(self, path: str, start=1, end=80, max_chars=12000, offset_chars=0,
             expected_sha256: str | None = None) -> dict:
        bounded_int(start,1,10_000_000); bounded_int(end,start,min(start+199,10_000_000))
        bounded_int(max_chars,1000,30000); bounded_int(offset_chars,0,MAX_FILE)
        status=self.fresh()
        with closing(self.connect()) as db:
            row=db.execute('SELECT digest FROM files WHERE path=?',(path,)).fetchone()
        if not row: raise ValueError('Only indexed, approved files may be read')
        data=safe_path(self.root,path).read_bytes(); checksum=sha(data)
        if checksum!=row['digest'] or (expected_sha256 is not None and expected_sha256!=checksum):
            raise ValueError('STALE_SOURCE: source changed; restart the read after reindex')
        lines=data.decode('utf-8').splitlines(keepends=True)
        text=''.join(lines[start-1:end])
        if offset_chars>len(text): raise ValueError('Read continuation is beyond selected source')
        response={**status,'path':path,'start':start,'end':min(end,len(lines)),
                  'content':'','content_offset_chars':offset_chars,
                  'file_offset_chars':sum(len(line) for line in lines[:start-1])+offset_chars,
                  'source_sha256':checksum,'provenance':'current-source-sha256:'+checksum,
                  'truncated':False,'continuation':None,
                  'budget_unit':'serialized JSON characters, not tokens'}
        def page(length):
            next_offset=offset_chars+length
            response['content']=text[offset_chars:next_offset]
            response['truncated']=next_offset<len(text)
            response['continuation']=({'path':path,'start':start,'end':end,
                                       'offset_chars':next_offset,'expected_sha256':checksum,
                                       'max_chars':max_chars} if response['truncated'] else None)
        low,high=0,len(text)-offset_chars
        while low<high:
            mid=(low+high+1)//2; page(mid)
            if len(dump(response))<=max_chars: low=mid
            else: high=mid-1
        page(low)
        if len(dump(response))>max_chars or (low==0 and offset_chars<len(text)):
            raise ValueError('RESULT_TOO_LARGE: increase max_chars')
        return response
