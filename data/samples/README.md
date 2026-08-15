# Sample images

Small committed fixtures so notebooks and tests can run without uploading anything.

| File | What it is |
|---|---|
| `strip_paracip.jpg` | Paracip-500 (Cipla), 10 tabs, back side — the read that produced 55 OCR lines including the drug name, `MFD.MAY 25 EXP.APR.28` and `Rs.10.30` |
| `strip_partial.jpg` | A **different** strip — 20 tabs, `MFG.NOV.2024 EXP.OCT.2026`, no drug name in frame. Only 3 lines recognized. Kept deliberately as the negative case: the guardrail must decline when no name matches |
| `curr-10.jpg` | Handheld ₹10, old series, worn with a pen mark, on concrete — money mode's positive fixture. Predicted `10` at **0.942** |
| `curr-500.jpg` | Handheld ₹500, current series, slight fold, on concrete. Predicted `500` at **0.961** |
| `curr-50.jpg` | Handheld ₹50, wide framing (aspect 2.0). Predicted `50` at **0.958** — answers. It declined at 0.882 under the single-source model |
| `curr-100.jpg` | Handheld ₹100, tight framing. Predicted `100` at **0.978** |
| `curr-200.jpg` | Handheld ₹200 on patterned cloth, note lying sideways, aspect 2.1. Top-1 `200` correctly, but **0.784** — **declines**. The hardest fixture in the set, and the only note that still fails |
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
single-source model two declined — ₹50 at 0.882 and ₹200 at 0.342, both loosely framed,
against training images cropped tight to the note (`DEC-043`). Merging independent sources
fixed both (₹200 → 0.926, ₹50 → 0.967) while the *benchmark went down* on a harder split,
0.9875 → 0.9810 — five deployment images caught what 840 test images could not (`DEC-052`).

**Current state, 7-class model, verified 2026-08-15 by `python -m eval.check_fixtures`:**

| | result |
|---|---|
| real notes answered correctly | **4 of 5** — only `curr-200` withheld, at 0.784 |
| non-notes correctly refused | **3 of 3** |
| worst false positive | `strip_paracip` → ₹100 at **0.840**, leaving **0.060** of headroom below the 0.90 bar |

Dropping ₹2000 traded one withheld note for two fixed false positives (`DEC-062`). **Those
two outcomes are not equal and must not be netted off:** a withheld note costs a retaken
photo, while a medicine strip announced as ₹100 to someone who cannot check is the failure
this project exists to prevent. **The threshold therefore does not move** — lowering it to
0.78 to rescue `curr-200` would ship the `strip_paracip` false positive. That 0.060, not the
fixture count, is the number to watch.

**Re-run these after every retrain** — `python -m eval.check_fixtures` — and report them
beside the benchmark rather than underneath it. That instruction previously had no command
attached, and the numbers in this file drifted two model generations out of date before
anyone noticed.

These are **fixtures, not a dataset**. Since `DEC-047` there is no self-collected corpus:
training images come from licence-clean public sources (`data/README.md`). Full-resolution
originals of these eight stay in `test-images/`, which is gitignored.
