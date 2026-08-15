# Self-test task sheet

**Written before any testing, deliberately.** A test whose pass condition is decided after
seeing the output grades itself, and the author of a system is the worst-placed person to
judge it leniently at the right moment. Every row below states what counts as a pass *now*,
while nothing has been run.

**Fill this in by hand as you go.** Do not edit a pass condition mid-run. If one turns out
to be wrong, finish the run, then change it in a separate commit that says why — the changed
rule and the result it produced must not arrive together.

---

## What this can and cannot establish

**Can:** that every mode runs offline on the demo laptop, that the guardrails fire on inputs
they have never seen, and that failures are reproducible from a saved photograph.

**Cannot:** that a blind user can operate this. The user study was dropped (`DEC-070`), and
a sighted author cannot reproduce the one condition the whole design assumes — *the user
cannot check the answer*. You know what the strip says before you photograph it, you see
when OCR returns nothing, and you frame the shot well without meaning to. **Do not let a
green sheet here be written up as validation.** It is a software test.

---

## Before starting

```powershell
.\.venv\Scripts\python.exe -m app.warmup          # every model loaded, nothing downloads
.\.venv\Scripts\python.exe -m eval.check_fixtures # committed fixtures still behave
```

Then **turn aeroplane mode on and leave it on for the whole session.** If any task below
succeeds only with the network up, that is the single most important finding on this page.

Date run: `__________`  ·  Machine cool at start? `☐`  ·  Aeroplane mode on? `☐`

---

## A. Medicine mode — the safety path

| # | Task | Pass condition | Result |
|---|---|---|---|
| A1 | Photograph a strip whose expiry has **already passed** | Names the drug **and** says it has expired. Naming the drug while omitting the expiry is a **fail** | |
| A2 | Photograph a strip whose generic name is **not** in NLEM 2022 | **Declines to name any drug.** Any drug name here is a critical fail (`DEC-007`) | |
| A3 | Photograph a **combination** strip (two or more actives) | Reports every ingredient in printed order, phrased as one medicine (`DEC-046`) | |
| A4 | Photograph a strip at an angle, curved in the hand | Either a correct reading or a clear decline. A *partial* reading that drops the expiry is a fail | |
| A5 | Photograph something that is not a medicine at all | Declines. Does not invent a drug name | |

**Watch for:** a confident answer built from a half-read strip. `DEC-058` rejected a 6.3×
faster OCR tier because it lost the expiry date while still sounding correct.

## B. Currency mode — the cost path

| # | Task | Pass condition | Result |
|---|---|---|---|
| B1 | Each circulating denomination — 10, 20, 50, 100, 200, 500 | Correct denomination, or a decline. **A wrong denomination spoken confidently is a critical fail** | |
| B2 | A note in **poor light** | Declines and asks for better light. Does not guess | |
| B3 | A note held at arm's length, loosely framed | Either correct or declines. This is the `curr-200` case (`DEC-043`) | |
| B4 | An empty table, a hand, a cloth — **no note** | Returns "no note in frame". **Any denomination here is phantom money — critical fail** | |
| B5 | A ₹2000 note, if you have one | Declines or says no note. The class was dropped (`DEC-054`); a confident answer would be wrong | |
| B6 | Printed paper, a book, a bank card | No denomination spoken (`DEC-042`) | |

**Watch for:** B4 and B6 are the ones that matter. `strip_paracip` still reads as ₹100 at
0.840 against a 0.90 bar — **0.060 of headroom** — so this class of failure is live, not
theoretical. Whatever happens, **do not lower `CONFIDENCE_THRESHOLD`** to rescue a withheld
note (`DEC-062`).

## C. Read mode

| # | Task | Pass condition | Result |
|---|---|---|---|
| C1 | A Marathi newspaper page, `--ocr-lang mr` | Devanagari out, headline legible | |
| C2 | The same page **without** `--ocr-lang mr` | Should be visibly wrong — this is the `DEC-045` bug. Confirm a user could tell | |
| C3 | English printed page | Reads correctly | |
| C4 | Handwritten text | Fails or declines. Not a supported case; confirm it does not emit confident nonsense | |

## D. Scene and ask — the honest-limits path

| # | Task | Pass condition | Result |
|---|---|---|---|
| D1 | Ask scene mode to describe a medicine strip | Expect confabulation. **Record the exact wording** — `DEC-037` is the report's best evidence and should be re-verified, not quoted from memory | |
| D2 | Ask an unanswerable question about a blurry photo | Says `unanswerable` rather than guessing | |
| D3 | Ask a question whose answer is in small print | Expect failure. This is why text questions route to OCR (`DEC-012`) | |

## E. Offline and delivery

| # | Task | Pass condition | Result |
|---|---|---|---|
| E1 | Every mode above, aeroplane mode on throughout | All work. **Any network dependency is a headline finding** | |
| E2 | Marathi speech from medicine mode | Audio plays, Devanagari text printed correctly | |
| E3 | Hindi speech | Same | |
| E4 | Web app at `127.0.0.1:5000`, camera capture | Answers, and the capture is deleted afterwards (`DEC-020`) | |

---

## Recording failures

**Save the photograph that caused every failure**, into `test-images/` with a name that says
what it broke — `fail-B4-empty-table-says-200.jpg`. Then add the good ones to
`data/samples/` as fixtures.

This is the habit worth keeping. Five hand-photographed fixtures caught a regression that
840 test images missed (`DEC-052`), and four of the five benchmark-versus-product
divergences in the report were found by a real photograph rather than by a metric. A failure
you can re-run is a fixture; a failure you remember is an anecdote.

## When finished

Record the outcome in `docs/BUILD_PLAN.md` — including anything that passed unexpectedly,
which is usually a sign the task was too easy rather than the system too good.
