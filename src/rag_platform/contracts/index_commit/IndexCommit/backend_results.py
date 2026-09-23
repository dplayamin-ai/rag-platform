"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Status(StrEnum):
    """
    바이블 §5.4 backend_results[].status 인라인 열거({Type}.{path} 등재 규칙 §5.7). ok=쓰기 성공·유지, failed=이 백엔드의 쓰기 또는 보상 실패, compensated=보상(삭제·복원) 완료
    """

    ok = "ok"
    failed = "failed"
    compensated = "compensated"
