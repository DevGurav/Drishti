"""Currency mode: classify the rupee note. Backed by the 7-class MobileNet trained on
the assembled Indian-currency dataset, wired in as app/engines/currency_cnn.py — see
DEC-040 to DEC-042 in docs/BUILD_PLAN.md.
"""
from __future__ import annotations

from pathlib import Path

from app.interfaces import Classifier

# Measured, not assumed (DEC-040). Notebook 03's sweep on 600 held-out test images,
# 2026-08-10:
#
#     thresh   answered   acc|answered   Rs error
#       0.50      98.7%         0.9916       1.32
#       0.85      90.3%         0.9945       1.00
#       0.90      85.0%         0.9961       0.71   <- chosen
#       0.95      61.5%         0.9973       0.49   (answers too rarely)
#
# 0.90 is the least expensive setting that still answers most of the time. The 0.85 here
# before was a scaffolding guess and cost Rs 0.29 more per identification.
CONFIDENCE_THRESHOLD = 0.90

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
