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
| `curr-20-withheld.jpg` | Flat ₹20, even light, generously framed — an *easy* photo. Top-1 `20` correctly, at **0.765**: declines. Added 2026-08-24 |
| `cloth-pink-towel.jpg` | A folded pink towel, no note anywhere in frame. Predicted `20` at **0.804**. Added 2026-08-24 |
| `strip_paracip_fullres.jpg` | The **same product** as `strip_paracip.jpg`, rephotographed at **4080×3072** and committed uncompressed. OCR reads the drug name and **loses the expiry and the MRP** that the smaller fixture reads correctly. Added 2026-08-24 |

**The two strips are different products, not two photos of one strip.** Notebook 00b OCRs both
in one cell, so its `expiry_candidates` output shows `['OCT.2026', 'APR.28']` — one date
from each. Read as a single strip carrying two dates, that pair produced a false conclusion
that survived into the decision log for a week (`DEC-030`, struck). Each strip has exactly
one expiry: Paracip is `APR.28`, the partial is `OCT.2026`.

The **strips** are downscaled to 1600px on the long side — the engine's default at the time
they were committed. **`max_side` is now resolved per script** (`DEC-073`): Latin runs at
**2048**, so these two files are no longer resized at all on the path that reads them;
Devanagari stays at **1280**.

The **newspaper is deliberately left at 1720px** and kept lossless, and that detail turned
out to matter more than it looks. Re-encoding it smaller would destroy the signal it exists
to measure, at a cost of 2.4 MB.

**A caution this file is now the evidence for.** `DEC-036` approved `max_side=1280` as
costing no accuracy, measured on this newspaper — but at 1720px on its long side, 1280
shrinks it by only 25%. A 4080×3072 phone photograph is shrunk by 69%, and small print does
not survive that: a foil strip at full phone resolution yielded 7 of 10 printed fields at
1280 against 10 of 10 at 2048 (`DEC-073`). **These fixtures are gentler than deployment**,
and a setting validated only on them has not been stressed. The same warning applies to the
notes: they were shot deliberately loose (`DEC-043`), and they are still the easy end of what
a blind photographer produces.

The two notes were shot on a phone and carry EXIF orientation. `curr-10.jpg` is stored
3072×4080 with a rotation tag, and the engines used to ignore it — every model saw that
note sideways. `app/imaging.py::load_upright` now applies the tag, and the committed
copies are re-encoded upright so the fixture matches what a viewer shows.

**The five notes are the deployment reality check, and they earned their keep.** Under the
single-source model two declined — ₹50 at 0.882 and ₹200 at 0.342, both loosely framed,
against training images cropped tight to the note (`DEC-043`). Merging independent sources
fixed both (₹200 → 0.926, ₹50 → 0.967) while the *benchmark went down* on a harder split,
0.9875 → 0.9810 — five deployment images caught what 840 test images could not (`DEC-052`).

**Current state, 7-class model, re-verified 2026-08-24 by `python -m eval.check_fixtures`:**

| | result |
|---|---|
| real notes answered correctly | **4 of 6** — `curr-200` withheld at 0.784, `curr-20-withheld` at 0.765 |
| non-notes correctly refused | **4 of 4** |
| worst false positive | `strip_paracip` → ₹100 at **0.840**, leaving **0.060** of headroom below the 0.90 bar |
| second worst | `cloth-pink-towel` → ₹20 at **0.804**, **0.096** of headroom |

**The two ₹20 rows are the finding, and only as a pair.** The towel scores **0.804** as a
twenty-rupee note; the actual twenty-rupee note scores **0.765**. A folded towel is a more
confident ₹20 than a ₹20 is, on an easy, evenly-lit, generously-framed photograph of the
note. Neither is spoken, so no user sees a failure today — the threshold holds both back.
But the *ordering* says what the 0.90 bar is really doing: it is not separating notes from
non-notes, it is sitting above a band where the two are interleaved. Any argument for
lowering the threshold to answer more notes now has a concrete counter-example that would
ship first, which is `DEC-062`'s point made with a second pair of images.

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
originals stay in `test-images/`, which is gitignored — so anything that only lives there
is not reproducible by anyone else, which is why the three 2026-08-24 additions were copied
in here rather than left behind.

**On the compression of the 2026-08-24 additions.** `curr-20-withheld.jpg` and
`cloth-pink-towel.jpg` are re-encoded at quality 85, halving them to ~2.2 MB each; the
classifier resizes to 224px, so this cannot plausibly move a prediction, and it was checked
anyway — both drifted **+0.003**, and the script that did it deletes the copy if the finding
stops reproducing. `strip_paracip_fullres.jpg` is **byte-for-byte** at 3.1 MB, because its
entire purpose is what a recogniser can resolve in small print at full phone resolution, and
compression artifacts land exactly there. A fixture is only worth its disk if it still
demonstrates the thing it was kept for.
