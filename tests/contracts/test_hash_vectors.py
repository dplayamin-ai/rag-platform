"""고정 키 파생(key-derivation) 해시 벡터 — `ADR-0004`가 얼린 입력→출력 쌍으로 `rag_platform.sdk.hashing`을 검증한다.

설계 근거: `ADR-0004`("적합성 키트의 고정 벡터로 쓴다"), 바이블 §6.2 `H()`, `10-development/03` §10.2 해시 벡터
게이트. `canonical_json`·`span` 형식·`str(level)`/`str(index_generation)` 직렬화·BLAKE3/`uuid5` 구현 중 어느
하나가 바뀌어도 이 테스트에서 즉시 불일치로 드러나야 하며, 하류에서 발견되어서는 안 된다.

구성: `rag_platform.sdk.hashing`의 `hash_of`(`H()`)·`blake3_hex`·`block_id`·`chunk_id`·`record_id`·
`point_id_for_record`와 `NAMESPACE_RAG_CHUNK`를 ADR-0004의 고정 벡터에 대입해 값을 비교하는 테스트 함수들.

불변식: 벡터 값 자체를 바꾸지 않는다(ADR이 정본). `sdk.hashing`을 손으로 검증하는 유일한 모듈이다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from uuid import UUID

import pytest

from rag_platform.sdk.hashing import (
    NAMESPACE_RAG_CHUNK,
    blake3_hex,
    block_id,
    chunk_id,
    hash_of,
    point_id_for_record,
    record_id,
)

# ADR-0004 "적합성 키트의 고정 벡터" JSON block, verbatim.
SOURCE_BYTES = b"RAG Platform ADR-0004 test vector\n"
DOC_VERSION = "4cf93d9ac740c93929421079b0ef91b9a703c978df6d7a637c8d2093c368565b"
ELEMENT_PATH = "/body/sec[0]/p[3]"
BLOCK_ID = "650f72efde5deeab20165112e8387e22"
CHUNKER_CONFIG_CANONICAL_JSON = '{"leaf_max_tokens":512,"merge_min_tokens":64,"parent_max_tokens":2048}'
CHUNKER_CONFIG_HASH = "149c63fad1744e0bc73c8ac4562d8fdc59f4260a4650a726dd1ae086fb635c97"
LEVEL = 0
SPAN = "650f72efde5deeab20165112e8387e22:0-650f72efde5deeab20165112e8387e22:120"
CHUNK_ID = "7694bf848e17bb681a9b737256cf4a824412fa1dac61e29003b46fb39cf43e0a"
TENANT_ID = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"
COLLECTION_ID = "01J9ZQ5C0Q3N4P5R6S7T8V9WXY"
DOCUMENT_ID = "01J9ZQ6D1R4P5R6S7T8V9WXYZ0"
INDEX_GENERATION = 1
RECORD_ID = "c1b52951c8dba53646f6a5f25dbd48f3efd9797370667faf17f333a3cce8914a"
POINT_ID = "ff147912-719c-595e-9d30-587d329e856f"
RECORD_ID_GENERATION_2 = "ef61d0055c4d8877c0bf391e84a5279ed39adec8cbbbf601e176aaefd49c6b28"
COLLECTION_ID_OTHER = "01J9ZQ7E2S5Q6R7S8T9V0WXYZ1"
RECORD_ID_OTHER_COLLECTION = "2d6d27e543b4ca08dd3723234eba9e7b785ee21ab6db42e4e776522abb1dfee7"


def test_h_combination_is_label_separated() -> None:
    """``H()`` must not collide two different (label, parts) splits of the same bytes."""
    assert hash_of("ab", "c") != hash_of("a", "bc")
    assert hash_of("a", "b", "c") != hash_of("a", "b,c")


def test_h_rejects_unit_separator() -> None:
    """bible §6.2 / 00-contract-overview §7.1: a U+001F in label or a part is `contract.violation`."""
    with pytest.raises(ValueError, match=r"contract\.violation"):
        hash_of("la\x1fbel", "part")
    with pytest.raises(ValueError, match=r"contract\.violation"):
        hash_of("label", "pa\x1frt")


def test_doc_version_is_labelless_content_hash() -> None:
    assert blake3_hex(SOURCE_BYTES) == DOC_VERSION


def test_block_id_vector() -> None:
    assert block_id(DOC_VERSION, ELEMENT_PATH) == BLOCK_ID
    assert len(BLOCK_ID) == 32, "block_id is the sole 32-char truncation (bible §6.2)"


def test_chunker_config_hash_vector() -> None:
    assert hash_of("config", CHUNKER_CONFIG_CANONICAL_JSON) == CHUNKER_CONFIG_HASH


def test_chunk_id_vector() -> None:
    assert chunk_id(DOC_VERSION, CHUNKER_CONFIG_HASH, LEVEL, SPAN) == CHUNK_ID
    assert len(CHUNK_ID) == 64


def test_record_id_vector() -> None:
    assert record_id(TENANT_ID, COLLECTION_ID, DOCUMENT_ID, INDEX_GENERATION, CHUNK_ID) == RECORD_ID
    assert len(RECORD_ID) == 64


def test_namespace_rag_chunk_vector() -> None:
    assert UUID("4198d3e2-bdc6-5334-b170-0d5490f26cc7") == NAMESPACE_RAG_CHUNK


def test_point_id_vector() -> None:
    assert point_id_for_record(RECORD_ID) == UUID(POINT_ID)


def test_record_id_generation_changes_the_key() -> None:
    """Same chunk_id, different index_generation -> different record_id (bible §11.4 generation
    saga: the new generation's records must coexist with, not overwrite, the previous one).
    """
    assert record_id(TENANT_ID, COLLECTION_ID, DOCUMENT_ID, 2, CHUNK_ID) == RECORD_ID_GENERATION_2
    assert RECORD_ID_GENERATION_2 != RECORD_ID


def test_record_id_collection_scope_changes_the_key() -> None:
    """Same chunk_id, different collection_id -> different record_id (ADR-0004 E17: cross-tenant/
    cross-collection upserts to a shared physical index must not collide).
    """
    result = record_id(TENANT_ID, COLLECTION_ID_OTHER, DOCUMENT_ID, INDEX_GENERATION, CHUNK_ID)
    assert result == RECORD_ID_OTHER_COLLECTION
    assert result != RECORD_ID


def test_chunk_id_is_scope_and_generation_independent() -> None:
    """chunk_id has no tenant/collection/generation in it — only record_id does (ADR-0004)."""
    assert chunk_id(DOC_VERSION, CHUNKER_CONFIG_HASH, LEVEL, SPAN) == CHUNK_ID
