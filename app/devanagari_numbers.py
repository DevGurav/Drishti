"""Read Marathi and Hindi number words back to values, so a translated number can be checked.

`DEC-072` spells numbers into English words before translation, because the Devanagari
voices have no digits in vocabulary and IndicTrans2 renders number *words* as Devanagari
number words. That is true most of the time. Measured over 16 real MRP values on
2026-08-24 it is false often enough to matter:

    "eighty four rupees and twenty one paise"   ->  चोवीस रुपये आणि एकवीस पैसे   (24.21)
    "seventy eight rupees and ninety paise"     ->  अठ्ठावीस रुपये आणि नव्वद पैसे  (28.90)
    "three hundred fifty three rupees ..."      ->  तीनशे तेचाळीस रुपये ...        (343.__)
    "ninety nine rupees and ninety nine paise"  ->  उनानबे रुपये और उनानबे पैसे    (89.89, hi)

Fluent, confident, and a different amount -- `DEC-037`'s failure mode arriving through the
translator, and `DEC-072`'s own shape a third time: the artifact that was checked (English)
was right and the artifact that is delivered (Devanagari) was not. `has_digits()` cannot
see it, because it guards the English side.

**This module is a verifier, not a generator, and the distinction is the whole design.**
A generator asserts what the number *is*; one wrong entry below would make the app state a
wrong price confidently. A verifier only asks "does the translation still say what the
source said?", and anything it fails to recognise -- an unlisted dialect form, a spelling
this table does not carry -- comes back as "cannot confirm", which callers turn into an
omission. Errors in this table therefore cost a silence, never a false statement. That is
`DEC-048`'s rule again: a guardrail that occasionally declines something real is worth more
than one that occasionally asserts something absent.

No library was available to validate these forms -- `num2words` covers 56 languages
including Bengali, Kannada and Telugu, but neither Marathi nor Hindi (checked 2026-08-24).
The lexicon is hand-written, which is exactly why it is used in the safe direction.
"""
from __future__ import annotations

import re

# Cardinals 0-99. Marathi and Hindi are listed separately because the forms genuinely
# differ (24 is चोवीस against चौबीस), and folding them into one table would let a Marathi
# answer be verified against a Hindi word -- a check that passes for the wrong reason.
_MARATHI = {
    'शून्य': 0, 'एक': 1, 'दोन': 2, 'तीन': 3, 'चार': 4, 'पाच': 5, 'सहा': 6, 'सात': 7,
    'आठ': 8, 'नऊ': 9, 'दहा': 10, 'अकरा': 11, 'बारा': 12, 'तेरा': 13, 'चौदा': 14,
    'पंधरा': 15, 'सोळा': 16, 'सतरा': 17, 'अठरा': 18, 'एकोणीस': 19, 'वीस': 20,
    'एकवीस': 21, 'बावीस': 22, 'तेवीस': 23, 'चोवीस': 24, 'पंचवीस': 25, 'सव्वीस': 26,
    'सत्तावीस': 27, 'अठ्ठावीस': 28, 'एकोणतीस': 29, 'तीस': 30,
    'एकतीस': 31, 'बत्तीस': 32, 'तेहतीस': 33, 'चौतीस': 34, 'पस्तीस': 35, 'छत्तीस': 36,
    'सदतीस': 37, 'अडतीस': 38, 'एकोणचाळीस': 39, 'चाळीस': 40,
    'एकेचाळीस': 41, 'बेचाळीस': 42, 'त्रेचाळीस': 43, 'चव्वेचाळीस': 44, 'पंचेचाळीस': 45,
    'सेहेचाळीस': 46, 'सत्तेचाळीस': 47, 'अठ्ठेचाळीस': 48, 'एकोणपन्नास': 49, 'पन्नास': 50,
    'एकावन्न': 51, 'बावन्न': 52, 'त्रेपन्न': 53, 'चोपन्न': 54, 'पंचावन्न': 55,
    'छप्पन्न': 56, 'सत्तावन्न': 57, 'अठ्ठावन्न': 58, 'एकोणसाठ': 59, 'साठ': 60,
    'एकसष्ट': 61, 'बासष्ट': 62, 'त्रेसष्ट': 63, 'चौसष्ट': 64, 'पासष्ट': 65,
    'सहासष्ट': 66, 'सदुसष्ट': 67, 'अडुसष्ट': 68, 'एकोणसत्तर': 69, 'सत्तर': 70,
    'एकाहत्तर': 71, 'बाहत्तर': 72, 'त्र्याहत्तर': 73, 'चौऱ्याहत्तर': 74, 'पंचाहत्तर': 75,
    'शहात्तर': 76, 'सत्याहत्तर': 77, 'अठ्ठ्याहत्तर': 78, 'एकोणऐंशी': 79, 'ऐंशी': 80,
    'एक्याऐंशी': 81, 'ब्याऐंशी': 82, 'त्र्याऐंशी': 83, 'चौऱ्याऐंशी': 84, 'पंच्याऐंशी': 85,
    'शहाऐंशी': 86, 'सत्त्याऐंशी': 87, 'अठ्ठ्याऐंशी': 88, 'एकोणनव्वद': 89, 'नव्वद': 90,
    'एक्याण्णव': 91, 'ब्याण्णव': 92, 'त्र्याण्णव': 93, 'चौऱ्याण्णव': 94, 'पंच्याण्णव': 95,
    'शहाण्णव': 96, 'सत्त्याण्णव': 97, 'अठ्ठ्याण्णव': 98, 'नव्व्याण्णव': 99,
}

