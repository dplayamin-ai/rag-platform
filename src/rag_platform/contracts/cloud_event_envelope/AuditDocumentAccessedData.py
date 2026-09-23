"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class View(StrEnum):
    """
    GET /v1/documents/{document_id}, /content?view=parsed|normalized|chunks, /commits, MCP get_document
    """

    metadata = "metadata"
    parsed = "parsed"
    normalized = "normalized"
    chunks = "chunks"
    commits = "commits"
