"""Download an Indian-currency-notes image dataset from Kaggle for the currency-mode
classifier (docs/synopsis.md objective 2: MobileNet CNN, >=99% target accuracy).

We deliberately do NOT hardcode a specific Kaggle dataset slug: several exist with
different licenses, denomination coverage, and quality, and data/README.md already
flags "verify license before use" as a required step. Search Kaggle for e.g.
"indian currency notes classification", pick one, confirm its license permits use in
an academic project (including any images reproduced in your report), then run:

    python data/scripts/download_currency.py --dataset <kaggle-owner>/<dataset-slug>

One-time setup:
  1. pip install kaggle
  2. Kaggle account -> Account settings -> "Create New Token" -> downloads kaggle.json
  3. Place it at ~/.kaggle/kaggle.json (Linux/Mac) or
     C:\\Users\\<you>\\.kaggle\\kaggle.json (Windows)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "currency"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dataset", required=True,
        help="Kaggle dataset ref, e.g. 'someowner/indian-currency-notes'",
    )
    parser.add_argument("--out", type=Path, default=DATA_DIR)
    args = parser.parse_args()

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        print("kaggle package not installed. Run: pip install kaggle", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)

    try:
        api = KaggleApi()
        api.authenticate()
    except Exception as e:
        print(
            f"Kaggle authentication failed ({e}).\n"
            f"Set up ~/.kaggle/kaggle.json first -- see this script's docstring.",
            file=sys.stderr,
        )
        return 1

    print(f"downloading {args.dataset} -> {args.out}")
    api.dataset_download_files(args.dataset, path=str(args.out), unzip=True, quiet=False)
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
