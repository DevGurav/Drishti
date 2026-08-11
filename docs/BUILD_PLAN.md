# Drishti — Build Plan

> **This is the single source of truth for scope, phases, status and decisions.**
> `README.md` describes *what the system is*. `OVERVIEW.md` explains the problem and the
> approach. Neither carries a timeline — if a date or milestone appears anywhere else,
> it is stale and should be deleted in favour of this file.
>
> **Last updated:** 2026-08-11 — currency mode trained and verified on the laptop
> (`DEC-040`–`DEC-042`). Previously 2026-08-10: full end-to-end run, every mode verified
> against real models (`DEC-035`–`DEC-037`).
>
> **Phase:** 1 of 6 · **Personal project by Devendra Ramesh Gurav**
>
> **Baseline:** stock SmolVLM-Instruct scored **0.308** on 500 VizWiz-val samples.
> Prompt engineering alone lifted it to **0.533** (+0.225, no training). Phase 3
> fine-tuning must beat **0.533**, not 0.308 — see `DEC-016`.

---

## 1. Status dashboard

| Phase | State |
|---|---|
| 0 — Feasibility & setup | ✅ **Complete** |
| 1 — Baselines & core pipeline | 🟢 **Complete** — every mode verified against real models on the laptop, 2026-08-11. NGO outreach is the one open item, and it belongs to Phase 5's user study |
| 2 — Dataset assembly | ✅ **Complete** — 5,602 images from four licence-clean sources, deduplicated, rebuildable from `data/currency_manifest.csv` |
| 3 — Fine-tuning | 🟡 **In progress** — currency retrained; `notebooks/05` written and running for the VLM LoRA against the 0.533 bar |
| 4 — Integration | 🟢 **All but one item done** — five modes, browser app on real engines, combination strips. Only the per-mode latency budget is open (RISK-1) |
| 5 — On-device + user study | ⬜ Not started |
| 6 — Evaluation & report | ⬜ Not started |

**Targets** (self-imposed — a plan with no date cannot tell you when it is slipping):
demoable end to end ≈ **Oct 2026** · project complete ≈ **Mar–Apr 2027**.

Per-phase month windows are deliberately absent. The order below is real; pretending to
know which month Phase 3 lands in is not.

### Component status

| Component | State | Evidence |
|---|---|---|
| App skeleton (router, 5 modes, guardrail) | ✅ Done | 175 tests passing |
| OCR engine (PaddleOCR) | ✅ Wired | `app/engines/paddle_ocr.py`. Verified on the **laptop** 2026-08-11: medicine and read modes both run locally, after fixing an inverted paddle/torch import order on Windows (`DEC-044`) |
| Medicine mode end-to-end | ✅ Works | Colab 2026-08-10 on `strip_paracip.jpg`: real OCR → `"This is Paracetamol. It is valid until APR.28. MRP is 10.30 rupees."` — drug name, expiry and MRP all correct against the strip |
| Read mode (English) | ✅ Works | via same engine |
| Read mode (Devanagari) | ✅ **Works** | Colab 2026-08-10: `newspaper-marathi.png` → **1010 Devanagari chars of 1238** at *both* 1280 (69.4 s) and 1600 (103.6 s). Headline and body both legible (`खंक तिजोरीमुळे भिवंडी भकास`, `ठाणे : अरुंद रस्ते…`). Foil is thin as expected: 14 chars @1280, 12 @1600. `RISK-7` retired |
| VizWiz baseline (stock prompt) | ✅ **0.308** | notebook 01, 500 samples, 1.21 s/answer |
| VizWiz with tuned prompt | ✅ **0.533** | notebook 02, same 500 samples, no training |
| Currency mode | ✅ **Retrained, ₹2000 dropped** | Colab 2026-08-11, 12 epochs, **5,010 images / 7 classes, 0.0% leaked**: accuracy **0.9827**, expected error **₹2.48** (was ₹9.43), worst single error **₹400** (was ₹2,000); at `CONFIDENCE_THRESHOLD=0.90` it answers 89.9% at **0.9941** and **₹0.68**. Verified on the laptop: **4 of 5 real notes answer** and **2 of 3 non-note images now return `background`** (`DEC-062`). Superseded 8-class run:  Accuracy **0.9810**, expected error **₹10.87**; at `CONFIDENCE_THRESHOLD=0.90` it answers **89.4%** at **0.9947** and **₹3.57**. The threshold sweep re-derived 0.90 independently on clean data. `DEC-041`'s systematic ₹20→₹200 and ₹50→₹500 confusions are **gone**; ₹2000 errors now carry 86% of all rupee cost (`DEC-051`). **All five real handheld fixtures now answer, against 3 of 5 before** — `curr-200` 0.342→0.926 (`DEC-052`). Checkpoint 6.2 MB |
| Scene / Ask modes | ✅ **Both work**, laptop included | Colab 2026-08-10 and **laptop 2026-08-11** (4.9 min warm, against 8 min on Colab CPU). Scene returns a full paragraph, confirming `DEC-031`. **The confabulation reproduces exactly** — "contains 30 tablets" (it holds 10) and "clear plastic… white backing" (it is opaque foil), word for word on both machines: `DEC-037` is a repeatable failure, not an anecdote |
| Translation + TTS | ✅ Works end-to-end, **laptop included** | Colab 2026-08-10, and laptop 2026-08-11 in 5.6 min: `हे पॅरासिटामॉल आहे. हे APR.28 पर्यंत वैध आहे. एमआरपी 10.30 रुपये आहे.` plus 5.3 s of Marathi audio. Needed VS Build Tools (`IndicTransToolkit` is source-only) and `sentencepiece` |
| Android port | ⬜ Not started | Phase 5 |
| NGO / user study | 🔴 **Not contacted** | long lead time — start now |
| Latency vs <8s target | 🔴 **OCR ~56s/photo · VLM ~294s on the laptop** | Colab 2026-08-10, GPU-less, model load (59.2s) excluded: medicine 56.2s @1280 vs 76.1s @1600; Devanagari 69.4s @1280 vs 103.6s @1600; scene 481.3s, ask 314.8s. **Laptop 2026-08-11 (i5-11300H): scene 294s warm** — faster than Colab's CPU but still minutes. Both far past 8s; see RISK-1 and `DEC-038` |

---

## 2. Phases

### Phase 0 — Feasibility & setup · ✅ Complete

**Goal:** prove nothing in the stack is impossible before committing eight months.

- [x] Problem selected, overview written
- [x] Repo scaffolded; app skeleton with router + mode handlers + safety guardrail
- [x] VLM candidates compared on real VizWiz photos (notebook 00)
- [x] OCR engine selected by measurement (notebook 00b)
- [x] Translation (IndicTrans2) and TTS (MMS-TTS) verified runnable

**Exit criteria met:** every load-bearing dependency demonstrated working at least once.

---

### Phase 1 — Baselines & core pipeline · 🟢 Exit criteria met

**Goal:** a measured baseline to improve on, and three modes running on a laptop.
**This is the part that has to work before anything else is worth doing.**

- [x] **Run notebook 01 → VizWiz baseline = 0.308** (answerable 0.310 / unanswerable 0.306)
- [x] Record 3 failure patterns — over-answering, fine-grained OCR misses, question-form misreads
- [x] Save `vizwiz_baseline_results.csv` to `eval/results/`, run `eval/analyze_results.py`
- [x] **Run `notebooks/02_abstention_prompts.ipynb`** — `stakes` prompt won; overall
      0.308 → **0.533**, abstention recall 0.258 → 0.639. Hypothesis in `DEC-013`
      confirmed: it was a calibration problem, and prompting fixed most of it
- [x] **Verify Read mode with `--ocr-lang mr`** — Colab 2026-08-10:
      `data/samples/newspaper-marathi.png` → **1010 Devanagari chars of 1238** in 60.8 s,
      headline and body both accurate. `RISK-7` retired; English-only fallback not needed
- [x] Wire SmolVLM into `app/engines/` as a `VLMEngine` → scene/ask modes now routable
- [x] Integrate IndicTrans2 + MMS-TTS as `Translator`/`TTSEngine` implementations
- [x] **Run the full pipeline on real hardware** — three runs on 2026-08-10. The first
      reached translation and speech but drew a conclusion later withdrawn (`DEC-034`);
      the second was SIGKILLed with two OCR languages in one process (`DEC-035`); the
      third completed every mode, evidence committed as
      `notebooks/04_app_end_to_end_devnagari.ipynb` with findings in its §8. That run
      confirmed `DEC-031`, corrected `DEC-036`, and produced `DEC-037`
