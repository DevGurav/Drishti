import unittest

from app import languages


class TestLanguageMapping(unittest.TestCase):
    def test_supported_codes(self):
        self.assertEqual(languages.codes(), ['en', 'hi', 'mr'])

    def test_marathi_maps_across_all_three_stacks(self):
        mr = languages.get('mr')
        self.assertEqual(mr.ocr, 'mr')                       # PaddleOCR
        self.assertEqual(mr.indictrans, 'mar_Deva')          # IndicTrans2
        self.assertEqual(mr.tts_model, 'facebook/mms-tts-mar')

    def test_hindi_maps_across_all_three_stacks(self):
        hi = languages.get('hi')
        self.assertEqual(hi.ocr, 'hi')
        self.assertEqual(hi.indictrans, 'hin_Deva')
        self.assertEqual(hi.tts_model, 'facebook/mms-tts-hin')

    def test_devanagari_is_not_an_ocr_code(self):
        """PaddleOCR 3.7.0 raises ValueError for lang='devanagari' on every ocr_version;
        the script is reached via 'hi'/'mr' (DEC-005)."""
        for lang in languages.LANGUAGES.values():
            self.assertNotEqual(lang.ocr, 'devanagari')

    def test_unknown_code_names_the_supported_set(self):
        with self.assertRaises(ValueError) as ctx:
            languages.get('devanagari')
        self.assertIn('en, hi, mr', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
