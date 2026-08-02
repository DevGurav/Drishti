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

Options to evaluate in M2: open lists derived from CDSCO-approved drug names / India
generic-medicine lists. Needed: one text file of valid drug names for fuzzy string matching.
