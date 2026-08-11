# Dataset Guide (Phase 2)

Drishti is built from **existing, licence-clean datasets**. There is no self-collected
photography phase.

That is a deliberate narrowing, decided 2026-08-11 (`DEC-047`), and it costs something
real: the project no longer claims an original Indian dataset. What it keeps is a routing
architecture, a safety guardrail, a measured prompt-engineering result, a cost-weighted
metric, and a decision log of things that were wrong and how that was found out. Those are
the contribution. Pretending 800 photographs were also taken would not have made it more
true.

The rest of this document is about getting the most out of public data, and being precise
about what public data cannot tell us.

---

## 1. What each mode needs, and where it comes from

Not every mode trains anything. That distinction drives everything below.

| Mode | Engine | Trained here? | Data source |
|---|---|---|---|
| Medicine | PaddleOCR + parsers + drug DB | **No** | Evaluation only — committed fixtures |
| Read | PaddleOCR | **No** | Evaluation only — committed fixtures |
| Currency | MobileNetV3 (ours) | **Yes** | Merged Kaggle sources + VizWiz negatives |
| Scene / Ask | SmolVLM + LoRA | **Yes** | VizWiz-VQA |

Medicine and Read run pretrained OCR and a database lookup. No quantity of photographs
improves them — photographs only *measure* them. This is why the old ~500-photo target for
those two modes was work without a payoff attached.

## 2. Currency — merge several sources rather than shoot

The trained model scores 0.9883 on its own test split and cleared the confidence threshold
on only 3 of 5 real handheld notes (`DEC-043`). The cause is capture diversity: every
training image came from one dataset, cropped tight to the note.

The fix without a camera is **more independent sources**. Different contributors shot at
different distances, on different surfaces, with different phones.

| Dataset | Licence | Use |
|---|---|---|
| `vishalmane109/indian-currency-note-images-dataset-2020` | **CC0-1.0** | Base, already in use (4,002 images) |
| `gauravsahani/indian-currency-notes-classifier` | **DbCL-1.0** | Merge |
| `pypiahmad/indian-rupees-and-thai-baht-banknotes` | **CC BY 4.0** | Merge — rupee classes only, **attribution required in the writeup** |
| `yashdogra/2000-notes` | **Apache-2.0** | Optional, ₹2000 only |
| ~~`shobhit18th/indian-currency-notes`~~ | **unknown** | **Excluded.** `DEC-022` requires a licence that permits use; "unknown" is not one |

Verify each licence yourself before merging — licences change, and a wrong one is not
something a reader of the writeup can check for you.

**Expect duplicates.** These datasets circulate and partly re-host each other. Deduplicate
by file hash *and* by perceptual hash before merging, or the same image lands in both train
and test and the accuracy number becomes fiction. This matters more than the extra images.

## 3. Currency negatives — VizWiz, not a shopping trip

The `background` class is the weakest part of the model: 431 photos of tables and hands from
one session, which do not generalise to anything else a camera gets pointed at. A medicine
strip scores `50` at 0.870, and only the 0.90 threshold prevents phantom money (`DEC-042`).

**VizWiz is a near-perfect negative set.** It is thousands of photographs taken by blind
people of arbitrary objects, in bad light, half-framed, blurry — the exact distribution a
"there is no note here" class needs, and almost none of it contains Indian currency.

- Sample ~500 VizWiz train images, excluding any whose question or answers mention money,
  currency, rupees, or a denomination.
- Add them to the `background` class alongside the existing 431.
- Annotations are already local in `data/vizwiz/`; images stream from
  `lmms-lab/VizWiz-VQA` or download via `data/scripts/download_vizwiz.py --images train`.

This is strictly better than photographing your own house: more surfaces, more lighting, and
captured by the population the app is for.

## 4. Scene and Ask — VizWiz, as originally planned

Unchanged. VizWiz train split for LoRA fine-tuning, weighted toward unanswerable examples
(`DEC-011`). This was never going to be self-collected data: the whole value of VizWiz is
that blind photographers took the photographs, which a sighted person cannot simulate.

## 5. Medicine and Read — evaluation only, and honestly small

No public dataset of Indian medicine strips with legible generic names and expiry dates was
found under a usable licence. Product photography from pharmacy sites is not licensed for
redistribution, so it cannot go in the repo or the writeup.

**Consequence, stated plainly:** medicine mode's ≥95% guardrailed-precision target cannot be
validated at that confidence on two fixtures. Options, in preference order:

1. **Restate the target as a measured range on a declared sample.** "On N strips, the
   guardrail declined every unverifiable name and reported no wrong drug" is honest and
   defensible at small N, as long as N is printed next to it.
2. **Opportunistic collection.** Strips already in the house, photographed as they turn up —
   no shooting sessions, no targets. Every one added is a real improvement on two.
3. **Drop the numeric target** and evaluate the guardrail logic by unit tests over the NLEM
   database, which already covers the nesting and combination cases exhaustively.

Recommendation: (1) plus (2) as it happens. Do not put an unvalidated ≥95% in the writeup.

The same applies to Read: Devanagari is confirmed on dense newsprint (1010 of 1238
characters) and thin on curved foil (14). Public Devanagari scene-text sets exist and are
worth checking if Read needs a stronger claim than "works on flat print".

## 6. Licensing and attribution

Every source above must appear in the writeup with its licence. CC BY 4.0 requires
attribution specifically — `pypiahmad` cannot be used silently.

Keep `data/README.md` listing each dataset, its licence, and the date it was verified. A
reader should be able to reconstruct the corpus without asking.

## 7. Layout and reproducibility

```
data/currency_raw/      each source's original download, untouched (gitignored)
data/currency/          merged, deduplicated, folder-per-class (gitignored)
data/vizwiz/            annotations (committed) + images (gitignored)
data/samples/           the committed fixtures that act as regression tests
```

Nothing large is committed. What *is* committed is the merge script and the manifest, so
the corpus is rebuildable from a clean checkout — that, not the images, is the artifact.

## 8. Before every training run

- Deduplicate across sources — by content hash and perceptual hash.
- Confirm class balance after merging; sources are unlikely to agree on denomination mix.
- Re-run `python eval/eval_currency.py` and compare against the recorded baseline
  (0.9883 accuracy, ₹5.37 expected error, 85.0% answered at 0.9961).
- **Re-run the five committed note fixtures in `data/samples/`.** Two currently fail. They
  are the only signal that new data fixed *deployment* rather than the benchmark, and the
  benchmark is exactly what merging more of the same kind of data will flatter.
