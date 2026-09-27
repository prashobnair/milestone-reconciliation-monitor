"""Pure comparison of versioned plan and tracker snapshots."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

from .policy import load_policy, validate_policy

KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}\Z")


@dataclass
class ContractError(Exception):
    code: str
    detail: str

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ContractError(
            "invalid_time", f"{field} must be an ISO 8601 timestamp with timezone"
        )
    try:
        date = datetime.fromisoformat(
            value[:-1] + "+00:00" if value.endswith("Z") else value
        )
    except ValueError as exc:
        raise ContractError(
            "invalid_time", f"{field} is not an ISO 8601 timestamp"
        ) from exc
    if date.tzinfo is None or date.utcoffset() is None:
        raise ContractError("invalid_time", f"{field} must include a timezone")
    return date.astimezone(UTC)


class Milestone(TypedDict):
    key: str
    title: str
    owner: str
    status: str
    due_at: datetime
    updated_at: datetime


def _record(raw: object, source: str) -> Milestone:
    if not isinstance(raw, Mapping):
        raise ContractError("invalid_record", f"{source} milestone must be an object")
    allowed = {"key", "title", "due_at", "status", "updated_at", "owner"}
    unknown = set(raw) - allowed
    if unknown:
        raise ContractError(
            "invalid_record",
            f"{source} has unknown fields: {', '.join(sorted(map(str, unknown)))}",
        )
    key = raw.get("key")
    if not isinstance(key, str) or not KEY.fullmatch(key):
        raise ContractError(
            "invalid_record", f"{source} key must be 1-100 safe characters"
        )
    title = raw.get("title")
    owner = raw.get("owner")
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        raise ContractError(
            "invalid_record", f"{source} title must be 1-120 characters"
        )
    if not isinstance(owner, str) or not owner.strip() or len(owner) > 120:
        raise ContractError(
            "invalid_record", f"{source} owner must be 1-120 characters"
        )
    status = raw.get("status")
    if status not in (
        "planned",
        "in_progress",
        "done",
        "open_unknown",
    ) or not isinstance(status, str):
        raise ContractError(
            "invalid_record",
            f"{source} status must be planned, in_progress, done or open_unknown",
        )
    due = _timestamp(raw.get("due_at"), f"{source}.due_at")
    updated = _timestamp(raw.get("updated_at"), f"{source}.updated_at")
    return {
        "key": key,
        "title": title.strip(),
        "owner": owner.strip(),
        "status": status,
        "due_at": due,
        "updated_at": updated,
    }


def _index(records: object, source: str) -> dict[str, Milestone]:
    if not isinstance(records, list):
        raise ContractError("invalid_snapshot", f"{source} must be a list")
    result: dict[str, Milestone] = {}
    for raw in records:
        record = _record(raw, source)
        key = record["key"]
        if key in result:
            raise ContractError(
                "duplicate_key", f"{source} contains duplicate key {key}"
            )
        result[key] = record
    return result


def reconcile(
    snapshot: Mapping[str, object], policy: Mapping[str, object] | None = None
) -> dict[str, Any]:
    """Return review findings, never an automatic winner or notification."""
    if not isinstance(snapshot, Mapping):
        raise ContractError("invalid_snapshot", "snapshot must be an object")
    if set(snapshot) != {"schema_version", "project_id", "as_of", "plan", "tracker"}:
        raise ContractError(
            "invalid_snapshot",
            "expected schema_version, project_id, as_of, plan and tracker only",
        )
    if snapshot.get("schema_version") != "1":
        raise ContractError("unsupported_version", "schema_version must be 1")
    project_id = snapshot.get("project_id")
    if not isinstance(project_id, str) or not KEY.fullmatch(project_id):
        raise ContractError(
            "invalid_snapshot", "project_id must be 1-100 safe characters"
        )
    rules = validate_policy(policy) if policy is not None else load_policy()
    as_of = _timestamp(snapshot.get("as_of"), "as_of")
    plan = _index(snapshot["plan"], "plan")
    tracker = _index(snapshot["tracker"], "tracker")
    if not plan and not tracker:
        raise ContractError(
            "invalid_snapshot", "at least one source milestone is required"
        )
    findings: list[dict[str, Any]] = []
    for key in sorted(plan.keys() | tracker.keys()):
        planned, tracked = plan.get(key), tracker.get(key)
        representative = planned if planned is not None else tracked
        if (
            representative is None
        ):  # impossible for a key in the union, but do not rely on assert
            raise ContractError("invalid_snapshot", "milestone disappeared")
        title = representative["title"]
        owner = representative["owner"]
        if not planned or not tracked:
            findings.append(
                {
                    "key": key,
                    "title": title,
                    "owner": owner,
                    "kind": "missing_source",
                    "detail": "plan" if not planned else "tracker",
                    "requires_review": True,
                }
            )
            continue
        for source, item in [("plan", planned), ("tracker", tracked)]:
            if item is None:
                raise ContractError(
                    "invalid_snapshot", "milestone missing after validation"
                )
            if item["updated_at"] > as_of:
                raise ContractError(
                    "future_update", f"{source} {key} updated_at is after as_of"
                )
            age = as_of - item["updated_at"]
            if age > timedelta(days=rules["stale_after_days"]):
                findings.append(
                    {
                        "key": key,
                        "title": title,
                        "owner": owner,
                        "kind": "stale_source",
                        "detail": source,
                        "age_days": age.days,
                        "requires_review": True,
                    }
                )
        if planned["due_at"] != tracked["due_at"]:
            findings.append(
                {
                    "key": key,
                    "title": title,
                    "owner": owner,
                    "kind": "due_at_mismatch",
                    "plan": planned["due_at"].isoformat(),
                    "tracker": tracked["due_at"].isoformat(),
                    "requires_review": True,
                }
            )
        if (
            planned["status"] != tracked["status"]
            and [planned["status"], tracked["status"]] not in rules["status_compatible"]
        ):
            findings.append(
                {
                    "key": key,
                    "title": title,
                    "owner": owner,
                    "kind": "status_mismatch",
                    "plan": planned["status"],
                    "tracker": tracked["status"],
                    "requires_review": True,
                }
            )
        if planned["owner"] != tracked["owner"]:
            findings.append(
                {
                    "key": key,
                    "title": title,
                    "owner": owner,
                    "kind": "owner_mismatch",
                    "plan": planned["owner"],
                    "tracker": tracked["owner"],
                    "requires_review": True,
                }
            )
    return {
        "schema_version": "1",
        "project_id": project_id,
        "as_of": as_of.isoformat(),
        "status": "needs_review" if findings else "aligned",
        "findings": findings,
        "milestone_count": len(plan.keys() | tracker.keys()),
    }
