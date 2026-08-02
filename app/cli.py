"""Laptop demo entry point.

OCR-backed modes (read, medicine) are wired to PaddleOCR and work today. The VLM
(scene, ask) and currency classifier are still placeholders — they need a model
chosen in notebooks/01_vizwiz_baseline.ipynb and the currency training run.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.drug_db import DrugDatabase
from app.engines.paddle_ocr import PaddleOCREngine
from app.router import MODES, Engines, route


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


def build_default_engines(lang: str = "en") -> Engines:
    return Engines(
        ocr=PaddleOCREngine(lang=lang),
        vlm=NotWiredEngine("VLM (scene/ask modes)", "notebooks/01_vizwiz_baseline.ipynb"),
        classifier=NotWiredEngine("currency classifier", "the MobileNet training run"),
        drug_db=DrugDatabase.from_file(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Drishti laptop demo")
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--question", default="", help="only used by --mode ask")
    parser.add_argument(
        "--lang",
        default="en",
        help="PaddleOCR language for read/medicine modes (default: en)",
    )
    args = parser.parse_args()

    if not args.image.exists():
        raise SystemExit(f"image not found: {args.image}")

    engines = build_default_engines(lang=args.lang)
    result = route(args.mode, args.image, engines, question=args.question)
    print(result)


if __name__ == "__main__":
    main()
