"""`fetcher.fsspec_httpx` 페처 스테이지 — `IngestRequest.source_uri` 하나를 받아 `SourceDocument`를 만든다.

역할: 수집 파이프라인 첫 스테이지 `fetch`(확장 지점 `fetcher`)의 코어 플러그인. `file://`(허용 루트
제한)와 `http(s)://`(httpx 스트리밍·크기 상한·조건부 GET·리다이렉트 정책)만 이 WP 범위다(`s3`/`gs`/
`az`/`smb`·`EgressGuard`·`KeyProvider`·악성 스캔·zip 컨테이너는 밖, WP-101 참조).
설계 근거: 바이블 §4.1(5멤버 스테이지)·§4.2 `fetch` 행·§5.4 `SourceDocument`·§5.7 `fetch.*` 오류
카탈로그, 04-pipelines/02 §2·§5·§6·§7.2·§9.
구성: `FetchConfig` — `config_schema`; `FsspecHttpxFetcher` — 스테이지 5멤버 + 내부 헬퍼
`_fetch_file`/`_fetch_http`(스킴별 다운로드)·`_build_source_document`(봉투 조립).
불변식·주의: BLAKE3는 `sdk.hashing.blake3_hex`로만 계산(ADR-0004). `storage`/`security`를 import하지
않는다(import-linter `adapters-no-storage`) — 저장은 `ctx.artifacts.put_source`만. `file://` 허용
루트는 `realpath` 정규화 후 `Path.is_relative_to()`로만 판정(문자열 접두 금지). fetch 출력의
`format_confidence`는 항상 `0.0`, `container_flags`는 항상 자리표 — 확정은 `detect`의 몫.
검증 계층: 1층(여기서 검증, respx 모의 HTTP) — `tests/adapters/fetch/test_fetch.py`.
DEFERRED: `s3://`/`gs://`/`az://`/`smb://`, `EgressGuard` CIDR/DNS pinning, `KeyProvider` 해소,
악성 스캔, zip 컨테이너 전개(후속 WP, WP-101 문서 참조).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from datetime import UTC
from email.utils import formatdate
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import url2pathname

import httpx
from pydantic import AnyUrl, BaseModel, ConfigDict, Field

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.source_document import (
    ContainerFlags,
    DedupReport,
    FetchReport,
    HttpMetadata,
    LineageRefs,
    SourceDocument,
    SourceMetadata,
)
from rag_platform.sdk.hashing import blake3_hex, hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from datetime import datetime

    from rag_platform.contracts.ingest_request import IngestRequest

__all__ = ["FetchConfig", "FsspecHttpxFetcher"]

PLUGIN_ID = "fetcher.fsspec_httpx"
PLUGIN_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0.0"

# 04-pipelines/02 §2.1: 이 WP는 file/http(s)만 구현한다(s3/gs/az/smb는 후속 WP).
_SUPPORTED_SCHEMES = frozenset({"file", "http", "https"})
_REDIRECT_STATUS = frozenset({301, 302, 303, 307, 308})

# §5.7 오류 카탈로그 철자(stage="fetch").
_ACCESS_DENIED = "fetch.access_denied"
_NOT_FOUND = "fetch.not_found"
_TOO_LARGE = "fetch.too_large"
_SCHEME_UNSUPPORTED = "fetch.scheme_unsupported"
_EGRESS_DENIED = "fetch.egress_denied"
_TIMEOUT = "fetch.timeout"
_UPSTREAM_ERROR = "fetch.upstream_error"

# 04-pipelines/02 §6 미디어 타입 힌트 정규화(일부 예시만; 표 전문의 부분집합).
_HINT_ALIASES: dict[str, str] = {
    "application/vnd.hancom.hwpx": "application/hwp+zip",
    "text/rtf": "application/rtf",
}

# 04-pipelines/02 §6 "미디어 타입 신호" 열 → 잠정 포맷.
_MEDIA_TYPE_FORMAT: dict[str, ct.SourceFormat] = {
    "application/hwp+zip": ct.SourceFormat.hwpx,
    "application/x-hwp": ct.SourceFormat.hwp5,
    "application/pdf": ct.SourceFormat.pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ct.SourceFormat.docx,
    "application/msword": ct.SourceFormat.doc,
    "application/rtf": ct.SourceFormat.rtf,
    "application/vnd.oasis.opendocument.text": ct.SourceFormat.odt,
    "text/html": ct.SourceFormat.html,
    "application/xhtml+xml": ct.SourceFormat.html,
    "text/markdown": ct.SourceFormat.md,
    "text/plain": ct.SourceFormat.txt,
    "application/json": ct.SourceFormat.json,
}

# 04-pipelines/02 §6 "확장자 신호" 열 → 잠정 포맷.
_EXTENSION_FORMAT: dict[str, ct.SourceFormat] = {
    ".hwpx": ct.SourceFormat.hwpx,
    ".hwp": ct.SourceFormat.hwp5,
    ".pdf": ct.SourceFormat.pdf,
    ".docx": ct.SourceFormat.docx,
    ".doc": ct.SourceFormat.doc,
    ".rtf": ct.SourceFormat.rtf,
    ".odt": ct.SourceFormat.odt,
    ".html": ct.SourceFormat.html,
    ".htm": ct.SourceFormat.html,
    ".md": ct.SourceFormat.md,
    ".markdown": ct.SourceFormat.md,
    ".txt": ct.SourceFormat.txt,
    ".json": ct.SourceFormat.json,
}

# 04-pipelines/02 §3.6 표(부분집합) — resolved_uri에서 제거할 공급자 서명 쿼리 키(대소문자 무시).
_SIGNATURE_QUERY_KEYS = frozenset(
    {"x-amz-signature", "x-amz-credential", "x-amz-security-token", "x-goog-signature", "sig"}
)


class FetchConfig(BaseModel):
    """`ingest.fetch`의 `max_bytes`(바이블 §7.3 예약 키) + 이 WP 범위(file/http(s))의 정책 값.

    `file_allowed_roots`는 배포 설정 `RAG_FETCH__FILE__ALLOWED_ROOTS`(04-pipelines/02 §2.3)의
    스탠드인이다 — 이 WP는 settings 계층 배선을 하지 않으므로 `config_schema`로 임시 수용한다
    (open issue, WP-101 참조).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_bytes: int = Field(209_715_200, ge=1)
    connect_timeout_ms: int = Field(5_000, ge=1)
    idle_read_timeout_ms: int = Field(30_000, ge=1_000)
    max_redirects: int = Field(3, ge=0)
    allowed_schemes: frozenset[str] = frozenset({"https", "http", "file"})
    file_allowed_roots: tuple[str, ...] = ()


