"""Qdrant `point_id` 변환·대조 — `record_id`(hex64)를 결정적 UUIDv5 `point_id`로 바꾸고 레코드의 키 정합을 검사한다.

설계 근거: 바이블 §6.1(`point_id = uuid5(NAMESPACE_RAG_CHUNK, record_id)`), §6.2 `record_id` 결합식,
ADR-0004 v1.2(스코프·세대 합성 키, E17 교차 테넌트 충돌 없음), 04-pipelines/13 §3 검증 순서 2단계.
계약 타입: `IndexRecord`(`record_id`·`point_id`와 스코프 필드 — 테넌트·컬렉션·문서·세대·`chunk_id`).

구성:
- `point_id_for(record_id)` — hex64 검사 후 `sdk.hashing.point_id_for_record`를 호출해 문자열 UUID 반환
- `verify_record_keys(record)` — `record_id` 재계산·`point_id` 재계산 대조, 불일치면 `contract.violation`

불변식: UUID 변환 공식은 `sdk/hashing.py` 한 곳에만 있다(여기서 재구현 금지, ADR-0004 단일 구현).
같은 `chunk_id`라도 테넌트·컬렉션·문서·세대가 다르면 `point_id`가 다르다 — 공유 컬렉션 격리의 전제.
검증 계층: 1층(여기서 검증) — `tests/adapters/index/test_qdrant_local.py`(결정적 `point_id`, 교차 테넌트).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rag_platform.sdk.hashing import point_id_for_record, record_id
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from rag_platform.contracts.index_record import IndexRecord

__all__ = ["point_id_for", "verify_record_keys"]

_CONTRACT_VIOLATION = "contract.violation"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def point_id_for(record_id_hex: str) -> str:
    """Return the canonical string UUID point id for a hex64 `record_id` (bible §6.1)."""
    if not _HEX64.match(record_id_hex):
        raise StageError(
            _CONTRACT_VIOLATION,
            stage="index",
            plugin_id="index_backend.qdrant",
            detail=f"record_id must be 64 lowercase hex chars: {record_id_hex!r}",
        )
    return str(point_id_for_record(record_id_hex))


def verify_record_keys(record: IndexRecord) -> str:
    """Recompute `record_id` and `point_id` from `record`'s scope fields; return the point id.

    Raises `contract.violation` when either stored key disagrees with the recomputation
    (04-pipelines/13 §3 step 2, E17).
    """
    expected_record_id = record_id(
        str(record.tenant_id.root),
        str(record.collection_id.root),
        str(record.document_id.root),
        record.index_generation,
        str(record.chunk_id.root),
    )
    stored_record_id = str(record.record_id.root)
    if stored_record_id != expected_record_id:
        raise StageError(
            _CONTRACT_VIOLATION,
            stage="index",
            plugin_id="index_backend.qdrant",
            detail=f"record_id mismatch for chunk {record.chunk_id.root}: stored {stored_record_id}",
        )
    expected_point_id = point_id_for(expected_record_id)
    if str(record.point_id.root) != expected_point_id:
        raise StageError(
            _CONTRACT_VIOLATION,
            stage="index",
            plugin_id="index_backend.qdrant",
            detail=f"point_id mismatch for record {stored_record_id}",
        )
    return expected_point_id
