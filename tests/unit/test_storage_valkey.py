"""Unit tests for the `rag_platform.storage.valkey` `KeyValueCache` protocol (bible §13.4)."""

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
