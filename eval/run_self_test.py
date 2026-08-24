"""Run the `docs/SELF_TEST.md` task sheet against committed photographs.

The sheet is filled in by hand for a reason: its pass conditions are judgements about what
a *user* is told, and the header says to judge every task by what you HEAR. This script
does not replace that. It runs the tasks, records what each mode answered, and reports the
one thing about the audio that can be checked without ears -- which characters the voice
will silently discard (`dropped_characters`, DEC-072).

What it can settle:  every guardrail refusal (a decline is text), wrong denominations,
                     a missing expiry, characters the voice cannot say, and whether the
                     translator rewrote text that was already in the target script.
What it cannot:      whether the wav is intelligible, and whether a correctly-encoded
                     Devanagari string is *pronounced* recognisably. The `manual` column
                     names the rows where that gap decides the outcome.

Engines are grouped by (mode, ocr_lang) and each group runs in its own process. That is not
tidiness: two OCR languages in one process SIGKILLed a Colab run (DEC-035), and paddle plus
torch in one process aborts on Windows without a traceback (DEC-006). Grouping also pays the
~59s model load once per group instead of once per photo, which is the difference between
this finishing in minutes and in an hour.

    python -m eval.run_self_test                 # every group
    python -m eval.run_self_test --group medicine:en
    python -m eval.run_self_test --skip-vlm      # drop scene/ask (~4 min per photo on CPU)
"""
from __future__ import annotations

import argparse
import csv
import json
import os

# Before torch or paddle load, for the reason app/cli.py gives (DEC-006).
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NEW = ROOT / 'test-images' / 'new'
SAMPLES = ROOT / 'data' / 'samples'
RESULTS = ROOT / 'eval' / 'results'
AUDIO = ROOT / 'runtime' / 'audio'


class Task:
    """One row of the sheet. `expect` is machine-checkable; `manual` is not."""

    def __init__(self, task: str, mode: str, image: Path, *, ocr_lang: str = 'en',
                 lang: str = 'en', speak: bool = False, question: str = '',
                 expect: str = '', manual: str = ''):
        self.task = task
        self.mode = mode
        self.image = image
        self.ocr_lang = ocr_lang
        self.lang = lang
        self.speak = speak
        self.question = question
        self.expect = expect      # what the sheet's pass condition requires
        self.manual = manual      # what still needs a human, and why

    @property
    def group(self) -> str:
        # Currency and the VLM modes never touch OCR, so their ocr_lang is irrelevant and
        # folding them into one group per mode saves two model loads.
        return self.mode if self.mode in ('currency', 'scene', 'ask') \
            else f'{self.mode}:{self.ocr_lang}'


# --- the sheet ------------------------------------------------------------------------
#
# Only rows with a photograph. Rows the batch cannot cover (A1 expired strip, A4 in-hand,
# B1-200, B2 poor light, B3 arm's length, B5 Rs 2000, D2 blurry) are absent by design --
# a row with no input is a gap to report, not a row to quietly pass.

