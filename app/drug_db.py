"""Drug-name guardrail: medicine mode may only report a name that matches this
database (see docs/synopsis.md, objective 3). This is what stops the OCR/VLM
pipeline from reporting a drug name it merely guessed at from blurry or partial
text — a wrong medicine name is a safety hazard, not a UX nuisance.

data/drug_names_seed.txt is a small placeholder list for development only.
Replace it with a real verified source (e.g. a CDSCO/NPPA drug list export)
before trusting results from this module.
"""
from __future__ import annotations

import re
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "drug_names_seed.txt"


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


class DrugDatabase:
    def __init__(self, names: list[str]):
        self._by_normalized = {_normalize(n): n for n in names if _normalize(n)}

    @classmethod
    def from_file(cls, path: Path | None = None) -> "DrugDatabase":
        path = path or DEFAULT_DB_PATH
        names = [
            line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        return cls(names)

    def find_match(self, ocr_text: str) -> str | None:
        """Return the canonical drug name if any part of `ocr_text` matches the
        database, else None. Substring matching over normalized text so e.g.
        'PARACETAMOL 500MG' still hits the entry 'Paracetamol'."""
        normalized_text = _normalize(ocr_text)
        for key, canonical in self._by_normalized.items():
            if key in normalized_text:
                return canonical
        return None
