"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class StructureSource(StrEnum):
    native = "native"
    tableformer = "tableformer"
    line_based = "line_based"
    render_fallback = "render_fallback"
