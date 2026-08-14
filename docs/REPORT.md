# Drishti — an offline vision assistant for blind users

**Devendra Ramesh Gurav** · [github.com/DevGurav/Drishti](https://github.com/DevGurav/Drishti)

> **Status: scaffold.** Sections marked `TODO` need writing; every number already present
> is measured and traceable to `docs/BUILD_PLAN.md` or a file in `eval/results/`. Nothing
> here is a placeholder figure — if a number is missing it is absent, not invented.

---

## 1. The problem

A blind user in India who wants to know *which note is this*, *has this medicine expired*,
or *what is in front of me* has two options today: ask a sighted person, or send a
photograph to a cloud service. The first costs independence. The second costs privacy —
medicine strips carry conditions, banknotes carry serial numbers — and it fails entirely
without a network.

Drishti runs **five modes fully offline on a laptop CPU**, and answers in **Marathi, Hindi
or English**:

| mode | question it answers |
|---|---|
| read | what does this text say? |
| medicine | what is this drug, and has it expired? |
| currency | which banknote is this? |
| scene | what is in front of me? |
| ask | free-form question about the photograph |

**The design constraint that shaped everything: the user cannot check the answer.** A
sighted user reading a wrong OCR result notices. A blind user does not. This makes a
confident wrong answer strictly worse than a refusal, and that asymmetry — not accuracy —
is the axis the whole system is designed around.

`TODO:` one paragraph on scale — how many blind users in India, why Marathi specifically.

## 2. Objectives, and how they turned out

Stated at the start of the project, scored honestly at the end. **Two of five met, two
partly, one not attempted.**

| # | objective | outcome |
|---|---|---|
| 1 | Fine-tune a **quantized (4-bit)** small VLM beating the stock VizWiz baseline | **Partly.** 0.308 → 0.575 beats stock decisively, but is *indistinguishable from a prompt change* (`DEC-067`), and the adapter does not ship (`DEC-068`). **No quantization was implemented.** |
| 2 | Specialist pipelines: Indic OCR + expiry parsing, and a ₹-note CNN at **≥99%** | **Partly.** Both pipelines work end to end. Currency reached **0.9827**, short of the 99% bar — and the bar itself proved to be the wrong target (`DEC-022`). |
| 3 | Safety guardrail: report a drug name only on a verified database match | **Met.** `app/drug_db.py`, declines otherwise, precision reported over a declared sample (`DEC-048`). |
| 4 | Offline speech in Marathi/Hindi/English, **under 8s** end to end | **Partly.** The full offline translate + TTS path works in all three languages. The 8s budget is met by **one mode of six** (`DEC-066`). |
| 5 | Validate with visually-impaired users; Android as a stretch goal | **Not attempted.** Android was dropped deliberately with its blocker measured (`DEC-064`); the user study is outstanding. |

**The honest summary is that the targets were mostly missed and the reasons are the
result.** The 99% accuracy bar was replaced by rupee-weighted cost because accuracy does
not describe what a wrong answer costs. The 8s budget was missed, and measuring *why*
showed the bottleneck was translation rather than the OCR everyone assumed. The VLM
fine-tune worked and still should not ship. A report that claimed five green ticks would
be less informative than this table.

## 3. Background

`TODO:` brief and honest. What already exists (Seeing AI, Lookout, Envision), what they
require (network, subscription, English-first), and what is genuinely different here
(offline, Indic-first, refusal as a first-class output). Do not oversell novelty — the
contribution is a measured system and its evaluation, not a new architecture.

## 4. System design

### 4.1 Routing, not one big model

The central design decision (`DEC-012`): **each mode is routed to the smallest model that
can answer it.** Currency is a closed-set problem with seven classes, so it runs a
MobileNetV3-Small — smaller, faster and more accurate than asking a vision-language model.
OCR runs PaddleOCR. Only the open-ended modes reach the VLM.

```text
                    ┌──────────────┐
   photo ─────────► │    router    │  app/router.py — picks by mode, not by content
                    └──────┬───────┘
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  ┌───────────┐     ┌────────────┐     ┌────────────┐
  │ PaddleOCR │     │ MobileNet  │     │  SmolVLM   │
  │ read      │     │ currency   │     │ scene, ask │
  │ medicine  │     │            │     │            │
  └─────┬─────┘     └──────┬─────┘     └──────┬─────┘
        │ text             │ class+conf       │ text
        │                  │                  │
        │            ┌─────▼──────┐           │
        └───────────►│  refuse?   │◄──────────┘   drug DB · threshold 0.90 ·
                     └─────┬──────┘               "unanswerable"
                           │ English answer
                     ┌─────▼──────┐
                     │ IndicTrans2│   en → mr/hi        (16–23s on long text)
                     └─────┬──────┘
                     ┌─────▼──────┐
                     │  MMS-TTS   │   offline speech    (3–6s)
                     └─────┬──────┘
                           ▼  spoken answer, no network at any point
```

Every box runs locally. The refusal stage is drawn as its own step because it is the
project's actual subject: three different mechanisms feed it, and §7 measures each.

### 4.2 Components

| layer | choice | why |
|---|---|---|
| OCR | PaddleOCR 3.7.0 | Devanagari recognition model available |
| Currency | MobileNetV3-Small, 1.5M params, 6.2 MB | phone-sized from the start |
| VLM | SmolVLM-Instruct (2.25B) | runs on CPU; LoRA-adaptable |
| Translation | IndicTrans2 | en → mr/hi |
| Speech | MMS-TTS | offline Indic synthesis |

### 4.3 Refusal as a designed output

Every mode can decline. Currency declines below a confidence threshold; the VLM answers
`unanswerable`; medicine mode refuses to guess a drug name that is not in its database.
These are separate mechanisms because they fail differently — §7 measures each.

## 5. Datasets

**No self-collected photography.** The corpus is assembled from licence-clean public
datasets (`DEC-047`), which is a reproducibility property: `data/currency_manifest.csv`
rebuilds it exactly.

| source | licence | kept |
|---|---|---|
| `vishalmane109` | CC0-1.0 | 3,083 |
| `pypiahmad` | CC BY 4.0 · attribution required | 1,961 |
| VizWiz-VQA negatives | CC BY 4.0 · attribution required | 485 |
| `gauravsahani` | DbCL-1.0 | 73 |
| ~~`shobhit18th`~~ | unknown — **excluded** | — |

**5,010 images across 7 classes** after excluding ₹2000 (`DEC-054`).

Three findings worth reporting in their own right:

1. **A single source was not enough.** Trained on one dataset the model scored 0.9883 on
   that dataset's own split and cleared its confidence threshold on **3 of 5** real
   handheld notes — every training image is cropped tight to the note (`DEC-043`).
2. **33.5% of the test split were duplicates of training images** (`DEC-049`). Accuracy
   barely moved; expected *cost* was understated by 54%.
3. **A platform licence tag is the uploader's claim, not a provenance audit** — a dataset
   tagged CC0 was found to contain watermarked stock photography (`DEC-053`). **No dataset
   image appears in this report.**

### 5.1 Privacy, stated rather than assumed

The corpus contains **no faces, no identity documents and no prescriptions carrying a
patient name**. Banknote **serial numbers are traceable to an individual transaction**, so
the five self-photographed fixtures are blurred at the serial and no note image appears in
this report.

That last rule has a second reason. A Kaggle dataset tagged CC0 was found to contain
Shutterstock-watermarked stock photography (`DEC-053`), which establishes that **a platform
licence tag records the uploader's claim, not a provenance audit**. Reproducing any dataset
image would propagate a licence this project cannot verify.

## 6. Method

`TODO:` per mode — preprocessing, model, thresholds, and where each constant came from.
Every threshold in this project was measured rather than assumed; say so with the sweep.

## 7. Evaluation

### 7.1 The metrics, and why not accuracy

**Currency — rupee-weighted error** (`DEC-022`). Calling a ₹500 note a ₹100 costs the user
₹400; calling a ₹10 a ₹20 costs ₹10. Accuracy treats those identically.

**VLM — abstention precision and recall, reported separately, never averaged**
(`DEC-014`). A model that declines on everything scores ~0.49 on VizWiz and is useless.

### 7.2 Results — currency

| | 8 classes | 7 classes (₹2000 dropped) |
|---|---|---|
| accuracy | 0.9774 | **0.9827** |
| expected error | ₹9.43 | **₹2.48** |
| worst single error | ₹2,000 | **₹400** |
| at threshold 0.90 | ₹2.91 | **₹0.68** |

Dropping ₹2000 improved **both** accuracy and cost (`DEC-059`) — the signature of an
attractor class rather than a merely difficult one: ₹10 and ₹20 notes stopped being pulled
into ₹1,990 errors.

Train/test leakage after deduplication: **0.0%**.

### 7.3 Results — VLM abstention

| | stock | stakes prompt | LoRA @0.45 | LoRA @0.28 |
|---|---|---|---|---|
| overall | 0.308 | 0.533 | 0.521 | **0.575** |
| unanswerable subset | 0.306 | 0.673 | 0.680 | **0.783** |
| abstention precision | **0.913** | 0.726 | 0.581 | 0.587 |
| abstention recall | 0.258 | 0.639 | 0.664 | **0.750** |
| declines on | 14% | 43% | 56% | 62% |
| needless refusals | 6 | 59 | 117 | 129 |

Paired bootstraps over the same 500 samples, same order:

- LoRA @0.28 vs prompt: **+0.043, CI [-0.005, +0.090]** — includes zero, so
  **indistinguishable**, despite the higher point estimate.
- LoRA @0.28 vs LoRA @0.45: **+0.054, CI [+0.013, +0.095]** — a real difference.

**A prediction was registered before run 2 and it failed on all four counts** (`DEC-061`,
`DEC-067`). Predicted: abstention 40–46%, precision 0.68–0.78, recall 0.55–0.62, overall
within noise of 0.53. Measured: 62%, 0.587, 0.750, 0.575. Reducing the share of
`unanswerable` training targets made the model abstain **more**, which is the opposite of
what prior-copying predicts.

The hypothesis that survives: `unanswerable` is one fixed string while the answerable
targets are hundreds of distinct answers, so it is the lowest-entropy output available and
cross-entropy drifts toward it regardless of its share.

**The prompt ships, not the adapter** (`DEC-068`). Run 2 scores best on VizWiz and refuses
**129 of 256 answerable questions**. VizWiz pays full credit for a correct `unanswerable`,
so declining is a cheap way to score; a blind user gets silence.

### 7.4 Results — latency

Laptop CPU, Marathi delivery, per photo, model load excluded (it is paid once per session,
not once per photo). Ranges span four runs in one evening — see the throttling note below.

| mode | inference | translate | speak | total | vs 8s target |
|---|---|---|---|---|---|
| currency | ~0s | 0.8s | 0.4s | **1–2s** | **meets it** |
| medicine | 12–13s | 7–8s | 3s | 19–30s | 2.4–3.7× |
| read | 12–16s | 16–23s | 5–6s | 29–45s | 3.6–5.6× |
| read-mr | 64–69s | 8–9s | 4–5s | 76–83s | ~10× |
| scene | 235s | 5.6s | 4.4s | ~245s | 31× |
| ask | 223s | 0.6s | 0.5s | ~224s | 28× |

**One mode of six meets the target.** Two findings beyond the headline (`DEC-066`):

**Delivery, not vision, dominates the English text modes.** For `read`, translation and
speech are 29s of a 45s total — 65% — against 12–16s of OCR. The risk register had framed
this as an OCR problem since Phase 1. Cost tracks *output length*, not mode: `ask`
translates in 0.6s because its answer is one word.

**The laptop throttles under sustained load.** Across four runs in one evening, per-photo
cost rose monotonically — currency +120%, medicine +58%, read +55%. Absolute figures
therefore carry roughly ±50% depending on how long the machine has been working, which is
why they are quoted as ranges.

## 8. Discussion — the benchmark is not the product

This is the thread running through the project, and it should be the centre of this
section rather than an aside. Four independent times, **the benchmark and the deployed
behaviour moved in opposite directions**:

1. Merging datasets made the **benchmark score go down** while real-note fixtures went
   from 3/5 to 5/5 (`DEC-052`).
2. A model with 0.9883 accuracy was measured on a test split that was **one-third
   memorised** (`DEC-049`).
3. `PP-OCRv6_tiny` was **6.3× faster** on the stopwatch and silently **lost the expiry
   date** — a change that would tell a blind user an expired medicine is safe (`DEC-058`).
4. Dropping ₹2000 improved every headline metric while pushing one real note **below** the
   confidence threshold (`DEC-062`).
5. The LoRA scoring **highest on VizWiz** is the one that refuses **half** of all
   answerable questions, so the prompt ships instead (`DEC-068`).

The practical conclusion: **five self-photographed fixtures caught what a 751-image test
set could not.** `TODO:` develop this into the report's main argument.

## 9. Limitations

State these plainly rather than burying them:

- **Latency misses the <8s target in five modes of six.** Currency meets it at 1–2s; scene and ask are 28–31× over and are not an optimisation problem.
- **Devanagari OCR needs a server-class detector.** Every lighter tier returned zero
  Devanagari characters (`DEC-058`), which is what blocks the phone port.
- **`background` does not fully generalise.** 2 of 3 non-note images are now handled, but
  a medicine strip still reads as a banknote at 0.840 against a 0.90 bar — **0.06 of
  headroom** (`DEC-062`).
- **The drug database is a guardrail, not a pharmacopoeia.**
- **Evaluated on public datasets and five fixtures**, not on photographs taken by blind
  users in their homes.

## 10. Future work

**The Android port is scoped and deliberately not attempted** (`DEC-064`). The choices
that enable it were made in Phase 1 — MobileNetV3-Small at 6.2 MB, a 37 MB LoRA adapter
rather than a full fine-tune — and the measurement that blocks it is itself a result: the
Devanagari detector does not fit a phone.

## 11. Conclusion

`TODO:` write last. The honest summary is likely: *a fully offline five-mode assistant that
works end to end in Marathi on a laptop CPU, evaluated with metrics chosen to reflect what
a wrong answer costs a user who cannot check it — and a repeated demonstration that the
benchmark and the product disagree.*

---

## Appendix A — Reproducibility

- 68 decisions and 9 risks with measurements: `docs/BUILD_PLAN.md`
- Per-sample predictions: `eval/results/*.csv`
- Corpus rebuild: `data/currency_manifest.csv` + `data/scripts/merge_currency.py`
- **186 automated tests**, including a compile check over every notebook cell (`DEC-065`)

## Appendix B — Attribution

Two sources are CC BY 4.0 and **require attribution**:

- **VizWiz-VQA** — Gurari et al., *VizWiz Grand Challenge: Answering Visual Questions from
  Blind People*, CVPR 2018. Used for the evaluation benchmark, the fine-tuning split, and
  as "no note in frame" negatives for the currency classifier.
- **`pypiahmad/indian-rupees-and-thai-baht-banknotes`** (Kaggle) — 1,961 images.

`vishalmane109` is CC0-1.0 and `gauravsahani` is DbCL-1.0; neither requires attribution,
and both are named anyway because `data/currency_manifest.csv` reproduces the corpus only
if the sources are identifiable.
