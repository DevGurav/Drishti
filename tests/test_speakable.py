"""Guards DEC-072: a spoken answer must contain no digit.

The Marathi and Hindi MMS voices have no '3', '5' or '8' in their character vocabulary
and drop what they cannot encode without raising, so "500" was spoken as "00" and an
expiry of "APR.28" as "2". These tests need no model: the invariant is enforced on the
English text, before translation, where a digit is still a digit.
"""
import unittest
from pathlib import Path

from app.drug_db import DrugDatabase
from app.engines.mms_tts import dropped_characters
from app.modes.currency import run as currency_run
from app.modes.medicine import run as medicine_run
from app.speech import localize
from app.speakable import (
    expiry_words,
    has_digits,
    money_words,
    number_words,
    spell_numbers_in_text,
)

CIRCULATING = ['10', '20', '50', '100', '200', '500']


class FakeOCR:
    def __init__(self, text): self._text = text
    def read(self, image_path: Path) -> str: return self._text


class FakeClassifier:
    def __init__(self, label, confidence=0.99):
        self.label, self.confidence = label, confidence

    def classify(self, image_path: Path):
        return self.label, self.confidence


class TestNumberWords(unittest.TestCase):
    def test_the_denominations_that_were_being_mangled(self):
        self.assertEqual(number_words(50), 'fifty')
        self.assertEqual(number_words(500), 'five hundred')

    def test_every_circulating_denomination(self):
        self.assertEqual(
            [number_words(int(d)) for d in CIRCULATING],
            ['ten', 'twenty', 'fifty', 'one hundred', 'two hundred', 'five hundred'],
        )

    def test_teens_and_compound_tens(self):
        self.assertEqual(number_words(0), 'zero')
        self.assertEqual(number_words(13), 'thirteen')
        self.assertEqual(number_words(45), 'forty five')

    def test_years(self):
        self.assertEqual(number_words(2028), 'two thousand twenty eight')
        self.assertEqual(number_words(2000), 'two thousand')

    def test_refuses_what_it_cannot_name(self):
        """Above a lakh the Indian names diverge; guessing would be worse than raising."""
        with self.assertRaises(ValueError):
            number_words(1_000_000)
        with self.assertRaises(ValueError):
            number_words(-1)


class TestMoneyWords(unittest.TestCase):
    def test_rupees_and_paise(self):
        self.assertEqual(money_words('10.30'), 'ten rupees and thirty paise')

    def test_whole_rupees(self):
        self.assertEqual(money_words('120'), 'one hundred twenty rupees')

    def test_zero_paise_is_not_spoken(self):
        self.assertEqual(money_words('45.00'), 'forty five rupees')

    def test_thousands_separator(self):
        self.assertEqual(money_words('1,050'), 'one thousand fifty rupees')

    def test_single_decimal_digit_means_tens_of_paise(self):
        """'10.5' on a strip is fifty paise, not five."""
        self.assertEqual(money_words('10.5'), 'ten rupees and fifty paise')

    def test_unreadable_amount_returns_none_rather_than_digits(self):
        """Callers omit the price instead. A mangled price is worse than no price."""
        for junk in ('', 'abc', '.', '12.ab'):
            self.assertIsNone(money_words(junk), junk)


class TestExpiryWords(unittest.TestCase):
    def test_the_fixture_date(self):
        self.assertEqual(expiry_words('APR.28'), 'April two thousand twenty eight')

    def test_four_digit_year_and_numeric_format(self):
        self.assertEqual(expiry_words('OCT.2026'), 'October two thousand twenty six')
        self.assertEqual(expiry_words('03/2027'), 'March two thousand twenty seven')

    def test_unparseable_returns_none(self):
        """Medicine mode then keeps saying 'I could not read a clear expiry date'."""
        self.assertIsNone(expiry_words('garbage'))

    def test_no_day_is_invented(self):
        """Strips print month and year only; parse_expiry_date's last-day-of-month is an
        internal comparison device, not something to read out."""
        self.assertNotIn('thirty', expiry_words('APR.28'))


class TestNoDigitReachesTheVoice(unittest.TestCase):
    """The invariant. If any of these fail, a user hears a different number than the
    one printed -- which is how DEC-072 stayed hidden for two weeks."""

    def test_every_denomination_is_spoken_without_digits(self):
        for label in CIRCULATING:
            with self.subTest(note=label):
                answer = currency_run(Path('n.jpg'), FakeClassifier(label))
                self.assertFalse(has_digits(answer), answer)

    def test_the_denomination_is_still_actually_named(self):
        """A digit-free answer that dropped the amount would pass the test above."""
        answer = currency_run(Path('n.jpg'), FakeClassifier('500'))
        self.assertIn('five hundred', answer)

    def test_currency_refusals_carry_no_digits(self):
        self.assertFalse(has_digits(currency_run(Path('n.jpg'),
                                                 FakeClassifier('background'))))
        self.assertFalse(has_digits(currency_run(Path('n.jpg'),
                                                 FakeClassifier('500', 0.5))))

    def test_medicine_answer_carries_no_digits(self):
        db = DrugDatabase(['Paracetamol'])
        result = medicine_run(Path('s.jpg'),
                              FakeOCR('PARACETAMOL 500MG EXP.APR.28 MRP Rs.10.30'), db)
        self.assertTrue(result.ok)
        self.assertFalse(has_digits(result.message_en), result.message_en)
        self.assertIn('April two thousand twenty eight', result.message_en)
        self.assertIn('ten rupees and thirty paise', result.message_en)

    def test_expired_warning_survives_an_unspellable_date(self):
        """Losing 'expired' because a month would not render is the one failure this
        mode cannot have, so the warning must not depend on the spelling."""
        db = DrugDatabase(['Paracetamol'])
        result = medicine_run(Path('s.jpg'),
                              FakeOCR('PARACETAMOL EXP: JAN2020'), db)
        self.assertIn('expired', result.message_en.lower())
        self.assertFalse(has_digits(result.message_en), result.message_en)


