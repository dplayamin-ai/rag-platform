"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    """
    바이블 §5.5 pack.tokenizer.provider 인라인 열거(= QueryRequest.target_model.provider 값 집합)
    """

    anthropic = "anthropic"
    openai = "openai"
    google = "google"
    local = "local"
