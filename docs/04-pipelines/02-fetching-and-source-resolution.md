---
title: "수집: 페치와 소스 해석"
status: active
owner: architecture
version: 0.1.1
last_updated: 2026-09-23
depends_on:
  - ../00-vision/00-design-brief.md
  - ../02-architecture/00-design-bible.md
  - ../07-tech-landscape/00-summary-and-selection-matrix.md
  - ../01-requirements/01-functional-requirements.md
  - ../01-requirements/02-non-functional-requirements.md
  - ../02-architecture/02-component-architecture.md
  - ../02-architecture/03-data-flow-and-document-lifecycle.md
  - ../02-architecture/05-plugin-architecture.md
  - ../02-architecture/06-orchestration-and-workflows.md
  - ../02-architecture/07-multi-tenancy-and-security-architecture.md
  - ../03-contracts/00-contract-overview.md
  - ../03-contracts/01-ingest-request.md
  - ../03-contracts/02-source-document.md
  - ../03-contracts/12-jobs-events-and-status.md
  - ../03-contracts/13-error-model.md
  - ../03-contracts/15-collection-profile-and-policy-contracts.md
  - ./01-pipeline-framework.md
  - ../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md
  - ../06-adr/0038-outbound-egress-policy-and-webhook-signing.md
---

# 수집: 페치와 소스 해석

## 목적

이 문서는 수집 파이프라인의 첫 스테이지 `fetch`(확장 지점 `fetcher`)가 `IngestRequest.source_uri` 하나를 **어떻게 해석하고, 어디까지 연결을 허용하고, 어떻게 내려받아 콘텐츠 주소화(content-addressed)로 저장하고, 무엇을 `SourceDocument`(fetch 출력)에 채우는가**를 확정한다. 계약(필드·열거·오류 코드)은 설계 바이블(Design Bible) §4.2 `fetch` 행, §4.4 `fetch` 정책, §5.3 `EgressPolicy`, §5.4 `IngestRequest`·`SourceDocument`, §5.7 오류 카탈로그, §10.3 E16, §13.3 오브젝트 키가 정본이며 이 문서는 그것을 알고리즘·정책·운영 수치로 **확장하되 바꾸지 않는다**. 실행 골격(셸·캐시·재시도·계측)은 [파이프라인 프레임워크](./01-pipeline-framework.md)를 그대로 쓴다.

브리프 R1의 함의 "플랫폼은 크롤러가 아니다"가 이 스테이지의 성격을 정한다: `fetch`는 호출자가 지정한 **단일 URI**를 **매번** 읽는 풀(pull) 스테이지이고(캐시 없음, 바이블 §4.2; [ADR-0037](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md)), 플랫폼 안에서 테넌트가 고른 목적지로 아웃바운드 연결을 여는 두 지점 중 하나이므로(다른 하나는 웹훅 릴레이) 서버 측 요청 위조(Server-Side Request Forgery, SSRF) 방어 E16의 1차 강제 지점이다([ADR-0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md)).

## 범위

- 포함: `fetch` 스테이지의 위치·책임 경계, `fetcher` 플러그인 모델과 코어 플러그인 `fetcher.fsspec_httpx`의 스킴 라우팅(`s3`·`gs`·`az`·`https`·`http`·`file`; `smb`는 플러그인), 소스 해석과 `EgressPolicy`(E16) 적용 범위(테넌트 제어 목적지 vs 운영자 설정 엔드포인트), HTTP(S) 세부(조건부 요청, 리다이렉트, 크기 한계, 스트리밍, robots 무시), `file://` 허용 루트, 인증 참조 해석(`credentials_ref` → KeyProvider), 스트리밍 BLAKE3·크기 상한 강제, 무결성 힌트 검증(제안), 악성 스캔 훅(ClamAV 옵션, 제안), 원본 저장(`sources/{blake3}`)과 중복 감지(`dedup_report`, `skip_if_same_hash`), 포맷 판별 1차(fetch 출력의 잠정값), 압축 컨테이너(zip) 정책, 실패 분류·재시도·취소, 크기·타임아웃 표, 관측성, fetch 출력 채움 규칙과 예시.
- 제외: 시그니처 기반 포맷 판별·`container_flags`([파싱 라우터와 포맷 판별](./03-parsing-router-and-format-detection.md); `detect`는 `parse` 액티비티 내부 서브스테이지다), `IngestRequest` 접수·멱등성([IngestRequest 계약](../03-contracts/01-ingest-request.md)), `SourceDocument` 스키마 전문([SourceDocument 계약](../03-contracts/02-source-document.md)), `EgressPolicy` 합성 규칙 전문([컬렉션·프로파일·정책 계약](../03-contracts/15-collection-profile-and-policy-contracts.md)), 무변경 생략 뒤의 payload 갱신·세대 사가([데이터 흐름과 문서 생애주기](../02-architecture/03-data-flow-and-document-lifecycle.md), [갱신·삭제·재색인](./19-update-delete-and-reindexing.md)), 웹훅 egress(릴레이, [웹훅과 이벤트](../05-api/07-webhooks-and-events.md)).
- 정본 규칙: 타입·필드·열거값·오류 코드·이벤트·메트릭 이름은 바이블 §5·§5.7·§6의 철자만 쓴다. 이 문서가 새로 붙이는 이름(`SourceClientFactory`, `MalwareScanner`, `RAG_FETCH__*`, `checksum_hint`, `fetch.checksum_mismatch` 등)은 본문에 "제안"으로 표시하고 `## 미해결 이슈`에 바이블·계약 반영 여부를 남긴다. 수치는 바이블 값이 아니면 모두 "초안 목표"다. 라이브러리 버전·라이선스는 [선정 매트릭스](../07-tech-landscape/00-summary-and-selection-matrix.md) `uri_fetcher` 행이 "연구 공백 — 잠정 권고"이므로 단정하지 않는다(확인 필요 as of 2026-09).

---

## 1. 위치와 책임 경계

### 1.1 스테이지 위치(바이블 §4.2·§4.4)

| 항목 | 값 | 출처 |
|------|----|------|
| 입력 → 출력 | `IngestRequest → SourceDocument`(fetch 출력; `format_confidence = 0.0`, `container_flags` 자리표) | 바이블 §4.2, 02-source-document §1.2 |
| 확장 지점 / 코어 플러그인 | `fetcher` / `fetcher.fsspec_httpx`(`adapters/fetch/fsspec_httpx.py`) | 바이블 §7.3, §12 |
| 격리 모드 | `in_process`(asyncio 네이티브 I/O; 큐 `ingest-io`) | 바이블 §4.2, §11.2 |
| 캐시 | **없음** — `stage_key` 미적용, 항상 실행. `CACHE_EXEMPT = {fetch, index}` | 바이블 §4.1·§4.2, ADR-0037, 01-pipeline-framework §7.2 |
| `StagePolicy` | `task_queue=ingest-io`, `start_to_close=5m`, `heartbeat=30s`, `max_attempts=5`(지수, 최대 간격 1m), `resumable=no`, `non_retryable_error_codes=[fetch.access_denied, fetch.not_found, fetch.too_large, fetch.scheme_unsupported, fetch.egress_denied]` | 바이블 §4.4 |
| 재시도 코드 | `fetch.timeout`, `fetch.upstream_error`(yes) | 바이블 §5.7 |
| 이벤트 | `ingest.document.fetched`(산출물·계보 저장 트랜잭션에서 셸이 기록; 무변경 생략 경로에도 발행) | 바이블 §5.7, 03-contracts/12, 03-data-flow §3.2 |
| 강제 지점 | E16 아웃바운드 egress(`EgressPolicy` 프로파일 AND 테넌트; 워커 NetworkPolicy는 2차 방어, §3.1), E5 오브젝트 키 접두(`tenants/{tenant_id}/`)·E17 콘텐츠 키 스코프(`lineage` PK에 `tenant_id`) | 바이블 §10.3 E5·E16·E17 |
| 결정성 등급 | 01-pipeline-framework §8.1의 세 등급(`pure`/`model_pinned`/`generative`) **밖** — 출력이 외부 상태(원천)에 의존하고 캐시 대상이 아니다. 캐시 제외 스테이지용 등급(제안 `external`) 또는 `determinism` 생략 허용을 01 미해결 이슈 8과 공동 제안한다(미해결 이슈 20). 적합성 `idempotency`는 "같은 바이트를 두 번 받으면 같은 `content_hash`·같은 `sources/` 키"만 검증한다 | 01-pipeline-framework §8.1, 미해결 이슈 20 |

### 1.2 책임 분리

`fetch`가 우아한 이유는 여섯 주체(`fetcher`·`EgressGuard`·`KeyProvider`·셸·워크플로우, 그리고 하류의 `detect`)가 서로의 일을 하지 않기 때문이다.

| 관심사 | `fetcher` 플러그인(`Stage.run`) | `EgressGuard`(`security/egress_policy`) | `KeyProvider`(`security/key_provider`) | 셸(`orchestration/context`) | 워크플로우(`ingest.document.v1`) | `detect`(`parse` 내부) |
|--------|------|------|------|------|------|------|
| URI 문법·스킴 라우팅 | 소유 | — | — | — | — | — |
| 스킴·호스트·포트·CIDR·리다이렉트·크기·시간 판정 | 호출만(`RuntimeServices.http`가 적용) | 소유(E16) | — | — | — | — |
| 비밀 값 해소 | 보지 않는다(`credentials_ref`만 전달) | — | 소유(`env|openbao|aws_kms`) | — | — | — |
| 스트리밍 다운로드·BLAKE3·크기 상한 | 소유 | — | — | — | — | — |
| 원본 저장(`sources/{blake3}`) | `ctx.artifacts.put_source` | — | — | 키 규약·테넌트 바인딩 | — | — |
| 조건부 GET 입력(이전 `SourceDocument`) | 읽기(`ctx.lineage`) | — | — | 소유(원장에서 로드, §7.1 제안) | — | — |
| `dedup_report` 채움 | 소유(판정 기록만) | — | — | — | 소유(생략·payload 갱신·계속 결정) | — |
| `format`·`format_confidence`·`container_flags` | 잠정값·자리표만(§6) | — | — | — | — | 소유 |
| 출력 검증·저장·계보·이벤트·잡 전이 | — | — | — | 소유 | — | — |
| 재시도·타임아웃·하트비트 타이머 | — | — | — | 정책 적용 | `StagePolicy` 전달 | — |

### 1.3 전체 흐름

```mermaid
sequenceDiagram
    autonumber
    participant W as ingest.document.v1 (PipelineContext.run)
    participant S as StageShell.execute (run_stage)
    participant L as ledger (jobs · documents · artifacts · lineage · outbox)
    participant F as fetcher.fsspec_httpx
    participant G as EgressGuard (E16)
    participant K as KeyProvider
    participant SRC as 원천 (https · s3 · gs · az · file)
    participant O as ArtifactStore (sources/)
    W->>S: StageActivityInput{stage=fetch, job, input_ref(IngestRequest)}
    S->>L: mark_stage_started(stage=fetch) [tx]
    S->>S: 캐시 조회 없음 (CACHE_EXEMPT)
    S->>L: (제안, §7.1·미해결 이슈 3) 현재 세대 source(documents.current_commit_id → artifact_refs.source) 조회 → 존재 확인
    S->>F: run(IngestRequest, ctx{lineage["SourceDocument"]? — 제안, §7.1})
    F->>G: check(source_uri, policy=profile ∧ tenant) → ResolvedTarget
    G-->>F: 허용 (정책 거부 fetch.egress_denied / 능력 부재 fetch.scheme_unsupported, §3.1)
    F->>K: resolve(credentials_ref) — 값은 클라이언트 팩토리 내부에만
    F->>SRC: GET (조건부: If-None-Match / If-Modified-Since, 검증자 있을 때만)
    alt 304 Not Modified
        SRC-->>F: 304
        F->>F: content_hash = 이전 doc_version, bytes 재사용
    else 200 OK (또는 3xx → 홉마다 G.check 반복, ≤ max_redirects)
        SRC-->>F: 스트림
        F->>F: 청크 단위 BLAKE3 증분 · 누적 ≤ max_bytes · 스풀 · (옵션) 스캐너 INSTREAM 동시 전송
        F->>F: (옵션) 스풀 완료 후 스캐너 판정 수신 (§5.3)
        F->>O: put_source(spool_path, media_type, blake3=h) — 스트리밍 오버로드(제안, 미해결 이슈 17); 동일 키 존재 시 쓰기 생략
        O-->>F: ArtifactRef{uri=…/sources/{h[:2]}/{h}, blake3=h, size_bytes}
    end
    F-->>S: SourceDocument(fetch 출력: format 잠정, format_confidence 0.0, dedup_report, fetch_report)
    S->>S: complete_envelope → validate_out (S-1 ~ S-16)
    S->>O: put_artifact(SourceDocument, stage_key=None → 바이트 해시 키, 잠정 채택 §5.4)
    S->>L: lineage(artifacts 행 없음, §5.4) + jobs.progress + outbox(ingest.document.fetched) [tx]
    S-->>W: ArtifactRef
    W->>W: dedup 판정(§7.3): 무변경 생략 / payload 갱신 / stage.parse 계속
```

---

## 2. Fetcher 플러그인 모델

### 2.1 프로토콜과 코어 플러그인

**결정:** `fetcher`는 `Stage[IngestRequest, SourceDocument]`의 타입 특수화이며 추가 멤버는 `schemes: frozenset[str]` 하나다([플러그인 아키텍처](../02-architecture/05-plugin-architecture.md) §3.2; [컴포넌트 아키텍처](../02-architecture/02-component-architecture.md) §2.4; [ADR-0032](../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md)). 코어는 플러그인 **하나**(`fetcher.fsspec_httpx`)를 제공하고 그 안에서 스킴별 어댑터로 분기한다. 이유: (1) 프로파일 `ingest.fetch.plugin`은 단일 값이고(바이블 §7.3), (2) 스킴별 플러그인을 나누면 레지스트리가 URI를 보고 플러그인을 고르는 "라우터 플러그인"이 다시 필요해져 `parse.router`와 같은 합성 계층이 하나 더 생기는데, 페치는 파서 체인처럼 폴백·격리 사다리가 없어 그 비용이 정당화되지 않는다. 레지스트리가 URI를 보고 플러그인을 고르는 라우터 플러그인은 두지 않으며, `runtime.egress.allowed_schemes`에 스킴만 추가하면 코어가 알아서 그 스킴의 플러그인을 찾는 **암묵 자동 위임도 불허**한다. 외부 스킴(`smb` 등)을 붙이는 길은 둘이다: (1) 프로파일이 `ingest.fetch.plugin`을 그 플러그인으로 **교체**한다 — 그 컬렉션은 그 플러그인의 `schemes`만 지원하고 코어 스킴(`s3`·`https` 등)을 잃는다; (2) 코어 플러그인의 `delegates`(제안, §2.3)에 `plugin_id`를 **명시 등록**해 코어가 스킴별로 위임한다 — 코어 스킴과 외부 스킴을 한 컬렉션에서 함께 쓰는 기본 경로다.

