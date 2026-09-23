"""`tests/api/test_api.py` — F5-01 API 표면(`ingest`/`jobs`/`query`/`render`) 계약·오류 테스트.

역할(무엇을 검증하는가): `POST /v1/ingest`의 202 접수·`Idempotency-Key` 필수·재전송(200)·지문
불일치(422)·서버 발급 필드 거부(400/422)·`LocalRunner` 백그라운드 실행(성공/실패 두 경로 모두
`GET /v1/jobs/{job_id}`로 관찰 가능)을 확인한다. `GET /v1/jobs/{job_id}`의 인증 실패(401)·존재하지
않는 잡(404)·테넌트 격리(404)를 확인한다. `POST /v1/query`의 `QueryRequest` 계약 검증(400)·서버
주입 필드 거부(400)·컬렉션 인가(403 `plan.collection_forbidden`)·`response_format=pack_only`·성공
응답의 `context_pack`/`rendered` 모양을 확인한다. `POST /v1/render`의 `pack_id`/`context_pack`
상호배타 검증·알 수 없는 `pack_id`(404)·인라인 팩 렌더를 확인한다. 모든 오류 응답이
`application/problem+json` + `ProblemDetails` 필수 필드(`type`/`title`/`status`/`code`/
`retryable`/`trace_id`)를 갖추는지도 함께 확인한다.
설계 근거·구성(픽스처 출처): `05-api/02-ingestion-api.md` §4(요청·응답 예시)·§4.4(멱등성 표)·
§6.2(`JobStatus` 예시), `05-api/03-retrieval-api.md` §3.1(요청 규칙)·§3.6(한국어 질의 예시 1의
필드 부분집합)을 골자로 한
축소 픽스처(전체 `IngestRequest`/RBAC/레이트리밋은 이 WP 범위 밖).
불변식·주의: 인메모리 대역(`IdempotencyStore`/`JobStore`)만 쓴다 — 외부 자원·모델 다운로드 없음.
검증 계층: 1층(여기서 검증) — 테스트 실행 자체가 검증. `# DEFERRED: 실 Postgres 원장·Cedar 인가·
레이트리밋은 open_issues`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from rag_platform.api.app import create_app

if TYPE_CHECKING:
    from fastapi import FastAPI

_TENANT_A = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"
_TENANT_B = "01J9ZQ4K7X2M8N3P5R6S7T8V9X"
_COLLECTION_A = "01J9ZQ5A1B2C3D4E5F6G7H8J9K"
_COLLECTION_B = "01J9ZQ5A1B2C3D4E5F6G7H8J9M"
_API_KEY_A = "rag_ak_test_tenant_a"
_API_KEY_B = "rag_ak_test_tenant_b"

_HEADERS_A = {"Authorization": f"Bearer {_API_KEY_A}"}
_HEADERS_B = {"Authorization": f"Bearer {_API_KEY_B}"}


@pytest.fixture
def app() -> FastAPI:
    """A fresh app per test: tenant A allows only `_COLLECTION_A`, tenant B has no allowed set."""
    application = create_app()
    application.state.api_keys.register(
        _API_KEY_A, tenant_id=_TENANT_A, subject="alice", allowed_collection_ids=[_COLLECTION_A]
    )
    application.state.api_keys.register(_API_KEY_B, tenant_id=_TENANT_B, subject="bob", allowed_collection_ids=None)
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """A `TestClient` bound to the per-test `app` fixture."""
    return TestClient(app)


def _ingest_body(*, source_uri: str = "s3://bucket/doc.hwpx", collection_id: str = _COLLECTION_A) -> dict[str, Any]:
    return {"collection_id": collection_id, "source_uri": source_uri}


def _query_body(**overrides: Any) -> dict[str, Any]:
    body = {
        "schema_version": "1.0.0",
        "query": "정보공개 청구를 받은 공공기관은 며칠 이내에 공개 여부를 결정해야 하나요?",
        "collection_ids": [_COLLECTION_A],
        "target_model": {"provider": "anthropic", "model": "claude-opus-5"},
        "requested_at": "2026-09-22T09:00:00.000Z",
    }
    body.update(overrides)
    return body


def _assert_problem_details(body: dict[str, Any], *, status: int, code: str) -> None:
    assert body["status"] == status
    assert body["code"] == code
    assert body["type"] == f"urn:rag:error:{code}"
    assert body["title"]
    assert isinstance(body["retryable"], bool)
    assert len(body["trace_id"]) == 32


class TestIngestAccepted:
    """`POST /v1/ingest` 202 접수 + `LocalRunner` 백그라운드 실행(성공 경로)."""

    def test_accepts_and_runs_to_succeeded(self, client: TestClient) -> None:
        response = client.post(
            "/v1/ingest", headers={**_HEADERS_A, "Idempotency-Key": "idem-ok-1"}, json=_ingest_body()
        )
        assert response.status_code == 202
        assert "Location" in response.headers
        body = response.json()
        assert set(body) == {"job_id", "request_id", "document_id", "status_url", "events_url"}

        job_response = client.get(f"/v1/jobs/{body['job_id']}", headers=_HEADERS_A)
        assert job_response.status_code == 200
        job = job_response.json()
        assert job["state"] == "succeeded"
        assert job["stage"] == "index"
        assert job["progress"] == {"done": 1, "total": 1, "unit": "stage"}
        assert job["index_commit_id"]
        assert job["idempotency_key"] == "idem-ok-1"
        assert job["status_url"] == body["status_url"]

    def test_failure_path_records_last_error(self, client: TestClient) -> None:
        response = client.post(
            "/v1/ingest",
            headers={**_HEADERS_A, "Idempotency-Key": "idem-fail-1"},
            json=_ingest_body(source_uri="stub-fail://sentinel"),
        )
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        job = client.get(f"/v1/jobs/{job_id}", headers=_HEADERS_A).json()
        assert job["state"] == "failed"
        assert job["last_error"]["code"] == "index.security_fields_missing"
        assert job["last_error"]["retryable"] is False


class TestIngestIdempotency:
    """05-api/02 §4.4 멱등성 표: 재전송(200)·지문 불일치(422)·헤더 부재(400)."""

    def test_missing_idempotency_key_is_rejected(self, client: TestClient) -> None:
        response = client.post("/v1/ingest", headers=_HEADERS_A, json=_ingest_body())
        assert response.status_code == 400
        _assert_problem_details(response.json(), status=400, code="contract.violation")

    def test_replay_same_key_same_body_returns_200_with_same_job(self, client: TestClient) -> None:
        headers = {**_HEADERS_A, "Idempotency-Key": "idem-replay-1"}
        first = client.post("/v1/ingest", headers=headers, json=_ingest_body())
        second = client.post("/v1/ingest", headers=headers, json=_ingest_body())
        assert first.status_code == 202
        assert second.status_code == 200
        assert second.json() == first.json()

    def test_same_key_different_body_is_422(self, client: TestClient) -> None:
        headers = {**_HEADERS_A, "Idempotency-Key": "idem-conflict-1"}
        first = client.post("/v1/ingest", headers=headers, json=_ingest_body(source_uri="s3://bucket/a.hwpx"))
        second = client.post("/v1/ingest", headers=headers, json=_ingest_body(source_uri="s3://bucket/b.hwpx"))
        assert first.status_code == 202
        assert second.status_code == 422
        _assert_problem_details(second.json(), status=422, code="api.idempotency_payload_mismatch")


class TestIngestValidation:
    """05-api/02 §4.1/§4.3: 서버 발급 필드 거부, 필수 필드, `priority` 범위."""

    def test_rejects_client_supplied_tenant_id(self, client: TestClient) -> None:
        body = {**_ingest_body(), "tenant_id": _TENANT_A}
        response = client.post("/v1/ingest", headers={**_HEADERS_A, "Idempotency-Key": "k1"}, json=body)
        assert response.status_code == 422
        _assert_problem_details(response.json(), status=422, code="contract.violation")

    def test_rejects_client_supplied_request_id(self, client: TestClient) -> None:
        body = {**_ingest_body(), "request_id": "01J9ZQ4K7X2M8N3P5R6S7T8V9Z"}
        response = client.post("/v1/ingest", headers={**_HEADERS_A, "Idempotency-Key": "k2"}, json=body)
        assert response.status_code == 400
        _assert_problem_details(response.json(), status=400, code="contract.violation")

    def test_missing_collection_id_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/v1/ingest",
            headers={**_HEADERS_A, "Idempotency-Key": "k3"},
            json={"source_uri": "s3://bucket/doc.hwpx"},
        )
        assert response.status_code == 400
        _assert_problem_details(response.json(), status=400, code="contract.violation")

    def test_priority_out_of_range_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/v1/ingest", headers={**_HEADERS_A, "Idempotency-Key": "k4"}, json={**_ingest_body(), "priority": 42}
        )
        assert response.status_code == 400
        _assert_problem_details(response.json(), status=400, code="contract.violation")


class TestIngestAuthAndTenancy:
    """바이블 §10.3 E1/E2: 인증 실패, 인가된 컬렉션 밖 접근."""

    def test_missing_authorization_is_401(self, client: TestClient) -> None:
        response = client.post("/v1/ingest", headers={"Idempotency-Key": "k5"}, json=_ingest_body())
        assert response.status_code == 401
        _assert_problem_details(response.json(), status=401, code="auth.unauthenticated")

    def test_unknown_api_key_is_401(self, client: TestClient) -> None:
        response = client.post(
            "/v1/ingest",
            headers={"Authorization": "Bearer not-a-real-key", "Idempotency-Key": "k6"},
            json=_ingest_body(),
        )
        assert response.status_code == 401

    def test_collection_outside_allowed_set_is_403(self, client: TestClient) -> None:
        response = client.post(
            "/v1/ingest",
            headers={**_HEADERS_A, "Idempotency-Key": "k7"},
            json=_ingest_body(collection_id=_COLLECTION_B),
        )
        assert response.status_code == 403
        _assert_problem_details(response.json(), status=403, code="auth.forbidden")


class TestJobsLookup:
    """`GET /v1/jobs/{job_id}` — 존재하지 않는 잡, 테넌트 격리."""

    def test_unknown_job_is_404(self, client: TestClient) -> None:
        response = client.get("/v1/jobs/01JUNKNOWNJOB000000000000", headers=_HEADERS_A)
        assert response.status_code == 404
        _assert_problem_details(response.json(), status=404, code="api.not_found")

    def test_other_tenant_cannot_see_job(self, client: TestClient) -> None:
        accepted = client.post(
            "/v1/ingest", headers={**_HEADERS_A, "Idempotency-Key": "k8"}, json=_ingest_body()
        ).json()
        response = client.get(f"/v1/jobs/{accepted['job_id']}", headers=_HEADERS_B)
        assert response.status_code == 404


class TestQuery:
    """`POST /v1/query` — 계약 검증, 서버 주입, 인가, 응답 모양."""

    def test_happy_path_returns_context_pack_and_rendered(self, client: TestClient) -> None:
        response = client.post("/v1/query", headers=_HEADERS_A, json=_query_body())
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        body = response.json()
        pack = body["context_pack"]
        assert pack["items"] == []
        assert pack["sufficiency"]["status"] == "not_needed"
        assert pack["collection_ids"] == [_COLLECTION_A]
        assert pack["tenant_id"] == _TENANT_A
        assert "rendered" in body
        assert body["rendered"]["renderer"] == "anthropic_search_result"

    def test_pack_only_omits_rendered(self, client: TestClient) -> None:
        response = client.post("/v1/query", headers=_HEADERS_A, json=_query_body(response_format="pack_only"))
        assert response.status_code == 200
        assert "rendered" not in response.json()

    def test_rejects_client_supplied_query_id(self, client: TestClient) -> None:
        response = client.post("/v1/query", headers=_HEADERS_A, json=_query_body(query_id="01J9ZQ4K7X2M8N3P5R6S7T8V9Z"))
        assert response.status_code == 400
        _assert_problem_details(response.json(), status=400, code="contract.violation")

    def test_missing_required_field_is_400(self, client: TestClient) -> None:
        body = _query_body()
        del body["query"]
        response = client.post("/v1/query", headers=_HEADERS_A, json=body)
        assert response.status_code == 400
        _assert_problem_details(response.json(), status=400, code="contract.violation")

    def test_collection_forbidden_is_403(self, client: TestClient) -> None:
        response = client.post("/v1/query", headers=_HEADERS_A, json=_query_body(collection_ids=[_COLLECTION_B]))
        assert response.status_code == 403
        _assert_problem_details(response.json(), status=403, code="plan.collection_forbidden")

    def test_missing_authorization_is_401(self, client: TestClient) -> None:
        response = client.post("/v1/query", json=_query_body())
        assert response.status_code == 401


class TestRender:
    """`POST /v1/render` — `pack_id`/`context_pack` 상호배타, 알 수 없는 `pack_id`, 인라인 렌더."""

    def test_render_by_pack_id(self, client: TestClient) -> None:
        query_response = client.post(
            "/v1/query", headers=_HEADERS_A, json=_query_body(response_format="pack_only")
        ).json()
        pack_id = query_response["context_pack"]["pack_id"]

        response = client.post("/v1/render", headers=_HEADERS_A, json={"pack_id": pack_id, "renderer": "markdown"})
        assert response.status_code == 200
        rendered = response.json()
        assert rendered["pack_id"] == pack_id
        assert rendered["renderer"] == "markdown"

    def test_render_inline_context_pack(self, client: TestClient) -> None:
        query_response = client.post(
            "/v1/query", headers=_HEADERS_A, json=_query_body(response_format="pack_only")
        ).json()
        context_pack = query_response["context_pack"]

        response = client.post(
            "/v1/render", headers=_HEADERS_A, json={"context_pack": context_pack, "renderer": "xml_documents"}
        )
        assert response.status_code == 200
        assert response.json()["renderer"] == "xml_documents"

    def test_unknown_pack_id_is_404(self, client: TestClient) -> None:
        response = client.post(
            "/v1/render", headers=_HEADERS_A, json={"pack_id": "01JUNKNOWNPACK00000000000", "renderer": "markdown"}
        )
        assert response.status_code == 404
        _assert_problem_details(response.json(), status=404, code="api.not_found")

    def test_both_pack_id_and_context_pack_is_400(self, client: TestClient) -> None:
        query_response = client.post(
            "/v1/query", headers=_HEADERS_A, json=_query_body(response_format="pack_only")
        ).json()
        response = client.post(
            "/v1/render",
            headers=_HEADERS_A,
            json={
                "pack_id": query_response["context_pack"]["pack_id"],
                "context_pack": query_response["context_pack"],
                "renderer": "markdown",
            },
        )
        assert response.status_code == 400
        _assert_problem_details(response.json(), status=400, code="contract.violation")

    def test_render_by_pack_id_rejects_other_key_with_narrower_collections(
        self, app: FastAPI, client: TestClient
    ) -> None:
        """05-api/03 §4.4 주체 바인딩 대조: 같은 테넌트라도 허용 컬렉션이 다른 키는 404."""
        wide_key = "rag_ak_test_tenant_a_wide"
        narrow_key = "rag_ak_test_tenant_a_narrow"
        app.state.api_keys.register(
            wide_key, tenant_id=_TENANT_A, subject="wide", allowed_collection_ids=[_COLLECTION_A, _COLLECTION_B]
        )
        app.state.api_keys.register(
            narrow_key, tenant_id=_TENANT_A, subject="narrow", allowed_collection_ids=[_COLLECTION_A]
        )

        query_response = client.post(
            "/v1/query",
            headers={"Authorization": f"Bearer {wide_key}"},
            json=_query_body(collection_ids=[_COLLECTION_A, _COLLECTION_B], response_format="pack_only"),
        ).json()
        pack_id = query_response["context_pack"]["pack_id"]

        response = client.post(
            "/v1/render",
            headers={"Authorization": f"Bearer {narrow_key}"},
            json={"pack_id": pack_id, "renderer": "markdown"},
        )
        assert response.status_code == 404
        _assert_problem_details(response.json(), status=404, code="api.not_found")

    def test_invalid_renderer_is_400(self, client: TestClient) -> None:
        query_response = client.post(
            "/v1/query", headers=_HEADERS_A, json=_query_body(response_format="pack_only")
        ).json()
        response = client.post(
            "/v1/render",
            headers=_HEADERS_A,
            json={"pack_id": query_response["context_pack"]["pack_id"], "renderer": "not-a-renderer"},
        )
        assert response.status_code == 400
        _assert_problem_details(response.json(), status=400, code="contract.violation")
