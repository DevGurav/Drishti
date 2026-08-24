"""Run the committed image fixtures through currency mode and print what a user would get.

`data/samples/README.md` says "re-run them after every retrain, and report them beside the
benchmark rather than underneath it" (DEC-052). That instruction had no command attached, so
the numbers in that README drifted a full model generation behind the checkpoint: it still
quoted the 8-class figures (Rs 200 at 0.926, "all five answer") after the 7-class retrain
moved them (DEC-062). This script is that command.

Why fixtures rather than the test split: they are the only images in the project drawn from
deployment rather than from the training distribution. Five of them caught a regression that
840 test images could not (DEC-052), and they are the check that a *benchmark* improvement
did not cost real-photo behaviour.

Two numbers are printed for every image, because they answer different questions:

  * top-1 and its confidence -- what the model believes
  * the spoken answer -- what the user is actually told, after
    app/modes/currency.py applies CONFIDENCE_THRESHOLD

A note that is predicted correctly but withheld is not a misread; it costs a retaken photo.
A non-note image that returns a denomination is the failure this mode exists to prevent, and
the two must never be netted off against each other (DEC-062).

    python -m eval.check_fixtures
    python -m eval.check_fixtures --json    # machine-readable, for a results file
"""
from __future__ import annotations

import argparse
import json
import os

# Before torch loads, for the same reason app/cli.py does it (DEC-006).
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

from app.engines.currency_cnn import CurrencyClassifier  # noqa: E402
from app.modes import currency  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[1] / 'data' / 'samples'

# What each fixture is, and what it *should* do. `expect` is the denomination the model
# ought to predict; None means "no note in frame", where the only correct outcome is a
# refusal -- either the background class or a sub-threshold confidence.
FIXTURES = [
    ('curr-10.jpg', '10', 'handheld Rs 10, worn, on concrete'),
    ('curr-50.jpg', '50', 'handheld Rs 50, wide framing (aspect 2.0)'),
    ('curr-100.jpg', '100', 'handheld Rs 100, tight framing'),
    ('curr-200.jpg', '200', 'handheld Rs 200 on cloth, sideways, aspect 2.1 - the hardest'),
    ('curr-500.jpg', '500', 'handheld Rs 500, slight fold, on concrete'),
    # Added 2026-08-24 from the Phase-5 batch, and only meaningful as a pair. The note is
    # predicted correctly and withheld at 0.765; the towel is predicted Rs 20 at 0.804.
    # **The cloth is a more confident twenty-rupee note than the twenty-rupee note is.**
    # Neither is spoken, so neither is a user-visible failure today -- but the ordering
    # says the margin protecting DEC-062 is luck rather than separation, and a threshold
    # lowered to answer the note would ship the towel first.
    ('curr-20-withheld.jpg', '20', 'flat Rs 20, even light - correct at 0.765, below the bar'),
    ('cloth-pink-towel.jpg', None, 'folded towel - predicts Rs 20 at 0.804, ABOVE the note'),
    ('strip_paracip.jpg', None, 'medicine strip - no note present'),
    ('strip_partial.jpg', None, 'medicine strip - no note present'),
    ('newspaper-marathi.png', None, 'Marathi newspaper - no note present'),
]


def check_one(classifier: CurrencyClassifier, name: str, expect: str | None) -> dict:
    path = SAMPLES / name
    if not path.exists():
        return {'file': name, 'error': 'missing'}

    label, confidence = classifier.classify(path)
    spoken = currency.run(path, classifier)
    answered = spoken.startswith('This is a')

    if expect is None:
        # A refusal is the only correct outcome. Which refusal matters: the background
        # class means "reframe", a low confidence means "better light" -- and a confident
        # denomination here is phantom money, the expensive failure.
        ok = not answered
    else:
        ok = answered and label == expect

    return {
        'file': name,
        'expect': expect,
        'top1': label,
        'confidence': round(confidence, 3),
        'answered': answered,
        'spoken': spoken,
        'ok': ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--json', action='store_true', help='emit JSON instead of a table')
    args = parser.parse_args()

    classifier = CurrencyClassifier()
    rows = [check_one(classifier, name, expect) for name, expect, _ in FIXTURES]

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0 if all(r.get('ok') for r in rows) else 1

    print(f'threshold: {currency.CONFIDENCE_THRESHOLD}   '
          f'classes: {", ".join(classifier.classes)}\n')

    notes = [r for r in rows if r.get('expect') is not None]
    blanks = [r for r in rows if r.get('expect') is None]

    print(f'{"file":<22} {"top-1":>6} {"conf":>6}  {"answered":<9} outcome')
    print('-' * 72)
    for group, title in ((notes, 'real notes'), (blanks, 'no note in frame')):
        print(f'  -- {title} --')
        for r in group:
            if r.get('error'):
                print(f'{r["file"]:<22} {"MISSING":>13}')
                continue
            mark = 'ok' if r['ok'] else 'FAIL'
            print(f'{r["file"]:<22} {r["top1"]:>6} {r["confidence"]:>6.3f}  '
                  f'{str(r["answered"]):<9} {mark}')

    answered_notes = sum(1 for r in notes if r['answered'] and r['ok'])
    refused_blanks = sum(1 for r in blanks if not r['answered'])
    print('-' * 72)
    print(f'real notes answered correctly : {answered_notes} of {len(notes)}')
    print(f'non-notes correctly refused   : {refused_blanks} of {len(blanks)}')

    # The margin that actually matters: how close the worst false positive is to the bar.
    # DEC-062 put it at 0.06 and called that thinness the number to watch.
    #
    # Only a non-note predicted as a *denomination* counts. A high-confidence `background`
    # is the model getting it right, and scoring it as a near-miss inverts the meaning --
    # the first version of this script did exactly that and named the newspaper (background
    # at 0.901) as the worst offender, when it is the best-behaved image in the set.
    # Confidence is only comparable between predictions that mean the same thing.
    false_positives = [r for r in blanks
                       if not r.get('error') and r['top1'] != currency.BACKGROUND_LABEL]
    worst = max(false_positives, key=lambda r: r['confidence'], default=None)
    if worst:
        margin = currency.CONFIDENCE_THRESHOLD - worst['confidence']
        print(f'worst false positive          : {worst["file"]} -> Rs {worst["top1"]} at '
              f'{worst["confidence"]:.3f}, {margin:+.3f} of headroom')
        if margin < 0.10:
            print('  NOTE: under 0.10 of headroom. Do not lower CONFIDENCE_THRESHOLD to '
                  'rescue a withheld note -- that would ship this false positive '
                  '(DEC-062).')
    else:
        print('worst false positive          : none - every non-note returned background')

    return 0 if all(r.get('ok') for r in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