```python
# src/rag_platform/adapters/fetch/fsspec_httpx.py — 정본 스케치(05 §3.2 프로토콜 + 이 문서)
class FsspecHttpxFetcher(StageBase[IngestRequest, SourceDocument]):
    plugin_id = "fetcher.fsspec_httpx"
    config_schema = FetchConfig                                   # §2.3
    schemes = frozenset({"https", "http", "s3", "gs", "az", "file"})   # 05 §3.2 목록 + http(옵트인 스킴; 05 patch 요청, 미해결 이슈 9)

    def __init__(self, config: FetchConfig, services: RuntimeServices, *, image_digest: str | None = None) -> None:
        super().__init__(config, image_digest=image_digest)
        self._http = services.http                # EgressGuard 적용 httpx.AsyncClient 팩토리(02 §2.3)
        self._sources = services.sources          # 제안: SourceClientFactory — s3/gs/az/file 클라이언트(운영자 엔드포인트 + credentials_ref)
        self._delegates = services.registry.fetch_delegates(config.delegates)   # 제안: 외부 스킴 플러그인(smb …)

    def capabilities(self) -> Capabilities:
        return Capabilities(isolation_modes=["in_process"], supports_resumable=False, contracts_compat=">=1.0,<2.0",
                            input_formats=sorted(self.schemes | self._delegates.schemes),
                            extra={"max_bytes": self.config.max_bytes, "supports_conditional_get": True, "supports_range": False})

    async def run(self, inp: IngestRequest, ctx: StageContext) -> SourceDocument:
        scheme = urlsplit(inp.source_uri).scheme.lower()
        adapter = self._adapter_for(scheme)                       # 능력 부재(input_formats ∪ delegates 밖)면 fetch.scheme_unsupported; 정책 거부는 EgressGuard가 fetch.egress_denied(§3.1)
        previous = ctx.lineage.get("SourceDocument")              # 제안(§7.1·미해결 이슈 3): 셸이 원장 현재 세대 source를 넣어 준다(없으면 None)
        target = await adapter.resolve(inp, ctx)                  # §3: EgressGuard 통과한 ResolvedTarget (s3/gs/az는 운영자 엔드포인트)
        result = await adapter.download(target, inp, previous, ctx)   # §5: 스트리밍 · BLAKE3 · max_bytes · 스풀 · 304 처리
        artifact = await self._store(result, ctx)                 # §5.4: put_source(spool_path, media_type=…, blake3=content_hash) 스트리밍 오버로드(제안, 미해결 이슈 17) 또는 이전 artifact 재사용
        return self._build_source_document(inp, result, artifact, previous, ctx)   # §12
```

`Capabilities.extra`의 `max_bytes`·`supports_conditional_get`·`supports_range`는 [플러그인 아키텍처](../02-architecture/05-plugin-architecture.md) §5 `fetcher` 행의 키 그대로다. `input_formats`(스킴 집합)과 프로파일 `runtime.egress.allowed_schemes`의 교집합만 활성화되고, 허용 스킴이 능력 밖이면 프로파일 검증이 `fetch.scheme_unsupported` 사전 경고를 낸다(05 §5). 05 §3.2의 `schemes` 예시는 `{s3, gs, az, https, file}`로 `http`가 없다 — `http`는 바이블 §5.3 옵트인 스킴이므로 코어 능력에 포함하고 05 §3.2 patch를 요청한다(미해결 이슈 9).

### 2.2 스킴 × 어댑터 표

라이브러리 열은 매트릭스 `uri_fetcher` 행의 **잠정 권고**(fsspec 계열 + httpx + smbprotocol; 대안 obstore·개별 SDK)를 그대로 옮긴 것이며 버전·API·라이선스는 확인 필요(as of 2026-09)다. 조사 기준은 §2.4에 둔다.

| 스킴 | 어댑터(코어 여부) | 라이브러리(잠정) | 네트워크 목적지 | E16 판정 대상(§3.2) | 검증자(`http_metadata`) | 조건부 GET | 인증(`credentials_ref` 시크릿 형태, §4) | 비고 |
|------|------|------|------|------|------|------|------|------|
| `https` | 코어 | httpx(`follow_redirects=False`, 스트리밍) | URI 호스트(테넌트 제어) | **전체**(스킴→호스트→포트→DNS→CIDR→고정 연결→홉 반복) | `ETag`, `Last-Modified`, `charset` | `If-None-Match` / `If-Modified-Since` | `bearer`·`basic`·`header`(없으면 익명) | 프리사인 URL 허용, 서명 쿼리는 `resolved_uri`에서 제거 |
| `http` | 코어 | 동일 | 동일 | 전체 + 프로파일이 열고 테넌트 옵트인(`allowed_schemes`·`allowed_ports=80`) | 동일 | 동일 | 동일 | 다운그레이드 리다이렉트(`https → http`) 금지(§3.3) |
| `s3` | 코어 | fsspec(s3fs) 또는 obstore — 확인 필요 | **운영자 설정 엔드포인트**(`RAG_FETCH__S3__ENDPOINT_URL`, 제안; 미설정 시 공급자 공개 엔드포인트) | 스킴 + `allowed_hosts`(URI authority = 버킷)만; 엔드포인트는 서비스 디스커버리 주소로 취급 | `ETag`(멀티파트 ETag는 콘텐츠 해시가 아니므로 불투명 검증자로만), `LastModified` | HEAD(`info`) ETag 비교 → 변경 시 GET; 네이티브 `IfNoneMatch` 지원 시 사용(확인 필요) | `aws`(access key·secret·session token) | 프리픽스·디렉터리 URI 미지원(`fetch.not_found`) |
| `gs` | 코어 | fsspec(gcsfs) — 확인 필요 | 운영자 설정 엔드포인트 | 동일 | `ETag`/`generation`(불투명), `updated` | HEAD 비교; 네이티브 조건 헤더 지원 확인 필요(02 미해결 이슈 11) | `gcp_sa`(서비스 계정 JSON) | |
| `az` | 코어 | fsspec(adlfs) — 확인 필요 | 운영자 설정 엔드포인트(계정 접미) | 동일 | `ETag`, `Last-Modified` | HEAD 비교; `If-None-Match` 지원 확인 필요 | `azure_sas`·`azure_key` | URI 형식 `az://{container}/{path}`(계정은 배포 설정) |
| `file` | 코어 | 표준 라이브러리(`os`, `aiofiles` 여부는 구현 선택) | 없음(로컬 FS) | 스킴(`runtime.orchestrator=local`만, 15 P-4) + 허용 루트(§3.4) | `Last-Modified`(mtime, HTTP-date 형식) | mtime + 크기 비교 | 없음 | 개발·CI·`lite` 로컬 전용; 운영 거부는 E16 테스트 항목 |
| `smb` | 플러그인 `fetcher.smbprotocol`(패키지 `rag-plugin-smb-fetcher`, 05 §미해결 이슈 8 제안 명칭) | smbprotocol — 확인 필요 | URI 서버(테넌트 입력)이나 **운영자 서버 허용 목록**에 있을 때만 | 스킴 + 서버 허용 목록(§3.5) | 수정 시각·크기 | mtime + 크기 비교 | `smb`(user·password·domain) | 사설망 원천 규칙은 ADR-0038 재검토 조건 |
| `sftp` | (미정) 플러그인 후보 | — | — | — | — | — | `ssh_key`·`basic` | 바이블 스킴 목록에 없음(미해결 이슈 9) |

### 2.3 설정: `config_schema`와 배포 설정의 분리

**결정:** 프로파일 값(`ingest.fetch.*`)은 `config_schema`로 검증되어 `config_hash`에 들어가고, 호스트명·경로·비밀·엔드포인트는 배포 설정(`RAG_FETCH__*`, 바이블 §6.6 접두 규약; 제안)으로 분리한다. 근거: [파이프라인 프레임워크](./01-pipeline-framework.md) §2.3 "설정에 절대 경로·호스트명·비밀·시각을 넣지 않는다". `fetch`는 캐시 대상이 아니라 지문의 캐시 효과는 없지만 `Producer.config_hash`는 여전히 재현성 기록이다.

바이블 §7.3의 `ingest.fetch`는 `{plugin, max_bytes, policy}` 세 예약 키만 적는다. 아래 `FetchConfig`의 나머지 키(`idle_read_timeout_ms`·`decoded_ratio_max`·`allow_ambient_credentials`·`per_host_concurrency`·`malware_scan`·`delegates`)는 플러그인 `config_schema`가 소유하는 **비예약 키**(01 §2.3; 프로파일 로더는 예약 키를 뺀 나머지를 플러그인 `config_schema`로 검증)이며, `profile.schema.json`·바이블 §7.3 YAML 등재는 별도 patch로 제안한다(미해결 이슈 19). 등재 전까지 이 키들은 "코어 플러그인 `fetcher.fsspec_httpx`의 설정"이지 프로파일 계약이 아니다.

```python
class MalwareScanConfig(BaseModel):                    # 제안(§5.3). 기본 끔
    model_config = ConfigDict(extra="forbid", frozen=True)
    enabled: bool = False
    fail_mode: Literal["closed", "open"] = "closed"    # 스캐너 불가 시: closed = 재시도 후 실패, open = 경고 없이 통과(운영 프로파일 금지)

class FetchConfig(BaseModel):                          # 프로파일 ingest.fetch 의 비예약 키(plugin·policy 제외)
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_bytes: int = Field(209_715_200, ge=1)                     # 바이블 §5.1·§7.3; EgressPolicy.max_bytes 기본값
    idle_read_timeout_ms: int = Field(30_000, ge=1_000)           # 초안 목표(§10)
    decoded_ratio_max: int = Field(100, ge=1)                     # 전송 압축 해제 폭탄 상한(초안 목표, NFR-SEC-10 준용)
    allow_ambient_credentials: bool = False                       # §4 결정: 워커 주변 자격 증명 기본 금지
    per_host_concurrency: int = Field(8, ge=1)                    # 초안 목표(§10)
    malware_scan: MalwareScanConfig = MalwareScanConfig()
    delegates: list[str] = []                                     # 제안: 외부 스킴 플러그인 plugin_id(예 fetcher.smbprotocol)
```

| 배포 설정(제안, `RAG_FETCH__*`) | 의미 | 기본 |
|------|------|------|
| `RAG_FETCH__S3__ENDPOINT_URL`, `__REGION`, `__ADDRESSING_STYLE` | `s3://` 네트워크 목적지(운영자 신뢰 엔드포인트) | 공급자 공개 엔드포인트 |
| `RAG_FETCH__GS__ENDPOINT_URL` / `RAG_FETCH__AZ__ACCOUNT_SUFFIX` | `gs://`·`az://` 목적지 | 공급자 기본 |
| `RAG_FETCH__FILE__ALLOWED_ROOTS` | `file://` 허용 루트 목록(§3.4) | 비어 있음(= 모두 거부) |
| `RAG_FETCH__SMB__SERVERS` | `smb://` 서버 허용 목록(플러그인이 읽음, §3.5) | 비어 있음 |
| `RAG_FETCH__SPOOL_DIR` | 스풀 디렉터리(§5.1) | 워커 임시 볼륨 |
| `RAG_FETCH__CLAMD__ADDRESS` | 악성 스캔 훅 `clamd` 주소(서비스 디스커버리, §5.3) | 없음 |

### 2.4 라이브러리 조사 기준(바이블 미해결 이슈 5)

매트릭스가 "04-pipelines/02 작성 전 별도 조사"로 남긴 `uri_fetcher` 비교(fsspec 계열 vs obstore vs 개별 SDK; httpx; smbprotocol)는 이 문서 작성 시점에도 수행되지 않았다. 선택은 **잠정**(`fetcher.fsspec_httpx`, 바이블 §7.3)이며, 조사는 다음 기준으로 한다. 어떤 결과든 이 문서의 정책(§3~§9)은 불변이어야 한다(ADR-0038 DR-8).

| # | 기준 | 이유 |
|---|------|------|
| 1 | 라이선스 등급 A(Apache/MIT/BSD), 순수 Python 또는 `linkage=dynamic`; `PluginMeta.license`·`license_grade` 기록 | D-02, ADR-0001 |
| 2 | 비동기 스트리밍 읽기(청크 단위)와 `Content-Length`/크기 사전 조회(`info`) | §5.1 크기 상한을 다운로드 전·중에 강제 |
| 3 | 검증자 노출(ETag·Last-Modified·generation)과 조건부 GET(네이티브 `IfNoneMatch` 또는 HEAD 비교) | 바이블 §4.2 조건부 재수집 |
| 4 | 호출 단위 자격 증명 주입(전역 환경 변수 아님)과 운영자 엔드포인트 지정 | §4 테넌트별 `credentials_ref`, §3.2 |
| 5 | https: 리다이렉트 자동 추적 비활성, 해석 IP 고정 연결 + 원 호스트명 SNI/`Host`(`resolve_pin`) | E16; httpx/httpcore의 `sni_hostname` 요청 확장으로 실현 가능한지 확인 필요(as of 2026-09) |
| 6 | 의존 트리 크기·릴리스 안정성(`uv lock --check`) | 바이블 리스크 #9 |
| 7 | 벤더 예외 → 카탈로그 코드 매핑 가능성(§9.1) | 어댑터 오류 경계(02 §6.1 B1) |

---

## 3. 소스 해석과 `EgressPolicy`(E16)

### 3.1 판정 순서

판정기는 `security/egress_policy`(`EgressGuard`) 하나이고 `fetch`·릴레이·구독 등록이 같은 코드를 쓴다(ADR-0038). 순서와 실패 코드는 [컬렉션·프로파일·정책 계약](../03-contracts/15-collection-profile-and-policy-contracts.md) §8과 같다.

