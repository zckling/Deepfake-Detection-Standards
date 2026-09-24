import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


MVP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP_ROOT))

from tools.repeatability import compare_prediction_runs, write_repeatability_report  # noqa: E402


def prediction(sample_id, run_id, *, score=0.2, status="ok", elapsed=0.01):
    return {
        "sample_id": sample_id,
        "system_id": "SUT-REAL-CANDIDATE",
        "system_version": "1.0.0",
        "run_id": run_id,
        "is_fake_pred": score >= 0.5 if status == "ok" else None,
        "fake_score": score if status == "ok" else None,
        "processing_time_sec": elapsed,
        "status": status,
        "error_code": None if status == "ok" else "EXAMPLE_ERROR",
        "schema_version": "1.0.0",
    }


class RepeatabilityTests(unittest.TestCase):
    def test_rejects_non_finite_scores(self):
        first = [prediction("DFSTD-I-000001", "RUN-1", score=math.nan)]
        second = [prediction("DFSTD-I-000001", "RUN-2", score=0.9)]
        with self.assertRaisesRegex(ValueError, "non-finite"):
            compare_prediction_runs(first, second)
    def test_identical_semantics_ignore_run_id_order_and_elapsed_time(self):
        first = [
            prediction("DFSTD-I-000001", "RUN-1", score=0.1, elapsed=0.01),
            prediction("DFSTD-I-000002", "RUN-1", score=0.9, elapsed=0.02),
        ]
        second = [
            prediction("DFSTD-I-000002", "RUN-2", score=0.9, elapsed=0.04),
            prediction("DFSTD-I-000001", "RUN-2", score=0.1, elapsed=0.03),
        ]
        report = compare_prediction_runs(first, second, score_tolerance=0.0)
        self.assertTrue(report["semantically_deterministic"])
        self.assertEqual(2, report["summary"]["compared"])
        self.assertEqual(2, report["summary"]["semantic_matches"])
        self.assertEqual(0, report["summary"]["score_mismatches"])
        self.assertEqual(0.015, report["latency"]["first_mean_sec"])
        self.assertEqual(0.035, report["latency"]["second_mean_sec"])
        self.assertNotEqual(report["first_semantic_sha256"], "")
        self.assertEqual(report["first_semantic_sha256"], report["second_semantic_sha256"])

    def test_reports_score_status_and_missing_record_differences(self):
        first = [
            prediction("DFSTD-I-000001", "RUN-1", score=0.1),
            prediction("DFSTD-I-000002", "RUN-1", score=0.9),
            prediction("DFSTD-I-000003", "RUN-1", score=0.2),
        ]
        second = [
            prediction("DFSTD-I-000001", "RUN-2", score=0.3),
            prediction("DFSTD-I-000002", "RUN-2", status="runtime_error"),
            prediction("DFSTD-I-000004", "RUN-2", score=0.8),
        ]
        report = compare_prediction_runs(first, second, score_tolerance=0.05)
        self.assertFalse(report["semantically_deterministic"])
        self.assertEqual(1, report["summary"]["score_mismatches"])
        self.assertEqual(1, report["summary"]["status_mismatches"])
        self.assertEqual(["DFSTD-I-000003"], report["missing_from_second"])
        self.assertEqual(["DFSTD-I-000004"], report["missing_from_first"])

    def test_rejects_duplicate_sample_ids_within_a_run(self):
        duplicate = [
            prediction("DFSTD-I-000001", "RUN-1"),
            prediction("DFSTD-I-000001", "RUN-1"),
        ]
        with self.assertRaises(ValueError):
            compare_prediction_runs(duplicate, [], score_tolerance=0.0)

    def test_writer_round_trips_json(self):
        report = compare_prediction_runs(
            [prediction("DFSTD-I-000001", "RUN-1")],
            [prediction("DFSTD-I-000001", "RUN-2")],
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "repeatability.json"
            write_repeatability_report(report, path)
            loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(report, loaded)


if __name__ == "__main__":
    unittest.main()
