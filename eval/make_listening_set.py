"""Synthesize the handful of answers whose whole content is a number, under stable names.

`MMSTTSEngine` writes `drishti_{lang}.wav` and overwrites it, so after a full run the only
audio left is the *last* answer in each language -- which, after a read-mode batch, is a page
of prose. The answers that matter for `DEC-072` and `DEC-076` are the ones that are almost
entirely a number: a denomination, an expiry, a price. Those get overwritten first and are
exactly what nobody has ever heard.

This writes them to `runtime/listening/` with names that say what each one should say, so a
listener can check without holding the mapping in their head. Judge each by ear against the
`expect` line printed beside it.

    python -m eval.make_listening_set
"""
from __future__ import annotations

import os

os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

import shutil  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / 'data' / 'samples'
NEW = ROOT / 'test-images' / 'new'
OUT = ROOT / 'runtime' / 'listening'

# (filename, mode, image, lang, what a listener should hear)
CLIPS = [
    ('01-currency-500-marathi', 'currency', SAMPLES / 'curr-500.jpg', 'mr',
     'pachshe -- five hundred. NOT "00", which is what DEC-072 produced'),
    ('02-currency-500-hindi', 'currency', SAMPLES / 'curr-500.jpg', 'hi',
     'paanch sau -- five hundred'),
    ('03-currency-100-marathi', 'currency', SAMPLES / 'curr-100.jpg', 'mr',
     'shambhar -- one hundred'),
    ('04-medicine-paracip-marathi', 'medicine', SAMPLES / 'strip_paracip.jpg', 'mr',
     'Paracetamol, valid until April 2028, MRP ten rupees and thirty paise. '
     'The expiry and the price must BOTH be spoken'),
    ('05-medicine-paracip-hindi', 'medicine', SAMPLES / 'strip_paracip.jpg', 'hi',
     'the same three facts in Hindi'),
    ('06-medicine-becosules-marathi', 'medicine', NEW / 'A3b-becosules-multivitamin.jpg', 'mr',
     'ingredients and an expiry, and NO price -- DEC-076 drops it because the '
     'translator corrupts Rs 62.37. A price here would be the bug'),
]


def main() -> int:
    from app import languages
    from app.cli import build_engines
    from app.engines.indictrans import IndicTrans2Translator
    from app.engines.mms_tts import MMSTTSEngine, dropped_characters
    from app.router import route
    from app.speech import deliver

    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass

    OUT.mkdir(parents=True, exist_ok=True)
    engines = build_engines(ocr_lang='en')
    translator = IndicTrans2Translator()
    tts = MMSTTSEngine(out_dir=OUT)
    tokenizers: dict[str, object] = {}

    for name, mode, image, lang, expect in CLIPS:
        if not image.exists():
            print(f'{name}: SKIPPED, no {image}')
            continue

        answer_en = route(mode, image, engines)
        result = deliver(answer_en, lang=lang, translator=translator, tts=tts, speak=True)
        if result.audio_path is None:
            print(f'{name}: nothing to speak')
            continue

        # Stable, self-describing name. The engine writes drishti_{lang}.wav and would
        # overwrite the previous clip on the next iteration.
        final = OUT / f'{name}.wav'
        shutil.move(str(result.audio_path), final)

        if lang not in tokenizers:
            from transformers import AutoTokenizer
            tokenizers[lang] = AutoTokenizer.from_pretrained(languages.get(lang).tts_model)
        lost = dropped_characters(result.text_out, tokenizers[lang])

        print(f'\n{final.name}')
        print(f'  printed : {result.text_out}')
        print(f'  expect  : {expect}')
        if lost:
            print(f'  NOTE    : the voice cannot say {"".join(lost)!r}')

    print(f'\n{len(list(OUT.glob("*.wav")))} clips in {OUT}')
    print('Play each and compare it to the `expect` line. The printed text is not the '
          'check -- it was correct throughout every defect this project has had.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
