"""Laptop demo entry point.

All five modes are wired. Heavy models load lazily on first use, so `--mode medicine`
never pays for the VLM and `--mode scene` never pays for OCR.
"""
from __future__ import annotations

import argparse
import os
import sys

# Must be set before PaddlePaddle or PyTorch load. Each bundles its own OpenMP runtime, and
# a single command can legitimately need both (medicine mode runs OCR, then --lang mr loads
# IndicTrans2 on torch). Co-loading them aborts the process -- it is what killed the Colab
# kernel during the OCR spike, with no Python traceback. See DEC-006 in docs/BUILD_PLAN.md.
# This is a mitigation, not a fix; the real fix is separate inference processes (Phase 5).
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

from pathlib import Path  # noqa: E402

from app import languages
from app.drug_db import DrugDatabase
from app.engines.currency_cnn import CurrencyClassifier
from app.engines.indictrans import IndicTrans2Translator
from app.engines.mms_tts import MMSTTSEngine
from app.engines.paddle_ocr import PaddleOCREngine
from app.engines.smolvlm import SmolVLMEngine
from app.router import MODES, Engines, route
from app.speech import deliver


def build_engines(ocr_lang: str = 'en') -> Engines:
    """Engines are cheap to construct — every one loads its weights lazily, so an unused
    mode costs nothing and a missing model is reported only when that mode is used."""
    return Engines(
        ocr=PaddleOCREngine(lang=languages.get(ocr_lang).ocr),
        vlm=SmolVLMEngine(),
        classifier=CurrencyClassifier(),
        drug_db=DrugDatabase.from_file(),
    )


def _force_utf8_stdout() -> None:
    """Windows consoles default to cp1252, which cannot encode Devanagari — printing a
    Marathi or Hindi answer raises UnicodeEncodeError and takes down the whole run. The
    output is the product here, so this is not cosmetic."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, OSError):
            pass  # already UTF-8, or a stream that doesn't support reconfigure


def main() -> None:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description="Drishti laptop demo")
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--question", default="", help="only used by --mode ask")
    parser.add_argument(
        "--lang", default="en", choices=languages.codes(),
        help="output language for the spoken answer (default: en)",
    )
    parser.add_argument(
        "--ocr-lang", default=None, choices=languages.codes(),
        help="script to OCR; defaults to --lang. Use 'en' for medicine strips, "
             "which print drug name and expiry in Latin script even on Marathi packaging",
    )
    parser.add_argument("--speak", action="store_true", help="synthesize a wav file")
    args = parser.parse_args()

    if not args.image.exists():
        raise SystemExit(f"image not found: {args.image}")

    engines = build_engines(ocr_lang=args.ocr_lang or args.lang)
    answer_en = route(args.mode, args.image, engines, question=args.question)

    translator = IndicTrans2Translator() if args.lang != "en" else None
    tts = MMSTTSEngine() if args.speak else None
    result = deliver(answer_en, lang=args.lang, translator=translator,
                     tts=tts, speak=args.speak)

    print(result.text_en)
    if result.text_out != result.text_en:
        print(f"[{languages.get(args.lang).name}] {result.text_out}")
    if result.audio_path:
        print(f"audio: {result.audio_path}")


if __name__ == "__main__":
    main()
