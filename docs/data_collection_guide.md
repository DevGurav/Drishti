# Custom Dataset Collection Guide (Phase 2)

Protocol for the Indian dataset described in `data/README.md` and `docs/synopsis.md`.
Read this before taking a single photo — the guiding principle, borrowed from VizWiz's own
findings, is: **a blind photographer can't verify framing, so a dataset of only perfect
studio shots will not match deployment conditions.** Deliberately include tilted, blurry,
half-framed and low-light shots alongside clean ones, in roughly the proportion a real
user's camera roll would have.

That used to be an argument from first principles. As of 2026-08-11 it is measured, and the
measurements say something sharper than "include some bad photos" — see below.

---

## 1. What the trained models already get wrong

This section exists so the shooting is aimed rather than merely diligent. Every number is
from `docs/BUILD_PLAN.md`'s decision log, not an impression.

### Currency: the benchmark is flattering, and the gap is framing

The classifier scores **0.9883** on the Kaggle test split, and **0.9961** on the answers it
is confident enough to give. On five real handheld notes it got the denomination right
every time but **only 3 of 5 cleared the confidence threshold** — ₹50 at 0.882, ₹200 at
0.342, against a 0.90 bar.

The two that failed were the two *loosely framed* shots. Kaggle's images are cropped tight
to the note; a user holding a note at arm's length is not. Swapping the eval-time crop was
tested and **rejected** — it helped those five photos and hurt the 600-image test set
(`DEC-043`). The gap is the data, which makes it yours to close.

> **Shoot notes the way a user holds them: at arm's length, note occupying maybe a third to
> a half of the frame, plenty of surroundings.** Tight, well-centred shots are the case that
> already works. If a photo looks like a product listing, it is not adding much.

### Currency: the confusions are systematic, not random

| actual → predicted | count | cost |
|---|---|---|
| ₹20 → ₹200 | 3 | ₹540 |
| ₹50 → ₹500 | 1 | ₹450 |
| ₹2000 → ₹10 | 1 | ₹1990 |
| background → ₹200 | 1 | ₹200 |

The frequent pairs differ by a trailing zero, and **both err upward** — the user is told
they hold ten times what they do, which is how someone gets short-changed at a counter
(`DEC-041`).

> **Over-sample ₹20/₹200 and ₹50/₹500.** Roughly 60 each rather than 40, taken from the
> other denominations. An extra ₹100 photo is worth much less than an extra ₹20.

### Currency: "no note here" barely works

The Kaggle `background` class is 431 photos of tables and hands from one session. It does
not generalise to anything else the camera gets pointed at (`DEC-042`):

| photographed | predicted | confidence |
|---|---|---|
| medicine strip | ₹50 | **0.870** |
| Marathi newspaper | ₹100 | 0.705 |
| partial strip | ₹500 | 0.578 |

All three declined only because the threshold is 0.90 — the strip missed being announced as
a ₹50 note by 0.03. Right now that threshold is the *only* thing preventing phantom money.

> **Shoot ~100 note-free negatives**, and make them varied: kitchen counters, fabric, tiled
> and concrete floors, newspaper, food packaging, a hand holding nothing, an empty table in
> bad light. This is the single highest-value category in the whole collection and it costs
> nothing but shutter presses.

### Read mode: dense print works, curved foil barely does

Devanagari OCR is confirmed — a photographed Maharashtra Times page returned **1010
Devanagari characters of 1238**, headline and body both accurate. The same recogniser
managed only **14 characters** on `पॅरासिप-500` printed on curved medicine foil.

> Flat printed Devanagari is a solved case; a little more is enough to confirm it. Spend the
> effort on **signage, packaging and labels** — curved, reflective and low-contrast
> surfaces are where the mode is actually weak.

### Medicine: combination strips are now supported, so collect them

`find_matches()` reports every active ingredient (`DEC-046`). That path has been tested
against the NLEM list but has **never seen a real combination pack through OCR**.

