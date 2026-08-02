"""Flask routing layer. All orchestration lives in api.py; this is transport only.

Runs entirely on localhost with no external requests -- the offline requirement applies to
the web app exactly as it does to the CLI, so nothing here loads a CDN font, script or
stylesheet.
"""
from __future__ import annotations

import argparse
import os

# Must precede any framework import -- see the note in app/cli.py (DEC-006).
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

from pathlib import Path  # noqa: E402

from flask import Flask, jsonify, render_template, request, send_file  # noqa: E402

from app.drug_db import DrugDatabase  # noqa: E402
from app.engines.paddle_ocr import PaddleOCREngine  # noqa: E402
from app.engines.smolvlm import SmolVLMEngine  # noqa: E402
from app.languages import LANGUAGES  # noqa: E402
from app.router import Engines  # noqa: E402
from app.web.api import AnswerRequest, AnswerService  # noqa: E402

UPLOAD_DIR = Path(__file__).resolve().parents[2] / 'runtime' / 'captures'


def build_service(enable_vlm: bool = True, enable_speech: bool = True) -> AnswerService:
    """Engines are constructed once and kept warm; weights load lazily on first use, so
    an unused mode costs nothing."""
    translator = tts = None
    if enable_speech:
        from app.engines.indictrans import IndicTrans2Translator
        from app.engines.mms_tts import MMSTTSEngine

        translator = IndicTrans2Translator()
        tts = MMSTTSEngine(out_dir=UPLOAD_DIR.parent / 'audio')

    engines = Engines(
        ocr=PaddleOCREngine(),
        vlm=SmolVLMEngine() if enable_vlm else None,
        drug_db=DrugDatabase.from_file(),
    )
    return AnswerService(engines=engines, upload_dir=UPLOAD_DIR,
                         translator=translator, tts=tts)


def create_app(service: AnswerService | None = None) -> Flask:
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    _service = service

    def get_service() -> AnswerService:
        nonlocal _service
        if _service is None:
            _service = build_service()
        return _service

    @app.get('/')
    def index():
        return render_template('index.html', languages=LANGUAGES)

    @app.post('/api/answer')
    def answer():
        upload = request.files.get('image')
        req = AnswerRequest(
            mode=request.form.get('mode', ''),
            image_bytes=upload.read() if upload else b'',
            lang=request.form.get('lang', 'en'),
            ocr_lang=request.form.get('ocr_lang') or None,
            question=request.form.get('question', ''),
            speak=request.form.get('speak') == 'true',
        )
        result = get_service().handle(req)
        return jsonify(result.to_dict()), (200 if result.ok else 400)

    @app.get('/api/audio/<token>')
    def audio(token: str):
        path = get_service().audio_path(token)
        if path is None or not path.exists():
            return jsonify({'error': 'audio not found'}), 404
        return send_file(path, mimetype='audio/wav')

    @app.get('/api/health')
    def health():
        return jsonify({'ok': True})

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description='Drishti web app (offline, localhost)')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--host', default='127.0.0.1',
                        help="use 0.0.0.0 to reach it from a phone on the same wifi")
    parser.add_argument('--no-vlm', action='store_true',
                        help='skip SmolVLM (~4.5GB) -- read and medicine modes still work')
    parser.add_argument('--no-speech', action='store_true',
                        help='skip translation and TTS models')
    args = parser.parse_args()

    service = build_service(enable_vlm=not args.no_vlm, enable_speech=not args.no_speech)
    print(f'Drishti running at http://{args.host}:{args.port}  (offline, no external calls)')
    create_app(service).run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
