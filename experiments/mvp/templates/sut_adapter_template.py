"""Copy-and-customize template for a real SUT adapter.

The adapter MUST NOT inspect labels or annotations. Replace every NotImplementedError
and register only capabilities that the wrapped system genuinely provides.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class RealSUTAdapterTemplate:
    synthetic_only = False
    system_id = "SUT-REPLACE-ME"
    output_fields = ("is_fake_pred", "fake_score", "processing_time_sec", "status")

    def registration(self) -> dict[str, Any]:
        raise NotImplementedError("return a system-registry.schema.json record")

    def predict_many(
        self, samples: Sequence[dict[str, Any]], *, run_id: str
    ) -> list[dict[str, Any]]:
        public_inputs = [
            {
                "sample_id": sample["sample_id"],
                "file_path": sample["file_path"],
                "media_type": sample["media_type"],
            }
            for sample in samples
        ]
        del public_inputs
        raise NotImplementedError(
            "invoke the real SUT using only public_inputs and map every result to prediction.schema.json"
        )
