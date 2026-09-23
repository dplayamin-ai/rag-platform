"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from .. import common_types
from .ContextPack import compression as compression_1
from .ContextPack.budget import tokenizer as tokenizer_1


class TokenizerSpec(BaseModel):
    """
    대상 LLM 토크나이저 3중 키(바이블 §5.5 budget.tokenizer; QueryPlan.pack.tokenizer 복사). 모델 식별자는 프로파일 값(플레이스홀더 허용)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    provider: tokenizer_1.Provider
    model: str = Field(..., description="대상 모델 식별자(예 claude-opus-5)", min_length=1)
    name: common_types.TokenizerId = Field(
        ...,
        description="tokenizer_id 형식(바이블 §6.1): hf:{repo} | tiktoken:{encoding} | anthropic:{model} | gemini:{model}. 접두는 provider에 대응(불일치는 pack.tokenizer_mismatch). Valkey tok:{name}:{H(text)} 캐시 키",
    )


class Budget(BaseModel):
    """
    토큰 예산(바이블 §5.5·§9.1 이중 카운트). 이중 제한 k_max × (max_context_tokens − reserved_answer_tokens); safety_margin은 근사 카운트에만 적용
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    tokenizer: TokenizerSpec
    count_method: common_types.CountMethod = Field(
        ...,
        description="exact_api(Anthropic count_tokens·Gemini count_tokens) / exact_local(tiktoken·HF tokenizers·Gemini LocalTokenizer) / approximate(근사 × calibration_ratio)",
    )
    calibration_ratio: float | None = Field(
        None,
        description="조건. count_method=approximate이면 골든셋 실측 exact/approx 배율(non-null 필수), 그 외 null 또는 생략(if/then/else)",
        gt=0.0,
    )
    safety_margin: float = Field(
        ...,
        description="안전 마진 비율(기본 0.10). count_method=approximate(count_api_failed 폴백 포함)일 때 근사 카운트에 얹는 보수 계수: token_count = ceil(raw × calibration_ratio × (1 + safety_margin)). exact_api·exact_local에는 적용하지 않고 프로파일 값을 기록만 한다. 절단 상한은 항상 max_context_tokens − reserved_answer_tokens(바이블 §8.2·§9.1)",
        ge=0.0,
        le=1.0,
    )
    max_context_tokens: int = Field(
        ...,
        description="팩 전체 상한(프로파일 query.pack.max_context_tokens; QueryRequest.max_context_tokens는 이하로만)",
        ge=1,
    )
    used_tokens: int = Field(
        ...,
        description="실제 사용(항목 본문 + 헤더 추정). 렌더 후 RenderedContext.token_count_rendered로 갱신",
        ge=0,
    )
    reserved_answer_tokens: int = Field(..., description="답변용 예약", ge=0)
    k_max: int = Field(
        ...,
        description="항목 수 상한(프로파일 query.pack.k_max; §5.1 초안 한계 20)",
        ge=1,
        le=20,
    )
    overflow_policy: list[common_types.OverflowPolicy] = Field(
        ...,
        description="예산 초과 시 적용 순서. 기본 [downgrade_tables, truncate]",
        min_length=1,
    )


class Ordering(BaseModel):
    """
    렌더 순서 전략(바이블 §9.2). budget_cut 뒤 최종 K개 기준 적용(K ≤ 1 포함). applied=false면 position = rank − 1
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    strategy: common_types.OrderingStrategy
    applied: bool = Field(
        ...,
        description="전략이 실제 적용되었는지. document_order의 원문 순서 정보 부재 등 전략을 실행할 수 없어 관련도순으로 폴백했을 때만 false",
    )


class PackOmittedEntry(BaseModel):
    """
    제외 항목(바이블 §5.5 omitted). cite_id 없음. RankedSet.omitted(10 RankedOmittedEntry)의 step·related_chunk_id·explain은 복사하지 않는다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    chunk_id: common_types.Hex64
    collection_id: common_types.Ulid
    document_id: common_types.Ulid
    reason: common_types.OmitReason


class MissingAspect(RootModel[str]):
    root: str = Field(..., min_length=1)


class Sufficiency(BaseModel):
    """
    충분성 신호(바이블 §9.1). partial 상태는 없고 coverage + confidence로 표현(ADR-0024)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    status: common_types.SufficiencyStatus
    coverage: float = Field(
        ...,
        description="(적중 질의 변형 수 + 적중 lexical_terms 수) / (전체 변형 수 + 전체 lexical_terms 수)",
        ge=0.0,
        le=1.0,
    )
    confidence: common_types.ConfidenceTier = Field(..., description="max(final_score)의 tier")
    missing_aspects: list[MissingAspect] = Field(
        ..., description="미적중 질의 변형·키워드 라벨(콘텐츠 아님; 질의 측 어휘)"
    )
    method: common_types.SufficiencyMethod


class StopSignal(BaseModel):
    """
    에이전트 루프용 파생 신호(바이블 §5.5). sufficient ⇔ sufficiency.status == sufficient
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    sufficient: bool
    coverage_estimate: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., max_length=256, min_length=1)


