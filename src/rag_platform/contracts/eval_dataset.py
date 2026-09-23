"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from . import common_types


class QrelsRef(BaseModel):
    """
    eval/datasets/{dataset_id}/qrels.jsonl(바이블 §13.3). 행 = $defs/QrelsRecord. 계약 산출물이 아니므로 schema_type 없음
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


class AnswerSpansRef(BaseModel):
    """
    eval/datasets/{dataset_id}/answer_spans.jsonl(바이블 §13.3). 행 = $defs/AnswerSpanRecord
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


class TopicsRef(BaseModel):
    """
    선택(N). eval/datasets/{dataset_id}/topics.jsonl. 행 = $defs/TopicRecord(질의 본문). 바이블 §5.6·§13.3 미등재(미해결 이슈 2)
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


class EvalDataset(BaseModel):
    """
    평가 골든셋 등록 계약(바이블 §5.6, D-12, ADR-0023). 진실값은 TREC qrels(문서 단위 관련성)와 answer_spans(문서 ID + doc_version + element_path + 원문 코드포인트 구간)이며 둘은 JSON Lines 산출물(ArtifactRef)로만 참조한다. 정본은 PostgreSQL eval_datasets 원장 행(바이블 §13.1). 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/16-eval-feedback-and-sidecar-contracts.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver | None = Field(
        None,
        description='선택(N). 계약 버전 "1.0.0". 바이블 §5.6 미등재(미해결 이슈 1)',
    )
    dataset_id: common_types.Ulid = Field(
        ...,
        description="서버 발급(바이블 §6.1). POST /v1/eval/datasets 본문에 오면 422",
    )
    tenant_id: common_types.Ulid | None = Field(
        None,
        description="선택(N). corpus_collection_id 소유 테넌트(서버 도출, 보안 삼중항 1). 바이블 §5.6 미등재(미해결 이슈 1)",
    )
    name: str = Field(
        ...,
        description="kebab 이름. 유일성 키는 (tenant_id, name, content_hash)이며 같은 name 의 개정판이 공존한다. Profile eval.datasets[]·gate.dataset 의 name 참조는 최신 행(created_at 최대)으로 해소한다(이 문서 §2.3, EF-1; 바이블 §7.3, 미해결 이슈 17)",
        max_length=64,
        min_length=1,
        pattern="^[a-z0-9][a-z0-9-]*$",
    )
    content_hash: common_types.Hex64 = Field(
        ...,
        description='H("evalset", qrels_ref.blake3, answer_spans_ref.blake3, topics_ref.blake3 or "")(이 문서 §2.3; 바이블 §6.2 반영 제안, 미해결 이슈 3)',
    )
    qrels_ref: QrelsRef = Field(
        ...,
        description="eval/datasets/{dataset_id}/qrels.jsonl(바이블 §13.3). 행 = $defs/QrelsRecord. 계약 산출물이 아니므로 schema_type 없음",
    )
    answer_spans_ref: AnswerSpansRef = Field(
        ...,
        description="eval/datasets/{dataset_id}/answer_spans.jsonl(바이블 §13.3). 행 = $defs/AnswerSpanRecord",
    )
    topics_ref: TopicsRef | None = Field(
        None,
        description="선택(N). eval/datasets/{dataset_id}/topics.jsonl. 행 = $defs/TopicRecord(질의 본문). 바이블 §5.6·§13.3 미등재(미해결 이슈 2)",
    )
    corpus_collection_id: common_types.Ulid = Field(
        ...,
        description="qrels.doc_id 가 속한 컬렉션(보안 삼중항 2). 하네스는 이 컬렉션의 현재 세대에 대해 질의한다",
    )
    judgment_level: common_types.JudgmentLevel = Field(
        ..., description="binary(rel ∈ {0, 1}) / graded(0..relevance_max)"
    )
    relevance_max: int | None = Field(
        None,
        description="선택(N). graded 등급 상한(기본 3, TREC RAG 2024). binary 는 1 로 고정(allOf). 바이블 §5.6 미등재(미해결 이슈 1)",
        ge=1,
        le=10,
    )
    label_provenance: common_types.LabelProvenance = Field(
        ...,
        description="human / umbrela / synthetic. 프로파일 게이트 데이터셋은 human 만(ADR-0023 준수 10)",
    )
    license: str = Field(
        ...,
        description="SPDX 라이선스 표현식(LicenseRef-* 허용, 예 LicenseRef-KOGL-1). NC·ND 셋은 배포물 미포함(ADR-0023 준수 11)",
        max_length=128,
        min_length=1,
        pattern="^[A-Za-z0-9.+-]+( (AND|OR|WITH) [A-Za-z0-9.+-]+)*$",
    )
    language: common_types.Bcp47 | None = Field(
        None,
        description="선택(N). 골든셋 주 언어(바이블 §6.3). 바이블 §5.6 미등재(미해결 이슈 1)",
    )
    created_at: common_types.DateTime = Field(..., description="원장 행 생성 시각(RFC 3339 UTC)")


