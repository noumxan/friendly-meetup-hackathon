import json
import unittest
from pathlib import Path

from agent.tools import get_order

ORDERS = Path(__file__).parents[1] / "agent" / "data" / "orders.json"


class GetOrderTests(unittest.TestCase):
    def test_unknown_order(self):
        self.assertIn("No order found", get_order("PP-9999"))

    def test_personal_details_are_withheld(self):
        order = json.loads(get_order(" pp-1004 "))
        text = json.dumps(order).lower()
        for secret in ("bermondsey", "jonah", "okafor", "se1", "amira", "elm"):
            self.assertNotIn(secret, text)
        self.assertNotIn("customer_name", order)
        self.assertNotIn("address", order)
        self.assertNotIn("identity_verified", order)
        self.assertEqual(order["status"], "out for delivery")
        self.assertEqual(order["order_id"], "PP-1004")
        self.assertEqual(order["personal_details"], "withheld")

    def test_operational_facts_remain(self):
        order = json.loads(get_order("PP-1002"))
        self.assertEqual(order["service"], "Next Day")
        self.assertEqual(order["delivered"], "2026-11-05")
        self.assertEqual(order["expected_delivery"], "2026-11-03")
        self.assertEqual(order["lateness"]["working_days_after_expected"], 2)
        self.assertTrue(order["lateness"]["express_delivery_fee_refundable"])

    def test_standard_weekend_is_one_working_day(self):
        order = json.loads(get_order("PP-1005"))
        self.assertEqual(order["lateness"]["calendar_days_after_expected"], 3)
        self.assertEqual(order["lateness"]["working_days_after_expected"], 1)
        self.assertFalse(order["lateness"]["standard_delivery_fee_refundable"])

    def test_every_order_hides_its_own_personal_data(self):
        orders = json.loads(ORDERS.read_text(encoding="utf-8"))
        for order in orders:
            text = get_order(order["order_id"])
            for field in ("customer_name", "address"):
                self.assertNotIn(order[field], text)


if __name__ == "__main__":
    unittest.main()
