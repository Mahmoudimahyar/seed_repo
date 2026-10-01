"""Bounded local DAG execution with resume evidence. Not an agent scheduler/sandbox."""
from __future__ import annotations
import fnmatch
import os
from pathlib import Path
import sys
import time
from .common import read_json,dump,sha,safe_path,atomic_json,now
from .file_policy import integrity_files as source_files, snapshot_fingerprint as fingerprint
from .processes import supervise
from .governance import validate, task_binding, references


def ordered_tasks(plan: dict) -> list[dict]:
    errors=validate('task-plan',plan)
    if errors:raise ValueError('; '.join(errors))
    if plan.get('require_governance') and any('governance' not in task for task in plan['tasks']):
        raise ValueError('Every task in this plan requires an explicit governance binding')
    tasks={t['id']:t for t in plan['tasks']}
    if len(tasks)!=len(plan['tasks']):raise ValueError('Duplicate task ID')
    done=set();ordered=[]
    while len(done)<len(tasks):
        ready=[t for t in tasks.values() if t['id'] not in done and set(t['depends_on'])<=done]
        if not ready:raise ValueError('Cyclic or unknown task dependency')
        for task in ready:ordered.append(task);done.add(task['id'])
    return ordered


def application_gate(root: Path, plan: dict) -> None:
    """Only application plans need this gate. Template maintenance is unaffected."""
    marker = safe_path(root, 'seed.json')
    if not marker.exists():
        return
    import seed
    state = seed.load_state(root)
    if state['kind'] != 'project':
        return
    issues = seed.ready(root)
    if issues:
        raise ValueError('Application readiness changed or is blocked: ' + '; '.join(issues))
    record = read_json(safe_path(root, 'docs/project/readiness.json'))
    if plan['scope'] != record['scope'] or plan.get('readiness_sha256') != record['approval']['binding']['sha256']:
        raise ValueError('Task plan is not bound to this approved application scope/revision')


