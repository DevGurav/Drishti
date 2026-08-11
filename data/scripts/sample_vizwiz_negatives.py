"""Sample VizWiz photographs to use as currency-mode "no note here" negatives.

Why VizWiz. The `background` class is the weakest part of the currency model: 431 photos of
tables and hands from a single capture session, which do not generalise to anything else a
camera gets pointed at. A medicine strip scores `50` at 0.870, and only the 0.90 threshold
prevents the app announcing money that is not there (`DEC-042`).

VizWiz is thousands of photographs taken *by blind people* of arbitrary objects, in bad
light, half-framed, blurry. That is exactly the distribution a "there is no note here" class
needs, and it was captured by the population the app is for -- which no amount of
photographing one's own kitchen can imitate.

Why this downloads almost nothing
---------------------------------
The image archives are 3.5 GB (val) and 11.3 GB (train), for a few hundred images. The
server supports HTTP range requests, so this reads the zip's central directory and then
fetches only the members it wants -- tens of megabytes rather than eleven gigabytes. Pass
``--zip`` to use an already-downloaded archive instead.

Output goes to ``data/currency_raw/vizwiz_negatives/background/`` so it becomes an ordinary
source for ``merge_currency.py``: deduplicated against everything else, recorded in the
manifest with its licence, and impossible to forget when the corpus is rebuilt.

    python data/scripts/sample_vizwiz_negatives.py --dry-run
    python data/scripts/sample_vizwiz_negatives.py -n 500
"""

from __future__ import annotations

import argparse
import io
import json
import random
import re
import sys
import http.client
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parents[1]
ANNOTATIONS = DATA / "vizwiz"
OUT = DATA / "currency_raw" / "vizwiz_negatives" / "background"
BASE = "https://vizwiz.cs.colorado.edu/VizWiz_final/images"

# Anything that might be money stays out. The cost of dropping a usable photo is nothing --
# there are 20,000 of them -- while the cost of teaching "this is not a note" over an actual
# banknote is a model that declines on real money. Deliberately over-broad: "note" catches
# "notebook" and "note the colour", and that is the right direction to be wrong in.
MONEY = re.compile(
    r"\b("
    r"money|cash|currency|rupee|rupees|paisa|paise|"
    r"note|notes|bill|bills|banknote|"
    r"dollar|dollars|euro|euros|pound|pounds|"
    r"denomination|wallet|purse|change|coin|coins|"
    r"ten|twenty|fifty|hundred|thousand"
    r")\b|₹|\$|€|£",
    re.IGNORECASE,
)


class HttpRangeFile(io.RawIOBase):
    """A seekable read-only file backed by HTTP range requests.

    `zipfile` only needs seek and read, and the archives are served with
    `Accept-Ranges: bytes`, so the whole file never has to be transferred.

    The connection is held open across reads. A first version opened a fresh one per read
    via `urllib`, and managed about six images a minute -- TLS setup dominated, since each
    request moves maybe 100 KB. Reuse turns the cost back into bandwidth.
    """

    def __init__(self, url: str):
        self.url = url
        self._pos = 0
        parts = urllib.parse.urlsplit(url)
        self._host = parts.netloc
        self._path = parts.path + (f"?{parts.query}" if parts.query else "")
        self._connection: http.client.HTTPSConnection | None = None

        response = self._request("HEAD")
        self.size = int(response.headers["Content-Length"])
        response.read()
        if response.headers.get("Accept-Ranges") != "bytes":
            raise SystemExit(
                f"{url} does not advertise range support; download it and pass --zip"
            )

    def _connect(self) -> http.client.HTTPSConnection:
        if self._connection is None:
            self._connection = http.client.HTTPSConnection(self._host, timeout=120)
        return self._connection

    def _request(self, method: str, headers: dict | None = None):
        for attempt in (1, 2):
            try:
                connection = self._connect()
                connection.request(method, self._path, headers=headers or {})
                return connection.getresponse()
            except (http.client.HTTPException, OSError):
                # A kept-alive connection can be closed by the server between reads; drop
                # it and retry once before giving up.
                if self._connection is not None:
                    self._connection.close()
                self._connection = None
                if attempt == 2:
                    raise
        raise AssertionError("unreachable")

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        super().close()

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self.size}[whence]
        self._pos = max(0, min(self.size, base + offset))
        return self._pos

    def readinto(self, buffer) -> int:
        if self._pos >= self.size:
            return 0
        end = min(self._pos + len(buffer) - 1, self.size - 1)
        response = self._request("GET", {"Range": f"bytes={self._pos}-{end}"})
        chunk = response.read()
        buffer[: len(chunk)] = chunk
        self._pos += len(chunk)
        return len(chunk)


def mentions_money(entry: dict) -> bool:
    text = entry.get("question", "")
    text += " " + " ".join(a.get("answer", "") for a in entry.get("answers", []))
    return bool(MONEY.search(text))


def choose(split: str, count: int, seed: int) -> tuple[list[str], int]:
    path = ANNOTATIONS / f"{split}.json"
    if not path.exists():
        raise SystemExit(
            f"{path} not found. Fetch annotations first:\n"
            f"    python data/scripts/download_vizwiz.py"
        )

    entries = json.loads(path.read_text(encoding="utf-8"))
    clean = [e for e in entries if not mentions_money(e)]
    excluded = len(entries) - len(clean)

    rng = random.Random(seed)
    rng.shuffle(clean)
    return [e["image"] for e in clean[:count]], excluded


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--split", default="train", choices=("train", "val"),
                        help="train by default: val is the VQA evaluation set and is left "
                             "alone so nobody has to argue about it later")
    parser.add_argument("-n", "--count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--zip", type=Path, default=None,
                        help="use a local archive instead of ranged HTTP reads")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    wanted, excluded = choose(args.split, args.count, args.seed)
    print(f"{args.split}: {excluded} entries excluded for mentioning money or a "
          f"denomination")
    print(f"selected {len(wanted)} images (seed {args.seed})")

    if args.dry_run:
        for name in wanted[:8]:
            print(f"  {name}")
        print(f"  ... ({len(wanted)} total)\n(dry run -- nothing downloaded)")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    source = args.zip if args.zip else HttpRangeFile(f"{BASE}/{args.split}.zip")
    if args.zip:
        print(f"reading {args.zip}")
    else:
        print(f"reading {BASE}/{args.split}.zip via range requests "
              f"({source.size / 1e9:.1f} GB archive, only the selected members transferred)")

    written = missing = skipped = 0
    with zipfile.ZipFile(io.BufferedReader(source, buffer_size=1 << 20)
                         if not args.zip else args.zip) as archive:
        members = {Path(n).name: n for n in archive.namelist()}
        for name in wanted:
            member = members.get(name)
            if member is None:
                missing += 1
                continue
            target = args.out / name
            if target.exists():
                skipped += 1
                continue
            target.write_bytes(archive.read(member))
            written += 1
            if written % 50 == 0:
                print(f"  {written} written", flush=True)

    print(f"\nwrote {written} images to {args.out}")
    if skipped:
        print(f"  {skipped} already present")
    if missing:
        print(f"  {missing} not found in the archive")
    print("\nVizWiz is CC BY 4.0 -- attribution belongs in the writeup.")
    print("Next: python data/scripts/merge_currency.py --clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
