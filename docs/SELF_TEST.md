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

> **Judge every task by what you HEAR, not by what is printed.** Added 2026-08-22 after
> `DEC-072`, `DEC-074`: for twelve days the printed text was correct while the audio said
> something else — ₹500 announced as "00", an MRP of ₹10.30 as ₹100, and a Marathi page
> rewritten into different Marathi before being read out. Every automated check in this
> repository passed throughout, because they all read the text. **Use headphones, play the
> answer, and compare it to the object in your hand** — not to the line on screen.
>
> This changes no pass condition. It says which artifact to apply them to, which the sheet
> failed to state, and that omission is the reason three bugs survived to be found by ear.

Date run: **2026-08-22** (by hand, stopped in section B) and **2026-08-24** (16 photographs,
via `python -m eval.run_self_test`, then the browser app in aeroplane mode)  ·  Machine cool
at start? `☑`  ·  Aeroplane mode on? **`☑` for the browser-app session (E1, E4); `☒` for the
CLI battery in A–D, which ran with the network up.**

> **Read the Result column as "checked by machine", not "checked".** The 08-24 session ran
> every task and compared the printed answer to the object in the photograph, which settles
> the refusals, the denominations and the missing expiries. It does **not** settle the one
> thing this page says matters most: `dropped_characters` can prove which characters a voice
> will discard, and cannot prove the wav is intelligible. **Rows marked PARTIAL are waiting
> on a person with headphones.**

---

## A. Medicine mode — the safety path

| # | Task | Pass condition | Result |
|---|---|---|---|
| A1 | Photograph a strip whose expiry has **already passed** | Names the drug **and** says it has expired. Naming the drug while omitting the expiry is a **fail** | **NOT RUN** — no expired strip was photographed. All four in the batch expire in the future. This is the most important untested row on the sheet |
| A2 | Photograph a strip whose generic name is **not** in NLEM 2022 | **Declines to name any drug.** Any drug name here is a critical fail (`DEC-007`) | **PASS** — Easibreathe (camphor/chlorothymol/eucalyptol/menthol/terpineol): *"I couldn't verify the medicine name on this strip."* No drug named |
| A3 | Photograph a **combination** strip (two or more actives) | Reports every ingredient in printed order, phrased as one medicine (`DEC-046`) | **FAIL, safely** — ZIFI CV 200 (Cefixime + Clavulanate). Declined. The matcher finds both actives given clean text; OCR returned 211 chars of noise and never read the header, which is printed across the blister bubbles. Declining beats guessing, but the row does not pass |
| A4 | Photograph a strip at an angle, curved in the hand | Either a correct reading or a clear decline. A *partial* reading that drops the expiry is a fail | **NOT RUN** — every strip was flat on the floor |
| A5 | Photograph something that is not a medicine at all | Declines. Does not invent a drug name | **PASS** — a Vaseline lip-balm tube. Declines, invents nothing |
| A3b | *(added)* A 9-active multivitamin — Becosules | Every ingredient once | **PARTIAL** — reports 2 of 9, *"a combination of Ascorbic acid and Riboflavin"*. Given clean text the matcher returns **both `Vitamin C` and `Ascorbic acid`** — the same substance, twice, from two NLEM entries. `DEC-033`'s occurrence counting cannot see it: neither name contains the other. **This row is also where `DEC-076` was found and where the fix is visible.** Its ₹62.37 was delivered as `एम. आर. पी. 62 रुपये आणि सत्ततीस पैसे आहे` — Latin digits the Marathi voice would have read as "62 … 7". After the fix the price sentence is **dropped** and the answer ends `…मिश्रण आहे. तो दोन हजार सत्तावीस मार्चपर्यंत वैध आहे.` — ingredients and expiry kept, price withheld |
| A-ctl | *(added)* Paracip at full phone resolution, 4080×3072 | Drug name, expiry and MRP — the committed 1600px fixture of this same product reads all three | **FAIL** — names Paracetamol, then *"I could not read a clear expiry date — please check manually."* No MRP either. `DEC-073` raised Latin `max_side` to 2048 for exactly this, and **2048 is not enough here**. It says so rather than omitting silently, which is the designed behaviour |

**Watch for:** a confident answer built from a half-read strip. `DEC-058` rejected a 6.3×
faster OCR tier because it lost the expiry date while still sounding correct.

## B. Currency mode — the cost path

