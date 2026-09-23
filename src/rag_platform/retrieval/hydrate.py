"""`hydrate` 서브스텝 — `fuse`가 절단한 상위 `hydrate.top_n`의 payload를 벡터 백엔드에서 1회 배치 조회한다.

역할: `RankedSet(stage=fused, hydrated=false)`의 각 결과에 대해 `record_id`로 인덱스 백엔드의
`text`·`context_prefix`·인용 좌표·ACL·헤더 필드를 채우고 `hydrated=true`로 바꾼다. 세대 플립 경합 등으로
레코드가 사라졌으면 그 결과를 제거하고 `omitted`·`degraded`·`explain`에 남긴다(부분 실패, 요청은 계속).
설계 근거: 바이블 §4.3 `hydrate` 행·§8.1 9단계, docs/04-pipelines/15 §11(`hydrate` 서브스텝 규칙 표),
계약 `RankedSet`/`RankedOmittedEntry`(`contracts/ranked_set.py`), `IndexRecord` payload 필드
(`contracts/index_record.py`).
구성: `HYDRATE_PAYLOAD_KEYS` — with_payload 요청 키(바이블 §4.3 목록); `HydrateBackend` — `index_backend`
확장 지점의 최소 포트(코디네이터는 백엔드를 모른다; 구현체는 `adapters/index/qdrant/hydrate.py`의
`QdrantHydrateBackend` — 바이블 §12 계층상 `retrieval`은 그 어댑터를 import할 수 없어 별도 모듈에 둔다);
`hydrate` — 배치 조회 + `RankedSet` 갱신.
불변식·주의: 결과 캐시 금지(ACL 시점성). 재조회에도 보안 (a) 조건(`PlanFilters.security`)을 다시
적용한다(E10) — `record_id`가 테넌트·컬렉션·문서·세대를 합성해 교차 테넌트 조회가 구조적으로 불가능해도
필터를 생략하지 않는다. `record_id`가 여러 컬렉션(`collection_id`)에 걸쳐 있으면 물리 alias별로 나눠
호출한다(바이블의 "1회 배치"는 컬렉션 1개 기준 문구이며, 다중 컬렉션 팬아웃은 alias 수만큼 호출 —
open_issues). `with_vectors`는 항상 `false`(§11 규칙 표 기본값; `dedup`용 `true` 옵션은 범위 밖).
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_fusion_channels.py`.
"""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from rag_platform.contracts.common_types import (
    Acl1,
    DateTime,
    DegradedComponent,
    DegradedEntry,
    DegradedReason,
    ExplainCode,
)
from rag_platform.contracts.ranked_set import RankedOmittedEntry, RankedSetStats, Reason, Result
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from rag_platform.contracts.common_types import SecurityFilter
    from rag_platform.contracts.query_plan import QueryPlan
    from rag_platform.contracts.ranked_set import RankedSet

__all__ = ["HYDRATE_PAYLOAD_KEYS", "HydrateBackend", "hydrate"]

_HYDRATE_BACKEND_ERROR = "hydrate.backend_error"

#: 바이블 §4.3 `hydrate` 행 with_payload 목록(1.3.0 선택 4종 포함) + 매칭용 `record_id`.
HYDRATE_PAYLOAD_KEYS: tuple[str, ...] = (
    "record_id",
    "text",
    "context_prefix",
    "heading_path",
    "numbering_path",
    "page_start",
    "page_end",
    "block_refs",
    "sentence_spans",
    "table_ref",
    "html_ref",
    "acl_allow",
    "acl_deny",
    "acl_visibility",
    "acl_classification",
    "acl_embargo_until",
    "acl_expires_at",
    "acl_hash",
    "title",
    "source_uri",
    "external_id",
    "doc_date",
    "doc_type",
    "lang",
    "text_source",
    "ocr_confidence_min",
    "chunk_set_blake3",
    "token_count_primary",
    "ordinal",
    "text_truncated",
    "pii_policy_applied",
)


def _root_str(value: Any) -> str | None:
    """`RootModel`(`.root`)이든 평범한 `str`/`None`이든 같은 방식으로 문자열을 뽑는다(테스트 이중 대비)."""
    if value is None:
        return None
    root = getattr(value, "root", None)
    return root if isinstance(root, str) else str(value)


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


@runtime_checkable
class HydrateBackend(Protocol):
    """`index_backend`의 hydrate 조회 표면(§4.3: `retrieve(record_ids, with_payload)`의 최소 포트)."""

    async def retrieve_by_ids(
        self,
        alias: str,
        record_ids: Sequence[str],
        *,
        security: SecurityFilter,
        with_payload: Sequence[str],
    ) -> list[Mapping[str, Any]]:
        """`alias`(물리 컬렉션)에서 `record_ids`의 payload를 배치 조회한다(보안 (a) 재적용, 존재하는 것만)."""
        ...


def _acl_from_payload(payload: Mapping[str, Any]) -> Acl1:
    return Acl1(
        allow=payload.get("acl_allow", []),
        deny=payload.get("acl_deny") or [],
        visibility=payload["acl_visibility"],
        classification=payload["acl_classification"],
        embargo_until=payload.get("acl_embargo_until"),
        expires_at=payload.get("acl_expires_at"),
        acl_hash=payload["acl_hash"],
    )


