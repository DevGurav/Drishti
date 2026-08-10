"""EXIF orientation, which every engine used to ignore.

Phones store the sensor image in a fixed orientation and record how the phone was held in
an EXIF tag. Galleries and browsers honour it, so a photo that looks upright everywhere
else arrives rotated at the model. A sighted developer checking the file sees it upright
and concludes the model is simply weak on that photo.

Needs only PIL, which is a core dependency, so this runs in the normal suite.
"""
import io
import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:  # pragma: no cover - PIL is a core dep; guard keeps the suite runnable
    HAVE_PIL = False

if HAVE_PIL:
    from app.imaging import load_upright

ORIENTATION_TAG = 0x0112
ROTATE_90_CW = 6      # "the top of the scene is at the right edge of the stored image"


def write_with_orientation(path: Path, size, orientation: int) -> None:
    """A JPEG whose stored pixels are `size`, tagged as needing rotation."""
    img = Image.new('RGB', size, 'white')
    exif = img.getexif()
    exif[ORIENTATION_TAG] = orientation
    img.save(path, 'JPEG', exif=exif)


@unittest.skipUnless(HAVE_PIL, 'PIL not installed')
class TestLoadUpright(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_rotation_tag_is_applied(self):
        """A landscape file tagged 'rotate 90' is a portrait photo."""
        p = self.tmp / 'rotated.jpg'
        write_with_orientation(p, (400, 300), ROTATE_90_CW)

        self.assertEqual(Image.open(p).size, (400, 300), 'raw pixels are landscape')
        self.assertEqual(load_upright(p).size, (300, 400), 'upright view is portrait')

    def test_untagged_images_are_unchanged(self):
        """Canvas captures from the web app carry no EXIF; this must be a no-op for them."""
        p = self.tmp / 'plain.jpg'
        Image.new('RGB', (400, 300), 'white').save(p, 'JPEG')
        self.assertEqual(load_upright(p).size, (400, 300))

    def test_result_is_rgb(self):
        """Engines index colour channels; a greyscale or palette file must not reach them."""
        p = self.tmp / 'grey.png'
        Image.new('L', (40, 40), 128).save(p)
        self.assertEqual(load_upright(p).mode, 'RGB')

    def test_every_engine_uses_it(self):
        """Guards the reason this module exists: three engines each opened images their
        own way, and all three ignored orientation."""
        root = Path(__file__).resolve().parents[1] / 'app' / 'engines'
        for name in ('paddle_ocr.py', 'smolvlm.py', 'currency_cnn.py'):
            with self.subTest(engine=name):
                source = (root / name).read_text(encoding='utf-8')
                self.assertIn('load_upright', source)
                self.assertNotIn(
                    'Image.open(image_path)',
                    source,
                    f'{name} opens images directly again, which drops EXIF orientation',
                )


if __name__ == '__main__':
    unittest.main()
