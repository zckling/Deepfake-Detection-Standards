import math
import sys
import unittest
from pathlib import Path


MVP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP_ROOT))

from tools.metrics import (  # noqa: E402
    bbox_iou,
    binary_metrics,
    latency_summary,
    prediction_latency_metrics,
    realtime_rate,
    temporal_iou,
    throughput_metrics,
)


class BinaryMetricTests(unittest.TestCase):
    def test_perfect_predictions_reach_expected_bounds(self):
        result = binary_metrics([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9], threshold=0.5)
        self.assertEqual({"tp": 2, "tn": 2, "fp": 0, "fn": 0}, result["confusion"])
        for name in ("accuracy", "precision", "recall", "specificity", "f1", "balanced_accuracy", "roc_auc"):
            self.assertEqual(1.0, result[name], name)
        self.assertEqual(0.0, result["eer"])

    def test_inverse_predictions_reach_opposite_bounds(self):
        result = binary_metrics([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1], threshold=0.5)
        self.assertEqual({"tp": 0, "tn": 0, "fp": 2, "fn": 2}, result["confusion"])
        self.assertEqual(0.0, result["accuracy"])
        self.assertEqual(0.0, result["roc_auc"])
        self.assertEqual(1.0, result["eer"])

    def test_constant_scores_handle_ties_and_threshold(self):
        result = binary_metrics([0, 0, 1, 1], [0.5, 0.5, 0.5, 0.5], threshold=0.5)
        self.assertEqual({"tp": 2, "tn": 0, "fp": 2, "fn": 0}, result["confusion"])
        self.assertEqual(0.5, result["accuracy"])
        self.assertEqual(0.5, result["precision"])
        self.assertEqual(1.0, result["recall"])
        self.assertEqual(0.0, result["specificity"])
        self.assertTrue(math.isclose(2 / 3, result["f1"]))
        self.assertEqual(0.5, result["balanced_accuracy"])
        self.assertEqual(0.5, result["roc_auc"])
        self.assertEqual(0.5, result["eer"])

    def test_single_class_truth_marks_auc_eer_and_missing_denominators_undefined(self):
        result = binary_metrics([0, 0], [0.1, 0.2], threshold=0.5)
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["recall"])
        self.assertEqual(1.0, result["specificity"])
        self.assertIsNone(result["balanced_accuracy"])
        self.assertIsNone(result["roc_auc"])
        self.assertIsNone(result["eer"])

    def test_rejects_mismatched_or_invalid_binary_inputs(self):
        with self.assertRaises(ValueError):
            binary_metrics([0, 1], [0.2], threshold=0.5)
        with self.assertRaises(ValueError):
            binary_metrics([0, 2], [0.2, 0.8], threshold=0.5)
        with self.assertRaises(ValueError):
            binary_metrics([], [], threshold=0.5)


class LocalizationMetricTests(unittest.TestCase):
    def test_temporal_iou_boundaries(self):
        self.assertEqual(1.0, temporal_iou((1.0, 3.0), (1.0, 3.0)))
        self.assertTrue(math.isclose(1 / 3, temporal_iou((0.0, 2.0), (1.0, 3.0))))
        self.assertEqual(0.0, temporal_iou((0.0, 1.0), (1.0, 2.0)))
        with self.assertRaises(ValueError):
            temporal_iou((1.0, 1.0), (0.0, 1.0))

    def test_bbox_iou_boundaries(self):
        self.assertEqual(1.0, bbox_iou((0.0, 0.0, 2.0, 2.0), (0.0, 0.0, 2.0, 2.0)))
        self.assertTrue(math.isclose(1 / 7, bbox_iou((0.0, 0.0, 2.0, 2.0), (1.0, 1.0, 3.0, 3.0))))
        self.assertEqual(0.0, bbox_iou((0.0, 0.0, 1.0, 1.0), (2.0, 2.0, 3.0, 3.0)))
        with self.assertRaises(ValueError):
            bbox_iou((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 1.0, 1.0))


