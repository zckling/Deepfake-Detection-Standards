import json
import sys
import tempfile
import unittest
from pathlib import Path


MVP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP_ROOT))

from tools.run_e0 import execute_cases, write_report  # noqa: E402


FIXTURE_PATH = MVP_ROOT / "fixtures" / "e0-cases.json"


class E0RunnerTests(unittest.TestCase):
    def test_frozen_fixture_cases_all_match_manual_expectations(self):
        report = execute_cases(FIXTURE_PATH)
        self.assertGreaterEqual(report["total"], 8)
        self.assertEqual(report["total"], report["passed"])
        self.assertEqual(0, report["failed"])
        self.assertTrue(all(case["status"] == "pass" for case in report["cases"]))

    def test_tampered_expected_value_is_reported_as_failure(self):
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        fixture["cases"][0]["expected"]["accuracy"] = 0.123
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "tampered.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            report = execute_cases(path)
        self.assertEqual(1, report["failed"])
        self.assertEqual("fail", report["cases"][0]["status"])
        self.assertTrue(any("accuracy" in message for message in report["cases"][0]["errors"]))

    def test_report_writer_round_trips_utf8_json(self):
        report = execute_cases(FIXTURE_PATH)
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "e0-report.json"
            write_report(report, output)
            loaded = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report, loaded)


if __name__ == "__main__":
    unittest.main()
