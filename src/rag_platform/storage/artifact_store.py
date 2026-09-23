"""`ArtifactStore` 프로토콜 + `FileArtifactStore`(`file://`) + `InMemoryArtifactStore`.

역할: 봉투 없는(envelope-free) 원본·파생 바이트와 계약 아티팩트를 저장하는 비동기 바이트 스토어
표면을 정의하고, 파일시스템·인메모리 두 구현을 제공한다.
설계 근거: 바이블 §13.3(오브젝트 키 규약, "이미 있는 경로는 절대 덮어쓰지 않는다"), §6.2
(`content_hash = blake3_hex(원본 바이트)`, 도메인 라벨 없음); ADR-0037(캐시 클래스: `stage_key` 키드
계약 아티팩트 vs 콘텐츠 해시 키드 봉투 없는 바이트).
구성: `ArtifactRef` — 바이블 §5.3 계약 필드를 그대로 미러링하는 dataclass(생성 모델 대체);
`ArtifactStore` — `put_source`/`put_derived`/`put_artifact`/`get_bytes`/`exists`/`lookup_stage_key`
프로토콜; `InMemoryArtifactStore`/`FileArtifactStore` — 각각 dict·`file://` 루트 구현(후자는
`compress=True`일 때 선택적 `zstandard`로 압축).
불변식: `put_*`는 콘텐츠 주소화 키에 대해 "없으면 쓰기"만 하는 멱등 연산이다(기존 객체를 덮어쓰지
않는다). `ArtifactStore`는 `Stage.run`에 직접 노출되지 않는다 — 단계는 `sdk.context.DerivedArtifacts`
를 대신 본다.
검증 계층: 1층(여기서 검증) — tests/unit/test_storage_artifact_store.py.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from rag_platform.sdk.hashing import blake3_hex
from rag_platform.storage.keys import artifact_key, artifact_key_by_hash, derived_key, kebab_case, source_key

__all__ = ["ArtifactRef", "ArtifactStore", "FileArtifactStore", "InMemoryArtifactStore"]


@dataclass(frozen=True)
class ArtifactRef:
    """Bible §5.3 `ArtifactRef` fields (stand-in for the not-yet-generated contract model)."""

    uri: str
    blake3: str
    media_type: str
    size_bytes: int
    schema_type: str | None = None
    schema_version: str | None = None
    stage_key: str | None = None


@runtime_checkable
class ArtifactStore(Protocol):
    """Bible §13.3 key convention behind a small async byte store surface.

    Exposed to the shell/orchestrator and `storage`/`retrieval.pack.chunk_text_store` only — never
    directly to a `Stage.run` implementation, which sees `sdk.context.DerivedArtifacts` instead
    (02-architecture/02-component-architecture.md §2.3).
    """

    async def put_source(self, data: bytes, *, tenant_id: str, media_type: str) -> ArtifactRef:
        """Store envelope-free original bytes at `sources/{blake3}` (bible §13.3)."""
        ...

    async def put_derived(self, data: bytes, *, tenant_id: str, kind: str, ext: str, media_type: str) -> ArtifactRef:
        """Store an envelope-free derived byte object at `derived/{kind}/{blake3}.{ext}`."""
        ...

    async def put_artifact(
        self,
        data: bytes,
        *,
        tenant_id: str,
        schema_type: str,
        media_type: str,
        stage_key: str | None = None,
    ) -> ArtifactRef:
        """Store a stage output; `stage_key`-addressed if cacheable, byte-hash-addressed otherwise."""
        ...

    async def get_bytes(self, ref: ArtifactRef) -> bytes:
        """Return the bytes `ref` points at."""
        ...

    async def exists(self, ref: ArtifactRef) -> bool:
        """Return whether an object exists at `ref.uri`."""
        ...

    async def lookup_stage_key(self, tenant_id: str, schema_type: str, stage_key: str) -> ArtifactRef | None:
        """Return the cached `ArtifactRef` for `stage_key`, or `None` on a cache miss (ADR-0037)."""
        ...


class InMemoryArtifactStore:
    """`ArtifactStore` backed by a dict; conformance/unit-test double, no filesystem."""

    def __init__(self) -> None:
        """Start with an empty object store."""
        self._objects: dict[str, bytes] = {}

    async def put_source(self, data: bytes, *, tenant_id: str, media_type: str) -> ArtifactRef:
        """Store envelope-free original bytes, content-addressed by `blake3`."""
        digest = blake3_hex(data)
        key = source_key(tenant_id, digest)
        self._objects.setdefault(key, data)  # content-addressed: never overwrite (bible §13.3)
        return ArtifactRef(uri=f"mem://{key}", blake3=digest, media_type=media_type, size_bytes=len(data))

    async def put_derived(self, data: bytes, *, tenant_id: str, kind: str, ext: str, media_type: str) -> ArtifactRef:
        """Store an envelope-free derived byte object, content-addressed by `blake3`."""
        digest = blake3_hex(data)
        key = derived_key(tenant_id, kind, digest, ext)
        self._objects.setdefault(key, data)
        return ArtifactRef(uri=f"mem://{key}", blake3=digest, media_type=media_type, size_bytes=len(data))

    async def put_artifact(
        self,
        data: bytes,
        *,
        tenant_id: str,
        schema_type: str,
        media_type: str,
        stage_key: str | None = None,
    ) -> ArtifactRef:
        """Store a stage output; `stage_key`-addressed if cacheable, byte-hash-addressed otherwise."""
        digest = blake3_hex(data)
        key = (
            artifact_key(tenant_id, schema_type, stage_key)
            if stage_key
            else artifact_key_by_hash(tenant_id, schema_type, digest)
        )
        self._objects.setdefault(key, data)
        return ArtifactRef(
            uri=f"mem://{key}",
            blake3=digest,
            media_type=media_type,
            size_bytes=len(data),
            schema_type=schema_type,
            stage_key=stage_key,
        )

    async def get_bytes(self, ref: ArtifactRef) -> bytes:
        """Return the bytes `ref` points at, or raise `FileNotFoundError`."""
        key = ref.uri.removeprefix("mem://")
        try:
            return self._objects[key]
        except KeyError:
            raise FileNotFoundError(ref.uri) from None

    async def exists(self, ref: ArtifactRef) -> bool:
        """Return whether an object exists at `ref.uri`."""
        return ref.uri.removeprefix("mem://") in self._objects

    async def lookup_stage_key(self, tenant_id: str, schema_type: str, stage_key: str) -> ArtifactRef | None:
        """Return the cached `ArtifactRef` for `stage_key`, or `None` on a cache miss (ADR-0037)."""
        key = artifact_key(tenant_id, schema_type, stage_key)
        data = self._objects.get(key)
        if data is None:
            return None
        return ArtifactRef(
            uri=f"mem://{key}",
            blake3=blake3_hex(data),
            media_type=f"application/vnd.rag.{kebab_case(schema_type)}+json",
            size_bytes=len(data),
            schema_type=schema_type,
            stage_key=stage_key,
        )


class FileArtifactStore:
    """`ArtifactStore` backed by a `file://` root directory (bible §13.3).

    ``compress=True`` stores objects zstd-compressed (`.zst` suffix). ``zstandard`` is not a core
    dependency (pyproject.toml keeps the minimal Phase 6A runtime set); requesting compression
    without it installed raises `ImportError` at construction time, not silently at first write.
    Blocking filesystem calls run in a worker thread (`asyncio.to_thread`) so this store does not
    stall the event loop.
    """

    def __init__(self, root: Path, *, compress: bool = False) -> None:
        """Build a store rooted at `root`; `compress=True` requires the optional `zstandard` package."""
        self._root = root
        self._compress = compress
        self._zstd = None
        if compress:
            try:
                import zstandard  # type: ignore[import-not-found] # noqa: PLC0415 — optional
            except ImportError as exc:  # pragma: no cover - exercised only when zstandard is absent
                msg = "FileArtifactStore(compress=True) requires the optional 'zstandard' package"
                raise ImportError(msg) from exc
            self._zstd = zstandard

    def _path_for(self, key: str) -> Path:
        suffix = ".zst" if self._compress else ""
        return self._root / f"{key}{suffix}"

    def _encode(self, data: bytes) -> bytes:
        if self._zstd is None:
            return data
        return bytes(self._zstd.ZstdCompressor().compress(data))

    def _decode(self, data: bytes) -> bytes:
        if self._zstd is None:
            return data
        return bytes(self._zstd.ZstdDecompressor().decompress(data))

    def _write_if_absent_sync(self, path: Path, data: bytes) -> None:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self._encode(data))

    async def _write_if_absent(self, key: str, data: bytes) -> str:
        path = self._path_for(key)
        await asyncio.to_thread(self._write_if_absent_sync, path, data)
        return f"file://{path.as_posix()}"

    def _read_if_present_sync(self, path: Path) -> bytes | None:
        if not path.exists():
            return None
        return self._decode(path.read_bytes())

    async def put_source(self, data: bytes, *, tenant_id: str, media_type: str) -> ArtifactRef:
        """Store envelope-free original bytes, content-addressed by `blake3`."""
        digest = blake3_hex(data)
        uri = await self._write_if_absent(source_key(tenant_id, digest), data)
        return ArtifactRef(uri=uri, blake3=digest, media_type=media_type, size_bytes=len(data))

    async def put_derived(self, data: bytes, *, tenant_id: str, kind: str, ext: str, media_type: str) -> ArtifactRef:
        """Store an envelope-free derived byte object, content-addressed by `blake3`."""
        digest = blake3_hex(data)
        uri = await self._write_if_absent(derived_key(tenant_id, kind, digest, ext), data)
        return ArtifactRef(uri=uri, blake3=digest, media_type=media_type, size_bytes=len(data))

    async def put_artifact(
        self,
        data: bytes,
        *,
        tenant_id: str,
        schema_type: str,
        media_type: str,
        stage_key: str | None = None,
    ) -> ArtifactRef:
        """Store a stage output; `stage_key`-addressed if cacheable, byte-hash-addressed otherwise."""
        digest = blake3_hex(data)
        key = (
            artifact_key(tenant_id, schema_type, stage_key)
            if stage_key
            else artifact_key_by_hash(tenant_id, schema_type, digest)
        )
        uri = await self._write_if_absent(key, data)
        return ArtifactRef(
            uri=uri,
            blake3=digest,
            media_type=media_type,
            size_bytes=len(data),
            schema_type=schema_type,
            stage_key=stage_key,
        )

    async def get_bytes(self, ref: ArtifactRef) -> bytes:
        """Return the bytes `ref` points at."""
        path = Path(ref.uri.removeprefix("file://"))
        data = await asyncio.to_thread(path.read_bytes)
        return self._decode(data)

    async def exists(self, ref: ArtifactRef) -> bool:
        """Return whether an object exists at `ref.uri`."""
        path = Path(ref.uri.removeprefix("file://"))
        return await asyncio.to_thread(path.exists)

    async def lookup_stage_key(self, tenant_id: str, schema_type: str, stage_key: str) -> ArtifactRef | None:
        """Return the cached `ArtifactRef` for `stage_key`, or `None` on a cache miss (ADR-0037)."""
        path = self._path_for(artifact_key(tenant_id, schema_type, stage_key))
        data = await asyncio.to_thread(self._read_if_present_sync, path)
        if data is None:
            return None
        return ArtifactRef(
            uri=f"file://{path.as_posix()}",
            blake3=blake3_hex(data),
            media_type=f"application/vnd.rag.{kebab_case(schema_type)}+json",
            size_bytes=len(data),
            schema_type=schema_type,
            stage_key=stage_key,
        )
