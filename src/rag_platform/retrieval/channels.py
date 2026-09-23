"""`retrieve` 스테이지 코디네이터 — 채널x컬렉션x변형 런을 `asyncio`로 병렬 실행해 `CandidateSet`을 만든다.

역할: `QueryPlan.channels[]`(`enabled=true`)와 `QueryPlan.rewritten_queries[]`를 곱집합으로 펼쳐 런
목록을 만들고, 세마포어로 동시성을 제한하며 런별 타임아웃 아래 `retriever` 어댑터를 호출한다. 곱집합이
비면(`route=no_retrieval` 등 모든 채널이 꺼짐) 시도조차 없었던 것이므로 빈 `CandidateSet`을 낸다(잡담
질의가 503으로 죽지 않게 함, 리뷰 지적). 부분 실패(타임아웃·백엔드 오류)는 그 런만 제외하고
`degraded[]`에 기록하며, 시도한 런이 하나 이상이고 전부 실패하면 `retrieve.unavailable`로 요청 전체를
실패시킨다. `retrieve.security_context_missing`(계약 위반)·`contract.violation`(사용자 필터 값 오류
등 비재시도 오류)은 부분 실패로 감싸지 않고 그대로 다시 던진다(그 외 코드를 `retrieve.unavailable`로
잘못 뭉뚱그리면 클라이언트가 재시도 폭풍을 만든다).
설계 근거: 바이블 §4.3 `retrieve` 행, §8.1 6·7단계; docs/04-pipelines/15 §2(병렬 리트리버 실행)·§2.2
실행 규칙 표·§3.1(`Retriever` 공통 인터페이스); 계약 `CandidateSet`/`ChannelRun`/`Candidate`
(`contracts/candidate_set.py`).
구성: `QueryVectors`/`ChannelRunInput`/`Retriever`/`PAYLOAD_SLIM_KEYS` — `sdk.channel_run`에서 재노출
(바이블 §12상 `retrieval`↔`adapters`는 독립 형제 계층이라 어댑터와 공유하는 이 타입들은 그 아래 `sdk`
층에 둔다); `run_one` — 런 하나 실행; `retrieve_once` — 병렬 실행 + `CandidateSet` 조립.
불변식·주의: 결과 캐시 금지(ACL 시점성). 무거운(임베딩 서버) 질의 벡터는 이 모듈이 계산하지 않는다 —
호출자가 `variant_id → QueryVectors`(dense 등) 매핑을 미리 만들어 넘긴다(임베딩은 §8.1 5단계, 이
모듈은 7단계). 대신 결정적 토큰화만 필요한 채널(lexical/BM25)을 위해 `ChannelRunInput.query_text`를
이 모듈이 직접 계산해 넘긴다(§3.2·§3.5: 원 질의는 채널별로 `dense_query_text`|`normalized_query`,
변형은 `variant.text`). 필터 빌더(백엔드 네이티브 변환)는 각 `Retriever` 어댑터가 `PlanFilters`로부터
직접 만든다(코디네이터는 `PlanFilters`·`exclude_ids`를 그대로 전달) — 이는 이 WP의 축소화 결정이며
다중 백엔드 통합 필터 빌더는 범위 밖이다(open_issues).
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_fusion_channels.py`.
"""

from __future__ import annotations

import asyncio
from datetime import UTC
from typing import TYPE_CHECKING, Any

from pydantic import AnyUrl
from ulid import ULID

from rag_platform.contracts.candidate_set import CandidateSet, ChannelRun, FiltersApplied
from rag_platform.contracts.common_types import (
    Channel,
    ChannelRunStatus,
    DegradedComponent,
    DegradedEntry,
    DegradedReason,
    ErrorCodeCatalog,
    ErrorTypeUrn,
    Producer,
    StageError as ContractStageError,
)
from rag_platform.sdk.channel_run import PAYLOAD_SLIM_KEYS, ChannelRunInput, QueryVectors, Retriever
from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.stage import RetryClass, StageError, classify_error

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from rag_platform.contracts.query_plan import ChannelPlan, QueryPlan, RewrittenQuery
    from rag_platform.sdk.context import StageContext

