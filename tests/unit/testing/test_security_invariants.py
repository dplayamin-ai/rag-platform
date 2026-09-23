"""`rag_platform.testing.security_invariants` 단위 테스트 — `IndexRecord`/`QueryPlan` 실 계약 인스턴스에서
`tenant_id`·ACL 사전 필터 필드가 존재·비어있지 않은지 검사하고, 빈 값·누락 필드를 실제로 검출하는지 검증한다.

설계 근거: ADR-0032 적합성 키트 표(`security_invariants`), 준수 확인 방법 표 #9, 바이블 §10.2 필터 불변식
(a)(사전 필터, 사후 필터 금지).

구성: `tests/contracts/fixtures/index-record/001.json`·`query-plan/001.json`(이미 `tools/extract_examples.py`
가 생성한 계약 골든 예시)을 `rag_platform.contracts`의 실제 생성 모델로 파싱해 통과 경로를 검증하고,
`model_copy(update=...)`로 ACL 사전 필터를 빈 값으로 바꾼 사본과, 두 필드 모두 없는 임의 객체로 실패 경로를
검증한다.

검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import pytest

from rag_platform.contracts.index_record import IndexRecord
from rag_platform.contracts.query_plan import QueryPlan
from rag_platform.testing.security_invariants import (
    assert_acl_prefilter,
    assert_security_prefilters,
    assert_tenant_prefilter,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"


def _load(fixture: str) -> dict:
    return json.loads((FIXTURES_DIR / fixture).read_text(encoding="utf-8"))


def test_index_record_has_tenant_and_acl_prefilters() -> None:
    record = IndexRecord.model_validate(_load("index-record/001.json"))
    result = assert_security_prefilters(record)
    assert result["tenant_id"]
    assert result["acl_field"] == "acl_allow"
    assert result["acl_value"]


def test_query_plan_prefilters_are_nested_under_filters_security() -> None:
    plan = QueryPlan.model_validate(_load("query-plan/001.json"))
    tenant_id = assert_tenant_prefilter(plan)
    acl_field, acl_value = assert_acl_prefilter(plan)
    assert tenant_id == plan.tenant_id.root
    assert acl_field == "principals"
    assert acl_value == plan.filters.security.principals


def test_assert_acl_prefilter_rejects_empty_list() -> None:
    record = IndexRecord.model_validate(_load("index-record/001.json"))
    emptied = record.model_copy(update={"acl_allow": []})
    with pytest.raises(AssertionError, match="acl_allow is empty"):
        assert_acl_prefilter(emptied)


def test_assert_tenant_prefilter_rejects_missing_field() -> None:
    class _NoTenant:
        acl_allow: ClassVar[list[str]] = ["group:x"]

    with pytest.raises(AssertionError, match="no tenant_id pre-filter field"):
        assert_tenant_prefilter(_NoTenant())  # type: ignore[arg-type]


def test_assert_acl_prefilter_rejects_missing_field() -> None:
    class _NoAcl:
        tenant_id = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"

    with pytest.raises(AssertionError, match="no ACL pre-filter field"):
        assert_acl_prefilter(_NoAcl())  # type: ignore[arg-type]
