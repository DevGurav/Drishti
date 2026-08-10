"""MobileNetV3 implementation of the Classifier protocol, for Money mode.

A note is a closed-set problem with six classes, so it goes to a small specialist model
rather than the VLM (DEC-012). MobileNetV3-Small is ~2.5M parameters and built for phones,
which matters for the Phase-5 Android port.

Class names and preprocessing are read **from the checkpoint**, never hardcoded. A
checkpoint trained on differently-ordered folders would otherwise relabel every prediction
silently, and reporting a Rs 500 note as Rs 10 is precisely the failure Money mode exists
to prevent.

Trained by notebooks/03_currency_classifier.ipynb.
"""
from __future__ import annotations

from pathlib import Path

DEFAULT_CHECKPOINT = Path(__file__).resolve().parents[2] / 'models' / 'currency_mobilenetv3.pt'


def denomination(class_name: str) -> str:
    """Digits from a folder label: '500', 'Rs500' and '500_note' all mean 500.

    Kept pure so the label handling is testable without torch or a checkpoint.
    """
    digits = ''.join(ch for ch in str(class_name) if ch.isdigit())
    return digits or str(class_name)


class CheckpointMissingError(RuntimeError):
    """Raised with instructions rather than a bare file-not-found."""

    def __init__(self, path: Path):
        super().__init__(
            f'No currency model at {path}.\n'
            f'Train one with notebooks/03_currency_classifier.ipynb, then copy the '
            f'checkpoint here. Money mode is unavailable until then.'
        )


class CurrencyClassifier:
    """Classifier backed by a trained MobileNetV3. Weights load lazily on first use."""

    def __init__(self, checkpoint: Path | None = None, device: str | None = None):
        self.checkpoint = Path(checkpoint) if checkpoint else DEFAULT_CHECKPOINT
        self._device = device
        self._model = None
        self._meta: dict = {}

    @property
    def classes(self) -> list[str]:
        self._load()
        return list(self._meta.get('classes', []))

    def _load(self):
        if self._model is not None:
            return self._model
        if not self.checkpoint.exists():
            raise CheckpointMissingError(self.checkpoint)

        import torch
        import torch.nn as nn
        from torchvision import models

        blob = torch.load(self.checkpoint, map_location='cpu', weights_only=False)
        classes = blob['classes']

        model = models.mobilenet_v3_small()
        model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, len(classes))
        model.load_state_dict(blob['state_dict'])
        model.eval()

        device = self._device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self._model = model.to(device)
        self._device = device
        self._meta = blob
        return self._model

    def _preprocess(self, image_path: Path):
        from torchvision import transforms

        from app.imaging import load_upright

        size = self._meta.get('img_size', 224)
        tf = transforms.Compose([
            transforms.Resize(int(size * 1.14)),
            transforms.CenterCrop(size),
            transforms.ToTensor(),
            transforms.Normalize(self._meta.get('mean', [0.485, 0.456, 0.406]),
                                 self._meta.get('std', [0.229, 0.224, 0.225])),
        ])
        return tf(load_upright(image_path)).unsqueeze(0)

    def classify(self, image_path: Path) -> tuple[str, float]:
        """Return (denomination, confidence). The caller decides whether to trust it —
        app/modes/currency.py declines below its threshold rather than guessing."""
        # _load() first: it reports a missing checkpoint with instructions, which is the
        # likely failure. Importing torch above this would mask that with a
        # ModuleNotFoundError on any machine that has not installed the ML stack yet.
        model = self._load()

        import torch

        x = self._preprocess(image_path).to(self._device)
        with torch.no_grad():
            probs = torch.softmax(model(x), dim=1)[0]
        idx = int(probs.argmax())
        return denomination(self._meta['classes'][idx]), float(probs[idx])
