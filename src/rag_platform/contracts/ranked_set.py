"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from . import common_types
from .common_types import RankedResult


class RerankerId(RootModel[str]):
    root: str = Field(
        ...,
        description="reranker 확장 지점의 plugin_id(바이블 §6.1)",
        pattern="^reranker\\.[a-z][a-z0-9_]*$",
    )


class FusionWeights(BaseModel):
    """
    채널 가중(키는 Channel 열거로 닫힘). 기본 dense:sparse:lexical = 1:1:1
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    dense: float | None = Field(None, ge=0.0)
    sparse: float | None = Field(None, ge=0.0)
    lexical: float | None = Field(None, ge=0.0)
    graph: float | None = Field(None, ge=0.0)
    tree: float | None = Field(None, ge=0.0)
    visual: float | None = Field(None, ge=0.0)
    late_interaction: float | None = Field(None, ge=0.0)


class FusionReport(BaseModel):
    """
    실제 적용된 융합 설정과 결과 수(바이블 §5.5 fusion)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    method: common_types.FusionMethod
    k: int = Field(..., description="RRF k(기본 60). 프로파일 필수값의 사본", ge=1)
    weights: FusionWeights
    variant_query_weight: float = Field(
        ...,
        description="변형 질의 런의 가중(기본 0.5; original은 1.0). = QueryPlan.fusion.variant_query_weight(09 §6.6과 같은 범위)",
        gt=0.0,
        le=1.0,
    )
    candidates_in: int = Field(..., description="= CandidateSet.total_unique", ge=0)
    candidates_out: int = Field(..., description="hydrate.top_n 절단 후 수(= fused 단계 results.length)", ge=0)
    downgraded_from: common_types.FusionMethod | None = Field(
        None,
        description="convex_* → rrf 강등 시 원 방식(degraded{fusion, profile_mismatch} 동반)",
    )


class RerankReport(BaseModel):
    """
    리랭크 적용 보고(바이블 §5.5 rerank). applied=false면 fused 순서 폴백 + results[].explain에 rerank_skipped
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    applied: bool
    plugin_id: RerankerId
    model_id: common_types.ModelId
    backend: common_types.RerankBackend
    response_schema: common_types.RerankResponseSchema
    normalization: common_types.ScoreNormalization
    top_n_in: int = Field(..., ge=1)
    top_n_out: int = Field(..., ge=1)
    took_ms: int = Field(..., ge=0)
    skipped_reason: str | None = Field(
        None,
        description="applied=false일 때 필수. 카탈로그 코드 rerank.timeout(타임아웃; degraded{rerank, timeout}) 또는 DegradedReason 값 unavailable(리랭커 5xx·연결 실패; degraded{rerank, unavailable}), latency_budget, skipped_by_policy(문서 §7)",
        max_length=64,
    )


class LateInteractionRerankReport(BaseModel):
    """
    2단 리랭크 1단(MaxSim) 보고. 현재는 순서 필터(재융합 없음)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    applied: bool
    model_id: common_types.ModelId
    top_n_in: int = Field(..., ge=1)
    top_n_out: int = Field(..., ge=1)
    took_ms: int = Field(..., ge=0)


class RelevanceGateReport(BaseModel):
    """
    relevance_gate 결과. passed = (max_score >= tau)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    tau: float = Field(..., ge=0.0, le=1.0)
    max_score: float = Field(
        ...,
        description="게이트 평가 시점 max(final_score); 입력이 비었으면 0",
        ge=0.0,
        le=1.0,
    )
    passed: bool
    retries: int = Field(
        ...,
        description="quality 변형의 재작성·필터 완화 재검색 횟수(최대 1)",
        ge=0,
        le=1,
    )


class PostprocessStepReport(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    step: common_types.PostprocessStep
    removed: int = Field(..., description="results에서 omitted로 옮긴 수", ge=0)
    added: int = Field(..., description="results에 추가된 수(parent_expand의 부모 항목)", ge=0)
    took_ms: int = Field(..., ge=0)


class PostprocessReport(BaseModel):
    """
    실행된 단계 보고. 순서는 고정 순서 relevance_gate → dedup → mmr → parent_expand → dedup → sentence_window → compress의 부분 수열(생략된 옵션 단계는 기록하지 않음)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    steps: list[PostprocessStepReport] = Field(..., max_length=7)


