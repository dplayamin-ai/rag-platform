# WP-101: fetch-fsspec-httpx (F1-01)

## 목표

`fetcher` 확장 지점의 코어 플러그인 `fetcher.fsspec_httpx`(`Stage[IngestRequest, SourceDocument]`)를
구현한다. 이 WP 범위는 스킴 `file://`(허용 루트 제한)와 `http(s)://`(httpx, `max_bytes`, 조건부
GET용 `etag`/`last-modified` 기록, 리다이렉트 정책)로 한정한다. `s3`/`gs`/`az`/`smb`, `EgressPolicy`의
전체 CIDR·DNS 고정 연결 강제(`EgressGuard`, `security/egress_policy`), 자격 증명 해소(`KeyProvider`),
악성 스캔, zip 컨테이너 전개는 이 WP 밖이다(아래 "불변식·금지"·"DEFERRED" 참조). BLAKE3 해시는
`sdk.hashing.blake3_hex`로만 계산하고(ADR-0004 단일 구현), 원본은 `ctx.artifacts.put_source`로
콘텐츠 주소화 저장한다. 포맷의 최종 판정(`container_flags`·확정 `format`)은 `detect`(별도 스테이지)의
몫이며 fetch 출력은 항상 잠정값만 채운다(바이블 §4.2 `detect` 행, 04-pipelines/02 §6).

## 파일

- `src/rag_platform/adapters/fetch/fsspec_httpx.py` — `FetchConfig`(config_schema), `FsspecHttpxFetcher`
  (5멤버 스테이지: `plugin_id`·`config_schema`·`requires_lineage`·`capabilities()`·`fingerprint()`·
  `async run()`), 내부 헬퍼(`_fetch_file`·`_fetch_http`·`_build_source_document`·미디어 타입/포맷
  판별·서명 쿼리 제거).
- `tests/adapters/fetch/test_fetch.py` — `file://`·`http(s)://` 성공/오류 경로, respx 모의 HTTP,
  실 네트워크 없음(`needs_network`는 없음 — 이 WP는 실제 아웃바운드 호출을 만들지 않는다).
- 테스트 픽스처는 `tests/fixtures/` 아래 필요 시 추가(임시 파일은 `tmp_path`로 생성, 별도 고정 파일
  불필요).

## 시그니처

```python
class FetchConfig(BaseModel):  # model_config = ConfigDict(extra="forbid", frozen=True)
    max_bytes: int = 209_715_200
    connect_timeout_ms: int = 5_000
    idle_read_timeout_ms: int = 30_000
    max_redirects: int = 3
    allowed_schemes: frozenset[str] = frozenset({"https", "http", "file"})
    file_allowed_roots: tuple[str, ...] = ()  # RAG_FETCH__FILE__ALLOWED_ROOTS 배포 설정의 스탠드인(open issue)

class FsspecHttpxFetcher:
    plugin_id = "fetcher.fsspec_httpx"
    config_schema = FetchConfig
    requires_lineage: tuple[str, ...] = ("SourceDocument",)  # 제안(04-pipelines/02 §7.1) — open issue

    def __init__(self, config: FetchConfig | None = None, *, client: httpx.AsyncClient | None = None) -> None: ...
    def config_hash(self) -> str: ...
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: IngestRequest, ctx: Any) -> SourceDocument: ...
```

`ctx`는 `sdk.context.StageContext` 구조(적어도 `tenant_id`·`document_id`·`now()`·`artifacts`·
`lineage`)를 만족해야 한다. `ctx.artifacts`는 `sdk.context.DerivedArtifacts`(`put_source(data, *,
media_type)`)만 쓰고 `ArtifactStore`(storage 계층)는 직접 보지 않는다(바이블 §12, import-linter
`adapters-no-storage` 계약).

## 입출력 계약 발췌(필드·열거 철자 그대로)

- `IngestRequest`(소비): `source_uri: AnyUrl`, `collection_id: Ulid`, `media_type_hint: MediaType|None`,
  `metadata: IngestMetadata|None`, `acl: Acl`, `pii_policy: PiiPolicy|None`, `pii_tokenize_mode:
  PiiTokenizeMode|None`, `credentials_ref: CredentialsRef|None`, `dedup_policy: DedupPolicy|None`,
  `external_id`/`external_version: str|None`, `request_id: Ulid`.
