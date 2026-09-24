import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


MVP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP_ROOT))

from tools.schema_validation import validate_jsonl, validate_record  # noqa: E402


SCHEMA_ROOT = MVP_ROOT / "schemas"
EXAMPLE_ROOT = MVP_ROOT / "fixtures" / "schema-examples"


class SchemaInventoryTests(unittest.TestCase):
    def test_all_seven_schemas_are_valid_draft_2020_12(self):
        from jsonschema import Draft202012Validator

        expected = {
            "sample-manifest.schema.json",
            "annotation.schema.json",
            "system-registry.schema.json",
            "prediction.schema.json",
            "run-manifest.schema.json",
            "metric-result.schema.json",
            "exclusion.schema.json",
        }
        actual = {path.name for path in SCHEMA_ROOT.glob("*.schema.json")}
        self.assertEqual(expected, actual)
        for path in sorted(SCHEMA_ROOT.glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                "https://json-schema.org/draft/2020-12/schema",
                schema["$schema"],
            )
            Draft202012Validator.check_schema(schema)

    def test_each_schema_has_a_valid_example_record(self):
        schema_paths = sorted(SCHEMA_ROOT.glob("*.schema.json"))
        example_paths = sorted(EXAMPLE_ROOT.glob("*.json"))
        self.assertEqual(len(schema_paths), len(example_paths))
        for schema_path in schema_paths:
            example_path = EXAMPLE_ROOT / schema_path.name.replace(".schema.json", ".example.json")
            self.assertTrue(example_path.exists(), example_path)
            record = json.loads(example_path.read_text(encoding="utf-8"))
            self.assertEqual([], validate_record(schema_path, record), example_path.name)


class RecordValidationTests(unittest.TestCase):
    def test_rejects_non_finite_numbers_in_memory_and_jsonl(self):
        record = {
            "sample_id": "DFSTD-V-000001", "system_id": "SUT-V1",
            "system_version": "1.0.0", "run_id": "RUN-E1-V1-001",
            "is_fake_pred": True, "fake_score": math.nan,
            "processing_time_sec": 0.1, "status": "ok", "error_code": None,
            "schema_version": "1.0.0",
        }
        self.assertTrue(any("non-finite" in item for item in validate_record(
            SCHEMA_ROOT / "prediction.schema.json", record
        )))
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "predictions.jsonl"
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            summary = validate_jsonl(SCHEMA_ROOT / "prediction.schema.json", path)
        self.assertEqual(1, summary.invalid)
    def test_accepts_minimal_valid_sample_manifest(self):
        record = {
            "sample_id": "DFSTD-V-000001",
            "group_id": "GRP-000001",
            "parent_sample_id": None,
            "source_id": "SRC-CTL-000001",
            "file_path": "media/real/DFSTD-V-000001.mp4",
            "sha256": "a" * 64,
            "source_type": "SRC-CTL",
            "media_type": "video",
            "label_state": "REAL",
            "fake_modalities": [],
            "fake_objects": [],
            "duration_sec": 3.2,
            "partition": "D0",
            "license_status": "standard_internal",
            "access_class": "internal",
            "annotation_version": "1.0.0",
            "review_status": "adjudicated",
            "exclusion_status": "included",
            "exclusion_reason": None,
            "schema_version": "1.0.0",
        }
        self.assertEqual([], validate_record(SCHEMA_ROOT / "sample-manifest.schema.json", record))

    def test_rejects_fake_sample_without_fake_modalities(self):
        record = {
            "sample_id": "DFSTD-V-000002",
            "group_id": "GRP-000002",
            "parent_sample_id": None,
            "source_id": "SRC-GEN-000001",
            "file_path": "media/fake/DFSTD-V-000002.mp4",
            "sha256": "b" * 64,
            "source_type": "SRC-GEN",
            "media_type": "video",
            "label_state": "FAKE",
            "fake_modalities": [],
            "fake_objects": ["O1"],
            "method_family": "identity_replacement",
            "scope_id": "face.full.segment",
            "granularity": "object",
            "duration_sec": 4.0,
            "partition": "D0",
            "license_status": "standard_internal",
            "access_class": "internal",
            "annotation_version": "1.0.0",
            "review_status": "adjudicated",
            "exclusion_status": "included",
            "exclusion_reason": None,
            "schema_version": "1.0.0",
        }
        errors = validate_record(SCHEMA_ROOT / "sample-manifest.schema.json", record)
        self.assertTrue(any("fake_modalities" in error for error in errors), errors)

    def test_rejects_prediction_score_outside_zero_one(self):
        record = {
            "sample_id": "DFSTD-V-000001",
            "system_id": "SUT-V1",
            "system_version": "1.0.0",
            "run_id": "RUN-E1-V1-001",
            "is_fake_pred": True,
            "fake_score": 1.2,
            "processing_time_sec": 0.1,
            "status": "ok",
            "error_code": None,
            "schema_version": "1.0.0",
        }
        errors = validate_record(SCHEMA_ROOT / "prediction.schema.json", record)
        self.assertTrue(any("fake_score" in error for error in errors), errors)

    def test_jsonl_summary_counts_valid_invalid_and_parse_errors(self):
        valid = {
            "sample_id": "DFSTD-V-000001",
            "system_id": "SUT-V1",
            "system_version": "1.0.0",
            "run_id": "RUN-E1-V1-001",
            "is_fake_pred": False,
            "fake_score": 0.2,
            "processing_time_sec": 0.1,
            "status": "ok",
            "error_code": None,
            "schema_version": "1.0.0",
        }
        invalid = dict(valid, fake_score=-0.1)
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "predictions.jsonl"
            path.write_text(
                json.dumps(valid) + "\n" + json.dumps(invalid) + "\n" + "{bad json}\n",
                encoding="utf-8",
            )
            summary = validate_jsonl(SCHEMA_ROOT / "prediction.schema.json", path)
        self.assertEqual(3, summary.total)
        self.assertEqual(1, summary.valid)
        self.assertEqual(2, summary.invalid)
        self.assertEqual(2, len(summary.errors))

    def test_rejects_invalid_date_time_format(self):
        record = {
            "exclusion_id": "EXC-000001",
            "sample_id": "DFSTD-V-000001",
            "stage": "analysis",
            "reason_code": "technical",
            "reason_detail": "Example",
            "requested_by": "analyst-a",
            "reviewed_by": "reviewer-b",
            "decision": "retained",
            "decided_at": "not-a-date",
            "schema_version": "1.0.0",
        }
        errors = validate_record(SCHEMA_ROOT / "exclusion.schema.json", record)
        self.assertTrue(any("decided_at" in error for error in errors), errors)

    def test_accepts_run_with_preregistered_performance_context(self):
        record = {
            "run_id": "RUN-E1-PERF-001",
            "experiment_id": "E1",
            "dataset_version": "D0-SMOKE-REAL-0.1.0",
            "system_id": "SUT-REAL-CANDIDATE",
            "system_version": "1.0.0",
            "config_sha256": "1" * 64,
            "environment_sha256": "2" * 64,
            "started_at": "2026-09-23T01:00:00Z",
            "finished_at": "2026-09-23T01:00:10Z",
            "status": "completed",
            "wall_clock_sec": 10.0,
            "batch_size": 1,
            "concurrency": 1,
            "queue_time_sec": 0.0,
            "timeout_cap_sec": 5.0,
            "timing_scope": "decode+preprocess+inference+postprocess",
            "schema_version": "1.0.0",
        }
        self.assertEqual([], validate_record(SCHEMA_ROOT / "run-manifest.schema.json", record))


if __name__ == "__main__":
    unittest.main()
