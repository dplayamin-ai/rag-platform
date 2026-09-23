"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, constr

from .. import common_types
from .Profile import observability as observability_1, runtime as runtime_1
from .Profile.eval import gates as gates_1
from .Profile.ingest.index import backends as backends_1, commit as commit_1
from .Profile.query.pack import tokenizer as tokenizer_1
from .Profile.query.postprocess import parent_expand as parent_expand_1
from .Profile.security import rate_limit as rate_limit_1


class ProfileId(RootModel[str]):
    root: str = Field(
        ...,
        description="프로파일 ID kebab-case(바이블 §6.1). urn:rag:schema:collection-spec:1#/$defs/ProfileId 의 사본",
        max_length=64,
        pattern="^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
    )


class MaxGrade(StrEnum):
    """
    허용 최고 등급. PluginMeta.license_grade <= max_grade
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    X = "X"
    A_1 = "A"
    B_1 = "B"
    C_1 = "C"
    D_1 = "D"


class TerritoryItem(RootModel[str]):
    root: str = Field(..., pattern="^[A-Z]{2}$")


class LicensePolicy(BaseModel):
    """
    바이블 §5.6 Profile.license_policy. urn:rag:schema:collection-spec:1#/$defs/LicensePolicy 의 사본. max_grade는 §5.7 나열 순 비교(A<B<C<D), X(사용 비허가)는 상한이 될 수 없다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    max_grade: MaxGrade = Field(..., description="허용 최고 등급. PluginMeta.license_grade <= max_grade")
    territory: list[TerritoryItem] = Field(
        ...,
        description="배포 지역 ISO 3166-1 alpha-2. PluginMeta.territory가 비어 있지 않으면 이 값 전부를 포함해야 한다(ADR-0001)",
        min_length=1,
    )


class MetricKey(RootModel[str]):
    root: str = Field(
        ...,
        description="메트릭 키 {metric}[@{k}](k >= 1, 선행 0 금지). urn:rag:schema:eval-run:1#/$defs/MetricKey 의 사본(계약 간 교차 $ref 회피; CI 동치 대조). GateSpec.metric·eval.gates 키가 참조하며 16 GateOutcome.metric 으로 그대로 표현된다",
        max_length=64,
        pattern="^[a-z][a-z0-9_]*(@[1-9][0-9]*)?$",
    )


class GateSpec1(BaseModel):
    """
    품질 게이트(바이블 §5.6 게이트 값 행, §7.4). metric 생략 = eval.gates의 ndcg@10, dataset 생략 = eval.datasets[0]. grid | min_delta | min_delta_pt | min_qrels | candidate | promote_to 중 하나 이상. 게이트가 붙은 값은 EvalReport.gate_result.passed와 ADR 없이 바꿀 수 없다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    metric: MetricKey | None = Field(
        None,
        description="EvalReport.metrics 키(ndcg@10, recall@20, mrr, span_hit_rate@10). GateOutcome.metric(16)과 같은 MetricKey 형식",
    )
    dataset: str | None = Field(
        None,
        description="EvalDataset.name(16 §2.1; 최신 행으로 해소). 생략 = eval.datasets[0]",
        max_length=64,
        pattern="^[a-z0-9][a-z0-9-]*$",
    )
    grid: list[float] = Field(..., description="탐색 격자(value가 그 원소)", min_length=2)
    min_delta: float | None = Field(None, description="후보 채택 최소 개선(지표 단위)", gt=0.0)
    min_delta_pt: float | None = Field(None, description="후보 채택 최소 개선(퍼센트 포인트)", gt=0.0)
    min_qrels: int | None = Field(None, description="전환 전 필요한 사람 라벨 qrels 수", ge=1)
    candidate: str | None = Field(None, description="비교 대상 후보(모델 ID 등)", max_length=256, min_length=1)
    max_cost_per_doc_usd: float | None = Field(None, description="문서당 비용 상한(LLM 보강)", ge=0.0)
    promote_to: common_types.FusionMethod | None = Field(None, description="융합 전환 목표(O-01)")
    tool: str | None = Field(
        None,
        description="판정 도구(ranx.optimize_fusion 등)",
        max_length=128,
        min_length=1,
    )


class GateSpec2(BaseModel):
    """
    품질 게이트(바이블 §5.6 게이트 값 행, §7.4). metric 생략 = eval.gates의 ndcg@10, dataset 생략 = eval.datasets[0]. grid | min_delta | min_delta_pt | min_qrels | candidate | promote_to 중 하나 이상. 게이트가 붙은 값은 EvalReport.gate_result.passed와 ADR 없이 바꿀 수 없다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    metric: MetricKey | None = Field(
        None,
        description="EvalReport.metrics 키(ndcg@10, recall@20, mrr, span_hit_rate@10). GateOutcome.metric(16)과 같은 MetricKey 형식",
    )
    dataset: str | None = Field(
        None,
        description="EvalDataset.name(16 §2.1; 최신 행으로 해소). 생략 = eval.datasets[0]",
        max_length=64,
        pattern="^[a-z0-9][a-z0-9-]*$",
    )
    grid: list[float] | None = Field(None, description="탐색 격자(value가 그 원소)", min_length=2)
    min_delta: float = Field(..., description="후보 채택 최소 개선(지표 단위)", gt=0.0)
    min_delta_pt: float | None = Field(None, description="후보 채택 최소 개선(퍼센트 포인트)", gt=0.0)
    min_qrels: int | None = Field(None, description="전환 전 필요한 사람 라벨 qrels 수", ge=1)
    candidate: str | None = Field(None, description="비교 대상 후보(모델 ID 등)", max_length=256, min_length=1)
    max_cost_per_doc_usd: float | None = Field(None, description="문서당 비용 상한(LLM 보강)", ge=0.0)
    promote_to: common_types.FusionMethod | None = Field(None, description="융합 전환 목표(O-01)")
    tool: str | None = Field(
        None,
        description="판정 도구(ranx.optimize_fusion 등)",
        max_length=128,
        min_length=1,
    )


