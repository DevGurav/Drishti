"""Shared image loading for the engines.

Phone cameras write the sensor image in a fixed orientation and record how the phone was
held in an EXIF `Orientation` tag. Software that ignores the tag sees the photo rotated by
90, 180 or 270 degrees. Viewers, browsers and phone galleries all honour it, so a photo
that looks upright everywhere else arrives sideways at the model.

That matters more here than in most projects: the user cannot see the preview, cannot tell
which way up they held the phone, and gets no feedback that anything is wrong. The failure
is silent and looks like a model that is simply bad at some photos.

Observed on `data/samples/curr-10.jpg`, a handheld ₹10 note: the file is 3072x4080 with an
orientation tag, and the engines were feeding the model a 4080x3072 sideways image.
"""
from __future__ import annotations

from pathlib import Path


def load_upright(image_path: Path | str):
    """Open an image, apply its EXIF orientation, and return it as RGB.

    `exif_transpose` is a no-op on images without the tag, so this is safe for the web
    app's canvas captures and for the committed fixtures alike.
    """
    from PIL import Image, ImageOps

    return ImageOps.exif_transpose(Image.open(image_path)).convert('RGB')
