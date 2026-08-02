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
    if not text_en.strip() or not needs_translation(lang) or translator is None:
        return text_en
    return translator.translate(text_en, lang)


def deliver(text_en: str, lang: str = 'en', translator: Translator | None = None,
            tts: TTSEngine | None = None, speak: bool = False) -> SpokenResult:
    """Run the full output stage. Audio is only synthesized when asked for."""
    text_out = localize(text_en, lang, translator)
    audio = tts.speak(text_out, lang) if (speak and tts and text_out.strip()) else None
    return SpokenResult(text_en=text_en, text_out=text_out, lang=lang, audio_path=audio)
