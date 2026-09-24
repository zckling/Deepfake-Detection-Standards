"""Validate a real-candidate SUT package before an E1 smoke run is accepted."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.metric_routing import build_computability_matrix, load_routes, validate_routes
from tools.relationship_validation import validate_relationships
from tools.schema_validation import validate_record


REQUIRED_FILES = {
    "system": "system.json",
    "run": "run.json",
    "license_register": "license-register.json",
    "samples": "samples.jsonl",
    "predictions": "predictions.jsonl",
}


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    return {"code": code, "message": message, "context": context}


def _load_json(path: Path, errors: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard numeric constant {value}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(_error("invalid_json", f"cannot read {path.name}: {exc}", path=str(path)))
        return None
    if not isinstance(value, dict):
        errors.append(_error("invalid_json_type", f"{path.name} must contain an object", path=str(path)))
        return None
    return value


def _load_jsonl(path: Path, errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        errors.append(_error("invalid_jsonl", f"cannot read {path.name}: {exc}", path=str(path)))
        return records
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(
                line,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-standard numeric constant {value}")
                ),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(
                _error(
                    "invalid_jsonl",
                    f"{path.name}:{line_number} is invalid JSON: {exc}",
                    path=str(path),
                    line=line_number,
                )
            )
            continue
        if not isinstance(value, dict):
            errors.append(
                _error(
                    "invalid_jsonl_type",
                    f"{path.name}:{line_number} must contain an object",
                    path=str(path),
                    line=line_number,
                )
            )
            continue
        records.append(value)
    return records


def _validate_schema_records(
    records: list[dict[str, Any]],
    schema_path: Path,
    record_kind: str,
    errors: list[dict[str, Any]],
) -> None:
    for index, record in enumerate(records, start=1):
        for detail in validate_record(schema_path, record):
            errors.append(
                _error(
                    "schema_validation_failed",
                    f"{record_kind} record {index}: {detail}",
                    record_kind=record_kind,
                    record_index=index,
                )
            )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def common_prediction_fields(predictions: list[dict[str, Any]]) -> set[str]:
    """Return fields present on every successful prediction, not their union."""

    successful = [set(record) for record in predictions if record.get("status") == "ok"]
    if not successful:
        return set()
    common = successful[0].copy()
    for fields in successful[1:]:
        common.intersection_update(fields)
    return common


def _approved_license_sources(
    register: dict[str, Any] | None,
    errors: list[dict[str, Any]],
    package_dir: Path,
) -> tuple[set[str], list[Path]]:
    if register is None:
        return set(), []
    if register.get("schema_version") != "1.0.0" or register.get("register_status") != "approved":
        errors.append(
            _error(
                "license_register_not_approved",
                "license register must use schema_version 1.0.0 and register_status approved",
            )
        )
    sources = register.get("sources")
    if not isinstance(sources, list):
        errors.append(_error("license_register_invalid", "license register sources must be an array"))
        return set(), []
    approved: set[str] = set()
    verified_evidence_paths: list[Path] = []
    seen: set[str] = set()
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            errors.append(
                _error(
                    "license_register_invalid",
                    f"license source {index} must be an object",
                    source_index=index,
                )
            )
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            errors.append(
                _error(
                    "license_register_invalid",
                    f"license source {index} has no source_id",
                    source_index=index,
                )
            )
            continue
        if source_id in seen:
            errors.append(
                _error(
                    "duplicate_license_source",
                    f"license source {source_id} occurs more than once",
                    source_id=source_id,
                )
            )
            continue
        seen.add(source_id)
        evidence_files = source.get("evidence_files")
        license_text_path = source.get("license_text_path")
        license_digest = source.get("license_text_sha256")
        fields_valid = (
            source.get("review_status") == "approved"
            and source.get("download_status") == "approved_for_download"
            and isinstance(source.get("reviewed_by"), str)
            and bool(source["reviewed_by"].strip())
            and isinstance(source.get("reviewed_at"), str)
            and bool(source["reviewed_at"].strip())
            and isinstance(license_digest, str)
            and len(license_digest) == 64
            and all(character in "0123456789abcdef" for character in license_digest)
            and isinstance(license_text_path, str)
            and bool(license_text_path.strip())
            and isinstance(evidence_files, list)
            and bool(evidence_files)
            and all(isinstance(item, str) and item.strip() for item in evidence_files)
        )
        if not fields_valid:
            errors.append(
                _error(
                    "license_source_not_approved",
                    f"license source {source_id} lacks an approved, evidenced decision",
                    source_id=source_id,
                )
            )
            continue
        source_evidence_paths: list[Path] = []
        source_evidence_valid = True
        for raw_path in [license_text_path, *evidence_files]:
            evidence_path = Path(raw_path)
            if not evidence_path.is_absolute():
                evidence_path = package_dir / evidence_path
            evidence_path = evidence_path.resolve()
            if not evidence_path.is_relative_to(package_dir):
                errors.append(
                    _error(
                        "license_evidence_outside_package",
                        f"license source {source_id} evidence path escapes the package",
                        source_id=source_id,
                        file_path=str(evidence_path),
                    )
                )
                source_evidence_valid = False
                continue
            if not evidence_path.is_file():
                errors.append(
                    _error(
                        "license_evidence_missing",
                        f"license source {source_id} evidence file is missing",
                        source_id=source_id,
                        file_path=str(evidence_path),
                    )
                )
                source_evidence_valid = False
                continue
            source_evidence_paths.append(evidence_path)
        resolved_license_text = Path(license_text_path)
        if not resolved_license_text.is_absolute():
            resolved_license_text = package_dir / resolved_license_text
        resolved_license_text = resolved_license_text.resolve()
        if resolved_license_text.is_file() and resolved_license_text.is_relative_to(package_dir):
            actual_license_digest = _file_sha256(resolved_license_text)
            if actual_license_digest != license_digest:
                errors.append(
                    _error(
                        "license_text_hash_mismatch",
                        f"license source {source_id} text hash does not match the register",
                        source_id=source_id,
                        expected=license_digest,
                        actual=actual_license_digest,
                    )
                )
                source_evidence_valid = False
        if not source_evidence_valid:
            continue
        verified_evidence_paths.extend(source_evidence_paths)
        approved.add(source_id)
    return approved, verified_evidence_paths


def validate_candidate_package(
    package_dir: Path,
    *,
    schema_root: Path,
    route_path: Path,
    require_media: bool = True,
) -> dict[str, Any]:
    package_dir = package_dir.resolve()
    errors: list[dict[str, Any]] = []
    paths = {name: package_dir / filename for name, filename in REQUIRED_FILES.items()}
    for name, path in paths.items():
        if not path.is_file():
            errors.append(
                _error(
                    "required_file_missing",
                    f"required package file is missing: {path.name}",
                    file_kind=name,
                    path=str(path),
                )
            )
    if errors:
        return {
            "schema_version": "1.0.0",
            "package_dir": str(package_dir),
            "ready_for_e1_smoke": False,
            "errors": errors,
            "counts": {"samples": 0, "predictions": 0},
            "artifact_sha256": {},
            "computability_matrix": [],
        }

    system = _load_json(paths["system"], errors)
    run = _load_json(paths["run"], errors)
    license_register = _load_json(paths["license_register"], errors)
    samples = _load_jsonl(paths["samples"], errors)
    predictions = _load_jsonl(paths["predictions"], errors)

    if system is not None:
        _validate_schema_records(
            [system], schema_root / "system-registry.schema.json", "system", errors
        )
    if run is not None:
        _validate_schema_records([run], schema_root / "run-manifest.schema.json", "run", errors)
    _validate_schema_records(
        samples, schema_root / "sample-manifest.schema.json", "sample", errors
    )
    approved_source_ids, verified_license_paths = _approved_license_sources(
        license_register, errors, package_dir
    )
    _validate_schema_records(
        predictions, schema_root / "prediction.schema.json", "prediction", errors
    )

    if system is not None and system.get("system_type") == "synthetic_baseline":
        errors.append(
            _error(
                "synthetic_system_not_allowed",
                "real-candidate gate does not accept synthetic_baseline systems",
                system_id=system.get("system_id"),
            )
        )
    if (
        system is not None
        and system.get("system_type") == "model"
        and system.get("weights_sha256") is None
    ):
        errors.append(
            _error(
                "model_weights_hash_missing",
                "a model candidate must record the SHA-256 of its frozen weights",
                system_id=system.get("system_id"),
            )
        )
    if run is not None and run.get("experiment_id") != "E1":
        errors.append(
            _error(
                "non_e1_run",
                f"expected experiment_id E1, got {run.get('experiment_id')}",
                experiment_id=run.get("experiment_id"),
            )
        )
    if run is not None and run.get("status") != "completed":
        errors.append(
            _error(
                "run_not_completed",
                f"candidate package run must be completed, got {run.get('status')}",
                run_id=run.get("run_id"),
                status=run.get("status"),
            )
        )
    if run is not None and run.get("status") == "completed":
        try:
            started = datetime.fromisoformat(str(run.get("started_at", "")).replace("Z", "+00:00"))
            finished = datetime.fromisoformat(str(run.get("finished_at", "")).replace("Z", "+00:00"))
            valid_time_range = finished >= started
        except ValueError:
            valid_time_range = False
        if not valid_time_range:
            errors.append(
                _error(
                    "invalid_run_time_range",
                    "completed run requires valid finished_at not earlier than started_at",
                )
            )
    if system is not None and run is not None:
        if system.get("system_id") != run.get("system_id"):
            errors.append(
                _error(
                    "system_identity_mismatch",
                    "system.json and run.json use different system_id values",
                    system_id=system.get("system_id"),
                    run_system_id=run.get("system_id"),
                )
            )
        if system.get("system_version") != run.get("system_version"):
            errors.append(
                _error(
                    "system_version_mismatch",
                    "system.json and run.json use different system_version values",
                    system_version=system.get("system_version"),
                    run_system_version=run.get("system_version"),
                )
            )

    expected_run_id = run.get("run_id") if run is not None else None
    expected_system_id = system.get("system_id") if system is not None else None
    expected_system_version = system.get("system_version") if system is not None else None
    errors.extend(
        validate_relationships(
            samples,
            predictions,
            expected_run_id=expected_run_id,
            expected_system_id=expected_system_id,
            expected_system_version=expected_system_version,
        )
    )

    if not samples:
        errors.append(_error("empty_sample_manifest", "candidate package has no sample records"))
    for sample in samples:
        sample_id = sample.get("sample_id")
        if sample.get("partition") != "D0":
            errors.append(
                _error(
                    "non_d0_sample",
                    f"E1 smoke package sample {sample_id} is not assigned to D0",
                    sample_id=sample_id,
                    partition=sample.get("partition"),
                )
            )
        license_status = sample.get("license_status")
        normalized_license = license_status.lower() if isinstance(license_status, str) else ""
        if normalized_license != "approved" and not normalized_license.startswith("approved_"):
            errors.append(
                _error(
                    "sample_license_not_approved",
                    f"sample {sample_id} does not carry an approved license status",
                    sample_id=sample_id,
                    license_status=license_status,
                )
            )
        if sample.get("exclusion_status") != "included":
            errors.append(
                _error(
                    "sample_not_included",
                    f"E1 package contains non-included sample {sample_id}",
                    sample_id=sample_id,
                    exclusion_status=sample.get("exclusion_status"),
                )
            )
        if sample.get("source_id") not in approved_source_ids:
            errors.append(
                _error(
                    "sample_source_unapproved",
                    f"sample {sample_id} source is absent from the approved license register",
                    sample_id=sample_id,
                    source_id=sample.get("source_id"),
                )
            )

    verified_media_paths: list[Path] = []
    if require_media:
        for sample in samples:
            sample_id = sample.get("sample_id")
            raw_path = sample.get("file_path")
            if not isinstance(raw_path, str):
                continue
            if raw_path.startswith("synthetic://"):
                errors.append(
                    _error(
                        "logical_media_uri_not_allowed",
                        f"sample {sample_id} uses a logical synthetic URI",
                        sample_id=sample_id,
                        file_path=raw_path,
                    )
                )
                continue
            media_path = Path(raw_path)
            if not media_path.is_absolute():
                media_path = package_dir / media_path
            media_path = media_path.resolve()
            if not media_path.is_relative_to(package_dir):
                errors.append(
                    _error(
                        "media_path_outside_package",
                        f"sample {sample_id} media path escapes the package directory",
                        sample_id=sample_id,
                        file_path=str(media_path),
                    )
                )
                continue
            if not media_path.is_file():
                errors.append(
                    _error(
                        "media_file_missing",
                        f"sample {sample_id} media file does not exist",
                        sample_id=sample_id,
                        file_path=str(media_path),
                    )
                )
                continue
            actual_digest = _file_sha256(media_path)
            if actual_digest != sample.get("sha256"):
                errors.append(
                    _error(
                        "media_hash_mismatch",
                        f"sample {sample_id} SHA-256 does not match its manifest",
                        sample_id=sample_id,
                        expected=sample.get("sha256"),
                        actual=actual_digest,
                    )
                )
            else:
                verified_media_paths.append(media_path)

    routes = load_routes(route_path)
    route_errors = validate_routes(routes)
    for detail in route_errors:
        errors.append(_error("metric_route_invalid", detail))
    output_fields = sorted(common_prediction_fields(predictions))
    matrix = []
    if system is not None and not route_errors:
        available_data_fields = {key for sample in samples for key in sample}
        if run is not None:
            available_data_fields.update(run)
        matrix = build_computability_matrix(
            routes,
            [
                {
                    "system_id": system.get("system_id"),
                    "capabilities": system.get("capabilities", []),
                    "output_fields": output_fields,
                }
            ],
            available_data_fields=available_data_fields,
        )

    artifact_paths = [
        paths["system"],
        paths["run"],
        paths["license_register"],
        paths["samples"],
        paths["predictions"],
    ]
    artifact_paths.extend(verified_media_paths)
    artifact_paths.extend(verified_license_paths)
    artifact_sha256 = {
        path.relative_to(package_dir).as_posix(): _file_sha256(path)
        for path in sorted(set(artifact_paths), key=lambda item: item.as_posix())
        if path.is_file() and path.is_relative_to(package_dir)
    }
    return {
        "schema_version": "1.0.0",
        "package_dir": str(package_dir),
        "validation_profile": "formal_media" if require_media else "structure_only",
        "media_validation_performed": require_media,
        "structurally_valid": not errors,
        "ready_for_e1_smoke": not errors and require_media,
        "errors": errors,
        "counts": {
            "samples": len(samples),
            "predictions": len(predictions),
            "computability_cells": len(matrix),
        },
        "artifact_sha256": artifact_sha256,
        "computability_matrix": matrix,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument(
        "--schema-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "schemas",
    )
    parser.add_argument(
        "--route-path",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "config" / "metric-routing.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-missing-media", action="store_true")
    args = parser.parse_args()
    report = validate_candidate_package(
        args.package,
        schema_root=args.schema_root,
        route_path=args.route_path,
        require_media=not args.allow_missing_media,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["ready_for_e1_smoke"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
