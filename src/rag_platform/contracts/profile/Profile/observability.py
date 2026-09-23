"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class ContentCapture(StrEnum):
    """
    트레이스 콘텍스트 캡처 모드 인라인 열거(OTel GenAI ContentCapturingMode 대응, 확인 필요 as of 2026-09). 모든 프로파일 기본 none(E13)
    """

    none = "none"
    span_only = "span_only"
    event_only = "event_only"
    span_and_event = "span_and_event"
