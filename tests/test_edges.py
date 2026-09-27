"""Synthetic edge cases for the core and policy gates."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from milestone_monitor.core import ContractError, reconcile
from milestone_monitor.policy import DEFAULT_POLICY, validate_policy

DRIFT = json.loads((Path(__file__).parents[1] / "examples/drift.json").read_text())


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("schema_version", "2", "unsupported_version"),
        ("project_id", "bad key", "invalid_snapshot"),
        ("as_of", "not-a-date", "invalid_time"),
        ("tracker", "bad", "invalid_snapshot"),
    ],
)
def test_snapshot_rejections(field: str, value: object, code: str):
    sample = copy.deepcopy(DRIFT)
    sample[field] = value
    with pytest.raises(ContractError) as error:
        reconcile(sample)
    assert error.value.code == code


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("key", "bad key", "invalid_record"),
        ("title", "", "invalid_record"),
        ("owner", "", "invalid_record"),
        ("status", "unknown", "invalid_record"),
        ("updated_at", "not-a-time", "invalid_time"),
        ("due_at", "2026-10-12T12:00:00", "invalid_time"),
    ],
)
def test_milestone_rejections(field: str, value: object, code: str):
    sample = copy.deepcopy(DRIFT)
    sample["plan"][0][field] = value
    with pytest.raises(ContractError) as error:
        reconcile(sample)
    assert error.value.code == code


def test_empty_and_missing_source():
    sample = copy.deepcopy(DRIFT)
    sample["plan"] = []
    sample["tracker"] = []
    with pytest.raises(ContractError, match="at least one"):
        reconcile(sample)
    sample["plan"] = copy.deepcopy(DRIFT["plan"])
    assert all(x["kind"] == "missing_source" for x in reconcile(sample)["findings"])
    sample["tracker"] = copy.deepcopy(DRIFT["tracker"])
    sample["plan"] = []
    assert all(x["kind"] == "missing_source" for x in reconcile(sample)["findings"])


@pytest.mark.parametrize(
    "changes",
    [
        {"stale_after_days": True},
        {"stale_after_days": -1},
        {"stale_age_bands": []},
        {"stale_age_bands": [7, 7]},
        {"status_compatible": [["planned", "foo"]]},
        {
            "status_compatible": [
                ["planned", "open_unknown"],
                ["planned", "open_unknown"],
            ]
        },
    ],
)
def test_policy_fails_closed(changes: dict):
    with pytest.raises(ValueError):
        validate_policy({**DEFAULT_POLICY, **changes})


def test_zoho_export_rejects_bad_inputs():
    from milestone_monitor.zoho_sample import _stamp, map_export

    sample = json.loads(
        (Path(__file__).parents[1] / "examples/zoho-shaped-portfolio.json").read_text()
    )
    with pytest.raises(ContractError, match="nonnegative"):
        _stamp(True, "date")
    with pytest.raises(ContractError, match="outside supported"):
        _stamp(10**50, "date")
    for value, code in [(None, "invalid_export"), ({}, "invalid_export")]:
        with pytest.raises(ContractError) as error:
            map_export(value)
        assert error.value.code == code
    for field, value in [("schema_version", "2"), ("as_of", 1), ("projects", [])]:
        changed = copy.deepcopy(sample)
        changed[field] = value
        with pytest.raises(ContractError):
            map_export(changed)
    project = sample["projects"][0]
    for field, value in [("project_name", " "), ("zoho_export", {})]:
        changed = copy.deepcopy(sample)
        changed["projects"][0][field] = value
        with pytest.raises(ContractError):
            map_export(changed)
    changed = copy.deepcopy(sample)
    changed["projects"][1]["project_id"] = project["project_id"]
    with pytest.raises(ContractError, match="duplicate"):
        map_export(changed)
    for field, value in [("status", "unknown"), ("end_date_long", -1)]:
        changed = copy.deepcopy(sample)
        changed["projects"][0]["zoho_export"]["milestones"][0][field] = value
        with pytest.raises(ContractError):
            map_export(changed)
