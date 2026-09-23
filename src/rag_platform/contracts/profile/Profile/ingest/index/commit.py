"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Strategy(StrEnum):
    """
    세대 사가 전략 인라인 열거(ADR-0026). v1은 insert_then_delete 하나
    """

    insert_then_delete = "insert_then_delete"
