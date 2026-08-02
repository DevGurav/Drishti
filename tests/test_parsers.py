import unittest
from datetime import date

from app.parsers import (
    extract_expiry_candidates,
    extract_mrp_candidates,
    is_expired,
    parse_expiry_date,
)


class TestExtraction(unittest.TestCase):
    def test_expiry_candidates_month_year(self):
        self.assertEqual(extract_expiry_candidates("EXP: MAR2027"), ["MAR2027"])

    def test_expiry_candidates_numeric(self):
        self.assertEqual(extract_expiry_candidates("Exp. 03/2027"), ["03/2027"])

    def test_mrp_candidates(self):
        self.assertEqual(extract_mrp_candidates("MRP: Rs. 45.50"), ["45.50"])

    def test_mrp_candidates_rupee_symbol(self):
        self.assertEqual(extract_mrp_candidates("₹120"), ["120"])


class TestParseExpiryDate(unittest.TestCase):
    def test_month_abbrev_and_two_digit_year(self):
        self.assertEqual(parse_expiry_date("MAR27"), date(2027, 3, 31))

    def test_month_abbrev_and_four_digit_year(self):
        self.assertEqual(parse_expiry_date("MAR2027"), date(2027, 3, 31))

    def test_numeric_mm_yyyy(self):
        self.assertEqual(parse_expiry_date("03/2027"), date(2027, 3, 31))

    def test_december_handled(self):
        self.assertEqual(parse_expiry_date("DEC2026"), date(2026, 12, 31))

    def test_unparseable_returns_none(self):
        self.assertIsNone(parse_expiry_date("not a date"))


class TestIsExpired(unittest.TestCase):
    def test_past_date_is_expired(self):
        self.assertTrue(is_expired("JAN2020", today=date(2026, 1, 1)))

    def test_future_date_is_not_expired(self):
        self.assertFalse(is_expired("JAN2030", today=date(2026, 1, 1)))

    def test_unparseable_returns_none_not_false(self):
        self.assertIsNone(is_expired("garbage"))


if __name__ == "__main__":
    unittest.main()
