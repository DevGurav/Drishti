"""Engine contracts that mode handlers depend on.

Real implementations (Moondream-2/SmolVLM, Surya/PaddleOCR, a MobileNet currency
classifier, IndicTrans2, MMS-TTS) get chosen in notebooks/00 and notebooks/01 and
wired in later without touching router/mode logic. Tests use plain fakes against
these same protocols instead of real models.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class OCREngine(Protocol):
    def read(self, image_path: Path) -> str:
        """Return raw recognized text from the image, line breaks preserved."""
        ...


@runtime_checkable
class VLMEngine(Protocol):
    def answer(self, image_path: Path, question: str) -> str:
        """Return a short natural-language answer to `question` about the image."""
        ...


@runtime_checkable
class Classifier(Protocol):
    def classify(self, image_path: Path) -> tuple[str, float]:
        """Return (label, confidence) for the image."""
        ...


@runtime_checkable
class Translator(Protocol):
    def translate(self, text: str, target_lang: str) -> str:
        """Translate English `text` to `target_lang` (e.g. 'mar_Deva', 'hin_Deva')."""
        ...


@runtime_checkable
class TTSEngine(Protocol):
    def speak(self, text: str, lang: str) -> Path:
        """Synthesize `text` and return the path to the generated audio file."""
        ...