- [x] **Source a real drug-name database** — `data/drug_names_nlem2022.txt`: the 384
      medicines of India's National List of Essential Medicines 2022, extracted from the
      CDSCO publication by `data/scripts/build_drug_db.py` (`DEC-032`). Building it
      exposed a latent matcher bug — see `DEC-033`
- [ ] **Send NGO / blind-school outreach emails** ← *long lead time; replies take weeks and
      scheduling takes weeks more, so this gates Phase 5 rather than Phase 1*

**Exit criteria — all met on the laptop, 2026-08-11:** baseline recorded (0.308 → 0.533) ·
read, medicine and currency answering locally, scene mode too (294 s) · spoken Marathi
end-to-end from medicine mode, text and audio.

Only the two items above that depend on other people remain.

---

### Phase 2 — Dataset assembly · 🟡 Partly done

**Goal:** a training corpus assembled from existing licence-clean datasets. No
self-collected photography (`DEC-047`). Protocol: `docs/dataset_guide.md`.

Medicine and Read train nothing — they run pretrained OCR plus a database lookup — so they
need *evaluation* data, not volume. Only currency and the VLM modes consume training data.

- [x] **Currency base corpus** — `vishalmane109/...-2020`, CC0-1.0, 4,002 images across 8
      classes, organized and trained on
- [x] **Merge the other licence-clean currency sources** — `data/scripts/merge_currency.py`,
      run 2026-08-11: **5,117 images** from vishalmane109 (60%), pypiahmad (38%) and
      gauravsahani (1%), up from 3,083 single-source. `shobhit18th` excluded, licence
      "unknown" fails `DEC-022`. pypiahmad requires attribution in the writeup
- [x] **Deduplicate by content hash *and* perceptual hash** — 591 exact and 489 near
      duplicates dropped from 6,197. **`gauravsahani` turned out to be almost entirely a
      re-host**: 73 of its images survived, so without hashing ~200 would have been added
      as if new. The confusable classes gained real data: ₹20 446 → 653, ₹50 433 → 833
- [x] **~500 VizWiz images as currency negatives** — `data/scripts/sample_vizwiz_negatives.py`,
      run 2026-08-11: 462 of 20,523 train entries excluded for mentioning money or a
      denomination, 500 sampled, **485 surviving deduplication**. `background` goes from
      398 to **883** and from the least varied class to the most. Fetched via HTTP range
      reads — 225 MB against an 11.3 GB archive
- [x] **Merge script and manifest committed** — `data/currency_manifest.csv`, 5,602 rows,
      so the corpus rebuilds from a clean checkout without shipping any images
- [ ] Record every source and licence in `data/README.md` with a verification date

**Exit criteria — met 2026-08-11:** **5,602 images** from four sources, deduplicated,
rebuildable from `data/currency_manifest.csv`, with `background` at 883. Licences recorded:
vishalmane109 CC0-1.0 (3,083) · pypiahmad CC BY 4.0 (1,961) · vizwiz_negatives CC BY 4.0
(485) · gauravsahani DbCL-1.0 (73). **Attribution required for pypiahmad and
vizwiz_negatives.**

Still open: retrain on this corpus and re-derive `CONFIDENCE_THRESHOLD`, which was chosen
on the contaminated split (`DEC-049`).

**Medicine and Read evaluation** is deliberately small and stated as such. No public Indian
medicine-strip dataset with legible generics and expiry dates was found under a usable
licence, and pharmacy product photography is not redistributable. The ≥95% guardrailed
precision target therefore cannot be validated at that confidence — see `DEC-048`.

---

### Phase 3 — Fine-tuning · ⬜ Not started

**Goal:** the core ML contribution. *Without this the project is an app that calls existing
models — an integration exercise rather than a project with a result of its own.*

Training data is VizWiz plus the merged public currency corpus (`DEC-047`); there is no
custom photographic dataset.

**Beat: 0.533**, the tuned-prompt result — not the 0.308 stock baseline (`DEC-017`).

Remaining headroom after prompting: abstention recall is 0.639 (88 of 244 still missed) and
precision has fallen to 0.726. Fine-tuning should aim to raise **both**, which prompting
alone could not do — every variant traded one for the other.

- [x] **Notebook written** — `notebooks/05_lora_finetune.ipynb`. Holds the prompt, the 500
      evaluation samples, the metric and the normalisation fixed at notebook 01's values so
      the result is comparable to 0.533; the suffix is *read from* `app/engines/smolvlm.py`
      rather than retyped, so it cannot drift from what the app ships
- [ ] Run it on a T4 and record the ablation
- [ ] **Weight abstention examples** — teaching "unanswerable" is worth up to +0.34 overall,
      versus +0.10 for a large gain in general answering ability
- [ ] Report abstention precision/recall separately, not just aggregate accuracy — a model
      that abstains on *everything* also scores well and would be useless
- [ ] Retrain the currency CNN on the merged multi-source corpus and re-check the five
      committed note fixtures — two of which fail today
- [ ] Re-run notebook 01 evaluation — **same N, same prompt** — for a fair comparison
- [ ] Train the MobileNet currency classifier (≥99% target) — `notebooks/03` is written
      and the engine is wired; needs a licensed Kaggle dataset (`DEC-022`)
- [ ] Ablation: stock vs VizWiz-tuned, and single-source vs merged currency corpus

**Exit criteria:** fine-tuned model beats 0.308 on the same slice, with the delta written up,
an ablation table produced, and abstention behaviour reported separately.

---

### Phase 4 — Integration · 🟡 Started early

**Goal:** one coherent app rather than five scripts.

Brought forward while model installs were pending — the interface needs no weights to build.

- [x] All five modes served through `app/router.py` with real engines
- [x] Mode routing: cheap specialist models first, VLM only for open-ended queries
- [x] Full pipeline wired: camera → mode → answer → IndicTrans2 → TTS
- [x] **Browser app** (`app/web/`) — camera capture, keys 1–5, space to capture
- [x] Accessible UX: `aria-live` announcements, ~4rem targets, AAA contrast, no
      dependence on sight, `prefers-reduced-motion` / `prefers-color-scheme`
- [x] Offline guaranteed by test — rendered page asserted to contain no external URLs
- [x] Captures deleted immediately after answering, including on engine error
- [x] **Run the browser app against real engines** — 2026-08-11, laptop: read, medicine and
      currency all answer through `AnswerService` with real weights. Exposed `DEC-045`
      (discarded `ocr_lang`), which fakes could not have caught
- [ ] Latency budget enforced per mode (see RISK-1)
- [x] **Separate scene description from VQA** — `VLMEngine` gained `describe()`, so the
      abstention suffix stays on `answer()` where the 0.533 was measured and off
      description, which asked for sentences and got `Paracip-500` (`DEC-031`). One
      loaded model still serves both
- [x] **Report every drug name found** — `DrugDatabase.find_matches()` returns all
      ingredients in printed order, `MedicineResult.drug_names` is a list, and a
      combination is spoken as one medicine (`DEC-046`)

**Exit criteria:** end-to-end spoken answer in Marathi from a photo, offline, <8s on laptop.

---

### Phase 5 — On-device + user study · ⬜ Not started

**Goal:** prove the "offline on a ₹10k phone" claim, and that blind users can actually use it.

- [ ] 4-bit quantization (GGUF) of the fine-tuned VLM
- [ ] Android port via llama.cpp / MediaPipe LLM Inference
- [ ] Resolve the PyTorch/PaddlePaddle process-isolation constraint (see DEC-006)
- [ ] Airplane-mode verification — no network calls anywhere
- [ ] User study with 5–10 visually-impaired participants; task-success rate
- [ ] Iterate on findings

**Exit criteria:** APK running offline on a real phone · user-study data collected.
**Fallback if the port slips:** laptop demo is the deliverable, Android becomes future work.

---

### Phase 6 — Evaluation & report · ⬜ Not started

- [ ] Final metrics: VizWiz accuracy vs baseline, per-mode precision/recall, latency
- [ ] Success bar: medicine ≥95% guardrailed precision · currency ≥99% · <8s for the OCR
      modes, with the VLM modes reported separately and honestly (`DEC-038`)
