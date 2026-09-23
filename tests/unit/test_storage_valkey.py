"""`rag_platform.storage.valkey`의 `KeyValueCache` 프로토콜 테스트 — `InMemoryKV` 이중체가 계약을 만족하는지 검증한다.

설계 근거: 바이블 §13.4(Valkey 키 명명 — `qemb:{space}:{hash}` 등, 테넌트 스코프 키는 `{tenant}` 접두 필수).

구성: `InMemoryKV`가 `KeyValueCache` 프로토콜을 만족함(불완전 구현은 거부됨) 확인, `get`/`set`(TTL 포함)/
`delete` 왕복, `mget`이 순서를 보존하고 미스는 `None`으로 채움을 확인.

검증 계층: 1층(여기서 검증) — 실제 Valkey 백엔드 연동은 `needs_docker` DEFERRED.
"""

from __future__ import annotations

from rag_platform.storage.valkey import KeyValueCache
from rag_platform.testing.doubles.in_memory_kv import InMemoryKV


def test_in_memory_kv_satisfies_key_value_cache_protocol() -> None:
    assert isinstance(InMemoryKV(), KeyValueCache)


def test_key_value_cache_protocol_rejects_incomplete_implementation() -> None:
    class _Incomplete:
        async def get(self, key: str) -> bytes | None:
            return None

    assert not isinstance(_Incomplete(), KeyValueCache)


async def test_in_memory_kv_get_set_delete_round_trip() -> None:
    kv = InMemoryKV()
    assert await kv.get("qemb:space:abc") is None
    await kv.set("qemb:space:abc", b"vector-bytes", ttl_s=60)
    assert await kv.get("qemb:space:abc") == b"vector-bytes"
    await kv.delete("qemb:space:abc")
    assert await kv.get("qemb:space:abc") is None


async def test_in_memory_kv_mget_preserves_order_and_misses() -> None:
    kv = InMemoryKV()
    await kv.set("a", b"1", ttl_s=60)
    await kv.set("c", b"3", ttl_s=60)
    assert await kv.mget(["a", "b", "c"]) == [b"1", None, b"3"]