| 순서 | 검사 | 입력 | 실패 코드 |
|------|------|------|-----------|
| 1 | **정책**: 스킴 ∈ `allowed_schemes`(프로파일 ∩ 테넌트). 운영 프로파일의 `file`, 미옵트인 `http`, 바이블 스킴 목록 밖 스킴이 정책에 없을 때 모두 여기서 끝난다 | `source_uri` | `fetch.egress_denied`(바이블 §5.4 `source_uri` 행 "비허용 스킴", E16 테스트 "`file://` 운영 거부") |
| 2 | **능력**: 스킴 ∈ `fetcher.input_formats` ∪ `delegates`의 스킴(정책은 허용했으나 이 배포의 플러그인이 다루지 못함; 프로파일 검증이 사전 경고하므로 실행 중 발생은 드물다, 05 §5) | `source_uri` | `fetch.scheme_unsupported` |
| 3 | `allowed_hosts`(있으면; `.` 접두 접미 일치 또는 소문자 정확 일치) | URI authority | `fetch.egress_denied` |
| 4 | 포트 ∈ `allowed_ports`(기본 `[443]`, `80` 옵트인) | URI 포트(기본값 보정) | `fetch.egress_denied` |
| 5 | DNS 해석(모든 A/AAAA) × `deny_cidrs`(합집합; 기본 9개 축소 불가) | 호스트명 | `fetch.egress_denied` |
| 6 | 고정 연결(`resolve_pin`): 검사한 IP로 연결, SNI·`Host`는 원 호스트명 | 5의 결과 | (연결 실패는 §9.1) |
| 7 | 3xx마다 1·3~6 반복, 홉 수 ≤ `max_redirects`(기본 3); 리다이렉트 목적지 스킴이 `http(s)` 밖이거나 다운그레이드면 정책 위반 | `Location` | `fetch.egress_denied` |
| 8 | `connect_timeout_ms`(기본 5,000), `max_bytes`(기본 `ingest.fetch.max_bytes`) | 연결·스트림 | `fetch.timeout` / `fetch.too_large` |

**결정(스킴 오류 코드의 단일 규칙):** 스킴 거부 코드는 **누가 막았는가**로 갈린다 — 정책(`allowed_schemes`)이 막으면 `fetch.egress_denied`, 정책은 허용했으나 플러그인 능력(`input_formats`·`delegates`)이 없으면 `fetch.scheme_unsupported`. 바이블 §5.4 `IngestRequest.source_uri` 행과 §10.3 E16 실패 열이 "비허용 스킴 → `fetch.egress_denied`"를 정본으로 두고, 05 §5가 `fetch.scheme_unsupported`를 "허용 스킴이 능력 밖"의 사전 경고로 쓰므로 이 구분이 두 앵커를 모두 만족한다. 이 규칙은 §3.4·§9.1·§13에 동일하게 적용된다. 13-error-model §3.2의 `fetch.scheme_unsupported` 설명("`allowed_schemes` 밖 또는 플러그인 부재")과 02-source-document §7 표("스킴 미허용 → `fetch.scheme_unsupported`")는 정책 거부까지 이 코드에 넣어 바이블 §5.4와 어긋나므로 patch를 요청한다(미해결 이슈 18; 15 §8은 바이블과 같다).

위반은 1회 시도로 종료하고(비재시도, 재시도 예산 소모 없음) `rag_egress_denied_total{component="fetch"}`를 올린다. 정책은 스테이지가 아니라 `RuntimeServices.http`(https)·`SourceClientFactory`(제안; s3/gs/az/file) 팩토리가 테넌트 ID로 합성 정책(`compose_egress(profile.runtime.egress, tenants.policies.egress_policy)`, 15 §8)을 가져와 적용한다 — 스테이지는 정책 객체를 보지 않고 원장을 읽지 않는다(01-pipeline-framework §2.5).

`EgressGuard`는 **1차** 방어다. 바이블 §10.3 E16과 06-orchestration §큐 표 `ingest-io` 행이 요구하는 **2차** 방어는 워커·릴레이 파드의 NetworkPolicy(사설 CIDR·클라우드 메타데이터 목적지 거부, 서비스 디스커버리 주소 — PostgreSQL·Qdrant·OpenSearch·Valkey·Temporal·사이드카·`clamd` — 만 허용)이며, [ADR-0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md) 준수 확인 "배포 매니페스트 검사"(09-operations/01·05 체크리스트)가 릴리스 차단 조건으로 검증한다. 2차 방어의 차단은 연결 타임아웃으로 나타나 `fetch.timeout` 재시도를 소모하므로(ADR-0038 대안 3), 1차 방어가 먼저 거부하는 것이 정상 경로다.

### 3.2 테넌트 제어 목적지와 운영자 설정 엔드포인트

바이블 E16은 "사이드카 호출은 서비스 디스커버리 주소만"이라고 적어, **테넌트 입력에서 파생된 목적지**와 **운영자가 배포 시 고정한 주소**를 구분한다. ADR-0038은 `s3`·`gs`·`az`의 엔드포인트 취급을 이 문서에 위임했다(중립 2, 재검토 조건 2).

**결정:** E16의 CIDR·고정 연결·리다이렉트 판정은 **테넌트 입력이 네트워크 목적지를 결정하는 경우**에만 적용한다. 스킴별로 다음과 같다.

| 스킴 | 목적지 결정자 | 적용 규칙 |
|------|---------------|-----------|
| `https`, `http` | 테넌트(`source_uri` 호스트·포트, 리다이렉트 `Location`) | §3.1 전체. 프리사인 URL도 동일(온프레미스 사설 대역의 프리사인 URL은 거부되며, 그 경우 `s3://` + 운영자 엔드포인트를 쓴다) |
| `s3`, `gs`, `az` | 운영자(배포 설정 엔드포인트; 테넌트는 버킷·컨테이너·키만 지정) | 스킴(1·2) + `allowed_hosts`(3; authority = 버킷·컨테이너)만. 엔드포인트는 서비스 디스커버리 주소로 간주해 `deny_cidrs`를 적용하지 않는다(온프레미스 RustFS·SeaweedFS S3 호환 엔드포인트가 사설 대역에 있어도 수집 가능). **테넌트가 엔드포인트를 지정하는 기능(BYO endpoint)은 v1 미지원**이며 도입 시 그 엔드포인트는 §3.1 전체 판정 대상이다 |
| `file` | 운영자(`RAG_FETCH__FILE__ALLOWED_ROOTS`) | 스킴(1·2; `runtime.orchestrator=local`만) + 허용 루트(§3.4). 네트워크 판정 없음 |
| `smb` | 테넌트(URI 서버) — 단, 운영자 허용 목록 안에서만 | 스킴(1·2) + 서버 ∈ `RAG_FETCH__SMB__SERVERS`; 목록에 없으면 `fetch.egress_denied`. 목록의 서버는 서비스 디스커버리 주소로 간주 |

이 결정은 `deny_cidrs` 축소 불가(바이블 §7.4 (12))를 유지하면서 사설망 오브젝트 스토리지 원천을 허용한다. 반대로 워커의 주변 자격 증명(IAM 역할 등)으로 임의 버킷을 읽는 경로는 §4에서 막는다. ADR-0038 재검토 조건 2의 답이므로 ADR 개정(patch)을 요청한다(미해결 이슈 1).

### 3.3 HTTP(S) 세부 규칙

**결정:** `http(s)://`는 **단일 리소스 GET**이다. 링크 추적·사이트맵·robots.txt·JS 렌더링은 하지 않는다.

| 항목 | 규칙 | 근거 |
|------|------|------|
| robots.txt | **무시한다.** 플랫폼은 크롤러가 아니라 호출자가 명시한 URI를 읽는 풀 모델이며(브리프 §6, FR-ING-16), robots.txt는 크롤러 대상 규약이다. 호출자(커넥터)가 준수 책임을 진다. SPA 렌더링 HTML 주입은 `fetcher` 플러그인으로 수용 가능(07-tech-landscape/03 제안)하되 코어 비범위 | 브리프 R1·§6 |
| 메서드·헤더 | `GET`만. `User-Agent: rag-platform/{version}`, `Accept: */*`, `Accept-Encoding: gzip, br`(brotli 지원은 확인 필요), 조건부 헤더(§7.2), `credentials_ref`가 준 인증 헤더. 쿠키 없음, `Referer` 없음 | — |
| 리다이렉트 | 자동 추적 끔(`follow_redirects=False`). 301·302·303·307·308만 따르고 `GET` 유지. 홉마다 §3.1 재검사, ≤ `max_redirects`(3), 초과·비허용 목적지·`https → http` 다운그레이드·`http(s)` 외 스킴(`file:`, `ftp:` 등)은 `fetch.egress_denied`. 교차 출처(스킴·호스트·포트 변경) 홉에서는 `Authorization`·인증 헤더를 제거한다. 상대 `Location`은 RFC 9110대로 해소. 중간 URL은 기록하지 않고 `fetch_report.redirects`에 수만 남긴다 | E16, ADR-0038 |
| TLS | 항상 검증(시스템 CA + 운영자 추가 CA 번들). 검증 비활성 옵션은 두지 않는다. SNI·`Host`는 원 호스트명(`resolve_pin`) | 브리프 §7 전송 TLS |
| 크기 | `Content-Length`가 있고 `> max_bytes`면 본문을 읽기 전에 `fetch.too_large`. 없거나 작아도 스트림 누적(**디코딩 후** 바이트)이 `max_bytes`를 넘으면 즉시 중단. 전송 압축(`Content-Encoding`) 해제 비율 > `decoded_ratio_max`(100:1, 초안)도 `fetch.too_large` | FR-ING-10, NFR-SEC-10 |
| 콘텐츠 해시 기준 | `content_hash`는 **전송 압축을 푼 표현 바이트**(문서 그 자체)다. 같은 문서가 gzip 유무로 다른 해시가 되지 않는다 | 원칙 4 |
| 시간 | 연결 `connect_timeout_ms`(5,000), 유휴 읽기 `idle_read_timeout_ms`(30,000, 초안), 전체는 `ctx.remaining_ms()`(액티비티 `start_to_close` 5m) | 바이블 §4.4·§5.3 |
| 429·503 + `Retry-After` | `fetch.upstream_error`(재시도)로 종료하고 셸의 백오프에 맡긴다(스테이지 내부 대기 금지, 01-pipeline-framework §2.5). `Retry-After`는 `StageError.detail`에 초 단위로만 남긴다 | ADR-0003 준수 확인 9 |
| 부분 응답 | 요청하지 않은 `206`, `Content-Length` 불일치, 조기 종료는 `fetch.upstream_error`(재시도). Range 재개는 v1 미지원(`supports_range=false`, `resumable=no`) | 바이블 §4.4 |
| 미디어 타입 | `Content-Type`의 타입/서브타입(소문자, 파라미터 제거)을 `media_type`로, `charset` 파라미터를 `http_metadata.charset`으로 기록(§6) | 바이블 §5.4 |
| 파일명 힌트 | `Content-Disposition; filename*=`의 확장자를 잠정 `format`의 마지막 신호로 쓴다(§6). 값은 저장하지 않는다 | — |

### 3.4 `file://` 허용 루트

**결정:** `file://`은 `runtime.orchestrator=local`(개발·CI·`lite` 로컬)에서만 스킴이 열리고(15 P-4), 경로는 운영자 허용 루트 안에 있어야 한다.

| 규칙 | 내용 | 위반 코드 |
|------|------|-----------|
| 스킴 | 운영 프로파일에서 `file`이 `allowed_schemes`에 없으면 즉시 종료(§3.1 1단계 — 정책 거부) | `fetch.egress_denied`(E16 테스트 "`file://` 운영 거부") |
| 형식 | `file:///abs/path`(빈 authority) 또는 `file://localhost/abs/path`만. 그 외 authority(UNC 호스트)는 거부 | `fetch.egress_denied` |
| 루트 | `os.path.realpath`(심볼릭 링크 해소) 결과가 `RAG_FETCH__FILE__ALLOWED_ROOTS` 중 하나의 **경로 세그먼트 기준 하위**여야 한다 — `Path(realpath).is_relative_to(root)`(또는 `os.path.commonpath([realpath, root]) == root`). 문자열 접두 비교는 금지한다(`/data/allowed`가 `/data/allowed-evil/x`를 통과시킨다; §13 테스트 항목). 루트 자체도 realpath로 정규화해 비교한다. 목록이 비어 있으면 모두 거부 | `fetch.access_denied` |
| 대상 | 일반 파일만. 디렉터리·장치·FIFO·소켓은 거부 | `fetch.not_found`(디렉터리·부재) / `fetch.access_denied`(특수 파일) |
| 검증자 | `Last-Modified`(mtime → HTTP-date) + 크기. 조건부 재수집은 mtime·크기 동일 시 304 동등 처리(§7.2) | — |
| `resolved_uri` | 정규화된 `file://` 경로(realpath). 허용 루트 밖 경로는 산출물에 남지 않는다(거부됨) | — |

### 3.5 `smb://`·`sftp://` 플러그인 규칙

`smb://`는 바이블 §5.4 스킴 목록의 유일한 플러그인 스킴이다. 코어는 라우팅 자리(`delegates`, 제안)와 정책만 정하고 구현은 `rag-plugin-smb-fetcher`(05 §미해결 이슈 8 제안 명칭)가 맡는다: (1) `input_formats=["smb"]`, (2) 서버는 `RAG_FETCH__SMB__SERVERS` 허용 목록 안에서만(§3.2), (3) 시크릿 형태 `smb`(§4), (4) 검증자는 수정 시각·크기, (5) 스풀·BLAKE3·크기 상한·`put_source`는 코어 SDK 헬퍼(`rag_platform.sdk.fetch_helpers`, 제안)를 재사용해 §5 규칙을 그대로 따른다. `sftp://`는 바이블 스킴 목록에 없어 이 문서는 정하지 않는다(미해결 이슈 9).

### 3.6 `resolved_uri`

**결정:** `resolved_uri`는 "최종적으로 읽은 리소스"를 서명·자격 증명 없이 가리키는 값이다(원칙은 02-source-document S-10). `https`: 최종 홉 URL에서 아래 표의 서명 쿼리 키를 제거(키 비교는 대소문자 무시, 값은 검사하지 않음, 나머지 쿼리·순서는 보존). `s3`/`gs`/`az`: 정규화된 `source_uri`(퍼센트 인코딩 정규화, 중복 `/` 제거). `file`: realpath. `resolved_uri`는 `IndexRecord.source_uri`의 원천 후보이며(02 미해결 이슈 6) 로그·스팬·이벤트에는 호스트·경로만 남긴다(§11).

02 미해결 이슈 12가 위임한 제거 키 목록의 **정본 위치**는 해소됐다: `EgressPolicy.strip_query_keys`는 바이블 §5.3 1.3.0에 등재됐다(AM-30, 15 §8 정의 그대로). `max_bytes`·`connect_timeout_ms`·`allowed_ports`도 같은 개정으로 `EgressPolicy` 선택 필드로 등재된 사실이다(AM-30). 이 문서 아래 표는 `strip_query_keys`의 **기본 목록 정본**이며(테넌트가 재정의하지 않는 한 이 값을 쓴다), 02의 계약 모델 상수 `_PROVIDER_SIGNATURE_KEYS`는 이 표에서 로드한다(미해결 이슈 16 해소). 제거 대상은 02 §7과 같게 **공급자 고유 서명 파라미터**로 한정한다 — `token`·`signature`·`key` 같은 범용 키는 정당한 원천 URL(예: 게시판 첨부 `?token=` 식별자)을 훼손할 수 있어 넣지 않고, 서명이 아닌 SAS 부속 파라미터(`se`·`sv`·`sp`·`sr`·`st` 등 만료·버전·권한 표기)는 비밀이 아니므로 남긴다.

