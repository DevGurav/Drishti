"""Tests for SmolVLM engine logic that does not require the model.

The abstention handling is the part worth pinning: on VizWiz-val 49% of questions are
unanswerable, and for a blind user a confident wrong answer is worse than "I can't tell".
"""
import unittest

from app.engines.smolvlm import (
    ABSTENTION_MESSAGE,
    ABSTENTION_SUFFIX,
    SCENE_PROMPT,
    SmolVLMEngine,
    humanize,
    is_abstention,
)


class TestAbstentionDetection(unittest.TestCase):
    def test_plain_token(self):
        self.assertTrue(is_abstention('unanswerable'))

    def test_tolerates_case_whitespace_and_trailing_punctuation(self):
        for raw in ('Unanswerable', '  UNANSWERABLE  ', 'unanswerable.', 'Unanswerable!'):
            self.assertTrue(is_abstention(raw), raw)

    def test_real_answers_are_not_abstentions(self):
        for raw in ('Paracetamol', '500', 'a blue cup', ''):
            self.assertFalse(is_abstention(raw), raw)

    def test_answer_merely_containing_the_word_is_not_an_abstention(self):
        """Guards against substring matching -- this is a real answer, not a refusal."""
        self.assertFalse(is_abstention('the question is unanswerable because it is dark'))

    def test_answer_prefix_is_stripped(self):
        """SmolVLM emits 'Answer: unanswerable' intermittently -- 4 of 500 in the
        notebook-02 run. Unhandled, the app reads that aloud instead of guiding a retake."""
        for raw in ('Answer: unanswerable', 'answer:unanswerable', 'Answer: Unanswerable.'):
            self.assertTrue(is_abstention(raw), raw)


class TestHumanize(unittest.TestCase):
    def test_abstention_becomes_actionable_guidance(self):
        spoken = humanize('unanswerable')
        self.assertEqual(spoken, ABSTENTION_MESSAGE)
        self.assertNotIn('unanswerable', spoken.lower())

    def test_real_answers_pass_through_unchanged(self):
        self.assertEqual(humanize('Paracetamol'), 'Paracetamol')

    def test_guidance_tells_the_user_what_to_do(self):
        """A blind user cannot see why the photo failed, so the message must suggest a fix."""
        self.assertTrue(any(w in ABSTENTION_MESSAGE.lower() for w in ('light', 'framing')))


class TestPromptSuffix(unittest.TestCase):
    """Pins the 'stakes' prompt that won the notebook-02 sweep (0.308 -> 0.533 overall).
    These assert the properties that made it win, so an edit-by-intuition trips a test."""

    def test_suffix_requests_terse_answers(self):
        """VizWiz scores by exact match, so verbose answers score ~0 even when correct."""
        self.assertIn('one to three words', ABSTENTION_SUFFIX)

    def test_suffix_names_the_exact_abstention_token(self):
        self.assertIn('unanswerable', ABSTENTION_SUFFIX)

    def test_suffix_states_the_stakes(self):
        """Naming that the user cannot verify the answer is what beat the four other
        variants -- listing criteria and demanding caution both scored lower."""
        lowered = ABSTENTION_SUFFIX.lower()
        self.assertIn('blind', lowered)
        self.assertIn('cannot check', lowered)


class TestScenePrompt(unittest.TestCase):
    """Scene description and abstention-aware VQA want opposite things (DEC-031)."""

    def test_scene_prompt_asks_for_sentences(self):
        self.assertIn('sentences', SCENE_PROMPT.lower())

    def test_scene_prompt_does_not_contain_the_abstention_suffix(self):
        """The suffix caps answers at three words. Concatenating the two produces a
        prompt that contradicts itself, which is what returned 'Paracip-500' for a
        whole-scene description on the first real run."""
        self.assertNotIn(ABSTENTION_SUFFIX.strip(), SCENE_PROMPT)
        self.assertNotIn('one to three words', SCENE_PROMPT.lower())

    def test_engine_exposes_both_verbs(self):
        """Constructing the engine loads no weights, so this is free to assert."""
        engine = SmolVLMEngine()
        self.assertTrue(callable(engine.answer))
        self.assertTrue(callable(engine.describe))


if __name__ == '__main__':
    unittest.main()
