# Sample images

Small committed fixtures so notebooks and tests can run without uploading anything.

| File | What it is |
|---|---|
| `strip_paracip.jpg` | Paracip-500 (Cipla), 10 tabs, back side — the read that produced 55 OCR lines including the drug name, `MFD.MAY 25 EXP.APR.28` and `Rs.10.30` |
| `strip_partial.jpg` | A **different** strip — 20 tabs, `MFG.NOV.2024 EXP.OCT.2026`, no drug name in frame. Only 3 lines recognized. Kept deliberately as the negative case: the guardrail must decline when no name matches |

**These are two different products, not two photos of one strip.** Notebook 00b OCRs both
in one cell, so its `expiry_candidates` output shows `['OCT.2026', 'APR.28']` — one date
from each. Read as a single strip carrying two dates, that pair produced a false conclusion
that survived into the decision log for a week (`DEC-030`, struck). Each strip has exactly
one expiry: Paracip is `APR.28`, the partial is `OCT.2026`.

Downscaled to 1600px on the long side, which is exactly
`app/engines/paddle_ocr.py::DEFAULT_MAX_SIDE` — the engine would downscale to this anyway,
so nothing is lost and the files stay ~300 KB instead of ~3.4 MB.

These are **fixtures, not the dataset**. The real collection lives in `data/custom/`
(gitignored) and follows `docs/data_collection_guide.md`. Full-resolution originals stay in
`test-images/`, also gitignored.