| 공급자 | 제거하는 쿼리 키(v1, 확인 필요 as of 2026-09) | 남기는 키(예) |
|--------|-----------------------------------------------|---------------|
| AWS SigV4 프리사인 | `X-Amz-Signature`, `X-Amz-Credential`, `X-Amz-Security-Token` | `X-Amz-Algorithm`, `X-Amz-Date`, `X-Amz-Expires`, `X-Amz-SignedHeaders` |
| GCS 서명 URL | `X-Goog-Signature` | `X-Goog-Algorithm`, `X-Goog-Credential`(서비스 계정 이메일 — 비밀 아님; 02와 같게 유지, 필요 시 미해결 이슈 16에서 재검토), `X-Goog-Date`, `X-Goog-Expires` |
| Azure SAS | `sig` | `se`, `sv`, `sp`, `sr`, `st`, `spr`, `sip`, `si` |
| 범용 | (없음) | `token`, `signature`, `key` 등은 제거하지 않는다(02 §7) |

---

## 4. 인증 참조 해석(`credentials_ref` → 시크릿)

**결정:** 비밀 값은 스테이지 코드에 도달하지 않는다. `fetcher`는 `IngestRequest.credentials_ref`(형식 `{provider}:{path}`, 01 §8.3)를 클라이언트 팩토리(`RuntimeServices.http` / `SourceClientFactory`)에 그대로 넘기고, 팩토리가 `KeyProvider.resolve(credentials_ref)`(시그니처는 [멀티테넌시·보안 아키텍처](../02-architecture/07-multi-tenancy-and-security-architecture.md) §미해결 이슈 21 제안)로 값을 얻어 요청 헤더·SDK 세션에 주입한다. 값은 `SourceDocument.credentials_ref`로 **참조만** 전파되고 로그·스팬·`StageError.detail`·`fetch_report` 어디에도 실리지 않는다(바이블 §6.6, FR-SEC-06, 02 S-12).

| 시크릿 `type`(제안, KeyProvider 값 스키마) | 필드 | 적용 스킴 | 주입 방식 |
|------|------|------|------|
| `bearer` | `token` | `https`·`http` | `Authorization: Bearer …`(교차 출처 리다이렉트에서 제거) |
| `basic` | `username`, `password` | `https`·`http`·`sftp`(후보) | `Authorization: Basic …` |
| `header` | `name`, `value` | `https`·`http` | 임의 헤더(API 키 헤더 등). `Host`·`Cookie` 금지 |
| `aws` | `access_key_id`, `secret_access_key`, `session_token?` | `s3` | SDK 세션(호출 단위, 전역 환경 변수 아님) |
| `gcp_sa` | 서비스 계정 JSON | `gs` | 토큰 발급 → 요청 |
| `azure_sas` / `azure_key` | `sas_token` / `account_key` | `az` | SAS 쿼리 / 공유 키 서명 |
| `smb` | `username`, `password`, `domain?` | `smb` | 세션 인증(플러그인) |

**결정(주변 자격 증명 금지):** `credentials_ref`가 없는 `s3`·`gs`·`az` 요청은 **익명 접근**으로 시도한다. 워커 프로세스의 주변 자격 증명(IAM 인스턴스 역할, Workload Identity, 환경 변수)은 기본으로 쓰지 않는다 — 쓰면 어떤 테넌트든 워커가 읽을 수 있는 모든 버킷을 `source_uri` 하나로 읽어 갈 수 있어 D-09 격리 위반이 된다. 단일 테넌트 배포는 `ingest.fetch.allow_ambient_credentials: true`(기본 `false`)로 명시 옵트인한다. 익명 접근 거부는 `fetch.access_denied`(비재시도)다.

프리사인 URL(`https://…?X-Amz-Signature=…`)은 자격 증명이 URL에 들어 있는 형태다. 허용하되(01 §8.2) 서명은 `resolved_uri`에서 제거되고 로그에 남지 않으며, `IngestRequest`의 `credentials_ref` 사용을 권고한다(만료 시 `fetch.access_denied`).

---

## 5. 스트리밍 다운로드·무결성·저장

### 5.1 스풀과 BLAKE3 증분 해시

**결정:** 원본은 메모리에 통째로 올리지 않는다. 청크(권장 1 MiB, 초안) 단위로 읽으며 BLAKE3 증분 해시·누적 크기·(옵션) 스캐너 스트림을 동시에 갱신하고, 워커 로컬 스풀 파일에 쓴다. 완료 후 `content_hash`가 확정되면 그 키로 `put_source`한다. 오브젝트 스토리지 멀티파트 스테이징(`tenants/{tenant_id}/staging/{request_id}`, 02 미해결 이슈 2 제안)은 **v1에서 채택하지 않는다** — 기본 `max_bytes` 200MB는 로컬 스풀로 충분하고, 콘텐츠 주소 키는 끝까지 읽어야 알 수 있어 스테이징 뒤 서버 측 복사가 한 번 더 필요하기 때문이다. `max_bytes`가 워커 디스크를 넘는 배포가 생기면 재검토한다(미해결 이슈 5).

| 단계 | 동작 | 실패 |
|------|------|------|
| 1 | E16 판정(§3.1) → `ResolvedTarget` | `fetch.scheme_unsupported`, `fetch.egress_denied` |
| 2 | 조건부 요청 판단(§7.2): 이전 `SourceDocument`(`ctx.lineage`)의 검증자가 있으면 조건부 헤더 부착 | — |
| 3 | 응답 헤더 검사: `Content-Length > max_bytes`면 본문 미수신 종료; 304면 §7.2로 분기 | `fetch.too_large` |
| 4 | 스트리밍: 청크마다 `hasher.update`, `spooled += len`, `spooled > max_bytes`면 즉시 중단·스풀 삭제; `ctx.cancelled`면 중단·스풀 삭제(§9.3) | `fetch.too_large` / 취소 |
| 5 | 완료: `content_hash = hasher.hexdigest()`, `size_bytes = spooled`; `checksum_hint`(제안, §5.2)가 있으면 대조 | (`fetch.checksum_mismatch` 제안) |
| 6 | (옵션) 악성 스캔 훅(§5.3): 스풀을 `clamd`에 스트리밍 | (`fetch.malware_detected` 제안) |
| 7 | `ctx.artifacts.put_source(spool, media_type=…)` → `tenants/{tenant_id}/sources/{h[:2]}/{h}`; 동일 키 존재 시 쓰기 생략(`dedup_report.source_bytes_reused=true`) | **코드 없음** — 저장 계층 실패는 `StageError`로 만들지 않고 미분류 예외로 전파해 셸이 재시도 가능으로 취급한다(01-pipeline-framework §10.2; 02 §5 5단계와 동일). `fetch.upstream_error`는 원천 5xx·네트워크 오류 전용(바이블 §4.2·§5.7)이라 쓰지 않는다. 전용 코드 `fetch.store_failed`(**제안**, yes)는 미해결 이슈 6·02 미해결 이슈 7 |
| 8 | read-after-write: 반환 `ArtifactRef.blake3 == content_hash`, `size_bytes` 일치(00 I-3) | `contract.violation` |
| 9 | 스풀 삭제(성공·실패 공통, `finally`) | — |

스풀 디스크 요구량은 `max_bytes × max_concurrent_activities(ingest-io)`(초안: 200MB × 32 ≈ 6.4GB)이며 tmpfs가 아닌 디스크 볼륨을 권고한다([확장과 성능](../09-operations/04-scaling-and-performance.md)). 부분 산출물은 어떤 경로로도 `sources/`에 도달하지 않는다(FR-ING-10).

`blake3` 구현은 Python `blake3` 패키지(Rust 바인딩)를 잠정 사용하며 라이선스·버전은 확인 필요(as of 2026-09; `PluginMeta.license` 기록 대상). 해시 결합 규칙은 바이블 §6.2 "`content_hash`(문서) = `blake3_hex(원본 바이트)` — 라벨 없음"이다.

### 5.2 무결성 힌트 검증(제안)

FR-ING-09(Should)는 "요청자가 기대 해시 또는 크기를 제시한 경우 불일치 시 실패"를 요구하지만 바이블 §5.4 `IngestRequest`에는 대응 필드가 없다. 이 문서는 다음을 **제안**하고 채택 전에는 구현하지 않는다(미해결 이슈 2).

| 제안 항목 | 내용 |
|-----------|------|
| 필드 | `IngestRequest.checksum_hint`(N): `{algorithm: enum[blake3, sha256], value: string(hex)}`, `IngestRequest.expected_size_bytes`(N, integer) |
| 알고리즘 | `blake3`(플랫폼 정본)와 `sha256`(원천 시스템이 흔히 제공). MD5·S3 ETag는 멀티파트에서 콘텐츠 해시가 아니므로 제외(03-data-flow §3.3) |
| 계산 | 스트리밍 중 `blake3`는 항상, `sha256`은 힌트가 있을 때만 병렬 갱신(추가 비용 무시 가능) |
| 판정 | 불일치 → `fetch.checksum_mismatch`(비재시도, 제안 코드) + 스풀 삭제, 산출물 없음. `expected_size_bytes` 불일치도 같은 코드 |
| 304 경로 | 이전 `content_hash`와 `blake3` 힌트를 대조; `sha256` 힌트는 이전 산출물에 값이 없어 검증 불가 → 조건부 요청을 생략하고 전체 다운로드 |
| 기록 | `fetch_report.checksum_verified`(N, boolean; 제안) |

```json
{
  "checksum_hint": {"algorithm": "sha256", "value": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"},
  "expected_size_bytes": 3145728
}
```

### 5.3 악성 스캔 훅(ClamAV 옵션, 제안)

**결정(훅 자리):** 스풀 완료 후·`put_source` 전에 `MalwareScanner` 포트(제안, `security/malware_scanner`)를 호출하는 훅을 둔다. 기본 구현은 `none`(호출 없음)이고, 옵션 구현 `clamd`는 별도 컨테이너의 `clamd`에 `INSTREAM` 프로토콜로 스풀을 스트리밍한다. 감염 바이트는 `sources/`에 저장되지 않는다.

| 항목 | 규칙 |
|------|------|
| 라이선스 경계 | ClamAV는 GPL 계열로 알려져 있어(확인 필요 as of 2026-09) D-02 **C 등급** 취급: 코어 이미지 미포함, 네트워크 API(`clamd` TCP)만, Helm `optIn.clamav`, 업스트림 공식 이미지 참조 링크만 둔다(자체 빌드 없음; 바이블 §6.7 별도 저장소 규칙은 자체 빌드 이미지에 적용) |
| 주소 | `RAG_FETCH__CLAMD__ADDRESS`(서비스 디스커버리 주소; E16 판정 대상 아님) |
| 크기 | `clamd`의 스트림 상한 설정을 `max_bytes` 이상으로 맞춘다(기본값이 작아 초과분이 통과되지 않도록; 값은 확인 필요) |
| 판정 | 양성 → `fetch.malware_detected`(비재시도, **제안 코드**) + 스풀 삭제 + 감사 이벤트 후보(`audit.document.accessed` 재사용 여부는 12 문서 합의); 시그니처 이름은 `StageError.detail`에 남기되 콘텐츠는 금지 |
| 스캐너 불가 | `fail_mode=closed`: `fetch.scanner_unavailable`(재시도, **제안 코드**) → 소진 시 잡 실패; `fail_mode=open`은 개발 프로파일에서만 허용(운영 프로파일에서 `profile.invalid`) |
| 활성 조건 | 두 제안 코드가 바이블 §5.7에 채택되기 전에는 `malware_scan.enabled=true`를 프로파일 검증이 거부한다(코드 없는 오류를 만들 수 없다, 13 I1) |
| 계량 | `rag_ingest_stage_duration_seconds{stage="fetch", outcome="failed"}` + 제안 메트릭 `rag_fetch_malware_detected_total`(§11) |

시그니처 기반 스캔은 문서 포맷 악성(매크로·XXE·zip bomb)의 완전한 방어가 아니다. 그 방어는 파서 샌드박스(NFR-SEC-10, 07 §12.4)가 맡고, 이 훅은 "알려진 악성 파일의 저장 차단"에 한정한다.

### 5.4 저장: 콘텐츠 주소화 원본과 fetch 출력 산출물

| 대상 | 키·규칙 | 근거 |
|------|---------|------|
| 원본 바이트 | `tenants/{tenant_id}/sources/{blake3[:2]}/{blake3}`, `Content-Type = media_type`, 오브젝트 사용자 메타데이터에 URI·콘텐츠 금지. **불변**(같은 키 = 같은 바이트; 덮어쓰기 no-op). 동일 키 존재 시 PUT 생략(HEAD 선행; 경합은 무해). 조건부 PUT(`If-None-Match: *`) 지원은 저장소별 확인 필요 | 바이블 §13.3, ADR-0037, 01-pipeline-framework §7.2 |
| 재사용 범위 | 테넌트 내 공유(다른 문서·컬렉션이 같은 바이트를 가져와도 1회 저장). 테넌트 간 공유 없음(키 접두 `tenants/{tenant_id}/`, E5·E17) | ADR-0037 |
| 보존 | 참조하는 `documents`가 하나라도 있으면 보존; 마지막 참조 삭제 후 30일 유예(`maintenance.cleanup.v1`); 컬렉션 "원본 미보존" 정책(FR-ING-08)은 처리 완료 후 삭제 → 이후 304 재사용 불가(§7.2 (5)) | [저장소 아키텍처](../02-architecture/04-storage-architecture.md) |
| fetch 출력 `SourceDocument` | `stage_key`가 없으므로 셸이 **바이트 해시 키** `tenants/{tenant_id}/artifacts/source-document/{blake3[:2]}/{blake3}.json`에 저장한다(바이블 §13.3 1.3.0, AM-19 채택; 02 미해결 이슈 2의 `fetch_key` 안 대신 이 안을 채택). `ArtifactRef.stage_key` 생략, `artifacts` 행 없음(캐시 없음), `lineage(fetch 출력, IngestRequest 산출물, job_id)` 기록 | 바이블 §4.2·§13.3, 01-pipeline-framework §6.2 |
| 미디어 타입 | 원본: 판정 MIME(fetch 출력은 §6 규칙); 산출물: `application/vnd.rag.source-document+json` | 바이블 §6.4, 00 §9.3 |

