"""Deterministic logical D0-SMOKE fixture for pipeline integration tests."""

from __future__ import annotations

import hashlib
from typing import Any


FAKE_CASES = [
    ("A", "audio", ["M1"], ["O1"], "voice_clone_or_conversion", "speaker.full"),
    ("V", "video", ["M2"], ["O1"], "identity_replacement", "face.full.segment"),
    ("I", "image", ["M3"], ["O2"], "object_editing", "object.local"),
    ("T", "text", ["M4"], ["O4"], "text_editing", "text.span"),
    ("M", "multimodal", ["M5"], ["O1", "O4"], "multimodal_joint", "mixed.cross_modal"),
    ("V", "video", ["M2"], ["O3"], "scene_generation", "scene.full"),
]


def _digest(sample_id: str) -> str:
    return hashlib.sha256(f"logical-d0-smoke:{sample_id}".encode()).hexdigest()


def _common(sample_id: str, group_id: str, media_type: str) -> dict[str, Any]:
    duration = None if media_type in {"image", "text"} else 4.0
    return {
        "sample_id": sample_id,
        "group_id": group_id,
        "source_id": f"SRC-D0-{group_id.removeprefix('GRP-')}",
        "file_path": f"synthetic://d0-smoke/{sample_id}",
        "sha256": _digest(sample_id),
        "media_type": media_type,
        "duration_sec": duration,
        "partition": "D0",
        "license_status": "internal_logical_fixture",
        "access_class": "internal",
        "annotation_version": "1.0.0",
        "review_status": "adjudicated",
        "exclusion_status": "included",
        "exclusion_reason": None,
        "schema_version": "1.0.0",
    }


def build_d0_smoke_samples() -> list[dict[str, Any]]:
    """Return six paired REAL/FAKE logical records; no media bytes are implied."""

    records: list[dict[str, Any]] = []
    for index, (prefix, media_type, modalities, objects, method, scope_id) in enumerate(
        FAKE_CASES, start=1
    ):
        group_id = f"GRP-{index:06d}"
        real_id = f"DFSTD-{prefix}-0{index:05d}"
        fake_id = f"DFSTD-{prefix}-1{index:05d}"
        real = {
            **_common(real_id, group_id, media_type),
            "parent_sample_id": None,
            "source_type": "SRC-CTL",
            "label_state": "REAL",
            "fake_modalities": [],
            "fake_objects": [],
        }
        fake = {
            **_common(fake_id, group_id, media_type),
            "parent_sample_id": real_id,
            "source_type": "SRC-GEN",
            "label_state": "FAKE",
            "fake_modalities": modalities,
            "fake_objects": objects,
            "fake_method": f"d0_smoke_{method}",
            "method_family": method,
            "scope_id": scope_id,
            "granularity": "full_generation" if method in {"scene_generation", "multimodal_joint"} else "object",
        }
        records.extend((real, fake))
    return records
