import unittest

from evals.checks import CHECKS


def result(answer="", calls=None, latency=1.0, error=None):
    payload = {"answer": answer, "tool_calls": calls or [], "latency_s": latency, "tokens": 10}
    if error:
        payload["error"] = error
    return payload


class CheckTests(unittest.TestCase):
    def test_every_check_returns_bool(self):
        sample = result(
            "Next Day is £6.50.",
            [{"name": "get_order", "args": {"order_id": "PP-1002"}}, {"name": "search_policies", "args": {"query": "refund"}}],
        )
        values = {
            "contains": "6.50",
            "not_contains": "Bermondsey",
            "tool_called": "get_order",
            "tool_not_called": "missing_tool",
            "tool_called_with": {"name": "get_order", "args": {"order_id": "PP-1002"}},
            "no_tools": None,
            "no_unexpected_tools": ["get_order", "search_policies"],
            "max_seconds": 5,
            "max_words": 20,
            "matches_regex": r"£\s*6\.50",
            "no_prohibited_claim": None,
        }
        for name, fn in CHECKS.items():
            self.assertIsInstance(fn(sample, values[name]), bool, name)

    def test_contains_and_prohibited_text(self):
        row = result("The address is 8 Bermondsey Street, London SE1 3TQ.")
        self.assertTrue(CHECKS["contains"](row, "bermondsey"))
        self.assertFalse(CHECKS["not_contains"](row, "SE1"))
        self.assertTrue(CHECKS["not_contains"](row, "Elm Road"))
        self.assertFalse(CHECKS["contains"](row, ""))

    def test_tool_called(self):
        row = result(calls=[{"name": "search_policies", "args": {"query": "price"}}])
        self.assertTrue(CHECKS["tool_called"](row, "search_policies"))
        self.assertFalse(CHECKS["tool_called"](row, "get_order"))
        self.assertFalse(CHECKS["tool_called"](row, ""))
        self.assertTrue(CHECKS["tool_not_called"](row, "get_order"))

    def test_tool_arguments(self):
        row = result(calls=[{"name": "get_order", "args": {"order_id": " pp-1003 "}}])
        self.assertTrue(
            CHECKS["tool_called_with"](row, {"name": "get_order", "args": {"order_id": "PP-1003"}})
        )
        self.assertFalse(
            CHECKS["tool_called_with"](row, {"name": "get_order", "args": {"order_id": "PP-1004"}})
        )
        self.assertFalse(CHECKS["tool_called_with"](row, "get_order"))

    def test_unexpected_tools_and_latency(self):
        row = result("Short answer.", calls=[{"name": "get_order", "args": {}}], latency=2.5)
        self.assertFalse(CHECKS["no_tools"](row, None))
        self.assertTrue(CHECKS["no_tools"](result("Just ask for the order ID."), None))
        self.assertFalse(CHECKS["no_unexpected_tools"](row, ["search_policies"]))
        self.assertTrue(CHECKS["no_unexpected_tools"](row, ["get_order"]))
        self.assertTrue(CHECKS["max_seconds"](row, 3))
        self.assertFalse(CHECKS["max_seconds"](row, 1))
        self.assertFalse(CHECKS["max_seconds"](result("x", latency=0, error="boom"), 30))
        self.assertTrue(CHECKS["max_words"](row, 2))
        self.assertFalse(CHECKS["max_words"](row, 1))

    def test_bad_values_fail_closed(self):
        row = result("hello")
        self.assertFalse(CHECKS["matches_regex"](row, "["))
        self.assertFalse(CHECKS["matches_regex"](row, ""))
        self.assertFalse(CHECKS["max_seconds"](row, "soon"))
        self.assertFalse(CHECKS["no_unexpected_tools"](row, None))
        self.assertFalse(CHECKS["tool_called"]({}, None))


if __name__ == "__main__":
    unittest.main()
