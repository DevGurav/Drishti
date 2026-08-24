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

import re

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


# Above this many digits a run is far more likely to be an identifier -- a pincode, a
# phone number, a batch code -- than a quantity, and "one five zero zero zero" is both
# safer and closer to how a person reads one out. Below it, the cardinal is right:
# a year, a page number, a price.
MAX_CARDINAL_DIGITS = 4

_ORDINAL_WORDS = {'one': 'first', 'two': 'second', 'three': 'third', 'five': 'fifth',
                  'eight': 'eighth', 'nine': 'ninth', 'twelve': 'twelfth'}

_NUMBER_RUN = re.compile(r'(\d+)(?:\.(\d+))?(st|nd|rd|th)?', re.IGNORECASE)


def _digit_by_digit(digits: str) -> str:
    return ' '.join(_ONES[int(d)] for d in digits)


def _ordinal(n: int) -> str:
    head, _, last = number_words(n).rpartition(' ')
    if last in _ORDINAL_WORDS:
        last = _ORDINAL_WORDS[last]
    elif last.endswith('y'):
        last = f'{last[:-1]}ieth'
    else:
        last = f'{last}th'
    return f'{head} {last}'.strip()


def spell_numbers_in_text(text: str) -> str:
    """Replace every digit run in free text with words.

    For the modes that *relay* text rather than construct it -- read, scene, ask -- the
    answer is whatever OCR or the VLM produced, so there is no single number to spell.
    Every voice this project ships drops digits it lacks (`DEC-072`): Marathi has no
    `3/5/8`, Hindi no `5/6/7/9`, and **English none of `7/8/9`**, which turns "789 rupees"
    into "rupees" and "EXP 2028" into "exp 202".

    >>> spell_numbers_in_text('EXP 2028, MRP 87.90')
    'EXP two thousand twenty eight, MRP eighty seven point nine zero'
    """
    def replace(match: re.Match) -> str:
        whole, frac, ordinal_suffix = match.group(1), match.group(2), match.group(3)

        if ordinal_suffix and not frac:
            if len(whole) <= MAX_CARDINAL_DIGITS:
                return _ordinal(int(whole))
            return f'{_digit_by_digit(whole)} {ordinal_suffix}'

        spoken = (number_words(int(whole)) if len(whole) <= MAX_CARDINAL_DIGITS
                  else _digit_by_digit(whole))
        if frac:
            # Read the fractional part digit by digit: "point nine zero", not "point
            # ninety", which would be a different quantity.
            spoken = f'{spoken} point {_digit_by_digit(frac)}'
        return spoken

    return _NUMBER_RUN.sub(replace, text)


def has_digits(text: str) -> bool:
    """True if any Latin digit survives in text bound for a Devanagari voice.

    The invariant the mode handlers are tested against. Cheap enough to assert on every
    spoken answer, and needs no model loaded.
    """
    return any(ch.isdigit() for ch in text)


_ENGLISH_CARDINALS = {word: value for value, word in enumerate(_ONES)}
_ENGLISH_CARDINALS.update({word: value * 10
                           for value, word in enumerate(_TENS) if word})

_WORD = re.compile(r"[a-z]+")


def parse_english_numbers(text: str) -> list[int]:
    """Every number this English text states, in order.

    The inverse of `number_words`, and the reason it exists: to know what a translation
    was *supposed* to say, the value has to be recoverable from the English that went in.
    By the time `app/speech.localize` sees a medicine answer the digits are already gone --
    the mode handler spelled them through `money_words` -- so reading the digits back is
    not an option and the words have to be parsed instead.

    >>> parse_english_numbers('MRP is eighty four rupees and twenty one paise.')
    [84, 21]
    >>> parse_english_numbers('It is valid until April two thousand twenty eight.')
    [2028]
    """
    found: list[int] = []
    total = 0
    current = 0
    started = False
    in_fraction = False

    def flush() -> None:
        nonlocal total, current, started
        if started:
            found.append(total + current)
        total, current, started = 0, 0, False

    for token in _WORD.findall(text.lower()):
        if token == 'point':
            # `spell_numbers_in_text` renders a fraction digit by digit -- "eighty seven
            # point nine zero" -- because "point ninety" would be a different quantity.
            # Each digit after this is its own value, so accumulating them the way a
            # compound accumulates would read .90 as a single 9 and 87.90 as 96.
            flush()
            in_fraction = True
        elif in_fraction and token in _ENGLISH_CARDINALS:
            found.append(_ENGLISH_CARDINALS[token])
        elif token == 'thousand':
            current = (current or 1) * 1000
            total += current
            current, started = 0, True
        elif token == 'hundred':
            current = (current or 1) * 100
            started = True
        elif token in _ENGLISH_CARDINALS:
            # "twenty one" is one number, but "one one" is two -- a compound only
            # continues while each part is smaller than the last.
            value = _ENGLISH_CARDINALS[token]
            if started and value >= max(current % 100 or 100, 1) and current % 100:
                flush()
            current += value
            started = True
        elif token == 'and':
            # "one hundred and twenty" is one number, and money_words writes "eighty four
            # rupees and twenty one paise" -- where `rupees` has already ended the first
            # number, so joining here costs nothing and helps the hundreds case.
            continue
        else:
            flush()
            in_fraction = False

    flush()
    return found
