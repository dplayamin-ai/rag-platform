"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Store(StrEnum):
    """
    레이트리밋 카운터 저장소 인라인 열거(E3). memory는 orchestrator=local 전용
    """

    valkey = "valkey"
    memory = "memory"


class FailMode(StrEnum):
    """
    저장소 불가 시 동작 인라인 열거(§7.2: 운영 closed)
    """

    open = "open"
    closed = "closed"
