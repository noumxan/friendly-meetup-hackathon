import unittest

from agent.agent import _enforce_capabilities
from agent.guard import SAFE_FALLBACK


class _Reply:
    def __init__(self, content):
        self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]
        self.usage = None


class _Client:
    def __init__(self, content):
        self.content = content
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        return _Reply(self.content)


class AgentGuardTests(unittest.TestCase):
    def test_clean_answer_is_unchanged(self):
        answer, guard = _enforce_capabilities(_Client("unused"), "model", [], "I cannot issue the refund.")
        self.assertEqual(answer, "I cannot issue the refund.")
        self.assertFalse(guard["rewritten"])
        self.assertFalse(guard["fallback"])

    def test_second_violation_uses_the_fallback_unchanged(self):
        answer, guard = _enforce_capabilities(
            _Client("I will issue the refund now."),
            "model",
            [],
            "I can process the refund for you.",
        )
        self.assertEqual(answer, SAFE_FALLBACK)
        self.assertTrue(guard["fallback"])
        self.assertIn("refund_promise", guard["violations"])

    def test_one_rewrite_can_remove_the_claim(self):
        answer, guard = _enforce_capabilities(
            _Client("I cannot issue the refund. Submit a claim at parcelpigeon.example/claims."),
            "model",
            [],
            "I will issue the refund today.",
        )
        self.assertIn("claims", answer)
        self.assertTrue(guard["rewritten"])
        self.assertFalse(guard["fallback"])


if __name__ == "__main__":
    unittest.main()