| # | Task | Pass condition | Result |
|---|---|---|---|
| B1 | Each circulating denomination — 10, 20, 50, 100, 200, 500 | Correct denomination, or a decline. **A wrong denomination spoken confidently is a critical fail** | **PASS on 5 of 6; ₹200 not photographed.** ₹10 (0.978), ₹50 (0.961), ₹100 (0.977), ₹500 (0.970) all spoken correctly. **₹20 correct at 0.765 → withheld**, which the condition allows. No wrong denomination anywhere |
| B2 | A note in **poor light** | Declines and asks for better light. Does not guess | **NOT RUN** — every note was shot in even daylight |
| B3 | A note held at arm's length, loosely framed | Either correct or declines. This is the `curr-200` case (`DEC-043`) | **NOT RUN** — every note was flat and generously framed |
| B4 | An empty table, a hand, a cloth — **no note** | Returns "no note in frame". **Any denomination here is phantom money — critical fail** | **PASS, with a caveat.** Floor and hand both return `background` → *"I can't see a note in this photo."* The **cloth refuses differently**: it predicted **₹20 at 0.804** and was held back by the threshold, so it says *"I'm not confident about this note"* — implying a note is there. No phantom money, but the refusal is the wrong kind, and 0.804 is **higher than the real ₹20 scored (0.765)** |
| B5 | A ₹2000 note, if you have one | Declines or says no note. The class was dropped (`DEC-054`); a confident answer would be wrong | **NOT RUN** — none available |
| B6 | Printed paper, a book, a bank card | No denomination spoken (`DEC-042`) | **PASS on printed paper** — a Marathi notice and an electricity bill both return `background` at 0.915 / 0.946. **Book and bank card not photographed** |

**Watch for:** B4 and B6 are the ones that matter. `strip_paracip` still reads as ₹100 at
0.840 against a 0.90 bar — **0.060 of headroom** — so this class of failure is live, not
theoretical. Whatever happens, **do not lower `CONFIDENCE_THRESHOLD`** to rescue a withheld
note (`DEC-062`).

## C. Read mode

| # | Task | Pass condition | Result |
|---|---|---|---|
| C1 | A Marathi newspaper page, `--ocr-lang mr` | Devanagari out, headline legible | **PASS on text.** A printed Marathi society notice (no newspaper available). Headline `बृहन्मुंबई महानगरपालिका कर्मचारी देवयानी नं.२` correct, and **not rewritten** — `DEC-074`'s fix holds. **But the voice drops `०१२३४५६७८९` entirely**, so the meeting's date `०६/०९/२०२६` and time `१०.३०` are silent. Known-open residual of `DEC-074`, now observed live |
| C2 | The same page **without** `--ocr-lang mr` | Should be visibly wrong — this is the `DEC-045` bug. Confirm a user could tell | **PASS** — `DEC-045` reproduces. Latin recogniser on Devanagari gives `2 142H () ( -) 73000-()…`, which delivery then renders as fluent Marathi nonsense (`दोनशे बावीस एच…`). A listener hears a stream of disconnected numbers and letters and would know |
| C3 | English printed page | Reads correctly | **PASS** — an Adani electricity bill, dense small print, read at 2048. Exposed a minor defect: `A-003` is spoken **"A-three"**, because `spell_numbers_in_text` drops leading zeros |
| C4 | Handwritten text | Fails or declines. Not a supported case; confirm it does not emit confident nonsense | **PASSED, AND SHOULD NOT HAVE.** OCR read most of a handwritten page (`1A1. modulel 1. pplication of AI in healthcare. 2.Define AI, mL, DL…`). The sheet says to record unexpected passes: this image came through WhatsApp at 1599×1396 and the writing is neat on ruled paper. **The task was too easy, not the system too good** |

## D. Scene and ask — the honest-limits path

| # | Task | Pass condition | Result |
|---|---|---|---|
| D1 | Ask scene mode to describe a medicine strip | Expect confabulation. **Record the exact wording** — `DEC-037` is the report's best evidence and should be re-verified, not quoted from memory | **CONFABULATION REPRODUCES VERBATIM**, 293.5s, third independent run. Exact wording: *"The image displays a blister pack of Paracetamol tablets. The blister pack is labeled as 'Paracetamol Tablets 500mg' and **contains 30 tablets**. The tablets are arranged in a grid pattern within the blister pack. The blister pack is made of a **clear plastic material and has a white backing**."* It holds **10** tablets and is **opaque foil** |
| D2 | Ask an unanswerable question about a blurry photo | Says `unanswerable` rather than guessing | **NOT RUN** — no blurry photo taken |
| D3 | Ask a question whose answer is in small print | Expect failure. This is why text questions route to OCR (`DEC-012`) | **PASS (fails safely)** — asked for the bill's total. *"I can't tell from this photo. Try again with better light or framing."* Declines rather than inventing a figure |

