"""결정적 콘텐츠 주소화 키 파생(바이블 §6.2 `H()`; ADR-0004).

역할: `block_id`/`chunk_id`/`stage_key`/`record_id`/Qdrant `point_id`와 모든 `*_hash`/`fingerprint`가
거쳐야 하는 단일 해시 조합 함수 `hash_of`(및 라벨 없는 콘텐츠 해시 `blake3_hex`)를 제공한다.
설계 근거: 바이블 §6.2(`H(label, *parts)` 정의, 필드 구분자 U+001F); ADR-0004("단일 구현 린트" —
`blake3`를 직접 import하는 유일한 모듈, `pyproject.toml`의 전용 `TID251` 예외로 강제).
구성: `hash_of(label, *parts)` — `H()` 조합 해시; `blake3_hex(data)` — 라벨 없는 콘텐츠 해시
(`content_hash` 전용); `block_id`/`chunk_id`/`stage_key`/`record_id`/`point_id_for_record` — 바이블
§6.2 각 키 공식의 구체 구현.
불변식: 단계(stage)와 L0-L3 핫패스는 이 모듈의 `blake3` 의존성을 직접 import하지 않고
`rag_platform.sdk`가 재노출한 `hash_of`/`blake3_hex`만 호출한다(10-development/03 §10.2). `label`/
`part`에 U+001F가 있으면 `ValueError`.
검증 계층: 1층(여기서 검증) — ADR-0004 고정 벡터, tests/contracts/test_hash_vectors.py.
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from blake3 import blake3

#: Field separator between ``H()`` parts (bible §6.2): ASCII Unit Separator, U+001F.
_SEP = b"\x1f"

#: Qdrant point-id namespace (ADR-0004): ``uuid5(NAMESPACE_URL, "urn:rag:chunk")``.
NAMESPACE_RAG_CHUNK: UUID = uuid5(NAMESPACE_URL, "urn:rag:chunk")


def _check_no_separator(label: str, parts: tuple[str, ...]) -> None:
    """Reject a U+001F inside any ``H()`` input (bible §6.2; 00-contract-overview §7.1)."""
    if "\x1f" in label or any("\x1f" in part for part in parts):
        msg = "contract.violation: hash_of() label/part must not contain U+001F"
        raise ValueError(msg)


def hash_of(label: str, *parts: str) -> str:
    """Compute the bible §6.2 combination hash ``H(label, *parts)``.

    ``H(label, *parts) = blake3_hex(utf8(label) + 0x1F + 0x1F.join(utf8(part) for part in parts))``.
    ``label`` is the domain prefix that separates hash purposes (``"block"``, ``"chunk"``,
    ``"record"``, ``"stage"``, ...; bible §6.2's label table is the single source of valid
    labels). Callers are responsible for turning non-string inputs into the exact strings the
    combination expects (``str(n)`` for integers, ``""`` for an absent optional part, a
    caller-chosen deterministic join for a list of parts, and — where the composed value itself
    must be reproducible — bible §6.2's ``canonical_json`` for structured config).

    Args:
        label: Domain prefix distinguishing what the hash is for.
        *parts: The pre-stringified components to combine with ``label``.

    Returns:
        A 64-character lowercase hex BLAKE3 digest.

    Raises:
        ValueError: If ``label`` or any part contains U+001F, the same separator ``H()`` uses to
            join its inputs (which would make two different input tuples collide byte-for-byte).
    """
    _check_no_separator(label, parts)
    data = label.encode("utf-8") + _SEP + _SEP.join(part.encode("utf-8") for part in parts)
    return blake3(data).hexdigest()


def blake3_hex(data: bytes | str) -> str:
    """Compute the label-less content hash used only for ``content_hash`` (bible §6.2).

    Every other content-derived key goes through :func:`hash_of`; ``content_hash`` is the sole
    exception (``blake3_hex(원본 바이트)`` for a document, ``blake3_hex(utf8(Chunk.text))`` for a
    chunk/``IndexRecord``) — there is no label to combine with.

    Args:
        data: Raw document bytes, or text that is UTF-8 encoded before hashing.

    Returns:
        A 64-character lowercase hex BLAKE3 digest.
    """
    payload = data.encode("utf-8") if isinstance(data, str) else data
    return blake3(payload).hexdigest()


def block_id(doc_version: str, element_path: str) -> str:
    """Compute ``block_id = H("block", doc_version, element_path)[:32]`` (bible §6.2, ADR-0004).

    ``block_id`` is the sole 32-character truncation among the content-derived keys; it only
    needs document-scoped uniqueness (``element_path`` is unique within one document).
    """
    return hash_of("block", doc_version, element_path)[:32]


def chunk_id(doc_version: str, chunker_config_hash: str, level: int, span: str) -> str:
    """Compute ``chunk_id = H("chunk", doc_version, chunker_config_hash, str(level), span)``.

    ``span`` is the caller-built ``"{first_block_id}:{char_start}-{last_block_id}:{char_end}"``
    string (bible §6.2). ``chunk_id`` is scope- and generation-independent content addressing —
    it is not a physical index key; see :func:`record_id` for the scoped, generation-aware key.
    """
    return hash_of("chunk", doc_version, chunker_config_hash, str(level), span)


def stage_key(stage_name: str, scope_key: str, input_hash: str, fingerprint: str) -> str:
    """Compute ``stage_key = H("stage", stage_name, scope_key, input_hash, fingerprint)``.

    ``scope_key`` is the caller-built ``f"{tenant_id}/{collection_id}/{document_id}"``
    (ADR-0037; not applied to the ``fetch`` stage). ``input_hash`` is the original
    ``content_hash`` for ``detect``/``parse``, else ``input_ref.blake3`` (bible §4.1).
    """
    return hash_of("stage", stage_name, scope_key, input_hash, fingerprint)


def record_id(tenant_id: str, collection_id: str, document_id: str, index_generation: int, chunk_id: str) -> str:
    """Compute the scope- and generation-composed physical index key (bible §6.2, ADR-0004).

    ``record_id = H("record", tenant_id, collection_id, document_id, str(index_generation),
    chunk_id)``. This is the OpenSearch ``_id`` and the upsert idempotency unit (bible §4.2
    ``index``); see :func:`point_id_for_record` for the Qdrant point id derived from it.
    """
    return hash_of("record", tenant_id, collection_id, document_id, str(index_generation), chunk_id)


def point_id_for_record(record_id: str) -> UUID:
    """Compute the Qdrant point id ``uuid5(NAMESPACE_RAG_CHUNK, record_id)`` (ADR-0004).

    Qdrant point ids must be a u64 or a UUID; this is the one deterministic conversion from the
    hex64 :func:`record_id` bible §6.2/ADR-0004 mandate. The production Qdrant adapter
    (``rag_platform.adapters.index.qdrant.point_id``, 10-development/03 §10.2) is expected to
    call this rather than re-deriving it, keeping the conversion defined in exactly one place.
    """
    return uuid5(NAMESPACE_RAG_CHUNK, record_id)