__all__ = [
    "DEFAULT_CONCURRENCY",
    "PAYLOAD_SLIM_KEYS",
    "PLUGIN_ID",
    "PLUGIN_VERSION",
    "ChannelRunInput",
    "QueryVectors",
    "Retriever",
    "retrieve_once",
    "run_one",
]

PLUGIN_ID = "retriever.pipeline"  # 09 §6.1 규약: 여러 retriever 플러그인을 합성한 CandidateSet의 producer
PLUGIN_VERSION = "0.1.0"
#: 04-pipelines/15 §2.1: "런은 동시성 상한을 갖는다"의 초안값(바이블 §8.1 7단계 근처, profile 확정 전 기본).
DEFAULT_CONCURRENCY = 32

_RETRIEVE_UNAVAILABLE = "retrieve.unavailable"
_CHANNEL_TIMEOUT = "retrieve.channel_timeout"
_BACKEND_ERROR = "retrieve.backend_error"
_SECURITY_CONTEXT_MISSING = "retrieve.security_context_missing"
_CONTRACT_VIOLATION = "contract.violation"
#: 부분 실패(그 런만 제외 + degraded)로 감싸지 않고 요청 전체를 실패시키는 코드(§2.2 예외 목록).
#: 둘 다 "이 요청 자체가 잘못됐다"는 신호라 다른 채널이 더 있어도 재시도 폭풍만 만들 뿐이다.
_NON_MASKABLE_CODES = frozenset({_SECURITY_CONTEXT_MISSING, _CONTRACT_VIOLATION})


def _root_str(value: Any) -> str:
    """`RootModel`(`.root`)이든 평범한 `str`이든 같은 방식으로 문자열을 뽑는다(테스트 이중 대비)."""
    root = getattr(value, "root", None)
    return root if isinstance(root, str) else str(value)


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def _is_variant(variant: RewrittenQuery, plan: QueryPlan) -> bool:
    """`variant`가 `original`(= `plan.query_id`)이 아니면 True(변형 가중 0.5 적용 대상, §5.1)."""
    return _root_str(variant.variant_id) != _root_str(plan.query_id)


def _query_text(channel: ChannelPlan, variant: RewrittenQuery, plan: QueryPlan) -> str:
    """런의 임베딩/토큰화 입력 텍스트(§3.2·§3.5): 변형은 `variant.text`, 원 질의는 채널별로 다르다.

    원 질의(`variant_id == plan.query_id`)의 벡터 런(dense·sparse_learned)은 `plan.dense_query_text`
    (HyDE 켬이면 가상 문서, 기본은 `normalized_query`와 동일), lexical(BM25)은 항상
    `plan.normalized_query`(가상 문서를 쓰지 않는다 — BM25는 실제 질의 형태소가 필요, §3.5).
    """
    if _is_variant(variant, plan):
        return variant.text
    if channel.channel == Channel.lexical:
        return plan.normalized_query
    return plan.dense_query_text


def _security_context_hash(security: Any) -> str:
    """바이블 §6.2 `H("sec", ...)` — 필터에 `tenant_id`가 포함됨을 서명하는 값."""
    return hash_of(
        "sec",
        _root_str(security.tenant_id),
        ",".join(sorted(_root_str(p) for p in security.principals)),
        ",".join(sorted(_root_str(c) for c in security.collection_ids)),
        _root_str(security.as_of),
        str(getattr(security.classification_max, "value", security.classification_max)),
        ",".join(sorted(str(getattr(v, "value", v)) for v in security.visible_set)),
    )


def _channel_run_id(channel: Any, collection_id: Any, variant_id: str) -> str:
    channel_value = str(getattr(channel, "value", channel))
    return f"{channel_value}:{_root_str(collection_id)}:{variant_id}"


def _disabled_runs(plan: QueryPlan) -> list[ChannelRun]:
    """`enabled=false` 채널도 감사를 위해 `status=disabled`로 유지한다(§2.1)."""
    original_variant_id = _root_str(plan.query_id)
    return [
        ChannelRun(
            channel_run_id=_channel_run_id(ch.channel, ch.collection_id, original_variant_id),
            channel=ch.channel,
            collection_id=ch.collection_id,
            variant_id=plan.query_id,
            retriever_id=_root_str(ch.retriever_id),
            backend_id=ch.backend_id,
            collection_alias=ch.collection_alias,
            embedding_profile_hash=ch.embedding_profile_hash,
            index_generation_seen=[],
            status=ChannelRunStatus.disabled,
            took_ms=0,
            returned=0,
            total_hits=None,
            truncated=False,
            error=None,
            candidates=[],
        )
        for ch in plan.channels
        if not ch.enabled
    ]


