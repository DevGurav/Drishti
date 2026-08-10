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
            try:
                self._tokenizer = AutoTokenizer.from_pretrained(
                    self.model_id, trust_remote_code=True)
                self._model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.model_id, trust_remote_code=True).to(device)
            except OSError as e:
                # AI4Bharat gated this repo, so a first download now needs an accepted
                # licence and a token. transformers reports it as a 22-frame traceback ending
                # in a bare OSError, which reads like a network fault; it is an access fault
                # and needs a human action, not a retry. Weights already in the local cache
                # are unaffected -- this only bites on a machine that has never fetched them,
                # which is exactly the demo laptop the day before a review.
                if '401' not in str(e) and 'gated' not in str(e).lower():
                    raise
                raise OSError(
                    f'{self.model_id} is a gated Hugging Face repo and this machine is not '
                    'authenticated.\n'
                    f'  1. Accept the licence at https://huggingface.co/{self.model_id}\n'
                    '  2. Create a read token at https://huggingface.co/settings/tokens\n'
                    '  3. Export it as HF_TOKEN (on Colab: Secrets in the sidebar, then '
                    'enable notebook access)\n'
                    'The download is one-time; the model runs offline afterwards.'
                ) from e
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
            # use_cache=False is required, not a tuning choice. IndicTrans2 ships its own
            # modeling code via trust_remote_code, written against the legacy tuple-of-tuples
            # KV cache:
            #     past_key_values[0][0].shape[2] if past_key_values is not None else 0
            # transformers 4.54+ passes an EncoderDecoderCache object instead. It is not
            # None, so that guard passes, but [0][0] is None on the first decode step and
            # the model dies with AttributeError. Disabling the cache keeps past_key_values
            # None throughout and takes the else branch.
            #
            # Cost: no KV reuse, so decoding is quadratic in output length. Irrelevant here
            # -- Drishti's answers are one or two short sentences, and the alternative is
            # pinning transformers to a 4.4x that predates the cache change, which
            # SmolVLM (Idefics3, needs >=4.46) would not tolerate.
            out = self._model.generate(**inputs, max_length=256, num_beams=4, use_cache=False)
        decoded = self._tokenizer.batch_decode(out, skip_special_tokens=True)
        return self._processor.postprocess_batch(decoded, lang=tag)[0]
