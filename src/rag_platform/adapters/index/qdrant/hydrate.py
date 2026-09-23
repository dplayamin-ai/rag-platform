"""`index_backend.qdrant`용 hydrate 백엔드 — `QdrantIndexBackend.client` 위의 보안 재필터 스크롤.

역할: `retrieval.hydrate.hydrate()`가 요구하는 `HydrateBackend` 포트(§4.3: `retrieve_by_ids(alias,
record_ids, security, with_payload)`)를 Qdrant로 구현한다. `standard`·`lite` 프로파일 공용이며
`HasIdCondition` + 보안 (a) 사전 필터로 `alias`를 스크롤해 payload만 배치 조회한다.
설계 근거: 바이블 §4.3 `hydrate` 행·§8.1 9단계, docs/04-pipelines/15 §11(규칙 표); `adapters/index/
qdrant/filters.py`(`build_filter`). `retrieval.hydrate.HydrateBackend`는 구조적 프로토콜이라 이 모듈은
그것을 import하지 않는다(바이블 §12 계층상 `retrieval`↔`adapters`는 독립 형제; import-linter 위반 회피).
구성: `QdrantHydrateBackend` — `HydrateBackend` 포트 구현(덕타이핑, `.retrieve_by_ids(...)`).
불변식·주의: 재조회에도 보안 (a) 조건을 다시 적용한다(E10) — 필터를 생략하지 않는다. `with_vectors`는
항상 `false`(§11 규칙 표 기본값). 동기 `QdrantClient.scroll` 위에 `async def`를 얹은 것뿐이라 실 서버
대상 논블로킹 I/O는 아니다(`AsyncQdrantClient` 전환은 후속 과제, open_issues).
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_fusion_channels.py`(`_FakeHydrateBackend`로 계약만
검증; 이 Qdrant 구현 자체는 `tests/adapters/index/test_qdrant_local.py`류의 로컬 모드 스모크가 없다면
DEFERRED — `# DEFERRED: QdrantHydrateBackend 전용 로컬 모드 통합 테스트`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from qdrant_client import models

from rag_platform.adapters.index.qdrant.filters import build_filter
from rag_platform.sdk.hashing import point_id_for_record

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID

    from rag_platform.contracts.common_types import SecurityFilter

__all__ = ["QdrantHydrateBackend"]


@dataclass(frozen=True, slots=True)
class QdrantHydrateBackend:
    """`standard`·`lite` 공통 hydrate 백엔드 — `QdrantIndexBackend.client` 위의 보안 재필터 스크롤(§11)."""

    backend: Any  # rag_platform.adapters.index.qdrant.backend.QdrantIndexBackend(순환 import 회피)

    async def retrieve_by_ids(
        self,
        alias: str,
        record_ids: Sequence[str],
        *,
        security: SecurityFilter,
        with_payload: Sequence[str],
    ) -> list[Mapping[str, Any]]:
        """`HasIdCondition` + 보안 (a) 사전 필터로 `alias`를 스크롤한다(E10)."""
        if not record_ids:
            return []
        point_ids: list[int | str | UUID] = [str(point_id_for_record(record_id)) for record_id in record_ids]
        base = build_filter(security)
        scroll_filter = models.Filter(
            must=[*(base.must or []), models.HasIdCondition(has_id=point_ids)], must_not=base.must_not
        )
        points, _next_page = self.backend.client.scroll(
            alias,
            scroll_filter=scroll_filter,
            limit=len(point_ids),
            with_payload=list(with_payload),
            with_vectors=False,
        )
        return [dict(point.payload or {}) for point in points]
