"""Revision-bound recorded approval. This does not authenticate or authorize a person.

A proposal fingerprint excludes the approval text to avoid a circular hash. The real
approval evidence must mention that fingerprint; its own bytes are pinned separately.
No operation here writes files or manufactures an approval conversation.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import tempfile

from .common import sha, has_secret, safe_path, is_private


def digest(document):
    return sha(json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                          allow_nan=False).encode())


def evidence(root: Path, ref: str) -> tuple[str, str]:
    if not isinstance(ref, str) or ':' in ref or '\\' in ref or is_private(ref):
        raise ValueError('Private, unsafe, or invalid approval evidence path')
    path = safe_path(root, ref)
    if ref != path.relative_to(root.resolve()).as_posix() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError('Missing, oversized, or noncanonical approval evidence')
    data = path.read_bytes()
    text = data.decode('utf-8')
    if has_secret(text): raise ValueError('Possible secret in approval evidence; inspect privately')
    return sha(data), text


def propose(root: Path, record: dict, state: dict) -> dict:
    if record.get('schema_version') != 2:
        raise ValueError('Migrate readiness to schema_version 2; old unbound approvals are not valid')
    if not isinstance(record.get('approval'), dict):
        raise ValueError('Readiness approval must be an explicit object')
    gates = record.get('gates')
    if not isinstance(gates, list) or not gates:
        raise ValueError('Approval binding requires gate evidence')
    hashes = {}
    for gate in gates:
        if not isinstance(gate, dict) or set(gate) != {'id', 'status', 'evidence'}:
            raise ValueError('Invalid readiness gate')
        if not isinstance(gate['evidence'], list) or not gate['evidence']:
            raise ValueError('Gate lacks evidence')
        for ref in gate['evidence']:
            if ref == record.get('approval', {}).get('evidence'):
                raise ValueError('Approval text cannot also be gate evidence (circular binding)')
            hashes[ref] = evidence(root, ref)[0]
    planning = record.get('planning')
    if not isinstance(planning, list):
        raise ValueError('Readiness planning must be an explicit list, empty when not used')
    snapshots = []
    ids = set()
    for item in planning:
        if not isinstance(item, dict) or set(item) not in ({'map_id', 'requirements'}, {'map_id', 'requirements', 'snapshot'}):
            raise ValueError('Invalid readiness decision-map reference')
        if not isinstance(item['map_id'], str) or item['map_id'] in ids:
            raise ValueError('Duplicate or invalid planning scope')
        ids.add(item['map_id'])
        from .planning import PlanningStore, DB_PATH
        if item.get('snapshot'):
            # Portable evidence for a clean CI checkout. No authoritative local store
            # is created or overwritten; original source/policy files are rechecked.
            hashes[item['snapshot']] = evidence(root, item['snapshot'])[0]
            saved = json.loads(safe_path(root, item['snapshot']).read_text(encoding='utf-8'))
            with tempfile.TemporaryDirectory(prefix='seed-approval-') as directory:
                mirror = PlanningStore(root, storage_root=Path(directory))
                mirror.import_snapshot(saved)
                snapshot = mirror.requirements_snapshot(item['map_id'], item['requirements'])
            if safe_path(root, DB_PATH).exists():
                live = PlanningStore(root).requirements_snapshot(item['map_id'], item['requirements'])
                if live != snapshot:
                    raise ValueError('Published planning snapshot is stale relative to the local decision store')
        else:
            snapshot = PlanningStore(root).requirements_snapshot(item['map_id'], item['requirements'])
        snapshots.append(snapshot)
    from .features import scope as feature_scope
    registry, feature_hashes = feature_scope(root,state)
    hashes.update(feature_hashes)
    # Bind registered external research identities, not private cache bytes. Clean CI can
    # verify the approved manifest/evidence; task execution separately verifies used caches.
    from .external import MANIFEST, Sources
    sources = Sources(root).manifest()['sources']
    if sources:
        hashes[MANIFEST] = evidence(root, MANIFEST)[0]
        for source in sources.values():
            review = source['mapping']['review']
            if review is not None:
                actual = evidence(root, review['evidence'])[0]
                if actual != review['evidence_sha256']:
                    raise ValueError('External mapping evidence is stale')
                hashes[review['evidence']] = actual
    manifest = {'features':registry, 'integrations':state.get('integrations'), 'scope': record.get('scope'), 'project': state.get('project'),
                'capabilities': state.get('capabilities'), 'blocking_gaps': record.get('blocking_gaps'),
                'gates': gates, 'files': dict(sorted(hashes.items())), 'planning': snapshots}
    return {'schema_version': 1, 'manifest': manifest, 'sha256': digest(manifest)}


def verify(root: Path, record: dict, state: dict) -> list[str]:
    try:
        proposal = propose(root, record, state)
        approval = record.get('approval', {})
        if approval.get('binding') != proposal:
            return ['Approval binding is missing or stale; review changed scope/evidence before reapproval']
        checksum, text = evidence(root, approval.get('evidence'))
        if proposal['sha256'] not in text or approval.get('evidence_sha256') != checksum:
            return ['Approval evidence does not match the reviewed binding or its recorded bytes']
        return []
    except (ValueError, OSError, TypeError, KeyError, ImportError) as exc:
        return ['Approval binding cannot be verified: ' + str(exc)]


def record(root: Path, readiness: dict, state: dict, actor: str, reference: str, proposal: dict) -> dict:
    if not isinstance(actor, str) or not actor.strip() or len(actor) > 120 or has_secret(actor):
        raise ValueError('Record an accountable approver; never impersonate a user')
    current = propose(root, readiness, state)
    if proposal != current:
        raise ValueError('Proposal is stale; do not rebind an old approval to changed documents')
    if reference in current['manifest']['files']:
        raise ValueError('Approval text cannot also be gate evidence')
    checksum, text = evidence(root, reference)
    if current['sha256'] not in text:
        raise ValueError('Actual approval evidence must refer to the proposed SHA-256 fingerprint')
    result = deepcopy(readiness)
    result['approval'] = {'approved': True, 'by': actor, 'evidence': reference,
                          'evidence_sha256': checksum, 'binding': current}
    return result


def migrate(record: dict) -> dict:
    if not isinstance(record, dict) or record.get('schema_version') != 1:
        raise ValueError('Only unbound readiness schema_version 1 needs this migration')
    result = deepcopy(record)
    result.update(schema_version=2, planning=[])
    result['approval'] = {'approved': False, 'by': None, 'evidence': None,
                          'evidence_sha256': None, 'binding': None}
    return result
