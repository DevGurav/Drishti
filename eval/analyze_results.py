"""Analyze notebooks/01_vizwiz_baseline.ipynb output
(eval/results/vizwiz_baseline_results.csv).

Adds breakdowns the notebook itself doesn't print: latency percentiles, accuracy vs
answer length (VizWiz's exact-match metric punishes verbose answers -- this makes
that visible), and the "missed unanswerable" failure mode isolated from plain wrong
answers. Pure stdlib, so it runs without installing anything.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import string
from pathlib import Path

DEFAULT_CSV = Path(__file__).resolve().parent / "results" / "vizwiz_baseline_results.csv"

_ARTICLES = {"a", "an", "the"}


def load_rows(csv_path: Path) -> list[dict]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def norm(text: str) -> str:
    """VQA-style answer normalization. Must match the scoring in
    notebooks/01_vizwiz_baseline.ipynb, otherwise metrics computed here and there
    silently disagree."""
    text = text.lower().strip().translate(str.maketrans("", "", string.punctuation))
    return " ".join(w for w in text.split() if w not in _ARTICLES)


def _is_true(value: str | None) -> bool:
    return str(value).strip().lower() == "true"


def _percentile(sorted_values: list[float], p: float) -> float:
    idx = min(int(len(sorted_values) * p), len(sorted_values) - 1)
    return sorted_values[idx]


def summarize(rows: list[dict]) -> dict:
    accs = [float(r["acc"]) for r in rows]
    latencies = sorted(float(r["latency_s"]) for r in rows)
    answerable = [r for r in rows if not _is_true(r.get("unanswerable_gt"))]
    unanswerable = [r for r in rows if _is_true(r.get("unanswerable_gt"))]

    return {
        "n": len(rows),
        "overall_acc": statistics.mean(accs),
        "answerable_acc": statistics.mean(float(r["acc"]) for r in answerable) if answerable else None,
        "unanswerable_acc": statistics.mean(float(r["acc"]) for r in unanswerable) if unanswerable else None,
        "latency_p50": _percentile(latencies, 0.50),
        "latency_p90": _percentile(latencies, 0.90),
        "latency_p99": _percentile(latencies, 0.99),
    }


def accuracy_by_answer_length(rows: list[dict], bucket_size: int = 2) -> dict[str, float]:
    """Bucket by predicted-answer word count -> mean accuracy."""
    buckets: dict[int, list[float]] = {}
    for r in rows:
        n_words = len(r["prediction"].split())
        bucket = (n_words // bucket_size) * bucket_size
        buckets.setdefault(bucket, []).append(float(r["acc"]))
    return {
        f"{b}-{b + bucket_size - 1} words": statistics.mean(v)
        for b, v in sorted(buckets.items())
    }


def missed_unanswerable(rows: list[dict], limit: int = 10) -> list[dict]:
    """Ground truth said 'unanswerable' but the model guessed anyway -- a distinct
    failure mode from getting an answerable question wrong."""
    matches = [
        r for r in rows
        if _is_true(r.get("unanswerable_gt")) and float(r["acc"]) == 0.0
    ]
    return matches[:limit]


def abstention_stats(rows: list[dict]) -> dict:
    """Precision/recall for saying 'unanswerable'.

    This is the headline Phase-3 metric. Aggregate accuracy hides the distinction that
    matters: a model can look identical whether it abstains too rarely (guesses at blurry
    photos -- unsafe for a blind user) or too often (useless). Splitting precision from
    recall makes the failure mode explicit, and rules out the degenerate "abstain on
    everything" model that would otherwise score well on the unanswerable subset.
    """
    said = [r for r in rows if norm(r["prediction"]) == "unanswerable"]
    gt = [r for r in rows if _is_true(r.get("unanswerable_gt"))]
    hits = [r for r in said if _is_true(r.get("unanswerable_gt"))]

    return {
        "gt_unanswerable": len(gt),
        "predicted_unanswerable": len(said),
        "precision": len(hits) / len(said) if said else None,
        "recall": len(hits) / len(gt) if gt else None,
        "missed": len(gt) - len(hits),
    }


def verbose_predictions(rows: list[dict], min_words: int = 6) -> list[dict]:
    """Predictions long enough that VizWiz exact-match scores them ~0 regardless of
    correctness. Tracked to keep the terseness claim honest -- at baseline this was only
    1.8% of samples, so it is a real but minor effect, not the main lever."""
    return [r for r in rows if len(r["prediction"].split()) >= min_words]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    if not args.csv.exists():
        raise SystemExit(
            f"{args.csv} not found -- run notebooks/01_vizwiz_baseline.ipynb, download "
            f"vizwiz_baseline_results.csv, and place it there first."
        )

    rows = load_rows(args.csv)
    s = summarize(rows)

    print(f"n={s['n']}")
    print(f"overall accuracy      : {s['overall_acc']:.3f}")
    if s["answerable_acc"] is not None:
        print(f"answerable accuracy   : {s['answerable_acc']:.3f}")
    if s["unanswerable_acc"] is not None:
        print(f"unanswerable accuracy : {s['unanswerable_acc']:.3f}")
    print(
        f"latency p50/p90/p99   : "
        f"{s['latency_p50']:.2f}s / {s['latency_p90']:.2f}s / {s['latency_p99']:.2f}s"
    )

    print("\naccuracy by answer length:")
    for bucket, acc in accuracy_by_answer_length(rows).items():
        print(f"  {bucket:16s} {acc:.3f}")

    verbose = verbose_predictions(rows)
    print(f"  (>=6 words: {len(verbose)}/{len(rows)} = {len(verbose)/len(rows):.1%}, all score ~0)")

    a = abstention_stats(rows)
    print("\nabstention ('unanswerable') — the Phase-3 target:")
    print(f"  ground truth unanswerable : {a['gt_unanswerable']}/{len(rows)}")
    print(f"  model said 'unanswerable' : {a['predicted_unanswerable']}/{len(rows)}")
    if a["precision"] is not None:
        print(f"  precision                 : {a['precision']:.3f}  (when it abstains, is it right?)")
    if a["recall"] is not None:
        print(f"  recall                    : {a['recall']:.3f}  (missed {a['missed']} of {a['gt_unanswerable']})")
    if a["precision"] and a["recall"] and a["precision"] - a["recall"] > 0.3:
        print("  -> High precision, low recall: the model's judgement is sound but its")
        print("     threshold is far too conservative. That is a CALIBRATION problem,")
        print("     not a missing capability — try prompting before fine-tuning.")

    missed = missed_unanswerable(rows)
    if missed:
        print(f"\n{len(missed)} sample cases where ground truth was 'unanswerable' "
              f"but the model guessed:")
        for r in missed[:5]:
            print(f"  Q: {r['question'][:60]}\n  A: {r['prediction']}\n")


if __name__ == "__main__":
    main()
