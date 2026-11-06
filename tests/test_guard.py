import unittest

from agent.guard import SAFE_FALLBACK, find_violations


class GuardTests(unittest.TestCase):
    def test_real_failures_are_caught(self):
        samples = {
            "refund_promise": "Could you verify your identity so I can proceed with issuing the refund?",
            "refund_confirmed": "Your refund has been issued to the original card.",
            "identity_workflow": "I can guide you through verifying your identity, and then read the address.",
            "address_changed": "I have changed the delivery address to 10 High Street.",
            "claim_submitted": "I will submit the claim for you now.",
        }
        for expected, text in samples.items():
            self.assertIn(expected, find_violations(text), text)
        self.assertIn(
            "refund_promise",
            find_violations("I can't see the parcel, but I will issue the refund today."),
        )

    def test_paraphrased_promises_are_caught(self):
        paraphrases = [
            "I'll sort the refund for you.",
            "Consider it refunded.",
            "Your money is on its way back.",
            "We can refund you directly in this chat.",
            "I've gone ahead and processed your refund.",
            "Let me just send the £6.50 back.",
        ]
        for text in paraphrases:
            self.assertTrue(find_violations(text), text)

    def test_legitimate_refusals_are_allowed(self):
        allowed = [
            "I cannot issue the refund. Please submit a claim at parcelpigeon.example/claims.",
            "I can't verify your identity in this chat, so I can't read out the address.",
            "I am unable to change the delivery address once it is out for delivery.",
            "The delivery fee is refundable, but I will not issue the refund myself.",
            "Refunds are processed within 5 working days to the original payment method.",
            "You are eligible for a refund of the delivery fee.",
            "You can claim a refund of the delivery fee at parcelpigeon.example/claims.",
            "The delivery fee is refundable, but only through the claims page. I cannot pay it here.",
            "Refunds take 5 working days.",
            "I will not sort a refund from this chat.",
            "I have not processed your refund.",
            "The parcel is on its way.",
            "I can't see the parcel, but I can explain the claim process.",
            "The address has not been changed.",
        ]
        for text in allowed:
            self.assertEqual(find_violations(text), [], text)

    def test_fallback_does_not_promise_an_action(self):
        self.assertEqual(find_violations(SAFE_FALLBACK), [])
        self.assertIn("parcelpigeon.example/claims", SAFE_FALLBACK)


if __name__ == "__main__":
    unittest.main()