_HINDI = {
    'शून्य': 0, 'एक': 1, 'दो': 2, 'तीन': 3, 'चार': 4, 'पाँच': 5, 'पांच': 5, 'छह': 6,
    'छः': 6, 'सात': 7, 'आठ': 8, 'नौ': 9, 'दस': 10, 'ग्यारह': 11, 'बारह': 12,
    'तेरह': 13, 'चौदह': 14, 'पंद्रह': 15, 'सोलह': 16, 'सत्रह': 17, 'अठारह': 18,
    'उन्नीस': 19, 'बीस': 20,
    'इक्कीस': 21, 'बाईस': 22, 'तेईस': 23, 'चौबीस': 24, 'पच्चीस': 25, 'छब्बीस': 26,
    'सत्ताईस': 27, 'अट्ठाईस': 28, 'उनतीस': 29, 'तीस': 30,
    'इकतीस': 31, 'बत्तीस': 32, 'तैंतीस': 33, 'चौंतीस': 34, 'पैंतीस': 35, 'छत्तीस': 36,
    'सैंतीस': 37, 'अड़तीस': 38, 'उनतालीस': 39, 'चालीस': 40,
    'इकतालीस': 41, 'बयालीस': 42, 'तैंतालीस': 43, 'चवालीस': 44, 'पैंतालीस': 45,
    'छियालीस': 46, 'सैंतालीस': 47, 'अड़तालीस': 48, 'उनचास': 49, 'पचास': 50,
    'इक्यावन': 51, 'बावन': 52, 'तिरपन': 53, 'चौवन': 54, 'पचपन': 55, 'छप्पन': 56,
    'सत्तावन': 57, 'अट्ठावन': 58, 'उनसठ': 59, 'साठ': 60,
    'इकसठ': 61, 'बासठ': 62, 'तिरसठ': 63, 'चौंसठ': 64, 'पैंसठ': 65, 'छियासठ': 66,
    'सड़सठ': 67, 'अड़सठ': 68, 'उनहत्तर': 69, 'सत्तर': 70,
    'इकहत्तर': 71, 'बहत्तर': 72, 'तिहत्तर': 73, 'चौहत्तर': 74, 'पचहत्तर': 75,
    'छिहत्तर': 76, 'सतहत्तर': 77, 'अठहत्तर': 78, 'उन्यासी': 79, 'अस्सी': 80,
    'इक्यासी': 81, 'बयासी': 82, 'तिरासी': 83, 'चौरासी': 84, 'पचासी': 85, 'छियासी': 86,
    'सतासी': 87, 'अट्ठासी': 88, 'नवासी': 89, 'नब्बे': 90,
    'इक्यानवे': 91, 'बानवे': 92, 'तिरानवे': 93, 'चौरानवे': 94, 'पचानवे': 95,
    'छियानवे': 96, 'सत्तानवे': 97, 'अट्ठानवे': 98, 'निन्यानवे': 99,
}

