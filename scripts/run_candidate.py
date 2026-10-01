#!/usr/bin/env python3
"""Run a builtin or reviewed adapter. Never send labels. Never silently retry.

Adapters receive {id,input} on stdin and emit the documented prediction/status
object. Output, wall time, and inherited environment are bounded; this is not a
sandbox. Saved output is one versioned envelope, not an orphaned metadata sidecar.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

from seedlib.common import read_json, safe_path, atomic_json, finite_number, sha, dump, now
from seedlib.evaluation import load_cases
from seedlib.predictions import normalize, envelope
from seedlib.processes import supervise


def predict_builtin(name, text):
    if name == 'empty':
        return []
    if name == 'regex-email':
        return [{'type': 'email', 'start': m.start(), 'end': m.end(), 'text': m.group(0)}
                for m in re.finditer(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)]
    raise ValueError('Unknown builtin candidate')


def run(root, cases, config, allow_external=False):
    if config.get('kind') not in {'builtin', 'external'}:
        raise ValueError('Candidate kind must be builtin or external')
    if config['kind'] == 'external' and not allow_external:
        raise ValueError('External code execution needs --allow-external after review')
    maximum = config.get('max_cases', 1000)
    if type(maximum) is not int or maximum < 1 or len(cases) > maximum:
        raise ValueError('Case budget exceeded or invalid')
    timeout = config.get('timeout_seconds', 60)
    finite_number(timeout)
    if not 0 < timeout <= 300:
        raise ValueError('Adapter timeout outside 0..300 seconds')
    env_keys = config.get('env_keys', [])
    if not isinstance(env_keys, list) or not all(isinstance(k, str) for k in env_keys):
        raise ValueError('Invalid env_keys')
    env = {k: v for k, v in os.environ.items()
           if k in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'HOME'} or k in env_keys}
    args = config.get('argv')
    if config['kind'] == 'external' and (not isinstance(args, list) or not args or
                                        not all(isinstance(a, str) for a in args)):
        raise ValueError('argv must be a nonempty string array')
    rows = []
    stop = safe_path(root, '.seed-local/STOP')
    for case in cases:
        if stop.exists():
            if not rows:
                raise ValueError('Emergency stop active')
            break
        started = time.monotonic()
        if config['kind'] == 'builtin':
            row = normalize({'prediction': predict_builtin(config['implementation'], case['input']), 'cost_usd': 0.0})
        else:
            execution = supervise([sys.executable if a == '{python}' else a for a in args],
                                  stdin=json.dumps({'id': case['id'], 'input': case['input']}).encode(),
                                  cwd=root, env=env, timeout=timeout, stop_file=stop,
                                  max_output_bytes=1_000_000)
            if execution.status != 'PASS':
                row = normalize({'status': 'ERROR', 'error_code': execution.reason or 'ADAPTER_EXIT'})
            else:
                try:
                    response = json.loads(execution.stdout.decode('utf-8'),
                                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite output')))
                    if 'id' in response or 'latency_ms' in response:
                        raise ValueError('Adapter cannot relabel the case or measured latency')
                    row = normalize(response)
                except (ValueError, TypeError, UnicodeError):
                    row = normalize({'status': 'ERROR', 'error_code': 'INVALID_OUTPUT'})
        rows.append({**row, 'id': case['id'], 'latency_ms': round((time.monotonic() - started) * 1000, 4)})
        if row['status'] == 'ERROR':
            break  # Preserve partial evidence. Do not retry expensive or effectful work.
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--cases', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--allow-external', action='store_true')
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        cases, dataset_sha = load_cases(safe_path(root, args.cases))
        config = read_json(safe_path(root, args.candidate))
        if not isinstance(config.get('candidate'), str) or not isinstance(config.get('configuration'), dict):
            raise ValueError('Candidate config must declare candidate ID and configuration metadata')
        out = safe_path(root, args.out)
        if out.exists():
            raise ValueError('Refusing to overwrite prior predictions')
        started = now()
        result = run(root, cases, config, args.allow_external)
        code_files = [Path(__file__), Path(__file__).parent / 'seedlib/processes.py',
                      Path(__file__).parent / 'seedlib/predictions.py']
        executor_sha = sha(dump({p.name: sha(p.read_bytes()) for p in code_files}).encode())
        saved = envelope(result, dataset_sha, config, started_at=started, executor_sha256=executor_sha)
        atomic_json(out, saved)
        passed = len(result) == len(cases) and not any(row['status'] == 'ERROR' for row in result)
        print(('PASS' if passed else 'FAIL') + ': saved ' + str(len(result)) + ' prediction results; no labels sent to adapter')
        return 0 if passed else 1
    except (OSError, ValueError, TypeError) as exc:
        print('BLOCKED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
