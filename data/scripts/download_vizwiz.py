"""Download VizWiz-VQA annotations (small). Image zips are several GB and are NOT
downloaded by default -- pass --images to fetch them, or stream from Hugging Face
(lmms-lab/VizWiz-VQA) inside the Colab notebooks instead.

Official page: https://vizwiz.org/tasks-and-datasets/vqa/
"""

import argparse
import sys
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://vizwiz.cs.colorado.edu/VizWiz_final"
ANNOTATIONS_URL = f"{BASE}/vqa_data/Annotations.zip"
IMAGE_URLS = {
    "val": f"{BASE}/images/val.zip",
    "train": f"{BASE}/images/train.zip",
    "test": f"{BASE}/images/test.zip",
}

DATA_DIR = Path(__file__).resolve().parents[1] / "vizwiz"


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"already exists, skipping: {dest}")
        return
    print(f"downloading {url} -> {dest}")

    def hook(blocks, block_size, total):
        done = blocks * block_size
        mb = done / 1e6
        pct = f" ({100 * done / total:.0f}%)" if total > 0 else ""
        print(f"\r  {mb:.1f} MB{pct}", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=hook)
    print()


def unzip(path: Path) -> None:
    print(f"extracting {path.name}...")
    with zipfile.ZipFile(path) as z:
        z.extractall(path.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", nargs="*", choices=list(IMAGE_URLS),
                        help="also download image splits (several GB each), e.g. --images val")
    args = parser.parse_args()

    try:
        ann_zip = DATA_DIR / "Annotations.zip"
        fetch(ANNOTATIONS_URL, ann_zip)
        unzip(ann_zip)
    except Exception as e:
        print(f"\nAnnotation download failed ({e}).\n"
              f"Download manually from https://vizwiz.org/tasks-and-datasets/vqa/ "
              f"into {DATA_DIR}", file=sys.stderr)
        return 1

    for split in args.images or []:
        img_zip = DATA_DIR / f"{split}.zip"
        fetch(IMAGE_URLS[split], img_zip)
        unzip(img_zip)

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
