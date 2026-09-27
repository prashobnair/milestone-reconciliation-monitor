# Changelog

## 0.1.1 - proposed

- Add strict Python 3.11+ packaging, uv lock, CI and release artifact workflow.
- Record stale-only age changes as `aged`, preserving history without repeated digest eligibility until a configured band is crossed.
- Move stale threshold and status-compatibility pairs into validated, JSON-compatible `policy.yaml`.
- Add a five-day synthetic regression and fail-closed policy/contract tests. No remote connector or notification is included.

## 0.1.0

Initial offline reconciliation and local SQLite review ledger.
