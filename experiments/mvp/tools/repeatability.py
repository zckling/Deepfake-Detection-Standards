"""Compare two prediction runs while separating semantics from latency variation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from tools.metrics import latency_summary


IGNORED_SEMANTIC_FIELDS = {"run_id", "processing_time_sec"}


def _index(records: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        sample_id = record.get("sample_id")
        if not isinstance(sample_id, str):
            raise ValueError(f"{label} contains a record without string sample_id")
        if sample_id in indexed:
            raise ValueError(f"{label} contains duplicate sample_id {sample_id}")
        indexed[sample_id] = record
    return indexed


def _semantic_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key not in IGNORED_SEMANTIC_FIELDS}


def _semantic_sha256(indexed: dict[str, dict[str, Any]]) -> str:
    value = [_semantic_record(indexed[sample_id]) for sample_id in sorted(indexed)]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _mean_latency(indexed: dict[str, dict[str, Any]]) -> float | None:
    values = [
        record.get("processing_time_sec")
        for record in indexed.values()
        if isinstance(record.get("processing_time_sec"), (int, float))
        and not isinstance(record.get("processing_time_sec"), bool)
        and math.isfinite(record["processing_time_sec"])
        and record["processing_time_sec"] >= 0
    ]
    return float(latency_summary(values)["mean_sec"]) if values else None


def compare_prediction_runs(
    first: list[dict[str, Any]],
    second: list[dict[str, Any]],
    *,
    score_tolerance: float = 0.0,
) -> dict[str, Any]:
    if not math.isfinite(score_tolerance) or score_tolerance < 0:
        raise ValueError("score_tolerance must be finite and non-negative")
    for label, records in (("first run", first), ("second run", second)):
        for record in records:
            for field in ("fake_score", "processing_time_sec"):
                value = record.get(field)
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError(f"{label} contains non-finite {field}")
    first_by_id = _index(first, "first run")
    second_by_id = _index(second, "second run")
    shared = sorted(first_by_id.keys() & second_by_id.keys())
    missing_from_second = sorted(first_by_id.keys() - second_by_id.keys())
    missing_from_first = sorted(second_by_id.keys() - first_by_id.keys())

    details: list[dict[str, Any]] = []
    semantic_matches = 0
    score_mismatches = 0
    status_mismatches = 0
    label_mismatches = 0
    other_semantic_mismatches = 0
    for sample_id in shared:
        first_record = first_by_id[sample_id]
        second_record = second_by_id[sample_id]
        differences: list[str] = []
        if first_record.get("status") != second_record.get("status"):
            status_mismatches += 1
            differences.append("status")
        if first_record.get("is_fake_pred") != second_record.get("is_fake_pred"):
            label_mismatches += 1
            differences.append("is_fake_pred")
        first_score = first_record.get("fake_score")
        second_score = second_record.get("fake_score")
        statuses_match = first_record.get("status") == second_record.get("status")
        if statuses_match:
            if isinstance(first_score, (int, float)) and isinstance(second_score, (int, float)):
                if abs(float(first_score) - float(second_score)) > score_tolerance:
                    score_mismatches += 1
                    differences.append("fake_score")
            elif first_score != second_score:
                score_mismatches += 1
                differences.append("fake_score")

        ignored_for_core = IGNORED_SEMANTIC_FIELDS | {"status", "is_fake_pred", "fake_score"}
        first_other = {key: value for key, value in first_record.items() if key not in ignored_for_core}
        second_other = {key: value for key, value in second_record.items() if key not in ignored_for_core}
        if first_other != second_other:
            other_semantic_mismatches += 1
            differences.append("other_semantics")

        if not differences:
            semantic_matches += 1
        details.append(
            {
                "sample_id": sample_id,
                "match": not differences,
                "differences": differences,
                "score_delta": (
                    abs(float(first_score) - float(second_score))
                    if isinstance(first_score, (int, float))
                    and isinstance(second_score, (int, float))
                    else None
                ),
            }
        )

    deterministic = (
        not missing_from_first
        and not missing_from_second
        and semantic_matches == len(shared)
    )
    return {
        "schema_version": "1.0.0",
        "score_tolerance": score_tolerance,
        "semantically_deterministic": deterministic,
        "first_semantic_sha256": _semantic_sha256(first_by_id),
        "second_semantic_sha256": _semantic_sha256(second_by_id),
        "missing_from_first": missing_from_first,
        "missing_from_second": missing_from_second,
        "summary": {
            "first_count": len(first_by_id),
            "second_count": len(second_by_id),
            "compared": len(shared),
            "semantic_matches": semantic_matches,
            "score_mismatches": score_mismatches,
            "status_mismatches": status_mismatches,
            "label_mismatches": label_mismatches,
            "other_semantic_mismatches": other_semantic_mismatches,
        },
        "latency": {
            "first_mean_sec": _mean_latency(first_by_id),
            "second_mean_sec": _mean_latency(second_by_id),
        },
        "details": details,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} must contain an object")
        records.append(value)
    return records


def write_repeatability_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", required=True, type=Path)
    parser.add_argument("--second", required=True, type=Path)
    parser.add_argument("--score-tolerance", type=float, default=0.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = compare_prediction_runs(
        _read_jsonl(args.first),
        _read_jsonl(args.second),
        score_tolerance=args.score_tolerance,
    )
    if args.output:
        write_repeatability_report(report, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["semantically_deterministic"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
