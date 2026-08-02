"""Laptop demo entry point.

All five modes are wired. Heavy models load lazily on first use, so `--mode medicine`
never pays for the VLM and `--mode scene` never pays for OCR.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app import languages
from app.drug_db import DrugDatabase
from app.engines.indictrans import IndicTrans2Translator
from app.engines.mms_tts import MMSTTSEngine
from app.engines.paddle_ocr import PaddleOCREngine
from app.engines.smolvlm import SmolVLMEngine
from app.router import MODES, Engines, route
from app.speech import deliver


class NotWiredEngine:
    """Fails loudly instead of silently returning fake data."""

    def __init__(self, what: str, blocked_on: str):
        self._what = what
        self._blocked_on = blocked_on

    def __getattr__(self, _name):
        def _unimplemented(*_args, **_kwargs):
            raise NotImplementedError(
                f"{self._what} is not wired in yet — blocked on {self._blocked_on}."
            )

        return _unimplemented


def build_engines(ocr_lang: str = 'en') -> Engines:
    return Engines(
        ocr=PaddleOCREngine(lang=languages.get(ocr_lang).ocr),
        vlm=SmolVLMEngine(),
        classifier=NotWiredEngine("currency classifier", "the MobileNet training run"),
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