## E. Offline and delivery

| # | Task | Pass condition | Result |
|---|---|---|---|
| E1 | Every mode above, aeroplane mode on throughout | All work. **Any network dependency is a headline finding** | **PASS, via the browser app.** Aeroplane mode on at the OS level, `python -m app.web.server` started, photos captured and answered through the UI. **No network dependency found** — the page loaded with no external fetch and the engines answered from cached weights. **Scope, stated so it is not read as more:** this exercises the path the demo actually uses, end to end, which is the strongest single check of the offline claim. It does **not** enumerate all 22 tasks individually — sections A–D above were run through the CLI with the network up |
| E2 | Marathi speech from medicine mode | Audio plays, Devanagari text printed correctly | **PARTIAL** — Devanagari printed correctly, wav written, and the tokenizer check says only `ॅ`/`ॉ` are lost (the known one-voice residual, `DEC-072`). **Nobody has listened.** That is the check that found all three defects on 08-22 |
| E3 | Hindi speech | Same | **PARTIAL, and cleaner than Marathi** — `यह पेरासिटामोल है। मैं एक स्पष्ट समाप्ति तिथि नहीं पढ़ सका` with **nothing dropped at all**, confirming `DEC-072`'s finding that the residual belongs to the Marathi voice rather than to the pipeline. Also unheard |
| E4 | Web app at `127.0.0.1:5000`, camera capture | Answers, and the capture is deleted afterwards (`DEC-020`) | **PASS on answering** — same session as E1: camera capture through the browser, answers returned. **The deletion half was not separately observed**, and is covered by unit tests rather than by this row. Worth a glance at `runtime/` next time the app runs |

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

---

## Outcome, 2026-08-24

**13 of 22 rows exercised. 9 had no input.** Full per-task output in
`eval/results/self_test_results.csv`; re-runnable with `python -m eval.run_self_test`.

| | |
|---|---|
| Passed | A2, A5, B1 (5 of 6 denominations), B4, B6 (paper only), C1, C2, C3, D1, D3, **E1**, E4 (answering half) |
| Failed | **A3** (declined a strip it should read), **A-ctl** (lost the expiry at full phone resolution) |
| Passed but shouldn't have | **C4** — handwriting was read, on an image too easy to be the test |
| Not run | A1, A4, B1-200, B2, B3, B5, B6 (book/card), D2 |
| Waiting on a listener | E2, E3, and the audio half of every row above |

**One new defect, and it was found by the fix for an old one.** `DEC-076`: IndicTrans2
renders spelled-out numbers faithfully only about two times in three, so `₹84.21` was being
announced as **twenty-four rupees**. `DEC-072`'s control — no digits in the spoken answer —
was asserted on the *English*, upstream of the translator, and stayed green throughout.
Delivery now verifies that a translated number still says what the English said, and drops
the sentence when it does not.

**Three things this sheet got right, worth keeping for whatever replaces it.** The pass
conditions were fixed in advance, so A3's decline could be scored a failure rather than
talked into a pass. C4's row said what *should* happen, which is why an unexpected success
registered as a warning instead of a win. And the framing "judge by what you HEAR" is what
makes the PARTIAL rows honest — without it the machine-checked results would read as a
green sheet.

**E1 closed the same day.** The browser app was driven end to end with aeroplane mode on and
answered without reaching for the network — the project's central claim, checked on the path
the demo actually uses rather than inferred from a unit test over the rendered HTML. That
test could only ever assert the page contains no external URLs; it could not see a model
phoning home, and now something has.

**The largest remaining gap is that nobody has listened.** Every defect found on 08-22 was
found by ear, and the 08-24 session was graded by machine. `dropped_characters` proves which
characters a voice discards and proves nothing about whether the result is intelligible.
Until someone plays the wavs, this page records that the *text* is right — which is the exact
belief that let ₹500 be announced as "00" for twelve days.
