"""`security.security_context.derive_security_context` 단위 테스트 — API 키는 서비스 주체.

역할(무엇을 검증하는가): API 키 인증 경로가 만드는 `SecurityContext`가 ADR-0027 SecurityContext
불릿·`05-api/03-retrieval-api.md` §2 "주체 문자열" 행이 요구하는 서비스 주체 모양
(`principals == ["service:{subject}"]`, `tenant:*` 부재, `visible_set == ["public"]`)인지 확인하고,
`allowed_collection_ids` 교집합 동작(기존 로직)이 이 수정으로 깨지지 않았는지 회귀 확인한다.
설계 근거·픽스처 출처: `docs/06-adr/0027-security-context-injection-and-acl-enforcement-points.md`
"결정" 절 SecurityContext 불릿, `docs/05-api/03-retrieval-api.md` §2 표("주체 문자열" 행).
구성: `TestApiKeyIsServicePrincipal`(서비스 주체 모양·visible_set), `TestCollectionIntersectionUnaffected`
(`allowed_collection_ids` 교집합 회귀).
불변식·주의: 외부 자원 없음, 순수 함수 호출만.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from datetime import UTC, datetime

from rag_platform.security.security_context import ApiKeyRecord, derive_security_context

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_TENANT = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"
_COLLECTION_A = "01J9ZQ5A1B2C3D4E5F6G7H8J9K"
_COLLECTION_B = "01J9ZQ5A1B2C3D4E5F6G7H8J9M"


class TestApiKeyIsServicePrincipal:
    """ADR-0027 SecurityContext 불릿: API 키 주체는 `service:{client_id}`만, `visible_set=[public]`."""

    def test_no_tenant_wildcard_and_public_only_visible_set(self) -> None:
        record = ApiKeyRecord(tenant_id=_TENANT, subject="svc-client-1", allowed_collection_ids=None)

        security = derive_security_context(record, requested_collection_ids=[_COLLECTION_A], now=_NOW)

        assert [p.root for p in security.principals] == ["service:svc-client-1"]
        assert not any(p.root.startswith(("user:", "group:")) for p in security.principals)
        assert "tenant:*" not in [p.root for p in security.principals]
        assert [v.value for v in security.visible_set] == ["public"]
        assert security.auth_method.value == "api_key"

    def test_different_subjects_get_distinct_service_principals(self) -> None:
        record_a = ApiKeyRecord(tenant_id=_TENANT, subject="alice", allowed_collection_ids=None)
        record_b = ApiKeyRecord(tenant_id=_TENANT, subject="bob", allowed_collection_ids=None)

        security_a = derive_security_context(record_a, requested_collection_ids=[_COLLECTION_A], now=_NOW)
        security_b = derive_security_context(record_b, requested_collection_ids=[_COLLECTION_A], now=_NOW)

        assert [p.root for p in security_a.principals] == ["service:alice"]
        assert [p.root for p in security_b.principals] == ["service:bob"]


class TestCollectionIntersectionUnaffected:
    """기존 동작 회귀: `allowed_collection_ids` 교집합 로직은 주체 모양 수정과 무관하게 그대로다."""

    def test_none_allows_every_requested_collection(self) -> None:
        record = ApiKeyRecord(tenant_id=_TENANT, subject="svc", allowed_collection_ids=None)

        security = derive_security_context(record, requested_collection_ids=[_COLLECTION_A, _COLLECTION_B], now=_NOW)

        assert [c.root for c in security.collection_ids] == [_COLLECTION_A, _COLLECTION_B]

    def test_narrows_to_allowed_set_and_preserves_request_order(self) -> None:
        record = ApiKeyRecord(tenant_id=_TENANT, subject="svc", allowed_collection_ids=[_COLLECTION_A])

        security = derive_security_context(record, requested_collection_ids=[_COLLECTION_B, _COLLECTION_A], now=_NOW)

        assert [c.root for c in security.collection_ids] == [_COLLECTION_A]

    def test_empty_intersection_yields_empty_collection_ids(self) -> None:
        record = ApiKeyRecord(tenant_id=_TENANT, subject="svc", allowed_collection_ids=[_COLLECTION_A])

        security = derive_security_context(record, requested_collection_ids=[_COLLECTION_B], now=_NOW)

        assert security.collection_ids == []
