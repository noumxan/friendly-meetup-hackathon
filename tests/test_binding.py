import json
import unittest

from agent.binding import prepare_tool_call
from agent.eligibility import claims_delivery_fee_refund, contradicts_decision, required_policy_heading
from agent.tools import search_policies, working_days_between


class BindingTests(unittest.TestCase):
    def test_guessed_year_is_replaced_by_the_order_record(self):
        question = "Order PP-1005 was due on 23 October and arrived on 26 October. I want a refund."
        args, error = prepare_tool_call(
            question,
            "working_days_between",
            {"start_date": "2023-10-23", "end_date": "2023-10-26"},
        )
        self.assertIsNone(error)
        self.assertEqual(args["order_id"], "PP-1005")
        result = json.loads(working_days_between(**args))
        self.assertEqual(result["working_days_after_expected"], 1)
        self.assertFalse(result["delivery_fee_refundable"])
        self.assertTrue(result["model_supplied_dates_ignored"])
        self.assertEqual(result["ignored_start_date"], "2023-10-23")
        self.assertNotIn("2023-10-26", json.dumps({k: result[k] for k in ("expected", "actual")}))

    def test_conflicting_order_id_is_rejected(self):
        question = "Refund PP-1005."
        args, error = prepare_tool_call(question, "get_order", {"order_id": "PP-1001"})
        self.assertEqual(args["order_id"], "PP-1001")
        payload = json.loads(error or "")
        self.assertEqual(payload["error"], "order_id_mismatch")
        self.assertNotIn("delivered", error or "")

    def test_several_order_ids_are_not_guessed(self):
        question = "PP-1001 and PP-1005 were both late."
        _args, error = prepare_tool_call(
            question,
            "working_days_between",
            {"start_date": "2026-10-23", "end_date": "2026-10-26"},
        )
        self.assertEqual(json.loads(error or "")["error"], "multiple_order_ids")

    def test_explicit_choice_among_several_orders_is_kept(self):
        question = "PP-1001 and PP-1005 were both late."
        args, error = prepare_tool_call(question, "working_days_between", {"order_id": "PP-1005"})
        self.assertIsNone(error)
        result = json.loads(working_days_between(**args))
        self.assertEqual(result["order_id"], "PP-1005")
        self.assertEqual(result["working_days_after_expected"], 1)

    def test_stated_dates_without_an_order_are_counted(self):
        question = "Due on Friday 23 October 2026 and arrived on Monday 26 October 2026."
        args, error = prepare_tool_call(
            question,
            "working_days_between",
            {"start_date": "2026-10-23", "end_date": "2026-10-26"},
        )
        self.assertIsNone(error)
        result = json.loads(working_days_between(**args))
        self.assertEqual(result["source"], "stated_dates")
        self.assertEqual(result["working_days_after_expected"], 1)


class PolicyGroundingTests(unittest.TestCase):
    def test_refund_question_retrieves_the_refund_section(self):
        self.assertEqual(required_policy_heading("I want a refund."), "Late deliveries and refunds")
        text = search_policies(
            "late delivery refund delivery fee standard next day same day working days claims"
        )
        self.assertIn("Late deliveries and refunds", text)
        self.assertIn("more than 2 working days late", text)
        self.assertIn("parcelpigeon.example/claims", text)

    def test_loss_question_retrieves_the_loss_section(self):
        self.assertEqual(required_policy_heading("What compensation for a lost parcel?"), "Lost or damaged parcels")
        text = search_policies("lost damaged parcel compensation photos report 28 days 7 days")
        self.assertIn("Lost or damaged parcels", text)
        self.assertIn("28 days", text)

    def test_price_question_does_not_force_a_refund_policy(self):
        self.assertIsNone(required_policy_heading("How much is Next Day delivery?"))

    def test_explanation_can_disagree_with_the_record(self):
        decision = {"order_id": "PP-1005", "delivery_fee_refundable": False, "working_days_after_expected": 1}
        self.assertTrue(claims_delivery_fee_refund("You are eligible for a refund of the delivery fee."))
        self.assertFalse(claims_delivery_fee_refund("The delivery fee is not refundable."))
        self.assertIsNone(claims_delivery_fee_refund("Please tell me the order ID."))
        self.assertEqual(contradicts_decision("You are eligible for a refund of the delivery fee.", [decision])["order_id"], "PP-1005")
        self.assertIsNone(contradicts_decision("The delivery fee is not refundable.", [decision]))


if __name__ == "__main__":
    unittest.main()
