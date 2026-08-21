"""Tests for the PaddleOCR engine's pure logic.

Deliberately does NOT import paddleocr — it's a heavy optional dependency that isn't
installed on the dev laptop. The config-building and result-normalizing logic is the
part that carries the hard-won knowledge from the notebook spike, so that's what's
pinned down here.
"""
import unittest

from app.engines.paddle_ocr import build_kwargs, extract_lines


class TestBuildKwargs(unittest.TestCase):
    def test_mkldnn_always_disabled(self):
        """Non-negotiable: PaddleOCR 3.7.0 + PaddlePaddle 3.3.x crashes on the oneDNN
        CPU path (Paddle #77340). Every config must keep this off."""
        for fast in (True, False):
            self.assertIs(build_kwargs('en', fast=fast)['enable_mkldnn'], False)

    def test_doc_preprocessing_on_by_default(self):
        """Measured on a real strip: disabling preprocessing lost the drug name, expiry
        and MRP for only a 13% speed gain (31.7s -> 27.6s). It must stay opt-in."""
        kw = build_kwargs('en')
        self.assertNotIn('use_doc_unwarping', kw)
        self.assertNotIn('use_doc_orientation_classify', kw)
        self.assertNotIn('use_textline_orientation', kw)

    def test_fast_mode_is_opt_in_and_disables_doc_preprocessing(self):
        kw = build_kwargs('en', fast=True)
        self.assertIs(kw['use_doc_orientation_classify'], False)
        self.assertIs(kw['use_doc_unwarping'], False)
        self.assertIs(kw['use_textline_orientation'], False)

    def test_lang_passed_through(self):
        self.assertEqual(build_kwargs('mr')['lang'], 'mr')


class TestDevanagariLangs(unittest.TestCase):
    """PaddleOCR 3.7.0 rejects 'devanagari'/'hindi'/'marathi'/'deva' outright; only these
    ISO-style codes resolve (to devanagari_PP-OCRv5_mobile_rec). Verified in notebook 00b."""

    def test_marathi_and_hindi_are_supported_codes(self):
        from app.engines.paddle_ocr import DEVANAGARI_LANGS

        self.assertIn('mr', DEVANAGARI_LANGS)
        self.assertIn('hi', DEVANAGARI_LANGS)

    def test_rejected_aliases_are_not_listed(self):
        from app.engines.paddle_ocr import DEVANAGARI_LANGS

        for bad in ('devanagari', 'hindi', 'marathi', 'deva'):
            self.assertNotIn(bad, DEVANAGARI_LANGS)


class TestExtractLines(unittest.TestCase):
    def test_v3_dict_shape(self):
        page = {'rec_texts': ['Paracetamol', 'EXP.OCT.2026'], 'rec_scores': [0.96, 0.98]}
        self.assertEqual(
            extract_lines([page]),
            [(0.96, 'Paracetamol'), (0.98, 'EXP.OCT.2026')],
        )

    def test_v3_object_shape(self):
        class Page:
            rec_texts = ['Rs.10.30']
            rec_scores = [0.96]

        self.assertEqual(extract_lines([Page()]), [(0.96, 'Rs.10.30')])

    def test_v3_json_attribute_shape(self):
        class Page:
            json = {'res': {'rec_texts': ['500mg'], 'rec_scores': [1.0]}}

        self.assertEqual(extract_lines([Page()]), [(1.0, '500mg')])

    def test_v2_nested_list_shape(self):
        page = [[[[0, 0], [1, 0], [1, 1], [0, 1]], ('Paracetamol', 0.9)]]
        self.assertEqual(extract_lines([page]), [(0.9, 'Paracetamol')])

    def test_missing_scores_do_not_crash(self):
        page = {'rec_texts': ['abc'], 'rec_scores': None}
        (score, text), = extract_lines([page])
        self.assertEqual(text, 'abc')
        self.assertNotEqual(score, score)  # NaN

    def test_empty_and_none_results(self):
        self.assertEqual(extract_lines(None), [])
        self.assertEqual(extract_lines([]), [])

    def test_malformed_v2_items_skipped(self):
        page = ['garbage', [[0, 0], ('ok', 0.5)]]
        self.assertEqual(extract_lines([page]), [(0.5, 'ok')])


