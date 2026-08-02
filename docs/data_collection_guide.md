# Custom Dataset Collection Guide (Milestone M3)

Protocol for the 500–1,000-photo Indian dataset described in `data/README.md` and
`docs/synopsis.md`. Read this before taking a single photo — the guiding principle,
borrowed from VizWiz's own findings, is: **a blind photographer can't verify framing,
so a dataset of only perfect studio shots will not match deployment conditions.**
Deliberately include tilted, blurry, half-framed, and low-light shots alongside clean
ones, in roughly the same proportion you'd expect a real user's camera roll to have.

## Privacy rules (non-negotiable)

- No faces. No ID documents, bank cards, prescriptions with a patient's name, or
  anything else that identifies a real person.
- If a bystander appears accidentally in a scene-mode background shot, crop or blur
  them out before adding the file to the dataset — don't just leave it and hope.
- If shooting in a shared/public space, get verbal consent from anyone nearby who
  might end up in frame.

## Target counts by mode (aim for ~700 total; adjust pro-rata for your final total)

| Mode | Target | What to vary |
|---|---|---|
| Medicine | ~300 | drug (use `data/drug_names_seed.txt` as a checklist, then go beyond it), strip vs. box, front vs. back, lighting (bright/dim), angle (straight/15–30° tilt), distance, partial finger/fold occlusion, faded/worn print |
| Currency | ~250 | every denomination in circulation (₹10/20/50/100/200/500), roughly balanced per class (~40 each), fresh/worn/folded, front and back, partial note half out of frame, varied backgrounds |
| Read / labels | ~200 | MRP tags, product labels, food packet text, mixed English + Devanagari, expiry/net-weight print |
| Scene | ~150 | indoor + outdoor, multiple rooms, varied lighting, single-object vs. cluttered, some deliberately blurry/handheld |

## File naming & storage

- `data/custom/images/{mode}_{4-digit-index}.jpg`, e.g. `medicine_0001.jpg`
  (this path is already gitignored — images stay local, only labels get committed)
- Keep a 1:1 mapping between each image file and one row in `data/custom/labels.csv`

## Labeling workflow

1. Copy `data/custom/labels_template.csv` to `data/custom/labels.csv` and append one
   row per photo as you shoot it — don't batch this for later, you'll forget details.
2. `question` — phrase it the way a blind user would actually ask it aloud
   ("what medicine is this", "what denomination is this note").
3. `answer` — the ground-truth a sighted person would give, in the same language as
   the question where practical.
4. Cover **all three languages (English/Hindi/Marathi)** from the start, not bolted
   on at the end — otherwise the IndicTrans2 + TTS pipeline only gets exercised late,
   when there's no time left to fix language-specific failures.

## Before every fine-tuning run

Spot-check a random 10% sample of `labels.csv` against the actual image for label
correctness. Mislabeled fine-tuning data is a silent failure mode — the model trains
fine and the accuracy drop only shows up as a mystery later.
