"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class ChangeKind(StrEnum):
    """
    인라인 열거(§5.7 {Type}.{path} 규칙; 미해결 이슈 8). profile = 프로파일 지정·변경·재색인 alias 교체, dictionary = 사용자 사전 변경(dictionary_hash), policy = 컬렉션 정책(TieringPolicy·EgressPolicy 등) 변경
    """

    profile = "profile"
    dictionary = "dictionary"
    policy = "policy"
