# Drishti — Build Plan

> **This is the single source of truth for scope, phases, status and decisions.**
> `README.md` describes *what the system is*. `synopsis.md` is the college submission
> document. Neither carries a timeline — if a date or milestone appears anywhere else,
> it is stale and should be deleted in favour of this file.
>
> **Last updated:** 2026-08-11 — currency mode trained and verified on the laptop
> (`DEC-040`–`DEC-042`). Previously 2026-08-10: full end-to-end run, every mode verified
> against real models (`DEC-035`–`DEC-037`).
>
> **Phase:** 1 of 6 · **Academic year:** 2026–27
>
> **Baseline:** stock SmolVLM-Instruct scored **0.308** on 500 VizWiz-val samples.
> Prompt engineering alone lifted it to **0.533** (+0.225, no training). Phase 3
> fine-tuning must beat **0.533**, not 0.308 — see `DEC-016`.

---

## 1. Status dashboard

| Phase | Window | State |
|---|---|---|
| 0 — Feasibility & setup | Jul 2026 | ✅ **Complete** |
| 1 — Baselines & core pipeline | Aug – Sep 2026 | 🟢 **Exit criteria met** — all five modes verified against real models 2026-08-10; only the two non-code items remain (synopsis approval, NGO outreach) |
| 2 — Data collection | Sep – Nov 2026 | 🔴 Barely started (3 photos of ~700) |
| 3 — Fine-tuning | Nov – Dec 2026 | ⬜ Not started |
| 4 — Integration | Jan 2027 | ⬜ Not started |
| 5 — On-device + user study | Feb 2027 | ⬜ Not started |
| 6 — Evaluation & report | Mar 2027 | ⬜ Not started |

**Hard gates:** Sem-7 review ≈ Oct 2026 (needs Phase 1 done) · Final submission ≈ Mar–Apr 2027.

### Component status

| Component | State | Evidence |
|---|---|---|
| App skeleton (router, 5 modes, guardrail) | ✅ Done | 162 tests passing |
| OCR engine (PaddleOCR) | ✅ Wired | `app/engines/paddle_ocr.py`. Verified on the **laptop** 2026-08-11: medicine and read modes both run locally, after fixing an inverted paddle/torch import order on Windows (`DEC-044`) |
| Medicine mode end-to-end | ✅ Works | Colab 2026-08-10 on `strip_paracip.jpg`: real OCR → `"This is Paracetamol. It is valid until APR.28. MRP is 10.30 rupees."` — drug name, expiry and MRP all correct against the strip |
| Read mode (English) | ✅ Works | via same engine |
| Read mode (Devanagari) | ✅ **Works** | Colab 2026-08-10: `newspaper-marathi.png` → **1010 Devanagari chars of 1238** at *both* 1280 (69.4 s) and 1600 (103.6 s). Headline and body both legible (`खंक तिजोरीमुळे भिवंडी भकास`, `ठाणे : अरुंद रस्ते…`). Foil is thin as expected: 14 chars @1280, 12 @1600. `RISK-7` retired |
| VizWiz baseline (stock prompt) | ✅ **0.308** | notebook 01, 500 samples, 1.21 s/answer |
| VizWiz with tuned prompt | ✅ **0.533** | notebook 02, same 500 samples, no training |
| Currency mode | ✅ **Trained** | Colab T4 2026-08-10, 12 epochs on 4002 images / 8 classes: test accuracy **0.9883**, expected error **₹5.37** unconditional; at `CONFIDENCE_THRESHOLD=0.90` it answers 85% of the time at **0.9961** accuracy and **₹0.71** (`DEC-040`). Checkpoint 6.2 MB. Misses the ≥99% bar *unconditionally* — it clears it only by declining. **Validated on notes, not on arbitrary scenes** (`DEC-042`) |
| Scene / Ask modes | ✅ **Both work** | Colab 2026-08-10: scene returned a full descriptive paragraph, confirming `DEC-031` against the real model. Ask answered `Paracip-500`, correctly. **But scene confabulated** — "contains 30 tablets" (it holds 10) and "clear plastic… white backing" (it is opaque foil): `DEC-007` demonstrated, not merely argued |
| Translation + TTS | ✅ Works end-to-end | Colab 2026-08-10: Marathi and Hindi text + audio from medicine mode's answer |
| Android port | ⬜ Not started | Phase 5 |
| NGO / user study | 🔴 **Not contacted** | long lead time — start now |
| Latency vs <8s target | 🔴 **OCR 56s/photo · VLM 315–481s on CPU** | Colab 2026-08-10, **GPU-less runtime**, model load (59.2s) excluded: medicine 56.2s @1280 vs 76.1s @1600; Devanagari 69.4s @1280 vs 103.6s @1600. Scene 481.3s, ask 314.8s — minutes, not the "tens of seconds" the README claimed. See RISK-1 |

