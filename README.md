# Drishti — Offline AI Vision Assistant for Blind Users in Indian Languages

Final-year AI&DS major project (2026–27). A fully **offline** assistant that lets blind users
read medicine strips, identify currency, read Devanagari/English text, and hear scene
descriptions — spoken in **Marathi/Hindi/English**, with zero internet and zero cloud upload.

**Why:** ~5M blind / ~70M visually-impaired Indians. Existing tools (Be My AI, Seeing AI,
Lookout) need internet + English and upload private photos (prescriptions, money, your home)
to the cloud. Drishti runs on a ₹10k Android phone, offline.

## Task modes

| Mode | What it does | Engine |
|---|---|---|
| Read | OCR printed text (incl. Devanagari), speak it | PaddleOCR (`lang=devanagari`) |
| Medicine | Drug name, expiry, MRP + "expired" warning | OCR + date parser + **drug-DB guardrail** |
| Currency | Identify ₹ note | Tiny MobileNet classifier |
| Scene | Describe surroundings | Quantized small VLM |
| Ask | Free-form visual Q&A | Quantized small VLM |

**Routing principle:** easy tasks go to small fast specialist models; only open-ended queries
hit the VLM. **Safety:** Medicine mode never lets the VLM guess a drug name — OCR text must
match a drug database or the app declines.

## Architecture

```
camera → mode router ├─ MobileNet (currency)
                     ├─ OCR + parsers (read/medicine)
                     └─ 4-bit VLM (scene/ask)  → English answer
                                                  → IndicTrans2 dist-200M (en→mr/hi)
                                                  → offline Indic TTS → speaker
```

- VLM candidates: Moondream-2 (~1.9B), SmolVLM (~2B), Qwen2.5-VL 3B, Gemma 3 4B — 4-bit GGUF
- Fine-tuning: LoRA on **VizWiz** (real blind-user photos) + self-collected Indian data
  (medicine strips, ₹ notes, MRP/expiry labels) — on free Colab/Kaggle GPUs
- Local dev machine has no NVIDIA GPU (Intel Iris Xe, 16 GB RAM) → **all training on Colab;
  laptop runs CPU inference of quantized models** (llama.cpp); Android port is the stretch goal

## Repo layout

```
data/        datasets + download scripts (large files gitignored)
notebooks/   00_feasibility_spike (Colab GPU) · 00b_ocr_spike (laptop CPU) · 01_vizwiz_baseline (Colab GPU)
models/      downloaded/quantized weights (gitignored)
app/         demo app: router, mode handlers, engine interfaces, CLI (laptop first, Android later)
tests/       unit tests for app/ (pure Python, no GPU/model needed — run with `python -m unittest discover -s tests -t .`)
eval/        evaluation results
docs/        synopsis.md (college submission draft)
```

### App architecture

`app/interfaces.py` defines `Protocol`s (`OCREngine`, `VLMEngine`, `Classifier`,
`Translator`, `TTSEngine`) that mode handlers depend on but don't implement — real
models (chosen via the notebooks) get wired in later without touching routing/mode
logic. `app/router.py` dispatches `--mode` to `app/modes/{read,medicine,currency,scene,ask}.py`.
`app/parsers.py` has the expiry/MRP extraction (pulled from the notebook 00 spike)
plus real date parsing. `app/drug_db.py` is the medicine-mode safety guardrail —
`data/drug_names_seed.txt` is a placeholder list, not a verified drug database.

**OCR engine: PaddleOCR** — see `DEC-003` in [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) for why
Surya and Tesseract were rejected, plus the mandatory config flags (`DEC-004`, `DEC-005`,
`DEC-008`).

## The app

A browser app served from localhost — one codebase for the laptop demo and the phone.

```powershell
pip install flask
python -m app.web.server --no-vlm --no-speech    # runs before any model is downloaded
# open http://127.0.0.1:5000
```

Drop the flags once the models are installed. `--host 0.0.0.0` makes it reachable from a
phone on the same wifi, which is the cheapest possible "mobile demo".

Interaction is designed to work without sight: **keys 1–5** pick a mode, **space** captures,
and every state change is announced through an `aria-live` region. Nothing loads from a CDN
— a test asserts the rendered page contains no external URLs, since one would silently break
the airplane-mode demo.

Captured photos are deleted immediately after answering, including when a model errors.
Users point this at prescriptions and bank documents; keeping them would contradict the
privacy claim the project rests on.

## Running it

**No model needs downloading by hand** — every engine fetches its weights on first use
(Hugging Face for the VLM/translation/TTS, PaddleX for OCR). Budget ~6 GB of disk.

Install in stages so a failure is easy to attribute, cheapest and most-proven first:

```powershell
# 0. tests need nothing at all - 76 tests, no models
python -m unittest discover -s tests -t .

# 1. OCR: read + medicine modes            (~100 MB downloaded on first run)
pip install paddlepaddle paddleocr
python -m app.cli --mode medicine --image strip.jpg

# 2. Speech: Marathi/Hindi output          (~950 MB on first run)
pip install transformers torch IndicTransToolkit
python -m app.cli --mode medicine --image strip.jpg --ocr-lang en --lang mr --speak

# 3. VLM: scene + ask modes                (~4.5 GB on first run)
python -m app.cli --mode scene --image room.jpg
python -m app.cli --mode ask --image x.jpg --question "what colour is this?"
```

`--ocr-lang` is separate from `--lang` on purpose: an Indian medicine strip prints the drug
name and expiry in **Latin script** even on Marathi packaging, so `--ocr-lang en --lang mr`
is the usual combination.

Currency mode still raises `NotImplementedError` — it needs the MobileNet training run.

On a CPU-only machine SmolVLM answers in tens of seconds rather than the 1.2 s measured on
a Colab T4. That is expected. OCR and speech are comfortable on CPU.

## Setup (local, Windows)

```powershell
./setup.ps1        # creates .venv with Python 3.12 and installs core deps
```

**Where each notebook runs.** `00_feasibility_spike_colab` and `01_vizwiz_baseline` load
multi-GB VLMs and need Colab's free T4 GPU.

The OCR spike was split into `00b_ocr_spike` because running PaddleOCR in a process that
already has the VLMs loaded **hard-kills the kernel** — the process dies, so you get a
kernel restart with no Python traceback. Two causes stack: PyTorch and PaddlePaddle each
bundle their own OpenMP runtime (co-loading them is a known segfault source), and the two
VLMs (~8.5 GB) leave little of Colab's ~12.7 GB system RAM spare. `00b_ocr_spike` imports
neither torch nor transformers, needs no GPU, and runs in a **fresh Colab runtime** or
locally in VS Code. Run it in a fresh runtime — not the one that loaded the VLMs.

## Planning, status and decisions

All of it lives in **[docs/BUILD_PLAN.md](docs/BUILD_PLAN.md)** — the six phases, current
status, the decision log (why SmolVLM over Moondream, why PaddleOCR over Surya, and the
mandatory config flags), the risk register, and the final success criteria.

Deliberately not duplicated here: a timeline in two files drifts, and the stale copy gets
believed. Update the build plan in the same commit as the work it describes.
