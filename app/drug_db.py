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

    def find_matches(self, ocr_text: str) -> list[str]:
        """Every distinct database drug present in `ocr_text`, in the order printed.

        Combination products are ordinary in India -- `IBUPROFEN 400mg PARACETAMOL 325mg`
        is a single tablet -- and reporting one name means a user is told half of what
        they are holding. `find_match` answers the "which name" question; this answers
        "which names", which is what medicine mode actually needs.

        The hard part is that reporting *more* names must not reintroduce the nesting bug
        `DEC-033` fixed. `Adrenaline` is a substring of `Noradrenaline`, so a naive
        "return everything that matches" turns one Noradrenaline vial into two drugs, one
        of which is not in the user's hand -- worse than the original bug, because it
        invents a medicine rather than merely mislabelling one.

        Occurrence counting separates the two cases without guessing. A short name is
        reported only when it appears more often than the longer names containing it can
        account for:

            'NORADRENALINE 2MG'              adrenaline x1, noradrenaline x1
                                             -> 1 - 1 = 0, so Adrenaline is not present
            'ADRENALINE 1MG NORADRENALINE'   adrenaline x2, noradrenaline x1
                                             -> 2 - 1 = 1, so both are genuinely present
        """
        text = _normalize(ocr_text)
        hits = {key: text.count(key) for key in self._by_normalized if key in text}

        present = [
            key for key, count in hits.items()
            if count > sum(c for other, c in hits.items() if other != key and key in other)
        ]
        # Printed order, so the spoken answer tracks the strip left to right rather than
        # dictionary order -- the user is matching what they hear against what they hold.
        present.sort(key=text.index)
        return [self._by_normalized[key] for key in present]

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