def run(root: Path,plan: dict,execute=False) -> dict:
    root=root.resolve();tasks=ordered_tasks(plan)
    if not execute:return {'status':'PREVIEW','tasks':[t['id'] for t in tasks],'note':'Use --execute only for reviewed, trusted commands.'}
    if not plan['approved']:raise ValueError('Plan not approved')
    application_gate(root, plan)
    from .external import Sources
    external = Sources(root)
    external.check_bindings(plan.get('external_sources', []))
    approval=safe_path(root,plan['approval_evidence'])
    if not approval.is_file():raise ValueError('Approval evidence missing')
    stop=safe_path(root,'.seed-local/STOP')
    if stop.exists():return {'status':'STOPPED'}
    state_path=safe_path(root,'.seed-local/task-state.json')
    lease=safe_path(root,'.seed-local/task-run.lock');lease.parent.mkdir(parents=True,exist_ok=True)
    try:fd=os.open(lease,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise ValueError('Another task run owns the lock, or an interrupted run requires inspected recovery')
    try:
        with os.fdopen(fd,'w') as f:f.write(dump({'pid':os.getpid(),'created_at':now()}))
        digest=sha(dump(plan).encode());files=source_files(root)
        state=read_json(state_path) if state_path.exists() else {'plan_sha256':digest,'tasks':{},'source_fingerprint':fingerprint(files)}
        if state['plan_sha256']!=digest:raise ValueError('Plan changed; reconcile/archive previous state before a new run')
        if state['source_fingerprint']!=fingerprint(files):raise ValueError('Source changed since checkpoint; review and reconcile before resume')
        state.setdefault('governance_usage', {})
        state['external_sources'] = plan.get('external_sources', [])
        used=0
        for task in tasks:
            previous=state['tasks'].get(task['id'],{})
            if previous.get('status')=='PASS':continue
            if used>=plan['max_steps_per_run']:break
            if previous.get('attempts',0)>=plan['max_attempts_per_task']:
                state['status']='BLOCKED';state['reason']='Repair budget exhausted';break
            if stop.exists():state['status']='STOPPED';break
            if any(state['tasks'].get(d,{}).get('status')!='PASS' for d in task['depends_on']):
                state['status']='BLOCKED';state['reason']='Dependency did not pass';break
            application_gate(root, plan)
            external.check_bindings(plan.get('external_sources', []))
            governance_usage = {}
            if task.get('governance'):
                workflow_id = task['governance']['request']['workflow_id']
                governance_usage = state['governance_usage'].get(workflow_id, {})
            try:
                preflight = task_binding(root, task, governance_usage)
            except (ValueError, OSError, TypeError) as exc:
                preflight = {'status':'BLOCKED', 'reasons':[str(exc)]}
            if preflight['status'] not in {'ALLOW','NOT_CONFIGURED'}:
                state['tasks'][task['id']] = {'status':'BLOCKED','governance':preflight,
                                              'attempts':previous.get('attempts',0)}
                state.update(status='BLOCKED',reason='GOVERNANCE_PREFLIGHT_DENIED')
                atomic_json(state_path,state)
                break
            before=source_files(root)
            log=safe_path(root,f'.seed-local/task-logs/{task["id"]}.log');log.parent.mkdir(parents=True,exist_ok=True)
            result={'attempts':previous.get('attempts',0)+1,'started_at':now(),'argv':task['argv'],'status':'RUNNING', 'governance':preflight}
            state['tasks'][task['id']]=result;atomic_json(state_path,state)
            started=time.monotonic()
            timeout=task['timeout_seconds']
            if preflight['status']=='ALLOW':
                timeout=min(timeout,preflight['remaining_seconds'])
                # Reserve the declared call and cost before execution (including failed attempts).
                counters=dict(preflight['usage'])
                counters['calls_used']+=1
                counters['cost_usd']+=task['governance']['request']['projected_cost_usd']
                state['governance_usage'][preflight['workflow_id']]=counters
                atomic_json(state_path,state)
            with log.open('wb') as stream:
                args=[sys.executable if a=='{python}' else a for a in task['argv']]
                execution=supervise(args, cwd=safe_path(root,task['cwd']),
                                    timeout=timeout, stop_file=stop,
                                    max_output_bytes=8_000_000, log=stream)
            result.update(status=execution.status, exit_code=execution.exit_code)
            if execution.reason:
                result['reason']=execution.reason
            if preflight['status']=='ALLOW':
                counters['elapsed_seconds']+=execution.duration_seconds
                state['governance_usage'][preflight['workflow_id']]=counters
                try:
                    workflow=read_json(safe_path(root,task['governance']['workflow']))
                    if sha(safe_path(root,task['governance']['workflow']).read_bytes())!=task['governance']['workflow_sha256']:
                        raise ValueError('Workflow changed')
                    references(root,workflow,task['governance']['reference_sha256'])
                except (ValueError,OSError,TypeError):
                    result.update(status='BLOCKED',reason='WORKFLOW_CHANGED_DURING_TASK')
            try:
                external.check_bindings(plan.get('external_sources', []))
            except (ValueError, OSError):
                result.update(status='BLOCKED', reason='EXTERNAL_SOURCE_CHANGED_DURING_TASK')
            try:
                application_gate(root, plan)
            except ValueError:
                result.update(status='BLOCKED', reason='APPROVED_SCOPE_CHANGED_DURING_TASK')
            after=source_files(root)
            changed=[p for p in set(before)|set(after) if before.get(p)!=after.get(p)]
            unexpected=[p for p in changed if not any(fnmatch.fnmatchcase(p,pattern) for pattern in plan['allowed_edit_paths'])]
            if unexpected:result.update(status='FAIL',reason='OUT_OF_SCOPE_EDITS',unexpected_paths=sorted(unexpected))
            result.update(duration_seconds=round(time.monotonic()-started,3),changed_paths=sorted(changed),log_sha256=sha(log.read_bytes()) if log.exists() else None)
            state['source_fingerprint']=fingerprint(after);state['updated_at']=now();used+=1
            state['status']=result['status'];atomic_json(state_path,state)
            if result['status']!='PASS':break
        if all(state['tasks'].get(t['id'],{}).get('status')=='PASS' for t in tasks):state['status']='PASS'
        elif state.get('status')=='PASS':state['status']='CHECKPOINT'
        state['boundary']='Trusted commands, inherited environment, no sandbox. Edit detection is after-the-fact on integrity inputs, independent of retrieval; use OS isolation and scoped credentials. Success proves commands exited zero, not requirements were complete.'
        atomic_json(state_path,state);return state
    finally:lease.unlink(missing_ok=True)
