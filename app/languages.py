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


def get(code: str) -> Language:
    """Look up a language, raising with the supported set rather than a bare KeyError."""
    try:
        return LANGUAGES[code]
    except KeyError:
        supported = ', '.join(sorted(LANGUAGES))
        raise ValueError(f"unsupported language {code!r}; supported: {supported}") from None


def codes() -> list[str]:
    return sorted(LANGUAGES)
