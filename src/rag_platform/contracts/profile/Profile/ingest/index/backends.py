"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """
    백엔드 역할 인라인 열거({Type}.{path} 등재 규칙 §5.7). collection-spec 의 CollectionSpec.backends.role 과 값 집합이 같다. commit.flip_order[] 항목도 이 역할 값이다
    """

    vector = "vector"
    lexical = "lexical"
    graph = "graph"