class GateSpec3(BaseModel):
    """
    품질 게이트(바이블 §5.6 게이트 값 행, §7.4). metric 생략 = eval.gates의 ndcg@10, dataset 생략 = eval.datasets[0]. grid | min_delta | min_delta_pt | min_qrels | candidate | promote_to 중 하나 이상. 게이트가 붙은 값은 EvalReport.gate_result.passed와 ADR 없이 바꿀 수 없다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    metric: MetricKey | None = Field(
        None,
        description="EvalReport.metrics 키(ndcg@10, recall@20, mrr, span_hit_rate@10). GateOutcome.metric(16)과 같은 MetricKey 형식",
    )
    dataset: str | None = Field(
        None,
        description="EvalDataset.name(16 §2.1; 최신 행으로 해소). 생략 = eval.datasets[0]",
        max_length=64,
        pattern="^[a-z0-9][a-z0-9-]*$",
    )
    grid: list[float] | None = Field(None, description="탐색 격자(value가 그 원소)", min_length=2)
    min_delta: float | None = Field(None, description="후보 채택 최소 개선(지표 단위)", gt=0.0)
    min_delta_pt: float = Field(..., description="후보 채택 최소 개선(퍼센트 포인트)", gt=0.0)
    min_qrels: int | None = Field(None, description="전환 전 필요한 사람 라벨 qrels 수", ge=1)
    candidate: str | None = Field(None, description="비교 대상 후보(모델 ID 등)", max_length=256, min_length=1)
    max_cost_per_doc_usd: float | None = Field(None, description="문서당 비용 상한(LLM 보강)", ge=0.0)
    promote_to: common_types.FusionMethod | None = Field(None, description="융합 전환 목표(O-01)")
    tool: str | None = Field(
        None,
        description="판정 도구(ranx.optimize_fusion 등)",
        max_length=128,
        min_length=1,
    )


class GateSpec4(BaseModel):
    """
    품질 게이트(바이블 §5.6 게이트 값 행, §7.4). metric 생략 = eval.gates의 ndcg@10, dataset 생략 = eval.datasets[0]. grid | min_delta | min_delta_pt | min_qrels | candidate | promote_to 중 하나 이상. 게이트가 붙은 값은 EvalReport.gate_result.passed와 ADR 없이 바꿀 수 없다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    metric: MetricKey | None = Field(
        None,
        description="EvalReport.metrics 키(ndcg@10, recall@20, mrr, span_hit_rate@10). GateOutcome.metric(16)과 같은 MetricKey 형식",
    )
    dataset: str | None = Field(
        None,
        description="EvalDataset.name(16 §2.1; 최신 행으로 해소). 생략 = eval.datasets[0]",
        max_length=64,
        pattern="^[a-z0-9][a-z0-9-]*$",
    )
    grid: list[float] | None = Field(None, description="탐색 격자(value가 그 원소)", min_length=2)
    min_delta: float | None = Field(None, description="후보 채택 최소 개선(지표 단위)", gt=0.0)
    min_delta_pt: float | None = Field(None, description="후보 채택 최소 개선(퍼센트 포인트)", gt=0.0)
    min_qrels: int = Field(..., description="전환 전 필요한 사람 라벨 qrels 수", ge=1)
    candidate: str | None = Field(None, description="비교 대상 후보(모델 ID 등)", max_length=256, min_length=1)
    max_cost_per_doc_usd: float | None = Field(None, description="문서당 비용 상한(LLM 보강)", ge=0.0)
    promote_to: common_types.FusionMethod | None = Field(None, description="융합 전환 목표(O-01)")
    tool: str | None = Field(
        None,
        description="판정 도구(ranx.optimize_fusion 등)",
        max_length=128,
        min_length=1,
    )


class GateSpec5(BaseModel):
    """
    품질 게이트(바이블 §5.6 게이트 값 행, §7.4). metric 생략 = eval.gates의 ndcg@10, dataset 생략 = eval.datasets[0]. grid | min_delta | min_delta_pt | min_qrels | candidate | promote_to 중 하나 이상. 게이트가 붙은 값은 EvalReport.gate_result.passed와 ADR 없이 바꿀 수 없다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    metric: MetricKey | None = Field(
        None,
        description="EvalReport.metrics 키(ndcg@10, recall@20, mrr, span_hit_rate@10). GateOutcome.metric(16)과 같은 MetricKey 형식",
    )
    dataset: str | None = Field(
        None,
        description="EvalDataset.name(16 §2.1; 최신 행으로 해소). 생략 = eval.datasets[0]",
        max_length=64,
        pattern="^[a-z0-9][a-z0-9-]*$",
    )
    grid: list[float] | None = Field(None, description="탐색 격자(value가 그 원소)", min_length=2)
    min_delta: float | None = Field(None, description="후보 채택 최소 개선(지표 단위)", gt=0.0)
    min_delta_pt: float | None = Field(None, description="후보 채택 최소 개선(퍼센트 포인트)", gt=0.0)
    min_qrels: int | None = Field(None, description="전환 전 필요한 사람 라벨 qrels 수", ge=1)
    candidate: str = Field(..., description="비교 대상 후보(모델 ID 등)", max_length=256, min_length=1)
    max_cost_per_doc_usd: float | None = Field(None, description="문서당 비용 상한(LLM 보강)", ge=0.0)
    promote_to: common_types.FusionMethod | None = Field(None, description="융합 전환 목표(O-01)")
    tool: str | None = Field(
        None,
        description="판정 도구(ranx.optimize_fusion 등)",
        max_length=128,
        min_length=1,
    )


class GateSpec6(BaseModel):
    """
    품질 게이트(바이블 §5.6 게이트 값 행, §7.4). metric 생략 = eval.gates의 ndcg@10, dataset 생략 = eval.datasets[0]. grid | min_delta | min_delta_pt | min_qrels | candidate | promote_to 중 하나 이상. 게이트가 붙은 값은 EvalReport.gate_result.passed와 ADR 없이 바꿀 수 없다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    metric: MetricKey | None = Field(
        None,
        description="EvalReport.metrics 키(ndcg@10, recall@20, mrr, span_hit_rate@10). GateOutcome.metric(16)과 같은 MetricKey 형식",
    )
    dataset: str | None = Field(
        None,
        description="EvalDataset.name(16 §2.1; 최신 행으로 해소). 생략 = eval.datasets[0]",
        max_length=64,
        pattern="^[a-z0-9][a-z0-9-]*$",
    )
    grid: list[float] | None = Field(None, description="탐색 격자(value가 그 원소)", min_length=2)
    min_delta: float | None = Field(None, description="후보 채택 최소 개선(지표 단위)", gt=0.0)
    min_delta_pt: float | None = Field(None, description="후보 채택 최소 개선(퍼센트 포인트)", gt=0.0)
    min_qrels: int | None = Field(None, description="전환 전 필요한 사람 라벨 qrels 수", ge=1)
    candidate: str | None = Field(None, description="비교 대상 후보(모델 ID 등)", max_length=256, min_length=1)
    max_cost_per_doc_usd: float | None = Field(None, description="문서당 비용 상한(LLM 보강)", ge=0.0)
    promote_to: common_types.FusionMethod = Field(..., description="융합 전환 목표(O-01)")
    tool: str | None = Field(
        None,
        description="판정 도구(ranx.optimize_fusion 등)",
        max_length=128,
        min_length=1,
    )