---

## 6. 포맷 판별 1차(fetch 출력의 잠정값)

`fetch`는 시그니처(매직 바이트)를 읽지 않는다. 판정은 `detect`(`parser` role `format_detector`, puremagic + ZIP/OLE 스니퍼)의 몫이며 [파싱 라우터와 포맷 판별](./03-parsing-router-and-format-detection.md)이 정본이다. fetch 출력은 하류 라우팅에 쓰이지 않는 **잠정값**만 채운다 — `format`은 `unknown`(또는 아래 표의 힌트), `format_confidence = 0.0`, `media_type`은 잠정값, `container_flags`는 자리표로 **미판정**을 뜻한다(바이블 §4.2 `detect` 행·§5.4 `SourceDocument` 1.3.0, AM-06; 02 §1.2 S-6).

| 필드 | fetch 출력 규칙 |
|------|-----------------|
| `media_type` | (1) HTTP `Content-Type` 타입/서브타입(소문자, 파라미터 제거; `application/octet-stream`이면 무시) → (2) `IngestRequest.media_type_hint`(정규화: `application/vnd.hancom.hwpx → application/hwp+zip`, `text/rtf → application/rtf`) → (3) `application/octet-stream`. 오브젝트 스토리지는 오브젝트 `Content-Type`을 (1)로 본다 |
| `format` | 아래 표의 첫 일치: `media_type_hint` → `Content-Type` → 확장자(`resolved_uri` 경로, 없으면 `Content-Disposition` filename). 어느 것도 아니면 `unknown` |
| `format_confidence` | 항상 `0.0` |
| `container_flags` | `{encrypted: false, distribution: false, compressed: false}` 자리표(`hwp_version` 생략) |
| `http_metadata.charset` | `Content-Type` `charset` 파라미터 원문(소문자) |

| 미디어 타입 신호 | 확장자 신호 | 잠정 `format` |
|------------------|-------------|---------------|
| `application/hwp+zip`, `application/vnd.hancom.hwpx` | `.hwpx` | `hwpx` |
| `application/x-hwp` | `.hwp` | `hwp5`(3.x 여부는 detect가 결정) |
| `application/pdf` | `.pdf` | `pdf` |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx` | `docx` |
| `application/msword` | `.doc` | `doc` |
| `application/rtf`, `text/rtf` | `.rtf` | `rtf` |
| `application/vnd.oasis.opendocument.text` | `.odt` | `odt` |
| `text/html`, `application/xhtml+xml` | `.html`, `.htm` | `html` |
| `text/markdown` | `.md`, `.markdown` | `md` |
| `text/plain` | `.txt` | `txt` |
| `application/json` | `.json` | `json` |
| 그 외 | 그 외 | `unknown` |

힌트와 detect 판정의 불일치는 `detect_report.hint_agrees=false`로 남는다(02 §2.6). fetch·detect에는 경고 코드가 없으므로 `warnings[]`는 항상 빈 배열이고 `quality=full`이다(02 S-11; 경고 코드 제안은 02 미해결 이슈 7).

---

## 7. 조건부 재수집과 중복 감지

### 7.1 이전 `SourceDocument`의 공급(제안)

바이블 §4.2는 "검증자가 있고 같은 `document_id`의 이전 `SourceDocument`가 있으면 조건부 GET"을 요구하지만, `IngestRequest`에는 봉투가 없어 `lineage_refs`로 이전 산출물이 전달되지 않고 스테이지는 원장을 읽을 수 없다(01-pipeline-framework §2.5). **제안:** 스테이지 표의 `fetch` 행에 `requires_lineage = ("SourceDocument",)`를 두되 로드 원천을 입력 봉투가 아니라 **원장의 현재 세대**(`documents.current_commit_id → index_commits.artifact_refs.source`, 즉 현재 committed 세대의 detect 출력)로 지정하는 열(`lineage_source = "ledger_current"`, 제안)을 추가한다. 셸은 (a) 현재 세대가 없거나, (b) 그 `artifact`(원본 오브젝트)가 보존 정책으로 사라졌으면(`exists()` 거짓) `ctx.lineage`에 넣지 않는다. 이렇게 하면 이전 검증자(`http_metadata`)와 `previous_doc_version`(= 그 `doc_version` = `documents.current_doc_version`)이 한 값으로 공급되고, 304 재사용 시 원본 부재를 스테이지가 검사할 필요가 없다(미해결 이슈 3).

### 7.2 조건부 요청 규칙

**결정(바이블 §4.2 정본의 세부):**

1. 조건부 요청은 `ctx.lineage["SourceDocument"]`가 있고 그 `http_metadata.etag` 또는 `.last_modified`가 있을 때만 보낸다. `etag`가 있으면 `If-None-Match`(약한 ETag `W/"…"` 허용), 없으면 `If-Modified-Since`. 두 헤더를 함께 보내지 않는다(RFC 9110은 `If-None-Match` 우선).
2. 검증자가 없으면 **항상 전체 다운로드**한다(리스크 #8 "검증자 없는 원천의 낡은 원본 재사용" 차단). `file://`의 mtime·크기, `smb://`의 수정 시각·크기는 이 문서가 검증자로 인정한다(전체 다운로드 없이 304 동등 판정).
3. 오브젝트 스토리지(`s3`·`gs`·`az`)는 HEAD(`info`)로 ETag를 읽어 이전 값과 같으면 GET을 생략한다(304 동등). 네이티브 조건부 GET을 지원하면 그것을 쓴다(확인 필요; 02 미해결 이슈 11). 멀티파트 ETag는 불투명 검증자로만 쓰고 `content_hash` 대용으로 쓰지 않는다.
4. 304(또는 동등)면 `content_hash`·`doc_version`·`size_bytes`·`artifact`를 이전 `SourceDocument`에서 복사하고 **봉투는 새로 발급**한다(`request_id`·`fetched_at`·`created_at`·`metadata`·`acl`·`producer`는 이번 요청·이번 실행 값). `fetch_report.not_modified=true`, `bytes_per_sec=0`, `http_status=304`(https), `dedup_report.content_unchanged=source_bytes_reused=true`(02 S-13).
5. 304인데 이전 원본 오브젝트가 없으면(§7.1 (b)에서 이미 걸러지지만 경합 대비) 조건부 헤더 없이 **1회 재요청**한다. 오류가 아니다.
6. 조건부 헤더는 모든 홉에 붙인다(3xx 응답은 이를 무시하므로 무해). `checksum_hint`(제안)가 `sha256`이면 조건부 요청을 생략한다(§5.2).
7. 새 응답의 검증자는 이번 `http_metadata`에 기록하고, 다음 수집의 조건부 요청 입력이 된다.

### 7.3 `dedup_report`와 워크플로우 판정

`fetcher`는 판정에 필요한 사실만 기록하고, 결정은 워크플로우가 한다(바이블 §4.2 `fetch` 행은 "동일 `content_hash` 원본이 `sources/`에 있으면 바이트 저장만 생략"까지가 `fetch`의 몫이다).

| `dedup_report` 필드 | 채움 |
|---------------------|------|
| `policy` | `IngestRequest.dedup_policy`가 있으면 그 값, 없으면 바이블 기본 `skip_if_same_hash`. 컬렉션 정책 기본값 해소는 워크플로우 판정 시점의 몫(미해결 이슈 4) |
| `previous_doc_version` | `ctx.lineage["SourceDocument"].doc_version`(없으면 `null`) |
| `content_unchanged` | `content_hash == previous_doc_version` |
| `source_bytes_reused` | `put_source`가 동일 키 존재로 쓰기를 생략했는가(304 포함) |

워크플로우 판정은 [데이터 흐름과 문서 생애주기](../02-architecture/03-data-flow-and-document-lifecycle.md) §3.2 표가 정본이며 요지는 다음과 같다. 워크플로우는 `ArtifactRef`만 받으므로 **제안:** `stage.fetch` 직후 로컬 액티비티 `decide_after_fetch`(06 소유 제안)가 fetch 출력을 로드해 `{content_unchanged, acl_changed, metadata_changed, policy}`만 돌려주고 워크플로우가 분기한다(02 미해결 이슈 10의 답; 미해결 이슈 4).

| `content_unchanged` | `acl_hash`·`metadata_hash` | `policy` | 동작 |
|---|---|---|---|
| false | — | — | `stage.parse`로 계속(`content_hash`가 같은 다른 문서의 파생물·임베딩은 콘텐츠 캐시로 재사용) |
| true | 동일 | `skip_if_same_hash` | **무변경 생략**: 잡 `succeeded`, 새 커밋 없음, `ingest.document.fetched`·`job.state.changed`만 발행 |
| true | `acl_hash` 다름 | `skip_if_same_hash` | payload ACL 갱신 경로(`aclrev:` 힌트 → `update_acl` → `acl.document.updated`), `doc_version` 불변([ADR-0005](../06-adr/0005-doc-version-content-hash-only-and-acl-payload-update.md)) |
| true | `metadata_hash` 다름 | `skip_if_same_hash` | payload 메타 갱신 경로(경로 미정, 03-data-flow 미해결 이슈 18) |
| true | — | `reindex_always` | `parse`~`embed`는 `stage_key` 적중, `index`는 새 세대([ADR-0026](../06-adr/0026-index-commit-generation-saga-and-ledger.md)) |

`fetch`의 `detect`·`parse` 하류 캐시 적중은 `content_hash` 기반 `stage_key` 덕분에 304로 봉투가 새로 발급되어도 유지된다(ADR-0037 중립 1).

---

## 8. 압축 컨테이너(zip) 정책

**결정:** v1 코어의 `fetch`는 컨테이너를 **전개하지 않는다** — "단일 URI = 단일 원본 바이트 = 단일 문서" 불변식을 지킨다. HWPX·DOCX·ODT처럼 ZIP 컨테이너인 **단일 문서**는 컨테이너가 아니라 문서이며 그대로 저장되고 전개는 파서의 몫이다(NFR-SEC-10 압축 해제 상한은 파서 샌드박스가 강제). `IngestRequest.split_hint=zip_members`(열거 `SplitHint`, 바이블 §5.7)는 **v1.1 확장**으로 두고 실현 경로를 아래에 설계해 둔다. 확정 전 v1에서 `split_hint=zip_members` 요청은 API 접수 시 400 `contract.violation`(`errors[].location.pointer=/split_hint`, "이 배포에서 지원하지 않는 값")으로 거부한다(전용 코드 `fetch.container_unsupported`는 제안, 미해결 이슈 6). `json_array`는 파서 라우터의 몫이다(바이블 §7.3 `json: {split: json_array, then: txt}`; [파싱 라우터와 포맷 판별](./03-parsing-router-and-format-detection.md)).

이유: (1) 멤버는 [IngestRequest 계약](../03-contracts/01-ingest-request.md) §5.2가 정한 대로 **별개 문서**(자기 `document_id`·`SourceDocument`·`IndexCommit`)여야 하는데, `document_id`는 API 접수 시 확정되고 멤버 목록은 다운로드 뒤에야 알 수 있어 **자식 잡 생성**이 필요하다 — 이는 스테이지가 아니라 워크플로우·디스패처의 일이다(바이블 §11.2). (2) 자식의 `fetch`가 멤버 바이트를 얻는 경로(부모가 저장한 바이트 재사용 vs 컨테이너 재다운로드)는 계약·컨텍스트 변경을 요구한다. (3) `SourceFormat`에 컨테이너 값이 없어 컨테이너 자체는 `parse`를 거칠 수 없다.

v1.1 설계안(부모 `fetch` 전개 + 워크플로우 자식 잡):

| 단계 | 주체 | 내용 | 필요한 변경 |
|------|------|------|-------------|
| 1 | 부모 `fetch` | 컨테이너를 §3~§5 규칙으로 내려받아 `sources/{blake3}` 저장. ZIP 열람 시 안전 한계: 멤버 ≤ 100(01 §5.2), 펼친 크기 합 ≤ min(원본 × 100, 2GB)(NFR-SEC-10), 멤버 각 ≤ `max_bytes`, 경로 탈출(`..`, 절대 경로) 거부, 중첩 컨테이너 미전개, 암호화 ZIP은 `credentials_ref` 없으면 멤버 미전개. 각 멤버 바이트를 `put_source`(`sources/{member_blake3}`)하고 매니페스트 `{locator, member_blake3, size_bytes, media_type_guess}`를 `put_derived(kind="container_manifest")` | `SourceDocument.container_manifest_ref`(N, `ArtifactRef`) — 02·바이블 §5.4 제안 |
| 2 | 워크플로우 | fetch 출력의 매니페스트를 로컬 액티비티로 읽어 디스패처에 멤버별 자식 `IngestRequest`(`source_uri = {source_uri}#member=zip:{path}`, `external_id`·`acl`·`metadata`·정책 상속) 접수 요청; 상한 초과 멤버는 부모 `partial` + `warnings[]` | 06 워크플로우·디스패처 내부 API; 경고 코드(01 미해결 이슈 5 `parse.member_limit_exceeded` 후보) |
| 3 | 자식 `fetch` | `#member=` 조각을 해석해 매니페스트의 `member_blake3`로 `sources/`의 바이트를 **읽는다**(다운로드 없음) — 스테이지의 테넌트 바인딩 읽기 포트 `ctx.artifacts.get_source(content_hash)`(제안; `sources/`만, 계약 산출물 읽기 불가) | 02-component §2.3 `DerivedArtifacts` 확장 제안 |
| 4 | 부모 잡 | 자식 잡 종료를 집계해 `succeeded`/`partial`/`failed`; `JobStatus`에 자식 목록 노출 | 03-contracts/12 합의 |

---

## 9. 실패 분류·재시도·취소

### 9.1 오류 매핑

어댑터는 벤더 예외를 아래 표의 카탈로그 코드로 바꿔 `StageFailure(stage_error(code, stage="fetch", plugin_id=…))` 하나만 던진다(01-pipeline-framework §10.1). 재시도 여부는 카탈로그(바이블 §5.7)가 정하고 셸은 `StagePolicy`만 적용한다. "제안" 코드는 채택 전 발생시키지 않고 "채택 전 대안" 열의 코드를 쓴다(13 §3.3 규칙).