- `SourceDocument`(생산, fetch 출력): 봉투(`schema_version="1.0.0"`, `schema_type="SourceDocument"`,
  `tenant_id`, `collection_id`, `producer`, `quality="full"`, `warnings=[]`, `created_at`,
  `lineage_refs={}`), `document_id`, `request_id`, `source_uri`/`resolved_uri`, `artifact`,
  `content_hash`/`doc_version`(동일값)/`size_bytes`, `media_type`/`format`/`format_confidence=0.0`,
  `container_flags={encrypted:false,distribution:false,compressed:false}`(자리표), `http_metadata`
  (`etag`/`last_modified`/`charset`, 있는 것만), `metadata`/`metadata_hash`, `acl`/`acl_hash`,
  `pii_policy`/`pii_tokenize_mode`, `external_id`/`external_version`/`credentials_ref`(참조만),
  `fetched_at`, `fetch_report`(`attempts,bytes_per_sec,redirects,http_status,conditional_request,
  not_modified,duration_ms`), `dedup_report`(`policy,previous_doc_version,content_unchanged,
  source_bytes_reused`). `detect_report`는 채우지 않는다(detect 전용).
- 오류 코드(§5.7 철자, `stage="fetch"`): `fetch.access_denied`(no), `fetch.not_found`(no),
  `fetch.too_large`(no), `fetch.scheme_unsupported`(no), `fetch.egress_denied`(no),
  `fetch.timeout`(yes), `fetch.upstream_error`(yes). "제안" 코드(`fetch.checksum_mismatch` 등)는
  채택 전이므로 발생시키지 않는다(04-pipelines/02 §9.1).

## 불변식·금지

1. **콘텐츠 해시**: `blake3_hex`(sdk.hashing)만 쓴다. 어댑터가 `blake3` 패키지를 직접 import하지
   않는다(ruff `TID251`, ADR-0004).
2. **저장 경계**: `rag_platform.storage`/`rag_platform.security`를 import하지 않는다(import-linter
   `adapters-no-storage`). 원본 저장은 `ctx.artifacts.put_source`만 호출한다.
3. **스킴 오류 코드 단일 규칙**(04-pipelines/02 §3.1 결정): 정책(`allowed_schemes`) 밖이면
   `fetch.egress_denied`, 정책은 허용했으나 이 플러그인의 능력(`file`/`http`/`https` 셋) 밖이면
   `fetch.scheme_unsupported`. 순서는 정책 검사 → 능력 검사.
4. **`file://` 허용 루트**: 문자열 접두 비교 금지, `os.path.realpath` 정규화 후
   `Path.is_relative_to()`로만 판정(04-pipelines/02 §3.4). 허용 루트가 비어 있으면 모두 거부.
5. **콘텐츠 해시 기준**: `content_hash`는 전송 압축을 해제한 표현 바이트(httpx가 `gzip` 자동 해제).
   같은 문서는 `Content-Encoding` 유무와 무관하게 같은 해시(04-pipelines/02 §3.3).
6. **크기 상한**: `Content-Length` 사전 검사 + 스트리밍 중 누적 검사 이중 강제, 초과 시 스풀(누적
   버퍼) 폐기 후 `fetch.too_large`.
7. **리다이렉트**: 자동 추적 끔(`follow_redirects=False`), 홉마다 재검사, `max_redirects` 초과·
   `http(s)` 외 스킴·`https→http` 다운그레이드는 `fetch.egress_denied`. 교차 출처 홉은 `Authorization`
   헤더 제거(이 WP는 인증 헤더를 설정하지 않지만 구조는 유지).
8. **포맷 판정 위임**: `format_confidence`는 항상 `0.0`, `container_flags`는 항상 자리표. `format`/
   `media_type`은 §6 표(힌트→Content-Type→확장자)의 잠정값일 뿐 하류 라우팅 정본이 아니다.
9. **비밀 미기록**: `resolved_uri`에서 공급자 서명 쿼리 키(`X-Amz-Signature` 등, §3.6 표 일부)를
   제거한다. `StageError.detail`에 인증 헤더·서명 값을 남기지 않는다.
10. 커밋 금지, 이모지 금지, 첫 줄 한국어 헤더(`tools/phase6/CODE-HEADER-RULE.md`).

## 단계

1. `FetchConfig` 정의(비예약 배포 설정은 이 WP에서 `config_schema`로 임시 수용 — open issue로 기록).
2. `FsspecHttpxFetcher` 5멤버 골격 + `config_hash`/`capabilities`/`fingerprint`(hwpx 파서 어댑터
   패턴 재사용).
3. `run()` — 스킴 정책·능력 검사 → `_fetch_file`/`_fetch_http` 분기 → `ctx.artifacts.put_source`
   (304 재사용 시 생략) → `_build_source_document`.
