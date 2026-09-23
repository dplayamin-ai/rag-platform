"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Correction(StrEnum):
    """
    다중 비교 보정 인라인 열거(D-12: holm)
    """

    holm = "holm"
    bonferroni = "bonferroni"
    none = "none"
