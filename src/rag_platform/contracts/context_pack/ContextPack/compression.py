"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Granularity(StrEnum):
    """
    인라인 열거. sentence는 segments 보존(오프셋 재계산), token은 text_format=plain 강제 + segments 전면 재계산
    """

    sentence = "sentence"
    token = "token"
