"""Merge several public Indian-currency datasets into one deduplicated training corpus.

Why merge at all: the model trained on a single source scores 0.9883 on that source's own
test split and cleared the confidence threshold on only 3 of 5 real handheld notes
(`DEC-043`). The images in that dataset are all cropped tight to the note. Independent
datasets were shot by different contributors, at different distances, on different
surfaces -- which is the capture diversity the model is missing, obtainable without a
camera (`DEC-047`).

Three things this script refuses to do quietly
----------------------------------------------
**Merge a source whose licence it does not know.** `DEC-022` requires a licence permitting
use. A source not listed in ``SOURCES`` is refused rather than assumed fine, because the
consequence of getting it wrong lands in a public writeup.

**Guess a class from a folder name.** `pypiahmad` ships Thai baht alongside rupees, so a
directory called ``20 Baht`` would parse as ₹20 under any digit-scraping rule and label
Thai money as Indian. Folder names must match a known denomination exactly, or the source
needs an explicit ``class_map``; anything else stops the merge.

**Silently keep duplicates.** These datasets re-host each other. A duplicate spanning the
train and test splits makes the accuracy number fiction, and that number is the one the
whole evaluation rests on. Exact duplicates are found by SHA-256, near-duplicates by
perceptual hash.

Usage
-----
    python data/scripts/merge_currency.py --dry-run
    python data/scripts/merge_currency.py
    python data/scripts/merge_currency.py --near-threshold 6      # more aggressive

Each source lives in its own directory under ``--raw``, named for its Kaggle owner:

    data/currency_raw/vishalmane109/...
    data/currency_raw/gauravsahani/...
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from organize_currency import (  # noqa: E402
    BACKGROUND_CLASS,
    IMAGE_SUFFIXES,
    KNOWN_DENOMINATIONS,
    parse_class,
    sort_key,
)

DATA = Path(__file__).resolve().parents[1]
RAW_DIR = DATA / "currency_raw"
OUT_DIR = DATA / "currency"
MANIFEST = DATA / "currency_manifest.csv"


@dataclass(frozen=True)
class Source:
    """A dataset we are allowed to use, and how to read its labels.

    `priority` decides which copy survives deduplication. Lower wins. The most permissive
    licence goes first so the surviving corpus is as unencumbered as possible -- a CC0
    image and a CC BY image of the same note are interchangeable for training, but only one
    of them obliges the writeup to carry an attribution line.
    """

    slug: str
    licence: str
    priority: int
    attribution_required: bool = False
    # Explicit folder-name -> class mapping, for sources that need one (mixed currencies,
    # unusual naming). Empty means: folder names must already be exact class names.
    class_map: dict[str, str] = field(default_factory=dict)
    note: str = ""


SOURCES: dict[str, Source] = {
    "vishalmane109": Source(
        slug="vishalmane109", licence="CC0-1.0", priority=0,
        note="indian-currency-note-images-dataset-2020; flat files, denomination in filename",
    ),
    "yashdogra": Source(
        slug="yashdogra", licence="Apache-2.0", priority=1,
        note="2000-notes; single denomination",
    ),
    "gauravsahani": Source(
        slug="gauravsahani", licence="DbCL-1.0", priority=2,
        note="indian-currency-notes-classifier; folders spell the denomination in words",
        # Digit-scraping these would be a catastrophe rather than a near miss:
        # '1Hundrednote' -> 1, '2Hundrednote' -> 2, '2Thousandnote' -> 2. Three
        # denominations destroyed, and 'Fiftynote' has no digits at all.
        class_map={
            "tennote": "10",
            "twentynote": "20",
            "fiftynote": "50",
            "1hundrednote": "100",
            "2hundrednote": "200",
            "5hundrednote": "500",
            "2thousandnote": "2000",
        },
    ),
    "pypiahmad": Source(
        slug="pypiahmad", licence="CC BY 4.0", priority=3, attribution_required=True,
        note="indian-rupees-and-thai-baht-banknotes; rupee classes only",
        # THAI20, THAI50, THAI500 would land directly on rupee classes under any digit
        # rule -- a 20-baht note taught as a Rs 20 note. Mapped to None, which excludes
        # them explicitly rather than relying on them being skipped by accident.
        #
        # NEW/OLD are the pre- and post-2016 designs of the same denomination. Both map to
        # the denomination: the user wants to know what it is worth, and carrying both
        # designs is exactly the intra-class variety a single-source corpus lacks.
        class_map={
            "india10new": "10", "india10old": "10",
            "india20": "20",
            "india50new": "50", "india50old": "50",
            "india100new": "100", "india100old": "100",
            "india200": "200",
            "india500": "500",
            "india2000": "2000",
            "thai20": "", "thai50": "", "thai100": "", "thai500": "", "thai1000": "",
        },
    ),
    "vizwiz_negatives": Source(
        slug="vizwiz_negatives", licence="CC BY 4.0", priority=4, attribution_required=True,
        note="VizWiz-VQA photographs used only as 'no note in frame' negatives; "
             "produced by data/scripts/sample_vizwiz_negatives.py",
        # Lowest priority deliberately. If a VizWiz photo somehow duplicates a currency
        # image from another source, the currency label is the one to keep -- a real note
        # mislabelled 'background' teaches the model to decline on money, which is the
        # failure this class exists to prevent, pointed the wrong way.
        class_map={"background": BACKGROUND_CLASS},
    ),
    # shobhit18th is deliberately absent: Kaggle reports its licence as "unknown", which
    # DEC-022 treats as unusable. Adding it here would be the whole safeguard undone.
}

VALID_CLASSES = {str(d) for d in KNOWN_DENOMINATIONS} | {BACKGROUND_CLASS}


# --------------------------------------------------------------------------- hashing


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dhash(path: Path, size: int = 8) -> int | None:
    """64-bit difference hash: which adjacent pixels get brighter.

    Catches the same photograph re-encoded, resized or lightly recompressed, which is how
    these datasets differ when they re-host one another. Returns None for unreadable files
    so a corrupt image is reported rather than crashing the merge.
    """
    try:
        from PIL import Image

        img = Image.open(path).convert("L").resize((size + 1, size), Image.LANCZOS)
    except Exception:
        return None

    pixels = list(img.getdata())
    bits = 0
    for row in range(size):
        offset = row * (size + 1)
        for col in range(size):
            bits = (bits << 1) | int(pixels[offset + col] < pixels[offset + col + 1])
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


# --------------------------------------------------------------------------- reading


def class_of(path: Path, source: Source, root: Path) -> tuple[str | None, str | None]:
    """(class, reason-if-rejected) for one image.

    Tries the directory name first, since folder-per-class is the common layout, then the
    filename. A directory name that is not exactly a known class is an error rather than
    something to scrape digits out of -- see the Thai baht case in the module docstring.
    """
    relative = path.relative_to(root)
    folder = path.parent.name.strip().lower()

    if folder in source.class_map:
        mapped = source.class_map[folder]
        return (mapped, None) if mapped else (None, f"excluded by class_map: {folder}")
    if folder in VALID_CLASSES:
        return folder, None

    # Order matters here. A folder that looks like it is *trying* to name a class, but
    # isn't one we recognise, must stop the merge -- it must NOT fall through to the
    # filename. `pypiahmad` stores Thai baht in folders like "20 Baht" whose files are
    # also named 20_*.jpg, so the filename would happily confirm the wrong answer and
    # label Thai money as Indian.
    if any(ch.isdigit() for ch in folder):
        return None, (
            f"folder {path.parent.name!r} contains digits but is not a known class -- add "
            f"a class_map entry for {source.slug} rather than letting it be guessed"
        )

    # Split folders ('train', 'test', 'validation') carry no class, so the filename does.
    parsed = parse_class(path.name)
    if parsed is None:
        return None, f"no class in folder or filename: {relative}"
    return str(parsed), None


def read_source(source: Source, raw: Path) -> tuple[list[tuple[Path, str]], list[str]]:
    root = raw / source.slug
    if not root.is_dir():
        return [], [f"{source.slug}: not downloaded ({root} missing)"]

    found: list[tuple[Path, str]] = []
    problems: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        cls, reason = class_of(path, source, root)
        if cls is None:
            if reason and "excluded by class_map" not in reason:
                problems.append(f"{source.slug}: {reason}")
            continue
        found.append((path, cls))

    # One line per distinct problem. A layout mistake affects every file under a folder,
    # and 4,000 identical messages bury the one detail that identifies it.
    seen: set[str] = set()
    unique = [p for p in problems if not (p in seen or seen.add(p))]
    return found, unique


# --------------------------------------------------------------------------- merging


def merge(entries: list[tuple[Source, Path, str]], near_threshold: int):
    """Deduplicate, keeping the highest-priority copy. Returns (kept, stats)."""
    entries.sort(key=lambda e: (e[0].priority, str(e[1])))

    by_sha: dict[str, tuple[Source, Path, str]] = {}
    kept: list[tuple[Source, Path, str, str, int | None]] = []
    per_class_hashes: dict[str, list[tuple[int, str]]] = defaultdict(list)
    stats = Counter()
    conflicts: list[str] = []
    unreadable: list[Path] = []

    for source, path, cls in entries:
        digest = sha256(path)

        if digest in by_sha:
            prior_source, prior_path, prior_cls = by_sha[digest]
            stats["exact_duplicate"] += 1
            if prior_cls != cls:
                # The same bytes labelled two different denominations. Never a dedup
                # question -- one of the datasets is wrong, and training on either label
                # teaches the model a contradiction.
                conflicts.append(
                    f"{prior_source.slug}/{prior_cls} vs {source.slug}/{cls}: "
                    f"{prior_path.name} == {path.name}"
                )
            continue

        perceptual = dhash(path)
        if perceptual is None:
            unreadable.append(path)
            stats["unreadable"] += 1
            continue

        near = next(
            (h for h, _ in per_class_hashes[cls] if hamming(h, perceptual) <= near_threshold),
            None,
        )
        if near is not None:
            stats["near_duplicate"] += 1
            continue

        by_sha[digest] = (source, path, cls)
        per_class_hashes[cls].append((perceptual, digest))
        kept.append((source, path, cls, digest, perceptual))
        stats[f"kept:{source.slug}"] += 1

    return kept, stats, conflicts, unreadable


def write_corpus(kept, out: Path, manifest: Path, clean: bool) -> None:
    """Replace the output directory rather than adding to it.

    `organize_currency.py` names files `{split}_{original}` and this script names them
    `{source}_{split}_{original}`, so writing over an earlier corpus does not overwrite it
    -- it *doubles* it. The duplicates would then be invisible: every filename distinct,
    every image present twice, and a training run that looks fine while the split leaks
    into itself. Refuse instead, and delete only on request.
    """
    if out.exists() and any(out.iterdir()):
        if not clean:
            raise SystemExit(
                f"error: {out} is not empty.\n"
                "       Merging into an existing corpus adds to it rather than replacing "
                "it, because\n"
                "       the filenames differ, so every image would end up duplicated and "
                "invisible.\n"
                "       Re-run with --clean to rebuild it from scratch."
            )
        shutil.rmtree(out)

    _write(kept, out, manifest)


def _write(kept, out: Path, manifest: Path) -> None:
    for cls in {c for _, _, c, _, _ in kept}:
        (out / cls).mkdir(parents=True, exist_ok=True)

    with manifest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["filename", "class", "source", "licence", "sha256", "dhash"])
        for source, path, cls, digest, perceptual in kept:
            name = f"{source.slug}_{path.parent.name}_{path.name}"
            shutil.copy2(path, out / cls / name)
            writer.writerow([name, cls, source.slug, source.licence, digest,
                             f"{perceptual:016x}"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--raw", type=Path, default=RAW_DIR)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--near-threshold", type=int, default=4,
                        help="max Hamming distance between 64-bit perceptual hashes for "
                             "two images to count as the same photo (default 4)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean", action="store_true",
                        help="delete the output directory first; required when rebuilding "
                             "over an existing corpus")
    args = parser.parse_args()

    if not args.raw.is_dir():
        print(f"error: {args.raw} not found", file=sys.stderr)
        return 1

    present = {d.name for d in args.raw.iterdir() if d.is_dir()}
    unknown = present - set(SOURCES)
    if unknown:
        print("error: unlisted source directories found:", ", ".join(sorted(unknown)),
              file=sys.stderr)
        print("       Add them to SOURCES with a verified licence, or move them out.",
              file=sys.stderr)
        print("       DEC-022 requires a licence check; an unlisted source has not had one.",
              file=sys.stderr)
        return 1

    entries: list[tuple[Source, Path, str]] = []
    problems: list[str] = []
    for slug in sorted(SOURCES, key=lambda s: SOURCES[s].priority):
        source = SOURCES[slug]
        found, issues = read_source(source, args.raw)
        problems.extend(issues)
        entries.extend((source, path, cls) for path, cls in found)
        if found:
            print(f"  {slug:16} {len(found):5} images   {source.licence}")

    if problems:
        print("\nproblems:")
        for line in problems[:20]:
            print(f"  {line}")
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more")
        blocking = [p for p in problems if "add a class_map" in p]
        if blocking:
            print("\nRefusing to merge: a folder name could not be resolved to a class "
                  "without guessing.", file=sys.stderr)
            return 1

    if not entries:
        print("\nNothing to merge. Download sources into "
              f"{args.raw}/<owner>/ first.", file=sys.stderr)
        return 1

    print(f"\n{len(entries)} images before deduplication")
    kept, stats, conflicts, unreadable = merge(entries, args.near_threshold)

    print(f"  exact duplicates dropped : {stats['exact_duplicate']}")
    print(f"  near duplicates dropped  : {stats['near_duplicate']} "
          f"(Hamming <= {args.near_threshold})")
    if unreadable:
        print(f"  unreadable files skipped : {len(unreadable)}")

    if conflicts:
        print(f"\n*** {len(conflicts)} LABEL CONFLICT(S): identical images, different "
              f"denominations ***")
        for line in conflicts[:10]:
            print(f"  {line}")
        print("  One of the sources is wrong. Training on either label teaches a")
        print("  contradiction, and the wrong one is spoken aloud as money.")

    print(f"\n{len(kept)} images kept")
    by_class = Counter(cls for _, _, cls, _, _ in kept)
    for cls in sorted(by_class, key=sort_key):
        print(f"  {cls:>10} {by_class[cls]:5}")

    attribution = sorted({s.slug for s, _, _, _, _ in kept
                          if SOURCES[s.slug].attribution_required})
    if attribution:
        print(f"\nAttribution required in the writeup for: {', '.join(attribution)}")

    if args.dry_run:
        print("\n(dry run -- nothing written)")
        return 0

    write_corpus(kept, args.out, args.manifest, args.clean)
    print(f"\nwrote {args.out}\nmanifest {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
