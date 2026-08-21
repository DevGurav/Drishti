"""Numbers must reach the TTS engine as words, never as digits.

MMS-TTS's Marathi and Hindi voices carry a Devanagari *character* vocabulary. The digits
`3`, `5` and `8` are absent from it, as is every Latin letter, and the tokenizer drops
what it cannot encode without raising. Measured on `facebook/mms-tts-mar`, 2026-08-22:

    "ही 500 रुपयांची नोट आहे."                     spoken as  "ही 00 रुपयांची नोट आहे"
    "हे APR.28 पर्यंत वैध आहे. एमआरपी 10.30 रुपये आहे."   spoken as  "हे 2 पर्यंत वैध आहे
                                                            एमआरपी 100 रुपये आहे"

So a Rs 500 note was announced as "00 rupees", an expiry of April 2028 as "2", and an
MRP of Rs 10.30 as Rs 100 -- each with correct-looking text printed beside it. IndicTrans2
passes numerals through as Latin digits, so nothing upstream converts them (DEC-072).

Everything here produces **English** words, applied before translation. IndicTrans2 then
renders them as Marathi/Hindi number words, which are wholly in-vocabulary.

The rule this enforces: *what is printed must be what is spoken.* Verifying the text
proves nothing about the audio unless the two are the same string.
"""
from __future__ import annotations

from app.parsers import parse_expiry_date

_ONES = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
         'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
         'seventeen', 'eighteen', 'nineteen']
_TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty',
         'ninety']
_MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                'August', 'September', 'October', 'November', 'December']

# Above this the Indian names (lakh, crore) diverge from the short scale, and nothing in
# this app -- a denomination, an MRP, a year -- comes close. Raise rather than guess.
MAX_NUMBER = 999_999


def number_words(n: int) -> str:
    """Spell a non-negative integer in English words.

    >>> number_words(500)
    'five hundred'
    >>> number_words(2028)
    'two thousand twenty eight'
    """
    if n < 0:
        raise ValueError(f'negative numbers are not spoken here: {n}')
    if n > MAX_NUMBER:
        raise ValueError(f'{n} exceeds MAX_NUMBER={MAX_NUMBER}')

    if n < 20:
        return _ONES[n]
    if n < 100:
        tens, rest = divmod(n, 10)
        return _TENS[tens] + (f' {_ONES[rest]}' if rest else '')
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        return f'{_ONES[hundreds]} hundred' + (f' {number_words(rest)}' if rest else '')
    thousands, rest = divmod(n, 1000)
    return (f'{number_words(thousands)} thousand'
            + (f' {number_words(rest)}' if rest else ''))


def money_words(raw: str) -> str | None:
    """Spell an OCR'd rupee amount, e.g. '10.30' -> 'ten rupees and thirty paise'.

    Returns None when the string cannot be read as an amount. Callers must then omit the
    price rather than fall back to the raw digits: an MRP that is silently mangled into a
    different number is worse than one that is not spoken at all.
    """
    cleaned = raw.strip().replace(',', '').rstrip('.')
    if not cleaned:
        return None

    rupees_part, _, paise_part = cleaned.partition('.')
    if not rupees_part.isdigit():
        return None
    # '10.5' means fifty paise, not five -- pad on the right, the side that was dropped.
    paise_part = paise_part.ljust(2, '0') if paise_part else ''
    if paise_part and not paise_part.isdigit():
        return None

    try:
        rupees = number_words(int(rupees_part))
        if not paise_part or int(paise_part[:2]) == 0:
            return f'{rupees} rupees'
        return f'{rupees} rupees and {number_words(int(paise_part[:2]))} paise'
    except ValueError:
        return None


def expiry_words(raw: str) -> str | None:
    """Spell a strip's expiry, e.g. 'APR.28' -> 'April two thousand twenty eight'.

    Month and year only. `parse_expiry_date` returns the *last day* of the printed month
    because strips carry no day, so speaking a day would invent precision the pack does
    not have. Returns None when the date cannot be parsed -- medicine mode already says
    "I could not read a clear expiry date" in that case and must keep saying it.
    """
    parsed = parse_expiry_date(raw)
    if parsed is None:
        return None
    return f'{_MONTH_NAMES[parsed.month - 1]} {number_words(parsed.year)}'


def has_digits(text: str) -> bool:
    """True if any Latin digit survives in text bound for a Devanagari voice.

    The invariant the mode handlers are tested against. Cheap enough to assert on every
    spoken answer, and needs no model loaded.
    """
    return any(ch.isdigit() for ch in text)
