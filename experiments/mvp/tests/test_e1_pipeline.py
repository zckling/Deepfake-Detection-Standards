import json
import sys
import tempfile
import unittest
from pathlib import Path


MVP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP_ROOT))

from tools.d0_smoke import build_d0_smoke_samples  # noqa: E402
from tools.run_e1 import execute_synthetic_preflight, write_preflight_artifacts  # noqa: E402
from tools.schema_validation import validate_record  # noqa: E402
from tools.sut_adapter import SyntheticAdapter  # noqa: E402


SCHEMA_ROOT = MVP_ROOT / "schemas"
ROUTE_PATH = MVP_ROOT / "config" / "metric-routing.json"


class D0SmokeFixtureTests(unittest.TestCase):
    def test_fixture_is_balanced_schema_valid_and_covers_frozen_taxonomy(self):
        samples = build_d0_smoke_samples()
        self.assertEqual(12, len(samples))
        self.assertEqual(6, sum(item["label_state"] == "REAL" for item in samples))
        self.assertEqual(6, sum(item["label_state"] == "FAKE" for item in samples))
        self.assertEqual({"D0"}, {item["partition"] for item in samples})
        self.assertEqual(
            {"M1", "M2", "M3", "M4", "M5"},
            {value for item in samples for value in item["fake_modalities"]},
        )
        self.assertEqual(
            {"O1", "O2", "O3", "O4"},
            {value for item in samples for value in item["fake_objects"]},
        )
        schema = SCHEMA_ROOT / "sample-manifest.schema.json"
        for record in samples:
            with self.subTest(sample_id=record["sample_id"]):
                self.assertEqual([], validate_record(schema, record))


class SyntheticAdapterTests(unittest.TestCase):
    def test_adapter_registration_and_predictions_conform_to_schemas(self):
        samples = build_d0_smoke_samples()
        adapter = SyntheticAdapter("perfect")
        registration = adapter.registration()
        self.assertEqual("synthetic_baseline", registration["system_type"])
        self.assertTrue(adapter.synthetic_only)
        self.assertEqual(
            [],
            validate_record(SCHEMA_ROOT / "system-registry.schema.json", registration),
        )
        predictions = adapter.predict_many(samples, run_id="RUN-E1-SYN-PERFECT-001")
        self.assertEqual(len(samples), len(predictions))
        for prediction in predictions:
            self.assertEqual(
                [],
                validate_record(SCHEMA_ROOT / "prediction.schema.json", prediction),
            )

    def test_missing_output_strategy_exercises_failure_contract(self):
        prediction = SyntheticAdapter("missing_output").predict_many(
            build_d0_smoke_samples()[:1],
            run_id="RUN-E1-SYN-MISSING-001",
        )[0]
        self.assertEqual("missing_output", prediction["status"])
        self.assertIsNone(prediction["fake_score"])
        self.assertEqual("SYNTHETIC_MISSING_OUTPUT", prediction["error_code"])
        self.assertEqual(
            [],
            validate_record(SCHEMA_ROOT / "prediction.schema.json", prediction),
        )


class E1SyntheticPreflightTests(unittest.TestCase):
    def test_metrics_join_predictions_by_sample_id_not_output_order(self):
        class ReverseAdapter(SyntheticAdapter):
            def predict_many(self, samples, *, run_id):
                return list(reversed(super().predict_many(samples, run_id=run_id)))

        report = execute_synthetic_preflight(
            build_d0_smoke_samples(), [ReverseAdapter("perfect")], route_path=ROUTE_PATH
        )
        self.assertEqual(1.0, report["metrics"]["SUT-SYN-PERFECT"]["C-1"])
    def test_preflight_runs_two_adapters_without_masquerading_as_formal_evaluation(self):
        report = execute_synthetic_preflight(
            build_d0_smoke_samples(),
            [SyntheticAdapter("perfect"), SyntheticAdapter("inverse")],
            route_path=ROUTE_PATH,
        )
        self.assertFalse(report["formal_evaluation"])
        self.assertEqual("synthetic_preflight", report["result_class"])
        self.assertEqual(12, report["dataset"]["sample_count"])
        self.assertEqual([], report["relationship_errors"])
        self.assertEqual(1.0, report["metrics"]["SUT-SYN-PERFECT"]["C-1"])
        self.assertEqual(0.0, report["metrics"]["SUT-SYN-INVERSE"]["C-1"])
        self.assertGreater(report["metrics"]["SUT-SYN-PERFECT"]["D-1"], 0)
        self.assertEqual(14, len(report["metric_results"]))
        for record in report["metric_results"]:
            self.assertEqual(
                [],
                validate_record(SCHEMA_ROOT / "metric-result.schema.json", record),
            )
        self.assertEqual(78, len(report["computability_matrix"]))
        self.assertEqual(
            {"RUN-E1-SYN-PERFECT-001", "RUN-E1-SYN-INVERSE-001"},
            {run["run_id"] for run in report["runs"]},
        )

    def test_writer_emits_replayable_json_jsonl_and_csv_artifacts(self):
        report = execute_synthetic_preflight(
            build_d0_smoke_samples(),
            [SyntheticAdapter("perfect"), SyntheticAdapter("inverse")],
            route_path=ROUTE_PATH,
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = write_preflight_artifacts(report, Path(tmp_dir))
            self.assertEqual(
                {
                    "report_json",
                    "report_markdown",
                    "sample_manifest",
                    "system_registry",
                    "predictions",
                    "metric_results",
                    "computability_csv",
                },
                set(outputs),
            )
            for path in outputs.values():
                self.assertTrue(path.exists(), path)
            manifest_records = [
                json.loads(line)
                for line in outputs["sample_manifest"].read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(12, len(manifest_records))
            self.assertIn("synthetic_preflight", outputs["report_markdown"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
