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

Latency note: the Latin path now runs the small tier and takes about 13s per photo on a
laptop CPU, down from 41s (`DEC-058`). Still above the project's <8s end-to-end target,
and Devanagari is worse at ~96s because no lighter detector works for it -- see
``eval/bench_ocr.py``. The gap is narrowed, not closed.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Measured 2026-08-10, one process, one loaded model, three photos: 1280 is 25-35% faster
# than 1600 (medicine 56.2s vs 76.1s, newsprint 69.4s vs 103.6s, foil 58.0s vs 76.6s) with
# no accuracy cost -- identical drug name, expiry and MRP, and 1010 Devanagari characters
# recognized at both sizes on the fixture most likely to suffer from a downscale. See
# DEC-036; two earlier readings of this knob were wrong in opposite directions.
DEFAULT_MAX_SIDE = 1280

# ...but that was measured on large print, and it is wrong for small Latin text. A phone
# shoots 4080x3072; 1280 crushes it 3.2x linearly, a 10x loss of pixel area, and body text
# falls below what the recogniser can resolve -- it then returns confident non-words rather
# than nothing. Measured 2026-08-22 on a foil strip photographed at 4080x3072 (`DEC-073`):
#
#   max_side   fine print recovered   seconds
#     1280        7/10 fields           6.2      <- the fine print is simply absent
#     1600        7/10                  6.2
#     2048       10/10                 10.1      <- chosen for Latin
#     2560       10/10                 16.4
#     4080        7/10                 46.4      <- collapses into garbage
#
# Bigger is *not* monotonically better: at native resolution the detector is outside the
# scale it was trained for and output degrades into non-words, which is the same symptom
# as too-small text and a trap for anyone "fixing" this by removing the downscale.
LATIN_MAX_SIDE = 2048

# Devanagari wants the opposite, and the same run measured it: newspaper-marathi.png reads
# 1010 Devanagari characters at 1280 *and* 1600, but only **938 at 2048 and 2560**. That
# fixture is 1296x1720, so 2048 stops downscaling it at all -- and native is worse here for
# the same reason 4080 is worse for Latin. 1280 is also 1.4x faster than 1600 at identical
# quality, so it stays. Raising one global value would have bought small Latin print at the
# cost of 72 Devanagari characters.
DEVANAGARI_MAX_SIDE = 1280

# Devanagari script codes that PaddleOCR 3.7.0 actually accepts (verified in notebook 00b).
# 'devanagari', 'hindi', 'marathi' and 'deva' all raise ValueError.
DEVANAGARI_LANGS = ('hi', 'mr', 'ne', 'sa')

# Measured 2026-08-11 by eval/bench_ocr.py on the Paracip strip (`DEC-058`). The small
# tier reads the drug name, expiry and MRP exactly as the default does, 3.2x faster:
# medicine mode end to end went 41.2s -> 12.9s.
#
# The tier below this one is a trap and is deliberately not used. `PP-OCRv6_tiny_*` is
# 6.3x faster and loses the expiry date -- a change that looks excellent on a stopwatch
# and tells a blind user a medicine is safe when nothing was read. `DEC-030` is the same
# mistake, made once already.
DEFAULT_LATIN_DET = 'PP-OCRv6_small_det'
DEFAULT_LATIN_REC = 'PP-OCRv6_small_rec'

# Devanagari keeps PaddleOCR's own defaults -- `PP-OCRv5_server_det` plus the mobile
# recogniser. Both lighter detectors were measured and both returned **zero** Devanagari
# characters on a newspaper page the server detector reads at 1010. That is a total
# failure rather than a degradation, so the server detector stays until something else
# is shown to work. It remains a Phase-5 problem for the Android port.

# Turning these off was measured as a net loss -- see module docstring. Opt-in only.
_DOC_PREPROCESS_OFF = {
    'use_doc_orientation_classify': False,
    'use_doc_unwarping': False,
    'use_textline_orientation': False,
}


