"""`InMemoryKV`: `storage.valkey.KeyValueCache` double, dict-backed, no Valkey server.

# DEFERRED: verify against a real Valkey server over the Valkey/Redis wire protocol —
# `needs_docker` (phase-6 plan §8 tier 2). Track in
# `docs/12-appendix/09-deferred-verification-ledger.md`.
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
