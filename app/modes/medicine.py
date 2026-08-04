"""Medicine mode: OCR -> drug-name guardrail -> expiry/MRP extraction -> spoken result.

Safety rule (docs/synopsis.md, objective 3): a drug name is only ever reported if it
matches DrugDatabase. If OCR can't produce a verified match, the mode declines rather
than letting a VLM guess.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.drug_db import DrugDatabase
from app.interfaces import OCREngine
from app.parsers import (
    earliest_expiry,
    extract_expiry_candidates,
    extract_mrp_candidates,
    is_expired,
)


@dataclass
class MedicineResult:
    ok: bool
    message_en: str
    drug_name: str | None = None
    expiry_raw: str | None = None
    expired: bool | None = None
    mrp: str | None = None


def run(image_path: Path, ocr: OCREngine, drug_db: DrugDatabase) -> MedicineResult:
    text = ocr.read(image_path)

    drug_name = drug_db.find_match(text)
    if drug_name is None:
        return MedicineResult(
            ok=False,
            message_en=(
                "I couldn't verify the medicine name on this strip. "
                "Please ask someone to confirm before use."
            ),
        )

    # Strips often show two dates (carton and blister, or two panels in one photo).
    # Take the earliest -- the medicine cannot be trusted past it, and OCR line order
    # is arbitrary. See parsers.earliest_expiry.
    expiry_raw = earliest_expiry(extract_expiry_candidates(text))
    mrp_candidates = extract_mrp_candidates(text)
    mrp = mrp_candidates[0] if mrp_candidates else None
    expired = is_expired(expiry_raw) if expiry_raw else None

    parts = [f"This is {drug_name}."]
    if expired is True:
        parts.append(f"Warning: it expired on {expiry_raw}. Do not use it.")
    elif expired is False:
        parts.append(f"It is valid until {expiry_raw}.")
    else:
        parts.append("I could not read a clear expiry date -- please check manually.")
    if mrp:
        parts.append(f"MRP is {mrp} rupees.")

    return MedicineResult(
        ok=True,
        message_en=" ".join(parts),
        drug_name=drug_name,
        expiry_raw=expiry_raw,
        expired=expired,
        mrp=mrp,
    )