class Compression(BaseModel):
    """
    overflow_policy compress 적용 기록(바이블 §5.5)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    method: str = Field(
        ...,
        description="압축기 plugin_id 또는 방법명(예 postprocessor.exit_sentence)",
        min_length=1,
    )
    rate: float = Field(..., description="압축 후 토큰 / 압축 전 토큰", ge=0.0, le=1.0)
    granularity: compression_1.Granularity


class EntityCounts(RootModel[int]):
    root: int = Field(..., ge=0)


class RedactionSummary(BaseModel):
    """
    PII 처리 요약(바이블 §5.5). entity_counts는 엔티티 타입별 집계(열린 객체, 값 integer)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    pii_policy: common_types.PiiPolicy
    entity_counts: dict[str, EntityCounts]


class RenderHints(BaseModel):
    """
    렌더 힌트(바이블 §5.5). 공급자 페이로드 자체가 아니라 렌더러 선택·지시문·데이터마킹 정책
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    preferred_renderer: common_types.Renderer
    citation_style: common_types.CitationStyle = Field(
        ...,
        description="native(공급자 citations; anthropic_* 렌더러에서만) / bracket_id([dN] 마커; 모든 렌더러 — anthropic_*는 구조화 출력 병용 시)",
    )
    instructions_template_id: str = Field(
        ...,
        description="시스템 지시문 템플릿(인용·기권·형식·데이터 경계 문구). 예 rag-answer-ko@1",
        pattern="^[a-z0-9][a-z0-9-]*@[0-9]+$",
    )
    stable_prefix_ref: common_types.ArtifactRef | None = Field(
        None,
        description="선택. 컬렉션 고정 문맥(용어집 등) 산출물 — 프롬프트 캐시 접두어(바이블 §9.4)",
    )
    table_format_preference: list[common_types.TableFormat] = Field(
        ...,
        description="표 형식 우선순위. downgrade_tables는 이 순서로 강등",
        min_length=1,
    )
    language: common_types.Bcp47 = Field(..., description="지시문 언어")
    expose_confidence: bool = Field(..., description="confidence_tier·ocr_confidence_min 노출 여부")
    data_marking: common_types.DataMarking = Field(
        ...,
        description="none / delimit(구분자 + 데이터 표지 문구) / datamark(공백 마커 삽입; korean-gov 기본)",
    )


class LatencyMs(BaseModel):
    """
    스테이지별 소요(ms). 7키 모두 필수이며 실행되지 않은 스테이지(route=no_retrieval 의 retrieve~postprocess, rerank.applied=false 의 rerank)는 0
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    plan: int = Field(..., ge=0)
    retrieve: int = Field(..., ge=0)
    fuse: int = Field(..., ge=0)
    hydrate: int = Field(..., ge=0)
    rerank: int = Field(..., ge=0)
    postprocess: int = Field(..., ge=0)
    pack: int = Field(..., ge=0)


