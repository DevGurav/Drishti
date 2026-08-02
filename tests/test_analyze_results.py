import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from eval.analyze_results import (
    abstention_stats,
    accuracy_by_answer_length,
    load_rows,
    missed_unanswerable,
    summarize,
    verbose_predictions,
)

FIELDNAMES = ["question", "prediction", "latency_s", "acc", "unanswerable_gt", "gt_sample"]

ROWS = [
    {"question": "what is this", "prediction": "a cup", "latency_s": "1.2",
     "acc": "1.0", "unanswerable_gt": "False", "gt_sample": "cup; cup; a cup"},
    {"question": "blurry photo what color", "prediction": "red", "latency_s": "2.5",
     "acc": "0.0", "unanswerable_gt": "True",
     "gt_sample": "unanswerable; unanswerable; unanswerable"},
    {"question": "read the label", "prediction": "paracetamol 500 mg tablet",
     "latency_s": "3.1", "acc": "0.33", "unanswerable_gt": "False",
     "gt_sample": "paracetamol; medicine; tablet"},
]


class TestAnalyzeResults(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.csv_path = Path(self._tmp.name) / "results.csv"
        with self.csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(ROWS)

    def test_load_rows_roundtrip(self):
        rows = load_rows(self.csv_path)
        self.assertEqual(len(rows), 3)

    def test_summarize_overall_accuracy(self):
        rows = load_rows(self.csv_path)
        summary = summarize(rows)
        self.assertEqual(summary["n"], 3)
        self.assertAlmostEqual(summary["overall_acc"], (1.0 + 0.0 + 0.33) / 3, places=4)

    def test_summarize_splits_answerable_and_unanswerable(self):
        rows = load_rows(self.csv_path)
        summary = summarize(rows)
        self.assertAlmostEqual(summary["unanswerable_acc"], 0.0)
        self.assertAlmostEqual(summary["answerable_acc"], (1.0 + 0.33) / 2, places=4)

    def test_missed_unanswerable_flags_the_guessed_row(self):
        rows = load_rows(self.csv_path)
        missed = missed_unanswerable(rows)
        self.assertEqual(len(missed), 1)
        self.assertEqual(missed[0]["question"], "blurry photo what color")

    def test_accuracy_by_answer_length_buckets_nonempty(self):
        rows = load_rows(self.csv_path)
        buckets = accuracy_by_answer_length(rows, bucket_size=2)
        self.assertGreaterEqual(len(buckets), 1)


class TestAbstentionStats(unittest.TestCase):
    """Baseline measured precision 0.913 / recall 0.258 — the model's judgement about
    unanswerability is sound but its threshold is far too conservative."""

    def _rows(self, specs):
        # specs: (prediction, unanswerable_gt)
        return [{"question": "q", "prediction": p, "latency_s": "1.0", "acc": "0.0",
                 "unanswerable_gt": gt, "gt_sample": "x"} for p, gt in specs]

    def test_perfect_abstention(self):
        s = abstention_stats(self._rows([("unanswerable", "True"), ("cup", "False")]))
        self.assertEqual(s["precision"], 1.0)
        self.assertEqual(s["recall"], 1.0)
        self.assertEqual(s["missed"], 0)

    def test_high_precision_low_recall_is_distinguishable(self):
        # abstains once, correctly; misses two other unanswerable questions
        s = abstention_stats(self._rows([
            ("unanswerable", "True"), ("red", "True"), ("blue", "True"),
        ]))
        self.assertEqual(s["precision"], 1.0)
        self.assertAlmostEqual(s["recall"], 1 / 3)
        self.assertEqual(s["missed"], 2)

    def test_degenerate_abstain_on_everything_shows_low_precision(self):
        """Guards the failure mode a single accuracy number would hide."""
        s = abstention_stats(self._rows([
            ("unanswerable", "True"), ("unanswerable", "False"), ("unanswerable", "False"),
        ]))
        self.assertAlmostEqual(s["precision"], 1 / 3)
        self.assertEqual(s["recall"], 1.0)

    def test_normalization_handles_punctuation_and_case(self):
        s = abstention_stats(self._rows([("Unanswerable.", "True")]))
        self.assertEqual(s["recall"], 1.0)

    def test_never_abstains_gives_none_precision(self):
        s = abstention_stats(self._rows([("cup", "True")]))
        self.assertIsNone(s["precision"])
        self.assertEqual(s["recall"], 0.0)


class TestVerbosePredictions(unittest.TestCase):
    def test_flags_only_long_predictions(self):
        rows = [{"prediction": "a b c d e f", "acc": "0.0"},
                {"prediction": "cup", "acc": "1.0"}]
        self.assertEqual(len(verbose_predictions(rows)), 1)


if __name__ == "__main__":
    unittest.main()
