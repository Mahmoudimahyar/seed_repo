#!/usr/bin/env python3
"""Offline Seed Repo utilities. No package installation, network, or Git writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any
from seedlib.file_policy import local_configuration, export_problems

MODES = (
    'product', 'internal-tool', 'developer-tool', 'cli', 'api', 'library',
    'research', 'automation', 'data-pipeline', 'ai-system', 'landing-page',
)
CAPABILITIES = ('ui', 'marketing', 'sales', 'ai')
IGNORED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'private',
           '.seed-ci-artifacts', '.seed-local', 'dist', 'build', '.pytest_cache',
           '.ruff_cache', '.mypy_cache', 'coverage', '.next', '.agent/scratch', '.agent/logs'}
CORE_DOCS = ('brief', 'prd', 'architecture', 'testing', 'gaps', 'decisions',
             'dependencies', 'configuration', 'plan')
REQUIRED = ('README.md', 'START_HERE.md', 'AGENTS.md', 'CLAUDE.md', 'LICENSE',
            'CONTRIBUTING.md', 'SECURITY.md', 'seed.json', 'quality/seed-checks.json',
            'quality/application-checks.example.json', 'docs/status.md')
TOKEN_PATTERNS = (
    re.compile(r'ghp_[A-Za-z0-9]{30,}'),
    re.compile(r'github_pat_[A-Za-z0-9_]{40,}'),
    re.compile(r'sk-(?:proj-)?[A-Za-z0-9_-]{32,}'),
    re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
)
PLACEHOLDER = re.compile(r'__FILL__|\bTBD\b|\bTODO\b|\{\{[^}]+\}\}')


def safe_path(root: Path, relative: str) -> Path:
    """Reject escapes and symlinks, including in existing parent directories."""
    root = root.resolve()
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Expected an in-repository relative path')
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'Symlink is not allowed: {relative}')
    if not current.resolve().is_relative_to(root):
        raise ValueError('Path escapes repository')
    return current


def read_json(root: Path, relative: str) -> Any:
    return json.loads(safe_path(root, relative).read_text(encoding='utf-8'))


def json_text(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + '\n'


def digest(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def load_state(root: Path) -> dict[str, Any]:
    state = read_json(root, 'seed.json')
    if not isinstance(state, dict) or state.get('schema_version') != 1:
        raise ValueError('seed.json must use schema_version 1')
    if state.get('kind') not in {'template', 'project'}:
        raise ValueError('seed.json kind must be template or project')
    caps = state.get('capabilities')
    if not isinstance(caps, dict) or any(type(caps.get(k)) is not bool for k in CAPABILITIES):
        raise ValueError('Capabilities must be explicit booleans')
    if state['kind'] == 'project':
        project = state.get('project')
        if not isinstance(project, dict) or project.get('mode') not in MODES:
            raise ValueError('Project mode is missing or invalid')
        if not isinstance(project.get('name'), str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', project['name']):
            raise ValueError('Project name must be a lowercase slug')
    return state


def init_plan(root: Path, name: str, mode: str, capabilities: dict[str, bool]) -> dict[str, str]:
    state = load_state(root)
    if state['kind'] != 'template':
        raise ValueError('Already initialized; change project scope through reviewed docs, not a reset')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', name) or mode not in MODES:
        raise ValueError('Use a lowercase project slug and a supported mode')
    if set(capabilities) != set(CAPABILITIES) or any(type(v) is not bool for v in capabilities.values()):
        raise ValueError('Capabilities must be explicit booleans')
    current_checks = safe_path(root, 'quality/seed-checks.json').read_text(encoding='utf-8')
    expected_checks = safe_path(root, 'quality/template-checks.json').read_text(encoding='utf-8')
    if current_checks != expected_checks:
        raise ValueError('Active CI configuration was customized; reconcile manually before initialization')

    state.update(kind='project', project={'name':name, 'mode':mode}, phase='discovery', capabilities=capabilities)
    state['integrations']={'mcp':{'enabled':False,'reason':'No MCP client requested; local context CLI remains available.'}}
    plan = {'seed.json': json_text(state),
            'quality/seed-checks.json': safe_path(root, 'quality/application-checks.example.json').read_text(encoding='utf-8')}
    for name_doc in CORE_DOCS:
        text = safe_path(root, f'templates/project/{name_doc}.md').read_text(encoding='utf-8')
        plan[f'docs/project/{name_doc}.md'] = text.replace('{{project_name}}', name).replace('{{project_mode}}', mode)
    if capabilities['ui']:
        for part in ('site-map', 'design-system'):
            plan[f'docs/project/{part}.md'] = safe_path(root, f'templates/project/{part}.md').read_text(encoding='utf-8').replace('{{project_name}}', name)
    for capability in ('marketing', 'sales', 'ai'):
        if capabilities[capability]:
            plan[f'docs/project/{capability}.md'] = safe_path(root, f'templates/project/{capability}.md').read_text(encoding='utf-8').replace('{{project_name}}', name)
    plan['docs/project/features.json'] = json_text({'schema_version':1,'features':[]})
    gates = [{'id': name_doc, 'status':'open', 'evidence':[f'docs/project/{name_doc}.md']}
             for name_doc in CORE_DOCS]
    gates.append({'id':'features','status':'open','evidence':['docs/project/features.json']})
    if capabilities['ui']:
        gates.extend({'id':part, 'status':'open', 'evidence':[f'docs/project/{part}.md']}
                     for part in ('site-map', 'design-system'))
    for capability in ('marketing', 'sales', 'ai'):
        if capabilities[capability]:
            gates.append({'id':capability, 'status':'open', 'evidence':[f'docs/project/{capability}.md']})
    plan['docs/project/readiness.json'] = json_text({
        'schema_version':2, 'scope':'__FILL__', 'gates':gates, 'planning':[],
        'blocking_gaps':['Initial discovery has not been completed'],
        'approval':{'approved':False,'by':None,'evidence':None,'evidence_sha256':None,'binding':None},
    })
    for relative in plan:
        path = safe_path(root, relative)
        if path.exists() and relative not in {'seed.json', 'quality/seed-checks.json'}:
            raise ValueError(f'Refusing to overwrite existing file: {relative}')
    return plan


def write_plan(root: Path, plan: dict[str, str], replace: set[str]) -> None:
    """Preflight conflicts; preserve existing files. Not a crash-atomic transaction."""
    for relative in plan:
        path = safe_path(root, relative)
        if path.exists() and relative not in replace:
            raise ValueError(f'Refusing to overwrite: {relative}')
        if path.exists() and not path.is_file():
            raise ValueError(f'Expected regular file: {relative}')
    for relative, text in plan.items():
        path = safe_path(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w' if relative in replace else 'x', encoding='utf-8', newline='\n') as handle:
            handle.write(text)


def skill_plan(root: Path) -> dict[str, str]:
    manifest_file = safe_path(root, '.seed/skill-mirrors.json')
    prior = read_json(root, '.seed/skill-mirrors.json') if manifest_file.exists() else {}
    sources = sorted(safe_path(root, '.agents/skills').glob('seed-*/SKILL.md'))
    if not sources:
        raise ValueError('No canonical Seed skills found')
    plan: dict[str, str] = {}
    manifest: dict[str, str] = {}
    for source in sources:
        text = safe_path(root, source.relative_to(root).as_posix()).read_text(encoding='utf-8')
        target = f'.claude/skills/{source.parent.name}/SKILL.md'
        path = safe_path(root, target)
        if path.exists():
            existing = path.read_text(encoding='utf-8')
            if existing != text and digest(existing) != prior.get(target):
                raise ValueError(f'Manually changed mirror; reconcile without discarding edits: {target}')
        plan[target] = text
        manifest[target] = digest(text)
    plan['.seed/skill-mirrors.json'] = json_text(manifest)
    skill_retirements(root, plan)  # Also reject unknown orphan files and edited retired copies.
    return plan


def skill_retirements(root: Path, plan: dict[str, str]) -> list[str]:
    previous = read_json(root, '.seed/skill-mirrors.json') if safe_path(root, '.seed/skill-mirrors.json').exists() else {}
    targets = {p for p in plan if p.startswith('.claude/skills/')}
    observed = {p.relative_to(root).as_posix() for p in safe_path(root, '.claude/skills').glob('seed-*/SKILL.md')}
    retire = []
    for relative in sorted((set(previous) | observed) - targets):
        if not re.fullmatch(r'\.claude/skills/seed-[a-z0-9-]+/SKILL\.md', relative):
            raise ValueError('Invalid generated mirror path')
        path = safe_path(root, relative)
        if not path.exists():
            continue
        if relative not in previous or digest(path.read_text(encoding='utf-8')) != previous[relative]:
            raise ValueError('Manually changed or untracked orphan mirror; reconcile before retirement: ' + relative)
        retire.append(relative)
    return retire


def apply_skills(root: Path, plan: dict[str, str]) -> None:
    if plan != skill_plan(root):
        raise ValueError('Skills changed since preview; review synchronization again')
    retire = skill_retirements(root, plan)
    # Preflight completes before removing any file. Only known, unchanged generated SKILL.md files retire.
    write_plan(root, plan, set(plan))
    for relative in retire:
        path = safe_path(root, relative)
        path.unlink()
        try:
            path.parent.rmdir()
        except OSError:
            pass  # Preserve unrelated/manual files in this directory.


def repo_files(root: Path):
    """Enumerate only non-runtime files; never follow symlinked directories."""
    for directory, dirs, files in os.walk(root, followlinks=False):
        base = Path(directory)
        retained = []
        for name in dirs:
            path = base / name
            rel = path.relative_to(root).as_posix()
            if name in IGNORED or rel in IGNORED:
                continue
            if path.is_symlink():
                yield path
            else:
                retained.append(name)
        dirs[:] = retained
        for name in files:
            if name in {'.git', '.DS_Store', 'Thumbs.db'} or name.endswith(('.pyc', '.pyo')):
                continue
            yield base / name


def sensitive_filename(name: str) -> bool:
    return ((name.startswith('.env') and not (name == '.env.example' or name.endswith('.example')))
            or name.endswith(('.pem', '.key')) or name.startswith('credentials')
            or name in {'CLAUDE.local.md','settings.local.json','.mcp.json','mcp.json'})


def validate(root: Path, public: bool = False) -> list[str]:
    problems: list[str] = []
    try:
        load_state(root)
    except (OSError, ValueError, TypeError) as exc:
        problems.append(f'Invalid state: {exc}')
    for relative in REQUIRED:
        try:
            if not safe_path(root, relative).is_file():
                problems.append(f'Missing required file: {relative}')
        except ValueError as exc:
            problems.append(str(exc))
    for path in repo_files(root):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            problems.append(f'Symlink not supported in distribution: {rel}')
            continue
        if sensitive_filename(path.name) or local_configuration(rel):
            if public:
                problems.append(f'Local/sensitive filename present; export a clean release: {rel}')
            continue  # Never inspect secret-file values.
        if path.suffix not in {'.md','.mdc','.py','.json','.yml','.yaml','.toml','.txt'}:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            problems.append(f'Unreadable UTF-8 text: {rel}')
            continue
        if any(pattern.search(text) for pattern in TOKEN_PATTERNS):
            problems.append(f'Possible credential material in {rel}; inspect privately')
        if path.suffix == '.json':
            try:
                json.loads(text)
            except ValueError:
                problems.append(f'Invalid JSON: {rel}')
        if path.suffix == '.md':
            # Deliberately limited to ordinary inline local links, not a general Markdown parser.
            prose = re.sub(r'```.*?```', '', text, flags=re.S)
            for match in re.finditer(r'(?<!!)\[[^\]\n]+\]\(([^)\s]+)\)', prose):
                link = match.group(1)
                if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', link) or link.startswith('#'):
                    continue
                target = link.split('#',1)[0].split('?',1)[0]
                dest = (root / target.lstrip('/') if target.startswith('/') else path.parent / target).resolve()
                if not dest.is_relative_to(root) or not dest.exists():
                    problems.append(f'Broken local link: {rel} -> {link}')
            if path.name == 'SKILL.md':
                expected = path.parent.name
                if not text.startswith('---\n') or f'name: {expected}\n' not in text:
                    problems.append(f'Invalid skill name/frontmatter: {rel}')
                if not re.search(r'^description: \S.+', text, re.M):
                    problems.append(f'Missing skill trigger description: {rel}')
    try:
        plan = skill_plan(root)
        for retired in skill_retirements(root, plan):
            problems.append(f'Retired skill mirror still discoverable: {retired}; run sync-skills --write')
        for rel, text in plan.items():
            if not safe_path(root, rel).is_file() or safe_path(root, rel).read_text(encoding='utf-8') != text:
                problems.append(f'Skill mirror missing/stale: {rel}; run sync-skills --write')
    except (OSError, ValueError, TypeError) as exc:
        problems.append(f'Skill synchronization: {exc}')
    try:
        from seedlib.external import Sources, MANIFEST
        sources = Sources(root).manifest()['sources']
        if public and sources:
            problems.append('Public starter export requires an empty external-source registry; review/sanitize research separately')
    except (ValueError, OSError, ImportError) as exc:
        problems.append('External source registry: ' + str(exc))
    try:
        from seedlib.features import REGISTRY, load as load_features
        from seedlib.spec_trace import lint_feature
        if safe_path(root, REGISTRY).is_file():
            for feature in load_features(root)['features']:
                if feature['status'] == 'active':
                    lint_feature(root, feature)
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        problems.append('Feature verification plan: ' + str(exc))
    if public:
        try:
            problems.extend(export_problems(root, [p.relative_to(root).as_posix() for p in repo_files(root)]))
        except (OSError, ValueError, TypeError) as exc:
            problems.append('Distribution policy: ' + str(exc))
    return problems


def ready(root: Path, check_approval: bool = True) -> list[str]:
    """Validate recorded readiness, not truth/adequacy of requirements or human identity."""
    problems: list[str] = []
    state = load_state(root)
    if state['kind'] != 'project':
        return ['Not initialized as an application/tool; template maintenance does not require this gate']
    record = read_json(root, 'docs/project/readiness.json')
    if not isinstance(record, dict) or record.get('schema_version') != 2:
        return ['Readiness must use schema_version 2; migrate the old record and obtain revision-bound approval']
    scope = record.get('scope')
    if not isinstance(scope, str) or len(scope.strip()) < 10 or PLACEHOLDER.search(scope):
        problems.append('A concrete approved build scope is missing')
    blockers = record.get('blocking_gaps')
    if not isinstance(blockers, list) or blockers:
        problems.append('Blocking gaps remain or the gap list is invalid')
    required = set(CORE_DOCS) | {'features'}
    if state['capabilities']['ui']:
        required |= {'site-map','design-system'}
    required |= {capability for capability in ('marketing','sales','ai') if state['capabilities'][capability]}
    gates = record.get('gates')
    if not isinstance(gates, list):
        return problems + ['Gates must be a list']
    seen: set[str] = set()
    for gate in gates:
        if not isinstance(gate, dict) or not isinstance(gate.get('id'), str):
            problems.append('Invalid gate object')
            continue
        name = gate['id']
        if name in seen:
            problems.append(f'Duplicate gate: {name}')
        seen.add(name)
        if gate.get('status') != 'satisfied':
            problems.append(f'Gate not satisfied: {name}')
        evidence = gate.get('evidence')
        if not isinstance(evidence, list) or not evidence:
            problems.append(f'Gate lacks evidence: {name}')
        else:
            for ref in evidence:
                if not isinstance(ref, str):
                    problems.append(f'Invalid evidence path: {name}')
                    continue
                path = safe_path(root, ref)
                if not path.is_file():
                    problems.append(f'Missing gate evidence: {ref}')
                elif sensitive_filename(path.name):
                    problems.append(f'Secret/local file cannot be gate evidence: {ref}')
                else:
                    text = path.read_text(encoding='utf-8')
                    if len(text.strip()) < 30 or PLACEHOLDER.search(text):
                        problems.append(f'Unfilled/insufficient recorded evidence: {ref}')
    for name in sorted(required - seen):
        problems.append(f'Required gate absent: {name}')
    from seedlib.approvals import propose, verify
    try:
        propose(root, record, state)
    except (ValueError, OSError, TypeError, KeyError, ImportError) as exc:
        problems.append('Approval binding: ' + str(exc))
    if not check_approval:
        return problems
    approval = record.get('approval')
    if not isinstance(approval, dict) or approval.get('approved') is not True:
        problems.append('Explicit user approval has not been recorded')
    else:
        by, ref = approval.get('by'), approval.get('evidence')
        if not isinstance(by, str) or not by.strip() or not isinstance(ref, str):
            problems.append('Approval needs an accountable approver and evidence file')
        else:
            path = safe_path(root, ref)
            if sensitive_filename(path.name) or local_configuration(ref):
                problems.append('Approval evidence must not be a secret/local file')
            elif not path.is_file():
                problems.append('Approval evidence file does not exist')
            else:
                text = path.read_text(encoding='utf-8')
                if len(text.strip()) < 30 or PLACEHOLDER.search(text):
                    problems.append('Approval evidence is unfilled')
    if isinstance(approval, dict) and approval.get('approved') is True:
        problems.extend(verify(root, record, state))
    return problems


def doctor(root: Path) -> dict[str, Any]:
    state = load_state(root)
    from seedlib.status import summary
    evidence_status=summary(root)
    return {
        'python': '.'.join(map(str, sys.version_info[:3])),
        'python_supported': sys.version_info >= (3,11),
        'kind': state['kind'], **evidence_status,
        'project': state.get('project'), 'capabilities':state['capabilities'],
        'binaries_on_path': {name: bool(shutil.which(name)) for name in ('git','claude','codex')},
        'mcp_config_present': (root / '.mcp.json').is_file(),
        'local_context_index_present': (root / '.seed-local/context.sqlite').is_file(),
        'local_context_note': 'Run seed_context.py status for freshness; config/index presence alone is not proof',
        'mcp_connectivity': 'NOT_VERIFIED; inspect in your client and make a real call',
        'note': 'No network, authentication, credential values returned, installs or Git writes. Integrity checks may hash private inputs without exposing their contents.',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor', help='Read-only local capability summary')
    integration = sub.add_parser('configure-mcp', help='Preview applicability; does not install/connect an MCP server')
    toggle=integration.add_mutually_exclusive_group(required=True)
    toggle.add_argument('--enable', action='store_true')
    toggle.add_argument('--disable', action='store_true')
    integration.add_argument('--reason', required=True)
    integration.add_argument('--write', action='store_true')
    feature = sub.add_parser('register-feature', help='Preview explicit feature/evidence registration')
    feature.add_argument('--id', required=True)
    feature.add_argument('--owner', required=True)
    feature.add_argument('--docs', required=True)
    feature.add_argument('--ui', action='store_true')
    feature.add_argument('--code', action='append', default=[])
    feature.add_argument('--test', action='append', default=[])
    feature.add_argument('--write', action='store_true')
    feature = sub.add_parser('migrate-features', help='Add the feature registry and revoke old approval')
    feature.add_argument('--write', action='store_true')
    check = sub.add_parser('validate', help='Static starter checks; not application acceptance')
    check.add_argument('--public', action='store_true', help='Also reject local secret filenames in the export')
    initialize = sub.add_parser('init', help='Preview initialization; --write applies it')
    initialize.add_argument('--name', required=True)
    initialize.add_argument('--mode', choices=MODES, required=True)
    for capability in CAPABILITIES:
        initialize.add_argument(f'--{capability}', action='store_true')
    initialize.add_argument('--write', action='store_true')
    mirror = sub.add_parser('sync-skills', help='Preview local Claude mirrors; --write applies')
    mirror.add_argument('--write', action='store_true')
    sub.add_parser('ready', help='Check recorded approval and active-scope evidence; not semantic proof')
    proposal = sub.add_parser('approval-manifest', help='Print a proposed revision binding; grants no approval')
    proposal.add_argument('--out', help='Optional new file for the proposal; never overwritten')
    approval = sub.add_parser('record-approval', help='Record existing actual approval of a matching manifest; preview by default')
    approval.add_argument('--by', required=True)
    approval.add_argument('--evidence', required=True)
    approval.add_argument('--proposal', required=True)
    approval.add_argument('--write', action='store_true')
    migration = sub.add_parser('migrate-readiness', help='Preview schema 1 to 2 migration; invalidates old approval')
    migration.add_argument('--write', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if sys.version_info < (3,11):
            raise ValueError('Python 3.11+ required')
        if args.command == 'configure-mcp':
            if len(args.reason.strip())<15:raise ValueError('Record a meaningful applicability decision')
            state=load_state(root)
            state.setdefault('integrations',{})['mcp']={'enabled':args.enable,'reason':args.reason}
            plan={'seed.json':json_text(state)}
            print(json_text(plan),end='')
            if args.write:write_plan(root,plan,{'seed.json'})
            return 0
        if args.command in {'register-feature','migrate-features'}:
            from seedlib import features
            if load_state(root)['kind']!='project':
                raise ValueError('Feature registration is for an initialized project')
            plan = (features.migrate(root) if args.command=='migrate-features' else
                    features.register(root, id=args.id, owner=args.owner, doc_root=args.docs,
                                      ui=args.ui, code=args.code, tests=args.test))
            print(json_text(plan), end='')
            if args.write:
                write_plan(root,plan,set(plan))
            return 0
        if args.command in {'approval-manifest', 'record-approval', 'migrate-readiness'}:
            from seedlib import approvals
            record_path = 'docs/project/readiness.json'
            readiness = read_json(root, record_path)
            if args.command == 'migrate-readiness':
                updated = approvals.migrate(readiness)
                print(json_text(updated), end='')
                if args.write:
                    archived = 'docs/project/readiness.v1.archived.json'
                    write_plan(root, {archived: json_text(readiness), record_path: json_text(updated)}, {record_path})
                return 0
            problems = ready(root, check_approval=False)
            if problems:
                raise ValueError('Readiness evidence is not ready for review: ' + '; '.join(problems))
            if args.command == 'approval-manifest':
                proposal = approvals.propose(root, readiness, load_state(root))
                print(json_text(proposal), end='')
                if args.out:
                    write_plan(root, {args.out: json_text(proposal)}, set())
            else:
                updated = approvals.record(root, readiness, load_state(root), args.by, args.evidence,
                                           read_json(root, args.proposal))
                print(json_text(updated), end='')
                if args.write:
                    write_plan(root, {record_path: json_text(updated)}, {record_path})
            return 0
        if args.command == 'doctor':
            print(json_text(doctor(root)), end='')
        elif args.command == 'validate':
            problems = validate(root, args.public)
            print('\n'.join(problems) if problems else 'PASS: static starter integrity checks')
            return 1 if problems else 0
        elif args.command == 'ready':
            problems = ready(root)
            print('\n'.join(problems) if problems else 'READY: recorded scope/evidence checks pass; verify actual user approval')
            return 2 if problems else 0
        else:
            if args.command == 'init':
                plan = init_plan(root, args.name, args.mode, {key:getattr(args,key) for key in CAPABILITIES})
                replace = {'seed.json','quality/seed-checks.json'}
            else:
                plan = skill_plan(root)
                replace = set(plan)
            print(('Writing:' if args.write else 'Preview only; add --write to apply:'))
            print('\n'.join(plan))
            if args.command == 'sync-skills':
                print('Retire known unchanged mirrors: ' + ', '.join(skill_retirements(root, plan)))
            if args.write:
                if args.command == 'sync-skills':
                    apply_skills(root, plan)
                else:
                    write_plan(root, plan, replace)
                if args.command == 'init':
                    print('Initialized discovery only. Application checks are now unconfigured/BLOCKED. No application code was created.')
        return 0
    except (OSError, ValueError, TypeError, ImportError) as exc:
        print(f'BLOCKED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
