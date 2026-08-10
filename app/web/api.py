"""Request handling for the web app, kept free of Flask.

The orchestration and validation live here so they can be unit-tested with fake engines
and no HTTP server. `server.py` is a thin routing layer over these functions.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app import languages
from app.engines.currency_cnn import CheckpointMissingError
from app.router import MODES, Engines, MissingEngineError, route
from app.speech import deliver

# Modes with no engine at all. Availability that depends on a trained model is decided at
# request time instead (see handle()), so training a model makes the mode work without a
# code change here.
UNAVAILABLE_MODES: dict[str, str] = {}

# Browsers hand us whatever the camera produced; refuse anything implausible early rather
# than letting a 40MB frame reach the model.
MAX_UPLOAD_BYTES = 12 * 1024 * 1024


@dataclass
class AnswerRequest:
    mode: str
    image_bytes: bytes
    lang: str = 'en'
    ocr_lang: str | None = None
    question: str = ''
    speak: bool = False


@dataclass
class AnswerResponse:
    ok: bool
    text_en: str = ''
    text_out: str = ''
    lang: str = 'en'
    audio_url: str | None = None
    error: str = ''

    def to_dict(self) -> dict:
        return {
            'ok': self.ok,
            'text_en': self.text_en,
            'text_out': self.text_out,
            'lang': self.lang,
            'audio_url': self.audio_url,
            'error': self.error,
        }


@dataclass
class ValidationError(Exception):
    message: str
    field: str = ''


def validate(req: AnswerRequest) -> None:
    """Raise ValidationError with a message that is safe to speak aloud.

    Error text reaches a blind user through a screen reader or TTS, so it says what to do
    rather than naming a status code.
    """
    if req.mode not in MODES:
        raise ValidationError(f"Unknown mode. Choose one of: {', '.join(MODES)}.", 'mode')
    if req.mode in UNAVAILABLE_MODES:
        raise ValidationError(UNAVAILABLE_MODES[req.mode], 'mode')
    if not req.image_bytes:
        raise ValidationError('No photo was received. Try taking the picture again.', 'image')
    if len(req.image_bytes) > MAX_UPLOAD_BYTES:
        raise ValidationError('That photo is too large. Try again.', 'image')
    if req.lang not in languages.LANGUAGES:
        raise ValidationError(f"Unsupported language. Choose: {', '.join(languages.codes())}.", 'lang')
    if req.ocr_lang and req.ocr_lang not in languages.LANGUAGES:
        raise ValidationError('Unsupported OCR language.', 'ocr_lang')
    if req.mode == 'ask' and not req.question.strip():
        raise ValidationError('Ask mode needs a question.', 'question')


@dataclass
class AnswerService:
    """Holds warm engines across requests so models load once, not per photo."""

    engines: Engines
    upload_dir: Path
    translator: object | None = None
    tts: object | None = None
    _audio: dict[str, Path] = field(default_factory=dict)

    def handle(self, req: AnswerRequest) -> AnswerResponse:
        try:
            validate(req)
        except ValidationError as e:
            return AnswerResponse(ok=False, error=e.message, lang=req.lang)

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        image_path = self.upload_dir / f'capture_{uuid.uuid4().hex[:12]}.jpg'
        image_path.write_bytes(req.image_bytes)

        try:
            answer_en = route(req.mode, image_path, self.engines, question=req.question)
            result = deliver(answer_en, lang=req.lang, translator=self.translator,
                             tts=self.tts, speak=req.speak)
        except CheckpointMissingError:
            # The exception text names notebooks and file paths -- useful to a developer,
            # useless spoken aloud. Translate it into something the user can act on.
            return AnswerResponse(
                ok=False, lang=req.lang,
                error='Money recognition is not available yet. Try another mode.')
        except MissingEngineError:
            # Running with --no-vlm is a deliberate configuration, not a fault: on CPU the
            # VLM modes take minutes, so the laptop demo turns them off (DEC-038). Falling
            # through to the generic handler would announce "something went wrong" to a
            # blind user, reporting a choice as a breakage and inviting them to retake a
            # photo that was never the problem.
            return AnswerResponse(
                ok=False, lang=req.lang,
                error=f'{req.mode.capitalize()} mode is switched off in this session. '
                      'Medicine and read modes still work.')
        except NotImplementedError as e:
            return AnswerResponse(ok=False, error=str(e), lang=req.lang)
        except Exception as e:  # noqa: BLE001 - surface a speakable message, log the rest
            return AnswerResponse(
                ok=False, lang=req.lang,
                error=f'Something went wrong reading that photo. {type(e).__name__}.')
        finally:
            image_path.unlink(missing_ok=True)   # captures are not retained

        audio_url = None
        if result.audio_path:
            token = uuid.uuid4().hex[:12]
            self._audio[token] = Path(result.audio_path)
            audio_url = f'/api/audio/{token}'

        return AnswerResponse(ok=True, text_en=result.text_en, text_out=result.text_out,
                              lang=result.lang, audio_url=audio_url)

    def audio_path(self, token: str) -> Path | None:
        return self._audio.get(token)
