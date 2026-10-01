"""Shared safe local I/O. No evaluation of repository instructions or shell input."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import os
import tempfile

PRIVATE_PARTS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'private',
                 '.seed-local', '.seed-ci-artifacts', '.pytest_cache', '.ruff_cache',
                 'dist', 'build', 'coverage', '.next'}
SECRET_NAMES = {'CLAUDE.local.md', 'settings.local.json', '.mcp.json', 'mcp.json'}
CREDENTIALS = (re.compile(r'ghp_[A-Za-z0-9]{30,}'),
               re.compile(r'github_pat_[A-Za-z0-9_]{40,}'),
               re.compile(r'sk-(?:proj-)?[A-Za-z0-9_-]{32,}'),
               re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'))

def safe_path(root: Path, name: str) -> Path:
    root = root.resolve()
    rel = Path(name)
    if not name or '\x00' in name or rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Expected a repository-relative path without traversal')
    current = root
    for part in rel.parts:
        current /= part
        if current.is_symlink():
            raise ValueError('Symlink paths are not allowed')
    if not current.resolve().is_relative_to(root):
        raise ValueError('Path escapes repository')
    return current

def is_private(name: str) -> bool:
    p = Path(name)
    return (any(x in PRIVATE_PARTS for x in p.parts) or
            p.name in SECRET_NAMES or p.name.startswith('.env') or
            p.suffix in {'.pem', '.key'} or p.name.lower().startswith('credentials') or
            name.startswith(('.agent/logs/', '.agent/scratch/', '.codex/')))

def has_secret(text: str) -> bool:
    return any(p.search(text) for p in CREDENTIALS)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_json(path: Path):
    def bad_constant(_):
        raise ValueError('Non-finite JSON number')
    return json.loads(path.read_text(encoding='utf-8'), parse_constant=bad_constant)

def dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n'

def atomic_json(path: Path, obj) -> None:
    if path.is_symlink():
        raise ValueError('Refusing symlink write')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='seed-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(dump(obj))
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def bounded_int(value, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'Expected integer in [{low}, {high}]')
    return value

def finite_number(value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError('Expected a finite number within bounds')
    return value


def bounded_response(value: dict, max_chars: int = 12000) -> dict:
    """Return complete evidence or an explicit limit result, never partial authority."""
    bounded_int(max_chars, 1000, 30000)
    size = len(dump(value))
    if size <= max_chars:
        return value
    return {'status': 'OUTPUT_LIMIT', 'truncated': True, 'required_chars': size,
            'map_id': value.get('map_id'), 'ticket_id': (value.get('active_ticket') or {}).get('id'),
            'continuation': None,
            'note': 'Narrow to one ticket/lower limit or inspect through the local planning CLI. '
                    'No partial authority, approval, or plan is supplied; do not act on this response.'}