class TestRealStripOutput(unittest.TestCase):
    """Regression guard using verbatim output from the notebook 00b Colab run."""

    def test_real_paracip_strip_lines(self):
        page = {
            'rec_texts': [
                'MFG.NOV.2024 EXP.OCT.2026',
                'Paracetamol Tablets IP',
                'PARACIP-500-500',
                'Rs.10.30 FOR 10 TABS.(INCL.OF ALL TAXE',
            ],
            'rec_scores': [0.98, 0.96, 0.98, 0.96],
        }
        text = ' '.join(t for _, t in extract_lines([page]))
        self.assertIn('Paracetamol', text)
        self.assertIn('EXP.OCT.2026', text)
        self.assertIn('10.30', text)


class TestImportOrderIsPlatformDependent(unittest.TestCase):
    """`_load()` looks like it has a redundant torch import. It does not.

    paddle and torch each bundle their own OpenMP, and the one that loses the race is
    whichever loads second -- but which one loses differs by platform. On Linux, torch
    first makes libpaddle segfault (`DEC-027`); on Windows, paddle first makes torch fail
    with WinError 127 loading shm.dll (`DEC-044`). Deleting the branch fixes one platform
    by breaking the other, and both failures are import-time crashes with no obvious link
    to OCR, so this test states the reason in the place someone would go looking.
    """

    def setUp(self):
        from pathlib import Path
        self.source = (Path(__file__).resolve().parents[1] / 'app' / 'engines'
                       / 'paddle_ocr.py').read_text(encoding='utf-8')

    def test_windows_imports_torch_before_paddle(self):
        load = self.source[self.source.index('def _load'):]
        win = load.index("sys.platform == 'win32'")
        torch_import = load.index('import torch')
        paddle_import = load.index('import paddle')
        self.assertLess(win, torch_import, 'the torch import must sit inside the win32 branch')
        self.assertLess(torch_import, paddle_import,
                        'on Windows torch must be imported before paddle, or torch fails '
                        'to load its DLLs (DEC-044)')

    def test_paddle_still_precedes_paddleocr_everywhere(self):
        """The Linux constraint survives: paddle before paddleocr on every platform."""
        load = self.source[self.source.index('def _load'):]
        self.assertLess(load.index('import paddle'), load.index('from paddleocr'),
                        'paddleocr pulls torch in via paddlex/modelscope, so paddle must '
                        'already be loaded (DEC-027)')

    def test_missing_torch_is_tolerated(self):
        """An OCR-only environment has no torch, and that must not be an error."""
        load = self.source[self.source.index('def _load'):self.source.index('from paddleocr')]
        self.assertIn('except ImportError', load)