class IndexGenerationSeenItem(RootModel[int]):
    root: int = Field(..., ge=0)


class ChannelRunSummary(BaseModel):
    """
    CandidateSet.channel_runs[]의 후보·오류 없는 요약(선택 필드 channel_runs의 원소)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    channel_run_id: common_types.ChannelRunId
    channel: common_types.Channel
    collection_id: common_types.Ulid
    variant_id: common_types.Ulid
    status: common_types.ChannelRunStatus
    returned: int = Field(..., ge=0, le=300)
    total_hits: int | None = Field(..., ge=0)
    truncated: bool
    took_ms: int = Field(..., ge=0)
    index_generation_seen: list[IndexGenerationSeenItem]


class Reason(StrEnum):
    below_threshold = "below_threshold"
    duplicate = "duplicate"
    budget_exceeded = "budget_exceeded"
    acl_denied = "acl_denied"
    parent_merged = "parent_merged"
    item_kind_excluded = "item_kind_excluded"
    risk_flagged = "risk_flagged"
    hydrate_missing = "hydrate_missing"
    below_threshold_1 = "below_threshold"
    duplicate_1 = "duplicate"
    parent_merged_1 = "parent_merged"
    hydrate_missing_1 = "hydrate_missing"


class RankedOmittedEntry(BaseModel):
    """
    hydrate·postprocess가 results에서 제거한 항목. reason은 OmitReason의 부분집합(below_threshold, duplicate, parent_merged, hydrate_missing). 11-context-pack의 PackOmittedEntry(4필드)와 형태가 달라 이름을 구별한다; pack이 4필드로 투영하고 acl_denied·budget_exceeded·risk_flagged·item_kind_excluded를 더해 ContextPack.omitted를 만든다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    chunk_id: common_types.Hex64
    collection_id: common_types.Ulid
    document_id: common_types.Ulid
    reason: Reason
    step: common_types.PostprocessStep | None = Field(..., description="제거한 후처리 단계. hydrate_missing은 null")
    related_chunk_id: common_types.Hex64 | None = Field(
        None, description="duplicate면 대표 chunk_id, parent_merged면 부모 chunk_id"
    )
    explain: list[common_types.ExplainCode] | None = Field(
        None,
        description="제거 시점의 explain 코드(hydrate_missing, below_gate, deduped 포함)",
    )


class RankedSetStats(BaseModel):
    """
    바이블 §5.5 stats
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    n_in: int = Field(
        ...,
        description="이 스테이지 입력 항목 수(fused: candidates_in; reranked: hydrated_n; postprocessed: rerank 출력 수)",
        ge=0,
    )
    n_out: int = Field(..., description="= results.length", ge=0, le=100)
    hydrated_n: int = Field(..., description="hydrate가 채운 항목 수(hydrated=false면 0)", ge=0)
    gate_passed: bool | None = Field(..., description="relevance_gate.passed의 사본. postprocessed 이전은 null")


class TimingsMs(BaseModel):
    """
    스테이지별 경과(ms). 값이 없는 스테이지는 키를 생략
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    retrieve: int | None = Field(None, ge=0)
    fuse: int | None = Field(None, ge=0)
    hydrate: int | None = Field(None, ge=0)
    rerank: int | None = Field(None, ge=0)
    postprocess: int | None = Field(None, ge=0)


class ResultParentRule(RootModel[Any]):
    root: Any = Field(
        ...,
        description="record_id = null ⇔ item_kind = parent(부모 확장 항목은 인덱스 레코드가 없다); 부모는 level 1, parent_chunk_id = null(level 1 위로는 확장하지 않는다)이고 expanded_from을 갖는다",
    )


