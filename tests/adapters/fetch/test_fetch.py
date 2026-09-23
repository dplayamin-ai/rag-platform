"""`fetcher.fsspec_httpx`(`file://`·`http(s)://`) 컴포넌트 테스트 — 성공·오류 분류·조건부 GET·리다이렉트.

설계 근거: 무엇을 검증하는지는 04-pipelines/02 §2(플러그인 5멤버)·§3.4(`file://` 허용 루트)·
§3.3(HTTP(S) 세부)·§5(스트리밍·BLAKE3·크기 상한)·§6(포맷 판별 1차)·§7.2(조건부 재수집)·
§9.1(오류 매핑) 그대로. HTTP는 `respx`로 모의하고(실 네트워크 없음), `file://`는 `tmp_path`로
임시 파일을 만든다.
구성: 픽스처는 고정 파일 불필요 — `tmp_path`(file)·respx 라우트(http(s))로 그때그때 구성한다.
불변식·주의: 실 네트워크 호출 금지(respx 미스는 즉시 실패), file:// 허용 루트 밖 접근은 예외로만 검증.
검증 계층: 1층(여기서 검증). `needs_network`/`needs_docker`/`needs_model`/`needs_gpu` 대상 테스트 없음
(WP-101: s3/gs/az/smb·EgressGuard CIDR/DNS pinning·KeyProvider·악성 스캔은 이 WP 밖, DEFERRED).
"""

from __future__ import annotations

import types
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import respx

from rag_platform.adapters.fetch.fsspec_httpx import FetchConfig, FsspecHttpxFetcher
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.ingest_request import IngestRequest
from rag_platform.sdk.hashing import blake3_hex
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from pathlib import Path

_TENANT_ID = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"
_DOCUMENT_ID = "01J9ZQ7D3E4F5G6H7J8K9M0N1P"


class _MemoryArtifacts:
    """`ctx.artifacts`(`DerivedArtifacts`)의 인메모리 가짜 — 콘텐츠 주소화만 흉내."""

    def __init__(self) -> None:
        self.calls: list[tuple[bytes, str]] = []

    async def put_source(self, data: bytes, *, media_type: str) -> ct.ArtifactRef:
        self.calls.append((data, media_type))
        digest = blake3_hex(data)
        return ct.ArtifactRef(
            uri=f"file:///tenants/t/sources/{digest[:2]}/{digest}",
            blake3=digest,
            media_type=media_type,
            size_bytes=len(data),
        )


class _Ctx:
    """`StageContext`의 최소 구조적 가짜(테넌트·문서 스코프·시계·아티팩트 포트·계보)."""

    def __init__(self, *, lineage: dict[str, Any] | None = None) -> None:
        self.tenant_id = _TENANT_ID
        self.document_id = _DOCUMENT_ID
        self.artifacts = _MemoryArtifacts()
        self.lineage = lineage or {}

    def now(self) -> datetime:
        return datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


def _ingest_request(source_uri: str, **overrides: Any) -> IngestRequest:
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "request_id": "01J9ZQ7B8C9D0E1F2G3H4J5K6M",
        "collection_id": "01J9ZQ5A1B2C3D4E5F6G7H8J9K",
        "source_uri": source_uri,
        "acl": {"allow_principals": ["tenant:*"], "visibility": "tenant"},
        "requested_at": "2026-09-22T09:00:00.000Z",
    }
    payload.update(overrides)
    return IngestRequest.model_validate(payload)


def _fake_previous(
    *, doc_version: str, size_bytes: int, media_type: str, etag: str | None = None, last_modified: str | None = None
) -> Any:
    """조건부 GET·dedup 입력용 이전 `SourceDocument`의 최소 구조적 가짜(속성 접근만 필요)."""
    return types.SimpleNamespace(
        doc_version=doc_version,
        size_bytes=size_bytes,
        media_type=media_type,
        format=ct.SourceFormat.txt,
        http_metadata=types.SimpleNamespace(etag=etag, last_modified=last_modified),
        artifact=ct.ArtifactRef(
            uri=f"file:///tenants/t/sources/{doc_version[:2]}/{doc_version}",
            blake3=doc_version,
            media_type=media_type,
            size_bytes=size_bytes,
        ),
    )


