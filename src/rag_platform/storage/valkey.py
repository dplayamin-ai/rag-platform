"""`KeyValueCache` 프로토콜(운영에서는 Valkey 백엔드; 바이블 §13.4 키 규약).

역할: `plan`/`embed`/`rerank`/`pack`/`aclrev` 등이 쓰는 캐시 표면(`get`/`mget`/`set`/`delete`)을
프로토콜로만 정의한다.
설계 근거: 바이블 §13.4(Valkey 키 표 — `qemb:`/`plan:`/`tok:`/`ptxt:`/`rr:`/`idem:`/`aclrev:`/`rl:`/
`cursor:`/`groups:`/`collspec:`), §11.1(`lite`는 단일 Valkey 인스턴스); ADR-0011(Valkey가 기본 KV로
Redis를 대체, BSD-3).
구성: `KeyValueCache` — `get`/`mget`/`set`/`delete` 4개 비동기 메서드로 이뤄진 프로토콜뿐이다.
불변식: 여기 있는 것은 프로토콜뿐이다 — 실제 Valkey 클라이언트(`valkey-py`)는 아직 없고,
`rag_platform.testing.doubles.InMemoryKV`가 오늘의 정합성 더블이다.
검증 계층: 1층(프로토콜 자체는 여기서 검증 — tests/unit/test_storage_valkey.py). DEFERRED: 실제
Valkey 서버로 검증하는 구현체는 needs_docker(phase-6 계획 §8 tier 2)이며 이 작업 범위 밖이다.
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
