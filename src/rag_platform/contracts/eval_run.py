"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from . import common_types


class IndexCommitsRef(BaseModel):
    """
    선택(N). eval/runs/{run_id}/index_commits.jsonl(행 = $defs/IndexCommitRecord). 커밋이 1,000개를 넘을 때만(전체 current 커밋 목록). 바이블 §5.6 미등재(미해결 이슈 4)
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


class MetricKey(RootModel[str]):
    root: str = Field(
        ...,
        description="메트릭 키 {metric}[@{k}]. 정본 키 ndcg@10, recall@20, mrr, span_hit_rate@10, judged@10(바이블 §5.6); 지수 이득은 ndcg_exp@k 로만(ADR-0023). EvalReport.metrics·comparison·GateOutcome.metric 이 참조",
        max_length=64,
        pattern="^[a-z][a-z0-9_]*(@[1-9][0-9]*)?$",
    )


class IndexCommitRecord(BaseModel):
    """
    index_commits.jsonl 한 행(커밋 1,000개 초과 코퍼스의 전체 current 커밋 목록; 08-index-commit §8 정의)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    commit_id: common_types.Ulid
    document_id: common_types.Ulid
    index_generation: int = Field(..., ge=1)


class EvalRun(BaseModel):
    """
    평가 실행 계약(바이블 §5.6, ADR-0023). 하나의 골든셋(dataset_id)을 하나의 해소된 프로파일(profile_hash)로, 평가 시작 시점의 문서별 current 커밋 집합(index_commit_ids; documents.current_commit_id 가 가리키는 커밋, 08-index-commit §8·IC-5)에 대해 실행한 기록이다. run_id 는 EvalRun 전용 식별자(바이블 §6.1·§6.4). 정본은 PostgreSQL eval_runs 원장 행. 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/16-eval-feedback-and-sidecar-contracts.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver | None = Field(
        None,
        description='선택(N). 계약 버전 "1.0.0". 바이블 §5.6 미등재(미해결 이슈 1)',
    )
    run_id: common_types.Ulid = Field(..., description="EvalRun 전용 식별자(바이블 §6.1). 서버 발급")
    tenant_id: common_types.Ulid | None = Field(
        None,
        description="선택(N). 데이터셋 소유 테넌트(서버 도출). 바이블 §5.6 미등재(미해결 이슈 1)",
    )
    dataset_id: common_types.Ulid = Field(..., description="EvalDataset.dataset_id")
    profile_id: str = Field(
        ...,
        description="kebab-case(바이블 §6.1). 평가 대상 프로파일",
        max_length=64,
        pattern="^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
    )
    profile_hash: common_types.Hex64 = Field(
        ...,
        description='H("profile", canonical_json(해소된 프로파일)). 실행된 모든 QueryPlan.profile_hash 와 같아야 한다(ADR-0023 준수 5)',
    )
    index_commit_ids: list[common_types.Ulid] = Field(
        ...,
        description="평가 시작 시점 corpus_collection_id 의 문서별 current 커밋 = documents.current_commit_id 가 가리키는 커밋(08-index-commit §8·IC-5; committed ∧ superseded_by 없음은 필요조건일 뿐이며 재색인 모드 A 채움 중의 green 커밋은 포함하지 않는다) ULID 오름차순. 1,000 초과 코퍼스는 앞 1,000개만 두고 전체는 index_commits_ref, 완전성은 index_commits_hash 로 검증(12 EvalRunCompletedData maxItems 1000 과 동일; 이 문서 §8, 미해결 이슈 4)",
        max_length=1000,
        min_length=1,
    )
    index_commits_hash: common_types.Hex64 | None = Field(
        None,
        description='선택(N). H("commits", *sorted(전체 current commit_id)). 스키마상 N 이지만 하네스가 항상 채운다(EF-9); index_commits_ref 가 있으면 필수(allOf). 바이블 §5.6 미등재(미해결 이슈 4)',
    )
    index_commits_ref: IndexCommitsRef | None = Field(
        None,
        description="선택(N). eval/runs/{run_id}/index_commits.jsonl(행 = $defs/IndexCommitRecord). 커밋이 1,000개를 넘을 때만(전체 current 커밋 목록). 바이블 §5.6 미등재(미해결 이슈 4)",
    )
    status: common_types.EvalRunStatus = Field(..., description="running → completed | failed(이 문서 §3.2 상태 기계)")
    judge_model: str | None = Field(
        None,
        description="LLM-judge 모델({repo}@{revision} 표기 권장, 바이블 §6.1). 평가 대상 프로파일의 리랭커·LLM 보강 모델과 다른 계열(ADR-0023 준수 10). 판정 미사용은 null 또는 생략",
        max_length=256,
        min_length=1,
    )
    experiment_id: str | None = Field(
        None,
        description="인터리빙·A/B 실험 ID(QueryRequest.experiment_id 와 같은 값 공간). FeedbackEvent.experiment_id 귀속 키",
        max_length=128,
        min_length=1,
    )
    baseline_run_id: common_types.Ulid | None = Field(
        None,
        description="선택(N). 비교 기준 런. EvalReport.comparison.baseline_run_id 와 같아야 한다. 바이블 §5.6 미등재(미해결 이슈 1)",
    )
    metrics_requested: list[MetricKey] = Field(
        ...,
        description="요청 메트릭 키. completed 리포트의 metrics 는 이 집합을 포함한다",
        max_length=64,
        min_length=1,
    )
    started_at: common_types.DateTime
    finished_at: common_types.DateTime | None = Field(
        None, description="running 이면 null 또는 생략, 종결 상태면 필수(allOf)"
    )
    job_id: common_types.Ulid | None = Field(
        None,
        description="선택(N). JobKind=evaluate 잡(eval.run.v1 워크플로우 ID). 바이블 §5.6 미등재(미해결 이슈 1)",
    )
    error: common_types.StageError | None = Field(
        None,
        description="선택(N). status=failed 의 최종 오류(retryable=false). LocalRunner 크래시·잡 취소는 error 없이 failed 가 허용된다(13-error-model §4.3 예외). 콘텐츠·질의 문자열 미포함. 바이블 §5.6 미등재(미해결 이슈 1)",
    )
