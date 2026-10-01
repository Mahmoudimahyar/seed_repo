"""Optional local decision lifecycle. No commands, models, network, or approval creation.

SQLite serializes writers on ONE local filesystem. Records and hashes are not identities,
policy enforcement, or tamper-proof signatures. Keep the store private; use reviewed
exports for handoff and an authoritative external system for distributed teams.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hmac
import json
from pathlib import Path
import sqlite3
import uuid

from .common import dump, has_secret, is_private, read_json, safe_path, sha
from .governance import validate

DB_PATH = '.seed-local/decisions.sqlite'
TERMINAL = {'resolved', 'out-of-scope', 'superseded'}
BOUNDARY = ('Planning records are evidence, not authorization. No commands or external '
            'actions are executed; real authority and budget enforcement belong to the executor.')


def checked(kind: str, document: dict) -> None:
    errors = validate(kind, document)
    if errors or has_secret(dump(document)):
        # Do not echo schemas' values: errors may contain sensitive user input.
        raise ValueError(f'Invalid {kind}: check the schema, filled fields, and secret policy')


def digest(document) -> str:
    return sha(json.dumps(document, sort_keys=True, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':')).encode())


def check_graph(documents: list[dict]) -> None:
    """Validate IDs and outcome-aware references, then detect cycles without recursion."""
    by_id = {item['id']: item for item in documents}
    if len(by_id) != len(documents):
        raise ValueError('Duplicate decision ticket ID')
    pending = {}
    for item in documents:
        deps = [d['ticket_id'] for d in item['depends_on']]
        if len(deps) != len(set(deps)) or any(d not in by_id for d in deps):
            raise ValueError('Duplicate or missing decision dependency')
        pending[item['id']] = set(deps)
    settled = set()
    while pending:
        eligible = {key for key, deps in pending.items() if deps <= settled}
        if not eligible:
            raise ValueError('Cyclic decision dependencies')
        settled |= eligible
        pending = {key: deps for key, deps in pending.items() if key not in eligible}


def evidence_path(root: Path, reference: str) -> Path:
    # Canonical POSIX-relative names make manifests portable across platforms.
    if not isinstance(reference, str) or '\\' in reference or ':' in reference:
        raise ValueError('Evidence must use a portable repository-relative file path')
    path = safe_path(root, reference)
    if is_private(reference) or reference != path.relative_to(root.resolve()).as_posix():
        raise ValueError('Private or noncanonical path cannot be planning evidence')
    return path


def file_hash(root: Path, reference: str) -> str:
    path = evidence_path(root, reference)
    if not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError('Evidence is missing, not a file, or exceeds the 2 MB limit')
    data = path.read_bytes()
    if has_secret(data.decode('utf-8', errors='replace')):
        raise ValueError('Possible credential material in evidence; inspect privately')
    return sha(data)


class PlanningStore:
    def __init__(self, root: Path, clock=None, *, storage_root: Path | None = None):
        self.root = root.resolve()
        self.storage_root = (storage_root or root).resolve()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @contextmanager
    def connection(self, write=False, create=False, stopping_ok=False):
        path = safe_path(self.storage_root, DB_PATH)
        for suffix in ('-wal', '-shm', '-journal'):
            safe_path(self.storage_root, DB_PATH + suffix)
        if write and not stopping_ok and safe_path(self.root, '.seed-local/STOP').exists():
            raise ValueError('Emergency stop active; planning mutations are stopped')
        if not path.exists() and not create:
            raise ValueError('No local decision store; create or import a map explicitly')
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
        uri = path.as_uri() + ('?mode=rwc' if create else '?mode=rw' if write else '?mode=ro')
        con = sqlite3.connect(uri, uri=True, timeout=5, isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            con.execute('PRAGMA foreign_keys=ON')
            con.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            if create:
                for statement in (
                    'CREATE TABLE IF NOT EXISTS maps (id TEXT PRIMARY KEY, revision INTEGER, lineage TEXT, document TEXT)',
                    'CREATE TABLE IF NOT EXISTS tickets (map_id TEXT REFERENCES maps(id), id TEXT, row_json TEXT, PRIMARY KEY(map_id,id))',
                    'CREATE TABLE IF NOT EXISTS claims (map_id TEXT, ticket_id TEXT, owner TEXT, token_hash TEXT, expires_at TEXT, PRIMARY KEY(map_id,ticket_id))',
                    'CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, map_id TEXT, ticket_id TEXT, event TEXT, revision INTEGER, recorded_at TEXT, document TEXT)',
                    'CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)',
                ):
                    con.execute(statement)
            yield con
            con.commit()
        except sqlite3.Error as exc:
            con.rollback()
            raise ValueError('Local planner database conflict or invalid store; inspect recovery') from exc
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    def _map(self, con, map_id):
        row = con.execute('SELECT * FROM maps WHERE id=?', (map_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown decision map')
        return {'document': json.loads(row['document']), 'revision': row['revision'], 'lineage': row['lineage']}

    def _rows(self, con, map_id):
        return {r['id']: json.loads(r['row_json']) for r in con.execute(
            'SELECT * FROM tickets WHERE map_id=? ORDER BY id', (map_id,))}

    def _row(self, con, map_id, ticket_id, expected=None):
        rows = self._rows(con, map_id)
        if ticket_id not in rows:
            raise ValueError('Unknown decision ticket')
        row = rows[ticket_id]
        if expected is not None and (type(expected) is not int or row['revision'] != expected):
            raise ValueError('Ticket revision conflict; reread before modifying')
        return row

    def _event(self, con, map_id, ticket_id, event, revision, document):
        con.execute('INSERT INTO events(map_id,ticket_id,event,revision,recorded_at,document) VALUES(?,?,?,?,?,?)',
                    (map_id, ticket_id, event, revision, self.clock().isoformat(), dump(document)))

    def _save(self, con, map_id, row, event):
        ticket_id = row['document']['id']
        con.execute('INSERT INTO tickets VALUES(?,?,?) ON CONFLICT(map_id,id) DO UPDATE SET row_json=excluded.row_json',
                    (map_id, ticket_id, dump(row)))
        self._event(con, map_id, ticket_id, event, row['revision'], row)

    def _paths(self, document):
        refs = document['required_evidence'] + [document['authority']['policy_ref']]
        if document['workflow_contract']:
            refs.append(document['workflow_contract'])
        for ref in refs:
            evidence_path(self.root, ref)
        return refs

    def create(self, document):
        checked('decision-map', document)
        if len({f['id'] for f in document['fog']}) != len(document['fog']):
            raise ValueError('Duplicate fog ID')
        with self.connection(write=True, create=True) as con:
            if con.execute('SELECT 1 FROM maps WHERE id=?', (document['id'],)).fetchone():
                raise ValueError('Decision map already exists; never overwrite it')
            con.execute('INSERT INTO maps VALUES(?,?,?,?)', (document['id'], 1, str(uuid.uuid4()), dump(document)))
            self._event(con, document['id'], None, 'created', 1, document)
        return {'map_id': document['id'], 'revision': 1}

    def revise_map(self, document, expected):
        checked('decision-map', document)
        if len({f['id'] for f in document['fog']}) != len(document['fog']):
            raise ValueError('Duplicate fog ID')
        with self.connection(write=True) as con:
            old = self._map(con, document['id'])
            if type(expected) is not int or old['revision'] != expected:
                raise ValueError('Map revision conflict')
            if self._live_claims(con, document['id']):
                raise ValueError('Release active claims before revising a map')
            con.execute('UPDATE maps SET revision=?, document=? WHERE id=?', (expected+1, dump(document), document['id']))
            self._event(con, document['id'], None, 'revised', expected+1, document)
        return {'map_id': document['id'], 'revision': expected+1}

    def add(self, map_id, document):
        checked('decision-ticket', document)
        self._paths(document)
        with self.connection(write=True) as con:
            self._map(con, map_id)
            rows = self._rows(con, map_id)
            if document['id'] in rows or len(rows) >= 500:
                raise ValueError('Duplicate ticket or 500-ticket local map limit reached')
            check_graph([r['document'] for r in rows.values()] + [document])
            row = {'document': document, 'revision': 1, 'state': 'open', 'resolution': None, 'replacement': None}
            self._save(con, map_id, row, 'created')
        return row

    def revise(self, map_id, document, expected):
        checked('decision-ticket', document)
        self._paths(document)
        with self.connection(write=True) as con:
            self._row(con, map_id, document['id'], expected)
            if document['id'] in self._live_claims(con, map_id):
                raise ValueError('Release active claim before revising a ticket')
            rows = self._rows(con, map_id)
            check_graph([r['document'] for key, r in rows.items() if key != document['id']] + [document])
            row = {'document': document, 'revision': expected+1, 'state': 'open', 'resolution': None, 'replacement': None}
            self._save(con, map_id, row, 'revised')
        return row

    def _live_claims(self, con, map_id):
        return {r['ticket_id']: dict(r) for r in con.execute('SELECT * FROM claims WHERE map_id=?', (map_id,))
                if datetime.fromisoformat(r['expires_at']) > self.clock()}

    def _evaluate(self, con, map_id):
        metadata = self._map(con, map_id)
        rows = self._rows(con, map_id)
        check_graph([r['document'] for r in rows.values()])
        claims = self._live_claims(con, map_id)
        scope_hash = digest(metadata)
        results = {}
        remaining = set(rows)
        while remaining:
            for key in sorted(remaining):
                row = rows[key]; doc = row['document']
                if any(d['ticket_id'] not in results for d in doc['depends_on']):
                    continue
                reasons = []
                dependency_hashes = {}
                for dep in doc['depends_on']:
                    value = results[dep['ticket_id']]
                    dependency_hashes[dep['ticket_id']] = value['signature']
                    if value['effective_state'] != 'resolved' or value['resolution']['outcome'] not in dep['allowed_outcomes']:
                        reasons.append('Unsatisfied dependency: ' + dep['ticket_id'])
                for ref in self._paths(doc):
                    try: file_hash(self.root, ref)
                    except (OSError, ValueError): reasons.append('Unavailable/unsafe evidence: ' + ref)
                if doc['resolver'] in {'prototype', 'prerequisite'} and not doc['workflow_contract']:
                    reasons.append('An isolated, governed workflow contract is required')
                if doc['workflow_contract']:
                    try:
                        checked('workflow', read_json(evidence_path(self.root, doc['workflow_contract'])))
                    except (OSError, ValueError): reasons.append('Invalid workflow contract')
                proof = row['resolution']
                if row['state'] in TERMINAL:
                    if proof is None:
                        reasons.append('Terminal state lacks a resolution')
                    else:
                        if proof['map_sha256'] != scope_hash: reasons.append('Map scope/revision changed')
                        if proof['dependencies'] != dependency_hashes: reasons.append('Dependency revision changed')
                        if proof['expires_at'] and datetime.fromisoformat(proof['expires_at']) <= self.clock():
                            reasons.append('Scoped exception/decision expired')
                        for ref, expected in proof['files'].items():
                            try: current = file_hash(self.root, ref)
                            except (OSError, ValueError): current = None
                            if current != expected: reasons.append('Evidence changed: ' + ref)
                    effective = 'stale' if reasons else row['state']
                elif reasons:
                    effective = 'blocked'
                elif key in claims:
                    effective = 'exploring'
                elif row['state'] == 'awaiting-human' or doc['resolver'] == 'interview' or doc['authority']['mode'] == 'human_required':
                    effective = 'awaiting-human'
                else:
                    effective = 'open'
                signature = digest({'row': row, 'map': scope_hash, 'dependencies': dependency_hashes})
                claim = claims.get(key)
                public_claim = {'owner': claim['owner'], 'expires_at': claim['expires_at']} if claim else None
                results[key] = {**row, 'effective_state': effective, 'reasons': reasons,
                                'signature': signature, 'claim': public_claim}
                remaining.remove(key)
        return metadata, results

    def get(self, map_id, ticket_id):
        with self.connection() as con:
            _, rows = self._evaluate(con, map_id)
            if ticket_id not in rows: raise ValueError('Unknown ticket')
            return rows[ticket_id]

    def _claim(self, con, map_id, ticket_id, token):
        claim = self._live_claims(con, map_id).get(ticket_id)
        if not claim or not isinstance(token, str) or not hmac.compare_digest(claim['token_hash'], sha(token.encode())):
            raise ValueError('Claim missing, expired, or not owned by this token')
        return claim

    def _ttl(self, row, seconds):
        maximum = min(3600, row['document']['budgets']['max_minutes'] * 60)
        if type(seconds) is not int or not 1 <= seconds <= maximum:
            raise ValueError(f'Claim TTL must be in [1, {maximum}] seconds')
        return (self.clock()+timedelta(seconds=seconds)).isoformat()

    def claim(self, map_id, ticket_id, owner, expected, ttl_seconds=300):
        if not isinstance(owner, str) or not owner.strip() or len(owner) > 120 or has_secret(owner):
            raise ValueError('Use a bounded, unique run identity for the claim')
        with self.connection(write=True) as con:
            self._row(con, map_id, ticket_id, expected)
            metadata, rows = self._evaluate(con, map_id)
            row = rows[ticket_id]
            if row['effective_state'] not in {'open', 'awaiting-human'}:
                raise ValueError('Ticket is not eligible or is already claimed')
            if len(self._live_claims(con, map_id)) >= metadata['document']['max_parallel_claims']:
                raise ValueError('Planning concurrency capacity reached')
            token = uuid.uuid4().hex
            expires = self._ttl(row, ttl_seconds)
            con.execute('INSERT INTO claims VALUES(?,?,?,?,?) ON CONFLICT(map_id,ticket_id) DO UPDATE SET owner=excluded.owner, token_hash=excluded.token_hash, expires_at=excluded.expires_at',
                        (map_id, ticket_id, owner, sha(token.encode()), expires))
            return {'map_id': map_id, 'ticket_id': ticket_id, 'token': token, 'expires_at': expires,
                    'boundary': BOUNDARY}

    def renew(self, map_id, ticket_id, token, ttl_seconds=300):
        with self.connection(write=True) as con:
            self._claim(con, map_id, ticket_id, token)
            row = self._row(con, map_id, ticket_id)
            expires = self._ttl(row, ttl_seconds)
            con.execute('UPDATE claims SET expires_at=? WHERE map_id=? AND ticket_id=?', (expires, map_id, ticket_id))
            return {'expires_at': expires}

    def release(self, map_id, ticket_id, token):
        with self.connection(write=True, stopping_ok=True) as con:
            self._claim(con, map_id, ticket_id, token)
            con.execute('DELETE FROM claims WHERE map_id=? AND ticket_id=?', (map_id, ticket_id))
        return {'status': 'RELEASED'}

    def resolve(self, map_id, ticket_id, record_path, expected, token, terminal='resolved', replacement=None):
        if terminal not in TERMINAL:
            raise ValueError('Use a supported terminal state')
        with self.connection(write=True) as con:
            self._claim(con, map_id, ticket_id, token)
            self._row(con, map_id, ticket_id, expected)
            metadata, rows = self._evaluate(con, map_id)
            row = rows[ticket_id]; doc = row['document']
            if row['effective_state'] != 'exploring':
                raise ValueError('Dependencies/evidence changed; resolution is blocked')
            if terminal == 'superseded':
                if replacement not in rows or replacement == ticket_id:
                    raise ValueError('Supersession requires a distinct existing replacement')
                cursor, visited = replacement, {ticket_id}
                while cursor is not None:
                    if cursor in visited:
                        raise ValueError('Cyclic supersession is not permitted')
                    visited.add(cursor)
                    cursor = rows[cursor]['replacement']
            elif replacement is not None:
                raise ValueError('Replacement applies only to supersession')
            file_hash(self.root, record_path)  # Enforce size/path policy before parsing.
            record = read_json(evidence_path(self.root, record_path))
            checked('decision', record)
            if record['workflow_id'] != ticket_id or record['scope'] != metadata['document']['scope']:
                raise ValueError('Decision ticket identity or scope mismatch')
            if record['outcome'] not in {'accepted', 'rejected'}:
                raise ValueError('Only accepted/rejected decisions settle a question')
            authority = record['authority']
            human_needed = doc['authority']['mode'] == 'human_required' or doc['resolver'] == 'interview' or terminal != 'resolved'
            if human_needed and (authority['kind'] != 'human_approval' or authority['actor'] != doc['authority']['owner']):
                raise ValueError('Recorded approval from the accountable human is required')
            if record['policy_sha256'] != file_hash(self.root, doc['authority']['policy_ref']):
                raise ValueError('Decision policy hash does not match the current policy')
            if datetime.fromisoformat(record['recorded_at'].replace('Z','+00:00')) > self.clock():
                raise ValueError('Decision timestamp is in the future')
            if record['expires_at'] and datetime.fromisoformat(record['expires_at'].replace('Z','+00:00')) <= self.clock():
                raise ValueError('Decision or exception already expired')
            refs = set(self._paths(doc)+record['evidence_refs']+[record_path, authority['evidence_reference']])
            if record['observed_result_reference']: refs.add(record['observed_result_reference'])
            if len(refs) > 300:
                raise ValueError('Resolution evidence exceeds the bounded snapshot size')
            proof = {'path': record_path, 'outcome': record['outcome'], 'expires_at': record['expires_at'],
                     'files': {ref: file_hash(self.root, ref) for ref in sorted(refs)},
                     'dependencies': {dep['ticket_id']: rows[dep['ticket_id']]['signature'] for dep in doc['depends_on']},
                     'map_sha256': digest(metadata)}
            new = {'document': doc, 'revision': expected+1, 'state': terminal,
                   'resolution': proof, 'replacement': replacement}
            self._save(con, map_id, new, terminal)
            con.execute('DELETE FROM claims WHERE map_id=? AND ticket_id=?', (map_id, ticket_id))
        return new

    def select(self, map_id):
        with self.connection(write=True) as con:
            self._map(con, map_id)
            con.execute("INSERT INTO settings VALUES('selected',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (map_id,))
        return {'selected_map': map_id, 'note': 'Selection is a local hint; parallel sessions must pass --map explicitly.'}

    def handoff(self, map_id=None, ticket_id=None, limit=8):
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError('Handoff limit must be 1..20')
        with self.connection() as con:
            if map_id is None:
                selected = con.execute("SELECT value FROM settings WHERE key='selected'").fetchone()
                ids = [r['id'] for r in con.execute('SELECT id FROM maps ORDER BY id')]
                if selected: map_id = selected['value']
                elif len(ids) == 1: map_id = ids[0]
                else: raise ValueError('Choose an explicit map; never infer it from modification time')
            metadata, rows = self._evaluate(con, map_id)
            if ticket_id and ticket_id not in rows: raise ValueError('Unknown ticket')
            ordered = sorted(rows.items(), key=lambda pair: (pair[1]['document']['priority'], pair[0]))
            def card(key, row):
                doc = row['document']
                return {'id': key, 'revision': row['revision'], 'question': doc['question'],
                        'resolver': doc['resolver'], 'state': row['effective_state'],
                        'priority_reason': doc['priority_reason'], 'reasons': row['reasons'][:8],
                        'evidence_refs': doc['required_evidence'][:8], 'evidence_requirements': doc['evidence_requirements'][:8], 'authority': doc['authority'],
                        'budgets': doc['budgets'], 'workflow_contract': doc['workflow_contract'],
                        'resolution_ref': row['resolution']['path'] if row['resolution'] else None,
                        'claim': row['claim'],
                        'truncated': any(len(items)>8 for items in (row['reasons'], doc['required_evidence'], doc['evidence_requirements']))}
            frontier = [(key,row) for key,row in ordered if row['effective_state'] in {'open','awaiting-human'}]
            blocked = [(key,row) for key,row in ordered if row['effective_state'] in {'blocked','stale'}]
            active = card(ticket_id, rows[ticket_id]) if ticket_id else None
            dependencies = []
            if ticket_id:
                dependencies = [card(d['ticket_id'], rows[d['ticket_id']]) for d in rows[ticket_id]['document']['depends_on'][:limit]]
            spec = metadata['document']
            return {'map_id': map_id, 'map_revision': metadata['revision'], 'destination': spec['destination'],
                    'scope': spec['scope'], 'constraints': spec['constraints'], 'exclusions': spec['exclusions'],
                    'fog': spec['fog'][:limit], 'active_ticket': active, 'prerequisites': dependencies,
                    'frontier': [card(k,r) for k,r in frontier[:limit]],
                    'blocked': [card(k,r) for k,r in blocked[:limit]],
                    'counts': {state: sum(r['effective_state']==state for r in rows.values()) for state in
                               ('open','awaiting-human','exploring','blocked','stale','resolved','superseded','out-of-scope')},
                    'truncated': (len(frontier)>limit or len(blocked)>limit or len(spec['fog'])>limit
                                  or bool(ticket_id and len(rows[ticket_id]['document']['depends_on'])>limit)
                                  or any(card(k,r)['truncated'] for k,r in frontier[:limit]+blocked[:limit])
                                  or any(c['truncated'] for c in dependencies)
                                  or bool(active and active['truncated'])),
                    'boundary': BOUNDARY,
                    'next_action': 'Resolve eligible questions with their stated evidence; ask the owner for nondelegated decisions. Do not start production from a map.'}

    def requirements_snapshot(self, map_id, requirements):
        if not isinstance(requirements, list) or not requirements:
            raise ValueError('Choose explicit required decisions, not an empty implicit map')
        with self.connection() as con:
            metadata, rows = self._evaluate(con, map_id)
            selected = {}
            for req in requirements:
                if not isinstance(req, dict) or set(req) != {'ticket_id','allowed_outcomes'}:
                    raise ValueError('Invalid decision requirement')
                key = req['ticket_id']; allowed = req['allowed_outcomes']
                if not isinstance(key, str) or key in selected or not isinstance(allowed,list) or not allowed or any(o not in {'accepted','rejected'} for o in allowed):
                    raise ValueError('Invalid/duplicate required decision or outcomes')
                row = rows.get(key)
                if not row or row['effective_state'] != 'resolved' or row['resolution']['outcome'] not in allowed:
                    raise ValueError('Required decision is unresolved, stale, or has an unacceptable outcome: '+key)
                selected[key] = row['signature']
            return {'map_id': map_id, 'map_sha256': digest(metadata), 'decisions': dict(sorted(selected.items()))}

    def history(self, map_id, ticket_id=None, limit=100):
        if type(limit) is not int or not 1 <= limit <= 20000: raise ValueError('Invalid history limit')
        with self.connection() as con:
            self._map(con, map_id)
            sql = 'SELECT * FROM events WHERE map_id=?'; params = [map_id]
            if ticket_id: sql += ' AND ticket_id=?'; params.append(ticket_id)
            sql += ' ORDER BY sequence DESC LIMIT ?'; params.append(limit)
            return [{k: json.loads(row[k]) if k=='document' else row[k] for k in
                     ('sequence','ticket_id','event','revision','recorded_at','document')} for row in con.execute(sql, params)]

    def export(self, map_id):
        # One read transaction yields a consistent portable snapshot, excluding leases and selection.
        with self.connection() as con:
            metadata = self._map(con, map_id)
            events = [{k: json.loads(row[k]) if k=='document' else row[k] for k in
                       ('sequence','ticket_id','event','revision','recorded_at','document')}
                      for row in con.execute('SELECT * FROM events WHERE map_id=? ORDER BY sequence', (map_id,))]
            return {'schema_version': 1, 'backend': 'seed-local-snapshot', 'map': metadata,
                    'tickets': list(self._rows(con, map_id).values()), 'events': events}

    def import_snapshot(self, snapshot):
        checked('planning-snapshot', snapshot)
        metadata = snapshot['map']; spec = metadata['document']; map_id = spec['id']
        check_graph([row['document'] for row in snapshot['tickets']])
        ids = {row['document']['id'] for row in snapshot['tickets']}
        if len({item['id'] for item in spec['fog']}) != len(spec['fog']):
            raise ValueError('Duplicate fog ID in snapshot')
        by_id = {row['document']['id']: row for row in snapshot['tickets']}
        for key in ids:
            cursor, visited = key, set()
            while cursor is not None:
                if cursor not in by_id or cursor in visited:
                    raise ValueError('Invalid or cyclic supersession in snapshot')
                visited.add(cursor)
                cursor = by_id[cursor]['replacement']
        for row in snapshot['tickets']:
            self._paths(row['document'])
            if row['replacement'] and (row['replacement'] not in ids or row['replacement']==row['document']['id']):
                raise ValueError('Invalid supersession target in snapshot')
            if row['resolution']:
                proof = row['resolution']
                if not set(self._paths(row['document']) + [proof['path']]) <= set(proof['files']):
                    raise ValueError('Incomplete resolution evidence fingerprint')
                if set(proof['dependencies']) != {d['ticket_id'] for d in row['document']['depends_on']}:
                    raise ValueError('Resolution prerequisite fingerprint mismatch')
                for ref in [row['resolution']['path'], *row['resolution']['files']]: evidence_path(self.root, ref)
        sequences = [event['sequence'] for event in snapshot['events']]
        if sequences != sorted(set(sequences)):
            raise ValueError('Invalid event ordering in snapshot')
        with self.connection(write=True, create=True) as con:
            if con.execute('SELECT 1 FROM maps WHERE id=?',(map_id,)).fetchone():
                raise ValueError('Refusing to replace an authoritative local map')
            con.execute('INSERT INTO maps VALUES(?,?,?,?)',(map_id,metadata['revision'],metadata['lineage'],dump(spec)))
            for row in snapshot['tickets']:
                con.execute('INSERT INTO tickets VALUES(?,?,?)',(map_id,row['document']['id'],dump(row)))
            for event in snapshot['events']:
                con.execute('INSERT INTO events(map_id,ticket_id,event,revision,recorded_at,document) VALUES(?,?,?,?,?,?)',
                            (map_id,event['ticket_id'],event['event'],event['revision'],event['recorded_at'],dump(event['document'])))
        return {'status': 'IMPORTED_UNTRUSTED_SNAPSHOT', 'map_id': map_id,
                'note': 'No claims or new approval imported. Recheck sources and actual authority; snapshots are not signatures.'}
