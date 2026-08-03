# Sample images

Small committed fixtures so notebooks and tests can run without uploading anything.

| File | What it is |
|---|---|
| `strip_paracip.jpg` | Paracip-500 strip, back side — the read that produced 55 OCR lines including drug name, `EXP.OCT.2026` and `Rs.10.30` |
| `strip_partial.jpg` | Same session, worse framing — only 3 lines recognized. Kept deliberately as the negative case |

Downscaled to 1600px on the long side, which is exactly
`app/engines/paddle_ocr.py::DEFAULT_MAX_SIDE` — the engine would downscale to this anyway,
so nothing is lost and the files stay ~300 KB instead of ~3.4 MB.

These are **fixtures, not the dataset**. The real collection lives in `data/custom/`
(gitignored) and follows `docs/data_collection_guide.md`. Full-resolution originals stay in
`test-images/`, also gitignored.
