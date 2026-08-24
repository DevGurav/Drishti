"""Guards the number verifier: a translated amount must still be the amount that went in.

`DEC-072` spelled numbers into English words before translation so the digit-less
Devanagari voices could say them, on the reasoning that IndicTrans2 renders number words
faithfully. Measured over 16 real MRP values on 2026-08-24 it does not: 7 of 16 Marathi
and 5 of 16 Hindi translations either re-emitted digits or stated a *different amount* --
"eighty four rupees" came back as `चोवीस रुपये`, twenty-four.

The translations below are the measured outputs of that run, not invented strings, so
these tests fail if the check stops catching a corruption that really happened. They need
no model: the verifier is pure text.
"""
import unittest

from app.devanagari_numbers import CARDINALS, parse_numbers, states_all
from app.speakable import parse_english_numbers, spell_numbers_in_text

# (english source, what IndicTrans2 actually returned, lang) -- measured 2026-08-24.
FAITHFUL = [
    ('MRP is ten rupees and thirty paise.',
     'एम. आर. पी. दहा रुपये आणि तीस पैसे आहे.', 'mr'),
    ('This is a five hundred rupee note.', 'ही पाचशे रुपयांची नोट आहे.', 'mr'),
    ('This is a twenty rupee note.', 'ही वीस रुपयांची नोट आहे.', 'mr'),
    ('This is a fifty rupee note.', 'ही पन्नास रुपयांची नोट आहे.', 'mr'),
    ('This is a one hundred rupee note.', 'ही शंभर रुपयांची नोट आहे.', 'mr'),
    ('It is valid until April two thousand twenty eight.',
     'तो दोन हजार अठ्ठावीस एप्रिलपर्यंत वैध आहे.', 'mr'),
    ('MRP is two hundred fifty rupees and sixty paise.',
     'एम. आर. पी. दोनशे पन्नास रुपये आणि साठ पैसे आहे.', 'mr'),
    ('This is a five hundred rupee note.', 'यह पाँच सौ रुपये का नोट है।', 'hi'),
    ('It is valid until April two thousand twenty eight.',
     'यह दो हजार अट्ठाईस अप्रैल तक वैध है।', 'hi'),
    ('MRP is sixty six rupees and sixty six paise.',
     'एम. आर. पी. छियासठ रुपये और छियासठ पैसे है।', 'hi'),
]

CORRUPTED = [
    ('MRP is eighty four rupees and twenty one paise.',
     'एम. आर. पी. चोवीस रुपये आणि एकवीस पैसे आहे.', 'mr', 'Rs 84 spoken as 24'),
    ('MRP is seventy eight rupees and ninety paise.',
     'एम. आर. पी. अठ्ठावीस रुपये आणि नव्वद पैसे आहे.', 'mr', 'Rs 78 spoken as 28'),
    ('MRP is three hundred fifty three rupees and thirty nine paise.',
     'एम. आर. पी. तीनशे तेचाळीस रुपये आणि एकोणतीस पैसे आहे.', 'mr', '353.39 -> 343.29'),
    ('MRP is sixty six rupees and sixty six paise.',
     'एम. आर. पी. साठ रुपये आणि साठ पैसे आहे.', 'mr', '66.66 -> 60.60'),
    ('MRP is ninety nine rupees and ninety nine paise.',
     'एम. आर. पी. उनानबे रुपये और उनानबे पैसे है।', 'hi', '99.99 -> 89.89'),
    ('MRP is three hundred fifty three rupees and thirty nine paise.',
     'एम. आर. पी. तीन सौ तैंतीस रुपये और उनतीस पैसे है।', 'hi', '353.39 -> 333.29'),
    ('MRP is seventy eight rupees and ninety paise.',
     'एम. आर. पी. अड़तालीस रुपये और नब्बे पैसे है।', 'hi', 'Rs 78 spoken as 48'),
    ('MRP is one hundred ninety nine rupees.',
     'एम. आर. पी. एक सौ उनानबे रुपये है।', 'hi', '199 -> 189'),
]


