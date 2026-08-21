"""English answer -> localized text -> spoken audio.

Mode handlers all produce English. Localization and speech are deliberately a separate
stage rather than something each mode does, so a new mode gets Marathi output for free and
the translation/TTS models are loaded at most once.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.engines.indictrans import needs_translation
from app.interfaces import TTSEngine, Translator
from app.languages import get as get_language
from app.languages import looks_devanagari, uses_devanagari
from app.speakable import spell_numbers_in_text


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
    return translator.translate(text_en, lang)


def deliver(text_en: str, lang: str = 'en', translator: Translator | None = None,
            tts: TTSEngine | None = None, speak: bool = False) -> SpokenResult:
    """Run the full output stage. Audio is only synthesized when asked for."""
    text_out = localize(text_en, lang, translator)
    audio = tts.speak(text_out, lang) if (speak and tts and text_out.strip()) else None
    return SpokenResult(text_en=text_en, text_out=text_out, lang=lang, audio_path=audio)