| 원천 상황(예) | 코드 | 재시도 | 비고 |
|---------------|------|--------|------|
| 스킴은 `allowed_schemes`가 허용했으나 `fetcher` 능력 밖(`input_formats` ∪ `delegates`의 스킴에 없음), 위임 플러그인 미설치 | `fetch.scheme_unsupported` | no | §3.1 (2) — **능력 부재만**. 프로파일 검증이 사전 경고하므로 실행 중 발생은 드물다(05 §5) |
| 스킴 ∉ `allowed_schemes`(프로파일 ∩ 테넌트; 운영 프로파일 `file`, 미옵트인 `http`, 바이블 스킴 목록 밖 스킴), `allowed_hosts`·`allowed_ports` 불일치, 해석 IP ∈ `deny_cidrs`, DNS 리바인딩(검사 후 재해석 차이), 리다이렉트 초과·비허용 목적지·다운그레이드, 허용 목록 밖 `smb` 서버 | `fetch.egress_denied` | no | E16, §3.1 (1)·(3)~(7); 바이블 §5.4 `source_uri` 행·§10.3 E16 "비허용 스킴 → `fetch.egress_denied`"; `rag_egress_denied_total{component="fetch"}` |
| HTTP 401·403·407, 프리사인 만료, S3 `AccessDenied`·`InvalidAccessKeyId`·`SignatureDoesNotMatch`·`ExpiredToken`, GCS 401/403, Azure `AuthenticationFailed`·`AuthorizationFailure`, 익명 접근 거부(§4), `file://` 허용 루트 밖·특수 파일, `credentials_ref` 해소 실패(존재하지 않는 참조) | `fetch.access_denied` | no | 비밀 값·서명은 `detail`에 금지 |
| HTTP 404·410, S3 `NoSuchKey`·`NoSuchBucket`, GCS 404, Azure `BlobNotFound`·`ContainerNotFound`, `file://` 부재·디렉터리, 프리픽스 URI, DNS NXDOMAIN | `fetch.not_found` | no | |
| `Content-Length > max_bytes`, 누적(디코딩 후) `> max_bytes`, 압축 해제 비율 초과 | `fetch.too_large` | no | 스풀 삭제, 산출물 없음 |
| 연결·유휴 읽기·전체 데드라인 초과, HTTP 408 | `fetch.timeout` | yes(5, 지수, 최대 1m) | `fetch_report.attempts`에 반영 |
| **원천**의 HTTP 5xx, 429(`Retry-After`), 그 외 4xx(400·405·406·416 등), S3 `SlowDown`·`InternalError`·`ServiceUnavailable`·`RequestTimeout`, 네트워크 리셋·TLS 핸드셰이크 중단, DNS SERVFAIL·일시 실패, 요청하지 않은 206·길이 불일치·조기 종료 | `fetch.upstream_error` | yes | 원천 5xx·네트워크 오류 전용(바이블 §4.2·§5.7, 13 §3.2). 소진 시 잡 `failed` + `ingest.document.failed` |
| **플랫폼 내부 의존성** 장애: `put_source` 원본 저장 실패(오브젝트 스토리지 5xx·연결 오류), KeyProvider 일시 불가 | (코드 없음) | yes(셸 취급) | `fetch.upstream_error`는 원천 전용이라 쓰지 않는다(02 §5 5단계). 미분류 예외로 전파 → 셸 재시도(01-pipeline-framework §10.2), 소진 시 `last_error`에 예외 타입만. 전용 코드 `fetch.store_failed`(**제안**, yes)는 미해결 이슈 6·02 미해결 이슈 7 |
| TLS 인증서 검증 실패 | `fetch.tls_failed`(**제안**, no) | — | 채택 전 대안 `fetch.upstream_error`(재시도 예산을 쓰는 단점; 미해결 이슈 6) |
| `checksum_hint`·`expected_size_bytes` 불일치 | `fetch.checksum_mismatch`(**제안**, no) | — | 필드 채택과 함께(§5.2) |
| 악성 판정 / 스캐너 불가(`fail_mode=closed`) | `fetch.malware_detected`(**제안**, no) / `fetch.scanner_unavailable`(**제안**, yes) | — | §5.3; 채택 전 훅 비활성 |
| 304인데 이전 원본 부재 | (오류 아님) | — | 조건부 헤더 없이 1회 재요청(§7.2 (5)) |
| 출력 봉투·불변식 위반(S-1~S-16) | `contract.violation` | no | 셸 `validate_out`(500) |
| 미분류 예외(라이브러리 버그 등) | (코드 없음) | yes(셸 취급) | 소진 시 `last_error`에 예외 타입만(01-pipeline-framework §10.2) |

```json
{
  "code": "fetch.egress_denied",
  "type": "urn:rag:error:fetch.egress_denied",
  "retryable": false,
  "stage": "fetch",
  "plugin_id": "fetcher.fsspec_httpx",
  "detail": "redirect hop 2 resolved to an address inside deny_cidrs (169.254.0.0/16); host and query omitted",
  "artifact_ref": {
    "uri": "s3://rag-artifacts/tenants/01J9ZQ4K7X2M8N3P5R6S7T8V9W/artifacts/ingest-request/3a/3a7f1c9e0b2d4f6a8c1e3b5d7f9a0c2e4b6d8f1a3c5e7b9d0f2a4c6e8b1d3f5a.json",
    "blake3": "3a7f1c9e0b2d4f6a8c1e3b5d7f9a0c2e4b6d8f1a3c5e7b9d0f2a4c6e8b1d3f5a",
    "media_type": "application/vnd.rag.ingest-request+json",
    "schema_type": "IngestRequest",
    "schema_version": "1.0.0",
    "size_bytes": 1842
  }
}
```

### 9.2 재시도·백오프·하트비트

| 항목 | 규칙 | 근거 |
|------|------|------|
| 정책 | `StagePolicy(fetch)`: `max_attempts=5`, `backoff{initial: 1s, coefficient: 2.0, max: 1m}`(`fetch`만 최대 간격 1m), `start_to_close=5m`, `heartbeat=30s` | 바이블 §4.4, 06 §Temporal 매핑 |
| 재시도 단위 | 시도마다 **처음부터**(Range 재개 없음, `resumable=no`). 이전 시도의 스풀은 `finally`에서 삭제되어 있다 | 바이블 §4.4 |
| E16 재검사 | 재시도마다 §3.1 전체를 다시 수행한다(DNS 결과·정책이 바뀔 수 있다) | ADR-0037 "매 수집마다 적용" |
| 하트비트 | 스테이지는 `ctx.heartbeat()`를 부르지 않는다(`supports_resumable=false`). 셸 타이머가 `heartbeat`의 1/3 이하 간격(≤ 10s)으로 liveness를 보낸다. 워커 크래시는 하트비트 타임아웃 → 재시도 가능 분류 | 01-pipeline-framework §11.3 |
| `Retry-After` | 셸 백오프가 우선한다. 원천의 `Retry-After`가 `backoff.max`보다 길면 소진 후 `failed`이고 운영자가 `POST /v1/jobs/{job_id}/retry`로 재개한다 | 바이블 §11.5 |
| 재시도 기록 | `jobs.attempts`, `ingest.document.retried`(셸), `fetch_report.attempts`(성공 시도 번호) | 03-contracts/12 |
| at-least-once | 성공 직후 워커가 죽어 재실행되어도 `put_source`는 동일 키 no-op, 출력 산출물은 바이트 해시 키, `event_ids.stage_event`는 시도 간 불변 → 아웃박스 정확히 한 번 | 01-pipeline-framework §7.3 |

### 9.3 취소와 부분 산출물

취소 시그널은 셸이 `ctx.cancelled=True`로 전달한다. `fetcher`는 청크 경계마다 `ctx.cancelled`를 확인해 스트림을 닫고 스풀을 삭제한 뒤 반환하며(01-pipeline-framework §11.4), `put_source` 이후의 취소는 이미 저장된 원본을 지우지 않는다(콘텐츠 주소 원본은 참조 GC 대상, FR-ING-15의 "부분 산출물 정리"는 스풀에 해당). `deadline_at` 초과는 `queued` 단계에서 `cancelled`로 끝나므로 `fetch`에 도달하지 않는다(바이블 §11.5).

---

## 10. 크기·타임아웃·동시성 정책(값 표)

| 항목 | `standard` 값 | 지위 | 출처 |
|------|---------------|------|------|
| `ingest.fetch.max_bytes` | 209,715,200 (200MB) | 바이블 값 | 바이블 §5.1·§7.3 |
| `EgressPolicy.connect_timeout_ms` | 5,000 | 바이블 값 | 바이블 §5.3 |
| `EgressPolicy.max_redirects` | 3 | 바이블 값 | 바이블 §5.3 |
| `EgressPolicy.allowed_ports` | `[443]`(80 옵트인) | 바이블 값 | 바이블 §5.3 |
| `StagePolicy.start_to_close` / `heartbeat` | 5m / 30s | 바이블 값 | 바이블 §4.4 |
| `StagePolicy.max_attempts` / `backoff.max` | 5 / 1m | 바이블 값 | 바이블 §4.4 |
| `idle_read_timeout_ms` | 30,000 | 초안 목표 | 이 문서 §3.3 |
| `decoded_ratio_max`(전송 압축 해제 비율) | 100 | 초안 목표(NFR-SEC-10 준용) | 이 문서 §3.3 |
| 스트리밍 청크 크기 | 1 MiB | 초안 목표 | 이 문서 §5.1 |
| `per_host_concurrency`(호스트별 동시 연결) | 8 | 초안 목표(제안 설정) | 이 문서 §2.3 |
| `ingest-io` 워커 슬롯 | 32 | 초안 목표 | 06 §큐 |
| 스풀 디스크 | ≥ `max_bytes × 슬롯`(≈ 6.4GB) | 초안 목표 | 이 문서 §5.1 |
| 셸 liveness 하트비트 간격 | ≤ 10s | 프레임워크 규칙(`heartbeat`/3) | 01-pipeline-framework §11.3 |
| zip 전개 한계(v1.1) | 멤버 ≤ 100, 펼친 합 ≤ min(100×, 2GB), 멤버 ≤ `max_bytes` | 01 §5.2·NFR-SEC-10 | §8 |
| 처리량 참고 | 텍스트 PDF 100페이지 < 30s(수집 전체) 중 fetch 몫은 네트워크 지배 | 브리프 §7 | — |

---

## 11. 관측성

| 신호 | 정본 여부 | 내용 |
|------|-----------|------|
| 스팬 `rag.ingest.fetch` | 정본(바이블 §6.5 패턴) | 셸이 연다. 속성 `rag.tenant_id_hash`, `rag.profile_hash`(정본); `rag.plugin_id`, `rag.attempt`(01 제안) |
| 자식 스팬 `rag.fetch.call` | 제안(01-pipeline-framework §9.1 `rag.{stage}.call` 확장; `kind="source"` 추가 제안) | 원천 호출 1회(홉 포함)당 하나. OTel HTTP 속성 `url.scheme`, `server.address`(호스트만), `http.response.status_code`; 쿼리·경로의 서명·`credentials_ref` 값 금지. 콘텐츠 캡처 끔 |
| 메트릭 `rag_ingest_stage_duration_seconds{stage="fetch", outcome, queue="ingest-io"}` | 정본 | 셸 기록. `outcome ∈ {ok, failed}`(fetch는 `degraded`·`partial`·`cache_hit` 없음) |
| 메트릭 `rag_egress_denied_total{component="fetch"}` | 정본 | `EgressGuard`가 증가 |
| 메트릭 `rag_fetch_bytes_total{outcome}` | 정본(바이블 §6.5 1.3.0, AM-41) | 전송량 관측 |
| 메트릭 `rag_fetch_not_modified_total`, `rag_fetch_source_reused_total`, `rag_fetch_redirects_count`, `rag_fetch_malware_detected_total` | **제안**(바이블 §6.5 미등재; 라벨 `scheme` 추가도 제안 — 정본 라벨 집합에 없음) | 304 비율·바이트 재사용률·리다이렉트 분포 관측 |
| 로그 | 정본 필드 `event, level, tenant_id_hash, job_id, trace_id, stage="fetch", code` | 호스트·경로만. 쿼리 문자열·헤더·userinfo·비밀 값·문서 바이트 금지(S-12). `fetch.egress_denied`는 거부 사유 범주(`scheme`, `host`, `port`, `cidr`, `redirect`, `dns_rebind`)를 `detail`에 남긴다 |
| 이벤트 `ingest.document.fetched` | 정본 | `data`: `job_id, document_id, stage=fetch, doc_version, quality, artifact_blake3` + `collection_id, size_bytes, format, warning_count`(03-contracts/12 `IngestStageEventData`; `stage_key` 없음). 03-data-flow가 제안한 `conditional_304`는 12 문서 합의 사항 |
| 잡 진행 | `jobs.stage=fetch`, `progress.unit=stage`; 바이트 진행률은 노출하지 않는다(`resumable=no`) | 바이블 §5.6 |

---

## 12. fetch 출력 `SourceDocument` 채움 규칙과 예시

| 필드 | fetch 출력 값 | 출처 |
|------|---------------|------|
| 봉투 | `schema_version="1.0.0"`, `schema_type="SourceDocument"`, `tenant_id`·`collection_id`(잡 스코프), `producer`(`fetcher.fsspec_httpx`, `plugin_version`, `config_hash`, `image_digest=null`), `quality="full"`, `warnings=[]`, `created_at=ctx.now()`(≥ `fetched_at`), `lineage_refs={}` | 바이블 §5.2, 02 S-9·S-11·S-15 |
| `document_id`, `request_id`, `collection_id` | 접수 시 확정값(`ctx.document_id`, `IngestRequest.request_id`) | 02 S-14 |
| `source_uri` / `resolved_uri` | 요청 원문 / §3.6 | 02 S-10 |
| `artifact`, `content_hash`, `doc_version`, `size_bytes` | `put_source` 결과 또는 304 시 이전 값 복사; `doc_version = content_hash` | 02 S-2·S-3, ADR-0005 |
| `media_type`, `format`, `format_confidence`, `container_flags` | §6 규칙(`format_confidence=0.0`, 자리표) | 02 S-6 |
| `http_metadata` | `etag`, `last_modified`, `charset`(있는 것만) | §3.3·§7.2 |
| `metadata`, `metadata_hash`, `acl`, `acl_hash` | `IngestRequest` 복사, `H("meta", …)`·`H("acl", …)`(값 없는 선택 필드 제거한 `canonical_json`, 02 §3) | 02 S-4 |
| `pii_policy`, `pii_tokenize_mode` | 확정값(요청 > 컬렉션 > 테넌트; 컬렉션·테넌트 기본은 셸이 `ctx`에 제공하는 값이 필요 — 미해결 이슈 4) | 바이블 §5.4 |
| `external_id`, `external_version`, `credentials_ref` | 요청 값 그대로(참조만) | 바이블 §5.4 |
| `fetched_at` | 다운로드 완료(또는 304 확인) 시각 `ctx.now()` | 바이블 §5.4 |
| `fetch_report` | `attempts`(현재 시도 번호), `bytes_per_sec`(304면 0), `redirects`, `http_status`(https만), `conditional_request`, `not_modified`, `duration_ms` | 02 §2.5 |
| `dedup_report` | §7.3 | 02 §2.7 |
| `detect_report` | 없음(detect 출력에만) | 02 §2.6 |

