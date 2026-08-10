"""PaddleOCR implementation of the OCREngine protocol.

Configuration here is not arbitrary -- every setting traces to a measurement in
notebooks/00b_ocr_spike.ipynb on real photographed medicine strips:

* ``enable_mkldnn=False`` is REQUIRED, not an optimization. PaddleOCR 3.7.0 on
  PaddlePaddle 3.3.x crashes on the PIR/oneDNN CPU path with
  ``NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support``
  (Paddle issue #77340). With mkldnn off, the same photos read cleanly.
* Document preprocessing (orientation classification, UVDoc unwarping, textline
  orientation) stays **ON**. Disabling it was tried and measured on a real strip photo:
  it saved only 13% of wall time (31.7s -> 27.6s) while destroying accuracy -- output
  collapsed from readable text to ``SRN E`` / ``F``, losing the drug name, expiry and
  MRP entirely. A medicine strip photographed in the hand is curved and rotated, so
  the orientation/unwarping stages are doing load-bearing work, not scanner-era
  overhead. ``fast=True`` remains available but is not the default and should only be
  used on already-flat, upright images.
* Images are downscaled to ``max_side`` before inference. Phone cameras produce 12MP
  files; OCR does not need them, PaddleOCR 3.x has a reported CPU memory blowup on
  large inputs, and the phone app would downscale anyway.
* Devanagari (Marathi/Hindi) uses ``lang='mr'`` or ``'hi'`` -- both resolve to the
  ``devanagari_PP-OCRv5_mobile_rec`` model. ``lang='devanagari'`` does NOT exist in
  3.7.0 and raises ``ValueError`` on every ``ocr_version``.

Latency note: ~56s/image on Colab CPU at the 1280 default, plus a one-time ~59s model
load, is far above the project's <8s end-to-end target. That gap is unresolved and is a
known open issue, not a solved problem. The next lever is the model tier: this loads
``PP-OCRv6_medium_det``/``_rec`` for English and ``PP-OCRv5_server_det`` for Devanagari,
none of them the mobile variants the Android target needs anyway.
"""
from __future__ import annotations

from pathlib import Path

# Measured 2026-08-10, one process, one loaded model, three photos: 1280 is 25-35% faster
# than 1600 (medicine 56.2s vs 76.1s, newsprint 69.4s vs 103.6s, foil 58.0s vs 76.6s) with
# no accuracy cost -- identical drug name, expiry and MRP, and 1010 Devanagari characters
# recognized at both sizes on the fixture most likely to suffer from a downscale. See
# DEC-036; two earlier readings of this knob were wrong in opposite directions.
DEFAULT_MAX_SIDE = 1280

# Devanagari script codes that PaddleOCR 3.7.0 actually accepts (verified in notebook 00b).
# 'devanagari', 'hindi', 'marathi' and 'deva' all raise ValueError.
DEVANAGARI_LANGS = ('hi', 'mr', 'ne', 'sa')

# Turning these off was measured as a net loss -- see module docstring. Opt-in only.
_DOC_PREPROCESS_OFF = {
    'use_doc_orientation_classify': False,
    'use_doc_unwarping': False,
    'use_textline_orientation': False,
}


def build_kwargs(lang: str, fast: bool = False) -> dict:
    """Constructor kwargs for PaddleOCR. Kept pure so it's testable without paddle installed.

    `fast=True` disables document preprocessing. Measured on a real strip photo it cost
    the drug name, expiry and MRP for a 13% speed gain, so it defaults off.
    """
    kwargs: dict = {'lang': lang, 'enable_mkldnn': False}
    if fast:
        kwargs.update(_DOC_PREPROCESS_OFF)
    return kwargs


def extract_lines(result) -> list[tuple[float, str]]:
    """Normalize PaddleOCR output to [(confidence, text)].

    Handles the 3.x ``predict()`` shape (objects/dicts with ``rec_texts``/``rec_scores``)
    and the 2.x ``ocr()`` shape (nested ``[[bbox, (text, score)], ...]``).
    """
    lines: list[tuple[float, str]] = []
    for page in result or []:
        texts = scores = None

        if isinstance(page, dict):
            texts, scores = page.get('rec_texts'), page.get('rec_scores')
        else:
            texts = getattr(page, 'rec_texts', None)
            scores = getattr(page, 'rec_scores', None)
            if texts is None and hasattr(page, 'json'):
                blob = page.json
                blob = blob.get('res', blob) if isinstance(blob, dict) else {}
                texts, scores = blob.get('rec_texts'), blob.get('rec_scores')

        if texts is not None:
            scores = scores if scores is not None else [float('nan')] * len(texts)
            lines.extend(zip(scores, texts))
            continue

        if isinstance(page, list):  # 2.x layout
            for item in page:
                try:
                    _bbox, (text, score) = item
                    lines.append((score, text))
                except (TypeError, ValueError):
                    continue
    return lines


class PaddleOCREngine:
    """OCREngine backed by PaddleOCR. The model loads lazily on first read()."""

    def __init__(self, lang: str = 'en', max_side: int = DEFAULT_MAX_SIDE, fast: bool = False):
        self.lang = lang
        self.max_side = max_side
        self.fast = fast
        self._ocr = None

    def _load(self):
        if self._ocr is None:
            # Import paddle BEFORE paddleocr, and keep it first.
            #
            # paddleocr defers loading paddle to paddlex's import_guard, by which point
            # paddlex has already dragged torch and TensorFlow into the process. libpaddle
            # then initializes second and segfaults in its static initializers -- observed
            # on Colab as SIGSEGV inside paddle/base/core.py, at import time, with no image
            # involved. Paddle, torch and TF each link their own glog/gflags/OpenMP; the
            # loser is whichever loads last.
            #
            # This is the same conflict as DEC-006, but it fires inside PaddleOCR's own
            # dependency chain, so it happens even when nothing else in Drishti is loaded.
            # Load-time, not inference-time: neither `fast` nor `max_side` affects it.
            import paddle  # noqa: F401  -- ordering, not use
            from paddleocr import PaddleOCR

            kwargs = build_kwargs(self.lang, self.fast)
            try:
                self._ocr = PaddleOCR(**kwargs)
            except TypeError:
                # Older/newer builds may not accept the doc-preprocessing flags; the
                # mkldnn setting is the one we cannot drop.
                self._ocr = PaddleOCR(lang=self.lang, enable_mkldnn=False)
        return self._ocr

    def _prepare(self, image_path: Path):
        import numpy as np
        from PIL import Image

        img = Image.open(image_path).convert('RGB')
        w, h = img.size
        if max(w, h) > self.max_side:
            s = self.max_side / max(w, h)
            img = img.resize((int(w * s), int(h * s)), Image.LANCZOS)
        return np.array(img)

    def read_lines(self, image_path: Path) -> list[tuple[float, str]]:
        """Recognized lines with confidences — use when a caller needs to filter on score."""
        ocr = self._load()
        arr = self._prepare(image_path)
        raw = ocr.predict(arr) if hasattr(ocr, 'predict') else ocr.ocr(arr)
        return extract_lines(raw)

    def read(self, image_path: Path) -> str:
        return ' '.join(text for _, text in self.read_lines(image_path))
