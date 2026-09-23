"""`InMemoryIndexBackend` — `sdk.ports.IndexBackend` 대역(double). 무차별 대입 코사인 유사도, Qdrant 없음.

역할: 실제 Qdrant 클러스터 없이 `upsert`/`search_dense`/`search_lexical` 호출부를 검증하는
딕셔너리 기반 인덱스 대역.
설계 근거: 바이블 §11.4(`is_current`/`index_generation` 플립을 포함한 인덱스 백엔드 계약)의
검증 대역 — 실 백엔드는 phase-6 계획 §8 tier 2로 이관.

구성:
- `InMemoryIndexBackend` — `upsert(records)`로 `{id, tenant_id, vector?, text?}` 레코드 저장
- `search_dense(tenant_id, vector, top_k)` — 코사인 유사도 상위 `top_k`
- `search_lexical(tenant_id, query, top_k)` — 단어 겹침 개수 기반 상위 `top_k`

불변식·주의: 모든 검색은 `tenant_id`로 스코프된다(다른 테넌트 레코드는 결과에서 제외).
검증 계층: 1층(대역 자체는 여기서 검증) — `tests/unit/test_testing_doubles.py`.
DEFERRED: 실 Qdrant 클러스터(gRPC, named vectors, payload 필터, `is_current`/`index_generation`
플립) 대상 검증은 `needs_docker`(phase-6 계획 §8 tier 2) —
`docs/12-appendix/09-deferred-verification-ledger.md`에서 추적.
"""

from __future__ import annotations

import math
from typing import Any

__all__ = ["InMemoryIndexBackend"]


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        msg = f"vector length mismatch: {len(a)} vs {len(b)}"
        raise ValueError(msg)
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (norm_a * norm_b)


class InMemoryIndexBackend:
    """`IndexBackend` double: `upsert` stores `{id, tenant_id, vector?, text?}` records in a dict."""

    def __init__(self) -> None:
        """Start with an empty record store."""
        self._records: dict[str, dict[str, Any]] = {}

    def upsert(self, records: list[dict[str, object]]) -> None:
        """Insert or replace each record in `records`, keyed by its `id` field."""
        for record in records:
            self._records[str(record["id"])] = dict(record)

    def search_dense(self, tenant_id: str, vector: list[float], top_k: int) -> list[tuple[str, float]]:
        """Return up to `top_k` `(record_id, cosine_similarity)` pairs scoped to `tenant_id`."""
        scored = [
            (record_id, _cosine(vector, record["vector"]))
            for record_id, record in self._records.items()
            if record.get("tenant_id") == tenant_id and record.get("vector") is not None
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def search_lexical(self, tenant_id: str, query: str, top_k: int) -> list[tuple[str, float]]:
        """Return up to `top_k` `(record_id, term_overlap_count)` pairs scoped to `tenant_id`."""
        terms = set(query.lower().split())
        scored = []
        for record_id, record in self._records.items():
            if record.get("tenant_id") != tenant_id:
                continue
            text = str(record.get("text", "")).lower()
            hits = sum(1 for term in terms if term in text)
            if hits > 0:
                scored.append((record_id, float(hits)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