class QueryId(RootModel[str]):
    root: str = Field(
        ...,
        description="골든셋 내 질의 ID(TREC query_id). 플랫폼 query_id(ULID)와 다른 네임스페이스",
        pattern="^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
    )


class Iteration(StrEnum):
    """
    TREC 관례 열(정보 없음)
    """

    field_0 = "0"
    Q0 = "Q0"


class QrelsRecord(BaseModel):
    """
    qrels.jsonl 한 행. TREC qrels 텍스트 한 줄 `query_id iteration doc_id relevance` 와 1:1(무손실 변환, rag eval export --format trec)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    query_id: QueryId
    iteration: Iteration = Field(..., description="TREC 관례 열(정보 없음)")
    doc_id: common_types.Ulid = Field(..., description="= document_id(D-06). corpus_collection_id 에 존재해야 한다")
    relevance: int = Field(
        ...,
        description="binary 는 0|1, graded 는 0..relevance_max(nDCG 선형 이득 rel)",
        ge=0,
        le=10,
    )


class AnswerSpanRecord(BaseModel):
    """
    answer_spans.jsonl 한 행. K1 좌표(바이블 §2.1·§6.3): element_path + 원문 Block.text 기준 0-based 유니코드 코드포인트, 끝 미포함. doc_version 으로 콘텐츠 버전에 고정되어 재청킹·재임베딩·프로파일 변경에 불변
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    query_id: QueryId
    doc_id: common_types.Ulid = Field(
        ...,
        description="= document_id. 같은 (query_id, doc_id) 가 qrels 에 relevance ≥ 1 로 존재해야 한다",
    )
    doc_version: common_types.Hex64 = Field(
        ...,
        description="= SourceDocument.content_hash. 현재 세대 doc_version 과 다르면 하네스가 해당 구간을 stale 로 표시한다",
    )
    element_path: str = Field(
        ...,
        description="Block.provenance.element_path(문서 내 유일)",
        max_length=1024,
        min_length=1,
    )
    char_start: int = Field(..., description="원문 Block.text 기준 코드포인트 오프셋", ge=0)
    char_end: int = Field(..., description="끝 미포함; char_start 이상", ge=0)


class TopicRecord(BaseModel):
    """
    topics.jsonl 한 행(질의 본문). TREC topic XML 대체(07-tech-landscape/09). 질의는 콘텐츠이므로 이벤트·로그·오류에 싣지 않는다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    query_id: QueryId
    query: str = Field(
        ...,
        description="QueryRequest.query 한계(바이블 §5.1)와 동일",
        max_length=4000,
        min_length=1,
    )
    language: common_types.Bcp47 | None = None
    metadata: dict[str, str | float | bool] | None = Field(
        None,
        description="질의 메타(도메인·난이도·다중 홉 여부 등). 값은 스칼라만(열린 객체, 미해결 이슈 8)",
    )
