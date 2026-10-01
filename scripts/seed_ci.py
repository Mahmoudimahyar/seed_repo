#!/usr/bin/env python3
"""Small, stack-neutral CI adapter. Not a sandbox or independent policy engine."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any
from seedlib.processes import supervise
from seedlib.file_policy import integrity_fingerprint

TITLE = re.compile(r"^(feat|fix|build|chore|ci|docs|style|refactor|perf|test|revert)(\([a-zA-Z0-9._/-]+\))?!?: \S[^\r\n]*$")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

def valid_title(title: str) -> bool:
    return len(title) <= 120 and bool(TITLE.fullmatch(title))

def contained(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path escapes repository root")
    return path

def load_config(path: Path, root: Path) -> tuple[list[dict[str, Any]], str]:
    raw = path.read_bytes()
    obj = json.loads(raw)
    if not isinstance(obj, dict) or obj.get("schema_version") != 1:
        raise ValueError("Expected schema_version 1")
    checks = obj.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("At least one check is required")
    seen: set[str] = set()
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("Each check must be an object")
        name = check.get("id", "")
        if not isinstance(name, str) or not IDENTIFIER.fullmatch(name) or name in seen:
            raise ValueError("Check IDs must be unique safe identifiers")
        seen.add(name)
        argv, na = check.get("argv"), check.get("not_applicable")
        if argv is not None and (not isinstance(argv, list) or not argv or
                                not all(isinstance(a, str) and a and "\x00" not in a for a in argv)):
            raise ValueError(f"{name}: argv must be a nonempty string array or null")
        if argv is not None and na is not None:
            raise ValueError(f"{name}: cannot both run and be not-applicable")
        cwd = check.get("cwd", ".")
        if not isinstance(cwd, str) or not contained(root, cwd).is_dir():
            raise ValueError(f"{name}: invalid working directory")
        timeout = check.get("timeout_seconds", 900)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
            raise ValueError(f"{name}: timeout must be between 0 and 3600 seconds")
        if na is not None:
            if not isinstance(na, dict) or not isinstance(na.get("reason"), str) or len(na["reason"].strip()) < 15:
                raise ValueError(f"{name}: meaningful not-applicable reason required")
            decision = na.get("decision")
            if not isinstance(decision, str) or not contained(root, decision).is_file():
                raise ValueError(f"{name}: existing in-repository decision file required")
    if all(c.get("not_applicable") is not None for c in checks):
        raise ValueError("All checks cannot be declared not-applicable")
    return checks, hashlib.sha256(raw).hexdigest()

def execute(check: dict[str, Any], root: Path, out: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"id": check["id"], "argv": check.get("argv"), "cwd": check.get("cwd", ".")}
    if check.get("not_applicable") is not None:
        return {**result, "status": "NOT_APPLICABLE", "scope_decision": check["not_applicable"]}
    if check.get("argv") is None:
        return {**result, "status": "BLOCKED", "reason": "UNCONFIGURED: wire a real check"}
    log = contained(root, str(out / (check["id"] + ".log")))
    start = time.monotonic()
    result["log"] = str(log.relative_to(root))
    with log.open("wb") as stream:
        argv = [sys.executable if arg == "{python}" else arg for arg in check["argv"]]
        execution = supervise(argv, cwd=contained(root, check.get("cwd", ".")),
                              timeout=check.get("timeout_seconds", 900),
                              max_output_bytes=8_000_000, log=stream)
    result.update(status=execution.status, exit_code=execution.exit_code)
    if execution.reason:
        result["reason"] = execution.reason
    result["duration_seconds"] = round(time.monotonic() - start, 3)
    return result

def git_value(root: Path, args: list[str]) -> str | None:
    try:
        proc = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=5)
        return proc.stdout.strip() if proc.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None

def run_checks(root: Path, config: str) -> tuple[int, dict[str, Any]]:
    root = root.resolve()
    out = contained(root, ".seed-ci-artifacts")
    out.mkdir(exist_ok=True)
    report_path = contained(root, str(out / "report.json"))
    dirty = git_value(root, ["status", "--porcelain"])
    report: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_sha": git_value(root, ["rev-parse", "HEAD"]),
        "working_tree_dirty": None if dirty is None else bool(dirty),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "checks": [],
        "evidence_scope": "Command execution report, not independent attestation or proof of test adequacy",
    }
    try:
        checks, digest = load_config(contained(root, config), root)
        report["config_sha256"] = digest
        failed_setup = False
        for check in checks:
            if failed_setup:
                result = {"id": check["id"], "status": "NOT_RUN", "reason": "Prior setup failed or was blocked"}
            else:
                result = execute(check, root, out)
            report["checks"].append(result)
            if check["id"] == "setup" and result["status"] not in {"PASS", "NOT_APPLICABLE"}:
                failed_setup = True
        statuses = {r["status"] for r in report["checks"]}
        code = 2 if statuses & {"BLOCKED", "NOT_RUN"} else 1 if "FAIL" in statuses else 0
        report["status"] = "BLOCKED" if code == 2 else "FAIL" if code == 1 else "PASS"
    except (OSError, ValueError, TypeError) as exc:
        code = 2
        report.update(status="BLOCKED", reason=f"Invalid/unavailable configuration: {exc}")
    report["source_fingerprint"] = integrity_fingerprint(root)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return code, report

def run_traceability(root: Path, code: int, report: dict) -> tuple[int, dict]:
    """Connect opted-in feature maps to application CI, never to template-only checks."""
    from seedlib.spec_trace import configured_features, run_configured
    try:
        configured = configured_features(root)
        trace = (run_configured(root) if code == 0 else
                 {'status': 'NOT_RUN', 'reason': 'Earlier application checks failed or were blocked'}) if configured else {
                     'status': 'NOT_CONFIGURED', 'features': [], 'note': 'No feature opted in; no trace coverage claimed.'}
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        trace = {'status': 'BLOCKED', 'reason': str(exc)}
    report['requirement_traceability'] = trace
    if trace['status'] == 'FAIL': code = max(code, 1)
    elif trace['status'] in {'BLOCKED', 'NOT_RUN', 'STALE'}: code = 2
    report['status'] = 'BLOCKED' if code == 2 else 'FAIL' if code == 1 else 'PASS'
    report['source_fingerprint'] = integrity_fingerprint(root)
    from seedlib.common import atomic_json, safe_path
    atomic_json(safe_path(root, '.seed-ci-artifacts/report.json'), report)
    return code, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="quality/seed-checks.json")
    parser.add_argument("--check-pr-title", action="store_true")
    parser.add_argument("--profile", action="store_true", help="Retained starter checks plus configured application checks")
    parser.add_argument("--profile-info", action="store_true")
    parser.add_argument("--github-output", action="store_true")
    args = parser.parse_args()
    if args.profile_info:
        try:
            from seedlib.acceptance import profile
            selected=profile(Path.cwd())
            print(json.dumps(selected,indent=2))
            if args.github_output:
                with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as output:
                    output.write("mcp_required="+str(selected['mcp_required']).lower()+"\n")
            return 0
        except (ValueError,OSError,KeyError,TypeError) as exc:
            print("BLOCKED: "+str(exc),file=sys.stderr);return 2
    if args.check_pr_title:
        ok = valid_title(os.environ.get("SEED_PR_TITLE", ""))
        print("PR title valid" if ok else "PR title invalid: use type(scope): description (maximum 120 characters)")
        return 0 if ok else 1
    try:
        if args.profile:
            from seedlib.acceptance import profile
            selected=profile(Path.cwd())
            code,report=run_checks(Path.cwd(),'quality/template-checks.json')
            if code or selected['profile']=='maintainer':
                print('Retained starter checks: '+report['status'])
                return code
            # Retain both reports. Application configuration cannot erase starter outcomes.
            retained=Path('.seed-ci-artifacts/starter-report.json')
            retained.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        code, report = run_checks(Path.cwd(), args.config)
        if args.profile:
            code, report = run_traceability(Path.cwd(), code, report)
    except (OSError, ValueError) as exc:
        print(f"BLOCKED: cannot initialize evidence output: {type(exc).__name__}", file=sys.stderr)
        return 2
    for check in report["checks"]:
        print(f"{check['id']}: {check['status']}")
    print(f"Overall: {report['status']}; evidence: .seed-ci-artifacts/report.json")
    if "reason" in report: print(report["reason"])
    return code

if __name__ == "__main__":
    raise SystemExit(main())
