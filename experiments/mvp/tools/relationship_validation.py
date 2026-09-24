"""Cross-file relationship checks that JSON Schema cannot express."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    return {"code": code, "message": message, "context": context}


def validate_relationships(
    samples: Sequence[dict[str, Any]],
    predictions: Sequence[dict[str, Any]],
    *,
    expected_run_id: str | None = None,
    expected_system_id: str | None = None,
    expected_system_version: str | None = None,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    sample_counts: dict[str, int] = defaultdict(int)
    samples_by_id: dict[str, dict[str, Any]] = {}
    group_partitions: dict[str, set[str]] = defaultdict(set)

    for record in samples:
        sample_id = record.get("sample_id")
        if not isinstance(sample_id, str):
            continue
        sample_counts[sample_id] += 1
        samples_by_id.setdefault(sample_id, record)
        group_id = record.get("group_id")
        partition = record.get("partition")
        if isinstance(group_id, str) and isinstance(partition, str):
            group_partitions[group_id].add(partition)

    for sample_id, count in sorted(sample_counts.items()):
        if count > 1:
            errors.append(
                _error(
                    "duplicate_sample_id",
                    f"sample_id {sample_id} occurs {count} times",
                    sample_id=sample_id,
                    count=count,
                )
            )
    for group_id, partitions in sorted(group_partitions.items()):
        if len(partitions) > 1:
            errors.append(
                _error(
                    "group_partition_leakage",
                    f"group {group_id} spans partitions {sorted(partitions)}",
                    group_id=group_id,
                    partitions=sorted(partitions),
                )
            )

    for record in samples:
        parent_id = record.get("parent_sample_id")
        if parent_id is None:
            continue
        child_id = record.get("sample_id")
        parent = samples_by_id.get(parent_id)
        if parent is None:
            errors.append(
                _error(
                    "unknown_parent_sample_id",
                    f"sample {child_id} references unknown parent {parent_id}",
                    sample_id=child_id,
                    parent_sample_id=parent_id,
                )
            )
            continue
        if parent.get("group_id") != record.get("group_id"):
            errors.append(
                _error(
                    "parent_group_mismatch",
                    f"sample {child_id} and parent {parent_id} use different groups",
                    sample_id=child_id,
                    parent_sample_id=parent_id,
                )
            )
        if parent.get("partition") != record.get("partition"):
            errors.append(
                _error(
                    "parent_partition_mismatch",
                    f"sample {child_id} and parent {parent_id} use different partitions",
                    sample_id=child_id,
                    parent_sample_id=parent_id,
                )
            )

    prediction_counts: dict[tuple[Any, Any, Any], int] = defaultdict(int)
    predicted_expected_samples: set[str] = set()
    for record in predictions:
        sample_id = record.get("sample_id")
        run_id = record.get("run_id")
        system_id = record.get("system_id")
        system_version = record.get("system_version")
        key = (run_id, system_id, sample_id)
        prediction_counts[key] += 1
        if sample_id not in samples_by_id:
            errors.append(
                _error(
                    "unknown_prediction_sample_id",
                    f"prediction references unknown sample {sample_id}",
                    sample_id=sample_id,
                )
            )
        if expected_run_id is not None and run_id != expected_run_id:
            errors.append(
                _error(
                    "unexpected_run_id",
                    f"expected run_id {expected_run_id}, got {run_id}",
                    sample_id=sample_id,
                    run_id=run_id,
                )
            )
        if expected_system_id is not None and system_id != expected_system_id:
            errors.append(
                _error(
                    "unexpected_system_id",
                    f"expected system_id {expected_system_id}, got {system_id}",
                    sample_id=sample_id,
                    system_id=system_id,
                )
            )
        if expected_system_version is not None and system_version != expected_system_version:
            errors.append(
                _error(
                    "unexpected_system_version",
                    f"expected system_version {expected_system_version}, got {system_version}",
                    sample_id=sample_id,
                    system_version=system_version,
                )
            )
        if (
            sample_id in samples_by_id
            and (expected_run_id is None or run_id == expected_run_id)
            and (expected_system_id is None or system_id == expected_system_id)
            and (expected_system_version is None or system_version == expected_system_version)
        ):
            predicted_expected_samples.add(sample_id)

    for key, count in sorted(prediction_counts.items(), key=lambda item: str(item[0])):
        if count > 1:
            run_id, system_id, sample_id = key
            errors.append(
                _error(
                    "duplicate_prediction",
                    f"prediction key {key} occurs {count} times",
                    run_id=run_id,
                    system_id=system_id,
                    sample_id=sample_id,
                    count=count,
                )
            )

    if expected_run_id is not None and expected_system_id is not None:
        for sample_id in sorted(samples_by_id.keys() - predicted_expected_samples):
            errors.append(
                _error(
                    "missing_prediction",
                    f"no prediction for sample {sample_id}",
                    sample_id=sample_id,
                    run_id=expected_run_id,
                    system_id=expected_system_id,
                )
            )
    return errors
