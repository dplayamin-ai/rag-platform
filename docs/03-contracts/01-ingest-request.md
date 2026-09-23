---
title: IngestRequest 계약
status: active
owner: architecture
version: 0.1.0
last_updated: 2026-09-22
depends_on:
  - ../00-vision/00-design-brief.md
  - ../02-architecture/00-design-bible.md
  - ../02-architecture/04-storage-architecture.md
  - ../07-tech-landscape/00-summary-and-selection-matrix.md
  - ./00-contract-overview.md
  - ./02-source-document.md
  - ./12-jobs-events-and-status.md
  - ./13-error-model.md
schema_version: "1.0.0"
---

# IngestRequest 계약

## 목적

`IngestRequest`는 브리프 R1("수집된 문서의 주소와 메타 정보를 API로 전달받아서")의 직접 구현이자 수집 파이프라인의 첫 계약이다. 클라이언트가 `POST /v1/ingest`(단건) 또는 `POST /v1/ingest/batch`(최대 100건)로 제출하는 문서 위치(URI)·메타데이터·ACL·처리 정책을 하나의 타입으로 확정하고, 그 접수(accept) 규약 — `Idempotency-Key` 멱등성, `request_id`·`document_id` 발급, 202 응답 본문, 문서 단위 잡 직렬화 — 을 함께 정의한다. 필드·필수 여부·열거값은 바이블 §5.4 `IngestRequest` 표를 같은 철자로 옮긴 것이며, 이 문서가 더한 것은 모두 선택(N) 필드 또는 검증 규칙이다(바이블 §1.1, 브리프 §11).

## 범위

- 포함: `IngestRequest` 필드 표(중첩 `metadata`·`metadata.custom`·`callback`·`profile_overrides`는 별도 표), 202 응답 본문(`IngestAccepted`, 배치 `IngestBatchAccepted`), 멱등성(`Idempotency-Key` + `request_id`, 200/409/422, 키 스코프·TTL), `dedup_policy`·`split_hint` 의미, 예약 메타데이터 키와 정규화 규칙(§5.7 `FilterableField` 정합), ACL 입력 규칙(주체 문자열 §6.1, 거부 우선, 문서 단위), URI 스킴 허용목록과 `EgressPolicy`(E16), `credentials_ref`, 검증 규칙·크기 한계(본문 64KB, `metadata` 16KB, 배치 100건), 문서 단위 잡 분할과 같은 `document_id` 직렬화(§11.2), JSON Schema 2020-12 전문(`schemas/ingest-request.schema.json`), Pydantic v2 모델, 예시, 불변식, 산출물 저장 규약, 버전 이력.
- 제외: `SourceDocument` 필드([02-source-document](02-source-document.md)), `JobStatus`·SSE·CloudEvents 페이로드([12-jobs-events-and-status](12-jobs-events-and-status.md)), 오류 코드 카탈로그 해설([13-error-model](13-error-model.md)), `Acl`·`EgressPolicy`·`CollectionSpec`·`Profile` 필드([00-contract-overview](00-contract-overview.md) §4.4·§4.23, [15-collection-profile-and-policy-contracts](15-collection-profile-and-policy-contracts.md)), 스킴별 `fetcher` 어댑터 구현([../04-pipelines/02-fetching-and-source-resolution.md](../04-pipelines/02-fetching-and-source-resolution.md)), OpenAPI 전문([../05-api/02-ingestion-api.md](../05-api/02-ingestion-api.md)), 요청 단위 `dry_run`(검증·`document_id` 확정만 수행하고 잡을 만들지 않는 모드 — 브리프·바이블 §14에 없고 응답 상태·본문(200 `IngestDryRunResult`)이 엔드포인트 의미를 바꾸므로 이 문서는 필드·예시를 두지 않는다; 미해결 이슈 9).
- 정본 관계: 공용 타입(`Acl`)과 열거(`PiiPolicy`, `PiiTokenizeMode`, `DedupPolicy`, `SplitHint`, `Genre`, `EventType`)는 `urn:rag:schema:common-types:1`의 `$defs`를 `$ref`로 참조하고 재정의하지 않는다(00 §2 소유 규칙). null·생략·확장·직렬화 규칙은 00 §8, 오류 코드는 13을 따른다.

## 1. 위치와 접수 흐름

`IngestRequest`는 봉투(Envelope)를 갖지 않는 클라이언트 입력 계약이다. 봉투 필드 중 `schema_version`·`collection_id`만 있고 `schema_type`·`tenant_id`·`producer`·`quality`·`warnings`·`created_at`·`lineage_refs`는 없다(00 §3.1). `tenant_id`는 인증 토큰에서 도출된 `SecurityContext`가 나르며 본문에 오면 **422**로 거부한다(E1, 00 §10.1; 코드는 §3.3). 접수 순서는 고정이다: (1) `request_id` 발급, (2) 값 정규화(§6) 후 스키마·불변식 검증, (3) `document_id` 조회·발급(§10), (4) 정규화된 인스턴스를 산출물로 저장(read-after-write 검증), (5) `jobs`·`idempotency_keys`·`documents`·`artifacts`를 **한 트랜잭션**으로 커밋, (6) 디스패처 큐잉. 오케스트레이터에는 `ArtifactRef`만 넘긴다(바이블 §4.1, §11.1 `pipelines.ingest.run(ctx, req_ref, profile)`; 산출물 저장 규약 절). 생산·소비(바이블 §5.1): 생산 = 클라이언트, 소비 = `fetch`(입력 계약)·API(접수·저장).

```mermaid
sequenceDiagram
    participant C as 클라이언트
    participant A as api
    participant P as PostgreSQL(jobs·idempotency_keys·documents·artifacts)
    participant O as Object Storage
    participant W as 디스패처 / Temporal
    C->>A: POST /v1/ingest (Idempotency-Key, IngestRequest 본문)
    A->>A: E1 인증·E2 인가(collection ingest)·E3 레이트리밋
    A->>A: 보안 필드 존재 거부(422)·readOnly 존재 거부(400) → request_id 발급 → 값 정규화(§6) → 스키마·불변식 검증
    A->>P: idempotency_keys(tenant_id, key) 조회 (Valkey idem: 캐시 우선, 새 키는 idem: 예약)
    alt 새 키
        A->>P: document_id 조회·발급(external_id or source_uri, §10)
        A->>O: put IngestRequest 산출물(read-after-write 검증) → ArtifactRef (실패 시 503, 접수 없음)
        A->>P: INSERT documents(신규 시) · INSERT jobs(queued) · INSERT idempotency_keys(request_hash, job_id) · INSERT artifacts — 동일 트랜잭션
        A->>W: 디스패처 큐잉(문서 직렬화·테넌트 동시성) → ingest.document.v1 시작
        A-->>C: 202 IngestAccepted {job_id, status_url, events_url, request_id?, document_id?}
    else 같은 키·같은 request_hash(커밋 완료)
        A-->>C: 200 동일 본문(재생)
    else 같은 키·다른 request_hash
        A-->>C: 422 api.idempotency_payload_mismatch
    else 같은 키·접수 트랜잭션 진행 중
        A-->>C: 409 api.idempotency_conflict (+ instance)
    end
```

## 2. 필드 정의

타입 표기는 브리프 §9.5. "필수" 열은 바이블 §5.4의 `Y`/`N`/조건을 그대로 쓴다. `N` 필드는 값이 없으면 **키를 생략**한다(`null` 금지, 00 §8.1). `조건`은 스키마 `dependentRequired`·`if/then`으로 표현했다.

**결정:** 값 정규화(§6: NFC·trim·공백 축약·순서 보존 중복 제거·BCP 47 대소문자)는 **스키마 검증 전**에 수행한다. 따라서 아래 표와 스키마의 `uniqueItems`·소문자 패턴·길이 상한은 **정규화된 저장 인스턴스**에 대한 제약이며, 정규화 후에도 남는 형식 위반(빈 문자열, `doc_type` 대문자, 스키마 밖 키 등)이 400 `contract.violation`이다. 예: `tags: ["기록물", "기록물 "]`는 정규화 후 `["기록물"]`로 접수되고, `language_hint: "KO-kr"`는 `ko-KR`로 접수된다. 멱등 지문 `request_hash`(§4)는 정규화 **전** 전송 본문으로 계산하므로 이 규칙과 무관하다.

### 2.1 `IngestRequest`(바이블 §5.4)

| 필드 | 타입 | 필수 | 설명 | 예시 |
|------|------|------|------|------|
| `schema_version` | string(semver) | Y | `"1.0.0"`. 이 스키마(`$id` major 1)는 `1.x`만 수용(패턴) | `"1.0.0"` |
| `request_id` | string(ulid) | Y | **서버 발급**(접수 시). 스키마 `readOnly`; 클라이언트 본문에 있으면 400 `contract.violation`(pointer `/request_id`, 00 §10.1). 202 응답에 `IngestAccepted.request_id`(N, §3.1)로 `job_id`와 함께 반환 | `"01J9ZQ7B8C9D0E1F2G3H4J5K6M"` |
| `collection_id` | string(ulid) | Y | 프로파일이 고정된 컬렉션. Cedar `allowed_collections` 밖이면 403 `auth.forbidden`(존재 비노출, E2) | `"01J9ZQ5A1B2C3D4E5F6G7H8J9K"` |
| `source_uri` | string(uri) | Y | 절대 URI. `s3://`, `gs://`, `az://`, `file://`, `http(s)://`, `smb://`(플러그인). authority에 userinfo 금지(패턴). 스킴·호스트 허용은 `fetch`가 `EgressPolicy`(E16)로 판정 — `fetch.scheme_unsupported`/`fetch.egress_denied`(§8) | `"s3://mois-records/regulations/2026/rule.hwpx"` |
| `media_type_hint` | string | N | 힌트만. 시그니처 판정(`detect`)이 우선(`SourceDocument.media_type`) | `"application/hwp+zip"` |
| `external_id` | string | N | 원천 시스템 문서 ID. `document_id` 재사용 키(갱신·삭제 조회 키, §10). 1..512자 | `"MOIS-REG-2026-0917"` |
| `external_version` | string | N | 원천 버전 라벨(etag 등). 참고 정보 — `doc_version`은 `content_hash`로만 결정(ADR-0005). 1..256자 | `"\"3f2a9c1e\""` |
| `metadata` | `IngestMetadata`(§2.2) | N | 예약 키 + `custom`. 생략 시 `{}`로 취급(`SourceDocument.metadata`는 Y) | §2.2 |
| `acl` | `Acl`(00 §4.4) | Y | 문서 단위 ACL(D-09, 바이블 §10.1): `allow_principals`(Y) · `visibility`(Y) · `deny_principals` · `classification` · `embargo_until` · `expires_at` · `source_acl_hash`. 모든 레벨 레코드·부모 번들이 상속. 입력 규칙 §7 | 예시 1 |
| `pii_policy` | enum(PiiPolicy) | N | 생략 시 컬렉션 기본값 상속. 확정값은 `SourceDocument.pii_policy`(요청 > 컬렉션 > 테넌트) | `"mask"` |
| `pii_tokenize_mode` | enum(PiiTokenizeMode) | 조건 | `pii_policy=tokenize`일 때만 존재 가능(`dependentRequired` + `if/then`); 생략 시 `encrypt` | `"encrypt"` |
| `credentials_ref` | string | N | KeyProvider 간접 참조 `{provider}:{path}`(암호화 문서 비밀번호·원천 토큰), 1..256자(02 `SourceDocument.credentials_ref`와 동일 상한). **본문 평문 금지**(§8.3) | `"openbao:secret/data/tenants/01J9…/sources/zip-password"` |
| `allow_distribution_documents` | boolean | N | 배포용 HWP 텍스트 폴백 허용(테넌트 정책과 AND). 생략 시 `false` | `false` |
| `llm_enrichment_allowed` | boolean | N | 외부 LLM 보강 옵트인(테넌트·컬렉션 정책과 AND, O-05). 생략 시 `false` | `false` |
| `dedup_policy` | enum(DedupPolicy) | N | 생략 시 `skip_if_same_hash`. `reindex_always`는 같은 `chunk_id` 집합이라도 새 `index_generation`으로 적재(§5.1) | `"reindex_always"` |
| `priority` | integer(0..9) | N | 생략 시 5. `PATCH /v1/jobs/{job_id}`로 변경 | `3` |
| `callback.webhook_url` | string(uri) | N | 릴레이가 `EgressPolicy`(E16)로 검사, `subscriptions.secret_ref`로 HMAC 서명(§6.2 `RAG-Signature`). 테넌트 등록 구독 URL과 일치해야 한다(§2.4) | `"https://hooks.example.go.kr/rag/ingest"` |
| `callback.events` | array<enum(EventType)> | N | 구독 이벤트 이름(바이블 §5.7)의 부분집합(§2.4). 생략 시 `["job.state.changed"]` | `["job.state.changed", "ingest.document.indexed"]` |
| `split_hint` | enum(SplitHint) | N | 컨테이너 내 다중 문서 분할. 생략 시 `none`. `json_array`는 멤버 분할 후 `txt` 라우팅(바이블 §7.3). `none`이 아니면 `source_uri`에 `#` 금지(§5.2) | `"zip_members"` |
| `profile_overrides` | `ProfileOverrides`(§2.5) | N | 컬렉션 프로파일의 허용 키만(`parse.pdf.route`, `enrich.generated_prefix`), 그 외 422 `profile.invalid` | `{"parse.pdf.route": "pdf_fast_cpu"}` |
| `deadline_at` | string(date-time) | N | 이 시각까지 시작하지 못하면 `queued → cancelled`(바이블 §11.5). `requested_at`보다 뒤 | `"2026-09-23T09:00:00.000Z"` |
| `requested_at` | string(date-time) | Y | 클라이언트 요청 시각(RFC 3339 UTC). 멱등 본문 지문에 포함되므로 재전송 시 같은 값(§4) | `"2026-09-22T09:00:00.000Z"` |

### 2.2 `metadata`(`$defs/IngestMetadata`; 바이블 §5.4 `metadata.*` 행)

모든 필드 N. 키 집합은 닫혀 있고(`additionalProperties: false`) 테넌트 정의 키는 `custom` 아래에만 둔다. 정규화·필터 대응은 §6.

| 필드 | 타입 | 필수 | 설명 | 예시 |
|------|------|------|------|------|
| `title` | string | N | 문서 제목(1..512자). 파서 메타로 보완 | `"공공기록물 관리에 관한 법률 시행규칙 일부개정안"` |
| `authors` | array<string> | N | 작성자·작성 기관(≤ 64개, 각 ≤ 256자; 02 `SourceMetadata`와 동일 상한) | `["행정안전부 국가기록원"]` |
| `doc_date` | string(date) | N | `YYYY-MM-DD`. 팩 헤더·상충 판정·필터 `doc_date` | `"2026-09-17"` |
| `doc_type` | string | N | 문서 종류 keyword, snake_case(`^[a-z][a-z0-9_]{0,63}$`). 예 `regulation`, `press_release`, `report` | `"regulation"` |
| `department` | string | N | 소관 부서·기관(1..256자). 필터 `department` | `"행정안전부"` |
| `language_hint` | string(bcp47) | N | 기본 `ko`. 힌트만(블록 `lang`은 `normalize`가 판정) | `"ko"` |
| `tags` | array<string> | N | 필터용 keyword(정확 일치; ≤ 64개, 각 1..128자, 정규화 후 중복 없음; 02 `SourceMetadata`와 동일 상한) | `["기록물", "시행규칙"]` |
| `genre` | enum(Genre) | N | 청커 장르 라우팅. 생략 시 `unknown` | `"law_article"` |
| `custom` | `CustomMetadata`(§2.3) | N | 테넌트 정의 keyword 메타 | §2.3 |

