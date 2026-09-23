"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    """
    인라인 열거(바이블 §5.5 QueryRequest.target_model.provider·09 QueryPlan.pack.tokenizer.provider와 같은 값 집합). tokenizer.name 접두 대응: anthropic→anthropic:, openai→tiktoken:, google→gemini:, local→hf:
    """

    anthropic = "anthropic"
    openai = "openai"
    google = "google"
    local = "local"