def _hydrated_result(result: Result, payload: Mapping[str, Any], *, final_rank: int) -> Result:
    """`result`(fused)의 채널 원장은 그대로 두고 `payload`(`IndexRecord` 투영)로 hydrate 필드를 채운다."""
    return Result(
        record_id=result.record_id,
        chunk_id=result.chunk_id,
        collection_id=result.collection_id,
        document_id=result.document_id,
        doc_version=result.doc_version,
        item_kind=result.item_kind,
        level=result.level,
        parent_chunk_id=result.parent_chunk_id,
        final_rank=final_rank,
        final_score=result.final_score,
        fused_score=result.fused_score,
        fused_rank=result.fused_rank,
        rerank_raw_score=result.rerank_raw_score,
        rerank_normalized_score=result.rerank_normalized_score,
        rerank_rank=result.rerank_rank,
        score_breakdown=result.score_breakdown,
        channels_hit=result.channels_hit,
        variant_ids=result.variant_ids,
        text=payload["text"],
        context_prefix=payload["context_prefix"],
        heading_path=payload.get("heading_path"),
        numbering_path=payload.get("numbering_path"),
        title=payload.get("title"),
        source_uri=payload.get("source_uri"),
        external_id=payload.get("external_id"),
        doc_date=payload.get("doc_date"),
        doc_type=payload.get("doc_type"),
        page_start=payload.get("page_start"),
        page_end=payload.get("page_end"),
        lang=payload.get("lang"),
        text_source=payload.get("text_source"),
        ocr_confidence_min=payload.get("ocr_confidence_min"),
        chunk_set_blake3=payload.get("chunk_set_blake3"),
        token_count_primary=payload.get("token_count_primary"),
        ordinal=payload.get("ordinal"),
        text_truncated=payload.get("text_truncated"),
        pii_policy_applied=payload.get("pii_policy_applied"),
        acl=_acl_from_payload(payload),
        block_refs=payload.get("block_refs"),
        sentence_spans=payload.get("sentence_spans"),
        table_ref=payload.get("table_ref"),
        html_ref=payload.get("html_ref"),
        expanded_from=result.expanded_from,
        duplicates_of=result.duplicates_of,
        window_chunk_ids=result.window_chunk_ids,
        explain=list(result.explain),
    )


def _alias_by_collection(plan: QueryPlan) -> dict[str, str]:
    return {_root_str(channel.collection_id) or "": channel.collection_alias for channel in plan.channels}


async def hydrate(rs: RankedSet, plan: QueryPlan, backend: HydrateBackend, *, now: datetime) -> RankedSet:
    """`RankedSet(fused, hydrated=false)`의 상위 결과를 1회 배치 조회로 hydrate한다(§11).

    이미 `hydrated=true`면 그대로 돌려준다(멱등). 컬렉션별로 물리 alias를 나눠 호출하고, 누락된
    `record_id`는 결과에서 제거해 `omitted += {hydrate_missing}` + `degraded += {hydrate,
    partial_result}` + `explain += hydrate_missing`을 남긴다. `final_rank`는 살아남은 결과만 다시
    1..n으로 재부여하고 `fused_rank`는 그대로 둔다(§11 규칙 표).
    """
    if rs.hydrated:
        return rs

    alias_by_collection = _alias_by_collection(plan)
    record_ids_by_alias: dict[str, list[str]] = {}
    for result in rs.results:
        record_id = _root_str(result.record_id)
        if record_id is None:
            continue  # item_kind=parent 확장 항목(record_id=null)은 hydrate 대상이 아니다
        alias = alias_by_collection.get(_root_str(result.collection_id) or "")
        if alias is None:
            continue
        record_ids_by_alias.setdefault(alias, []).append(record_id)

    payload_by_record_id: dict[str, Mapping[str, Any]] = {}
    try:
        for alias, record_ids in record_ids_by_alias.items():
            rows = await backend.retrieve_by_ids(
                alias, record_ids, security=plan.filters.security, with_payload=HYDRATE_PAYLOAD_KEYS
            )
            for row in rows:
                record_id = _root_str(row.get("record_id"))
                if record_id is not None:
                    payload_by_record_id[record_id] = row
    except StageError:
        raise
    except Exception as exc:
        raise StageError(_HYDRATE_BACKEND_ERROR, stage="hydrate", detail=str(exc)) from exc

    results: list[Result] = []
    omitted: list[RankedOmittedEntry] = list(rs.omitted or ())
    missing = False
    for result in rs.results:
        record_id = _root_str(result.record_id)
        payload = payload_by_record_id.get(record_id) if record_id is not None else None
        if payload is None:
            missing = True
            omitted.append(
                RankedOmittedEntry(
                    chunk_id=result.chunk_id,
                    collection_id=result.collection_id,
                    document_id=result.document_id,
                    reason=Reason.hydrate_missing,
                    step=None,
                    related_chunk_id=None,
                    explain=[ExplainCode.hydrate_missing],
                )
            )
            continue
        results.append(_hydrated_result(result, payload, final_rank=len(results) + 1))

    degraded = list(rs.degraded)
    if missing:
        degraded.append(DegradedEntry(component=DegradedComponent.hydrate, reason=DegradedReason.partial_result))

    return rs.model_copy(
        update={
            "hydrated": True,
            "results": results,
            "omitted": omitted,
            "degraded": degraded,
            "created_at": DateTime(root=_rfc3339_ms(now)),
            "stats": RankedSetStats(
                n_in=rs.stats.n_in, n_out=len(results), hydrated_n=len(results), gate_passed=rs.stats.gate_passed
            ),
        }
    )