### 2.3 `metadata.custom`(`$defs/CustomMetadata`; 열린 객체, 00 §8.2)

| 항목 | 규칙 |
|------|------|
| 키 | `^[a-z][a-z0-9_]{0,63}$`(`propertyNames`), ≤ 64개(`maxProperties`; 초안 목표, 02 `SourceMetadata.custom`과 동일 상한) |
| 값 | `string`(≤ 1,024자) \| `number` \| `boolean`. 객체·배열·`null` 금지 |
| 필터 | 컬렉션 `CollectionSpec.filterable_fields`에 선언된 키만 `FilterNode.field = custom.{key}`로 필터 가능하고 `IndexRecord.custom`에 투영된다(바이블 §5.4 `IndexRecord`). 미선언 키는 저장(`documents.metadata`·`SourceDocument.metadata`)만 된다 |

### 2.4 `callback`(`$defs/IngestCallback`)

| 필드 | 타입 | 필수 | 설명 | 예시 |
|------|------|------|------|------|
| `webhook_url` | string(uri) | Y(객체가 있을 때) | `https`(기본) 또는 `http`(테넌트 옵트인). userinfo 금지. **테넌트의 등록 구독(`subscriptions.webhook_url`)과 일치**해야 서명 키를 해소할 수 있다 — 불일치는 400 `contract.violation`(pointer `/callback/webhook_url`) | `"https://hooks.example.go.kr/rag/ingest"` |
| `events` | array<enum(EventType)> | N | 이 잡이 발행할 수 있는 12종만: `job.state.changed`, `ingest.document.{fetched, parsed, normalized, chunked, enriched, embedded, indexed, retried, failed}`, `index.commit.{published, rolled_back}`(참조 옆 `enum`으로 좁힘). 1..12개, 중복 없음 | `["job.state.changed"]` |

### 2.5 `profile_overrides`(`$defs/ProfileOverrides`)

키는 프로파일 YAML 경로(점 구분, `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$`, ≤ 16개). 허용 키 집합은 컬렉션 프로파일이 선언하고(15 문서) 스키마는 바이블 §5.4의 두 예시 키만 형태를 고정한다: `parse.pdf.route`(string, 라우트 이름 `pdf_fast_cpu`·`pdf_standard`·`pdf_scanned_gpu`·`pdf_airgapped` 등 프로파일 정의), `enrich.generated_prefix`(`{enabled: boolean}`; 켜려면 `llm_enrichment_allowed`와 테넌트·컬렉션 정책이 모두 참, O-05). 허용 밖 키·값은 422 `profile.invalid`(13 §7.1; 바이블 §5.4 "그 외 422"). 오버라이드는 `Producer.config_hash`에 반영되어 `stage_key`를 바꾸므로 같은 문서라도 캐시 적중이 달라진다(바이블 §4.1).

## 3. 202 응답과 배치

### 3.1 `IngestAccepted`(`$defs/IngestAccepted`; D-08, 바이블 §14)

필수(Y) 필드는 브리프 D-08·바이블 §14 `202 {job_id, status_url, events_url}` 세 개다. 바이블 §5.4 `request_id` 행("응답에 `job_id`와 함께 반환")은 §14 행과 상충하므로 이 문서는 `request_id`를 **선택(N)** 으로만 둔다(바이블 §5.1 "추가 필드는 선택(N)으로만", 브리프 §11; 미해결 이슈 1). 서버 구현은 `request_id`·`document_id`를 항상 채우지만 클라이언트는 부재를 허용해야 한다.

| 필드 | 타입 | 필수 | 설명 | 예시 |
|------|------|------|------|------|
| `job_id` | string(ulid) | Y | `ingest.document.v1` 워크플로우 ID(`id_conflict_policy=USE_EXISTING`) | `"01J9ZQ7C9D0E1F2G3H4J5K6M7N"` |
| `request_id` | string(ulid) | N | 서버 발급 `IngestRequest.request_id`. **바이블 §14 응답 표에 없음**(§5.4와 상충) — 선택 필드로 두고 반영 제안(미해결 이슈 1) | `"01J9ZQ7B8C9D0E1F2G3H4J5K6M"` |
| `document_id` | string(ulid) | N | 접수 시 확정된 문서 ID(§10). **바이블 §14 응답 표에 없음** — 선택 필드로 두고 반영 제안(미해결 이슈 1) | `"01J9ZQ6M0N1P2Q3R4S5T6V7W8X"` |
| `status_url` | string(uri) | Y | `GET /v1/jobs/{job_id}` 절대 URL(`Location` 헤더와 동일) | `"https://rag.example.go.kr/v1/jobs/01J9…"` |
| `events_url` | string(uri) | Y | `GET /v1/jobs/{job_id}/events` SSE 절대 URL(`= status_url + "/events"`) | `"https://rag.example.go.kr/v1/jobs/01J9…/events"` |

### 3.2 배치(`POST /v1/ingest/batch`)

| 항목 | 규칙 |
|------|------|
| 본문 | `IngestRequest` **배열** 1..100건(`$defs/IngestBatchRequest`; 바이블 §14 "최대 100건 배열") |
| 검증 | 전체 원자적. 한 건이라도 위반이면 400 `contract.violation` + `errors[]`(`location.pointer`는 `/{index}/{field}`, 예 `/3/acl/visibility`), 잡은 하나도 만들지 않는다 |
| 접수 | 단일 트랜잭션에 `jobs` N행 + `idempotency_keys` 1행 + `artifacts` N행. `request_id`·`document_id`·산출물은 건별 발급·확정·저장. **원장 저장 규칙은 잠정안**(§4 "배치 원장" 행, 미해결 이슈 12) — 바이블 §13.1은 `jobs.idempotency_key UNIQUE(tenant_id, idempotency_key)`와 `idempotency_keys.job_id` 단일 컬럼을 정본으로 두어 한 키에 N개 잡 행을 그대로 넣을 수 없다 |
| 응답 | 202 `IngestBatchAccepted{jobs[]}`(`$defs/IngestBatchAccepted`); `jobs[i]`는 요청 배열 `i`번째 |
| 멱등성 | `Idempotency-Key` 하나가 배치 전체를 덮는다(§4; 의미론은 단건과 동일 — 200/409/422). 재생(200)은 전체 `IngestBatchAccepted`를 돌려준다(재구성 방식은 미해결 이슈 12) |
| 같은 문서 | 배열 안 두 건이 같은 `document_id`로 확정되면 뒤 건이 `queued(waiting_for=앞 job_id)`(§10) |

### 3.3 상태 코드(13 §7.1과 정합)

| 상태 | 조건 | 코드 |
|------|------|------|
| 202 | 접수 완료(본문 `IngestAccepted` / `IngestBatchAccepted`, `Location: status_url`) | — |
| 200 | 같은 `Idempotency-Key` + 같은 `request_hash` 재전송(접수 커밋 후) — 원 응답과 동일 본문 | — |
| 400 | 스키마·불변식 위반, `Idempotency-Key` 부재, `request_id` 존재, 비밀 값 평문, 인라인 한계 초과, 미등록 콜백 URL | `contract.violation`(`errors[].location.pointer`) |
| 401 / 403 | 미인증 / 컬렉션 `ingest` 권한 없음(fail-closed, 존재 비노출) | `auth.unauthenticated` / `auth.forbidden` |
| 409 | 같은 키의 접수 트랜잭션이 아직 커밋되지 않음(동시 중복) | `api.idempotency_conflict`(`instance`에 잠정 `/v1/jobs/{job_id}`, `Retry-After: 1`) |
| 422 | 같은 키·다른 본문 / `profile_overrides` 허용 밖 / 주체 1,024 초과 / 본문에 `tenant_id` 등 보안 필드 존재(E1, 00 §10.1 — 상태는 **422로 고정**) | `api.idempotency_payload_mismatch` / `profile.invalid` / `auth.too_many_principals` / `contract.violation`(13 §3.3 `auth.tenant_mismatch` 채택 전 대안; 카탈로그 HTTP 열이 400/500이라 상태와 불일치 — 미해결 이슈 7) |
| 429 | 테넌트·API 키 한도(E3) | `api.rate_limited` + `RateLimit`·`Retry-After` |
| 503 | (a) 오케스트레이터 불가 — 접수 트랜잭션은 커밋, 잡은 `queued`로 남고 조정 스케줄이 시작(바이블 §11.5), 같은 키 재전송은 200; (b) 산출물 저장(오브젝트 스토리지) 불가 — 접수하지 않음, 같은 키 재전송은 새 접수 | 본문은 `ProblemDetails` **필수**(13 §7.1) + `Retry-After: 30`(13 §7.2). 카탈로그에 맞는 코드가 없고 13 §3.3은 `contract.violation` 사용을 부적절로 판정했으므로 `api.orchestrator_unavailable`(a)·`api.dependency_unavailable`(b) **조기 채택이 구현 전제**(미해결 이슈 13, 13 미해결 이슈와 공동) |

## 4. 멱등성(`Idempotency-Key` + `request_id`)

**결정:** `POST /v1/ingest`·`/v1/ingest/batch`는 `Idempotency-Key` 헤더가 **필수**이며 draft-ietf-httpapi-idempotency-key-header-07 의미론(재전송 200 / 409 / 422)을 따른다. 판정 정본은 PostgreSQL `idempotency_keys(tenant_id, key)`이고 `jobs` INSERT와 동일 트랜잭션에 기록한다; Valkey `idem:{tenant}:{key}`는 조회 캐시다(D-08, 바이블 §13.1·§13.4; [ADR-0017](../06-adr/0017-event-delivery-outbox-cloudevents-no-broker.md), [ADR-0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md)).

| 항목 | 규약 |
|------|------|
| 키 형식 | `$defs/IdempotencyKey`: 가시 ASCII 1..255자, 서버에 불투명. 권장 UUIDv4 또는 ULID. 부재 시 400 `contract.violation`(pointer 없음; 13 §3.3 `api.idempotency_key_required` 채택 전) |
| 스코프 | `(tenant_id, key)` — 테넌트 전역. 컬렉션·엔드포인트로 나뉘지 않으므로 같은 키를 단건과 배치에 쓰면 `request_hash`가 달라 422 |
| 본문 지문 | `request_hash = H("idem", endpoint_path, canonical_json(wire_body))`(00 §7 `H()`). `wire_body`는 **서버 주입 전** 클라이언트 본문이므로 `request_id`·기본값 채움과 무관하다. `requested_at`이 포함되므로 재전송은 본문을 그대로 보낸다 |
| `request_id` 관계 | 키 1개 ↔ `request_id` 1개(단건) 또는 N개(배치). 같은 키의 재생(200)은 같은 `job_id`(·`request_id`)를 돌려준다. `request_id`는 잡 원장(`jobs.request_id`)·`SourceDocument.request_id`·산출물 참조(§산출물 저장 규약)의 역참조 키다 |
| 배치 원장(잠정안) | 바이블 §13.1 정본(`jobs.idempotency_key UNIQUE(tenant_id, idempotency_key)`, `idempotency_keys(tenant_id, key) → job_id` 단일)과 모순 없이 N건을 기록하기 위한 **잠정안**(미해결 이슈 12): `idempotency_keys(tenant_id, key)` 1행의 `job_id` = `jobs[0].job_id`, `request_hash` = 배치 본문 지문; 배치 멤버 `i`의 `jobs.idempotency_key` = `"{key}#{i}"`(단건은 `key` 그대로 — 파생 키는 `#`가 포함될 수 있는 단건 키와 충돌할 수 있으므로 정본 개정 전 임시). 재생(200)은 `jobs[0]`부터 `"{key}#{i}"`를 `i = 0..99` 순서로 조회해 `IngestBatchAccepted`를 **재구성**한다(`IngestAccepted`의 모든 필드는 `jobs` 행 + 기본 URL에서 결정적으로 도출). 정본 개정 후보: `idempotency_keys.job_ids array<ulid>` 또는 `response jsonb`(응답 스냅샷; 07-tech-landscape/08 "요청 지문 + 최종 응답 저장") |
| TTL | `idempotency_keys.expires_at = 접수 + 24h`(초안 목표; Valkey `idem:` 24h와 동일, 바이블 §13.4). 만료 후 같은 키는 새 요청(새 잡)이다. 정리는 `maintenance.cleanup.v1` |
| 재생 응답 | 상태 200, 본문은 원 202 응답과 **내용 동일**(단건 `IngestAccepted`는 바이트 동일; 배치 `IngestBatchAccepted`는 잠정안에서 `jobs` 행으로 재구성하므로 필드·값·순서 동일, 스냅샷 컬럼 채택 시 바이트 동일). 잡의 현재 상태는 `status_url`에서 조회한다 |
| 409 | 같은 키의 첫 요청이 접수 트랜잭션을 커밋하기 전(예약 `idem:` 존재, `jobs` 미커밋)에 온 중복. 잠정 `job_id`를 `instance`에 담고 `Retry-After: 1`(초안). 클라이언트는 새 키로 재전송하지 않는다(13 §10) |
| 422 | 같은 키·다른 `request_hash`. 본문이 바뀐 것이므로 새 키로 재전송 |
| 503 | (a) 접수 트랜잭션은 커밋됐으나 워크플로우 시작 실패 — 잡은 `queued`, 조정 스케줄이 시작, 같은 키 재전송은 200(잡 존재); (b) 산출물 put 실패 — 트랜잭션 미시작, `idem:` 예약 해제, 같은 키 재전송은 새 접수. 두 경우 모두 본문은 `ProblemDetails`(§3.3, 미해결 이슈 13) |

판정 분기(키 부재 → 400, 새 키 → 202, 같은 키·같은 지문 → 200, 같은 키·다른 지문 → 422, 미커밋 중복 → 409)는 §1 시퀀스 다이어그램의 `alt` 분기와 동일하다.

## 5. `dedup_policy`와 `split_hint`

### 5.1 `dedup_policy`(enum(DedupPolicy): `skip_if_same_hash` 기본, `reindex_always`)

판정 시점은 `fetch` 완료 후(`content_hash` 확정)이며 기준은 같은 `document_id`의 `documents.current_doc_version`·`current_generation`이다(바이블 §4.2 `fetch`, §11.4, [ADR-0005](../06-adr/0005-doc-version-content-hash-only-and-acl-payload-update.md), [ADR-0026](../06-adr/0026-index-commit-generation-saga-and-ledger.md)).

| 조건 | `skip_if_same_hash` | `reindex_always` |
|------|---------------------|------------------|
| `content_hash` 다름(신규 또는 변경) | 전 스테이지 실행 → 새 `index_generation` → `succeeded` | 동일 |
| `content_hash` 같고 `committed` 세대 존재, `acl_hash`·`metadata_hash` 동일 | `parse`~`index` 생략, 잡 `succeeded`(`progress.total = 1`, 이벤트 `ingest.document.fetched` → `job.state.changed`), 새 커밋 없음 | `parse`~`embed`는 `stage_key` 캐시 적중, `index`는 **새 세대** 적재·플립(`record_id`가 세대 포함, E17) |
| `content_hash` 같고 `acl_hash` 또는 `metadata_hash`만 다름 | **결정:** 재임베딩 없이 payload 갱신 경로(`acl.update.v1`과 동일 장치: `aclrev:` 힌트 → `update_acl`/메타 payload → `acl.document.updated`), `doc_version` 불변(ADR-0005). 잡 `succeeded` | 새 세대 적재(payload에 새 `acl_*`·메타 반영) |
| 같은 바이트를 다른 컬렉션·테넌트가 수집 | 스코프가 다르므로 "같은 문서"가 아니다 — 전 스테이지 실행(원본 바이트 저장만 `sources/{blake3}` 공유, ADR-0037) | 동일 |