---

## 2. Phases

### Phase 0 — Feasibility & setup · Jul 2026 · ✅ Complete

**Goal:** prove nothing in the stack is impossible before committing eight months.

- [x] Problem selected, synopsis drafted
- [x] Repo scaffolded; app skeleton with router + mode handlers + safety guardrail
- [x] VLM candidates compared on real VizWiz photos (notebook 00)
- [x] OCR engine selected by measurement (notebook 00b)
- [x] Translation (IndicTrans2) and TTS (MMS-TTS) verified runnable

**Exit criteria met:** every load-bearing dependency demonstrated working at least once.

---

### Phase 1 — Baselines & core pipeline · Aug – Sep 2026 · 🟢 Exit criteria met

**Goal:** a measured baseline to improve on, and three modes running on a laptop.
**This is what the Sem-7 review is graded against.**

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
- [ ] **Send NGO / blind-school outreach emails** ← *long lead time, do immediately*
- [ ] Get synopsis approved by guide (names + roll numbers still blank)

**Exit criteria:** baseline number recorded · read + medicine + one VLM mode demoable on a
laptop · spoken Marathi output working end-to-end for at least one mode.

---

### Phase 2 — Data collection · Sep – Nov 2026 · 🔴 Barely started

**Goal:** the custom Indian dataset that makes this project original rather than an
integration exercise. Protocol: `docs/data_collection_guide.md`.

- [ ] ~300 medicine strips (varied drugs, lighting, angles, wear)
- [ ] ~250 currency notes (₹10–500, ~40 each, worn/folded/partial). **Over-sample ₹20/₹200
      and ₹50/₹500** — the trained model's errors concentrate on denominations whose
      numerals are prefixes of one another, always erring upward (`DEC-041`)
- [ ] **~100 note-free negatives** — household surfaces, packaging, paper, fabric, floors.
      The Kaggle `background` class is tables and hands from one session and does not
      generalise: a medicine strip scored `50` at 0.870 (`DEC-042`). Without these, the
      confidence threshold is the only thing preventing phantom denominations
- [ ] ~200 labels + Devanagari signage
- [ ] ~150 scene photos
- [ ] `data/custom/labels.csv` maintained per-photo, all three languages represented
- [ ] Spot-check 10% of labels against images before any training run

**Exit criteria:** ≥500 labelled photos, label accuracy spot-checked.
**Runs in parallel with Phases 1 and 3 — 20 photos/day, not one weekend.**

---

### Phase 3 — Fine-tuning · Nov – Dec 2026 · ⬜ Not started

**Goal:** the core ML contribution. *Without this the project is an app that calls existing
models — an integration project, not a final-year AI&DS project.*

**Beat: 0.533**, the tuned-prompt result — not the 0.308 stock baseline (`DEC-017`).

Remaining headroom after prompting: abstention recall is 0.639 (88 of 244 still missed) and
precision has fallen to 0.726. Fine-tuning should aim to raise **both**, which prompting
alone could not do — every variant traded one for the other.

