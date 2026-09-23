"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, constr

from .. import common_types, eval_dataset, eval_run
from .EvalReport.gate_result import failed_gates as failed_gates_1


class ArtifactsRef(BaseModel):
    """
    eval/runs/{run_id}/per_query.jsonl(행 = $defs/PerQueryRecord; 바이블 §13.3 반영 제안, 미해결 이슈 2). 계약 산출물이 아니므로 schema_type 없음
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: Literal["application/x-ndjson"] = Field(
        ...,
        description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME",
        pattern="^[a-z]+/[A-Za-z0-9!#$&^_.+-]+$",
    )
    schema_type: common_types.SchemaTypeName | None = Field(
        None,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
    )
    schema_version: common_types.Semver | None = Field(None, description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class RunRef(BaseModel):
    """
    선택(N). eval/runs/{run_id}/run.trec — TREC run 텍스트(query_id Q0 doc_id rank score run_tag; run_tag = run_id). ranx·ir_measures 교차 검증 입력. 바이블 §5.6 미등재(미해결 이슈 1)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: Literal["text/plain"] = Field(
        ...,
        description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME",
        pattern="^[a-z]+/[A-Za-z0-9!#$&^_.+-]+$",
    )
    schema_type: common_types.SchemaTypeName | None = Field(
        None,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
    )
    schema_version: common_types.Semver | None = Field(None, description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class PValues(RootModel[float]):
    root: float = Field(..., ge=0.0, le=1.0)


class EvalComparison(BaseModel):
    """
    바이블 §5.6 comparison{baseline_run_id, deltas, p_values, correction: "holm"}. 질의 단위 쌍대 검정 p값에 Holm 보정을 적용한 값이 p_values 다(ADR-0023)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    baseline_run_id: common_types.Ulid = Field(..., description="같은 dataset_id 의 completed 런. run_id 와 다르다")
    deltas: dict[constr(pattern=r"^[a-z][a-z0-9_]*(@[1-9][0-9]*)?$", max_length=64), float] = Field(
        ...,
        description="metrics[k] − baseline.metrics[k]. 키는 metrics 의 부분집합(≤ 64)",
        max_length=64,
        min_length=1,
    )
    p_values: dict[constr(pattern=r"^[a-z][a-z0-9_]*(@[1-9][0-9]*)?$", max_length=64), PValues] = Field(
        ...,
        description="Holm 보정 후 p값. 키 집합 = deltas 키 집합",
        max_length=64,
        min_length=1,
    )
    correction: Literal["holm"] = Field(..., description="고정값(D-12)")
    stat_test: str | None = Field(
        None,
        description="선택(N). 보정 전 검정 이름(예 fisher_randomization, paired_t, tukey_hsd; 정본은 08-evaluation/02). 바이블 §5.6 미등재(미해결 이슈 1)",
        max_length=64,
        pattern="^[a-z][a-z0-9_]*$",
    )


class Severity(StrEnum):
    """
    fail 은 passed 를 false 로 만들고, warn(warn_below 등)은 warned_gates 에만 기록된다
    """

    fail = "fail"
    warn = "warn"


class SpanHitRank(RootModel[int]):
    root: int = Field(..., ge=1)


class PerQueryRecord(BaseModel):
    """
    per_query.jsonl 한 행(질의별 메트릭). 질의 본문·청크 본문은 싣지 않는다(ID·수치만)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    query_id: eval_dataset.QueryId
    metrics: dict[constr(pattern=r"^[a-z][a-z0-9_]*(@[1-9][0-9]*)?$", max_length=64), float] = Field(
        ..., max_length=64, min_length=1
    )
    top_doc_ids: list[common_types.Ulid] | None = Field(
        None,
        description="선택(N). 상위 문서 ID(순위순). TREC run 과 중복되므로 run_ref 가 있으면 생략 가능",
        max_length=100,
    )
    span_hit_ranks: list[SpanHitRank] | None = Field(
        None,
        description="선택(N). answer_spans 와 겹친 청크의 최종 순위(1-based)",
        max_length=100,
    )


class GateOutcome(BaseModel):
    """
    게이트 하나의 판정. gate_path 는 프로파일 YAML 경로(eval.gates.ndcg@10 또는 게이트가 붙은 파라미터 경로 ingest.chunk.leaf_max_tokens), condition 은 그 게이트 객체 안에서 실패한 키
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    gate_path: str = Field(
        ...,
        description="프로파일 YAML 경로(바이블 §7.3)",
        max_length=256,
        pattern="^[a-z][a-z0-9_]*(\\.[a-z0-9_@-]+)*$",
    )
    metric: eval_run.MetricKey = Field(..., description="판정에 쓴 메트릭 키(gate.metric 또는 eval.gates 의 키)")
    condition: failed_gates_1.Condition
    expected: float = Field(
        ...,
        description="통과에 필요한 값 하나의 의미만(min 0.80, max 800, max_regression 0.01, p 0.05, warn_below 0.7, min_delta 0.03, min_delta_pt 2, min_qrels 200, max_cost_per_doc_usd 0.05; grid 는 그리드 중 metric 이 최고인 후보 값)",
    )
    observed: float | None = Field(
        ...,
        description="관측값(min·max·warn_below 는 metrics[k], max_regression 은 −deltas[k], p 는 p_values[k], min_delta 는 deltas[k], min_delta_pt 는 deltas[k]×100, min_qrels 는 qrels 수, grid 는 프로파일의 현재 value). 계산 불가면 null",
    )
    dataset: str | None = Field(
        None,
        description="선택(N). 게이트가 지정한 데이터셋 이름(EvalDataset.name)",
        max_length=64,
        pattern="^[a-z0-9][a-z0-9-]*$",
    )
    severity: failed_gates_1.Severity
    detail: str | None = Field(
        None,
        description="선택(N). 영문 진단 문구. 콘텐츠·질의 문자열 미포함",
        max_length=512,
    )


class FailedGate(GateOutcome):
    severity: Literal["fail"] = Field(
        ...,
        description="fail 은 passed 를 false 로 만들고, warn(warn_below 등)은 warned_gates 에만 기록된다",
    )


class WarnedGate(GateOutcome):
    severity: Literal["warn"] = Field(
        ...,
        description="fail 은 passed 를 false 로 만들고, warn(warn_below 등)은 warned_gates 에만 기록된다",
    )


class GateResult(BaseModel):
    """
    바이블 §5.6 gate_result{passed, failed_gates[]} + warned_gates(N). passed ⇔ failed_gates 가 비어 있다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    passed: bool = Field(
        ...,
        description="true 면 이 런이 인용된 프로파일 값 변경이 허용된다(바이블 §7.4)",
    )
    failed_gates: list[FailedGate] = Field(..., description="severity=fail 항목만", max_length=64)
    warned_gates: list[WarnedGate] | None = Field(
        None,
        description="선택(N). warn_below 등 경고 게이트(judged@10 < 0.7 → qrels 보강 필요). passed 에 영향 없음. 바이블 §5.6 미등재(미해결 이슈 1)",
        max_length=64,
    )


class EvalReport(BaseModel):
    """
    평가 결과 계약(바이블 §5.6·§7.4, ADR-0023). 한 EvalRun 의 메트릭 집계(metrics; 질의 평균 또는 런 단위 값), 베이스라인 대비 Holm 보정 비교(comparison), 프로파일 게이트 판정(gate_result), 질의별 산출물 참조(artifacts_ref)를 담는다. gate_result.passed 는 프로파일 품질 기본값 변경의 유일한 판정자(바이블 §7.4). 정본은 PostgreSQL eval_reports 원장 행. MetricKey 는 urn:rag:schema:eval-run:1 을, 공용 타입은 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/16-eval-feedback-and-sidecar-contracts.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver | None = Field(
        None,
        description='선택(N). 계약 버전 "1.0.0". 바이블 §5.6 미등재(미해결 이슈 1)',
    )
    run_id: common_types.Ulid = Field(..., description="EvalRun.run_id(status=completed). 리포트는 런당 1개")
    tenant_id: common_types.Ulid | None = Field(
        None,
        description="선택(N). EvalRun.tenant_id 복사(서버 도출; 하네스가 항상 채운다, EF-30). 바이블 §5.6 미등재(미해결 이슈 1)",
    )
    dataset_id: common_types.Ulid | None = Field(
        None,
        description="선택(N). EvalRun.dataset_id 복사(외부 소비자 편의). 바이블 §5.6 미등재(미해결 이슈 1)",
    )
    profile_hash: common_types.Hex64 | None = Field(
        None,
        description="선택(N). EvalRun.profile_hash 복사. 바이블 §5.6 미등재(미해결 이슈 1)",
    )
    query_count: int | None = Field(
        None,
        description="선택(N). 집계에 포함된 질의 수(검정력 판단). 바이블 §5.6 미등재(미해결 이슈 1)",
        ge=1,
    )
    metrics: dict[constr(pattern=r"^[a-z][a-z0-9_]*(@[1-9][0-9]*)?$", max_length=64), float] = Field(
        ...,
        description="질의 평균 또는 런 단위 집계값(키별 정의 이 문서 §4.2; ndcg@k 는 선형 이득 고정). ≤ 64 키(metrics_requested 상한과 동일, §8). EvalRun.metrics_requested 를 포함해야 한다",
        max_length=64,
        min_length=1,
    )
    comparison: EvalComparison | None = Field(
        None,
        description="선택(N, null 허용). 베이스라인 런 대비 비교. 없으면 절대 게이트(min·warn_below)만 판정",
    )
    gate_result: GateResult
    artifacts_ref: ArtifactsRef = Field(
        ...,
        description="eval/runs/{run_id}/per_query.jsonl(행 = $defs/PerQueryRecord; 바이블 §13.3 반영 제안, 미해결 이슈 2). 계약 산출물이 아니므로 schema_type 없음",
    )
    run_ref: RunRef | None = Field(
        None,
        description="선택(N). eval/runs/{run_id}/run.trec — TREC run 텍스트(query_id Q0 doc_id rank score run_tag; run_tag = run_id). ranx·ir_measures 교차 검증 입력. 바이블 §5.6 미등재(미해결 이슈 1)",
    )
    created_at: common_types.DateTime = Field(..., description="리포트 확정 시각 = EvalRun.finished_at")