class PackStepReport(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    step: common_types.PackStep
    removed: int = Field(..., ge=0)
    took_ms: int = Field(..., ge=0)


class AclRecheckReport(BaseModel):
    """
    acl_recheck 증적(바이블 §9.1, E9). route=no_retrieval(입력 0건)이면 {checked: 0, denied: 0, hint_hits: 0}
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    checked: int = Field(
        ...,
        description="재검증한 후보 수 = pack 입력(RankedSet(postprocessed).results) 건수; 후처리가 이미 제외한 항목은 대상이 아니다",
        ge=0,
    )
    denied: int = Field(..., description="omitted(acl_denied) 수", ge=0)
    hint_hits: int = Field(..., description="aclrev: 회수 힌트가 payload와 달라 힌트로 판정한 수", ge=0)


class IndexGenerationsSeenItem(RootModel[int]):
    root: int = Field(..., ge=0)


class Step(StrEnum):
    """
    pack 내부 고정 순서.
    """

    acl_recheck = "acl_recheck"
    budget_cut = "budget_cut"
    reorder = "reorder"
    citation_align = "citation_align"


class PackStep(PackStepReport):
    step: Literal["acl_recheck"] = Field(..., description="pack 내부 고정 순서.")


class PackStep2(PackStepReport):
    step: Literal["budget_cut"] = Field(..., description="pack 내부 고정 순서.")


class PackStep3(PackStepReport):
    step: Literal["reorder"] = Field(..., description="pack 내부 고정 순서.")


class PackStep4(PackStepReport):
    step: Literal["citation_align"] = Field(..., description="pack 내부 고정 순서.")


class PackExplainItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    cite_id: common_types.CiteId
    chunk_id: common_types.Hex64
    final_score: float = Field(..., ge=0.0, le=1.0)
    fused_rank: int = Field(..., ge=1)
    rerank_rank: int | None = Field(..., ge=1)
    explain: list[common_types.ExplainCode]


class PackExplainOmitted(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    chunk_id: common_types.Hex64
    final_score: float | None = Field(..., ge=0.0, le=1.0)
    reason: common_types.OmitReason
    explain: list[common_types.ExplainCode]


class PackExplain(BaseModel):
    """
    explain=true 시 상위 K·제외 항목의 점수 요약(원시 점수 분해는 items[].scores)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    ranked_set_id: common_types.Ulid | None = Field(
        ...,
        description="Y(nullable). 입력 RankedSet.ranked_set_id; route=no_retrieval(RankedSet 없음, 09 P-17)이면 null(최상위 allOf 가 sufficiency.status=not_needed 와 결합)",
    )
    items: list[PackExplainItem]
    omitted: list[PackExplainOmitted]


class ContextPack(BaseModel):
    """
    pack 스테이지 출력(바이블 §5.5 ContextPack·ContextItem, §8.2 pack 서브스텝, §9 패커·렌더러 정본). LLM 공급자 중립 표준 JSON: 대상 LLM 토크나이저로 재계산한 토큰 예산, litm_alternating 렌더 순서(position), 관련도순 불변 인용 ID(cite_id = d{rank}), 인용 세그먼트·provenance, 반환 직전 ACL 재검증 증적, 충분성 신호, 렌더 힌트를 담는다. items는 position 오름차순이며 content_hash = H("pack", canonical_json(hash_view(items)))(items에서 타임스탬프 키 acl.checked_at 를 제거한 해시 뷰; 바이블 §6.2·§9.1). 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조하고 재정의하지 않는다(FiltersApplied·SecurityFilter·StrategyFilter 는 10 §3.6·09 §5.1·§5.2 와 같은 형태의 사본, CI 동치 검사). 소유 문서: docs/03-contracts/11-context-pack.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver = Field(..., description='계약 버전. 초기 "1.0.0"')
    schema_type: Literal["ContextPack"] = Field(..., description="PascalCase 타입명(봉투)")
    tenant_id: common_types.Ulid = Field(..., description="보안 삼중항 1(봉투). 공급자 페이로드에는 나가지 않는다")
    collection_ids: list[common_types.Ulid] = Field(
        ...,
        description="질의 측 봉투(복수). QueryPlan.collection_ids 복사. 모든 items[].collection_id는 이 집합에 속한다",
        max_length=20,
        min_length=1,
    )
    producer: common_types.Producer = Field(
        ...,
        description="재현성 지문(봉투). plugin_id는 packer 확장 지점 구현(예 packer.standard), image_digest는 인프로세스이므로 null",
    )
    warnings: list[common_types.Warning] = Field(
        ...,
        description="품질 삼중항 2(봉투). pack.budget_overflow, pack.conflict_unlabeled 등 경고 코드만. 콘텐츠 미포함",
    )
    degraded: list[common_types.DegradedEntry] = Field(
        ...,
        description="품질 삼중항 3(질의 측 봉투). plan~pack의 저하 누적(token_count·acl_recheck 포함)",
    )
    created_at: common_types.DateTime = Field(..., description="RFC 3339 UTC(봉투). content_hash 계산에서 제외")
    pack_id: common_types.Ulid = Field(..., description="서버 발급 팩 식별자")
    query_id: common_types.Ulid = Field(..., description="QueryRequest.query_id")
    plan_id: common_types.Ulid = Field(..., description="QueryPlan.plan_id")
    profile_id: str = Field(
        ...,
        description="kebab-case 프로파일 ID(바이블 §6.1)",
        pattern="^[a-z0-9]+(-[a-z0-9]+)*$",
    )
    profile_hash: common_types.Hex64 = Field(..., description='H("profile", canonical_json(해소된 프로파일))')
    trace_id: str = Field(
        ...,
        description="OTel/W3C Trace Context trace-id(소문자 hex 32). content_hash 계산에서 제외",
        pattern="^[0-9a-f]{32}$",
    )
    budget: Budget
    ordering: Ordering
    items: list[common_types.ContextItem] = Field(
        ...,
        description="최종 항목 K개, position 오름차순(렌더 순서). cite_id는 d1..dK 연속. 상한 20은 바이블 §5.1 초안 한계",
        max_length=20,
    )
    omitted: list[PackOmittedEntry] = Field(
        ...,
        description="제외 항목. cite_id 없음(cite_id는 최종 항목에만 존재). 렌더하지 않는다",
    )
    sufficiency: Sufficiency
    stop_signal: StopSignal | None = None
    compression: Compression | None = Field(
        None,
        description="선택. overflow_policy의 compress가 적용되었을 때만 객체, 아니면 생략 또는 null",
    )
    redaction_summary: RedactionSummary
    classification_max: common_types.Classification = Field(
        ..., description="items[].acl.classification의 최고 등급(K=0이면 public)"
    )
    render_hints: RenderHints
    explain: PackExplain | None = Field(
        None,
        description="선택. QueryRequest.explain=true일 때만 객체(items[].scores와 함께)",
    )
    diagnostics: Diagnostics
    truncated: bool | None = Field(None, description="선택(MCP). 결과 토큰 상한(20k)으로 절단되었으면 true")
    next_cursor: str | None = Field(
        None,
        description='선택(MCP). "더 보기" 불투명 핸들(Valkey cursor:{tenant}:{ulid}, 10m, 테넌트 바인딩)',
        max_length=512,
    )
    content_hash: common_types.Hex64 = Field(
        ...,
        description='H("pack", canonical_json(hash_view(items))) — hash_view 는 items 의 레퍼런스 직렬화에서 타임스탬프 키(*_at; 현재 acl.checked_at)를 재귀 제거한 뷰. created_at·trace_id·diagnostics 는 items 밖. 같은 RankedSet·설정이면 SecurityContext.as_of 가 달라도 동일(바이블 §6.2·§9.1, P-13)',
    )


class FiltersApplied(BaseModel):
    """
    백엔드에 실제 전송된 필터 트리(바이블 §5.5 CandidateSet.filters_applied·§10.2 (a)(b)(c) 구분). 10 §3.6 FiltersApplied 와 같은 형태의 구조 사본(CI 동치 검사) — CandidateSet.filters_applied 를 그대로 복사(완화가 있었으면 완화 후 값). route=no_retrieval(CandidateSet 없음)이면 QueryPlan.filters 의 4묶음 + 계획 effective_hash
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    security: common_types.SecurityFilter = Field(
        ...,
        description="= CandidateSet.filters_applied.security = QueryPlan.filters.security(보안 불변식 (a), 09 §5.1). 제거·완화 불가. principals 는 요청 주체 자신의 목록이며 MCP 슬림 팩·공급자 페이로드에는 나가지 않는다",
    )
    strategy: common_types.StrategyFilter = Field(
        ...,
        description="= CandidateSet.filters_applied.strategy = QueryPlan.filters.strategy(전략 필터 (b), 09 §5.2)",
    )
    user: common_types.FilterNode | None = Field(..., description="Y(nullable). 사용자 필터(page 변환·완화 후 값)")
    self_query: common_types.FilterNode | None = Field(..., description="Y(nullable). 추출 필터(완화 후 값)")
    effective_hash: common_types.Hex64 = Field(
        ...,
        description='Y(10 과 동일; 바이블 §5.5 patch 전제, 10 미해결 이슈 3). 실전송 해시 H("filters", canonical_json(security + strategy + user + self_query; as_of 는 바인드 이름 ":as_of"))(바이블 §6.2, 09 §5.4) — 변환·완화가 없으면 QueryPlan.filters.effective_hash 와 같다; route=no_retrieval 은 계획 해시',
    )


class Diagnostics(BaseModel):
    """
    진단(바이블 §5.5 diagnostics). pack_steps는 고정 순서 4개
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    dedup_removed: int = Field(..., ge=0)
    parent_expansions: int = Field(..., ge=0)
    mmr_lambda: float | None = Field(..., description="Y(nullable). mmr 끔이면 null", ge=0.0, le=1.0)
    filters_applied: FiltersApplied = Field(
        ...,
        description="= CandidateSet.filters_applied(실전송 필터; 10 §3.6 과 같은 형태). route=no_retrieval 이면 QueryPlan.filters 4묶음 + 계획 effective_hash",
    )
    relaxed_applied_keys: list[common_types.FilterableField1] | None = Field(
        None,
        description="선택(N; 바이블 §5.5 diagnostics 미등재, 11 미해결 이슈 3). 0건 완화(QueryPlan.filters.relaxable_keys 순서)로 실제 제거된 사용자·self-query 필드. 완화가 없으면 생략",
        max_length=32,
    )
    latency_ms: LatencyMs
    index_generations_seen: list[IndexGenerationsSeenItem] = Field(
        ...,
        description="후보가 속한 인덱스 세대(플립 혼합 진단). route=no_retrieval 이면 []",
    )
    count_method_fallback: bool = Field(..., description="pack.count_api_failed 폴백이 발생했으면 true")
    pack_steps: tuple[PackStep, PackStep2, PackStep3, PackStep4] = Field(
        ...,
        description="PackStep 고정 순서 acl_recheck → budget_cut → reorder → citation_align(바이블 §8.2)",
    )
    acl_recheck: AclRecheckReport


ContextPack.model_rebuild()
