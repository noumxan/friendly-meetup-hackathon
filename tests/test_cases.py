import json
import unittest
from pathlib import Path

from evals.checks import CHECKS

CASES = Path(__file__).parent.parent / "evals" / "cases.jsonl"
ADVERSARIAL = Path(__file__).parent.parent / "evals" / "cases_adversarial.jsonl"


class CaseTests(unittest.TestCase):
    def setUp(self):
        self.cases = [
            json.loads(line)
            for line in CASES.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_dataset_size_and_ids(self):
        self.assertGreaterEqual(len(self.cases), 20)
        self.assertLessEqual(len(self.cases), 30)
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_case_is_runnable(self):
        for case in self.cases:
            self.assertTrue(case["input"].strip(), case["id"])
            self.assertTrue(case["expected"].strip(), case["id"])
            self.assertIsInstance(case["checks"], list, case["id"])
            self.assertTrue(case["tags"], case["id"])
            for check in case["checks"]:
                self.assertIn(check["type"], CHECKS, case["id"])
                passed = CHECKS[check["type"]](
                    {"answer": "", "tool_calls": [], "latency_s": 0},
                    check.get("value"),
                )
                self.assertIsInstance(passed, bool, (case["id"], check["type"]))


class AdversarialCaseTests(unittest.TestCase):
    def test_suite_is_separate_and_valid(self):
        historical = {
            json.loads(line)["id"]
            for line in CASES.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        rows = [
            json.loads(line)
            for line in ADVERSARIAL.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertGreaterEqual(len(rows), 15)
        self.assertLessEqual(len(rows), 25)
        ids = [row["id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(set(ids).isdisjoint(historical))
        severities = set()
        for row in rows:
            self.assertTrue(row["input"].strip())
            self.assertTrue(row["expected"].strip())
            self.assertTrue(row["why"].strip())
            self.assertIn(row["severity"], {"low", "medium", "high", "critical"})
            severities.add(row["severity"])
            for check in row["checks"]:
                self.assertIn(check["type"], CHECKS)
        self.assertIn("low", severities)
        self.assertIn("critical", severities)


if __name__ == "__main__":
    unittest.main()