class TestSpellNumbersInText(unittest.TestCase):
    """For read/scene/ask, which relay text rather than build it. Every voice drops
    digits it lacks -- English has no 7, 8 or 9, so this is not a Devanagari-only fix."""

    def test_year_and_price(self):
        self.assertEqual(
            spell_numbers_in_text('EXP 2028, MRP 87.90'),
            'EXP two thousand twenty eight, MRP eighty seven point nine zero')

    def test_the_english_cases_that_vanished(self):
        self.assertEqual(spell_numbers_in_text('789 rupees'),
                         'seven hundred eighty nine rupees')
        self.assertEqual(spell_numbers_in_text('chapter 7'), 'chapter seven')

    def test_fraction_is_read_digit_by_digit(self):
        """'point ninety' would be a different quantity from 'point nine zero'."""
        self.assertIn('point nine zero', spell_numbers_in_text('87.90'))
        self.assertIn('point zero five', spell_numbers_in_text('1.05'))

    def test_long_runs_are_read_out_as_digits(self):
        """A ten-digit run is a phone number, not a quantity."""
        self.assertEqual(spell_numbers_in_text('9876543210'),
                         'nine eight seven six five four three two one zero')

    def test_ordinals(self):
        self.assertEqual(spell_numbers_in_text('3rd floor'), 'third floor')
        self.assertEqual(spell_numbers_in_text('21st'), 'twenty first')
        self.assertEqual(spell_numbers_in_text('12th'), 'twelfth')
        self.assertEqual(spell_numbers_in_text('40th'), 'fortieth')

    def test_text_without_digits_is_untouched(self):
        marathi = 'ठाणे : अरुंद रस्ते'
        self.assertEqual(spell_numbers_in_text(marathi), marathi)

    def test_nothing_survives_that_a_voice_would_drop(self):
        page = 'Published 2026. Call 022 12345678. Page 7 of 89. Rs 1,250.75'
        self.assertFalse(has_digits(spell_numbers_in_text(page)),
                         spell_numbers_in_text(page))


class TestLocalizeSpellsNumbers(unittest.TestCase):
    """The wiring: read/scene/ask get this for free because it lives in delivery."""

    def test_english_path_is_covered_too(self):
        """No translator involved, and English still cannot say 7, 8 or 9."""
        self.assertEqual(localize('chapter 7', 'en', None), 'chapter seven')

    def test_runs_before_translation_not_after(self):
        """IndicTrans2 passes digits through unchanged, so spelling afterwards would be
        too late -- the translator must receive words."""
        seen = []

        class SpyTranslator:
            def translate(self, text, lang):
                seen.append(text)
                return 'translated'

        localize('EXP 2028', 'mr', SpyTranslator())
        self.assertEqual(seen, ['EXP two thousand twenty eight'])


class CharVocabTokenizer:
    """Mimics a VITS tokenizer: filters to a character vocabulary, raises nothing."""

    def __init__(self, vocab): self.vocab = set(vocab)

    def __call__(self, text):
        kept = [c for c in text if c in self.vocab]
        return type('Enc', (), {'input_ids': kept})()

    def decode(self, ids): return ''.join(ids)


class TestDroppedCharacters(unittest.TestCase):
    """The detector that would have caught this on day one."""

    def test_reports_the_digits_the_marathi_voice_lacks(self):
        tok = CharVocabTokenizer('0124679 रुपयांचीनोटआहे')
        self.assertEqual(dropped_characters('ही 500 रुपयांची नोट आहे', tok), ['5'])

    def test_silent_when_everything_is_speakable(self):
        tok = CharVocabTokenizer('abc ')
        self.assertEqual(dropped_characters('a b c', tok), [])

    def test_whitespace_is_not_reported(self):
        tok = CharVocabTokenizer('ab')
        self.assertEqual(dropped_characters('a\tb', tok), [])

    def test_punctuation_is_not_reported(self):
        """Every voice drops the final full stop. Warning on it would make the detector
        fire on all output, which is how a warning stops being read."""
        tok = CharVocabTokenizer('abc ')
        self.assertEqual(dropped_characters('a, b. c!', tok), [])

    def test_devanagari_vowel_marks_are_reported(self):
        """पॅरासिटामॉल -> परासिटामल is a real mispronunciation of a drug name."""
        tok = CharVocabTokenizer('परासिटामल')
        self.assertEqual(dropped_characters('पॅरासिटामॉल', tok), ['ॅ', 'ॉ'])


if __name__ == '__main__':
    unittest.main()
