---
title: 바이블 1.3.0 전파 지시서
status: active
owner: architecture
version: 1.0.0
last_updated: 2026-09-23
depends_on: ["07-bible-amendment-triage-decisions.md", "01-phase3-completeness-review.md", "03-bible-amendment-triage-input.md", "../00-vision/00-design-brief.md", "../02-architecture/00-design-bible.md"]
---

# 바이블 1.3.0 전파 지시서

## 목적

4단계 T2가 [설계 바이블](../02-architecture/00-design-bible.md)을 1.3.0으로, [설계 브리프](../00-vision/00-design-brief.md)를 v1.2.2로 개정했다. 이 문서는 그 개정과 [트리아지 결정](07-bible-amendment-triage-decisions.md)이 하류 문서에 요구하는 편집을 **문서별 체크리스트**로 고정한다. P1(문서 전파) 담당자는 자기 문서의 절만 읽고 항목을 처리한 뒤 체크한다. 이 문서는 새 결정을 만들지 않는다. 모든 항목은 바이블 1.3.0 절, 트리아지 AM 번호, 계약 감사 정본 결정(CR), 기계 감사, 완전성 검토 중 하나를 근거로 갖는다.

## 범위

- 포함: 문서 편집 지시. 출처는 다섯 가지다. (a) AM-01~AM-44 채택 항목의 영향 문서(트리아지 §2.1·§2.2), (b) 계약 감사 정본 결정 CR-01~CR-47 중 04-pipelines·05-api·08~11 문서가 같은 필드·열거를 쓰는 곳(트리아지 입력 §3, 트리아지 §6.2), (c) 트리아지 §6.1 문서 내부 지시(요청 행 번호 `#nn`), (d) 기계 감사 `tools/phase4/results/audit-pre.md`의 A3(`likely_ok=false` 행)·A7(미정의 인용), (e) [3단계 완전성 검토](01-phase3-completeness-review.md) §3 #1·#2·#9·#10·#12.
- 제외: 바이블·브리프 본문(T2 완료), `schemas/*.schema.json`과 03-contracts의 `## 스키마`·Pydantic 블록 수정(T3 담당, 항목에 `[T3]`로 표시해 문서 쪽 서술만 맞춘다), 새 ADR 본문 작성(ADR-0039는 06-adr 절의 지시로만 둔다), 보류 AM-45~AM-56의 채택, `docs/README.md` 현황표(5단계), 900행 초과 문서의 절 이관(P2; 해당 문서에는 한 줄로만 표시).
- 표기: `- [ ]` 항목 = 한 번의 편집 단위. 괄호 안은 근거(바이블 절·AM·CR·`#요청행`·A3/A7·완전성 #). "L123"은 감사 시점(2026-09-23) 행 번호이며 편집으로 밀릴 수 있다. 문서 경로는 `docs/` 기준이다.
- 완료 조건: 문서마다 모든 항목 체크 + frontmatter `version` patch 증가 + `last_updated: 2026-09-23`(`status` 불변, ADR은 `accepted` 유지) + 계약·스키마를 건드린 경우 `node tools/validate-contracts.mjs --root .` ERROR 0.

## 1. 공통 지시(모든 문서)

아래 여섯 항목은 2절의 모든 문서에 암묵으로 포함된다. 2절 체크리스트에는 반복하지 않는다.

- [ ] **GL-/PL- 접두 확인(D4-1):** 용어집 미해결 이슈는 `GL-xx`, 용어집 링크 키는 `[PL-xx]`로 전환 완료 상태다. 자기 문서에 "용어집 미해결 이슈 N", "용어집 O-xx", 구 `[P-xx]` 형태가 남아 있으면 `GL-xx`/`[PL-xx]`로 바꾼다. 개방 결정 `O-xx`는 브리프·바이블 전용(O-01~O-12)이므로 용어집 이슈 번호와 섞지 않는다.
- [ ] **바이블 인용 갱신:** 바이블 버전을 적은 곳(`바이블 v1.1`, `v1.2.1` 등)은 1.3.0으로 바꾸고, 1.3.0에서 절 내용이 바뀐 곳(아래 표)을 인용하는 문장은 새 문구와 맞는지 확인한다. 브리프 버전 인용은 v1.2.2로 바꾼다.
- [ ] **기각 기술 문맥 명시(A3):** PyMuPDF·pyhwp·MinIO·Redis·Infinity·SPLADE-v3·EasyOCR·HunyuanOCR·jina 언급은 "대안·기각" 또는 "옵트인 격리" 문맥임이 문장 안에서 드러나야 한다(예: "PyMuPDF(AGPL, 인프로세스 제외 — ADR-0006)", "Redis 호환(Valkey)"). 채택 사실처럼 읽히는 문장만 브리프 §4 v1.1·v1.2 개정 행으로 정정한다. `likely_ok=false` 행은 2절에 행 번호로 적었다.
- [ ] **"제안" → "결정" 승격:** 1.3.0이 채택한 항목(아래 표)을 자기 문서가 `**제안:**`·"바이블 미등재"·"minor 제안"으로 적었으면 `**결정:**`(근거: 바이블 1.3.0 §x, AM-nn)으로 바꾸고, 해당 `## 미해결 이슈` 항목은 "종결(바이블 1.3.0 AM-nn)"로 표시한다. 보류 항목(AM-45~AM-56)은 제안 지위를 유지하되 트리아지 §5.2의 잠정 규칙과 재발의 시점을 한 줄 덧붙인다.
- [ ] **전방 참조 제거(#138·#142~#145·#147):** 문서 맵의 모든 문서가 작성되었으므로 "(작성 예정)", "미게시", "작성 시점 미게시" 표기를 지우고 링크를 실제 절로 고친다. 링크 대상은 브리프 §8 문서 맵 경로만 쓴다(v1.2.2에서 `07-tech-landscape/13·14`, `12-appendix/02~08` 등재).
- [ ] **카탈로그 개수 인용:** 이벤트 카탈로그는 24 → **25종**(`tenant.policies.changed`), 오류·경고 코드는 68 → **84종**(AM-36), 계약 인벤토리는 34 → **35종**(`SchemaDiffReport`)이다. 개수를 적은 문장을 고친다.

**1.3.0 변경 절 요약(인용 대조용)**

| 바이블 절 | 1.3.0 변경 | AM |
|-----------|------------|----|
| §1.2 | 필수 → 선택화·제약 완화 = minor(조건부), 제약 강화 = major | AM-23 |
| §3.2·§3.3 | O-11·O-12(`open`), ADR-0039(1.3.0 가산 묶음) | AM-21 |
| §4.1 | `stage_key` 입력 해시(`detect`·`parse` = `content_hash`), `requires_lineage` 범위(`chunk`·`enrich` LLM), `StageContext.plan`·`artifacts` | AM-05·26·27 |
| §4.2·§4.4 | `detect` 잠정값 규약, `embed.token_overflow` → `degraded`, `parse(텍스트)` `resumable` = `Capabilities` | AM-06·07 |
| §4.3·§8.1 | `hydrate` `with_payload`에 `heading_path`·`numbering_path`·`page_start`·`page_end` + 선택 4종 | AM-08·33 |
| §5.1 | `SchemaDiffReport` 행, API 전용 뷰 각주, 공용 타입 승격 11종 | AM-01·02·35 |
| §5.3~§5.6 | `StageError`·`ProblemDetails`·`EgressPolicy`·`NormalizedDocument`·`RankedResult`·`EvalDataset`·`Profile` 선택 필드, `Chunk.ordinal`, `parser_version`·`profile_option` 형식 | AM-09·28~34 |
| §5.7 | 인라인 열거 = common-types `$defs`, `JobKind.delete_collection`, `TenantStatus`, `CompatLevel`·`SchemaChangeKind`, 이벤트 `tenant.policies.changed`, 오류·경고 16종, `retrieve.security_context_missing` 500 | AM-10·25·36~38 |
| §6.1·§6.2 | `{extension_point}.pipeline`, API `model_id`, JCS 직렬화, 선택 필드 제거 후 해시, `derived` `options_hash`, `plan` `opts`, `query_hash`·`principal_hash`, `llm-enrich` 입력 | AM-11·12·40 |
| §6.5·§6.7 | CloudEvents `source` = `api`·`worker`, 메트릭 36종·스팬 2종, `/v1/version` 단수 예외 | AM-13·39·41 |
| §7.1·§7.3 | `lite` 컨테이너 4 / 5~6, HWP 5.0 `standard` 배포용 Tika, TXT·MD·JSON 하위 라이브러리, `pii.reject_entities` | AM-14·42·43 |
| §10.1·§10.3 | 잠금 ACL = 경고 `contract.acl_deny_all`, E7 = 500 카탈로그 코드 | AM-17·25 |
| §11.2·§11.4 | `collection.delete.v1`, 정합성 검사 트리거, `index_generation = max + 1` 비재사용 | AM-18·37·39 |
| §12 | `parse/router.py`·`hwpx_hwpxlib_sidecar.py`·`settings/`·루트 개발 파일, `cli/` 명령 정본 = 10-development/02 §CLI | AM-22 |
| §13.1·§13.3 | `tenants.status·quotas·disabled_at`, `collections.deleted_at`, `idempotency_keys.job_ids`, 캐시 제외 산출물·LLM 보강 캐시 키 | AM-19·37·39·44 |
| §14 | `/v1/tenants` 계열, API 키, 플러그인, 스키마 목록, 버전, 정합성 검사, 감사 이벤트, 프로파일 게시, unmask, SSE 진행률 범위 | AM-20·39 |

## 2. 문서별 지시

### 00-vision/03-glossary.md

- [ ] v0.2.0으로 minor 개정한다(완전성 #1, 트리아지 §4 #1). 바이블 §16 표가 정본이며 바이블은 고치지 않는다.
- [ ] 바이블 §16 "추가" 38행을 각 절(도메인·파이프라인·검색·임베딩·평가·운영·한국어·포맷)에 정의문으로 전개한다. 정의문은 바이블 절을 근거로 한 줄 이상, 식별자는 §5·§6 철자 그대로(`hydrate`, `ChunkTextStore`, `record_id`, `scope_key`/`stage_key`, `RAG-Signature`, `EgressPolicy`, `TieringPolicy`, `litm_alternating`, `PackStep`, `recount`, `aclrev`, `channel_run_id`/`variant_id`/`workflow_run_id` 등).
- [ ] 바이블 §16 "변경" 17행은 구 용어 항목에 "→ 새 용어" 표기(예: "Redis → Valkey(Redis 호환 KV)", "`point_id = uuid5(chunk_id)` → `uuid5(record_id)`", "강제 지점 15개 → 17개")로 반영하고, 구 용어를 채택 사실처럼 서술한 문장은 기각·대체 문맥으로 고친다.
- [ ] 1.3.0 새 이름을 등재한다(트리아지 §4 #1): `TenantStatus`(`active, disabled`), `JobKind.delete_collection`·`collection.delete.v1`, `tenant.policies.changed`, `SchemaDiffReport`·`CompatLevel`·`SchemaChangeKind`, `requires_lineage` 범위(`index`·`chunk`·`enrich` LLM), `DerivedArtifacts`, O-11·O-12(개방 결정, `open`), 잠금 ACL, API 전용 뷰(API-only view).
- [ ] 미해결 이슈는 `GL-xx` 접두를 유지하고, 바이블 §16 "변경" 행에 "GL-05·06·07·08·12·13·14·15 해소"로 적힌 항목은 용어집 미해결 이슈에서 "해소(바이블 §16)"로 닫는다.
- [ ] A3 `likely_ok=false` 행 문맥 검토: L416·L552 PyMuPDF, L397·L405·L553 pyhwp, L272·L323·L355·L555 Redis, L164·L271 Infinity, L263 SPLADE-v3. 기각·옵트인 문맥으로 명시하거나 대체 용어로 바꾼다.
- [ ] 내부 문서 참조 목록에 `07-tech-landscape/13`·`14`, `12-appendix/06-traceability-matrix.md`를 추가한다(브리프 v1.2.2 문서 맵).

### 00-vision/01-vision-and-goals.md

- [x] patch 개정(v0.1.1)만 한다(완전성 #2, 트리아지 §4 #2). 목표 ID·지표 문장의 의미는 바꾸지 않는다.
- [x] 브리프 v1.2 개정 요지 반영: 수집 셸 "인프로세스 러너"류 표현은 비내구 `LocalRunner`(D-17 v1.1), 저장소 표기는 Valkey·RustFS/SeaweedFS(D-14 v1.1), PDF 고속 경로는 pypdfium2 + pdftext(D-18 v1.1)로 정정한다.
- [x] 목표·지표 표에서 재현성·격리를 말하는 행은 `record_id` 세대 합성(D-06 v1.2)과 `stage_key` 잡 스코프(ADR-0037)를 한 줄로 인용한다(새 목표 추가 아님, 근거 링크만).
- [x] A3 L353 Redis(`likely_ok=true`)는 "Redis 호환" 문맥인지만 재확인한다.
- [x] `depends_on`에 바이블을 넣고 참조 절의 브리프·바이블 버전 표기를 v1.2.2·1.3.0으로 맞춘다.

### 00-vision/02-design-principles.md

- [x] patch 개정(v0.1.1)(완전성 #2).
- [x] DP-03.R6 "Temporal 워커와 인프로세스 러너" → "Temporal 워커와 비내구 `LocalRunner`"(D-17 v1.1, 바이블 §11.1).
- [x] DP-01·DP-02 "관련 결정" 줄에 개정 행 표기를 붙인다: D-01·D-02·D-04는 v1.1, D-06·D-07은 v1.2(브리프 §4). 결정 요지를 풀어 쓴 문장이 있으면 개정 문구와 대조한다(예: D-04 `page`/`bbox` nullable).
- [x] 멀티테넌시 원칙(원칙 9) 설명에 강제 지점 17개(E16 egress, E17 키 스코프, 바이블 §10.3)를 인용한다.
- [x] 멱등성 원칙 설명에 `stage_key = H("stage", stage_name, scope_key, input_hash, fingerprint)`(바이블 §4.1 1.3.0 표기)를 인용한다.

### 00-vision/04-scope-and-non-goals.md

- [x] patch 개정(v0.1.1)(완전성 #2).
- [x] §6.2 HWP 5.0·PDF·암호화 문구를 D-18 v1.1·ADR-0006·ADR-0007로 갱신한다(#114): HWP 5.0 1차 = Java 사이드카, pyhwp = AGPL 선택 플러그인, 배포용 = 테넌트 옵트인 Tika 텍스트(`quality=degraded`), 암호화 = `credentials_ref` 없으면 `parse.document_encrypted`.
- [x] I-13의 `NFR-I-02` → `ISS-NFR-02`(Redis 라이선스, 비기능 요구사항 미해결 표)로 정정한다(완전성 #9 (a), A7 계열).
- [x] L55 "서빙 엔진(TEI, Infinity)" → "TEI·vLLM pooling(Infinity는 제외, D-16 v1.1)", L109 저장소 "Redis" → "Valkey(Redis 호환)", L167 "`s3://`(MinIO 포함)" → "S3 호환(RustFS·SeaweedFS 등)"으로 정정한다(A3).
- [x] A3 나머지 행 문맥 검토: L466·L520·L668 PyMuPDF, L464·L519 pyhwp, L415·L672 Redis, L216·L567 Infinity. 기각 서술이면 유지하고 "기각(ADR-xxxx)"을 병기한다.
- [x] 관리 API 범위 행에 테넌트 관리 API(`/v1/tenants` 계열, 바이블 §14 1.3.0, FR-MGT-01)가 v1 범위임을 반영한다(AM-39).

### 01-requirements/01-functional-requirements.md

- [ ] patch 개정(v0.1.1)(완전성 #2). 요구사항 ID·우선순위·SHALL 문장은 바꾸지 않는다.
- [ ] FR-MGT-01 비고에 "설계 충족: 바이블 §14 `/v1/tenants` 계열·`tenants.quotas`·`TenantStatus`(1.3.0, AM-39·AM-38)"를 추가한다(트리아지 §4 #3).
- [ ] FR-API-04 비고에 "관리 API 응답 객체는 API 전용 뷰, `api/` Pydantic 단일 출처 + `schemas/` `$ref` 재사용으로 충족(바이블 §5.1 1.3.0, AM-02)"을 추가한다.
- [ ] FR-API-06(버전 조회) 비고에 `GET /v1/version`(바이블 §14 1.3.0)을 적는다.
- [ ] FR-ING-14 잡 상태 제안(`fetching`, `parsing` 등)·FR-CHK-11 청크 타입 제안이 바이블 §5.7 `JobState`·`ItemKind`와 다른 곳은 비고로 "설계 열거는 바이블 §5.7" 한 줄을 단다(02-architecture/01 미해결 7). SHALL 문장은 유지한다.

### 01-requirements/02-non-functional-requirements.md

- [ ] patch 개정(v0.2.1)(완전성 #2).
- [ ] `NFR-REL-17`은 신설하지 않는다(완전성 #9 (b)). 미해결 이슈 표에 "리전 손실 RPO/RTO 요구사항 신설 여부 — 요구사항 소유자 백로그(09-operations/07 제안)" 행을 추가한다.
- [ ] L578 Redis 행(라이선스 표): "Valkey 기본(D-14 v1.1), Redis 8은 호환 옵션"으로 결론 열을 갱신한다(A3). ISS-NFR-01(PyMuPDF)·ISS-NFR-02(Redis)·ISS-NFR-03(pyhwp)은 "해소: ADR-0006·ADR-0011·ADR-0007"로 닫는다(A3 L582·L589·L745~L747).
- [ ] ISS-NFR-06 잡 상태명 제안은 "해소: 바이블 §5.7 `JobState`, 삭제 이벤트 `ingest.document.deleted`"로 닫는다.
- [ ] ISS-NFR-07 `degraded` 필드는 "해소: 바이블 §5.2 봉투 `degraded[]`"로 닫는다.

### 01-requirements/03-personas-and-use-cases.md

- [ ] A2 "필수 필드 누락 5건"은 frontmatter 부재가 아니라 CRLF 줄끝 때문에 감사기가 파싱하지 못한 결과다(파일 첫 줄 `---\r\n`). 줄끝을 LF로 정규화하고 frontmatter 값(`title`·`status: active`·`owner: architecture`)은 유지한다. `tools/audit-docs.mjs`의 frontmatter 파서가 CRLF를 허용하도록 고치는 것은 5단계 도구 작업으로 넘긴다.
- [ ] A3 문맥 검토: L360 PyMuPDF, L266·L460 Redis. 기각 기술이면 "(기각, ADR-0006/0011)"을 병기하고 채택 사실처럼 쓴 곳은 pypdfium2·Valkey로 바꾼다.
- [ ] 테넌트 관리자 페르소나의 유즈케이스에 `/v1/tenants`·API 키 발급·회전(바이블 §14 1.3.0)을 인용한다(AM-39).

### 01-requirements/04-user-stories-and-acceptance-criteria.md

- [ ] patch 개정(v0.1.1)(완전성 #2).
- [ ] L209 AC-1 "1차 파서(D-18: pyhwp/hwp5 어댑터 …)" → "1차 파서(D-18 v1.1: Apache-2.0 Java 사이드카 → HWPX → OWPML 어댑터; pyhwp는 AGPL 선택 플러그인)"로 정정한다(A3, #114와 같은 근거). AC의 Given/When/Then 검증 의미는 유지한다.
- [ ] EP-07 관리 API 스토리의 수용 기준에 테넌트 생성·비활성화·할당량(`TenantStatus.disabled` 요청 = `auth.forbidden` 403, 할당량 초과 = `api.quota_exceeded`)을 인용한다(AM-38·AM-39·AM-36). 새 스토리 ID는 만들지 않는다.
- [ ] EP-07 "관련 결정" 열의 D-17을 브리프 §6 "관리 API" 포함 범위로 보강한다.

### 02-architecture/01-system-overview.md

- [x] 미해결 3(`lite` 컨테이너 수)을 "종결: 바이블 §7.1 1.3.0 — 4(개발) / 5~6(운영 `--durable`)"로 닫고 §5.1 표기를 맞춘다(AM-14).
- [x] 미해결 11(C4 `api` → Object Storage 간선)을 "종결: 바이블 §2.2 1.3.0"으로 닫고 본문 C4에도 같은 간선을 둔다(AM-04).
- [x] 미해결 12(테넌트 생성·목록 API 부재)를 "종결: 바이블 §14 `/v1/tenants` 계열(AM-39)"로 닫는다(트리아지 §4 #3).
- [x] A3 문맥 검토: L185·L580 PyMuPDF, L185·L231·L579 pyhwp, L573 Redis.
- [x] 컨테이너 책임 서술에 `api`의 새 관리 표면(테넌트·API 키·플러그인·감사 이벤트 조회)을 한 줄 추가한다(바이블 §14).

### 02-architecture/02-component-architecture.md

- [x] §2.3 플러그인 레지스트리: `build_stage()`와 `build_port()`를 분리해 기술한다(#14).
- [x] §2.4 `ContextRenderer`에 `plugin_id` 멤버를 추가한다(#18). 합성 생산자의 `plugin_id`는 `{extension_point}.pipeline`(바이블 §6.1 1.3.0, AM-11).
- [x] 스테이지 셸 서술에 `StageContext.plan: QueryPlan | None`·`artifacts: DerivedArtifacts`(바이블 §4.1, AM-27)와 `requires_lineage` 범위 확대(`chunk` = `ParsedDocument`, `enrich` LLM = `ChunkSet`, AM-26)를 반영한다.
- [x] 모듈 표에 `adapters/parse/router.py`(`ParseRouterStage`), `adapters/parse/hwpx_hwpxlib_sidecar.py`, 최상위 `settings/`(pydantic-settings, `security`·`profiles`와 같은 층)를 추가하고 import-linter 계층 식을 바이블 §12 1.3.0과 맞춘다(AM-22).
- [x] `rag reprocess` 등 CLI 명령 서술은 "명령 정본: 10-development/02 §CLI" 인용으로 바꾼다(완전성 #10).
- [x] L944 PyMuPDF·pyhwp 문맥 검토(A3).
- [x] 설정 모델 절은 09-operations/02로 이관 대상임을 표시한다(#169, P2 — 이관 자체는 P2). 문서가 998행(900행 초과)이 되어 범위 절에 P2 이관 한 줄을 추가했다.

### 02-architecture/03-data-flow-and-document-lifecycle.md

- [x] 미해결 11 "미정(O-xx 미배정, green 물리 이름 규칙)" → `**미정(O-11):**`(바이블 §3.2 1.3.0, AM-21).
- [x] 미해결 20 "미정(O-xx 미배정, blue/green 채움 중 `documents` 원장 처리)" → `**미정(O-12):**`(AM-21).
- [x] 두 항목에 잠정 규칙을 한 줄 덧붙인다: `profile_hash`만 바뀐 재색인은 자동 실행 불가(부모 잡 `failed`) + 운영자 대안(04-pipelines/19), 해결은 ADR-0039 이후 ADR-0026 개정(AM-45 보류).
- [x] 컬렉션 수명주기 서술에 컬렉션 삭제 `collection.delete.v1`(`collections.deleted_at` 논리 삭제 → 자식 `delete.document.v1` 팬아웃, 새 이벤트 없음)을 추가한다(바이블 §11.2 1.3.0, AM-37).
- [x] `detect` 단계 설명에 fetch 잠정값(`format = unknown`, `format_confidence = 0.0`, `container_flags` 자리표)은 미판정이라는 규약을 인용한다(AM-06).

### 02-architecture/04-storage-architecture.md

- [x] §2.4 역할 표에 `GRANT rag_owner TO rag_platform_admin`을 등재한다(#16).
- [x] §4.4 `DatetimeIndexParams`의 "확인 필요(as of 2026-09)" 표기를 유지한다(#75).
- [x] §5.2 BM25 필드 `index_text.bigram` → `cjk_bigram`(바이블 §13.4 필드명; 분석기 `rag_hangul_bigram` 정의는 유지)(#83·#192).
- [x] 원장 표 DDL·서술에 1.3.0 컬럼을 추가한다: `tenants.status`(`TenantStatus`)·`quotas jsonb`·`disabled_at`(AM-39), `collections.deleted_at`(AM-37), `idempotency_keys.job_ids text[]`와 배치 자식 잡 `jobs.idempotency_key` NULL 허용(AM-44).
- [x] 오브젝트 키 표에 캐시 제외 스테이지 산출물 `tenants/{tenant_id}/artifacts/{schema_type_kebab}/{blake3[:2]}/{blake3}.json`, LLM 보강 캐시 `derived/llm_enrich/{key[:2]}/{key}.json`, "점유된 `stage_key` 경로 비덮어쓰기" 규칙을 추가한다(바이블 §13.3, AM-19).
- [x] `derived` 파생물 키를 `H("derived", content_hash, sidecar_image_digest or "", options_hash or "")`로 갱신한다(바이블 §6.2, AM-40).
- [x] `index_generation` 할당 서술을 `max(index_commits.index_generation) + 1`, 세대 번호 비재사용으로 맞춘다(AM-18, CR-31).

### 02-architecture/05-plugin-architecture.md

- [ ] §2.4 미분류 예외 처리 규칙을 04-pipelines/01 §10.2(B2)에 맞춘다(#17).
- [ ] 질의 측 확장 지점 시그니처를 `Stage[In, Out]` 특수화로 기술한다(#54). 질의 측 스테이지는 `ctx.plan`(1.3.0 선택 멤버)으로 `QueryPlan`을 읽는다(AM-27).
- [ ] §6.3 레지스트리 절에 `build_port()`를 반영한다(#14).
- [ ] `requires_lineage` 설명을 바이블 §4.1 1.3.0 범위(`index`·`chunk`·`enrich` LLM, 입력 `lineage_refs`로 고정되는 상류만)로 갱신하고 "현재 `index`만"류 문장을 지운다(AM-26, CR-04).
- [ ] 합성 생산자 `plugin_id` 예약 구현명 `{extension_point}.pipeline`을 명명 규칙 절에 추가한다(AM-11).
- [ ] A3 문맥 검토: L926·L936·L978 pyhwp(선택 플러그인 문맥 명시).

### 02-architecture/06-orchestration-and-workflows.md

- [ ] §6.2 "queued 생성 — 이벤트 없음" → "접수 시 `job.state.changed`"(#116).
- [ ] 셸 모듈 표기를 `orchestration/context.py`로 정정한다(R-08; `orchestration/stage_shell.py` 삭제).
- [ ] §2.5 세대 할당 서술을 `documents` 행 잠금 아래 `max(index_commits.index_generation) + 1`, 폐기·롤백 세대 번호 비재사용으로 확정한다(바이블 §11.4 (6), AM-18).
- [ ] 워크플로우 표에 `collection.delete.v1`(`JobKind.delete_collection`)과 `maintenance.consistency.v1`의 API 트리거 `POST /v1/collections/{collection_id}/consistency-check`를 추가한다(바이블 §11.2 1.3.0, AM-37·AM-39).
- [ ] 재색인 모드 B·blue/green 원장 문제는 `**미정(O-11):**`·`**미정(O-12):**`로 표기한다(AM-21).
- [ ] 취소 경합은 트리아지 §5.2 AM-46 잠정 규칙을 인용한다: 플립 시작 후 도착한 취소는 `cancelling`으로 전이시키지 않고 잡은 `running → succeeded`, 취소 API는 202 + 현재 `JobStatus`(CR-29).
- [ ] §9 처리량·사이징은 09-operations/04로 이관 대상임을 표시한다(#159, P2).

### 02-architecture/07-multi-tenancy-and-security-architecture.md

- [ ] §4.1 `manage_tenants` 행을 관리 API(`/v1/tenants`, 바이블 §14 1.3.0) 유지로 정리한다(#56, AM-39). 05-api/04 미해결 12의 액션(`read_registry`, `read_audit`, `manage_api_keys`, `unmask_pii`)을 액션 표에 반영하고 이 표가 권한 액션 정본임을 명시한다(바이블 미해결 23).
- [ ] ACL 의미 절에 잠금 ACL(`restricted` + 빈 `allow_principals`, `deny ∋ tenant:*`) = 누구에게도 보이지 않음 + 수집 경고 `contract.acl_deny_all`을 추가한다(바이블 §10.1, AM-17).
- [ ] 테넌트 상태·할당량 절: `TenantStatus`(`active, disabled`; `disabled` 요청은 `auth.forbidden` 403), `tenants.quotas{documents_max, storage_bytes_max, qps_max}`, `tenant.policies.changed`(정책 캐시 무효화; 감사 이벤트 겸용 금지)를 추가한다(AM-38·AM-39, 트리아지 §4 #12).
- [ ] §10 레이트 리밋·쿼터에서 `api.quota_exceeded`의 HTTP 상태를 확정한다(트리아지 미해결 4; 초안: 문서 수·저장 용량 초과 403, QPS 초과는 `api.rate_limited` 429). 확정값을 05-api/01 §9와 같게 둔다.
- [ ] §8.2 캐시·해시 키에 `query_hash = H("query", normalized_query)`, `principal_hash = H("principal", tenant_id, subject)`, `plan` 캐시 키의 `opts` 항을 반영한다(바이블 §6.2, AM-40).
- [ ] `POST /v1/documents/{document_id}/unmask`(역할 `pii_officer`, `tokenize`·`encrypt` 모드만)를 PII 통제 절에 인용한다(AM-39).
- [ ] E7 행의 실패 처리를 "`retrieve.security_context_missing` 500 카탈로그 코드(클라이언트 원인은 E6 `plan.security_context_missing` 400)"로 맞춘다(AM-25).

### 02-architecture/08-deployment-architecture.md

- [ ] 미해결 14(`lite` "컨테이너 5")를 "종결: 바이블 §7.1 1.3.0"으로 닫고 L59 부근 결정 문단의 "바이블 §7.1 열 머리 문구 자체는 무조건 5" 단서를 삭제한다(AM-14).
- [ ] §3.3 `lo-sidecar` 프로파일 재사용 방식은 콜드스타트 실측 후 정정한다고 표시한다(#47).
- [ ] §5.2 NetworkPolicy 표에 `parser-workers` → Object Storage egress 행을 추가한다(#86).
- [ ] C4·배포 다이어그램에 `api` → Object Storage 간선(산출물 읽기)을 반영한다(AM-04).
- [ ] HWP 5.0 `standard` 경로 서술에 배포용 문서 = 테넌트 옵트인 시 Tika `HwpV5Parser` 텍스트(`degraded`)를 넣는다(AM-14).
- [ ] A3 문맥 검토: L148·L166·L337·L770 pyhwp(별도 저장소 `rag-platform-gpl-sidecars`의 AGPL 선택 플러그인 문맥 명시).

### 03-contracts/00-contract-overview.md

- [ ] §2 "열거 타입은 모두 common-types" 문구를 유지하고 인라인 열거 `{Type}.{path}`도 common-types `$defs` 등재임을 명시한다(AM-10; CR-08 해석은 CR-25로 대체).
- [ ] §3.2 표에 `detect` 행(입력·출력 `SourceDocument`, 출력 `lineage_refs = {}`)을 추가하고 `chunk` 행의 `requires_lineage`를 `ParsedDocument`로, `enrich`(LLM) 행을 `ChunkSet`으로 채운다(CR-11·#39, AM-26).
- [ ] §4.12 예시에서 `dataschema`(`urn:rag:schema:job-status:1`)를 제거한다(#97, CR-43).
- [ ] §9.3 미디어 타입 표에 `application/xml` 행을 추가한다(#166).
- [ ] [T3] U-12·U-13 선택 필드(`StageError.message·occurred_at·attempt·location·cause`, `ProblemDetails.retry_after·request_id`, `instance` uri-reference)를 "바이블 1.3.0 §5.3 등재"로 표기 전환한다(AM-28, CR-34).
- [ ] [T3] 공용 타입 승격 11종(`SecurityFilter`, `StrategyFilter`, `ChannelRunId`, `EmbeddingSpaceIds`, `TableRef`, `ProfileId`, `AnalyzerId`, `KebabName`, `ContractsCompat`, `Bcp47`, `MediaType`)을 `$defs` 키 목록에 추가한다(AM-35).
- [ ] §4.4 ACL 불변식에 잠금 ACL = 경고 `contract.acl_deny_all`을 추가한다(AM-17).
- [ ] API 전용 뷰(관리 API DTO)는 계약 인벤토리 밖이라는 바이블 §5.1 각주를 범위 절에 인용한다(AM-02).

### 03-contracts/01-ingest-request.md

- [ ] §8.3·버전 이력의 02 `credentials_ref` 서술을 "패턴 채택" 사실로 갱신한다(#156).
- [ ] IR-5 ACL A4: 400 거부 대신 경고 `contract.acl_deny_all`과 함께 접수로 완화한다(AM-17·AM-36).
- [ ] [T3] 배치 멱등: `idempotency_keys.job_ids`(배치 응답 재현), 배치 자식 잡 `jobs.idempotency_key` NULL 허용을 §배치 절에 반영하고 `JobStatus.idempotency_key` 필수 여부와 충돌하는지 03-contracts/12와 대조한다(AM-44; 필수 → nullable은 바이블 §1.2 minor(조건부)).
- [ ] 범위 절 "제외"에 `dry_run`은 AM-53 보류(M3 API 표면 확정 시 재발의)로 유지함을 적는다.
- [ ] L289 Infinity 문맥 검토(A3).

### 03-contracts/02-source-document.md

- [ ] §7 `fetch.scheme_unsupported` 설명을 13 §3.2와 정합한다(#38).
- [ ] 미해결 13(`container_flags` fetch 출력 선택화)을 "종결: 바이블 §4.2·§5.4 1.3.0 잠정값 규약(AM-06), 필수 Y 유지(R-05)"로 닫는다.
- [ ] 미해결 12(서명 쿼리 키 목록)를 `EgressPolicy.strip_query_keys`(바이블 §5.3 1.3.0, AM-30) 등재로 종결하고 정본 목록 위치(04-pipelines/02 §3.6 표)를 인용한다.
- [ ] `acl_hash`·`metadata_hash` 입력 규약(값 없는 선택 필드 제거 후 `canonical_json`, JCS 수치)을 "바이블 §6.2 1.3.0 결정"으로 표기 전환한다(AM-12, CR-13).
- [ ] §8 HWP 배포용 서술을 `standard` 테넌트 옵트인 Tika 텍스트(`degraded`)와 맞춘다(AM-14).
- [ ] [T3] `Bcp47`·`MediaType`을 common-types `$ref`로 전환한다(AM-35).
- [ ] A3 문맥 검토: L310·L824·L860 pyhwp.

### 03-contracts/03-parsed-document.md

- [ ] §3.1 `element_path` 표에서 DOCX(OOXML) 행을 분리한다(#33).
- [ ] §3.2 bbox 문구를 "보정 후 좌표 = 표시 페이지 프레임"으로 정정한다(#42).
- [ ] §5.3 (e)를 "폴백 체인에서 실패 뒤 성공 = `degraded`"로 확정한다(#85·#89).
- [ ] P-1에 `then` 변환 경로(DOC/RTF/ODT → DOCX)를 반영한다(#87).
- [ ] §7 각주·미주 행을 HWPX·OOXML로 분리하고(#128), §5.1 flow 행 `source=ocr`·§3.1 caption 경로를 보완한다(#86).
- [ ] `parser_fingerprint.parser_version` = `{package}=={version}`(복수는 패키지명 오름차순 `;`), `profile_option` = `{format}_{variant}`(값 목록 정본 04-pipelines/03)를 필드 표에 반영한다(AM-09).
- [ ] [T3] `section_index` 의미 "HWPX `secPr`, OOXML `w:sectPr`"로 확장(AM-29), 경고·오류 코드 `parse.page_ocr_failed`·`parse.page_skipped`·`parse.block_oversized`·`parse.block_limit_exceeded`를 카탈로그 등재로 표기 전환(AM-36).
- [ ] §8.1 Docling 체크박스 → `form_field` "확인 필요" 행은 유지한다(AM-55 보류).
- [ ] A3 문맥 검토: L1398·L1425 pyhwp. 900행 초과 문서의 절 이관은 P2에서 처리한다.

### 03-contracts/04-normalized-document.md

- [ ] "바이블 미등재"로 표기한 `table_cell_views`(조건)·`genre_source`·`pii_report.tokenize_mode_applied`·`stats`·`pii_spans[].row/col`을 "바이블 §5.4 1.3.0 등재(AM-31)"로 전환한다.
- [ ] §3.3 M5 예시 문구를 통일한다(#48).
- [ ] I-8을 minor 개정 표기로 정리한다(#90).
- [ ] 미해결 1·4·10·19를 1.3.0 반영분과 대조해 종결 또는 유지로 표시한다(#77).
- [ ] 옛한글 조합형 자모(미해결 18)는 AM-48 보류 잠정 규칙(현행 불변식 + `normalize.nfd_residual`)을 한 줄로 적는다.
- [ ] [T3] `genre_source` 인라인 열거를 common-types `$defs/NormalizedDocument.genre_source`로 이동한다(AM-10).

### 03-contracts/05-chunk-set.md

- [ ] C-3 형제 정의를 바이블 §5.4 1.3.0 문구("같은 부모(`parent_chunk_id`; 없으면 문서) 아래 형제 순서(0-based)")로 인용한다(#31·#96, AM-09).
- [ ] 표 청크의 `BlockRef.original_char_*` 상수 `0, 0`을 원문 `Block.text` 기준 `offset_map` 사상 결과(표는 03 §6 선형화 텍스트 기준)로 정정한다(CR-03).
- [ ] `chunk` 스테이지의 `ctx.lineage["ParsedDocument"]` 서술을 잠정(제안)에서 결정으로 전환한다(바이블 §4.1 1.3.0, AM-26, CR-04).
- [ ] [T3] `TableRef`·`AnalyzerId`를 common-types `$ref`로 전환한다(AM-35).
- [ ] 04-pipelines/18이 제안한 `ChunkSet` 관련 항목(#31)을 수용 또는 기각으로 판정해 버전 이력에 남긴다.

### 03-contracts/06-enriched-chunk-set.md

- [ ] `budget_used.charged_tokens`(선택)를 "바이블 §5.4 1.3.0 등재(AM-32)"로 전환한다.
- [ ] E-12 `keywords[].weight ≥ 0`은 계약 검증기 경고로만 둔다(AM-50 보류, CR-12).
- [ ] 예시 1의 부모 청크 텍스트를 자식 리프 `text`의 U+000A 결합으로 정정한다(CR-07).
- [ ] §10 LLM 보강 캐시 키 입력(`embed_text` = `generated` 미포함 조립 결과, 문서·섹션 요약은 섹션 텍스트 해시)과 저장 경로 `derived/llm_enrich/{key[:2]}/{key}.json`을 바이블 §6.2·§13.3 1.3.0으로 인용한다(AM-12·AM-19).
- [ ] 합성 생산자 `Producer.plugin_id = enricher.pipeline`을 예시·필드 설명에 반영한다(AM-11).
- [ ] 예시의 `lineage_refs.source`를 `SourceDocument` 계약 산출물 참조로 맞춘다(CR-01).

### 03-contracts/07-embedded-chunk-set-and-index-record.md

- [ ] §3 예시 `"int8"` → `onnx_int8`(#30).
- [ ] `IndexRecord` payload 선택 필드 `token_count_primary`·`ordinal`·`text_truncated`·`pii_policy_applied`가 `hydrate` → `RankedResult` 선택 필드로 이어짐을 원천 열에 적는다(AM-33).
- [ ] §9 `original_char_end` 클리핑 규칙을 `offset_map` 없이 정의하고(CR-05), 절단 재계산에서 원문 좌표에 display 절단 위치를 대입하지 않도록 정정한다(CR-21).
- [ ] 예시 3의 부모 텍스트를 자식 결합 규칙으로 정정한다(CR-07).
- [ ] `embed` Producer 지문(공간 설정의 `embedding_space_id`)과 `embedder_fingerprint`가 별개 키임을 바이블 §4.1 1.3.0으로 인용한다(AM-05).
- [ ] `embed.token_overflow` 절단 시 봉투 `quality=degraded`(V-5)를 바이블 §4.2 1.3.0으로 인용한다(AM-07).
- [ ] [T3] `EmbeddingSpaceIds`(visual-pages `page_*` 키 포함)·`AnalyzerId`를 common-types `$ref`로 전환하고 `index-record` `analyzer_id` 완화 패턴을 단일 패턴으로 좁힌다(AM-35, CR-10·CR-26).

### 03-contracts/08-index-commit.md

- [ ] §2.2 `backend_version` 문구를 "어댑터 `backend_version` 속성(`capabilities()` 호출 시 조회)"으로 바꾼다(#12).
- [ ] 미해결 14의 `last_generation` 대안을 삭제하고 `index_generation = max(index_commits.index_generation) + 1`(비재사용)을 "바이블 §11.4 (6) 1.3.0 결정"으로 표기한다(R-01, AM-18, CR-31).
- [ ] §3 규칙 (6)을 AM-46 잠정 규칙(플립 시작 후 취소는 `running → succeeded`, 취소 API 202)과 정합시킨다(CR-29).
- [ ] §7 "current 커밋 없으면 커밋 미생성·`index_commit_id=null`"을 삭제 tombstone 커밋(`record_count=0`) 규칙으로 정정한다(CR-30).
- [ ] 예시 2의 봉투 `quality`를 상류 `degraded` 전파로 맞춘다(CR-06).
- [ ] 재색인 모드 B 관련 미해결은 `**미정(O-11):**`·`**미정(O-12):**`로 표기한다(AM-21).
- [ ] [T3] `embedding_space_ids`를 common-types `EmbeddingSpaceIds` `$ref`로 전환한다(AM-35, CR-02·CR-39).

### 03-contracts/09-query-request-and-query-plan.md

- [ ] §3 Cedar 액션 `query` → `search`(#28).
- [ ] §6.7 `rerank.enabled=false`에도 `RankedSet.rerank`(`applied=false`)가 필수 출력임을 병기한다(#126).
- [ ] 미해결에서 `calibration_ratio`·`safety_margin` 제안을 제거한다(R-03).
- [ ] §5.4 `effective_hash` 해석(계획 필터 트리, `as_of` = 바인드 이름 `":as_of"`)이 바이블 §6.2 1.3.0에서 채택되었음을 표기하고 "바이블 식의 해석" 단서 문장을 결정으로 바꾼다(AM-12, CR-17).
- [ ] `plan` 캐시 키의 `H("opts", …)` 항을 캐시 키 절에 반영한다(AM-40).
- [ ] P-11 `pack.k_max = min(top_k, 프로파일 k_max)`를 삭제하고 `pack.k_max = 프로파일 query.pack.k_max`, `PackPlan.k_max 1..20`으로 정합한다(CR-14·CR-15).
- [ ] 예시 `tokenizer.name`을 `tokenizer_id` 형식(`anthropic:<target-model-id>`)으로 맞춘다(AM-16, CR-24).
- [ ] validate-contracts WARN 2건(L579·L626 문서 내 스키마 블록 ↔ `schemas/query-request`·`query-plan` 불일치)을 T3 반영 뒤 동기화한다.

### 03-contracts/10-candidate-set-and-ranked-set.md

- [ ] §4.3 `unavailable` 의미 열에 429·응답 검증 실패·서킷 열림을 포함한다(#71).
- [ ] §9 explain 표에서 `boost_*` fuse 행을 삭제한다(#26).
- [ ] `hydrated=true` 조건 필수 18필드와 `with_payload` 목록 일치(바이블 §4.3·§8.1 1.3.0)를 RS 불변식에 인용한다(AM-08, CR-19).
- [ ] [T3] `RankedResult` 선택 필드 `token_count_primary`·`ordinal`·`text_truncated`·`pii_policy_applied`를 등재한다(AM-33).
- [ ] [T3] `SecurityFilter`·`StrategyFilter`·`ChannelRunId`를 09 교차 `$ref`에서 common-types `$ref`로 전환한다(AM-35, CR-26).
- [ ] `retrieve.security_context_missing` = 500 카탈로그 코드를 채널 실패 절에 인용한다(AM-25).

### 03-contracts/11-context-pack.md

- [ ] §2.8 본문을 저장 스키마 `principals[]`로 정합한다(#24).
- [ ] P-13의 `as_of` 조건을 삭제하고 `items[].acl.checked_at`을 `content_hash` 입력에서 제외한다(CR-16).
- [ ] `PackFiltersApplied`를 10 `FiltersApplied`(common-types 승격 후 `$ref`)로 전환하거나 이름을 바꾼다(CR-18, AM-35).
- [ ] §6·§9의 `item.variant_ids`·`block_refs[j].char_start` 참조를 `ContextItem` 승계 규칙(바이블 §5.5)에 맞춰 `RankedResult` 쪽 참조로 고친다(CR-20).
- [ ] P-6 제외 항목 동일성 키를 `(collection_id, chunk_id)`로 고친다(CR-22).
- [ ] §8.2 "앞 2개 세그먼트 ≤ 300"을 `text_preview` ≤ 200자로 정정한다(CR-23).
- [ ] 팩 PII 원천이 `IndexRecord` payload `pii_policy_applied` → `RankedResult.pii_policy_applied`(1.3.0 선택 필드) 경로임을 명시한다(AM-33).

### 03-contracts/12-jobs-events-and-status.md

- [ ] 이벤트 카탈로그 24 → 25종: `tenant.policies.changed`(도메인 "테넌트") `data` 타입 초안과 `EVENT_BINDINGS` 행을 추가한다(AM-38). [T3] common-types `EventType`에 값 추가.
- [ ] [T3] `JobKind.delete_collection`을 추가하고 `collection.delete.v1`이 새 이벤트 없이 `collection.profile.changed`·`ingest.document.deleted`·`audit.admin.action`을 재사용함을 기술한다(AM-37). 이 항목 반영 전에는 validate-contracts가 `JobKind` 불일치 ERROR를 낸다.
- [ ] §6.2 `audit.admin.action.action` 어휘를 확정한다(`delete_collection`, `manage_collection`, `gc_sweep`, `manage_tenants`, `rotate_api_key` 등)(#117).
- [ ] `IndexConsistencyMismatchData` 선택 필드 `kind`·`observed_generations`를 등재한다(#172, 계약 minor).
- [ ] 미해결 16(`outbox.published_seq`)을 "실측 후 재발의"로 격하한다(R-09).
- [ ] §5 `source` 값 집합 `urn:rag:api`·`urn:rag:worker`를 "바이블 §6.5 1.3.0 결정"으로 표기하고 I-20의 SSE 진행률 = 스테이지 경계(세부 진행률은 폴링)를 바이블 §14 1.3.0으로 인용한다(AM-13·AM-20).
- [ ] `job.progress.updated`는 AM-54 보류(UX 요구 확인 시 minor)로 남긴다.
- [ ] `JobStatus.idempotency_key`(Y)와 배치 자식 잡 NULL 허용(AM-44)의 충돌 여부를 판정해 기록한다.

### 03-contracts/13-error-model.md

- [ ] `stage-error`·`problem-details` 스키마를 common-types `$ref` 래퍼로 전환하고 §2.2 문구를 실제 파일과 일치시킨다(#6).
- [ ] §3.2 카탈로그 표에 AM-36 16개 코드를 추가하고 개수 68 → 84를 대조한다(재시도 열: `no` = `parse.block_limit_exceeded`·`parse.container_limit_exceeded`·`contract.schema_type_mismatch`·`contract.upcast_failed`·`render.template_unsupported`·`api.not_found`(404)·`api.quota_exceeded`, `—` = 나머지 경고)(트리아지 미해결 6).
- [ ] §3.2 `fetch.scheme_unsupported` 설명을 02와 맞춘다(#38).
- [ ] E7·이슈 5를 "`retrieve.security_context_missing` = HTTP 500, 카탈로그 코드로 실패"로 확정한다(AM-25).
- [ ] `enrich.extractor_timeout`이 청크 단위 `Warning.code`로도 쓰임을 표에 비고로 둔다(AM-36).
- [ ] `ProblemDetails.instance` 타입을 `string(uri-reference)`로, 선택 필드 7종을 "바이블 §5.3 1.3.0 등재"로 표기 전환한다(AM-28, CR-34).
- [ ] `api.quota_exceeded` HTTP 상태는 05-api/01 §9 확정값을 인용한다(트리아지 미해결 4).

### 03-contracts/14-schema-versioning-and-compatibility.md

- [ ] 미해결 15(`SchemaDiffReport` 인벤토리 등재)를 "종결: 바이블 §5.1·§5.7 1.3.0(AM-01) — 인벤토리 35종, `CompatLevel`·`SchemaChangeKind` 등재"로 닫고 범위 절의 "인벤토리 대상 아님" 문구를 고친다. `GET /v1/schemas/{name}` 게시 대상 여부도 같은 결정에 맞춘다.
- [ ] §3.1 변경 절차 표에 바이블 §1.2 1.3.0 행(필수 → 선택화·제약 완화 = minor 조건부, 제약 강화 = major)을 반영한다(AM-23).
- [ ] 계약 `schema_version` 1.0.0 유지(M1 이전 개정) 예외를 §3.1에 1행으로 명시한다(트리아지 미해결 5, 바이블 범위 절 1.3.0 변경 이력).
- [ ] 예시 4의 `source`를 `urn:rag:worker`로 고친다(CR-42, AM-13).
- [ ] [T3] `ContractsCompat` 문법(§4.3)을 common-types로 승격하고 `plugin-meta.schema.json`을 맞춘다(CR-38, AM-35). 오류 코드 `contract.schema_type_mismatch`·`contract.upcast_failed`·`render.template_unsupported`를 등재 표기로 전환한다(AM-36).

### 03-contracts/15-collection-profile-and-policy-contracts.md

- [ ] `flip_order[] ⊆ backends[].role` 불변식에 번호를 부여한다(#112).
- [ ] `EmbedConfig.sparse_bm25.avgdl`·`dense.prompts`를 등재한다(#30).
- [ ] [T3] `Profile.profile_hash`(readOnly, N)를 추가하고 §3.8 계산식과 연결한다(AM-34, 완전성 #12).
- [ ] [T3] `EgressPolicy.strip_query_keys`를 §8에 정의한다(AM-30). `ingest.normalize.pii.reject_entities: tuple[str, ...]`(korean-gov `[KR_RRN]`, `policy=reject`와 병용 시 `profile.invalid`)를 추가한다(AM-43).
- [ ] `GateSpec`의 `metric?`·`dataset?`·`min_delta_pt`·`promote_to`·`tool`을 "바이블 §5.6 결정(1.2.1 반영, AM-34 확인)"으로 표기 전환한다(CR-37).
- [ ] `mapping_version`의 계약 위치를 이 문서에서 확정해 바이블 미해결 20을 닫을 근거를 만든다(CR-44).
- [ ] `PackConfig.k_max ≤ 20`·`ChannelConfig.top_k ≤ 300`으로 정합한다(CR-46). 경고 코드 `profile.gate_pending`을 검증 규칙 표에 추가한다(AM-36).
- [ ] [T3] `ProfileId`·`KebabName`을 common-types `$ref`로 전환한다(AM-35).

### 03-contracts/16-eval-feedback-and-sidecar-contracts.md

- [ ] 미해결 1(`relevance_max`)과 `topics_ref`·`language` "미등재" 표기를 "바이블 §5.6 1.3.0 등재(AM-34)"로 전환한다.
- [ ] EF-9 "current 커밋"을 08 §8·IC-5 정의(`documents.current_commit_id`가 가리키는 committed ∧ superseded_by 없음, 모드 A green 제외)로 정합한다(CR-40).
- [ ] `index_commit_ids` 상한 2,000을 `EvalRun` 64KB 안에서 재산정하고 이벤트 쪽은 `index_commits_hash`로 완전성을 보장한다(CR-41).
- [ ] §6.2 `dictionary_hash` 정규화 행 정의가 바이블 §6.2 1.3.0에서 정본 참조로 채택되었음을 표기한다(AM-12, CR-44).
- [ ] §7.3 "비재시도 `parse.*`는 폴백 없이 전파"를 ADR-0033 patch와 같은 문구로 유지한다(CR-45).
- [ ] A3 L1626 pyhwp 문맥 검토.

### 04-pipelines/01-pipeline-framework.md

- [ ] `lineage_refs.source` = detect 출력 `SourceDocument` 계약 산출물로 정정한다(R-10, CR-01; L576·L628·L1094 부근).
- [ ] `ctx.lineage["ParsedDocument"]`(L93~L147 부근)를 잠정에서 결정으로 전환한다: `chunk`의 `requires_lineage = ("ParsedDocument",)`, `enrich` LLM 서브스텝 `("ChunkSet",)`, 선언 가능 = 입력 `lineage_refs`로 고정되는 상류만, `stage_key` 불변(바이블 §4.1 1.3.0, AM-26, CR-04).
- [ ] `StageContext` 정의에 `plan: QueryPlan | None`·`artifacts: DerivedArtifacts`를 추가하고 "스테이지는 I/O를 직접 쓰지 않는다" 규칙과의 관계(셸이 저장·계보 기록)를 적는다(AM-27).
- [ ] §7.1 `stage_key` 표를 입력 해시 규약(`detect`·`parse` = `content_hash`, 그 외 `input_ref.blake3`, `recount` 지문 = `tokenizer_id` 포함)으로 갱신한다(AM-05).
- [ ] `format_detector` 프로파일 위치를 04-pipelines/03과 합의해 한쪽을 정본으로 적는다(#7).
- [ ] `model_ids`의 `dict:` 항목 인스턴스 규약을 04-pipelines/09와 합의한다(#44). API 모델 `model_id` = `{provider}:{model}`(`@{revision}` 선택)을 반영한다(AM-11).
- [ ] 원본 바이트 포트를 `DerivedArtifacts`와 구분해 기술한다(#86).
- [ ] §13 `rag run-stage`를 "개발 전용 하위 명령, 정본 10-development/02 §CLI"로 인용하고, CLI·테스트 유틸 절은 10-development/04 이관 대상으로 표시한다(완전성 #10, #168 P2).
- [ ] 캐시 제외 스테이지 산출물 경로·점유 `stage_key` 비덮어쓰기(바이블 §13.3 1.3.0)를 산출물 저장 절에 인용한다(AM-19).
- [ ] 1,112행 — 900행 초과 절 이관은 P2에서 처리한다(D4-2).

### 04-pipelines/02-fetching-and-source-resolution.md

- [ ] fetch 출력 잠정값 규약(`format = unknown` 또는 힌트, `format_confidence = 0.0`, 잠정 `media_type`, `container_flags` 자리표 = 미판정)을 바이블 §4.2·§5.4 1.3.0으로 인용한다(AM-06).
- [ ] L296 `EgressPolicy.strip_query_keys`의 "제안 필드명" 표기를 "바이블 §5.3 1.3.0 등재(AM-30)"로 바꾸고 §3.6 표를 기본 목록 정본으로 둔다(미해결 16 종결 근거). `max_bytes`·`connect_timeout_ms`·`allowed_ports`도 등재 사실로 표기한다.
- [ ] `lineage_refs.source` 서술(L94·L432)이 detect 출력 기준임을 확인한다(CR-01·CR-11: fetch 출력은 `source`에 넣지 않음).
- [ ] 캐시 제외 스테이지(`fetch`) 산출물 키 `tenants/{tenant_id}/artifacts/source-document/{blake3[:2]}/{blake3}.json`을 저장 절에 반영한다(AM-19).
- [ ] 메트릭 `rag_fetch_bytes_total{outcome}`(L381 부근)을 정본 등재로 표기 전환한다(AM-41).
- [ ] L240 "(작성 예정)" 표기를 제거한다(공통 전방 참조).

### 04-pipelines/03-parsing-router-and-format-detection.md

- [ ] `lineage_refs.source`를 detect 출력 `SourceDocument`로 정정한다(R-10; L81·L632·L647).
- [ ] §4.5 `parse.pdf.route` 값을 03-contracts/01 §2.5 라우트 이름으로 맞춘다(#76).
- [ ] §7.2 변환기 digest 기록 규약을 `derived` 키 `options_hash`(바이블 §6.2 1.3.0)와 함께 정리한다(#86, AM-40).
- [ ] `ParseRouterStage` 모듈 위치 `adapters/parse/router.py`를 바이블 §12 1.3.0으로 인용한다(AM-22).
- [ ] `profile_option` 값 목록을 이 문서가 정본으로 소유함을 표로 명시한다(형식 `{format}_{variant}`, AM-09).
- [ ] §8 관측성 표: 메트릭 `rag_parse_format_mismatch_total`(라벨 없음)·`rag_parse_fallback_total{stage}`·`rag_parse_source_kind_total{outcome}`·`rag_parse_page_status_total{outcome}`, 스팬 `rag.ingest.detect`·`rag.parse.call`을 정본 등재로 전환하고 라벨을 바이블 §6.5 1.3.0 표기로 맞춘다(미해결 14 종결, AM-41).
- [ ] `parse(텍스트)` `resumable` = 후보 어댑터 `Capabilities`로 결정(흐름 포맷 no)을 바이블 §4.4 1.3.0으로 인용한다(AM-07).
- [ ] A3 문맥 검토: L650 PyMuPDF, L24·L51·L632·L636·L650 pyhwp.

### 04-pipelines/04-parser-hwpx-and-hwp.md

- [ ] 암호화 HWPX 사이드카 어댑터 모듈 `adapters/parse/hwpx_hwpxlib_sidecar.py`를 바이블 §12 1.3.0으로 인용한다(AM-22).
- [ ] `standard` 배포용 HWP = 테넌트 옵트인 시 Tika `HwpV5Parser` 텍스트(`degraded`), 옵트인 없으면 `parse.distribution_document`를 바이블 §7.1 1.3.0 문구로 맞춘다(AM-14).
- [ ] `section_index` = HWPX `secPr` 인덱스(바이블 §5.3 1.3.0)로 표기한다(AM-29).
- [ ] ConvertRequest/Response ↔ parse 실패 정책 서술을 바이블 §4.2와 대조한다(CR-45).
- [ ] A3 `pageBreak` 행(L131·L136·L411): OWPML 속성명 철자(`pageBreak` 원문 표기)인지 확인하고 계약 쪽 `page_break`(BlockType)와 구분해 표기한다.
- [ ] A3 pyhwp 행 문맥 검토: L19·L155·L464·L472·L590.

### 04-pipelines/05-parser-pdf.md

- [ ] 오류·경고 코드 `parse.page_ocr_failed`·`parse.page_skipped`·`parse.block_limit_exceeded`(L695·L798 부근)를 "바이블 §5.7 1.3.0 등재(AM-36)"로 표기 전환한다.
- [ ] `profile_option` 값(`pdf_standard`, `pdf_fast_cpu`, `pdf_scanned_gpu`, `pdf_vlm_gpu`, `pdf_airgapped`)을 04-pipelines/03 정본 목록과 대조한다(AM-09).
- [ ] PDFium `helper_process`·lite `page_route`는 AM-52 보류(측정 후 minor)로 현행 값을 유지한다고 적는다.
- [ ] 파생물 키에 DPI·OCR 언어 `options_hash`를 반영한다(AM-40).
- [ ] A3 문맥 검토: L78·L95·L761·L783 PyMuPDF(AGPL 옵트인 사이드카 문맥 명시).

### 04-pipelines/06-parser-doc-and-docx.md

- [ ] `parse.container_limit_exceeded`·`parse.element_path_synthesized`·`parse.footnote_unanchored`·`parse.table_structure_fallback`을 "바이블 §5.7 1.3.0 등재(AM-36)"로 전환한다.
- [ ] `section_index` = OOXML `w:sectPr` 인덱스를 반영한다(AM-29).
- [ ] `parser_fingerprint.parser_version`이 docling·docx2python 두 패키지일 때 `docling==x;docx2python==y`(패키지명 오름차순)로 기록함을 예시에 반영한다(AM-09).
- [ ] 03-contracts/03 §3.1 DOCX(OOXML) `element_path` 행 분리(#33)와 문법을 맞춘다.
- [ ] A3 문맥 검토: L595·L633 pyhwp.

### 04-pipelines/07-parser-html.md

- [ ] 03-contracts/03 §5.3 (e) 확정("폴백 체인에서 실패 뒤 성공 = `degraded`") 후 HTML 경로의 `degraded` 근거를 재검토한다(#88).
- [ ] `parse.extractor_fallback`(L670 부근)을 "바이블 §5.7 1.3.0 등재(AM-36)"로 전환한다.
- [ ] `parse(텍스트)` HTML의 `resumable = no`(흐름 포맷)를 바이블 §4.4 1.3.0으로 인용한다(AM-07).

### 04-pipelines/08-parser-txt-md-and-others.md

- [ ] 미해결 17(하위 경로 라이브러리 바이블 반영)을 "종결: 바이블 §7.1·§12 1.3.0(AM-42)"로 닫고 L93 라이선스 행의 "**제안**" 표기를 결정으로 바꾼다(`mdit_py_plugins`, `clevercsv`, `orjson`/`ijson`, `lxml`).
- [ ] `parse(텍스트)` TXT·MD `resumable = no`를 바이블 §4.4 1.3.0으로 인용한다(AM-07).
- [ ] L845 "(작성 예정)" 표기를 제거한다.
- [ ] `application/xml` 라우팅(03-contracts/00 §9.3 #166)과 이 문서의 XML 감지 규칙을 대조한다.

### 04-pipelines/09-normalization-and-cleaning.md

- [ ] `pii.reject_entities`(L387·L407 "제안") → "바이블 §7.3 1.3.0 등재(AM-43)"로 전환하고 미해결 7·20 중 해당 항목을 닫는다. `steps`는 제안 지위를 유지한다.
- [ ] `table_cell_views`·`genre_source`·`pii_report.tokenize_mode_applied`·`stats`·`pii_spans[].row/col` 생산 규칙이 바이블 §5.4 1.3.0 필드와 일치하는지 대조한다(AM-31).
- [ ] 미주 기본 `separate`를 04-pipelines/10 §1 정본 표에 병기하도록 10과 맞춘다(#1).
- [ ] §8.5 diff 리포트 CLI를 "개발 전용 하위 명령, 정본 10-development/02 §CLI"로 인용한다(완전성 #10, AM-22).
- [ ] 경고 `normalize.segmenter_fallback`은 `Warning.code`로만 기록(StageError 아님)을 확인한다(CR-33).
- [ ] 옛한글 조합형 자모는 AM-48 보류 잠정 규칙(`normalize.nfd_residual`)을 한 줄 적는다.
- [ ] `dictionary_hash` 정규화 행은 03-contracts/16 §6.2를 인용한다(AM-12, CR-44).

### 04-pipelines/10-chunking-strategies.md

- [ ] `ctx.lineage["ParsedDocument"]`(L70·L254·L694)를 잠정에서 결정으로 전환한다(바이블 §4.1 1.3.0 `chunk` `requires_lineage`, AM-26, CR-04). 사용 필드는 `Block.type`·`numbering_label`·`provenance`·`TableData`·`caption_of`로 한정한다.
- [ ] 표 청크 `original_char_*`를 원문 기준 `offset_map` 사상(표는 03 §6 선형화 텍스트 기준)으로 정정한다(CR-03; L232~L247 부근).
- [ ] 부모 청크 `text` = 자식 리프 `text` U+000A 결합, `block_refs` = 자식 refs 재기준을 인용한다(CR-07).
- [ ] `Chunk.ordinal` 정의를 바이블 §5.4 1.3.0 문구(같은 부모 아래 형제 순서, 0-based)로 맞춘다(AM-09).
- [ ] §1 정본 표에 미주 기본 `separate`를 병기한다(#1).
- [ ] 청커가 `table_cell_views`를 써야 하는 조건(`pii_report.policy_applied ≠ keep`)을 바이블 §5.4 1.3.0으로 인용한다(AM-31).
- [ ] L719 "(작성 예정)" 표기를 제거한다.

### 04-pipelines/11-enrichment.md

- [ ] §3 `G` 행에 규칙 2(b) 예외 문구를 추가한다(#29).
- [ ] `enrich` LLM 서브스텝의 `requires_lineage = ("ChunkSet",)`(바이블 §4.1 1.3.0)를 반영한다(AM-26).
- [ ] `budget_used.charged_tokens`(L404·L517~L519)를 "바이블 §5.4 1.3.0 등재(AM-32)"로 전환한다.
- [ ] LLM 보강 캐시 키 입력(`embed_text` = `generated` 미포함 조립 결과, 요약은 섹션 텍스트 해시)과 경로 `derived/llm_enrich/{key[:2]}/{key}.json`을 바이블 §6.2·§13.3 1.3.0으로 인용한다(AM-12·AM-19).
- [ ] 합성 생산자 `plugin_id = enricher.pipeline`, API 모델 `model_id = {provider}:{model}`(`@{revision}` 선택, 없으면 `created_at` 병기)을 반영한다(AM-11; L45·L79·L90·L181·L387~L389 부근).
- [ ] `enrich.extractor_timeout`의 청크 단위 `Warning.code` 겸용을 실패 정책 절에 적는다(AM-36).
- [ ] `enrich.llm_unavailable` 소진 시 partial은 AM-47 보류 — 현행 "재시도 소진 = 잡 `failed`, `retry?stages=enrich`"를 유지한다고 적는다. premium `enrichment_budget_tokens` 재산정은 AM-52 보류.
- [ ] L586 `/v1/tenants` 인용이 바이블 §14 1.3.0 경로와 일치하는지 확인한다.

### 04-pipelines/12-embedding.md

- [ ] `embed.token_overflow` 절단 시 봉투 `quality=degraded` + 경고(StageError 아님)를 바이블 §4.2 1.3.0으로 인용한다(AM-07, CR-33).
- [ ] `values = 1.0` 규칙은 04-pipelines/15 `tf_q`로 위임한다고 적는다(#186).
- [ ] `embed` Producer 지문의 `embedding_space_id`(공간 설정)와 `embedder_fingerprint`가 별개 키임을 인용한다(AM-05).
- [ ] 메트릭 `rag_embed_batch_tokens_count`·`rag_embed_truncated_total`·`rag_embed_cache_total`(미해결 11)을 정본 등재로 전환한다(AM-41).
- [ ] A3 L244 SPLADE-v3 문맥 검토(제외, O-02).
- [ ] "(작성 예정)" 4곳(L544·L613·L626·L716) 제거.

### 04-pipelines/13-indexing.md

- [x] §4.1 `hnsw_config {m: 0, payload_m: 0}`를 반영하고 Qdrant 동작 "확인 필요"를 유지한다(#65). 값은 이미 `m:0, payload_m:16`으로 바이블 §13.4·§10.4와 일치했다 — 확인 문구·확인 필요 태그만 §4.1 결정문에 추가.
- [x] `values = 1.0` 규칙을 04-pipelines/15 `tf_q`로 위임한다(#186).
- [x] 미해결 13(두 해시 불변 프로파일 변경)을 `**미정(O-11):**`로 표기하고 잠정 규칙(자동 재색인 불가)을 인용한다(AM-21·AM-45).
- [x] `index_generation` 할당 = `max + 1` 비재사용(바이블 §11.4 (6) 1.3.0)을 사가 절에 인용한다(AM-18).
- [x] `index` 산출물(`IndexCommit`) 저장 키 = 캐시 제외 스테이지 바이트 해시 키(바이블 §13.3 1.3.0)를 반영한다(AM-19).
- [x] payload 선택 필드 `token_count_primary`·`ordinal`·`text_truncated`·`pii_policy_applied`가 `hydrate` 대상임을 매핑 표에 적는다(AM-33).
- [x] Nori stoptags·필터 순서 변경 제안은 AM-51 보류(M2 골든셋 A/B 통과 시 minor) — 바이블 §13.4 현행(`J*`·`E*`·`S*`)과 §5.1 한계 명시를 유지한다.
- [x] `mapping_version` 위치는 03-contracts/15 확정 대기로 표기한다(CR-44).
- [x] "(작성 예정)" 4곳(L38·L91·L576·L699) 제거 — 09-operations/04·07이 작성 완료되어 실제 링크로 교체.
- 미해결 이슈 17(바이블 §11.4 mermaid 세미콜론)은 바이블 1.3.0 AM-24로 해소되어 "해소" 표기.

### 04-pipelines/14-query-understanding.md

- [x] `QueryPlan.filters.effective_hash` = 계획 필터 트리 해시(`as_of` 바인드 이름)로 바이블 §6.2 1.3.0 채택 사실을 인용한다(AM-12, CR-17).
- [x] 플랜 캐시 키에 `H("opts", canonical_json(플랜에 영향 주는 QueryRequest 옵션))` 항을 추가한다(L43·L478, AM-40) — 이미 있던 값을 "09가 더한 잠정 part"에서 "바이블 1.3.0이 채택"으로 지위 격상, 미해결 이슈 19 해소.
- [x] 합성 생산자 `plugin_id = query_transformer.pipeline`(L46·L701 부근)을 반영한다(AM-11).
- [x] 질의 측 스테이지가 `ctx.plan`으로 `QueryPlan`을 읽는 경로(바이블 §4.1 1.3.0)를 반영한다(AM-27).
- [x] 제외 항목·`exclude_ids` 동일성 키 `(collection_id, chunk_id)`를 확인한다(CR-22; L429~L484) — `exclude_ids`는 의도적으로 `chunk_id` 단일 키(컬렉션·세대 무관)이며 CR-22 후보 동일성과는 별개 식별 공간임을 확인·주석.
- [x] `query_hash`(감사·로그 상관 키)를 감사 이벤트 절에 인용한다(AM-40).
- [x] "(작성 예정)" 2곳(L33·L862) 제거 — 05-api/05-mcp-server·09-operations/02가 작성 완료되어 실제 링크로 교체.

### 04-pipelines/15-hybrid-search-and-fusion.md

- [x] `hydrate` `with_payload` 목록을 바이블 §4.3·§8.1 1.3.0(조건 필수 18필드 + 선택 4종)과 일치시킨다(AM-08·AM-33, CR-19; L57·L89·L217·L222).
- [x] L173 `min(top_k …)` 서술을 `pack.k_max = 프로파일 query.pack.k_max`(`top_k`와 별개)로 정합한다(CR-14).
- [x] 후보 동일성 `(collection_id, chunk_id)`·`record_id` 타이브레이크를 확인한다(CR-22) — RRF 누적기·정렬 키가 이미 `record_id`(collection_id 합성) 기준이라 일치 확인, 변경 불필요.
- [x] `retrieve.security_context_missing` = HTTP 500 카탈로그 코드(L158·L170·L211)를 바이블 §5.7·§10.3 E7 1.3.0으로 맞춘다(AM-25).
- [x] `retriever.pipeline` 예약 구현명(다중 채널 합성 생산자)을 반영한다(AM-11).
- [x] A3 문맥 검토: L227·L649(기각 기술 행) — 이미 ADR-0014 인용과 함께 기각 문맥 명확, 변경 불필요.

### 04-pipelines/16-reranking.md

- [x] 09-operations/04 링크의 "작성 예정" 표기를 제거한다(#147; L603·L755).
- [x] 리랭커 API 모델 `model_id` 표기(`{provider}:{model}`, 자체 호스팅 `{repo}@{revision}`)를 바이블 §6.1 1.3.0과 맞춘다(AM-11) — 이 문서의 6개 백엔드는 모두 자체 호스팅이라 `{repo}@{revision}`만 해당함을 명시.
- [x] 게이트 표기(`candidate`, `min_delta_pt`)가 바이블 §5.6 게이트 값 행과 일치하는지 확인한다(CR-37) — 바이블 §7.3 예시와 완전히 일치 확인, 인용만 추가.
- [x] A3 L751 Infinity 문맥 검토(제외, D-16 v1.1).

### 04-pipelines/17-post-processing-and-context-packing.md

- [ ] `with_payload`·`hydrate` 필드 참조(L148·L1056·L1069)를 바이블 §4.3 1.3.0 목록과 맞춘다(AM-08, CR-19).
- [ ] `RankedResult` 선택 필드(`token_count_primary`·`ordinal`·`text_truncated`·`pii_policy_applied`)를 패킹 사전 예산·절단 표시·PII 표지 원천으로 인용한다(AM-33; L148·L163·L249·L355).
- [ ] `content_hash` 입력에서 `items[].acl.checked_at`을 제외한다(CR-16; L271·L771·L808·L856).
- [ ] `ContextItem` 승계 규칙(`heading_path → header.section_path`, `variant_ids`·`channels_hit`·`block_refs` 비승계)을 바이블 §5.5로 인용하고 L329~L355 참조를 고친다(CR-20).
- [ ] `tokenizer.name` = `tokenizer_id` 형식(`anthropic:<target-model-id>`)으로 예시를 고친다(L58·L253, AM-16, CR-24).
- [ ] `k_max` 상한 20, `top_k`와 별개임을 확인한다(CR-14·CR-15). `packer.default` 예시를 반영한다(AM-11).
- [ ] 분량 이관은 P2에서 처리한다(#119, 1,084행).

### 04-pipelines/18-advanced-retrieval-graph-raptor-agentic.md

- [ ] 이 문서가 기록한 타 문서 제안(04-pipelines/11·13, 03-contracts/05·09)을 소유 문서가 반영했는지 확인하고, 반영·기각 결과를 미해결 이슈에 적는다(#31).
- [ ] 후보 동일성 키 `(collection_id, chunk_id)`(L52·L82·L471·L472)를 CR-22와 대조한다.
- [ ] `original_char_*` 기준(원문 `Block.text`)을 확인한다(CR-03·CR-21; L285·L286).
- [ ] `retrieve.security_context_missing`(L110) = 500 카탈로그 코드로 맞춘다(AM-25).
- [ ] 그래프·RAPTOR 보강 생산자의 `plugin_id`(`enricher.pipeline` 합성 시)를 반영한다(AM-11).

### 04-pipelines/19-update-delete-and-reindexing.md

- [ ] §6.1 컬렉션 삭제(`JobKind.delete_collection`, `collection.delete.v1`, `collections.deleted_at`)를 "바이블 §5.7·§11.2·§13.1 1.3.0 결정(AM-37)"으로 전환하고 미해결 17을 닫는다(완전성 #12).
- [ ] 미해결 1 "미정(O-xx 미배정)" → `**미정(O-11):**`, blue/green 채움 중 원장 포인터 항목은 `**미정(O-12):**`로 표기한다(AM-21; L331·L410·L586).
- [ ] 삭제 잡은 항상 tombstone 커밋(`record_count=0`)을 만든다는 규칙을 확인한다(CR-30; L45·L244·L263).
- [ ] `index_generation = max + 1` 비재사용을 인용한다(AM-18, CR-31; L74·L406).
- [ ] 취소 경합은 AM-46 잠정 규칙(플립 시작 후 취소 → `running → succeeded`, 취소 API 202)을 인용한다(CR-29).
- [ ] `POST /v1/collections/{collection_id}/consistency-check`(`JobKind.consistency_check`)·`POST /v1/profiles`(불변 게시)를 바이블 §14 1.3.0 경로로 인용한다(AM-39; L509·L324·L374).
- [ ] `lineage_refs.source`(L520)를 detect 출력 기준으로 확인한다(CR-01).
- [ ] 재색인 모드 B·이름 불변 백엔드 일괄 플립은 AM-45 보류 잠정 규칙(자동 재색인 불가 + 운영자 대안)을 결정 절에 명시한다.

### 05-api/01-api-design-guidelines.md

- [ ] §3.1 예외 행 "교차 테넌트 관리 — v1 API 표면에 없다(§14에 `POST /v1/tenants` 없음)"(L112)를 폐기하고 `/v1/tenants` 계열(바이블 §14 1.3.0)로 바꾼다. `rag` CLI는 같은 API를 호출하는 래퍼다(트리아지 §4 #3, AM-39).
- [ ] 경로 규칙에 단일 인스턴스 자원 예외 `GET /v1/version`(단수)을 등재한다(바이블 §6.7 1.3.0). `/v1/capacity`는 AM-53 보류로 예외 목록에서 뺀다.
- [ ] §8 래퍼·DTO 규칙에 "관리 API 응답 객체 = API 전용 뷰, `api/` Pydantic 단일 출처, 계약 타입은 `schemas/` `$ref`"를 바이블 §5.1 1.3.0으로 인용한다(AM-02, FR-API-04).
- [ ] §9 오류 매핑 표에 `api.not_found`(404), `api.quota_exceeded`(상태 확정: 02-architecture/07과 같은 값), `contract.acl_deny_all`(경고, 접수 성공), `retrieve.security_context_missing`(500)을 추가한다(AM-25·AM-36, 트리아지 미해결 4).
- [ ] §9.3 상태 표에 `DELETE /v1/collections/{collection_id}` 202 `JobStatus(kind=delete_collection)`, `POST …/consistency-check` 202를 반영한다(AM-37·AM-39).
- [ ] `ProblemDetails` 선택 필드 `retry_after`·`request_id`, `instance` = uri-reference를 바이블 §5.3 1.3.0으로 인용한다(AM-28).
- [ ] 배치 멱등(`idempotency_keys.job_ids`로 배치 응답 재현)을 멱등 절에 반영한다(AM-44).
- [ ] A3 L551 문맥 검토.

### 05-api/02-ingestion-api.md

- [ ] `GET /v1/jobs/{job_id}/events` SSE 범위 = `job.state.changed` + 스테이지 경계 진행률, 세부 진행률은 `GET /v1/jobs/{job_id}` 폴링으로 맞춘다(바이블 §14 1.3.0, AM-20). `job.progress.updated`는 AM-54 보류.
- [ ] 잡 접수형 DELETE 멱등 지문(`wire_body = {}`)을 05-api/04와 대조한다(#52).
- [ ] 배치 수집 멱등: `idempotency_keys.job_ids`로 배치 응답 재현, 자식 잡 `jobs.idempotency_key` NULL 허용을 반영한다(AM-44).
- [ ] IR-5 잠금 ACL 수집은 400이 아니라 경고 `contract.acl_deny_all`과 함께 202 접수로 바꾼다(AM-17·AM-36).
- [ ] 취소 API: AM-46 잠정 규칙(플립 시작 후 취소는 202 + 현재 `JobStatus`, 잡 `running → succeeded`)을 L426~L429 서술과 맞춘다(CR-29).
- [ ] 삭제 커밋 = tombstone(`record_count=0`) 규칙을 확인한다(CR-30; L657).
- [ ] `POST /v1/documents/{document_id}/unmask`(L523·L858·L870)를 "바이블 §14 1.3.0 등재"로 표기 전환한다(AM-39).
- [ ] `dry_run`은 AM-53 보류 — 202→200 의미 변경을 제안 지위로 유지한다.

### 05-api/03-retrieval-api.md

- [ ] 보안 필드 필터 거부를 422 `plan.filter_field_forbidden`으로 정정한다(#28).
- [ ] `retrieve.security_context_missing` = 500(서버 측 계약 위반, 카탈로그 코드), 클라이언트 원인은 `plan.security_context_missing` 400을 오류 표에 반영한다(AM-25; L71).
- [ ] `content_hash`에서 `items[].acl.checked_at` 제외를 확인한다(CR-16; L69·L294·L324·L367).
- [ ] `ContextItem` 승계(`variant_ids` 비승계 등)와 응답 필드 표를 대조한다(CR-20; L286·L310).
- [ ] 미해결 17(`top_k` 수용만)은 CR-14 정본(`pack.k_max = 프로파일 값`)을 유지한다고 결론을 적는다.
- [ ] `text_preview` ≤ 200자(L112·L384)를 확인한다(CR-23).
- [ ] `plan` 캐시 키 `opts` 항(L666)을 반영한다(AM-40).

### 05-api/04-management-api.md

- [ ] 엔드포인트 표의 "제안" 정본 열을 "§14"로 전환한다: `/v1/tenants`·`/v1/tenants/{tenant_id}`·`GET …/policies`, `/v1/api-keys*`, `/v1/plugins`·`/v1/plugins/{plugin_id}`, `GET /v1/schemas`, `GET /v1/version`, `POST …/consistency-check`, `GET /v1/audit-events`, `POST /v1/profiles`, `POST …/unmask`(AM-39). `/v1/capacity`·`/v1/tenants/{tenant_id}/dictionary`·`/v1/plugins/{plugin_id}/health`는 AM-53 보류로 "제안" 유지.
- [ ] 미해결 1(§14 minor 발의)을 "종결: 바이블 1.3.0 AM-39(보류분 AM-53 제외)"로 닫는다.
- [ ] 미해결 2(응답 객체 계약 지위)를 "종결: API 전용 뷰(바이블 §5.1 각주, AM-02)"로 닫는다. `TenantTier`·`Role`은 §5.7에 등재하지 않는다(트리아지 §4 #5).
- [ ] 미해결 3(`tenant.policies.changed`)·6(`delete_collection`)·8(`Profile.profile_hash`)·9(`profile.gate_pending`)을 각각 AM-38·AM-37·AM-34·AM-36으로 종결한다(완전성 #12).
- [ ] 테넌트 절: `TenantStatus`(`active, disabled`), `quotas{documents_max, storage_bytes_max, qps_max}`, `tier` 읽기 전용(승격 `tier.promotion.v1`), `tenants.disabled_at`을 필드 표에 반영한다(AM-38·AM-39). 테넌트 생성을 CLI·Helm 경로로 두자는 정정 요청이 남아 있으면 폐기한다(트리아지 §4 #3).
- [ ] `/healthz` = liveness(의존성 미포함), 의존성 상태는 `/readyz`로 09-operations/03과 맞춘다(#174).
- [ ] 잡 접수형 DELETE 멱등 지문(`wire_body = {}`)을 05-api/02와 대조한다(#52).
- [ ] 미해결 12의 액션 목록을 02-architecture/07 §4.1 정본 표로 이관했음을 적는다.

### 05-api/05-mcp-server.md

- [x] `top_k`(1..50)는 수용만, `pack.k_max`는 프로파일 값(standard 20, 상한 20)임을 CR-14·CR-15로 확인한다(L152·L442·L537). — 확인 완료, 기존 서술이 이미 정본과 일치(수정 불필요).
- [x] `concise` 응답의 `text_preview` ≤ 200자를 확인한다(CR-23; L229·L236·L428). — 확인 완료, 일치.
- [x] 슬림 `structuredContent` 항목이 `ContextItem` 승계 규칙(`variant_ids` 비승계)을 따르는지 대조한다(CR-20; L243·L254·L747·L758). — 확인 완료, `SlimItem`에 `variant_ids`·`channels_hit`·`block_refs` 없음(일치).
- [x] 제외 항목·`exclude_ids` 동일성 키 `(collection_id, chunk_id)`를 확인한다(CR-22). — 확인 완료. `seen_chunk_ids`는 03-contracts/09가 정의한 대로 콘텐츠 주소(`chunk_id`) 단독 스코프-무관 키를 그대로 쓰며 이 문서 서술과 일치(CR-22는 candidate·result 동일성 키 — 10 RS-11 대상이며 exclude_ids와는 별개 사안).
- [x] 오류 매핑에 `api.not_found`(404)를 "바이블 §5.7 1.3.0 등재"로 표기하고 `ProblemDetails` 선택 필드를 인용한다(AM-28·AM-36). — §8 오류 표(`api.not_found` 행), 레이트 리밋 `retry_after`, `ProblemDetails.instance` 설명에 반영(AM-28·AM-36 인용).

### 05-api/06-client-sdks.md

- [x] SDK 오류 클래스 매핑에 AM-36 신규 코드(`api.not_found`, `api.quota_exceeded`, `contract.schema_type_mismatch`, `contract.upcast_failed`)를 추가한다. — §4 표에 `QuotaExceededError` 신설, `NotFoundError`·`ContractViolationError` 행 갱신.
- [x] 관리 클라이언트 메서드에 `/v1/tenants`·API 키·플러그인·`GET /v1/schemas`·`GET /v1/version`·감사 이벤트를 추가하거나 "OpenAPI 코드젠 범위"로 명시한다(AM-39). — §5.1 표에 `client.api_keys`·`client.plugins`·`client.audit` 신설, `client.tenants`·`client.schemas`·`client.system` 확장(`/v1/tenants` 목록·생성은 04 미게시로 각주만).
- [x] 컬렉션 삭제가 잡(`JobKind.delete_collection`, 202)을 반환함을 반영한다(AM-37; L151). — §3.3 멱등 키 표 뒤에 명시 각주 추가.
- [x] `ProblemDetails.retry_after` 처리(재시도 대기)를 SDK 재시도 절에 인용한다(AM-28). — §3.2에 `retry_after` 본문 사본 경로와 AM-28 인용 추가.
- [x] `contracts_compat` 문법을 03-contracts/14 §4.3으로 인용한다(CR-38). — 이미 §3.7에 인용되어 있어 수정 불필요(확인만).

### 05-api/07-webhooks-and-events.md

- [x] 이벤트 카탈로그 24 → 25종: `tenant.policies.changed`를 구독 가능 목록·표에 추가하고 L47·L99·L145의 "24종"·`1..24`를 25로 고친다(AM-38, CR-32). — 카탈로그 표에 `tenant.policies.changed` 행 추가, 개수 표기 전부 25로 정정(§9.1 결정 사항 요약·메트릭 라벨 카디널리티 포함).
- [x] `source` 값 `urn:rag:api`·`urn:rag:worker`를 "바이블 §6.5 1.3.0 결정"으로 표기한다(AM-13, CR-42). — 봉투 필드 요약에 인용 추가.
- [x] `dataschema`는 `data`가 완전한 인스턴스일 때만(24종 → 25종 모두 생략)을 확인한다(CR-43; L130). — 확인 및 표기 갱신.
- [x] 컬렉션 삭제는 새 이벤트 없이 `collection.profile.changed`·`ingest.document.deleted`·`audit.admin.action`을 재사용함을 이벤트 표 비고에 적는다(AM-37). — §2 카탈로그 표 뒤에 전용 문단 추가.
- [x] SSE 진행률 범위(스테이지 경계, 세부는 폴링)를 바이블 §14 1.3.0으로 인용한다(AM-20). — §9.4에 인용 추가.
- [x] L792 `api.quota_exceeded` 인용을 등재 코드로 표기 전환한다(AM-36). — S6 행·미해결 이슈 9를 "바이블 §5.7 1.3.0 AM-36 등재, HTTP 상태 미확정"으로 갱신.

### 05-api/openapi.yaml

- [x] A10(바이블 §14 ↔ openapi) 대조에서 바이블에만 있는 1.3.0 경로를 `paths`에 추가한다: `GET/POST /v1/tenants`, `GET/PATCH /v1/tenants/{tenant_id}`, `GET /v1/tenants/{tenant_id}/policies`, `GET/POST /v1/api-keys`, `DELETE /v1/api-keys/{api_key_id}`, `POST /v1/api-keys/{api_key_id}/rotate`, `GET /v1/plugins`, `GET /v1/plugins/{plugin_id}`, `GET /v1/audit-events`, `GET /v1/schemas`, `GET /v1/version`, `POST /v1/profiles`, `POST /v1/collections/{collection_id}/consistency-check`, `POST /v1/documents/{document_id}/unmask`(AM-39). 14개 경로 전부 추가(신규 컴포넌트 스키마 `Tenant`·`TenantCreateRequest`·`TenantPatch`·`TenantList`·`TenantStatus`·`TenantQuotas`·`ApiKey`·`ApiKeyCreateRequest`·`ApiKeyList`·`PluginMeta`·`PluginMetaList`·`AuditEventList`·`SchemaDescriptor`·`SchemaDescriptorList`·`VersionInfo`·`UnmaskRequest`·`UnmaskResult` 포함). `/v1/tenants` 목록·생성은 04-management-api.md가 아직 operationId를 정의하지 않아 이 문서가 잠정 확정하고 04 갱신 대상으로 표시.
- [x] A10 기존 차이(`DELETE /v1/subscriptions`, `POST /v1/subscriptions/{}`, `POST /v1/eval/runs/{}`, `POST /v1/eval/runs/{}/report`)는 바이블 §14 행의 `GET/POST/DELETE` 결합 표기를 감사기가 경로마다 곱해서 생긴 것인지 확인하고, 실제 누락이면 추가, 표기 문제면 5단계 A10 파서 수정으로 넘긴다. `POST /mcp`는 §14 `/mcp` 행과 같은 연산임을 주석으로 둔다. — 확인 결과 실제 누락 아님(각 경로는 이미 의미 있는 조합만 구현), info.description에 근거와 5단계 이관 메모 추가. `POST /mcp` 주석 추가.
- [x] `DELETE /v1/collections/{collection_id}` 응답 설명(L3464·L3525·L3605 부근)의 "`delete_collection` 채택 전 — 첫 자식 `delete_document` 잡" 문구를 `JobStatus(kind=delete_collection)` 202로 바꾼다(AM-37). — description·200/202 예시 모두 `kind: delete_collection`·`progress.unit=document`로 교체, x-rag-pending 제거.
- [x] `ProfileValidationResult.warnings[].code`의 "`profile.gate_pending` 등재 대기"(L4319 부근)를 등재 사실로 바꾼다(AM-36). — 스키마 설명·연산 `x-rag-pending` 모두 갱신.
- [x] 테넌트 응답 뷰(`Tenant`·`TenantPolicies`·`TenantUsage`)에 `status`(`TenantStatus` — common-types `$ref`, T3 등재 후)·`quotas`·`tier`(readOnly)를 반영한다(AM-38·AM-39). API 전용 뷰는 `components`에만 두고 계약 타입은 `schemas/` `$ref`로 잇는 파일 머리 주석 규칙을 유지한다(AM-02). — 신규 `Tenant`(status·quotas·tier 모두 포함) + `TenantQuotas`·`TenantStatus`($ref) 추가, `TenantPolicies`는 기존 `tier` 유지. T3가 `common-types.schema.json`에 `TenantStatus`를 이미 등재해 확인 완료.
- [x] `ProblemDetails`는 `schemas/problem-details.schema.json` `$ref`만 두므로 T3 반영(선택 필드·`instance` uri-reference, AM-28) 뒤 예시 응답만 대조한다. — T3가 `common-types.schema.json`에 `retry_after`·`request_id`·`instance`(uri-reference) 반영 완료 확인, 기존 예시(rate-limited 등)가 이미 부합해 수정 불필요.
- [x] `GET /v1/jobs/{job_id}/events` 설명을 "스테이지 경계 진행률, 세부 진행률은 `GET /v1/jobs/{job_id}` 폴링"으로 맞춘다(AM-20). — description 갱신, AM-20 인용 추가.
- [x] 파일 머리 주석의 정본 표기와 `info.description`의 바이블 인용을 1.3.0으로 갱신하고, YAML 파싱 검증(`node -e`로 js-yaml 또는 동등 파서)과 validate-contracts를 실행한다. — 파일 머리 주석·`info.version`(0.1.1)·`info.description` 갱신. Node에 js-yaml 미설치라 `.venv`(PyYAML 6.0.3)로 동등 파싱 검증 통과, `node tools/validate-contracts.mjs --root .` ERROR 0 확인(스키마·03-contracts 미변경이라 베이스라인 그대로).

### 06-adr/README.md

- [ ] 인덱스 표에 ADR-0039 행(`bible-1-3-additive-amendment-bundle`, 바이블 1.3.0 가산 개정 묶음 AM-26~AM-44)을 추가하고 "다음 번호"를 0040으로 바꾼다(바이블 §3.3 1.3.0).
- [ ] `docs/06-adr/0039-bible-1-3-additive-amendment-bundle.md`를 §1.3 frontmatter·§1.4 절 구성(60~200행)으로 작성한다. 결정 = AM-26~AM-44 가산, 대안 = major 동반 개정(기각, D4-3), 게이트 근거 = 해당 없음(기본 파라미터 불변). A7 "ADR-0039 파일 없음"(L282)을 이 파일로 해소한다.
- [ ] 릴리스 버전 정책 ADR(09-operations/08·10-development/08 제안 slug)은 다음 빈 번호(0040~)로 발의한다고 적는다.
- [ ] A3 문맥 검토: L132 PyMuPDF, L133·L184 pyhwp, L178 MinIO·Redis(기각 결정 요약 문맥 명시).

### 06-adr/0002-provenance-element-path-and-nullable-page-bbox.md

- [ ] `element_path` 예시를 03-contracts/03 §3.1 권고 문법(OWPML `/hp:sec[i]/hp:p[j]`)으로 맞춘다(AM-16).
- [ ] `section_index` 의미 확장(HWPX `secPr`, OOXML `w:sectPr`)을 결과 절에 한 줄 적는다(AM-29).
- [ ] 바이블 1.3.0 §5.3 인용으로 갱신한다(patch, `accepted` 유지).

### 06-adr/0012-lite-profile-qdrant-only-client-bm25.md

- [ ] `lite`에서 `analyzer_id` 변경이 `sparse_bm25` 공간 id 변경 → Qdrant blue/green을 유발함을 결과 절에 반영한다(#61, patch).
- [ ] `lite` 컨테이너 수(4 / 5~6) 인용을 바이블 §7.1 1.3.0과 맞춘다(AM-14).
- [ ] `values = 1.0` 질의 가중을 04-pipelines/15 `tf_q`로 위임한 사실을 인용한다(#186).

### 06-adr/0020-default-chunker-structure-aware-and-dependency-locks.md

- [ ] `Chunk.text`(markdown) 직렬화와 표시 html의 역할 분담 문구를 추가한다(#104, patch).
- [ ] 기본 청커가 `requires_lineage = ("ParsedDocument",)`로 구조 필드를 읽는다는 결정(바이블 §4.1 1.3.0, AM-26)을 결과 절에 적는다.
- [ ] `Chunk.ordinal` 형제 순서 정의(AM-09)를 인용한다.

### 06-adr/0022-observability-genai-semconv-pin-and-license-boundary.md

- [ ] 바이블 §6.5 1.3.0 정본 메트릭 36종·스팬 2종 추가(라벨 규약 불변)를 결과 절에 기록한다(AM-41).
- [ ] 새 라벨(`code`, `status`, `route`, `kind`)이 필요한 4종은 라벨 허용 집합 개정(이 ADR minor) 대기임을 재검토 조건에 적는다(09-operations/03 미해결 1).
- [ ] CloudEvents `source` 컴포넌트 값 규약(AM-13)을 관측성 식별자 절에 인용한다.

### 06-adr/0026-index-commit-generation-saga-and-ledger.md

- [ ] `index_generation = max(index_commits.index_generation) + 1`, 폐기·롤백 세대 번호 비재사용을 결정 절에 반영한다(AM-18, patch).
- [ ] 재검토 조건에 O-11(프로파일 해시만 바뀐 재색인·green 물리 이름)·O-12(blue/green 채움 중 원장 포인터)를 추가한다(AM-21·AM-45).
- [ ] `last_generation` 컬럼 대안은 기각(R-01)으로 대안 절에 기록한다.

### 06-adr/0033-sidecar-convert-contract-and-isolation-ladder.md

- [x] "비재시도 `parse.*`는 폴백 없이 전파" 문구를 바이블 §4.2 실패 정책(`sidecar_unavailable` 재시도 후 폴백, `conversion_failed` 폴백 체인)과 정합시킨다(CR-45, patch). 해소(v1.3, CR-45): 배정 기준 표 `in_process` 행에 비재시도 코드는 체인을 끊고 `parse.conversion_failed`만 폴백 체인이 진행됨을 명시.
- [x] `derived` 파생물 키의 `options_hash`(바이블 §6.2 1.3.0)를 변환본 재사용 조건에 인용한다(AM-40). 해소(v1.3, AM-40): 결정 절·시퀀스 다이어그램·결과 절 세 곳의 `H("derived", …)` 식에 `options_hash` 인자 추가.
- [x] 바이블 1.3.0 인용으로 갱신한다(`accepted` 유지). 해소(v1.3): 위 두 항목 인용에 "바이블 §4.2/§6.2 1.3.0" 명시, `status: accepted` 불변.

### 06-adr/0037-artifact-cache-scope-and-stage-key-composition.md

- [x] `stage_key` 입력 해시 규약(`detect`·`parse` = 원본 `content_hash`, 그 외 `input_ref.blake3`)을 결정 절에 반영한다(AM-05, patch). 해소(v1.3, AM-05): 결정 절 일반식을 `input_hash`로 바꾸고 `detect`·`parse` = `content_hash`, 그 외 = `input_ref.blake3` qualifier와 다이어그램을 함께 갱신.
- [x] 캐시 제외 스테이지(`fetch`·`index`) 산출물 키와 점유 `stage_key` 경로 비덮어쓰기 규칙(바이블 §13.3 1.3.0)을 결과 절에 추가한다(AM-19). 해소(v1.3, AM-19): 결과·중립 절에 바이트 해시 키 경로·`derived/llm_enrich/` 경로·비덮어쓰기 규칙 불릿 추가.
- [x] `derived` 키 `options_hash`와 `llm-enrich` 키 입력(AM-12·AM-40)을 콘텐츠 전용 캐시 목록에 반영한다. 해소(v1.3, AM-12·AM-40): 결정 절 문장과 캐시 부류 표의 파생물·LLM 보강 행에 `options_hash`·`embed_text`(생성 결과 제외) 정의 반영.

### 08-evaluation/01-evaluation-strategy.md

- [ ] `EvalDataset.relevance_max`·`topics_ref`·`language`(L193·L197·L258)를 "바이블 §5.6 1.3.0 등재(AM-34)"로 표기 전환한다.
- [ ] 게이트 값 형식(`metric?` 기본 `ndcg@10`, `dataset?` 기본 `eval.datasets[0]`, `min_delta_pt`·`promote_to`·`tool`)을 바이블 §5.6으로 인용한다(CR-37).
- [ ] `EvalRun.index_commit_ids`의 "current 커밋" 정의를 03-contracts/08 §8·IC-5로 인용한다(CR-40).
- [ ] L582·L583 "(작성 예정)" 제거.

### 08-evaluation/02-retrieval-metrics-and-harness.md

- [ ] §12 "dev 마커"를 `slow` 재배정으로 정정한다(#195).
- [ ] `index_commit_ids` current 정의(CR-40)와 상한(EvalRun 64KB 안 재산정, CR-41)을 반영한다.
- [ ] `span_hit_rate@k`가 `block_refs.original_char_*`(원문 기준)와 `answer_spans`를 교차함을 바이블 §6.3으로 확인한다(CR-47).
- [ ] 메트릭 `rag_eval_last_run_timestamp_seconds{profile_id}`·`rag_eval_judge_cost_usd_total`의 정본 등재(AM-41)를 하네스 계량 절에 반영한다. `rag_eval_metric_value`에 `dataset` 라벨은 추가하지 않는다(R-07).
- [ ] `EvalDataset.relevance_max`(nDCG 선형 이득 상한)를 등재 사실로 표기한다(AM-34).

### 08-evaluation/03-golden-dataset-construction.md

- [ ] `relevance_max`·`topics_ref`·`language`(L84·L398·L523·L606)를 등재 표기로 전환한다(AM-34).
- [ ] `answer_spans` 오프셋 기준(원문 `Block.text` 코드포인트, 0-based, 끝 미포함)을 바이블 §6.3으로 확인한다(CR-47).
- [ ] 표 셀 정답 구간이 `table_cell_views`(조건 필수, AM-31)를 기준으로 할 때의 좌표 규칙을 03-contracts/04와 대조한다(L444·L446).
- [ ] L35·L790 "(작성 예정)" 제거.

### 08-evaluation/04-llm-judge-and-generation-quality.md

- [ ] judge 모델 `model_id` 표기를 API 모델 `{provider}:{model}`(`@{revision}` 선택, 없으면 `created_at` 병기)로 맞춘다(AM-11).
- [ ] `PairwiseRecord`·온라인 `judge.jsonl` 경로는 AM-56 보류(M2) — 제안 지위를 유지한다.
- [ ] 판정 스키마 `$id urn:rag:eval:judge-pack-verdict:1`(L184 등)은 등재 시 `urn:rag:schema:{kebab-name}:{major}` 규약(바이블 §6.4)을 따라야 함을 미해결 이슈에 적는다.
- [ ] 입력 `ContextItem` 필드 참조(L107·L170)를 승계 규칙과 대조한다(CR-20).

### 08-evaluation/05-benchmark-plan-and-baselines.md

- [ ] 리랭크 미적용 시 게이트 점수 기준을 확정한다(#99).
- [ ] 게이트 값 형식(CR-37)과 `index_commit_ids` current 정의(CR-40)를 인용한다.
- [ ] `embed.token_overflow` 경고 = `degraded` 봉투(AM-07)를 벤치마크 실패 분류 표(L485)에 반영한다.
- [ ] premium 예산·lite `page_route`는 AM-52 보류(측정 후 minor)이며 이 문서의 측정 계획이 재발의 근거임을 적는다.

### 08-evaluation/06-online-feedback-loop.md

- [ ] L621 "모드 B `rolling_canary`(두 해시 불변)"에 `**미정(O-11):**` 의존을 명시한다 — 재색인 모드 B가 보류(AM-45)이므로 이 경로는 O-11 해결 전까지 운영자 대안(새 컬렉션 이관)으로만 가능하다.
- [ ] `filters.effective_hash` 해석(계획 트리, `as_of` 바인드 이름)을 바이블 §6.2 1.3.0으로 인용한다(CR-17; L356·L372).
- [ ] 피드백 이벤트 `source` = `urn:rag:api`(L245)를 확인한다(AM-13).
- [ ] `rag_feedback_events_total{kind}`(L813)는 새 라벨 `kind` 대기로 미등재임을 적는다(AM-41).
- [ ] `principal_hash`·`query_hash`(바이블 §6.2 1.3.0)를 피드백 원장 상관 키로 인용한다(AM-40).

### 09-operations/01-deployment-guide.md

- [ ] `lite` 컨테이너 수를 4(개발) / 5~6(운영 `--durable`)로 바이블 §7.1 1.3.0 문구와 맞춘다(AM-14; L50·L61).
- [ ] HWP 5.0 `standard` 배포용 Tika 텍스트(테넌트 옵트인)를 파서 워커 절에 반영한다(AM-14).
- [ ] 첫 테넌트 생성 절차를 `POST /v1/tenants`(또는 같은 API를 호출하는 `rag tenant`)로 바꾼다(AM-39; L483·L580·L866). 원장 직접 삽입 경로는 부트스트랩 전용으로 한정한다.
- [ ] CLI 명령 인용(L317·L583·L865)을 "정본 10-development/02 §CLI"로 연결한다(완전성 #10).
- [ ] A3 L127·L426 문맥 검토. L37·L894 "(작성 예정)" 제거.

### 09-operations/02-configuration-reference.md

- [ ] `security.tiering` 정본 경로(바이블 §5.6·§7.3)를 확인하고 `ingest.index.tiering`은 스키마 거부로 기술한다(AM-15, CR-36; L405·L865).
- [ ] `ingest.normalize.pii.reject_entities`(L785·L991)를 "바이블 §7.3 1.3.0 등재(AM-43)"로 전환한다.
- [ ] `EgressPolicy` 선택 키 `max_bytes`·`connect_timeout_ms`·`allowed_ports`·`strip_query_keys`를 설정 표에 반영한다(AM-30; L352·L599·L600·L870).
- [ ] 게이트 값 키(`metric?`·`dataset?`·`min_delta_pt`·`promote_to`·`tool`)와 `profile.gate_pending` 경고를 검증 규칙 표에 반영한다(CR-37, AM-36).
- [ ] `PackConfig.k_max ≤ 20`·`ChannelConfig.top_k ≤ 300`을 확인한다(CR-46). `StagePolicy` 부분 선언 → 로더가 §4.4 기본값으로 완성(CR-35; L865).
- [ ] 테넌트 설정 절에 `tenants.quotas`·`TenantStatus`를 반영하고 `settings/` 모듈(pydantic-settings, 바이블 §12 1.3.0)을 환경 변수 절에 인용한다(AM-39·AM-22).
- [ ] CLI 명령 정본은 10-development/02 §CLI이며 이 문서는 인용만 한다(완전성 #10; L823).
- [ ] A3 L165 Redis 문맥 검토. 1,007행 — 900행 초과 절 이관은 P2.

### 09-operations/03-observability.md

- [ ] 미해결 2(제안 메트릭 38종)를 부분 종결한다: 34종 + 04-pipelines/03 라우터 2종은 바이블 §6.5 1.3.0 정본(AM-41), `rag_stage_errors_total`·`rag_api_problems_total`·`rag_feedback_events_total`·`rag_api_sse_connections_count` 4종은 새 라벨 대기(미해결 1과 묶어 ADR-0022 minor). §4.2 표의 "정본/제안" 열을 갱신한다.
- [ ] `/healthz` = liveness(의존성 미포함), 의존성 상태는 `/readyz`(#174).
- [ ] §8 런북 열의 "(제안) RB" 번호를 09-operations/06 번호로 바꾼다(#141).
- [ ] CloudEvents `source` 값 규약(`api`·`worker`)을 로그·스팬 상관 절에 인용한다(AM-13).
- [ ] 합성 생산자 `plugin_id`(`enricher.pipeline` 등, L87·L137·L181·L186)를 바이블 §6.1 1.3.0 예약 구현명으로 확인한다(AM-11).
- [ ] `embed.token_overflow`·`normalize.segmenter_fallback` 경고 계량(L357)이 `Warning.code` 기반임을 확인한다(CR-33).

### 09-operations/05-security-and-compliance.md

- [ ] `tenant_admin`의 `pii_officer` 자기 부여 직무 분리 통제를 수용한다(#62).
- [ ] `POST /v1/documents/{document_id}/unmask`(역할 `pii_officer`, `tokenize`·`encrypt` 모드만)를 "바이블 §14 1.3.0 등재"로 전환한다(AM-39; L280·L578·L580·L639).
- [ ] API 키 발급·폐기·회전(`/v1/api-keys*`)과 테넌트 비활성화(`TenantStatus.disabled` → `auth.forbidden` 403)를 접근 통제 절에 인용한다(AM-38·AM-39).
- [ ] `principal_hash = H("principal", tenant_id, subject)`를 감사 로그 식별자로 인용하고 `tenant_id_hash` 키 정책(09-operations/03 미해결 3)과 같은 정책임을 적는다(AM-40).
- [ ] 잠금 ACL 경고 `contract.acl_deny_all`을 ACL 운영 절에 인용한다(AM-17).
- [ ] A3 문맥 검토: L684 PyMuPDF·pyhwp, L462 pyhwp·Redis.

### 09-operations/06-runbooks.md

- [ ] RB-16을 색인에 등재하고 버킷 손실 전용 런북 여부를 판단한다(#59). 09-operations/07 §4.1 참조를 동기화한다(#60).
- [ ] 취소 경합 런북(L591~L601)을 AM-46 잠정 규칙(플립 시작 후 취소 → `running → succeeded`)으로 맞춘다(CR-29).
- [ ] 정합성 검사 수동 실행을 `POST /v1/collections/{collection_id}/consistency-check`로 기술한다(AM-39).
- [ ] 컬렉션 삭제 런북을 `collection.delete.v1`(논리 삭제 → 문서 팬아웃)로 기술한다(AM-37).
- [ ] 삭제 tombstone 커밋(L649)을 확인한다(CR-30). `/healthz`·`/readyz` 구분을 점검 절차에 반영한다(#174).

### 09-operations/07-backup-and-disaster-recovery.md

- [ ] 미해결 3의 `NFR-REL-17` 신설 제안(L605)을 "요구사항 없음, 운영 목표(제안)"로 고쳐 쓰고 요구사항 신설은 요구사항 소유자 백로그로 넘긴다(완전성 #9 (b), A7).
- [ ] §3.1 리전 손실 RPO/RTO 표를 "운영 목표(제안)" 표기로 바꾼다.
- [ ] 복구 시 캐시 제외 스테이지 산출물·LLM 보강 캐시 키(바이블 §13.3 1.3.0)를 백업 대상 표에 반영한다(AM-19).
- [ ] 컬렉션 삭제(`collections.deleted_at` 논리 삭제) 후 복구 가능 창을 기술한다(AM-37; L248).
- [ ] 09-operations/06 RB-16과 §4.1 참조를 동기화한다(#60).

### 09-operations/08-upgrade-and-migration.md

- [ ] `**제안:**` 표기를 유지하고 릴리스 ADR은 0040 이후 번호의 백로그로 등록한다(#4; ADR-0039는 1.3.0 가산 묶음이 사용, 바이블 §3.3).
- [ ] 미해결 1의 slug 제안 `0039-platform-release-versioning-and-support-policy`를 번호 미정(0040~)으로 고친다.
- [ ] 미해결 4(이름 불변 백엔드 전환)를 `**미정(O-11):**` 의존으로 표기한다(AM-21·AM-45; L647).
- [ ] 계약 `schema_version` 1.0.0 유지(M1 이전 개정)와 `SchemaDiffReport` 인벤토리 등재를 마이그레이션 게이트 절에 인용한다(AM-01, 트리아지 §1.2).
- [ ] 원장 마이그레이션 목록에 1.3.0 컬럼(`tenants.status·quotas·disabled_at`, `collections.deleted_at`, `idempotency_keys.job_ids`)을 추가한다(AM-37·AM-39·AM-44).

### 10-development/01-repository-structure.md

- [ ] 루트 개발 파일(`justfile`, `.pre-commit-config.yaml`)과 `deploy/compose/compose.{lite,lite-durable,observability}.yaml`을 바이블 §12 1.3.0과 맞춘다(AM-22).
- [ ] `src/rag_platform/settings/`(pydantic-settings, `security`·`profiles`와 같은 층; L168·L642)를 트리와 import-linter 계층에 반영한다(AM-22).
- [ ] `adapters/parse/router.py`·`hwpx_hwpxlib_sidecar.py`, `sdk`의 `DerivedArtifacts`를 트리에 추가한다(AM-22·AM-27).
- [ ] `api/` 모듈 목록에 `api_keys`·`plugins`·`schemas`·`version`·`audit_events`(API 전용 뷰 DTO 단일 출처)를 추가한다(AM-02·AM-39).
- [ ] A3 문맥 검토: L39·L44·L631·L671 pyhwp(별도 저장소 문맥 명시).

### 10-development/02-development-environment.md

- [ ] **§CLI 절을 신설한다(완전성 #10, 바이블 §12 1.3.0 `cli/` 주석).** 바이블 §12 명령(`up ingest query reprocess reindex eval profile(validate diff) plugin(list --check-license) cache(invalidate --stage) serve(api worker relay sidecar) mcp`) + `rag tenant`(관리 API 래퍼, AM-39) + 개발 전용 `rag run-stage`(04-pipelines/01 §13) + diff 리포트 명령(04-pipelines/09 §8.5)을 명령·인자·호출 API·소유 문서 표로 모은다.
- [ ] 이 문서가 CLI 정본임을 범위 절과 결정 요약에 적고, 다른 문서는 인용만 한다고 명시한다.
- [ ] `justfile`(제안)을 루트 개발 파일로 바이블 §12 1.3.0에 등재된 사실로 전환한다(AM-22).
- [ ] 개발 스택 `lite` 컨테이너 수(L223)를 4(개발)로 확인한다(AM-14).
- [ ] A3 문맥 검토: L61·L675 pyhwp. L674 "(작성 예정)" 제거. 분량(676행 + §CLI)이 900행을 넘지 않게 유지한다.

### 10-development/03-coding-standards.md

- [ ] 모호한 `01 §x` 인용을 전체 경로로 바꾼다(#10).
- [ ] §13 테스트 마커 목록을 04-testing-strategy §21 인용으로 바꾼다(#187).
- [ ] §14·§15를 07-contributing 정본 인용으로 바꾼다(#194).
- [ ] `canonical_json` 규칙(L322·L363·L373·L601)을 RFC 8785(JCS) 수치 직렬화·선택 필드 제거 후 해시로 갱신한다(바이블 §6.2 1.3.0, AM-12).
- [ ] `StageContext` 사용 규칙에 `ctx.plan`·`ctx.artifacts`를 추가하고 "스테이지는 I/O 직접 금지"와의 관계를 적는다(AM-27).
- [ ] A3 L630·L633 문맥 검토.

### 10-development/04-testing-strategy.md

- [ ] 적합성 키트에 `requires_lineage` 결정성 테스트(`chunk`의 `ParsedDocument` 로드가 `stage_key`를 바꾸지 않음, 입력 `lineage_refs` 밖 선언 거부)를 추가한다(AM-26).
- [ ] `canonical_json` 골든 벡터에 JCS 수치(`1.0` → `1`)와 선택 필드 제거 케이스를 추가한다(AM-12; L79·L99·L117·L149).
- [ ] 열거 대조 테스트 대상에 `TenantStatus`·`CompatLevel`·`SchemaChangeKind`·`JobKind.delete_collection`을 추가한다(바이블 §5.7 1.3.0).
- [ ] `retrieve.security_context_missing` = 500 계약 테스트 기대값(L391)을 갱신한다(AM-25).

### 10-development/05-ci-cd.md

- [ ] 미해결 16(`rag_eval_metric_value` `dataset` 라벨)을 "종결: R-07 — `EvalRun` 원장 분해로 대체"로 닫는다.
- [ ] 봇 PR 자동 머지 vs "팀 1인" 규칙, `Breaking-Kind`·`Cache-Invalidation` 트레일러 템플릿을 07-contributing과 합의한다(#94).
- [ ] 스키마 diff 게이트가 `SchemaDiffReport`(바이블 §5.1 인벤토리 35종, AM-01)를 산출하고 `declared_level ≥ computed_level`을 판정함을 인용한다.
- [ ] 열거 대조 CI 대상에 1.3.0 열거·이벤트·오류 코드 84종을 반영한다.

### 10-development/06-plugin-development-guide.md

- [ ] `StageContext`의 `plan`·`artifacts`(파생물 쓰기 포트)를 SDK 사용법 절에 추가한다(AM-27; L150·L152·L211·L454).
- [ ] `requires_lineage` 선언 규칙(입력 `lineage_refs`로 고정되는 상류만, `chunk` 예)을 갱신한다(AM-26; L147).
- [ ] 합성 생산자 `{extension_point}.pipeline` 예약 구현명과 API 모델 `model_id` 표기(`{provider}:{model}`)를 명명 절에 추가한다(AM-11).
- [ ] `parser_fingerprint.parser_version`(`{package}=={version}`, 복수 `;`)·`profile_option` 형식을 파서 플러그인 절에 반영한다(AM-09; L190·L248·L249).
- [ ] `contracts_compat` 문법을 03-contracts/14 §4.3으로 인용한다(CR-38). `RankedResult` 선택 필드(L481)를 확인한다(AM-33).
- [ ] `retrieve.security_context_missing` 예외(L424·L462)를 500 카탈로그 코드로 맞춘다(AM-25).

### 10-development/07-contributing.md

- [ ] ADR 번호 절차: 다음 번호를 0040으로 바꾼다(L245·L677; ADR-0039는 1.3.0 가산 묶음).
- [ ] 미해결 9(ADR 행 추가의 변경 등급)를 "바이블 §1.2 patch(ADR 목록 행 추가는 표 보강)로 처리"로 결론낸다. 바이블 §1.2 1.3.0 표(필수 → 선택화 = minor 조건부)도 인용한다(AM-23).
- [ ] `Breaking-Kind`·`Cache-Invalidation` 트레일러 템플릿을 05-ci-cd와 합의한다(#94).
- [ ] A3 문맥 검토: L640 PyMuPDF·pyhwp, L722 pyhwp.

### 10-development/08-release-process.md

- [ ] §5.4에 핫픽스 PR 행 추가를 검토한다(#95).
- [ ] 미해결 1의 ADR slug 제안 번호를 0040~로 고친다(ADR-0039 사용됨, 바이블 §3.3).
- [ ] 릴리스 게이트의 `SchemaDiffReport` 인용을 인벤토리 등재 사실(AM-01)로 갱신하고 계약 `schema_version` 1.0.0 유지(M1 이전) 규칙을 인용한다.

### 11-roadmap/01-milestones.md

- [ ] T-MGT-30/T-CHK-23 의존 인용 문장을 확인한다(#23).
- [ ] M1 정의에 필수 개정 AM-26(`chunk` `requires_lineage`)·AM-27(`StageContext.plan`·`artifacts`)이 1.3.0에 반영되었음을 적는다(트리아지 §5.1).
- [ ] 관리 API 마일스톤 항목에 `/v1/tenants`·API 키·감사 이벤트(AM-39)와 컬렉션 삭제(AM-37)를 반영한다(L369·L433).
- [ ] 미해결 17 "신규 ADR(0039~)"을 "0040~"로 고친다(ADR-0039 사용됨).
- [ ] L191 바이블 버전 인용을 1.3.0으로 갱신하고 A3 L648·L695 pyhwp 문맥을 검토한다.

### 11-roadmap/02-epics-and-backlog.md

- [ ] T-PLG-01 "공용 타입 24종"(L106·L695)을 1.3.0 승격 11종 포함 개수로 갱신한다(AM-35).
- [ ] 관리 API 에픽에 `/v1/tenants`·`/v1/api-keys*`·`/v1/plugins*`·`GET /v1/schemas`·`/v1/version`·`consistency-check`·`/v1/audit-events`·`POST /v1/profiles`·unmask 태스크를 추가하거나 기존 태스크에 매핑한다(AM-39).
- [ ] 계약 태스크에 1.3.0 가산 필드(AM-28~AM-34)·열거(AM-36~AM-38)·common-types 승격(AM-35) 반영 작업을 T3 산출물 기준으로 연결한다.
- [ ] CLI 태스크의 정본 참조를 10-development/02 §CLI로 바꾼다(완전성 #10).
- [ ] T-EVL-19 "신규 ADR 0039~"(L466·L980)를 "0040~"로 고친다. A3 L996 pyhwp 문맥 검토.

### 11-roadmap/03-risks-and-mitigations.md

- [ ] 재색인·마이그레이션 리스크(R-O-11 등)의 완화 열에 O-11·O-12 보류(AM-45)와 잠정 규칙을 인용한다. 리스크 ID `R-O-11`과 개방 결정 `O-11`이 혼동되지 않게 "개방 결정 O-11"로 풀어 쓴다.
- [ ] A3 `likely_ok=false` 행 문맥 검토: L113 PyMuPDF·pyhwp·Redis, L98·L440 pyhwp, L105 Infinity, L114 SPLADE-v3.
- [ ] 라이선스 리스크 행에서 기각 기술 목록을 바이블 §15 리스크 #2 문구와 맞춘다.

### 12-appendix/06-traceability-matrix.md

- [ ] A1 깨진 링크(L383 `./01-functional-requirements.md`)를 생성기 `tools/traceability.mjs`에서 `../01-requirements/01-functional-requirements.md`로 고쳐 재생성한다(기계 생성 문서이므로 수동 편집 금지).
- [ ] A7 `NFR-REL-17`(L30) 인용을 요구사항 미정의로 표시하거나 제외한다(완전성 #9 (b)).
- [ ] FR-MGT-01 행의 설계 충족 열에 바이블 §14 1.3.0(`/v1/tenants`)을 반영한다(AM-39).

## 결정 사항 요약

- **결정:** 바이블 1.3.0·브리프 v1.2.2 개정의 하류 전파는 이 문서 2절의 문서별 체크리스트가 단일 입력이다. 공통 지시 6항(1절)은 모든 문서에 암묵으로 적용된다.
- **결정:** 03-contracts의 스키마·Pydantic 블록 변경은 `[T3]` 표시 항목으로만 두고 T3가 수행한다. 문서 쪽 서술은 T3 반영과 같은 PR에서 맞춘다. `JobKind.delete_collection`이 common-types에 반영되기 전까지 validate-contracts는 ERROR 1건(바이블 §5.7 ↔ `JobKind`)을 낸다.
- **결정:** CLI 명령 정본은 10-development/02 §CLI(신설)이고, 다른 문서는 인용만 한다(완전성 #10).
- **결정:** 개방 결정 번호 O-11·O-12를 "O-xx 미배정" 표기 자리에 쓴다(02-architecture/03, 04-pipelines/13·19, 08-evaluation/06, 09-operations/08).
- **결정:** 릴리스 버전 정책 ADR은 0040 이후 번호로 발의한다(ADR-0039는 1.3.0 가산 묶음).

## 미해결 이슈

1. `api.quota_exceeded`의 HTTP 상태(403 vs 429)는 02-architecture/07 §10과 05-api/01 §9가 같은 PR에서 확정해야 한다(트리아지 미해결 4). 확정 전 두 문서는 초안(문서 수·저장 용량 403, QPS 429)을 쓴다.
2. `JobStatus.idempotency_key`(Y)와 배치 자식 잡 NULL 허용(AM-44)이 충돌하면 03-contracts/12가 nullable로 바꿔야 하며, 이는 바이블 §1.2 1.3.0의 "필수 → 선택화 = minor(조건부)"에 해당한다. T3가 판정해 바이블 §5.6 `JobStatus` 행 patch를 요청한다.
3. 2절의 행 번호는 감사 시점 기준이다. P1이 앞 절을 편집하면 뒤 행 번호가 밀리므로 토큰·문구로 찾아야 한다.
4. P1 완료 후 `tools/audit-docs.mjs` 재실행(A1·A3·A7) 결과로 이 문서의 체크 상태를 대조하는 5단계 검증이 필요하다.

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) v1.2.2 §4·§5·§8
- [설계 바이블](../02-architecture/00-design-bible.md) 1.3.0 — `## 결정 사항 요약`의 v1.3.0 변경 목록
- [바이블 개정 요청 트리아지 결정](07-bible-amendment-triage-decisions.md) §2·§4·§5·§6
- [바이블 개정 요청 트리아지 입력](03-bible-amendment-triage-input.md) §3(계약 감사 정본 결정 47건)
- [3단계 완전성 검토](01-phase3-completeness-review.md) §3
- [4·5단계 계획](02-phase4-5-plan.md) §2.3(D4-1~D4-4)
- 기계 감사: `tools/phase4/results/audit-pre.md`(A1·A2·A3·A7)
