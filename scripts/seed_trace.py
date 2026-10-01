#!/usr/bin/env python3
"""Plan or run optional feature requirement/JUnit mappings. Never grants build approval."""
from pathlib import Path
import argparse
import json
import sys

from seedlib.spec_trace import check, plan_status, run, run_configured


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    plan = subs.add_parser('plan', help='Validate declared requirements and planned test references without execution')
    plan.add_argument('--feature', required=True)
    execute = subs.add_parser('run', help='Run trusted test commands and retain fresh, revision-bound JUnit evidence')
    selection = execute.add_mutually_exclusive_group(required=True)
    selection.add_argument('--feature')
    selection.add_argument('--all', action='store_true')
    verify = subs.add_parser('check', help='Recheck stored result integrity and current source')
    verify.add_argument('--report', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.action == 'plan': result = plan_status(root, args.feature)
        elif args.action == 'check': result = check(root, args.report)
        elif args.all: result = run_configured(root)
        else: result = run(root, args.feature)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        # Planned/not-applicable checks are explicitly not executed behavior verification.
        if result['status'] in {'PASS', 'PLANNED', 'NOT_APPLICABLE'}: return 0
        return 1 if result['status'] == 'FAIL' else 2
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        print('BLOCKED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