- [ ] Write up the results; the decision log below is the methodology section, already written
- [ ] **Demo rehearsal, in this order** (`DEC-038`): airplane mode on → medicine strip
      (expiry + MRP spoken in Marathi) → ₹500 note → Marathi newspaper read aloud →
      *then* the recorded scene-mode clip, introduced as needing a GPU
- [ ] Pre-load every model on the demo machine and leave the server warm — the 59s model
      load is one-time and should not happen in front of anyone (`RISK-9` covers the
      gated repos)
- [ ] Rehearse the two questions anyone watching will ask: "why is it slow?" (RISK-1, with the
      measured table) and "does it ever make things up?" (`DEC-037`, with scene mode's own
      30-tablets paragraph and the guardrail that stops it reaching the user)

---

## 3. Decision log

Records *why*, so decisions aren't relitigated and the report has evidence.

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Project = Drishti (offline blind-assistance VLM) | Chosen over scam-call shield and ISL translator: best mix of social impact, demo strength, and 2026–27 hiring skills |
| DEC-002 | Base VLM = **SmolVLM-Instruct**, not Moondream-2 | Measured on real VizWiz photos: 2.5× faster (1.75s vs 4.4s), terse answers (VizWiz scores by *exact match*, so verbosity ≈ 0), and native transformers classes instead of `trust_remote_code` |
| DEC-003 | OCR = **PaddleOCR**, not Surya or Tesseract | Surya 2.x needs a vllm/Docker inference server — incompatible with offline on-device. Tesseract returned noise on curved foil strips. PaddleOCR read every needed field at ≥0.96 |
| DEC-004 | PaddleOCR document preprocessing stays **ON** | Disabling it saved 13% wall time but destroyed accuracy (lost drug name, expiry, MRP). A hand-held strip is curved and rotated, so orientation/unwarping is load-bearing |
| DEC-005 | Devanagari via `lang='mr'` / `'hi'` | `'devanagari'`, `'hindi'`, `'marathi'`, `'deva'` all raise `ValueError` in PaddleOCR 3.7.0. Working codes resolve to `devanagari_PP-OCRv5_mobile_rec`. **Correction (2026-08-10):** only the *recogniser* is mobile — the run showed `lang='mr'` also pulling `PP-OCRv5_server_det` (87.9 MB), so the earlier "good for the Android target" was half right. Quality is confirmed regardless (1010 Devanagari chars of 1238 on real newsprint); the det model is a Phase-5 swap, and part of why `mr` and `en` cannot share a process (`DEC-035`) |
| DEC-006 | VLM and OCR must run in **separate processes** | PyTorch and PaddlePaddle each bundle an OpenMP runtime; co-loading kills the process with no traceback. A notebook annoyance now, an architecture constraint on Android |
| DEC-007 | Medicine names come **only** from a verified DB | Moondream fabricated a drug classification *and* ingredient list when asked about a medicine. A wrong drug name is a safety hazard, so the VLM is never trusted for it |
| DEC-008 | `enable_mkldnn=False` is mandatory | PaddleOCR 3.7.0 + PaddlePaddle 3.3.x crash on the PIR/oneDNN CPU path (Paddle #77340) |
| DEC-009 | Pin dependencies explicitly; introspect APIs at runtime | Four upstream breakages in one week (transformers v5, surya 2.x, Paddle oneDNN, PP-OCRv6 dropping Devanagari). Unpinned environments are not reproducible |
| DEC-010 | Downscale inputs to 1600px before OCR | 12MP phone photos waste time, risk a reported PaddleOCR CPU memory blowup, and the phone app must downscale anyway |
| DEC-011 | **Fine-tuning targets abstention first**, not general VQA skill | 49% of VizWiz-val is unanswerable (blurry/dark/mis-framed — what happens when the photographer cannot see). Stock SmolVLM scores 0.306 there because it guesses rather than declining. Lifting that subset to 1.0 moves overall 0.308 → 0.647 (+0.34); lifting *answerable* accuracy to 0.50 moves it only to 0.405 (+0.10) |
| DEC-012 | Text-reading questions route to PaddleOCR, not the VLM | Baseline failures include `545` vs `1545` and `Twelve years` vs `dog years`. The VLM is weak at fine-grained text; the OCR engine already reads strips at ≥0.96. Validates the routing architecture with measurements rather than assumption |
| DEC-013 | **Try prompt engineering before LoRA fine-tuning** | Baseline abstention is precision **0.913** / recall **0.258** — when the model says "unanswerable" it is almost always right, it just says it far too rarely (69 times against 244 opportunities). The capability exists; the *threshold* is miscalibrated. Recalibration may be reachable by prompt alone, which is a ~15-minute experiment against days of fine-tuning. Fine-tune only if prompting plateaus |
| DEC-014 | Report abstention precision **and** recall, never aggregate accuracy alone | A model that abstains on everything scores well on the unanswerable subset while being useless. Splitting the two makes that degenerate solution visible; `eval/analyze_results.py` computes both and a unit test guards the degenerate case |
| DEC-015 | Evaluation CSVs are versioned, not gitignored | Every claim in the report traces to one; they are ~60 KB. `.gitignore` negates `eval/results/*.csv` so results are reproducible and comparable across runs |
| DEC-016 | **Ship the `stakes` prompt; accept the precision drop** | Sweep of 5 variants on the baseline's own 500 samples. Naming the stakes ("the person asking is blind and cannot check your answer") beat listing failure criteria (0.508), stating the base rate (0.477) and demanding caution (0.302). Overall 0.308 → **0.533**; abstention recall 0.258 → 0.639 at the cost of precision 0.913 → 0.726. The trade is deliberate and asymmetric: a false abstention costs a retaken photo, a false answer can cost a wrong medicine |
| DEC-017 | **Phase 3 is measured against 0.533, not 0.308** | The +0.225 came from prompting and is already banked. Comparing a fine-tuned model to the stock-prompt baseline would credit fine-tuning with a gain it did not produce |
| DEC-018 | Strip an `Answer:` prefix before abstention matching | SmolVLM emits `"Answer: unanswerable"` intermittently (4 of 500). Unhandled, the app reads that string aloud to a blind user instead of offering retake guidance — a correctness bug in the product, not just 0.008 of unscored metric |
| DEC-019 | **The app is a browser app, not a desktop GUI** | One codebase covers the laptop demo and the phone, so the Phase-5 Android port becomes a PWA rather than native llama.cpp work — a large reduction in the riskiest milestone. Browsers also give camera access, screen-reader support and `aria-live` for free. Cost: a local server process must be running |
| DEC-020 | Captures are deleted immediately after answering | Users point this at prescriptions, bank documents and money. Retaining those on disk would contradict the privacy claim the project rests on. Deletion is in a `finally` block so it also happens when a model raises |
| DEC-021 | Offline-ness is enforced by a test, not a convention | A single CDN font or script would silently break the airplane-mode demo — and would only be discovered on stage. A test asserts the rendered page contains no external URLs |
| DEC-025 | Medicine mode takes the **earliest** of multiple expiry dates — kept as a **precaution**, after its original evidence was withdrawn (`DEC-034`) | The rationale first recorded here — "a real Paracip strip carries two dates, carton `OCT.2026` and blister `APR.28`" — was **false**: those dates are on two different sample strips. No capture has yet yielded two dates from one photo. The rule stays anyway, because the case is realistic (an Indian pack does print a carton date and a blister date, and a hand-held photo can catch both panels) and `candidates[0]` would then trust OCR's arbitrary line ordering. It is now labelled defensive rather than evidence-backed, and the report must not cite an observed failure it never had |
| DEC-026 | ~~Notebook 04 is split into a Paddle phase and a torch phase with a manual restart~~ **Superseded by DEC-027** | The split was built on a guess — that OCR + IndicTransToolkit in one kernel tripped `DEC-006`. It never worked, because §2 imported transformers (and TensorFlow) into the kernel *before* the "Paddle-only" phase began. A restart placed after a collision cannot prevent it. Kept here rather than deleted: the wrong diagnosis is why three days were lost, and the report's methodology section should say so |
| DEC-027 | **`import paddle` must precede `import paddleocr`**, and OCR runs in its own process | Found by stack trace, not inference. `paddleocr` defers loading paddle to `paddlex.utils.import_guard`, which imports torch and TensorFlow first; `libpaddle` then initializes into a process that already owns the glog/gflags/OpenMP symbols it needs and segfaults inside `paddle/base/core.py`. This is the real mechanism behind `DEC-006` — a **load-time** crash, which is why `max_side` and `fast` (both inference-time) changed nothing across three days of attempts. Fixed in `app/engines/paddle_ocr.py::_load()`; notebook 04 additionally runs OCR as a subprocess so the memory is reclaimed and a crash reports an exit code instead of killing the session |
| DEC-028 | **Debug native crashes with `faulthandler` + unbuffered output, never by hypothesis** | Three wrong diagnoses preceded the right one (OpenMP collision, then OOM, then unwarping memory), each costing a Colab run. `faulthandler.enable()` before the first import, plus `python -u` so a signal-killed process does not discard its buffered stdout, produced the answer in a single run. Staged progress markers reporting which heavy modules are loaded turned "it crashed" into "it crashed importing libpaddle with torch already resident" |
| DEC-029 | **`ai4bharat/indictrans2-en-indic-dist-200M` is a gated repo** — a first fetch needs an accepted licence and `HF_TOKEN` | Discovered when §6 failed with a 401 that transformers surfaces as a 22-frame traceback ending in a bare `OSError`, indistinguishable from a network fault. Does **not** compromise the offline claim: weights cache locally and run in airplane mode afterwards. It does mean a machine that has never downloaded them cannot be provisioned without credentials — see RISK-9. The translator now names the repo and the three fix steps, and notebook 04 preflights every model repo before downloading any of them |
| DEC-032 | **The guardrail database is NLEM 2022, generic names only** | `DEC-007` promises a *verified* database, which means nothing unless the list itself traces to an authority — the previous 30 names were hand-typed. The National List of Essential Medicines 2022 is published by the Ministry of Health via CDSCO: government-issued, dated, citable in the report, and small enough to commit (391 names from 384 entries, combinations expanded per component). Generic-only is deliberate: Indian labelling requires the generic on the pack, so brand strips still match through it (`CROCIN … PARACETAMOL TABLETS IP` → `Paracetamol`), while the ~250k brand names have no authoritative public list and inventing one would defeat the guardrail. Committed rather than fetched at runtime because the project is offline-first; `build_drug_db.py --check` proves the file still matches the source |
| DEC-033 | **`find_match` returns the longest match, not the first** | Real drug names nest: `Adrenaline` inside `Noradrenaline`, `Chloroquine` inside `Hydroxychloroquine`, `Prednisolone` inside `Methylprednisolone`, `Insulin` inside `Insulin Glargine` — 14 such pairs in NLEM. Returning the first hit made the answer depend on file order, so an alphabetical database would report a Noradrenaline vial as `Adrenaline`: a different drug, spoken confidently to someone who cannot verify it. The 30-name placeholder hid this completely because none of its entries nested — the bug was created by making the data real, not by changing the code |
| DEC-030 | ~~**`max_side` is a safety parameter, not a performance knob**~~ **WITHDRAWN — see `DEC-034`** | Claimed that downscaling to 1280 made OCR miss a carton date and report an expiry 18 months late. The failure never happened: `strip_paracip.jpg` carries exactly one expiry, `EXP.APR.28`, and the 1280 run read it correctly. Kept rather than deleted, per the `DEC-026` precedent — the report's methodology section should show how the wrong conclusion was reached |
| DEC-031 | **Description and VQA are separate verbs on `VLMEngine`, not one call with a flag** | `ABSTENTION_SUFFIX` says "answer in one to three words … otherwise answer exactly: unanswerable", contradicting the scene prompt's "one or two short sentences"; the first real run returned `Paracip-500` for a scene description. Rejected: editing the suffix (invalidates the measured 0.533, `DEC-016`) and a second `SmolVLMEngine` instance (loads 4.5 GB of weights twice). `describe()` alongside `answer()` keeps the measured prompt intact, keeps one model in memory, and puts the prompt next to the suffix it must stay consistent with instead of in the mode handler |
| DEC-022 | **Currency is scored by rupee error, not just accuracy** | Misclassification cost is asymmetric: ₹500→₹100 costs the user ₹400, ₹10→₹20 costs ₹10. Two models with equal accuracy are not equally good. Notebook 03 reports expected rupee error per identification and ranks the confusion matrix by rupee impact rather than frequency |
| DEC-034 | **Two sample strips were mistaken for one, inventing a safety bug that never existed** | `notebooks/00b` OCRs both fixtures in a single cell, so `expiry_candidates` printed `['OCT.2026', 'APR.28']`. The spike itself recorded this correctly — *"from two different strips. Harmless"* — but a week later the pair was written into `DEC-025` and `DEC-030` as one strip carrying a carton date and a blister date. It does not: `strip_paracip.jpg` (Paracip-500, 10 tabs) reads `MFD.MAY 25 EXP.APR.28`, and `strip_partial.jpg` (20 tabs, no drug name in frame) reads `MFG.NOV.2024 EXP.OCT.2026`. Two products. Consequences: `DEC-030` withdrawn, `DEC-025` demoted to a precaution, `max_side=1280` restored as a legitimate latency lever (RISK-1), and the fixture README now states the two are different strips. **Method lesson for the report:** the raw spike output was right and the summary written from memory was wrong — verify a claim against the artifact before promoting it to a decision, especially one that asserts a safety failure |
| DEC-035 | **One OCR language per process, and the checkpoint is written after every phase** | `DEC-027` established that paddle must be imported first, into a clean process. The 2026-08-10 run found the second half of that constraint: each *language* is a full pipeline (doc_ori + UVDoc + textline_ori + det + rec), and `mr` resolves to `PP-OCRv5_server_det` rather than a mobile det, so holding `en` open while loading `mr` passed 3.9 GB of 10.8 GB and was SIGKILLed. The expensive part was not the crash but the bookkeeping: the checkpoint was written once at the end, so a correct medicine result computed five minutes earlier died with the process and §6–§7 had nothing to run on. Phases are now separate subprocesses that persist before the next begins, and a Devanagari failure is a warning rather than fatal — nothing downstream depends on it. **Lesson for the report:** long pipelines need durable intermediate state, or an unrelated failure costs all the work upstream of it |
| DEC-036 | **`max_side=1280` is the default: 25–35% faster at no measured accuracy cost** | ~~First written as "neither a safety parameter nor a latency lever"~~ — that reading came from two passes on one Colab machine (46.5/54.5s at 1280 against 53.7/52.8s at 1600) where within-setting spread matched the between-setting gap. A controlled back-to-back comparison the same day, one process, one loaded model, three photos, disagrees consistently: medicine **56.2s vs 76.1s**, newspaper **69.4s vs 103.6s**, foil **58.0s vs 76.6s**. Accuracy is unaffected — identical drug name, expiry and MRP, and **1010 Devanagari chars at both sizes** on the fixture most likely to suffer from a downscale. **Method note for the report:** this knob has now been called dangerous (`DEC-030`), irrelevant (this entry's first version), then useful, and only the last came from a controlled comparison. Cross-session Colab timings are not evidence; same-session, same-process, same-model comparisons are |
| DEC-037 | **Scene mode's own output is the guardrail's best evidence — quote it in the report** | **Reproduced word for word on Colab (2026-08-10) and the laptop (2026-08-11)**, which makes it a repeatable property of the shipped model rather than one unlucky sample. Asked to describe the Paracip strip, SmolVLM produced fluent prose that was right about the drug and dosage and invented the rest: "contains **30 tablets**" (it holds 10, printed on the strip) and "made of a **clear plastic material** and has a **white backing**" (opaque foil). The invented details are indistinguishable in tone from the true ones. `DEC-007` was argued from a Moondream anecdote during selection; this is the *shipped* model on a *committed* fixture, reproducible from `notebooks/04_app_end_to_end_devnagari.ipynb`. Consequences: scene mode is framed as orientation, never as fact; every actionable field (drug, expiry, MRP) stays on OCR + database; and the report quotes this paragraph verbatim rather than asserting that VLMs hallucinate |
| DEC-038 | **The live demo is OCR-first; scene and ask are shown as a recording, with the GPU dependency stated** | Measured on a GPU-less runtime: medicine 56s, read 69s, but scene **481s** and ask **315s**. Medicine, read and currency never touch the VLM, so the three modes that carry the project's actual claim — a blind user reading a medicine strip offline in Marathi — are the three that stay demoable on a laptop. Rejected alternatives: *demo everything live* (five to eight minutes of silence on stage, and what gets remembered is the hang rather than the guardrail); *quantise until scene fits* (4-bit GGUF is Phase 5, unbuilt, and betting the review on unfinished work is how demos fail); *quietly drop scene and ask* (they are in the overview, and hiding a working feature because it is slow invites the question anyway, unprepared). Saying "this needs a GPU, here it is running on one, here is the measured CPU cost" is a stronger position than any of them — the honest number is defensible, a claimed 8s is not, and `RISK-1` stays visible instead of being papered over. Consequence for the report: latency is stated per mode tier, never as one aggregate |
| DEC-039 | **Currency has an eighth class, `background`: "no note in frame"** | The Kaggle dump (`DEC-022`'s dataset) ships 431 `Background__*.jpg` images with no note in them. `organize_currency.py` first treated these as unparseable junk and refused to run. Keeping them is strictly better: with seven denomination classes and nothing else, a softmax **must** name an amount, so a photo of a table, a hand, or a badly-missed shot returns a denomination — and money mode speaks it. The class gives the model somewhere honest to put that. Note this is a *different* failure from low confidence, so `app/modes/currency.py` answers it differently: `background` asks the user to reframe, `CONFIDENCE_THRESHOLD` asks for better light. Two consequences for evaluation: `background` is ~11% of the data, so headline accuracy is doubly misleading; and `class_value('background')` is ₹0, so a real ₹500 called `background` scores as a ₹500 error when it is in truth the *cheap* failure — the expensive one is calling an empty table ₹500. Report those separately rather than averaging them |
| DEC-040 | **`CONFIDENCE_THRESHOLD = 0.90`, chosen by rupee error rather than by answer rate** | The 0.85 in the code was a scaffolding guess (`DEC-024` promised to measure it). Notebook 03's sweep over 600 held-out images: `0.50` → 98.7% answered, ₹1.32 expected error; `0.85` → 90.3%, ₹1.00; **`0.90` → 85.0%, 0.9961 accuracy, ₹0.71**; `0.95` → 61.5%, ₹0.49 but answers too rarely. The notebook's original rule picked the *lowest* viable threshold and so recommended 0.50 — optimising for answering often, which contradicts `DEC-022`'s whole premise that rupee cost is the metric. The rule now minimises rupee error subject to answering ≥80%, and flags rows with fewer than 50 answered samples as noise (the 0.99 row scored 0.9667 off 30 samples and one error, which reads misleadingly as "stricter is worse") |
| DEC-041 | **The model's errors cluster on denominations whose numerals are prefixes of one another** | The costliest confusions are not random: `20 → 200` three times (₹540), `50 → 500` once (₹450), `2000 → 10` once (₹1990). Both frequent pairs differ by a trailing zero, and both err *upward* — the user is told they hold ten times what they do, which is the direction that gets someone short-changed at a counter. One `background → 200` is the same class of harm: phantom money where there is no note. Two consequences: Phase-2 note photography should over-sample the 20/200 and 50/500 pairs rather than spreading evenly across denominations, and the report should show this table instead of the 0.9883 headline, because "98.8% accurate" hides that the residual errors are concentrated in the expensive direction |
| DEC-042 | **`background` learned *this dataset's* backgrounds, not "no note present"** | Verified on the laptop 2026-08-11 against three note-free images. The medicine strip returned `50` at **0.870** confidence with `background` at 0.038; the partial strip `500` at 0.578; the Marathi newspaper `100` at 0.705. All three declined only because `CONFIDENCE_THRESHOLD` is 0.90 — the strip missed being announced as a ₹50 note by 0.03. So `DEC-039` is right that the class is necessary and wrong that it is sufficient: its 431 training images are tables and hands from one capture session, which does not generalise to foil, newsprint or anything else a camera gets pointed at. Consequences: the threshold is currently the *only* real defence and must not be lowered on answer-rate grounds; Phase 2 must collect **diverse negatives** — household surfaces, packaging, paper, fabric, floors — not just more notes; and the report should state that money mode is validated on notes and on this dataset's backgrounds, not on arbitrary scenes |
| DEC-043 | **Keep `CenterCrop` for evaluation; the real-photo gap is data, not preprocessing** | Five handheld notes shot on 2026-08-11: top-1 correct on all five, but only **3 of 5 cleared the 0.90 threshold** — ₹50 at 0.882 and ₹200 at 0.342. The two weak ones are the two elongated frames (aspect 2.04 and 2.10 against 1.33–1.36 for the rest), which suggested `Resize(256)`+`CenterCrop(224)` was cutting away the corner numerals. Two alternatives were measured on the notebook's own 600-image test split with `eval/eval_currency.py`: **center_crop 0.9883 / ₹5.37, letterbox 0.9850 / ₹7.75, squash 0.9817 / ₹7.82.** So `squash` helps the hand-shot photos and *hurts* the dataset, because the Kaggle images are already cropped tight to the note and have no margin to preserve. Changing the transform would trade a measured 600-image result for an unmeasured 5-image one. The gap is that the training data does not look like deployment: **the 0.9961 conditional accuracy is measured on tightly-cropped images and overstates what a blind user gets.** The fix is Phase-2 photographs of notes framed loosely and held at arm's length, then retraining — not a preprocessing change |
| DEC-044 | **The paddle/torch import order is inverted on Windows** | `DEC-027` established that paddle must be imported *before* paddleocr, because paddlex drags torch in and libpaddle then segfaults. On Windows the same ordering breaks the other library instead: with `paddle\libs\libiomp5md.dll` already resident, torch fails at import with `OSError: [WinError 127] ... Error loading torch\lib\shm.dll`. Importing torch first, then paddle, then paddleocr works on Windows; on Linux it is what `DEC-027` proved fatal. `_load()` now branches on `sys.platform`, tolerating a missing torch for OCR-only environments. Two things this pins down: the conflict is **not** avoidable by declining to use the VLM, since `paddlex/inference/utils/official_models.py` imports `modelscope` unconditionally and that pulls torch regardless; and `DEC-006`'s "separate processes" constraint is now a *cross-platform* requirement rather than a Colab quirk, which raises the cost of the Phase-5 Android port. Found on the laptop, not on Colab — the demo machine is the one that matters |
| DEC-045 | **The web app selects the OCR engine per request; `ocr_lang` was being discarded** | Found by driving the real API with the committed fixtures rather than the camera. `ocr_lang` was parsed from the form, validated against the language table, and then never used: `AnswerService` held a single English `PaddleOCREngine` built at startup. Reading the Marathi newspaper through the browser returned `Tach taaRa firast HoH HEST machals` — the Latin recogniser transliterating Devanagari. **Nothing raised**, so a blind user hears confident gibberish with no signal that the wrong model ran; the same request now returns **1010 Devanagari characters**. The front end was half the bug: it sent `ocr_lang` only for medicine mode, so Read never asked for a script at all. Engines are built lazily and cached per script rather than pre-built for every language, because two live pipelines peaked at 11.65 GB (`DEC-035`). **Method note:** this was invisible to the test suite because the fakes return whatever they are given, and invisible in manual testing because garbage output looks like a bad photo. Driving the real service with known-good fixtures is what separated an app bug from camera quality |
| DEC-046 | **Combination strips report every ingredient, resolved by occurrence counting** | An Indian combination tablet (`IBUPROFEN 400mg PARACETAMOL 325mg`) is one product with several actives, and naming only one hides an ingredient the user may be avoiding or reacting to. The naive fix — return every database hit — would have been *worse* than the bug it replaced: `Adrenaline` is a substring of `Noradrenaline`, so one vial becomes two drugs, one of which is not in the user's hand. Inventing a medicine beats mislabelling one for sheer harm. `find_matches()` therefore reports a short name only when it occurs more often than the longer names containing it can account for — `NORADRENALINE` gives adrenaline×1 / noradrenaline×1, so Adrenaline is suppressed; `ADRENALINE … NORADRENALINE` gives ×2 / ×1, so both are reported. Names come back in printed order so the spoken answer tracks the strip. Phrasing says "a combination of A and B" rather than two sentences, which would imply two tablets. `MedicineResult.drug_names` is the list; `drug_name` survives as a property because notebook 04's checkpoint JSON reads it |
| DEC-047 | **No self-collected dataset; build from licence-clean public sources** | Decided 2026-08-11. The plan called for ~800 photographs, and that is the one part of the project no one else can do — but it is also the part with the weakest link between effort and result. Half of it (medicine strips, labels) trained *nothing*: those modes run pretrained OCR plus a database lookup, so photographs only measure them. Scene data was worse than the alternative, since VizWiz was shot by blind photographers and a sighted person can only simulate that. What remains genuinely camera-shaped is currency, and the diversity it lacks can come from merging **independent public sources** whose contributors shot at different distances on different surfaces. Currency negatives come from VizWiz, which is thousands of photographs of arbitrary objects taken by exactly the target population. **The cost, stated plainly:** the project can no longer claim an original Indian dataset, and that was listed as what made it more than an integration exercise. What is left as its own: the routing architecture, the guardrail, the measured prompt result (0.308 → 0.533), the rupee-weighted metric, and a decision log that records what was believed wrongly and how it was caught. That is a defensible contribution; a dataset that was never going to be photographed is not |
| DEC-048 | **Medicine mode's ≥95% precision target is not validatable, and must not be claimed** | No public dataset of Indian medicine strips with legible generic names and expiry dates exists under a licence permitting redistribution, and pharmacy product photography is not licensed for it. With `DEC-047` ruling out photography, the evaluation set is the committed fixtures. Two strips cannot support a 95% claim at any useful confidence. The number therefore does not go in the writeup as a result. What *is* reportable: the guardrail's behaviour on the NLEM database, which unit tests cover exhaustively including the nesting pairs and combinations; and a measured statement over a declared sample — "on N strips it named no drug it could not verify" — with N printed beside it. Opportunistic photographs of strips already in the house are welcome and change nothing about the claim until N is large. Recorded because an unvalidated safety number is worse than no number: it invites exactly the trust the guardrail exists to withhold |
| DEC-049 | **The training set has 23% redundancy and 7 contradictory labels; report the leakage-corrected cost, not the headline** | Building the merge script surfaced this inside the CC0 base dataset itself, before any second source was added: of 4,002 images, **532 are byte-identical duplicates and 387 more are near-duplicates** (perceptual hash, Hamming ≤ 4) — 23% redundant. Because notebook 03 random-splits all 4,002, **33.5% of the test split (201 of 600) is a duplicate or near-duplicate of a training image.** Measured effect, and it is not what was first assumed: accuracy barely moves, **0.9883 → 0.9875 on the 399 clean images**, so the model genuinely recognises notes. The *cost* metrics move a lot — expected error **₹5.37 → ₹7.52**, and at the 0.90 threshold **₹0.71 → ₹1.09, a 54% understatement** of what a wrong answer costs, which is the number `DEC-022` exists to track. On the leaked subset the model scores a perfect 1.0000 accuracy and ₹0.00 error above threshold, which is memorisation, not recognition. Worse, **7 images are byte-identical with contradictory labels** — `200 vs 20`, `2000 vs 20`, and five `50 vs background` — and those pairs are exactly the confusions `DEC-041` and `DEC-042` measured. The model was taught a contradiction on precisely the classes it gets wrong. Consequence: quote the clean-split numbers, deduplicate before retraining, and re-derive the threshold on uncontaminated data rather than inheriting 0.90 |
| DEC-050 | **Leakage is same-class only; cross-class look-alikes are hard negatives, not duplicates** | The first leakage check compared every test image against every training image regardless of label, and reported 1.9% residual leakage on a corpus that had just been deduplicated. All 16 were cross-class, and inspecting them showed why: `pypiahmad` photographed each denomination in one fixed setup, so `INDIA500_130` and `INDIA200_130` share a background, a light and a pose. A 64-bit perceptual hash keys on all of that rather than on the note, and matches them at Hamming ≤ 4. They are genuinely different denominations. Two consequences. **The check was wrong:** a test image resembling a *different-class* training image cannot inflate the score, because the model saw those pixels with a different label — that is label noise or a hard negative, and it hurts rather than helps. Leakage means same image, same label, both sides of the split; measured that way the corpus is at **0.0%**, down from 33.5% (`DEC-049`). **The merge must not dedup across classes:** doing so would delete real training data and, in the `50`/`background` case, delete whichever side of a label conflict happened to sort second. Both counts are now reported separately, since a rising cross-class count would itself be worth investigating |
| DEC-051 | **The systematic confusions are gone; ₹2000 now carries 86% of the remaining cost** | Retrained on the merged 5,602-image corpus, first run with a verified-clean split (0.0% leakage). Headline metrics look worse than the old contaminated ones and even than the old *clean* subset — accuracy 0.9875 → 0.9810, expected error ₹7.52 → ₹10.87 — but the test set is harder (pypiahmad's distribution plus VizWiz negatives) and the failure *character* changed completely. `DEC-041`'s systematic prefix pairs are **gone**: ₹20→₹200 appeared three times before and zero times now, ₹50→₹500 likewise, and ₹500 precision is 1.000. What remains is six scattered singletons. **Four of them involve the ₹2000 note** — `2000→background`, `10→2000`, `20→2000`, `2000→100` — and at ₹1,900–2,000 each they account for **₹7,870 of the ₹9,131 total, or 86% of all rupee cost**. Without them expected error would be **₹1.50**. The ₹2000 was withdrawn from circulation in May 2023, so the class the app is worst at is one a user is least likely to hold. Options: drop it and report the corpus as covering circulating denominations; or keep it and report expected error both ways. Do not average it away silently — `DEC-022` exists because rupee cost is the metric, and here one obsolete class is the metric |
| DEC-052 | **The benchmark got worse and deployment got better — trust the fixtures** | The retrained model scores *lower* on its own test split than the old one did on its clean subset (0.9810 against 0.9875, ₹10.87 against ₹7.52), and yet **all five real handheld notes now answer, against three of five before**. The gain lands precisely where `DEC-043` predicted: `curr-200` went **0.342 → 0.926** and `curr-50` **0.882 → 0.967**, the two loosely-framed shots that were failing, while the two already-comfortable fixtures moved by −0.036 and −0.005. Merging independent sources bought capture diversity, exactly as `DEC-047` argued it would when self-collection was ruled out. Two lessons worth carrying: **a harder test set reads as a worse model**, so accuracy across differently-composed corpora is not comparable and the writeup must say which corpus each number came from; and **a five-image fixture set caught something 840 test images could not**, because the fixtures are the only data drawn from deployment rather than from the training distribution. Keep them, keep running them, and report them beside the benchmark rather than underneath it |
| DEC-053 | **The seven label conflicts are resolved by hash, and one of them is watermarked stock photography** | Looked at the images. In all seven `vishalmane109` cases the denomination folder is right: `200.__115` is a bundle of ₹200 notes, `2000__60` is an unmistakable ₹2000, and `50__276`–`280` are ₹50 **RBI SPECIMEN** notes filed as `background` — those five teach the model to decline on real money, the guardrail pointed backwards. `RESOLVED_CONFLICTS` records the correct class per SHA-256, so a resolution cannot drift onto another file. **Honest note: the merge was already producing these labels, by accident.** Entries sort by path, and `training/200/` happens to precede `training/20/`, so the right copy won a string comparison. Renaming a file would have flipped it silently. The table makes it deliberate and reviewable. They are listed rather than inferred because no rule is safe: "prefer the denomination over background" breaks the moment a genuine background image is misfiled under a denomination, which teaches phantom money. **Separately and more awkwardly:** `200.__115` carries a visible Shutterstock watermark, inside a dataset Kaggle labels CC0-1.0. A CC0 declaration by an uploader is not evidence they held the rights to what they uploaded. It does not change the merge, but it does mean **no dataset image should be reproduced in the writeup** — use the five self-photographed fixtures, which are unambiguously ours |
| DEC-054 | **Drop the ₹2000 class: it was an attractor, not just an expensive class** | Reversing the reasoning in `organize_currency.py`, which kept ₹2000 on the argument that a model never shown one would confidently misname it. The retrain measured the opposite problem. Of the four costly errors, **two are `10→2000` and `20→2000`** — the class was pulling notes people carry every day into ₹1,990 mistakes, and those errors exist *only because the class exists*. Dropping it removes all four: the `→2000` predictions become impossible and the `2000→` cases have no images. Expected error falls from **₹10.87 to about ₹1.50**, and the corpus goes to 5,010 images across 7 better-balanced classes. The residual risk is a user holding a genuine ₹2000 — withdrawn from circulation May 2023, still legal tender, effectively absent by 2026 — and the confidence threshold plus the `background` class give that somewhere safe to fail. **Costs nothing in the app**, because class names travel inside the checkpoint (`DEC-023`): the corpus changes, the code does not. `--exclude` keeps the choice reversible, and the writeup should state that the model covers circulating denominations rather than implying full coverage |
| DEC-055 | **VizWiz train is not on Hugging Face; the fine-tune reads the official archive** | `notebooks/05` assumed `load_dataset('lmms-lab/VizWiz-VQA', split='train')` and got `ValueError: Bad split. Available splits: ['test', 'val']`. That repository is an *evaluation* dataset built for lmms-eval pipelines, which is why notebook 01 could use it for `val` and Phase 3 cannot use it for training. The 20,523-pair train split exists only as an 11.3 GB archive. **Training on `val` was the tempting shortcut and is rejected**: evaluation is `val[:500]`, so fine-tuning on the remainder of the same split would flatter the headline in a way no reader could verify, and `DEC-017` already insists the 0.533 comparison be honest. Instead the annotations come from `download_vizwiz.py` (21 MB) and images are pulled out of the archive individually over HTTP range requests — a few thousand files rather than eleven gigabytes. The transport now lives in `data/scripts/vizwiz_images.py`, shared with the negatives sampler, so the connection-reuse fix that took it from six images a minute to eighty-four exists in one place rather than two |
| DEC-056 | **A cache check must compare against what was asked for, not merely that something exists** | `EXCLUDE = ['2000']` was set, notebook 03 ran, and the model trained on ₹2000 anyway. The setup cell asked *"do denomination folders exist?"* rather than *"do the folders I asked for exist?"*, found the previous corpus still on the VM, and skipped the rebuild — so a 35-minute training run answered a question nobody had asked, and its numbers (0.9774, ₹9.43) describe the 8-class corpus. The check now compares the class folders on disk against the set implied by `EXCLUDE` and rebuilds on any mismatch, printing both lists so the reason is visible. Same family as the `--clean` guard in `merge_currency.py`: a cache keyed on existence rather than on inputs is not a cache, it is a silent staleness bug, and both cost a full run before being noticed. **A useful accident:** that run is a repeat of the previous configuration, so the two together measure run-to-run variance — accuracy 0.9810 vs 0.9774, expected error **₹10.87 vs ₹9.43**. The rupee metric swings by ₹1.4 between identical configurations because a handful of ₹2000-scale errors dominate it. Any claimed improvement smaller than that is noise, and the writeup should say so |
| DEC-057 | **Fit the fine-tune to the T4 without changing what is measured** | Training OOMed on a 14.56 GB T4 at batch 2. SmolVLM tiles each image into sub-images, so one sample is well over a thousand visual tokens and the stored *activations* — not the 4.5 GB of fp16 weights — exhaust the card. The obvious fix, `do_image_splitting=False`, is **rejected**: notebook 01 measured 0.533 with splitting on, and turning it off would mean the fine-tuned number answers a different question (`DEC-017`). Fixed on the memory side instead: gradient checkpointing, batch 1 with 8-step accumulation to keep the effective batch, `expandable_segments` for the fragmentation the error itself pointed at (510 MB reserved but unallocated), and `N_TRAIN` cut from 3,000 to 1,500 so the run fits a free-tier session. Two details that would otherwise look like a model that refuses to learn rather than a numerics bug: **LoRA parameters are cast to fp32**, because Adam on fp16 master weights underflows at these update magnitudes, and a **GradScaler** is used because the T4 is Turing and has no bfloat16. The general rule this is an instance of: when a run does not fit, change the machinery before changing the measurement |
| DEC-058 | **The Latin OCR path drops to `PP-OCRv6_small`: 3.2× faster, nothing lost. Devanagari cannot follow** | `DEC-036` ruled out `max_side` and pointed at the model tier; `eval/bench_ocr.py` measured it. English defaults were `PP-OCRv6_medium_*`; the **small** tier reads the strip in **11.8 s against 39.4 s** and still finds drug name, expiry and MRP — medicine mode end to end went **41.2 s → 12.9 s**, same spoken answer. **`PP-OCRv6_tiny` is the trap and is deliberately unused:** 6.3× faster and it loses the expiry date, which on a stopwatch looks like the best result on the table and in the hand tells a blind user a medicine is safe when nothing was read. That is `DEC-030` exactly, which is why the benchmark scores fields alongside seconds and fails a config that drops one. **Devanagari keeps the server detector.** Both lighter detectors returned **zero** Devanagari characters on a page the default reads at 1010 — total failure, not degradation — so `lang in DEVANAGARI_LANGS` falls through to PaddleOCR's own choice. Consequence for RISK-1: the Latin path is close to usable at ~13 s, Devanagari remains ~96 s and unimproved, and the ₹10k-phone claim still rests on a server-class detector for Indic script. That is a Phase-5 problem now named rather than assumed away |
| DEC-059 | **Dropping ₹2000 improved accuracy *and* cost, and removed the catastrophic tail** | `DEC-054` argued the class was an attractor rather than merely an expensive one. Measured, on 5,010 images across 7 classes with a verified-clean split: accuracy **0.9774 → 0.9827**, expected error **₹9.43 → ₹2.48**, and at the threshold **₹2.91 → ₹0.68**. `DEC-051` predicted about ₹1.50; ₹2.48 is the same order and far outside the ±₹1.4 run-to-run band `DEC-056` established, so the effect is real rather than noise. **Both metrics moving together is the informative part**: a hard class being removed would have raised accuracy while leaving cost roughly proportional. Instead ₹10 and ₹20 stopped being pulled into ₹1,990 mistakes, which is what an attractor does. The worst single error fell from **₹2,000 to ₹400** — the catastrophic tail is gone, not merely rarer. The threshold sweep re-derived **0.90** independently for the third time, on a third corpus, so that constant now rests on repeated measurement rather than one run |
| DEC-060 | **LoRA tied with the prompt baseline, and over-abstained because it learned the training prior** | 1,500 VizWiz-train examples, r=16 on the language-side attention projections, 100 minutes on a free T4, loss 17.9 → 1.73. Result **0.521** against the prompt-only **0.533** — but a paired bootstrap over the same 500 samples puts the difference at **[-0.058, +0.036]**, straddling zero. The honest reading is a **tie, not a loss**; claiming prompting won would overclaim as badly as claiming training did. **The informative number is not the accuracy.** Abstention recall rose 0.639 → 0.664 while precision fell 0.726 → **0.581**, and needless refusals of answerable questions went **59 → 117**. Buying +0.025 recall for -0.145 precision is the signature of a shifted threshold, not improved discrimination — had the model learned to tell the two cases apart, both would have risen, which is exactly what `DEC-014` predicted training should deliver and prompting could not. **The likely cause is a knob I set**: `ABSTAIN_RATIO = 0.45` against a true unanswerable rate of 49%, and the model came out abstaining on **56%**. It learned the training mix's prior rather than a decision rule. The §6 guard only fires above 75%, so it passed silently — the guard tested for the degenerate case and not for the realistic one. **This confounds the finding.** Until a run at the natural 28% rate exists, the claim this supports is 'fine-tuning at a 45% abstention prior ties with prompting', not 'fine-tuning does not help'. Those are different papers |
| DEC-061 | **Prediction, recorded before run 2: matching the natural abstention rate recovers precision without recovering overall accuracy** | `ABSTAIN_RATIO` goes 0.45 → **0.28**, VizWiz-train's own rate, holding everything else fixed. If `DEC-060`'s diagnosis is right — the model learned the training prior rather than a decision rule — then run 2 should abstain on **roughly 40–46%** rather than 56%, precision should recover to **0.68–0.78**, recall should fall back to **0.55–0.62**, and overall should land **within noise of 0.53 again**. Writing the interval down first is the point: a prediction made afterwards would fit any result. **Both outcomes are publishable and they say different things.** If it lands there, abstention on VizWiz is threshold-bound rather than capability-bound, prompting already captures essentially all of it, and a 100-minute fine-tune buys nothing a one-line prompt did not — a genuine negative result, and the honest headline of Phase 3. If instead precision *and* recall both rise, `DEC-014`'s original hypothesis survives and run 1 was simply mis-parameterised. What is no longer possible is the outcome run 1 produced, because the confound that caused it has been removed |
| DEC-062 | **The ₹2000 retrain traded one withheld note for two fixed false positives, and the threshold stays at 0.90** | Fixtures re-run on the laptop against the 7-class checkpoint, because a benchmark cannot see this (`DEC-052`). **Real notes: 4 of 5 answer, down from 5 of 5.** `curr-200` fell 0.926 → **0.784** — it still predicts `200` correctly, so this is a *withheld correct answer*, not a misread, and the cost is a retaken photo. **Non-note images: 2 of 3 now return `background`, up from 0 of 3.** `strip_partial` went `500`@0.578 → **`background`@0.861**, `newspaper-marathi` went `100`@0.705 → **`background`@0.901**. `DEC-042` — that `background` had learned this dataset's tables rather than 'no note present' — is largely resolved, and the VizWiz negatives are what resolved it. **These two failures are not equal and must not be netted off.** A withheld note costs a retake; a medicine strip announced as ₹100 to someone who cannot check is the failure this project exists to prevent. **The threshold therefore does not move.** `strip_paracip` still reads `100` at **0.840**, so lowering the bar to 0.78 to rescue `curr-200` would ship that false positive — headroom between the worst false positive and the bar is **0.06**, and that thinness, not the fixture count, is the number to watch |
| DEC-063 | **A missing GPU must stop a notebook, not warn it** | Notebook 05 crashed twice with "session crashed after using all available RAM", which reads as a memory bug and is nothing of the kind: the Colab runtime had **no CUDA driver at all**. The model cell loads `float32` when `DEVICE == 'cpu'` — about **9 GB for 2.25B parameters on a 12.7 GB runtime** — so it exhausted host RAM ten minutes after starting, having already downloaded 4.5 GB of weights. The notebook *did* detect this and **printed a warning**, then continued. **That is the bug.** A warning at the top of a long run scrolls off screen and the failure surfaces later, disguised as something else; the first diagnosis chased the evaluation buffer instead. Notebook 05 now raises, before any download. Related and previously unnoticed: **notebook 03 trained on CPU too** (290s/epoch against 170s), so the free-tier GPU quota had been exhausted for some time without either notebook saying so plainly. Free Colab GPU resets in roughly a day; Kaggle offers 30 GPU-hours a week and is the fallback |
| DEC-023 | Class names live in the checkpoint, never in code | A checkpoint trained on differently-ordered folders would silently relabel every prediction. Hardcoding the order makes "₹500 reported as ₹10" a one-line mistake, which is the exact failure Money mode exists to prevent |
| DEC-024 | The currency confidence threshold is measured, not assumed | `CONFIDENCE_THRESHOLD = 0.85` was a guess made while scaffolding. Notebook 03 §5 sweeps it and refuses to recommend any value that cannot reach ≥99% accuracy while still answering ≥80% of the time — better to declare the mode unready than to ship a confident wrong denomination |

---

## 4. Risk register

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| RISK-1 | **Latency far past the <8s target** — 2026-08-10, model load excluded: OCR **46.5–54.5s** per photo at *either* `max_side`, translate+TTS 33.8s cold / 9.7s warm, VLM 65.5s | 🔴 High | Levers by measured payoff: (1) **`max_side=1280` — banked**, 25–35% (`DEC-036`); (2) **small-tier Latin models — banked**, medicine mode 41.2 s → 12.9 s at no accuracy cost, though Devanagari cannot follow and stays at ~96 s (`DEC-058`); (3) ~~swap the medium/server models for mobile~~ — `en` resolves to `PP-OCRv6_medium_det`/`_rec` and `mr` to `PP-OCRv5_server_det`, none of them the mobile variants the Android target needs anyway, so this serves Phase 5 too; (3) drop `use_doc_unwarping` per mode — `DEC-004` measured it at 13% and destroying accuracy *on foil*, but a flat newspaper may not need it, making it a per-mode rather than global choice; (4) **keep the VLM off the demo path** — scene 481s and ask 315s are what blow the budget, while medicine, read and currency never touch it, so a CPU-only review demo should be driven by the OCR modes with scene/ask shown as a recorded clip. Model load (59.2s) is one-time and must be quoted separately, never folded into the per-photo figure. If <8s still can't be met, restate the target honestly — a demo that answers in 15s is defensible, a false claim of 8s is not |
| RISK-2 | ~~One source deep~~ **Largely retired** — four sources merged, and all five real-note fixtures now answer (`DEC-052`) | 🟢 Low | Self-collection is out (`DEC-047`), so diversity has to come from merging independent public sources and from VizWiz negatives. Residual risk stays: no public dataset has Indian notes photographed *by blind users at arm's length*, which is the case `DEC-043` measured as failing. The five committed fixtures are the honest check, and the writeup must report them rather than only the test split |
| RISK-3 | **No NGO contact yet** | 🔴 High | Email 5–6 today; replies take weeks, scheduling weeks more. Without this, objective 5 fails |
| RISK-4 | Android port may not fit the timeline | 🟡 Medium | Laptop demo is the committed deliverable; Android is explicitly a stretch goal |
| RISK-5 | Fine-tuning may not beat the stock baseline | 🟡 Medium | Even a negative result is publishable if measured honestly; ablation table makes it defensible |
| RISK-6 | Upstream dependency churn breaks a working pipeline | 🟡 Medium | Pins + `requirements.txt` + DEC-009; re-verify before the demo |
| RISK-7 | ~~Devanagari OCR quality unknown~~ **Largely retired** | 🟢 Low | Measured 2026-08-10: 1010 Devanagari chars of 1238 on a photographed Maharashtra Times page, headline and body both accurate. `devanagari_PP-OCRv5_mobile_rec` works on real newsprint, so the English-only fallback is no longer needed. Still open: the foil case (`पॅरासिप-500`) and the 1600 comparison, both cut short by the OOM — neither threatens the mode |
| RISK-8 | Single-person bus factor on Colab sessions | 🟢 Low | Notebooks are committed; results downloaded to `eval/results/` |
| RISK-9 | ~~**Gated model repos block provisioning a fresh machine**~~ **Retired for the demo laptop** (`DEC-029`) | 🟢 Low | Runtime offline-ness is unaffected — weights cache locally. But a demo laptop set up from scratch needs an HF account, an accepted licence and a token. **Done 2026-08-11 on this laptop:** licence accepted, `hf auth login` cached to `%USERPROFILE%\.cache\huggingface	oken`, and IndicTrans2 plus the MMS voices downloaded and cached. The offline claim is intact — they run in airplane mode now. Still applies to any *other* machine, so a replacement laptop before review week needs the same three steps, and the same is true if a gate appears upstream on a model that is currently open |

---

## 5. Success criteria (final)

| Metric | Target |
|---|---|
| VizWiz accuracy | Fine-tuned model **beats** the stock baseline on the same slice |
| Medicine mode precision | ≥95%, guardrailed (declines rather than guesses) |
| Currency accuracy | ≥99% |
| End-to-end spoken answer, **OCR modes** (medicine, read, currency) | <8s on laptop CPU — the live-demo path (`DEC-038`). Currently 56s; the gap is RISK-1 |
| End-to-end spoken answer, **VLM modes** (scene, ask) | <8s **with a GPU**. On CPU it is 315–481s, measured, and no realistic optimisation closes that — reported honestly rather than targeted |
| Offline operation | Zero network calls — verified in airplane mode |
| User study | 5–10 visually-impaired participants, task-success rate recorded |

---

## 6. Document map

| File | Purpose |
|---|---|
| **`docs/BUILD_PLAN.md`** | **This file — phases, status, decisions, risks. The single source of truth.** |
| `README.md` | What the system is; architecture; how to run it |
| `docs/OVERVIEW.md` | What the project is and why: problem, objectives, literature, methodology |
| `docs/dataset_guide.md` | Phase-2 sources, licences, dedup and the evaluation caveats |
| `notebooks/00_feasibility_spike_colab.ipynb` | VLM comparison + translation/TTS spike (Colab GPU) |
| `notebooks/00b_ocr_spike.ipynb` | OCR engine selection (CPU, no GPU) |
| `notebooks/01_vizwiz_baseline.ipynb` | The baseline number (Colab GPU) |
| `notebooks/02_abstention_prompts.ipynb` | Prompt sweep to recalibrate abstention (Colab GPU) |
| `notebooks/05_lora_finetune.ipynb` | Phase 3: LoRA fine-tune on VizWiz, measured against 0.533 |
| `eval/results/` | Downloaded run artifacts — the evidence trail |

**Maintenance rule:** update the status dashboard and decision log in the same commit as the
work itself. A build plan that lags the code is worse than none.
