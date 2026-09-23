"""`InMemoryKV` — `storage.valkey.KeyValueCache` 대역(double). 딕셔너리 기반, 실제 Valkey 서버 없음.

역할: 실 Valkey 서버 없이 `get`/`mget`/`set`/`delete` 호출부를 검증하는 키-값 캐시 대역.
설계 근거: `storage.valkey.KeyValueCache` 포트의 conformance 대역 — 실 서버 검증은 phase-6
계획 §8 tier 2로 이관.

구성: `InMemoryKV` — TTL 만료가 있는 딕셔너리 캐시(`get`, `mget`, `set`, `delete`).

불변식·주의: TTL 만료 판정은 `time.monotonic()` 기준 근사치이며 시스템 시각(달력·시계 값)을
읽지 않는다 — 실 Valkey 서버의 TTL 의미와 정확히 일치하지 않을 수 있다.
검증 계층: 1층(대역 자체는 여기서 검증) — `tests/unit/test_testing_doubles.py`.
DEFERRED: 실 Valkey 서버(Valkey/Redis 와이어 프로토콜) 대상 검증은 `needs_docker`(phase-6
계획 §8 tier 2) — `docs/12-appendix/09-deferred-verification-ledger.md`에서 추적.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["InMemoryKV"]


class InMemoryKV:
    """`KeyValueCache` double with approximate TTL expiry (`time.monotonic`, not wall-clock)."""

    def __init__(self) -> None:
        """Start with an empty cache."""
        self._values: dict[str, bytes] = {}
        self._expires_at: dict[str, float] = {}

    def _expired(self, key: str) -> bool:
        deadline = self._expires_at.get(key)
        return deadline is not None and deadline <= time.monotonic()

    def _evict_if_expired(self, key: str) -> None:
        if self._expired(key):
            self._values.pop(key, None)
            self._expires_at.pop(key, None)

    async def get(self, key: str) -> bytes | None:
        """Return the value at `key`, or `None` if absent or expired."""
        self._evict_if_expired(key)
        return self._values.get(key)

    async def mget(self, keys: Sequence[str]) -> list[bytes | None]:
        """Return one value per key in `keys`, in the same order (`None` for misses)."""
        return [await self.get(key) for key in keys]

    async def set(self, key: str, value: bytes, *, ttl_s: int) -> None:
        """Set `key` to `value`, expiring `ttl_s` seconds from now (`time.monotonic`)."""
        self._values[key] = value
        self._expires_at[key] = time.monotonic() + ttl_s

    async def delete(self, *keys: str) -> None:
        """Remove every key in `keys` (missing keys are not an error)."""
        for key in keys:
            self._values.pop(key, None)
            self._expires_at.pop(key, None)
