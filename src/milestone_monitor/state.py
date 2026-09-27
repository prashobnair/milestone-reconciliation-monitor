"""Durable local review state for synthetic reconciliation findings. No notifications."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .core import reconcile
from .policy import load_policy, validate_policy

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
  project_id TEXT NOT NULL,
  finding_id TEXT NOT NULL,
  signature TEXT NOT NULL,
  finding_json TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  active INTEGER NOT NULL CHECK(active IN (0, 1)),
  PRIMARY KEY(project_id, finding_id)
);
CREATE TABLE IF NOT EXISTS observations (
  project_id TEXT PRIMARY KEY,
  last_as_of TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  finding_id TEXT NOT NULL,
  transition TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  finding_json TEXT NOT NULL
);
"""


def _canonical(item: object) -> str:
    return json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _identity(finding: dict[str, Any]) -> str:
    # Identity excludes mutable values, preserving a thread as a due date changes.
    stable = {k: finding.get(k) for k in ("key", "kind", "detail")}
    return hashlib.sha256(_canonical(stable).encode()).hexdigest()[:24]


def apply_snapshot(
    db_path: str | Path,
    snapshot: dict[str, Any],
    policy: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    """Validate first, then atomically reconcile active findings with one project.

    The database is local review bookkeeping, not a remote monitor. A changed
    finding keeps its identity but records a new signature and history event.
    """
    rules = validate_policy(policy) if policy is not None else load_policy()
    report = reconcile(snapshot, rules)
    project, observed = report["project_id"], report["as_of"]
    current = {_identity(f): f for f in report["findings"]}
    if len(current) != len(report["findings"]):
        raise ValueError("finding identity collision; no state changed")
    with sqlite3.connect(db_path) as db:
        db.executescript(SCHEMA)
        # An explicit transaction keeps the entire observation all-or-nothing.
        db.execute("BEGIN IMMEDIATE")
        try:
            rows = {
                row[0]: row
                for row in db.execute(
                    "SELECT finding_id, signature, finding_json, first_seen, last_seen, active "
                    "FROM findings WHERE project_id=?",
                    (project,),
                )
            }
            prior_observation = db.execute(
                "SELECT last_as_of FROM observations WHERE project_id=?", (project,)
            ).fetchone()
            if prior_observation and observed < prior_observation[0]:
                raise ValueError(
                    "snapshot as_of precedes already observed project state"
                )
            transitions = []
            for fid, finding in sorted(current.items()):
                body = _canonical(finding)
                signature = hashlib.sha256(body.encode()).hexdigest()
                previous = rows.get(fid)
                if previous is None:
                    action = "opened"
                    db.execute(
                        "INSERT INTO findings VALUES (?,?,?,?,?,?,1)",
                        (project, fid, signature, body, observed, observed),
                    )
                elif not previous[5]:
                    action = "reopened"
                    db.execute(
                        "UPDATE findings SET signature=?, finding_json=?, last_seen=?, active=1 "
                        "WHERE project_id=? AND finding_id=?",
                        (signature, body, observed, project, fid),
                    )
                elif previous[1] != signature:
                    former = json.loads(previous[2])
                    age_only = finding["kind"] == "stale_source" and {
                        k: v for k, v in former.items() if k != "age_days"
                    } == {k: v for k, v in finding.items() if k != "age_days"}
                    action = "aged" if age_only else "changed"
                    db.execute(
                        "UPDATE findings SET signature=?, finding_json=?, last_seen=? "
                        "WHERE project_id=? AND finding_id=?",
                        (signature, body, observed, project, fid),
                    )
                else:
                    action = "unchanged"
                    db.execute(
                        "UPDATE findings SET last_seen=? WHERE project_id=? AND finding_id=?",
                        (observed, project, fid),
                    )
                if action != "unchanged":
                    db.execute(
                        "INSERT INTO history(project_id,finding_id,transition,observed_at,finding_json) "
                        "VALUES (?,?,?,?,?)",
                        (project, fid, action, observed, body),
                    )
                notify = action in ("opened", "reopened", "changed")
                if action == "aged":
                    old_age = former["age_days"]
                    new_age = finding["age_days"]
                    crossed = [
                        band
                        for band in rules["stale_age_bands"]
                        if old_age < band <= new_age
                        and band != rules["stale_after_days"]
                    ]
                    notify = bool(crossed)
                transitions.append(
                    {
                        "finding_id": fid,
                        "transition": action,
                        "finding": finding,
                        "digest_eligible": notify,
                    }
                )
            for fid, previous in sorted(rows.items()):
                if previous[5] and fid not in current:
                    db.execute(
                        "UPDATE findings SET active=0, last_seen=? WHERE project_id=? AND finding_id=?",
                        (observed, project, fid),
                    )
                    db.execute(
                        "INSERT INTO history(project_id,finding_id,transition,observed_at,finding_json) "
                        "VALUES (?,?,?,?,?)",
                        (project, fid, "resolved", observed, previous[2]),
                    )
                    transitions.append(
                        {
                            "finding_id": fid,
                            "transition": "resolved",
                            "finding": json.loads(previous[2]),
                            "digest_eligible": True,
                        }
                    )
            db.execute(
                "INSERT INTO observations(project_id,last_as_of) VALUES (?,?) "
                "ON CONFLICT(project_id) DO UPDATE SET last_as_of=excluded.last_as_of",
                (project, observed),
            )
            db.commit()
        except BaseException:
            db.rollback()
            raise
    return {
        "project_id": project,
        "as_of": observed,
        "status": report["status"],
        "transitions": transitions,
        "notification_count": 0,
        "digest_eligible_count": sum(t["digest_eligible"] for t in transitions),
    }
