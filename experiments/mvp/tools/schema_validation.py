"""Validate JSON records and JSONL files against Draft 2020-12 schemas."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


@dataclass(frozen=True)
class ValidationSummary:
    total: int
    valid: int
    invalid: int
    errors: tuple[str, ...]


def _load_schema(schema_path: Path) -> dict[str, Any]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def validate_record(schema_path: Path, record: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(_load_schema(schema_path), format_checker=FormatChecker())
    messages: list[str] = []
    def inspect(value: Any, path: str = "$") -> None:
        if isinstance(value, float) and not math.isfinite(value):
            messages.append(f"{path}: non-finite number is not valid JSON")
        elif isinstance(value, dict):
            for key, child in value.items():
                inspect(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                inspect(child, f"{path}[{index}]")
    inspect(record)
    for error in sorted(validator.iter_errors(record), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        messages.append(f"{location}: {error.message}")
    return messages


def validate_jsonl(schema_path: Path, jsonl_path: Path) -> ValidationSummary:
    total = 0
    valid = 0
    messages: list[str] = []
    for line_number, raw_line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        total += 1
        try:
            record = json.loads(
                raw_line,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-standard numeric constant {value}")
                ),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            messages.append(f"line {line_number}: invalid JSON: {exc}")
            continue
        errors = validate_record(schema_path, record)
        if errors:
            messages.append(f"line {line_number}: " + " | ".join(errors))
        else:
            valid += 1
    return ValidationSummary(total=total, valid=valid, invalid=total - valid, errors=tuple(messages))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--jsonl", required=True, type=Path)
    args = parser.parse_args()
    summary = validate_jsonl(args.schema, args.jsonl)
    print(json.dumps(summary.__dict__, ensure_ascii=False, indent=2))
    return 0 if summary.invalid == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
