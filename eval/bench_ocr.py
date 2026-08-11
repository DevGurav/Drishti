"""Measure OCR model tiers against latency *and* against still being right.

`RISK-1` is the only high risk left: OCR takes about 56 s per photo against an 8 s target.
`DEC-036` ruled out `max_side` as the lever — 1280 and 1600 are within noise of each other,
so the cost is the pipeline, not the pixels. This measures the tier below the default.

The defaults are heavier than the project's own hardware story admits. English resolves to
`PP-OCRv6_medium_det` / `_medium_rec`, and Devanagari to **`PP-OCRv5_server_det`** — a
server-class detector for an app whose pitch is a ₹10,000 phone.

**Speed alone decides nothing here.** A faster model that loses the expiry date is not a
better model, it is `DEC-030` repeated: a change adopted for a benchmark that costs a blind
user something the benchmark does not measure. So every configuration is checked against
the fields the modes actually need, and a config that drops one is reported as failing no
matter what it did to the clock.

    python eval/bench_ocr.py                 # English tiers on the medicine strip
    python eval/bench_ocr.py --devanagari    # also the Devanagari detector, on newsprint
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from app.engines.paddle_ocr import PaddleOCREngine

ROOT = Path(__file__).resolve().parents[1]
STRIP = ROOT / 'data' / 'samples' / 'strip_paracip.jpg'
NEWSPAPER = ROOT / 'data' / 'samples' / 'newspaper-marathi.png'

# What medicine mode has to read off the strip. Drop any of these and the mode declines or,
# worse, reports a wrong expiry.
STRIP_REQUIRED = {
    'drug name': ('paracetamol', 'paracip'),
    'expiry': ('apr.28', 'apr28', 'apr 28'),
    'MRP': ('10.30',),
}

ENGLISH_TIERS = [
    ('default (v6 medium)', None, None),
    ('v6 small', 'PP-OCRv6_small_det', 'PP-OCRv6_small_rec'),
    ('v6 tiny', 'PP-OCRv6_tiny_det', 'PP-OCRv6_tiny_rec'),
    ('v5 mobile', 'PP-OCRv5_mobile_det', 'PP-OCRv5_mobile_rec'),
    ('v5 mobile det + en rec', 'PP-OCRv5_mobile_det', 'en_PP-OCRv5_mobile_rec'),
]

# Devanagari recognition is already mobile; only the detector is server-class.
DEVANAGARI_TIERS = [
    ('default (v5 server det)', None, None),
    ('v5 mobile det', 'PP-OCRv5_mobile_det', None),
    ('v6 small det', 'PP-OCRv6_small_det', None),
]

DEVANAGARI_RANGE = range(0x0900, 0x0980)


def run_once(image: Path, lang: str, det: str | None, rec: str | None):
    """(load_seconds, read_seconds, text). Load is timed separately: it happens once per
    app start, and folding it into the per-photo figure overstates the steady state."""
    engine = PaddleOCREngine(lang=lang, det_model=det, rec_model=rec)
    t0 = time.time()
    engine._load()
    load_s = time.time() - t0

    t0 = time.time()
    text = engine.read(image)
    read_s = time.time() - t0
    return load_s, read_s, text


def check_strip(text: str) -> tuple[bool, list[str]]:
    lowered = text.lower()
    missing = [name for name, options in STRIP_REQUIRED.items()
               if not any(o in lowered for o in options)]
    return not missing, missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--devanagari', action='store_true',
                        help='also sweep the Devanagari detector on the newspaper fixture')
    parser.add_argument('--image', type=Path, default=STRIP)
    args = parser.parse_args()

    print(f'English tiers on {args.image.name}\n')
    header = f"{'tier':26}{'load':>8}{'read':>8}{'chars':>7}  fields"
    print(header)
    print('-' * len(header))

    baseline = None
    for label, det, rec in ENGLISH_TIERS:
        try:
            load_s, read_s, text = run_once(args.image, 'en', det, rec)
        except Exception as e:
            print(f'{label:26}{"":>8}{"":>8}{"":>7}  FAILED: {type(e).__name__}')
            continue

        ok, missing = check_strip(text)
        baseline = baseline or read_s
        verdict = 'all found' if ok else 'MISSING ' + ', '.join(missing)
        speedup = f'  ({baseline / read_s:.1f}x)' if read_s and baseline else ''
        print(f'{label:26}{load_s:>7.1f}s{read_s:>7.1f}s{len(text):>7}  {verdict}{speedup}')

    if args.devanagari:
        print(f'\n\nDevanagari tiers on {NEWSPAPER.name}\n')
        header = f"{'tier':26}{'load':>8}{'read':>8}{'deva':>7}  verdict"
        print(header)
        print('-' * len(header))
        best = None
        for label, det, rec in DEVANAGARI_TIERS:
            try:
                load_s, read_s, text = run_once(NEWSPAPER, 'mr', det, rec)
            except Exception as e:
                print(f'{label:26}{"":>8}{"":>8}{"":>7}  FAILED: {type(e).__name__}')
                continue
            deva = sum(ord(c) in DEVANAGARI_RANGE for c in text)
            best = best or deva
            share = deva / best if best else 0
            verdict = ('keeps the text' if share > 0.9
                       else f'LOSES TEXT ({share:.0%} of the baseline)')
            print(f'{label:26}{load_s:>7.1f}s{read_s:>7.1f}s{deva:>7}  {verdict}')

    print('\nA tier is only usable if it is both faster and still finds everything.')
    print('Losing a field to save seconds is DEC-030 repeated.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