def _response_without_content_length(status: int, content: bytes, headers: dict[str, str]) -> httpx.Response:
    response = httpx.Response(status, content=content, headers=headers)
    if "content-length" in response.headers:
        del response.headers["content-length"]
    return response


# ---------------------------------------------------------------------------------------------
# file://
# ---------------------------------------------------------------------------------------------


async def test_file_fetch_success(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    data = "안녕하세요, RAG platform".encode()
    target.write_bytes(data)
    fetcher = FsspecHttpxFetcher(FetchConfig(file_allowed_roots=(str(tmp_path),)))
    ctx = _Ctx()
    inp = _ingest_request(target.as_uri())

    doc = await fetcher.run(inp, ctx)

    assert doc.schema_type == "SourceDocument"
    assert doc.content_hash.root == blake3_hex(data)
    assert doc.doc_version.root == doc.content_hash.root
    assert doc.size_bytes == len(data)
    # file:// 에는 Content-Type이 없고 힌트도 없다 — §6 표는 media_type을 (1) Content-Type →
    # (2) media_type_hint → (3) octet-stream 순으로만 정하므로 확장자는 여기 쓰이지 않는다.
    # format은 확장자로 잠정 판별된다(§6 "format" 행 세 번째 신호).
    assert doc.media_type.root == "application/octet-stream"
    assert doc.format == ct.SourceFormat.txt
    assert doc.format_confidence == 0.0
    assert doc.container_flags.encrypted is False
    assert str(doc.resolved_uri) == target.resolve().as_uri()
    assert doc.fetch_report.http_status is None
    assert doc.dedup_report.source_bytes_reused is False
    assert ctx.artifacts.calls == [(data, "application/octet-stream")]


async def test_file_outside_allowed_root_denied(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside" / "doc.txt"
    outside.parent.mkdir()
    outside.write_bytes(b"x")
    fetcher = FsspecHttpxFetcher(FetchConfig(file_allowed_roots=(str(allowed),)))
    inp = _ingest_request(outside.as_uri())

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.access_denied"


async def test_file_prefix_lookalike_root_denied(tmp_path: Path) -> None:
    """`/data/allowed`가 `/data/allowed-evil`를 통과시키면 안 된다(04-pipelines/02 §3.4 문자열 접두 금지)."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    lookalike = tmp_path / "allowed-evil"
    lookalike.mkdir()
    target = lookalike / "doc.txt"
    target.write_bytes(b"x")
    fetcher = FsspecHttpxFetcher(FetchConfig(file_allowed_roots=(str(allowed),)))
    inp = _ingest_request(target.as_uri())

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.access_denied"


async def test_file_empty_allowed_roots_denied(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    target.write_bytes(b"x")
    fetcher = FsspecHttpxFetcher(FetchConfig())  # file_allowed_roots=() 기본값
    inp = _ingest_request(target.as_uri())

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.access_denied"


async def test_file_directory_not_found(tmp_path: Path) -> None:
    fetcher = FsspecHttpxFetcher(FetchConfig(file_allowed_roots=(str(tmp_path),)))
    inp = _ingest_request(tmp_path.as_uri())

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.not_found"


async def test_file_missing_not_found(tmp_path: Path) -> None:
    fetcher = FsspecHttpxFetcher(FetchConfig(file_allowed_roots=(str(tmp_path),)))
    inp = _ingest_request((tmp_path / "missing.txt").as_uri())

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.not_found"


async def test_file_unc_authority_denied(tmp_path: Path) -> None:
    fetcher = FsspecHttpxFetcher(FetchConfig(file_allowed_roots=(str(tmp_path),)))
    inp = _ingest_request("file://some-host/share/doc.txt")

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.egress_denied"


async def test_file_scheme_denied_when_not_in_allowed_schemes(tmp_path: Path) -> None:
    target = tmp_path / "doc.txt"
    target.write_bytes(b"x")
    fetcher = FsspecHttpxFetcher(FetchConfig(allowed_schemes=frozenset({"https"}), file_allowed_roots=(str(tmp_path),)))
    inp = _ingest_request(target.as_uri())

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.egress_denied"


# ---------------------------------------------------------------------------------------------
# http(s):// — respx 모의(실 네트워크 없음)
# ---------------------------------------------------------------------------------------------

_URL = "https://example.test/doc.pdf"


@respx.mock
async def test_http_fetch_success() -> None:
    body = b"%PDF-1.4 fake body"
    respx.get(_URL).mock(
        return_value=httpx.Response(
            200,
            content=body,
            headers={
                "content-type": "application/pdf",
                "etag": '"abc123"',
                "last-modified": "Mon, 15 Sep 2026 00:12:41 GMT",
            },
        )
    )
    fetcher = FsspecHttpxFetcher()
    inp = _ingest_request(_URL)

    doc = await fetcher.run(inp, _Ctx())

    assert doc.media_type.root == "application/pdf"
    assert doc.format == ct.SourceFormat.pdf
    assert doc.content_hash.root == blake3_hex(body)
    assert doc.http_metadata is not None
    assert doc.http_metadata.etag == '"abc123"'
    assert doc.fetch_report.http_status == 200
    assert doc.fetch_report.not_modified is False
    assert doc.fetch_report.redirects == 0


@respx.mock
async def test_http_media_type_hint_normalized_and_wins_format() -> None:
    body = b"hwpx-bytes"
    respx.get(_URL).mock(
        return_value=httpx.Response(200, content=body, headers={"content-type": "application/octet-stream"})
    )
    fetcher = FsspecHttpxFetcher()
    inp = _ingest_request(_URL, media_type_hint="application/vnd.hancom.hwpx")

    doc = await fetcher.run(inp, _Ctx())

    assert doc.format == ct.SourceFormat.hwpx
    # media_type 열은 Content-Type 우선이나 octet-stream은 무시되므로 힌트로 보완된다.
    assert doc.media_type.root == "application/hwp+zip"


@respx.mock
async def test_http_content_length_precheck_too_large() -> None:
    respx.get(_URL).mock(
        return_value=httpx.Response(
            200, content=b"short", headers={"content-length": "100000000", "content-type": "text/plain"}
        )
    )
    fetcher = FsspecHttpxFetcher(FetchConfig(max_bytes=1_000))
    inp = _ingest_request(_URL)

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.too_large"


@respx.mock
async def test_http_streaming_abort_too_large_without_content_length() -> None:
    respx.get(_URL).mock(
        return_value=_response_without_content_length(200, b"x" * 5_000, {"content-type": "text/plain"})
    )
    fetcher = FsspecHttpxFetcher(FetchConfig(max_bytes=1_000))
    inp = _ingest_request(_URL)

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.too_large"


@respx.mock
async def test_http_redirect_followed() -> None:
    next_url = "https://example.test/redirected.pdf"
    respx.get(_URL).mock(return_value=httpx.Response(302, headers={"location": next_url}))
    respx.get(next_url).mock(
        return_value=httpx.Response(200, content=b"final", headers={"content-type": "application/pdf"})
    )
    fetcher = FsspecHttpxFetcher()
    inp = _ingest_request(_URL)

    doc = await fetcher.run(inp, _Ctx())

    assert doc.fetch_report.redirects == 1
    assert doc.content_hash.root == blake3_hex(b"final")


@respx.mock
async def test_http_redirect_downgrade_denied() -> None:
    respx.get(_URL).mock(return_value=httpx.Response(302, headers={"location": "http://example.test/insecure.pdf"}))
    fetcher = FsspecHttpxFetcher()
    inp = _ingest_request(_URL)

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.egress_denied"


@respx.mock
async def test_http_redirect_loop_exceeds_max_redirects() -> None:
    respx.get(_URL).mock(return_value=httpx.Response(302, headers={"location": _URL}))
    fetcher = FsspecHttpxFetcher(FetchConfig(max_redirects=1))
    inp = _ingest_request(_URL)

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.egress_denied"


@respx.mock
async def test_http_conditional_get_not_modified_reuses_bytes() -> None:
    respx.get(_URL).mock(return_value=httpx.Response(304, headers={"etag": '"same"'}))
    previous = _fake_previous(doc_version=blake3_hex(b"cached"), size_bytes=6, media_type="text/plain", etag='"same"')
    fetcher = FsspecHttpxFetcher()
    inp = _ingest_request(_URL)
    ctx = _Ctx(lineage={"SourceDocument": previous})

    doc = await fetcher.run(inp, ctx)

    assert doc.fetch_report.not_modified is True
    assert doc.fetch_report.bytes_per_sec == 0.0
    assert doc.content_hash.root == previous.doc_version
    assert doc.dedup_report.content_unchanged is True
    assert doc.dedup_report.source_bytes_reused is True
    assert ctx.artifacts.calls == []  # 304면 put_source를 다시 부르지 않는다


@respx.mock
async def test_http_conditional_headers_sent_only_with_previous() -> None:
    route = respx.get(_URL).mock(
        return_value=httpx.Response(200, content=b"data", headers={"content-type": "text/plain"})
    )
    fetcher = FsspecHttpxFetcher()
    inp = _ingest_request(_URL)

    await fetcher.run(inp, _Ctx())  # previous 없음 → 조건부 헤더 없음

    assert "if-none-match" not in route.calls.last.request.headers
    assert "if-modified-since" not in route.calls.last.request.headers


@respx.mock
@pytest.mark.parametrize(
    ("status", "expected_code"),
    [
        (401, "fetch.access_denied"),
        (404, "fetch.not_found"),
        (429, "fetch.upstream_error"),
        (500, "fetch.upstream_error"),
    ],
)
async def test_http_status_error_mapping(status: int, expected_code: str) -> None:
    respx.get(_URL).mock(return_value=httpx.Response(status))
    fetcher = FsspecHttpxFetcher()
    inp = _ingest_request(_URL)

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == expected_code


@respx.mock
async def test_http_connect_timeout_maps_to_fetch_timeout() -> None:
    respx.get(_URL).mock(side_effect=httpx.ConnectTimeout("boom"))
    fetcher = FsspecHttpxFetcher()
    inp = _ingest_request(_URL)

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.timeout"


@respx.mock
async def test_http_transport_error_maps_to_upstream_error() -> None:
    respx.get(_URL).mock(side_effect=httpx.ConnectError("reset"))
    fetcher = FsspecHttpxFetcher()
    inp = _ingest_request(_URL)

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.upstream_error"


async def test_http_scheme_disallowed_by_policy() -> None:
    fetcher = FsspecHttpxFetcher(FetchConfig(allowed_schemes=frozenset({"https", "file"})))
    inp = _ingest_request("http://example.test/doc.txt")

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.egress_denied"


async def test_scheme_unsupported_when_policy_allows_but_plugin_cannot() -> None:
    fetcher = FsspecHttpxFetcher(FetchConfig(allowed_schemes=frozenset({"https", "http", "file", "s3"})))
    inp = _ingest_request("s3://bucket/key.pdf")

    with pytest.raises(StageError) as excinfo:
        await fetcher.run(inp, _Ctx())
    assert excinfo.value.code == "fetch.scheme_unsupported"


# ---------------------------------------------------------------------------------------------
# 무결성·스모크
# ---------------------------------------------------------------------------------------------


@respx.mock
async def test_same_bytes_yield_same_content_hash_regardless_of_encoding_header() -> None:
    body = b"identical document bytes"
    respx.get(_URL).mock(return_value=httpx.Response(200, content=body, headers={"content-type": "text/plain"}))
    fetcher = FsspecHttpxFetcher()
    doc_a = await fetcher.run(_ingest_request(_URL), _Ctx())

    other_url = "https://example.test/other.txt"
    respx.get(other_url).mock(
        return_value=httpx.Response(
            200, content=body, headers={"content-type": "text/plain", "content-encoding": "identity"}
        )
    )
    doc_b = await fetcher.run(_ingest_request(other_url), _Ctx())

    assert doc_a.content_hash.root == doc_b.content_hash.root == blake3_hex(body)


def test_capabilities_fingerprint_config_hash_are_deterministic() -> None:
    fetcher = FsspecHttpxFetcher()
    other = FsspecHttpxFetcher()

    assert fetcher.config_hash() == other.config_hash()
    assert fetcher.fingerprint() == other.fingerprint()
    caps = fetcher.capabilities()
    assert caps.isolation_modes == [ct.IsolationMode.in_process]
    assert caps.extra["max_bytes"] == FetchConfig().max_bytes
    assert set(caps.input_formats or []) == {"file", "http", "https"}
