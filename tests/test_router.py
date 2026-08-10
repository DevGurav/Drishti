import unittest
from pathlib import Path

from app.drug_db import DrugDatabase
from app.router import Engines, MissingEngineError, route


class FakeVLM:
    """Records which verb was called — scene and ask must not share one (DEC-031)."""

    def __init__(self):
        self.calls: list[str] = []

    def answer(self, image_path: Path, question: str) -> str:
        self.calls.append("answer")
        return f"fake answer to: {question}"

    def describe(self, image_path: Path) -> str:
        self.calls.append("describe")
        return "a strip of tablets on a wooden table"


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
        self.assertIn("wooden table", result)

    def test_scene_describes_rather_than_answers(self):
        """Scene must not go through answer(): that path appends the abstention suffix,
        which demands one to three words and made the first real run reply
        'Paracip-500' to a request for a description. See DEC-031."""
        vlm = FakeVLM()
        route("scene", Path("x.jpg"), Engines(vlm=vlm))
        self.assertEqual(vlm.calls, ["describe"])

    def test_ask_still_answers(self):
        """Ask keeps the suffix -- terse, abstention-aware VQA is the measured behaviour."""
        vlm = FakeVLM()
        route("ask", Path("x.jpg"), Engines(vlm=vlm), question="what colour is it?")
        self.assertEqual(vlm.calls, ["answer"])

    def test_currency_routes_to_classifier(self):
        result = route("currency", Path("x.jpg"), Engines(classifier=FakeClassifier()))
        self.assertIn("500", result)

    def test_medicine_routes_through_guardrail(self):
        engines = Engines(ocr=FakeOCR(), drug_db=DrugDatabase(["Paracetamol"]))
        result = route("medicine", Path("x.jpg"), engines)
        self.assertIn("Paracetamol", result)


if __name__ == "__main__":
    unittest.main()
