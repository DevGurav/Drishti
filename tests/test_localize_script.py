"""Guards DEC-074: text already in the target script must not be translated.

Read mode OCRs a Marathi page and is asked for Marathi out, so its answer reaches
delivery already in Devanagari. IndicTrans2 is an English-to-Indic model; given that
input it rewrites the text into fluent, different Marathi and then loops. Measured
2026-08-22 on `newspaper-marathi.png`:

    OCR read : ...भिवंडी भकास... निधीचा ओघ नाही, ठाणे : अरुंद रस्ते...
    spoken   : ...विव्हंदी भकास... नीतीचा ओघ नाही, ठाणेः अरुंध रंसते...
               then: अधिक माहितीचे, अधिक माहितीचे, अधिक मा

`भिवंडी` is a city and `विव्हंदी` is not a word; `निधीचा` means "of funds" and `नीतीचा`
means "of policy". The OCR was correct and delivery destroyed it.
"""
import unittest

from app.languages import looks_devanagari, uses_devanagari
from app.speech import deliver, localize

MARATHI_PAGE = 'ठाणे : अरुंद रस्ते, महापालिकेची आर्थिक कोंडी'
ENGLISH_ANSWER = 'This is a five hundred rupee note.'


class SpyTranslator:
    def __init__(self): self.calls = []

    def translate(self, text, lang):
        self.calls.append((text, lang))
        return 'TRANSLATED'


class TestScriptDetection(unittest.TestCase):
    def test_devanagari_page_is_recognised(self):
        self.assertTrue(looks_devanagari(MARATHI_PAGE))

    def test_english_is_not(self):
        self.assertFalse(looks_devanagari(ENGLISH_ANSWER))

    def test_a_latin_byline_does_not_flip_a_devanagari_page(self):
        """Verbatim from newspaper-marathi.png's own OCR output. The email alone is 28
        Latin letters against 18 Devanagari, so a majority rule calls this English and
        translates it -- which is exactly the bug. English answers carry no Devanagari
        at all, so the bar does not need to be a majority."""
        self.assertTrue(looks_devanagari(
            'महेश गायकवाड mahesh gaikwad@timesofindia.com विकास निधीचा ओघ नाही'))

    def test_an_english_answer_with_no_devanagari_is_still_english(self):
        """The other side of the same threshold: nothing the app builds in English must
        ever skip translation."""
        for answer in (ENGLISH_ANSWER,
                       'This is Paracetamol. It is valid until April two thousand.',
                       "I can't see a note in this photo.",
                       'unanswerable'):
            self.assertFalse(looks_devanagari(answer), answer)

    def test_digits_and_punctuation_alone_are_not_devanagari(self):
        for text in ('', '   ', '2026', '--- 12.50 ---'):
            self.assertFalse(looks_devanagari(text), repr(text))

    def test_output_languages_written_in_devanagari(self):
        self.assertTrue(uses_devanagari('mr'))
        self.assertTrue(uses_devanagari('hi'))
        self.assertFalse(uses_devanagari('en'))


class TestLocalizeSkipsRedundantTranslation(unittest.TestCase):
    def test_marathi_in_marathi_out_is_left_alone(self):
        spy = SpyTranslator()
        self.assertEqual(localize(MARATHI_PAGE, 'mr', spy), MARATHI_PAGE)
        self.assertEqual(spy.calls, [], 'the translator must not be called at all')

    def test_hindi_page_likewise(self):
        spy = SpyTranslator()
        self.assertEqual(localize(MARATHI_PAGE, 'hi', spy), MARATHI_PAGE)
        self.assertEqual(spy.calls, [])

    def test_english_answers_are_still_translated(self):
        """The modes that build English answers must keep their translation step."""
        spy = SpyTranslator()
        self.assertEqual(localize(ENGLISH_ANSWER, 'mr', spy), 'TRANSLATED')
        self.assertEqual(len(spy.calls), 1)

    def test_english_output_is_untouched_by_the_script_rule(self):
        self.assertEqual(localize(MARATHI_PAGE, 'en', None), MARATHI_PAGE)

    def test_numbers_are_not_spelled_into_a_devanagari_page(self):
        """They would become English words with no translation step to render them, and
        every Latin letter is outside these voices' vocabulary -- losing whole words
        rather than single digits."""
        page = f'{MARATHI_PAGE} 2026'
        self.assertIn('2026', localize(page, 'mr', SpyTranslator()))
        self.assertNotIn('two thousand', localize(page, 'mr', SpyTranslator()))

    def test_read_mode_delivery_end_to_end_keeps_the_ocr_text(self):
        result = deliver(MARATHI_PAGE, lang='mr', translator=SpyTranslator())
        self.assertEqual(result.text_out, MARATHI_PAGE)
        self.assertEqual(result.text_en, MARATHI_PAGE)


if __name__ == '__main__':
    unittest.main()