class TestMaxSidePerScript(unittest.TestCase):
    """The two scripts want opposite downscale limits and one value cannot serve both
    (`DEC-073`). Measured 2026-08-22: a foil strip shot at 4080x3072 recovers 7 of 10
    printed fields at 1280 and all 10 at 2048; newspaper-marathi.png reads 1010
    Devanagari characters at 1280 and only 938 at 2048. Raising a single global default
    would have fixed small Latin print by losing 72 Devanagari characters.
    """

    def test_latin_gets_the_larger_limit(self):
        from app.engines.paddle_ocr import LATIN_MAX_SIDE, max_side_for
        self.assertEqual(max_side_for('en'), LATIN_MAX_SIDE)
        self.assertGreaterEqual(LATIN_MAX_SIDE, 2048)

    def test_devanagari_keeps_the_smaller_one(self):
        from app.engines.paddle_ocr import (
            DEVANAGARI_LANGS, DEVANAGARI_MAX_SIDE, max_side_for,
        )
        for lang in DEVANAGARI_LANGS:
            with self.subTest(lang=lang):
                self.assertEqual(max_side_for(lang), DEVANAGARI_MAX_SIDE)
        self.assertEqual(DEVANAGARI_MAX_SIDE, 1280)

    def test_the_two_are_not_the_same_value(self):
        """If these ever converge, one script's measurement was thrown away."""
        from app.engines.paddle_ocr import DEVANAGARI_MAX_SIDE, LATIN_MAX_SIDE
        self.assertNotEqual(LATIN_MAX_SIDE, DEVANAGARI_MAX_SIDE)

    def test_native_resolution_is_not_a_default(self):
        """At 4080 the detector is outside its trained scale and output degrades into
        non-words -- the same symptom as text that is too small, so 'just stop
        downscaling' looks like a fix and is not."""
        from app.engines.paddle_ocr import DEVANAGARI_MAX_SIDE, LATIN_MAX_SIDE
        for value in (LATIN_MAX_SIDE, DEVANAGARI_MAX_SIDE):
            self.assertLessEqual(value, 2560)

    def test_engine_resolves_by_lang_but_an_explicit_value_wins(self):
        from app.engines.paddle_ocr import (
            LATIN_MAX_SIDE, DEVANAGARI_MAX_SIDE, PaddleOCREngine,
        )
        self.assertEqual(PaddleOCREngine(lang='en').max_side, LATIN_MAX_SIDE)
        self.assertEqual(PaddleOCREngine(lang='mr').max_side, DEVANAGARI_MAX_SIDE)
        self.assertEqual(PaddleOCREngine(lang='en', max_side=999).max_side, 999)


class TestModelTierDefaults(unittest.TestCase):
    """Latin script runs the small tier; Devanagari must not (`DEC-058`).

    Measured on the Paracip strip: small reads the drug name, expiry and MRP exactly as
    the default did, 3.2x faster. The tier below it, `tiny`, is 6.3x faster and loses the
    expiry -- excellent on a stopwatch, and it tells a blind user a medicine is safe when
    nothing was read. On Devanagari every lighter detector returned zero characters where
    the server detector reads 1010, so that path keeps PaddleOCR's own defaults.
    """

    def test_latin_uses_the_small_tier(self):
        from app.engines.paddle_ocr import (
            DEFAULT_LATIN_DET, DEFAULT_LATIN_REC, build_kwargs,
        )
        kwargs = build_kwargs('en')
        self.assertEqual(kwargs['text_detection_model_name'], DEFAULT_LATIN_DET)
        self.assertEqual(kwargs['text_recognition_model_name'], DEFAULT_LATIN_REC)

    def test_devanagari_keeps_the_library_defaults(self):
        from app.engines.paddle_ocr import DEVANAGARI_LANGS, build_kwargs
        for lang in DEVANAGARI_LANGS:
            with self.subTest(lang=lang):
                kwargs = build_kwargs(lang)
                self.assertNotIn('text_detection_model_name', kwargs)
                self.assertNotIn('text_recognition_model_name', kwargs)

    def test_the_tiny_tier_is_not_a_default(self):
        """It loses the expiry date. If it ever becomes the default, that was a mistake."""
        from app.engines.paddle_ocr import DEFAULT_LATIN_DET, DEFAULT_LATIN_REC
        self.assertNotIn('tiny', DEFAULT_LATIN_DET)
        self.assertNotIn('tiny', DEFAULT_LATIN_REC)

    def test_an_explicit_choice_still_wins(self):
        from app.engines.paddle_ocr import build_kwargs
        kwargs = build_kwargs('en', det_model='PP-OCRv5_mobile_det')
        self.assertEqual(kwargs['text_detection_model_name'], 'PP-OCRv5_mobile_det')


if __name__ == '__main__':
    unittest.main()
