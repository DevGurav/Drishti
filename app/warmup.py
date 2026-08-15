"""Pre-demo preflight: load every model once, so nothing downloads or cold-starts on the day.

`docs/DEMO.md` lists four commands to run the day before. This is those commands with a
verdict attached -- it reports which stage failed and how long each took, rather than
leaving four terminal scrollbacks to read.

**Every stage runs as its own subprocess, deliberately.** PyTorch and PaddlePaddle each
bundle an OpenMP runtime and co-loading them aborts the process with no traceback
(DEC-006, DEC-027), and each OCR *language* is a full pipeline -- holding English open while
loading Marathi passed 3.9 GB of 10.8 GB and was SIGKILLed (DEC-035). A single-process
warmup would therefore crash on exactly the machine it is meant to protect. Subprocesses
also mean a stage that dies reports an exit code instead of taking the whole run with it.

The model load is ~59s and is paid once per session, not once per photo, so a warm machine
is the difference between a demo that answers in seconds and one that appears to hang
(DEC-038). Run this the day before *and* again shortly before the demo.

    python -m app.warmup              # all stages
    python -m app.warmup --quick      # skip the VLM, which is ~4 minutes on CPU

Note on timings: these are warm-cache numbers on a cool machine. Sustained load raises
per-photo cost by 55-120% as the laptop throttles (DEC-066), so a slow figure here after a
long working session is thermal, not a regression.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / 'data' / 'samples'

# (label, cli args, per-photo cost, skip when --quick). Ordered cheapest first so a broken
# install is reported in seconds rather than after the VLM has spent four minutes.
#
# The third field is `eval/bench_modes.py`'s figure, which **excludes model load** because
# that is paid once a session rather than once a photo (DEC-066). Every stage here is a cold
# process and pays it, so these timings are *expected* to exceed the per-photo cost -- by
# roughly the load time, which is up to ~59s. Printed side by side only so the gap is
# visible as startup rather than misread as a regression; the point of this script is that
# the second run of any mode is the fast one.
STAGES: list[tuple[str, list[str], str, bool]] = [
    ('currency', ['--mode', 'currency', '--image', str(SAMPLES / 'curr-500.jpg')],
     '1-2s', False),
    ('medicine (OCR en)', ['--mode', 'medicine', '--image', str(SAMPLES / 'strip_paracip.jpg'),
                           '--ocr-lang', 'en'], '19-30s', False),
    ('medicine + Marathi speech', ['--mode', 'medicine', '--image', str(SAMPLES / 'strip_paracip.jpg'),
                                   '--ocr-lang', 'en', '--lang', 'mr', '--speak'],
     '30-45s', False),
    ('read Devanagari (OCR mr)', ['--mode', 'read', '--image', str(SAMPLES / 'newspaper-marathi.png'),
                                  '--ocr-lang', 'mr'], '76-83s', False),
    ('scene (VLM)', ['--mode', 'scene', '--image', str(SAMPLES / 'curr-500.jpg')],
     '~245s', True),
]


def run_stage(label: str, args: list[str], expected: str) -> tuple[bool, float, str]:
    """One CLI invocation in a clean process. Returns (ok, seconds, last output line)."""
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, '-m', 'app.cli', *args],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace',
    )
    elapsed = time.monotonic() - started

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or '').strip().splitlines()
        return False, elapsed, tail[-1] if tail else f'exit {proc.returncode}'

    lines = [ln for ln in (proc.stdout or '').strip().splitlines() if ln.strip()]
    return True, elapsed, lines[0] if lines else '(no output)'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--quick', action='store_true',
                        help='skip the VLM stage (~4 minutes on laptop CPU)')
    args = parser.parse_args()

    stages = [s for s in STAGES if not (args.quick and s[3])]
    print(f'Warming {len(stages)} stages. Each runs in its own process (DEC-006).\n')

    failures = []
    total = 0.0
    for label, cli_args, expected, _ in stages:
        print(f'  {label:<28} ... ', end='', flush=True)
        ok, elapsed, detail = run_stage(label, cli_args, expected)
        total += elapsed
        if ok:
            print(f'{elapsed:6.1f}s  (per-photo once warm: {expected})')
        else:
            print(f'{elapsed:6.1f}s  FAILED')
            print(f'      {detail}')
            failures.append(label)

    print(f'\ntotal {total:.1f}s')

    if failures:
        print(f'\nFAILED: {", ".join(failures)}')
        print('Fix before the demo. docs/DEMO.md has the fallbacks for each mode.')
        return 1

    print('\nAll stages warm. Two things DEMO.md asks for that this cannot do:')
    print('  - turn aeroplane mode on, and leave it on')
    print('  - start from a cool machine (throttling costs 55-120%, DEC-066)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
