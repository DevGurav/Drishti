"""HTTP-level tests for the web app.

Skipped when Flask is not installed, so the core suite still runs on a bare checkout.
The orchestration is covered without Flask in test_web_api.py; these cover routing,
status codes and the offline guarantee.
"""
import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    import flask  # noqa: F401
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

from app.drug_db import DrugDatabase
from app.router import Engines
from app.web.api import AnswerService

JPEG = b'\xff\xd8\xff\xe0fake-jpeg-bytes'


class FakeOCR:
    def read(self, image_path):
        return 'PARACETAMOL 500MG EXP: MAR2030 MRP: Rs.45.50'


@unittest.skipUnless(HAS_FLASK, 'flask not installed')
class TestRoutes(unittest.TestCase):
    def setUp(self):
        from app.web.server import create_app

        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        service = AnswerService(
            engines=Engines(ocr=FakeOCR(), drug_db=DrugDatabase.from_file()),
            upload_dir=Path(self._tmp.name),
        )
        self.client = create_app(service).test_client()

    def test_health(self):
        self.assertEqual(self.client.get('/api/health').status_code, 200)

    def test_index_renders(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Drishti', res.data)

    def test_page_loads_no_external_resources(self):
        """The offline requirement applies to the web app too -- a CDN font or script
        would silently break the airplane-mode demo."""
        body = self.client.get('/').data.decode()
        for marker in ('http://', 'https://', '//cdn', 'googleapis'):
            self.assertNotIn(marker, body, f'external reference found: {marker}')

    def test_answer_returns_guardrailed_result(self):
        res = self.client.post('/api/answer', data={
            'mode': 'medicine', 'lang': 'en',
            'image': (io.BytesIO(JPEG), 'capture.jpg'),
        }, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Paracetamol', res.get_json()['text_en'])

    def test_bad_mode_is_400_with_speakable_error(self):
        res = self.client.post('/api/answer', data={
            'mode': 'teleport',
            'image': (io.BytesIO(JPEG), 'capture.jpg'),
        }, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        self.assertTrue(res.get_json()['error'])

    def test_missing_image_is_400(self):
        res = self.client.post('/api/answer', data={'mode': 'read'},
                               content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)

    def test_unknown_audio_token_is_404(self):
        self.assertEqual(self.client.get('/api/audio/nope').status_code, 404)


@unittest.skipUnless(HAS_FLASK, 'flask not installed')
class TestAccessibleMarkup(unittest.TestCase):
    """The interface is for users who cannot see it; these are correctness tests."""

    def setUp(self):
        from app.web.server import create_app

        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        service = AnswerService(
            engines=Engines(ocr=FakeOCR(), drug_db=DrugDatabase.from_file()),
            upload_dir=Path(self._tmp.name),
        )
        self.body = create_app(service).test_client().get('/').data.decode()

    def test_has_assertive_live_region(self):
        """Without this a screen reader never announces the answer."""
        self.assertIn('aria-live="assertive"', self.body)

    def test_every_mode_button_has_a_number_shortcut(self):
        for key in '12345':
            self.assertIn(f'accesskey="{key}"', self.body)

    def test_language_declared_on_html_element(self):
        self.assertIn('<html lang=', self.body)

    def test_question_input_has_a_label(self):
        self.assertIn('for="question"', self.body)


if __name__ == '__main__':
    unittest.main()
