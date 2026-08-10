# Project Synopsis

**Title:** Drishti — An Offline, Privacy-Preserving AI Vision Assistant for Visually-Impaired
Users in Indian Languages

**Domain:** Artificial Intelligence & Data Science (Computer Vision · Multimodal Deep Learning
· Edge AI · Accessibility)

**Submitted by:** Devendra Ramesh Gurav (individual project) · **Roll No.:** _<roll number>_
· **Guide:** _<guide name>_ · **Academic year:** 2026–27

---

## Abstract

India has an estimated 5 million blind and about 70 million visually-impaired citizens.
Existing AI assistance tools (Be My AI, Microsoft Seeing AI, Google Lookout) require constant
internet connectivity, respond primarily in English, and upload private images — prescriptions,
currency, the user's home — to cloud servers. This excludes rural, non-English-speaking, and
privacy-conscious users. We propose **Drishti**, a fully offline assistant that runs a
quantized vision-language model (VLM) on commodity hardware and speaks its answers in Marathi,
Hindi, or English. Drishti provides five task modes — text reading (including Devanagari),
medicine-strip identification with expiry warnings, currency recognition, scene description,
and free-form visual question answering — using a **model-routing architecture** that sends
each task to the smallest capable model, and a **safety-guardrail design** that prevents the
VLM from guessing medicine names. The VLM is fine-tuned with LoRA on VizWiz (photographs taken
by blind users) plus a self-collected Indian dataset of medicine strips, currency notes, and
product labels.

## Problem statement

Visually-impaired users in India cannot independently perform everyday visual tasks — verifying
a medicine and its expiry date, identifying currency, reading labels and signage — because
existing assistive AI requires internet, English literacy, and cloud upload of private images.

## Objectives

1. Fine-tune and deploy a quantized (4-bit) small VLM that answers visual questions on real
   blind-user photographs, exceeding the stock-model baseline on the VizWiz benchmark.
2. Build specialist pipelines: Indic-script OCR + expiry/MRP parsing for medicine mode, and a
   lightweight CNN for ₹-note recognition (≥99% target accuracy).
3. Implement a safety guardrail: medicine names are reported only when OCR output matches a
   verified drug-name database; the system otherwise declines.
4. Deliver answers as speech in Marathi/Hindi/English through an offline translation
   (IndicTrans2) and TTS pipeline; end-to-end spoken answer under 8 seconds on a laptop CPU.
5. Validate with visually-impaired users through an NGO/blind-school partnership (task-success
   study) and port the system to an Android device as a stretch goal.

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
2. **Data (M3):** collect and label 500–1,000 photographs of Indian medicine strips, currency
   notes, and MRP/expiry labels under realistic (imperfect) capture conditions.
3. **Fine-tuning (M3–4):** LoRA fine-tune the chosen VLM on VizWiz + custom data (free
   Colab/Kaggle GPUs); train the currency CNN; assemble the routing layer and guardrail.
4. **Speech pipeline (M4):** IndicTrans2 dist-200M (en→mr/hi) + MMS-TTS, all offline.
5. **Deployment (M5–6):** 4-bit GGUF quantization; laptop demo app; Android port via
   llama.cpp/MediaPipe LLM Inference (stretch); NGO user testing.
6. **Evaluation (M7–8):** VizWiz accuracy vs baseline; per-mode precision/recall; latency;
   user task-success study; final report.

## System requirements

- Development: Python 3.12, PyTorch, Hugging Face Transformers/PEFT, llama.cpp; free
  Colab/Kaggle T4 GPUs for training (no local GPU required)
- Deployment target: mid-range Android phone (≈₹10,000) or any laptop CPU — no internet

## Expected outcomes

A working offline assistant (laptop demo + Android stretch goal), measurable improvement over
the stock-model baseline on VizWiz, ≥95% guardrailed precision in medicine mode, ≥99% currency
accuracy, a small user-study with visually-impaired participants, and the final project report.

## Timeline

Summary for submission. The working plan — six phases with tasks, live status, decision log
and risk register — is `docs/BUILD_PLAN.md`, which is authoritative if the two ever differ.

| Phase | Months | Deliverable |
|---|---|---|
| Feasibility spike + baselines | Jul–Sep 2026 | 3 modes on laptop (Sem-7 review) |
| Data collection + fine-tuning | Oct–Dec 2026 | Fine-tuned VLM beats baseline |
| Deployment + user testing | Jan–Feb 2027 | Android/laptop app, NGO study |
| Evaluation + report | Feb–Mar 2027 | Black-book report + demo |
