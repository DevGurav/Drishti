# Datasets

## 1. VizWiz-VQA (core training/eval data)

~30k photos taken by blind users with their spoken questions + 10 crowdsourced answers each.
This is our deployment distribution: blurry, tilted, thumb-in-frame images.

- Official page (license: CC BY 4.0): https://vizwiz.org/tasks-and-datasets/vqa/
- Easiest programmatic access (used by our notebooks): Hugging Face `lmms-lab/VizWiz-VQA`
- Local annotation download: `python scripts/download_vizwiz.py` (annotations only, ~small;
  image zips are several GB — download only when needed, or stream from HF in Colab)

## 2. Custom Indian dataset (we collect this — M3)

Full protocol (target counts per mode, privacy rules, naming convention, labeling workflow):
**`docs/data_collection_guide.md`**. Schema template: `data/custom/labels_template.csv`.
Keep faces and personal documents OUT of the dataset.

## 3. Indian currency (for MobileNet classifier)

Public Kaggle datasets exist (search "indian currency notes classification"); verify license
before use, augment heavily (folds, occlusion, low light). Once you've picked one:
`python data/scripts/download_currency.py --dataset <owner>/<slug>` (needs a Kaggle API
token — see the script's docstring for one-time setup).

## 4. Drug-name database (medicine-mode guardrail)

**`data/drug_names_nlem2022.txt`** — 391 names expanded from the 384 entries of the
**National List of Essential Medicines 2022**, published by the Ministry of Health and Family
Welfare via CDSCO. Government-issued, dated and citable, which is what `DEC-007`'s promise of
a *verified* database requires.

- Regenerate: `python data/scripts/build_drug_db.py`
- Verify the committed file still matches the source: `python data/scripts/build_drug_db.py --check`
- The file is committed rather than downloaded at runtime: Drishti is offline-first, and a
  demo machine cannot depend on cdsco.gov.in being reachable.

**Generic names only.** Indian labelling requires the generic name on the pack, so brand
strips still match (`CROCIN … PARACETAMOL TABLETS IP` → `Paracetamol`). The ~250k brand names
have no authoritative public list, and inventing one would defeat the point of the guardrail.
A strip whose generic name OCR cannot read declines rather than guesses.

`data/drug_names_seed.txt` is no longer used by the app. It survives as the photography
checklist for Phase-2 data collection — common Indian brands worth capturing.
