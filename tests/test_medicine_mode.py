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


if __name__ == "__main__":
    unittest.main()
