"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Orchestrator(StrEnum):
    """
    바이블 §5.6 runtime.orchestrator 인라인 열거. local = LocalRunner(개발·CI·하네스)
    """

    local = "local"
    temporal = "temporal"
