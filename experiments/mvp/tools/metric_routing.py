"""Metric routing and computability assessment for the frozen 39-metric inventory."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any


EXPECTED_METRIC_IDS = {
    *(f"A-{index}" for index in range(1, 4)),
    *(f"B-{index}" for index in range(1, 4)),
    *(f"C-{index}" for index in range(1, 11)),
    *(f"D-{index}" for index in range(1, 6)),
    *(f"E-{index}" for index in range(1, 5)),
    *(f"F-{index}" for index in range(1, 5)),
    *(f"G-{index}" for index in range(1, 6)),
    *(f"H-{index}" for index in range(1, 6)),
}
VALID_APPLICABILITY = {"mandatory", "conditional", "extension"}
VALID_CALCULATOR_STATUS = {"implemented", "pending"}
VALID_OUTPUT_TYPES = {"scalar", "vector", "record", "boolean"}
REQUIRED_KEYS = {
    "metric_id",
    "metric_name",
    "tasks",
    "applicability",
    "required_capabilities",
    "required_data_fields",
    "required_prediction_fields",
    "calculator_status",
    "output_type",
}


def load_routes(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("routes"), list):
        raise ValueError("metric route file must contain a top-level routes array")
    return payload["routes"]


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def validate_routes(routes: Sequence[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    objects = [route for route in routes if isinstance(route, dict)]
    metric_ids = [route.get("metric_id") for route in objects]
    duplicates = _duplicates(value for value in metric_ids if isinstance(value, str))
    if duplicates:
        errors.append(f"duplicate metric_id values: {sorted(duplicates)}")
    actual_ids = {value for value in metric_ids if isinstance(value, str)}
    if actual_ids != EXPECTED_METRIC_IDS:
        errors.append(
            f"metric inventory mismatch; missing={sorted(EXPECTED_METRIC_IDS - actual_ids)}, "
            f"unexpected={sorted(actual_ids - EXPECTED_METRIC_IDS)}"
        )

    for index, route in enumerate(routes):
        prefix = f"route[{index}]"
        if not isinstance(route, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing_keys = REQUIRED_KEYS - route.keys()
        if missing_keys:
            errors.append(f"{prefix} missing keys: {sorted(missing_keys)}")
            continue
        metric_id = route["metric_id"]
        if not isinstance(metric_id, str) or not re.fullmatch(r"[A-H]-([1-9]|10)", metric_id):
            errors.append(f"{prefix}.metric_id is invalid")
        if not isinstance(route["metric_name"], str) or not route["metric_name"].strip():
            errors.append(f"{prefix}.metric_name must be non-empty")
        if not isinstance(route["tasks"], list) or not route["tasks"]:
            errors.append(f"{prefix}.tasks must be a non-empty array")
        for key in (
            "required_capabilities",
            "required_data_fields",
            "required_prediction_fields",
        ):
            value = route[key]
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                errors.append(f"{prefix}.{key} must be a string array")
        if route["applicability"] not in VALID_APPLICABILITY:
            errors.append(f"{prefix}.applicability is invalid")
        if route["calculator_status"] not in VALID_CALCULATOR_STATUS:
            errors.append(f"{prefix}.calculator_status is invalid")
        if route["output_type"] not in VALID_OUTPUT_TYPES:
            errors.append(f"{prefix}.output_type is invalid")
    return errors


def build_computability_matrix(
    routes: Sequence[dict[str, Any]],
    systems: Sequence[dict[str, Any]],
    *,
    available_data_fields: set[str],
) -> list[dict[str, Any]]:
    """Return one deterministic metric/system decision per Cartesian-product cell."""

    matrix: list[dict[str, Any]] = []
    for route in routes:
        for system in systems:
            capabilities = set(system.get("capabilities", []))
            output_fields = set(system.get("output_fields", []))
            missing_data = sorted(set(route["required_data_fields"]) - available_data_fields)
            missing_capabilities = sorted(set(route["required_capabilities"]) - capabilities)
            missing_outputs = sorted(set(route["required_prediction_fields"]) - output_fields)

            if missing_data:
                status = "missing_data"
            elif missing_capabilities:
                status = "unsupported"
            elif missing_outputs:
                status = "missing_output"
            elif route["calculator_status"] != "implemented":
                status = "calculator_pending"
            else:
                status = "computable"

            matrix.append(
                {
                    "metric_id": route["metric_id"],
                    "metric_name": route["metric_name"],
                    "system_id": system["system_id"],
                    "status": status,
                    "missing_data_fields": missing_data,
                    "missing_capabilities": missing_capabilities,
                    "missing_prediction_fields": missing_outputs,
                    "calculator_status": route["calculator_status"],
                }
            )
    return matrix
