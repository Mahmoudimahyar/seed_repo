"""Separate scope acceptance from technical test success. Local records aren't identity."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess

from .common import read_json, safe_path


def profile(root: Path) -> dict:
    import seed
    state = seed.load_state(root)
    if state['kind'] == 'template':
        return {'profile': 'maintainer', 'starter_regressions_required': True,
                'mcp_required': True, 'reason': 'Maintainers test every shipped integration.'}
    entry = state.get('integrations', {}).get('mcp')
    if (not isinstance(entry, dict) or set(entry) != {'enabled', 'reason'}
            or type(entry['enabled']) is not bool or not isinstance(entry['reason'], str)
            or len(entry['reason'].strip()) < 15):
        raise ValueError('Declare MCP applicability with configure-mcp before using the application CI profile')
    return {'profile': 'application', 'starter_regressions_required': True,
            'mcp_required': entry['enabled'], 'reason': entry['reason']}


def changed_paths(root: Path, base: str) -> list[str]:
    if not isinstance(base, str) or not re.fullmatch(r'[a-fA-F0-9]{40,64}', base) or set(base) == {'0'}:
        raise ValueError('A concrete fetched base commit is required for a documentation-only exception')
    paths = set()
    for args in (['diff', '--name-only', '-z', base, 'HEAD'], ['diff', '--name-only', '-z'],
                 ['diff', '--cached', '--name-only', '-z'], ['ls-files', '--others', '--exclude-standard', '-z']):
        process = subprocess.run(['git', *args], cwd=root, capture_output=True, timeout=15)
        if process.returncode:
            raise ValueError('Cannot verify changed paths against the requested base')
        paths.update(p for p in process.stdout.decode('utf-8').split('\0') if p)
    return sorted(paths)


def event_base() -> str | None:
    path = os.environ.get('GITHUB_EVENT_PATH')
    if not path:
        return None
    event = read_json(Path(path))
    if 'pull_request' in event:
        return event['pull_request']['base']['sha']
    if 'merge_group' in event:
        return event['merge_group']['base_sha']
    return event.get('before')


def scope_status(root: Path, *, base: str | None = None) -> dict:
    import seed
    state = seed.load_state(root)
    if state['kind'] == 'template':
        return {'status': 'NOT_APPLICABLE', 'reason': 'Template maintenance does not need fictional application approval.'}
    issues = seed.ready(root)
    if not issues:
        record = read_json(safe_path(root, 'docs/project/readiness.json'))
        return {'status': 'PASS', 'scope': record['scope'],
                'readiness_sha256': record['approval']['binding']['sha256'],
                'boundary': 'Recorded evidence only. Authenticate approvers and protect this check externally.'}
    if base:
        paths = changed_paths(root, base)
        policy = read_json(safe_path(root, 'quality/scope-policy.json'))
        if set(policy) != {'schema_version', 'documentation_only'} or policy['schema_version'] != 1:
            raise ValueError('Unknown scope exception policy')
        rule = policy['documentation_only']
        if set(rule) != {'reason', 'roots', 'files'} or len(rule['reason'].strip()) < 15:
            raise ValueError('Documentation exception needs explicit paths and rationale')
        # Only prose plus the declared discovery records can receive the exception.
        # Workflow/source/config changes cannot claim to be documentation by prefix alone.
        allowed = all((name.endswith('.md') and any(name.startswith(prefix) for prefix in rule['roots']))
                      or name in rule['files'] for name in paths)
        safe_files = {'docs/project/readiness.json', 'docs/project/features.json'}
        if (not set(rule['files']) <= safe_files or
                any(not isinstance(r, str) or not r.startswith('docs/') or not r.endswith('/') or '..' in r for r in rule['roots'])):
            raise ValueError('Overbroad documentation-only scope policy')
        if paths and allowed:
            return {'status': 'NOT_APPLICABLE', 'reason': rule['reason'], 'base_commit': base,
                    'changed_paths': paths, 'note': 'Discovery-only exception, NOT approval to implement. Requires protected policy/review.'}
    return {'status': 'BLOCKED', 'issues': issues, 'reason': 'Technical success does not establish current scope approval.'}
