# Drishti — Offline AI Vision Assistant for Blind Users in Indian Languages

A personal project. A fully **offline** assistant that lets blind users
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
eval/        evaluation results, plus check_fixtures (real-photo regression) and
             run_self_test (the docs/SELF_TEST.md task sheet, run against photographs)
docs/        OVERVIEW.md (what the project is) + BUILD_PLAN.md (status, decisions, risks)
```

### App architecture

`app/interfaces.py` defines `Protocol`s (`OCREngine`, `VLMEngine`, `Classifier`,
`Translator`, `TTSEngine`) that mode handlers depend on but don't implement — real
models (chosen via the notebooks) get wired in later without touching routing/mode
logic. `app/router.py` dispatches `--mode` to `app/modes/{read,medicine,currency,scene,ask}.py`.
`app/parsers.py` has the expiry/MRP extraction (pulled from the notebook 00 spike)
plus real date parsing. `app/drug_db.py` is the medicine-mode safety guardrail, backed by
`data/drug_names_nlem2022.txt` — the 384 medicines of India's National List of Essential
Medicines 2022, extracted from the CDSCO publication by `data/scripts/build_drug_db.py`.

**OCR engine: PaddleOCR** — see `DEC-003` in [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) for why
Surya and Tesseract were rejected, plus the mandatory config flags (`DEC-004`, `DEC-005`,
`DEC-008`).

**Numbers are checked after translation, not just before it.** These TTS voices carry a
character vocabulary with no digits, so answers are built as words (`app/speakable.py`,
`DEC-072`) — and IndicTrans2 then renders those words as a *different amount* about one time
in three: `₹84.21` came back as twenty-four rupees. `app/devanagari_numbers.py` reads the
translation back and `app/speech.py` **drops any sentence whose numbers did not survive**
(`DEC-076`). It verifies rather than corrects, because a wrong entry in a hand-written
Marathi number table would be a confidently wrong price, while a missing one is only a
silence.

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

### Demoing it on a laptop

Run with `--no-vlm` and drive the demo through **medicine, read and currency**. Those three
never touch the VLM, they carry the project's actual claim, and they answer in seconds
rather than minutes on CPU. Scene and ask are shown as a recording, with the GPU
requirement stated out loud — see `DEC-038` in [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).

Start the server and run one photo through it *before* the audience arrives: the ~59s model
load is one-time, and there is no reason to spend it in front of an audience.

## Running it

**No model needs downloading by hand** — every engine fetches its weights on first use
(Hugging Face for the VLM/translation/TTS, PaddleX for OCR). Budget ~6 GB of disk.

Install in stages so a failure is easy to attribute, cheapest and most-proven first:

```powershell
# 0. tests need nothing at all - 255 tests, no models
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

Currency mode works. The 7-class MobileNet is trained and wired in
(`app/engines/currency_cnn.py`, a 6.2 MB checkpoint) — **0.9827** accuracy on the 2026-08-11
retrain, and at the chosen `CONFIDENCE_THRESHOLD = 0.90` it answers 89.9% of the time at
**0.9941**, an expected error of **₹0.68** per identification. Below that threshold it says it is
unsure rather than guessing a denomination, and a photo with no note in it comes back as
`background` instead of an amount. Verified on the laptop the same day: 4 of the 5 real handheld
fixtures answer, and 2 of 3 non-note photos correctly return `background`. ₹2000 is deliberately
not a class — see `DEC-051` in [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).

**CPU timings, measured 2026-08-10 on a GPU-less Colab runtime** — not estimates:

| Mode | CPU | For comparison |
|---|---|---|
| Scene (VLM) | **481 s** | 1.2 s/answer on a T4 |
| Ask (VLM) | **315 s** | |
| Medicine / Read (OCR) | **56 s** + 59 s one-time model load | |
| Translation + TTS | comfortable | |

The VLM modes are **minutes, not seconds**, on CPU. Plan any demo around that: medicine,
read and currency never touch the VLM, so they stay usable on a laptop, while scene and
ask effectively need a GPU. Closing this gap is the project's main open engineering problem
— see RISK-1 in [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).

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
