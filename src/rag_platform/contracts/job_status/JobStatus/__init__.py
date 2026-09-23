"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class FromStage(StrEnum):
    """
    바이블 §14 reprocess.from_stage 값
    """

    parse = "parse"
    normalize = "normalize"
    chunk = "chunk"
    recount = "recount"
    enrich = "enrich"
    embed = "embed"
    index = "index"
