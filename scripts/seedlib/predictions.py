"""Versioned prediction/result envelopes. Hash bindings are integrity, not signatures."""
from __future__ import annotations

from pathlib import Path
import uuid

from .common import dump, finite_number, now, sha

STATUSES = {'PREDICTED', 'ABSTAINED', 'ERROR'}


def normalize(row: dict) -> dict:
    if not isinstance(row, dict):
        raise ValueError('Prediction result must be an object')
    allowed = {'id', 'status', 'prediction', 'abstained', 'error_code', 'cost_usd', 'latency_ms'}
    if set(row) - allowed:
        raise ValueError('Unknown prediction result field')
    if 'abstained' in row and type(row['abstained']) is not bool:
        raise ValueError('abstained must be boolean')
    status = row.get('status', 'ABSTAINED' if row.get('abstained') else 'PREDICTED')
    if status not in STATUSES:
        raise ValueError('Unknown prediction status')
    if 'abstained' in row and row['abstained'] != (status == 'ABSTAINED'):
        raise ValueError('Conflicting abstention and status')
    if status == 'PREDICTED' and ('prediction' not in row or row.get('error_code') is not None):
        raise ValueError('PREDICTED requires a prediction and no error')
    if status != 'PREDICTED' and row.get('prediction') is not None:
        raise ValueError('Non-prediction status cannot also carry a prediction')
    if status == 'ERROR' and not isinstance(row.get('error_code'), str):
        raise ValueError('ERROR requires a bounded error code')
    if row.get('error_code') is not None and (len(row['error_code']) > 80 or not row['error_code'].replace('_', '').isalnum()):
        raise ValueError('Error codes must not contain provider messages or secrets')
    for key in ('cost_usd', 'latency_ms'):
        if row.get(key) is not None:
            finite_number(row[key])
    result = {'status': status, 'prediction': row.get('prediction'),
              'abstained': status == 'ABSTAINED', 'cost_usd': row.get('cost_usd'),
              'latency_ms': row.get('latency_ms')}
    if 'id' in row:
        if not isinstance(row['id'], str) or not row['id']:
            raise ValueError('Prediction ID must be a nonempty string')
        result['id'] = row['id']
    if status == 'ERROR':
        result['error_code'] = row['error_code']
    # Also rejects NaN in a prediction nested several levels deep.
    dump(result)
    return result


def envelope(rows: list[dict], dataset_sha256: str, candidate: dict, *, started_at=None,
             executor_sha256=None) -> dict:
    if not isinstance(candidate.get('candidate'), str) or not isinstance(candidate.get('configuration'), dict):
        raise ValueError('Saved runs require candidate and full configuration fields')
    normalized = [normalize(row) for row in rows]
    manifest = {'run_id': str(uuid.uuid4()), 'dataset_sha256': dataset_sha256,
                'candidate': candidate, 'candidate_sha256': sha(dump(candidate).encode()),
                'predictions_sha256': sha(dump(normalized).encode()),
                'executor_sha256': executor_sha256,
                'started_at': started_at or now(), 'finished_at': now(),
                'count': len(normalized)}
    return {'schema_version': 1, 'kind': 'seed-prediction-run', 'manifest': manifest,
            'manifest_sha256': sha(dump(manifest).encode()), 'predictions': normalized}


def unpack(value, dataset_sha256: str, score_config: dict):
    if isinstance(value, list):
        return [normalize(row) for row in value], {'status': 'UNBOUND_LEGACY',
                'note': 'Exploration only. No generating run is bound; not eligible for promotion.'}
    if (not isinstance(value, dict) or set(value) != {'schema_version', 'kind', 'manifest', 'manifest_sha256', 'predictions'}
            or value['schema_version'] != 1 or value['kind'] != 'seed-prediction-run'):
        raise ValueError('Expected a versioned prediction run')
    manifest = value['manifest']
    if not isinstance(manifest, dict) or value['manifest_sha256'] != sha(dump(manifest).encode()):
        raise ValueError('Prediction manifest integrity mismatch')
    candidate = manifest.get('candidate')
    if not isinstance(candidate, dict) or manifest.get('candidate_sha256') != sha(dump(candidate).encode()):
        raise ValueError('Generating candidate configuration mismatch')
    if candidate.get('candidate') != score_config.get('candidate') or candidate.get('configuration') != score_config.get('configuration'):
        raise ValueError('Scorer cannot relabel a different candidate/configuration')
    if manifest.get('dataset_sha256') != dataset_sha256:
        raise ValueError('Generating dataset mismatch')
    rows = value['predictions']
    if not isinstance(rows, list) or manifest.get('count') != len(rows) or manifest.get('predictions_sha256') != sha(dump(rows).encode()):
        raise ValueError('Predictions differ from the generating run')
    return [normalize(row) for row in rows], {'status': 'BOUND_RUN',
            'manifest_sha256': value['manifest_sha256'], 'run_manifest': manifest,
            'note': 'Local hash consistency, not authentication, a provider attestation, or independent provenance.'}