def _failed_run(channel: ChannelPlan, variant: RewrittenQuery, code: str, status: ChannelRunStatus) -> ChannelRun:
    """타임아웃·백엔드 오류로 제외된 런의 기록(§2.2: "그 런만 제외 + degraded")."""
    retryable = classify_error(code) is RetryClass.RETRYABLE
    error = ContractStageError(
        code=ErrorCodeCatalog(code),
        type=ErrorTypeUrn(AnyUrl(f"urn:rag:error:{code}")),
        retryable=retryable,
        stage="retrieve",
        plugin_id=_root_str(channel.retriever_id),
    )
    return ChannelRun(
        channel_run_id=_channel_run_id(channel.channel, channel.collection_id, _root_str(variant.variant_id)),
        channel=channel.channel,
        collection_id=channel.collection_id,
        variant_id=variant.variant_id,
        retriever_id=_root_str(channel.retriever_id),
        backend_id=channel.backend_id,
        collection_alias=channel.collection_alias,
        embedding_profile_hash=channel.embedding_profile_hash,
        index_generation_seen=[],
        status=status,
        took_ms=0,
        returned=0,
        total_hits=None,
        truncated=False,
        error=error,
        candidates=[],
    )


def _degraded_entry(run: ChannelRun) -> DegradedEntry:
    channel_value = str(getattr(run.channel, "value", run.channel))
    reason = DegradedReason.timeout if run.status == ChannelRunStatus.timeout else DegradedReason.unavailable
    return DegradedEntry(component=DegradedComponent(f"channel.{channel_value}"), reason=reason)


async def run_one(
    channel: ChannelPlan,
    variant: RewrittenQuery,
    query_vectors: QueryVectors,
    plan: QueryPlan,
    ctx: StageContext,
    *,
    retrievers: Mapping[str, Retriever],
) -> ChannelRun:
    """런 하나(§2.1 삼중항) 실행: 리트리버를 찾아 `ChannelRunInput`을 만들고 `retriever.run`을 호출한다."""
    retriever = retrievers[_root_str(channel.retriever_id)]
    inp = ChannelRunInput(
        channel=channel,
        variant=variant,
        query_vectors=query_vectors,
        query_text=_query_text(channel, variant, plan),
        filters=plan.filters,
        exclude_ids=tuple(_root_str(cid) for cid in (plan.exclude_ids or ())),
        security=plan.security_context,
        payload_slim_keys=PAYLOAD_SLIM_KEYS,
        lexical_terms=tuple(plan.lexical_terms),
    )
    return await retriever.run(inp, ctx)


def _build_candidate_set(
    plan: QueryPlan,
    channel_runs: Sequence[ChannelRun],
    degraded: Sequence[DegradedEntry],
    *,
    now: datetime,
    took_ms: int,
) -> CandidateSet:
    total_unique = len({_root_str(c.record_id) for run in channel_runs for c in run.candidates})
    return CandidateSet(
        schema_version="1.0.0",
        schema_type="CandidateSet",
        tenant_id=plan.tenant_id,
        collection_ids=plan.collection_ids,
        producer=Producer(
            plugin_id=PLUGIN_ID,
            plugin_version=PLUGIN_VERSION,
            config_hash=hash_of("config", "{}"),
            image_digest=None,
            model_ids=None,
        ),
        warnings=[],
        degraded=[*plan.degraded, *degraded],
        created_at=_rfc3339_ms(now),
        candidate_set_id=str(ULID()),
        plan_id=plan.plan_id,
        query_id=plan.query_id,
        channel_runs=list(channel_runs),
        filters_applied=FiltersApplied(
            security=plan.filters.security,
            strategy=plan.filters.strategy,
            user=plan.filters.user,
            self_query=plan.filters.self_query,
            effective_hash=plan.filters.effective_hash,
        ),
        security_context_hash=_security_context_hash(plan.security_context),
        total_unique=total_unique,
        total_latency_ms=took_ms,
    )


