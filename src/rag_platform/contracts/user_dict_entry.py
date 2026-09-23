"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, RootModel

from rag_platform.contracts.contract_model import ContractModel

from . import common_types


class DictToken(RootModel[str]):
    root: str = Field(
        ...,
        description="공백·탭·개행이 없는 1..64자 문자열(TSV·Nori 공백 구분 규칙 생성 안전). NFC 정규형은 Pydantic 이 검증한다",
        pattern="^\\S{1,64}$",
    )


class UserDictEntry(ContractModel):
    """
    사용자 사전 항목 계약(바이블 §5.6, §14 GET/PUT /v1/collections/{collection_id}/dictionary, ADR-0021). Kiwi·mecab-ko 사용자 사전, OpenSearch Nori user_dictionary_rules, synonym_graph 규칙을 생성하는 단일 소스다. collection_id=null 은 테넌트 전역 항목. 항목 집합의 정규화 행 정렬 해시가 dictionary_hash = H("dict", *sorted(rows))(바이블 §6.2)이며 변경은 CollectionSpec.dictionary_hash → lexical_profile_hash 변경 → 렉시컬 재색인 제안으로 이어진다. 정본은 PostgreSQL user_dictionary_entries 원장 행. 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/16-eval-feedback-and-sidecar-contracts.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver | None = Field(
        None,
        description='선택(N). 계약 버전 "1.0.0". 바이블 §5.6 미등재(미해결 이슈 1)',
    )
    entry_id: common_types.Ulid = Field(
        ...,
        description="서버 발급(바이블 §6.1). 자연 키 (tenant_id, collection_id, surface, pos) 가 같으면 PUT 교체 후에도 유지된다",
    )
    tenant_id: common_types.Ulid = Field(..., description="SecurityContext.tenant_id 에서 도출(보안 삼중항 1)")
    collection_id: common_types.Ulid | None = Field(
        ...,
        description="Y(nullable). 컬렉션 항목 / null = 테넌트 전역 항목(모든 컬렉션 사전에 병합; 같은 (surface, pos) 는 컬렉션 항목이 우선)",
    )
    surface: DictToken = Field(..., description="표층형(NFC). 형태소 분석기 사용자 단어·Nori 규칙의 첫 토큰")
    pos: str = Field(
        ...,
        description="세종 품사 태그(NNG, NNP, NNB, SL, SN 등). 분석기가 사용자 사전으로 받는 태그만 유효(위반은 PUT 시 contract.violation)",
        pattern="^[A-Z]{2,4}$",
    )
    reading: DictToken | None = Field(
        None,
        description="선택(N). 독음(한자·영문 약어 표층형의 한글 읽기; Nori nori_readingform 대체 입력). 없으면 생략 또는 null",
    )
    synonyms: list[DictToken] = Field(
        ...,
        description="동의어·약칭(행안부 ↔ 행정안전부). synonym_graph 규칙과 Kiwi orig_word 생성 입력. surface 자신은 포함하지 않는다. 빈 배열 허용",
        max_length=32,
    )
    decompound: list[DictToken] | None = Field(
        None,
        description="선택(N). 복합명사 분해 구성요소(Nori user_dictionary_rules 한 줄 `surface part1 part2` 형식). 구성요소를 이어 붙이면 surface 와 같아야 한다(불변식 EF-22). 바이블 §5.6 미등재(미해결 이슈 5)",
        max_length=8,
        min_length=2,
    )
    weight: float = Field(
        ...,
        description="가중치. Kiwi add_user_word(score=weight) 입력, Nori 는 무시, 질의 시 BoostKind.user_dictionary 부스트 계수 입력(초안). 기본 0.0",
    )
    source: common_types.DictSource = Field(
        ...,
        description="manual(운영자 입력) / imported(외부 사전 일괄 반입) / mined(Kiwi extract_words 등 자동 추출 후 검수)",
    )
    updated_at: common_types.DateTime = Field(..., description="마지막 변경 시각(서버 기록)")