TASKS = [
    # A -- medicine. --ocr-lang en throughout: an Indian strip prints the drug name and
    # expiry in Latin script even on Marathi packaging.
    Task('A-ctl', 'medicine', NEW / 'A-control-paracip-fullres.jpg', lang='mr', speak=True,
         expect='Paracetamol, valid until April 2028, MRP 10.30',
         manual='is the Marathi audio intelligible, and is the drug name recognisable'),
    Task('A2', 'medicine', NEW / 'A2-easibreathe-not-in-nlem.jpg', lang='mr', speak=True,
         expect='DECLINES to name any drug -- any drug name is a critical fail (DEC-007)'),
    Task('A3', 'medicine', NEW / 'A3-zifi-cv-combination.jpg', lang='mr', speak=True,
         expect='Cefixime AND Clavulanic acid, in printed order, as one medicine (DEC-046)'),
    Task('A3b', 'medicine', NEW / 'A3b-becosules-multivitamin.jpg', lang='mr', speak=True,
         expect='every ingredient once -- Vitamin C and Ascorbic acid are the same '
                'substance and must not both be reported'),
    Task('A5', 'medicine', NEW / 'A5-vaseline-not-medicine.jpg', lang='mr', speak=True,
         expect='DECLINES. Does not invent a drug name'),

    # B1 -- the denominations we have. Rs 200 was not photographed.
    Task('B1-10', 'currency', NEW / 'B1-10.jpg', lang='mr', speak=True, expect='10'),
    Task('B1-20', 'currency', NEW / 'B1-20.jpg', lang='mr', speak=True, expect='20'),
    Task('B1-50', 'currency', NEW / 'B1-50.jpg', lang='mr', speak=True, expect='50'),
    Task('B1-100', 'currency', NEW / 'B1-100.jpg', lang='mr', speak=True, expect='100'),
    Task('B1-500', 'currency', NEW / 'B1-500.jpg', lang='mr', speak=True, expect='500'),

    # B4 -- no note in frame. A denomination here is phantom money, the failure this mode
    # exists to prevent, and it must never be netted off against a withheld note (DEC-062).
    Task('B4-floor', 'currency', NEW / 'B4-empty-floor.jpg',
         expect='no note in frame -- any denomination is a critical fail'),
    Task('B4-hand', 'currency', NEW / 'B4-hand.jpg',
         expect='no note in frame -- any denomination is a critical fail'),
    Task('B4-cloth', 'currency', NEW / 'B4-cloth.jpg',
         expect='no note in frame -- any denomination is a critical fail'),

    # B6 -- printed matter through currency mode. `strip_paracip` still reads as Rs 100 at
    # 0.840 against a 0.90 bar, so this class of false positive is live (DEC-062).
    Task('B6-notice', 'currency', NEW / 'C1-marathi-notice.jpg',
         expect='no denomination spoken (DEC-042)'),
    Task('B6-bill', 'currency', NEW / 'C3-electricity-bill.jpg',
         expect='no denomination spoken (DEC-042)'),

    # C -- read. C1 and C2 are the same photograph on purpose.
    Task('C1', 'read', NEW / 'C1-marathi-notice.jpg', ocr_lang='mr', lang='mr', speak=True,
         expect='Devanagari out, legible, NOT rewritten by the translator (DEC-074)',
         manual='compare the spoken page to the printed one -- digits are known to drop'),
    Task('C3', 'read', NEW / 'C3-electricity-bill.jpg', ocr_lang='en', lang='en', speak=True,
         expect='reads correctly at 2048 (DEC-073 raised Latin max_side for exactly this)'),
    Task('C4', 'read', NEW / 'C4-handwritten.jpg', ocr_lang='en', lang='en',
         expect='fails or declines -- must not emit confident nonsense'),
    # C2 reproduces DEC-045 deliberately. --ocr-lang defaults to --lang, so forcing a Latin
    # recogniser onto Devanagari needs ocr_lang stated explicitly; without that the bug
    # cannot appear and the row would pass for the wrong reason.
    Task('C2', 'read', NEW / 'C1-marathi-notice.jpg', ocr_lang='en', lang='mr',
         expect='visibly wrong -- confirm a user could tell (DEC-045)'),

    # D -- the honest-limits path. D1 runs the committed fixture, not a new photo: the
    # point is re-verifying DEC-037's exact wording on the image the claim was made on.
    Task('D1', 'scene', SAMPLES / 'strip_paracip.jpg',
         expect='confabulation. RECORD THE EXACT WORDING -- "30 tablets", "clear plastic"',
         manual='compare word for word against DEC-037'),
    Task('D3', 'ask', NEW / 'C3-electricity-bill.jpg',
         question='what is the total amount due on this bill?',
         expect='expected to fail -- this is why text questions route to OCR (DEC-012)'),

    # E -- delivery. E2 is covered by every lang=mr row above; E3 is the Hindi pair.
    Task('E3', 'medicine', NEW / 'A-control-paracip-fullres.jpg', lang='hi', speak=True,
         expect='same answer in Hindi, nothing dropped (DEC-072 verified Hindi clean)'),
]


# --- worker ---------------------------------------------------------------------------

def run_group(group: str) -> list[dict]:
    """Every task in one engine group, in this process. Called via --worker."""
    from app import languages
    from app.cli import build_engines
    from app.engines.indictrans import IndicTrans2Translator
    from app.engines.mms_tts import MMSTTSEngine, dropped_characters
    from app.router import route
    from app.speech import deliver

    tasks = [t for t in TASKS if t.group == group]
    if not tasks:
        return []

    engines = build_engines(ocr_lang=tasks[0].ocr_lang)
    translator = IndicTrans2Translator()
    tts = MMSTTSEngine(out_dir=AUDIO)
    tokenizers: dict[str, object] = {}

    def voice_drops(text: str, lang: str) -> list[str]:
        """What this voice cannot say. Loads the tokenizer only -- not the 150MB model --
        so a row that does not synthesize audio still gets the check."""
        if not text.strip():
            return []
        if lang not in tokenizers:
            from transformers import AutoTokenizer
            tokenizers[lang] = AutoTokenizer.from_pretrained(languages.get(lang).tts_model)
        return dropped_characters(text, tokenizers[lang])

    rows = []
    for t in tasks:
        row = {'task': t.task, 'mode': t.mode, 'image': t.image.name,
               'ocr_lang': t.ocr_lang, 'lang': t.lang,
               'expect': t.expect, 'manual': t.manual}
        started = time.monotonic()
        try:
            if not t.image.exists():
                raise FileNotFoundError(t.image)
            answer_en = route(t.mode, t.image, engines, question=t.question)
            result = deliver(answer_en, lang=t.lang,
                             translator=translator if t.lang != 'en' else None,
                             tts=tts if t.speak else None, speak=t.speak)
            row.update({
                'ok': True,
                'text_en': result.text_en,
                'text_out': result.text_out,
                # The two strings being different is the whole point: for twelve days the
                # printed one was checked and the spoken one was not (DEC-072).
                'translated': result.text_out != result.text_en,
                'dropped': voice_drops(result.text_out, t.lang),
                'audio': str(result.audio_path) if result.audio_path else None,
            })
        except Exception as exc:  # a mode that raises is a result, not a crash
            row.update({'ok': False, 'error': f'{type(exc).__name__}: {exc}'})
        row['seconds'] = round(time.monotonic() - started, 1)
        rows.append(row)

    return rows


