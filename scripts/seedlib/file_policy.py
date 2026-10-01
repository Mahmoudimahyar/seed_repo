"""Purpose-specific path policies. Retrieval exclusions never govern execution/export.

Integrity snapshots hash content, never return content. They are local change detectors,
not a filesystem sandbox or independent attestation.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from .common import dump, read_json, safe_path, sha

# Only generated runtime/dependency directories are omitted from integrity snapshots.
# Private user input and .env files ARE hashed; values are never emitted to reports.
RUNTIME_NAMES = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.seed-local',
                 '.seed-ci-artifacts', '.pytest_cache', '.ruff_cache', '.mypy_cache',
                 'dist', 'build', '.next', 'coverage'}
RUNTIME_PATHS = {'.agent/logs', '.agent/scratch'}
LOCAL_CONFIGS = {'.mcp.json', '.claude.json', 'CLAUDE.local.md',
                 '.claude/settings.local.json', '.cursor/mcp.json', '.codex/config.toml'}


def local_configuration(name: str) -> bool:
    """Paths, not basenames: a Codex config is local even though config.toml isn't."""
    path = Path(name).as_posix()
    return (path in LOCAL_CONFIGS or path.startswith('.codex/') or
            Path(path).name in {'CLAUDE.local.md', 'settings.local.json', '.mcp.json', 'mcp.json'})


def tracked_inputs(root: Path) -> set[str]:
    """Tracked source cannot disappear merely because its folder resembles build output."""
    if not (root / '.git').exists():
        return set()
    try:
        process = subprocess.run(['git', '-c', 'core.fsmonitor=false', 'ls-files', '-z', '--cached'],
                                 cwd=root, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError('Cannot inspect tracked execution inputs') from exc
    if process.returncode:
        raise ValueError('Cannot inspect tracked execution inputs')
    paths = {name for name in process.stdout.decode('utf-8').split('\0') if name}
    for name in paths:
        safe_path(root, name)
        if (name.startswith(('.seed-local/', '.seed-ci-artifacts/', '.agent/logs/', '.agent/scratch/'))):
            raise ValueError('Generated runtime state must not be tracked as source: ' + name)
    return paths


def integrity_files(root: Path) -> dict[str, str]:
    """Hash all regular source/input/config files, independent of retrieval policy.

    Includes untracked files, dependency locks, large and binary inputs, and private
    input bytes without exposing them. No retrieval extension/size/filter rules apply.
    Symlinks fail closed. Generated runtime trees above are the explicit exclusion.
    """
    root = root.resolve()
    result: dict[str, str] = {}
    paths: set[str] = set()
    for parent, dirs, names in os.walk(root, followlinks=False):
        base = Path(parent)
        kept = []
        for name in sorted(dirs):
            path = base / name
            relative = path.relative_to(root).as_posix()
            if name in RUNTIME_NAMES or relative in RUNTIME_PATHS:
                continue
            if path.is_symlink():
                raise ValueError('Symlink execution input is unsupported: ' + relative)
            kept.append(name)
        dirs[:] = kept
        for name in sorted(names):
            if name == '.git' or name.endswith(('.pyc', '.pyo')) or name in {'.DS_Store', 'Thumbs.db'}:
                continue
            path = base / name
            relative = path.relative_to(root).as_posix()
            safe_path(root, relative)
            if not path.is_file():
                raise ValueError('Non-regular execution input: ' + relative)
            paths.add(relative)
    # Re-add tracked inputs excluded by default build/dependency folder conventions.
    # A deleted tracked path stays absent, making a prior fingerprint stale.
    for name in tracked_inputs(root):
        if safe_path(root, name).exists():
            paths.add(name)
    for relative in sorted(paths):
        path = safe_path(root, relative)
        if not path.is_file():
            raise ValueError('Non-regular tracked execution input: ' + relative)
        checksum = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                checksum.update(chunk)
        # Executable-bit changes affect commands on POSIX and should invalidate evidence.
        result[relative] = sha((checksum.hexdigest() + ':' + str(path.stat().st_mode & 0o111)).encode())
    return result


def integrity_fingerprint(root: Path) -> str:
    return snapshot_fingerprint(integrity_files(root))


def snapshot_fingerprint(files: dict[str, str]) -> str:
    return sha(dump(dict(sorted(files.items()))).encode())


def export_problems(root: Path, names: list[str]) -> list[str]:
    """An exact, reviewed distribution inventory—not whatever is in a used checkout."""
    policy = read_json(safe_path(root, 'quality/export-policy.json'))
    if not isinstance(policy, dict) or set(policy) != {'schema_version', 'files'} or policy['schema_version'] != 1:
        raise ValueError('Invalid distribution allowlist')
    allowed = policy['files']
    if (not isinstance(allowed, list) or not all(isinstance(p, str) for p in allowed)
            or len(set(allowed)) != len(allowed)):
        raise ValueError('Distribution files must be unique canonical paths')
    for name in allowed:
        path = safe_path(root, name)
        if path.relative_to(root.resolve()).as_posix() != name or local_configuration(name):
            raise ValueError('Unsafe distribution entry: ' + name)
    actual = set(names) - {'MANIFEST.sha256'}
    return ([f'Unreviewed distribution file: {p}' for p in sorted(actual - set(allowed))] +
            [f'Missing distribution file: {p}' for p in sorted(set(allowed) - actual)])