class GateSpec(RootModel[GateSpec1 | GateSpec2 | GateSpec3 | GateSpec4 | GateSpec5 | GateSpec6]):
    root: GateSpec1 | GateSpec2 | GateSpec3 | GateSpec4 | GateSpec5 | GateSpec6 = Field(
        ...,
        description="품질 게이트(바이블 §5.6 게이트 값 행, §7.4). metric 생략 = eval.gates의 ndcg@10, dataset 생략 = eval.datasets[0]. grid | min_delta | min_delta_pt | min_qrels | candidate | promote_to 중 하나 이상. 게이트가 붙은 값은 EvalReport.gate_result.passed와 ADR 없이 바꿀 수 없다",
    )


class GatedValue(BaseModel):
    """
    게이트 보유 값 {value, gate}(바이블 §5.6)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    value: int | float | str | bool
    gate: GateSpec


class Backoff(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    initial: common_types.Duration
    max: common_types.Duration
    coefficient: float = Field(..., ge=1.0)


class StagePolicyPartial(BaseModel):
    """
    프로파일 YAML 안의 부분 StagePolicy. 로더가 task_queue(runtime.queues[stage])·non_retryable_error_codes(§4.4 기본)·resumable(capabilities)·backoff{1s,5m,2.0}를 채워 완전한 StagePolicy(urn:rag:schema:common-types:1#/$defs/StagePolicy)로 만든다. 해소 결과는 그 스키마를 통과해야 한다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    task_queue: str | None = Field(None, pattern="^[a-z][a-z0-9-]*$")
    start_to_close: common_types.Duration | None = None
    heartbeat: common_types.Duration | None = None
    max_attempts: int | None = Field(None, ge=1)
    backoff: Backoff | None = None
    non_retryable_error_codes: list[common_types.ErrorCodeCatalog] | None = None
    resumable: bool | None = None
    isolation: common_types.IsolationMode | None = None


class PluginRef(BaseModel):
    """
    플러그인 지정 + 폴백 + 플러그인 config_schema 필드(열린 객체)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId
    fallback: common_types.PluginId | None = Field(None, description="예외 시 폴백 플러그인(같은 확장 지점·역할)")


class Queues(RootModel[str]):
    root: str = Field(..., pattern="^[a-z][a-z0-9-]*$")


class ConsistencyCheck(BaseModel):
    """
    선택(N). §7.2 consistency_check 주기
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    sample_every: common_types.Duration | None = None
    full_every: common_types.Duration


class Snapshot(BaseModel):
    """
    선택(N). §7.2 snapshot 주기
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    every: common_types.Duration
    replicate_region: bool | None = None


class RuntimeConfig(BaseModel):
    """
    바이블 §5.6 runtime
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    orchestrator: runtime_1.Orchestrator
    queues: dict[constr(pattern=r"^[a-z][a-z0-9_]*$"), Queues] = Field(
        ...,
        description="스테이지 → Temporal task_queue(kebab). StagePolicy.task_queue 기본값의 원천. 선택 키 detect, ocr, enrich_llm, recount(폴백 detect·ocr → parse, recount → chunk). publish 는 로컬 액티비티라 키가 없다",
    )
    tenant_concurrent_jobs_max: int = Field(..., description="디스패처가 jobs.running 수로 강제(§11.2)", ge=1)
    acl_propagation_slo: common_types.Duration = Field(
        ..., description="E11 회수 전파 SLO(rag_acl_propagation_seconds)"
    )
    outbox_lag_slo: common_types.Duration = Field(..., description="아웃박스 릴레이 지연 SLO(rag_outbox_lag_seconds)")
    egress: common_types.EgressPolicy = Field(
        ...,
        description="E16. deny_cidrs는 기본 9개 CIDR을 포함해야 한다(검증 규칙 12). file 스킴은 orchestrator=local일 때만",
    )
    consistency_check: ConsistencyCheck | None = Field(None, description="선택(N). §7.2 consistency_check 주기")
    snapshot: Snapshot | None = Field(None, description="선택(N). §7.2 snapshot 주기")


class RouteStep(BaseModel):
    """
    parse.router 폴백 체인의 한 단계(§7.3). then = 변환 뒤 재라우팅할 SourceFormat
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    plugin: common_types.PluginId
    isolation: common_types.IsolationMode | None = None
    image: str | None = Field(
        None,
        description="사이드카 이미지 이름(parser-workers, lo-sidecar, ocr-gpu). digest는 런타임 Producer.image_digest",
        pattern="^[a-z][a-z0-9-]*$",
    )
    then: common_types.SourceFormat | None = None


class RouteChain(RootModel[list[common_types.PluginId | RouteStep]]):
    """
    시도 순서대로의 파서 체인. ParsedDocument.parser_chain[]에 실제 시도 순서가 기록된다
    """

    root: list[common_types.PluginId | RouteStep] = Field(
        ...,
        description="시도 순서대로의 파서 체인. ParsedDocument.parser_chain[]에 실제 시도 순서가 기록된다",
        min_length=1,
    )


class RouteTerminal(StrEnum):
    """
    해당 포맷을 즉시 비재시도 오류로 종료(§7.3 hwp3·unknown). 카탈로그 부분집합(00 §2 열거 규칙)
    """

    fetch_access_denied = "fetch.access_denied"
    fetch_not_found = "fetch.not_found"
    fetch_too_large = "fetch.too_large"
    fetch_scheme_unsupported = "fetch.scheme_unsupported"
    fetch_egress_denied = "fetch.egress_denied"
    fetch_timeout = "fetch.timeout"
    fetch_upstream_error = "fetch.upstream_error"
    parse_unsupported_format = "parse.unsupported_format"
    parse_unsupported_variant = "parse.unsupported_variant"
    parse_corrupt_container = "parse.corrupt_container"
    parse_document_encrypted = "parse.document_encrypted"
    parse_distribution_document = "parse.distribution_document"
    parse_sidecar_unavailable = "parse.sidecar_unavailable"
    parse_conversion_failed = "parse.conversion_failed"
    parse_page_timeout = "parse.page_timeout"
    parse_page_ocr_failed = "parse.page_ocr_failed"
    parse_page_skipped = "parse.page_skipped"
    parse_block_oversized = "parse.block_oversized"
    parse_block_limit_exceeded = "parse.block_limit_exceeded"
    parse_element_path_synthesized = "parse.element_path_synthesized"
    parse_table_structure_fallback = "parse.table_structure_fallback"
    parse_footnote_unanchored = "parse.footnote_unanchored"
    parse_container_limit_exceeded = "parse.container_limit_exceeded"
    parse_extractor_fallback = "parse.extractor_fallback"
    normalize_nfd_residual = "normalize.nfd_residual"
    normalize_pii_policy_violation = "normalize.pii_policy_violation"
    normalize_pii_detector_unavailable = "normalize.pii_detector_unavailable"
    normalize_segmenter_fallback = "normalize.segmenter_fallback"
    chunk_tokenizer_missing = "chunk.tokenizer_missing"
    chunk_count_exceeded = "chunk.count_exceeded"
    chunk_block_oversized = "chunk.block_oversized"
    enrich_content_policy_violation = "enrich.content_policy_violation"
    enrich_llm_policy_denied = "enrich.llm_policy_denied"
    enrich_budget_exceeded = "enrich.budget_exceeded"
    enrich_extractor_timeout = "enrich.extractor_timeout"
    enrich_llm_unavailable = "enrich.llm_unavailable"
    embed_space_mismatch = "embed.space_mismatch"
    embed_tokenizer_missing = "embed.tokenizer_missing"
    embed_server_unavailable = "embed.server_unavailable"
    embed_token_overflow = "embed.token_overflow"
    index_security_fields_missing = "index.security_fields_missing"
    index_generation_conflict = "index.generation_conflict"
    index_backend_unavailable = "index.backend_unavailable"
    index_partial_commit = "index.partial_commit"
    plan_security_context_missing = "plan.security_context_missing"
    plan_filter_field_forbidden = "plan.filter_field_forbidden"
    plan_collection_forbidden = "plan.collection_forbidden"
    plan_llm_failed = "plan.llm_failed"
    retrieve_security_context_missing = "retrieve.security_context_missing"
    fuse_k_missing = "fuse.k_missing"
    retrieve_channel_timeout = "retrieve.channel_timeout"
    retrieve_backend_error = "retrieve.backend_error"
    retrieve_unavailable = "retrieve.unavailable"
    hydrate_backend_error = "hydrate.backend_error"
    rerank_schema_mismatch = "rerank.schema_mismatch"
    pack_tokenizer_mismatch = "pack.tokenizer_mismatch"
    render_mixed_blocks = "render.mixed_blocks"
    render_citations_with_structured_output = "render.citations_with_structured_output"
    render_empty_pack = "render.empty_pack"
    rerank_timeout = "rerank.timeout"
    postprocess_parent_text_miss = "postprocess.parent_text_miss"
    pack_count_api_failed = "pack.count_api_failed"
    pack_budget_overflow = "pack.budget_overflow"
    pack_conflict_unlabeled = "pack.conflict_unlabeled"
    pack_acl_hint_unavailable = "pack.acl_hint_unavailable"
    auth_unauthenticated = "auth.unauthenticated"
    auth_forbidden = "auth.forbidden"
    auth_too_many_principals = "auth.too_many_principals"
    api_idempotency_conflict = "api.idempotency_conflict"
    api_idempotency_payload_mismatch = "api.idempotency_payload_mismatch"
    api_rate_limited = "api.rate_limited"
    api_not_found = "api.not_found"
    api_quota_exceeded = "api.quota_exceeded"
    contract_violation = "contract.violation"
    contract_schema_type_mismatch = "contract.schema_type_mismatch"
    contract_upcast_failed = "contract.upcast_failed"
    contract_acl_deny_all = "contract.acl_deny_all"
    profile_invalid = "profile.invalid"
    profile_gate_pending = "profile.gate_pending"
    plugin_license_denied = "plugin.license_denied"
    plugin_capability_unsupported = "plugin.capability_unsupported"
    render_template_unsupported = "render.template_unsupported"
    outbox_egress_denied = "outbox.egress_denied"
    outbox_relay_failed = "outbox.relay_failed"
    parse_unsupported_format_1 = "parse.unsupported_format"
    parse_unsupported_variant_1 = "parse.unsupported_variant"


class PdfRoute(BaseModel):
    """
    PDF는 source_kind별 라우팅. mixed=page_route 는 페이지 단위로 born_digital/scanned 경로를 섞는다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    born_digital: common_types.PluginId
    scanned: common_types.PluginId
    mixed: common_types.PluginId | Literal["page_route"]


class SplitRoute(BaseModel):
    """
    컨테이너 분할 후 재라우팅(§7.3 json: split_hint=json_array 이면 멤버 분할 후 then 포맷으로)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    split: common_types.SplitHint
    then: common_types.SourceFormat


class RouteEntry(RootModel[RouteChain | RouteTerminal | PdfRoute | SplitRoute]):
    root: RouteChain | RouteTerminal | PdfRoute | SplitRoute


class ParseRouter(BaseModel):
    """
    SourceFormat 13값 전부를 키로 가진다(검증 규칙 10; 누락 → profile.invalid)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    hwpx: RouteEntry
    hwp5: RouteEntry
    hwp3: RouteEntry
    pdf: RouteEntry
    docx: RouteEntry
    doc: RouteEntry
    rtf: RouteEntry
    odt: RouteEntry
    html: RouteEntry
    txt: RouteEntry
    md: RouteEntry
    json_: RouteEntry = Field(..., alias="json")
    unknown: RouteEntry


class LangItem(RootModel[str]):
    root: str = Field(..., min_length=1)


class OcrOptions(BaseModel):
    """
    검증 규칙 6: plugin·lang·version·model 필수(O-08; RapidOCR 기본 PP-OCRv6 차단)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    plugin: str = Field(
        ...,
        description="OCR 엔진 이름(PDF 파서 플러그인 내부 옵션; entry point 아님). rapidocr, paddleocr, tesseract, surya",
        pattern="^[a-z][a-z0-9_]*$",
    )
    lang: list[LangItem] = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)


class PageTimeout(BaseModel):
    """
    페이지 단위 하트비트 타임아웃(O-08: CPU 60s / GPU 20s)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    cpu: common_types.Duration
    gpu: common_types.Duration


class ParseOptions(BaseModel):
    """
    파서 공통 옵션. pdf·page_timeout 외 키는 포맷별 파서 config_schema
    """

    model_config = ConfigDict(
        extra="allow",
    )
    pdf: dict[str, Any] | None = Field(
        None,
        description="PDF 파서 옵션(layout_model, table_model, threads). 열린 객체: 키·값은 PDF 파서 플러그인 config_schema가 검증",
    )
    ocr: OcrOptions
    page_timeout: PageTimeout | None = Field(None, description="페이지 단위 하트비트 타임아웃(O-08: CPU 60s / GPU 20s)")


class FetchConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId
    max_bytes: int = Field(
        ...,
        description="원본 상한(§5.1 SourceDocument 200MB). EgressPolicy.max_bytes 기본값",
        ge=1,
    )
    policy: StagePolicyPartial | None = None


class ParseConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    router: ParseRouter
    options: ParseOptions
    policy: StagePolicyPartial | None = Field(None, description="parse(텍스트) 행(§4.4)")
    policy_ocr: StagePolicyPartial | None = Field(
        None, description="parse(OCR) 행(§4.4). 생략 시 policy 상속 + queues.ocr"
    )
    policy_detect: StagePolicyPartial | None = Field(
        None,
        description="선택(N, 이 문서 추가). detect 행(§4.4: ingest-cpu, 1m, heartbeat 없음, 3회, parse.unsupported_format·parse.corrupt_container, resumable=false). detect 는 parser 확장 지점 role=format_detector 이므로 parse 아래에 둔다. 생략 시 §4.4 detect 행 그대로, task_queue 는 queues.detect ?? queues.parse",
    )


class Recognizer(RootModel[str]):
    root: str = Field(..., pattern="^[A-Z][A-Z0-9_]*$")


class RejectEntity(RootModel[str]):
    root: str = Field(..., pattern="^[A-Z][A-Z0-9_]*$")


class PiiConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId
    policy: common_types.PiiPolicy = Field(
        ...,
        description="프로파일 기본. CollectionSpec.policies.pii_policy·IngestRequest.pii_policy 중 가장 엄격한 값 적용",
    )
    tokenize_mode: common_types.PiiTokenizeMode | None = None
    recognizers: list[Recognizer] | None = Field(
        None,
        description="명시 활성 인식기(KR_RRN, KR_PHONE, KR_BANK_ACCOUNT, KR_CARD, KR_PASSPORT)",
    )
    reject_entities: list[RejectEntity] | None = Field(
        None,
        description='N(바이블 §7.3 1.3.0, AM-43). 이 목록의 엔티티 타입이 탐지되면 policy 값과 무관하게 문서를 reject(korean-gov 기본값 예 ["KR_RRN"]). policy=reject 와 함께 오면 중복 지정이므로 profile.invalid',
    )


class NormalizeConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    analyzer: PluginRef = Field(..., description="role=korean_analyzer(ADR-0021). lite 필수(검증 규칙 9)")
    sentence_splitter: PluginRef = Field(..., description="role=sentence_splitter")
    pii: PiiConfig = Field(..., description="role=pii_detector. 로딩 실패 시 keep 폴백 금지(E4)")
    policy: StagePolicyPartial | None = None


class LeafMaxTokens(RootModel[int]):
    root: int = Field(..., description="리프 상한(게이트 보유 값, O-09 그리드)", ge=1)


class OverlapRatio(RootModel[float]):
    root: float = Field(..., ge=0.0, le=1.0)


class Fallback(BaseModel):
    """
    구조가 없는 flat_text 폴백 청커
    """

    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId
    max_tokens: int = Field(..., ge=1)
    overlap_ratio: OverlapRatio | GatedValue | None = None
    sentence_window_n: int | None = Field(None, ge=0)


class ChunkConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId
    tokenizer: common_types.TokenizerId = Field(
        ..., description="예산 토크나이저 = 임베딩 모델 토크나이저(검증 규칙 4, O-09)"
    )
    secondary_tokenizers: list[common_types.TokenizerId] | None = Field(
        None, description="token_counts 병기(tiktoken:o200k_base)"
    )
    leaf_max_tokens: LeafMaxTokens | GatedValue = Field(..., description="리프 상한(게이트 보유 값, O-09 그리드)")
    parent_max_tokens: int = Field(..., ge=1)
    merge_min_tokens: int = Field(..., ge=0)
    fallback: Fallback | None = Field(None, description="구조가 없는 flat_text 폴백 청커")
    table_row_group_tokens: int | None = Field(None, ge=1)
    genre_rules: dict[str, Any] | None = Field(
        None,
        description="Genre별 분할 규칙(law_article 등). 열린 객체: 키·값은 청커 플러그인 config_schema가 검증",
    )
    policy: StagePolicyPartial | None = None


class RecountConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId = Field(..., description="chunker 그룹 role=token_counter")
    policy: StagePolicyPartial | None = None


class GeneratedPrefix(BaseModel):
    """
    LLM 접두어(O-05). 모든 프로파일 기본 false, 컬렉션 정책으로 켬
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    enabled: bool
    plugin: common_types.PluginId | None = None
    gate: GateSpec | None = None


class ContextualDocSummary(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    enabled: bool
    plugin: common_types.PluginId | None = None


class Budget(BaseModel):
    """
    프로파일 기본 예산(ADR-0016). CollectionSpec.policies가 컬렉션 값을 가진다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    enrichment_budget_tokens: int = Field(..., ge=0)
    corpus_multiplier_max: float = Field(..., ge=1.0)
    queue: str | None = Field(None, pattern="^[a-z][a-z0-9-]*$")


class EnrichConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    deterministic: list[common_types.PluginId] = Field(
        ...,
        description="결정적 보강 체인(접두어·형태소 키워드·엔티티·파생 메타). 실행 순서 = 배열 순서",
        min_length=1,
    )
    generated_prefix: GeneratedPrefix = Field(
        ...,
        description="LLM 접두어(O-05). 모든 프로파일 기본 false, 컬렉션 정책으로 켬",
    )
    contextual_doc_summary: ContextualDocSummary | None = None
    budget: Budget = Field(
        ...,
        description="프로파일 기본 예산(ADR-0016). CollectionSpec.policies가 컬렉션 값을 가진다",
    )
    policy: StagePolicyPartial | None = Field(None, description="enrich(결정적) 행")
    policy_llm: StagePolicyPartial | None = Field(None, description="enrich(LLM) 행(queues.enrich_llm)")


class Dense(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId
    model_id: str = Field(
        ...,
        description="HF 저장소(BAAI/bge-m3). Producer.model_ids 표기는 {repo}@{revision}",
        min_length=1,
    )
    revision: str = Field(..., description="HF 커밋 SHA(models.lock)", min_length=1)
    dim: int = Field(..., ge=1)
    normalized: bool
    dtype: str | None = Field(None, pattern="^[a-z0-9_]+$")
    quantization: str | None = Field(None, pattern="^[a-z0-9_]+$")


class Sparse(BaseModel):
    """
    learned sparse(sparse_learned 벡터)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId
    vocab_id: str = Field(
        ...,
        description="xlm-roberta-250k 등. 불일치 → embed.space_mismatch",
        min_length=1,
    )


class SparseBm25(BaseModel):
    """
    lite 플랫폼 BM25(ADR-0012; k1=1.2, b=0.75 고정)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId
    k1: float = Field(..., ge=0.0)
    b: float = Field(..., ge=0.0, le=1.0)


class LateInteraction(BaseModel):
    """
    별도 슬롯(ADR-0010, 기본 끔). 백엔드 supports_multivector=false면 자동 비활성 + degraded
    """

    model_config = ConfigDict(
        extra="allow",
    )
    enabled: bool
    plugin: common_types.PluginId | None = None
    model_id: str | None = Field(None, min_length=1)
    revision: str | None = Field(None, min_length=1)
    dim: int | None = Field(None, ge=1)


class EquivalenceGate(BaseModel):
    """
    같은 공간 안 서빙 교체 동등성 게이트(D-16)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    cosine_min: float = Field(..., ge=0.0, le=1.0)
    sample: int = Field(..., ge=1)


class EmbedConfig1(BaseModel):
    """
    dense 필수 + sparse(sparse_learned) 또는 sparse_bm25(lite) 중 하나 이상(D-07 3-way)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    dense: Dense
    sparse: Sparse = Field(..., description="learned sparse(sparse_learned 벡터)")
    sparse_bm25: SparseBm25 | None = Field(None, description="lite 플랫폼 BM25(ADR-0012; k1=1.2, b=0.75 고정)")
    late_interaction: LateInteraction = Field(
        ...,
        description="별도 슬롯(ADR-0010, 기본 끔). 백엔드 supports_multivector=false면 자동 비활성 + degraded",
    )
    equivalence_gate: EquivalenceGate = Field(..., description="같은 공간 안 서빙 교체 동등성 게이트(D-16)")
    batch_max_tokens: int | None = Field(None, ge=1)
    policy: StagePolicyPartial | None = None


class EmbedConfig2(BaseModel):
    """
    dense 필수 + sparse(sparse_learned) 또는 sparse_bm25(lite) 중 하나 이상(D-07 3-way)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    dense: Dense
    sparse: Sparse | None = Field(None, description="learned sparse(sparse_learned 벡터)")
    sparse_bm25: SparseBm25 = Field(..., description="lite 플랫폼 BM25(ADR-0012; k1=1.2, b=0.75 고정)")
    late_interaction: LateInteraction = Field(
        ...,
        description="별도 슬롯(ADR-0010, 기본 끔). 백엔드 supports_multivector=false면 자동 비활성 + degraded",
    )
    equivalence_gate: EquivalenceGate = Field(..., description="같은 공간 안 서빙 교체 동등성 게이트(D-16)")
    batch_max_tokens: int | None = Field(None, ge=1)
    policy: StagePolicyPartial | None = None


class EmbedConfig(RootModel[EmbedConfig1 | EmbedConfig2]):
    root: EmbedConfig1 | EmbedConfig2 = Field(
        ...,
        description="dense 필수 + sparse(sparse_learned) 또는 sparse_bm25(lite) 중 하나 이상(D-07 3-way)",
    )


class IndexBackendConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId = Field(
        ...,
        description="index_backend.{implementation} = CollectionSpec.backends[].backend_id",
    )
    role: backends_1.Role
    named_vectors: list[common_types.VectorName] | None = Field(
        None,
        description="role=vector: 적재하는 named vectors(= embedding_space_ids 키 집합)",
    )
    tenant_isolation: common_types.TenantIsolationTier | None = Field(
        None, description="선택. 있으면 security.tenant_isolation_tier와 같아야 한다"
    )


class Commit(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    strategy: commit_1.Strategy
    flip_order: list[backends_1.Role] = Field(
        ...,
        description="alias 교체 순서(렉시컬 → 벡터). 항목은 backends[].role 값",
        min_length=1,
    )
    cleanup_delay: common_types.Duration


class IndexConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    backends: list[IndexBackendConfig] = Field(
        ...,
        description="plugin 유일, role=vector 정확히 1개",
        max_length=8,
        min_length=1,
    )
    commit: Commit
    tiering: Any | None = None
    policy: StagePolicyPartial | None = None


class IngestConfig(BaseModel):
    """
    바이블 §5.6 ingest {fetch, parse{router, options}, normalize, chunk, recount?, enrich, embed, index}
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    fetch: FetchConfig
    parse: ParseConfig
    normalize: NormalizeConfig
    chunk: ChunkConfig
    recount: RecountConfig | None = None
    enrich: EnrichConfig
    embed: EmbedConfig
    index: IndexConfig


class ChannelConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    channel: common_types.Channel
    retriever: common_types.PluginId = Field(
        ...,
        description="retriever.{implementation}. sparse_bm25 벡터는 channel=lexical + retriever.qdrant_sparse_bm25",
    )
    top_k: int = Field(
        ...,
        description="채널 런당 후보 수. 상한 300 = 바이블 §5.1 CandidateSet 채널 런당 300",
        ge=1,
        le=300,
    )
    timeout_ms: int = Field(..., ge=1)
    weight: float | None = Field(None, description="선택. 있으면 fusion.weights[channel]과 같아야 한다", ge=0.0)


class Weights(RootModel[float]):
    root: float = Field(..., ge=0.0)


class FusionConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    method: common_types.FusionMethod
    k: int = Field(..., description="RRF 상수(검증 규칙 3 필수; 런타임 방어 fuse.k_missing)", ge=1)
    weights: dict[str, Weights] = Field(..., description="채널 가중. 키 집합 = channels[].channel 집합", min_length=1)
    variant_query_weight: float = Field(..., description="변형 질의 기여 가중(O-01: 0.5)", ge=0.0, le=1.0)
    gate: GateSpec | None = None


class HydrateConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    top_n: int = Field(..., description=">= max(rerank.top_n_in, pack.k_max)(검증 규칙 11)", ge=1)
    backend: common_types.PluginId = Field(..., description="payload 1회 배치 조회 백엔드(role=vector 백엔드 중 하나)")
    with_vectors: bool


class RerankConfig(BaseModel):
    """
    enabled=false(lite 생략)면 나머지 키 선택. 그 외에는 plugin~normalization 필수
    """

    model_config = ConfigDict(
        extra="allow",
    )
    enabled: bool | None = None
    plugin: common_types.PluginId | None = None
    model_id: str | None = Field(None, min_length=1)
    response_schema: common_types.RerankResponseSchema | None = None
    backend: common_types.RerankBackend | None = None
    top_n_in: int | None = Field(None, ge=1)
    top_n_out: int | None = Field(None, ge=1)
    max_tokens_per_text: int | None = Field(None, ge=1)
    timeout_ms: int | None = Field(None, ge=1)
    normalization: common_types.ScoreNormalization | None = None
    gate: GateSpec | None = None


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
    seed: int = Field(..., ge=0)
    scheme: str = Field(..., pattern="^[a-z0-9_]+$")
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


class ParentExpand(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    ratio_threshold: float = Field(..., ge=0.0, le=1.0)
    max_parent_tokens: int = Field(..., ge=1)
    text_store: parent_expand_1.TextStore


class SentenceWindow(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    n: int = Field(..., ge=1)


class Compress(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    plugin: common_types.PluginId


class PostprocessConfig(BaseModel):
    """
    order는 고정 순서 [relevance_gate, dedup, mmr, parent_expand, dedup, sentence_window, compress]의 부분 수열(D-07). reorder·citation_align은 pack 내부
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    order: list[common_types.PostprocessStep] = Field(..., max_length=7, min_length=1)
    relevance_gate: RelevanceGate
    dedup: Dedup
    mmr: Mmr | None = None
    parent_expand: ParentExpand | None = None
    sentence_window: SentenceWindow | None = None
    compress: Compress | None = None


class Tokenizer(BaseModel):
    """
    팩 예산 토크나이저(대상 LLM으로 재계산, O-09). chunk.tokenizer와 카운터 일치 검증(규칙 4)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    provider: tokenizer_1.Provider
    model: str = Field(..., description="대상 LLM 모델 식별자(배포별 값)", min_length=1)
    count_method: common_types.CountMethod
    calibration_ratio: float | None = Field(..., gt=0.0)
    safety_margin: float = Field(..., ge=0.0, le=1.0)


class ConfidenceTiers(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    high: float = Field(..., ge=0.0, le=1.0)
    medium: float = Field(..., ge=0.0, le=1.0)


class PackConfig(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    k_max: int = Field(
        ...,
        description="최종 팩 항목 수 상한. 상한 20 = 바이블 §5.1 ContextPack 항목 20(11 Budget.k_max 1..20·items maxItems 20, 16 FeedbackEvent.cite_ids <= 20 과 같은 값)",
        ge=1,
        le=20,
    )
    max_context_tokens: int = Field(..., ge=1)
    reserved_answer_tokens: int = Field(..., ge=0)
    ordering: common_types.OrderingStrategy
    renderer: common_types.Renderer
    instructions_template_id: str | None = Field(
        None,
        description="렌더러 지시문 템플릿 {id}@{n}",
        pattern="^[a-z][a-z0-9-]*@[0-9]+$",
    )
    tokenizer: Tokenizer = Field(
        ...,
        description="팩 예산 토크나이저(대상 LLM으로 재계산, O-09). chunk.tokenizer와 카운터 일치 검증(규칙 4)",
    )
    table_format_preference: list[common_types.TableFormat] = Field(..., min_length=1)
    overflow_policy: list[common_types.OverflowPolicy] = Field(..., min_length=1)
    confidence_tiers: ConfidenceTiers
    data_marking: common_types.DataMarking | None = Field(None, description="선택. korean-gov 는 datamark")
    citation_style: common_types.CitationStyle | None = None


class LatencyBudget(BaseModel):
    """
    p95 목표(ms, 초안). 부분 예산 합 <= total
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    total: int = Field(..., ge=1)
    plan: int | None = Field(None, ge=0)
    retrieve: int | None = Field(None, ge=0)
    rerank: int | None = Field(None, ge=0)
    postprocess: int | None = Field(None, ge=0)
    pack: int | None = Field(None, ge=0)


class QueryConfig(BaseModel):
    """
    바이블 §5.6 query {transform, channels, fusion, hydrate, rerank, postprocess, pack, latency_budget_ms}
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    transform: list[common_types.PluginId] = Field(
        ...,
        description="query_transformer 파이프 순서(normalize_ko → router → self_query → rewrite → expand)",
        min_length=1,
    )
    channels: list[ChannelConfig] = Field(..., description="channel 유일", max_length=7, min_length=1)
    fusion: FusionConfig
    hydrate: HydrateConfig
    rerank: RerankConfig
    postprocess: PostprocessConfig
    pack: PackConfig
    latency_budget_ms: LatencyBudget


class Authz(BaseModel):
    """
    닫힌 객체(플랫폼 인프라 설정, 플러그인 config_schema 없음)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    plugin: str = Field(
        ...,
        description="cedar | static_roles(플랫폼 인프라, 확장 지점 아님)",
        pattern="^[a-z][a-z0-9_]*$",
    )
    policy_version: str = Field(..., description="SecurityContext.policy_version 원천", min_length=1)


class RateLimit(BaseModel):
    """
    닫힌 객체(E3 인프라 설정)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    store: rate_limit_1.Store
    fail_mode: rate_limit_1.FailMode


class SecurityConfig(BaseModel):
    """
    바이블 §5.6 security {authn, authz, rate_limit, tenant_isolation_tier, tiering: TieringPolicy}
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    authn: common_types.AuthMethod = Field(..., description="기본 인증 방식(E1). mTLS 추가 계층은 배포 매니페스트")
    authz: Authz = Field(..., description="닫힌 객체(플랫폼 인프라 설정, 플러그인 config_schema 없음)")
    rate_limit: RateLimit = Field(..., description="닫힌 객체(E3 인프라 설정)")
    tenant_isolation_tier: common_types.TenantIsolationTier = Field(
        ...,
        description="새 컬렉션의 기본 등급(§7.2). 모든 vector·lexical 백엔드의 IndexBackendCapabilities.tenant_isolation[]에 포함되어야 한다",
    )
    tiering: common_types.TieringPolicy = Field(
        ...,
        description="E15 승격 정책(ADR-0028). 정본 경로는 여기이며 ingest.index.tiering은 거부된다",
    )


class ObservabilityConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    content_capture: observability_1.ContentCapture
    tenant_id_hash: bool = Field(
        ...,
        description="스팬 rag.tenant_id_hash만 기록(§6.5). false 금지 대상은 아니지만 korean-gov는 true 고정",
    )
    content_capture_locked: bool | None = Field(
        None,
        description="선택(N). true면 RAG_OTEL__CONTENT_CAPTURE 환경 변수로 재정의 불가(korean-gov NO_CONTENT 잠금)",
    )


class EvalGate(BaseModel):
    """
    프로파일 전체 회귀 게이트(EvalReport.gate_result 판정 입력)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    min: float | None = None
    max: float | None = None
    max_regression: float | None = Field(None, ge=0.0)
    p: float | None = Field(None, gt=0.0, le=1.0)
    correction: gates_1.Correction | None = None
    warn_below: float | None = None


class Dataset(RootModel[str]):
    root: str = Field(..., max_length=64, pattern="^[a-z0-9][a-z0-9-]*$")


class EvalConfig(BaseModel):
    """
    바이블 §5.6 eval {datasets[], gates}
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    datasets: list[Dataset] = Field(
        ...,
        description="기본 평가 데이터셋. 항목은 EvalDataset.name(16 §2.1; 같은 name 의 최신 행으로 해소, 16 EF-1). GateSpec.dataset 생략 시 [0]",
    )
    gates: dict[constr(pattern=r"^[a-z][a-z0-9_]*(@[1-9][0-9]*)?$", max_length=64), EvalGate] = Field(
        ...,
        description="키는 MetricKey(16 GateOutcome.metric 과 같은 형식)",
        min_length=1,
    )


class Profile(BaseModel):
    """
    파이프라인 구성 프리셋(바이블 §5.6 최상위 키, §7.3 YAML 정본). 운영자가 YAML로 생산하고 로더·검증기(§7.4)와 모든 스테이지가 소비한다. extends 단일 상속·깊은 병합(배열 교체)을 해소하고 StagePolicy 기본값을 채운 결과의 canonical_json BLAKE3가 profile_hash다. 이 스키마는 YAML 원본과 해소 결과 양쪽에 적용되며 default 키워드를 갖지 않는다(14 §8). 스테이지 값 객체는 {plugin, policy, 플러그인 config_schema 필드}라 열린 객체(additionalProperties: true)이고 나머지 필드는 플러그인 config_schema가 로딩 시 검증한다. ProfileId·LicensePolicy·Profile.ingest.index.backends.role 은 collection-spec 스키마의 같은 정의의 사본이다(계약 간 교차 $ref 회피; CI 동치 대조). 소유 문서: docs/03-contracts/15-collection-profile-and-policy-contracts.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver = Field(..., description='계약 버전. 초기 "1.0.0"')
    schema_type: Literal["Profile"] | None = Field(
        None,
        description="선택(N, 이 문서 추가). 해소 결과(GET /v1/profiles/{profile_id}) 식별용",
    )
    profile_id: ProfileId = Field(
        ...,
        description="kebab-case(§6.1). 내장 base, lite, standard, premium, korean-gov",
    )
    version: common_types.Semver = Field(
        ...,
        description="내용 버전. 값 변경 = version 증가 = profile_hash 변경 = 컬렉션 blue/green(§7.4)",
    )
    description: str | None = Field(None, description="선택(N). 운영자 설명", max_length=1024)
    extends: ProfileId | None = Field(
        ...,
        description="단일 부모. null은 조상 전용 프로파일(base)이며 컬렉션에 바인딩할 수 없다. 배열은 자식 값으로 교체된다(ADR-0031)",
    )
    tier: common_types.ProfileTier = Field(
        ..., description="인프라 등급. 내장 프로파일은 profile_id와 같고 base는 lite"
    )
    license_policy: LicensePolicy = Field(..., description="로딩 검증 (1)의 상한(ADR-0001)")
    runtime: RuntimeConfig
    ingest: IngestConfig
    query: QueryConfig
    security: SecurityConfig
    observability: ObservabilityConfig
    eval: EvalConfig
    profile_hash: common_types.Hex64 | None = Field(
        None,
        description='N(바이블 §6.2·§5.6 1.3.0, AM-34 완전성 #12). H("profile", canonical_json(resolved))(§3.8). 로더가 계산해 채우는 파생값 — 프로파일 작성자가 직접 쓰지 않는다(readOnly). CollectionSpec.profile_hash·IndexCommit·QueryPlan·ContextPack·EvalRun.profile_hash 기록 지점의 정본 계산식',
    )