async def retrieve_once(
    plan: QueryPlan,
    query_vectors: Mapping[str, QueryVectors],
    ctx: StageContext,
    *,
    retrievers: Mapping[str, Retriever],
    concurrency: int = DEFAULT_CONCURRENCY,
) -> CandidateSet:
    """§2.2 `retrieve_once` 그대로: 런을 `asyncio.gather`로 병렬 실행하고 `CandidateSet`을 조립한다.

    `query_vectors`는 `variant_id → QueryVectors`(호출자가 §8.1 5단계에서 미리 계산). 세마포어
    `concurrency`가 동시 실행 상한이고, 런마다 `channel.timeout_ms`의 `asyncio.wait_for`가 걸린다.
    시도할 런이 아예 없으면(`route=no_retrieval` 등) 빈 `CandidateSet`을 돌려준다 — 실패가 아니다.
    `retrieve.security_context_missing`·`contract.violation`은 부분 실패로 감싸지 않고 그대로 다시
    던진다(전자는 계약 위반 E7, 후자는 재시도로 고쳐지지 않는 사용자 입력 오류). 시도한 런이 하나
    이상인데 성공 런이 하나도 없으면 `retrieve.unavailable`을 던진다.
    """
    started = ctx.now()
    runs: list[tuple[ChannelPlan, RewrittenQuery]] = [
        (channel, variant)
        for channel in plan.channels
        if channel.enabled
        for variant in plan.rewritten_queries
        if channel.channel in variant.channels
    ]
    if not runs:
        # `route=no_retrieval`(또는 모든 채널이 꺼짐)이면 시도할 런이 아예 없다 — "성공한 런이
        # 없다"(retrieve.unavailable, 503)와는 다른 상황이라 실패시키지 않고 빈 CandidateSet을
        # 낸다(리뷰 지적: 잡담 질의가 503으로 죽지 않고 pack에서 sufficiency=not_needed가 되게 함).
        took_ms = max(0, int((ctx.now() - started).total_seconds() * 1000))
        return _build_candidate_set(plan, _disabled_runs(plan), [], now=ctx.now(), took_ms=took_ms)
    semaphore = asyncio.Semaphore(concurrency)

    async def guarded(channel: ChannelPlan, variant: RewrittenQuery) -> ChannelRun:
        vectors = query_vectors.get(_root_str(variant.variant_id), QueryVectors())
        async with semaphore:
            return await asyncio.wait_for(
                run_one(channel, variant, vectors, plan, ctx, retrievers=retrievers),
                timeout=channel.timeout_ms / 1000,
            )

    gathered = await asyncio.gather(*(guarded(channel, variant) for channel, variant in runs), return_exceptions=True)

    channel_runs: list[ChannelRun] = _disabled_runs(plan)
    for (channel, variant), outcome in zip(runs, gathered, strict=True):
        if isinstance(outcome, ChannelRun):
            channel_runs.append(outcome)
        elif isinstance(outcome, StageError):
            if outcome.code in _NON_MASKABLE_CODES:
                raise outcome  # 계약 위반(E7)·사용자 입력 오류 — 부분 실패로 감싸지 않고 그대로 던진다
            channel_runs.append(_failed_run(channel, variant, outcome.code, ChannelRunStatus.error))
        elif isinstance(outcome, TimeoutError):
            channel_runs.append(_failed_run(channel, variant, _CHANNEL_TIMEOUT, ChannelRunStatus.timeout))
        elif isinstance(outcome, BaseException):
            channel_runs.append(_failed_run(channel, variant, _BACKEND_ERROR, ChannelRunStatus.error))

    ok = [run for run in channel_runs if run.status == ChannelRunStatus.ok]
    if not ok:
        raise StageError(_RETRIEVE_UNAVAILABLE, stage="retrieve", retryable=True, detail="no channel run succeeded")

    degraded = [
        _degraded_entry(run) for run in channel_runs if run.status in (ChannelRunStatus.timeout, ChannelRunStatus.error)
    ]
    took_ms = max(0, int((ctx.now() - started).total_seconds() * 1000))
    return _build_candidate_set(plan, channel_runs, degraded, now=ctx.now(), took_ms=took_ms)