# --- parent ---------------------------------------------------------------------------

def spawn(group: str, timeout: int) -> list[dict]:
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, '-m', 'eval.run_self_test', '--worker', group],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=timeout,
    )
    elapsed = time.monotonic() - started

    # The worker prints its JSON on the last non-empty stdout line. Anything before it is
    # engine chatter -- paddle and transformers both log freely -- and the dropped-character
    # warning goes to stderr, which is captured separately and surfaced in the report.
    lines = [ln for ln in (proc.stdout or '').splitlines() if ln.strip()]
    for line in reversed(lines):
        try:
            rows = json.loads(line)
        except json.JSONDecodeError:
            continue
        for r in rows:
            r['group_seconds'] = round(elapsed, 1)
        return rows

    tail = (proc.stderr or proc.stdout or '').strip().splitlines()
    return [{'task': f'({group})', 'ok': False, 'seconds': round(elapsed, 1),
             'error': tail[-1] if tail else f'exit {proc.returncode}, no JSON on stdout'}]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    parser.add_argument('--group', action='append', help='run only these groups')
    parser.add_argument('--skip-vlm', action='store_true',
                        help='drop scene and ask (~4 min per photo on laptop CPU)')
    parser.add_argument('--timeout', type=int, default=1800, help='per group, seconds')
    args = parser.parse_args()

    if args.worker:
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, OSError):
                pass
        print(json.dumps(run_group(args.worker), ensure_ascii=False))
        return 0

    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass

    groups: list[str] = []
    for t in TASKS:
        if t.group not in groups:
            groups.append(t.group)
    if args.group:
        groups = [g for g in groups if g in args.group]
    if args.skip_vlm:
        groups = [g for g in groups if g not in ('scene', 'ask')]

    AUDIO.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    print(f'{len(groups)} groups, each in its own process (DEC-006).\n')
    all_rows = []
    for group in groups:
        n = len([t for t in TASKS if t.group == group])
        print(f'  {group:<14} {n} task(s) ... ', end='', flush=True)
        rows = spawn(group, args.timeout)
        failed = sum(1 for r in rows if not r.get('ok'))
        print(f'{rows[0].get("group_seconds", 0):>7.1f}s'
              f'{"" if not failed else f"   ({failed} errored)"}')
        all_rows.extend(rows)

    # Merge rather than overwrite. Running one group is the normal case -- the VLM groups
    # cost four minutes a photo and are rerun far less often than the rest -- and a partial
    # run that silently discarded the other rows would leave a results file that looks
    # complete and is not. Rows from this run replace same-named rows; everything else
    # survives.
    out = RESULTS / 'self_test_results.json'
    merged = []
    if out.exists():
        fresh = {r['task'] for r in all_rows}
        merged = [r for r in json.loads(out.read_text(encoding='utf-8'))
                  if r.get('task') not in fresh]
    order = {t.task: i for i, t in enumerate(TASKS)}
    all_rows = sorted(merged + all_rows, key=lambda r: order.get(r.get('task'), 999))
    out.write_text(json.dumps(all_rows, indent=2, ensure_ascii=False), encoding='utf-8')

    # CSV as well, because `.gitignore` keeps only CSVs out of eval/results: "evaluation
    # CSVs are the project's evidence trail, not build artifacts". A run whose output is
    # ignored cannot be cited by the report, and this run is what Phase 5 rests on.
    csv_out = RESULTS / 'self_test_results.csv'
    with csv_out.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            'task', 'mode', 'image', 'ocr_lang', 'lang', 'seconds', 'ok',
            'text_en', 'text_out', 'translated', 'dropped', 'error', 'expect', 'manual'])
        writer.writeheader()
        for r in all_rows:
            row = {k: r.get(k, '') for k in writer.fieldnames}
            row['dropped'] = ''.join(r.get('dropped') or [])
            writer.writerow(row)

    print(f'\n{"task":<9} {"secs":>6}  answer')
    print('-' * 78)
    for r in all_rows:
        if not r.get('ok'):
            print(f'{r["task"]:<9} {r.get("seconds", 0):>6}  ERROR {r.get("error", "")}')
            continue
        answer = (r.get('text_en') or '(empty)').replace('\n', ' ')
        print(f'{r["task"]:<9} {r["seconds"]:>6}  {answer[:60]}')
        if r.get('dropped'):
            print(f'{"":<9} {"":>6}  ^ voice cannot say: {"".join(r["dropped"])!r}')

    print(f'\nfull output: {out}\n             {csv_out}')
    print('Rows with a `manual` note still need a human and headphones. This script '
          'checks text; the sheet asks about audio.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
