import copy
import json
import unittest
from pathlib import Path

from milestone_monitor.core import ContractError
from milestone_monitor.zoho_sample import map_export

EXAMPLE = json.loads(
    (Path(__file__).parents[1] / "examples/zoho-shaped-portfolio.json").read_text()
)


class ZohoSampleTests(unittest.TestCase):
    def test_two_project_portfolio(self):
        result = map_export(EXAMPLE)
        self.assertEqual(result["project_count"], 2)
        self.assertEqual(result["finding_count"], 3)
        self.assertEqual(
            [p["status"] for p in result["projects"]], ["needs_review", "aligned"]
        )
        self.assertEqual(result["projects"][0]["findings"][0]["kind"], "stale_source")

    def test_duplicate_project_and_bad_export_block(self):
        case = copy.deepcopy(EXAMPLE)
        case["projects"].append(copy.deepcopy(case["projects"][0]))
        with self.assertRaisesRegex(ContractError, "duplicate project"):
            map_export(case)
        case = copy.deepcopy(EXAMPLE)
        case["projects"][0]["zoho_export"]["milestones"][0]["end_date_long"] = (
            "tomorrow"
        )
        with self.assertRaisesRegex(ContractError, "epoch milliseconds"):
            map_export(case)
        case = copy.deepcopy(EXAMPLE)
        case["projects"][0]["zoho_export"]["milestones"][0]["status"] = "inprogress"
        with self.assertRaisesRegex(ContractError, "completed or notcompleted"):
            map_export(case)


if __name__ == "__main__":
    unittest.main()
