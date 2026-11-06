import json
import unittest
from unittest.mock import patch

from evals.judge import _failure, judge, parse_verdict
from evals.run import overall_passed


class ParseTests(unittest.TestCase):
    def test_passing_scores(self):
        for score in (4, 5):
            verdict = parse_verdict(json.dumps({"score": score, "reason": "Matches the policy."}))
            self.assertEqual(verdict["score"], score)
            self.assertTrue(verdict["passed"])
            self.assertNotIn("error", verdict)

    def test_failing_scores(self):
        for score in (1, 2, 3):
            verdict = parse_verdict(json.dumps({"score": score, "reason": "Misses the refund rule."}))
            self.assertFalse(verdict["passed"])
            self.assertNotIn("error", verdict)

    def test_markdown_and_score_prefix(self):
        verdict = parse_verdict('```json\n{"score": "4/5", "reason": "Close enough."}\n```')
        self.assertEqual(verdict["score"], 4)
        self.assertTrue(verdict["passed"])

    def test_invalid_output_is_not_a_pass(self):
        for text in ("sure, looks good", "", "{", '{"reason": "no score"}', '{"score": true, "reason": "x"}'):
            verdict = parse_verdict(text)
            self.assertFalse(verdict["passed"], text)
            self.assertTrue(verdict["error"])

    def test_out_of_range_and_missing_reason_fail(self):
        high = parse_verdict('{"score": 9, "reason": "too high"}')
        empty = parse_verdict('{"score": 5, "reason": "  "}')
        self.assertFalse(high["passed"])
        self.assertFalse(empty["passed"])
        self.assertTrue(high["error"])
        self.assertTrue(empty["error"])

    def test_secret_is_redacted(self):
        verdict = _failure("bad key sk-abcDEF123456")
        self.assertNotIn("abcDEF123456", verdict["reason"])
        self.assertIn("sk-REDACTED", verdict["reason"])
        self.assertFalse(verdict["passed"])


class JudgeContractTests(unittest.TestCase):
    def test_missing_expectation_skips(self):
        self.assertIsNone(judge({"input": "hello"}, {"answer": "hi"}))
        self.assertIsNone(judge({"input": "hello", "expected": "   "}, {"answer": "hi"}))

    def test_api_error_is_not_a_pass(self):
        class Boom:
            def __init__(self):
                self.chat = self
                self.completions = self

            def create(self, **kwargs):
                raise RuntimeError("connection reset sk-supersecretvalue")

        with patch("evals.judge.client_for", return_value=(Boom(), "gpt-4.1")):
            verdict = judge(
                {"input": "How much is Next Day?", "expected": "£6.50 up to 2 kg."},
                {"answer": "£6.50", "tool_calls": []},
            )
        self.assertFalse(verdict["passed"])
        self.assertTrue(verdict["error"])
        self.assertNotIn("supersecretvalue", verdict["reason"])

    def test_failed_judge_fails_the_case_even_when_checks_pass(self):
        checks = [{"type": "contains", "passed": True}]
        verdict = {"score": None, "passed": False, "reason": "Judge error", "error": True}
        self.assertFalse(overall_passed(checks, verdict, {"answer": "ok"}))

    def test_unscored_when_nothing_ran(self):
        self.assertIsNone(overall_passed([], None, {"answer": "ok"}))

    def test_agent_error_fails(self):
        self.assertFalse(overall_passed([{"passed": True}], {"passed": True}, {"error": "nope"}))


if __name__ == "__main__":
    unittest.main()
