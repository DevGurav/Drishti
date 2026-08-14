# Demo runbook

The order below is deliberate and the reasons are measured. Follow it rather than
improvising — a live demo is the one situation where this project's slowest paths are
most likely to be the ones someone asks for.

---

## The day before

```powershell
# 1. Clean-install verification (RISK-6: upstream churn breaks a working pipeline)
.\setup.ps1
.\.venv\Scripts\python.exe -m unittest discover -s tests -q     # expect 186 tests, OK

# 2. Warm every model cache, so nothing downloads on the day
.\.venv\Scripts\python.exe -m app.cli --mode currency --image data\samples\curr-500.jpg
.\.venv\Scripts\python.exe -m app.cli --mode medicine --image data\samples\strip_paracip.jpg --lang mr --speak
.\.venv\Scripts\python.exe -m app.cli --mode read --image data\samples\newspaper-marathi.png --ocr-lang mr --lang mr --speak
.\.venv\Scripts\python.exe -m app.cli --mode scene --image data\samples\curr-500.jpg
```

**Confirm `models/currency_mobilenetv3.pt` exists.** It is gitignored, so a fresh clone does
not have it, and money mode is the demo's strongest moment.

## Thirty minutes before

- **Start from a cool machine.** Per-photo cost rose **55–120%** across four runs in one
  evening as the laptop heated (`DEC-066`). Close Colab tabs, close anything heavy, and do
  not run the benchmark first.
- **Turn on aeroplane mode and leave it on.** This is the claim. Do it *before* the demo
  starts so nobody wonders whether something was cached over the network mid-run.
- Have `data/samples/` open, and headphones or a speaker tested.

---

## Running order

Fastest and most convincing first. If time runs short you will have shown the strongest
material, and the slow modes are the ones with an honest explanation attached.

### 1. Money — the headline (~1–2s)

```powershell
.\.venv\Scripts\python.exe -m app.cli --mode currency --image data\samples\curr-500.jpg --lang mr --speak
```

**Then show the refusal**, which is the actual point:

```powershell
.\.venv\Scripts\python.exe -m app.cli --mode currency --image data\samples\curr-200.jpg --lang mr --speak
```

`curr-200` predicts `200` correctly at 0.784, below the 0.90 threshold, so it declines and
asks for a better photo. Say plainly why that is the *right* behaviour: a withheld answer
costs a retaken photo, a wrong denomination costs money, and the user cannot check
(`DEC-062`).

### 2. Medicine — the safety argument (~19–30s)

```powershell
.\.venv\Scripts\python.exe -m app.cli --mode medicine --image data\samples\strip_paracip.jpg --ocr-lang en --lang mr --speak
```

Reads the drug name, expiry and MRP, and speaks in Marathi. Two things to mention while it
runs: the drug name is spoken **only** on a verified database match, and a faster OCR tier
was rejected because it lost the expiry date — 6.3× quicker, and it would tell a blind user
an expired medicine is safe (`DEC-058`).

### 3. Read, Marathi — the hardest thing here (~76–83s)

```powershell
.\.venv\Scripts\python.exe -m app.cli --mode read --image data\samples\newspaper-marathi.png --ocr-lang mr --lang mr --speak
```

**Start it, then talk while it runs.** 1010 Devanagari characters off real newsprint. This
is the mode that needs a server-class detector, which is exactly why the Android port was
dropped rather than half-attempted (`DEC-064`).

### 4. Scene or ask — only if there is time (~3.5–4 minutes)

```powershell
.\.venv\Scripts\python.exe -m app.cli --mode ask --image data\samples\curr-500.jpg --question "what is in front of me?"
```

**Do not run this cold in front of an audience without saying the number first.** A 2B VLM
on a laptop CPU takes minutes. Frame it as the measurement that shows where a phone port
would need a different answer, not as a feature demonstration.

### Web UI alternative

```powershell
.\.venv\Scripts\python.exe -m app.web.server
# http://127.0.0.1:5000
```

Better for an audience than a terminal. Same engines, same latency.

---

## Questions you should expect

**"Is it really offline?"** — Aeroplane mode is already on. Every model is on disk;
`requirements.txt` pins them and `setup.ps1` fetches them once.

**"Why not just use Seeing AI?"** — It is good and this does not beat it. It sends scene
descriptions to a server and treats Marathi as a second-class output. The interesting
question here is what a system should do **when it is not sure** (§3 of the report).

**"Why is accuracy only 98.3%?"** — Because accuracy is the wrong metric, and the report
says so. Expected error is **₹2.48**, and **₹0.68** at the shipping threshold. Two models
with equal accuracy are not equally good if one confuses ₹10 with ₹20 and the other
confuses ₹100 with ₹500 (`DEC-022`).

**"Did the fine-tuning work?"** — It scored highest on the benchmark and **it does not
ship**. It refuses 129 of 256 answerable questions against 59 for a one-line prompt change
(`DEC-068`). That is the most interesting result in the project.

**"Why is it slow?"** — One mode of six meets the 8s target, and the measurement showed the
bottleneck is **translation, not OCR** — the opposite of what was assumed for months
(`DEC-066`).

## If something fails live

- **Model not found** → `models/currency_mobilenetv3.pt` is missing; fall back to medicine.
- **Devanagari returns nothing** → check `--ocr-lang mr` was passed. Without it the engine
  reads Devanagari with a Latin recogniser and returns transliterated nonsense (`DEC-045`).
- **No audio** → drop `--speak` and read the printed Marathi text aloud. The pipeline is the
  claim, not the speaker.
- **Anything hangs** → say what it is doing. Every latency figure in this project is
  measured and written down; being able to name the number is better than apologising for
  it.
