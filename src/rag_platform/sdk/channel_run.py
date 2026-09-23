"""`retriever` 확장 지점의 SDK 내부 타입 — `retrieval.channels`와 `adapters.retrieve.*`가 공유한다.

역할: `QueryVectors`(런 하나의 임베딩 입력)·`ChannelRunInput`(`Retriever.run`의 입력)·`Retriever`
(구조적 프로토콜)를 정의한다. 바이블 §12상 `retrieval`↔`adapters`는 독립 형제 계층이라 서로 직접
import할 수 없으므로, 두 계층이 공유해야 하는 이 타입들은 그 아래 `sdk` 층에 둔다(포트 경유 — 02-
architecture/02 §1.3과 같은 패턴).
설계 근거: 바이블 §4.3 `retrieve` 행, docs/04-pipelines/15 §3.1(`Retriever` 공통 인터페이스); 계약
아님(경계 계약은 `contracts/candidate_set.py`).
구성: `PAYLOAD_SLIM_KEYS` — 채널이 요청하는 payload 슬림 10키; `QueryVectors` — dense/sparse_learned/
sparse_bm25/late_interaction 슬롯; `ChannelRunInput` — `Retriever.run`의 입력; `Retriever` — 어댑터가
구현하는 구조적 프로토콜(`channel`·`plugin_id`·`capabilities()`·`run()`).
불변식·주의: 이 모듈은 `contracts`·`sdk` 밖을 import하지 않는다(`retrieval`·`adapters` 어느 쪽도 모름).
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_fusion_channels.py`(`retrieval.channels`를 통해
간접 검증).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from rag_platform.contracts.candidate_set import ChannelRun
    from rag_platform.contracts.common_types import Capabilities
    from rag_platform.contracts.index_record import SparseVector
    from rag_platform.contracts.query_plan import ChannelPlan, LexicalTerm, PlanFilters, RewrittenQuery
    from rag_platform.sdk.context import StageContext

__all__ = ["PAYLOAD_SLIM_KEYS", "ChannelRunInput", "QueryVectors", "Retriever"]

#: 04-pipelines/15 §2.3 표: 후보 payload_slim 10키 (contracts/candidate_set.py `PayloadSlim`).
PAYLOAD_SLIM_KEYS: tuple[str, ...] = (
    "heading_path",
    "page_start",
    "page_end",
    "doc_date",
    "acl_classification",
    "acl_hash",
    "token_count_primary",
    "text_preview",
    "content_hash",
    "text_source",
)


@dataclass(frozen=True, slots=True)
class QueryVectors:
    """런 하나가 임베딩 입력으로 쓰는 질의 벡터(SDK 내부 타입, §3.1). 채널이 필요로 하지 않는 슬롯은 `None`."""

    dense: tuple[float, ...] | None = None
    sparse_learned: SparseVector | None = None
    sparse_bm25: SparseVector | None = None
    late_interaction: tuple[tuple[float, ...], ...] | None = None


@dataclass(frozen=True, slots=True)
class ChannelRunInput:
    """`Retriever.run`의 입력(SDK 내부 타입, §3.1) — 경계 계약이 아니다."""

    channel: ChannelPlan
    variant: RewrittenQuery
    query_vectors: QueryVectors
    query_text: str
    filters: PlanFilters
    exclude_ids: tuple[str, ...]
    security: Any  # common_types.SecurityContext(순환 import 회피를 위해 구조적으로만 사용)
    payload_slim_keys: tuple[str, ...] = PAYLOAD_SLIM_KEYS
    lexical_terms: tuple[LexicalTerm, ...] = field(default_factory=tuple)


@runtime_checkable
class Retriever(Protocol):
    """`retriever` 확장 지점(§3.1) — `channel`(생산 채널) + `Stage` 5멤버 중 실행에 필요한 3개."""

    channel: Any  # common_types.Channel
    plugin_id: str

    def capabilities(self) -> Capabilities:
        """이 리트리버가 요구하는 질의 벡터 슬롯 등을 담은 `Capabilities.extra`를 선언한다."""
        ...

    async def run(self, inp: ChannelRunInput, ctx: StageContext) -> ChannelRun:
        """런 하나(`ChannelRunInput`)를 실행해 `ChannelRun`(원점수 내림차순, `rank` 1..n)을 반환한다."""
        ...
