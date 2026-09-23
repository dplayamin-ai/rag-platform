"""규칙 경로 플래너 — `QueryRequest` + `SecurityContext`를 받아 `QueryPlan`을 확정한다(`plan` 스테이지).

역할: 04-pipelines/14 §1.1 `finalize(draft)`의 규칙 경로(LLM 없음) 구현 — 정규화·라우팅·필터 3층을
거쳐 채널(`dense`+`lexical`)·`fusion`(rrf, k=60)·`hydrate`·`rerank`·`postprocess`·`pack`·예산·캐시
키를 채운 `QueryPlan`을 만든다. `WP-404-render-and-query-pipeline.md` §3 `Planner` 프로토콜
(`(request, security) -> QueryPlan`)과 맞춘 `plan()`이 진입점이다.
설계 근거: 04-pipelines/14 §1.1(파이프·`finalize`)·§9(채널·k 산정·사전 저하 일부)·§10(캐시 키 식);
바이블 §4.3 `plan` 행, §5.5 `QueryRequest`/`QueryPlan` 표, §10.2 필터 불변식. `CollectionSpec`/
`IndexBackendCapabilities`/`profiles.loader` 미배선(이 WP 읽기 예산 밖·바이블 §12 계층상 `retrieval`
은 `profiles`를 모른다) — `PlannerDefaults`가 `lite.yaml` 값을 사본으로 든다(WP-401 open issue).
구성: `PlanDraft` — 내부 초안(계약 아님, 04-pipelines/14 §1.1); `PlannerDefaults` — 규칙 경로 기본값;
`plan(request, security, *, plan_id=None, defaults=None) -> QueryPlan` — 진입점.
불변식·주의: `security=None`이면 `plan.security_context_missing`, 요청∩보안 컬렉션=∅이면
`plan.collection_forbidden`, `QueryPlan` 생성 실패는 `contract.violation`으로 격상(§1.1). `created_at`
은 `security_context.as_of`("서버 now()")를 그대로 써 `datetime.now()` 금지 규칙을 지킨다(banned-api).
정규화·라우팅은 `rag_platform.korean.normalize`/`rag_platform.korean.rule_router`(바이블 §12상
`retrieval`도 import할 수 있는 `korean` 층)를 직접 호출한다 — `adapters/query/korean_normalize.py`·
`rule_router.py`는 같은 순수 함수를 재노출해 `PluginRegistry` 등록용 Stage 5멤버 래퍼로 쓴다(F4 배치
검증으로 기존 `retrieval → adapters` 계층 위반을 해소).
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_planner.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError
from ulid import ULID

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.query_plan import (
    CacheKeys,
    ChannelPlan,
    Compress,
    ConfidenceTiers,
    Dedup,
    FusionPlan,
    HydratePlan,
    LatencyBudget,
    LexicalTerm,
    Minhash,
    Mmr,
    PackPlan,
    ParentExpand,
    PlanBudget,
    PostprocessPlan,
    QueryPlan,
    RelevanceGate,
    RerankPlan,
    RewrittenQuery,
    SentenceWindow,
    Tokenizer,
    Weights,
)
from rag_platform.contracts.query_plan.QueryPlan.pack import tokenizer as qp_tokenizer
from rag_platform.contracts.query_plan.QueryPlan.postprocess import parent_expand as qp_parent_expand
from rag_platform.korean.normalize import normalize_query
from rag_platform.korean.rule_router import adopt_strategy, classify_intent, route_for_intent
from rag_platform.retrieval.filters import build_plan_filters, canonical_json, validate_and_normalize_user_filter
from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from rag_platform.contracts.query_request import QueryRequest

__all__ = ["PlanDraft", "PlannerDefaults", "plan"]

#: `PlanDraft`의 채널x컬렉션 알리아스 접미(바이블 §13.4) — 백엔드 물리 배치를 따른다(`qdrant`는
#: `_vec`, `opensearch`는 `_lex`; `lite`는 `sparse_bm25`도 qdrant라 `_vec`).
_OPENSEARCH_BACKEND_ID = "index_backend.opensearch"
#: `query.transform`(규칙 경로 고정) — `Producer.config_hash`/`planner_fingerprint` 입력.
_TRANSFORM_PLUGIN_IDS: tuple[str, ...] = ("query_transformer.korean_normalize", "query_transformer.rule_router")
_TRANSFORM_PLUGIN_VERSIONS: tuple[str, ...] = ("0.1.0", "0.1.0")
_PRODUCER_CONFIG_HASH = hash_of("config", canonical_json(list(_TRANSFORM_PLUGIN_IDS)))
#: postprocess 고정 순서(`lite.yaml` 사본) — `sentence_window`/`compress`는 이 WP 기본 꺼짐.
_POSTPROCESS_ORDER: tuple[ct.PostprocessStep, ...] = (
    ct.PostprocessStep.relevance_gate,
    ct.PostprocessStep.dedup,
    ct.PostprocessStep.mmr,
    ct.PostprocessStep.parent_expand,
    ct.PostprocessStep.dedup,
)


@dataclass
class PlanDraft:
    """`plan` 파이프 내부 초안(계약 아님, 04-pipelines/14 §1.1) — 향후 Stage 기반 파이프 배선용 자리.

    `plan()`은 이 형태를 스레딩하지 않고 로컬 변수로 직접 다룬다; `korean_normalize.
    KoreanNormalizeTransformer`/`rule_router.RuleRouterTransformer`의 `run(draft, ctx)`가 이
    형태를 소비·생산하도록 필드명을 맞춰 두었다.
    """

    request: QueryRequest
    security: ct.SecurityContext
    original_query: str = ""
    normalized_query: str = ""
    lexical_view: str = ""
    lang: str = "ko"
    intent: str = "natural_question"
    route: ct.Route = ct.Route.single
    complexity: ct.Complexity = ct.Complexity.single_step
    strategy: ct.Strategy = ct.Strategy.hybrid
    lexical_terms: list[LexicalTerm] = field(default_factory=list)
    analyzer_id: str = ""
    dictionary_hash: str = ""
    degraded: list[ct.DegradedEntry] = field(default_factory=list)


@dataclass(frozen=True)
class ChannelDefault:
    """`PlannerDefaults.channels`의 한 항목 — `lite.yaml query.channels[]`의 사본."""

    channel: ct.Channel
    retriever_id: str
    backend_id: str
    top_k: int
    timeout_ms: int


@dataclass(frozen=True)
class PlannerDefaults:
    """규칙 경로 기본값(`lite.yaml` 사본, WP-401 §7) — `CollectionSpec`/`profiles.loader` 미배선 자리.

    `profile_hash`/채널의 `embedding_profile_hash`는 진짜 프로파일·컬렉션 해시가 아니라 이 WP가 만든
    플레이스홀더다(WP-401 open issue) — 바이블 §12 계층상 `retrieval`은 `profiles`를 임포트할 수 없다.
    """

    profile_id: str = "lite"
    profile_hash: str = hash_of("profile", "rag_platform.retrieval.planner.rule_path_draft.v1")
    channels: tuple[ChannelDefault, ...] = (
        ChannelDefault(ct.Channel.dense, "retriever.qdrant_dense", "index_backend.qdrant", 100, 250),
        ChannelDefault(ct.Channel.lexical, "retriever.qdrant_sparse_bm25", "index_backend.qdrant", 100, 250),
    )
    fusion_k: int = 60
    variant_query_weight: float = 0.5
    hydrate_backend_id: str = "index_backend.qdrant"
    rerank_plugin_id: str = "reranker.flashrank"
    rerank_model_id: str = "BAAI/bge-reranker-v2-m3@main"
    rerank_backend: ct.RerankBackend = ct.RerankBackend.in_process
    rerank_response_schema: ct.RerankResponseSchema = ct.RerankResponseSchema.tei
    rerank_top_n_in: int = 100
    rerank_top_n_out: int = 20
    rerank_max_tokens_per_text: int = 512
    rerank_timeout_ms: int = 300
    rerank_normalization: ct.ScoreNormalization = ct.ScoreNormalization.sigmoid
    #: 바이블 §7.2 표 `lite` 열(04-pipelines/14 §9.2도 "lite 10"으로 재확인) — F4 배치 검증으로
    #: `standard` 값(20/24,000/4,000) 오기를 `lite.yaml`과 함께 정정.
    pack_k_max: int = 10
    pack_max_context_tokens: int = 12000
    pack_reserved_answer_tokens: int = 2000
    pack_renderer: ct.Renderer = ct.Renderer.anthropic_search_result
    pack_ordering: ct.OrderingStrategy = ct.OrderingStrategy.litm_alternating
    pack_tokenizer_provider: qp_tokenizer.Provider = qp_tokenizer.Provider.anthropic
    pack_tokenizer_model: str = "claude-placeholder"
    pack_count_method: ct.CountMethod = ct.CountMethod.approximate
    pack_table_format_preference: tuple[ct.TableFormat, ...] = (
        ct.TableFormat.html,
        ct.TableFormat.markdown,
        ct.TableFormat.json,
    )
    pack_overflow_policy: tuple[ct.OverflowPolicy, ...] = (
        ct.OverflowPolicy.downgrade_tables,
        ct.OverflowPolicy.truncate,
    )
    pack_confidence_high: float = 0.7
    pack_confidence_medium: float = 0.4
    latency_total_ms: int = 800
    latency_plan_ms: int = 60
    latency_retrieve_ms: int = 120
    latency_rerank_ms: int = 250
    latency_postprocess_ms: int = 60
    latency_pack_ms: int = 40
    default_max_tool_calls: int = 4


_DEFAULT_PLANNER_DEFAULTS = PlannerDefaults()


def _selected_collection_ids(request: QueryRequest, security: ct.SecurityContext) -> list[ct.Ulid]:
    """요청 컬렉션 ∩ 보안 컬렉션(09 §5.5 "SecurityContext.collection_ids와 교집합")."""
    security_ids = {cid.root for cid in security.collection_ids}
    return [cid for cid in request.collection_ids if cid.root in security_ids]


def _channel_types_for_mode(mode: ct.RetrievalMode | None, defaults: PlannerDefaults) -> frozenset[ct.Channel]:
    """`QueryRequest.mode`로 이 WP가 지원하는 두 채널(`dense`, `lexical`) 중 활성 집합을 고른다.

    `mode=sparse`(학습형 sparse 채널)는 이 규칙 경로의 2채널 구성(`dense`+`lexical`=`sparse_bm25`)에
    대응하는 채널이 없어 `hybrid`와 같이 둘 다 켠다(DEFERRED — WP-401 open issue).
    """
    all_channels = frozenset(cd.channel for cd in defaults.channels)
    if mode is None or mode in (ct.RetrievalMode.hybrid, ct.RetrievalMode.sparse):
        return all_channels
    if mode == ct.RetrievalMode.dense:
        return frozenset({ct.Channel.dense})
    return frozenset({ct.Channel.lexical})


def _build_channels(
    collection_ids: list[ct.Ulid],
    defaults: PlannerDefaults,
    *,
    enabled_types: frozenset[ct.Channel],
    route_enabled: bool,
) -> list[ChannelPlan]:
    """컬렉션 x `{dense, lexical}` 채널 항목을 만든다(09 §5.5 "비활성 채널도 항목은 유지")."""
    channels: list[ChannelPlan] = []
    for collection_id in collection_ids:
        for channel_default in defaults.channels:
            alias_suffix = "_lex" if channel_default.backend_id == _OPENSEARCH_BACKEND_ID else "_vec"
            channels.append(
                ChannelPlan(
                    channel=channel_default.channel,
                    collection_id=collection_id,
                    retriever_id=channel_default.retriever_id,
                    backend_id=channel_default.backend_id,
                    collection_alias=f"col_{collection_id.root}{alias_suffix}",
                    embedding_profile_hash=defaults.profile_hash,
                    index_generation_min=0,
                    top_k=max(channel_default.top_k, defaults.pack_k_max),
                    timeout_ms=channel_default.timeout_ms,
                    weight=1.0,
                    embedding_space_id=None,
                    query_vector_ref=None,
                    enabled=route_enabled and channel_default.channel in enabled_types,
                )
            )
    return channels


def _build_fusion(defaults: PlannerDefaults, enabled_channel_types: frozenset[ct.Channel]) -> FusionPlan:
    """`fusion.method=rrf, k=60`(바이블 §3.2 O-01, ADR-0013)."""
    weights = {channel.value: Weights(1.0) for channel in enabled_channel_types}
    return FusionPlan(
        method=ct.FusionMethod.rrf,
        k=defaults.fusion_k,
        weights=weights,
        variant_query_weight=defaults.variant_query_weight,
    )


def _build_rerank(defaults: PlannerDefaults, *, enabled: bool) -> RerankPlan:
    """리랭크 계획 — `enabled=False`여도 프로파일 값은 유지한다(09 §6.6)."""
    return RerankPlan(
        enabled=enabled,
        plugin_id=defaults.rerank_plugin_id,
        model_id=defaults.rerank_model_id,
        backend=defaults.rerank_backend,
        response_schema=defaults.rerank_response_schema,
        top_n_in=defaults.rerank_top_n_in,
        top_n_out=max(defaults.rerank_top_n_out, defaults.pack_k_max),
        max_tokens_per_text=defaults.rerank_max_tokens_per_text,
        timeout_ms=defaults.rerank_timeout_ms,
        normalization=defaults.rerank_normalization,
        instruction=None,
    )


def _build_hydrate(defaults: PlannerDefaults, rerank: RerankPlan, *, rerank_enabled: bool) -> HydratePlan:
    """`hydrate.top_n = rerank.top_n_in`(리랭크 켬) 또는 `k_max x 2`(끔, §9.2)."""
    top_n = rerank.top_n_in if rerank_enabled else defaults.pack_k_max * 2
    return HydratePlan(top_n=top_n, backend_id=defaults.hydrate_backend_id, with_vectors=False)


def _build_postprocess() -> PostprocessPlan:
    """후처리 계획(`lite.yaml` 사본) — `sentence_window`/`compress`는 기본 꺼짐."""
    return PostprocessPlan(
        order=list(_POSTPROCESS_ORDER),
        relevance_gate=RelevanceGate(tau=0.3),
        dedup=Dedup(cosine_threshold=0.95, minhash=Minhash(num_perm=128, seed=42, scheme="affine32", threshold=0.8)),
        mmr=Mmr(**{"lambda": 0.7}),
        parent_expand=ParentExpand(
            enabled=True,
            ratio_threshold=0.5,
            max_parent_tokens=2048,
            text_store=qp_parent_expand.TextStore.artifact_store,
        ),
        sentence_window=SentenceWindow(enabled=False, n=2),
        compress=Compress(enabled=False, method=None),
    )


def _build_pack(defaults: PlannerDefaults) -> PackPlan:
    """`PackPlan`(`lite.yaml` 사본) — `k_max`는 요청 `top_k`와 결합하지 않는다(09 §7.2, §16 GL-08)."""
    tokenizer_name = ct.TokenizerId(f"{defaults.pack_tokenizer_provider.value}:{defaults.pack_tokenizer_model}")
    return PackPlan(
        k_max=defaults.pack_k_max,
        max_context_tokens=defaults.pack_max_context_tokens,
        reserved_answer_tokens=defaults.pack_reserved_answer_tokens,
        tokenizer=Tokenizer(
            provider=defaults.pack_tokenizer_provider, model=defaults.pack_tokenizer_model, name=tokenizer_name
        ),
        count_method=defaults.pack_count_method,
        renderer=defaults.pack_renderer,
        ordering=defaults.pack_ordering,
        table_format_preference=list(defaults.pack_table_format_preference),
        overflow_policy=list(defaults.pack_overflow_policy),
        expose_confidence=False,
        confidence_tiers=ConfidenceTiers(high=defaults.pack_confidence_high, medium=defaults.pack_confidence_medium),
    )


def _build_latency_budget(defaults: PlannerDefaults, max_latency_ms: int | None) -> LatencyBudget:
    """`total = min(요청 budget.max_latency_ms, 프로파일 total)`(§9.3). 나머지 4단계 사다리는 DEFERRED."""
    total = defaults.latency_total_ms if max_latency_ms is None else min(defaults.latency_total_ms, max_latency_ms)
    return LatencyBudget(
        total=total,
        plan=defaults.latency_plan_ms,
        retrieve=defaults.latency_retrieve_ms,
        rerank=defaults.latency_rerank_ms,
        postprocess=defaults.latency_postprocess_ms,
        pack=defaults.latency_pack_ms,
    )


def _build_budget(request: QueryRequest, defaults: PlannerDefaults) -> PlanBudget:
    """`llm_calls_allowed=False` 고정(규칙 경로는 `quality` 변형을 지원하지 않는다, §5.3)."""
    max_tool_calls = defaults.default_max_tool_calls
    if request.budget is not None and request.budget.max_tool_calls is not None:
        max_tool_calls = request.budget.max_tool_calls
    return PlanBudget(max_tool_calls=max_tool_calls, llm_calls_allowed=False)


def _request_options(request: QueryRequest) -> dict[str, Any]:
    """`cache_keys.plan`의 `opts` part 입력(§10 "request_options" 목록)."""
    budget = request.budget
    return {
        "mode": request.mode.value if request.mode else None,
        "retrieval_variant": request.retrieval_variant.value if request.retrieval_variant else None,
        "strategy_hint": request.strategy_hint.value if request.strategy_hint else None,
        "target_model": request.target_model.model_dump(mode="json") if request.target_model else None,
        "renderer": request.renderer.value if request.renderer else None,
        "ordering_strategy": request.ordering_strategy.value if request.ordering_strategy else None,
        "include_parents": request.include_parents,
        "max_context_tokens": request.max_context_tokens,
        "budget_max_context_tokens": budget.max_context_tokens if budget else None,
        "budget_max_tool_calls": budget.max_tool_calls if budget else None,
        "conversation": [turn.model_dump(mode="json") for turn in request.conversation]
        if request.conversation
        else None,
    }


def _build_cache_keys(
    *,
    tenant_id: str,
    profile_hash: str,
    normalized_query: str,
    collection_ids: list[ct.Ulid],
    principals: list[ct.PrincipalString],
    filters_effective_hash: str,
    request: QueryRequest,
) -> CacheKeys:
    """§10 캐시 키 식 — `query_embedding`은 임베딩 공간이 미배선이라 이 WP는 항상 `null`이다."""
    sorted_collection_ids = ",".join(sorted(cid.root for cid in collection_ids))
    principals_hash = hash_of("principals", *sorted(p.root for p in principals))
    opts_hash = hash_of("opts", canonical_json(_request_options(request)))
    plan_hash = hash_of(
        "plan",
        normalized_query,
        sorted_collection_ids,
        filters_effective_hash,
        profile_hash,
        principals_hash,
        opts_hash,
    )
    return CacheKeys(query_embedding=None, plan=f"plan:{tenant_id}:{profile_hash}:{plan_hash}", self_query=None)


def plan(
    request: QueryRequest,
    security: ct.SecurityContext | None,
    *,
    plan_id: str | None = None,
    defaults: PlannerDefaults | None = None,
) -> QueryPlan:
    """`QueryRequest` + `SecurityContext`로부터 규칙 경로 `QueryPlan`을 확정한다(04-pipelines/14 §1.1).

    Args:
        request: 클라이언트 질의 요청.
        security: 서버 주입 `SecurityContext`(`None`이면 `plan.security_context_missing`).
        plan_id: 미주입 시 `ulid.ULID()`로 발급(`adapters/index/saga.py` 선례).
        defaults: 규칙 경로 기본값(`PlannerDefaults`). 생략 시 `lite.yaml` 사본 기본값.

    Returns:
        `QueryPlan` — 채널 `dense`+`lexical`, `fusion.method=rrf, k=60`, `filters.self_query=null`,
        `budget.llm_calls_allowed=false`.

    Raises:
        StageError: `plan.security_context_missing`·`plan.collection_forbidden`·
            `plan.filter_field_forbidden`·`contract.violation`(§12).
    """
    if security is None:
        code = "plan.security_context_missing"
        raise StageError(code, stage="plan", detail="SecurityContext missing (ADR-0027)")
    resolved_defaults = defaults or _DEFAULT_PLANNER_DEFAULTS

    collection_ids = _selected_collection_ids(request, security)
    if not collection_ids:
        code = "plan.collection_forbidden"
        detail = "requested collection_ids ∩ security_context.collection_ids = ∅"
        raise StageError(code, stage="plan", detail=detail)

    normalized = normalize_query(request.query)
    intent = classify_intent(
        normalized.lexical_terms, normalized.normalized_query, has_conversation=bool(request.conversation)
    )
    route, complexity = route_for_intent(intent)
    strategy, strategy_degraded = adopt_strategy(request.strategy_hint)
    user_filter, relaxable_keys = validate_and_normalize_user_filter(request.filters)
    plan_filters = build_plan_filters(
        security=security,
        strategy=strategy,
        user_filter=user_filter,
        relaxable_keys=relaxable_keys,
        collection_ids=collection_ids,
    )

    route_enabled = route != ct.Route.no_retrieval
    enabled_channel_types = _channel_types_for_mode(request.mode, resolved_defaults) if route_enabled else frozenset()
    channels = _build_channels(
        collection_ids, resolved_defaults, enabled_types=enabled_channel_types, route_enabled=route_enabled
    )
    fusion = _build_fusion(resolved_defaults, enabled_channel_types)

    # `rerank`/`hydrate`/`postprocess`/`pack`/예산은 `route=no_retrieval`이어도 "정상 계산"한다(09
    # §7.5 — `channels[].enabled`·`fusion.weights`만 강제로 끈다). `fast` 변형만 리랭크를 끈다(§9.2).
    fast_mode = request.retrieval_variant == ct.RetrievalVariant.fast
    rerank_enabled = not fast_mode
    rerank = _build_rerank(resolved_defaults, enabled=rerank_enabled)
    hydrate = _build_hydrate(resolved_defaults, rerank, rerank_enabled=rerank_enabled)
    postprocess = _build_postprocess()
    pack = _build_pack(resolved_defaults)
    max_latency_ms = request.budget.max_latency_ms if request.budget else None
    latency_budget = _build_latency_budget(resolved_defaults, max_latency_ms)
    budget = _build_budget(request, resolved_defaults)

    original_channels = sorted(enabled_channel_types, key=lambda channel: channel.value) if route_enabled else []
    rewritten_queries = [
        RewrittenQuery(
            variant_id=request.query_id,
            text=normalized.normalized_query,
            role=ct.QueryRole.original,
            weight=1.0,
            channels=original_channels,
        )
    ]

    cache_keys = _build_cache_keys(
        tenant_id=security.tenant_id.root,
        profile_hash=resolved_defaults.profile_hash,
        normalized_query=normalized.normalized_query,
        collection_ids=collection_ids,
        principals=security.principals,
        filters_effective_hash=plan_filters.effective_hash.root,
        request=request,
    )
    producer = ct.Producer(
        plugin_id="query_transformer.pipeline",
        plugin_version="0.1.0",
        config_hash=_PRODUCER_CONFIG_HASH,
        image_digest=None,
        model_ids=[],
    )
    planner_fingerprint = hash_of(
        "planner",
        *sorted(
            f"{plugin_id}@{version}:{_PRODUCER_CONFIG_HASH}"
            for plugin_id, version in zip(_TRANSFORM_PLUGIN_IDS, _TRANSFORM_PLUGIN_VERSIONS, strict=True)
        ),
        resolved_defaults.profile_hash,
    )

    try:
        return QueryPlan(
            schema_version="1.0.0",
            schema_type="QueryPlan",
            tenant_id=security.tenant_id,
            collection_ids=collection_ids,
            producer=producer,
            warnings=[],
            degraded=strategy_degraded,
            created_at=security.as_of,
            plan_id=plan_id or str(ULID()),
            query_id=request.query_id,
            security_context=security,
            profile_id=resolved_defaults.profile_id,
            profile_hash=resolved_defaults.profile_hash,
            original_query=request.query,
            normalized_query=normalized.normalized_query,
            dense_query_text=normalized.normalized_query,
            analyzer_id=normalized.analyzer_id,
            # `korean.normalize.normalize_query()`는 `sdk`를 import할 수 없어(바이블 §12) `dictionary_hash`를
            # 채우지 않는다(§0) — `H("dict")`는 `sdk.hashing`을 가진 이 계층이 직접 계산한다.
            dictionary_hash=hash_of("dict"),
            route=route,
            complexity=complexity,
            strategy=strategy,
            rewritten_queries=rewritten_queries,
            sub_queries=None,
            lexical_terms=normalized.lexical_terms,
            filters=plan_filters,
            channels=channels,
            fusion=fusion,
            hydrate=hydrate,
            rerank=rerank,
            late_interaction_rerank=None,
            postprocess=postprocess,
            pack=pack,
            latency_budget_ms=latency_budget,
            budget=budget,
            cache_keys=cache_keys,
            explain=bool(request.explain),
            planner_fingerprint=planner_fingerprint,
            session_id=request.session_id,
            exclude_ids=request.exclude_ids,
            experiment_id=request.experiment_id,
            team_assignment=request.team_assignment,
        )
    except ValidationError as exc:
        code = "contract.violation"
        raise StageError(code, stage="plan", detail=str(exc)) from exc