### 5.2 `split_hint`(enum(SplitHint): `none` 기본, `json_array`, `zip_members`)

**결정:** 컨테이너의 각 멤버는 **별개 문서**다(바이블 §5.4 "컨테이너 내 다중 문서 분할") — 자기 `document_id`·`SourceDocument`·`IndexCommit`을 갖고 요청의 `acl`·`metadata`·정책을 그대로 상속하며 문서 단위로 직렬화된다(§10). 앵커에 근거가 있는 규칙은 사전 조건·라우팅 행이다.

**미정:** 멤버의 `source_uri`·`external_id` 합성 규약은 바이블 §5.4 `split_hint` 행·§6.1 식별자 표·§7.3 라우터 어디에도 없다. `document_id` 확정 키(§10)에 직접 영향하는 식별 규약이므로 이 문서가 단정하지 않는다. 아래 "잠정안" 행은 [../04-pipelines/02-fetching-and-source-resolution.md](../04-pipelines/02-fetching-and-source-resolution.md)·[03-parsing-router-and-format-detection](../04-pipelines/03-parsing-router-and-format-detection.md) 확정 후 바이블 §6.1 등재를 제안하는 초안이다(미해결 이슈 5).

| 항목 | 규칙 |
|------|------|
| 사전 조건(결정) | `split_hint ≠ none`이면 `source_uri`에 `#`(fragment)이 없어야 한다(스키마 `if/then`; 멤버 식별자가 fragment를 쓰는 어떤 잠정안과도 충돌하지 않도록 예약) |
| 라우팅(결정) | `json_array` 멤버는 `SourceFormat=json` 라우터 `{split: json_array, then: txt}`로 `txt` 파서에 간다(바이블 §7.3). `zip_members` 멤버는 각자 `detect`로 포맷을 판정한다. HWPX·DOCX 같은 ZIP 기반 단일 문서는 `zip_members`를 쓰지 않는다(컨테이너가 아니라 문서) |
| 멤버 `source_uri`(잠정안) | `{source_uri}#member={locator}`; `json_array` → `json[{i}]`(0-based 배열 인덱스), `zip_members` → `zip:{member_path}`. `locator`는 NFC 정규화 후 RFC 3986 percent-encoding(예약 문자·공백·`#`·`%`·비ASCII 모두 인코딩)을 적용해 멤버 `source_uri`가 `source_uri` 패턴(공백 금지)을 만족하고 결정적이 되게 한다. 예: ZIP 항목 `2026-07/공고문_01.hwpx` → `s3://…/q3-notices-bundle.zip#member=zip:2026-07/%EA%B3%B5%EA%B3%A0%EB%AC%B8_01.hwpx` |
| 멤버 `external_id`(잠정안) | 요청에 `external_id`가 있으면 `{external_id}#member={locator}`(같은 percent-encoding), 없으면 생략(`source_uri` 기준 식별) |
| 멤버 수(잠정안) | ≤ 100(초안 목표; 배치 상한과 동일). 초과분은 처리하지 않고 부모 잡 `partial` + `warnings[]`(코드는 미해결 이슈 5) |
| 미정 | 분할을 수행하는 스테이지(`fetch` vs `parse` 내부)와 자식 잡 생성 방식은 04-pipelines/02·03에서 확정(미해결 이슈 5) |

## 6. 예약 메타데이터 키와 정규화 규칙

**결정:** 정규화는 API 접수 시 값 수준에서 1회, **스키마 검증 전**에 수행하고(§2 도입부), 저장되는 `IngestRequest` 산출물은 정규화된 값을 담는다. `fetch`는 이를 `SourceDocument.metadata`로 **그대로 복사**하고 `metadata_hash = H("meta", canonical_json(metadata))`를 계산한다(바이블 §5.4·§6.2). 해시 입력은 값 없는 선택 필드(생략 또는 `null`)를 제거한 직렬화다(02 §3 해시 입력 규약; 예시 1의 `acl.expires_at: null`은 `acl_hash` 입력에 들어가지 않는다). 기본값(`language_hint=ko`, `genre=unknown`)은 **채워 넣지 않는다** — 생략된 키는 생략된 채 남고 소비자가 기본값을 적용한다(00 §8.1). 정규화는 멱등하다(`normalize(normalize(x)) = normalize(x)`).

| 키 | 정규화 | `FilterableField`(바이블 §5.7) | 투영(`IndexRecord`·`ContextItem`) |
|----|--------|-------------------------------|------------------------------------|
| `title` | NFC, 양끝 trim, 내부 공백 1칸으로 축약, 결과가 빈 문자열이면 위반 | — | `IndexRecord.title`(Y; 부재 시 `ParsedDocument.metadata.title` → 첫 `heading` level 0 → `source_uri` 마지막 경로 요소), `ContextItem.header.title`, 결정적 `context_prefix` |
| `authors` | 각 항목 NFC·trim, 순서 보존 중복 제거 | — | 인덱스 미투영(`documents.metadata` 저장; 미해결 이슈 4) |
| `doc_date` | 형식 검증만(`YYYY-MM-DD`); 요청 값이 파서 메타(문서 속성 생성일)보다 우선 | `doc_date` | `IndexRecord.doc_date`(datetime 인덱스), `ContextItem.header.doc_date`, 상충 판정 `ConflictKind=date` |
| `doc_type` | 패턴 `^[a-z][a-z0-9_]{0,63}$`(대·소문자 변환 없음 — 위반은 400) | `doc_type` | `IndexRecord.doc_type`(keyword) |
| `department` | NFC·trim·공백 축약 | `department` | `IndexRecord.department`(keyword; 한국어 기관명 정확 일치) |
| `language_hint` | trim 후 기본 서브태그 소문자, 2자 지역 서브태그 대문자(`KO-kr` → `ko-KR`; 00 U-10). 스키마 `Bcp47` 패턴은 정규화 결과에 적용 | `lang` | 문서 기본 `lang`; 블록·청크 `lang`은 `normalize`가 판정하고 `IndexRecord.lang`(Y)은 청크 값 |
| `tags` | 각 항목 NFC·trim, 순서 보존 중복 제거, 대소문자 변환 없음(정확 일치 keyword). 스키마 `uniqueItems`는 정규화 결과에 적용 | `tags`(`contains_any`/`contains_all`) | `IndexRecord.tags` |
| `genre` | 열거 검증만 | `genre` | `NormalizedDocument.genre`, `ChunkSet.genre_route`, `IndexRecord.genre`(Y; 생략 시 `unknown`) |
| `custom.{key}` | 키 패턴·개수·값 타입 검증(§2.3); 문자열 값 NFC·trim | `custom.{key}`(컬렉션 `filterable_fields` 선언 키만) | `IndexRecord.custom`(선언 키만) |
| (최상위) `external_id` | NFC·trim | `external_id` | `IndexRecord.external_id`, `ContextItem.header.source_uri`와 함께 인용 식별 |

## 7. ACL 입력 규칙

정본은 바이블 §10.1과 00 §4.4·I-12이다([ADR-0027](../06-adr/0027-security-context-injection-and-acl-enforcement-points.md)). A1·A2·A3·A5·A7·A8·A9·A10은 앵커 규칙의 입력 시점 적용이다. **A4·A6은 이 문서가 더한 추가 규칙**으로, 공용 타입 `Acl`(00 §4.4, `common-types` `$defs/Acl`)이 허용하는 인스턴스에 의미를 더하므로 바이블 §10.1·00 §4.4 등재 전까지 **잠정**이다(미해결 이슈 14; 채택 전 완화안도 거기에 병기).

| # | 규칙 | 위반 시 |
|---|------|---------|
| A1 | 주체 문자열은 `user:{subject}`, `group:{group_id}`, `service:{client_id}`, `tenant:*`(바이블 §6.1; `$defs/PrincipalString`). 접두는 소문자 고정, `subject` 부분은 trim만 하고 대소문자를 바꾸지 않는다(OIDC `sub`는 대소문자 구분) | 400 `contract.violation` |
| A2 | `allow_principals`·`deny_principals` 각 ≤ 1,024, 순서 보존 중복 제거(E4) | 400 `contract.violation`(스키마 `maxItems`); 확장 후 주체 수 초과는 422 `auth.too_many_principals` |
| A3 | 거부 우선: 같은 주체가 양쪽에 있어도 오류가 아니며 항상 거부된다(I-12) | — |
| A4(이 문서 추가 규칙, 잠정) | `deny_principals`에 `tenant:*` 금지 — 모든 주체를 거부하는 문서는 의미가 없다(삭제 또는 `expires_at`을 쓴다). 공용 `Acl` 스키마는 이 값을 허용하므로 이 계약의 불변식(IR-5)으로만 거부한다 | 400 `contract.violation`(채택 전 대안: 접수 허용 + `Warning` — 미해결 이슈 14) |
| A5 | `visibility`: `public` = allow 검사 생략(교차 테넌트 불가, deny·embargo·expires·classification은 적용); `tenant` = 인증 사용자 전원(`service:` 주체는 `allow_principals` 필요); `restricted` = `allow_principals`만 | — |
| A6(이 문서 추가 규칙, 잠정) | `restricted`이고 `allow_principals=[]`는 허용된다 — "잠금(locked)" 문서로 접수되며 `PATCH /v1/documents/{document_id}/acl`로 열 때까지 아무 주체에게도 반환되지 않는다(의도적 워크플로우: 승인 후 공개). 바이블 §10.1 `restricted` 정의("`allow_principals`에 포함된 주체만")에서 도출되는 귀결이지만 "잠금" 의미 자체는 앵커에 없다 | — |
| A7 | `embargo_until`·`expires_at`는 RFC 3339 UTC; 둘 다 있으면 `embargo_until < expires_at`(I-12). `expires_at ≤ 접수 시각`인 문서는 접수하되 검색에 나타나지 않는다(경고 없음) | 400 `contract.violation` |
| A8 | `classification` 생략 시 `internal`; `SecurityContext.classification_max`와의 비교는 질의 시(E9)이며 접수 시 검사하지 않는다 | — |
| A9 | 문서 단위: 블록·청크 단위 ACL 필드는 없다(v1). `acl`은 `SourceDocument.acl` 하나로 전파되고 `acl_hash = H("acl", canonical_json(acl))`로 모든 레벨 레코드·부모 번들에 동일 적용된다 | — |
| A10 | ACL만 바꾸려면 새 `IngestRequest`가 아니라 `PATCH /v1/documents/{document_id}/acl`(`acl.update.v1`)을 쓴다. 같은 바이트를 다른 ACL로 재제출하면 §5.1의 payload 갱신 경로로 처리된다 | — |

## 8. URI 스킴 허용목록·`EgressPolicy`·`credentials_ref`

### 8.1 스킴 허용목록

| 스킴 | 지위 | 기본 `EgressPolicy.allowed_schemes`(바이블 §5.3) |
|------|------|-------------------------------------------------|
| `https` | 코어(`fetcher.fsspec_httpx`; 매트릭스 `uri_fetcher` — 연구 공백, 확인 필요 as of 2026-09) | 포함 |
| `s3`, `gs`, `az` | 코어(fsspec 계열; 확인 필요 as of 2026-09) | 포함 |
| `http` | 코어 | 제외 — 테넌트 옵트인 |
| `file` | 코어 | 제외 — 개발 모드만(바이블 §5.3 "`file`은 개발 프로파일만"; `ProfileTier`에 개발 등급이 없어 `runtime.orchestrator: local` 한정인지 `lite` 전체인지는 [ADR-0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md)·15·09-operations/02 확정 전 **미정**). 운영 프로파일 거부는 E16 계약 테스트 항목 |
| `smb` | 플러그인(`rag-plugin-smb`, `fetcher` 확장 지점) | 제외 — 플러그인 설치 + 정책 추가 |
| 그 외 | 등록된 `fetcher` 플러그인이 있을 때만 | 제외 |

**결정:** API는 `source_uri`의 **문법**만 검증한다(절대 URI, userinfo 금지, 공백 금지, ≤ 2,048자). 스킴·호스트·IP·리다이렉트·크기 판정은 단일 강제 지점 E16(`fetch`)이 `EgressPolicy`(프로파일 AND 테넌트 정책)로 수행하고 실패는 잡 `failed` + `last_error.code ∈ {fetch.scheme_unsupported, fetch.egress_denied, fetch.too_large}`(비재시도)로 드러난다([ADR-0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md)). 접수 시점 사전 거부는 두지 않는다(정책 판정 지점을 하나로 유지; 미해결 이슈 6).

### 8.2 `EgressPolicy` 적용(E16, 바이블 §10.3)

| 검사 | 내용 | 실패 코드 |
|------|------|-----------|
| 스킴 | `allowed_schemes` ∩ 등록 `fetcher` 스킴 | `fetch.scheme_unsupported` |
| 호스트·IP | `allowed_hosts`(있으면), DNS 해석 IP를 `deny_cidrs`(사설·루프백·링크로컬·클라우드 메타데이터 `169.254.169.254`, IPv6 포함)와 대조 후 **고정 연결**(`resolve_pin`, DNS 리바인딩 차단) | `fetch.egress_denied` |
| 리다이렉트 | 매 홉 재검사, `max_redirects`(기본 3) | `fetch.egress_denied` |
| 포트 | `allowed_ports`(기본 `[443]`, `80`은 옵트인) | `fetch.egress_denied` |
| 크기·시간 | `max_bytes`(기본 `fetch.max_bytes` 200MB), `connect_timeout_ms`(기본 5,000) | `fetch.too_large` / `fetch.timeout`(재시도) |
| 콜백 | `callback.webhook_url`은 릴레이가 같은 정책으로 검사 | `outbox.egress_denied` |

프리사인 URL(`s3://`·`https://`의 쿼리 서명)은 허용되며 `fetch`가 `SourceDocument.resolved_uri`(서명·자격 증명 쿼리 제거본, 02 §7)에 해소 결과를 기록한다. 쿼리 문자열을 포함한 `source_uri` **자체**는 로그·트레이스·이벤트 `data`·`ProblemDetails.detail`·`StageError.detail`에 기록하지 않는다(호스트·경로도 포함하지 않는다 — 13 §9·§11, 00 I-16); 필요하면 `document_id`·`request_id`·`job_id`로 가리킨다.

### 8.3 `credentials_ref`(비밀 값 직접 전달 금지)

**결정:** 비밀번호·토큰·키는 어떤 필드로도 본문에 오지 않는다. `credentials_ref`는 `{provider}:{path}` 형식의 간접 참조(`$defs/CredentialsRef`: `^[a-z][a-z0-9_]*:[^\s]{1,240}$`, 1..256자)이며 워커가 KeyProvider로 해소한다. API는 **형식만** 검증한다 — provider 값(`RAG_SECRETS__PROVIDER = env | openbao | aws_kms`, 바이블 §6.6)의 유효성은 KeyProvider 해소 시 워커가 판정하며(미등록 provider·부재 경로는 `parse.document_encrypted` 또는 `fetch.access_denied`, 비재시도), 패턴은 provider 집합을 고정하지 않는다(테넌트 플러그인 provider 허용). 길이 상한 256은 `SourceDocument.credentials_ref`(02 스키마 `maxLength: 256`)와 같게 두어 접수된 값이 하류 출력 검증에서 `contract.violation`(500)이 되지 않게 한다; 02가 `$defs/CredentialsRef`를 `$ref`하도록 정합 제안을 남긴다(미해결 이슈 15). 값은 `SourceDocument.credentials_ref`·`ConvertRequest.credentials_ref`로 그대로 전파되고(값 미포함) 로그·트레이스·이벤트·`ProblemDetails.detail`에 기록되지 않는다. 암호화 문서(HWP 5.0 FileHeader 암호 플래그, PDF 암호)에 `credentials_ref`가 없으면 `parse.document_encrypted`(비재시도, 바이블 §3.2 O-07). `source_uri` userinfo(`https://user:pass@host/`)는 패턴으로 거부하고, 스키마에 없는 `password`·`token` 같은 키는 `additionalProperties: false`로 거부한다(400 `contract.violation`).

