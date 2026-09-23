"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from .. import common_types
from .QueryPlan.pack import tokenizer as tokenizer_1
from .QueryPlan.postprocess import parent_expand as parent_expand_1


class RewrittenQuery(BaseModel):
    """
    질의 변형. original 은 weight 1.0·variant_id = query_id; 변형은 fusion.variant_query_weight. channels ⊆ enabled 채널(route≠no_retrieval 이면 1개 이상, no_retrieval 이면 빈 배열 — 최상위 allOf). 벡터 런 임베딩 입력은 original 이면 QueryPlan.dense_query_text, 그 외는 text.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    variant_id: common_types.Ulid
    text: str = Field(..., max_length=8000, min_length=1)
    role: common_types.QueryRole
    weight: float = Field(..., gt=0.0, le=1.0)
    channels: list[common_types.Channel]


class SubQuery(BaseModel):
    """
    route=multi 분해 질의. sub_query_id 는 rewritten_queries[role=sub_query].variant_id 와 같다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    sub_query_id: common_types.Ulid
    text: str = Field(..., max_length=4000, min_length=1)
    depends_on: list[common_types.Ulid]


class LexicalTerm(BaseModel):
    """
    형태소 키워드. 사용자 사전 가중 1.5.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    term: str = Field(..., max_length=128, min_length=1)
    weight: float = Field(..., gt=0.0)
    tag: str = Field(
        ...,
        description="분석기 품사 태그(NNG, NNP, SL, SN) 또는 USER_DICT",
        pattern="^[A-Z][A-Z0-9_]{0,15}$",
    )


class ChannelPlan(BaseModel):
    """
    채널 × 컬렉션 런 정의. enabled=false 항목도 유지(감사).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    channel: common_types.Channel
    collection_id: common_types.Ulid
    retriever_id: common_types.PluginId
    backend_id: common_types.PluginId
    collection_alias: str = Field(
        ...,
        description="col_{collection_id}_vec | col_{collection_id}_lex(바이블 §13.4)",
        max_length=128,
        min_length=1,
    )
    embedding_profile_hash: common_types.Hex64
    index_generation_min: int = Field(..., ge=0)
    top_k: int = Field(..., description="채널·컬렉션당 후보 수. ≥ pack.k_max", ge=1)
    timeout_ms: int = Field(..., ge=1)
    weight: float = Field(..., description="= fusion.weights[channel]", ge=0.0)
    embedding_space_id: common_types.Hex64 | None = Field(None, description="선택(N). 벡터 채널의 공간 ID")
    query_vector_ref: str | None = Field(
        None,
        description="선택(N). 이 채널·공간의 original 변형 질의 벡터 캐시 키. embedding_space_id 와 dense_query_text 에서 유도 가능하므로 플래너는 기본 생략(retrieve 가 유도; 문서 §8.2·§11); 유도식이 다른 플러그인 채널만 채운다",
        pattern="^qemb:[0-9a-f]{64}:[0-9a-f]{64}$",
    )
    enabled: bool


class Weights(RootModel[float]):
    root: float = Field(..., ge=0.0)


class FusionPlan(BaseModel):
    """
    융합 설정(ADR-0013). k 필수. weights 키 = enabled 채널 집합(route=no_retrieval 이면 빈 객체, 그 외 1개 이상 — 최상위 allOf).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    method: common_types.FusionMethod
    k: int = Field(..., ge=1)
    weights: dict[str, Weights]
    variant_query_weight: float = Field(..., gt=0.0, le=1.0)


class HydratePlan(BaseModel):
    """
    fuse 뒤 payload 1회 배치 조회(ADR-0034). top_n ≥ max(rerank.top_n_in, pack.k_max).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    top_n: int = Field(
        ...,
        description="fused 상위 N. 상한 100 = RankedSet.results maxItems(바이블 §5.1; 10 RS-12 candidates_out ≤ hydrate.top_n ≤ 100)",
        ge=1,
        le=100,
    )
    backend_id: common_types.PluginId
    with_vectors: bool


class RerankPlan(BaseModel):
    """
    크로스인코더 리랭크. enabled=false 여도 프로파일 값은 유지된다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    enabled: bool
    plugin_id: common_types.PluginId
    model_id: common_types.ModelId
    backend: common_types.RerankBackend
    response_schema: common_types.RerankResponseSchema
    top_n_in: int = Field(..., ge=1)
    top_n_out: int = Field(..., ge=1)
    max_tokens_per_text: int = Field(..., ge=1)
    timeout_ms: int = Field(..., ge=1)
    normalization: common_types.ScoreNormalization
    instruction: str | None = Field(
        None,
        description="선택(N). 지시형 리랭커 프롬프트",
        max_length=1024,
        min_length=1,
    )


class LateInteractionRerankPlan(BaseModel):
    """
    2단 리랭크 1단(MaxSim), O-04 실험 슬롯(ADR-0010).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    enabled: bool
    model_id: common_types.ModelId
    top_n_in: int = Field(..., ge=1)
    top_n_out: int = Field(..., ge=1)


