import copy
import json
import unittest
from pathlib import Path

from milestone_monitor import ContractError, reconcile

DRIFT = json.loads((Path(__file__).parents[1] / "examples/drift.json").read_text())


class ReconcileTests(unittest.TestCase):
    def test_drift_staleness_and_timezone_equivalence(self):
        result = reconcile(DRIFT)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["milestone_count"], 3)
        self.assertEqual(
            [(x["key"], x["kind"]) for x in result["findings"]],
            [
                ("data-load", "stale_source"),
                ("data-load", "due_at_mismatch"),
                ("data-load", "status_mismatch"),
                ("launch", "owner_mismatch"),
            ],
        )
        self.assertEqual(result["findings"][0]["detail"], "tracker")
        self.assertEqual(result["findings"][1]["owner"], "Data specialist")

    def test_exact_alignment_even_with_different_offset(self):
        item = copy.deepcopy(DRIFT)
        item["tracker"] = copy.deepcopy(item["plan"])
        item["tracker"][0]["due_at"] = "2026-10-05T11:30:00Z"
        self.assertEqual(reconcile(item)["findings"], [])
        self.assertEqual(reconcile(item)["status"], "aligned")

    def test_missing_and_duplicate_records(self):
        item = copy.deepcopy(DRIFT)
        item["tracker"].pop()
        self.assertEqual(reconcile(item)["findings"][-1]["kind"], "missing_source")
        item["tracker"].append(copy.deepcopy(item["tracker"][0]))
        with self.assertRaisesRegex(ContractError, "duplicate key"):
            reconcile(item)

    def test_invalid_and_future_times(self):
        for changed, expected in [
            ("2026-10-12T17:00:00", "timezone"),
            ("nonsense", "ISO 8601"),
        ]:
            item = copy.deepcopy(DRIFT)
            item["plan"][0]["due_at"] = changed
            with self.assertRaisesRegex(ContractError, expected):
                reconcile(item)
        item = copy.deepcopy(DRIFT)
        item["tracker"][0]["updated_at"] = "2026-09-27T09:00:00+05:30"
        with self.assertRaisesRegex(ContractError, "after as_of"):
            reconcile(item)

    def test_policy_defaults_and_custom_threshold(self):
        from milestone_monitor.policy import load_policy, validate_policy

        default = load_policy("policy.yaml")
        self.assertEqual(reconcile(DRIFT, default), reconcile(DRIFT))
        custom = {
            **default,
            "stale_after_days": 20,
            "stale_age_bands": [20, 30],
            "status_compatible": [],
        }
        kinds = [x["kind"] for x in reconcile(DRIFT, custom)["findings"]]
        self.assertNotIn("stale_source", kinds)
        self.assertIn("status_mismatch", kinds)
        with self.assertRaisesRegex(ValueError, "sorted unique"):
            validate_policy({**default, "stale_age_bands": [14, 7]})


if __name__ == "__main__":
    unittest.main()