- [ ] LoRA fine-tune the base VLM on VizWiz train split (free Colab/Kaggle T4)
- [ ] **Weight abstention examples** — teaching "unanswerable" is worth up to +0.34 overall,
      versus +0.10 for a large gain in general answering ability
- [ ] Report abstention precision/recall separately, not just aggregate accuracy — a model
      that abstains on *everything* also scores well and would be useless
- [ ] Continue fine-tuning on the custom Indian dataset
- [ ] Re-run notebook 01 evaluation — **same N, same prompt** — for a fair comparison
- [ ] Train the MobileNet currency classifier (≥99% target) — `notebooks/03` is written
      and the engine is wired; needs a licensed Kaggle dataset (`DEC-022`)
- [ ] Ablation: stock vs VizWiz-tuned vs VizWiz+custom-tuned

**Exit criteria:** fine-tuned model beats 0.308 on the same slice, with the delta written up,
an ablation table produced, and abstention behaviour reported separately.

---

### Phase 4 — Integration · Jan 2027 · 🟡 Started early

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
- [ ] Report **every** drug name found, not just one — a combination strip
      (`IBUPROFEN 400mg PARACETAMOL 325mg`) currently names only the longest match, so the
      user hears half of what they are holding. Needs `MedicineResult.drug_name` to become
      a list, and the spoken phrasing to handle it

**Exit criteria:** end-to-end spoken answer in Marathi from a photo, offline, <8s on laptop.

---

### Phase 5 — On-device + user study · Feb 2027 · ⬜ Not started

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

### Phase 6 — Evaluation & report · Mar 2027 · ⬜ Not started

- [ ] Final metrics: VizWiz accuracy vs baseline, per-mode precision/recall, latency
- [ ] Success bar: medicine ≥95% guardrailed precision · currency ≥99% · <8s for the OCR
      modes, with the VLM modes reported separately and honestly (`DEC-038`)
- [ ] Black-book report; decision log below feeds the methodology section
- [ ] **Demo rehearsal, in this order** (`DEC-038`): airplane mode on → medicine strip
      (expiry + MRP spoken in Marathi) → ₹500 note → Marathi newspaper read aloud →
      *then* the recorded scene-mode clip, introduced as needing a GPU
- [ ] Pre-load every model on the demo machine and leave the server warm — the 59s model
      load is one-time and must not happen on stage (`RISK-9` covers the gated repos)
