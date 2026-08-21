"""Tests for Money mode and the currency classifier's non-model logic.

Deliberately avoids torch and a checkpoint: what is worth pinning here is the label
handling and the refusal behaviour, which is where a wrong answer costs a user money.
"""
import unittest
from pathlib import Path

from app.engines.currency_cnn import (
    CheckpointMissingError,
    CurrencyClassifier,
    denomination,
)
from app.modes.currency import BACKGROUND_LABEL, CONFIDENCE_THRESHOLD
from app.modes.currency import run as run_currency


class FakeClassifier:
    def __init__(self, label, confidence):
        self._result = (label, confidence)

    def classify(self, image_path):
        return self._result


class TestDenomination(unittest.TestCase):
    def test_plain_digits(self):
        self.assertEqual(denomination('500'), '500')

    def test_common_folder_naming_variants(self):
        for raw in ('Rs500', '500_note', 'rs_500', '500 rupees'):
            self.assertEqual(denomination(raw), '500', raw)

    def test_non_numeric_label_passes_through(self):
        """Better to speak an odd label than to silently return an empty string."""
        self.assertEqual(denomination('unknown'), 'unknown')


class TestMoneyMode(unittest.TestCase):
    def test_confident_prediction_is_reported(self):
        """Spelled out, not '500' -- the Marathi voice has no '5' and spoke it as
        '00' (DEC-072). tests/test_speakable.py holds the full invariant."""
        out = run_currency(Path('n.jpg'), FakeClassifier('500', 0.99))
        self.assertIn('five hundred', out)

    def test_low_confidence_refuses_rather_than_guessing(self):
        """A wrong denomination costs the user money; a refusal costs a retaken photo."""
        out = run_currency(Path('n.jpg'), FakeClassifier('500', 0.42))
        self.assertNotIn('five hundred', out)
        self.assertIn('not confident', out.lower())

    def test_refusal_tells_the_user_what_to_do(self):
        out = run_currency(Path('n.jpg'), FakeClassifier('100', 0.10))
        self.assertTrue(any(w in out.lower() for w in ('clearer', 'light')))

    def test_threshold_boundary_is_inclusive(self):
        out = run_currency(Path('n.jpg'), FakeClassifier('200', CONFIDENCE_THRESHOLD))
        self.assertIn('two hundred', out)

    def test_just_below_threshold_refuses(self):
        out = run_currency(Path('n.jpg'), FakeClassifier('200', CONFIDENCE_THRESHOLD - 0.01))
        self.assertNotIn('two hundred', out)

    def test_threshold_is_high_enough_to_be_meaningful(self):
        """Guards against someone lowering the bar to make the demo look good."""
        self.assertGreaterEqual(CONFIDENCE_THRESHOLD, 0.80)


class TestNoNoteInFrame(unittest.TestCase):
    """The training set has a `background` class of photos with no note in them, so the
    model can answer 'nothing here' instead of being forced to name a denomination."""

    def test_background_never_becomes_a_denomination(self):
        out = run_currency(Path('n.jpg'), FakeClassifier(BACKGROUND_LABEL, 0.97))
        self.assertNotIn('rupee note', out)
        self.assertIn("can't see a note", out.lower())

    def test_background_wins_even_at_high_confidence(self):
        """Confidence is about *which* class, not whether there is a note. A confident
        background prediction is the model working, not failing."""
        for confidence in (0.99, CONFIDENCE_THRESHOLD, 0.50):
            with self.subTest(confidence=confidence):
                out = run_currency(Path('n.jpg'), FakeClassifier(BACKGROUND_LABEL, confidence))
                self.assertIn("can't see a note", out.lower())

    def test_background_label_casing_from_the_checkpoint_is_tolerated(self):
        """ImageFolder takes class names from directories, and DEC-023 says the checkpoint
        is authoritative -- so casing depends on how the folder was created."""
        for raw in ('background', 'Background', 'BACKGROUND', ' Background '):
            with self.subTest(raw=raw):
                out = run_currency(Path('n.jpg'), FakeClassifier(raw, 0.95))
                self.assertIn("can't see a note", out.lower())

    def test_advice_differs_from_the_low_confidence_advice(self):
        """Framing and lighting are different problems; identical wording would send the
        user to fix the thing that was not wrong."""
        no_note = run_currency(Path('n.jpg'), FakeClassifier(BACKGROUND_LABEL, 0.95))
        unsure = run_currency(Path('n.jpg'), FakeClassifier('500', 0.10))
        self.assertNotEqual(no_note, unsure)
        self.assertIn('frame', no_note.lower())


class TestMissingCheckpoint(unittest.TestCase):
    def test_error_names_the_notebook_that_produces_the_model(self):
        clf = CurrencyClassifier(checkpoint=Path('does/not/exist.pt'))
        with self.assertRaises(CheckpointMissingError) as ctx:
            clf.classify(Path('n.jpg'))
        self.assertIn('03_currency_classifier', str(ctx.exception))

    def test_error_is_raised_lazily_not_at_construction(self):
        """Constructing engines must stay cheap — the CLI builds all of them up front."""
        CurrencyClassifier(checkpoint=Path('does/not/exist.pt'))


if __name__ == '__main__':
    unittest.main()
