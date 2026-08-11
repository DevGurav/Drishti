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

## 2. Objectives

`TODO:` restate from `docs/OVERVIEW.md`, and mark which are met.

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

`TODO:` architecture diagram — camera → router → engine → translation → speech.

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

`TODO:` say plainly that ₹ note serial numbers are traceable, that fixtures are blurred,
and that no faces, ID documents or prescriptions were used.

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

| | stock | stakes prompt | LoRA (run 1) |
|---|---|---|---|
| overall | 0.308 | **0.533** | 0.521 |
| abstention precision | 0.913 | 0.726 | 0.581 |
| abstention recall | 0.258 | 0.639 | 0.664 |
| declines on | 14% | 43% | 56% |

A **paired bootstrap** over the same 500 samples puts the LoRA–prompt difference at
**[-0.058, +0.036]** — a tie, not a loss (`DEC-060`).

`TODO:` add run 2 at the natural abstention rate, and state whether `DEC-061`'s
pre-registered intervals held.

### 7.4 Results — latency

`TODO:` from `eval/results/mode_latency.csv`.

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

The practical conclusion: **five self-photographed fixtures caught what a 751-image test
set could not.** `TODO:` develop this into the report's main argument.

## 9. Limitations

State these plainly rather than burying them:

- **Latency misses the <8s target.** `TODO:` current figures.
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

- 64 decisions and 9 risks with measurements: `docs/BUILD_PLAN.md`
- Per-sample predictions: `eval/results/*.csv`
- Corpus rebuild: `data/currency_manifest.csv` + `data/scripts/merge_currency.py`
- `TODO:` test count at submission

## Appendix B — Attribution

`pypiahmad` and VizWiz-VQA are CC BY 4.0 and **require attribution**. `TODO:` full
citations.
