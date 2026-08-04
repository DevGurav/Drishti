"""Text-parsing building blocks for medicine mode.

The expiry/MRP regexes originated in notebooks/00_feasibility_spike_colab.ipynb (S3)
against real OCR output from a photographed strip. `parse_expiry_date`/`is_expired`
are new: the notebook spike only pulled out date-like substrings, it never parsed
them into an actual date to compare against today.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

_EXPIRY_PAT = re.compile(
    r"(?:EXP|Expiry|Exp\.?)[:\s.]*([A-Z]{3}[.\s/-]?\d{2,4}|\d{1,2}[./-]\d{2,4})", re.I
)
_MRP_PAT = re.compile(r"(?:MRP|Rs\.?|₹)[:\s.]*([\d,.]+)", re.I)

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def extract_expiry_candidates(text: str) -> list[str]:
    return _EXPIRY_PAT.findall(text)


def extract_mrp_candidates(text: str) -> list[str]:
    return _MRP_PAT.findall(text)


def _normalize_year(raw_year: str) -> int:
    year = int(raw_year)
    return 2000 + year if year < 100 else year


def _last_day_of_month(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def parse_expiry_date(raw: str) -> date | None:
    """Parse strip formats like 'MAR2027', 'MAR/27', '03/2027' into the last day of
    that month (strips print month+year, never a day). Returns None if the string
    doesn't match a known format — callers must treat that as 'cannot verify', not
    'not expired'.
    """
    raw = raw.strip().upper()

    m = re.match(r"([A-Z]{3})[.\s/-]?(\d{2,4})", raw)
    if m and m.group(1).lower() in _MONTHS:
        month = _MONTHS[m.group(1).lower()]
        return _last_day_of_month(_normalize_year(m.group(2)), month)

    m = re.match(r"(\d{1,2})[./-](\d{2,4})$", raw)
    if m:
        month = int(m.group(1))
        if 1 <= month <= 12:
            return _last_day_of_month(_normalize_year(m.group(2)), month)

    return None


def is_expired(raw_expiry: str, today: date | None = None) -> bool | None:
    """True/False if determinable, None if the date string couldn't be parsed.
    Medicine mode must treat None as 'cannot verify' — never silently say 'not
    expired' just because parsing failed.
    """
    parsed = parse_expiry_date(raw_expiry)
    if parsed is None:
        return None
    return parsed < (today or date.today())


def earliest_expiry(candidates: list[str]) -> str | None:
    """Pick the earliest parseable expiry from several candidates.

    Indian strips routinely carry more than one date — a carton date and a blister
    date, or the photo catches two panels at once. A real capture of the Paracip strip
    yields both 'OCT.2026' and 'APR.28'. Taking `candidates[0]` means trusting OCR's
    line ordering, which is arbitrary, and on that strip it silently reported the date
    18 months *later* than the true one.

    The earliest date is the only safe reading: the medicine cannot be trusted past it.
    Unparseable strings are ignored here — `is_expired` still reports None for them, so
    'cannot verify' is preserved when nothing parses at all.
    """
    dated = [(parse_expiry_date(c), c) for c in candidates]
    dated = [(d, raw) for d, raw in dated if d is not None]
    if not dated:
        return candidates[0] if candidates else None
    return min(dated, key=lambda pair: pair[0])[1]