> Deliberately buy or borrow a few combination strips — `IBUPROFEN + PARACETAMOL`,
> `AMOXICILLIN + CLAVULANIC ACID`, cold and flu combinations. Also worth collecting: packs
> where the generic line is *small* or wraps, since the guardrail needs the generic, and
> packs carrying **two dates** (carton and blister in one frame), which `earliest_expiry()`
> handles but no photo has ever exercised (`DEC-025`).

### Scene: the failure to capture is confabulation, not blindness

Asked to describe the Paracip strip, the VLM produced fluent prose that was right about the
drug and invented the rest — "contains 30 tablets" for a 10-tablet strip, "clear plastic
material" for opaque foil (`DEC-037`).

> Scene photos are worth collecting for evaluation, not just training. When labelling, write
> down what a describer **should not** claim about the image, not only what it contains.

---

## 2. Privacy rules (non-negotiable)

- No faces. No ID documents, bank cards, prescriptions with a patient's name, or anything
  else identifying a real person.
- **Note serial numbers count.** They are printed on every ₹ note and traceable; blur them
  before a photo leaves your machine, and never put one in the report.
- If a bystander appears accidentally in a scene shot, crop or blur them out before adding
  the file — don't leave it and hope.
- In a shared or public space, get verbal consent from anyone who might end up in frame.

## 3. Target counts by mode (~800 total; adjust pro-rata)

| Mode | Target | What to vary |
|---|---|---|
| Medicine | ~300 | drug (`data/drug_names_seed.txt` is a brand checklist; the guardrail matches the *generic* from `data/drug_names_nlem2022.txt`, so the generic line must be legible), **combination packs**, **two-date packs**, strip vs. box, front vs. back, bright/dim, straight vs. 15–30° tilt, distance, finger or fold occlusion, faded print |
| Currency | ~250 | all of ₹10/20/50/100/200/500, **~60 each for ₹20, ₹200, ₹50, ₹500** and ~40 for the rest; **loose framing at arm's length**; fresh/worn/folded; front and back; partially out of frame; varied surfaces |
| Currency negatives | **~100** | no note in frame at all — counters, floors, fabric, paper, packaging, empty hands, cluttered desks, poor light |
| Read / labels | ~200 | signage, MRP tags, product labels, food packets, mixed English + Devanagari, **curved and reflective surfaces**, expiry and net-weight print |
| Scene | ~150 | indoor and outdoor, several rooms, varied lighting, single-object vs. cluttered, some deliberately blurry or handheld |

## 4. File naming & storage

- `data/custom/images/{mode}_{4-digit-index}.jpg`, e.g. `medicine_0001.jpg`
  (gitignored — images stay local, only labels are committed)
- Negatives go in as `currency_negative_0001.jpg`, so they can be split out or folded into
  the `background` class without renaming later.
- One image file to one row in `data/custom/labels.csv`.
- **Phone photos are fine as-is.** Every engine applies EXIF orientation
  (`app/imaging.py::load_upright`), so a photo taken sideways is handled. Do not "fix" it by
  re-saving through an editor that strips the tag.

## 5. Labelling workflow

1. Copy `data/custom/labels_template.csv` to `data/custom/labels.csv` and append a row per
   photo *as you shoot it* — batching this loses the details you needed.
2. `question` — phrase it the way a blind user would say it aloud ("what medicine is this",
   "what note is this").
3. `answer` — the ground truth a sighted person would give, in the question's language
   where practical. For a combination strip, list **every** active ingredient.
4. Cover **English, Hindi and Marathi from the start**, not bolted on at the end —
   otherwise the IndicTrans2 and TTS path is only exercised when there is no time to fix
   language-specific failures.

## 6. Before every fine-tuning run

Spot-check a random 10% of `labels.csv` against the actual images. Mislabelled training data
is a silent failure: the model trains fine and the accuracy drop surfaces later as a mystery.

Then re-run `python eval/eval_currency.py` and compare against the recorded baseline
(0.9883 accuracy, ₹5.37 expected error, 85.0% answered at 0.9961). **Also re-run the five
committed note fixtures in `data/samples/` — two of them currently fail, and they are the
cheapest signal that new data actually fixed deployment rather than just the benchmark.**
