"""SmolVLM implementation of the VLMEngine protocol.

Chosen over Moondream-2 by measurement (DEC-002): 2.5x faster, terse answers, and native
transformers classes rather than `trust_remote_code`, which broke on transformers v5.

The abstention suffix is the important part. On VizWiz-val, 49% of questions are
unanswerable -- photos too blurry, dark or mis-framed, which is what happens when the
photographer cannot see. Stock SmolVLM abstains with precision 0.913 but recall 0.258: its
judgement is sound, it simply says so too rarely. For a blind user a confident wrong answer
is worse than "I can't tell", so the prompt pushes toward abstention deliberately.

ABSTENTION_SUFFIX should be replaced with whatever wins in
notebooks/02_abstention_prompts.ipynb.
"""
from __future__ import annotations

from pathlib import Path

MODEL_ID = 'HuggingFaceTB/SmolVLM-Instruct'

# Baseline prompt from notebooks/01. Update once notebook 02 picks a winner.
ABSTENTION_SUFFIX = (
    " Answer in one to three words. If the question cannot be answered"
    " from the image, answer exactly: unanswerable"
)

SCENE_PROMPT = 'Describe what is in this image in one or two short sentences.'

# Answers matching this (after normalization) mean "I could not tell" and should be
# spoken as a plain-language apology rather than read out literally.
ABSTENTION_TOKEN = 'unanswerable'
ABSTENTION_MESSAGE = "I can't tell from this photo. Try again with better light or framing."

MAX_SIDE = 1536


def is_abstention(answer: str) -> bool:
    """True if the model declined. Kept pure and separate so callers can distinguish
    'declined' from 'answered' without string-matching in five places."""
    cleaned = answer.lower().strip().strip('.!,')
    return cleaned == ABSTENTION_TOKEN


def humanize(answer: str) -> str:
    """Turn a raw model answer into something worth speaking aloud."""
    return ABSTENTION_MESSAGE if is_abstention(answer) else answer


class SmolVLMEngine:
    """VLMEngine backed by SmolVLM. Model loads lazily on first answer()."""

    def __init__(self, model_id: str = MODEL_ID, device: str | None = None,
                 suffix: str = ABSTENTION_SUFFIX, max_side: int = MAX_SIDE):
        self.model_id = model_id
        self.suffix = suffix
        self.max_side = max_side
        self._device = device
        self._model = None
        self._processor = None

    def _load(self):
        if self._model is None:
            import torch
            from transformers import AutoProcessor
            try:  # renamed in transformers 5
                from transformers import AutoModelForImageTextToText as _VisionSeq
            except ImportError:
                from transformers import AutoModelForVision2Seq as _VisionSeq

            device = self._device or ('cuda' if torch.cuda.is_available() else 'cpu')
            self._processor = AutoProcessor.from_pretrained(self.model_id)
            self._model = _VisionSeq.from_pretrained(
                self.model_id,
                dtype=torch.float16 if device == 'cuda' else torch.float32,
                device_map=device,
            )
            self._model.eval()
            self._device = device
        return self._model

    def _open(self, image_path: Path):
        from PIL import Image

        img = Image.open(image_path).convert('RGB')
        w, h = img.size
        if max(w, h) > self.max_side:
            s = self.max_side / max(w, h)
            img = img.resize((int(w * s), int(h * s)), Image.LANCZOS)
        return img

    def answer(self, image_path: Path, question: str) -> str:
        import torch

        self._load()
        img = self._open(image_path)
        msgs = [{'role': 'user',
                 'content': [{'type': 'image'},
                             {'type': 'text', 'text': question + self.suffix}]}]
        prompt = self._processor.apply_chat_template(msgs, add_generation_prompt=True)
        inputs = self._processor(text=prompt, images=[img], return_tensors='pt').to(self._device)
        with torch.no_grad():
            out = self._model.generate(**inputs, max_new_tokens=64, do_sample=False)
        text = self._processor.batch_decode(out, skip_special_tokens=True)[0]
        return humanize(text.split('Assistant:')[-1].strip())
