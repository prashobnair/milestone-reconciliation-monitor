[![CI](https://github.com/prashobnair/milestone-reconciliation-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/prashobnair/milestone-reconciliation-monitor/actions/workflows/ci.yml)

# Milestone Reconciliation Monitor

An offline portfolio prototype using fictional implementation milestones. It compares a project plan with a tracker snapshot, preserves both sources, and gives a project manager a review list. It does **not** change either system, select a winning date, send alerts, or connect to a real app.

## Why a separate project

The Implementation Intake Translator is about turning messy kickoff facts into a reviewed spec. This project tests a different operating constraint: a delivery plan drifts from its tracker between reviews, and stale records can mislead a PM. Reconciliation must work across time zones and avoid duplicate alerts before it can be scheduled safely.

## Run locally

Requires Python 3.11+; runtime uses only the standard library. From the repo root:

```sh
PYTHONPATH=src python3 -m milestone_monitor.cli examples/drift.json
PYTHONPATH=src python3 -m milestone_monitor.zoho_sample examples/zoho-shaped-portfolio.json
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The first fixture has three fictional milestones. The second simulates two Zoho Projects-like project exports and PM-owned baselines; see `docs/ZOHO_SAMPLE.md` for exactly which fields are sourced from published Zoho REST examples and which are invented for the demo. `notcompleted` is mapped to `open_unknown`, so the importer does not pretend to know planned versus in-progress state. Design sign-off dates are the same instant in IST and UTC, so they are not flagged. Data load has a stale tracker record, due-date mismatch and status mismatch. Launch has an owner mismatch. No trial account, API key, Docker, or external connection is needed. Only synthetic data belongs here.

## Current limits

This is a local reconciliation and review-state slice, not a connected or scheduled monitor. SQLite tracks finding transitions and avoids duplicate history rows on unchanged snapshots; it does not send alerts, schedule jobs, offer a UI, or resolve owners. The default seven-day stale threshold is a demonstrator rule, not an external SLA. Missing records are flagged for review; neither source silently wins. A future increment could add a local demo view, then a source adapter only after verifying current Zoho API contracts.

## Persist review changes across runs

The monitor now has a **local SQLite review ledger**. It takes the same fictional version-1 snapshot and compares each finding with the prior observation of that project. Run it twice to see four `opened` transitions followed by four `unchanged` transitions:

```sh
PYTHONPATH=src python3 -m milestone_monitor.state_cli /tmp/milestone-review.sqlite examples/drift.json
PYTHONPATH=src python3 -m milestone_monitor.state_cli /tmp/milestone-review.sqlite examples/drift.json
```

Use a different local database path for a clean run. The ledger stores active findings, first/last seen times and an append-only transition history (`opened`, `aged`, `changed`, `resolved`, `reopened`). A changed due date keeps the same finding identity while its signature changes. Resolution does not delete past evidence, and a later recurrence reopens it. A project is isolated from other project IDs. Invalid or older snapshots are rejected before changing existing state. See `docs/STATE.md` for the state schema and limitations.

This is still not a scheduled or connected monitor. The CLI performs **zero notifications**; suppressing repeat history rows is not authorization to send reminders. The database path is local, not a hosted service. Do not put customer data in it or commit a `.sqlite` file. No Zoho trial, credentials or remote service are needed to run this increment.

## WP-03: reproducible checks and policy

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). Run `uv sync --locked --group dev`, then `uv run pytest`; no trial, Zoho account, API key or network call is needed after dependency installation. CI checks Ruff, `mypy --strict`, three Python versions, full branch coverage (80% overall, 90% core), Bandit, pip-audit and gitleaks. The demo job uploads synthetic JSON artifacts. The release workflow runs only when the lead pushes a `v*` tag; it builds wheel/sdist and attaches them to the GitHub release.

`policy.yaml` is JSON-compatible YAML, so the stdlib can parse it without a YAML dependency. The defaults reproduce the earlier 7-day stale threshold and status compatibility (`planned` or `in_progress` versus Zoho's `open_unknown`). The bands 7/14/30 are review boundaries. Override with `--policy path/to/policy.yaml` on the reconciliation or state CLI; malformed or unknown fields fail closed. The Zoho-shaped importer remains a fixed demonstration of the default policy.

A `stale_source` finding keeps its `(key, kind, source)` identity when `age_days` changes. Its age-only update is logged as `aged`, and it is digest-eligible only if its age crosses a configured band after the opening band. An unrelated material content change still becomes `changed`. `digest_eligible` is metadata for future review, **not** a sent notification; `notification_count` stays zero. Running the same sample twice preserves the history without extra entries. The five-day regression walks daily stale-age changes, then crosses the 14-day band. See `docs/STATE.md`.
