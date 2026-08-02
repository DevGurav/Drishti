"""Read mode: OCR the image and return the raw text for translation/TTS."""
from __future__ import annotations

from pathlib import Path

from app.interfaces import OCREngine


def run(image_path: Path, ocr: OCREngine) -> str:
    text = ocr.read(image_path).strip()
    return text if text else "I could not find any readable text in this image."
