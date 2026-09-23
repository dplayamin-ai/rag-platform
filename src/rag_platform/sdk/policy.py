"""`StagePolicy` 모델과 적용 헬퍼(백오프, 재시도 판단).

역할: 프로파일이 선언하는 단계별 정책(큐, 타임아웃, 재시도 횟수, 백오프, 격리)을 파싱하고,
`should_retry`/`compute_backoff_delay`로 실행기가 재시도 여부와 지연 시간을 판단하게 한다.
설계 근거: 바이블 §4.4(`StagePolicy` 표, `standard`), §5.3(`StagePolicy` 필드), §11.3(재시도 분류);
`schemas/stage-policy.schema.json`.
구성: `parse_duration(value)` — 바이블 §5.3 `Duration`(짧은 표기/ISO 8601) 파싱; `BackoffPolicy` —
`backoff` 하위 필드; `StagePolicy`(+`from_mapping`) — 스키마 모양의 매핑을 그대로 파싱;
`compute_backoff_delay` — 지수 백오프; `should_retry` — 정책의 `non_retryable_error_codes`가 카탈로그
기본 분류(`classify_error`)보다 항상 우선한다.
불변식: 아직 생성되지 않은 계약 `StagePolicy` Pydantic 모델 대신 쓰는 평범한 dataclass이며,
`from_mapping`은 프로파일 dict와 향후 생성 모델 양쪽을 같은 모양으로 받아들인다.
검증 계층: 1층(여기서 검증) — tests/unit/test_sdk_policy.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from rag_platform.sdk.stage import RetryClass, classify_error

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rag_platform.sdk.stage import StageError

__all__ = ["BackoffPolicy", "StagePolicy", "compute_backoff_delay", "parse_duration", "should_retry"]

# Bible §5.3 Duration: either ISO 8601 (`PT5M`) or the bible §4.4/§5.3 short form (`5m`, `30s`, `24h`).
_SHORT_DURATION = re.compile(r"^(\d+)(ms|s|m|h|d)$")
_ISO8601_DURATION = re.compile(
    r"^P(?!$)(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?"
    r"(?:T(?=\d)(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$"
)
_SHORT_UNIT_SECONDS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}


def parse_duration(value: str) -> timedelta:
    """Parse a bible §5.3 ``Duration`` string (short form or ISO 8601) into a `timedelta`."""
    short = _SHORT_DURATION.match(value)
    if short:
        amount, unit = short.groups()
        return timedelta(seconds=float(amount) * _SHORT_UNIT_SECONDS[unit])
    iso = _ISO8601_DURATION.match(value)
    if iso:
        years, months, weeks, days, hours, minutes, seconds = (float(g) if g else 0.0 for g in iso.groups())
        # Calendar years/months are approximated as 365/30 days; StagePolicy durations never use them.
        total_days = years * 365 + months * 30 + weeks * 7 + days
        return timedelta(days=total_days, hours=hours, minutes=minutes, seconds=seconds)
    msg = f"not a valid Duration (bible §5.3): {value!r}"
    raise ValueError(msg)


@dataclass(frozen=True)
class BackoffPolicy:
    """Bible §5.3 `StagePolicy.backoff`; default ``{1s, 5m, 2.0}``."""

    initial: timedelta = timedelta(seconds=1)
    max: timedelta = timedelta(minutes=5)
    coefficient: float = 2.0

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> BackoffPolicy:
        """Parse a `StagePolicy.backoff` mapping, defaulting absent fields to the bible §5.3 values."""
        if data is None:
            return cls()
        return cls(
            initial=parse_duration(data["initial"]) if "initial" in data else cls.initial,
            max=parse_duration(data["max"]) if "max" in data else cls.max,
            coefficient=float(data.get("coefficient", cls.coefficient)),
        )


@dataclass(frozen=True)
class StagePolicy:
    """Bible §5.3 `StagePolicy`: one row of the §4.4 table applied to a single stage call."""

    task_queue: str
    start_to_close: timedelta
    heartbeat: timedelta | None
    max_attempts: int
    resumable: bool
    non_retryable_error_codes: tuple[str, ...] = field(default_factory=tuple)
    backoff: BackoffPolicy = field(default_factory=BackoffPolicy)
    isolation: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> StagePolicy:
        """Parse the `stage-policy.schema.json` shape (durations as short-form strings)."""
        heartbeat = data.get("heartbeat")
        return cls(
            task_queue=data["task_queue"],
            start_to_close=parse_duration(data["start_to_close"]),
            heartbeat=parse_duration(heartbeat) if heartbeat else None,
            max_attempts=int(data["max_attempts"]),
            resumable=bool(data["resumable"]),
            non_retryable_error_codes=tuple(data.get("non_retryable_error_codes", ())),
            backoff=BackoffPolicy.from_mapping(data.get("backoff")),
            isolation=data.get("isolation"),
        )


def compute_backoff_delay(policy: StagePolicy, attempt: int) -> timedelta:
    """Exponential backoff for a 1-based `attempt` number, capped at `policy.backoff.max`."""
    if attempt < 1:
        msg = f"attempt must be >= 1, got {attempt}"
        raise ValueError(msg)
    delay = policy.backoff.initial.total_seconds() * (policy.backoff.coefficient ** (attempt - 1))
    capped = min(delay, policy.backoff.max.total_seconds())
    return timedelta(seconds=capped)


def should_retry(policy: StagePolicy, attempt: int, error: StageError) -> bool:
    """Bible §11.3: retry only `RetryClass.RETRYABLE` failures, and only within `max_attempts`.

    `policy.non_retryable_error_codes` (the profile's per-stage override, bible §4.4) always wins
    over the SDK's default catalog classification (`classify_error`), even if the catalog default
    would otherwise call the code retryable.
    """
    if error.code in policy.non_retryable_error_codes:
        return False
    if classify_error(error.code) is not RetryClass.RETRYABLE:
        return False
    return attempt < policy.max_attempts
