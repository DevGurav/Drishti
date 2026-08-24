"""English answer -> localized text -> spoken audio.

Mode handlers all produce English. Localization and speech are deliberately a separate
stage rather than something each mode does, so a new mode gets Marathi output for free and
the translation/TTS models are loaded at most once.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import re
import sys

from app.devanagari_numbers import states_all
from app.engines.indictrans import needs_translation
from app.interfaces import TTSEngine, Translator
from app.languages import get as get_language
from app.languages import looks_devanagari, uses_devanagari
from app.speakable import has_digits, parse_english_numbers, spell_numbers_in_text


@dataclass
class SpokenResult:
    text_en: str
    text_out: str
    lang: str
    audio_path: Path | None = None


def localize(text_en: str, lang: str, translator: Translator | None) -> str:
    """Translate an English answer into `lang`.

    Returns the English unchanged when the target is English or no translator is wired,
    so callers get a usable string rather than an exception in the degraded case.
    """
    get_language(lang)  # validate early, with a helpful error

    # Already in the target script? Then there is nothing to translate, and translating
    # anyway destroys it. Read mode OCRs a Marathi page correctly and IndicTrans2 -- an
    # English-to-Indic model -- rewrote `भिवंडी` (a city) as `विव्हंदी` (not a word) and
    # `निधीचा` (of funds) as `नीतीचा` (of policy), then looped on `अधिक माहितीचे`. Fluent,
    # confident and wrong, to a user who cannot see the page (`DEC-074`).
    #
    # Number spelling is skipped on this path too, and must be: it produces *English*
    # words, and with no translation step to render them these voices would drop them
    # entirely -- every Latin letter is outside their vocabulary. Digits in Devanagari
    # text are therefore still partly lost, which `dropped_characters` warns about and
    # only a Marathi/Hindi number speller would fix.
    if uses_devanagari(lang) and looks_devanagari(text_en):
        return text_en

    # Digits are spelled out here, before translation, for *every* language. Currency and
    # medicine already build their answers as words, but read, scene and ask relay whatever
    # OCR or the VLM produced, and every voice this project ships drops digits it lacks:
    # Marathi has no 3/5/8, Hindi no 5/6/7/9, and English none of 7/8/9 -- so "789 rupees"
    # was spoken as "rupees" even on the untranslated path (`DEC-072`). Doing it before
    # translation matters: IndicTrans2 renders number *words* into Devanagari number words,
    # and passes digits through unchanged.
    text_en = spell_numbers_in_text(text_en)

    if not text_en.strip() or not needs_translation(lang) or translator is None:
        return text_en

    # No numbers to lose: translate as one block, which is both faster and what read mode
    # wants for a page of prose.
    if not parse_english_numbers(text_en):
        return translator.translate(text_en, lang)

    return _translate_verifying_numbers(text_en, lang, translator)


_SENTENCE = re.compile(r'(?<=[.!?])\s+')


def _numbers_reached_the_listener(source_en: str, translated: str, lang: str) -> bool:
    """Will the listener hear the numbers the English sentence stated?

    Two ways they will not, and both end the same way. `states_all` catches a value that
    *changed* -- "eighty four rupees" returning as `चोवीस रुपये`, twenty-four. The digit
    check catches a value that survived as digits: the translator re-emits them roughly
    one time in five, and these voices have no digits in vocabulary, so
    `62 रुपये आणि 37 पैसे` is spoken "62 rupees and 7 paise" (`DEC-072`). Right on the
    page, wrong in the ear -- the distinction this project keeps relearning.

    The script gate matters. The lexicon is Devanagari, so running it over Latin output
    can only ever fail, and a translator that returned Latin has a different problem that
    a different guard already reports: `dropped_characters` warns that a voice with no
    Latin letters is about to discard the whole sentence. Rejecting here as well would
    turn one clear diagnosis into two vague ones.
    """
    expected = parse_english_numbers(source_en)
    if not expected or not looks_devanagari(translated):
        return True
    return not has_digits(translated) and states_all(expected, translated, lang)


def _translate_verifying_numbers(text_en: str, lang: str, translator: Translator) -> str:
    """Translate sentence by sentence, dropping any sentence whose numbers did not survive.

    IndicTrans2 renders number words faithfully most of the time and silently wrongly the
    rest: measured over 16 real MRP values on 2026-08-24, 7 of 16 Marathi and 5 of 16 Hindi
    translations either re-emitted digits or stated a different amount -- `eighty four
    rupees` came back as `चोवीस रुपये`, twenty-four. `DEC-072`'s fix runs upstream of the
    translator, and `has_digits()` guards the English, so nothing downstream noticed.

    Per sentence rather than per answer because the alignment has to be exact: knowing a
    number went missing is no use without knowing which clause to drop. A medicine answer
    is three sentences -- name, expiry, price -- and losing only the price to a bad
    translation is the outcome `DEC-072` already specified for an unspeakable MRP: "an MRP
    that cannot be spelled is omitted rather than spoken as digits".

    Dropping is safe in a way that correcting would not be. Rewriting the number would mean
    asserting the Marathi form ourselves, and no library validates those (`num2words` covers
    neither language); a wrong assertion here is a confidently wrong price, the exact defect
    this guards. A dropped clause costs the user a fact they can ask for again.
    """
    kept, dropped = [], []
    for sentence in _SENTENCE.split(text_en.strip()):
        if not sentence.strip():
            continue
        translated = translator.translate(sentence, lang)
        if _numbers_reached_the_listener(sentence, translated, lang):
            kept.append(translated)
        else:
            dropped.append(sentence)

    if dropped:
        # stderr, not silence: the printed English still carries the number, so a listener
        # who is told less than a reader should be traceable to a cause.
        print(f'warning: {len(dropped)} sentence(s) dropped from the {lang} answer -- the '
              f'translation did not preserve their numbers, and speaking a different '
              f'amount is worse than speaking none: {dropped}', file=sys.stderr)

    return ' '.join(kept)


def deliver(text_en: str, lang: str = 'en', translator: Translator | None = None,
            tts: TTSEngine | None = None, speak: bool = False) -> SpokenResult:
    """Run the full output stage. Audio is only synthesized when asked for."""
    text_out = localize(text_en, lang, translator)
    audio = tts.speak(text_out, lang) if (speak and tts and text_out.strip()) else None
    return SpokenResult(text_en=text_en, text_out=text_out, lang=lang, audio_path=audio)