예시 — 국세청 보도자료 PDF의 **fetch 출력**(리다이렉트 1회, 조건부 GET 후 내용 변경). 02-source-document 예시 2의 detect 출력과 같은 잡이며, 차이는 `producer`·`format_confidence`·`container_flags` 자리표·`detect_report` 부재다. `metadata`·`acl`과 그 해시는 02 예시 2와 동일 값이다(ID는 형식 규약을 지키는 플레이스홀더).

```json
{
  "schema_version": "1.0.0",
  "schema_type": "SourceDocument",
  "tenant_id": "01J9ZQ4K7X2M8N3P5R6S7T8V9W",
  "collection_id": "01J9ZQ5C2D3E4F5G6H7J8K9M0N",
  "producer": {"plugin_id": "fetcher.fsspec_httpx", "plugin_version": "1.0.0", "config_hash": "7e3b9a0c1d2e4f5061728394a5b6c7d8e9f0a1b2c3d4e5f60718293a4b5c6d7e", "image_digest": null},
  "quality": "full",
  "warnings": [],
  "created_at": "2026-09-22T09:03:11.240Z",
  "lineage_refs": {},
  "document_id": "01J9ZQ8R2S3T4V5W6X7Y8Z9A0B",
  "request_id": "01J9ZQ8M1N2P3Q4R5S6T7V8W9X",
  "source_uri": "https://www.nts.example.go.kr/press/latest/tax-schedule-2026h2.pdf",
  "resolved_uri": "https://www.nts.example.go.kr/press/2026/09/15/tax-schedule-2026h2.pdf",
  "artifact": {"uri": "s3://rag-artifacts/tenants/01J9ZQ4K7X2M8N3P5R6S7T8V9W/sources/12/12ef37752cc4996419c282b5e691c4508ac6294a6a18eeade2219890653dba30",
               "blake3": "12ef37752cc4996419c282b5e691c4508ac6294a6a18eeade2219890653dba30", "media_type": "application/pdf", "size_bytes": 3145728},
  "content_hash": "12ef37752cc4996419c282b5e691c4508ac6294a6a18eeade2219890653dba30",
  "doc_version": "12ef37752cc4996419c282b5e691c4508ac6294a6a18eeade2219890653dba30",
  "size_bytes": 3145728,
  "media_type": "application/pdf",
  "format": "pdf",
  "format_confidence": 0.0,
  "container_flags": {"encrypted": false, "distribution": false, "compressed": false},
  "http_metadata": {"etag": "W/\"68c7a1f0-300000\"", "last_modified": "Mon, 15 Sep 2026 01:20:00 GMT"},
  "metadata": {"title": "2026년 하반기 세무 일정 안내", "authors": ["국세청 대변인실"], "doc_date": "2026-09-15", "doc_type": "press_release", "department": "국세청 대변인실",
               "language_hint": "ko", "tags": ["보도자료", "세무일정"], "genre": "narrative", "custom": {"press_no": "2026-0915-03", "page_count_hint": 12}},
  "metadata_hash": "0e72e7bfd2098d98ccf52876dbbeb2d9aedd3a19488ecb72c4eaf6ed23a132b7",
  "acl": {"allow_principals": ["tenant:*"], "visibility": "public", "classification": "public"},
  "acl_hash": "e7b219f54219ad7b9ec8ac12d2aefc00bc171ef78545665c2ce36839e501c23c",
  "pii_policy": "tokenize",
  "pii_tokenize_mode": "encrypt",
  "external_id": "nts-press-2026-0915-03",
  "external_version": "W/\"68c7a1f0-300000\"",
  "fetched_at": "2026-09-22T09:03:11.207Z",
  "fetch_report": {"attempts": 2, "bytes_per_sec": 12582912.0, "redirects": 1, "http_status": 200, "conditional_request": true, "not_modified": false, "duration_ms": 412},
  "dedup_report": {"policy": "skip_if_same_hash", "previous_doc_version": "b803834df454c7767db9932d9fe3040c5deabb9016c5b45bb3c394f058f61414", "content_unchanged": false, "source_bytes_reused": false}
}
```

---

## 13. 테스트와 적합성

| 수단 | 내용 | 근거 |
|------|------|------|
| E16 계약 테스트(`tests/security`) | `169.254.169.254`, RFC1918 3대역, `localhost`·`127.0.0.1`·`::1`, `0.0.0.0`, 링크로컬 IPv6, 공개 이름 → 사설 IP 해석(DNS 리바인딩 모의), `https` → `http://169.254.169.254` 302, 4번째 리다이렉트, `https → http` 다운그레이드, 운영 프로파일 `file://`, `http` 미옵트인, 비허용 포트, 허용 목록 밖 `smb` 서버 — 모두 1회 시도로 거부 코드 + `rag_egress_denied_total{component="fetch"}` 증가, 재시도 0 | ADR-0038 준수 확인 |
| 운영자 엔드포인트 예외 | 사설 대역의 `s3://` 운영자 엔드포인트는 통과하고, 같은 대역의 프리사인 `https://`는 거부된다(§3.2) | 이 문서 |
| `fetch` 계약 테스트 | 셸이 `fetch`에 대해 `artifacts`를 조회하지 않는다; 검증자 없는 원천에 조건부 헤더를 보내지 않는다; 검증자 있고 이전 `SourceDocument`가 있으면 조건부 GET → 304 시 바이트 재사용·봉투 신규; 동일 `content_hash`면 `sources/` PUT 생략; 모든 경로에서 `EgressGuard.check` 호출 | ADR-0037 준수 확인 |
| 크기·시간 | `Content-Length > max_bytes` 본문 미수신; 길이 없는 스트림 `max_bytes + 1` 바이트에서 중단·스풀 부재; 압축 해제 비율 초과; 유휴 30s 초과 → `fetch.timeout`; 5회 소진 → `failed` + `ingest.document.failed` | FR-ING-10 |
| 무결성 | 같은 바이트를 두 번 받으면 같은 `content_hash`·같은 `sources/` 키(적합성 `idempotency` fetch 변형); `Content-Encoding: gzip` 유무에 관계없이 같은 `content_hash` | 원칙 4 |
| 비밀 | 로그·스팬·`StageError.detail`·`fetch_report`·`resolved_uri`에 `Authorization` 값·서명 쿼리·`credentials_ref` 해소 값이 없다(적합성 `security_invariants` 확장) | S-12, E13 |
| 주변 자격 증명 | `allow_ambient_credentials=false`에서 `credentials_ref` 없는 `s3://`는 익명으로만 시도된다(SDK 세션에 환경 자격 증명 미주입) | §4 |
| 골든 회귀 | 기록형 HTTP 클라이언트(카세트)로 200·304·3xx 체인·429·5xx·조기 종료 시나리오를 재생해 `SourceDocument` 정규화 해시(`created_at`·`producer`·`lineage_refs`·`fetched_at`·`fetch_report.duration_ms`·`bytes_per_sec` 제외) 비교 | 01-pipeline-framework §12.2(제외 집합 확장은 미해결 이슈 8) |

---

## 결정 사항 요약

- **결정:** `fetch`는 캐시 없는 단일 URI 풀 스테이지다 — 항상 실행, `EgressPolicy`(E16) 매회 적용, 검증자(`etag`|`last_modified`)가 있을 때만 조건부 GET, 304면 바이트 재사용 + 봉투 신규, 동일 `content_hash`면 `sources/` 저장만 생략([ADR-0037](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md), [ADR-0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md)).
- **결정:** 코어 플러그인은 `fetcher.fsspec_httpx` 하나이며 스킴별 어댑터(`https`·`http`·`s3`·`gs`·`az`·`file`)를 내부 분기한다; `smb`는 플러그인이 `delegates`(제안)로 붙는다. 라이브러리 선택은 잠정이며 §2.4 기준으로 조사한다([ADR-0032](../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md)).
- **결정:** E16의 CIDR·고정 연결·리다이렉트 판정은 테넌트 입력이 목적지를 정하는 `http(s)`에 전체 적용하고, `s3`·`gs`·`az`는 운영자 설정 엔드포인트를 서비스 디스커버리 주소로 간주해 스킴·`allowed_hosts`만 판정한다(BYO endpoint v1 미지원). `deny_cidrs` 축소 불가는 유지된다(ADR-0038 재검토 조건 2의 답).
- **결정:** `http(s)`는 단일 리소스 GET이다 — robots.txt 무시, 자동 리다이렉트 끔·홉마다 재검사·다운그레이드 금지, TLS 항상 검증, 크기 상한은 디코딩 후 바이트에 스트림 도중 강제, `content_hash`는 전송 압축을 푼 표현 바이트.
- **결정:** 비밀은 `credentials_ref`로만 다루고 팩토리가 KeyProvider로 해소한다; 워커 주변 자격 증명은 기본 금지(`allow_ambient_credentials=false`), `file://`은 `orchestrator=local` + 허용 루트 안에서만([ADR-0027](../06-adr/0027-security-context-injection-and-acl-enforcement-points.md)).
- **결정:** 원본은 로컬 스풀 + BLAKE3 증분 해시로 받아 `tenants/{tenant_id}/sources/{blake3}`에 불변 저장하고(멀티파트 스테이징 v1 미채택), fetch 출력 `SourceDocument`(캐시 제외 스테이지)는 바이트 해시 키 `tenants/{tenant_id}/artifacts/source-document/{blake3[:2]}/{blake3}.json`으로 저장한다(바이블 §13.3 1.3.0, AM-19).
- **결정:** `fetch`는 시그니처를 읽지 않으며 `format`은 힌트·확장자 기반 잠정값(`format_confidence=0.0`), `media_type`·`container_flags`도 잠정값(미판정), 판정은 `detect`가 한다(바이블 §4.2·§5.4 1.3.0, AM-06).
- **결정:** `dedup_report`는 사실 기록이고 무변경 생략·payload 갱신·계속의 결정은 워크플로우가 한다(`decide_after_fetch` 로컬 액티비티 제안; [ADR-0005](../06-adr/0005-doc-version-content-hash-only-and-acl-payload-update.md), [ADR-0026](../06-adr/0026-index-commit-generation-saga-and-ledger.md)).
- **결정:** v1 `fetch`는 컨테이너를 전개하지 않는다(단일 URI = 단일 문서). `split_hint=zip_members`는 v1.1 확장이며 §8 설계안(부모 전개 + 자식 잡 + `sources/` 재사용)과 안전 한계를 따른다.
- **결정:** 악성 스캔은 `put_source` 전 훅(`MalwareScanner`, 기본 `none`; `clamd` 옵션은 C 등급 분리 컨테이너)이며 전용 오류 코드 채택 전에는 활성화되지 않는다. 무결성 힌트(`checksum_hint`)도 필드·코드 채택이 선행한다.
- **결정:** 오류는 바이블 §5.7 `fetch.*` 7종에 §9.1 표대로 매핑하고 재시도 여부는 카탈로그가 정한다 — 스킴 거부는 "누가 막았는가"로 갈리고(정책 → `fetch.egress_denied`, 능력 부재 → `fetch.scheme_unsupported`), `put_source` 등 플랫폼 내부 의존성 장애는 코드 없이 셸 재시도로 처리한다(`fetch.upstream_error`는 원천 전용); 스테이지는 재시도·대기·하트비트를 직접 하지 않는다([ADR-0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md), [ADR-0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md)).

## 미해결 이슈

