"""Default-policy golden outputs protect the offline input/output contracts."""

import json
from pathlib import Path

from milestone_monitor.core import reconcile
from milestone_monitor.zoho_sample import map_export

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden"


def test_default_policy_snapshot_golden():
    source = json.loads((ROOT / "examples" / "drift.json").read_text(encoding="utf-8"))
    expected = json.loads((GOLDEN / "drift-default.json").read_text(encoding="utf-8"))
    assert reconcile(source) == expected
    assert json.dumps(reconcile(source), indent=2) + "\n" == (
        GOLDEN / "drift-default.json"
    ).read_text(encoding="utf-8")


def test_default_policy_zoho_portfolio_golden():
    source = json.loads(
        (ROOT / "examples" / "zoho-shaped-portfolio.json").read_text(encoding="utf-8")
    )
    expected = json.loads(
        (GOLDEN / "zoho-shaped-portfolio-default.json").read_text(encoding="utf-8")
    )
    assert map_export(source) == expected
    assert json.dumps(map_export(source), indent=2) + "\n" == (
        GOLDEN / "zoho-shaped-portfolio-default.json"
    ).read_text(encoding="utf-8")