## 9. 검증 규칙, 크기 한계, 대형 데이터

검증 지점은 00 §10.1의 세 곳 중 API 경계(입력)와 셸 입력 로드(`fetch` 앞)다. 셸 출력 저장 전 검증은 `IngestRequest`에 없다(스테이지 출력이 아님). 원본 문서는 본문에 절대 인라인하지 않는다(base64 포함 금지, 00 §8.3) — 위치만 `source_uri`로 주고 `fetch`가 `sources/{blake3}`에 저장하며 원본 크기 상한은 `EgressPolicy.max_bytes`(기본 `fetch.max_bytes` 200MB, 초과는 `fetch.too_large`)다.

| # | 규칙 | 근거 | 위반 시 |
|---|------|------|---------|
| V1 | 두 척도 모두 ≤ 65,536바이트: (a) 요청 바이트(API 경계, `Content-Length` 또는 실제 수신 바이트) — 정규화·주입 **전**; (b) 저장 인스턴스의 `canonical_json` UTF-8 — 정규화·`request_id` 주입 **후**(Pydantic `_invariants`가 검사). (a)는 스트리밍 파서가 본문을 다 읽기 전에 거부하기 위한 경계 상한, (b)는 산출물 인라인 한계다 | 바이블 §5.1 "64KB(본문)" | 400 `contract.violation`(13 §3.3 `api.payload_too_large` 채택 전) |
| V2 | `metadata`의 `canonical_json` UTF-8 ≤ 16,384바이트 | 바이블 §5.1 "`metadata` 16KB" | 400 `contract.violation`(pointer `/metadata`) |
| V3 | 배치 1..100건; 배치 본문 상한은 100 × 64KB(산술 도출) | 바이블 §14 | 400 `contract.violation` |
| V4 | `Content-Type: application/json`, UTF-8, BOM 없음, `NaN`/`Infinity` 없음 | 00 §8.3 | 400 `contract.violation`(13 §3.3 `api.unsupported_media_type` 채택 전) |
| V5 | JSON Schema 2020-12(`urn:rag:schema:ingest-request:1`) + Pydantic 검증; 필드별 오류는 `ProblemDetails.errors[]`(≤ 16)에 `location.pointer` | 00 §10.1 | 400 `contract.violation` |
| V6 | `readOnly`(`request_id`) 존재 거부; 보안 필드(`tenant_id`, `SecurityContext` 하위 키) 존재 거부 | 00 §8.2·§10.1, E1 | `request_id`: 400 `contract.violation`(pointer `/request_id`) / `tenant_id`: **422** `contract.violation`(pointer `/tenant_id`; `auth.tenant_mismatch` 채택 전, §3.3·미해결 이슈 7) |
| V7 | `collection_id`는 `SecurityContext.collection_ids`(Cedar `allowed_collections`)에 속한다 | E2 | 403 `auth.forbidden` |
| V8 | `profile_overrides` 키·값이 컬렉션 프로파일 허용 집합에 속한다(DB 조회) | 바이블 §5.4 | 422 `profile.invalid` |
| V9 | `callback.webhook_url`이 테넌트 등록 구독과 일치한다(DB 조회) | §2.4 | 400 `contract.violation` |
| V10 | 배열 상한(초안 목표): `authors` 64, `tags` 64(항목 ≤ 128자), `custom` 키 64, `callback.events` 12, `profile_overrides` 16; 주체 1,024(바이블 §5.3). `authors`·`tags`·`custom` 상한은 02 `SourceMetadata`(복사 대상)와 같은 값이다 | 이 문서, 02 §2.4 | 400 `contract.violation` |

## 10. 문서 단위 잡 분할과 같은 `document_id` 직렬화

**결정:** 잡의 단위는 문서다(`JobKind=ingest_document`). `document_id`는 API 접수 트랜잭션에서 확정해 `jobs.document_id`에 기록하고, 같은 `document_id`의 활성 잡(`queued | running | cancelling`)이 있으면 새 잡은 `queued(waiting_for = 앞 job_id)`로 남아 디스패처가 순서대로 시작한다(바이블 §11.2, D-08; [ADR-0026](../06-adr/0026-index-commit-generation-saga-and-ledger.md)).

| 단계 | 규칙 |
|------|------|
| 식별 조회 | (1) `external_id`가 있으면 `documents(tenant_id, collection_id, external_id)` 일치 행 재사용; (2) 없으면 `documents(tenant_id, collection_id, source_uri)` 중 `external_id IS NULL`인 행 재사용; (3) 둘 다 없으면 새 ULID 발급 + `documents` INSERT(같은 트랜잭션). `external_id`가 같고 `source_uri`가 달라도 같은 문서(이동); `source_uri`가 같고 `external_id`가 다르면 다른 문서 |
| 직렬화 | 디스패처(api 프로세스, PG advisory lock `tenant_id`)가 앞 잡 종료 이벤트·조정 스케줄에서 다음 잡을 시작. 순서 = 접수 순서(배치 안에서는 배열 순서). 앞 잡이 `failed`·`cancelled`여도 뒤 잡은 시작한다 |
| 테넌트 동시성 | `runtime.tenant_concurrent_jobs_max`(`standard` 32, 초안)를 `jobs.state=running` 수로 강제 — 초과분은 `queued` |
| 세대 | 직렬화 덕분에 문서당 `index_generation`은 단조 증가하고 플립 충돌은 `index.generation_conflict` 안전망만 남는다(바이블 §11.4) |
| 분할 | `split_hint` 멤버(§5.2)는 각자 `document_id`로 위 규칙을 그대로 따른다 |
| 취소·기한 | `deadline_at` 초과 시 `queued → cancelled`(시작한 잡은 영향 없음); `POST /v1/jobs/{job_id}/cancel`은 `waiting_for` 대기 잡도 취소한다 |

## 11. LLM 최종 소비에 미치는 영향

`IngestRequest`의 값은 `ContextPack`까지 결정적으로 전파된다(브리프 원칙 10; 00 §11).

| 관심사 | 이 계약의 필드 | 도달 지점 |
|--------|----------------|-----------|
| 인용 가능성·provenance | `source_uri`, `external_id`, `metadata.title`·`doc_date` | `IndexRecord.source_uri`·`external_id`·`title`·`doc_date` → `ContextItem.header{title, source_uri, doc_date}`; 본문 좌표(`block_refs`)는 파서가 만들지만 문서 식별은 이 계약이 정한다. `title`이 없으면 대체 순서(§6)로 채워지므로 공문서는 `title`을 주는 것이 인용 품질에 직접 영향한다 |
| 3-텍스트 규칙 | `metadata.title`, heading 경로 | 결정적 `context_prefix`(임베딩·리랭크 입력)에만 들어가고 `ContextItem.text`(표시 원문)에는 섞이지 않는다(K2, [ADR-0029](../06-adr/0029-three-text-rule-and-deterministic-context-prefix.md)). `custom`·`tags`·`authors`는 LLM 텍스트에 들어가지 않는다 |
| 보안 삼중항 | `collection_id`, `acl`(+ 서버 `tenant_id`) | 모든 `IndexRecord`의 `tenant_id`·`collection_id`·`acl_*`·`acl_hash`(E5) → 사전 필터(E7) → `pack` 재검증(E9, `ContextItem.acl.checked`). LLM은 주체가 볼 수 없는 문서를 받지 못한다 |
| 상충·최신성 | `metadata.doc_date`, `external_version` | 팩의 `conflicts_with[].kind=date` 판정과 `boost recency`; `doc_date` 부재 시 `pack.conflict_unlabeled` 경고 |
| PII·데이터 경계 | `pii_policy`, `pii_tokenize_mode`, `llm_enrichment_allowed` | `normalize`가 두 텍스트 뷰에서 PII를 제거·토큰화한 뒤에만 외부 LLM(보강·판정)에 전달(O-05). `keep`은 고유식별정보·계좌·카드에 불가(E4) |
| 장르·언어 | `metadata.genre`, `language_hint` | 청킹 전략(`law_article` 조·항 분할) → 항목 경계·`segments` 품질; `lang` → `render_hints.language` |

## 스키마

