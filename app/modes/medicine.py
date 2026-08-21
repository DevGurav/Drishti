"""Medicine mode: OCR -> drug-name guardrail -> expiry/MRP extraction -> spoken result.

Safety rule (docs/OVERVIEW.md, objective 3): a drug name is only ever reported if it
matches DrugDatabase. If OCR can't produce a verified match, the mode declines rather
than letting a VLM guess.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.drug_db import DrugDatabase
from app.interfaces import OCREngine
from app.parsers import (
    earliest_expiry,
    extract_expiry_candidates,
    extract_mrp_candidates,
    is_expired,
)
from app.speakable import expiry_words, money_words


@dataclass
class MedicineResult:
    ok: bool
    message_en: str
    drug_names: list[str] = field(default_factory=list)
    expiry_raw: str | None = None
    expired: bool | None = None
    mrp: str | None = None

    @property
    def drug_name(self) -> str | None:
        """The first verified name, for callers that predate combination support."""
        return self.drug_names[0] if self.drug_names else None


def name_phrase(names: list[str]) -> str:
    """How the verified names are spoken.

    A combination is announced as one, rather than as a list of separate medicines: a
    user holding a single tablet of `IBUPROFEN 400 + PARACETAMOL 325` should not come
    away thinking they are holding two.
    """
    if len(names) == 1:
        return f"This is {names[0]}."
    if len(names) == 2:
        return f"This is a combination of {names[0]} and {names[1]}."
    return f"This is a combination of {', '.join(names[:-1])} and {names[-1]}."


def run(image_path: Path, ocr: OCREngine, drug_db: DrugDatabase) -> MedicineResult:
    text = ocr.read(image_path)

    drug_names = drug_db.find_matches(text)
    if not drug_names:
        return MedicineResult(
            ok=False,
            message_en=(
                "I couldn't verify the medicine name on this strip. "
                "Please ask someone to confirm before use."
            ),
        )

    # A pack can show two dates (carton and blister, or two panels in one photo), and
    # OCR line order is arbitrary, so take the earliest -- the medicine cannot be
    # trusted past it. Precautionary: no fixture has produced two dates from one photo
    # yet. See parsers.earliest_expiry.
    expiry_raw = earliest_expiry(extract_expiry_candidates(text))
    mrp_candidates = extract_mrp_candidates(text)
    mrp = mrp_candidates[0] if mrp_candidates else None
    expired = is_expired(expiry_raw) if expiry_raw else None

    # Dates and prices are spoken as words, never as digits. The Devanagari voices have
    # no '3', '5' or '8' and no Latin letters, so "APR.28" reached the user as "2" and an
    # MRP of 10.30 as 100 -- both silently, beside correct-looking text (DEC-072).
    expiry_spoken = expiry_words(expiry_raw) if expiry_raw else None

    parts = [name_phrase(drug_names)]
    if expired is True:
        # The warning does not depend on being able to spell the date. Losing "expired"
        # because the month would not render is the one failure this mode cannot have.
        when = f" in {expiry_spoken}" if expiry_spoken else ""
        parts.append(f"Warning: this medicine expired{when}. Do not use it.")
    elif expired is False and expiry_spoken:
        parts.append(f"It is valid until {expiry_spoken}.")
    else:
        parts.append("I could not read a clear expiry date -- please check manually.")

    # An unspellable price is omitted, not read out as digits: silence about the MRP is
    # recoverable, a confidently wrong price is not.
    mrp_spoken = money_words(mrp) if mrp else None
    if mrp_spoken:
        parts.append(f"MRP is {mrp_spoken}.")

    return MedicineResult(
        ok=True,
        message_en=" ".join(parts),
        drug_names=drug_names,
        expiry_raw=expiry_raw,
        expired=expired,
        mrp=mrp,
    )
