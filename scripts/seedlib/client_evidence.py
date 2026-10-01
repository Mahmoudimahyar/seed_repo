"""Consume optional local client acceptance records without inferring real execution."""
from pathlib import Path
from .common import read_json, safe_path
from .governance import validate
from .approvals import evidence

RECORD = '.seed-local/client-acceptance.json'


def status(root: Path) -> dict:
    path = safe_path(root, RECORD)
    if not path.exists():
        return {'status': 'NOT_VERIFIED', 'reason': 'No native-client acceptance record exists.'}
    try:
        record = read_json(path)
        issues = validate('client-acceptance', record)
        rows = record.get('scenarios', [])
        if issues or len({row['id'] for row in rows}) != len(rows):
            raise ValueError('Invalid or duplicate client acceptance scenarios')
        for row in rows:
            if row['status'] in {'PASS', 'FAIL', 'NOT_APPLICABLE'} and not row['evidence_sha256']:
                raise ValueError('Completed or inapplicable scenario needs evidence')
            for ref, checksum in row['evidence_sha256'].items():
                if evidence(root, ref)[0] != checksum:
                    raise ValueError('Stale client acceptance evidence')
        outcomes = {row['status'] for row in rows}
        state = ('RECORDED_FAILURE' if 'FAIL' in outcomes else 'RECORDED_INCOMPLETE'
                 if outcomes & {'NOT_RUN', 'BLOCKED'} else 'RECORDED_OUTCOMES')
        return {'status': state, 'client': record['client'], 'client_version': record['client_version'],
                'outcomes': {row['id']: row['status'] for row in rows},
                'boundary': 'Locally supplied observations, not authenticated telemetry or independent client certification.'}
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        return {'status': 'BLOCKED', 'reason': 'Client record/evidence is unavailable, malformed or stale; inspect privately.'}
