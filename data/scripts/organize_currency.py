"""Reshape a flat Kaggle currency dump into the folder-per-class layout ImageFolder needs.

`vishalmane109/indian-currency-note-images-dataset-2020` (CC0-1.0) stores every image in
`Indian currency dataset v1/{training,test,validation}/`, with the denomination encoded in
the *filename* rather than a directory:

    100_15.jpg   100__371.jpg   10__206.jpg   200.__1.jpg   2000__114.jpg

`notebooks/03_currency_classifier.ipynb` calls ``datasets.ImageFolder(DATA_DIR)``, which
takes class names from directory names, so the dump cannot be used as-is.

Why this is a safety-critical script rather than a convenience
-------------------------------------------------------------
A filename parsed wrongly becomes a *training label* that is wrong, and currency mode
exists to stop a blind user being told a Rs 500 note is a Rs 10 note (`DEC-023`). The
separators are inconsistent (``_``, ``__``, ``.__``) and the denominations nest as strings
-- ``20`` inside ``200`` inside ``2000`` -- so a lenient parser can mislabel an entire
class without anything looking wrong. This script therefore:

* takes the **whole leading digit run**, never a prefix match, so ``2000__114`` is 2000 and
  never 200 or 20;
* checks every result against the known denomination set and **refuses to guess**;
* copies nothing at all if anything is unrecognised, unless you pass ``--force``;
* prints a per-class count so a class that silently lost its images is visible before an
  hour of training rather than after.

The splits are merged deliberately. The notebook does its own 70/15/15 ``random_split``
from one ``ImageFolder``, so pre-existing train/test directories would be split *again*.
See the near-duplicate warning it prints -- merging is correct here, but it does mean the
test set can contain near-duplicates of training images, which inflates accuracy.

Usage
-----
    python data/scripts/organize_currency.py --src data/currency_raw --dry-run
    python data/scripts/organize_currency.py --src data/currency_raw
    python data/scripts/organize_currency.py --src data/currency_raw --exclude 2000
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "currency"

# Denominations a user can actually be holding. Rs 1000 and the pre-2016 Rs 500 are
# demonetised and absent from this dataset; Rs 2000 was withdrawn from circulation in
# 2023 but is still legal tender, so it is kept by default -- a model that has never
# seen one will confidently call it something else, which is the worse failure.
KNOWN_DENOMINATIONS = (10, 20, 50, 100, 200, 500, 2000)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

_LEADING_DIGITS = re.compile(r"^(\d+)")


def parse_denomination(filename: str) -> int | None:
    """Denomination from a filename, or None if it is not unambiguously one.

    Takes the entire leading digit run so the string nesting cannot bite:

    >>> parse_denomination('2000__114.jpg')
    2000
    >>> parse_denomination('200.__1.jpg')
    200
    >>> parse_denomination('20__7.jpg')
    20
    >>> parse_denomination('100__389.jpg')
    100

    Anything that is not exactly a known denomination returns None rather than a guess:

    >>> parse_denomination('10023.jpg') is None
    True
    >>> parse_denomination('note_500.jpg') is None
    True
    """
    match = _LEADING_DIGITS.match(filename)
    if not match:
        return None
    value = int(match.group(1))
    return value if value in KNOWN_DENOMINATIONS else None


def collect(src: Path) -> tuple[dict[int, list[Path]], list[Path]]:
    """Group every image under `src` by denomination, and list what could not be parsed."""
    by_denomination: dict[int, list[Path]] = defaultdict(list)
    unrecognised: list[Path] = []

    for path in sorted(src.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        denomination = parse_denomination(path.name)
        if denomination is None:
            unrecognised.append(path)
        else:
            by_denomination[denomination].append(path)

    return dict(by_denomination), unrecognised


def report(by_denomination: dict[int, list[Path]], unrecognised: list[Path]) -> None:
    total = sum(len(v) for v in by_denomination.values())
    print(f"\n{'class':>8} {'images':>8}   share")
    print("-" * 34)
    for denomination in sorted(by_denomination):
        count = len(by_denomination[denomination])
        share = count / total if total else 0
        bar = "#" * round(share * 20)
        print(f"{denomination:>8} {count:>8}   {share:5.1%} {bar}")
    print("-" * 34)
    print(f"{'total':>8} {total:>8}")

    if by_denomination:
        counts = [len(v) for v in by_denomination.values()]
        imbalance = max(counts) / max(min(counts), 1)
        if imbalance > 3:
            print(
                f"\nWARNING: largest class is {imbalance:.1f}x the smallest. Accuracy will "
                f"flatter the common classes.\n         Notebook 03 reports per-class recall "
                f"and rupee-weighted error (DEC-022) -- read those, not the headline number."
            )

    if unrecognised:
        print(f"\n{len(unrecognised)} file(s) could not be assigned a denomination:")
        for path in unrecognised[:15]:
            print(f"  {path.name}")
        if len(unrecognised) > 15:
            print(f"  ... and {len(unrecognised) - 15} more")


def organize(by_denomination: dict[int, list[Path]], out: Path, exclude: set[int]) -> int:
    written = Counter()
    for denomination, paths in sorted(by_denomination.items()):
        if denomination in exclude:
            continue
        class_dir = out / str(denomination)
        class_dir.mkdir(parents=True, exist_ok=True)
        for path in paths:
            # Splits are merged, and 'training/100_15.jpg' and 'test/100_15.jpg' both
            # exist, so the source split is folded into the name to stop one silently
            # overwriting the other -- which would look like a smaller dataset, not a bug.
            target = class_dir / f"{path.parent.name}_{path.name}"
            n = 2
            while target.exists():
                target = class_dir / f"{path.parent.name}_{path.stem}_{n}{path.suffix}"
                n += 1
            shutil.copy2(path, target)
            written[denomination] += 1
    return sum(written.values())


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--src", type=Path, required=True,
                        help="folder the Kaggle zip was extracted into")
    parser.add_argument("--out", type=Path, default=DATA_DIR,
                        help=f"ImageFolder root to create (default: {DATA_DIR})")
    parser.add_argument("--exclude", type=int, nargs="*", default=[],
                        help="denominations to leave out, e.g. --exclude 2000")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be written and change nothing")
    parser.add_argument("--force", action="store_true",
                        help="proceed even when some filenames could not be parsed")
    args = parser.parse_args()

    if not args.src.is_dir():
        print(f"error: --src {args.src} is not a directory", file=sys.stderr)
        return 1

    by_denomination, unrecognised = collect(args.src)
    if not by_denomination:
        print(f"error: no recognisable currency images under {args.src}", file=sys.stderr)
        print("       expected filenames beginning with a denomination, e.g. 500__12.jpg",
              file=sys.stderr)
        return 1

    report(by_denomination, unrecognised)

    missing = [d for d in KNOWN_DENOMINATIONS
               if d not in by_denomination and d not in set(args.exclude)]
    if missing:
        print(f"\nnote: no images found for {missing} -- currency mode cannot identify a "
              f"denomination it was never trained on.")

    if unrecognised and not args.force:
        print("\nRefusing to continue: unparsed filenames usually mean the dataset layout "
              "differs\nfrom the one this script was written for, and a wrong label here "
              "becomes a wrong\ndenomination spoken to someone who cannot check it. "
              "Inspect the list above, then\nre-run with --force if they are genuinely "
              "not currency images.", file=sys.stderr)
        return 1

    if args.dry_run:
        print("\n(dry run -- nothing written)")
        return 0

    total = organize(by_denomination, args.out, set(args.exclude))
    print(f"\nwrote {total} images to {args.out}")
    print(f"point DATA_DIR in notebooks/03_currency_classifier.ipynb at: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
