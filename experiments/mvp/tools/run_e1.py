"""Execute and materialize the synthetic E1 plumbing preflight."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from tools.d0_smoke import build_d0_smoke_samples
from tools.metric_routing import build_computability_matrix, load_routes, validate_routes
from tools.metrics import binary_metrics, prediction_latency_metrics
from tools.relationship_validation import validate_relationships
from tools.sut_adapter import SUTAdapter, SyntheticAdapter


FIXED_STARTED_AT = "2026-09-23T00:00:00Z"
FIXED_FINISHED_AT = "2026-09-23T00:00:01Z"


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _metric_projection(values: dict[str, Any]) -> dict[str, float | None]:
    return {
        "C-1": values["accuracy"],
        "C-2": values["precision"],
        "C-3": values["recall"],
        "C-4": values["f1"],
        "C-5": values["roc_auc"],
        "C-6": values["eer"],
    }


def _metric_records(
    run_id: str,
    values: dict[str, float | None],
    *,
    confusion: dict[str, int] | None,
    latency: dict[str, float | int] | None,
) -> list[dict[str, Any]]:
    fractions: dict[str, tuple[float | None, float | None]] = {
        "C-1": (
            confusion["tp"] + confusion["tn"] if confusion else None,
            sum(confusion.values()) if confusion else None,
        ),
        "C-2": (
            confusion["tp"] if confusion else None,
            confusion["tp"] + confusion["fp"] if confusion else None,
        ),
        "C-3": (
            confusion["tp"] if confusion else None,
            confusion["tp"] + confusion["fn"] if confusion else None,
        ),
        "C-4": (
            2 * confusion["tp"] if confusion else None,
            2 * confusion["tp"] + confusion["fp"] + confusion["fn"] if confusion else None,
        ),
        "C-5": (None, None),
        "C-6": (None, None),
        "D-1": (
            float(latency["sum_sec"]) if latency else None,
            float(latency["count"]) if latency else None,
        ),
    }
    records: list[dict[str, Any]] = []
    for metric_id in ("C-1", "C-2", "C-3", "C-4", "C-5", "C-6", "D-1"):
        numerator, denominator = fractions[metric_id]
        value = values[metric_id]
        records.append(
            {
                "run_id": run_id,
                "metric_id": metric_id,
                "status": "ok" if value is not None else "undefined",
                "value": value,
                "numerator": numerator,
                "denominator": denominator,
                "analysis_unit": "sample",
                "calculator_version": "mvp-1.1.0",
                "schema_version": "1.0.0",
            }
        )
    return records


def execute_synthetic_preflight(
    samples: Sequence[dict[str, Any]],
    adapters: Sequence[SUTAdapter],
    *,
    route_path: Path,
) -> dict[str, Any]:
    if any(not adapter.synthetic_only for adapter in adapters):
        raise ValueError("synthetic preflight accepts synthetic-only adapters")
    routes = load_routes(route_path)
    route_errors = validate_routes(routes)
    if route_errors:
        raise ValueError(f"invalid metric route table: {route_errors}")

    registrations: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    all_predictions: list[dict[str, Any]] = []
    relationship_errors: list[dict[str, Any]] = []
    metrics: dict[str, dict[str, float | None]] = {}
    metric_results: list[dict[str, Any]] = []
    matrix_systems: list[dict[str, Any]] = []

    labels_by_id = {
        sample["sample_id"]: 1 if sample["label_state"] == "FAKE" else 0 for sample in samples
    }
    for adapter in adapters:
        registration = adapter.registration()
        registrations.append(registration)
        run_id = f"RUN-E1-{adapter.system_id.removeprefix('SUT-')}-001"
        predictions = adapter.predict_many(samples, run_id=run_id)
        all_predictions.extend(predictions)
        relationship_errors.extend(
            validate_relationships(
                samples,
                predictions,
                expected_run_id=run_id,
                expected_system_id=adapter.system_id,
                expected_system_version=registration["system_version"],
            )
        )
        usable = [prediction for prediction in predictions if prediction["status"] == "ok"]
        if len(usable) == len(samples):
            usable_by_id = {prediction["sample_id"]: prediction for prediction in usable}
            ordered_ids = sorted(labels_by_id)
            binary_values = binary_metrics(
                [labels_by_id[sample_id] for sample_id in ordered_ids],
                [usable_by_id[sample_id]["fake_score"] for sample_id in ordered_ids],
            )
            latency = prediction_latency_metrics(predictions, timeout_cap_sec=1.0)
            projected = _metric_projection(binary_values)
            projected["D-1"] = float(latency["mean_sec"])
            metrics[adapter.system_id] = projected
            metric_results.extend(
                _metric_records(
                    run_id,
                    projected,
                    confusion=binary_values["confusion"],
                    latency=latency,
                )
            )
        else:
            projected = {
                metric_id: None
                for metric_id in ("C-1", "C-2", "C-3", "C-4", "C-5", "C-6", "D-1")
            }
            metrics[adapter.system_id] = projected
            metric_results.extend(
                _metric_records(run_id, projected, confusion=None, latency=None)
            )

        runs.append(
            {
                "run_id": run_id,
                "experiment_id": "E1",
                "dataset_version": "D0-SMOKE-LOGICAL-1.0.0",
                "system_id": adapter.system_id,
                "system_version": registration["system_version"],
                "config_sha256": _sha256_json({"strategy": getattr(adapter, "strategy", "unknown")}),
                "environment_sha256": _sha256_json(registration["environment"]),
                "started_at": FIXED_STARTED_AT,
                "finished_at": FIXED_FINISHED_AT,
                "status": "completed",
                "schema_version": "1.0.0",
            }
        )
        matrix_systems.append(
            {
                "system_id": adapter.system_id,
                "capabilities": registration["capabilities"],
                "output_fields": list(adapter.output_fields),
            }
        )

    available_data_fields = {key for sample in samples for key in sample}
    matrix = build_computability_matrix(
        routes,
        matrix_systems,
        available_data_fields=available_data_fields,
    )
    return {
        "schema_version": "1.0.0",
        "result_class": "synthetic_preflight",
        "formal_evaluation": False,
        "warning": "Truth-aware logical fixtures validate plumbing only; they are not detector-quality evidence.",
        "dataset": {
            "dataset_id": "D0-SMOKE-LOGICAL",
            "sample_count": len(samples),
            "contains_media_bytes": False,
            "purpose": "schema, adapter, routing, and report integration preflight",
        },
        "samples": list(samples),
        "systems": registrations,
        "runs": runs,
        "predictions": all_predictions,
        "metrics": metrics,
        "metric_results": metric_results,
        "relationship_errors": relationship_errors,
        "computability_matrix": matrix,
    }


def _write_jsonl(records: Sequence[dict[str, Any]], path: Path) -> None:
    content = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    path.write_text(content, encoding="utf-8")


def _markdown_summary(report: dict[str, Any]) -> str:
    lines = [
        "# E1 synthetic_preflight 报告",
        "",
        "> 结论边界：本报告仅证明逻辑夹具、适配器、指标路由与报告链路可运行；不构成真实深度伪造检测性能结论。",
        "",
        f"- result_class: `{report['result_class']}`",
        f"- formal_evaluation: `{str(report['formal_evaluation']).lower()}`",
        f"- D0-SMOKE 逻辑样本数: {report['dataset']['sample_count']}",
        f"- 合成被测对象数: {len(report['systems'])}",
        f"- 指标×系统矩阵单元数: {len(report['computability_matrix'])}",
        f"- 跨文件关系错误数: {len(report['relationship_errors'])}",
        "",
        "## 合成分类指标",
        "",
        "| system_id | C-1 | C-2 | C-3 | C-4 | C-5 | C-6 | D-1(s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system_id, values in report["metrics"].items():
        rendered = ["undefined" if values[key] is None else f"{values[key]:.6f}" for key in ("C-1", "C-2", "C-3", "C-4", "C-5", "C-6", "D-1")]
        lines.append(f"| {system_id} | " + " | ".join(rendered) + " |")
    lines.extend(["", "## 禁止用途", "", "不得把上述数值用于模型排名、采购判定、达标声明或标准阈值校准。", ""])
    return "\n".join(lines)


def write_preflight_artifacts(report: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "report_json": output_dir / "e1-synthetic-preflight.json",
        "report_markdown": output_dir / "E1-synthetic-preflight.md",
        "sample_manifest": output_dir / "D0-SMOKE.samples.jsonl",
        "system_registry": output_dir / "synthetic-systems.jsonl",
        "predictions": output_dir / "synthetic-predictions.jsonl",
        "metric_results": output_dir / "synthetic-metric-results.jsonl",
        "computability_csv": output_dir / "e1-computability-matrix.csv",
    }
    outputs["report_json"].write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    outputs["report_markdown"].write_text(_markdown_summary(report), encoding="utf-8")
    _write_jsonl(report["samples"], outputs["sample_manifest"])
    _write_jsonl(report["systems"], outputs["system_registry"])
    _write_jsonl(report["predictions"], outputs["predictions"])
    _write_jsonl(report["metric_results"], outputs["metric_results"])

    fieldnames = [
        "metric_id",
        "metric_name",
        "system_id",
        "status",
        "missing_data_fields",
        "missing_capabilities",
        "missing_prediction_fields",
        "calculator_status",
    ]
    with outputs["computability_csv"].open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["computability_matrix"]:
            writer.writerow(
                {
                    **row,
                    "missing_data_fields": ";".join(row["missing_data_fields"]),
                    "missing_capabilities": ";".join(row["missing_capabilities"]),
                    "missing_prediction_fields": ";".join(row["missing_prediction_fields"]),
                }
            )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "reports" / "e1-synthetic",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = execute_synthetic_preflight(
        build_d0_smoke_samples(),
        [SyntheticAdapter("perfect"), SyntheticAdapter("inverse")],
        route_path=root / "config" / "metric-routing.json",
    )
    outputs = write_preflight_artifacts(report, args.output_dir)
    print(json.dumps({key: str(path) for key, path in outputs.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