- [ ] Rehearse the two questions the panel will ask: "why is it slow?" (RISK-1, with the
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
| DEC-037 | **Scene mode's own output is the guardrail's best evidence — quote it in the report** | Asked to describe the Paracip strip, SmolVLM produced fluent prose that was right about the drug and dosage and invented the rest: "contains **30 tablets**" (it holds 10, printed on the strip) and "made of a **clear plastic material** and has a **white backing**" (opaque foil). The invented details are indistinguishable in tone from the true ones. `DEC-007` was argued from a Moondream anecdote during selection; this is the *shipped* model on a *committed* fixture, reproducible from `notebooks/04_app_end_to_end_devnagari.ipynb`. Consequences: scene mode is framed as orientation, never as fact; every actionable field (drug, expiry, MRP) stays on OCR + database; and the report quotes this paragraph verbatim rather than asserting that VLMs hallucinate |
| DEC-038 | **The live demo is OCR-first; scene and ask are shown as a recording, with the GPU dependency stated** | Measured on a GPU-less runtime: medicine 56s, read 69s, but scene **481s** and ask **315s**. Medicine, read and currency never touch the VLM, so the three modes that carry the project's actual claim — a blind user reading a medicine strip offline in Marathi — are the three that stay demoable on a laptop. Rejected alternatives: *demo everything live* (five to eight minutes of silence on stage, and the panel remembers the hang rather than the guardrail); *quantise until scene fits* (4-bit GGUF is Phase 5, unbuilt, and betting the review on unfinished work is how demos fail); *quietly drop scene and ask* (they are in the synopsis, and hiding a working feature because it is slow invites the question anyway, unprepared). Saying "this needs a GPU, here it is running on one, here is the measured CPU cost" is a stronger position than any of them — the honest number is defensible, a claimed 8s is not, and `RISK-1` stays visible instead of being papered over. Consequence for the report: latency is stated per mode tier, never as one aggregate |
| DEC-039 | **Currency has an eighth class, `background`: "no note in frame"** | The Kaggle dump (`DEC-022`'s dataset) ships 431 `Background__*.jpg` images with no note in them. `organize_currency.py` first treated these as unparseable junk and refused to run. Keeping them is strictly better: with seven denomination classes and nothing else, a softmax **must** name an amount, so a photo of a table, a hand, or a badly-missed shot returns a denomination — and money mode speaks it. The class gives the model somewhere honest to put that. Note this is a *different* failure from low confidence, so `app/modes/currency.py` answers it differently: `background` asks the user to reframe, `CONFIDENCE_THRESHOLD` asks for better light. Two consequences for evaluation: `background` is ~11% of the data, so headline accuracy is doubly misleading; and `class_value('background')` is ₹0, so a real ₹500 called `background` scores as a ₹500 error when it is in truth the *cheap* failure — the expensive one is calling an empty table ₹500. Report those separately rather than averaging them |
| DEC-040 | **`CONFIDENCE_THRESHOLD = 0.90`, chosen by rupee error rather than by answer rate** | The 0.85 in the code was a scaffolding guess (`DEC-024` promised to measure it). Notebook 03's sweep over 600 held-out images: `0.50` → 98.7% answered, ₹1.32 expected error; `0.85` → 90.3%, ₹1.00; **`0.90` → 85.0%, 0.9961 accuracy, ₹0.71**; `0.95` → 61.5%, ₹0.49 but answers too rarely. The notebook's original rule picked the *lowest* viable threshold and so recommended 0.50 — optimising for answering often, which contradicts `DEC-022`'s whole premise that rupee cost is the metric. The rule now minimises rupee error subject to answering ≥80%, and flags rows with fewer than 50 answered samples as noise (the 0.99 row scored 0.9667 off 30 samples and one error, which reads misleadingly as "stricter is worse") |
| DEC-041 | **The model's errors cluster on denominations whose numerals are prefixes of one another** | The costliest confusions are not random: `20 → 200` three times (₹540), `50 → 500` once (₹450), `2000 → 10` once (₹1990). Both frequent pairs differ by a trailing zero, and both err *upward* — the user is told they hold ten times what they do, which is the direction that gets someone short-changed at a counter. One `background → 200` is the same class of harm: phantom money where there is no note. Two consequences: Phase-2 note photography should over-sample the 20/200 and 50/500 pairs rather than spreading evenly across denominations, and the report should show this table instead of the 0.9883 headline, because "98.8% accurate" hides that the residual errors are concentrated in the expensive direction |
| DEC-042 | **`background` learned *this dataset's* backgrounds, not "no note present"** | Verified on the laptop 2026-08-11 against three note-free images. The medicine strip returned `50` at **0.870** confidence with `background` at 0.038; the partial strip `500` at 0.578; the Marathi newspaper `100` at 0.705. All three declined only because `CONFIDENCE_THRESHOLD` is 0.90 — the strip missed being announced as a ₹50 note by 0.03. So `DEC-039` is right that the class is necessary and wrong that it is sufficient: its 431 training images are tables and hands from one capture session, which does not generalise to foil, newsprint or anything else a camera gets pointed at. Consequences: the threshold is currently the *only* real defence and must not be lowered on answer-rate grounds; Phase 2 must collect **diverse negatives** — household surfaces, packaging, paper, fabric, floors — not just more notes; and the report should state that money mode is validated on notes and on this dataset's backgrounds, not on arbitrary scenes |
| DEC-043 | **Keep `CenterCrop` for evaluation; the real-photo gap is data, not preprocessing** | Five handheld notes shot on 2026-08-11: top-1 correct on all five, but only **3 of 5 cleared the 0.90 threshold** — ₹50 at 0.882 and ₹200 at 0.342. The two weak ones are the two elongated frames (aspect 2.04 and 2.10 against 1.33–1.36 for the rest), which suggested `Resize(256)`+`CenterCrop(224)` was cutting away the corner numerals. Two alternatives were measured on the notebook's own 600-image test split with `eval/eval_currency.py`: **center_crop 0.9883 / ₹5.37, letterbox 0.9850 / ₹7.75, squash 0.9817 / ₹7.82.** So `squash` helps the hand-shot photos and *hurts* the dataset, because the Kaggle images are already cropped tight to the note and have no margin to preserve. Changing the transform would trade a measured 600-image result for an unmeasured 5-image one. The gap is that the training data does not look like deployment: **the 0.9961 conditional accuracy is measured on tightly-cropped images and overstates what a blind user gets.** The fix is Phase-2 photographs of notes framed loosely and held at arm's length, then retraining — not a preprocessing change |
| DEC-044 | **The paddle/torch import order is inverted on Windows** | `DEC-027` established that paddle must be imported *before* paddleocr, because paddlex drags torch in and libpaddle then segfaults. On Windows the same ordering breaks the other library instead: with `paddle\libs\libiomp5md.dll` already resident, torch fails at import with `OSError: [WinError 127] ... Error loading torch\lib\shm.dll`. Importing torch first, then paddle, then paddleocr works on Windows; on Linux it is what `DEC-027` proved fatal. `_load()` now branches on `sys.platform`, tolerating a missing torch for OCR-only environments. Two things this pins down: the conflict is **not** avoidable by declining to use the VLM, since `paddlex/inference/utils/official_models.py` imports `modelscope` unconditionally and that pulls torch regardless; and `DEC-006`'s "separate processes" constraint is now a *cross-platform* requirement rather than a Colab quirk, which raises the cost of the Phase-5 Android port. Found on the laptop, not on Colab — the demo machine is the one that matters |
| DEC-045 | **The web app selects the OCR engine per request; `ocr_lang` was being discarded** | Found by driving the real API with the committed fixtures rather than the camera. `ocr_lang` was parsed from the form, validated against the language table, and then never used: `AnswerService` held a single English `PaddleOCREngine` built at startup. Reading the Marathi newspaper through the browser returned `Tach taaRa firast HoH HEST machals` — the Latin recogniser transliterating Devanagari. **Nothing raised**, so a blind user hears confident gibberish with no signal that the wrong model ran; the same request now returns **1010 Devanagari characters**. The front end was half the bug: it sent `ocr_lang` only for medicine mode, so Read never asked for a script at all. Engines are built lazily and cached per script rather than pre-built for every language, because two live pipelines peaked at 11.65 GB (`DEC-035`). **Method note:** this was invisible to the test suite because the fakes return whatever they are given, and invisible in manual testing because garbage output looks like a bad photo. Driving the real service with known-good fixtures is what separated an app bug from camera quality |
| DEC-023 | Class names live in the checkpoint, never in code | A checkpoint trained on differently-ordered folders would silently relabel every prediction. Hardcoding the order makes "₹500 reported as ₹10" a one-line mistake, which is the exact failure Money mode exists to prevent |
| DEC-024 | The currency confidence threshold is measured, not assumed | `CONFIDENCE_THRESHOLD = 0.85` was a guess made while scaffolding. Notebook 03 §5 sweeps it and refuses to recommend any value that cannot reach ≥99% accuracy while still answering ≥80% of the time — better to declare the mode unready than to ship a confident wrong denomination |

---

## 4. Risk register

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| RISK-1 | **Latency far past the <8s target** — 2026-08-10, model load excluded: OCR **46.5–54.5s** per photo at *either* `max_side`, translate+TTS 33.8s cold / 9.7s warm, VLM 65.5s | 🔴 High | Levers by measured payoff: (1) **`max_side=1280` — banked**, 25–35% at no accuracy cost (`DEC-036`); (2) **swap the medium/server models for mobile** — `en` resolves to `PP-OCRv6_medium_det`/`_rec` and `mr` to `PP-OCRv5_server_det`, none of them the mobile variants the Android target needs anyway, so this serves Phase 5 too; (3) drop `use_doc_unwarping` per mode — `DEC-004` measured it at 13% and destroying accuracy *on foil*, but a flat newspaper may not need it, making it a per-mode rather than global choice; (4) **keep the VLM off the demo path** — scene 481s and ask 315s are what blow the budget, while medicine, read and currency never touch it, so a CPU-only review demo should be driven by the OCR modes with scene/ask shown as a recorded clip. Model load (59.2s) is one-time and must be quoted separately, never folded into the per-photo figure. If <8s still can't be met, restate the target honestly — a demo that answers in 15s is defensible, a false claim of 8s is not |
| RISK-2 | **Dataset collection not started** (3 of ~700 photos) | 🔴 High | 20 photos/day starting now; blocks Phase 3 entirely |
| RISK-3 | **No NGO contact yet** | 🔴 High | Email 5–6 today; replies take weeks, scheduling weeks more. Without this, objective 5 fails |
| RISK-4 | Android port may not fit the timeline | 🟡 Medium | Laptop demo is the committed deliverable; Android is explicitly a stretch goal |
| RISK-5 | Fine-tuning may not beat the stock baseline | 🟡 Medium | Even a negative result is publishable if measured honestly; ablation table makes it defensible |
| RISK-6 | Upstream dependency churn breaks a working pipeline | 🟡 Medium | Pins + `requirements.txt` + DEC-009; re-verify before the demo |
| RISK-7 | ~~Devanagari OCR quality unknown~~ **Largely retired** | 🟢 Low | Measured 2026-08-10: 1010 Devanagari chars of 1238 on a photographed Maharashtra Times page, headline and body both accurate. `devanagari_PP-OCRv5_mobile_rec` works on real newsprint, so the English-only fallback is no longer needed. Still open: the foil case (`पॅरासिप-500`) and the 1600 comparison, both cut short by the OOM — neither threatens the mode |
| RISK-8 | Single-person bus factor on Colab sessions | 🟢 Low | Notebooks are committed; results downloaded to `eval/results/` |
| RISK-9 | **Gated model repos block provisioning a fresh machine** (`DEC-029`) | 🟡 Medium | Runtime offline-ness is unaffected — weights cache locally. But a demo laptop set up from scratch needs an HF account, an accepted licence and a token. Download the weights onto the demo machine *before* review week, and keep a local copy; a gate added upstream in March 2027 would otherwise surface on stage |

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
| `docs/synopsis.md` | College submission document (abstract, objectives, literature) |
| `docs/data_collection_guide.md` | Phase-2 protocol: counts, privacy rules, labelling |
| `notebooks/00_feasibility_spike_colab.ipynb` | VLM comparison + translation/TTS spike (Colab GPU) |
| `notebooks/00b_ocr_spike.ipynb` | OCR engine selection (CPU, no GPU) |
| `notebooks/01_vizwiz_baseline.ipynb` | The baseline number (Colab GPU) |
| `notebooks/02_abstention_prompts.ipynb` | Prompt sweep to recalibrate abstention (Colab GPU) |
| `eval/results/` | Downloaded run artifacts — the evidence trail |

**Maintenance rule:** update the status dashboard and decision log in the same commit as the
work itself. A build plan that lags the code is worse than none.
