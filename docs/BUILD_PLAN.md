# Drishti — Build Plan

> **This is the single source of truth for scope, phases, status and decisions.**
> `README.md` describes *what the system is*. `synopsis.md` is the college submission
> document. Neither carries a timeline — if a date or milestone appears anywhere else,
> it is stale and should be deleted in favour of this file.
>
> **Last updated:** 2026-08-02 · **Phase:** 1 of 6 · **Academic year:** 2026–27
>
> **Baseline:** stock SmolVLM-Instruct scored **0.308** on 500 VizWiz-val samples.
> Prompt engineering alone lifted it to **0.533** (+0.225, no training). Phase 3
> fine-tuning must beat **0.533**, not 0.308 — see `DEC-016`.

---

## 1. Status dashboard

| Phase | Window | State |
|---|---|---|
| 0 — Feasibility & setup | Jul 2026 | ✅ **Complete** |
| 1 — Baselines & core pipeline | Aug – Sep 2026 | 🟡 **In progress** |
| 2 — Data collection | Sep – Nov 2026 | 🔴 Barely started (3 photos of ~700) |
| 3 — Fine-tuning | Nov – Dec 2026 | ⬜ Not started |
| 4 — Integration | Jan 2027 | ⬜ Not started |
| 5 — On-device + user study | Feb 2027 | ⬜ Not started |
| 6 — Evaluation & report | Mar 2027 | ⬜ Not started |

**Hard gates:** Sem-7 review ≈ Oct 2026 (needs Phase 1 done) · Final submission ≈ Mar–Apr 2027.

### Component status

| Component | State | Evidence |
|---|---|---|
| App skeleton (router, 5 modes, guardrail) | ✅ Done | 39 tests passing |
| OCR engine (PaddleOCR) | ✅ Wired | `app/engines/paddle_ocr.py`, proven on a real strip |
| Medicine mode end-to-end | ✅ Works | Real OCR → `"This is Paracetamol. It is valid until OCT.2026…"` |
| Read mode (English) | ✅ Works | via same engine |
| Read mode (Devanagari) | 🟡 Lang code found (`mr`/`hi`), **untested** | no photo with Devanagari text yet |
| VizWiz baseline (stock prompt) | ✅ **0.308** | notebook 01, 500 samples, 1.21 s/answer |
| VizWiz with tuned prompt | ✅ **0.533** | notebook 02, same 500 samples, no training |
| Currency mode | ⬜ Not started | no dataset, no model |
| Scene / Ask modes | 🟡 SmolVLM wired, not yet run through `app/` | `app/engines/smolvlm.py` |
| Translation + TTS | 🟡 Wired, not yet run through `app/` | `app/speech.py`, `--lang mr --speak` |
| Android port | ⬜ Not started | Phase 5 |
| NGO / user study | 🔴 **Not contacted** | long lead time — start now |
| Latency vs <8s target | 🔴 **~30s/image** | unresolved, see RISK-1 |

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

### Phase 1 — Baselines & core pipeline · Aug – Sep 2026 · 🟡 In progress

**Goal:** a measured baseline to improve on, and three modes running on a laptop.
**This is what the Sem-7 review is graded against.**

- [x] **Run notebook 01 → VizWiz baseline = 0.308** (answerable 0.310 / unanswerable 0.306)
- [x] Record 3 failure patterns — over-answering, fine-grained OCR misses, question-form misreads
- [x] Save `vizwiz_baseline_results.csv` to `eval/results/`, run `eval/analyze_results.py`
- [x] **Run `notebooks/02_abstention_prompts.ipynb`** — `stakes` prompt won; overall
      0.308 → **0.533**, abstention recall 0.258 → 0.639. Hypothesis in `DEC-013`
      confirmed: it was a calibration problem, and prompting fixed most of it
- [ ] Photograph a strip **with Marathi/Hindi text**; verify Read mode with `--ocr-lang mr`
- [x] Wire SmolVLM into `app/engines/` as a `VLMEngine` → scene/ask modes now routable
- [x] Integrate IndicTrans2 + MMS-TTS as `Translator`/`TTSEngine` implementations
- [ ] **Run the full pipeline once on real hardware** — `--mode medicine --ocr-lang en
      --lang mr --speak`. Logic is unit-tested with fakes, but no model has actually been
      loaded through `app/` yet; that is the Phase-1 exit criterion, not the wiring
