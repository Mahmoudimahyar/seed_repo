"""Optional requirement -> JUnit result traceability, not semantic proof or authorization.

The approved plan stays in the feature root. Mutable evidence goes only to a unique
.seed-local/verification run. Trusted test commands use the shared bounded process
runner. No model calls, installs, shell interpolation, retries or approval writes.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys
from uuid import uuid4
import xml.etree.ElementTree as ET

from .common import atomic_json, dump, is_private, now, read_json, safe_path, sha
from .features import load as load_features
from .file_policy import integrity_fingerprint
from .governance import validate
from .processes import supervise

MAX_XML_BYTES = 2_000_000
BASE = '.seed-local/verification'
ID = re.compile(r'^#{2,6}\s+(REQ-[a-z][a-z0-9-]*-\d{3,})(?:\s*[:—-]\s+.*)?\s*$')
BOUNDARY = ('Local test evidence only, not human authentication, a sandbox, semantic coverage proof, '
            'or approval to ship. Review assertions, manual evidence, and independent checks.')


def declared_ids(text: str, feature_id: str, *, strict: bool = True) -> set[str]:
    """Narrow Markdown convention: actual REQ headings, not tables or fenced examples."""
    found = set()
    fence = None
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = re.match(r'(`{3,}|~{3,})', stripped)
        if marker:
            token = marker[1]
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1]:
                fence = None
            continue
        if fence or not re.match(r'^#{2,6}\s+REQ-', line):
            continue
        match = ID.fullmatch(line)
        if not match and not strict:
            continue  # Old heading styles remain prose unless the feature enables this pilot.
        if not match or not re.fullmatch(r'REQ-' + re.escape(feature_id) + r'-\d{3,}', match[1]):
            raise ValueError('Malformed or wrong-namespace requirement heading')
        if match[1] in found:
            raise ValueError('Duplicate requirement ID: ' + match[1])
        found.add(match[1])
    return found


def lint_feature(root: Path, feature: dict) -> dict | None:
    folder = feature['doc_root']
    spec = safe_path(root, folder + '/requirements.md')
    if spec.exists() and spec.stat().st_size > MAX_XML_BYTES:
        raise ValueError('Oversized requirement document')
    path = safe_path(root, folder + '/verification.json')
    ids = declared_ids(spec.read_text(encoding='utf-8'), feature['id'], strict=path.exists()) if spec.exists() else set()
    if not path.exists():
        return None  # Legacy prose stays valid; do not infer executable coverage.
    if not path.is_file() or path.stat().st_size > MAX_XML_BYTES:
        raise ValueError('Invalid or oversized verification map')
    plan = read_json(path)
    errors = validate('verification-map', plan)
    if errors:
        raise ValueError('Verification map: ' + '; '.join(errors))
    mapped = [item['id'] for item in plan['requirements']]
    if plan['feature_id'] != feature['id'] or len(mapped) != len(set(mapped)) or set(mapped) != ids:
        raise ValueError('Verification map must match unique declared requirement IDs for this feature')
    command = plan['command']
    if not any('{junit}' in arg for arg in command['argv']):
        raise ValueError('Test command must write its fresh report at {junit}')
    if '{junit}' in command['argv'][0]:
        raise ValueError('Report path cannot be an executable')
    if is_private(command['cwd']) or not safe_path(root, command['cwd']).is_dir():
        raise ValueError('Test cwd must be an existing nonprivate repository directory')
    return plan


def selected_plan(root: Path, feature_id: str) -> tuple[dict, str]:
    feature = next((f for f in load_features(root)['features'] if f['id'] == feature_id), None)
    if feature is None or feature['status'] != 'active':
        raise ValueError('Select a registered active feature')
    plan = lint_feature(root, feature)
    if plan is None:
        raise ValueError('Verification map is NOT_CONFIGURED for this feature')
    return plan, feature['doc_root'] + '/verification.json'


def plan_status(root: Path, feature_id: str) -> dict:
    feature = next((f for f in load_features(root)['features'] if f['id'] == feature_id), None)
    if feature is None or feature['status'] != 'active':
        raise ValueError('Select a registered active feature')
    plan = lint_feature(root, feature)
    return {'status': 'PLANNED' if plan else 'NOT_CONFIGURED', 'feature_id': feature_id,
            'requirements': len(plan['requirements']) if plan else 0,
            'note': 'Structural mapping only; test cases may be absent before TDD implementation.'}


def parse_junit(data: bytes) -> dict[str, str]:
    """Small explicit JUnit subset. Fail closed on empty/ambiguous/unsupported reports."""
    if len(data) > MAX_XML_BYTES:
        raise ValueError('JUnit report exceeds size limit')
    text = data.decode('utf-8-sig')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('DTD/entities are not accepted')
    try:
        tree = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError('Malformed JUnit report') from exc
    if tree.tag not in {'testsuite', 'testsuites'}:
        raise ValueError('Unsupported JUnit root/namespace')
    results, element_status = {}, {}
    for suite in tree.iter():
        if suite.tag in {'testsuite', 'testsuites'}:
            if any(child.tag in {'error', 'failure', 'skipped'} for child in suite):
                raise ValueError('Suite-level failure/skip cannot be assigned reliable case coverage')
            if 'tests' in suite.attrib:
                count = suite.get('tests', '')
                if not count.isdigit() or int(count) != sum(1 for _ in suite.iter('testcase')):
                    raise ValueError('JUnit declared case count does not match collected cases')
    for case in tree.iter('testcase'):
        name, cls = case.get('name', ''), case.get('classname', '')
        if not name.strip() or any(ord(c) < 32 for c in name + cls):
            raise ValueError('JUnit case requires a safe exact name')
        identifier = cls + '::' + name if cls else name
        if len(identifier) > 1000 or identifier in results:
            raise ValueError('Oversized or duplicate JUnit test identifier')
        tags = {child.tag for child in case}
        if tags - {'failure', 'error', 'skipped', 'system-out', 'system-err', 'properties'}:
            raise ValueError('Unsupported JUnit case outcome; provide an explicit adapter')
        attr = case.get('status', '')
        outcome = case.get('result', '')
        if attr not in {'', 'run', 'passed', 'failed', 'skipped', 'notrun', 'disabled'} or outcome not in {'', 'completed', 'suppressed', 'skipped'}:
            raise ValueError('Unsupported JUnit status/result attribute')
        results[identifier] = ('ERROR' if 'error' in tags else
                               'FAIL' if 'failure' in tags or attr == 'failed' else
                               'SKIPPED' if 'skipped' in tags or attr in {'skipped', 'notrun', 'disabled'}
                               or outcome in {'suppressed', 'skipped'} else 'PASS')
        element_status[case] = results[identifier]
    for suite in tree.iter():
        if suite.tag not in {'testsuite', 'testsuites'}:
            continue
        outcomes = [element_status[c] for c in suite.iter('testcase')]
        for attribute, state in (('failures', 'FAIL'), ('errors', 'ERROR'), ('skipped', 'SKIPPED')):
            if attribute in suite.attrib:
                count = suite.get(attribute, '')
                if not count.isdigit() or int(count) != outcomes.count(state):
                    raise ValueError('JUnit outcome counters disagree with cases')
    if not results:
        raise ValueError('No test cases collected')
    return results


def coverage(plan: dict, cases: dict) -> tuple[str, list[dict]]:
    rows = []
    for requirement in plan['requirements']:
        method = requirement['method']
        tests = {name: cases.get(name, 'NOT_RUN') for name in requirement['tests']}
        if method == 'post_release':
            status = 'OBSERVE_LATER'
        elif method == 'manual':
            status = 'NOT_RUN'
        else:
            status = next((s for s in ('ERROR', 'FAIL', 'NOT_RUN', 'SKIPPED') if s in tests.values()), 'PASS')
        rows.append({'id': requirement['id'], 'method': method, 'status': status, 'tests': tests})
    if any(s in {'FAIL', 'ERROR'} for s in cases.values()):
        return 'FAIL', rows  # Supporting failures cannot be hidden by a narrow map.
    if any(row['status'] in {'NOT_RUN', 'SKIPPED'} for row in rows):
        return 'BLOCKED', rows
    return ('PASS' if any(row['method'] == 'automated' for row in rows) else 'NOT_APPLICABLE'), rows


def run(root: Path, feature_id: str) -> dict:
    root = root.resolve()
    plan, plan_ref = selected_plan(root, feature_id)
    folder = BASE + '/' + uuid4().hex
    directory = safe_path(root, folder)
    directory.mkdir(parents=True, exist_ok=False)
    xml_path = safe_path(root, folder + '/junit.xml')
    before = integrity_fingerprint(root)
    argv = [arg.replace('{python}', sys.executable).replace('{junit}', str(xml_path)) for arg in plan['command']['argv']]
    process = supervise(argv, cwd=safe_path(root, plan['command']['cwd']),
                        timeout=plan['command']['timeout_seconds'], stop_file=safe_path(root, '.seed-local/STOP'))
    safe_path(root, folder + '/stdout.log').write_bytes(process.stdout)
    safe_path(root, folder + '/stderr.log').write_bytes(process.stderr)
    cases, xml_digest, problem = {}, None, None
    try:
        xml_path = safe_path(root, folder + '/junit.xml')
        if not xml_path.is_file() or xml_path.stat().st_size > MAX_XML_BYTES:
            raise ValueError('Missing or oversized fresh JUnit report')
        raw = xml_path.read_bytes()
        xml_digest = sha(raw)
        cases = parse_junit(raw)
    except (ValueError, OSError) as exc:
        problem = type(exc).__name__ + ': ' + str(exc)
    status, rows = coverage(plan, cases)
    if problem:
        status = 'BLOCKED'
    if process.status != 'PASS':
        status = 'BLOCKED' if process.status in {'BLOCKED', 'STOPPED'} else 'FAIL'
    try:
        current = integrity_fingerprint(root)
    except (ValueError, OSError):
        current = None
    if current != before:
        status = 'STALE'
    report = {'schema_version': 1, 'status': status, 'created_at': now(),
              'feature_id': feature_id, 'plan_path': plan_ref, 'plan_sha256': sha(dump(plan).encode()),
              'source_before': before, 'source_after': current,
              'process': {'status': process.status, 'exit_code': process.exit_code, 'reason': process.reason,
                          'duration_seconds': process.duration_seconds},
              'junit_path': folder + '/junit.xml', 'junit_sha256': xml_digest,
              'case_count': len(cases), 'coverage': rows, 'problem': problem,
              'report_path': folder + '/report.json', 'boundary': BOUNDARY}
    report['report_sha256'] = sha(dump(report).encode())
    atomic_json(safe_path(root, report['report_path']), report)
    return report


def check(root: Path, report_ref: str) -> dict:
    """Verify local result integrity/freshness. Not an attestation against a malicious writer."""
    if not re.fullmatch(re.escape(BASE) + r'/[0-9a-f]{32}/report\.json', report_ref):
        raise ValueError('Select a local verification report')
    report = read_json(safe_path(root, report_ref))
    if not isinstance(report, dict) or report.get('schema_version') != 1:
        return {'status': 'BLOCKED', 'reason': 'Unsupported result envelope'}
    body = {k: v for k, v in report.items() if k != 'report_sha256'}
    if report.get('report_sha256') != sha(dump(body).encode()) or report.get('report_path') != report_ref:
        return {'status': 'BLOCKED', 'reason': 'Result envelope integrity mismatch'}
    try:
        plan, plan_ref = selected_plan(root, report['feature_id'])
        if (plan_ref != report['plan_path'] or sha(dump(plan).encode()) != report['plan_sha256']
                or report['source_before'] != report['source_after']
                or report['source_after'] != integrity_fingerprint(root)):
            return {'status': 'STALE', 'reason': 'Source or approved plan inputs changed'}
        expected_xml = report_ref.rsplit('/', 1)[0] + '/junit.xml'
        if report['junit_path'] != expected_xml:
            return {'status': 'BLOCKED', 'reason': 'Result artifact path mismatch'}
        if report['junit_sha256'] is not None:
            path = safe_path(root, expected_xml)
            if not path.is_file() or path.stat().st_size > MAX_XML_BYTES or sha(path.read_bytes()) != report['junit_sha256']:
                return {'status': 'STALE', 'reason': 'Result artifact changed'}
        if report['status'] in {'PASS', 'NOT_APPLICABLE'}:
            status, rows = coverage(plan, parse_junit(safe_path(root, expected_xml).read_bytes()))
            if report['process']['status'] != 'PASS' or report['process']['exit_code'] != 0 or status != report['status'] or rows != report['coverage']:
                return {'status': 'BLOCKED', 'reason': 'Recorded result does not match executable evidence'}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {'status': 'BLOCKED', 'reason': 'Cannot verify result: ' + str(exc)}
    return report


def configured_features(root: Path) -> list[str]:
    """The existing active-feature registry is authoritative; no parallel tracker."""
    from .features import REGISTRY
    if not safe_path(root, REGISTRY).exists():
        return []
    return [feature['id'] for feature in load_features(root)['features']
            if feature['status'] == 'active'
            and safe_path(root, feature['doc_root'] + '/verification.json').exists()]


def run_configured(root: Path) -> dict:
    ids = configured_features(root)
    if not ids:
        return {'status': 'NOT_CONFIGURED', 'features': [],
                'note': 'No active feature enabled executable traceability; no coverage is claimed.'}
    reports = [run(root, feature_id) for feature_id in ids]
    states = {report['status'] for report in reports}
    status = ('BLOCKED' if states & {'STALE', 'BLOCKED'} else 'FAIL' if 'FAIL' in states
              else 'PASS' if 'PASS' in states else 'NOT_APPLICABLE')
    return {'status': status, 'features': [{'id': report['feature_id'], 'status': report['status'],
                                         'report_path': report['report_path'],
                                         'evidence': {key: report[key] for key in (
                                             'plan_sha256', 'source_before', 'source_after',
                                             'junit_sha256', 'report_sha256', 'process',
                                             'case_count', 'coverage')}} for report in reports],
            'boundary': BOUNDARY}
