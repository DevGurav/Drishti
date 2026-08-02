import unittest
from pathlib import Path

from app.drug_db import DrugDatabase
from app.router import Engines, MissingEngineError, route


class FakeVLM:
    def answer(self, image_path: Path, question: str) -> str:
        return f"fake answer to: {question}"


class FakeOCR:
    def read(self, image_path: Path) -> str:
        return "PARACETAMOL EXP MAR2030"


class FakeClassifier:
    def classify(self, image_path: Path):
        return ("500", 0.97)


class TestRouter(unittest.TestCase):
    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            route("bogus", Path("x.jpg"), Engines())

    def test_missing_engine_raises(self):
        with self.assertRaises(MissingEngineError):
            route("scene", Path("x.jpg"), Engines())

    def test_scene_routes_to_vlm(self):
        result = route("scene", Path("x.jpg"), Engines(vlm=FakeVLM()))
        self.assertIn("fake answer", result)

    def test_currency_routes_to_classifier(self):
        result = route("currency", Path("x.jpg"), Engines(classifier=FakeClassifier()))
        self.assertIn("500", result)

    def test_medicine_routes_through_guardrail(self):
        engines = Engines(ocr=FakeOCR(), drug_db=DrugDatabase(["Paracetamol"]))
        result = route("medicine", Path("x.jpg"), engines)
        self.assertIn("Paracetamol", result)


if __name__ == "__main__":
    unittest.main()
