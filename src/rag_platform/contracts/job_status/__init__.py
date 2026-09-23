"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from .. import common_types
from . import JobStatus as JobStatus_1
from .JobStatus import progress as progress_1


class Stage(RootModel[str]):
    root: str = Field(
        ...,
        description="Y(nullable). 현재/마지막 스테이지. 시작 전 queued는 null",
        max_length=32,
        pattern="^[a-z][a-z0-9_]*$",
    )


class WorkflowId(RootModel[str]):
    root: str = Field(
        ...,
        description="Y(nullable). Temporal 워크플로우 ID(문서 잡 = job_id). LocalRunner는 null",
        max_length=255,
        min_length=1,
    )


class IdempotencyKey(RootModel[str]):
    root: str = Field(
        ...,
        description="Y(null 허용; 바이블 §1.2 1.3.0 제약 완화, AM-44). 접수 Idempotency-Key(가시 ASCII 1..255, (tenant_id, key) 유일). 배치 자식 잡은 null(배치 키는 idempotency_keys.job_ids 에만 저장); 내부 트리거 잡은 internal:{workflow_type}:{ulid}(초안)",
        pattern="^[!-~]{1,255}$",
    )


class JobCost(BaseModel):
    """
    누적 비용(바이블 §5.6). usage_ledger의 원천
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    llm_tokens_in: int = Field(..., ge=0)
    llm_tokens_out: int = Field(..., ge=0)
    cost_usd: float = Field(..., ge=0.0)
    gpu_seconds: float = Field(..., ge=0.0)


class JobProgress(BaseModel):
    """
    진행률 {done, total, unit}(바이블 §5.6). done ≤ total
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    done: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
    unit: progress_1.Unit


class JobStatus(BaseModel):
    """
    PostgreSQL jobs 원장의 읽기 모델(바이블 §5.6·§11.5·§13.1, D-08, ADR-0017). 잡의 종류·상태·스테이지·진행률·시도·비용·오류·시각을 담는다. 봉투 계약이 아니며 산출물로 저장되지 않는다. 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver = Field(..., description='계약 버전. 초기 "1.0.0"')
    schema_type: Literal["JobStatus"] | None = Field(
        None,
        description="선택(N). 바이블 §5.6 미등재 — 조회 응답·dataschema 소비자 편의",
    )
    job_id: common_types.Ulid = Field(..., description="잡 ID = Temporal 워크플로우 ID")
    tenant_id: common_types.Ulid = Field(..., description="보안 삼중항 1")
    collection_id: common_types.Ulid = Field(..., description="보안 삼중항 2")
    kind: common_types.JobKind
    state: common_types.JobState = Field(..., description="바이블 §11.5 상태 기계")
    stage: Stage | None = Field(..., description="Y(nullable). 현재/마지막 스테이지. 시작 전 queued는 null")
    progress: JobProgress
    attempts: int = Field(
        ...,
        description="현재(마지막) 스테이지의 시도 번호. queued 0, 첫 시도 1, 재시도마다 +1, 새 스테이지 1로 재설정",
        ge=0,
    )
    workflow_run_id: common_types.Uuid | None = Field(
        ..., description="Y(nullable). Temporal run id. LocalRunner·시작 전은 null"
    )
    workflow_id: WorkflowId | None = Field(
        ...,
        description="Y(nullable). Temporal 워크플로우 ID(문서 잡 = job_id). LocalRunner는 null",
    )
    idempotency_key: IdempotencyKey | None = Field(
        ...,
        description="Y(null 허용; 바이블 §1.2 1.3.0 제약 완화, AM-44). 접수 Idempotency-Key(가시 ASCII 1..255, (tenant_id, key) 유일). 배치 자식 잡은 null(배치 키는 idempotency_keys.job_ids 에만 저장); 내부 트리거 잡은 internal:{workflow_type}:{ulid}(초안)",
    )
    request_id: common_types.Ulid | None = Field(None, description="선택(N). 접수 요청 ID")
    waiting_for: common_types.Ulid | None = Field(
        None,
        description="선택(N, null 허용). 문서 단위 직렬화로 대기 중인 앞 job_id. state=queued에서만 non-null",
    )
    document_id: common_types.Ulid | None = Field(None, description="선택(N, null 허용). 문서 잡은 non-null 필수")
    index_commit_id: common_types.Ulid | None = Field(
        None, description="선택(N, null 허용). 이 잡의 IndexCommit.commit_id"
    )
    from_stage: JobStatus_1.FromStage | None = Field(
        None, description="선택(N, null 허용). 재처리·retry 시작 스테이지(바이블 §14)"
    )
    last_error: common_types.StageError | None = Field(
        None,
        description="선택(N, null 허용). 최근 실패 시도의 오류(13 J2). 콘텐츠 미포함, ≤4KB",
    )
    degraded: list[common_types.DegradedEntry] = Field(
        ..., description="상류 DegradedEntry 합집합. 빈 배열 허용", max_length=64
    )
    cost: JobCost
    priority: int = Field(..., description="기본 5", ge=0, le=9)
    status_url: common_types.Uri = Field(..., description="GET /v1/jobs/{job_id} 절대 URL")
    events_url: common_types.Uri = Field(..., description='= status_url + "/events"')
    created_at: common_types.DateTime = Field(..., description="접수 시각")
    started_at: common_types.DateTime | None = Field(None, description="선택(N, null 허용). 첫 액티비티 시작 시각")
    updated_at: common_types.DateTime = Field(..., description="마지막 원장 갱신 시각")
    finished_at: common_types.DateTime | None = Field(
        None, description="선택(N, null 허용). 종결 시각. 종결 상태에서 non-null"
    )
    deadline_at: common_types.DateTime | None = Field(None, description="선택(N, null 허용). IngestRequest.deadline_at")
