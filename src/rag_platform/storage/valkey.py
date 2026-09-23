"""`KeyValueCache` protocol (Valkey-backed in production; bible §13.4 key conventions).

Canon: design bible §13.4 (Valkey key table: ``qemb:``, ``plan:``, ``tok:``, ``ptxt:``, ``rr:``,
``idem:``, ``aclrev:``, ``rl:``, ``cursor:``, ``groups:``, ``collspec:``); §11.1 (`lite` uses a
single Valkey instance); ADR-0011 (Valkey replaces Redis as the default KV, BSD-3).

Only the protocol lives here. The real client (``valkey-py`` over the Valkey wire protocol) is a
future work package; ``rag_platform.testing.doubles.InMemoryKV`` is the in-memory conformance
double used to unit-test callers against this protocol today.

# DEFERRED: a real Valkey-backed implementation of `KeyValueCache`, verified against a live Valkey
# server, is `needs_docker` (phase-6 plan §8 tier 2) and is not part of this work package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["KeyValueCache"]


@runtime_checkable
class KeyValueCache(Protocol):
    """Bible §13.4 key-value cache surface used by `plan`, `embed`, `rerank`, `pack`, `aclrev`, ..."""

    async def get(self, key: str) -> bytes | None:
        """Return the value at `key`, or `None` if absent or expired."""
        ...

    async def mget(self, keys: Sequence[str]) -> list[bytes | None]:
        """Return one value per key in `keys`, in the same order (`None` for misses)."""
        ...

    async def set(self, key: str, value: bytes, *, ttl_s: int) -> None:
        """Set `key` to `value`, expiring after `ttl_s` seconds."""
        ...

    async def delete(self, *keys: str) -> None:
        """Remove every key in `keys` (missing keys are not an error)."""
        ...
