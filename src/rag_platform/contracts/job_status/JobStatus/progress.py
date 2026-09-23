"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Unit(StrEnum):
    """
    바이블 §5.6 인라인 열거(§5.7 {Type}.{path} 규칙)
    """

    stage = "stage"
    page = "page"
    chunk = "chunk"
    document = "document"
