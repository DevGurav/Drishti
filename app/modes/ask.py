"""Ask mode: free-form VQA -- the user's own question about the photo."""
from __future__ import annotations

from pathlib import Path

from app.interfaces import VLMEngine


def run(image_path: Path, vlm: VLMEngine, question: str) -> str:
    if not question.strip():
        return "Please ask a question about the photo."
    return vlm.answer(image_path, question)
