import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from milestone_monitor import ContractError
from milestone_monitor.state import apply_snapshot

DRIFT = json.loads((Path(__file__).parents[1] / "examples/drift.json").read_text())


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "state.sqlite3"

    def apply(self, snapshot):
        return apply_snapshot(self.db, snapshot)

    def counts(self):
        with sqlite3.connect(self.db) as db:
            return db.execute(
                "SELECT transition, count(*) FROM history GROUP BY transition"
            ).fetchall()

    def test_open_then_repeat_suppresses_history(self):
        first = self.apply(DRIFT)
        self.assertEqual(
            ["opened"] * 4, [x["transition"] for x in first["transitions"]]
        )
        again = self.apply(DRIFT)
        self.assertEqual(
            ["unchanged"] * 4, [x["transition"] for x in again["transitions"]]
        )
        self.assertEqual([("opened", 4)], self.counts())
        self.assertEqual(0, again["notification_count"])

    def test_changed_snapshot_retains_identity(self):
        self.apply(DRIFT)
        changed = copy.deepcopy(DRIFT)
        changed["as_of"] = "2026-09-27T12:00:00+05:30"
        changed["tracker"][1]["due_at"] = "2026-10-09T12:00:00+05:30"
        result = self.apply(changed)
        self.assertIn("changed", [x["transition"] for x in result["transitions"]])
        self.assertIn(("changed", 1), self.counts())
        self.assertIn(("aged", 1), self.counts())

    def test_resolution_and_reopen(self):
        self.apply(DRIFT)
        aligned = copy.deepcopy(DRIFT)
        aligned["as_of"] = "2026-09-27T12:00:00+05:30"
        aligned["tracker"] = copy.deepcopy(aligned["plan"])
        result = self.apply(aligned)
        self.assertEqual(
            ["resolved"] * 4, [x["transition"] for x in result["transitions"]]
        )
        later = copy.deepcopy(DRIFT)
        later["as_of"] = "2026-09-28T12:00:00+05:30"
        self.assertEqual(
            ["reopened"] * 4,
            [x["transition"] for x in self.apply(later)["transitions"]],
        )
        self.assertIn(("reopened", 4), self.counts())

    def test_invalid_input_does_not_mutate(self):
        self.apply(DRIFT)
        bad = copy.deepcopy(DRIFT)
        bad["tracker"][0]["due_at"] = "not-a-time"
        with self.assertRaises(ContractError):
            self.apply(bad)
        self.assertEqual([("opened", 4)], self.counts())

    def test_older_snapshot_does_not_mutate(self):
        later = copy.deepcopy(DRIFT)
        later["as_of"] = "2026-09-27T12:00:00+05:30"
        self.apply(later)
        changed = copy.deepcopy(DRIFT)
        changed["as_of"] = "2026-09-26T11:00:00+05:30"
        with self.assertRaises(ValueError):
            self.apply(changed)
        self.assertEqual([("opened", 4)], self.counts())

    def test_other_project_state_is_isolated(self):
        self.apply(DRIFT)
        second = copy.deepcopy(DRIFT)
        second["project_id"] = "other-project"
        self.apply(second)
        self.assertEqual([("opened", 8)], self.counts())

    def test_stale_age_five_days_is_non_notifying_until_band(self):
        snapshot = copy.deepcopy(DRIFT)
        snapshot["tracker"][1]["updated_at"] = "2026-09-17T12:00:00+05:30"
        ages = []
        for day in range(26, 31):
            snapshot["as_of"] = f"2026-09-{day}T09:00:00+05:30"
            result = self.apply(snapshot)
            stale = next(
                t
                for t in result["transitions"]
                if t["finding"]["kind"] == "stale_source"
            )
            ages.append(stale["transition"])
            self.assertEqual(day == 26, stale["digest_eligible"])
        self.assertEqual(["opened", "aged", "aged", "aged", "aged"], ages)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(
                5,
                db.execute(
                    "SELECT count(*) FROM history WHERE transition IN ('opened','aged') AND finding_json LIKE '%stale_source%'"
                ).fetchone()[0],
            )
        snapshot["as_of"] = "2026-10-02T09:00:00+05:30"
        result = self.apply(snapshot)
        stale = next(
            t for t in result["transitions"] if t["finding"]["kind"] == "stale_source"
        )
        self.assertEqual("aged", stale["transition"])
        self.assertTrue(stale["digest_eligible"])


if __name__ == "__main__":
    unittest.main()
