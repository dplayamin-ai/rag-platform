"""`rag_platform.storage.artifact_store` 단위 테스트 — `InMemoryArtifactStore`/`FileArtifactStore`의 키 규약과
`ArtifactStore` 프로토콜 준수를 검증한다.

설계 근거: 바이블 §13.3(오브젝트 키 규약 — 원본은 콘텐츠 해시, `stage_key` 있는 스테이지 산출물은 `stage_key`
경로, `fetch`/`index`는 바이트 해시 경로, 이미 점유된 `stage_key` 경로는 덮어쓰지 않음), `ADR-0037`(캐시 스코프).

구성:
- `put_source`/`put_artifact`/`lookup_stage_key` — 콘텐츠 주소화, `stage_key` 유무에 따른 경로 분기,
  캐시 조회가 첫 쓰기 이후에만 적중함을 확인.
- `FileArtifactStore` — 실제 파일시스템 왕복, 점유된 `stage_key` 경로 불변, `compress=True`인데
  `zstandard`가 없으면 `ImportError`.
- `InMemoryArtifactStore`/`FileArtifactStore` 모두 `ArtifactStore` 프로토콜을 만족함을 확인.

불변식: 이미 점유된 `stage_key` 경로는 어떤 백엔드에서도 덮어쓰지 않는다(§13.3).
검증 계층: 1층(여기서 검증) — 실제 오브젝트 스토리지 백엔드는 `needs_docker` DEFERRED.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rag_platform.storage.artifact_store import ArtifactStore, FileArtifactStore, InMemoryArtifactStore

if TYPE_CHECKING:
    from pathlib import Path


async def test_in_memory_store_put_source_is_content_addressed() -> None:
    store = InMemoryArtifactStore()
    ref1 = await store.put_source(b"hello", tenant_id="t1", media_type="text/plain")
    ref2 = await store.put_source(b"hello", tenant_id="t1", media_type="text/plain")
    assert ref1.blake3 == ref2.blake3
    assert ref1.uri == ref2.uri  # same bytes -> same object key (bible §13.3)


async def test_in_memory_store_put_artifact_uses_stage_key_when_given() -> None:
    store = InMemoryArtifactStore()
    stage_key = "cd" * 32
    ref = await store.put_artifact(
        b'{"a": 1}', tenant_id="t1", schema_type="ParsedDocument", media_type="application/json", stage_key=stage_key
    )
    assert ref.stage_key == stage_key
    assert "parsed-document" in ref.uri
    assert await store.exists(ref)
    assert await store.get_bytes(ref) == b'{"a": 1}'


async def test_in_memory_store_put_artifact_falls_back_to_byte_hash_key() -> None:
    store = InMemoryArtifactStore()
    ref = await store.put_artifact(b"raw", tenant_id="t1", schema_type="SourceDocument", media_type="application/pdf")
    assert ref.stage_key is None
    assert ref.blake3 in ref.uri  # cache-exempt path is byte-hash keyed (bible §13.3, ADR-0037)


async def test_in_memory_store_lookup_stage_key_hits_after_first_write() -> None:
    store = InMemoryArtifactStore()
    stage_key = "ef" * 32
    assert await store.lookup_stage_key("t1", "ChunkSet", stage_key) is None
    await store.put_artifact(
        b"chunks", tenant_id="t1", schema_type="ChunkSet", media_type="application/json", stage_key=stage_key
    )
    hit = await store.lookup_stage_key("t1", "ChunkSet", stage_key)
    assert hit is not None
    assert hit.stage_key == stage_key


async def test_file_store_round_trips_bytes(tmp_path: Path) -> None:
    store = FileArtifactStore(tmp_path)
    ref = await store.put_source(b"binary content", tenant_id="t1", media_type="application/octet-stream")
    assert await store.exists(ref)
    assert await store.get_bytes(ref) == b"binary content"
    assert (tmp_path / "tenants" / "t1" / "sources").is_dir()


async def test_file_store_never_overwrites_an_occupied_stage_key_path(tmp_path: Path) -> None:
    store = FileArtifactStore(tmp_path)
    stage_key = "12" * 32
    ref1 = await store.put_artifact(
        b"first", tenant_id="t1", schema_type="ChunkSet", media_type="application/json", stage_key=stage_key
    )
    ref2 = await store.put_artifact(
        b"second-different-bytes",
        tenant_id="t1",
        schema_type="ChunkSet",
        media_type="application/json",
        stage_key=stage_key,
    )
    assert ref1.uri == ref2.uri
    assert await store.get_bytes(ref2) == b"first"  # bible §13.3: an occupied stage_key path wins


def test_file_store_compress_without_zstandard_raises_import_error(tmp_path: Path) -> None:
    with pytest.raises(ImportError, match="zstandard"):
        FileArtifactStore(tmp_path, compress=True)


def test_in_memory_and_file_store_satisfy_artifact_store_protocol(tmp_path: Path) -> None:
    assert isinstance(InMemoryArtifactStore(), ArtifactStore)
    assert isinstance(FileArtifactStore(tmp_path), ArtifactStore)
