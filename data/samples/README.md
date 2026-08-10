# Sample images

Small committed fixtures so notebooks and tests can run without uploading anything.

| File | What it is |
|---|---|
| `strip_paracip.jpg` | Paracip-500 (Cipla), 10 tabs, back side — the read that produced 55 OCR lines including the drug name, `MFD.MAY 25 EXP.APR.28` and `Rs.10.30` |
| `strip_partial.jpg` | A **different** strip — 20 tabs, `MFG.NOV.2024 EXP.OCT.2026`, no drug name in frame. Only 3 lines recognized. Kept deliberately as the negative case: the guardrail must decline when no name matches |
| `curr-10.jpg` | Handheld ₹10, old series, worn with a pen mark, on concrete — money mode's positive fixture. Predicted `10` at 0.973 |
| `curr-500.jpg` | Handheld ₹500, current series, slight fold, on concrete. Predicted `500` at 0.960 |
| `newspaper-marathi.png` | Photographed Marathi newspaper page (Maharashtra Times), 1296×1720 — the Devanagari Read-mode fixture. Dense printed body text plus a large headline, so it exercises both easy and hard recognition in one image |

**The two strips are different products, not two photos of one strip.** Notebook 00b OCRs both
in one cell, so its `expiry_candidates` output shows `['OCT.2026', 'APR.28']` — one date
from each. Read as a single strip carrying two dates, that pair produced a false conclusion
that survived into the decision log for a week (`DEC-030`, struck). Each strip has exactly
one expiry: Paracip is `APR.28`, the partial is `OCT.2026`.

The **strips** are downscaled to 1600px on the long side — the engine's default at the time
they were committed. `DEFAULT_MAX_SIDE` is now **1280** (`DEC-036`), so the engine does
resize them, and `max_side=1600` is the setting that is a no-op on these two files. Keeping
them at 1600 is deliberate: it preserves the headroom needed to compare the two settings.

The **newspaper is deliberately left at 1720px** and kept lossless. It is the one fixture
where a downscale could plausibly cost accuracy — newsprint body text is small per glyph —
so it is genuinely resized by both 1280 and 1600, which is what makes the `max_side`
comparison in notebook 04 §5 mean anything. Re-encoding it to a 1600px JPEG would destroy
exactly the signal it exists to measure, at a cost of 2.4 MB.

The two notes were shot on a phone and carry EXIF orientation. `curr-10.jpg` is stored
3072×4080 with a rotation tag, and the engines used to ignore it — every model saw that
note sideways. `app/imaging.py::load_upright` now applies the tag, and the committed
copies are re-encoded upright so the fixture matches what a viewer shows.

These are **fixtures, not the dataset**. The real collection lives in `data/custom/`
(gitignored) and follows `docs/data_collection_guide.md`. Full-resolution originals stay in
`test-images/`, also gitignored.
