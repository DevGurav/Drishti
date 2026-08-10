"""Scene mode: free-form 'describe this photo' via the VLM."""
from __future__ import annotations

from pathlib import Path

from app.interfaces import VLMEngine


def run(image_path: Path, vlm: VLMEngine) -> str:
    # describe(), not answer(): answering carries an abstention suffix demanding one to
    # three words, which contradicts a description request and made this mode reply
    # `Paracip-500` on its first real run. The prompt now lives in the engine, next to
    # the suffix it has to stay consistent with. See DEC-031.
    return vlm.describe(image_path)
