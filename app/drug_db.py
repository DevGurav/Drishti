"""Drug-name guardrail: medicine mode may only report a name that matches this
database (see docs/synopsis.md, objective 3). This is what stops the OCR/VLM
pipeline from reporting a drug name it merely guessed at from blurry or partial
text — a wrong medicine name is a safety hazard, not a UX nuisance.

The database is the National List of Essential Medicines 2022, published by the
Ministry of Health via CDSCO — government-issued, dated and citable. `DEC-007`'s
promise of a *verified* database only means something if the list itself traces to
an authority, which the previous 30-name placeholder did not.

It holds generic names only. Indian labelling requires the generic on the pack (the
Paracip strip prints "PARACETAMOL TABLETS IP" beneath the brand), while the ~250k
brand names have no authoritative public list. A strip whose generic name OCR cannot
read therefore declines rather than guesses, which is the safe direction.

Regenerate with `python data/scripts/build_drug_db.py`; that script also has a
`--check` mode proving the committed file still matches the published PDF.
"""
from __future__ import annotations

import re
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "drug_names_nlem2022.txt"


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
        'PARACETAMOL 500MG' still hits the entry 'Paracetamol'.

        **The longest match wins**, and that is a safety rule, not a tie-break
        preference. Real drug names nest inside one another -- 'Adrenaline' inside
        'Noradrenaline', 'Chloroquine' inside 'Hydroxychloroquine', 'Prednisolone'
        inside 'Methylprednisolone', 'Insulin' inside 'Insulin Glargine'. Returning
        the first hit made the answer depend on file order, so an alphabetical
        database would report a Noradrenaline vial as 'Adrenaline': a different drug,
        spoken confidently to someone who cannot check it. Taking the longest match
        always yields the most specific name that is actually present in the text.

        The 30-name placeholder list hid this entirely -- none of its entries nested.
        """
        normalized_text = _normalize(ocr_text)
        best: str | None = None
        best_len = 0
        for key, canonical in self._by_normalized.items():
            if len(key) > best_len and key in normalized_text:
                best, best_len = canonical, len(key)
        return best
