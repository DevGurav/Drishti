# Sample images

Small committed fixtures so notebooks and tests can run without uploading anything.

| File | What it is |
|---|---|
| `strip_paracip.jpg` | Paracip-500 (Cipla), 10 tabs, back side — the read that produced 55 OCR lines including the drug name, `MFD.MAY 25 EXP.APR.28` and `Rs.10.30` |
| `strip_partial.jpg` | A **different** strip — 20 tabs, `MFG.NOV.2024 EXP.OCT.2026`, no drug name in frame. Only 3 lines recognized. Kept deliberately as the negative case: the guardrail must decline when no name matches |
| `curr-10.jpg` | Handheld ₹10, old series, worn with a pen mark, on concrete — money mode's positive fixture. Predicted `10` at 0.973 |
| `curr-500.jpg` | Handheld ₹500, current series, slight fold, on concrete. Predicted `500` at 0.960 |
| `curr-50.jpg` | Handheld ₹50, wide framing (aspect 2.0). Top-1 `50` but only 0.882 — **declines** at the 0.90 threshold |
| `curr-100.jpg` | Handheld ₹100, tight framing. Predicted `100` at 0.945 |
| `curr-200.jpg` | Handheld ₹200 on patterned cloth, note lying sideways, aspect 2.1. Top-1 `200` but 0.342 — **declines**. The hardest fixture in the set |
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

**The five notes are the deployment reality check, and they earned their keep.** Under the
single-source model two of them declined — ₹50 at 0.882 and ₹200 at 0.342, both loosely
framed, against training images cropped tight to the note (`DEC-043`). After retraining on
the merged multi-source corpus **all five answer**, with ₹200 at 0.926 and ₹50 at 0.967.

That happened while the *benchmark* went down (0.9875 → 0.9810 on a harder split), which is
why these files stay committed: five images drawn from deployment caught something 840 test
images could not (`DEC-052`). Re-run them after every retrain, and report them beside the
benchmark rather than underneath it.

These are **fixtures, not the dataset**. The real collection lives in `data/custom/`
(gitignored) and follows `docs/dataset_guide.md`. Full-resolution originals stay in
`test-images/`, also gitignored.
