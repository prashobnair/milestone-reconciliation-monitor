"""Read a synthetic snapshot and print review findings; make no changes."""
from __future__ import annotations
import argparse
import json
import sys
from .core import ContractError, reconcile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', help='version-1 synthetic JSON snapshot')
    args = parser.parse_args()
    try:
        with open(args.snapshot, encoding='utf-8') as source:
            report = reconcile(json.load(source))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f'reconciliation error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
