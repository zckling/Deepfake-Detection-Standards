"""SUT adapter contract plus deterministic synthetic adapters for preflight only."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class SUTAdapter(Protocol):
    synthetic_only: bool
    system_id: str
    output_fields: tuple[str, ...]

    def registration(self) -> dict[str, Any]: ...

    def predict_many(
        self, samples: Sequence[dict[str, Any]], *, run_id: str
    ) -> list[dict[str, Any]]: ...


class SyntheticAdapter:
    """Truth-aware adapter used solely to test plumbing, never detector quality."""

    synthetic_only = True
    output_fields = ("is_fake_pred", "fake_score", "processing_time_sec", "status")
    _SYSTEM_IDS = {
        "perfect": "SUT-SYN-PERFECT",
        "inverse": "SUT-SYN-INVERSE",
        "missing_output": "SUT-SYN-MISSING",
    }

    def __init__(self, strategy: str):
        if strategy not in self._SYSTEM_IDS:
            raise ValueError(f"unknown synthetic strategy: {strategy}")
        self.strategy = strategy
        self.system_id = self._SYSTEM_IDS[strategy]

    def registration(self) -> dict[str, Any]:
        return {
            "system_id": self.system_id,
            "name": f"D0 synthetic {self.strategy} adapter",
            "system_version": "1.0.0",
            "system_type": "synthetic_baseline",
            "code_revision": "logical-preflight-v1",
            "weights_sha256": None,
            "capabilities": ["binary_classification"],
            "environment": {
                "runtime": "python-standard-library",
                "purpose": "pipeline_preflight_only",
                "truth_aware": True,
            },
            "schema_version": "1.0.0",
        }

    def predict_many(
        self, samples: Sequence[dict[str, Any]], *, run_id: str
    ) -> list[dict[str, Any]]:
        predictions: list[dict[str, Any]] = []
        for index, sample in enumerate(samples, start=1):
            if self.strategy == "missing_output":
                predictions.append(
                    {
                        "sample_id": sample["sample_id"],
                        "system_id": self.system_id,
                        "system_version": "1.0.0",
                        "run_id": run_id,
                        "is_fake_pred": None,
                        "fake_score": None,
                        "processing_time_sec": 0.001,
                        "status": "missing_output",
                        "error_code": "SYNTHETIC_MISSING_OUTPUT",
                        "schema_version": "1.0.0",
                    }
                )
                continue

            is_fake = sample["label_state"] == "FAKE"
            if self.strategy == "inverse":
                is_fake = not is_fake
            predictions.append(
                {
                    "sample_id": sample["sample_id"],
                    "system_id": self.system_id,
                    "system_version": "1.0.0",
                    "run_id": run_id,
                    "is_fake_pred": is_fake,
                    "fake_score": 0.9 if is_fake else 0.1,
                    "processing_time_sec": round(0.001 + index / 1_000_000, 6),
                    "status": "ok",
                    "error_code": None,
                    "schema_version": "1.0.0",
                }
            )
        return predictions
