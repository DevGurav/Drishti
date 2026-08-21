"""Tests for the web request layer, using fake engines and no HTTP server."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.drug_db import DrugDatabase
from app.router import Engines
from app.web.api import (
    MAX_UPLOAD_BYTES,
    AnswerRequest,
    AnswerService,
    ValidationError,
    validate,
)

JPEG = b'\xff\xd8\xff\xe0fake-jpeg-bytes'


class FakeOCR:
    def read(self, image_path):
        return 'PARACETAMOL 500MG EXP: MAR2030 MRP: Rs.45.50'


class FakeVLM:
    def answer(self, image_path, question):
        return 'a blue cup on a table'

    def describe(self, image_path):
        return 'a blue cup on a table'


class ExplodingOCR:
    def read(self, image_path):
        raise RuntimeError('model file corrupt')


class FakeCurrency:
    def classify(self, image_path):
        return ('500', 0.99)


class UntrainedClassifier:
    def classify(self, image_path):
        from pathlib import Path as _P

        from app.engines.currency_cnn import CheckpointMissingError
        raise CheckpointMissingError(_P('models/currency_mobilenetv3.pt'))


class FakeTranslator:
    def translate(self, text, target_lang):
        return f'<{target_lang}>{text}'


class FakeTTS:
    def speak(self, text, lang):
        return Path(f'{lang}.wav')


def _service(tmp, **engine_kw):
    engines = Engines(drug_db=DrugDatabase.from_file(), **engine_kw)
    return AnswerService(engines=engines, upload_dir=Path(tmp),
                         translator=FakeTranslator(), tts=FakeTTS())


class ScriptOCR:
    """An OCR engine that reports which script it was built for."""

    def __init__(self, script):
        self.script = script

    def read(self, image_path):
        return f'text-in-{self.script}'


class TestOcrLangRouting(unittest.TestCase):
    """`ocr_lang` was accepted, validated, and then discarded.

    The service held one English engine, so reading a Devanagari page ran the Latin
    recogniser and returned transliterated noise -- 'Tach taaRa firast HoH HEST' from a
    Marathi newspaper. Nothing raised, so a blind user simply heard confident gibberish.
    See DEC-045; on real weights the same request went from 0 to 1010 Devanagari
    characters once the engine was selected per request.
    """

    def setUp(self):
        self._tmpdir = TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = self._tmpdir.name
        self.built = []

    def _svc(self):
        def factory(script):
            self.built.append(script)
            return ScriptOCR(script)

        engines = Engines(ocr=ScriptOCR('en'), drug_db=DrugDatabase.from_file())
        return AnswerService(engines=engines, upload_dir=Path(self.tmp),
                             translator=FakeTranslator(), tts=FakeTTS(),
                             ocr_factory=factory)

    def test_requested_script_reaches_the_engine(self):
        """'mr' is the code PaddleOCR accepts; it resolves to devanagari_PP-OCRv5_mobile_rec
        inside the library (`DEC-005`). What matters here is that the request's script, not
        the service's default, is what the engine was built for."""
        r = self._svc().handle(
            AnswerRequest(mode='read', image_bytes=JPEG, ocr_lang='mr'))
        self.assertTrue(r.ok)
        self.assertEqual(self.built, ['mr'])
        self.assertIn('text-in-mr', r.text_en)
        self.assertNotIn('text-in-en', r.text_en, 'the English default was used instead')

    def test_default_is_used_when_no_script_requested(self):
        svc = self._svc()
        r = svc.handle(AnswerRequest(mode='read', image_bytes=JPEG))
        self.assertIn('text-in-en', r.text_en)
        self.assertEqual(svc._ocr_by_lang, {}, 'no engine should be built without a request')

    def test_engines_are_cached_per_script(self):
        """Each PaddleOCR language is a full pipeline costing ~60s to load; rebuilding one
        per photo would make the mode unusable."""
        svc = self._svc()
        for _ in range(3):
            svc.handle(AnswerRequest(mode='read', image_bytes=JPEG, ocr_lang='mr'))
        self.assertEqual(len(self.built), 1, f'built {len(self.built)} engines, expected 1')

    def test_only_requested_scripts_are_loaded(self):
        """Two live pipelines peaked at 11.65 GB on Colab (DEC-035), so they must not be
        pre-built for every supported language."""
        svc = self._svc()
        svc.handle(AnswerRequest(mode='read', image_bytes=JPEG, ocr_lang='hi'))
        self.assertEqual(len(self.built), 1)


class TestValidation(unittest.TestCase):
    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValidationError):
            validate(AnswerRequest(mode='teleport', image_bytes=JPEG))

    def test_missing_image_rejected(self):
        with self.assertRaises(ValidationError):
            validate(AnswerRequest(mode='read', image_bytes=b''))

    def test_oversize_image_rejected(self):
        with self.assertRaises(ValidationError):
            validate(AnswerRequest(mode='read', image_bytes=b'x' * (MAX_UPLOAD_BYTES + 1)))

    def test_unsupported_language_rejected(self):
        with self.assertRaises(ValidationError):
            validate(AnswerRequest(mode='read', image_bytes=JPEG, lang='devanagari'))

    def test_ask_mode_requires_a_question(self):
        with self.assertRaises(ValidationError):
            validate(AnswerRequest(mode='ask', image_bytes=JPEG, question='   '))

    def test_errors_are_speakable_not_status_codes(self):
        """Messages reach a blind user through TTS, so they must say what to do."""
        for req in (AnswerRequest(mode='read', image_bytes=b''),
                    AnswerRequest(mode='teleport', image_bytes=JPEG)):
            with self.assertRaises(ValidationError) as ctx:
                validate(req)
            msg = ctx.exception.message
            self.assertTrue(msg[0].isupper() and msg.endswith('.'), msg)


