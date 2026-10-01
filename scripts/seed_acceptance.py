#!/usr/bin/env python3
"""Report the independent recorded-scope gate. Does not run tests or grant authority."""
import argparse
from pathlib import Path
import sys

from seedlib.acceptance import event_base, scope_status
from seedlib.common import dump, atomic_json, safe_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--base', help='Fetched immutable base SHA for the protected documentation-only policy')
    parser.add_argument('--ci', action='store_true', help='Use the GitHub event base if available')
    parser.add_argument('--out', help='Optional repository-relative report path')
    args = parser.parse_args()
    try:
        result = scope_status(args.root.resolve(), base=args.base or (event_base() if args.ci else None))
        if args.out:
            atomic_json(safe_path(args.root.resolve(), args.out), result)
        print(dump(result), end='')
        return 0 if result['status'] in {'PASS', 'NOT_APPLICABLE'} else 2
    except (ValueError, OSError, KeyError, TypeError, ImportError) as exc:
        print('BLOCKED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