@dataclass
class _FetchResult:
    """한 번의 다운로드(또는 304 재사용) 결과 — `_build_source_document`가 소비하는 중간 표현."""

    media_type: str
    format: ct.SourceFormat
    resolved_uri: str
    size_bytes: int
    content_hash: str | None
    data: bytes | None
    etag: str | None
    last_modified: str | None
    charset: str | None
    redirects: int
    http_status: int | None
    conditional_request: bool
    not_modified: bool
    duration_ms: int
    bytes_per_sec: float
    reused: bool = False


def _root(value: Any) -> Any:
    """RootModel 래퍼(`Ulid`·`Hex64`·`MediaType` 등)를 순수 값으로 벗긴다. 평범한 값은 그대로."""
    return value.root if hasattr(value, "root") else value


def _rfc3339_ms(moment: datetime) -> str:
    """바이블 §6.3 정본 표기(밀리초 정밀도, `Z` 접미)로 UTC 타임스탬프를 렌더링한다."""
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def _canonical_json(data: dict[str, Any]) -> str:
    """정렬 키·구분자 고정 JSON(바이블 §6.2 근사) — `H()` 조합 해시 입력."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _to_artifact_ref(value: Any, *, media_type: str) -> ct.ArtifactRef:
    """`ctx.artifacts.put_source` 반환값(구현마다 dataclass·모델·dict일 수 있음)을 `ArtifactRef`로 정규화."""
    if isinstance(value, ct.ArtifactRef):
        return value
    if hasattr(value, "model_dump"):
        return ct.ArtifactRef.model_validate(value.model_dump(mode="json"))
    return ct.ArtifactRef(
        uri=_root(value.uri),
        blake3=_root(value.blake3),
        media_type=media_type,
        size_bytes=value.size_bytes,
    )


def _normalize_hint(hint: str | None) -> str | None:
    if not hint:
        return None
    lowered = hint.split(";", 1)[0].strip().lower()
    return _HINT_ALIASES.get(lowered, lowered)


def _format_for_path(path: str) -> ct.SourceFormat | None:
    suffix = Path(unquote(path)).suffix.lower()
    return _EXTENSION_FORMAT.get(suffix)


def _resolve_media_type_and_format(
    *, hint: str | None, header_content_type: str | None, path_for_extension: str
) -> tuple[str, ct.SourceFormat, str | None]:
    """04-pipelines/02 §6 표 그대로: `media_type`은 Content-Type 우선, `format`은 힌트 우선."""
    charset: str | None = None
    header_media_type: str | None = None
    if header_content_type:
        parts = header_content_type.split(";")
        main = parts[0].strip().lower()
        if main and main != "application/octet-stream":
            header_media_type = main
        for part in parts[1:]:
            key, sep, value = part.partition("=")
            if sep and key.strip().lower() == "charset":
                charset = value.strip().strip('"').lower()

    normalized_hint = _normalize_hint(hint)
    media_type = header_media_type or normalized_hint or "application/octet-stream"

    fmt = None
    if normalized_hint:
        fmt = _MEDIA_TYPE_FORMAT.get(normalized_hint)
    if fmt is None and header_media_type:
        fmt = _MEDIA_TYPE_FORMAT.get(header_media_type)
    if fmt is None:
        fmt = _format_for_path(path_for_extension)
    if fmt is None:
        fmt = ct.SourceFormat.unknown
    return media_type, fmt, charset


def _resolve_and_check_file(raw_path: str, roots: tuple[str, ...], plugin_id: str) -> tuple[str, os.stat_result]:
    """블로킹 파일시스템 검사(realpath·존재·종류·`stat`)를 한데 모은 동기 헬퍼 — `asyncio.to_thread`로 호출.

    04-pipelines/02 §3.4 순서: 허용 루트 포함(문자열 접두 금지, `realpath` 정규화 후
    `Path.is_relative_to()`만) → 대상 검사(일반 파일만).
    """
    realpath = os.path.realpath(raw_path)
    normalized_roots = [os.path.realpath(root) for root in roots]
    if not normalized_roots or not any(Path(realpath).is_relative_to(root) for root in normalized_roots):
        raise StageError(
            _ACCESS_DENIED,
            stage="fetch",
            plugin_id=plugin_id,
            detail="path outside RAG_FETCH__FILE__ALLOWED_ROOTS (04-pipelines/02 §3.4)",
        )
    path_obj = Path(realpath)
    if not path_obj.exists() or path_obj.is_dir():
        raise StageError(_NOT_FOUND, stage="fetch", plugin_id=plugin_id, detail="file missing or is a directory")
    if not path_obj.is_file():
        raise StageError(_ACCESS_DENIED, stage="fetch", plugin_id=plugin_id, detail="not a regular file")
    return realpath, path_obj.stat()


def _strip_signed_query(url: str) -> str:
    """04-pipelines/02 §3.6 — 공급자 서명 쿼리 키만 제거하고 나머지·순서는 보존."""
    parsed = urlsplit(url)
    if not parsed.query:
        return url
    kept = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _SIGNATURE_QUERY_KEYS
    ]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(kept), parsed.fragment))


class FsspecHttpxFetcher:
    """`fetcher.fsspec_httpx` 코어 플러그인 — `file`/`http`/`https` 스킴만 내부 분기(04-pipelines/02 §2.1)."""

    plugin_id = PLUGIN_ID
    config_schema = FetchConfig
    # 제안(04-pipelines/02 §7.1·미해결 이슈 3): 조건부 GET 입력. 바이블 §4.1은 오늘 `index`만
    # `requires_lineage`를 쓴다고 적어 이 선언은 그 문구와 어긋난다 — open issue로 보고한다.
    requires_lineage: tuple[str, ...] = ("SourceDocument",)

    def __init__(self, config: FetchConfig | None = None, *, client: httpx.AsyncClient | None = None) -> None:
        """설정을 고정한다. `client`를 주면 그 연결을 재사용하고(호출자 소유), 없으면 호출마다 새로 연다."""
        self.config = config or FetchConfig()
        self._client = client

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2 근사)."""
        dumped = self.config.model_dump(mode="json")
        dumped["allowed_schemes"] = sorted(dumped["allowed_schemes"])
        return hash_of("config", _canonical_json(dumped))

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`, `input_formats=[file,http,https]`(04-pipelines/02 §2.1 스케치)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=sorted(_SUPPORTED_SCHEMES),
            requires_gpu=False,
            extra={
                "max_bytes": self.config.max_bytes,
                "supports_conditional_get": True,
                "supports_range": False,
            },
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(인프로세스: 이미지·모델 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def run(self, inp: IngestRequest, ctx: Any) -> SourceDocument:
        """스킴 정책·능력 검사 → 스킴별 다운로드 → 저장 → `SourceDocument` 조립(04-pipelines/02 §1.3)."""
        scheme = urlsplit(str(inp.source_uri)).scheme.lower()
        if scheme not in self.config.allowed_schemes:
            raise StageError(
                _EGRESS_DENIED,
                stage="fetch",
                plugin_id=self.plugin_id,
                detail=f"scheme {scheme!r} not in allowed_schemes (04-pipelines/02 §3.1 (1))",
            )
        if scheme not in _SUPPORTED_SCHEMES:
            raise StageError(
                _SCHEME_UNSUPPORTED,
                stage="fetch",
                plugin_id=self.plugin_id,
                detail=f"scheme {scheme!r} not supported by {self.plugin_id} (04-pipelines/02 §3.1 (2))",
            )
        previous = self._previous_source_document(ctx)
        result = await self._fetch_file(inp) if scheme == "file" else await self._fetch_http(inp, previous)
        artifact = await self._store(result, previous, ctx)
        return self._build_source_document(inp, ctx, result, artifact, previous)

    def _previous_source_document(self, ctx: Any) -> Any | None:
        """조건부 GET·dedup 판정 입력(제안, §7.1) — `ctx.lineage["SourceDocument"]`, 없으면 `None`."""
        lineage = getattr(ctx, "lineage", None)
        if not lineage:
            return None
        return lineage.get("SourceDocument")

    async def _store(self, result: _FetchResult, previous: Any | None, ctx: Any) -> ct.ArtifactRef:
        """304 재사용은 이전 `artifact`를 그대로 참조하고, 아니면 `ctx.artifacts.put_source`로 저장."""
        if result.reused:
            # `reused=True`는 `_read_not_modified`가 previous None이면 이미 예외를 던진 뒤에만
            # 나오므로 여기서는 None이 아니다(정적 타입 좁히기용 방어 assert).
            assert previous is not None  # noqa: S101 - reused=True 분기는 previous None이면 이미 예외를 던진 뒤에만 온다
            return _to_artifact_ref(previous.artifact, media_type=result.media_type)
        ref = await ctx.artifacts.put_source(result.data, media_type=result.media_type)
        return _to_artifact_ref(ref, media_type=result.media_type)

    # ------------------------------------------------------------------------------------------
    # file://
    # ------------------------------------------------------------------------------------------

    async def _fetch_file(self, inp: IngestRequest) -> _FetchResult:
        """04-pipelines/02 §3.4 — 권위부 형식 → 허용 루트 포함 → 대상 검사 순서로 판정 후 전체 읽기."""
        parsed = urlsplit(str(inp.source_uri))
        if parsed.netloc not in ("", "localhost"):
            raise StageError(
                _EGRESS_DENIED,
                stage="fetch",
                plugin_id=self.plugin_id,
                detail=f"file:// authority {parsed.netloc!r} not supported (04-pipelines/02 §3.4)",
            )
        raw_path = url2pathname(unquote(parsed.path))
        realpath, stat = await asyncio.to_thread(
            _resolve_and_check_file, raw_path, self.config.file_allowed_roots, self.plugin_id
        )
        path_obj = Path(realpath)

        start = time.monotonic()
        data = await asyncio.to_thread(path_obj.read_bytes)
        if len(data) > self.config.max_bytes:
            raise StageError(_TOO_LARGE, stage="fetch", plugin_id=self.plugin_id, detail="file exceeds max_bytes")
        duration = max(time.monotonic() - start, 1e-9)
        media_type, fmt, _charset = _resolve_media_type_and_format(
            hint=_root(inp.media_type_hint), header_content_type=None, path_for_extension=realpath
        )
        return _FetchResult(
            media_type=media_type,
            format=fmt,
            resolved_uri=path_obj.as_uri(),
            size_bytes=len(data),
            content_hash=blake3_hex(data),
            data=data,
            etag=None,
            last_modified=formatdate(stat.st_mtime, usegmt=True),
            charset=None,
            redirects=0,
            http_status=None,
            conditional_request=False,
            not_modified=False,
            duration_ms=int(duration * 1000),
            bytes_per_sec=len(data) / duration,
            reused=False,
        )

    # ------------------------------------------------------------------------------------------
    # http(s)://
    # ------------------------------------------------------------------------------------------

    async def _fetch_http(self, inp: IngestRequest, previous: Any | None) -> _FetchResult:
        """04-pipelines/02 §3.3·§5.1·§7.2 — 조건부 헤더 → 리다이렉트 루프 → 304/오류/200 분기."""
        etag, last_modified = self._conditional_validators(previous)
        headers: dict[str, str] = {
            "User-Agent": f"rag-platform/{PLUGIN_VERSION}",
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
        }
        conditional_request = False
        if etag:
            headers["If-None-Match"] = etag
            conditional_request = True
        elif last_modified:
            headers["If-Modified-Since"] = last_modified
            conditional_request = True

        url = str(inp.source_uri)
        client = self._client or httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(
                connect=self.config.connect_timeout_ms / 1000,
                read=self.config.idle_read_timeout_ms / 1000,
                write=self.config.idle_read_timeout_ms / 1000,
                pool=self.config.idle_read_timeout_ms / 1000,
            ),
        )
        owns_client = self._client is None
        redirects = 0
        start = time.monotonic()
        try:
            while True:
                try:
                    async with client.stream("GET", url, headers=headers) as response:
                        status = response.status_code
                        if status in _REDIRECT_STATUS:
                            url, redirects = self._follow_redirect(url, response, redirects, headers)
                            continue
                        if status == httpx.codes.NOT_MODIFIED:
                            return self._not_modified_result(
                                previous,
                                response,
                                url,
                                redirects=redirects,
                                conditional_request=conditional_request,
                                start=start,
                            )
                        if status != httpx.codes.OK:
                            raise self._map_status_error(status)
                        return await self._read_success(
                            inp,
                            response,
                            url,
                            redirects=redirects,
                            conditional_request=conditional_request,
                            start=start,
                        )
                except httpx.TimeoutException as exc:
                    raise StageError(_TIMEOUT, stage="fetch", plugin_id=self.plugin_id, detail=str(exc)) from exc
                except httpx.TransportError as exc:
                    raise StageError(_UPSTREAM_ERROR, stage="fetch", plugin_id=self.plugin_id, detail=str(exc)) from exc
        finally:
            if owns_client:
                await client.aclose()

    def _conditional_validators(self, previous: Any | None) -> tuple[str | None, str | None]:
        if previous is None:
            return None, None
        http_meta = getattr(previous, "http_metadata", None)
        if http_meta is None:
            return None, None
        return _root(getattr(http_meta, "etag", None)), _root(getattr(http_meta, "last_modified", None))

    def _follow_redirect(
        self, url: str, response: httpx.Response, redirects: int, headers: dict[str, str]
    ) -> tuple[str, int]:
        location = response.headers.get("location")
        if not location:
            raise StageError(
                _UPSTREAM_ERROR,
                stage="fetch",
                plugin_id=self.plugin_id,
                detail=f"redirect {response.status_code} without Location",
            )
        redirects += 1
        if redirects > self.config.max_redirects:
            raise StageError(
                _EGRESS_DENIED,
                stage="fetch",
                plugin_id=self.plugin_id,
                detail="max_redirects exceeded (04-pipelines/02 §3.1 (7))",
            )
        next_url = urljoin(url, location)
        prev_parsed, next_parsed = urlsplit(url), urlsplit(next_url)
        next_scheme = next_parsed.scheme.lower()
        if next_scheme not in ("http", "https"):
            raise StageError(
                _EGRESS_DENIED,
                stage="fetch",
                plugin_id=self.plugin_id,
                detail=f"redirect to unsupported scheme {next_scheme!r}",
            )
        if prev_parsed.scheme.lower() == "https" and next_scheme == "http":
            raise StageError(
                _EGRESS_DENIED, stage="fetch", plugin_id=self.plugin_id, detail="https to http downgrade redirect"
            )
        if (prev_parsed.scheme, prev_parsed.hostname, prev_parsed.port) != (
            next_parsed.scheme,
            next_parsed.hostname,
            next_parsed.port,
        ):
            headers.pop("Authorization", None)
        return next_url, redirects

    def _map_status_error(self, status: int) -> StageError:
        detail = f"HTTP {status}"
        if status in (401, 403, 407):
            return StageError(_ACCESS_DENIED, stage="fetch", plugin_id=self.plugin_id, detail=detail)
        if status in (404, 410):
            return StageError(_NOT_FOUND, stage="fetch", plugin_id=self.plugin_id, detail=detail)
        if status == httpx.codes.REQUEST_TIMEOUT:
            return StageError(_TIMEOUT, stage="fetch", plugin_id=self.plugin_id, detail=detail)
        # 429·5xx·그 외 4xx·요청 없는 206 등: 원천 상황(04-pipelines/02 §9.1 표) 전용 재시도 코드.
        return StageError(_UPSTREAM_ERROR, stage="fetch", plugin_id=self.plugin_id, detail=detail)

    def _not_modified_result(
        self,
        previous: Any | None,
        response: httpx.Response,
        url: str,
        *,
        redirects: int,
        conditional_request: bool,
        start: float,
    ) -> _FetchResult:
        if previous is None:
            # §7.2 (5)는 "원본 부재" 경합만 다룬다 — previous가 아예 없으면 조건부 헤더를 보내지
            # 않았을 것이므로 이 304는 원천 이상 동작이다(재시도 가능으로 분류).
            raise StageError(
                _UPSTREAM_ERROR,
                stage="fetch",
                plugin_id=self.plugin_id,
                detail="304 Not Modified without a previous SourceDocument",
            )
        duration_ms = int((time.monotonic() - start) * 1000)
        return _FetchResult(
            media_type=_root(getattr(previous, "media_type", None)) or "application/octet-stream",
            format=getattr(previous, "format", ct.SourceFormat.unknown),
            resolved_uri=_strip_signed_query(url),
            size_bytes=_root(getattr(previous, "size_bytes", 0)) or 0,
            content_hash=_root(getattr(previous, "doc_version", None)),
            data=None,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            charset=None,
            redirects=redirects,
            http_status=httpx.codes.NOT_MODIFIED,
            conditional_request=conditional_request,
            not_modified=True,
            duration_ms=duration_ms,
            bytes_per_sec=0.0,
            reused=True,
        )

    async def _read_success(
        self,
        inp: IngestRequest,
        response: httpx.Response,
        url: str,
        *,
        redirects: int,
        conditional_request: bool,
        start: float,
    ) -> _FetchResult:
        content_length = response.headers.get("content-length")
        if content_length is not None:
            declared = int(content_length) if content_length.isdigit() else None
            if declared is not None and declared > self.config.max_bytes:
                raise StageError(
                    _TOO_LARGE, stage="fetch", plugin_id=self.plugin_id, detail=f"Content-Length {declared}"
                )
        buffer = bytearray()
        async for chunk in response.aiter_bytes():
            buffer.extend(chunk)
            if len(buffer) > self.config.max_bytes:
                raise StageError(
                    _TOO_LARGE, stage="fetch", plugin_id=self.plugin_id, detail="streamed body exceeds max_bytes"
                )
        data = bytes(buffer)
        media_type, fmt, charset = _resolve_media_type_and_format(
            hint=_root(inp.media_type_hint),
            header_content_type=response.headers.get("content-type"),
            path_for_extension=urlsplit(url).path,
        )
        duration = max(time.monotonic() - start, 1e-9)
        return _FetchResult(
            media_type=media_type,
            format=fmt,
            resolved_uri=_strip_signed_query(url),
            size_bytes=len(data),
            content_hash=blake3_hex(data),
            data=data,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            charset=charset,
            redirects=redirects,
            http_status=response.status_code,
            conditional_request=conditional_request,
            not_modified=False,
            duration_ms=int(duration * 1000),
            bytes_per_sec=len(data) / duration,
            reused=False,
        )

    # ------------------------------------------------------------------------------------------
    # SourceDocument 조립
    # ------------------------------------------------------------------------------------------

    def _build_source_document(
        self,
        inp: IngestRequest,
        ctx: Any,
        result: _FetchResult,
        artifact: ct.ArtifactRef,
        previous: Any | None,
    ) -> SourceDocument:
        """04-pipelines/02 §12 채움 규칙 — 봉투·메타/ACL 해시·`fetch_report`/`dedup_report` 조립."""
        timestamp = _rfc3339_ms(ctx.now())

        metadata = (
            SourceMetadata.model_validate(inp.metadata.model_dump(mode="json"))
            if inp.metadata is not None
            else SourceMetadata()
        )
        meta_dump = metadata.dump_contract()
        for key, default in (("language_hint", "ko"), ("genre", "unknown")):
            if meta_dump.get(key) == default:
                meta_dump.pop(key, None)
        metadata_hash = hash_of("meta", _canonical_json(meta_dump))

        acl_dump = inp.acl.dump_contract()
        acl_defaults: list[tuple[str, object]] = [("deny_principals", []), ("classification", "internal")]
        for acl_key, acl_default in acl_defaults:
            if acl_dump.get(acl_key) == acl_default:
                acl_dump.pop(acl_key, None)
        acl_hash = hash_of("acl", _canonical_json(acl_dump))

        # 미해결(04-pipelines/02 §7.3 미해결 이슈 4): 컬렉션·테넌트 기본값은 셸이 ctx로 제공해야
        # 한다. 그 배선이 없는 이 WP는 바이블 §7.1 예시 컬렉션 기본(mask)으로 근사한다.
        pii_policy = inp.pii_policy or ct.PiiPolicy.mask
        pii_tokenize_mode = inp.pii_tokenize_mode
        if pii_policy == ct.PiiPolicy.tokenize and pii_tokenize_mode is None:
            pii_tokenize_mode = ct.PiiTokenizeMode.encrypt

        http_metadata = None
        if result.etag or result.last_modified or result.charset:
            http_metadata = HttpMetadata(etag=result.etag, last_modified=result.last_modified, charset=result.charset)

        previous_doc_version = _root(getattr(previous, "doc_version", None)) if previous is not None else None
        dedup_report = DedupReport(
            policy=inp.dedup_policy or ct.DedupPolicy.skip_if_same_hash,
            previous_doc_version=previous_doc_version,
            content_unchanged=previous_doc_version is not None and previous_doc_version == result.content_hash,
            source_bytes_reused=result.reused,
        )

        return SourceDocument(
            schema_version=SCHEMA_VERSION,
            schema_type="SourceDocument",
            tenant_id=ctx.tenant_id,
            collection_id=inp.collection_id,
            producer=ct.Producer(
                plugin_id=self.plugin_id,
                plugin_version=PLUGIN_VERSION,
                config_hash=self.config_hash(),
                image_digest=None,
            ),
            quality=ct.Quality.full,
            warnings=[],
            created_at=timestamp,
            lineage_refs=LineageRefs(),
            document_id=ctx.document_id,
            request_id=inp.request_id,
            source_uri=inp.source_uri,
            resolved_uri=AnyUrl(result.resolved_uri),
            artifact=artifact,
            content_hash=artifact.blake3,
            doc_version=artifact.blake3,
            size_bytes=artifact.size_bytes,
            media_type=result.media_type,
            format=result.format,
            format_confidence=0.0,
            container_flags=ContainerFlags(encrypted=False, distribution=False, compressed=False),
            http_metadata=http_metadata,
            metadata=metadata,
            metadata_hash=metadata_hash,
            acl=inp.acl,
            acl_hash=acl_hash,
            pii_policy=pii_policy,
            pii_tokenize_mode=pii_tokenize_mode,
            external_id=inp.external_id,
            external_version=inp.external_version,
            credentials_ref=inp.credentials_ref.root if inp.credentials_ref is not None else None,
            fetched_at=timestamp,
            fetch_report=FetchReport(
                attempts=1,
                bytes_per_sec=result.bytes_per_sec,
                redirects=result.redirects,
                http_status=result.http_status,
                conditional_request=result.conditional_request,
                not_modified=result.not_modified,
                duration_ms=result.duration_ms,
            ),
            dedup_report=dedup_report,
        )
