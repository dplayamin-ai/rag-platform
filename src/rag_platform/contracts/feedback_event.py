"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from . import common_types


class FeedbackEvent(BaseModel):
    """
    온라인 피드백 계약(바이블 §5.6, §14 POST /v1/feedback, ADR-0023). 한 ContextPack(pack_id)에 대한 다운스트림 신호 — LLM 응답이 인용한 cite_ids(cited), 사용자 평점(rated), 정정(corrected). cite_id 는 pack_id 의 인용 맵으로 chunk_id·record_id·document_id 에 역추적된다. feedback_id·tenant_id·created_at·pii_policy_applied 는 서버가 채운다(readOnly; 요청 본문에 오면 422, E1). comment 는 PII 정책 적용 후에만 저장된다(정책 원천은 미정 — 바이블 §13.1 tenants.policies 에 pii_policy 없음; 초안은 팩 컬렉션들의 CollectionSpec.policies.pii_policy 중 최엄격, 이 문서 §5.2·미해결 이슈 18). 정본은 PostgreSQL feedback_events 원장 행. 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/16-eval-feedback-and-sidecar-contracts.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver | None = Field(
        None,
        description='선택(N). 계약 버전 "1.0.0". 바이블 §5.6 미등재(미해결 이슈 1)',
    )
    feedback_id: common_types.Ulid = Field(..., description="서버 발급(바이블 §6.1)")
    tenant_id: common_types.Ulid = Field(
        ...,
        description="SecurityContext.tenant_id 에서 도출(보안 삼중항 1). 본문에 오면 422",
    )
    query_id: common_types.Ulid = Field(..., description="= ContextPack.query_id(pack_id 와 일치해야 한다)")
    pack_id: common_types.Ulid = Field(
        ...,
        description="피드백 대상 ContextPack. 인용 맵(cite_id → chunk_id·record_id·document_id·collection_id·doc_version)의 키",
    )
    kind: common_types.FeedbackKind = Field(..., description="cited / rated / corrected. 종류별 필수 필드는 allOf")
    cite_ids: list[common_types.CiteId] = Field(
        ...,
        description="이 피드백이 가리키는 팩 항목(d1..dK). 팩에 존재하는 cite_id 만(불변식 EF-18). cited 면 1개 이상, 그 외는 빈 배열 허용",
        max_length=20,
    )
    rating: int | None = Field(None, description="1..5. rated 면 필수", ge=1, le=5)
    comment: str | None = Field(
        None,
        description="PII 정책 적용 후 저장된 텍스트(원문 저장 금지). corrected 면 정정 내용으로 필수. 이벤트·로그에 싣지 않는다",
        max_length=2000,
        min_length=1,
    )
    experiment_id: str | None = Field(
        None,
        description="선택(N). 인터리빙·A/B 귀속 키(QueryRequest.experiment_id 복사; 서버가 pack 에서 채울 수 있음). 바이블 §5.6 미등재(미해결 이슈 1)",
        max_length=128,
        min_length=1,
    )
    pii_policy_applied: common_types.PiiPolicy | None = Field(
        None,
        description="선택(N, readOnly). 서버가 comment 에 적용한 정책(mask | tokenize | exclude | keep)을 기록한다. comment 를 저장한 서버는 항상 채운다(EF-19 서버 불변식; 스키마 필수는 아님 — 바이블 §5 서문 N 규칙). reject 는 저장 거부이므로 나타나지 않는다(not). 바이블 §5.6 미등재(미해결 이슈 1)",
    )
    created_at: common_types.DateTime = Field(..., description="서버 수신 시각")