전문은 [schemas/ingest-request.schema.json](../../schemas/ingest-request.schema.json)과 동일하다. 공용 타입·열거는 `urn:rag:schema:common-types:1#/$defs/*`를 참조한다.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:rag:schema:ingest-request:1",
  "title": "IngestRequest",
  "description": "수집 요청 계약(바이블 §5.4). 클라이언트가 POST /v1/ingest 로 제출하는 문서 위치(URI)·메타데이터·ACL·정책. tenant_id 는 본문에 없고(SecurityContext 에서 도출, E1) request_id 는 서버가 발급한다(readOnly). 비밀 값은 credentials_ref 간접 참조로만 받는다. 소비: fetch, API.",
  "type": "object",
  "properties": {
    "schema_version": { "$ref": "urn:rag:schema:common-types:1#/$defs/Semver", "pattern": "^1\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$", "description": "계약 버전. 초기 \"1.0.0\"; 이 스키마($id major 1)는 1.x 만 수용" },
    "request_id": { "$ref": "urn:rag:schema:common-types:1#/$defs/Ulid", "readOnly": true, "description": "서버 발급(접수 시 ULID). 클라이언트 본문에 존재하면 400 contract.violation. 202 응답 IngestAccepted.request_id(N)로 job_id 와 함께 반환" },
    "collection_id": { "$ref": "urn:rag:schema:common-types:1#/$defs/Ulid", "description": "프로파일이 고정된 컬렉션. SecurityContext.collection_ids(Cedar allowed_collections) 밖이면 403 auth.forbidden(E2, 존재 비노출)" },
    "source_uri": { "$ref": "urn:rag:schema:common-types:1#/$defs/Uri", "pattern": "^[a-z][a-z0-9+.-]*://[^\\s/@]*(/[^\\s]*)?$", "maxLength": 2048, "description": "절대 URI. s3://, gs://, az://, file://, http(s)://, smb://(플러그인). authority 에 userinfo(user:pass@) 금지. 스킴·호스트 허용 여부는 fetch 가 EgressPolicy(E16)로 판정 — 위반은 fetch.scheme_unsupported / fetch.egress_denied" },
    "media_type_hint": { "$ref": "urn:rag:schema:common-types:1#/$defs/MediaType", "description": "힌트만. 시그니처 판정(detect)이 우선" },
    "external_id": { "type": "string", "minLength": 1, "maxLength": 512, "description": "원천 시스템 문서 ID. document_id 재사용 키(갱신·삭제 조회 키)" },
    "external_version": { "type": "string", "minLength": 1, "maxLength": 256, "description": "원천 버전 라벨(etag 등). 참고 정보이며 doc_version 은 content_hash 로만 결정된다(ADR-0005)" },
    "metadata": { "$ref": "#/$defs/IngestMetadata", "description": "예약 메타데이터 키(바이블 §5.4)와 custom. 생략 시 {} 로 취급" },
    "acl": { "$ref": "urn:rag:schema:common-types:1#/$defs/Acl", "description": "문서 단위 ACL(D-09, 바이블 §10.1). 모든 레벨 레코드·부모 번들이 상속" },
    "pii_policy": { "$ref": "urn:rag:schema:common-types:1#/$defs/PiiPolicy", "description": "생략 시 컬렉션 기본값 상속(확정값은 SourceDocument.pii_policy)" },
    "pii_tokenize_mode": { "$ref": "urn:rag:schema:common-types:1#/$defs/PiiTokenizeMode", "description": "pii_policy=tokenize 일 때만 존재 가능. 생략 시 encrypt" },
    "credentials_ref": { "$ref": "#/$defs/CredentialsRef", "description": "KeyProvider 간접 참조(암호화 문서 비밀번호·원천 토큰). 비밀 값 자체를 본문에 넣으면 400 contract.violation" },
    "allow_distribution_documents": { "type": "boolean", "description": "배포용 HWP 텍스트 폴백 허용(테넌트 정책과 AND). 생략 시 false" },
    "llm_enrichment_allowed": { "type": "boolean", "description": "외부 LLM 보강 옵트인(테넌트·컬렉션 정책과 AND). 생략 시 false" },
    "dedup_policy": { "$ref": "urn:rag:schema:common-types:1#/$defs/DedupPolicy", "description": "생략 시 skip_if_same_hash. reindex_always 는 같은 chunk_id 집합이라도 새 index_generation 으로 적재(§11.4)" },
    "priority": { "type": "integer", "minimum": 0, "maximum": 9, "description": "생략 시 5. PATCH /v1/jobs/{job_id} 로 변경 가능" },
    "callback": { "$ref": "#/$defs/IngestCallback", "description": "잡 단위 웹훅 콜백. 릴레이가 EgressPolicy(E16)로 검사하고 subscriptions.secret_ref 로 HMAC 서명" },
    "split_hint": { "$ref": "urn:rag:schema:common-types:1#/$defs/SplitHint", "description": "컨테이너 내 다중 문서 분할. 생략 시 none. json_array 는 멤버 분할 후 txt 라우팅(바이블 §7.3)" },
    "profile_overrides": { "$ref": "#/$defs/ProfileOverrides", "description": "컬렉션 프로파일이 허용한 키만(parse.pdf.route, enrich.generated_prefix). 그 외 키는 422 profile.invalid" },
    "deadline_at": { "$ref": "urn:rag:schema:common-types:1#/$defs/DateTime", "description": "이 시각까지 시작하지 못하면 cancelled. requested_at 보다 뒤여야 한다" },
    "requested_at": { "$ref": "urn:rag:schema:common-types:1#/$defs/DateTime", "description": "클라이언트 요청 시각(RFC 3339 UTC). 멱등 본문 지문에 포함되므로 재전송 시 같은 값을 보낸다" }
  },
  "required": ["schema_version", "request_id", "collection_id", "source_uri", "acl", "requested_at"],
  "additionalProperties": false,
  "dependentRequired": { "pii_tokenize_mode": ["pii_policy"] },
  "allOf": [
    { "if": { "required": ["pii_tokenize_mode"] }, "then": { "properties": { "pii_policy": { "const": "tokenize" } } } },
    { "if": { "required": ["split_hint"], "properties": { "split_hint": { "enum": ["json_array", "zip_members"] } } }, "then": { "properties": { "source_uri": { "pattern": "^[^#]*$" } } } }
  ],
  "$defs": {
    "IngestMetadata": {
      "type": "object",
      "description": "예약 메타데이터 키(바이블 §5.4). doc_date·doc_type·department·tags·language_hint(→lang)·genre 는 §5.7 FilterableField 와 정합. 정규화(01-ingest-request §6)는 스키마 검증 전에 수행되므로 uniqueItems·패턴·길이는 정규화된 저장 인스턴스에 대한 제약이다. canonical_json 크기 ≤ 16KB(바이블 §5.1). authors·tags·custom 상한은 02 SourceMetadata 와 동일.",
      "properties": {
        "title": { "type": "string", "minLength": 1, "maxLength": 512, "description": "문서 제목. NFC·trim·공백 축약. 부재 시 파서 메타 → 첫 heading level 0 → source_uri 마지막 경로 요소 순으로 보완" },
        "authors": { "type": "array", "items": { "type": "string", "minLength": 1, "maxLength": 256 }, "maxItems": 64, "description": "작성자·작성 기관(NFC·trim·순서 보존 중복 제거 후)" },
        "doc_date": { "$ref": "urn:rag:schema:common-types:1#/$defs/Date", "description": "문서 일자(YYYY-MM-DD). 팩 헤더·상충 판정·필터 doc_date" },
        "doc_type": { "type": "string", "pattern": "^[a-z][a-z0-9_]{0,63}$", "description": "문서 종류 keyword(snake_case). 예 regulation, press_release, report. 필터 doc_type" },
        "department": { "type": "string", "minLength": 1, "maxLength": 256, "description": "소관 부서·기관(NFC·trim). 필터 department" },
        "language_hint": { "$ref": "urn:rag:schema:common-types:1#/$defs/Bcp47", "description": "기본 ko. 힌트만(블록 단위 lang 은 normalize 가 판정). 필터 lang 의 문서 기본값" },
        "tags": { "type": "array", "items": { "type": "string", "minLength": 1, "maxLength": 128 }, "maxItems": 64, "uniqueItems": true, "description": "필터용 keyword(정확 일치). NFC·trim·순서 보존 중복 제거(정규화) 후의 값에 uniqueItems 적용" },
        "genre": { "$ref": "urn:rag:schema:common-types:1#/$defs/Genre", "description": "청커 장르 라우팅(law_article 등). 생략 시 unknown" },
        "custom": { "$ref": "#/$defs/CustomMetadata", "description": "테넌트 정의 keyword 메타. 컬렉션 filterable_fields 에 선언된 키만 필터·IndexRecord.custom 투영" }
      },
      "additionalProperties": false
    },
    "CustomMetadata": {
      "type": "object",
      "description": "열린 객체(00-contract-overview §8.2). 키는 snake_case ≤ 64자, 값은 스칼라(string ≤ 1,024 | number | boolean). 키 ≤ 64개(02 SourceMetadata.custom 과 동일).",
      "propertyNames": { "pattern": "^[a-z][a-z0-9_]{0,63}$" },
      "additionalProperties": { "anyOf": [ { "type": "string", "maxLength": 1024 }, { "type": "number" }, { "type": "boolean" } ] },
      "maxProperties": 64
    },
    "IngestCallback": {
      "type": "object",
      "description": "잡 단위 웹훅 콜백. webhook_url 은 테넌트의 등록 구독(subscriptions.webhook_url)과 일치해야 서명 키(secret_ref)를 해소할 수 있다.",
      "properties": {
        "webhook_url": { "$ref": "urn:rag:schema:common-types:1#/$defs/Uri", "pattern": "^https?://[^\\s/@]+(/[^\\s]*)?$", "maxLength": 2048, "description": "https 기본, http 는 테넌트 옵트인(EgressPolicy.allowed_schemes). userinfo 금지" },
        "events": {
          "type": "array",
          "items": {
            "$ref": "urn:rag:schema:common-types:1#/$defs/EventType",
            "enum": ["job.state.changed", "ingest.document.fetched", "ingest.document.parsed", "ingest.document.normalized", "ingest.document.chunked", "ingest.document.enriched", "ingest.document.embedded", "ingest.document.indexed", "ingest.document.retried", "ingest.document.failed", "index.commit.published", "index.commit.rolled_back"]
          },
          "minItems": 1,
          "maxItems": 12,
          "uniqueItems": true,
          "description": "구독 이벤트(바이블 §5.7 카탈로그 중 이 잡이 발행하는 부분집합). 생략 시 [job.state.changed]"
        }
      },
      "required": ["webhook_url"],
      "additionalProperties": false
    },
    "ProfileOverrides": {
      "type": "object",
      "description": "요청 단위 프로파일 오버라이드. 키는 프로파일 YAML 경로(점 구분). 허용 키 집합은 컬렉션 프로파일이 선언하며 스키마는 바이블 §5.4 의 두 예시 키만 형태를 고정한다. 허용 밖 키·값은 422 profile.invalid.",
      "properties": {
        "parse.pdf.route": { "type": "string", "pattern": "^[a-z][a-z0-9_]{0,63}$", "description": "PDF 라우트 이름(pdf_fast_cpu, pdf_standard, pdf_scanned_gpu, pdf_airgapped 등 프로파일 정의)" },
        "enrich.generated_prefix": { "type": "object", "properties": { "enabled": { "type": "boolean" } }, "required": ["enabled"], "additionalProperties": false, "description": "LLM 접두어 켬/끔. 켜려면 llm_enrichment_allowed 와 테넌트·컬렉션 정책이 모두 참이어야 한다(O-05)" }
      },
      "propertyNames": { "pattern": "^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)*$", "maxLength": 128 },
      "additionalProperties": true,
      "maxProperties": 16
    },
    "CredentialsRef": { "type": "string", "pattern": "^[a-z][a-z0-9_]*:[^\\s]{1,240}$", "minLength": 1, "maxLength": 256, "description": "{provider}:{path}. 형식만 검증하며 provider(RAG_SECRETS__PROVIDER env|openbao|aws_kms, 바이블 §6.6) 유효성은 KeyProvider 해소 시 워커가 판정한다. 상한 256 은 SourceDocument.credentials_ref(02)와 동일. 값은 SourceDocument·ConvertRequest 로 그대로 전파되고 로그·트레이스·이벤트에는 기록하지 않는다" },
    "IdempotencyKey": { "type": "string", "minLength": 1, "maxLength": 255, "pattern": "^[\\x21-\\x7E]+$", "description": "Idempotency-Key 헤더 값(draft-ietf-httpapi-idempotency-key-header-07). 가시 ASCII, 서버에 불투명. 권장 UUIDv4 또는 ULID. 스코프 (tenant_id, key), TTL 24h(초안 목표)" },
    "IngestAccepted": {
      "type": "object",
      "description": "POST /v1/ingest 202 응답 본문(D-08, 바이블 §14 {job_id, status_url, events_url}). request_id·document_id 는 선택(N; 바이블 §14 반영 제안). 같은 Idempotency-Key 재전송의 200 응답도 동일 본문.",
      "properties": {
        "job_id": { "$ref": "urn:rag:schema:common-types:1#/$defs/Ulid", "description": "ingest.document.v1 워크플로우 ID" },
        "request_id": { "$ref": "urn:rag:schema:common-types:1#/$defs/Ulid", "description": "서버 발급 IngestRequest.request_id. 선택(N) — 바이블 §14 응답 표에 없음(§5.4 와 상충), 반영 제안" },
        "document_id": { "$ref": "urn:rag:schema:common-types:1#/$defs/Ulid", "description": "접수 시 확정된 문서 ID(바이블 §11.2). 선택(N) — 바이블 §14 응답 표에 없어 반영 제안" },
        "status_url": { "$ref": "urn:rag:schema:common-types:1#/$defs/Uri", "description": "GET /v1/jobs/{job_id} 절대 URL" },
        "events_url": { "$ref": "urn:rag:schema:common-types:1#/$defs/Uri", "description": "GET /v1/jobs/{job_id}/events SSE 절대 URL" }
      },
      "required": ["job_id", "status_url", "events_url"],
      "additionalProperties": false
    },
    "IngestBatchRequest": { "type": "array", "items": { "$ref": "#" }, "minItems": 1, "maxItems": 100, "description": "POST /v1/ingest/batch 본문: IngestRequest 배열(1..100, 바이블 §14). 배열 순서가 응답 jobs[] 순서다. 검증은 전체 원자적(한 건이라도 위반이면 400 + errors[].location.pointer /{index}/{field})." },
    "IngestBatchAccepted": {
      "type": "object",
      "description": "POST /v1/ingest/batch 202 응답 본문. jobs[i] 는 요청 배열 i 번째 항목의 접수 결과.",
      "properties": { "jobs": { "type": "array", "items": { "$ref": "#/$defs/IngestAccepted" }, "minItems": 1, "maxItems": 100 } },
      "required": ["jobs"],
      "additionalProperties": false
    }
  }
}
```

## Pydantic v2 모델

패키지 `rag_platform.contracts.ingest`. 기반 `ContractModel`·공용 타입·`H()`·`canonical_json`은 00 문서의 `rag_platform.contracts.common`에서, 열거는 `rag_platform.contracts.enums`에서 임포트한다. 열거는 00 Pydantic 절의 규약대로 **`StrEnum`** 이다(멤버 `.value`가 철자 그대로의 문자열; `str(member)` 형태에 의존하지 않는다). 원시 패턴은 스키마와 동일 문자열이다(00 §10.3 Pydantic 동치 게이트). §2 도입부의 결정("정규화는 스키마 검증 전")에 따라 정규화 검증기는 모두 `mode="before"`로 두어 `Annotated` 패턴·길이 제약이 정규화 결과에 적용되게 한다.

```python
from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator

from rag_platform.contracts.common import H, Acl, ContractModel, Ulid, _utc, canonical_json
from rag_platform.contracts.enums import DedupPolicy, EventType, Genre, PiiPolicy, PiiTokenizeMode, SplitHint