CARDINALS = {'mr': _MARATHI, 'hi': _HINDI}

# Marathi writes hundreds as one word (तीनशे = 300); Hindi separates them (तीन सौ). Both
# forms are accepted for both languages, because the translator does not reliably respect
# the distinction and a verifier that rejects a *correct* answer costs a silence for no
# reason.
_HUNDRED_SUFFIX = re.compile(r'^(.+?)(शे|शें)$')
_HUNDRED_WORDS = {'सौ', 'शंभर', 'शे'}
_THOUSAND_WORDS = {'हजार', 'हज़ार'}

# Devanagari digits, in case the translator emits those rather than Latin ones.
_DEV_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')


def _tokens(text: str) -> list[str]:
    """Words, with punctuation stripped. Danda and full stop both end a clause."""
    cleaned = text.translate(_DEV_DIGITS)
    return [t for t in re.split(r'[\s।,.!?()\-–—:;"\']+', cleaned) if t]


def parse_numbers(text: str, lang: str) -> list[int]:
    """Every number this Devanagari text states, in order.

    Compounds accumulate the way the language builds them -- `दोन हजार अठ्ठावीस` is
    2000 + 28, `तीन सौ तैंतीस` is 300 + 33 -- and any word outside the lexicon ends the
    current number, so unrecognised text separates values rather than corrupting them.

    >>> parse_numbers('ही पाचशे रुपयांची नोट आहे.', 'mr')
    [500]
    >>> parse_numbers('हे दोन हजार अठ्ठावीस एप्रिलपर्यंत वैध आहे.', 'mr')
    [2028]
    """
    cardinals = CARDINALS.get(lang)
    if cardinals is None:
        return []

    found: list[int] = []
    total = 0        # completed thousands
    current = 0      # the group being built
    started = False

    def flush() -> None:
        nonlocal total, current, started
        if started:
            found.append(total + current)
        total, current, started = 0, 0, False

    for token in _tokens(text):
        if token.isdigit():
            # A digit run the translator passed through rather than spelling. It is a
            # stated number like any other; whether the *voice* can say it is a separate
            # question, answered by `dropped_characters`.
            flush()
            found.append(int(token))
            continue

        hundred = _HUNDRED_SUFFIX.match(token)
        if token in _THOUSAND_WORDS:
            current = (current or 1) * 1000
            total += current
            current, started = 0, True
        elif token in _HUNDRED_WORDS:
            current = (current or 1) * 100
            started = True
        elif hundred and hundred.group(1) in cardinals:
            # Marathi's single-word hundreds: तीनशे, पाचशे. `शंभर` (100) is handled above.
            current += cardinals[hundred.group(1)] * 100
            started = True
        elif token in cardinals:
            current += cardinals[token]
            started = True
        else:
            flush()

    flush()
    return found


def states_all(expected: list[int], text: str, lang: str) -> bool:
    """Does `text` state every value in `expected`, each at least as often as required?

    Order is not checked. Marathi and Hindi both reorder against English -- "April two
    thousand twenty eight" becomes `दोन हजार अठ्ठावीस एप्रिल`, year first -- so requiring
    position would fail correct translations. Presence and multiplicity are what a listener
    would notice going missing.
    """
    if not expected:
        return True
    found = parse_numbers(text, lang)
    for value in expected:
        if value in found:
            found.remove(value)
        else:
            return False
    return True
