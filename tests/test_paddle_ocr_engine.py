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


if __name__ == '__main__':
    unittest.main()
