"""Currency mode: classify the rupee note. Backed by the MobileNet CNN to be
trained on an Indian-currency dataset (data/scripts/download_currency.py, not
yet built) once notebook 00's candidate evaluation picks the model shape.
"""
from __future__ import annotations

from pathlib import Path

from app.interfaces import Classifier

CONFIDENCE_THRESHOLD = 0.85

# The training set carries a class of photos containing no note at all, so "there is no
# note here" is something the model can actually predict rather than a gap it must fill
# with a denomination. Without it, pointing the camera at a table returns an amount.
BACKGROUND_LABEL = "background"

NO_NOTE_MESSAGE = (
    "I can't see a note in this photo. Try again with the note filling more of the frame."
)
UNSURE_MESSAGE = (
    "I'm not confident about this note. Please try a clearer, well-lit photo."
)


def run(image_path: Path, classifier: Classifier) -> str:
    label, confidence = classifier.classify(image_path)

    # Order matters. A *confident* "no note" is a different answer from "not sure", and
    # deserves different guidance: reframe the shot rather than improve the lighting.
    if str(label).strip().lower() == BACKGROUND_LABEL:
        return NO_NOTE_MESSAGE
    if confidence < CONFIDENCE_THRESHOLD:
        return UNSURE_MESSAGE
    return f"This is a {label} rupee note."
