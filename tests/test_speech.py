import unittest
from pathlib import Path

from app.engines.indictrans import needs_translation
from app.engines.mms_tts import split_for_tts
from app.speech import deliver, localize


class FakeTranslator:
    def __init__(self):
        self.calls = []

    def translate(self, text, target_lang):
        self.calls.append((text, target_lang))
        return f'<{target_lang}>{text}'


class FakeTTS:
    def __init__(self):
        self.calls = []

    def speak(self, text, lang):
        self.calls.append((text, lang))
        return Path(f'{lang}.wav')


class TestNeedsTranslation(unittest.TestCase):
    def test_english_skips_the_model(self):
        """Loading IndicTrans2 costs ~800MB; English output must not pay for it."""
        self.assertFalse(needs_translation('en'))

    def test_indic_languages_need_it(self):
        self.assertTrue(needs_translation('mr'))
        self.assertTrue(needs_translation('hi'))


class TestLocalize(unittest.TestCase):
    def test_english_passes_through_untouched(self):
        t = FakeTranslator()
        self.assertEqual(localize('This is Paracetamol.', 'en', t), 'This is Paracetamol.')
        self.assertEqual(t.calls, [])

    def test_marathi_is_translated(self):
        t = FakeTranslator()
        self.assertEqual(localize('Hello', 'mr', t), '<mr>Hello')

    def test_missing_translator_degrades_to_english(self):
        """A missing engine should not crash the whole answer path."""
        self.assertEqual(localize('Hello', 'mr', None), 'Hello')

    def test_empty_text_is_not_sent_to_the_model(self):
        t = FakeTranslator()
        self.assertEqual(localize('   ', 'mr', t), '   ')
        self.assertEqual(t.calls, [])

    def test_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            localize('Hello', 'devanagari', FakeTranslator())


class TestDeliver(unittest.TestCase):
    def test_no_audio_unless_requested(self):
        tts = FakeTTS()
        r = deliver('Hello', lang='en', tts=tts, speak=False)
        self.assertIsNone(r.audio_path)
        self.assertEqual(tts.calls, [])

    def test_speaks_the_localized_text_not_the_english(self):
        t, tts = FakeTranslator(), FakeTTS()
        r = deliver('Hello', lang='mr', translator=t, tts=tts, speak=True)
        self.assertEqual(r.text_out, '<mr>Hello')
        self.assertEqual(tts.calls, [('<mr>Hello', 'mr')])
        self.assertEqual(r.audio_path, Path('mr.wav'))

    def test_keeps_english_alongside_translation(self):
        r = deliver('Hello', lang='mr', translator=FakeTranslator())
        self.assertEqual(r.text_en, 'Hello')
        self.assertEqual(r.text_out, '<mr>Hello')

    def test_blank_answer_is_not_synthesized(self):
        tts = FakeTTS()
        r = deliver('', lang='en', tts=tts, speak=True)
        self.assertIsNone(r.audio_path)
        self.assertEqual(tts.calls, [])


class TestSplitForTTS(unittest.TestCase):
    def test_short_text_is_one_chunk(self):
        self.assertEqual(split_for_tts('This is Paracetamol.'), ['This is Paracetamol.'])

    def test_empty_text_yields_nothing(self):
        self.assertEqual(split_for_tts(''), [])
        self.assertEqual(split_for_tts('   '), [])

    def test_long_text_splits_under_the_limit(self):
        text = ' '.join(f'Sentence number {i} here.' for i in range(60))
        chunks = split_for_tts(text, max_chars=200)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(c), 200)

    def test_no_content_is_dropped_when_splitting(self):
        text = 'First one. Second one. Third one.'
        joined = ' '.join(split_for_tts(text, max_chars=20))
        for word in ('First', 'Second', 'Third'):
            self.assertIn(word, joined)


if __name__ == '__main__':
    unittest.main()
