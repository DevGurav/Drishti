"""Language code mapping.

Every component in the pipeline names the same language differently:

    user / CLI        en          hi           mr
    PaddleOCR         en          hi           mr
    IndicTrans2       eng_Latn    hin_Deva     mar_Deva
    MMS-TTS           mms-tts-eng mms-tts-hin  mms-tts-mar

Keeping the translation in one place stops the mismatches from leaking into mode
handlers. `lang='devanagari'` is deliberately absent -- PaddleOCR 3.7.0 rejects it on
every ocr_version (see DEC-005 in docs/BUILD_PLAN.md); the script is reached through
'hi' or 'mr'.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str          # what the user and CLI use
    name: str          # human-readable, for messages
    ocr: str           # PaddleOCR lang
    indictrans: str    # IndicTrans2 flores-style tag
    tts_model: str     # Hugging Face MMS-TTS repo id


LANGUAGES: dict[str, Language] = {
    'en': Language('en', 'English', 'en', 'eng_Latn', 'facebook/mms-tts-eng'),
    'hi': Language('hi', 'Hindi', 'hi', 'hin_Deva', 'facebook/mms-tts-hin'),
    'mr': Language('mr', 'Marathi', 'mr', 'mar_Deva', 'facebook/mms-tts-mar'),
}

DEFAULT_LANG = 'en'

# Output languages written in Devanagari. Deliberately *not* imported from
# `app.engines.paddle_ocr`, which owns the OCR-side list: importing that module pulls in
# paddle, and the paddle/torch import order is load-bearing and platform-dependent
# (`DEC-027`, `DEC-044`). A four-entry duplicate is cheaper than that coupling.
DEVANAGARI_CODES = frozenset({'hi', 'mr'})

_DEVANAGARI_BLOCK = ('ऀ', 'ॿ')

# A quarter, not a majority. Every English answer this app builds -- a denomination, a
# drug name from NLEM, a VLM description -- contains *zero* Devanagari, so the test only
# has to tell "some" from "none". It must survive the other direction though: a real
# newspaper column carries a byline and an email, and in one excerpt of the committed
# fixture `mahesh gaikwad@timesofindia.com` alone outweighs the surrounding Devanagari
# 28 letters to 18. A majority rule called that page English and translated it (`DEC-074`).
_DEVANAGARI_SHARE = 0.25


def uses_devanagari(code: str) -> bool:
    return code in DEVANAGARI_CODES


def looks_devanagari(text: str) -> bool:
    """True when text is *already* predominantly Devanagari.

    Read mode OCRs a Marathi page and is asked for Marathi out, so its answer arrives at
    the delivery stage already in the target script. Passing that to IndicTrans2 -- an
    **English**-to-Indic model -- does not pass it through: it rewrites it into fluent,
    different Marathi and then degenerates into a repeating phrase (`DEC-074`). Detecting
    the script is how delivery knows there is nothing to translate.

    A share rather than a majority, and rather than "any" -- see `_DEVANAGARI_SHARE`.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    lo, hi = _DEVANAGARI_BLOCK
    devanagari = sum(1 for c in letters if lo <= c <= hi)
    return devanagari >= len(letters) * _DEVANAGARI_SHARE


def get(code: str) -> Language:
    """Look up a language, raising with the supported set rather than a bare KeyError."""
    try:
        return LANGUAGES[code]
    except KeyError:
        supported = ', '.join(sorted(LANGUAGES))
        raise ValueError(f"unsupported language {code!r}; supported: {supported}") from None


def codes() -> list[str]:
    return sorted(LANGUAGES)
