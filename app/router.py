"""Dispatches a (mode, image, engines) request to the right mode handler.

Keeps mode-selection logic in one place so the CLI (and later, the Android/laptop
app UI) doesn't need to know which engines each mode requires.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.drug_db import DrugDatabase
from app.interfaces import Classifier, OCREngine, VLMEngine
from app.modes import ask, currency, medicine, read, scene

MODES = ("read", "medicine", "currency", "scene", "ask")


@dataclass
class Engines:
    ocr: OCREngine | None = None
    vlm: VLMEngine | None = None
    classifier: Classifier | None = None
    drug_db: DrugDatabase | None = None


class MissingEngineError(RuntimeError):
    pass


def _require(engine, name: str):
    if engine is None:
        raise MissingEngineError(f"mode needs an engine that wasn't provided: {name}")
    return engine


def route(mode: str, image_path: Path, engines: Engines, question: str = "") -> str:
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}, expected one of {MODES}")

    if mode == "read":
        return read.run(image_path, _require(engines.ocr, "ocr"))
    if mode == "medicine":
        result = medicine.run(
            image_path, _require(engines.ocr, "ocr"), _require(engines.drug_db, "drug_db")
        )
        return result.message_en
    if mode == "currency":
        return currency.run(image_path, _require(engines.classifier, "classifier"))
    if mode == "scene":
        return scene.run(image_path, _require(engines.vlm, "vlm"))
    if mode == "ask":
        return ask.run(image_path, _require(engines.vlm, "vlm"), question)

    raise AssertionError("unreachable")