class TestParseEnglishNumbers(unittest.TestCase):
    """The inverse of `number_words`. Without it there is nothing to compare against:
    by the time speech.localize sees a medicine answer the digits are already words."""

    def test_compounds(self):
        cases = {
            'MRP is eighty four rupees and twenty one paise.': [84, 21],
            'It is valid until April two thousand twenty eight.': [2028],
            'This is a five hundred rupee note.': [500],
            'MRP is three hundred fifty three rupees and thirty nine paise.': [353, 39],
            'MRP is one hundred twenty rupees.': [120],
            'This is Paracetamol.': [],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_english_numbers(text), expected)

    def test_adjacent_numbers_do_not_merge(self):
        # "one one" is two values; "twenty one" is one. A compound continues only while
        # each part is smaller than the last.
        self.assertEqual(parse_english_numbers('one one'), [1, 1])
        self.assertEqual(parse_english_numbers('twenty one'), [21])

    def test_a_fraction_is_read_digit_by_digit(self):
        # `spell_numbers_in_text('87.90')` is "eighty seven point nine zero", because
        # "point ninety" would be a different quantity. Accumulating those the way a
        # compound accumulates would give 96, and the sentence would then be dropped for
        # failing to match itself.
        self.assertEqual(
            parse_english_numbers(spell_numbers_in_text('87.90')), [87, 9, 0])
        self.assertEqual(
            parse_english_numbers(spell_numbers_in_text('1.05')), [1, 0, 5])

    def test_hundred_joined_by_and(self):
        self.assertEqual(parse_english_numbers('one hundred and twenty'), [120])


class TestParseDevanagariNumbers(unittest.TestCase):
    def test_marathi_compounds(self):
        self.assertEqual(parse_numbers('ही पाचशे रुपयांची नोट आहे.', 'mr'), [500])
        self.assertEqual(parse_numbers('दोन हजार अठ्ठावीस एप्रिल', 'mr'), [2028])
        self.assertEqual(parse_numbers('तीनशे पन्नास', 'mr'), [350])

    def test_an_unlisted_spelling_costs_a_rejection_not_a_wrong_value(self):
        # The translator wrote 43 as `तेचाळीस`; this lexicon carries `त्रेचाळीस`. The tail
        # is therefore unrecognised, and `तीनशे तेचाळीस` reads as 300 rather than 343 --
        # so a caller asking whether 353 was stated gets "no" either way. This is the
        # design working: a gap in the table costs a silence, never a false amount.
        # Adding every dialect spelling would make the parser more accurate and the
        # guarantee no stronger, while every added entry is one more thing to get wrong.
        self.assertEqual(parse_numbers('तीनशे तेचाळीस', 'mr'), [300])
        self.assertFalse(states_all([353, 39], 'तीनशे तेचाळीस रुपये आणि एकोणतीस पैसे', 'mr'))

    def test_hindi_compounds(self):
        self.assertEqual(parse_numbers('यह पाँच सौ रुपये का नोट है।', 'hi'), [500])
        self.assertEqual(parse_numbers('दो हजार अट्ठाईस अप्रैल', 'hi'), [2028])
        self.assertEqual(parse_numbers('तीन सौ तैंतीस', 'hi'), [333])

    def test_unknown_words_separate_rather_than_corrupt(self):
        # The safe direction: a word this table does not carry ends the current number
        # instead of being absorbed into it.
        self.assertEqual(parse_numbers('दहा कशाचेतरी तीस', 'mr'), [10, 30])

    def test_devanagari_digits_are_read_as_numbers(self):
        self.assertEqual(parse_numbers('५०० रुपये', 'mr'), [500])

    def test_lexicons_are_injective(self):
        # Two words mapping to one value is fine (dialect spellings); one word mapping to
        # two values is not expressible, but a value appearing under a wrong word would
        # let a corruption through. This asserts every value 0-99 is covered exactly.
        for lang, table in CARDINALS.items():
            with self.subTest(lang=lang):
                self.assertEqual(sorted(set(table.values())), list(range(100)))


class TestStatesAll(unittest.TestCase):
    def test_accepts_every_faithful_translation(self):
        for src, out, lang in FAITHFUL:
            with self.subTest(src=src, lang=lang):
                self.assertTrue(
                    states_all(parse_english_numbers(src), out, lang),
                    f'rejected a correct {lang} translation: {out}')

    def test_rejects_every_measured_corruption(self):
        for src, out, lang, why in CORRUPTED:
            with self.subTest(why=why, lang=lang):
                self.assertFalse(
                    states_all(parse_english_numbers(src), out, lang),
                    f'accepted a corruption ({why}): {out}')

    def test_no_numbers_expected_always_passes(self):
        # A sentence with nothing to lose must not be dropped.
        self.assertTrue(states_all([], 'हे पॅरासिटामॉल आहे.', 'mr'))

    def test_order_is_not_required(self):
        # Devanagari puts the year before the month; English does not. Requiring position
        # would fail correct translations.
        self.assertTrue(states_all([2028], 'दोन हजार अठ्ठावीस एप्रिलपर्यंत', 'mr'))

    def test_partial_match_is_a_failure(self):
        # 84 lost, 21 survived. Half a price is not a price.
        self.assertFalse(states_all([84, 21], 'चोवीस रुपये आणि एकवीस पैसे', 'mr'))


if __name__ == '__main__':
    unittest.main()
