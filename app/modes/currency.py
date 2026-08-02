"""Currency mode: classify the rupee note. Backed by the MobileNet CNN to be
trained on an Indian-currency dataset (data/scripts/download_currency.py, not
yet built) once notebook 00's candidate evaluation picks the model shape.
"""
from __future__ import annotations

from pathlib import Path

from app.interfaces import Classifier

CONFIDENCE_THRESHOLD = 0.85


def run(image_path: Path, classifier: Classifier) -> str:
    label, confidence = classifier.classify(image_path)
    if confidence < CONFIDENCE_THRESHOLD:
        return "I'm not confident about this note. Please try a clearer, well-lit photo."
    return f"This is a {label} rupee note."