| # | 이슈 | 제안 |
|---|------|------|
| 1 | **E16 적용 범위(§3.2)**: `s3`·`gs`·`az` 운영자 엔드포인트를 서비스 디스커버리 주소로 간주해 `deny_cidrs` 판정에서 제외하고 `smb` 서버 허용 목록을 같은 부류로 둔 것은 ADR-0038 중립 2·재검토 조건 2의 답이다 | ADR-0038 patch(결정 절에 스킴별 판정 대상 표 추가), 바이블 §10.3 E16 문구에 "테넌트 제어 목적지" 정의 명시(patch); BYO endpoint 도입 시 별도 ADR |
| 2 | **무결성 힌트(§5.2)**: FR-ING-09가 요구하나 바이블 §5.4에 필드가 없다 | `IngestRequest.checksum_hint{algorithm: enum[blake3, sha256], value}`·`expected_size_bytes`(N), `fetch_report.checksum_verified`(N), 오류 `fetch.checksum_mismatch`(no) — ADR minor로 바이블 §5.4·§5.7·`common-types` 개정; 01·02 문서 스키마 갱신 |
| 3 | **이전 `SourceDocument` 공급(§7.1)**: 조건부 GET·`previous_doc_version`에 필요한 이전 산출물을 스테이지가 얻는 경로가 프레임워크에 없다 | 스테이지 표 `fetch` 행 `requires_lineage=("SourceDocument",)` + 새 열 `lineage_source="ledger_current"`(원장 현재 세대 source, 원본 존재 확인 포함) — 01-pipeline-framework §2.2·§5.2, 06 셸 patch; 바이블 §4.1 `requires_lineage` 문구("`index`만 사용") 개정(minor) |
| 4 | **fetch 뒤 판정 기계(§7.3)**: 워크플로우는 `ArtifactRef`만 받으므로 `dedup_report`를 읽을 수 없다; `pii_policy` 확정값(컬렉션·테넌트 기본)과 `dedup_report.policy`의 컬렉션 기본 해소도 스테이지 밖 정보다 | 06에 로컬 액티비티 `decide_after_fetch`(fetch 출력 로드 → `{content_unchanged, acl_changed, metadata_changed, policy}`) 신설; 셸이 `build_stage_context`에서 컬렉션·테넌트 정책 해소값(`pii_policy`, `dedup_policy` 기본)을 `ctx`에 제공하는 멤버(제안 `ctx.policies`) 또는 API 접수 시 확정값을 `IngestRequest` 산출물에 채우는 방식 중 택1(01 §6 "기본값은 채우지 않는다"와 조정). 02 미해결 이슈 10의 답 |
| 5 | **스풀 vs 멀티파트 스테이징(§5.1)**: v1은 로컬 스풀만이다. `max_bytes`가 워커 디스크를 넘는 배포(대형 스캔 PDF 묶음)가 생기면 재검토 | 02 미해결 이슈 2의 `tenants/{tenant_id}/staging/{request_id}` 키를 바이블 §13.3에 예약(patch)하되 구현은 보류; 조건부 PUT 지원은 RustFS·SeaweedFS·`file://`별 확인 필요(as of 2026-09) |
| 6 | **제안 오류 코드**: `fetch.tls_failed`(no), `fetch.checksum_mismatch`(no), `fetch.malware_detected`(no), `fetch.scanner_unavailable`(yes), `fetch.container_unsupported`(no), `fetch.store_failed`(yes; `put_source` 원본 저장 실패 — 02 미해결 이슈 7과 같은 이름) — 채택 전 대안은 §9.1·§8·§5.1(저장 실패는 코드 없이 셸 재시도) | 13-error-model §3.3 표에 02 미해결 이슈 7과 공동 등재 후 ADR minor(바이블 §5.7·`ErrorCodeCatalog`); `fetch.tls_failed`는 재시도 예산 낭비를 막고 `fetch.store_failed`는 `last_error`에 코드가 남게 하므로 조기 채택 권고 |
| 7 | **악성 스캔 훅(§5.3)**: `MalwareScanner` 포트·`RAG_FETCH__CLAMD__ADDRESS`·Helm `optIn.clamav`는 바이블 §12·배포 매니페스트 미등재; ClamAV 라이선스·`clamd` 스트림 상한 기본값은 확인 필요(as of 2026-09) | 07-tech-landscape/12 보완 조사 → ADR-0001 등급표 적용 확인 → 바이블 §12 `security/malware_scanner` 등재(minor); 09-operations/05·01에 컨테이너·NetworkPolicy 규칙 |
| 8 | **관측 제안(§11)**: `rag_fetch_bytes_total`은 해소(바이블 §6.5 1.3.0, AM-41). 남은 제안: `rag.fetch.call(kind="source")`, `rag_fetch_not_modified_total`, `rag_fetch_source_reused_total`, `rag_fetch_redirects_count`, `rag_fetch_malware_detected_total`, 라벨 `scheme`; 골든 정규화 제외 집합에 `fetched_at`·`fetch_report.duration_ms`·`bytes_per_sec` 추가 | 09-operations/03과 합의 후 ADR-0022 minor(바이블 §6.5); 01-pipeline-framework 미해결 이슈 9·11과 공동 |
| 9 | **`sftp://`와 `smb` 플러그인 명명(§2.2·§3.5)**: `sftp`는 바이블 스킴 목록에 없다; `smb` 플러그인 패키지명이 01(`rag-plugin-smb`)과 05(`rag-plugin-smb-fetcher`, `fetcher.smbprotocol`)에서 다르다 | 05 §미해결 이슈 8과 함께 `rag-plugin-smb-fetcher` / `fetcher.smbprotocol`로 통일(01 patch); `sftp`는 수요 확인 후 바이블 §5.4 `source_uri` 스킴 목록 개정(minor) |
| 10 | **fetch 출력 산출물 키(§5.4) — 해소.** 바이트 해시 키 `artifacts/source-document/{blake3[:2]}/{blake3}.json`(바이블 §13.3 1.3.0, AM-19). 02 미해결 이슈 2의 `fetch_key` 안과 다르므로 02 문서 §11 표 갱신 필요 | 바이블 §13.3 1.3.0 AM-19 |
| 11 | **조건부 GET 스킴별 지원(§7.2 (3))**: `gs`·`az` 네이티브 조건 헤더, fsspec 계열의 ETag 노출·`IfNoneMatch` 전달 여부 확인 필요(as of 2026-09) | §2.4 조사 항목 3으로 확정; 미지원 스킴은 HEAD 비교로 통일(현 규칙) |
| 12 | **`resolve_pin` 실현(§2.4 기준 5)**: httpx/httpcore의 `sni_hostname` 요청 확장으로 "해석 IP 연결 + 원 호스트명 SNI/`Host`"가 성립하는지 확인 필요(as of 2026-09) | 불가하면 ADR-0038 재검토 조건 1(전용 egress 프록시 또는 자체 전송 계층) |
| 13 | **zip 컨테이너(§8)**: `SourceDocument.container_manifest_ref`(N), `ctx.artifacts.get_source(content_hash)`(테넌트 바인딩 읽기, `sources/`만), 06 자식 잡 생성 액티비티, 부모 잡 집계 규칙, 경고 코드(`parse.member_limit_exceeded` 후보) | v1.1 ADR 1건으로 묶어 발의; 채택 전 `zip_members`는 접수 거부. `json_array`의 "멤버 = 별개 문서"(01 §5.2)와 라우터 내부 분할(바이블 §7.3)의 긴장은 03 문서가 해소 |
| 14 | **`allowed_hosts`의 오브젝트 스토리지 의미(§3.2)**: URI authority(버킷·컨테이너)에 적용한다고 정했으나 15 §8은 "호스트명"으로만 서술한다 | 15 문서 `allowed_hosts` 행에 "오브젝트 스토리지 스킴은 authority(버킷·컨테이너)에 적용" 명시(patch) |
| 15 | **`ingest.document.fetched` 확장 키**: 03-data-flow가 제안한 `conditional_304`와 이 문서의 `not_modified`·`source_bytes_reused` 관측 요구 | 03-contracts/12 `IngestStageEventData` 선택 키로 `not_modified`(boolean) 추가 제안(minor); `data`에 URI는 넣지 않는다(E12) |
| 16 | **서명 쿼리 키 목록의 정본 이관(§3.6) — 해소(바이블 §5.3 1.3.0, AM-30).** `EgressPolicy.strip_query_keys` 등재로 이 문서 §3.6 표가 기본값 정본, 02 상수는 로드처가 됐다. `X-Goog-Credential`(서비스 계정 이메일)을 남기는 현 규칙의 개인정보 재검토만 남음 | 02 상수가 §3.6 표를 로드하도록 전환(02 minor); `X-Goog-Credential` 제거 여부는 02와 함께 결정 |
| 17 | **`put_source` 스트리밍 오버로드(§1.3·§2.1·§5.1)**: `DerivedArtifacts.put_source(data: bytes, *, media_type)`(02-component §2.3, 01-pipeline-framework §6.2)는 바이트만 받아 200MB 스풀을 메모리에 올려야 한다 | 파일 경로(또는 비동기 바이트 스트림)와 사전 계산 `blake3`를 받는 오버로드 `put_source(path_or_stream, *, media_type, blake3)`를 02-component §2.3 `DerivedArtifacts`·01 §6.2 포트 표·바이블 §12 `sdk/`에 추가(patch); 포트는 반환 `ArtifactRef.blake3 == blake3`를 검증(00 I-3, §5.1 8단계) |
| 18 | **스킴 오류 코드 설명 불일치(§3.1)**: 13-error-model §3.2 `fetch.scheme_unsupported` 설명("`allowed_schemes` 밖 또는 플러그인 부재")과 02-source-document §7 표("스킴 미허용 → `fetch.scheme_unsupported`")가 정책 거부까지 이 코드에 넣어 바이블 §5.4 `source_uri` 행·§10.3 E16("비허용 스킴 → `fetch.egress_denied`")과 어긋난다 | 13 §3.2 설명을 "정책은 허용했으나 `fetcher` 능력(`input_formats`·`delegates`) 밖"으로, 02 §7 표의 "스킴 미허용" 행을 `fetch.egress_denied`로 patch; 15 §8은 바이블과 같아 현행 유지. 이 문서 §3.1 결정이 두 앵커를 모두 만족하는 단일 규칙 |
| 19 | **`FetchConfig` 비예약 키의 등재(§2.3)**: `idle_read_timeout_ms`·`decoded_ratio_max`·`allow_ambient_credentials`·`per_host_concurrency`·`malware_scan`·`delegates`는 바이블 §7.3 `ingest.fetch`(`plugin`·`max_bytes`·`policy`)와 15 문서 프로파일 스키마(`profile.schema.json`, 15 소유)에 없다 | 15 프로파일 스키마의 `ingest.fetch`에 "예약 키 외 나머지는 플러그인 `config_schema`로 위임"을 명시(01 §2.3 규칙의 스키마 표현)하고, 바이블 §7.3 YAML 주석에 비예약 키 예시를 추가(patch); 등재 전까지 이 키들은 코어 플러그인 `fetcher.fsspec_httpx`의 설정으로만 취급하고 프로파일 계약으로 부르지 않는다 |
| 20 | **캐시 제외 스테이지의 결정성 등급(§1.1)**: 01-pipeline-framework §8.1의 세 등급(`pure`/`model_pinned`/`generative`)은 캐시 키 규칙을 전제하므로 `CACHE_EXEMPT`인 `fetch`·`index`에 맞지 않는다 | `Capabilities.extra.determinism`(N)에 네 번째 값 `external`(출력이 외부 상태에 의존, 캐시 없음, 적합성은 `idempotency`만)을 추가하거나 `CACHE_EXEMPT` 스테이지는 `determinism` 생략을 허용 — 01 미해결 이슈 8·03-contracts/15 `capabilities.schema.json`과 공동 제안 |

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) — §2 R1(풀 모델·URI 스킴), §3 원칙 3·4·9, §4 D-06·D-08·D-09·D-10·D-14·D-17, §6 비목표(크롤러), §7 보안·처리량, §9 문서 규약
- [설계 바이블](../02-architecture/00-design-bible.md) — §1 우선순위·변경 절차, §3.1 D-06·D-08·D-09, §3.3 ADR-0037·0038, §4.1 공통 규약(캐시·오류 모델), §4.2 `fetch`·`detect` 행, §4.4 `fetch` 정책, §5.1 인벤토리(`SourceDocument`·`EgressPolicy`), §5.3 `ArtifactRef`·`Producer`·`StageError`·`EgressPolicy`·`Capabilities`, §5.4 `IngestRequest`·`SourceDocument`, §5.7 `SourceFormat`·`DedupPolicy`·`SplitHint`·이벤트·오류 카탈로그, §6.1~6.6 명명·해시·메트릭·환경 변수, §7.3 `ingest.fetch`·`runtime.egress`, §7.4 (12), §10.3 E5·E16·E17, §11.2~11.5, §12 모듈 맵, §13.1·§13.3, §15 리스크 #3·#8, 미해결 이슈 5
- [기술 지형 종합: 선정 매트릭스](../07-tech-landscape/00-summary-and-selection-matrix.md) — `uri_fetcher` 행(연구 공백·잠정 권고), `format_detector` 행, 미해결 이슈 1
- [기능 요구사항](../01-requirements/01-functional-requirements.md) — FR-ING-01·02·05·08·09·10·15·16, FR-SEC-06·09; [비기능 요구사항](../01-requirements/02-non-functional-requirements.md) — NFR-SEC-06·10
- [컴포넌트 아키텍처](../02-architecture/02-component-architecture.md) — §2.3 `RuntimeServices`·`EgressGuard`·`DerivedArtifacts`, §2.4 `fetcher` 행, §6 오류 경계
- [데이터 흐름과 문서 생애주기](../02-architecture/03-data-flow-and-document-lifecycle.md) — §3.2 재제출 판정 표, §3.3 조건부 재수집 규칙, §4 부분 재처리
- [저장소 아키텍처](../02-architecture/04-storage-architecture.md) — `sources/` 보존·GC, 파생물 색인
- [플러그인 아키텍처](../02-architecture/05-plugin-architecture.md) — §2.4 오류 계약, §3.2 `fetcher`, §5 `Capabilities` 확장 키, §7 격리, 미해결 이슈 8
- [오케스트레이션과 워크플로우](../02-architecture/06-orchestration-and-workflows.md) — `ingest.document.v1`, `CACHE_EXEMPT`, `StageActivityInput`, 큐·슬롯
- [멀티테넌시·보안 아키텍처](../02-architecture/07-multi-tenancy-and-security-architecture.md) — §비밀 관리(`KeyProvider`, `credentials_ref`), §12.4 파서 샌드박스, 미해결 이슈 21
- [계약 개요와 공통 규약](../03-contracts/00-contract-overview.md) — §2 인벤토리·소유, §4.1 `ArtifactRef`, §4.10 `StageError`, §4.23 `EgressPolicy`, §7 `H()`, §9 산출물 저장, §10 검증 지점
- [IngestRequest 계약](../03-contracts/01-ingest-request.md) — §5 `dedup_policy`·`split_hint`, §8 스킴 허용목록·`EgressPolicy`·`credentials_ref`, 미해결 이슈 5·6
- [SourceDocument 계약](../03-contracts/02-source-document.md) — §1.2 두 인스턴스, §2.5 `fetch_report`, §2.7 `dedup_report`, §5 저장·스트리밍 해시, §6 중복 감지, §7 조건부 재수집, 불변식 S-1~S-16, 미해결 이슈 2·3·10·11
- [잡·이벤트·상태 계약](../03-contracts/12-jobs-events-and-status.md) — `ingest.document.fetched` `IngestStageEventData`
- [오류 모델](../03-contracts/13-error-model.md) — §3.2 `fetch.*` 카탈로그, §3.3 제안 코드 절차
- [컬렉션·프로파일·정책 계약](../03-contracts/15-collection-profile-and-policy-contracts.md) — §8 `EgressPolicy` 합성·판정 순서, P-4·E-1
- [파이프라인 프레임워크](./01-pipeline-framework.md) — §2 `Stage`·순수성, §3 `StageContext`, §5 셸, §6.2 산출물 포트·바이트 해시 키, §7 캐시 제외, §8 결정성, §9 계측, §10 오류, §11 하트비트·취소, §12 테스트
- 하류·인접 문서(문서 맵 경로): [파싱 라우터와 포맷 판별](./03-parsing-router-and-format-detection.md), [갱신·삭제·재색인](./19-update-delete-and-reindexing.md), [수집 API](../05-api/02-ingestion-api.md), [웹훅과 이벤트](../05-api/07-webhooks-and-events.md), [설정 레퍼런스](../09-operations/02-configuration-reference.md), [관측성](../09-operations/03-observability.md), [확장과 성능](../09-operations/04-scaling-and-performance.md), [보안과 컴플라이언스](../09-operations/05-security-and-compliance.md), [플러그인 개발 가이드](../10-development/06-plugin-development-guide.md)
- ADR(바이블 §3.3 번호·slug): [0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md), [0005](../06-adr/0005-doc-version-content-hash-only-and-acl-payload-update.md), [0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md), [0026](../06-adr/0026-index-commit-generation-saga-and-ledger.md), [0027](../06-adr/0027-security-context-injection-and-acl-enforcement-points.md), [0032](../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md), [0037](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md), [0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md)
- 외부 규격: RFC 3986(URI), RFC 9110(HTTP 의미론 — 조건부 요청·검증자·리다이렉트), RFC 9457(Problem Details), BLAKE3, JSON Schema 2020-12
