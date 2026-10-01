"""Explicit active-feature evidence. Planned code/test paths are mappings, not proof.

The registry is the one declaration source; readiness hashes its active documents
and the context graph derives existing-file links from it. Deferred work stays optional.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re

from .common import read_json, dump, safe_path, is_private

REGISTRY = 'docs/project/features.json'
ROOTS = ('docs/features/', 'docs/project/features/')


def valid_root(value: str) -> bool:
    return any(value.startswith(prefix) and value[len(prefix):] and '/' not in value[len(prefix):]
               and value[len(prefix):] not in {'.', '..'} for prefix in ROOTS)


def load(root: Path) -> dict:
    from .governance import validate
    registry = read_json(safe_path(root, REGISTRY))
    errors = validate('feature-registry', registry)
    if errors:
        raise ValueError('Feature registry: ' + '; '.join(errors))
    ids = set()
    folders = set()
    for feature in registry['features']:
        if feature['id'] in ids or feature['doc_root'] in folders:
            raise ValueError('Duplicate feature ID or documentation root')
        ids.add(feature['id']); folders.add(feature['doc_root'])
        path = safe_path(root, feature['doc_root'])
        if (not valid_root(feature['doc_root']) or is_private(feature['doc_root'])
                or feature['doc_root'].endswith('/') or path.relative_to(root.resolve()).as_posix() != feature['doc_root']):
            raise ValueError('Feature docs must use a canonical docs/features/<id> or docs/project/features/<id> root')
        for ref in feature['code'] + feature['tests']:
            safe_path(root, ref)
            if is_private(ref) or '*' in ref:
                raise ValueError('Feature links require exact safe planned file paths')
    for prefix in ROOTS:
        base = safe_path(root, prefix)
        if not base.exists():
            continue
        for folder in base.iterdir():
            if folder.is_dir() and folder.relative_to(root).as_posix() not in folders:
                raise ValueError('Unregistered feature documentation: ' + folder.relative_to(root).as_posix())
    return registry


def scope(root: Path, state: dict) -> tuple[dict, dict[str, str]]:
    """Return registry and evidence digests for the exact active scope."""
    from .approvals import evidence
    registry = load(root)
    hashes = {REGISTRY: evidence(root, REGISTRY)[0]}
    for feature in registry['features']:
        if feature['status'] == 'deferred':
            continue
        if feature['ui'] and not state['capabilities']['ui']:
            raise ValueError('UI feature requires the approved UI capability')
        if not feature['tests']:
            raise ValueError('Active feature requires test-file mappings: ' + feature['id'])
        required = ['requirements.md', 'test-plan.md'] + (['ui-flow.md'] if feature['ui'] else [])
        folder = safe_path(root, feature['doc_root'])
        for name in required:
            if not (folder / name).is_file():
                raise ValueError('Missing active feature artifact: ' + feature['doc_root'] + '/' + name)
        # All documents within an active feature root are in its scope. New or removed
        # files affect the approval manifest too; no forgotten per-file registration.
        for path in sorted(folder.rglob('*')):
            if path.is_symlink():
                raise ValueError('Symlink feature evidence is forbidden')
            if not path.is_file():
                continue
            ref = path.relative_to(root).as_posix()
            checksum, text = evidence(root, ref)
            if len(text.strip()) < 30 or re.search(r'__FILL__|\bTBD\b|\bTODO\b|\{\{[^}]+\}\}', text):
                raise ValueError('Unfilled active feature artifact: ' + ref)
            hashes[ref] = checksum
        from .spec_trace import lint_feature
        lint_feature(root, feature)
    return registry, hashes


def register(root: Path, *, id: str, owner: str, doc_root: str, ui=False,
             code: list[str] | None = None, tests: list[str] | None = None) -> dict[str, str]:
    path = safe_path(root, REGISTRY)
    registry = read_json(path) if path.exists() else {'schema_version': 1, 'features': []}
    # Registration deliberately works while docs are incomplete: readiness does not.
    from .governance import validate
    if validate('feature-registry', registry):
        raise ValueError('Repair the existing feature registry before registering more work')
    if any(f['id'] == id or f['doc_root'] == doc_root for f in registry['features']):
        raise ValueError('Feature already registered; revise its scoped record through review')
    updated = deepcopy(registry)
    updated['features'].append({'id': id, 'owner': owner, 'status': 'active', 'reason': 'Included in the proposed implementation scope.',
                                'doc_root': doc_root, 'ui': ui, 'code': code or [], 'tests': tests or []})
    errors = validate('feature-registry', updated)
    safe_path(root, doc_root)
    if errors or not valid_root(doc_root) or is_private(doc_root):
        raise ValueError('Invalid feature registration: ' + '; '.join(errors))
    return {REGISTRY: dump(updated)}


def migrate(root: Path) -> dict[str, str]:
    """Preview an explicit migration; do not infer owners or approve discovered features."""
    readiness = read_json(safe_path(root, 'docs/project/readiness.json'))
    if readiness.get('schema_version') != 2:
        raise ValueError('Migrate readiness to version 2 first')
    if safe_path(root, REGISTRY).exists() and any(g['id'] == 'features' for g in readiness['gates']):
        raise ValueError('Feature registry is already enabled')
    result = deepcopy(readiness)
    result['gates'] = [g for g in result['gates'] if g['id'] != 'features']
    result['gates'].append({'id': 'features', 'status': 'open', 'evidence': [REGISTRY]})
    result['approval'] = {'approved': False, 'by': None, 'evidence': None, 'evidence_sha256': None, 'binding': None}
    writes = {'docs/project/readiness.json': dump(result)}
    if not safe_path(root, REGISTRY).exists():
        writes[REGISTRY] = dump({'schema_version': 1, 'features': []})
    return writes


def links(root: Path, indexed: dict) -> list[dict]:
    if not safe_path(root, REGISTRY).exists():
        return []
    registry = load(root)
    result = []
    for feature in registry['features']:
        if feature['status'] != 'active':
            continue
        doc = feature['doc_root'] + '/requirements.md'
        for source in feature['code']:
            if source in indexed and doc in indexed:
                result.append({'source': doc, 'target': source, 'relation': 'documents'})
            for test in feature['tests']:
                if source in indexed and test in indexed:
                    result.append({'source': test, 'target': source, 'relation': 'tests'})
    return result