class PerformanceMetricTests(unittest.TestCase):
    def test_latency_summary_uses_mean_and_linear_percentiles(self):
        result = latency_summary([0.1, 0.2, 0.4])
        self.assertTrue(math.isclose(0.7 / 3, result["mean_sec"]))
        self.assertEqual(0.2, result["median_sec"])
        self.assertTrue(math.isclose(0.38, result["p95_sec"]))
        self.assertTrue(math.isclose(0.7, result["sum_sec"]))
        self.assertEqual(3, result["count"])

    def test_latency_summary_rejects_empty_negative_or_nonfinite_values(self):
        for values in ([], [-0.1], [math.nan], [math.inf]):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    latency_summary(values)

    def test_prediction_latency_uses_registered_cap_for_timeouts_and_reports_failures(self):
        result = prediction_latency_metrics(
            [
                {"status": "ok", "processing_time_sec": 0.1},
                {"status": "timeout", "processing_time_sec": None},
                {"status": "runtime_error", "processing_time_sec": 0.05},
            ],
            timeout_cap_sec=1.0,
        )
        self.assertTrue(math.isclose(1.15 / 3, result["mean_sec"]))
        self.assertTrue(math.isclose(0.91, result["p95_sec"]))
        self.assertEqual(3, result["included_count"])
        self.assertEqual(1, result["timeout_count"])
        self.assertEqual(1, result["failure_count"])
        self.assertTrue(math.isclose(1 / 3, result["timeout_rate"]))

    def test_prediction_latency_rejects_missing_ok_duration_or_invalid_timeout_cap(self):
        with self.assertRaises(ValueError):
            prediction_latency_metrics(
                [{"status": "ok", "processing_time_sec": None}],
                timeout_cap_sec=1.0,
            )
        with self.assertRaises(ValueError):
            prediction_latency_metrics([], timeout_cap_sec=0.0)

    def test_realtime_rate_includes_failed_attempt_time_and_timeout_cap(self):
        result = realtime_rate(
            [4.0, 6.0, 5.0],
            [
                {"status": "ok", "processing_time_sec": 2.0},
                {"status": "runtime_error", "processing_time_sec": 1.0},
                {"status": "timeout", "processing_time_sec": None},
            ],
            timeout_cap_sec=5.0,
        )
        self.assertEqual(15.0, result["media_duration_sec"])
        self.assertEqual(8.0, result["processing_time_sec"])
        self.assertEqual(1.875, result["realtime_rate"])
        self.assertTrue(math.isclose(1 / 3, result["success_rate"]))
        self.assertTrue(math.isclose(2 / 3, result["failure_rate"]))

    def test_realtime_rate_rejects_mismatches_and_nonpositive_totals(self):
        with self.assertRaises(ValueError):
            realtime_rate([1.0], [], timeout_cap_sec=2.0)
        with self.assertRaises(ValueError):
            realtime_rate([0.0], [{"status": "ok", "processing_time_sec": 1.0}], timeout_cap_sec=2.0)
        with self.assertRaises(ValueError):
            realtime_rate(
                [1.0],
                [{"status": "runtime_error", "processing_time_sec": None}],
                timeout_cap_sec=2.0,
            )

    def test_throughput_reports_success_only_rates_and_failure_fraction(self):
        result = throughput_metrics(
            [4.0, 6.0, 5.0],
            [
                {"status": "ok"},
                {"status": "runtime_error"},
                {"status": "ok"},
            ],
            wall_clock_sec=10.0,
        )
        self.assertEqual(720.0, result["successful_items_per_hour"])
        self.assertEqual(0.9, result["successful_media_hours_per_hour"])
        self.assertEqual(2, result["success_count"])
        self.assertEqual(1, result["failure_count"])
        self.assertTrue(math.isclose(1 / 3, result["failure_rate"]))

    def test_throughput_rejects_invalid_wall_clock_or_unaligned_records(self):
        with self.assertRaises(ValueError):
            throughput_metrics([1.0], [], wall_clock_sec=1.0)
        with self.assertRaises(ValueError):
            throughput_metrics([], [], wall_clock_sec=0.0)


if __name__ == "__main__":
    unittest.main()
