# Milestone Reconciliation Monitor

A private portfolio prototype using fictional implementation milestones. It compares a project plan with a tracker snapshot, preserves both sources, and gives a project manager a review list. It does **not** change either system, select a winning date, send alerts, or connect to a real app.

## Why a separate project

The Implementation Intake Translator is about turning messy kickoff facts into a reviewed spec. This project tests a different operating constraint: a delivery plan drifts from its tracker between reviews, and stale records can mislead a PM. Reconciliation must work across time zones and avoid duplicate alerts before it can be scheduled safely.

## Run locally

Requires Python 3.10+; runtime uses only the standard library. From the repo root:

```sh
PYTHONPATH=src python3 -m milestone_monitor.cli examples/drift.json
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The fixture has three fictional milestones. Design sign-off dates are the same instant in IST and UTC, so they are not flagged. Data load has a stale tracker record, due-date mismatch and status mismatch. Launch has an owner mismatch. No trial account, API key, Docker, or external connection is needed. Only synthetic data belongs here.

## Current limits

This is a pure reconciliation slice, not yet a monitor. No SQLite run history, duplicate-alert suppression, scheduler, UI, or owner-resolution workflow is present. The seven-day stale threshold is a demonstrator rule, not an external SLA. Missing records are flagged for review; neither source silently wins. Next increment: durable run/alert state and tests for repeated snapshots, changed snapshots and recovery. Then a local demo view and CI.
