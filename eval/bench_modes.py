"""Per-mode end-to-end latency on this laptop — the measurement RISK-1 is waiting on.

`DEC-038` sets the bar at **<8s from shutter to spoken answer** on laptop CPU, because
that is the live-demo path. RISK-1 has been red since 2026-08-10 against numbers measured
*before* `DEC-058` cut the Latin OCR path from 41.2s to 12.9s, so the risk is currently
tracking a figure that no longer describes the code.

Three things this reports that a single stopwatch number would hide:

- **Model load is separated from inference.** Load happens once per session; a user
  photographing three things pays it once and the per-photo cost three times. Folding
  them together makes the first photo look representative when it is the outlier.
- **Translation and speech are timed separately from vision.** They are the same cost for
  every mode, so if they dominate, the answer is to fix them once rather than to optimise
  five modes.
- **English and Marathi are both measured.** The demo is in Marathi, and Devanagari OCR
  runs a server-class detector because every lighter one read zero characters
  (`DEC-058`) — reporting only the English path would flatter the result by design.

Scene and ask run the VLM on CPU and take minutes, not seconds. They are included because
leaving them out would be choosing the flattering subset; `--skip-vlm` exists for a quick
pass while iterating, not for the number that goes in the writeup.

    python eval/bench_modes.py
    python eval/bench_modes.py --skip-vlm
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SAMPLES = ROOT / 'data' / 'samples'
OUT_CSV = ROOT / 'eval' / 'results' / 'mode_latency.csv'
TARGET_S = 8.0

# (mode, image, ocr_lang, question). The VLM does not care what the photograph shows for
# timing purposes -- cost is driven by tiling and resolution -- so an existing fixture is
# a fair stand-in for a scene, and noting that is better than quietly omitting the mode.
CASES = [
    ('currency', 'curr-500.jpg', 'en', ''),
    ('medicine', 'strip_paracip.jpg', 'en', ''),
    ('read', 'strip_paracip.jpg', 'en', ''),
    ('read-mr', 'newspaper-marathi.png', 'mr', ''),
    ('scene', 'curr-500.jpg', 'en', ''),
    ('ask', 'curr-500.jpg', 'en', 'What is in front of me?'),
]
VLM_MODES = {'scene', 'ask'}


@dataclass
class Row:
    mode: str
    load_s: float = 0.0
    infer_s: float = 0.0
    translate_s: float = 0.0
    tts_s: float = 0.0
    answer: str = ''
    notes: list[str] = field(default_factory=list)

    @property
    def per_photo_s(self) -> float:
        """What the *second* photo costs. Model load is excluded deliberately: it is paid
        once per session, and charging it to every photo overstates steady-state use."""
        return self.infer_s + self.translate_s + self.tts_s

    @property
    def first_photo_s(self) -> float:
        return self.load_s + self.per_photo_s


def timed(fn):
    t0 = time.perf_counter()
    value = fn()
    return value, time.perf_counter() - t0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--skip-vlm', action='store_true',
                    help='skip scene and ask (minutes each on CPU)')
    ap.add_argument('--lang', default='mr',
                    help="delivery language for the translate+TTS legs (default: the "
                         "demo language, mr)")
    args = ap.parse_args()

    from app import languages
    from app.cli import build_engines
    from app.router import route
    from app.engines.indictrans import IndicTrans2Translator
    from app.engines.mms_tts import MMSTTSEngine
    from app.speech import deliver

    cases = [c for c in CASES if not (args.skip_vlm and c[0].split('-')[0] in VLM_MODES)]
    missing = [img for _, img, _, _ in cases if not (SAMPLES / img).exists()]
    if missing:
        print(f'missing fixtures: {sorted(set(missing))}', file=sys.stderr)
        return 1

    print(f'laptop CPU · target <{TARGET_S:.0f}s per photo · delivery language '
          f'{args.lang}\n')

    rows: list[Row] = []
    for mode, image, ocr_lang, question in cases:
        base = mode.split('-')[0]
        row = Row(mode=mode)
        path = SAMPLES / image
        engines = build_engines(ocr_lang=ocr_lang)

        # First call pays the model load; the second is the steady-state cost. Both are
        # reported rather than averaged, because they answer different questions.
        _, cold = timed(lambda: route(base, path, engines, question=question))
        answer, warm = timed(lambda: route(base, path, engines, question=question))
        row.load_s = max(cold - warm, 0.0)
        row.infer_s = warm
        row.answer = str(answer)[:70].replace('\n', ' ')

        if args.lang != 'en':
            translator = IndicTrans2Translator()
            _, _ = timed(lambda: deliver(row.answer, lang=args.lang,
                                         translator=translator, tts=None, speak=False))
            _, row.translate_s = timed(
                lambda: deliver(row.answer, lang=args.lang, translator=translator,
                                tts=None, speak=False))

        tts = MMSTTSEngine(out_dir=ROOT / 'runtime' / 'audio')
        try:
            _, _ = timed(lambda: deliver(row.answer, lang=args.lang, translator=None,
                                         tts=tts, speak=True))
            _, row.tts_s = timed(
                lambda: deliver(row.answer, lang=args.lang, translator=None,
                                tts=tts, speak=True))
        except Exception as exc:                       # noqa: BLE001
            row.notes.append(f'tts unavailable: {type(exc).__name__}')

        rows.append(row)
        verdict = 'PASS' if row.per_photo_s < TARGET_S else 'over'
        print(f'{mode:10} load {row.load_s:7.1f}s  infer {row.infer_s:7.1f}s  '
              f'translate {row.translate_s:5.1f}s  tts {row.tts_s:5.1f}s  '
              f'-> {row.per_photo_s:7.1f}s per photo  [{verdict}]', flush=True)

    print(f'\n{"mode":10}{"1st photo":>12}{"per photo":>12}{"vs target":>12}')
    print('-' * 46)
    for r in rows:
        print(f'{r.mode:10}{r.first_photo_s:>11.1f}s{r.per_photo_s:>11.1f}s'
              f'{r.per_photo_s / TARGET_S:>11.1f}x')

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['mode', 'load_s', 'infer_s', 'translate_s', 'tts_s',
                    'per_photo_s', 'first_photo_s', 'target_s', 'answer', 'notes'])
        for r in rows:
            w.writerow([r.mode, f'{r.load_s:.2f}', f'{r.infer_s:.2f}',
                        f'{r.translate_s:.2f}', f'{r.tts_s:.2f}',
                        f'{r.per_photo_s:.2f}', f'{r.first_photo_s:.2f}',
                        TARGET_S, r.answer, '; '.join(r.notes)])
    print(f'\nwrote {OUT_CSV}')

    passing = [r.mode for r in rows if r.per_photo_s < TARGET_S]
    print(f'{len(passing)} of {len(rows)} modes under {TARGET_S:.0f}s: '
          f'{", ".join(passing) or "none"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
