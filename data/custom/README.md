# Custom Indian Dataset

See `docs/dataset_guide.md` for where the data comes from (public sources, licences,
privacy rules, naming convention) before shooting anything.

- `labels_template.csv` — schema to copy into `labels.csv` as you collect: one row
  per photo, columns `filename, mode, question, answer, lang, notes`.
- `images/` — gitignored; photos stay local, only the CSV (text, no personal data) is
  committed.
