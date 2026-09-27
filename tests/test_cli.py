"""Exercise offline entry points without a network or customer data."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def invoke(module: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_reconcile_cli_demo_and_invalid_file():
    result = invoke("milestone_monitor.cli", "examples/drift.json")
    assert result.returncode == 0
    assert json.loads(result.stdout)["milestone_count"] == 3
    invalid = invoke("milestone_monitor.cli", "/missing-snapshot.json")
    assert invalid.returncode == 2
    assert "reconciliation error:" in invalid.stderr


def test_zoho_sample_demo_and_invalid_file():
    result = invoke(
        "milestone_monitor.zoho_sample", "examples/zoho-shaped-portfolio.json"
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["project_count"] == 2
    invalid = invoke("milestone_monitor.zoho_sample", "/missing-export.json")
    assert invalid.returncode == 2
    assert "export error:" in invalid.stderr


def test_state_cli_demo_and_invalid_file(tmp_path: Path):
    db = str(tmp_path / "review.sqlite3")
    result = invoke("milestone_monitor.state_cli", db, "examples/drift.json")
    assert result.returncode == 0
    assert len(json.loads(result.stdout)["transitions"]) == 4
    repeat = invoke("milestone_monitor.state_cli", db, "examples/drift.json")
    assert repeat.returncode == 0
    assert all(
        x["transition"] == "unchanged" for x in json.loads(repeat.stdout)["transitions"]
    )
    invalid = invoke("milestone_monitor.state_cli", db, "/missing-snapshot.json")
    assert invalid.returncode == 2
    assert "state error:" in invalid.stderr


def test_entrypoints_in_process(monkeypatch, capsys, tmp_path: Path):
    from milestone_monitor import cli, state_cli, zoho_sample

    cases = [
        (cli.main, ["examples/drift.json"], "milestone_count"),
        (
            state_cli.main,
            [str(tmp_path / "live.sqlite"), "examples/drift.json"],
            "transitions",
        ),
        (zoho_sample.main, ["examples/zoho-shaped-portfolio.json"], "project_count"),
    ]
    for entry, args, key in cases:
        monkeypatch.setattr(sys, "argv", ["monitor", *args])
        assert entry() == 0
        assert key in json.loads(capsys.readouterr().out)
        monkeypatch.setattr(sys, "argv", ["monitor", *args[:-1], "/missing.json"])
        assert entry() == 2
        assert "error:" in capsys.readouterr().err
