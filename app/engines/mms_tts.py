"""MMS-TTS implementation of the TTSEngine protocol.

Meta's MMS voices cover Marathi and Hindi, run offline, and are small (~150MB each) --
the combination Drishti needs. Verified in notebooks/00_feasibility_spike_colab.ipynb §5.

One model is loaded per language and cached, because switching languages mid-session is
expected (a user may ask in Marathi and read an English label).
"""
from __future__ import annotations

import sys
import unicodedata
import wave
from collections import Counter
from pathlib import Path

from app.languages import get as get_language

# MMS-TTS degrades on very long inputs; Drishti's answers are short, but scene
# descriptions can run long enough to matter.
MAX_CHARS = 400


def split_for_tts(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Split text into chunks at sentence boundaries, staying under max_chars.

    Pure function so chunking is testable without loading a model.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current = ''
    for sentence in text.replace('\n', ' ').split('. '):
        piece = sentence if sentence.endswith('.') else sentence + '.'
        if current and len(current) + len(piece) + 1 > max_chars:
            chunks.append(current.strip())
            current = piece
        else:
            current = f'{current} {piece}'.strip()
    if current:
        chunks.append(current.strip())
    return chunks


def dropped_characters(text: str, tokenizer) -> list[str]:
    """Characters this voice silently discards, found by round-tripping the tokenizer.

    A VITS tokenizer filters its input down to its own character vocabulary and raises
    nothing, so a number that will not be spoken looks exactly like one that will. The
    Marathi voice has no '3', '5' or '8' and no Latin letters at all: it turned "500"
    into "00" and an expiry of "APR.28" into "2" (DEC-072).

    This is a **detector, not a control** -- it reports after the fact, and read mode
    legitimately passes through arbitrary OCR text. The actual fix is upstream, in
    `app/speakable.py`, where answers are built as words before they ever get here.
    """
    heard = tokenizer.decode(tokenizer(text).input_ids)
    lost = Counter(text.lower()) - Counter(heard.lower())
    return sorted({ch for ch in lost if _carries_meaning(ch)})


def _carries_meaning(ch: str) -> bool:
    """Whether losing this character changes what the listener hears as content.

    Every voice drops the sentence-final full stop, so counting punctuation would make
    this warn on all output -- and a warning that always fires is not a signal, it is
    noise that gets tuned out (the DEC-063 lesson). Letters, digits and the Devanagari
    vowel marks are kept: those change the word.
    """
    return ch.isalnum() or unicodedata.category(ch).startswith('M')


class MMSTTSEngine:
    """Offline speech synthesis. Models load lazily and are cached per language."""

    def __init__(self, out_dir: Path | None = None):
        self.out_dir = out_dir or Path('.')
        self._models: dict[str, tuple] = {}

    def _load(self, lang: str):
        if lang not in self._models:
            from transformers import AutoTokenizer, VitsModel

            repo = get_language(lang).tts_model
            self._models[lang] = (
                VitsModel.from_pretrained(repo),
                AutoTokenizer.from_pretrained(repo),
            )
        return self._models[lang]

    def speak(self, text: str, lang: str) -> Path:
        """Synthesize `text` and return the path to a wav file."""
        import numpy as np
        import torch

        model, tokenizer = self._load(lang)
        chunks = split_for_tts(text)
        if not chunks:
            raise ValueError('nothing to speak')

        waveforms = []
        for chunk in chunks:
            lost = dropped_characters(chunk, tokenizer)
            if lost:
                print(
                    f"warning: the {lang} voice has no {''.join(lost)!r} in its "
                    f'vocabulary -- those characters are missing from the audio, so '
                    f'what is spoken differs from what was printed',
                    file=sys.stderr,
                )
            inputs = tokenizer(chunk, return_tensors='pt')
            with torch.no_grad():
                waveforms.append(model(**inputs).waveform.squeeze().cpu().numpy())

        audio = np.concatenate(waveforms) if len(waveforms) > 1 else waveforms[0]
        pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)

        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / f'drishti_{lang}.wav'
        with wave.open(str(path), 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(model.config.sampling_rate)
            f.writeframes(pcm.tobytes())
        return path
