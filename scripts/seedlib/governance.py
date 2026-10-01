"""Executable contract checks and local preflight; NOT an independent authorizer.

Use authenticated external approval and OS/cloud permissions for real enforcement.
The requester must not control protected policy, counters, or approval evidence.
"""
from __future__ import annotations
from datetime import datetime, timezone
import fnmatch
from pathlib import Path
import re
from .common import read_json,dump,sha,safe_path,is_private,finite_number

SCHEMAS=Path(__file__).resolve().parents[2]/'schemas'
KINDS={'verification-map','external-request','external-sources','client-acceptance','feature-registry','promotion-policy','workflow','data-access','decision','purpose','action-request','task-plan','decision-map','decision-ticket','planning-snapshot'}


def validate(kind: str, value) -> list[str]:
    if kind not in KINDS:raise ValueError('Unknown schema name')
    from jsonschema import Draft202012Validator,FormatChecker
    schema=read_json(SCHEMAS/(kind+'.schema.json'))
    Draft202012Validator.check_schema(schema)
    validator=Draft202012Validator(schema,format_checker=FormatChecker())
    problems=[str('/'.join(map(str,e.absolute_path)))+': '+e.message for e in validator.iter_errors(value)]
    if '__FILL__' in dump(value) or '{{' in dump(value):problems.append('Unfilled template')
    # jsonschema can accept NaN supplied by Python despite JSON disallowing it.
    def numbers(item):
        if isinstance(item,dict):
            for v in item.values():numbers(v)
        elif isinstance(item,list):
            for v in item:numbers(v)
        elif isinstance(item,float):finite_number(item,minimum=float('-inf'))
    try:numbers(value)
    except ValueError:problems.append('Non-finite numeric value')
    return problems


def request_digest(request: dict) -> str:
    return sha(dump({**request,'approval':None}).encode())


def preflight(root: Path, workflow: dict, request: dict, reference_sha256: dict | None = None, usage: dict | None = None) -> dict:
    root=root.resolve()
    if safe_path(root,'.seed-local/STOP').exists():
        return {'status':'STOPPED','reasons':['Emergency stop active; no reason is required to stop.']}
    problems=validate('workflow',workflow)+validate('action-request',request)
    if problems:return {'status':'BLOCKED','reasons':problems}
    try:
        pinned = references(root, workflow, reference_sha256)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        return {'status':'BLOCKED','reasons':['Reference validation: '+str(exc)]}
    usage = usage or {}
    counters = {key: max(finite_number(request[key]), finite_number(usage.get(key, 0)))
                for key in ('calls_used','elapsed_seconds','cost_usd')}
    perm=workflow['permissions'];budget=workflow['budgets']
    if request['workflow_id']!=workflow['id']:problems.append('Workflow identity mismatch')
    if request['action'] not in perm['actions']:problems.append('Action not permitted')
    if request['mutates'] and workflow['autonomy']=='read_only':problems.append('Read-only workflow cannot mutate')
    patterns=perm['write_paths'] if request['mutates'] else perm['read_paths']
    for path in request['paths']:
        try:
            safe_path(root,path)
            if is_private(path) or not any(fnmatch.fnmatchcase(path,p) for p in patterns):
                problems.append('Path outside approved access scope')
        except ValueError:problems.append('Unsafe path')
    if not set(request['hosts']).issubset(perm['network_hosts']):problems.append('Host not allowed')
    if counters['calls_used']>=budget['max_calls']:problems.append('Call budget exhausted')
    if counters['elapsed_seconds']>=budget['max_seconds']:problems.append('Time budget exhausted')
    if counters['cost_usd']+request['projected_cost_usd']>budget['max_cost_usd']:problems.append('Cost budget exceeded')
    if workflow['autonomy']=='approval_required':
        approval=request['approval']
        if approval is None:problems.append('Approval required')
        else:
            if approval['request_sha256']!=request_digest(request):problems.append('Approval not bound to this exact request')
            if datetime.fromisoformat(approval['expires_at'].replace('Z','+00:00'))<=datetime.now(timezone.utc):problems.append('Approval expired')
            try:
                path=safe_path(root,approval['evidence_path'])
                if is_private(approval['evidence_path']) or not path.is_file():problems.append('Approval evidence absent or private')
            except ValueError:problems.append('Unsafe approval evidence path')
    return {'status':'BLOCKED' if problems else 'ALLOW','reasons':problems,
            'request_sha256':request_digest(request),'workflow_sha256':sha(dump(workflow).encode()),
            'reference_sha256':pinned, 'usage':counters,
            'boundary':'Local consistency check only. Authenticate approvals and enforce counters/permissions in a trusted executor.'}


def references(root: Path, workflow: dict, expected: dict | None = None) -> dict:
    """Validate the referenced graph and return pin-able hashes. No approval created."""
    problems = validate('workflow', workflow)
    if problems:
        raise ValueError('; '.join(problems))
    from .approvals import evidence
    paths = [workflow['data_manifest'], *workflow['evaluation_refs'],
             workflow['recovery']['rollback_reference']]
    if workflow.get('purpose_ref'):
        paths.append(workflow['purpose_ref'])
    hashes = {}
    for path in paths:
        checksum, text = evidence(root, path)
        if not text.strip():
            raise ValueError('Empty or unfinished workflow reference: ' + path)
        hashes[path] = checksum
    data = read_json(safe_path(root, workflow['data_manifest']))
    errors = validate('data-access', data)
    if errors or data['workflow_id'] != workflow['id']:
        raise ValueError('Invalid or mismatched data-access manifest: ' + '; '.join(errors))
    if workflow.get('purpose_ref'):
        errors = validate('purpose', read_json(safe_path(root, workflow['purpose_ref'])))
        if errors:
            raise ValueError('Invalid purpose contract: ' + '; '.join(errors))
    if expected is not None and expected != hashes:
        raise ValueError('Workflow reference set is incomplete, changed, or stale')
    return hashes


def task_binding(root: Path, task: dict, usage: dict | None = None) -> dict:
    """Opt-in pre-action adapter. It validates declared effects, not arbitrary code semantics."""
    binding = task.get('governance')
    if binding is None:
        return {'status': 'NOT_CONFIGURED', 'note': 'This task is not certified as governed.'}
    from .approvals import evidence
    checksum, _ = evidence(root, binding['workflow'])
    if checksum != binding['workflow_sha256']:
        raise ValueError('Workflow changed after task approval')
    workflow = read_json(safe_path(root, binding['workflow']))
    if binding['request']['execution_sha256'] != sha(dump({'argv': task['argv'], 'cwd': task['cwd']}).encode()):
        raise ValueError('Governed request is not bound to this command and working directory')
    result = preflight(root, workflow, binding['request'],
                       reference_sha256=binding['reference_sha256'], usage=usage)
    result['workflow_id'] = workflow['id']
    result['remaining_seconds'] = max(0, workflow['budgets']['max_seconds'] - result.get('usage', {}).get('elapsed_seconds', 0))
    return result
