"""SmolVLM implementation of the VLMEngine protocol.

Chosen over Moondream-2 by measurement (DEC-002): 2.5x faster, terse answers, and native
transformers classes rather than `trust_remote_code`, which broke on transformers v5.

The abstention suffix is the important part. On VizWiz-val, 49% of questions are
unanswerable -- photos too blurry, dark or mis-framed, which is what happens when the
photographer cannot see.

ABSTENTION_SUFFIX is the 'stakes' variant, which won the sweep in
notebooks/02_abstention_prompts.ipynb over five candidates (500 samples, same slice as
the baseline):

    metric          stock prompt   stakes    delta
    overall             0.308       0.533   +0.225
    unanswerable acc    0.306       0.673   +0.367
    abstention recall   0.258       0.639   +0.381
    abstention prec.    0.913       0.726   -0.187

Naming the stakes -- that the user cannot verify the answer -- beat listing failure
criteria, stating the base rate, and simply demanding more caution. The precision drop is
an accepted trade: a false abstention costs a retaken photo, a false answer can cost a
wrong medicine. See DEC-016 in docs/BUILD_PLAN.md.
"""
from __future__ import annotations

from pathlib import Path

MODEL_ID = 'HuggingFaceTB/SmolVLM-Instruct'

# Winner of the notebook-02 sweep. Changing this changes measured behaviour -- re-run
# notebooks/02_abstention_prompts.ipynb rather than editing it by intuition.
ABSTENTION_SUFFIX = (
    " The person asking is blind and cannot check your answer, so a confident wrong"
    " answer is worse than no answer. Answer in one to three words only if the image"
    " clearly shows it. Otherwise answer exactly: unanswerable"
)

SCENE_PROMPT = 'Describe what is in this image in one or two short sentences.'

# Answers matching this (after normalization) mean "I could not tell" and should be
# spoken as a plain-language apology rather than read out literally.
ABSTENTION_TOKEN = 'unanswerable'
ABSTENTION_MESSAGE = "I can't tell from this photo. Try again with better light or framing."

MAX_SIDE = 1536


def is_abstention(answer: str) -> bool:
    """True if the model declined. Kept pure and separate so callers can distinguish
    'declined' from 'answered' without string-matching in five places.

    The `Answer:` prefix is stripped because SmolVLM emits it intermittently -- 4 of 500
    abstentions in the notebook-02 run came back as "Answer: unanswerable". Left unhandled
    the app would read that string aloud to a blind user instead of offering the retake
    guidance, which is the failure this function exists to prevent.
    """
    cleaned = answer.lower().strip().strip('.!,').strip()
    if cleaned.startswith('answer:'):
        cleaned = cleaned[len('answer:'):].strip()
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
        from PIL import Image      # for the resample constant

        from app.imaging import load_upright

        img = load_upright(image_path)
        w, h = img.size
        if max(w, h) > self.max_side:
            s = self.max_side / max(w, h)
            img = img.resize((int(w * s), int(h * s)), Image.LANCZOS)
        return img

    def _generate(self, image_path: Path, prompt_text: str, max_new_tokens: int) -> str:
        import torch

        self._load()
        img = self._open(image_path)
        msgs = [{'role': 'user',
                 'content': [{'type': 'image'}, {'type': 'text', 'text': prompt_text}]}]
        prompt = self._processor.apply_chat_template(msgs, add_generation_prompt=True)
        inputs = self._processor(text=prompt, images=[img], return_tensors='pt').to(self._device)
        with torch.no_grad():
            out = self._model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        text = self._processor.batch_decode(out, skip_special_tokens=True)[0]
        return humanize(text.split('Assistant:')[-1].strip())

    def answer(self, image_path: Path, question: str) -> str:
        """Terse, abstention-aware VQA — the behaviour measured at 0.533 on VizWiz."""
        return self._generate(image_path, question + self.suffix, max_new_tokens=64)

    def describe(self, image_path: Path) -> str:
        """Scene description, deliberately without `self.suffix`.

        The abstention suffix demands one to three words or the literal token
        `unanswerable`, which flatly contradicts asking for a sentence or two. Sharing
        it made the first real run answer `Paracip-500` for a whole-scene description.
        Editing the suffix to suit both would invalidate the measured 0.533 (`DEC-016`),
        so description simply does not carry it (`DEC-031`).

        `humanize` still applies: the model can decline unprompted, and reading the raw
        token aloud to a blind user is the bug it exists to prevent.
        """
        return self._generate(image_path, SCENE_PROMPT, max_new_tokens=128)
