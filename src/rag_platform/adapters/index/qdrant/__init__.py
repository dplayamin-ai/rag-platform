"""Qdrant 인덱스 백엔드 어댑터 패키지(`index_backend.qdrant`, role `vector`) — `lite` 단독·`standard` 벡터 레그.

설계 근거: 바이블 §12 `adapters/index/qdrant/`(`filters`·`point_id`·`bm25_sparse`), §13.4 명명,
04-pipelines/13 §4·§6, ADR-0012(`lite` = Qdrant 단독 + 플랫폼 계산 `sparse_bm25`).
구성:
- `backend` — `QdrantIndexBackend`: 컬렉션 생성·대조, upsert/delete/검색, 세대 플립, alias 교체
- `filters` — 표준 필터 DSL(`PlanFilters`/`FilterNode`) → Qdrant `Filter` 순수 변환, E7 보안 검사
- `point_id` — `record_id → uuid5 point_id` 변환·대조(E17)
- `bm25_sparse` — 형태소 토큰 → BM25 TF 포화값 sparse 벡터(`modifier: idf`는 서버)
불변식: 검색·쓰기 필터에는 항상 `tenant_id`가 들어간다(보안 사전 필터 없으면 예외).
검증 계층: 1층(여기서 검증, qdrant-client 로컬 모드) — `tests/adapters/index/test_qdrant_local.py`.
DEFERRED: 서버 모드(payload 인덱스·`is_tenant` 서브그래프·insert-only 충돌)는 `needs_docker`.
"""

from __future__ import annotations
