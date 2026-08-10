"""Re-evaluate a trained currency checkpoint without Colab.

Reproduces the exact test split notebook 03 used -- `ImageFolder` sorts classes and
filenames, and the notebook takes `random_split` under `torch.Generator().manual_seed(42)`
with 70/15/15 -- so numbers printed here are comparable with the ones in that notebook
rather than merely similar. Verified 2026-08-11: this script reproduced the notebook's
0.9883 accuracy and Rs 5.37 error to the digit.

Why it exists: changing anything about inference (the resize strategy, the threshold, a
different checkpoint) otherwise means burning a Colab session to find out whether it helped.
On CPU this is about a minute for 600 images.

    python eval/eval_currency.py
    python eval/eval_currency.py --variant squash --data data/currency
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from torch.utils.data import random_split
from torchvision import datasets, transforms

from app.engines.currency_cnn import CurrencyClassifier

SEED = 42          # must match notebooks/03_currency_classifier.ipynb
THRESHOLDS = (0.50, 0.70, 0.80, 0.85, 0.90, 0.95, 0.99)


def build_variants(size: int):
    """Eval-time resize strategies.

    `center_crop` is what the notebook trained and measured against. The alternatives keep
    the whole frame, which matters when the photo is elongated: on a 736x1544 handheld shot
    the centre crop keeps roughly the middle 40% of the note's length, and the denomination
    numerals sit at the corners. They lose on this dataset anyway -- see DEC-043; its images
    are already cropped tight to the note, so there is nothing at the edges to preserve.
    """
    def letterbox(im):
        w, h = im.size
        s = size / max(w, h)
        im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.BILINEAR)
        return ImageOps.pad(im, (size, size), color=(0, 0, 0))

    return {
        'center_crop': transforms.Compose(
            [transforms.Resize(int(size * 1.14)), transforms.CenterCrop(size)]),
        'letterbox': letterbox,
        'squash': lambda im: im.resize((size, size), Image.BILINEAR),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', type=Path, default=Path('data/currency'))
    parser.add_argument('--checkpoint', type=Path, default=None)
    parser.add_argument('--variant', default='all',
                        help="'all' (default) or one of center_crop / letterbox / squash")
    args = parser.parse_args()

    if not args.data.is_dir():
        print(f'error: {args.data} not found. Run data/scripts/organize_currency.py first.')
        return 1

    clf = CurrencyClassifier(checkpoint=args.checkpoint)
    model = clf._load()
    classes = clf._meta['classes']
    size = clf._meta.get('img_size', 224)
    normalize = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(clf._meta['mean'], clf._meta['std']),
    ])

    full = datasets.ImageFolder(args.data)
    if full.classes != classes:
        print(f'error: folder classes {full.classes} != checkpoint classes {classes}')
        print('       the split and every label would be misaligned; refusing to report.')
        return 1

    n_val = int(0.15 * len(full))
    n_test = int(0.15 * len(full))
    gen = torch.Generator().manual_seed(SEED)
    _, _, test_ds = random_split(full, [len(full) - n_val - n_test, n_val, n_test], generator=gen)
    print(f'{len(full)} images · test split {len(test_ds)} · classes {classes}\n')

    values = np.array([float(''.join(c for c in n if c.isdigit()) or 0) for n in classes])
    variants = build_variants(size)
    chosen = variants if args.variant == 'all' else {args.variant: variants[args.variant]}

    for name, fn in chosen.items():
        probs = []
        labels = []
        with torch.no_grad():
            for i in range(len(test_ds)):
                img, y = test_ds[i]
                x = normalize(fn(img)).unsqueeze(0).to(clf._device)
                probs.append(torch.softmax(model(x), dim=1)[0].cpu().numpy())
                labels.append(y)

        probs = np.stack(probs)
        y_true = np.array(labels)
        y_pred = probs.argmax(1)
        conf = probs.max(1)
        rupee = np.abs(values[y_pred] - values[y_true])

        print(f'=== {name} ===')
        print(f'accuracy {(y_pred == y_true).mean():.4f} · expected error Rs {rupee.mean():.2f}')
        print(f"{'thresh':>7} {'answered':>9} {'acc|answered':>13} {'Rs err':>8}")
        for t in THRESHOLDS:
            keep = conf >= t
            if keep.sum() < 50:      # too few to mean anything -- see DEC-040
                continue
            print(f'{t:7.2f} {keep.mean():9.1%} {(y_pred[keep] == y_true[keep]).mean():13.4f} '
                  f'{rupee[keep].mean():8.2f}')
        print()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
