# Drishti — Project Overview

**Title:** Drishti — An Offline, Privacy-Preserving AI Vision Assistant for Visually-Impaired
Users in Indian Languages

**Domain:** Artificial Intelligence & Data Science (Computer Vision · Multimodal Deep Learning
· Edge AI · Accessibility)

**By:** Devendra Ramesh Gurav · **Started:** July 2026

A personal project. `docs/BUILD_PLAN.md` carries the live status, decision log and risks;
this document explains what Drishti is and why it is built this way.

---

## Abstract

India has an estimated 5 million blind and about 70 million visually-impaired citizens.
Existing AI assistance tools (Be My AI, Microsoft Seeing AI, Google Lookout) require constant
internet connectivity, respond primarily in English, and upload private images — prescriptions,
currency, the user's home — to cloud servers. This excludes rural, non-English-speaking, and
privacy-conscious users. **Drishti** is a fully offline assistant that runs a
quantized vision-language model (VLM) on commodity hardware and speaks its answers in Marathi,
Hindi, or English. Drishti provides five task modes — text reading (including Devanagari),
medicine-strip identification with expiry warnings, currency recognition, scene description,
and free-form visual question answering — using a **model-routing architecture** that sends
each task to the smallest capable model, and a **safety-guardrail design** that prevents the
VLM from guessing medicine names. The VLM is fine-tuned with LoRA on VizWiz (photographs taken
by blind users), and the currency classifier on merged public Indian-currency datasets with
VizWiz images as negatives — all licence-clean and rebuildable from a manifest rather than
self-collected (`DEC-047`).

## Problem statement

Visually-impaired users in India cannot independently perform everyday visual tasks — verifying
a medicine and its expiry date, identifying currency, reading labels and signage — because
existing assistive AI requires internet, English literacy, and cloud upload of private images.

## Objectives

1. Fine-tune and deploy a quantized (4-bit) small VLM that answers visual questions on real
   blind-user photographs, exceeding the stock-model baseline on the VizWiz benchmark.
2. Build specialist pipelines: Indic-script OCR + expiry/MRP parsing for medicine mode, and a
   lightweight CNN for ₹-note recognition (≥99% target accuracy on a held-out public split).
3. Implement a safety guardrail: medicine names are reported only when OCR output matches a
   verified drug-name database; the system otherwise declines. Its precision is reported
   over a declared sample rather than as an unvalidated percentage (`DEC-048`).
4. Deliver answers as speech in Marathi/Hindi/English through an offline translation
   (IndicTrans2) and TTS pipeline; end-to-end spoken answer under 8 seconds on a laptop CPU.
5. ~~Validate with visually-impaired users through an NGO/blind-school partnership
   (task-success study) and port the system to an Android device as a stretch goal.~~
   **Both dropped, and the objective is scored *not met* rather than redefined** — the
   Android port with its blocker measured (`DEC-064`), the user study for time (`DEC-070`).
   Self-conducted task testing replaces the study and does not stand in for it: a sighted
   author cannot reproduce the one condition the whole design assumes, that the user cannot
   check the answer. See `docs/REPORT.md` §9.

## Literature survey (indicative)

- Gurari et al., *VizWiz Grand Challenge: Answering Visual Questions from Blind People*, CVPR 2018
- Recent small/efficient VLMs: Moondream-2, SmolVLM (Hugging Face TB), Qwen2.5-VL, Gemma 3
- Hu et al., *LoRA: Low-Rank Adaptation of Large Language Models*, ICLR 2022
- Gala et al. (AI4Bharat), *IndicTrans2*, TMLR 2023 — en→Indic machine translation
- Pratap et al., *Scaling Speech Technology to 1,000+ Languages* (MMS), 2023 — offline Indic TTS
- PaddleOCR (PP-OCR) — multilingual OCR incl. Devanagari (Hindi/Marathi), with
  mobile-optimized models for on-device deployment
- Commercial systems survey: Seeing AI, Be My AI, Google Lookout (cloud-dependent baselines)

## Proposed methodology

1. **Baseline (M1–2):** stream VizWiz-VQA; measure stock-VLM accuracy with the official VizWiz
   metric; build the OCR + parsing pipeline; select the VLM base by accuracy/latency trade-off.
2. **Data:** assemble a corpus from licence-clean public sources — several independent
   Indian-currency datasets, deduplicated and merged for capture diversity, plus VizWiz
   images as "no note present" negatives. Medicine and Read are evaluated, not trained.
3. **Fine-tuning:** LoRA fine-tune the chosen VLM on VizWiz (free Colab/Kaggle GPUs);
   train the currency CNN on the merged corpus; assemble the routing layer and guardrail.
4. **Speech pipeline (M4):** IndicTrans2 dist-200M (en→mr/hi) + MMS-TTS, all offline.
5. **Deployment (M5–6):** laptop demo app. ~~4-bit GGUF quantization; Android port via
   llama.cpp/MediaPipe LLM Inference (stretch); NGO user testing~~ — all three dropped
   (`DEC-064`, `DEC-068`, `DEC-070`).
6. **Evaluation (M7–8):** VizWiz accuracy vs baseline; per-mode precision/recall; latency;
   a scripted self-test in airplane mode; a written record of what worked and what did not.
   ~~User task-success study~~ — dropped (`DEC-070`), and recorded as a limitation rather
   than replaced.

## System requirements

- Development: Python 3.12, PyTorch, Hugging Face Transformers/PEFT, llama.cpp; free
  Colab/Kaggle T4 GPUs for training (no local GPU required)
- Deployment target: mid-range Android phone (≈₹10,000) or any laptop CPU — no internet

## Expected outcomes

A working offline assistant (laptop demo), measurable improvement over the stock-model
baseline on VizWiz, guardrail behaviour reported over a stated sample rather than as an
unvalidated ≥95%, and currency accuracy on a held-out public split reported as rupee-weighted
cost rather than as a bare ≥99% — plus an honest writeup of the measurements, including the
ones that did not go the way they were expected to.

**Not delivered, and stated here rather than at the end:** the Android port (`DEC-064`) and
the user study with visually-impaired participants (`DEC-070`). The second means the project
never establishes that its intended user can operate it — its largest gap, and the one no
measurement elsewhere compensates for.

## Targets

Two dates, self-imposed, kept because a plan with no date cannot tell you when something is
slipping. The ordered work — six phases, live status, decision log and risk register — is in
`docs/BUILD_PLAN.md`, which is authoritative if the two ever differ.

| Target | By | What "done" means |
|---|---|---|
| Demoable end to end | ~Oct 2026 | Read, medicine and currency answering on a laptop, offline, spoken in Marathi |
| Project complete | ~Mar–Apr 2027 | Fine-tuning measured and written up (it tied with prompting and does not ship — `DEC-068`), a scripted self-test passed in airplane mode, and the results written up. **No user study** (`DEC-070`) |
