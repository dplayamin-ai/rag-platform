"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    """
    대상 LLM 토크나이저 공급자(tokenizer_id 접두, §6.1). count_method=exact_api 는 anthropic·gemini만
    """

    anthropic = "anthropic"
    gemini = "gemini"
    hf = "hf"
    tiktoken = "tiktoken"
