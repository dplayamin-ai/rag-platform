"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """
    바이블 §5.6 backends[].role 인라인 열거({Type}.{path} 등재 규칙 §5.7). profile.schema.json 의 Profile.ingest.index.backends.role 과 값 집합이 같다(CI 동치 대조)
    """

    vector = "vector"
    lexical = "lexical"
    graph = "graph"
