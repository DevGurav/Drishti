import unittest
from pathlib import Path

from app.drug_db import DrugDatabase
from app.modes.medicine import run


class FakeOCR:
    def __init__(self, text: str):
        self._text = text

    def read(self, image_path: Path) -> str:
        return self._text


class TestMedicineModeGuardrail(unittest.TestCase):
    def setUp(self):
        self.db = DrugDatabase(["Paracetamol", "Azithromycin"])

    def test_declines_when_no_drug_name_matches(self):
        ocr = FakeOCR("some blurry unreadable text EXP MAR2027")
        result = run(Path("strip.jpg"), ocr, self.db)
        self.assertFalse(result.ok)
        self.assertIsNone(result.drug_name)

    def test_reports_expired_medicine(self):
        ocr = FakeOCR("PARACETAMOL 500MG EXP: JAN2020 MRP: Rs.20")
        result = run(Path("strip.jpg"), ocr, self.db)
        self.assertTrue(result.ok)
        self.assertEqual(result.drug_name, "Paracetamol")
        self.assertTrue(result.expired)
        self.assertIn("expired", result.message_en.lower())

    def test_reports_valid_medicine_with_unreadable_expiry(self):
        ocr = FakeOCR("AZITHROMYCIN 250MG")
        result = run(Path("strip.jpg"), ocr, self.db)
        self.assertTrue(result.ok)
        self.assertEqual(result.drug_name, "Azithromycin")
        self.assertIsNone(result.expired)
        self.assertIn("could not read", result.message_en.lower())


class TestCombinationStrips(unittest.TestCase):
    """A combination tablet is one medicine with several ingredients, and the user must
    hear all of them -- being told 'Paracetamol' while holding
    IBUPROFEN+PARACETAMOL hides an ingredient they may be avoiding."""

    def setUp(self):
        self.db = DrugDatabase(["Ibuprofen", "Paracetamol", "Caffeine"])

    def test_every_ingredient_is_spoken(self):
        result = run(Path("strip.jpg"),
                     FakeOCR("IBUPROFEN 400 PARACETAMOL 325 EXP: MAR2030"), self.db)
        self.assertEqual(result.drug_names, ["Ibuprofen", "Paracetamol"])
        for name in ("Ibuprofen", "Paracetamol"):
            self.assertIn(name, result.message_en)

    def test_phrased_as_one_medicine_not_several(self):
        """'This is Ibuprofen. This is Paracetamol.' would suggest two tablets."""
        result = run(Path("strip.jpg"),
                     FakeOCR("IBUPROFEN 400 PARACETAMOL 325"), self.db)
        self.assertIn("combination", result.message_en.lower())
        self.assertEqual(result.message_en.lower().count("this is"), 1)

    def test_three_ingredients_read_naturally(self):
        result = run(Path("strip.jpg"),
                     FakeOCR("PARACETAMOL 325 CAFFEINE 30 IBUPROFEN 400"), self.db)
        self.assertEqual(len(result.drug_names), 3)
        self.assertIn("Paracetamol, Caffeine and Ibuprofen", result.message_en)

    def test_single_ingredient_phrasing_is_unchanged(self):
        """The common case must not start announcing a 'combination' of one."""
        result = run(Path("strip.jpg"), FakeOCR("PARACETAMOL 500MG"), self.db)
        self.assertIn("This is Paracetamol.", result.message_en)
        self.assertNotIn("combination", result.message_en.lower())

    def test_drug_name_still_works_for_older_callers(self):
        """notebook 04 and the checkpoint JSON read `drug_name`."""
        result = run(Path("strip.jpg"),
                     FakeOCR("IBUPROFEN 400 PARACETAMOL 325"), self.db)
        self.assertEqual(result.drug_name, "Ibuprofen")

    def test_declining_leaves_no_names(self):
        result = run(Path("strip.jpg"), FakeOCR("BATCH 4471 STORE BELOW 30C"), self.db)
        self.assertFalse(result.ok)
        self.assertEqual(result.drug_names, [])
        self.assertIsNone(result.drug_name)


if __name__ == "__main__":
    unittest.main()
