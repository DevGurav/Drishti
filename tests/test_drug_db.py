import unittest

from app.drug_db import DEFAULT_DB_PATH, DrugDatabase


class TestLongestMatchWins(unittest.TestCase):
    """Real drug names nest inside one another, so 'first hit' is not safe.

    Every case here is a genuine NLEM 2022 pair. Before the longest-match rule the
    answer depended on file order, and an alphabetical database returns the *shorter*
    name first -- reporting a different drug than the one on the label.
    """

    def test_noradrenaline_is_not_reported_as_adrenaline(self):
        db = DrugDatabase(["Adrenaline", "Noradrenaline"])
        self.assertEqual(db.find_match("NORADRENALINE INJECTION IP"), "Noradrenaline")

    def test_hydroxychloroquine_is_not_reported_as_chloroquine(self):
        db = DrugDatabase(["Chloroquine", "Hydroxychloroquine"])
        self.assertEqual(db.find_match("HYDROXYCHLOROQUINE SULPHATE 200"), "Hydroxychloroquine")

    def test_methylprednisolone_is_not_reported_as_prednisolone(self):
        db = DrugDatabase(["Prednisolone", "Methylprednisolone"])
        self.assertEqual(db.find_match("METHYLPREDNISOLONE TABLETS"), "Methylprednisolone")

    def test_insulin_glargine_is_not_reported_as_plain_insulin(self):
        db = DrugDatabase(["Insulin", "Insulin Glargine"])
        self.assertEqual(db.find_match("INSULIN GLARGINE 100IU/ML"), "Insulin Glargine")

    def test_order_in_the_file_does_not_change_the_answer(self):
        text = "NORADRENALINE BITARTRATE"
        forwards = DrugDatabase(["Adrenaline", "Noradrenaline"]).find_match(text)
        backwards = DrugDatabase(["Noradrenaline", "Adrenaline"]).find_match(text)
        self.assertEqual(forwards, backwards)

    def test_shorter_name_still_matches_when_it_is_the_one_present(self):
        db = DrugDatabase(["Adrenaline", "Noradrenaline"])
        self.assertEqual(db.find_match("ADRENALINE 1MG/ML"), "Adrenaline")


class TestShippedDatabase(unittest.TestCase):
    """Guards the committed NLEM file itself, since app/ trusts it blindly."""

    @classmethod
    def setUpClass(cls):
        cls.db = DrugDatabase.from_file()
        cls.names = [
            line.strip() for line in DEFAULT_DB_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

    def test_database_is_the_full_nlem_list(self):
        # A silent parse failure in build_drug_db.py would ship a truncated list, which
        # declines on real medicines while still looking like it works.
        self.assertGreater(len(self.names), 380)

    def test_matches_the_generic_name_on_a_real_strip(self):
        # The exact OCR text medicine mode saw on the Paracip strip in the Colab run.
        ocr = "PARACIP-500 PARACETAMOL TABLETS IP EXP.OCT.2026 Rs.10.30"
        self.assertEqual(self.db.find_match(ocr), "Paracetamol")

    def test_combination_strip_reports_every_ingredient(self):
        """A user holding IBUPROFEN+PARACETAMOL was told about one of them."""
        db = DrugDatabase(["Ibuprofen", "Paracetamol"])
        self.assertEqual(
            db.find_matches("IBUPROFEN 400 mg AND PARACETAMOL 325 mg TABLETS"),
            ["Ibuprofen", "Paracetamol"],
        )

    def test_names_come_back_in_printed_order(self):
        """Spoken order should track the strip, so the user can follow along."""
        db = DrugDatabase(["Ibuprofen", "Paracetamol"])
        self.assertEqual(
            db.find_matches("PARACETAMOL 325 mg AND IBUPROFEN 400 mg"),
            ["Paracetamol", "Ibuprofen"],
        )

    def test_nested_name_is_not_invented_as_a_second_drug(self):
        """Reporting every match would turn one Noradrenaline vial into two drugs, one
        of which is not in the user's hand -- worse than DEC-033's original bug."""
        db = DrugDatabase(["Adrenaline", "Noradrenaline"])
        self.assertEqual(db.find_matches("NORADRENALINE BITARTRATE INJECTION IP"),
                         ["Noradrenaline"])

    def test_both_reported_when_both_are_genuinely_printed(self):
        """Occurrence counting, not blanket suppression: 'adrenaline' appears twice, and
        only one of those is explained by 'noradrenaline'."""
        db = DrugDatabase(["Adrenaline", "Noradrenaline"])
        self.assertEqual(
            db.find_matches("ADRENALINE 1mg/ml AND NORADRENALINE 2mg/ml"),
            ["Adrenaline", "Noradrenaline"],
        )

    def test_nesting_holds_against_the_real_database(self):
        """The 14 nesting pairs in NLEM are the point; a synthetic two-name db could
        pass while the shipped list fails."""
        db = DrugDatabase.from_file()
        for text, expected in [
            ("INSULIN GLARGINE 100IU/ML", ["Insulin Glargine"]),
            ("HYDROXYCHLOROQUINE SULPHATE 200", ["Hydroxychloroquine"]),
            ("METHYLPREDNISOLONE TABLETS", ["Methylprednisolone"]),
        ]:
            with self.subTest(text=text):
                self.assertEqual(db.find_matches(text), expected)

    def test_find_match_still_answers_the_single_name_question(self):
        db = DrugDatabase(["Ibuprofen", "Paracetamol"])
        self.assertIn(db.find_match("IBUPROFEN 400 PARACETAMOL 325"),
                      ("Ibuprofen", "Paracetamol"))

    def test_no_matches_is_an_empty_list_not_none(self):
        self.assertEqual(DrugDatabase(["Paracetamol"]).find_matches("BATCH NO 4471"), [])

    def test_declines_on_text_with_no_drug_name(self):
        self.assertIsNone(self.db.find_match("BATCH NO 4471 MFD 09/2025 STORE BELOW 30C"))

    def test_no_name_normalizes_to_something_too_short_to_be_safe(self):
        # A 1-3 character key would match inside batch numbers and dosage text. NLEM's
        # shortest entries are 'Mesna' and '2-PAM'; anything shorter arriving in a future
        # regeneration is a false-positive generator, not a drug name.
        import re

        shortest = min(re.sub(r"[^a-z0-9]", "", n.lower()) for n in self.names)
        self.assertGreaterEqual(len(shortest), 4)


if __name__ == "__main__":
    unittest.main()
