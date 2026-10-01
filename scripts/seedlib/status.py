"""Evidence-derived status views. Availability, applicability and verification stay distinct."""
from pathlib import Path
import sqlite3

from .common import read_json, safe_path
from .acceptance import profile, scope_status
from .file_policy import integrity_fingerprint


def summary(root: Path) -> dict:
    import seed
    from .external import Sources
    external_sources = Sources(root).status()
    state = seed.load_state(root)
    capabilities = {}
    for name, enabled in state['capabilities'].items():
        capabilities[name] = {'applicability': 'ENABLED' if enabled else 'NOT_NEEDED',
                              'evidence': 'seed.json', 'verification': 'NOT_VERIFIED' if enabled else 'NOT_APPLICABLE'}
    try:
        chosen = profile(root)
    except (ValueError, OSError) as exc:
        chosen = {'profile': state['kind'], 'status': 'BLOCKED', 'reason': str(exc)}
    try:
        approval = scope_status(root)
    except (ValueError, OSError, TypeError, KeyError, ImportError) as exc:
        approval = {'status': 'BLOCKED', 'reason': str(exc)}
    from .context import Context, DATABASE
    retrieval = {'status': 'AVAILABLE_NOT_INDEXED'}
    if safe_path(root, DATABASE).exists():
        try:
            retrieval = Context(root).status()
        except (ValueError, OSError, sqlite3.Error) as exc:
            retrieval = {'status': 'BLOCKED', 'reason': str(exc)}
    task_path = safe_path(root, '.seed-local/task-state.json')
    tasks = {'status': 'NOT_RUN'}
    task_error = False
    if task_path.exists():
        try:
            recorded = read_json(task_path)
            if not isinstance(recorded, dict) or not isinstance(recorded.get('tasks', {}), dict):
                raise ValueError('Invalid task evidence')
            if not all(isinstance(value, dict) for value in recorded.get('tasks', {}).values()):
                raise ValueError('Invalid task result')
        except (ValueError, OSError):
            task_error = True
            recorded = {}
        try:
            fresh = recorded.get('source_fingerprint') == integrity_fingerprint(root)
            Sources(root).check_bindings(recorded.get('external_sources', []))
        except (OSError, ValueError):
            fresh = False
        tasks = {'status': 'BLOCKED' if task_error else 'RECORDED_CURRENT' if fresh else 'STALE',
                 'recorded_result': recorded.get('status'), 'plan_sha256': recorded.get('plan_sha256'),
                 'evidence': '.seed-local/task-state.json',
                 'external_sources': recorded.get('external_sources', []),
                 'governed_tasks': [key for key, value in recorded.get('tasks', {}).items()
                                    if isinstance(value.get('governance'), dict) and value['governance'].get('status') == 'ALLOW'],
                 'note': 'Command evidence, not application acceptance or an authenticated attestation.'}
    technical = {'status': 'NOT_RUN'}
    report_path = safe_path(root, '.seed-ci-artifacts/report.json')
    if report_path.exists():
        report_error = False
        try:
            report = read_json(report_path)
            if not isinstance(report, dict):
                raise ValueError('Invalid technical evidence')
        except (ValueError, OSError):
            report_error = True
            report = {}
        try:
            fresh = report.get('source_fingerprint') == integrity_fingerprint(root)
        except (ValueError, OSError):
            fresh = False
        technical = {'status': 'BLOCKED' if report_error else 'RECORDED_CURRENT' if fresh else 'STALE',
                     'recorded_result': report.get('status'), 'evidence': '.seed-ci-artifacts/report.json'}
    planning = {'status': 'AVAILABLE_NOT_CONFIGURED', 'lease_is_runtime_budget': False}
    if safe_path(root, '.seed-local/decisions.sqlite').exists():
        planning['status'] = 'CONFIGURED'
        planning['note'] = 'Use explicit seed_plan handoff to inspect eligibility, evidence, and claims.'
    if state['kind'] == 'template':
        phase = 'TEMPLATE_MAINTENANCE'
    elif approval['status'] != 'PASS':
        phase = 'SCOPE_REVIEW_REQUIRED'
    elif tasks.get('status') == 'RECORDED_CURRENT':
        phase = 'EXECUTION_RECORDED'  # Does not infer that the application is complete.
    else:
        phase = 'APPROVED_FOR_SCOPED_WORK'
    from .client_evidence import status as client_status
    client = client_status(root)
    governed = tasks.get('governed_tasks', [])
    from .spec_trace import configured_features, plan_status
    try:
        mapped = configured_features(root)
        traceability = {'status': 'PLANNED' if mapped else 'NOT_CONFIGURED',
                        'features': [plan_status(root, key) for key in mapped],
                        'note': 'See current CI requirement_traceability and per-run check results; no semantic proof is inferred.'}
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        traceability = {'status': 'BLOCKED', 'reason': str(exc)}
    return {'phase': phase, 'declared_phase_hint': state.get('phase'), 'ci_profile': chosen,
            'capability_status': capabilities, 'scope_acceptance': approval,
            'context': retrieval, 'planning': planning, 'task_execution': tasks,
            'technical_checks': technical, 'requirement_traceability': traceability,
            'native_client': client, 'integrations': {'mcp': {'applicability': chosen.get('mcp_required'), 'verification': 'NOT_VERIFIED'},
                             'governance': {'status': ('RECORDED_PREFLIGHT_CURRENT' if tasks.get('status') == 'RECORDED_CURRENT' else 'RECORDED_PREFLIGHT_STALE') if governed else 'AVAILABLE_NOT_USED_IN_RECORDED_TASKS',
                                            'verification': 'See individual task preflight evidence; not a sandbox.'},
                             'evaluation': {'status': 'AVAILABLE', 'verification': 'No project-specific benchmark inferred from shipped demos.'},
                             'external_sources': external_sources,
                             'github': {'status': 'NOT_VERIFIED'}, 'deployment': {'status': 'NOT_VERIFIED'}}}