4. `_fetch_file` — 권위부(authority) 형식 검사 → 허용 루트 포함 검사 → 대상 검사(일반 파일만) →
   스트리밍 없이 전체 읽기(로컬 파일이므로 스풀 불요) + `blake3_hex` + mtime→HTTP-date.
5. `_fetch_http` — 조건부 헤더(이전 `SourceDocument`는 `ctx.lineage["SourceDocument"]`에서 읽음,
   §7.1 제안) → 리다이렉트 루프(정책 재검사) → 304/오류/200 분기 → 스트리밍 청크 누적 + 크기 상한 →
   `httpx` 예외 → 카탈로그 코드 매핑.
6. `_build_source_document` — 봉투·메타데이터/ACL 해시(근사 `canonical_json`, 00-contract-overview
   §7 전문은 읽기 예산 밖이라 근사치, open issue)·`fetch_report`/`dedup_report` 조립.
7. 테스트 작성 → `uv run pytest -q tests/adapters/fetch/test_fetch.py` → `uv run ruff check
   src/rag_platform/adapters/fetch/fsspec_httpx.py`.

## 테스트(파일·케이스)

`tests/adapters/fetch/test_fetch.py`:

- `file://`: 허용 루트 내부 파일 성공(해시·크기·`resolved_uri`=as_uri 검증), 허용 루트 밖 거부
  (`fetch.access_denied`), 허용 루트 빈 목록 거부, 디렉터리 대상(`fetch.not_found`), 부재 파일
  (`fetch.not_found`), UNC 권위부 거부(`fetch.egress_denied`), 심볼릭 링크로 루트 탈출 시도 거부
  (플랫폼이 지원할 때만 — 스킵 가드).
- `http(s)://`(respx 모의): 200 성공(미디어 타입·포맷·해시), `Content-Length`>`max_bytes` 사전 거부,
  스트리밍 중 초과 중단, 301/302 리다이렉트 추적(≤`max_redirects`) 및 초과 시 거부, `https→http`
  다운그레이드 거부, 조건부 GET(이전 `SourceDocument` 주입) → 304 시 바이트 재사용·`dedup_report`,
  401/403→`fetch.access_denied`, 404→`fetch.not_found`, 429/5xx→`fetch.upstream_error`,
  `httpx.ConnectTimeout`→`fetch.timeout`, `http` 스킴이 `allowed_schemes` 밖일 때
  `fetch.egress_denied`, 지원 밖 스킴(`s3://`)일 때 `fetch.scheme_unsupported`.
- 무결성: 같은 바이트를 두 번 받으면 같은 `content_hash`(gzip 유무 무관은 respx `Content-Encoding`
  헤더만 설정한 사례로 근사 검증 — 실제 압축 스트림은 httpx가 처리하므로 별도 압축 불요).
- `capabilities()`/`fingerprint()`/`config_hash()` 스모크(결정적 재현).

## 완료 기준

- 위 테스트 케이스가 `uv run pytest -q tests/adapters/fetch/test_fetch.py`로 통과.
- `uv run ruff check src/rag_platform/adapters/fetch/fsspec_httpx.py` 통과.
- import-linter `adapters-no-storage`/`layers` 계약을 위반하는 import 없음(수동 확인: `storage`/
  `security` import 부재).
- 신규 패키지 추가 없음(기존 `httpx`/`blake3`/`respx` 재사용).

## 검증 계층·DEFERRED

1층(여기서 검증) — `tests/adapters/fetch/test_fetch.py`(respx 모의 HTTP, `tmp_path` 파일 I/O).
실 네트워크·Docker·모델·GPU 의존 없음 — 이 WP에 `needs_network`/`needs_docker`/`needs_model`/
`needs_gpu` 마커 테스트가 없다. `s3://`/`gs://`/`az://`/`smb://` 어댑터, `EgressGuard`(CIDR·DNS
고정 연결) 강제, `KeyProvider`(`credentials_ref` 실제 해소), 악성 스캔 훅, zip 컨테이너 전개,
`decoded_ratio_max`(압축 해제 폭탄 비율) 실측 강제는 이 WP 밖이며 후속 WP로 미룬다(아래
open_issues와 04-pipelines/02 §미해결 이슈 1·5·7 참조). `# DEFERRED: s3/gs/az/smb 스킴, EgressGuard
CIDR/DNS pinning, KeyProvider 해소, 악성 스캔, zip 컨테이너 — 후속 WP·security/storage 계층 구현
후 tests/security에서 재검증`.

결과: 통과 27 / xfail 0 / DEFERRED 상기 항목
