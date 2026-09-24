import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


MVP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP_ROOT))

from tools.sut_package_validation import common_prediction_fields, validate_candidate_package  # noqa: E402


SCHEMA_ROOT = MVP_ROOT / "schemas"
ROUTE_PATH = MVP_ROOT / "config" / "metric-routing.json"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path, records):
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


class SUTPackageValidationTests(unittest.TestCase):
    def build_package(self, root: Path, *, synthetic=False, wrong_hash=False, omit_prediction=False):
        media_dir = root / "media"
        media_dir.mkdir()
        media_path = media_dir / "sample.bin"
        media_path.write_bytes(b"real-media-placeholder-for-package-validation")
        digest = hashlib.sha256(media_path.read_bytes()).hexdigest()
        if wrong_hash:
            digest = "0" * 64

        system_id = "SUT-SYN-BLOCKED" if synthetic else "SUT-REAL-CANDIDATE"
        system = {
            "system_id": system_id,
            "name": "Candidate detector",
            "system_version": "1.0.0",
            "system_type": "synthetic_baseline" if synthetic else "model",
            "code_revision": "candidate-revision-001",
            "weights_sha256": hashlib.sha256(b"candidate-test-weights").hexdigest(),
            "capabilities": ["binary_classification"],
            "environment": {"runtime": "test"},
            "schema_version": "1.0.0",
        }
        run = {
            "run_id": "RUN-E1-REAL-001",
            "experiment_id": "E1",
            "dataset_version": "D0-SMOKE-REAL-0.1.0",
            "system_id": system_id,
            "system_version": "1.0.0",
            "config_sha256": "1" * 64,
            "environment_sha256": "2" * 64,
            "started_at": "2026-09-23T01:00:00Z",
            "finished_at": "2026-09-23T01:00:01Z",
            "status": "completed",
            "wall_clock_sec": 1.0,
            "batch_size": 1,
            "concurrency": 1,
            "queue_time_sec": 0.0,
            "timeout_cap_sec": 5.0,
            "timing_scope": "decode+preprocess+inference+postprocess",
            "schema_version": "1.0.0",
        }
        sample = {
            "sample_id": "DFSTD-I-000001",
            "group_id": "GRP-000001",
            "parent_sample_id": None,
            "source_id": "SRC-APPROVED-000001",
            "file_path": "media/sample.bin",
            "sha256": digest,
            "source_type": "SRC-CTL",
            "media_type": "image",
            "label_state": "REAL",
            "fake_modalities": [],
            "fake_objects": [],
            "duration_sec": None,
            "partition": "D0",
            "license_status": "approved_internal_controlled",
            "access_class": "internal",
            "annotation_version": "1.0.0",
            "review_status": "adjudicated",
            "exclusion_status": "included",
            "exclusion_reason": None,
            "schema_version": "1.0.0",
        }
        prediction = {
            "sample_id": sample["sample_id"],
            "system_id": system_id,
            "system_version": "1.0.0",
            "run_id": run["run_id"],
            "is_fake_pred": False,
            "fake_score": 0.1,
            "processing_time_sec": 0.01,
            "status": "ok",
            "error_code": None,
            "schema_version": "1.0.0",
        }
        evidence_dir = root / "license-evidence"
        evidence_dir.mkdir()
        license_text = evidence_dir / "license.txt"
        approval_record = evidence_dir / "approval-record.pdf"
        license_text.write_bytes(b"approved test license text")
        approval_record.write_bytes(b"approved test decision record")
        license_register = {
            "schema_version": "1.0.0",
            "register_status": "approved",
            "sources": [
                {
                    "source_id": sample["source_id"],
                    "review_status": "approved",
                    "download_status": "approved_for_download",
                    "reviewed_by": "authorized-reviewer",
                    "reviewed_at": "2026-09-23T00:30:00Z",
                    "license_text_path": "license-evidence/license.txt",
                    "license_text_sha256": hashlib.sha256(license_text.read_bytes()).hexdigest(),
                    "evidence_files": ["license-evidence/approval-record.pdf"],
                }
            ],
        }
        write_json(root / "system.json", system)
        write_json(root / "run.json", run)
        write_json(root / "license-register.json", license_register)
        write_jsonl(root / "samples.jsonl", [sample])
        write_jsonl(root / "predictions.jsonl", [] if omit_prediction else [prediction])

    def validate(self, root):
        return validate_candidate_package(
            root,
            schema_root=SCHEMA_ROOT,
            route_path=ROUTE_PATH,
            require_media=True,
        )

    def test_accepts_complete_real_candidate_package(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            report = self.validate(root)
        self.assertTrue(report["ready_for_e1_smoke"])
        self.assertEqual([], report["errors"])
        self.assertEqual(39, len(report["computability_matrix"]))
        by_metric = {row["metric_id"]: row for row in report["computability_matrix"]}
        self.assertEqual("computable", by_metric["D-4"]["status"])
        self.assertEqual(
            {
                "system.json",
                "run.json",
                "license-register.json",
                "samples.jsonl",
                "predictions.jsonl",
                "media/sample.bin",
                "license-evidence/license.txt",
                "license-evidence/approval-record.pdf",
            },
            set(report["artifact_sha256"]),
        )
        self.assertTrue(all(len(value) == 64 for value in report["artifact_sha256"].values()))

    def test_rejects_synthetic_system_from_real_candidate_gate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root, synthetic=True)
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertIn("synthetic_system_not_allowed", {item["code"] for item in report["errors"]})

    def test_rejects_media_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root, wrong_hash=True)
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertIn("media_hash_mismatch", {item["code"] for item in report["errors"]})

    def test_rejects_missing_prediction(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root, omit_prediction=True)
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertIn("missing_prediction", {item["code"] for item in report["errors"]})

    def test_rejects_media_path_that_escapes_package(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "package"
            root.mkdir()
            self.build_package(root)
            outside = Path(tmp_dir) / "outside.bin"
            outside.write_bytes(b"outside-package-media")
            samples_path = root / "samples.jsonl"
            sample = json.loads(samples_path.read_text(encoding="utf-8"))
            sample["file_path"] = "../outside.bin"
            sample["sha256"] = hashlib.sha256(outside.read_bytes()).hexdigest()
            write_jsonl(samples_path, [sample])
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertIn("media_path_outside_package", {item["code"] for item in report["errors"]})

    def test_rejects_real_model_without_weights_hash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            system_path = root / "system.json"
            system = json.loads(system_path.read_text(encoding="utf-8"))
            system["weights_sha256"] = None
            write_json(system_path, system)
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertIn("model_weights_hash_missing", {item["code"] for item in report["errors"]})

    def test_rejects_non_d0_or_unapproved_sample(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            samples_path = root / "samples.jsonl"
            sample = json.loads(samples_path.read_text(encoding="utf-8"))
            sample["partition"] = "D1"
            sample["license_status"] = "pending_review"
            write_jsonl(samples_path, [sample])
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("non_d0_sample", codes)
        self.assertIn("sample_license_not_approved", codes)

    def test_rejects_license_text_that_only_happens_to_start_with_approved(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            samples_path = root / "samples.jsonl"
            sample = json.loads(samples_path.read_text(encoding="utf-8"))
            sample["license_status"] = "approvedly_pending"
            write_jsonl(samples_path, [sample])
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertIn("sample_license_not_approved", {item["code"] for item in report["errors"]})

    def test_output_fields_require_presence_on_every_successful_prediction(self):
        records = [
            {"status": "ok", "fake_score": 0.1, "regions": []},
            {"status": "ok", "fake_score": 0.9},
            {"status": "runtime_error", "error_code": "FAILED"},
        ]
        self.assertEqual({"status", "fake_score"}, common_prediction_fields(records))
        self.assertEqual(set(), common_prediction_fields([]))

    def test_rejects_sample_whose_source_is_absent_from_license_register(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            register_path = root / "license-register.json"
            register = json.loads(register_path.read_text(encoding="utf-8"))
            register["sources"] = []
            write_json(register_path, register)
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertIn("sample_source_unapproved", {item["code"] for item in report["errors"]})

    def test_rejects_pending_or_unaudited_license_source(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            register_path = root / "license-register.json"
            register = json.loads(register_path.read_text(encoding="utf-8"))
            source = register["sources"][0]
            source["review_status"] = "pending"
            source["reviewed_by"] = None
            source["evidence_files"] = []
            write_json(register_path, register)
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertIn("license_source_not_approved", {item["code"] for item in report["errors"]})

    def test_rejects_missing_license_evidence_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            (root / "license-evidence" / "approval-record.pdf").unlink()
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertIn("license_evidence_missing", {item["code"] for item in report["errors"]})

    def test_structure_only_mode_can_never_claim_e1_readiness(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            (root / "media" / "sample.bin").unlink()
            report = validate_candidate_package(
                root, schema_root=SCHEMA_ROOT, route_path=ROUTE_PATH, require_media=False
            )
        self.assertTrue(report["structurally_valid"])
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertEqual("structure_only", report["validation_profile"])
        self.assertFalse(report["media_validation_performed"])

    def test_rejects_prediction_system_version_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            path = root / "predictions.jsonl"
            item = json.loads(path.read_text(encoding="utf-8"))
            item["system_version"] = "9.9.9"
            write_jsonl(path, [item])
            report = self.validate(root)
        self.assertIn("unexpected_system_version", {item["code"] for item in report["errors"]})

    def test_completed_run_requires_ordered_finish_time(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            path = root / "run.json"
            item = json.loads(path.read_text(encoding="utf-8"))
            item["finished_at"] = "2026-09-22T01:00:00Z"
            write_json(path, item)
            report = self.validate(root)
        self.assertIn("invalid_run_time_range", {item["code"] for item in report["errors"]})

    def test_rejects_non_standard_nan_in_prediction_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_package(root)
            path = root / "predictions.jsonl"
            path.write_text(path.read_text(encoding="utf-8").replace('0.1', 'NaN'), encoding="utf-8")
            report = self.validate(root)
        self.assertFalse(report["ready_for_e1_smoke"])
        self.assertIn("invalid_jsonl", {item["code"] for item in report["errors"]})


if __name__ == "__main__":
    unittest.main()
