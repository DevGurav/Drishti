"""IndicTrans2 implementation of the Translator protocol.

Uses the distilled 200M checkpoint rather than the 1B: it is the size that can
realistically ship on a phone alongside a quantized VLM, and translation quality on the
short, factual sentences Drishti produces ("This is Paracetamol. It is valid until
MAR 2027.") does not need the larger model.

Verified working in notebooks/00_feasibility_spike_colab.ipynb §4.
"""
from __future__ import annotations

from app.languages import get as get_language

MODEL_ID = 'ai4bharat/indictrans2-en-indic-dist-200M'


def needs_translation(target_lang: str) -> bool:
    """English in, English out -- skip the model entirely.

    Worth an explicit check: loading IndicTrans2 costs ~800MB and several seconds, and
    English is a supported output language, so the common case should not pay for it.
    """
    return get_language(target_lang).indictrans != 'eng_Latn'


class IndicTrans2Translator:
    """Translates English into Indic languages. Model loads lazily on first use."""

    def __init__(self, model_id: str = MODEL_ID, device: str | None = None):
        self.model_id = model_id
        self._device = device
        self._model = None
        self._tokenizer = None
        self._processor = None

    def _load(self):
        if self._model is None:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            try:
                from IndicTransToolkit.processor import IndicProcessor
            except ImportError as e:
                # IndicTransToolkit imports PreTrainedTokenizerBase from
                # transformers.tokenization_utils, which moved in transformers v5. The
                # bare ImportError points at a transformers internal and reads like a
                # broken install, so name the actual constraint instead.
                raise ImportError(
                    f'IndicTransToolkit could not be imported ({e}).\n'
                    'It requires transformers 4.x -- v5 moved the tokenizer base class '
                    'it depends on.\n'
                    "Install with:  pip install 'transformers<5' IndicTransToolkit\n"
                    'and restart the runtime afterwards; a pip downgrade cannot replace '
                    'an already-imported module.'
                ) from e

            device = self._device or ('cuda' if torch.cuda.is_available() else 'cpu')
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_id, trust_remote_code=True).to(device)
            self._processor = IndicProcessor(inference=True)
            self._device = device
        return self._model

    def translate(self, text: str, target_lang: str) -> str:
        if not text.strip() or not needs_translation(target_lang):
            return text

        import torch

        tag = get_language(target_lang).indictrans
        self._load()

        batch = self._processor.preprocess_batch([text], src_lang='eng_Latn', tgt_lang=tag)
        inputs = self._tokenizer(
            batch, truncation=True, padding='longest', return_tensors='pt').to(self._device)
        with torch.no_grad():
            out = self._model.generate(**inputs, max_length=256, num_beams=4)
        decoded = self._tokenizer.batch_decode(out, skip_special_tokens=True)
        return self._processor.postprocess_batch(decoded, lang=tag)[0]
