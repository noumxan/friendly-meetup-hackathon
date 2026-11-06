import unittest
from datetime import date

from agent.working_days import (
    assess_lateness,
    bank_holidays,
    easter_sunday,
    is_working_day,
    working_days_after,
)


class WorkingDayTests(unittest.TestCase):
    def test_known_easter_and_bank_holidays(self):
        self.assertEqual(easter_sunday(2024), date(2024, 3, 31))
        self.assertEqual(easter_sunday(2026), date(2026, 4, 5))
        holidays_2024 = bank_holidays(2024)
        for day in (
            date(2024, 1, 1),
            date(2024, 3, 29),
            date(2024, 4, 1),
            date(2024, 5, 6),
            date(2024, 5, 27),
            date(2024, 8, 26),
            date(2024, 12, 25),
            date(2024, 12, 26),
        ):
            self.assertIn(day, holidays_2024)
        self.assertEqual(len(holidays_2024), 8)
        holidays_2026 = bank_holidays(2026)
        self.assertIn(date(2026, 1, 1), holidays_2026)
        self.assertIn(date(2026, 4, 3), holidays_2026)
        self.assertIn(date(2026, 4, 6), holidays_2026)
        self.assertIn(date(2026, 5, 4), holidays_2026)
        self.assertIn(date(2026, 5, 25), holidays_2026)
        self.assertIn(date(2026, 8, 31), holidays_2026)
        self.assertIn(date(2026, 12, 25), holidays_2026)
        self.assertIn(date(2026, 12, 28), holidays_2026)
        self.assertNotIn(date(2026, 12, 26), holidays_2026)

    def test_weekend_substitutes(self):
        self.assertIn(date(2022, 1, 3), bank_holidays(2022))
        self.assertNotIn(date(2022, 1, 1), bank_holidays(2022))
        self.assertIn(date(2022, 12, 26), bank_holidays(2022))
        self.assertIn(date(2022, 12, 27), bank_holidays(2022))
        self.assertIn(date(2021, 12, 27), bank_holidays(2021))
        self.assertIn(date(2021, 12, 28), bank_holidays(2021))

    def test_friday_to_monday_is_one_working_day(self):
        result = assess_lateness("2026-10-23", "2026-10-26")
        self.assertTrue(result["ok"])
        self.assertEqual(result["calendar_days_after_expected"], 3)
        self.assertEqual(result["working_days_after_expected"], 1)
        self.assertFalse(result["standard_delivery_fee_refundable"])
        self.assertTrue(result["express_delivery_fee_refundable"])

    def test_friday_to_tuesday_is_two_working_days(self):
        result = assess_lateness("2026-10-23", "2026-10-27")
        self.assertEqual(result["working_days_after_expected"], 2)
        self.assertFalse(result["standard_delivery_fee_refundable"])

    def test_more_than_two_working_days(self):
        result = assess_lateness("2026-10-23", "2026-10-28")
        self.assertEqual(result["working_days_after_expected"], 3)
        self.assertTrue(result["standard_delivery_fee_refundable"])

    def test_same_day_and_early(self):
        same = assess_lateness("2026-11-03", "2026-11-03")
        self.assertEqual(same["working_days_after_expected"], 0)
        self.assertTrue(same["on_time"])
        self.assertFalse(same["express_delivery_fee_refundable"])
        early = assess_lateness("2026-11-03", "2026-11-02")
        self.assertTrue(early["early"])
        self.assertLess(early["working_days_after_expected"], 0)

    def test_month_and_year_boundaries(self):
        self.assertEqual(working_days_after(date(2026, 1, 30), date(2026, 2, 2)), 1)
        self.assertEqual(working_days_after(date(2026, 12, 31), date(2027, 1, 4)), 1)
        self.assertFalse(is_working_day(date(2027, 1, 1)))

    def test_bank_holiday_is_not_counted(self):
        self.assertFalse(is_working_day(date(2026, 5, 4)))
        self.assertEqual(working_days_after(date(2026, 5, 1), date(2026, 5, 4)), 0)
        self.assertEqual(working_days_after(date(2026, 4, 2), date(2026, 4, 7)), 1)

    def test_invalid_dates_do_not_guess(self):
        for expected, actual in ((None, "2026-10-26"), ("", "2026-10-26"), ("23/10/2026", "2026-10-26"), ("2026-02-31", "2026-03-02")):
            result = assess_lateness(expected, actual)
            self.assertFalse(result["ok"])
            self.assertIn("error", result)
            self.assertNotIn("working_days_after_expected", result)


if __name__ == "__main__":
    unittest.main()
