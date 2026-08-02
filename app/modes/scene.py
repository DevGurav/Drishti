"""Scene mode: free-form 'describe this photo' via the VLM."""
from __future__ import annotations

from pathlib import Path

from app.interfaces import VLMEngine

_SCENE_PROMPT = "Describe what is in this image in one or two short sentences."


def run(image_path: Path, vlm: VLMEngine) -> str:
    return vlm.answer(image_path, _SCENE_PROMPT)
