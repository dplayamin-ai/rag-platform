"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .. import common_types
from .QueryRequest import conversation as conversation_1, target_model as target_model_1


class RequestBudget(BaseModel):
    """
    요청 예산(프로파일 상한 내). 1개 이상 키.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    max_latency_ms: int | None = Field(
        None,
        description="프로파일 latency_budget_ms.total 보다 작으면 사전 저하 순서 적용",
        ge=1,
    )
    max_tool_calls: int | None = Field(None, description="→ QueryPlan.budget.max_tool_calls", ge=0)
    max_context_tokens: int | None = Field(None, description="→ pack.max_context_tokens = min(요청, 프로파일)", ge=1)


class ConversationTurn(BaseModel):
    """
    대화 한 턴. 재작성 입력만이며 팩·렌더에 포함되지 않는다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    role: conversation_1.Role
    text: str = Field(..., max_length=4000, min_length=1)


class TargetModel(BaseModel):
    """
    토큰 카운터·렌더러 선택(바이블 §5.5). pack.tokenizer{provider, model} 과 pack.renderer 기본값의 원천.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    provider: target_model_1.Provider
    model: str = Field(
        ...,
        description="공급자 모델 식별자(플레이스홀더 허용)",
        max_length=128,
        min_length=1,
    )


class QueryRequest(BaseModel):
    """
    리트리벌 API 입력 계약(바이블 §5.5). 클라이언트가 POST /v1/query 또는 MCP search 로 제출한다. 봉투 없음: schema_version·collection_ids 만 갖고 tenant_id·as_of·security_context 는 본문에 없다(서버 SecurityContext 주입, ADR-0027; 본문에 있으면 거부). query_id 는 서버가 접수 시 발급한다(readOnly). filters 는 FilterNode DSL(공용 타입)이며 보안·전략 필터와 AND 로 결합된다. 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소비: plan. 소유 문서: docs/03-contracts/09-query-request-and-query-plan.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description='계약 버전. 초기 "1.0.0"; 이 스키마($id major 1)는 1.x 만 수용',
        pattern="^1\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$",
    )
    query_id: common_types.Ulid = Field(
        ...,
        description="서버 발급(접수 시 ULID). 클라이언트 본문에 존재하면 400 contract.violation(pointer /query_id). rewritten_queries[] 의 original 변형 variant_id 와 같다",
    )
    query: str = Field(
        ...,
        description="원 질의(1..4,000 유니코드 코드포인트). 정규화는 플래너가 수행하고 원문은 QueryPlan.original_query 에 보존",
        max_length=4000,
        min_length=1,
    )
    collection_ids: list[common_types.Ulid] = Field(
        ...,
        description="1..20. SecurityContext.collection_ids 와 교집합; 빈 집합이면 403 plan.collection_forbidden",
        max_length=20,
        min_length=1,
    )
    conversation: list[ConversationTurn] | None = Field(
        None,
        description="대화 재작성 입력(≤ 10턴). LLM 공급자에게 전달되지 않는다",
        max_length=10,
        min_length=1,
    )
    filters: common_types.FilterNode | None = Field(
        None,
        description="사용자 필터(FilterNode DSL, 바이블 §5.7). 보안·전략 필터와 AND. canonical_json ≤ 8,192바이트, 깊이 ≤ 3, 절 ≤ 32(플래너 검증). 금지 필드는 422 plan.filter_field_forbidden",
    )
    top_k: int | None = Field(
        None,
        description="요청 항목 수 힌트. 기본 10. 팩 k_max 와 별개(바이블 §5.5) — 플래너는 pack.k_max 에 결합하지 않는다(pack.k_max = 프로파일 query.pack.k_max; 바이블 §16 GL-08 최종 K = pack.k_max). 결합은 바이블 §5.5 patch 채택 후 반영(문서 미해결 이슈 1)",
        ge=1,
        le=50,
    )
    mode: common_types.RetrievalMode | None = Field(
        None, description="기본 hybrid. dense/sparse/lexical 은 해당 채널만 enabled"
    )
    retrieval_variant: common_types.RetrievalVariant | None = Field(
        None,
        description="컬렉션 프로파일이 허용한 변형만. quality = LLM 플래너·multi-query·HyDE, fast = 리랭크 생략(hydrate.top_n = pack.k_max × 2)",
    )
    strategy_hint: common_types.Strategy | None = Field(None, description="라우터 힌트(강제 아님)")
    target_model: TargetModel | None = None
    max_context_tokens: int | None = Field(
        None,
        description="프로파일 기본(standard 24,000) 이하로만. budget.max_context_tokens 와 함께 오면 작은 값",
        ge=1,
    )
    renderer: common_types.Renderer | None = Field(
        None,
        description="기본은 target_model.provider 에서 유도(없으면 프로파일 pack.renderer)",
    )
    ordering_strategy: common_types.OrderingStrategy | None = Field(None, description="기본 프로파일 pack.ordering")
    include_parents: bool | None = Field(None, description="small-to-big(parent_expand) 강제 켬/끔. 생략 시 프로파일")
    response_format: common_types.ResponseFormat | None = Field(
        None,
        description="MCP 기본 concise, REST 기본 detailed. pack_only 는 rendered 생략",
    )
    session_id: common_types.Ulid | None = Field(
        None,
        description="에이전트 반복 검색 세션. 이전 턴 팩은 재정렬하지 않고 추가만(바이블 §9.4)",
    )
    exclude_ids: list[common_types.Hex64] | None = Field(
        None,
        description="이미 본 chunk_id(콘텐츠 주소, 세대·스코프 무관). 백엔드 must_not 으로 전달",
        max_length=1000,
        min_length=1,
    )
    cursor: str | None = Field(
        None,
        description='MCP "더 보기" 불투명 핸들(Valkey cursor:{tenant}:{ulid}, 10m, 테넌트 바인딩). 서버가 이전 요청 + 누적 exclude_ids 로 해석',
        max_length=512,
        min_length=1,
    )
    budget: RequestBudget | None = None
    experiment_id: str | None = Field(None, description="인터리빙·A/B 실험 ID", max_length=128, min_length=1)
    team_assignment: str | None = Field(None, description="A/B 팀(프로파일 변형 선택 키)", max_length=64, min_length=1)
    explain: bool | None = Field(
        None,
        description="true 면 응답 explain 에 QueryPlan 전문·RankedSet.score_breakdown·팩 explain 포함. MCP search 는 항상 false",
    )
    requested_at: common_types.DateTime = Field(
        ...,
        description="클라이언트 요청 시각(RFC 3339 UTC). embargo·expiry 판정에는 쓰지 않는다(서버 as_of)",
    )