def max_side_for(lang: str) -> int:
    """The downscale limit for a script. Pure, so the choice is testable without paddle.

    Latin gets 2048 because small print in a 12MP phone photo does not survive 1280;
    Devanagari keeps 1280 because it reads *worse* above it. See `DEC-073` for both
    measurements -- neither value is transferable to the other script.
    """
    return DEVANAGARI_MAX_SIDE if lang in DEVANAGARI_LANGS else LATIN_MAX_SIDE


def build_kwargs(lang: str, fast: bool = False, det_model: str | None = None,
                 rec_model: str | None = None) -> dict:
    """Constructor kwargs for PaddleOCR. Kept pure so it's testable without paddle installed.

    `fast=True` disables document preprocessing. Measured on a real strip photo it cost
    the drug name, expiry and MRP for a 13% speed gain, so it defaults off.

    `det_model` / `rec_model` select the model tier. Left unset, PaddleOCR picks its own
    default -- which is `PP-OCRv6_medium_*` for English and, more awkwardly for a project
    targeting a phone, `PP-OCRv5_server_det` for Devanagari. `DEC-036` ruled out `max_side`
    as a latency lever and pointed here instead; `eval/bench_ocr.py` measures the tiers.
    """
    kwargs: dict = {'lang': lang, 'enable_mkldnn': False}

    # Latin script defaults to the small tier; Devanagari falls through to PaddleOCR's
    # own choice, because every lighter detector tried on it read nothing at all.
    if det_model is None and lang not in DEVANAGARI_LANGS:
        det_model = DEFAULT_LATIN_DET
    if rec_model is None and lang not in DEVANAGARI_LANGS:
        rec_model = DEFAULT_LATIN_REC

    if det_model:
        kwargs['text_detection_model_name'] = det_model
    if rec_model:
        kwargs['text_recognition_model_name'] = rec_model
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

    def __init__(self, lang: str = 'en', max_side: int | None = None, fast: bool = False,
                 det_model: str | None = None, rec_model: str | None = None):
        self.lang = lang
        # Resolved per script, not shared: the two want opposite values and a single
        # default cannot serve both (`DEC-073`). Explicit `max_side` still wins, so
        # eval/bench_ocr.py can sweep it.
        self.max_side = max_side if max_side is not None else max_side_for(lang)
        self.fast = fast
        self.det_model = det_model
        self.rec_model = rec_model
        self._ocr = None

    def _load(self):
        if self._ocr is None:
            # Import order between paddle and torch is load-bearing, and the correct
            # order is the OPPOSITE on Windows and Linux. Both link their own
            # glog/gflags/OpenMP; whichever initializes second loses (`DEC-006`).
            #
            # `paddleocr` drags torch in either way -- paddlex imports `modelscope`
            # unconditionally in inference/utils/official_models.py -- so this is not
            # avoidable by simply not using the VLM. It fires even when nothing else in
            # Drishti is loaded, and it is a *load-time* fault: neither `fast` nor
            # `max_side` affects it.
            #
            # Linux (Colab): paddle must go FIRST. Loading torch first made libpaddle
            # segfault in its static initializers -- SIGSEGV inside paddle/base/core.py,
            # at import, with no image involved (`DEC-027`).
            #
            # Windows: paddle first *breaks torch instead* --
            #   OSError: [WinError 127] ... Error loading torch\lib\shm.dll
            # because paddle\libs\libiomp5md.dll is already resident and exports a
            # different symbol set than torch's copy. Importing torch first makes both
            # work (`DEC-044`).
            if sys.platform == 'win32':
                try:
                    import torch  # noqa: F401  -- ordering, not use
                except ImportError:
                    pass          # an OCR-only environment has no torch to lose

            import paddle  # noqa: F401  -- ordering, not use
            from paddleocr import PaddleOCR

            kwargs = build_kwargs(self.lang, self.fast,
                                  self.det_model, self.rec_model)
            try:
                self._ocr = PaddleOCR(**kwargs)
            except TypeError:
                # Older/newer builds may not accept the doc-preprocessing flags; the
                # mkldnn setting is the one we cannot drop.
                self._ocr = PaddleOCR(lang=self.lang, enable_mkldnn=False)
        return self._ocr

    def _prepare(self, image_path: Path):
        import numpy as np
        from PIL import Image      # for the resample constant

        from app.imaging import load_upright

        img = load_upright(image_path)
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