class HydratedRequired(RootModel[Any]):
    root: Any = Field(
        ...,
        description="hydrated=true일 때 results[] 조건 필수(바이블 §5.5; hydrate가 IndexRecord payload에서 채운다)",
    )


class Result(RankedResult):
    pass


class RankedSet(BaseModel):
    """
    fuse(fused) → hydrate(fused, hydrated=true) → rerank(reranked) → postprocess(postprocessed)가 갱신하는 질의 측 계약(바이블 §5.5). 같은 타입이 stage로 구분되며 단계별 조건 필수는 if/then으로 표현한다. results[]는 RankedResult(common-types $defs), 점수 원장은 ScoreBreakdown(Σ contribution = fused). 소비자는 pack과 평가(TREC run). 소유 문서: docs/03-contracts/10-candidate-set-and-ranked-set.md.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description='계약 버전. 초기 "1.0.0"; 이 스키마($id major 1)는 1.x 만 수용',
        pattern="^1\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$",
    )
    schema_type: Literal["RankedSet"]
    tenant_id: common_types.Ulid
    collection_ids: list[common_types.Ulid] = Field(..., max_length=20, min_length=1)
    producer: common_types.Producer = Field(
        ...,
        description="이 인스턴스를 마지막으로 쓴 스테이지의 플러그인(fused: fuser.*, reranked: reranker.*, postprocessed: postprocessor.*). hydrate는 서브스텝이라 producer를 바꾸지 않는다(stage=fused, hydrated=true도 fuser.*; index_backend.* 어댑터 지문은 기록하지 않음)",
    )
    warnings: list[common_types.Warning]
    degraded: list[common_types.DegradedEntry] = Field(
        ...,
        description="입력 CandidateSet.degraded를 상속하고 fusion·hydrate·rerank·postprocess 항목을 더한다",
    )
    created_at: common_types.DateTime
    ranked_set_id: common_types.Ulid = Field(..., description="발급형 ID. 세 단계 갱신 동안 유지된다")
    plan_id: common_types.Ulid
    query_id: common_types.Ulid
    candidate_set_id: common_types.Ulid | None = Field(
        None,
        description="선택(N). 입력 CandidateSet.candidate_set_id(바이블 §5.5 미등재, 미해결 이슈 2)",
    )
    stage: common_types.RankedStage
    hydrated: bool = Field(
        ...,
        description="hydrate 완료 여부. fuse 직후 false, hydrate 뒤 true, reranked 이후 항상 true",
    )
    fusion: FusionReport
    rerank: RerankReport | None = Field(None, description="조건: stage ∈ {reranked, postprocessed}")
    late_interaction_rerank: LateInteractionRerankReport | None = Field(
        None, description="선택(N). O-04 실험 슬롯(stage ∈ {reranked, postprocessed})"
    )
    relevance_gate: RelevanceGateReport | None = Field(None, description="조건: stage = postprocessed")
    calibration_ref: str | None = Field(
        None,
        description="선택(N). 컬렉션별 리랭크 점수 분포(calibrations 표) 참조",
        max_length=128,
    )
    postprocess_report: PostprocessReport | None = Field(None, description="조건: stage = postprocessed")
    channel_runs: list[ChannelRunSummary] | None = Field(
        None,
        description="선택(N). CandidateSet.channel_runs의 후보 없는 요약(pack diagnostics·explain 원천; 미해결 이슈 2)",
        min_length=1,
    )
    results: list[Result] = Field(..., description="final_rank 오름차순(1..n 연속). 상한 100", max_length=100)
    omitted: list[RankedOmittedEntry] | None = Field(
        None,
        description="선택(N). hydrate·postprocess가 results에서 제거한 항목. 플랫폼 구현은 항상 채운다(없으면 []); pack이 11의 PackOmittedEntry{chunk_id, collection_id, document_id, reason}로 투영해 ContextPack.omitted에 넣는다(미해결 이슈 2)",
    )
    stats: RankedSetStats
    timings_ms: TimingsMs | None = Field(
        None,
        description="선택(N). 스테이지별 경과(ContextPack.diagnostics.latency_ms 원천; 미해결 이슈 2)",
    )
