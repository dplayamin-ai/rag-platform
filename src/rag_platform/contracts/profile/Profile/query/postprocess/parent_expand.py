"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class TextStore(StrEnum):
    """
    부모 텍스트 저장 방식(바이블 §13.2) 인라인 열거
    """

    artifact_store = "artifact_store"
    vector_payload = "vector_payload"
