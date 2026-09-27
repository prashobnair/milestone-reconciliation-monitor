"""Validate and map fictional Zoho Projects-like milestone exports.

The field subset mirrors published Zoho Projects REST milestone examples. This
is a synthetic snapshot mapper, not an authenticated API client.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime

from .core import ContractError, reconcile


def _stamp(milliseconds: object, field: str) -> str:
    if (
        isinstance(milliseconds, bool)
        or not isinstance(milliseconds, int)
        or milliseconds < 0
    ):
        raise ContractError(
            "invalid_export", f"{field} must be nonnegative epoch milliseconds"
        )
    try:
        return datetime.fromtimestamp(milliseconds / 1000, tz=UTC).isoformat()
    except (OverflowError, OSError, ValueError) as exc:
        raise ContractError(
            "invalid_export", f"{field} is outside supported date range"
        ) from exc


def map_export(export: Mapping[str, object]) -> dict[str, object]:
    """Translate a synthetic PM baseline plus per-project tracker snapshots."""
    if not isinstance(export, Mapping) or set(export) != {
        "schema_version",
        "as_of",
        "projects",
    }:
        raise ContractError(
            "invalid_export", "expected schema_version, as_of and projects"
        )
    if export["schema_version"] != "1":
        raise ContractError("unsupported_version", "schema_version must be 1")
    as_of = export["as_of"]
    if not isinstance(as_of, str):
        raise ContractError("invalid_export", "as_of must be timestamp text")
    projects = export["projects"]
    if not isinstance(projects, list) or not projects:
        raise ContractError("invalid_export", "projects must be a nonempty list")
    seen_projects: set[str] = set()
    packets = []
    for project in projects:
        if not isinstance(project, Mapping) or set(project) != {
            "project_id",
            "project_name",
            "baseline",
            "zoho_export",
        }:
            raise ContractError(
                "invalid_export",
                "each project needs project_id, project_name, baseline and zoho_export",
            )
        project_id, name = project["project_id"], project["project_name"]
        if (
            not isinstance(project_id, str)
            or not isinstance(name, str)
            or not name.strip()
        ):
            raise ContractError(
                "invalid_export", "project_id and project_name must be text"
            )
        if project_id in seen_projects:
            raise ContractError(
                "duplicate_project", f"duplicate project_id {project_id}"
            )
        seen_projects.add(project_id)
        records = project["zoho_export"]
        if (
            not isinstance(records, Mapping)
            or set(records) != {"milestones"}
            or not isinstance(records["milestones"], list)
        ):
            raise ContractError(
                "invalid_export", "zoho_export must contain a milestones list"
            )
        tracker = []
        for row in records["milestones"]:
            required = {
                "id",
                "name",
                "owner_name",
                "end_date_long",
                "status",
                "last_modified_time",
            }
            if not isinstance(row, Mapping) or not required.issubset(row):
                raise ContractError(
                    "invalid_export",
                    "milestone missing id, name, owner_name, end_date_long, status or last_modified_time",
                )
            raw_status = row["status"]
            if raw_status not in ("completed", "notcompleted"):
                raise ContractError(
                    "invalid_export",
                    "milestone status must be completed or notcompleted",
                )
            tracker.append(
                {
                    "key": str(row["id"]),
                    "title": row["name"],
                    "owner": row["owner_name"],
                    "due_at": _stamp(row["end_date_long"], "end_date_long"),
                    "updated_at": _stamp(
                        row["last_modified_time"], "last_modified_time"
                    ),
                    "status": "done" if raw_status == "completed" else "open_unknown",
                }
            )
        snapshot = {
            "schema_version": "1",
            "project_id": project_id,
            "as_of": as_of,
            "plan": project["baseline"],
            "tracker": tracker,
        }
        result = reconcile(snapshot)
        packets.append({"project_name": name.strip(), **result})
    return {
        "schema_version": "1",
        "project_count": len(packets),
        "finding_count": sum(len(p["findings"]) for p in packets),
        "projects": packets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare fictional Zoho Projects-like exports to synthetic PM baselines"
    )
    parser.add_argument("sample")
    args = parser.parse_args()
    try:
        with open(args.sample, encoding="utf-8") as source:
            result = map_export(json.load(source))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"export error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
