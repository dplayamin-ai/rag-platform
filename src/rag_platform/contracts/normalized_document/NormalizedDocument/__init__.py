"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class GenreSource(StrEnum):
    """
    request_hint = IngestRequest.metadata.genre, parser = ParsedDocument.metadata.genre, heuristic = normalize 규칙
    """

    request_hint = "request_hint"
    parser = "parser"
    heuristic = "heuristic"
