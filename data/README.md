# Datasets

**No self-collected photography** (`DEC-047`). Every training image comes from a
licence-clean public dataset, and the corpus rebuilds exactly from
`data/currency_manifest.csv` without any images being committed to this repository.

**Licences verified: 2026-08-15.** A platform licence tag records the uploader's claim, not
a provenance audit — see the warning under §1.3.

---

## 1. Indian currency (MobileNetV3-Small classifier)

### 1.1 Sources

Four sources, merged and deduplicated by `data/scripts/merge_currency.py`. Counts are the
images **surviving** deduplication, and are reproduced directly from the committed manifest.

| source | licence | attribution | kept |
|---|---|---|---|
| `vishalmane109/indian-currency-notes-classifier` | CC0-1.0 | not required | 3,083 |
| `pypiahmad/indian-rupees-and-thai-baht-banknotes` | CC BY 4.0 | **required** | 1,961 |
| VizWiz-VQA negatives (`background`) | CC BY 4.0 | **required** | 485 |
| `gauravsahani/indian-currency-notes-classifier` | DbCL-1.0 | not required | 73 |
| ~~`shobhit18th/indian-currency-note-images-dataset`~~ | **unknown — excluded** | — | — |

`shobhit18th` is excluded on licence grounds alone (`DEC-022`): an unstated licence cannot
be verified, and the corpus has to be redistributable as a manifest.

**Total: 5,602 images across 8 classes.** Training uses **5,010 across 7** — the ₹2000 class
(592 images) stays in the manifest but is excluded at training time via `--exclude 2000`,
which keeps the decision reversible (`DEC-054`).

| class | images | | class | images |
|---|---|---|---|---|
| `10` | 847 | | `500` | 516 |
| `20` | 653 | | `background` | 883 |
| `50` | 833 | | `2000` | 592 *(excluded)* |
| `100` | 773 | | | |
| `200` | 505 | | **total** | **5,602** |

`background` is the largest class by design — it is the model's only honest place to put a
photograph with no note in it. Without it a softmax **must** name a denomination, and money
mode would speak an amount for a picture of a table (`DEC-039`).

### 1.2 Why four sources rather than one

A model trained on `vishalmane109` alone scored 0.9883 on that dataset's own split and
cleared its confidence threshold on **3 of 5** real handheld notes — every image in it is
cropped tight to the note, which is not what a blind user's camera produces (`DEC-043`).
Merging independent sources bought capture diversity — different distances, surfaces and
lighting — and took the fixtures to **5 of 5** (`DEC-052`).

The `background` class ("no note in frame") comes mostly from **VizWiz**, which is
photographs taken by blind people — the actual deployment distribution. Entries mentioning
money or a denomination were filtered out first: 462 of 20,523 excluded, 500 sampled, 485
surviving deduplication (`DEC-042`).

### 1.3 Deduplication, label conflicts and one licence warning

- **23% of the base dataset was redundant** — 591 exact and 489 near-duplicate images
  dropped from 6,197. Left in, 33.5% of the test split duplicated a training image, which
  understated expected rupee cost by 54% (`DEC-049`).
- **Deduplication is same-class only.** Cross-class look-alikes are hard negatives, not
  leakage — `pypiahmad` shot every denomination in one fixed setup, so a perceptual hash
  matches ₹200 and ₹500 frames that are genuinely different notes (`DEC-050`).
- **Seven images were byte-identical with contradictory labels**, resolved per SHA-256 in
  `RESOLVED_CONFLICTS` rather than by a rule. Five were RBI **SPECIMEN** ₹50 notes filed as
  `background` — they would have taught the model to decline on real money (`DEC-053`).
- ⚠️ **One image in the CC0-tagged `vishalmane109` set carries a visible Shutterstock
  watermark.** A CC0 declaration by an uploader is not evidence they held the rights.
  **No dataset image may be reproduced in the report or any presentation** — use the five
  self-photographed fixtures instead.

### 1.4 Rebuild

```bash
python data/scripts/download_currency.py --dataset <owner>/<slug>   # needs a Kaggle token
python data/scripts/sample_vizwiz_negatives.py                      # background class
python data/scripts/merge_currency.py --clean                       # dedup + manifest
```

`merge_currency.py` writes `data/currency_manifest.csv` — filename, class, source, licence,
SHA-256 and perceptual hash per row. `--clean` is required to rebuild, because a cache keyed
on mere existence is a silent staleness bug (`DEC-056`).

---

## 2. VizWiz-VQA (benchmark, fine-tuning split, currency negatives)

~30k photographs taken by blind users with their spoken questions and 10 crowdsourced
answers each. This is the deployment distribution: blurry, tilted, thumb in frame. Roughly
half the validation set is unanswerable by construction, which is what makes abstention
measurable.

- Official page — <https://vizwiz.org/tasks-and-datasets/vqa/> · **licence CC BY 4.0,
  attribution required**
- Annotations: `python data/scripts/download_vizwiz.py` (~21 MB)
- **The `train` split is not on Hugging Face.** `lmms-lab/VizWiz-VQA` carries `test` and
  `val` only — it is an evaluation dataset. The 20,523-pair train split exists solely as an
  11.3 GB archive, so `data/scripts/vizwiz_images.py` pulls individual images out of it over
  HTTP range requests (`DEC-055`).
- **Training on `val` is deliberately rejected**: evaluation is `val[:500]`, so fine-tuning
  on the remainder would flatter the headline in a way no reader could verify.

---

## 3. Drug-name database (medicine-mode guardrail)

**`data/drug_names_nlem2022.txt`** — 391 names expanded from the 384 entries of the
**National List of Essential Medicines 2022**, published by the Ministry of Health and
Family Welfare via CDSCO. Government-issued, dated and citable, which is what `DEC-007`'s
promise of a *verified* database requires.

- Regenerate: `python data/scripts/build_drug_db.py`
- Verify the committed file still matches the source: `python data/scripts/build_drug_db.py --check`
- Committed rather than fetched at runtime: Drishti is offline-first, and a demo machine
  cannot depend on `cdsco.gov.in` being reachable.

**Generic names only.** Indian labelling requires the generic on the pack, so brand strips
still match through it (`CROCIN … PARACETAMOL TABLETS IP` → `Paracetamol`). The ~250k brand
names have no authoritative public list, and inventing one would defeat the guardrail. A
strip whose generic name OCR cannot read **declines rather than guesses**.

`data/drug_names_seed.txt` is no longer used by the app and is retained only as history.

**Evaluation is deliberately small, and says so.** No public dataset of Indian medicine
strips with legible generic names and expiry dates exists under a redistributable licence,
so medicine mode is evaluated on committed fixtures. The ≥95% guardrailed-precision target
therefore **cannot be validated and is not claimed** (`DEC-048`).

---

## 4. Privacy rules for anything added here

- **No faces, no identity documents, no prescriptions carrying a patient name.**
- Banknote **serial numbers are traceable to a transaction** — the five self-photographed
  fixtures are blurred at the serial, and no note image appears in the report.
- Captures made by the app are deleted immediately after answering, including on engine
  error (`DEC-020`).
