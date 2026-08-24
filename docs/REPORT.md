# Drishti — an offline vision assistant for blind users

**Devendra Ramesh Gurav** · [github.com/DevGurav/Drishti](https://github.com/DevGurav/Drishti)

> **Status: complete.** Every number here is measured and traceable to `docs/BUILD_PLAN.md`
> or a file in `eval/results/` — if a figure is missing it is absent, not invented.
> External claims about competing products carry the date they were verified (§3,
> **2026-08-15**); they date quickly and should be re-checked before any public version.

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

**The scale.** India's most recent nationally representative eye survey puts country-wide
blindness prevalence at **0.36%** and visual impairment at **5.47%**, which the authors
extrapolate to roughly **4.8 million blind and 74 million visually impaired people** as of
2017 (Vashist et al., 2022). For that population "ask a sighted person" is not an
occasional inconvenience; it is the daily mechanism for reading a medicine strip or
checking a banknote.

**Marathi is not an arbitrary choice of first language.** The 2011 Census records about
**83 million** first-language Marathi speakers — the fourth largest in India — and roughly
99 million including second-language speakers. It is also written in Devanagari, so `read`
mode reaches Marathi and Hindi through a single OCR recogniser rather than two. The
consumer assistants surveyed in §3 do read Marathi text; what none of them does is *answer*
in it (§3), which is the half that matters to a user who cannot read the screen.

## 2. Objectives, and how they turned out

Stated at the start of the project, scored honestly at the end. **Two of five met, two
partly, one not attempted.**

| # | objective | outcome |
|---|---|---|
| 1 | Fine-tune a **quantized (4-bit)** small VLM beating the stock VizWiz baseline | **Partly.** 0.308 → 0.575 beats stock decisively, but is *indistinguishable from a prompt change* (`DEC-067`), and the adapter does not ship (`DEC-068`). **No quantization was implemented.** |
| 2 | Specialist pipelines: Indic OCR + expiry parsing, and a ₹-note CNN at **≥99%** | **Partly.** Both pipelines work end to end. Currency reached **0.9827**, short of the 99% bar — and the bar itself proved to be the wrong target (`DEC-022`). |
| 3 | Safety guardrail: report a drug name only on a verified database match | **Met.** `app/drug_db.py`, declines otherwise, precision reported over a declared sample (`DEC-048`). |
| 4 | Offline speech in Marathi/Hindi/English, **under 8s** end to end | **Partly.** The full offline translate + TTS path works in all three languages. The 8s budget is met by **one mode of six** (`DEC-066`). This row read the same before 2026-08-22, when it was **wrong**: the speech was carrying the wrong numbers in every language (`DEC-072`) and read mode was rewriting its own Marathi (`DEC-074`). Both are fixed and verified end to end; the row is annotated rather than quietly corrected, because how long it stood is §8.4's point. |
| 5 | Validate with visually-impaired users; Android as a stretch goal | **Not met, and now out of scope.** Android was dropped with its blocker measured (`DEC-064`); the user study was dropped for time (`DEC-070`) and replaced by self-conducted task testing, which tests the software rather than the user experience. **Scored not met rather than redefined** — see §9. |

**The honest summary is that the targets were mostly missed and the reasons are the
result.** The 99% accuracy bar was replaced by rupee-weighted cost because accuracy does
not describe what a wrong answer costs. The 8s budget was missed, and measuring *why*
showed the bottleneck was translation rather than the OCR everyone assumed. The VLM
fine-tune worked and still should not ship. A report that claimed five green ticks would
be less informative than this table.

## 3. Background

Assistive vision tools for blind users are a solved problem in the sense that good ones
exist. **Microsoft Seeing AI**, **Google Lookout** and **Envision AI** all read text,
identify currency and describe scenes, and **Be My Eyes** connects users to sighted
volunteers and, more recently, to a cloud model. Several are free. None of them is
improved on here, and this report does not claim to.

Every claim in this section was re-verified against first-party documentation on
**2026-08-15**. These products ship frequently, and the re-check **weakened two of the three
assumptions this project was originally scoped against** — recorded here rather than quietly
left in the stronger form.

- **They lean on the network — but decreasingly.** Text recognition is often local, while
  scene description and free-form questions are typically served by a cloud model, which
  fails on a patchy connection and sends a photograph of a medicine strip to a server.
  **This is actively changing:** in **June 2026** Envision shipped on-device scene
  description and visual question answering built on Gemma 4, running on Arm SME2-capable
  phones, released as a preview. Google documents only Lookout's Food labels mode as
  working offline. The offline gap is real but narrowing, and on phone-class hardware a
  competitor has now closed part of it.
- **Indic support is real for *reading* and absent for *answering*.** Lookout reads text in
  33 languages including Marathi, Hindi, Gujarati, Kannada, Tamil, Telugu and Bengali — so
  "these tools cannot read Devanagari" would be false. But its detailed image descriptions
  are English, and Seeing AI's published list at its Android launch was 18 languages, none
  of them Indic. The gap is not recognising Indic script; it is **replying in an Indic
  language**, which is what the translate-and-speak path exists for.
- **Currency recognition is region-specific, and Indian notes are already covered.**
  Lookout's currency mode supports US dollars, Euros and **Indian Rupees**; Seeing AI has a
  currency channel. This project's currency mode therefore fills **no coverage gap**. What
  it adds is a rupee-weighted cost metric and a measured refusal threshold (§7.2) — a
  different claim from working where they do not.

**What survives the re-check is narrower than the original framing.** None of these products
documents the whole chain — Indic OCR, an Indic *spoken* answer, and a designed refusal —
running offline on ordinary hardware, and none publishes what a wrong answer costs its user.
That is a defensible position. "Existing tools do not work for Indian users" would not have
been, and was the claim before this section was checked.

**What is different here is not architecture.** Every component is an off-the-shelf open
model, and that is deliberate: the interesting question is not whether a 2B VLM can
describe a photograph, but what a system built from such parts should *do when it is not
sure*. The contributions this report claims are therefore:

1. A **fully offline** five-mode pipeline including Indic translation and speech, measured
   end to end on ordinary laptop hardware rather than on a GPU.
2. Metrics chosen to describe **what a wrong answer costs a user who cannot check it** —
   rupee-weighted error, and abstention precision and recall reported separately.
3. A repeated, documented finding that **benchmark scores and deployed behaviour diverge**,
   with five independent instances and one that changed what ships (§8).

Academic work on abstention and selective prediction is the closer relative to this project
than the consumer apps are. **VizWiz** (Gurari et al., 2018) is the benchmark that makes it
measurable, because it is photographs actually taken by blind people, and roughly half of
its validation set is unanswerable by construction.

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

**No constant in this system is a guess.** Every threshold below was set by a sweep, and
where one started as a scaffolding value the decision log records both the guess and the
measurement that replaced it. That is the methodological claim of this section.

### 6.1 Shared preprocessing

All three engines load images through `app/imaging.py::load_upright`, which applies EXIF
orientation. Phone photographs record rotation as metadata rather than rotating the pixels,
so an engine reading the raw file sees a sideways image — and a blind user has no way to
know their photograph was rotated.

### 6.2 Read and medicine — PaddleOCR

| constant | value | how it was set |
|---|---|---|
| `max_side`, Latin | **2048** | 1280 recovers 7 of 10 printed fields from a 4080×3072 phone photo; 2048 recovers 10 of 10 for +4s. Native resolution recovers 7 and degrades into non-words (`DEC-073`) |
| `max_side`, Devanagari | **1280** | the opposite result on the same day: 1010 characters at 1280 *and* 1600, but 938 at 2048. One shared value would have traded one mode's failure for another's (`DEC-073`) |
| detector, Latin | `PP-OCRv6_small_det` | benchmarked over five tiers scoring **fields recovered alongside seconds**, not seconds alone (`DEC-058`) |
| detector, Devanagari | `PP-OCRv5_server_det` | every lighter tier returned **zero** Devanagari characters where this reads 1010 |
| `enable_mkldnn` | `False` | mandatory — the oneDNN CPU path crashes on this version pair |
| doc preprocessing | on | disabling it lost the drug name, expiry and MRP for a 13% speed gain |

The tier benchmark is the part worth reporting. `PP-OCRv6_tiny` is **6.3× faster** and
**loses the expiry date** — excellent on a stopwatch, and it would tell a blind user an
expired medicine is safe. Scoring required fields alongside latency is what caught it.

**Medicine mode** then parses expiry and MRP from the OCR text (`app/parsers.py`) and looks
the drug name up in a verified database (`app/drug_db.py`). Matching counts occurrences
rather than testing substrings, so `NORADRENALINE` does not resolve to `Adrenaline`
(`DEC-046`). **No database match means no drug name is spoken** — the mode declines.

### 6.3 Currency — MobileNetV3-Small

Transfer-learned from ImageNet, 224px, 12 epochs, AdamW with cosine annealing and label
smoothing 0.05. **Augmentation is chosen to match how a blind user photographs a note** —
random resized crop to 0.55 (partially framed), rotation ±25° (handheld tilt), heavy colour
jitter (indoor bulbs), perspective distortion (folded notes), and random erasing (a thumb
over the note). Both flips are included, since a note handed over upside-down is the same
note.

`CONFIDENCE_THRESHOLD = 0.90` was a scaffolding guess of 0.85 until notebook 03 swept it
(`DEC-040`). Selection minimises **rupee error** subject to answering ≥80% of the time; an
earlier rule picked the lowest viable threshold and recommended 0.50, optimising for
answering often, which contradicts the premise that rupee cost is what matters. The sweep
has since re-derived 0.90 independently on three different corpora.

Class names, image size and normalisation travel **inside** the checkpoint (`DEC-023`), so
a corpus with different folders cannot silently relabel every prediction.

### 6.4 Scene and ask — SmolVLM

The prompt is the method. `ABSTENTION_SUFFIX` in `app/engines/smolvlm.py` states the stakes
plainly — that the person asking is blind and cannot check the answer, that a confident
wrong answer is worse than none, and that the model should reply exactly `unanswerable`
otherwise. **This single change moved VizWiz accuracy 0.308 → 0.533** (`DEC-016`), which is
why it, not the stock model, is the bar fine-tuning had to clear (`DEC-017`).

The notebooks read that suffix **from the source file rather than retyping it**, so a
measured number always describes the prompt the app actually ships.

The model intermittently emits `Answer: unanswerable`; unhandled, the app reads that string
aloud instead of offering retake guidance, so it is stripped (`DEC-018`).

### 6.5 Delivery — translation and speech

IndicTrans2 for en → mr/hi, then MMS-TTS. Speech is chunked at sentence boundaries under
400 characters, because MMS degrades on long inputs and scene descriptions run long.

Note for anyone reproducing the latency figures: **the speech leg must be timed on the
translated text**. MMS-TTS tokenises against a Devanagari vocabulary, so English input
reduces to no tokens and the model fails outright — a harness error that briefly looked
like a missing feature.

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

**Re-measured 2026-08-22, after the resolution fix** (`DEC-073`), on the same benchmark and
machine: currency **1.6s**, medicine **24.2s**, read **35.9s**, read-mr **65.5s**. Every
mode fell inside the ranges above *despite Latin OCR now running at 2048 rather than 1280* —
a 2.6× increase in pixels processed. **Recovering the small print cost no measurable time**,
which is worth stating because the 1280 default had been justified partly on latency
grounds. read-mr should improve further still: `DEC-074` removes a 6.4s translation step
from that path, and that step was actively corrupting the text.

#### The benchmark photographs are not the hard ones

Every figure above was measured on `data/samples/`. Running the same modes over the
2026-08-24 self-test photographs — phone shots at 4080×3072, framed the way a user would —
gives a different picture, and the direction is the one §8.4 keeps predicting.

| mode | on the fixtures | on a real photograph | ratio |
|---|---|---|---|
| currency | 1.6s | **0.2–2.6s** | same, or faster |
| medicine | 24.2s | **26.7–47.6s** | ~1.5× |
| read (English) | 35.9s | **314s** on a full utility bill | **8.7×** |
| read-mr | 65.5s | **119.7s** on a printed notice | 1.8× |

**Currency does not care and read mode cares enormously**, and the reason is text volume
rather than difficulty: `newspaper-marathi.png` is one column, while an electricity bill is
a dense two-sided A4 of small print, and OCR cost scales with the number of text lines
detected. A five-minute answer is not a usable one. **This does not change the conclusion —
one mode of six met the target and one still does — but it does change the size of the
miss**, and it is another instance of a number that was true of the fixture and not of the
task. The honest version of the read-mode row is *"36 seconds on a newspaper column, five
minutes on a bill"*.

## 8. Discussion — the benchmark is not the product

This is the thread running through the project. **Five independent times, the benchmark and
the deployed behaviour moved in opposite directions** — and the pattern is consistent
enough to be the report's main claim rather than an aside:

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

### 8.1 Why this keeps happening

These are not five unrelated accidents. Each has the same shape: **the metric is a proxy,
and optimising a proxy hard enough eventually pushes against the thing it stands for.**

- **The test set is drawn from the same distribution as the training set.** A currency
  corpus of tightly-cropped catalogue photographs measures how well the model reads
  tightly-cropped catalogue photographs. Real notes are held at arm's length in bad light.
- **The metric omits the cost structure.** VizWiz pays full credit for a correct
  `unanswerable`, so declining is a cheap way to score. Accuracy treats a ₹10→₹20 error and
  a ₹100→₹500 error identically. Both metrics are reasonable; neither describes the user.
- **Latency measured on one component hides where the time goes.** Six months of the risk
  register said "OCR is slow". Measured end to end, translation is the larger half.

### 8.2 What actually caught them

Not better benchmarks. Four cheap habits, and they generalise beyond this project:

1. **A handful of real fixtures, photographed by hand.** Five banknote photographs and three
   non-note images caught what a 751-image test split could not — twice. They cost an
   afternoon and are the single highest-value artifact in the repository.
2. **A cost metric alongside the accuracy metric.** Rupee-weighted error is what revealed
   that ₹2000 was an attractor rather than a merely difficult class, and that dataset
   leakage understated cost by 54% while barely moving accuracy.
3. **Per-sample predictions, versioned.** Every claim traces to a CSV, which is what made
   paired confidence intervals possible after the fact — and paired intervals are what
   demoted "fine-tuning beats prompting" to "indistinguishable".
4. **Predictions written down before the run.** `DEC-061` was registered in advance and
   **failed on all four counts**, which falsified a diagnosis that had already been written
   into the decision log as though it were established. Nothing else would have caught it;
   a hypothesis formed after seeing the result would have fitted the result.

### 8.3 The uncomfortable version

The strongest result in this project is a **negative** one, and it took two GPU runs to
establish: a one-line prompt change captures essentially everything a 100-minute fine-tune
does, and the fine-tune that scores highest is the one that should not ship. Had the
project reported only the headline metric — 0.308 → 0.575, an 87% relative improvement —
every number would have been true and the conclusion would have been wrong.

### 8.4 A second pattern: the failures were in the stage nobody measured

Everything above was written before Phase 5 began. On the **first day of self-testing**,
using the app rather than evaluating it turned up three defects, and none of them was
visible to any metric in this report:

1. **Every spoken number was wrong** (`DEC-072`). MMS-TTS voices carry a character
   vocabulary and silently discard what they cannot encode. Marathi has no `3`, `5` or `8`;
   Hindi no `5`, `6`, `7` or `9`; **English none of `7`, `8` or `9`**. So ₹500 was announced
   as "00", an expiry of `APR.28` as "2", and an MRP of ₹10.30 as **₹100** — a tenfold price
   error, spoken confidently, to someone who cannot check it.
2. **Read mode returned non-words on book text** (`DEC-073`). `max_side=1280` reduces a
   4080×3072 phone photo by 3.2× per side — a **10× loss of pixel area** — putting body text
   below what the recogniser resolves.
3. **Read mode was translating Marathi into Marathi** (`DEC-074`). Correctly-OCR'd
   Devanagari was passed to IndicTrans2, an English-to-Indic model, which rewrote `भिवंडी`
   (a city) as `विव्हंदी` (not a word), `निधीचा` ("of funds") as `नीतीचा` ("of policy"), and
   then looped on `अधिक माहितीचे`.

A second batch on **2026-08-24** produced a fourth, and it is the most instructive of the
set because **the fix for the first one caused it**.

**The translator changes the numbers** (`DEC-076`). `DEC-072` was fixed by spelling numbers
into English *words* before translation, so the digit-less voices could say them. Measured
over 16 real MRP values, IndicTrans2 renders those words faithfully only about two times in
three. It re-emits digits (Marathi 3 of 16, Hindi 1 of 16) — and then the voice drops them
again, exactly as before. Worse, it states **a different amount** (Marathi 4 of 16, Hindi
4 of 16): `eighty four rupees and twenty one paise` returned as `चोवीस रुपये` —
**twenty-four**; `seventy eight` as `अठ्ठावीस` (28) in Marathi and `अड़तालीस` (48) in Hindi;
a real strip's `₹353.39` as **343.29**. Grammatical, fluent, and a different price.

**Why the fix did not hold.** `DEC-072` also added a control — `has_digits()`, asserted on
every spoken answer, which fails the build if a digit reaches the voice. It was placed on
the **English** text, because that is where the digits had been. The defect moved to the
translator's *output*, and the guard was watching its *input*. Every one of the 250 tests
passed while `₹84.21` was being announced as twenty-four rupees.

**The shape is the same in all four, and it is not the shape of §8.** These are not proxies
drifting from the goal. Each component was *certified by a measurement that stopped one
stage short of the user*:

| What was measured | What was not | Result |
|---|---|---|
| 1010 Devanagari characters **recognised** (`DEC-036`) | what delivery did with them afterwards | the page was rewritten before it was spoken |
| correct Marathi text, and 5.3s of audio **produced** | whether the audio said the text | ₹500 announced as "00" for twelve days |
| "no accuracy cost at 1280" (`DEC-036`) | that the test image was 1296×1720 and barely downscaled | the default was validated on an input that did not stress it |
| no digits in the **English** answer (`DEC-072`'s own control) | what the translator did to the number words afterwards | ₹84.21 announced as twenty-four rupees, with 250 tests green |

Each measurement was real, correctly performed, and honestly reported. Each stopped at the
boundary of the component being built rather than at the person being served. **The third
row is the sharpest of the original three: a downscale limit was approved using a fixture it
shrank by 25%, then applied to photographs it shrank by 69%.**

**The fourth row is sharper still, because it is not a missing measurement — it is a
measurement in the wrong place.** `DEC-072` ended by adding a control precisely so this
class of bug could not recur, and the control was correct, cheap, and asserted on every
answer. It simply guarded the stage that had already been fixed. A test suite says nothing
about the stages it does not straddle, and "we added a regression test" is not the same
claim as "the output is checked".

Stated as a rule, and it is the more useful half of this report's argument: **a component
is only validated on inputs that stress it, and a pipeline is only validated end to end.**
Section 8's five cases argue that metrics can point away from the product. These three argue
something narrower and more actionable — that a metric which never reaches the product
cannot point anywhere at all.

**What caught them was using the app.** Not a better benchmark, not more test coverage —
somebody listening to the audio and noticing the number was wrong. That is the same lesson
as §8.2's hand-photographed fixtures, arriving from the opposite direction: the fixtures
caught what the test split missed because they came from deployment, and these three were
caught because someone finally ran the thing end to end and paid attention to the output.

**Recorded honestly, this section is also an admission.** This report was complete, its
results tables filled and its conclusion written, while the product was announcing the wrong
denomination to its user. That gap between "the write-up is finished" and "the system works"
is the most useful thing in the document, and it would have been invisible had testing been
skipped for time — which, given the user study was already dropped for exactly that reason
(§9, `DEC-070`), is not a hypothetical.

## 9. Limitations

State these plainly rather than burying them:

- **Latency misses the <8s target in five modes of six.** Currency meets it at 1–2s; scene and ask are 28–31× over and are not an optimisation problem. **And the published figures are the gentle ones** — read mode takes 36s on the newspaper fixture and **314s on a real utility bill**, because OCR cost scales with the number of text lines and the fixtures are short (§7.4).
- **Devanagari OCR needs a server-class detector.** Every lighter tier returned zero
  Devanagari characters (`DEC-058`), which is what blocks the phone port.
- **`background` does not fully generalise.** Only 2 of 4 non-note fixtures are caught by
  the class itself; the other two are predicted as denominations and stopped by the
  threshold alone — a medicine strip at ₹100/**0.840** and a folded towel at ₹20/**0.804**.
  The towel scores higher as a ₹20 note than the real ₹20 note does (0.765), so the 0.90 bar
  is not separating notes from non-notes, it is sitting above a band where they interleave
  (`DEC-062`).
- **The drug database is a guardrail, not a pharmacopoeia.** It also matches generic names
  only, so a packet showing just a brand or an abbreviation is declined even when the
  medicine is in the list — a false negative, which is the safe direction, but a real one.
- **Numbers inside Devanagari text are still partly lost when spoken.** `DEC-072` is fixed
  for every answer the app *constructs*, because those are built as words before delivery.
  Read mode *relays* a page, and on the Devanagari path there is nowhere safe to put a
  number: the voices lack Latin digits, Devanagari digits **and** Latin letters, so English
  number words cannot be used either. Only a Marathi/Hindi number speller closes this, and
  it is not written. The engine now warns when a voice discards characters, which makes the
  loss visible rather than silent — a detector, not a fix.
- **About one spoken number in three is now withheld rather than spoken** (`DEC-076`).
  IndicTrans2 renders spelled-out numbers faithfully roughly two times in three; the rest
  of the time it re-emits digits or states a different amount — `₹84.21` as twenty-four
  rupees. Since 2026-08-24 the app verifies that a translated number still says what the
  English said, and **drops the sentence when it does not**. So a Marathi listener is now
  reliably told the drug name and the expiry, and is told the price only when the price
  survived; the printed text always carries it. This is honest rather than good. Closing
  it needs a validated Marathi/Hindi number speller — no library provides one (`num2words`
  covers 56 languages, neither of these), and writing one is a linguistic task needing a
  native reviewer, not more engineering.
- **Marathi mispronounces transliterated drug names.** That voice lacks `ॅ` and `ॉ`, so
  `पॅरासिटामॉल` is spoken `परासिटामल`. Recognisable, not a wrong answer, and absent in
  Hindi — the residual belongs to one voice rather than to the pipeline.
- **Framing is load-bearing and the user cannot judge it.** `DEC-073` recovered small print
  by processing more pixels, but a whole page photographed from far back still has too few
  pixels per character at any setting. This is `DEC-043`'s finding for currency appearing
  again for text, and it is the failure a blind photographer is most likely to cause and
  least able to detect.
- **Evaluated on public datasets and ten committed fixtures**, not on photographs taken by
  blind users in their homes.
- **No blind user has ever used this system, and nothing here shows that one could.** The
  study that would have established it was dropped for time (`DEC-070`); what replaces it is
  the author testing his own build. That is a weaker instrument than it sounds, and weakest
  exactly where this project is most exposed: **the entire design rests on the premise that
  the user cannot check the answer**, which is the one condition a sighted author cannot
  reproduce. He knows what the strip says before photographing it, sees immediately when OCR
  returns nothing, and frames the shot well without meaning to. The failure modes that
  matter most — a confident wrong answer, a refusal with no way to know why, an answer that
  never arrives — are the ones self-testing is worst at finding. **This is the project's
  largest single gap**, and no amount of the measurement in §7 substitutes for it.

## 10. Future work

**The Android port is scoped and deliberately not attempted** (`DEC-064`). The choices
that enable it were made in Phase 1 — MobileNetV3-Small at 6.2 MB, a 37 MB LoRA adapter
rather than a full fine-tune — and the measurement that blocks it is itself a result: the
Devanagari detector does not fit a phone.

## 11. Conclusion

Drishti is a five-mode vision assistant that runs **entirely offline on a laptop CPU** and
answers in Marathi, Hindi or English. Reading text, identifying a medicine and its expiry,
naming a banknote, describing a scene and answering a question about a photograph all work
end to end, with no network at any point. That much is demonstrable and was the committed
deliverable.

Most of the numeric targets set at the start were missed. Currency reached 0.9827 against a
99% bar; one mode of six meets the 8-second budget; no quantization was implemented; the
user study was dropped. **The reasons those targets were missed are the substance of this
project**, because in every case the target turned out to describe something other than what
a blind user experiences:

- **99% accuracy was the wrong bar.** Replaced by rupee-weighted error, which revealed that
  ₹2000 was an *attractor* rather than a difficult class — removing it improved accuracy and
  cut expected cost from ₹9.43 to ₹2.48, and eliminated the ₹2,000 error entirely.
- **The 8-second miss was informative.** Measuring per mode showed translation, not OCR, is
  the larger cost on the English text path — the opposite of what the risk register had
  assumed since Phase 1.
- **Fine-tuning worked and should not ship.** The LoRA adapter scores highest on VizWiz and
  refuses half of all answerable questions. A one-line prompt change captures what a
  hundred-minute training run does, and the paired interval says the difference is
  indistinguishable from zero.

- **The report was finished before the system worked.** On the first day of Phase-5
  self-testing, using the app turned up three defects no metric here could see: every spoken
  number was wrong in all three languages (`DEC-072`), small print was destroyed by a
  downscale limit validated on an image it barely touched (`DEC-073`), and read mode was
  handing its own correct Marathi to an English-to-Indic translator, which rewrote a city's
  name into a non-word and then looped (`DEC-074`).

The finding that recurs, and the one this report puts forward as its main claim, is that
**benchmark scores and deployed behaviour diverged five separate times** — and that the
things which caught it were cheap: a handful of hand-photographed fixtures, a cost metric
kept alongside the accuracy metric, versioned per-sample predictions, and a prediction
written down before the run that then failed on all four counts.

**A second pattern arrived late and is sharper** (§8.4). The three Phase-5 defects share a
shape the five above do not: each component had been certified by a measurement that stopped
one stage short of the user. Read mode was signed off on *1010 characters recognised*, an
OCR-stage number taken before delivery existed. Speech was signed off on correct text plus
the existence of audio, which never established that the audio said the text. The downscale
limit was signed off on an image it shrank by 25%, then applied to photographs it shrank by
69%. Every one of those measurements was real and honestly reported, and none of them
reached the person being served. **A component is only validated on inputs that stress it,
and a pipeline is only validated end to end.**

None of the components here are novel. The contribution is a working offline system for a
user who is poorly served by the existing ones, and an evaluation honest enough to
recommend against its own best-scoring model.

**Two things were dropped rather than finished, and both are recorded as such.** The Android
port went first, with its blocker measured: Devanagari OCR needs a server-class detector
because every lighter one read zero characters (`DEC-064`). The user study went second, for
time (`DEC-070`). That second one leaves the project's largest gap, and it is a gap in
exactly the place the design is most exposed — **a system built entirely around the premise
that the user cannot check the answer has never been put in front of a user who cannot check
the answer.** Self-testing by a sighted author does not close that, and this report does not
pretend otherwise (§9). Naming it is the same discipline the rest of the project ran on: the
`DEC-048` rule that an unvalidated claim is worse than an absent one, applied here to the
claim that would have been the most tempting to make.

The project's most-used artifact is not the code but `docs/BUILD_PLAN.md` — 71 decisions,
each with the measurement that settled it, including the ones that were wrong.

---

## Appendix A — Reproducibility

- 71 decisions and 9 risks with measurements: `docs/BUILD_PLAN.md`
- Per-sample predictions: `eval/results/*.csv`
- Corpus rebuild: `data/currency_manifest.csv` + `data/scripts/merge_currency.py`
- **237 automated tests**, including a compile check over every notebook cell (`DEC-065`),
  a model-free invariant that no digit reaches a voice (`DEC-072`), and a guard that text
  already in the target script is never translated (`DEC-074`)

## Appendix B — Attribution

Two sources are CC BY 4.0 and **require attribution**:

- **VizWiz-VQA** — Gurari et al., *VizWiz Grand Challenge: Answering Visual Questions from
  Blind People*, CVPR 2018. Used for the evaluation benchmark, the fine-tuning split, and
  as "no note in frame" negatives for the currency classifier.
- **`pypiahmad/indian-rupees-and-thai-baht-banknotes`** (Kaggle) — 1,961 images.

`vishalmane109` is CC0-1.0 and `gauravsahani` is DbCL-1.0; neither requires attribution,
and both are named anyway because `data/currency_manifest.csv` reproduces the corpus only
if the sources are identifiable.

## Appendix C — External sources

Cited for the scale figures in §1 and the competitor claims in §3. **Everything in §3 was
verified on 2026-08-15** against first-party documentation; consumer assistants change
often, and each claim should be re-checked rather than quoted from here later.

- Vashist P, Senjam SS, Gupta V, et al. (2022). *Blindness and visual impairment and their
  causes in India: Results of a nationally representative survey.* **PLoS ONE** 17(7):
  e0271736. <https://doi.org/10.1371/journal.pone.0271736> — source of the 0.36% / 5.47%
  prevalence figures and the 4.8 million / 74 million extrapolation for 2017.
- **Census of India 2011**, language tables — 83 million first-language Marathi speakers,
  ~99 million including second-language speakers.
- Gurari D, et al. (2018). *VizWiz Grand Challenge: Answering Visual Questions from Blind
  People.* **CVPR 2018.** <https://vizwiz.org/tasks-and-datasets/vqa/>
- **Microsoft Seeing AI** — feature channels and the 18-language list, from the Android
  launch announcement, Microsoft Accessibility Blog.
- **Google Lookout** — seven modes, currency limited to USD/EUR/INR, 33 text-reading
  languages including Marathi, and Food labels as the only documented offline mode:
  Android Accessibility Help,
  <https://support.google.com/accessibility/android/answer/9031274>
- **Envision** — on-device scene description and VQA with Gemma 4 on Arm SME2 hardware,
  announced **June 2026** and shipped as a preview:
  <https://www.letsenvision.com/blog/envision-arm-and-google-are-bringing-powerful-visual-ai-on-device>