- [ ] Source a real drug-name database (replace `data/drug_names_seed.txt` placeholder)
- [ ] **Send NGO / blind-school outreach emails** ← *long lead time, do immediately*
- [ ] Get synopsis approved by guide (names + roll numbers still blank)

**Exit criteria:** baseline number recorded · read + medicine + one VLM mode demoable on a
laptop · spoken Marathi output working end-to-end for at least one mode.

---

### Phase 2 — Data collection · Sep – Nov 2026 · 🔴 Barely started

**Goal:** the custom Indian dataset that makes this project original rather than an
integration exercise. Protocol: `docs/data_collection_guide.md`.

- [ ] ~300 medicine strips (varied drugs, lighting, angles, wear)
- [ ] ~250 currency notes (₹10–500, ~40 each, worn/folded/partial)
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
- [ ] Train the MobileNet currency classifier (≥99% target)
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
- [ ] Run the browser app against **real** engines (currently verified with fakes)
- [ ] Latency budget enforced per mode (see RISK-1)

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
- [ ] Success bar: medicine ≥95% guardrailed precision · currency ≥99% · <8s spoken answer
- [ ] Black-book report; decision log below feeds the methodology section
- [ ] Demo rehearsal: airplane mode → medicine strip → ₹500 note → scene description

---

## 3. Decision log

Records *why*, so decisions aren't relitigated and the report has evidence.

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Project = Drishti (offline blind-assistance VLM) | Chosen over scam-call shield and ISL translator: best mix of social impact, demo strength, and 2026–27 hiring skills |
| DEC-002 | Base VLM = **SmolVLM-Instruct**, not Moondream-2 | Measured on real VizWiz photos: 2.5× faster (1.75s vs 4.4s), terse answers (VizWiz scores by *exact match*, so verbosity ≈ 0), and native transformers classes instead of `trust_remote_code` |
| DEC-003 | OCR = **PaddleOCR**, not Surya or Tesseract | Surya 2.x needs a vllm/Docker inference server — incompatible with offline on-device. Tesseract returned noise on curved foil strips. PaddleOCR read every needed field at ≥0.96 |
| DEC-004 | PaddleOCR document preprocessing stays **ON** | Disabling it saved 13% wall time but destroyed accuracy (lost drug name, expiry, MRP). A hand-held strip is curved and rotated, so orientation/unwarping is load-bearing |
| DEC-005 | Devanagari via `lang='mr'` / `'hi'` | `'devanagari'`, `'hindi'`, `'marathi'`, `'deva'` all raise `ValueError` in PaddleOCR 3.7.0. Working codes resolve to `devanagari_PP-OCRv5_mobile_rec` — a *mobile* model, good for the Android target |
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

---

## 4. Risk register

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| RISK-1 | **OCR latency ~30s/image vs <8s target** | 🔴 High | Try PP-OCR *mobile* det model, smaller `max_side`, per-mode budgets. If unfixable, restate the target honestly and report measured numbers |
| RISK-2 | **Dataset collection not started** (3 of ~700 photos) | 🔴 High | 20 photos/day starting now; blocks Phase 3 entirely |
| RISK-3 | **No NGO contact yet** | 🔴 High | Email 5–6 today; replies take weeks, scheduling weeks more. Without this, objective 5 fails |
| RISK-4 | Android port may not fit the timeline | 🟡 Medium | Laptop demo is the committed deliverable; Android is explicitly a stretch goal |
| RISK-5 | Fine-tuning may not beat the stock baseline | 🟡 Medium | Even a negative result is publishable if measured honestly; ablation table makes it defensible |
| RISK-6 | Upstream dependency churn breaks a working pipeline | 🟡 Medium | Pins + `requirements.txt` + DEC-009; re-verify before the demo |
| RISK-7 | Devanagari OCR quality unknown | 🟡 Medium | Untested — no Devanagari photo yet. Test early in Phase 1; fallback is English-only Read mode for Sem-7 |
| RISK-8 | Single-person bus factor on Colab sessions | 🟢 Low | Notebooks are committed; results downloaded to `eval/results/` |

---

## 5. Success criteria (final)

| Metric | Target |
|---|---|
| VizWiz accuracy | Fine-tuned model **beats** the stock baseline on the same slice |
| Medicine mode precision | ≥95%, guardrailed (declines rather than guesses) |
| Currency accuracy | ≥99% |
| End-to-end spoken answer | <8s on laptop CPU |
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
