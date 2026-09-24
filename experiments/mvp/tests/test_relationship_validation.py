import sys
import unittest
from pathlib import Path


MVP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP_ROOT))

from tools.relationship_validation import validate_relationships  # noqa: E402


def sample(sample_id, group_id, *, partition="D0", parent_sample_id=None):
    return {
        "sample_id": sample_id,
        "group_id": group_id,
        "partition": partition,
        "parent_sample_id": parent_sample_id,
    }


def prediction(sample_id, *, run_id="RUN-E1-SYN-001", system_id="SUT-SYN-PERFECT", system_version="1.0.0"):
    return {"sample_id": sample_id, "run_id": run_id, "system_id": system_id, "system_version": system_version}


class RelationshipValidationTests(unittest.TestCase):
    def test_accepts_consistent_samples_and_predictions(self):
        samples = [
            sample("DFSTD-V-000001", "GRP-000001"),
            sample(
                "DFSTD-V-000002",
                "GRP-000001",
                parent_sample_id="DFSTD-V-000001",
            ),
        ]
        predictions = [prediction(item["sample_id"]) for item in samples]
        self.assertEqual(
            [],
            validate_relationships(
                samples,
                predictions,
                expected_run_id="RUN-E1-SYN-001",
                expected_system_id="SUT-SYN-PERFECT",
                expected_system_version="1.0.0",
            ),
        )

    def test_reports_duplicate_ids_group_leakage_and_bad_parent(self):
        samples = [
            sample("DFSTD-V-000001", "GRP-000001", partition="D0"),
            sample("DFSTD-V-000001", "GRP-000002", partition="D0"),
            sample("DFSTD-V-000002", "GRP-000003", partition="D1"),
            sample("DFSTD-V-000003", "GRP-000003", partition="D2"),
            sample(
                "DFSTD-V-000004",
                "GRP-000004",
                parent_sample_id="DFSTD-V-999999",
            ),
        ]
        errors = validate_relationships(samples, [])
        codes = {error["code"] for error in errors}
        self.assertIn("duplicate_sample_id", codes)
        self.assertIn("group_partition_leakage", codes)
        self.assertIn("unknown_parent_sample_id", codes)

    def test_reports_unknown_duplicate_and_mismatched_predictions(self):
        samples = [sample("DFSTD-V-000001", "GRP-000001")]
        predictions = [
            prediction("DFSTD-V-000001"),
            prediction("DFSTD-V-000001"),
            prediction("DFSTD-V-999999"),
            prediction("DFSTD-V-000001", run_id="RUN-WRONG", system_id="SUT-WRONG"),
        ]
        errors = validate_relationships(
            samples,
            predictions,
            expected_run_id="RUN-E1-SYN-001",
            expected_system_id="SUT-SYN-PERFECT",
        )
        codes = {error["code"] for error in errors}
        self.assertIn("duplicate_prediction", codes)
        self.assertIn("unknown_prediction_sample_id", codes)
        self.assertIn("unexpected_run_id", codes)
        self.assertIn("unexpected_system_id", codes)

    def test_reports_unexpected_system_version(self):
        errors = validate_relationships(
            [sample("DFSTD-V-000001", "GRP-000001")],
            [prediction("DFSTD-V-000001", system_version="9.9.9")],
            expected_run_id="RUN-E1-SYN-001",
            expected_system_id="SUT-SYN-PERFECT",
            expected_system_version="1.0.0",
        )
        self.assertIn("unexpected_system_version", {item["code"] for item in errors})


if __name__ == "__main__":
    unittest.main()