class RelevanceGate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    tau: float = Field(..., ge=0.0, le=1.0)


class Minhash(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    num_perm: int = Field(..., ge=1)
    seed: int
    scheme: str = Field(..., min_length=1)
    threshold: float = Field(..., ge=0.0, le=1.0)


class Dedup(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    cosine_threshold: float = Field(..., ge=0.0, le=1.0)
    minhash: Minhash


class Mmr(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    lambda_: float = Field(..., alias="lambda", ge=0.0, le=1.0)


class SentenceWindow(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    enabled: bool
    n: int = Field(..., ge=0)


class Compress(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    enabled: bool
    method: str | None = Field(..., min_length=1)


class ConfidenceTiers(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    high: float = Field(..., ge=0.0, le=1.0)
    medium: float = Field(..., ge=0.0, le=1.0)


class LatencyBudget(BaseModel):
    """
    남은 지연 예산(ms). plan + retrieve + rerank + postprocess + pack ≤ total.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    total: int = Field(..., ge=0)
    plan: int = Field(..., ge=0)
    retrieve: int = Field(..., ge=0)
    rerank: int = Field(..., ge=0)
    postprocess: int = Field(..., ge=0)
    pack: int = Field(..., ge=0)


class PlanBudget(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    max_tool_calls: int = Field(..., ge=0)
    llm_calls_allowed: bool


class CacheKeys(BaseModel):
    """
    Valkey 키(바이블 §13.4). query_embedding 은 original 변형·첫 활성 벡터 채널 공간 기준이며 활성 벡터 채널이 없으면(no_retrieval, mode=lexical, 임베딩 불가) null. self_query 는 정규식 self-query 면 null.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    query_embedding: str | None = Field(
        ...,
        description="Y(nullable). qemb:{embedding_space_id}:{blake3_hex(utf8(dense_query_text))}",
        pattern="^qemb:[0-9a-f]{64}:[0-9a-f]{64}$",
    )
    plan: str = Field(
        ...,
        description='plan:{tenant_id}:{profile_hash}:{H("plan", normalized_query, sorted collection_ids, filters.effective_hash, profile_hash, H("principals", *sorted(principals)), request_options_hash)}(문서 §8.1; 여섯째 part 는 잠정, 미해결 이슈 16)',
        pattern="^plan:[0-9A-HJKMNP-TV-Z]{26}:[0-9a-f]{64}:[0-9a-f]{64}$",
    )
    self_query: str | None = Field(..., pattern="^sq:[0-9A-HJKMNP-TV-Z]{26}:[0-9a-f]{64}$")


class ParentExpand(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    enabled: bool
    ratio_threshold: float = Field(..., ge=0.0, le=1.0)
    max_parent_tokens: int = Field(..., ge=1)
    text_store: parent_expand_1.TextStore


class PostprocessPlan(BaseModel):
    """
    후처리 설정. order 는 고정 순서 relevance_gate → dedup → mmr → parent_expand → dedup → sentence_window → compress 의 부분열(Pydantic 검증).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    order: list[common_types.PostprocessStep] = Field(..., max_length=7, min_length=1)
    relevance_gate: RelevanceGate
    dedup: Dedup
    mmr: Mmr
    parent_expand: ParentExpand
    sentence_window: SentenceWindow
    compress: Compress


class Tokenizer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    provider: tokenizer_1.Provider
    model: str = Field(..., max_length=128, min_length=1)
    name: common_types.TokenizerId


class PackPlan(BaseModel):
    """
    패킹 설정. 내부 순서 acl_recheck → budget_cut → reorder → citation_align 은 고정(바이블 §8.2).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    k_max: int = Field(
        ...,
        description="최종 항목 수 상한 = 프로파일 query.pack.k_max(바이블 §7.2 standard 20). QueryRequest.top_k 와 결합하지 않는다(바이블 §5.5 별개·§16 GL-08; 문서 미해결 이슈 1). 상한 20 = ContextPack.budget.k_max·items maxItems(바이블 §5.1 초안 한계 20; 11 §2.2 가 이 값을 budget.k_max 로 복사)",
        ge=1,
        le=20,
    )
    max_context_tokens: int = Field(..., ge=1)
    reserved_answer_tokens: int = Field(..., ge=0)
    tokenizer: Tokenizer
    count_method: common_types.CountMethod
    renderer: common_types.Renderer
    ordering: common_types.OrderingStrategy
    table_format_preference: list[common_types.TableFormat] = Field(..., max_length=3, min_length=1)
    overflow_policy: list[common_types.OverflowPolicy] = Field(..., max_length=3, min_length=1)
    expose_confidence: bool
    confidence_tiers: ConfidenceTiers


class QueryPlan(BaseModel):
    """
    plan 스테이지 출력(바이블 §5.5). QueryRequest + 서버 주입 SecurityContext 로부터 만든 질의 이해 결과이며 retrieve·fuse·hydrate·rerank·postprocess·pack 은 이를 재해석하지 않는다. 질의 측 봉투(schema_version, schema_type, tenant_id, collection_ids, producer, warnings, degraded, created_at). filters 는 security(제거·완화 불가) ∧ strategy(플래너 결정) ∧ user ∧ self_query(relaxable_keys 순서로만 완화) 4묶음(바이블 §10.2). 인프로세스 값이며 산출물로 저장하지 않는다(explain 시 응답 포함, ≤ 32KB). 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/09-query-request-and-query-plan.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description="계약 버전. 1.x 만 수용",
        pattern="^1\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$",
    )
    schema_type: Literal["QueryPlan"] = Field(..., description="봉투. PascalCase 타입명")
    tenant_id: common_types.Ulid = Field(..., description="봉투. = security_context.tenant_id")
    collection_ids: list[common_types.Ulid] = Field(
        ...,
        description="봉투(질의 측 복수). SecurityContext.collection_ids ∩ QueryRequest.collection_ids",
        max_length=20,
        min_length=1,
    )
    producer: common_types.Producer = Field(
        ...,
        description='플래너 지문. plugin_id = query_transformer.pipeline(초안 합성 ID — 바이블 §6.1 규약에 pipeline 구현체는 없음, 미해결 이슈 17), config_hash = H("config", canonical_json(query.transform)), image_digest = null, model_ids 는 quality LLM 모델(없으면 빈 배열)',
    )
    warnings: list[common_types.Warning] = Field(..., description="봉투. 빈 배열 허용")
    degraded: list[common_types.DegradedEntry] = Field(
        ...,
        description="봉투(질의 측). planner_llm/llm_failed, fusion/profile_mismatch, channel.*/analyzer_mismatch|capability_unsupported|latency_budget, multi_query|rerank|hydrate/latency_budget, query_embedding/unavailable, parent_expand/skipped_by_policy. self_query_filter/filter_relaxed|latency_budget 는 retrieve 시점 판정이라 CandidateSet 봉투에 기록된다(플랜 불변, 문서 §5.3)",
    )
    created_at: common_types.DateTime = Field(..., description="플랜 생성 시각(security_context.as_of 와 같거나 이후)")
    plan_id: common_types.Ulid = Field(..., description="서버 발급")
    query_id: common_types.Ulid = Field(..., description="= QueryRequest.query_id")
    security_context: common_types.SecurityContext = Field(
        ..., description="서버 주입·읽기 전용(ADR-0027). filters.security 의 원천"
    )
    profile_id: common_types.ProfileId = Field(
        ...,
        description="kebab-case(바이블 §6.1). = 해소된 프로파일의 profile_id(team_assignment 반영)",
    )
    profile_hash: common_types.Hex64 = Field(..., description='H("profile", canonical_json(해소된 프로파일))')
    original_query: str = Field(..., description="= QueryRequest.query", max_length=4000, min_length=1)
    normalized_query: str = Field(
        ...,
        description="NFC·공백 정규화 + Kiwi 오타·띄어쓰기 교정(mecab-ko 는 교정 생략)",
        max_length=4000,
        min_length=1,
    )
    dense_query_text: str = Field(
        ...,
        description="original 변형의 벡터 런(dense·sparse) 임베딩 입력. default·fast 는 = normalized_query, 치환형 HyDE(quality)는 가상 문서(바이블 §5.5). 그 외 변형의 벡터 런은 rewritten_queries[].text 를 임베딩한다",
        max_length=8000,
        min_length=1,
    )
    analyzer_id: common_types.AnalyzerId = Field(
        ...,
        description="{engine}:{version}:{dictionary}(바이블 §6.1). 컬렉션 값(CollectionSpec.analyzer_id = IndexRecord.analyzer_id)과 불일치 → degraded{channel.lexical, analyzer_mismatch}",
    )
    dictionary_hash: common_types.Hex64 = Field(
        ..., description='H("dict", *sorted(entry 정규화 행))(바이블 §6.2); 컬렉션 값'
    )
    route: common_types.Route
    complexity: common_types.Complexity | None = Field(
        None,
        description="Adaptive-RAG. 있으면 route 와 대응(no_retrieval↔no_retrieval, single_step↔single, multi_step↔multi)",
    )
    strategy: common_types.Strategy = Field(..., description="기본 hybrid; filters.strategy 를 결정")
    rewritten_queries: list[RewrittenQuery] = Field(
        ...,
        description="original(weight 1.0, variant_id = query_id) 항상 포함, 변형은 fusion.variant_query_weight",
        max_length=16,
        min_length=1,
    )
    sub_queries: list[SubQuery] | None = Field(
        None,
        description="route=multi 일 때 필수, 그 외 부재",
        max_length=16,
        min_length=1,
    )
    lexical_terms: list[LexicalTerm] = Field(
        ...,
        description="Kiwi/mecab-ko NNG·NNP·SL·SN + 사용자 사전(가중 1.5). 빈 배열 허용",
        max_length=128,
    )
    filters: PlanFilters
    channels: list[ChannelPlan] = Field(
        ...,
        description="채널 × 컬렉션 단위(항목은 enabled=false 여도 유지). 질의 변형은 rewritten_queries[].channels 로 결합되어 런이 된다. route=no_retrieval 이면 모든 항목 enabled=false(최상위 allOf). 실효 상한은 QueryPlan 32KB 한계가 정한다(문서 §11)",
        max_length=140,
        min_length=1,
    )
    fusion: FusionPlan
    hydrate: HydratePlan
    rerank: RerankPlan
    late_interaction_rerank: LateInteractionRerankPlan | None = None
    postprocess: PostprocessPlan
    pack: PackPlan
    latency_budget_ms: LatencyBudget
    budget: PlanBudget
    cache_keys: CacheKeys
    explain: bool = Field(..., description="= QueryRequest.explain or false")
    planner_fingerprint: common_types.Hex64 = Field(
        ...,
        description='H("planner", *sorted(f"{plugin_id}@{plugin_version}:{config_hash}" for transform in query.transform), profile_hash)',
    )
    session_id: common_types.Ulid | None = Field(
        None,
        description="선택(N). = QueryRequest.session_id. 바이블 §5.5 미등재(미해결 이슈 5)",
    )
    exclude_ids: list[common_types.Hex64] | None = Field(
        None,
        description="선택(N). QueryRequest.exclude_ids ∪ cursor 누적. retrieve 가 must_not chunk_id 로 적용. 바이블 §5.5 미등재(미해결 이슈 5)",
        max_length=1000,
        min_length=1,
    )
    experiment_id: str | None = Field(
        None,
        description="선택(N). 요청 값 복사. 바이블 §5.5 미등재(미해결 이슈 5)",
        max_length=128,
        min_length=1,
    )
    team_assignment: str | None = Field(
        None,
        description="선택(N). 요청 값 복사. 바이블 §5.5 미등재(미해결 이슈 5)",
        max_length=64,
        min_length=1,
    )


class PlanFilters(BaseModel):
    """
    필터 4묶음. security ∧ strategy ∧ user ∧ self_query. relaxable_keys 는 FilterableField 타입이므로 보안·전략 키를 담을 수 없다(E6).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    security: common_types.SecurityFilter
    strategy: common_types.StrategyFilter
    user: common_types.FilterNode | None = Field(
        ...,
        description="Y(nullable). QueryRequest.filters 원형(page 변환 전·완화 전). 실전송 트리는 CandidateSet.filters_applied.user 가 기록",
    )
    self_query: common_types.FilterNode | None = Field(
        ...,
        description="Y(nullable). 플래너 추출 필터(완화 전). 실전송 트리는 CandidateSet.filters_applied.self_query 가 기록",
    )
    relaxable_keys: list[common_types.FilterableField1] = Field(
        ...,
        description="0건 시 순서대로 제거할 사용자·self-query 필드. user·self_query 리프에 존재하는 필드만",
        max_length=32,
    )
    effective_hash: common_types.Hex64 = Field(
        ...,
        description='H("filters", canonical_json(계획 필터 트리: QueryPlan.filters 에 저장된 security + strategy + user + self_query 그대로, page 변환·완화 전))(바이블 §6.2 식의 계획 시점 값). QueryPlan 과 함께 불변이며 재계산·갱신하지 않는다; 실전송 트리(page 변환·완화 반영)의 해시는 CandidateSet.filters_applied.effective_hash 가 기록(문서 §5.4). as_of 는 바인드 이름 ":as_of" 로 직렬화한다 — 바이블 §10.2 바인드 파라미터 표기에 근거한 잠정 해석(미해결 이슈 3(a))',
    )


QueryPlan.model_rebuild()
