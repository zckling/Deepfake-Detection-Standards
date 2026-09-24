import sys
import unittest
from collections import Counter
from pathlib import Path


MVP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP_ROOT))

from tools.metric_routing import build_computability_matrix, load_routes, validate_routes  # noqa: E402


ROUTE_PATH = MVP_ROOT / "config" / "metric-routing.json"


class MetricRoutingInventoryTests(unittest.TestCase):
    def test_malformed_route_returns_diagnostic_instead_of_crashing(self):
        errors = validate_routes([None, "bad-route"])
        self.assertEqual(2, sum("must be an object" in item for item in errors))
    def test_route_table_covers_the_frozen_39_metric_inventory_once(self):
        routes = load_routes(ROUTE_PATH)
        self.assertEqual([], validate_routes(routes))
        self.assertEqual(39, len(routes))
        self.assertEqual(39, len({route["metric_id"] for route in routes}))
        self.assertEqual(
            {"A": 3, "B": 3, "C": 10, "D": 5, "E": 4, "F": 4, "G": 5, "H": 5},
            dict(sorted(Counter(route["metric_id"].split("-")[0] for route in routes).items())),
        )

    def test_each_route_declares_inputs_capabilities_and_calculator_state(self):
        routes = load_routes(ROUTE_PATH)
        for route in routes:
            with self.subTest(metric_id=route["metric_id"]):
                self.assertTrue(route["metric_name"])
                self.assertTrue(route["tasks"])
                self.assertIn(route["applicability"], {"mandatory", "conditional", "extension"})
                self.assertIsInstance(route["required_capabilities"], list)
                self.assertIsInstance(route["required_data_fields"], list)
                self.assertIsInstance(route["required_prediction_fields"], list)
                self.assertIn(route["calculator_status"], {"implemented", "pending"})
                self.assertIn(route["output_type"], {"scalar", "vector", "record", "boolean"})


class ComputabilityMatrixTests(unittest.TestCase):
    def setUp(self):
        self.routes = load_routes(ROUTE_PATH)
        self.systems = [
            {
                "system_id": "SUT-SYN-CLASSIFIER",
                "capabilities": ["binary_classification"],
                "output_fields": ["is_fake_pred", "fake_score", "processing_time_sec", "status"],
            },
            {
                "system_id": "SUT-SYN-LOCALIZER",
                "capabilities": [
                    "binary_classification",
                    "spatial_localization",
                    "temporal_media",
                ],
                "output_fields": [
                    "is_fake_pred",
                    "fake_score",
                    "processing_time_sec",
                    "status",
                    "regions",
                ],
            },
        ]

    def test_matrix_distinguishes_computable_unsupported_and_pending(self):
        matrix = build_computability_matrix(
            self.routes,
            self.systems,
            available_data_fields={
                "label_state",
                "fake_modalities",
                "fake_objects",
                "regions",
                "duration_sec",
                "wall_clock_sec",
                "batch_size",
                "concurrency",
            },
        )
        by_key = {(row["metric_id"], row["system_id"]): row for row in matrix}
        self.assertEqual(78, len(matrix))
        self.assertEqual("computable", by_key[("C-1", "SUT-SYN-CLASSIFIER")]["status"])
        self.assertEqual("unsupported", by_key[("C-8", "SUT-SYN-CLASSIFIER")]["status"])
        self.assertEqual("computable", by_key[("C-8", "SUT-SYN-LOCALIZER")]["status"])
        self.assertEqual("computable", by_key[("D-1", "SUT-SYN-CLASSIFIER")]["status"])
        self.assertEqual("computable", by_key[("D-2", "SUT-SYN-LOCALIZER")]["status"])
        self.assertEqual("computable", by_key[("D-4", "SUT-SYN-CLASSIFIER")]["status"])

    def test_matrix_reports_missing_data_before_attempting_calculation(self):
        matrix = build_computability_matrix(
            [route for route in self.routes if route["metric_id"] == "C-1"],
            self.systems[:1],
            available_data_fields=set(),
        )
        self.assertEqual("missing_data", matrix[0]["status"])
        self.assertEqual(["label_state"], matrix[0]["missing_data_fields"])


if __name__ == "__main__":
    unittest.main()
