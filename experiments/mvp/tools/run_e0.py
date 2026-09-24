"""Execute frozen E0 metric cases and compare results with manual expectations."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from tools.metrics import bbox_iou, binary_metrics, temporal_iou


def _dispatch(case: dict[str, Any]) -> Any:
    inputs = case["input"]
    match case["metric_type"]:
        case "binary":
            return binary_metrics(inputs["y_true"], inputs["y_score"], threshold=inputs["threshold"])
        case "temporal_iou":
            return {"temporal_iou": temporal_iou(tuple(inputs["first"]), tuple(inputs["second"]))}
        case "bbox_iou":
            return {"bbox_iou": bbox_iou(tuple(inputs["first"]), tuple(inputs["second"]))}
        case unknown:
            raise ValueError(f"unsupported metric_type: {unknown}")


def _compare(expected: Any, actual: Any, tolerance: float, path: str = "$") -> list[str]:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, got {type(actual).__name__}"]
        messages: list[str] = []
        for key, expected_value in expected.items():
            if key not in actual:
                messages.append(f"{path}.{key}: missing actual value")
            else:
                messages.extend(_compare(expected_value, actual[key], tolerance, f"{path}.{key}"))
        return messages
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return [f"{path}: expected numeric {expected!r}, got {actual!r}"]
        if not math.isclose(float(expected), float(actual), rel_tol=0.0, abs_tol=tolerance):
            return [f"{path}: expected {expected!r}, got {actual!r}, tolerance={tolerance}"]
        return []
    if expected != actual:
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    return []


def execute_cases(fixture_path: Path) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    tolerance = float(fixture.get("absolute_tolerance", 1e-12))
    results: list[dict[str, Any]] = []
    for case in fixture["cases"]:
        errors: list[str]
        actual: Any
        try:
            actual = _dispatch(case)
        except Exception as exc:  # E0 intentionally exercises invalid inputs.
            actual = {"error_type": type(exc).__name__, "message": str(exc)}
            expected_error = case.get("expected_error")
            errors = [] if expected_error == type(exc).__name__ else [
                f"$: expected error {expected_error!r}, got {type(exc).__name__}: {exc}"
            ]
        else:
            if "expected_error" in case:
                errors = [f"$: expected error {case['expected_error']!r}, but calculation succeeded"]
            else:
                errors = _compare(case["expected"], actual, tolerance)
        results.append(
            {
                "case_id": case["case_id"],
                "metric_type": case["metric_type"],
                "status": "pass" if not errors else "fail",
                "errors": errors,
                "actual": actual,
            }
        )
    passed = sum(result["status"] == "pass" for result in results)
    return {
        "fixture_version": fixture["fixture_version"],
        "absolute_tolerance": tolerance,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "cases": results,
    }


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = execute_cases(args.cases)
    write_report(report, args.output)
    print(json.dumps({key: report[key] for key in ("total", "passed", "failed")}, ensure_ascii=False))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