SourceUri = Annotated[str, Field(pattern=r"^[a-z][a-z0-9+.-]*://[^\s/@]*(/[^\s]*)?$", max_length=2048)]
WebhookUrl = Annotated[str, Field(pattern=r"^https?://[^\s/@]+(/[^\s]*)?$", max_length=2048)]
MediaType = Annotated[str, Field(pattern=r"^[a-z]+/[A-Za-z0-9!#$&^_.+-]+$")]
Bcp47 = Annotated[str, Field(pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")]
Date = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
DocType = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
CredentialsRef = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*:[^\s]{1,240}$", min_length=1, max_length=256)]
IdempotencyKey = Annotated[str, Field(pattern=r"^[\x21-\x7E]+$", min_length=1, max_length=255)]
Author = Annotated[str, Field(min_length=1, max_length=256)]   # 스키마 IngestMetadata.authors.items
Tag = Annotated[str, Field(min_length=1, max_length=128)]      # 스키마 IngestMetadata.tags.items

_META_KEY = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_OVERRIDE_KEY = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
_WS = re.compile(r"\s+")
BODY_MAX_BYTES = 65_536          # 바이블 §5.1 "64KB(본문)" — V1 (a) 요청 바이트, (b) 저장 인스턴스 canonical_json 둘 다
METADATA_MAX_BYTES = 16_384      # 바이블 §5.1 "metadata 16KB"
BATCH_MAX_ITEMS = 100            # 바이블 §14
CALLBACK_EVENTS: frozenset[str] = frozenset({
    "job.state.changed", "ingest.document.fetched", "ingest.document.parsed", "ingest.document.normalized",
    "ingest.document.chunked", "ingest.document.enriched", "ingest.document.embedded", "ingest.document.indexed",
    "ingest.document.retried", "ingest.document.failed", "index.commit.published", "index.commit.rolled_back",
})


def _nfc_trim(value: Any) -> str:
    """§6 정규화(스키마 검증 전, mode="before"): NFC, 양끝 trim, 내부 공백 1칸. 결과가 비면 contract.violation."""
    if not isinstance(value, str):
        raise ValueError("contract.violation: expected string")
    out = _WS.sub(" ", unicodedata.normalize("NFC", value)).strip()
    if not out:
        raise ValueError("contract.violation: empty after normalization")
    return out


class IngestMetadata(ContractModel):
    """바이블 §5.4 metadata.* 행. 모든 필드 N(생략, null 금지). 상한은 02 SourceMetadata 와 동일(V10)."""

    title: str | None = Field(default=None, min_length=1, max_length=512, description="문서 제목")
    authors: list[Author] | None = Field(default=None, max_length=64, description="작성자·작성 기관")
    doc_date: Date | None = Field(default=None, description="YYYY-MM-DD; 필터 doc_date")
    doc_type: DocType | None = Field(default=None, description="snake_case keyword(변환 없음, 위반은 400); 필터 doc_type")
    department: str | None = Field(default=None, min_length=1, max_length=256, description="필터 department")
    language_hint: Bcp47 | None = Field(default=None, description="기본 ko; 필터 lang 의 문서 기본값")
    tags: list[Tag] | None = Field(default=None, max_length=64, description="정확 일치 keyword; 필터 tags")
    genre: Genre | None = Field(default=None, description="청커 장르 라우팅; 생략 시 unknown")
    custom: dict[str, str | int | float | bool] | None = Field(default=None, max_length=64, description="테넌트 정의 keyword 메타")

    # 정규화 검증기는 모두 mode="before": Annotated 패턴·길이·uniqueItems 동치 검사는 정규화 결과에 적용된다(§2 도입부).
    @field_validator("title", "department", mode="before")
    @classmethod
    def _norm_text(cls, v: Any) -> Any:
        return _nfc_trim(v)

    @field_validator("authors", "tags", mode="before")
    @classmethod
    def _norm_list(cls, v: Any) -> Any:
        if not isinstance(v, list):
            return v  # 타입 오류는 표준 검증이 보고
        out: list[str] = []
        for item in v:
            n = _nfc_trim(item)
            if n not in out:  # 순서 보존 중복 제거 → 스키마 uniqueItems 동치
                out.append(n)
        return out

    @field_validator("language_hint", mode="before")
    @classmethod
    def _norm_lang(cls, v: Any) -> Any:
        if not isinstance(v, str):
            return v
        parts = v.strip().split("-")
        return "-".join([parts[0].lower()] + [p.upper() if len(p) == 2 else p for p in parts[1:]])

    @field_validator("custom", mode="before")
    @classmethod
    def _custom(cls, v: Any) -> Any:
        if not isinstance(v, dict):
            return v
        out: dict[str, Any] = {}
        for key, val in v.items():
            if not isinstance(key, str) or not _META_KEY.match(key):
                raise ValueError(f"contract.violation: custom key {key!r} must match ^[a-z][a-z0-9_]{{0,63}}$")
            if isinstance(val, str):
                val = _nfc_trim(val)
                if len(val) > 1024:
                    raise ValueError("contract.violation: custom string value longer than 1024")
            elif isinstance(val, bool):
                pass
            elif isinstance(val, (int, float)):
                if isinstance(val, float) and not math.isfinite(val):
                    raise ValueError("contract.violation: custom number must be finite")
            else:
                raise ValueError("contract.violation: custom value must be string | number | boolean")
            out[key] = val
        return out

    @model_validator(mode="after")
    def _size(self) -> "IngestMetadata":
        if len(canonical_json(self.model_dump(mode="json", exclude_none=True)).encode("utf-8")) > METADATA_MAX_BYTES:
            raise ValueError("contract.violation: metadata exceeds 16KB")
        return self


class IngestCallback(ContractModel):
    webhook_url: WebhookUrl = Field(description="테넌트 등록 구독 URL과 일치해야 한다(§2.4)")
    events: list[EventType] | None = Field(default=None, min_length=1, max_length=12, description="이 잡이 발행하는 12종 부분집합")

    @field_validator("events")
    @classmethod
    def _subset(cls, v: list[EventType]) -> list[EventType]:
        if len(set(v)) != len(v):
            raise ValueError("contract.violation: callback.events must be unique")
        if bad := [e for e in v if e.value not in CALLBACK_EVENTS]:  # StrEnum: str(e) 가 아니라 .value 로 대조
            raise ValueError(f"contract.violation: callback.events not emitted by ingest job: {bad}")
        return v


class IngestRequest(ContractModel):
    """바이블 §5.4 IngestRequest. 봉투 없음; tenant_id 는 SecurityContext, request_id 는 서버 발급."""

    schema_version: str = Field(pattern=r"^1\.(0|[1-9]\d*)\.(0|[1-9]\d*)$", description="1.x 만 수용")
    request_id: Ulid = Field(json_schema_extra={"readOnly": True}, description="서버 발급; 본문에 오면 400")
    collection_id: Ulid = Field(description="프로파일이 고정된 컬렉션")
    source_uri: SourceUri = Field(description="절대 URI, userinfo 금지; 스킴·호스트는 fetch 가 EgressPolicy 로 판정")
    media_type_hint: MediaType | None = Field(default=None, description="힌트만; 시그니처 판정 우선")
    external_id: str | None = Field(default=None, min_length=1, max_length=512, description="document_id 재사용 키")
    external_version: str | None = Field(default=None, min_length=1, max_length=256, description="원천 버전 라벨(참고)")
    metadata: IngestMetadata | None = Field(default=None, description="생략 시 {}")
    acl: Acl = Field(description="문서 단위 ACL(D-09)")
    pii_policy: PiiPolicy | None = Field(default=None, description="생략 시 컬렉션 기본값")
    pii_tokenize_mode: PiiTokenizeMode | None = Field(default=None, description="pii_policy=tokenize 일 때만")
    credentials_ref: CredentialsRef | None = Field(default=None, description="{provider}:{path} 간접 참조")
    allow_distribution_documents: bool | None = Field(default=None, description="테넌트 정책과 AND")
    llm_enrichment_allowed: bool | None = Field(default=None, description="테넌트·컬렉션 정책과 AND")
    dedup_policy: DedupPolicy | None = Field(default=None, description="생략 시 skip_if_same_hash")
    priority: int | None = Field(default=None, ge=0, le=9, description="생략 시 5")
    callback: IngestCallback | None = None
    split_hint: SplitHint | None = Field(default=None, description="생략 시 none")
    profile_overrides: dict[str, Any] | None = Field(default=None, max_length=16, description="컬렉션 프로파일 허용 키만(422 profile.invalid)")
    deadline_at: datetime | None = Field(default=None, description="초과 시 queued → cancelled")
    requested_at: datetime = Field(description="클라이언트 요청 시각(RFC 3339 UTC); 멱등 지문에 포함")

    _requested_utc = field_validator("requested_at")(_utc)
    _external_id_norm = field_validator("external_id", mode="before")(_nfc_trim)

    @field_validator("profile_overrides")
    @classmethod
    def _override_shape(cls, v: dict[str, Any]) -> dict[str, Any]:
        for key, val in v.items():
            if len(key) > 128 or not _OVERRIDE_KEY.match(key):
                raise ValueError(f"contract.violation: profile_overrides key {key!r} is not a profile path")
            if key == "parse.pdf.route" and not (isinstance(val, str) and _META_KEY.match(val)):
                raise ValueError("contract.violation: parse.pdf.route must be a route name")
            if key == "enrich.generated_prefix" and not (isinstance(val, dict) and set(val) == {"enabled"} and isinstance(val["enabled"], bool)):
                raise ValueError("contract.violation: enrich.generated_prefix must be {enabled: bool}")
        return v

    @model_validator(mode="after")
    def _invariants(self) -> "IngestRequest":
        if self.pii_tokenize_mode is not None and self.pii_policy != PiiPolicy.tokenize:
            raise ValueError("contract.violation: pii_tokenize_mode requires pii_policy=tokenize (IR-6)")
        if self.deadline_at is not None and _utc(self.deadline_at) <= self.requested_at:
            raise ValueError("contract.violation: deadline_at must be after requested_at (IR-7)")
        if self.split_hint in (SplitHint.json_array, SplitHint.zip_members) and "#" in self.source_uri:
            raise ValueError("contract.violation: source_uri must not carry a fragment when split_hint != none (IR-13)")
        if self.acl.deny_principals and "tenant:*" in self.acl.deny_principals:
            # 이 문서 추가 규칙 A4(잠정; 공용 Acl 스키마는 허용 — 미해결 이슈 14)
            raise ValueError("contract.violation: tenant:* is not allowed in deny_principals (IR-5, A4)")
        # V1 (b): 정규화·request_id 주입 후 저장 인스턴스의 canonical_json 상한. (a) 요청 바이트는 from_wire 가 검사한다.
        if len(canonical_json(self.model_dump(mode="json", exclude_none=True)).encode("utf-8")) > BODY_MAX_BYTES:
            raise ValueError("contract.violation: IngestRequest canonical_json exceeds 64KB (V1(b), IR-9)")
        return self

    @classmethod
    def from_wire(cls, body: dict[str, Any], request_id: str, *, body_bytes: int) -> "IngestRequest":
        """API 경계(00 §10.1): 요청 바이트 상한(V1(a)) → 보안 필드(422)·readOnly 필드(400) 존재 거부 → 서버 발급
        request_id 주입 → 정규화(mode="before" 검증기)·스키마 동치 검증·불변식. body_bytes 는 Content-Length 또는 실제 수신 바이트."""
        if body_bytes > BODY_MAX_BYTES:
            raise ValueError("contract.violation: request body exceeds 64KB (V1(a), IR-9)")
        if "tenant_id" in body:
            # E1·00 §10.1: 상태 422. 코드는 auth.tenant_mismatch 채택 전 contract.violation(미해결 이슈 7)
            raise ValueError("contract.violation: tenant_id must not appear in the body (E1, 422)")
        if "request_id" in body:
            raise ValueError("contract.violation: request_id is server-issued (readOnly, 400)")
        return cls.model_validate({**body, "request_id": request_id})


def idempotency_fingerprint(endpoint_path: str, wire_body: Any) -> str:
    """request_hash = H("idem", endpoint_path, canonical_json(wire_body)) — 서버 주입 전 본문 기준(§4)."""
    return H("idem", endpoint_path, canonical_json(wire_body))


class IngestAccepted(ContractModel):
    """202 응답 본문(D-08, 바이블 §14 {job_id, status_url, events_url}). 같은 Idempotency-Key 재생(200)도 동일 본문."""

    job_id: Ulid
    request_id: Ulid | None = Field(default=None, description="서버 발급 IngestRequest.request_id(N; 바이블 §14 반영 제안, 미해결 이슈 1)")
    document_id: Ulid | None = Field(default=None, description="접수 시 확정(N; 바이블 §14 반영 제안, 미해결 이슈 1)")
    status_url: str = Field(min_length=1, description="GET /v1/jobs/{job_id} 절대 URL")
    events_url: str = Field(min_length=1, description="GET /v1/jobs/{job_id}/events 절대 URL")

    @model_validator(mode="after")
    def _urls(self) -> "IngestAccepted":
        if not self.status_url.endswith(f"/v1/jobs/{self.job_id}") or self.events_url != self.status_url + "/events":
            raise ValueError("contract.violation: status_url/events_url must point at job_id (IR-14)")
        return self


class IngestBatchAccepted(ContractModel):
    jobs: list[IngestAccepted] = Field(min_length=1, max_length=BATCH_MAX_ITEMS, description="요청 배열과 같은 순서")
```

## 예시

모든 예시는 `schemas/ingest-request.schema.json`(공용 `$defs`는 `common-types.schema.json`)으로 검증되는 골든 인스턴스다(00 §10.3). 예시 1~3은 **접수 후 저장되는 계약 인스턴스**(정규화 완료)이므로 서버 발급 `request_id`를 포함한다 — 클라이언트 전송 본문은 같은 내용에서 `request_id`만 없다. 예시 4·5의 `request_id`·`document_id`는 선택(N) 필드가 값을 가진 경우다(서버는 항상 채우지만 클라이언트는 부재를 허용해야 한다, §3.1). ID는 형식 규약을 지키는 플레이스홀더(ULID 26자 Crockford 대문자)다. `dry_run` 예시는 의도적으로 없다(범위 절 제외 목록, 미해결 이슈 9).

### 예시 1 — 공공기관 HWPX 규정 문서 1건(`POST /v1/ingest`, 제한 공개·공개 유예·콜백)

```json
{
  "schema_version": "1.0.0",
  "request_id": "01J9ZQ7B8C9D0E1F2G3H4J5K6M",
  "collection_id": "01J9ZQ5A1B2C3D4E5F6G7H8J9K",
  "source_uri": "s3://mois-records/regulations/2026/records-management-rule-2026-09.hwpx",
  "media_type_hint": "application/hwp+zip",
  "external_id": "MOIS-REG-2026-0917",
  "external_version": "\"3f2a9c1e\"",
  "metadata": {
    "title": "공공기록물 관리에 관한 법률 시행규칙 일부개정안",
    "authors": ["행정안전부 국가기록원"],
    "doc_date": "2026-09-17",
    "doc_type": "regulation",
    "department": "행정안전부",
    "language_hint": "ko",
    "tags": ["기록물", "시행규칙", "개정안"],
    "genre": "law_article",
    "custom": { "law_name": "공공기록물 관리에 관한 법률", "revision_no": 12, "is_draft": true }
  },
  "acl": {
    "allow_principals": ["group:mois_records", "user:kim.minsu@example.go.kr"],
    "deny_principals": [],
    "visibility": "restricted",
    "classification": "internal",
    "embargo_until": "2026-10-01T00:00:00.000Z",
    "expires_at": null
  },
  "pii_policy": "mask",
  "allow_distribution_documents": false,
  "llm_enrichment_allowed": false,
  "priority": 5,
  "callback": {
    "webhook_url": "https://hooks.example.go.kr/rag/ingest",
    "events": ["job.state.changed", "ingest.document.indexed", "ingest.document.failed"]
  },
  "requested_at": "2026-09-22T09:00:00.000Z"
}
```

### 예시 2 — 배치(`POST /v1/ingest/batch`): 보도자료 PDF(공개) + 연차보고서 PDF(필터 메타·PII 토큰화·거부 주체)

```json
[
  {
    "schema_version": "1.0.0",
    "request_id": "01J9ZQ8R2S3T4V5W6X7Y8Z9A0B",
    "collection_id": "01J9ZQ5A1B2C3D4E5F6G7H8J9K",
    "source_uri": "https://open.example.go.kr/files/2026/press/press-release-2026-09-15.pdf",
    "media_type_hint": "application/pdf",
    "external_id": "MOIS-PR-2026-0915",
    "metadata": {
      "title": "2026년 지방자치단체 데이터 개방 확대 계획 발표",
      "doc_date": "2026-09-15",
      "doc_type": "press_release",
      "department": "행정안전부",
      "language_hint": "ko",
      "tags": ["보도자료", "데이터개방"],
      "genre": "narrative"
    },
    "acl": { "allow_principals": ["tenant:*"], "visibility": "public", "classification": "public" },
    "requested_at": "2026-09-22T09:05:00.000Z"
  },
  {
    "schema_version": "1.0.0",
    "request_id": "01J9ZQ8R2S3T4V5W6X7Y8Z9A0C",
    "collection_id": "01J9ZQ5A1B2C3D4E5F6G7H8J9K",
    "source_uri": "s3://mois-records/reports/2026/local-data-open-annual-report-2025.pdf",
    "media_type_hint": "application/pdf",
    "external_id": "MOIS-RPT-2025-ANNUAL-DATA",
    "external_version": "2025.12-final",
    "metadata": {
      "title": "2025년 지방자치단체 데이터 개방 연차보고서",
      "authors": ["행정안전부 공공데이터정책과"],
      "doc_date": "2025-12-30",
      "doc_type": "report",
      "department": "행정안전부",
      "language_hint": "ko",
      "tags": ["연차보고서", "공공데이터"],
      "genre": "outline_report",
      "custom": { "fiscal_year": 2025, "program_code": "DATA-OPEN-2025" }
    },
    "acl": {
      "allow_principals": ["group:mois_data_policy", "group:mois_records"],
      "deny_principals": ["user:contractor.temp@example.go.kr"],
      "visibility": "tenant",
      "classification": "internal"
    },
    "pii_policy": "tokenize",
    "pii_tokenize_mode": "encrypt",
    "priority": 3,
    "requested_at": "2026-09-22T09:05:00.000Z"
  }
]
```

### 예시 3 — 재처리 옵션: 암호화 ZIP 묶음(`credentials_ref`) + `reindex_always` + `zip_members` + `profile_overrides` + `deadline_at`

```json
{
  "schema_version": "1.0.0",
  "request_id": "01J9ZQ9C0D1E2F3G4H5J6K7M8N",
  "collection_id": "01J9ZQ5A1B2C3D4E5F6G7H8J9K",
  "source_uri": "s3://mois-records/archives/2026/q3-notices-bundle.zip",
  "media_type_hint": "application/zip",
  "external_id": "MOIS-NOTICE-2026-Q3-BUNDLE",
  "metadata": { "title": "2026년 3분기 공고문 묶음", "doc_type": "notice", "department": "행정안전부", "language_hint": "ko", "genre": "form" },
  "acl": { "allow_principals": ["group:mois_records"], "visibility": "tenant", "classification": "internal" },
  "credentials_ref": "openbao:secret/data/tenants/01J9ZQ4K7X2M8N3P5R6S7T8V9W/sources/archive-zip-password",
  "dedup_policy": "reindex_always",
  "split_hint": "zip_members",
  "profile_overrides": { "parse.pdf.route": "pdf_fast_cpu", "enrich.generated_prefix": { "enabled": false } },
  "priority": 2,
  "deadline_at": "2026-09-23T09:00:00.000Z",
  "requested_at": "2026-09-22T09:10:00.000Z"
}
```

### 예시 4 — 202 `IngestAccepted`(예시 1의 응답; 같은 키 재전송의 200 본문도 동일)

```json
{
  "job_id": "01J9ZQ7C9D0E1F2G3H4J5K6M7N",
  "request_id": "01J9ZQ7B8C9D0E1F2G3H4J5K6M",
  "document_id": "01J9ZQ6M0N1P2Q3R4S5T6V7W8X",
  "status_url": "https://rag.example.go.kr/v1/jobs/01J9ZQ7C9D0E1F2G3H4J5K6M7N",
  "events_url": "https://rag.example.go.kr/v1/jobs/01J9ZQ7C9D0E1F2G3H4J5K6M7N/events"
}
```

### 예시 5 — 202 `IngestBatchAccepted`(예시 2의 응답)

```json
{
  "jobs": [
    { "job_id": "01J9ZQ8S3T4V5W6X7Y8Z9A0B1C", "request_id": "01J9ZQ8R2S3T4V5W6X7Y8Z9A0B", "document_id": "01J9ZQ8T4V5W6X7Y8Z9A0B1C2D", "status_url": "https://rag.example.go.kr/v1/jobs/01J9ZQ8S3T4V5W6X7Y8Z9A0B1C", "events_url": "https://rag.example.go.kr/v1/jobs/01J9ZQ8S3T4V5W6X7Y8Z9A0B1C/events" },
    { "job_id": "01J9ZQ8S3T4V5W6X7Y8Z9A0B1D", "request_id": "01J9ZQ8R2S3T4V5W6X7Y8Z9A0C", "document_id": "01J9ZQ8T4V5W6X7Y8Z9A0B1C2E", "status_url": "https://rag.example.go.kr/v1/jobs/01J9ZQ8S3T4V5W6X7Y8Z9A0B1D", "events_url": "https://rag.example.go.kr/v1/jobs/01J9ZQ8S3T4V5W6X7Y8Z9A0B1D/events" }
  ]
}
```

### 예시 6 — 422 `api.idempotency_payload_mismatch`(`ProblemDetails`, 13 문서 스키마)

```json
{
  "type": "urn:rag:error:api.idempotency_payload_mismatch",
  "title": "Idempotency payload mismatch",
  "status": 422,
  "detail": "Idempotency-Key was first used with a different request fingerprint for POST /v1/ingest; send the same body or use a new key",
  "instance": "/v1/ingest",
  "code": "api.idempotency_payload_mismatch",
  "retryable": false,
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "request_id": "01J9ZQ9D1E2F3G4H5J6K7M8N9P"
}
```

## 불변식(Invariants)

위반 시 오류 코드는 별도 표기가 없으면 `contract.violation`(400, 비재시도; [13-error-model](13-error-model.md) §3.2)이다. 00 문서의 I-6·I-8·I-11·I-12·I-13·I-28은 이 계약에도 그대로 적용된다. I-4(봉투의 `tenant_id`·`collection_id`)는 봉투가 없는 이 계약에 그대로 적용되지 않는다 — `collection_id`는 갖되 `tenant_id`는 서버 주입 `SecurityContext`로 대체된다(00 §3.1, I-13).

| # | 불변식 | 출처 |
|---|--------|------|
| IR-1 | `schema_version`은 `1.x.y`(major 1)이며 `$id` `urn:rag:schema:ingest-request:1`과 함께 움직인다 | 바이블 §5, §6.4 |
| IR-2 | `request_id`는 서버 발급 ULID다. 클라이언트 본문에 `request_id`가 있으면 400 `contract.violation`, `tenant_id`(보안 필드)가 있으면 **422**(E1, 00 §10.1; 코드는 `auth.tenant_mismatch` 채택 전 `contract.violation`, 미해결 이슈 7) | 바이블 §5.4, E1, 00 §8.2·§10.1 |
| IR-3 | `collection_id` ∈ `SecurityContext.collection_ids`; 아니면 403 `auth.forbidden`(존재 비노출) | E2 |
| IR-4 | `source_uri`는 절대 URI, authority에 userinfo 없음, 공백 없음, ≤ 2,048자. 스킴·호스트 판정은 `fetch`(E16)만 수행하고 `fetch.scheme_unsupported`/`fetch.egress_denied`(비재시도)로 실패한다 | 바이블 §5.4, §10.3 E16 |
| IR-5 | `acl`: 주체 문자열 형식(`$defs/PrincipalString`), 각 목록 ≤ 1,024(초과 확장은 `auth.too_many_principals` 422), 거부 우선, `embargo_until < expires_at`(앵커 규칙); `deny_principals`에 `tenant:*` 없음(이 문서 추가 규칙 A4, 잠정 — 미해결 이슈 14) | 바이블 §10.1, 00 I-12, §7 |
| IR-6 | `pii_tokenize_mode`가 있으면 `pii_policy`가 있고 `= tokenize`다(`dependentRequired` + `if/then`) | 바이블 §5.4 |
| IR-7 | `requested_at`·`deadline_at`은 RFC 3339 UTC `Z`; `deadline_at`이 있으면 `deadline_at > requested_at` | 바이블 §6.3, §11.5 |
| IR-8 | `metadata` 키는 예약 9종(`title, authors, doc_date, doc_type, department, language_hint, tags, genre, custom`)만; `custom` 키는 `^[a-z][a-z0-9_]{0,63}$` ≤ 64개, 값은 스칼라; `doc_type`은 snake_case; 저장 인스턴스의 `tags`·`authors`는 중복 없음(정규화가 스키마 검증 전에 순서 보존 중복 제거를 수행, §2 도입부) | 바이블 §5.4, §5.7 `FilterableField`, §6, 02 §2.4 |
| IR-9 | 요청 바이트 ≤ 65,536(API 경계, 정규화·주입 전) **그리고** 저장 인스턴스 `canonical_json` ≤ 65,536바이트(정규화·주입 후); `metadata` `canonical_json` ≤ 16,384바이트; 배치 1..100건 | 바이블 §5.1, §14, V1 |
| IR-10 | 본문 어디에도 비밀 값이 없다: `credentials_ref`는 `{provider}:{path}` 참조이고 `source_uri` userinfo와 스키마 밖 키는 거부된다. `credentials_ref` 값은 로그·트레이스·이벤트·`detail`에 나타나지 않는다 | 바이블 §5.4, §6.6, E13 |
| IR-11 | `callback.webhook_url`은 `http(s)` 절대 URL이고 테넌트 등록 구독과 일치한다; `callback.events`는 12종 부분집합, 중복 없음 | 바이블 §5.4, §13.1 `subscriptions`, E16 |
| IR-12 | `profile_overrides` 키는 프로파일 경로 형식이고 컬렉션 프로파일 허용 집합에 속한다; 아니면 422 `profile.invalid` | 바이블 §5.4 |
| IR-13 | `split_hint ∈ {json_array, zip_members}`이면 `source_uri`에 `#`(fragment)이 없다. (멤버 `source_uri`·`external_id` 합성 규약은 불변식이 아니라 §5.2 잠정안이며 미해결 이슈 5로 바이블 §6.1 등재를 제안한다) | 바이블 §5.4 `split_hint`, §5.2 |
| IR-14 | 멱등성(단건 `POST /v1/ingest`): 같은 `(tenant_id, Idempotency-Key)` + 같은 `request_hash`는 같은 `job_id`(·`request_id`)를 돌려준다(200); 다른 `request_hash`는 422 `api.idempotency_payload_mismatch`; 접수 미커밋 중복은 409 `api.idempotency_conflict`. 배치는 같은 의미론을 따르되 원장 저장·재생 재구성은 미해결 이슈 12의 잠정안에 따른다. `IngestAccepted.status_url`은 `/v1/jobs/{job_id}`로 끝나고 `events_url = status_url + "/events"` | D-08, 바이블 §13.1, §4 |
| IR-15 | `document_id`는 접수 트랜잭션에서 `(tenant_id, collection_id, external_id or source_uri)`로 결정적으로 확정되며 같은 `document_id`의 활성 잡은 한 번에 하나만 `running`이다 | 바이블 §11.2, E17 |
| IR-16 | `dedup_policy` 생략 = `skip_if_same_hash`; `reindex_always`는 항상 새 `index_generation`을 만든다(`record_id` 세대 포함) | 바이블 §5.4, §11.4 |
| IR-17 | 정규화는 접수 시 1회·멱등·스키마 검증 전이며 저장 인스턴스는 정규화된 값을 담는다; `fetch`는 이를 복사해 `metadata_hash = H("meta", canonical_json(metadata))`, `acl_hash = H("acl", canonical_json(acl))`를 계산한다. 해시 입력은 값 없는 선택 필드(생략·`null`)를 제거한 직렬화다(02 §3, 02 미해결 이슈 9) | §6, 바이블 §6.2, 02 §3 |
| IR-18 | 저장된 `IngestRequest` 산출물의 `ArtifactRef.schema_type = "IngestRequest"`, `media_type = application/vnd.rag.ingest-request+json`, `blake3`·`size_bytes`는 저장 바이트 기준 | 00 I-2·I-3 |

## 산출물 저장 규약

**결정:** API는 정규화·주입이 끝난 `IngestRequest` 인스턴스를 접수 트랜잭션 **커밋 전에** 오브젝트 스토리지에 저장(read-after-write 재검증)하고, 같은 트랜잭션에 `artifacts(tenant_id, stage_key)` 행을 기록한 뒤 `ArtifactRef`만 오케스트레이터에 넘긴다(바이블 §4.1 경계 페이로드, §11.1 `req_ref`, §13.1 `artifacts`; [ADR-0037](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md)). 커밋된 `queued` 잡에 요청 산출물이 없는 상태는 존재하지 않는다.

| 항목 | 규약 |
|------|------|
| 순서·실패 처리 | (1) `document_id` 조회·발급(§10; `scope_key`에 필요) → (2) put + read-after-write(`blake3`·`size_bytes` 재검증) → (3) PG 트랜잭션(`documents` INSERT(신규 시)·`jobs`·`idempotency_keys`·`artifacts`) 커밋 → (4) 디스패처 큐잉(§1 다이어그램과 동일). (2) 실패 → 접수하지 않고 503(`ProblemDetails`; 코드는 미해결 이슈 13), `idem:` 예약 해제. (3) 실패 → 롤백, put한 오브젝트는 고아(콘텐츠 주소이므로 재시도 시 재사용되거나 `maintenance.cleanup.v1`이 `artifacts` 행 없는 `ingest-request/` 키를 정리 — 바이블 §11.2 행 추가 제안, 미해결 이슈 3). 신규 문서 동시 경합으로 `documents` UNIQUE에 걸리면 기존 행의 `document_id`로 (1)~(3)을 1회 재수행한다 |
| 오브젝트 키 | `tenants/{tenant_id}/artifacts/ingest-request/{stage_key[:2]}/{stage_key}.json`(바이블 §13.3) |
| `stage_key` | API는 스테이지가 아니므로 입력 `ArtifactRef`가 없다. `stage_key = H("stage", "accept", scope_key, request_blake3, api_fingerprint)`, `scope_key = f"{tenant_id}/{collection_id}/{document_id}"`, `request_blake3 = blake3_hex(canonical bytes)`, `api_fingerprint = H("producer", "api.ingest", api_version, "", "", "")`(바이블 §6.2 규칙 적용; 구성은 미해결 이슈 3) |
| `ArtifactRef` | `{uri, blake3, media_type: "application/vnd.rag.ingest-request+json", schema_type: "IngestRequest", schema_version: "1.0.0", size_bytes, stage_key}`; `blake3`·`size_bytes`는 저장 바이트 기준(00 §9.2, read-after-write 재검증) |
| 압축 | 미정(00 U-4). 확정 전까지 압축 없이 저장한다; zstd는 후보이며 도입 시 `ArtifactRef.content_encoding`(N) 추가와 함께 ADR로 결정 |
| 역참조 | `SourceDocument.lineage_refs`는 `{}`이므로(00 §3.2) 요청 산출물은 계보가 아니라 `jobs.request_id`·`artifacts(tenant_id, stage_key)`로 도달한다. `SourceDocument.request_id`가 역참조 키다 |
| 보존 | 잡 원장과 같은 보존 기간(운영 정책, [../09-operations/07-backup-and-disaster-recovery.md](../09-operations/07-backup-and-disaster-recovery.md)). 재시도(`POST /v1/jobs/{job_id}/retry`)는 같은 산출물을 다시 읽는다 |

## 버전 이력

이 표는 계약 `schema_version`(`urn:rag:schema:ingest-request:1`)의 이력이다. 문서 버전(frontmatter `version` 0.1.0)과 독립이다.

| `schema_version` | 날짜 | 내용 |
|------------------|------|------|
| 1.0.0 | 2026-09-22 | 초판. 바이블 v1.2.0 §5.4 `IngestRequest` 표 전 필드, §5.7 열거 참조, §14 202 응답(`IngestAccepted{job_id, status_url, events_url}` + `request_id`·`document_id` N, 배치), `Idempotency-Key` 규약(D-08). 계약 전용 `$defs`: `IngestMetadata`(`authors` ≤ 64, `tags` 항목 ≤ 128), `CustomMetadata`(키 ≤ 64), `IngestCallback`, `ProfileOverrides`, `CredentialsRef`(≤ 256, 02와 동일), `IdempotencyKey`, `IngestAccepted`, `IngestBatchRequest`, `IngestBatchAccepted`. 리뷰 1차 반영(2026-09-22): `IngestAccepted.request_id` Y→N, `CredentialsRef` 512→256, 배열 상한 02 정합 — 게시 전 개정이므로 `schema_version` 불변 |

호환성 규칙(정본 [14-schema-versioning-and-compatibility](14-schema-versioning-and-compatibility.md), 바이블 §1.2): 선택 필드·열거값·`callback.events` 부분집합 **추가**는 minor(가산만, `schema_version` 1.x → 1.(x+1)); 필드 제거·필수화·의미 변경(예 `request_id` 클라이언트 발급으로 전환, `dedup_policy` 기본값 변경), 패턴 강화, `IngestBatchRequest`의 배열 → 객체 전환은 major(`$id` `:2`). 클라이언트 SDK는 `schema_version`을 항상 명시하고 서버는 `Capabilities.contracts_compat` 범위 밖 버전을 400 `contract.violation`으로 거부한다(13 §3.3 `contract.version_unsupported` 채택 전).

## 결정 사항 요약

- **결정:** `IngestRequest`는 봉투 없는 클라이언트 입력 계약이며 바이블 §5.4 표를 같은 철자·필수로 옮겼다. `tenant_id`는 본문에 없고(있으면 **422**, E1·00 §10.1), `request_id`는 서버 발급 `readOnly`(있으면 400)다([ADR-0027](../06-adr/0027-security-context-injection-and-acl-enforcement-points.md), [ADR-0036](../06-adr/0036-naming-and-identifier-conventions.md)).
- **결정:** `Idempotency-Key` 필수, draft-07 의미론(200/409/422), 스코프 `(tenant_id, key)`, 판정 정본 PostgreSQL `idempotency_keys` + 동일 트랜잭션 `jobs` INSERT, `request_hash = H("idem", endpoint_path, canonical_json(wire_body))`, TTL 24h(초안 목표)([ADR-0017](../06-adr/0017-event-delivery-outbox-cloudevents-no-broker.md), [ADR-0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md)). 배치(키 1개 ↔ 잡 N개)의 원장 저장은 바이블 §13.1 정본과 정합하는 잠정안(§4)이며 정본 개정 제안은 미해결 이슈 12.
- **결정:** 202 본문은 `IngestAccepted{job_id, status_url, events_url}`(브리프 D-08·바이블 §14 그대로 Y) + `request_id?`·`document_id?`(N, 반영 제안); 배치는 `IngestRequest` 배열 1..100 → `IngestBatchAccepted{jobs[]}`, 검증·접수 원자적.
- **결정:** `dedup_policy=skip_if_same_hash`에서 같은 `content_hash`·다른 `acl_hash`/`metadata_hash`는 재임베딩 없는 payload 갱신 경로로 처리하고 `doc_version`은 불변이다([ADR-0005](../06-adr/0005-doc-version-content-hash-only-and-acl-payload-update.md)); `reindex_always`는 항상 새 세대다([ADR-0026](../06-adr/0026-index-commit-generation-saga-and-ledger.md)).
- **결정:** `split_hint` 멤버는 별개 문서(자기 `document_id`·`SourceDocument`·`IndexCommit`, 요청 정책 상속)이고 `split_hint ≠ none`이면 `source_uri`에 fragment가 없다. **미정:** 멤버 `source_uri`/`external_id` 합성 규약(`#member={locator}`, percent-encoding)은 §5.2 잠정안이며 04-pipelines/02·03 확정 후 바이블 §6.1 등재를 제안한다(미해결 이슈 5).
- **결정:** 메타데이터 정규화는 접수 시 값 수준 1회·**스키마 검증 전**(NFC·trim·공백 축약·순서 보존 중복 제거·BCP 47 대소문자; 스키마 `uniqueItems`·패턴은 정규화 결과에 적용), 기본값은 채우지 않으며, `doc_type`은 snake_case 패턴, `custom` 키는 snake_case ≤ 64개·스칼라 값(상한은 02 `SourceMetadata`와 동일)이다.
- **결정:** ACL 입력은 바이블 §10.1 그대로 적용한다. `deny_principals`에 `tenant:*` 금지(A4)와 `restricted`+빈 `allow_principals`의 "잠금" 의미(A6)는 **이 문서 추가 규칙(잠정)** 이며 바이블 §10.1·00 §4.4 등재를 제안한다(미해결 이슈 14).
- **결정:** API는 `source_uri` 문법(userinfo 금지)만 검증하고 스킴·호스트·IP·리다이렉트 판정은 단일 지점 E16(`fetch`)이 `EgressPolicy`로 수행한다([ADR-0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md)). 비밀은 `credentials_ref` 간접 참조만(형식 검증, ≤ 256자; provider 유효성은 KeyProvider 해소 시). `source_uri` 자체는 로그·트레이스·이벤트·`detail`에 기록하지 않는다(13 §9·§11).
- **결정:** `callback.webhook_url`은 테넌트 등록 구독 URL과 일치해야 하며 `callback.events`는 잡이 발행하는 12종으로 좁힌다.
- **결정:** 접수된 인스턴스는 접수 트랜잭션 **커밋 전에** `tenants/{tenant_id}/artifacts/ingest-request/` 아래 산출물로 저장(read-after-write)하고 같은 트랜잭션에 `artifacts` 행을 기록한 뒤 `ArtifactRef`만 오케스트레이터에 넘긴다; put 실패는 접수 없음 + 503; 압축은 00 U-4 확정까지 없음([ADR-0037](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md)).
- **결정:** 요청 크기 상한 64KB는 두 척도(요청 바이트, 저장 인스턴스 `canonical_json`)에 모두 적용한다(V1).

## 미해결 이슈

| # | 이슈 | 제안 |
|---|------|------|
| 1 | 바이블 §14 202 응답 `{job_id, status_url, events_url}`(= 브리프 D-08)에 `request_id`(§5.4는 "응답에 `job_id`와 함께 반환")와 접수 시 확정되는 `document_id`가 없다. 두 앵커가 상충하므로 이 문서는 둘 다 **N**으로 두었다(바이블 §5.1 "추가 필드는 N만", 브리프 우선) | 바이블 §14 `POST /v1/ingest` 행에 `request_id`·`document_id` 추가(minor; §5.4 문구와 정합) 후 이 문서에서 Y로 승격(계약 minor — 응답 필드 필수화는 클라이언트에 가산만이므로) |
| 2 | `request_id`가 바이블 §5.4에서 Y이면서 "서버 발급"이다. 클라이언트 전송 본문과 저장 인스턴스의 스키마가 다르다는 뜻이므로 이 문서는 `readOnly` + 본문 존재 시 400으로 해석했다(00 §10.1 "readOnly 필드 존재 거부 = `contract.violation` 400") | 바이블 §5.4 `request_id` 의미 열에 "`readOnly`; 본문 존재 시 400"을 명시(patch) |
| 3 | API가 생산하는 산출물(`IngestRequest`)의 `stage_key`·`Producer.plugin_id` 구성은 바이블 §4.1·§6.2에 없다(`api`는 확장 지점이 아님). 이 문서는 `H("stage", "accept", scope_key, request_blake3, api_fingerprint)`를 제안했다. `H()` 라벨 `idem`(멱등 지문)도 §6.2 표에 없다. 또 put 뒤 트랜잭션 롤백으로 생기는 고아 `ingest-request/` 오브젝트 정리 책임이 바이블 §11.2 `maintenance.cleanup.v1` 행에 없다 | 바이블 §6.2 표에 `accept` 산출물 키와 `idem` 라벨 등재(minor); §11.2 `maintenance.cleanup.v1` 행에 "`artifacts` 행 없는 접수 산출물 정리" 추가(patch) |
| 4 | `metadata.authors`는 `IndexRecord`에 투영되지 않고 `FilterableField`에도 없다. 작성 기관 필터 요구가 있으면 `department`와의 관계 정리가 필요하다 | 07 문서에서 `IndexRecord.authors`(N) 또는 `custom.authors` 관례 중 택1 제안 |
| 5 | `split_hint`의 (a) 분할 수행 스테이지(`fetch` vs `parse` 내부)와 자식 잡 생성 방식, (b) 멤버 `source_uri`/`external_id` 합성 규약(§5.2 잠정안 `{source_uri}#member={locator}`, `json[{i}]`/`zip:{member_path}`, locator NFC + RFC 3986 percent-encoding), (c) 멤버 상한(≤ 100) 초과 시 경고 코드(`fetch.*`/`parse.*` 카탈로그에 없음)가 미정이다. (b)는 `document_id` 확정 키에 영향하므로 이 문서가 단정하지 않았다 | 04-pipelines/02·03에서 (a)·(b) 확정 후 바이블 §4.2·§6.1 식별자 표(멤버 URI·ID 합성 행)·§5.7 갱신(minor); 경고 코드 후보 `parse.member_limit_exceeded`(—) |
| 6 | 접수 시점에 `source_uri` 스킴을 유효 `EgressPolicy`와 대조해 즉시 거부(fail-fast)할지는 미정이다. 이 문서는 판정 지점을 E16 하나로 유지했다. `file://`이 허용되는 "개발 프로파일"의 범위(`runtime.orchestrator: local` vs `lite` 전체)도 ADR-0038·15·09-operations/02 확정 전 미정이다 | 05-api/02에서 UX 요구가 확인되면 `api.egress_denied`(400, 비재시도) 제안 코드 ADR과 함께 도입; `file` 허용 범위는 15 문서 `EgressPolicy` 기본값 표에 고정 |
| 7 | 바이블 E1·00 §10.1은 본문 `tenant_id`를 **422**로 고정하지만 해당 카탈로그 코드가 없다(13 §3.3 `auth.tenant_mismatch` 제안). 이 문서는 상태 422 + 채택 전 대안 `contract.violation`을 쓰는데, 바이블 §5.7 카탈로그의 `contract.violation` HTTP 열은 `400/500`이라 코드·상태 매핑이 불일치한다 | 13 미해결 이슈와 공동: (a) `auth.tenant_mismatch`(422) 조기 채택(minor) 또는 (b) 바이블 §5.7 `contract.violation` 상태에 422 병기(patch). (a) 권고 |
| 8 | `callback.webhook_url`을 등록 구독과 URL 일치로 묶었다. `callback.subscription_id`(N)로 명시 참조하는 편이 견고하다 | 12·15 문서 합의 후 `callback.subscription_id` 추가(minor); URL 일치는 하위 호환 유지 |
| 9 | 요청 단위 `dry_run`(검증·`document_id` 확정만 수행, 잡 미생성)은 문서 outline에는 있었지만 브리프·바이블 §14에 없다. 선택(N) 필드 추가 자체는 허용되지만 응답 상태(202 → 200)·본문(`IngestDryRunResult`)·멱등 키 소비 여부까지 바뀌는 엔드포인트 의미 변경이므로 이 문서는 필드·예시를 두지 않고 범위 절 제외 목록에 명시했다 | 05-api/02에서 필요성 확인 시 `dry_run`(N, boolean, 기본 false) + 200 `IngestDryRunResult{request_id, document_id, normalized: IngestRequest}` + "`Idempotency-Key` 미소비"를 바이블 §14 행 개정(minor)과 함께 ADR로 제안 |
| 10 | `doc_type`을 snake_case 패턴으로 조였다(바이블은 `string`). 한국어 `doc_type` 값 요구가 있으면 패턴이 장애가 된다. `authors`(≤ 64)·`tags`(≤ 64, 항목 ≤ 128자)·`custom`(키 ≤ 64, 스칼라 값) 상한은 복사 대상 02 `SourceMetadata`와 같은 값으로 맞췄다(초안 목표; 바이블은 상한 없음) | 바이블 §5.4 `doc_type` 행에 패턴 명시(patch) 또는 이 문서 패턴 완화; `metadata.*` 상한은 바이블 §5.1 인라인 한계 열 또는 §5.4 표에 등재(patch)하여 01·02가 같은 정본을 참조 |
| 11 | 문서 식별 조회(§10)에서 `external_id` 없이 접수된 기존 문서를 뒤에 `external_id`를 붙여 재제출하면 새 문서가 된다(채택 없음) | 05-api/02·02-source-document에서 "`source_uri` 일치 시 `external_id` 채택(backfill)" 옵션 검토 |
| 12 | 배치 멱등성: 키 1개가 잡 N개를 덮지만 바이블 §13.1은 `jobs.idempotency_key UNIQUE(tenant_id, idempotency_key)`·`idempotency_keys.job_id`(단일)를 정본으로 두고(12 `JobStatus.idempotency_key`도 "`(tenant_id, key)` 유일"), 응답 스냅샷 컬럼이 없어 N건 재생(200)을 원장만으로 복원할 수 없다. 이 문서는 §4 "배치 원장" 행의 **잠정안**(`jobs.idempotency_key = "{key}#{i}"`, `idempotency_keys.job_id = jobs[0]`, 재생은 `jobs` 행에서 재구성)을 두었다 — 파생 키가 `#`를 포함한 단건 키와 충돌할 수 있는 임시 방편이다 | 바이블 §13.1 개정(minor): `idempotency_keys`에 `job_ids array<ulid>`(또는 `response jsonb` 응답 스냅샷, 04-storage `response_status`와 함께) 추가, `jobs.idempotency_key`는 배치 멤버에서 NULL 허용(04-storage는 내부 잡에 이미 NULL 허용). 12 문서 `JobStatus.idempotency_key` 의미 열과 07-tech-landscape/08 "요청 지문 + 최종 응답 저장"과 정합 |
| 13 | 503 응답(오케스트레이터 불가, 오브젝트 스토리지 put 실패)에 본문 `ProblemDetails`가 필수(13 §7.1)이고 `code`는 카탈로그 값이어야 하는데(00 I-14) 맞는 코드가 없다. 13 §3.3은 `contract.violation` 대용을 부적절로 판정했으므로 채택 전 대안이 없다 | 13 미해결 이슈와 공동: `api.orchestrator_unavailable`(503, 재시도)·`api.dependency_unavailable`(503, 재시도) 조기 채택(minor) — 구현 전제 |
| 14 | ACL 입력 규칙 A4(`deny_principals ∌ tenant:*`)·A6(`restricted` + 빈 `allow_principals` = 잠금)은 바이블 §10.1·00 §4.4·`common-types` `Acl`에 없는 의미 규칙이다. A4는 공용 타입이 허용하는 인스턴스를 이 계약에서만 거부한다 | 바이블 §10.1·00 §4.4 `Acl` 의미 열에 두 규칙 등재(patch/minor). 채택 전 완화안: A4 위반을 400 대신 접수 허용 + `Warning{code: "contract.acl_deny_all"}`(제안 코드) 또는 `PATCH .../acl` 유도 |
| 15 | `credentials_ref` 형식: 이 문서는 `{provider}:{path}`(`$defs/CredentialsRef`, ≤ 256)를 두고 provider 집합은 강제하지 않는다. 02 `SourceDocument.credentials_ref`는 `string` ≤ 256만 정의하고 예시가 `kp://tenant/…`라 형식 관례가 다르다(길이 상한은 이 문서가 02에 맞춰 정합) | 바이블 §5.4 `credentials_ref` 의미 열에 형식 명시(patch); 02·16(`ConvertRequest`)이 `urn:rag:schema:ingest-request:1#/$defs/CredentialsRef`를 `$ref`하거나 `common-types` `$defs`로 승격(00 소유, minor) |

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) — R1, 원칙 4·9·10, D-06·D-08·D-09, §7 보안, §9.5 타입 표기
- [설계 바이블](../02-architecture/00-design-bible.md) — §3.1 D-08·D-09, §3.3 ADR 표, §4.1 공통 규약, §4.2 `fetch`, §5.1 인벤토리, §5.3 `Acl`·`EgressPolicy`, §5.4 `IngestRequest`·`SourceDocument`·`IndexRecord`, §5.6 `JobStatus`, §5.7 `DedupPolicy`·`SplitHint`·`PiiPolicy`·`PiiTokenizeMode`·`Genre`·`FilterableField`·이벤트·오류 카탈로그, §6.1 주체 문자열, §6.2 `metadata_hash`·`acl_hash`·웹훅 서명, §7.3 프로파일 YAML(`json` 라우터, `egress`), §10.1 ACL 의미, §10.3 E1·E2·E4·E16·E17, §11.2 디스패처·문서 직렬화, §11.4 세대 사가, §11.5 잡 상태 기계, §13.1 `jobs`·`idempotency_keys`·`documents`·`subscriptions`, §13.3 오브젝트 키, §13.4 Valkey `idem:`, §14 `POST /v1/ingest`·`/v1/ingest/batch`
- [기술 지형 종합: 선정 매트릭스](../07-tech-landscape/00-summary-and-selection-matrix.md) — `uri_fetcher` 연구 공백(fsspec·httpx·smbprotocol 잠정 권고), P2 API 규약(RFC 9457·`Idempotency-Key`)
- [계약 개요와 공통 규약](00-contract-overview.md) — §2 소유 규칙, §3.1 봉투(IngestRequest 예외), §4.4 `Acl`, §4.23 `EgressPolicy`, §7 `H()`, §8 null·확장·크기, §9 산출물 저장, §10 검증 지점·CI 게이트, §11 LLM 소비
- [에러 모델](13-error-model.md) — §3.2 카탈로그(`api.idempotency_conflict`, `api.idempotency_payload_mismatch`, `contract.violation`, `fetch.*`), §3.3 제안 코드(`auth.tenant_mismatch`, `api.orchestrator_unavailable`, `api.dependency_unavailable`), §7 HTTP 매핑, §9·§11 `source_uri`·비밀 미기록, §10 클라이언트 처리 지침
- [저장소 아키텍처](../02-architecture/04-storage-architecture.md) — §2.2 `jobs`·`idempotency_keys`·`documents` 컬럼, UNIQUE 제약(배치 원장 잠정안의 근거)
- 계약 문서: [02-source-document](02-source-document.md)(§2.4 `SourceMetadata` 상한, §3 해시 입력 규약, `credentials_ref` ≤ 256), [07-embedded-chunk-set-and-index-record](07-embedded-chunk-set-and-index-record.md), [12-jobs-events-and-status](12-jobs-events-and-status.md)(`JobStatus.idempotency_key`), [14-schema-versioning-and-compatibility](14-schema-versioning-and-compatibility.md), [15-collection-profile-and-policy-contracts](15-collection-profile-and-policy-contracts.md)
- 파이프라인·API: [../04-pipelines/02-fetching-and-source-resolution.md](../04-pipelines/02-fetching-and-source-resolution.md), [../04-pipelines/03-parsing-router-and-format-detection.md](../04-pipelines/03-parsing-router-and-format-detection.md), [../05-api/02-ingestion-api.md](../05-api/02-ingestion-api.md), [../05-api/07-webhooks-and-events.md](../05-api/07-webhooks-and-events.md)
- ADR: [0005](../06-adr/0005-doc-version-content-hash-only-and-acl-payload-update.md), [0017](../06-adr/0017-event-delivery-outbox-cloudevents-no-broker.md), [0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md), [0026](../06-adr/0026-index-commit-generation-saga-and-ledger.md), [0027](../06-adr/0027-security-context-injection-and-acl-enforcement-points.md), [0029](../06-adr/0029-three-text-rule-and-deterministic-context-prefix.md), [0036](../06-adr/0036-naming-and-identifier-conventions.md), [0037](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md), [0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md)
- 스키마 파일: [schemas/ingest-request.schema.json](../../schemas/ingest-request.schema.json), [schemas/common-types.schema.json](../../schemas/common-types.schema.json)
- 외부 규격: JSON Schema 2020-12, RFC 3339, RFC 3986(URI), RFC 9457, draft-ietf-httpapi-idempotency-key-header-07, BCP 47, ULID 명세, BLAKE3