class TestAnswerService(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def test_medicine_mode_returns_guardrailed_answer(self):
        r = _service(self.tmp, ocr=FakeOCR()).handle(
            AnswerRequest(mode='medicine', image_bytes=JPEG))
        self.assertTrue(r.ok)
        self.assertIn('Paracetamol', r.text_en)

    def test_marathi_request_is_translated(self):
        r = _service(self.tmp, ocr=FakeOCR()).handle(
            AnswerRequest(mode='medicine', image_bytes=JPEG, lang='mr'))
        self.assertTrue(r.text_out.startswith('<mr>'))
        self.assertNotEqual(r.text_out, r.text_en)

    def test_audio_url_only_when_speak_requested(self):
        svc = _service(self.tmp, vlm=FakeVLM())
        quiet = svc.handle(AnswerRequest(mode='scene', image_bytes=JPEG))
        loud = svc.handle(AnswerRequest(mode='scene', image_bytes=JPEG, speak=True))
        self.assertIsNone(quiet.audio_url)
        self.assertTrue(loud.audio_url.startswith('/api/audio/'))

    def test_audio_token_resolves_to_a_path(self):
        svc = _service(self.tmp, vlm=FakeVLM())
        r = svc.handle(AnswerRequest(mode='scene', image_bytes=JPEG, speak=True))
        token = r.audio_url.rsplit('/', 1)[-1]
        self.assertIsNotNone(svc.audio_path(token))

    def test_unknown_audio_token_returns_none(self):
        self.assertIsNone(_service(self.tmp).audio_path('not-a-token'))

    def test_capture_is_deleted_after_answering(self):
        """Photos of prescriptions and money must not accumulate on disk."""
        svc = _service(self.tmp, ocr=FakeOCR())
        svc.handle(AnswerRequest(mode='medicine', image_bytes=JPEG))
        self.assertEqual(list(Path(self.tmp).glob('capture_*')), [])

    def test_capture_is_deleted_even_when_the_engine_fails(self):
        svc = _service(self.tmp, ocr=ExplodingOCR())
        r = svc.handle(AnswerRequest(mode='medicine', image_bytes=JPEG))
        self.assertFalse(r.ok)
        self.assertEqual(list(Path(self.tmp).glob('capture_*')), [])

    def test_engine_failure_is_reported_not_raised(self):
        r = _service(self.tmp, ocr=ExplodingOCR()).handle(
            AnswerRequest(mode='medicine', image_bytes=JPEG))
        self.assertFalse(r.ok)
        self.assertIn('went wrong', r.error)

    def test_unwired_engine_reports_cleanly(self):
        r = _service(self.tmp).handle(AnswerRequest(mode='scene', image_bytes=JPEG))
        self.assertFalse(r.ok)
        self.assertTrue(r.error)

    def test_no_vlm_is_announced_as_a_choice_not_a_breakage(self):
        """--no-vlm is the laptop demo configuration (DEC-038): on CPU the VLM modes take
        minutes. Announcing 'something went wrong' would tell a blind user their photo
        failed and invite them to retake one that was never the problem."""
        for mode in ('scene', 'ask'):
            with self.subTest(mode=mode):
                r = _service(self.tmp).handle(
                    AnswerRequest(mode=mode, image_bytes=JPEG, question='what is this?'))
                self.assertFalse(r.ok)
                self.assertIn('switched off', r.error)
                self.assertIn('Medicine and read modes still work', r.error)
                self.assertNotIn('went wrong', r.error)
                self.assertNotIn('Error', r.error)

    def test_validation_failure_short_circuits_before_touching_disk(self):
        svc = _service(self.tmp, ocr=FakeOCR())
        svc.handle(AnswerRequest(mode='teleport', image_bytes=JPEG))
        self.assertEqual(list(Path(self.tmp).glob('capture_*')), [])

    def test_untrained_currency_model_gives_a_speakable_message(self):
        """The raw exception names notebooks and file paths -- fine for a developer,
        useless read aloud to a blind user."""
        r = _service(self.tmp, classifier=UntrainedClassifier()).handle(
            AnswerRequest(mode='currency', image_bytes=JPEG))
        self.assertFalse(r.ok)
        self.assertIn('not available yet', r.error)
        self.assertNotIn('notebook', r.error.lower())

    def test_trained_currency_model_answers(self):
        r = _service(self.tmp, classifier=FakeCurrency()).handle(
            AnswerRequest(mode='currency', image_bytes=JPEG))
        self.assertTrue(r.ok)
        self.assertIn('five hundred', r.text_en)

    def test_response_serializes_for_json(self):
        r = _service(self.tmp, ocr=FakeOCR()).handle(
            AnswerRequest(mode='medicine', image_bytes=JPEG))
        d = r.to_dict()
        self.assertEqual(set(d), {'ok', 'text_en', 'text_out', 'lang', 'audio_url', 'error'})


if __name__ == '__main__':
    unittest.main()
