"""Offline policy, stored as JSON-compatible YAML for zero runtime dependencies."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DEFAULT_POLICY: dict[str, Any] = {
    "stale_after_days": 7,
    "stale_age_bands": [7, 14, 30],
    "status_compatible": [["planned", "open_unknown"], ["in_progress", "open_unknown"]],
}


def validate_policy(raw: Mapping[str, object]) -> dict[str, Any]:
    """Fail closed on malformed policy instead of silently relaxing comparisons."""
    if not isinstance(raw, Mapping) or set(raw) != set(DEFAULT_POLICY):
        raise ValueError(
            "policy needs stale_after_days, stale_age_bands, status_compatible"
        )
    threshold = raw["stale_after_days"]
    bands = raw["stale_age_bands"]
    pairs = raw["status_compatible"]
    if type(threshold) is not int or threshold < 0:
        raise ValueError("stale_after_days must be a nonnegative integer")
    if (
        not isinstance(bands, list)
        or not bands
        or any(type(x) is not int or x < 0 for x in bands)
    ):
        raise ValueError("stale_age_bands must be nonnegative integer boundaries")
    if bands != sorted(set(bands)) or bands[0] != threshold:
        raise ValueError(
            "stale_age_bands must be sorted unique and begin at stale_after_days"
        )
    statuses = {"planned", "in_progress", "done", "open_unknown"}
    if not isinstance(pairs, list) or any(
        not isinstance(pair, list)
        or len(pair) != 2
        or any(not isinstance(value, str) or value not in statuses for value in pair)
        for pair in pairs
    ):
        raise ValueError("status_compatible needs pairs of known statuses")
    if len({tuple(pair) for pair in pairs}) != len(pairs):
        raise ValueError("status_compatible contains duplicates")
    return {
        "stale_after_days": threshold,
        "stale_age_bands": bands,
        "status_compatible": pairs,
    }


def load_policy(path: str | Path | None = None) -> dict[str, Any]:
    """JSON is a valid YAML document; policy.yaml stays stdlib-readable."""
    if path is None:
        return validate_policy(DEFAULT_POLICY)
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_policy(raw)
