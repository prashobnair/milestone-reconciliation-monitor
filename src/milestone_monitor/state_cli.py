"""Keep local review history for synthetic snapshots; no external alerts."""
from __future__ import annotations
import argparse
import json
import sqlite3
import sys
from .core import ContractError
from .state import apply_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', help='local SQLite path (created if absent)')
    parser.add_argument('snapshot', help='version-1 synthetic snapshot JSON')
    args = parser.parse_args()
    try:
        with open(args.snapshot, encoding='utf-8') as source:
            report = apply_snapshot(args.database, json.load(source))
    except (OSError, sqlite3.Error, json.JSONDecodeError, ContractError, ValueError) as exc:
        print(f'state error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
