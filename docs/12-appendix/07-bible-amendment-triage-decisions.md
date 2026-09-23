---
title: 바이블 개정 요청 트리아지 결정
status: active
owner: architecture
version: 1.0.0
last_updated: 2026-09-23
depends_on: ["02-phase4-5-plan.md", "03-bible-amendment-triage-input.md", "01-phase3-completeness-review.md", "../00-vision/00-design-brief.md", "../02-architecture/00-design-bible.md"]
---

# 바이블 개정 요청 트리아지 결정

## 목적

3단계 문서들이 남긴 바이블 개정 요청 후보 200건(`12-appendix/03-bible-amendment-triage-input.md` §2), 계약 감사 정본 결정 47건(같은 문서 §3), [3단계 완전성 검토](01-phase3-completeness-review.md)의 누락 12건·인계 13건을 4단계 T1(트리아지)으로 판정한다. 판정 결과는 개정 항목(AM-nn)으로 묶어 T2(바이블·브리프 개정)와 P1(문서 전파)의 단일 입력이 된다. 이 문서는 바이블·브리프·계약·스키마를 **수정하지 않는다**.

## 범위

- 포함: 요청 200행 전부의 판정(채택 patch/minor/major, 보류, 기각, 문서 내부), 같은 취지 요청의 병합, 바이블 목표 버전, 계약 영향, 완전성 검토 #1~#12 판정, 계약 감사 정본 결정 47건의 전파 대상 지정.
- 제외: 바이블 본문 작성(T2), 스키마 수정(T3), 문서 편집(P1·P2), ADR-0039 이후 ADR 작성(목록만), 입력 목록 §4 "문서 내부·기타 미해결 이슈" 280건(각 문서 소유자가 P1에서 처리).
- 전제(4·5단계 계획 `12-appendix/02-phase4-5-plan.md` §2.3 제안값 채택): **D4-1** 용어집 미해결 이슈 `GL-xx`·링크 키 `[PL-xx]` 접두 전환 완료, **D4-2** 900행 초과 비계약 문서는 절 이관, **D4-3** 바이블 목표 1.3.0(minor)·major 유발 요청은 보류, **D4-4** 경량 모드 수정분 20% 표본 검증.
- 판정 기준: 바이블 §1.2 변경 절차 표. 우선순위는 브리프 > 바이블 > ADR > 개별 문서(바이블 §1.1).

입력 목록의 "바이블 절" 열은 정규식이 요청 문장에서 뽑은 첫 절 번호라서 대부분 **출처 문서 자신의 절**이다(예: `08-release-process`의 "§5.4"는 그 문서 §5.4). 따라서 절 표기가 아니라 요청 내용으로 판정했고, 그 결과 200행 중 111행은 바이블 개정이 아닌 문서 내부 사안으로 분류됐다.

## 1. 집계

### 1.1 요청 행 단위(200행, §3)

| 판정 | 행 수 | 설명 |
|------|------:|------|
| 채택(patch) | 31 | 오탈자·설명 보강·예시·누락 행 |
| 채택(minor) | 34 | 선택 필드·열거값·이벤트·JobKind·§14 엔드포인트·해시 키 보강 |
| 채택(major) | 0 | M1 필수 major 없음(§5.1 참고) |
| 보류(ADR-0039+ 또는 근거 대기) | 14 | 의미 변경·개명·제약 강화·게이트 근거 부재 |
| 기각 | 10 | 바이블 정본을 오독했거나 대체 경로가 이미 있음 |
| 문서 내부(전파 지시) | 111 | 바이블 무관: 문서 간 정합·관찰 메모·분량·링크(§6) |
| **합계** | **200** | |

### 1.2 개정 항목 단위(§2)

| 판정 | 항목 수 | 항목 |
|------|--------:|------|
| 채택(patch) | 25 | AM-01~AM-25 |
| 채택(minor) | 19 | AM-26~AM-44 |
| 채택(major) | 0 | — |
| 보류 | 12 | AM-45~AM-56 |
| 기각 | 10 | R-01~R-10(§2.4) |

**결정:** minor 채택이 19건이므로 바이블 목표 버전은 **1.3.0**, 브리프는 §8 문서 맵 patch로 **v1.2.2**다. major 채택은 없으므로 2.0.0 개정과 영향 문서 일괄 개정은 발생하지 않는다(D4-3).

**결정:** 계약·스키마에 영향이 있다(contracts_affected). AM-26·28·29·30·31·32·33·34·35·36·37·38·43이 `schemas/common-types.schema.json`(`$defs`: `ErrorCodeCatalog`·`EventType`·`JobKind`·`TenantStatus`·공용 타입 승격·`RankedResult`·`StageError`·`ProblemDetails`)과 개별 계약 스키마(`normalized-document`·`enriched-chunk-set`·`eval-dataset`·`profile`·`egress-policy`)에 가산 변경을 일으킨다. 모두 선택(N) 필드·열거값 추가이며 필드 제거·필수화·개명은 없다. 03-contracts·`schemas/`에 대한 반영은 T3가 하고 `tools/validate-contracts.mjs` ERROR 0을 게이트로 한다.

**결정:** 계약 `schema_version`은 **1.0.0을 유지**한다. 계약 `schema_version`은 M1부터 1.0.0으로 시작하므로(11-roadmap/01 릴리스 태그 규칙) 아직 생산 인스턴스가 없고, 이번 가산 변경은 1.0.0 확정 전 개정으로 각 계약 문서 `## 버전 이력`에 기록한다. 바이블 §5.1 `schema_version` 열도 1.0.0으로 둔다.

## 2. 개정 항목

### 2.1 채택(patch) — 바이블·브리프 소유자 직접 수정

| 항목 | 판정 | 바이블 절 | 변경 요지 | 병합한 요청 # | 영향 문서 |
|------|------|-----------|-----------|---------------|-----------|
| AM-01 | 채택(patch) | §5.1 | 인벤토리 35번째 행 `SchemaDiffReport`(`schema-diff-report.schema.json`, `$id urn:rag:schema:schema-diff-report:1`, 생산 CI 스키마 diff 도구, 소비 릴리스 게이트·관리 API, 소유 03-contracts/14) 추가. `Capabilities` 행 스키마 파일 열에 "`capabilities.schema.json`은 common-types 순수 래퍼(별칭 없음)" 주석 | 175; 완전성 #8 | 03-contracts/14·15, 05-api/04, 10-development/05·06·08, `schemas/README.md`(5단계) |
| AM-02 | 채택(patch) | §5.1 | 표 아래 각주: 관리 API 응답 객체(`TenantPolicies`, `TenantUsage`, `CollectionCreateRequest`, `ReindexEstimate`, `CollectionStatsView`, `DictionaryReplaceResult`, `ProfileSummary`, `ProfileValidationResult`, `PluginCapabilitiesView`, `PluginHealth`, `SchemaDescriptor`, `ApiKey`, `VersionInfo`, `CapacityView`, `Document` 등)는 **API 전용 뷰**다. 계약 인벤토리·`schemas/`·`GET /v1/schemas` 게시 대상이 아니며, 단일 출처는 `src/rag_platform/api/`의 Pydantic 모델이고 계약 타입을 담을 때는 `schemas/`를 `$ref`로 재사용한다(FR-API-04 동일 출처 충족) | 완전성 #5 | 05-api/01 §8, 05-api/04, 03-contracts/00, `05-api/openapi.yaml` |
| AM-03 | 채택(patch) | 브리프 §8, 바이블 `## 참조`·`## 미해결 이슈` | 브리프 §8 문서 맵 v1.2.2: `07-tech-landscape/` "00~14"(13 한국어 NLP, 14 고급 RAG 등재), `12-appendix/`에 02 계획·03 트리아지 입력·04 문서 원장·05 6단계 구현 키트 계획·06 추적 매트릭스·07 본 문서 등재, 개정 이력 1행. 바이블 `## 참조`의 브리프 버전 표기(v1.1.0) 현행화, 바이블 미해결 11(하위 문서 미작성)은 3단계 완료로 종결 | 완전성 #7·#4 | `docs/README.md`(5단계), 전 문서(링크 검사 A1) |
| AM-04 | 채택(patch) | §2.2 | C4 다이어그램에 `Rel(api, s3, "산출물 읽기(GET …/content, 평가 셋)")` 추가 | 8 | 02-architecture/01·08 |
| AM-05 | 채택(patch) | §4.1 | `stage_key` 일반식의 입력 해시 표기 정합: "입력 해시 = `detect`·`parse`는 원본 `content_hash`, 그 외 `input_ref.blake3`", §4.2 `recount` 행은 `fingerprint`(tokenizer_id 포함)로 표기. `embed`의 Producer 지문이 `embedding_space_id`를 담는 위치(`config_hash`의 공간 설정)와 `embedder_fingerprint`(§6.2)가 별개 키임을 명시 | 53, 61 | 04-pipelines/01 §7.1, 03-contracts/07, ADR-0037 |
| AM-06 | 채택(patch) | §4.2 `detect` 행, §5.4 `SourceDocument` | fetch 출력 잠정값 규약: `format = unknown`(또는 힌트), `format_confidence = 0.0`, `media_type` 잠정값, `container_flags` 자리표 `{false, false, false}`는 **미판정**이며 판정 사실은 detect 출력만 가진다. `container_flags`는 Y 유지 | 39, 92 | 03-contracts/02, 04-pipelines/02·03 |
| AM-07 | 채택(patch) | §4.2 `embed` 행, §4.4 | `embed.token_overflow` 절단 시 "truncate + 경고 + 봉투 `quality=degraded`"(§4.1 부분 성공 규약의 적용). §4.4 `parse(텍스트)` 행 `resumable` 비고 "후보 어댑터 `Capabilities`로 결정(흐름 포맷 TXT·MD·HTML·HWPX는 no)" | 61, 73, 81 | 03-contracts/07 V-5, 04-pipelines/03·08·12·15 |
| AM-08 | 채택(patch) | §4.3 `hydrate` 행, §8.1 9단계 | `with_payload` 목록을 §5.5 `RankedSet` 조건 필수 18필드와 일치(`heading_path`, `numbering_path`, `page_start`, `page_end` 추가) | CR-19 | 04-pipelines/15·17, 03-contracts/10 |
| AM-09 | 채택(patch) | §5.4 `Chunk`·`ParsedDocument` | `Chunk.ordinal` 의미를 "같은 부모(`parent_chunk_id`; 없으면 문서) 아래 형제 순서(0-based)"로. `parser_fingerprint.parser_version` = `{package}=={version}`, 복수 패키지는 패키지명 오름차순 `;` 연결. `profile_option` 형식 `{format}_{variant}`(snake_case), 값 목록 정본은 04-pipelines/03 | 11, 96, 197 | 03-contracts/03·05, 04-pipelines/03·05·06·10 |
| AM-10 | 채택(patch) | §5.7 서두 | 인라인 열거 `{Type}.{path}`의 등재 파일을 **`common-types.schema.json` `$defs`** 로 명시(§12 `enums.py` 단일 소스와 일치). 정본 결정 CR-08의 "파일 미지정" 해석은 CR-25로 대체 | CR-08, CR-25 | 03-contracts/00 §2, 03-contracts/01~16 로컬 인라인 열거(T3 이동) |
| AM-11 | 채택(patch) | §6.1 | `plugin_id` 행: 여러 플러그인을 합성한 생산자는 예약 구현명 `{extension_point}.pipeline`(`enricher.pipeline`, `query_transformer.pipeline`, `retriever.pipeline`), 예시에 `packer.default` 추가. `model_id` 행: API 모델은 `{provider}:{model}`, `@{revision}`은 선택(공급자 날짜 스냅샷이 있으면 그 값, 없으면 Models API `created_at`을 `producer`에 병기) | 30, 82, 109, 110, 131 | 03-contracts/06·09·10, 04-pipelines/11·14, 08-evaluation/04, 11-roadmap/02 |
| AM-12 | 채택(patch) | §6.2 | 정밀화 5건: (a) `canonical_json` 수치는 RFC 8785(JCS) 직렬화(정수값 실수 `1.0` → `1`); (b) `acl_hash`·`metadata_hash` 입력은 값 없는 선택 필드를 제거한 뒤 `canonical_json`(03-contracts/02 §3); (c) `filters.effective_hash`의 `as_of` 바인드 직렬화는 03-contracts/09 잠정 해석 채택; (d) `dictionary_hash` 정규화 행 정의는 03-contracts/16 §6.2 참조; (e) `llm-enrich` 키의 `embed_text` = `generated` 미포함 조립 결과, 문서·섹션 요약은 섹션 텍스트 해시 | 171, 176; CR-13, CR-17, CR-44 | 03-contracts/02·09·11·16, 03-contracts/06 §10, 04-pipelines/11 |
| AM-13 | 채택(patch) | §6.5 | CloudEvents `source` 컴포넌트 값 = §2.3 컨테이너 이름, 도메인 이벤트 생산자는 `urn:rag:api`·`urn:rag:worker` 둘(`eval`은 worker) | 125; CR-42 | 03-contracts/12 §5·14 예시 4, common-types `source` 패턴 |
| AM-14 | 채택(patch) | §7.1 | `lite` 열 머리 "컨테이너 5" 내역 명시(02-architecture/08 미해결 14 값). HWP 5.0 행 `standard` 열에 "배포용: 테넌트 옵트인 시 Tika `HwpV5Parser` 텍스트(degraded)"(O-07·ADR-0007과 일치) | 39, 130 | 02-architecture/08, 09-operations/01, 03-contracts/02 §8 |
| AM-15 | 채택(patch) | §7.3 | YAML `ingest.index.tiering` → `security.tiering`(§5.6 `Profile` 표가 정본) | CR-36 | 03-contracts/15, 09-operations/02 |
| AM-16 | 채택(patch) | §9.5 | 예시 `tokenizer.name`을 `tokenizer_id` 형식(`"anthropic:<target-model-id>"`)으로, `element_path` 예시를 03-contracts/03 §3.1 권고 문법으로 정정 | 86, 100; CR-24 | 03-contracts/09·11, ADR-0002 |
| AM-17 | 채택(patch) | §10.1 | ACL 의미 보강: `visibility=restricted` + 빈 `allow_principals` = 잠금(누구에게도 보이지 않음). `deny_principals ∋ tenant:*`도 같은 결과이며 거부 대신 경고(AM-36 `contract.acl_deny_all`) | 173 | 03-contracts/00 §4.4·01 IR-5, 02-architecture/07 |
| AM-18 | 채택(patch) | §11.4 원칙 (6) | `index_generation` 할당 원천 = `documents` 행 잠금 아래 `max(index_commits.index_generation) + 1`, 폐기·롤백 세대 번호는 재사용하지 않음 | 179; CR-31 | 03-contracts/08, 02-architecture/06 §2.5 |
| AM-19 | 채택(patch) | §13.3 | 행 추가: 캐시 제외 스테이지(`fetch`·`index`) 산출물 `tenants/{tenant_id}/artifacts/{schema_type_kebab}/{blake3[:2]}/{blake3}.json`; LLM 보강 캐시 `derived/llm_enrich/{key[:2]}/{key}.json`. 규칙: 점유된 `stage_key` 경로는 덮어쓰지 않는다(정규화 동치면 기존 참조 반환, 다르면 바이트 해시 키에 저장) | 111, 171 | 04-pipelines/01·02·13, 02-architecture/04, 03-contracts/06 |
| AM-20 | 채택(patch) | §14 `GET /v1/jobs/{job_id}/events` | 목적 열 "SSE(`job.state.changed`, 스테이지 경계 진행률; 세부 진행률은 `GET /v1/jobs/{job_id}` 폴링)" | 107 | 03-contracts/12 I-20, 05-api/02 |
| AM-21 | 채택(patch) | §3.2(+ 브리프 §5 비고) | 개방 결정 번호 배정: **O-11** 두 물리 해시가 불변인 컬렉션 프로파일 변경(`profile_hash`만 변경)의 green 물리 이름·재색인 모드 B, **O-12** blue/green 채움 중 `documents` 원장·정합성 검사 기준(모드 A 원장 포인터). 상태 `open`, 해결은 ADR-0039+(AM-45) | 40 | 02-architecture/03·06, 04-pipelines/13·19, 03-contracts/08 |
| AM-22 | 채택(patch) | §12 | 모듈 맵 누락 행: `adapters/parse/router.py`(`ParseRouterStage`), `adapters/parse/hwpx_hwpxlib_sidecar.py`, 최상위 `settings/`(pydantic-settings, `security`·`profiles`와 같은 층), 루트 개발 파일(`justfile`, `.pre-commit-config.yaml`, `compose` 오버레이). `cli/` 주석에 "명령 정본: 10-development/02 §CLI"(완전성 #10 결정) | 86, 180, 182, 184; 완전성 #10 | 02-architecture/02, 04-pipelines/01·03·04, 10-development/01·02 |
| AM-23 | 채택(patch) | §1.2 | 변경 절차 표 보강: 산출물·응답 계약의 필수 → 선택화·제약 완화 = minor(조건부: 소비자 minor ≥ 생산자 minor, 03-contracts/14 §2.1), 제약 강화 = major | 67 | 03-contracts/14 §2.1·§3.1 |
| AM-24 | 채택(patch) | §11.4 | mermaid `Note` 텍스트의 `;`를 제거(렌더러가 문장 구분자로 해석) | 12, 185 | — |
| AM-25 | 채택(patch) | §5.7 카탈로그, §10.3 E7 | `retrieve.security_context_missing` = HTTP 500(서버 측 계약 위반, 미분류 500이 아니라 카탈로그 코드로 실패). 클라이언트 원인은 `plan.security_context_missing`(400)이 먼저 차단 | 200 | 03-contracts/13 E7·이슈 5, 05-api/03 |

### 2.2 채택(minor) — ADR 없이 T2가 바이블 표 갱신(가산만)

바이블 §1.2는 minor에 "ADR 발의 → 게이트 근거"를 요구한다. 아래 항목은 필드·열거·엔드포인트 가산이며 기본 파라미터 값을 바꾸지 않으므로 게이트 근거(§7.4)는 해당 없음으로 판정했다. ADR 기록은 T2가 다음 빈 ADR 번호 한 건("바이블 1.3.0 가산 개정 묶음")으로 발의한다.

| 항목 | 판정 | 바이블 절 | 변경 요지 | 병합한 요청 # | 영향 문서 |
|------|------|-----------|-----------|---------------|-----------|
| AM-26 | 채택(minor) | §4.1 `경계 페이로드`, §4.2 `chunk`·`enrich` 행 | `requires_lineage` 사용 범위 확대: 선언 가능한 것은 입력 산출물의 `lineage_refs`로 고정되는 상류 산출물뿐(결정성 보장). `index`(기존) + `chunk`: `ParsedDocument`(구조 필드 `Block.type`·`numbering_label`·`provenance`·`TableData`·`caption_of`) + `enrich` LLM 서브스텝: `ChunkSet`. 경계 페이로드는 여전히 `ArtifactRef` 1개, `stage_key` 불변. **M1 필수**(기본 청커 `structure_aware`가 구조 필드를 요구) | 57, 63; CR-04 | 03-contracts/00 §3.2·04·05, 04-pipelines/01·10·11, 02-architecture/02·05 |
| AM-27 | 채택(minor) | §4.1 `스테이지 시그니처` | `StageContext` 선택 멤버: `plan: QueryPlan \| None`(질의 측 스테이지), `artifacts: DerivedArtifacts`(파생물 쓰기 포트; 스테이지는 여전히 I/O 직접 사용 금지) | 54, 58 | 02-architecture/02·05, 04-pipelines/01·14~17 |
| AM-28 | 채택(minor) | §5.3 `StageError`·`ProblemDetails` | 선택(N) 필드 등재: `message`, `occurred_at`, `attempt`, `location`(`ErrorLocation{page, block_id, chunk_id, pointer}`), `cause`, `retry_after`, `request_id`. `ProblemDetails.instance` 타입 `string(uri-reference)`(RFC 9457 §3.1.5) | 78, 84, 199; CR-34 | 03-contracts/00 U-12·13, common-types |
| AM-29 | 채택(minor) | §5.3 `Provenance`·`BlockRef` | `section_index` 의미 "구역 인덱스: HWPX `secPr`, OOXML `w:sectPr`"(선택 필드 값 영역 확장) | 43 | 03-contracts/03, 04-pipelines/06 |
| AM-30 | 채택(minor) | §5.3 `EgressPolicy` | 선택 필드 `max_bytes`, `connect_timeout_ms`, `allowed_ports`, `strip_query_keys`(03-contracts/15 §8 정의 그대로) | 39, 139 | 03-contracts/02·15, 04-pipelines/02, 05-api/04 |
| AM-31 | 채택(minor) | §5.4 `NormalizedDocument` | 03-contracts/04 1.0.0이 이미 정의한 필드 등재: `table_cell_views`(조건: `type=table` 블록이 있고 `pii_report.policy_applied ≠ keep`), `genre_source`(N), `pii_report.tokenize_mode_applied`(N), `stats`(N), `pii_spans[].row/col`(N) | 25 | 03-contracts/04·05, 04-pipelines/09·10 |
| AM-32 | 채택(minor) | §5.4 `EnrichedChunkSet.budget_used` | 선택 키 `charged_tokens`(예산 대조 기준) | 136 | 03-contracts/06, 04-pipelines/11 |
| AM-33 | 채택(minor) | §5.5 `RankedResult` | 선택 필드(hydrate 시 채움): `token_count_primary`, `ordinal`, `text_truncated`, `pii_policy_applied`(팩의 PII 원천은 `IndexRecord` payload 경로로 확정) | 22, 50, 108 | 03-contracts/10·11, 04-pipelines/15·17, common-types |
| AM-34 | 채택(minor) | §5.6 `EvalDataset`·게이트 값·`Profile` | `EvalDataset` 선택 필드 `relevance_max`, `topics_ref`, `language`. 게이트 값 선택 키 `metric?`(기본 `ndcg@10`)·`dataset?`(기본 `eval.datasets[0]`)·`min_delta_pt`·`promote_to`·`tool`. `Profile.profile_hash`(readOnly, N) | 102; CR-37; 완전성 #12 | 03-contracts/15·16, 05-api/04, 08-evaluation/03 |
| AM-35 | 채택(minor) | §5.1 공용 타입 행 | common-types 승격: `SecurityFilter`, `StrategyFilter`, `ChannelRunId`, `EmbeddingSpaceIds`(visual-pages `page_*` 키 포함), `TableRef`, `ProfileId`, `AnalyzerId`, `KebabName`, `ContractsCompat`, `Bcp47`·`MediaType`(Pydantic 절). 승격 후 사본·교차 `$ref`는 common-types `$ref`로 전환 | 13, 15, 39, 154; CR-02, CR-26, CR-38, CR-39 | 03-contracts/00·05·07·08·09·10·14·15, `schemas/*` |
| AM-36 | 채택(minor) | §5.7 오류 코드 카탈로그 | 추가: `parse.page_ocr_failed`(—), `parse.page_skipped`(—), `parse.block_oversized`(—), `parse.block_limit_exceeded`(no), `parse.element_path_synthesized`(—), `parse.table_structure_fallback`(—), `parse.footnote_unanchored`(—), `parse.container_limit_exceeded`(no), `parse.extractor_fallback`(—), `contract.schema_type_mismatch`(no), `contract.upcast_failed`(no), `contract.acl_deny_all`(—), `render.template_unsupported`(no), `api.not_found`(no, 404), `api.quota_exceeded`(no; AM-39 할당량), `profile.gate_pending`(—). 비고: `enrich.extractor_timeout`은 청크 단위 `Warning.code`로도 쓴다 | 49, 105, 106, 135, 160, 162, 173; 완전성 #12 | 03-contracts/01·03·13·14·15, 04-pipelines/03~08·11, 05-api/01·04, common-types `ErrorCodeCatalog` |
| AM-37 | 채택(minor) | §5.7 `JobKind`, §11.2, §13.1 | 컬렉션 삭제: `JobKind.delete_collection`, 워크플로우 `collection.delete.v1`(부모가 문서 페이지를 순회해 자식 `delete.document.v1` 팬아웃), `collections.deleted_at`(논리 삭제). 새 이벤트 없음(`collection.profile.changed`·`ingest.document.deleted`·`audit.admin.action` 재사용) | 148; 완전성 #12 | 04-pipelines/19, 05-api/04, 02-architecture/03·04·06, 03-contracts/12 |
| AM-38 | 채택(minor) | §5.7 이벤트·열거 | 이벤트 `tenant.policies.changed`(도메인 "ACL·컬렉션" 옆 "테넌트"), 열거 `TenantStatus`: `active, disabled` | 완전성 #3·#12 | 03-contracts/12, 05-api/04·07, 02-architecture/07 |
| AM-39 | 채택(minor) | §14, §13.1 `tenants`, §6.7 | 엔드포인트 추가: `GET/POST /v1/tenants`, `GET/PATCH /v1/tenants/{tenant_id}`(`status`, `quotas{documents_max, storage_bytes_max, qps_max}`; `tier`는 읽기 전용, 승격은 `tier.promotion.v1`), `GET /v1/tenants/{tenant_id}/policies`, `GET/POST /v1/api-keys`·`DELETE /v1/api-keys/{api_key_id}`·`POST /v1/api-keys/{api_key_id}/rotate`, `GET /v1/plugins`·`/v1/plugins/{plugin_id}`, `GET /v1/schemas`(목록), `GET /v1/version`, `POST /v1/collections/{collection_id}/consistency-check`(`JobKind.consistency_check`), `GET /v1/audit-events`, `POST /v1/profiles`(새 버전 게시, 불변), `POST /v1/documents/{document_id}/unmask`(`pii_officer`, `tokenize`·`encrypt` 모드만). `tenants` 컬럼 `status`, `quotas jsonb`, `disabled_at`. §6.7에 단일 인스턴스 자원 예외(`/v1/version`) 명시 | 8; 완전성 #3 | 05-api/01·04·06, `05-api/openapi.yaml`, 02-architecture/01·04·07, 01-requirements/01(FR-MGT-01 충족 표기), 09-operations/05 |
| AM-40 | 채택(minor) | §6.2 | 캐시·해시 키 보강(구현 전이라 저장된 키 없음, 계약 필드 아님): `derived` = `H("derived", content_hash, sidecar_image_digest or "", options_hash or "")`(DPI·OCR 언어 등 파생물 옵션); `plan` 캐시 키에 `H("opts", canonical_json(플랜에 영향 주는 QueryRequest 옵션))` 추가; 새 행 `query_hash = H("query", normalized_query)`, `principal_hash = H("principal", tenant_id, subject)` | 70, 113, 115 | 03-contracts/09·12, 02-architecture/07 §8.2, 04-pipelines/05·14, 09-operations/03 |
| AM-41 | 채택(minor) | §6.5 | 정본 메트릭 목록에 09-operations/03 미해결 2의 확정분(`rag_eval_last_run_timestamp_seconds`, `rag_serving_gpu_seconds_total` 포함)과 04-pipelines/03 라우터 메트릭·스팬 추가. 라벨 규약 불변 | 122, 123 | 09-operations/03, 04-pipelines/03, ADR-0022 |
| AM-42 | 채택(minor) | §7.1 TXT·MD·JSON 행, §12 | 하위 경로 라이브러리 병기: `clevercsv`, `orjson`/`ijson`, `lxml`, `mdit_py_plugins`(04-pipelines/08 라이선스 확인분) | 133 | 04-pipelines/08 |
| AM-43 | 채택(minor) | §7.3 `ingest.normalize.pii` | 선택 키 `reject_entities: tuple[str, ...]`(`korean-gov` 주민등록번호 reject, §7.1 정본 실현) | 134 | 03-contracts/15, 04-pipelines/09, `schemas/profile.schema.json` |
| AM-44 | 채택(minor) | §13.1 `idempotency_keys`·`jobs` | 배치 멱등: `idempotency_keys.job_ids text[]`(배치 응답 재현), 배치 자식 잡의 `jobs.idempotency_key` NULL 허용(배치 키는 `idempotency_keys`에만) | 188 | 03-contracts/01, 05-api/02, 02-architecture/04 |

### 2.3 보류 — 요약(이유는 §5)

| 항목 | 판정 | 바이블 절 | 변경 요지 | 병합한 요청 # | 영향 문서 |
|------|------|-----------|-----------|---------------|-----------|
| AM-45 | 보류(major) | §11.4, §13.4 | 재색인 모드 B(두 해시 불변 변경)의 green 물리 이름, 모드 A 원장 포인터, 이름 불변 백엔드 일괄 플립 | 19, 32, 101, 163, 178 | 02-architecture/03·06, 04-pipelines/13·19, 03-contracts/08, ADR-0026 |
| AM-46 | 보류(major) | §11.5 | `cancelling → succeeded` 전이 추가 | 179; CR-29 | 03-contracts/08·12, 02-architecture/06 |
| AM-47 | 보류(major) | §11.3, ADR-0016 | `enrich.llm_unavailable` 소진 시 결정적 결과 보유면 `partial` | 177 | 04-pipelines/11, 02-architecture/06 |
| AM-48 | 보류(major) | §5.4 불변식, §4.2 | 원문 유래 조합형 자모(옛한글) 처리 | 93 | 03-contracts/04, 04-pipelines/09 |
| AM-49 | 보류(major) | §5.5 | `relaxed_keys` → `relaxed_applied_keys` 개명 | 198 | 03-contracts/11 |
| AM-50 | 보류(major) | §5.3 `Enrichment` | `keywords[].weight ≥ 0` 제약 강화 | CR-12 | 03-contracts/00·06 |
| AM-51 | 보류(근거 대기) | §13.4 | Nori stoptags `E, J, SC, SE, SF, SP, SSC, SSO, SY`·필터 순서 `nori_readingform → rag_pos_stop → lowercase` | 191 | 04-pipelines/13, 02-architecture/04 |
| AM-52 | 보류(근거 대기) | §7.1, §7.2, §4.2 | lite `page_route`, premium `enrichment_budget_tokens` 재산정, PDFium `helper_process` | 66, 132, 136 | 04-pipelines/05·11 |
| AM-53 | 보류(설계 미확정) | §14 | `dry_run`(202→200 의미 변경), `/v1/capacity`, `/v1/tenants/{tenant_id}/dictionary`, `/v1/plugins/{plugin_id}/health` | 193 | 03-contracts/01, 05-api/02·04 |
| AM-54 | 보류(근거 대기) | §5.7 이벤트 | `job.progress.updated` | 107 | 03-contracts/12 |
| AM-55 | 보류(외부 사실 확인) | §5.7 `BlockType` | Docling 체크박스 라벨 → `form_field` 매핑 비고 | 149 | 03-contracts/03, 04-pipelines/05 |
| AM-56 | 보류(M2) | §13.3 | `PairwiseRecord`·온라인 `judge.jsonl` 경로 | 190 | 08-evaluation/04 |

### 2.4 기각

| ID | 요청 # | 제안 | 기각 이유 | 문서 쪽 지시 |
|----|--------|------|-----------|--------------|
| R-01 | 20 | 바이블 §13.1에 `last_generation` 컬럼 | max+1 비재사용(AM-18)으로 충분, 컬럼 중복 | 03-contracts/08 미해결 14 대안 삭제 |
| R-02 | 21 | `CommitStatus`에 `discarded` | 02-architecture/06 §2.5 A-6이 폐기 green을 `committed`로 유지하기로 결정, 열거 추가는 소비자 배포 순서 영향이 큼 | 없음(08 비권장 기록 유지) |
| R-03 | 35 | `PackPlan.calibration_ratio`·`safety_margin` | 프로파일 `query.pack.tokenizer.*`를 PackContext가 읽는 경로로 해소(04-pipelines/17 정정 완료) | 03-contracts/09 미해결에서 제거 |
| R-04 | 79 | `VectorBundle`을 "바이블에 없는 새 타입"으로 표기 | 바이블 §5.1 공용 타입·§5.4 `EmbeddedChunkSet` 표에 정본으로 존재(리뷰 오독) | 없음 |
| R-05 | 92 | `container_flags` fetch 출력 선택화 | AM-06 잠정값 규약 patch로 오독 위험 해소, 필수 여부 변경 불필요 | 03-contracts/02 미해결 13을 AM-06으로 종결 |
| R-06 | 121 | `rag_eval_metric_value` 개명 | 바이블 §6.5 정본 목록·ADR-0036 유일 예외 | 없음 |
| R-07 | 124 | `rag_eval_metric_value`에 `dataset` 라벨 | 라벨 저카디널리티 규약(§6.5) 유지, `EvalRun` 원장 분해로 대체(10-development/05) | 10-development/05 미해결 16 종결 |
| R-08 | 181 | 셸 모듈 `orchestration/stage_shell.py` | 바이블 §12 `orchestration/context.py`가 정본 | 02-architecture/06 스케치 정정 |
| R-09 | 189 | `outbox.published_seq` 컬럼 | 바이블 컬럼만으로 `(published_at, event_id)` 커서가 성립(단일 릴레이 단조), IDENTITY는 늦은 커밋 문제를 풀지 못함 | 03-contracts/12 미해결 16을 실측 후 재발의로 격하 |
| R-10 | 2 | `lineage_refs.source`를 fetch 출력으로(04-pipelines/02 정정 요청) | 정본 결정 CR-01·CR-11: `source`는 detect 출력 `SourceDocument`, 02 §1.2가 정합 | 04-pipelines/03·01을 정정 |

## 3. 요청별 판정

괄호 안 절 표기는 입력 목록의 "바이블 절" 열(정규식 추출)이다. "문서 내부(전파 지시)" 행의 지시는 §6에 문서별로 다시 모았다.

| # | 출처 | 판정 | AM 또는 이유 |
|--:|------|------|--------------|
| 1 | 04-pipelines/09 (§1) | 문서 내부(전파 지시) | 04-pipelines/09·10: 미주 기본값 `separate`를 10 §1 정본 표에 병기해 합의(바이블 무관) |
| 2 | 04-pipelines/03 (§1.2) | 기각 | R-10. 정본 결정 CR-01(`lineage_refs.source` = detect 출력 `SourceDocument`)상 02 §1.2가 정합, 04-pipelines/03·01 쪽을 정정 |
| 3 | 09-operations/04 (§1.2) | 문서 내부(전파 지시) | 조치 없음(관찰 메모) |
| 4 | 09-operations/08 (§1.2) | 문서 내부(전파 지시) | 09-operations/08: `**제안:**` 유지, 릴리스 ADR은 ADR-0039+ 백로그로 등록 |
| 5 | 04-pipelines/03 (§2.1) | 문서 내부(전파 지시) | 조치 없음(리뷰 전건 반영 메모) |
| 6 | 03-contracts/00 (§2.2) | 문서 내부(전파 지시) | 03-contracts/13: 두 스키마를 common-types `$ref` 래퍼로 전환하고 §2.2 문구를 실제 파일과 일치시킴(T3) |
| 7 | 04-pipelines/01 (§2.2) | 문서 내부(전파 지시) | 04-pipelines/01·03: `format_detector` 프로파일 위치 합의; `lineage_refs.source`는 CR-01 |
| 8 | 02-architecture/01 (§2.2) | 채택(patch) | AM-04(C4 `Rel(api, s3)`); 테넌트 API는 AM-39(minor) |
| 9 | 03-contracts/02 (§2.2) | 문서 내부(전파 지시) | 조치 없음(01 정본 값 유지가 정합) |
| 10 | 10-development/03 (§2.2) | 문서 내부(전파 지시) | 10-development/03: 모호한 `01 §x`를 전체 경로(`10-development/01`·`04-pipelines/01`)로 표기 |
| 11 | 04-pipelines/06 (§2.2) | 채택(patch) | AM-09(`parser_version` 복수 패키지 표기) |
| 12 | 04-pipelines/13 (§2.2) | 채택(patch) | AM-24(바이블 §11.4 Note 세미콜론); 03-contracts/08 §2.2 `backend_version` 문구 정정은 문서 내부 |
| 13 | 03-contracts/15 (§2.2) | 채택(minor) | AM-35(공용 타입 승격) |
| 14 | 02-architecture/05 (§2.3) | 문서 내부(전파 지시) | 02-architecture/02 §2.3·05 §6.3: 레지스트리 `build_stage()`(Stage 반환)와 `build_port()`(포트 반환) 분리로 정적 타입 해소 |
| 15 | 03-contracts/08 (§2.3) | 채택(minor) | AM-35(`EmbeddingSpaceIds` 승격 시 visual-pages `page_*` 키 포함) |
| 16 | 09-operations/01 (§2.4) | 문서 내부(전파 지시) | 02-architecture/04 §2.4: `GRANT rag_owner TO rag_platform_admin`을 마이그레이션 역할 규약으로 등재 |
| 17 | 04-pipelines/01 (§2.4) | 문서 내부(전파 지시) | 02-architecture/05 §2.4: 미분류 예외 처리를 04-pipelines/01 §10.2(B2)에 맞춰 정정 |
| 18 | 02-architecture/05 (§2.4) | 문서 내부(전파 지시) | 02-architecture/02 §2.4: `ContextRenderer`에 `plugin_id` 추가(레지스트리 조회 키) |
| 19 | 02-architecture/03 (§2.5) | 보류 | AM-45(재색인 모드 B·green 명명, ADR-0026 개정) |
| 20 | 03-contracts/08 (§2.5) | 기각 | R-01. `last_generation` 컬럼 불필요 — AM-18이 max+1 비재사용을 명시 |
| 21 | 03-contracts/08 (§2.5) | 기각 | R-02. `CommitStatus` 값 추가(discarded) 불채택 — 02-architecture/06 §2.5 A-6이 폐기 green을 committed로 유지 |
| 22 | 04-pipelines/17 (§2.5) | 채택(minor) | AM-33(`RankedResult` 선택 필드) |
| 23 | 11-roadmap/02 (§2.8) | 문서 내부(전파 지시) | 11-roadmap/01: T-MGT-30/T-CHK-23 의존 인용 문장 확인 |
| 24 | 04-pipelines/17 (§2.8) | 문서 내부(전파 지시) | 03-contracts/11: 본문을 저장 스키마(`principals[]`)에 맞추고 `PackFiltersApplied`는 10의 `FiltersApplied` `$ref`로(CR-18) |
| 25 | 03-contracts/05 (§2.9) | 채택(minor) | AM-31(`table_cell_views` 등 NormalizedDocument 필드 등재) |
| 26 | 04-pipelines/17 (§2.9) | 문서 내부(전파 지시) | 03-contracts/10 §9: explain 표의 `boost_*` fuse 행 삭제(부스트 정본 17 §2.9) |
| 27 | 04-pipelines/06 (§2.15) | 문서 내부(전파 지시) | 조치 없음(잠금 버전 정본은 `uv.lock`) |
| 28 | 05-api/03 (§3) | 문서 내부(전파 지시) | 03-contracts/09 §3: Cedar 액션을 `search`(02-architecture/07 §4.1 정본)로; 05-api/03: 보안 필드 필터 거부는 422 `plan.filter_field_forbidden`(바이블 §4.3) |
| 29 | 03-contracts/06 (§3) | 문서 내부(전파 지시) | 04-pipelines/11 §3: `G` 행에 규칙 2(b) 예외 문구 추가 |
| 30 | 04-pipelines/12 (§3) | 채택(patch) | AM-11(`{extension_point}.pipeline`); 03-contracts/07 예시 `onnx_int8`, 03-contracts/15 `EmbedConfig` 필드 등재는 문서 내부 |
| 31 | 04-pipelines/18 (§3) | 문서 내부(전파 지시) | 04-pipelines/11·13, 03-contracts/05·09: 04-pipelines/18이 기록한 제안을 각 소유 문서가 반영 |
| 32 | 04-pipelines/19 (§3) | 보류 | AM-45(이름 불변 백엔드의 일괄 플립 대안은 커밋 상태 의미 변경) |
| 33 | 04-pipelines/06 (§3.1) | 문서 내부(전파 지시) | 03-contracts/03 §3.1: `element_path` 표에 DOCX(OOXML) 행 분리 |
| 34 | 03-contracts/14 (§3.1) | 문서 내부(전파 지시) | 조치 없음(14 내부 해소) |
| 35 | 04-pipelines/17 (§3.1) | 기각 | R-03. `PackPlan.calibration_ratio`·`safety_margin` 불필요 — 프로파일 `query.pack.tokenizer.*`를 PackContext가 읽는 것으로 해소 |
| 36 | 02-architecture/01 (§3.2) | 문서 내부(전파 지시) | 조치 없음(형식 선택 메모) |
| 37 | 02-architecture/01 (§3.2) | 문서 내부(전파 지시) | 조치 없음(형식 선택 메모) |
| 38 | 04-pipelines/02 (§3.2) | 문서 내부(전파 지시) | 03-contracts/13 §3.2·03-contracts/02 §7: `fetch.scheme_unsupported` 설명 정합 |
| 39 | 03-contracts/02 (§3.2) | 채택(patch) | AM-06(fetch 잠정값 규약)·AM-14(standard Tika)·AM-30(`strip_query_keys`)·AM-35(`Bcp47` 등); 00 §3.2 detect 행은 문서 내부 |
| 40 | 02-architecture/03 (§3.2) | 채택(patch) | AM-21(O-11·O-12 번호 배정) |
| 41 | 10-development/05 (§3.2) | 문서 내부(전파 지시) | 조치 없음(실측 후 판단) |
| 42 | 04-pipelines/05 (§3.2) | 문서 내부(전파 지시) | 03-contracts/03 §3.2: bbox는 "표시 페이지 프레임으로 역변환한 보정 후 좌표"로 문구 정합 |
| 43 | 04-pipelines/06 (§3.2) | 채택(minor) | AM-29(`section_index` OOXML 구역) |
| 44 | 04-pipelines/09 (§3.2) | 문서 내부(전파 지시) | 04-pipelines/01·09: `model_ids`의 `dict:` 항목과 인스턴스 규약 합의 |
| 45 | 04-pipelines/18 (§3.2) | 문서 내부(전파 지시) | 조치 없음(바이블 §3.2 O-03·§12 현행 유지, 배치는 ADR-0015 개정 시) |
| 46 | 08-evaluation/05 (§3.3) | 문서 내부(전파 지시) | 조치 없음 |
| 47 | 04-pipelines/06 (§3.3) | 문서 내부(전파 지시) | 02-architecture/08 §3.3: lo-sidecar 프로파일 재사용 방식을 콜드스타트 실측 후 정정 |
| 48 | 04-pipelines/09 (§3.3) | 문서 내부(전파 지시) | 03-contracts/04 §3.3: M5 예시 문구를 04-pipelines/09 M6 표현과 통일 |
| 49 | 03-contracts/14 (§3.3) | 채택(minor) | AM-36(`contract.schema_type_mismatch`·`contract.upcast_failed`·`render.template_unsupported`) |
| 50 | 04-pipelines/17 (§3.5) | 채택(minor) | AM-33(`pii_policy_applied`는 hydrate 경로로 확정) |
| 51 | 04-pipelines/09 (§3.9) | 문서 내부(전파 지시) | 조치 없음 |
| 52 | 05-api/01 (§4) | 문서 내부(전파 지시) | 05-api/02·04: DELETE 잡 접수형 멱등 지문 규칙(`wire_body = {}`) 대조 |
| 53 | 04-pipelines/01 (§4.1) | 채택(patch) | AM-05(`stage_key` 입력 해시 표기 정합) |
| 54 | 02-architecture/02 (§4.1) | 채택(minor) | AM-27(`StageContext.plan`); 02-architecture/05 질의 측 시그니처를 `Stage[In, Out]`로 정정 |
| 55 | 09-operations/03 (§4.1) | 문서 내부(전파 지시) | 조치 없음 |
| 56 | 05-api/04 (§4.1) | 문서 내부(전파 지시) | 02-architecture/07 §4.1: `manage_tenants` 행은 AM-39에 따라 "관리 API(`/v1/tenants`)" 유지로 정정 |
| 57 | 03-contracts/05 (§4.1) | 채택(minor) | AM-26(`requires_lineage` 범위: chunk) |
| 58 | 02-architecture/05 (§4.1) | 채택(minor) | AM-27(`StageContext.plan`·`artifacts`) |
| 59 | 09-operations/07 (§4.1) | 문서 내부(전파 지시) | 09-operations/06·07: RB-16이 색인에 오르면 07 §4.1 OpenSearch 행 참조 갱신 |
| 60 | 09-operations/07 (§4.1) | 문서 내부(전파 지시) | 09-operations/06: 버킷 전체 손실 전용 런북 신설 여부 판단(현행 RB-05 준용) |
| 61 | 03-contracts/07 (§4.1) | 채택(patch) | AM-05(embed 지문)·AM-07(embed 절단 `quality`); ADR-0012 문구 정합은 문서 내부 |
| 62 | 02-architecture/07 (§4.1) | 문서 내부(전파 지시) | 09-operations/05: `tenant_admin`의 `pii_officer` 자기 부여 직무 분리 통제 수용 |
| 63 | 04-pipelines/11 (§4.1) | 채택(minor) | AM-26(`requires_lineage` 범위: enrich LLM 서브스텝) |
| 64 | 04-pipelines/12 (§4.1) | 문서 내부(전파 지시) | 조치 없음(03-contracts/16과 공동 확정 대기) |
| 65 | 04-pipelines/18 (§4.1) | 문서 내부(전파 지시) | 04-pipelines/13 §4.1: `{m: 0, payload_m: 0}` 반영, Qdrant 동작 확인 필요 유지 |
| 66 | 04-pipelines/05 (§4.2) | 보류 | AM-52(PDFium helper_process, 적대적 코퍼스 측정 대기) |
| 67 | 03-contracts/14 (§4.2) | 채택(patch) | AM-23(§1.2 선택화·완화·강화 분류) |
| 68 | 04-pipelines/17 (§4.2) | 문서 내부(전파 지시) | 조치 없음 |
| 69 | 10-development/06 (§4.3) | 문서 내부(전파 지시) | 조치 없음 |
| 70 | 03-contracts/09 (§4.3) | 채택(minor) | AM-40(plan 캐시 키에 옵션 해시) |
| 71 | 04-pipelines/16 (§4.3) | 문서 내부(전파 지시) | 03-contracts/10 §4.3: `unavailable` 의미 열에 429·응답 검증 실패·서킷 열림 포함 |
| 72 | 04-pipelines/18 (§4.3) | 문서 내부(전파 지시) | 조치 없음 |
| 73 | 04-pipelines/08 (§4.4) | 채택(patch) | AM-07(parse 텍스트 resumable 비고) |
| 74 | 10-development/08 (§4.4) | 문서 내부(전파 지시) | 조치 없음 |
| 75 | 04-pipelines/13 (§4.4) | 문서 내부(전파 지시) | 02-architecture/04 §4.4: `DatetimeIndexParams` 확인 필요 표기 유지, 구현 스파이크에서 확정 |
| 76 | 04-pipelines/05 (§4.5) | 문서 내부(전파 지시) | 04-pipelines/03 §4.5: `parse.pdf.route` 값을 03-contracts/01 §2.5 라우트 이름으로 정정 |
| 77 | 04-pipelines/09 (§5) | 문서 내부(전파 지시) | 03-contracts/04: 미해결 1·4·10·19 정정 요청 검토 |
| 78 | 03-contracts/13 (§5) | 채택(minor) | AM-28(StageError·ProblemDetails 선택 필드) |
| 79 | 02-architecture/02 (§5.1) | 기각 | R-04. `VectorBundle`은 바이블 §5.1·§5.4에 이미 정본(리뷰 오독) |
| 80 | 03-contracts/14 (§5.1) | 문서 내부(전파 지시) | 조치 없음(리뷰 인용 오류, 00 현행 유지) |
| 81 | 03-contracts/07 (§5.2) | 채택(patch) | AM-07(embed 절단 시 `quality=degraded`) |
| 82 | 03-contracts/10 (§5.2) | 채택(patch) | AM-11(`retriever.pipeline`) |
| 83 | 04-pipelines/15 (§5.2) | 문서 내부(전파 지시) | 02-architecture/04 §5.2: `index_text.bigram` → `cjk_bigram`(바이블 §13.4 철자) |
| 84 | 03-contracts/00 (§5.3) | 채택(minor) | AM-28(`instance` uri-reference) |
| 85 | 04-pipelines/03 (§5.3) | 문서 내부(전파 지시) | 03-contracts/03 §5.3 (e): "폴백 체인에서 실패 뒤 성공 = degraded"(04-pipelines/03 §6.4)로 확정 |
| 86 | 04-pipelines/04 (§5.3) | 채택(patch) | AM-16(§9.5 `element_path` 예시)·AM-22(`hwpx_hwpxlib_sidecar`); 나머지는 03-contracts/03, 04-pipelines/01·03, 02-architecture/08 문서 내부 |
| 87 | 04-pipelines/06 (§5.3) | 문서 내부(전파 지시) | 03-contracts/03 P-1·§5.3: then 변환 경로(사이드카 → 인프로세스)를 반영 |
| 88 | 04-pipelines/07 (§5.3) | 문서 내부(전파 지시) | 04-pipelines/07: 03 §5.3 (e) 확정 후 degraded 근거 재검토 |
| 89 | 04-pipelines/07 (§5.3) | 문서 내부(전파 지시) | 03-contracts/03: #85와 동일 정정 |
| 90 | 04-pipelines/09 (§5.3) | 문서 내부(전파 지시) | 03-contracts/04: I-8 minor 개정(계약 소유) |
| 91 | 04-pipelines/19 (§5.3) | 문서 내부(전파 지시) | 조치 없음 |
| 92 | 03-contracts/02 (§5.4) | 기각 | R-05. `container_flags` 선택화 불채택 — AM-06 잠정값 규약 patch로 해소 |
| 93 | 03-contracts/04 (§5.4) | 보류 | AM-48(옛한글 조합형 자모 불변식) |
| 94 | 10-development/07 (§5.4) | 문서 내부(전파 지시) | 10-development/05·07: 봇 PR 자동 머지 vs "팀 1인" 규칙, 트레일러 템플릿 합의 |
| 95 | 10-development/08 (§5.4) | 문서 내부(전파 지시) | 10-development/08 §5.4: 핫픽스 PR 행 추가 검토 |
| 96 | 04-pipelines/10 (§5.4) | 채택(patch) | AM-09(`Chunk.ordinal` 문구) |
| 97 | 03-contracts/14 (§5.4) | 문서 내부(전파 지시) | 03-contracts/00 §4.12: 예시 `dataschema` 제거(CR-43) |
| 98 | 04-pipelines/15 (§5.4) | 문서 내부(전파 지시) | 조치 없음(불일치 부존재 확인) |
| 99 | 08-evaluation/05 (§5.5) | 문서 내부(전파 지시) | 08-evaluation/05: 게이트 점수 기준(리랭크 미적용 시 `final_score`) 확정 |
| 100 | 03-contracts/11 (§5.5) | 채택(patch) | AM-16(§9.5 `tokenizer.name`) |
| 101 | 04-pipelines/19 (§5.5) | 보류 | AM-45(§13.4 물리 이름 규약 개정) |
| 102 | 08-evaluation/03 (§5.6) | 채택(minor) | AM-34(`EvalDataset` 선택 필드) |
| 103 | 03-contracts/03 (§5.7) | 문서 내부(전파 지시) | 조치 없음 |
| 104 | 03-contracts/05 (§5.7) | 문서 내부(전파 지시) | ADR-0020: `Chunk.text` 직렬화(markdown)와 표시 html의 역할 분담 문구 patch |
| 105 | 04-pipelines/06 (§5.7) | 채택(minor) | AM-36(parse 경고·오류 코드) |
| 106 | 04-pipelines/07 (§5.7) | 채택(minor) | AM-36(`parse.extractor_fallback`) |
| 107 | 03-contracts/12 (§5.7) | 채택(patch) | AM-20(§14 "스테이지 경계 진행률"); `job.progress.updated`는 AM-54 보류 |
| 108 | 03-contracts/10 (§6) | 채택(minor) | AM-33(`text_truncated`) |
| 109 | 11-roadmap/02 (§6.1) | 채택(patch) | AM-11(§6.1 예시 `packer.default`) |
| 110 | 04-pipelines/11 (§6.1) | 채택(patch) | AM-11(API 모델 `model_id` 표기) |
| 111 | 04-pipelines/01 (§6.2) | 채택(patch) | AM-19(캐시 제외 스테이지 키·덮어쓰기 금지) |
| 112 | 09-operations/02 (§6.2) | 문서 내부(전파 지시) | 03-contracts/15: `flip_order[] ⊆ backends[].role` 불변식 번호 부여 후 09-operations/02 detail 접두 교체 |
| 113 | 09-operations/03 (§6.2) | 채택(minor) | AM-40(`query_hash`·`principal_hash`) |
| 114 | 04-pipelines/03 (§6.2) | 문서 내부(전파 지시) | 00-vision/04 §6.2: HWP 5.0·PDF·암호화 문구를 D-18 v1.1·ADR-0006·0007로 갱신 |
| 115 | 04-pipelines/05 (§6.2) | 채택(minor) | AM-40(`derived` 키 `options_hash`) |
| 116 | 03-contracts/12 (§6.2) | 문서 내부(전파 지시) | 02-architecture/06 §6.2: "queued 생성 — 이벤트 없음"을 "접수 시 `job.state.changed`"로 정정 |
| 117 | 04-pipelines/19 (§6.2) | 문서 내부(전파 지시) | 03-contracts/12 §6.2: `audit.admin.action.action` 어휘 확정(05-api/04·04-pipelines/19 합의) |
| 118 | 02-architecture/02 (§6.3) | 문서 내부(전파 지시) | 조치 없음 |
| 119 | 04-pipelines/17 (§6.3) | 문서 내부(전파 지시) | P2 분량 이관 대상(04-pipelines/17) |
| 120 | 02-architecture/08 (§6.4) | 문서 내부(전파 지시) | P1: relay → api SSE 푸시 전제를 가진 문서 점검 |
| 121 | 08-evaluation/02 (§6.5) | 기각 | R-06. `rag_eval_metric_value` 개명 불채택 — 바이블 §6.5 정본·ADR-0036 예외 |
| 122 | 09-operations/03 (§6.5) | 채택(minor) | AM-41(메트릭 추가) |
| 123 | 04-pipelines/03 (§6.5) | 채택(minor) | AM-41(라우터 메트릭·스팬) |
| 124 | 10-development/05 (§6.5) | 기각 | R-07. `dataset` 라벨 불채택 — `EvalRun` 원장 분해로 대체(라벨 카디널리티 규약 유지) |
| 125 | 03-contracts/12 (§6.5) | 채택(patch) | AM-13(CloudEvents `source` 값) |
| 126 | 03-contracts/10 (§6.7) | 문서 내부(전파 지시) | 03-contracts/09 §6.7: `enabled=false`여도 `RankedSet.rerank`(applied=false) 필수 출력 병기 |
| 127 | 11-roadmap/03 (§7) | 문서 내부(전파 지시) | 조치 없음(M1 종료 검토에서 바이블 §15 동기화 재판단) |
| 128 | 04-pipelines/06 (§7) | 문서 내부(전파 지시) | 03-contracts/03 §7: 각주·미주 행을 포맷별(HWPX·OOXML) 규칙으로 분리 |
| 129 | 04-pipelines/12 (§7) | 문서 내부(전파 지시) | 조치 없음(실측 후 전환) |
| 130 | 09-operations/01 (§7.1) | 채택(patch) | AM-14(lite 컨테이너 수) |
| 131 | 08-evaluation/04 (§7.1) | 채택(patch) | AM-11(`@<revision>` 선택) |
| 132 | 04-pipelines/05 (§7.1) | 보류 | AM-52(lite `page_route`, 게이트 근거 대기) |
| 133 | 04-pipelines/08 (§7.1) | 채택(minor) | AM-42(TXT·MD 하위 경로 라이브러리) |
| 134 | 04-pipelines/09 (§7.1) | 채택(minor) | AM-43(`pii.reject_entities`) |
| 135 | 03-contracts/13 (§7.1) | 채택(minor) | AM-36(`api.not_found`) |
| 136 | 04-pipelines/11 (§7.2) | 채택(minor) | AM-32(`charged_tokens`); premium 예산 재산정은 AM-52 보류 |
| 137 | 04-pipelines/02 (§7.3) | 문서 내부(전파 지시) | 조치 없음 |
| 138 | 04-pipelines/01 (§8) | 문서 내부(전파 지시) | 조치 없음(A1 링크 검사로 처리) |
| 139 | 05-api/04 (§8) | 채택(minor) | AM-30(`EgressPolicy` 선택 필드) |
| 140 | 09-operations/06 (§8) | 문서 내부(전파 지시) | 조치 없음 |
| 141 | 09-operations/06 (§8) | 문서 내부(전파 지시) | 09-operations/03 §8: 런북 열의 (제안) RB 번호를 06-runbooks 번호로 교체 |
| 142 | 03-contracts/07 (§8) | 문서 내부(전파 지시) | A1: 링크 대상 존재 확인 후 "(작성 예정)" 관행 정리 |
| 143 | 02-architecture/08 (§8) | 문서 내부(전파 지시) | A1: 전방 참조 1행 제거(대상 문서 작성 완료) |
| 144 | 03-contracts/08 (§8) | 문서 내부(전파 지시) | A1: "(작성 예정)" 표기 제거 |
| 145 | 02-architecture/09 (§8) | 문서 내부(전파 지시) | A1: 조치 없음(대상 문서 작성 완료) |
| 146 | 03-contracts/12 (§8) | 문서 내부(전파 지시) | 조치 없음(계약 문서 분량 예외, 브리프 §9.11) |
| 147 | 04-pipelines/16 (§8) | 문서 내부(전파 지시) | 04-pipelines/16: "작성 예정" 표기 제거(09-operations/04 존재) |
| 148 | 04-pipelines/19 (§8) | 채택(minor) | AM-37(컬렉션 삭제 등재) |
| 149 | 03-contracts/03 (§8.1) | 보류 | AM-55(체크박스 → `form_field` 매핑, 외부 사실 확인 대기) |
| 150 | 08-evaluation/05 (§8.1) | 문서 내부(전파 지시) | 조치 없음 |
| 151 | 03-contracts/09 (§8.1) | 문서 내부(전파 지시) | 조치 없음 |
| 152 | 09-operations/08 (§8.2) | 문서 내부(전파 지시) | 조치 없음 |
| 153 | 03-contracts/11 (§8.2) | 문서 내부(전파 지시) | 조치 없음 |
| 154 | 03-contracts/14 (§8.2) | 채택(minor) | AM-35(`KebabName`·`ContractsCompat` 승격) |
| 155 | 03-contracts/02 (§8.3) | 문서 내부(전파 지시) | 조치 없음 |
| 156 | 03-contracts/02 (§8.3) | 문서 내부(전파 지시) | 03-contracts/01 §8.3: 02의 `credentials_ref` 패턴 채택 사실로 문구 갱신 |
| 157 | 09-operations/04 (§8.3) | 문서 내부(전파 지시) | 조치 없음 |
| 158 | 02-architecture/03 (§9) | 문서 내부(전파 지시) | 조치 없음 |
| 159 | 02-architecture/06 (§9) | 문서 내부(전파 지시) | P2: 02-architecture/06 §9(처리량·사이징) → 09-operations/04 이관(D4-2) |
| 160 | 04-pipelines/07 (§9) | 채택(minor) | AM-36(`parse.block_limit_exceeded`) |
| 161 | 04-pipelines/10 (§9) | 문서 내부(전파 지시) | 조치 없음 |
| 162 | 04-pipelines/11 (§9) | 채택(minor) | AM-36(`enrich.extractor_timeout` 경고 겸용 명시) |
| 163 | 04-pipelines/13 (§9) | 보류 | AM-45(두 해시 불변 컬렉션 프로파일 변경) |
| 164 | 04-pipelines/14 (§9.2) | 문서 내부(전파 지시) | 조치 없음(CR-14 정합 확인) |
| 165 | 05-api/02 (§9.3) | 문서 내부(전파 지시) | 조치 없음 |
| 166 | 04-pipelines/07 (§9.3) | 문서 내부(전파 지시) | 03-contracts/00 §9.3: `application/xml` 미디어 타입 행 추가 |
| 167 | 05-api/03 (§9.4) | 문서 내부(전파 지시) | 조치 없음 |
| 168 | 04-pipelines/01 (§9.11) | 문서 내부(전파 지시) | P2: 04-pipelines/01 CLI·테스트 유틸 → 10-development/04 이관(D4-2) |
| 169 | 02-architecture/02 (§9.11) | 문서 내부(전파 지시) | P2: 02-architecture/02 설정 모델 → 09-operations/02 이관(D4-2) |
| 170 | 03-contracts/15 (§9.11) | 문서 내부(전파 지시) | 조치 없음(계약 문서 분량 예외) |
| 171 | 04-pipelines/11 (§10) | 채택(patch) | AM-12(`llm-enrich` 키 입력 정의)·AM-19(`derived/llm_enrich/` 행) |
| 172 | 04-pipelines/13 (§10) | 문서 내부(전파 지시) | 03-contracts/12: `IndexConsistencyMismatchData`에 선택 필드 `kind`·`observed_generations` 추가(계약 minor, T3) |
| 173 | 03-contracts/01 (§10.1) | 채택(minor) | AM-36(`contract.acl_deny_all` 경고)·AM-17(A6 잠금 의미) |
| 174 | 02-architecture/09 (§10.2) | 문서 내부(전파 지시) | 09-operations/03·05-api/04: `/healthz` = liveness(의존성 미포함), 의존성 상태는 `/readyz` |
| 175 | 03-contracts/15 (§10.3) | 채택(patch) | AM-01(`Capabilities` 행 순수 래퍼 주석) |
| 176 | 03-contracts/09 (§11) | 채택(patch) | AM-12(canonical_json 수치 표기) |
| 177 | 04-pipelines/11 (§11.3) | 보류 | AM-47(`enrich.llm_unavailable` 소진 시 partial 완화) |
| 178 | 02-architecture/06 (§11.4) | 보류 | AM-45(모드 A 원장 포인터, ADR-0026 개정) |
| 179 | 03-contracts/08 (§11.4) | 채택(patch) | AM-18(N 원천 명시); `cancelling → succeeded`는 AM-46 보류 |
| 180 | 02-architecture/02 (§12) | 채택(patch) | AM-22(`settings/` 등재) |
| 181 | 02-architecture/02 (§12) | 기각 | R-08. 셸 모듈은 바이블 §12 `orchestration/context.py`가 정본 — 02-architecture/06 스케치 정정 |
| 182 | 10-development/02 (§12) | 채택(patch) | AM-22(CLI 정본 소유·루트 개발 파일); 나머지 이슈는 10-development/02 문서 내부 |
| 183 | 08-evaluation/02 (§12) | 문서 내부(전파 지시) | 조치 없음(P3 표본 검증 시 대조) |
| 184 | 04-pipelines/03 (§12) | 채택(patch) | AM-22(`adapters/parse/router.py`) |
| 185 | 02-architecture/07 (§12.1) | 문서 내부(전파 지시) | 조치 없음(바이블 쪽 동일 결함은 AM-24) |
| 186 | 04-pipelines/15 (§12.3) | 문서 내부(전파 지시) | 04-pipelines/12·13: `values = 1.0` 규칙을 04-pipelines/15 `tf_q`로 위임하는 patch |
| 187 | 10-development/04 (§13) | 문서 내부(전파 지시) | 10-development/03 §13: 마커 목록을 04-testing-strategy §21 인용으로 교체 |
| 188 | 03-contracts/01 (§13.1) | 채택(minor) | AM-44(배치 멱등 원장 컬럼) |
| 189 | 03-contracts/12 (§13.1) | 기각 | R-09. `published_seq` 컬럼 불채택 — `(published_at, event_id)` 커서로 충족 |
| 190 | 08-evaluation/04 (§13.3) | 보류 | AM-56(평가 판정 산출물 경로, M2) |
| 191 | 04-pipelines/13 (§13.4) | 보류 | AM-51(Nori stoptags·필터 순서, 골든셋 A/B 게이트 대기) |
| 192 | 04-pipelines/13 (§13.4) | 문서 내부(전파 지시) | 02-architecture/04 §5.2: #83과 동일 |
| 193 | 03-contracts/01 (§14) | 보류 | AM-53(`dry_run` 엔드포인트 의미 변경) |
| 194 | 10-development/07 (§14) | 문서 내부(전파 지시) | 10-development/03 §14·§15: 07-contributing 정본(`rag-plugin-{name}`, `ADR:` 푸터, 브랜치 패턴) 인용 |
| 195 | 10-development/04 (§21) | 문서 내부(전파 지시) | 08-evaluation/02 §12: "dev 마커" 표기를 `slow` 재배정으로 정정 |
| 196 | 03-contracts/00 (-) | 문서 내부(전파 지시) | 조치 없음 |
| 197 | 04-pipelines/03 (-) | 채택(patch) | AM-09(`profile_option` 형식·예시) |
| 198 | 03-contracts/11 (-) | 보류 | AM-49(필드 개명) |
| 199 | 03-contracts/13 (-) | 채택(minor) | AM-28(`instance` 표기) |
| 200 | 03-contracts/13 (-) | 채택(patch) | AM-25(`retrieve.security_context_missing` HTTP 매핑) |

## 4. 완전성 검토 항목 판정

[3단계 완전성 검토](01-phase3-completeness-review.md) §3 누락 12건의 판정이다. 인계 13건 중 #1~#11은 아래 누락 번호와 1:1이며, 인계 #12(분량 실측 9건)는 P2가 A5 목록을 실측값(02-architecture/02·05·06·07, 04-pipelines/01·17, 08-evaluation/04, 09-operations/02, 11-roadmap/02)으로 교체해 처리하고, 인계 #13(정본 명칭 출현·FR/NFR 인용·§14 ↔ openapi 대조)은 `tools/audit-docs.mjs` A9 확장으로 처리한다(바이블 무관).

| # | 항목 | 판정 | 결정 |
|--:|------|------|------|
| 1 | 용어집 v0.2.0(바이블 §16 표 55행 미반영) | 문서 내부(P1 단독 묶음) | **결정:** 바이블 §16 표가 정본이며 바이블은 고치지 않는다. `00-vision/03-glossary.md`를 v0.2.0으로 개정해 추가 38행을 정의문으로 전개하고 변경 17행은 구 용어에 "→ 새 용어" 표기. 용어집 미해결 이슈는 `GL-xx`, 링크 키는 `[PL-xx]`(D4-1). 이번 트리아지의 새 이름(`TenantStatus`, `delete_collection`, `tenant.policies.changed`, `SchemaDiffReport`, `requires_lineage` 범위, O-11·O-12)도 함께 등재 |
| 2 | 비전 01·02·04, 요구사항 01·02·04 동기화 | 문서 내부(A3 → P1, patch) | **결정:** 여섯 문서는 patch 개정(v0.x.1)만 한다. 기각 기술(Redis·MinIO·PyMuPDF 기본·Infinity·pyhwp) 언급은 A3 출력으로 문맥 판정해 "기각했다"는 서술이면 유지, 채택 사실처럼 쓴 곳만 브리프 §4 v1.1·v1.2 개정 행(D-xx amended)으로 정정한다. 요구사항 ID·우선순위·SHALL 문장은 바꾸지 않는다(요구사항 의미 변경은 범위 밖). `00-vision/04` §6.2는 #114 지시를 따른다 |
| 3 | `FR-MGT-01` 테넌트 API 부재 | 채택(minor) AM-39·AM-38·AM-36 | **결정:** 요구사항(Must)을 설계에 맞춰 낮추지 않고 바이블 §14에 `/v1/tenants` 계열을 추가한다(브리프 §6 "관리 API" 포함 범위). 할당량은 `tenants.quotas`와 `api.quota_exceeded`, 비활성화는 `TenantStatus.disabled`(요청은 `auth.forbidden` 403). `rag` CLI는 같은 API를 호출하는 래퍼다. 05-api/01 §3.1 예외 행("§14에 `POST /v1/tenants` 없음")과 05-api/04 미해결 12의 "CLI·Helm" 정정 요청은 폐기 |
| 4 | FR/NFR 추적 매트릭스 부재 | 채택(문서 신설 완료) + AM-03 | **결정:** 기계 생성 `12-appendix/06-traceability-matrix.md`(`tools/traceability.mjs`, `11-roadmap/02` FR→에픽 표 시드)를 정본 추적 도구로 삼는다. 설계 문서 본문에 FR 인용을 억지로 넣지 않으며, 문서 맵 등재는 AM-03 |
| 5 | 관리 API DTO 15종 계약 지위 | 채택(patch) AM-02 | **결정:** API 전용 뷰로 두고 `openapi.yaml` `components`에만 정의한다. 계약 인벤토리를 늘리지 않으며, 동일 출처 원칙(FR-API-04)은 "DTO는 `api/` Pydantic 모델이 단일 출처, 계약 타입은 `schemas/` `$ref` 재사용"으로 충족한다. `TenantTier`·`Role`의 §5.7 등재는 하지 않는다(`TenantIsolationTier`가 이미 있음, 역할은 Cedar 정책 소유) |
| 6 | `docs/README.md` 상태·현황표 | 범위 밖(5단계) | **결정:** A6 자동 전환 대상에서 제외, 5단계 마감 편집 뒤 `active` |
| 7 | 브리프 §8 문서 맵 불일치 | 채택(patch) AM-03 | **결정:** 브리프 v1.2.2. `07-tech-landscape/` 13·14, `12-appendix/` 02~07 등재 |
| 8 | 바이블 §5.1 인벤토리 34 → 35 | 채택(patch) AM-01 | **결정:** `SchemaDiffReport` 행 추가 |
| 9 | `NFR-I-02`·`NFR-REL-17` | 문서 내부(A7 + P1) | **결정:** (a) `00-vision/04` I-13의 `NFR-I-02`는 NFR 문서의 실제 이슈 ID(`ISS-NFR-nn`)로 정정한다. (b) `NFR-REL-17`(리전 손실 RPO/RTO)은 4단계에서 신설하지 않는다. `09-operations/07`은 "요구사항 없음, 운영 목표(제안)"로 표기하고 요구사항 신설은 요구사항 소유자 백로그로 넘긴다 |
| 10 | CLI 정본 절 부재 | 채택(patch) AM-22 | **결정:** CLI 명령 정본은 `10-development/02-development-environment.md`에 "§CLI" 절을 신설해 둔다(676행으로 여유 있음; 09-operations/02는 1,006행이라 이관 대상). 바이블 §12 `cli/` 명령 목록(`up ingest query reprocess reindex eval profile plugin cache serve mcp`)과 `rag tenant`(AM-39 래퍼), 04-pipelines/01 §13 `rag run-stage`, 04-pipelines/09 §8.5 diff 리포트 명령을 이 절로 모은다. `rag run-stage`·diff 명령은 개발 전용 하위 명령으로 채택하고 바이블 §12 주석에 "명령 정본: 10-development/02" 1행만 둔다 |
| 11 | 제안서 A·B·C `status` | 문서 내부(A6) | **결정:** `deprecated`로 전환(역사 기록). 본문은 고치지 않는다 |
| 12 | 카탈로그 등재 후보 4건 | 채택(minor) AM-37·AM-38·AM-36·AM-34 | **결정:** `tenant.policies.changed` 등재(AM-38), `JobKind.delete_collection`·`collection.delete.v1`·`collections.deleted_at` 등재(AM-37), `profile.gate_pending` 경고 등재(AM-36), `Profile.profile_hash` readOnly N 등재(AM-34). 감사 이벤트를 캐시 무효화 트리거로 겸용하는 대안은 E12 원칙과 충돌하므로 쓰지 않는다 |

## 5. 보류 목록과 이유

보류는 두 부류다. (가) **major 유발**: 바이블 §1.2상 필드 제거·의미 변경·필수화·제약 강화·개명·스테이지 경계·상태 기계 변경이라 1.3.0 목표(D4-3)와 맞지 않고 ADR-0039 이후로 이관한다. (나) **근거 대기**: 가산이거나 기본값 변경이지만 게이트(§7.4)·실측·외부 사실 확인이 없어 지금 채택하면 근거 없는 결정이 된다.

### 5.1 M1 필수 여부 점검

6단계 M1(`lite`, `LocalRunner`, 계약 패키지·SDK, 한 문서 종단 간)의 필수 경로를 기준으로 보류 항목을 점검했다. M1에 반드시 필요한 개정은 AM-26(청커의 `ParsedDocument` 계보 접근)과 AM-27(`StageContext.plan`·`artifacts`)이며 둘 다 가산(minor)으로 표현할 수 있어 major 예외 채택은 없다. 아래 보류 항목은 M1 경로에 없거나(재색인 모드 B, 취소 경합, LLM 보강, 옛한글, premium·korean-gov 기본값) 현행 정본으로 M1을 구현할 수 있다.

### 5.2 목록

| 항목 | 부류 | 이유 | 그때까지의 잠정 규칙 | 재발의 시점 |
|------|------|------|----------------------|-------------|
| AM-45 재색인 모드 B·green 물리 이름·모드 A 원장 포인터 | (가) | §13.4 물리 이름 규약(명명 규약) 변경이고 §11.4 사가 예외를 만든다. 대안 (a)(b) 모두 바이블·ADR-0026 개정 필요 | `profile_hash`만 바뀐 재색인은 자동 실행 불가(부모 잡 `failed`) + 운영자 대안(변경 묶기·새 컬렉션 이관)(04-pipelines/19 잠정 규칙). 번호는 O-11·O-12(AM-21) | M2 이후, 04-pipelines/19 실측과 함께 ADR-0026 개정 |
| AM-46 `cancelling → succeeded` | (가) | 잡 상태 기계(§11.5)의 전이 의미 변경, 소비자 상태 처리에 영향 | 03-contracts/12 `ALLOWED_TRANSITIONS` 유지. 플립 시작(`flipping_lexical`) 후 도착한 취소 신호는 `cancelling`으로 전이시키지 않고 잡은 `running → succeeded`로 끝나며 취소 API는 202와 현재 `JobStatus`를 돌려준다(03-contracts/08 §3 규칙 (6) 정합) | M3 전 운영 요구 확인 시 |
| AM-47 `enrich.llm_unavailable` 소진 시 partial | (가) | 실패 정책 의미 변경(§11.3 재시도 분류, ADR-0016) | 현행: 재시도 소진 = 잡 `failed`, `retry?stages=enrich`로 재개 | LLM 보강을 켜는 M4 전 |
| AM-48 옛한글 조합형 자모 | (가) | `NormalizedDocument` 불변식(U+1100~U+11FF 잔존 금지)과 §4.2 실패 정책 변경 | 현행 불변식 유지, 원문 유래 조합형 자모는 `normalize.nfd_residual` 경로(03-contracts/04 미해결 18) | 한국어 골든셋에 옛한글 문서가 확인될 때 |
| AM-49 `relaxed_keys` 개명 | (가) | 필드 개명 = major | 현행 이름 유지 | 2.0.0 묶음 |
| AM-50 `keywords[].weight ≥ 0` | (가) | common-types 제약 강화 = major(AM-23) | 03-contracts/06 E-12는 계약 검증기 경고로만 | 2.0.0 묶음 |
| AM-51 Nori stoptags·필터 순서 | (나) | `analyzer_id`·렉시컬 매핑 기본값 변경 → 렉시컬 재색인. 04-pipelines/13이 골든셋 A/B 게이트를 조건으로 제시 | 바이블 §13.4 전문(`J*`·`E*`·`S*`) 유지, 04-pipelines/13 §5.1의 한계 명시 유지 | M2 골든셋 A/B 통과 시 minor |
| AM-52 lite `page_route`·premium 예산·PDFium `helper_process` | (나) | 기본 파라미터·격리 모드 변경은 게이트·적대적 코퍼스 측정 근거 필요 | 현행 §7.1·§7.2·§4.2 값 | 해당 측정 완료 시 minor |
| AM-53 `dry_run`·`/v1/capacity`·테넌트 사전·플러그인 헬스 프록시 | (나) | `dry_run`은 응답 상태·본문·멱등 키 소비를 바꾸는 엔드포인트 의미 변경. 나머지는 요구사항 근거가 약하거나 NetworkPolicy 정합(05-api/04 미해결 13)이 미정 | 03-contracts/01 범위 절 "제외" 유지 | M3 API 표면 확정 시 |
| AM-54 `job.progress.updated` | (나) | 세부 진행률 이벤트의 필요가 확인되지 않았다(AM-20으로 문구 해소) | 스테이지 경계 진행률 + 폴링 | UX 요구 확인 시 minor |
| AM-55 체크박스 → `form_field` | (나) | Docling 라벨명은 외부 사실이며 04-pipelines/05에서 확인 전 | 03-contracts/03 §8.1 "확인 필요" 행 유지 | 04-pipelines/05 확인 후 patch |
| AM-56 평가 판정 산출물 경로 | (나) | 온라인 판정 흐름이 M2 평가 착수 전 미확정 | 08-evaluation/04 제안 지위 | M2 |

## 6. 문서 내부 전파 지시

### 6.1 요청 행에서 나온 지시(문서별 한 줄)

AM 채택분의 전파(영향 문서 열)는 T2가 전파 지시서로 따로 낸다. 아래는 바이블 개정 없이 문서만 고치는 지시다.

- `00-vision/03-glossary.md`: v0.2.0 개정(완전성 #1, §4).
- `00-vision/04-scope-and-non-goals.md`: §6.2 HWP 5.0·PDF·암호화 문구를 D-18 v1.1·ADR-0006·0007로 갱신(#114), I-13 `NFR-I-02` → `ISS-NFR-nn`(완전성 #9).
- `02-architecture/02-component-architecture.md`: §2.3 레지스트리 `build_stage()`/`build_port()` 분리(#14), §2.4 `ContextRenderer.plugin_id` 추가(#18), 설정 모델 절 09-operations/02 이관(#169, P2).
- `02-architecture/04-storage-architecture.md`: §2.4 `GRANT rag_owner TO rag_platform_admin` 등재(#16), §4.4 `DatetimeIndexParams` 확인 필요 유지(#75), §5.2 `index_text.bigram` → `cjk_bigram`(#83·#192).
- `02-architecture/05-plugin-architecture.md`: §2.4 미분류 예외를 04-pipelines/01 §10.2(B2)에 맞춤(#17), 질의 측 확장 지점 시그니처를 `Stage[In, Out]` 특수화로(#54), §6.3 `build_port()` 반영(#14).
- `02-architecture/06-orchestration-and-workflows.md`: §6.2 "queued 생성 — 이벤트 없음" → "접수 시 `job.state.changed`"(#116), 셸 모듈 표기 `orchestration/context.py`(R-08), §9 처리량·사이징 → 09-operations/04 이관(#159, P2).
- `02-architecture/07-multi-tenancy-and-security-architecture.md`: §4.1 `manage_tenants` 행은 관리 API(`/v1/tenants`) 유지로 정리(#56, AM-39).
- `02-architecture/08-deployment-architecture.md`: §3.3 lo-sidecar 프로파일 재사용 방식을 콜드스타트 실측 후 정정(#47), §5.2 parser-workers Object Storage egress 행 추가(#86).
- `03-contracts/00-contract-overview.md`: §3.2 표에 `detect` 행(출력 `lineage_refs = {}`) 추가(CR-11·#39), §4.12 예시 `dataschema` 제거(#97·CR-43), §9.3 `application/xml` 행 추가(#166), §2 "열거 타입은 모두 common-types" 문구 유지(AM-10).
- `03-contracts/01-ingest-request.md`: §8.3·버전 이력의 02 `credentials_ref` 서술을 패턴 채택 사실로 갱신(#156), IR-5 ACL A4는 400 대신 `contract.acl_deny_all` 경고 접수로 완화(AM-17·AM-36).
- `03-contracts/02-source-document.md`: §7 `fetch.scheme_unsupported` 설명을 13 §3.2와 정합(#38).
- `03-contracts/03-parsed-document.md`: §3.1 DOCX(OOXML) `element_path` 행 분리(#33), §3.2 bbox 문구 "보정 후 좌표 = 표시 페이지 프레임"(#42), §5.3 (e) = "폴백 체인에서 실패 뒤 성공 = degraded"(#85·#89), P-1에 then 변환 경로 반영(#87), §7 각주·미주 행을 HWPX·OOXML로 분리(#128), §5.1 flow 행 `source=ocr`·§3.1 caption 경로(#86).
- `03-contracts/04-normalized-document.md`: §3.3 M5 예시 문구 통일(#48), I-8 minor 개정(#90), 미해결 1·4·10·19 검토(#77).
- `03-contracts/05-chunk-set.md`: C-3 형제 정의를 AM-09 문구로 인용(#31·#96).
- `03-contracts/07-embedded-chunk-set-and-index-record.md`: §3 예시 `"int8"` → `onnx_int8`(#30).
- `03-contracts/08-index-commit.md`: §2.2 `backend_version` 문구를 "어댑터 `backend_version` 속성(`capabilities()` 호출 시 조회)"로(#12), 미해결 14의 `last_generation` 대안 삭제(R-01).
- `03-contracts/09-query-request-and-query-plan.md`: §3 Cedar 액션 `query` → `search`(#28), §6.7 `enabled=false`에도 `RankedSet.rerank`(applied=false) 필수 출력 병기(#126), 미해결에서 `calibration_ratio`·`safety_margin` 제안 제거(R-03).
- `03-contracts/10-candidate-set-and-ranked-set.md`: §4.3 `unavailable` 의미 열에 429·응답 검증 실패·서킷 열림 포함(#71), §9 explain 표의 `boost_*` fuse 행 삭제(#26).
- `03-contracts/11-context-pack.md`: §2.8 본문을 저장 스키마 `principals[]`로 정합(#24).
- `03-contracts/12-jobs-events-and-status.md`: §6.2 `audit.admin.action.action` 어휘 확정(`delete_collection`·`manage_collection`·`gc_sweep` 등, #117), `IndexConsistencyMismatchData` 선택 필드 `kind`·`observed_generations`(#172, 계약 minor), 미해결 16(`published_seq`)은 실측 후 재발의로 격하(R-09).
- `03-contracts/13-error-model.md`: `stage-error`·`problem-details` 스키마를 common-types `$ref` 래퍼로 전환하고 §2.2 문구를 실제 파일과 일치(#6), §3.2 `fetch.scheme_unsupported` 설명(#38), E7 문구를 AM-25로 확정.
- `03-contracts/15-collection-profile-and-policy-contracts.md`: `flip_order[] ⊆ backends[].role` 불변식 번호 부여(#112), `EmbedConfig.sparse_bm25.avgdl`·`dense.prompts` 등재(#30).
- `04-pipelines/01-pipeline-framework.md`: `lineage_refs.source` = detect 출력 `SourceDocument`(R-10), `format_detector` 프로파일 위치를 03과 합의(#7), `model_ids`의 `dict:` 항목 인스턴스 규약을 09와 합의(#44), 원본 바이트 포트(#86), CLI·테스트 유틸 절 → 10-development/04 이관(#168, P2).
- `04-pipelines/03-parsing-router-and-format-detection.md`: `lineage_refs.source` 정정(R-10), §4.5 `parse.pdf.route` 값을 03-contracts/01 §2.5 라우트 이름으로(#76), §7.2 변환기 digest 기록 규약(#86).
- `04-pipelines/07-parser-html.md`: 03 §5.3 (e) 확정 후 degraded 근거 재검토(#88).
- `04-pipelines/09-normalization-and-cleaning.md`·`10-chunking-strategies.md`: 미주 기본 `separate`를 10 §1 정본 표에 병기(#1).
- `04-pipelines/11-enrichment.md`: §3 `G` 행에 규칙 2(b) 예외 문구(#29).
- `04-pipelines/12-embedding.md`·`13-indexing.md`: `values = 1.0` 규칙을 04-pipelines/15 `tf_q`로 위임(#186).
- `04-pipelines/13-indexing.md`: §4.1 `hnsw_config {m: 0, payload_m: 0}` 반영, Qdrant 동작 확인 필요 유지(#65).
- `04-pipelines/16-reranking.md`: 09-operations/04 링크의 "작성 예정" 표기 제거(#147).
- `04-pipelines/17-post-processing-and-context-packing.md`: 분량 이관(#119, P2).
- `04-pipelines/18-advanced-retrieval-graph-raptor-agentic.md`: 기록한 타 문서 제안(04-pipelines/11·13, 03-contracts/05·09)을 각 소유 문서가 반영(#31).
- `05-api/02-ingestion-api.md`·`04-management-api.md`: 잡 접수형 DELETE 멱등 지문(`wire_body = {}`) 대조(#52).
- `05-api/03-retrieval-api.md`: 보안 필드 필터 거부를 422 `plan.filter_field_forbidden`으로(#28).
- `05-api/04-management-api.md`·`09-operations/03-observability.md`: `/healthz` = liveness(의존성 미포함), 의존성 상태는 `/readyz`(#174).
- `08-evaluation/02-retrieval-metrics-and-harness.md`: §12 "dev 마커"를 `slow` 재배정으로 정정(#195).
- `08-evaluation/05-benchmark-plan-and-baselines.md`: 리랭크 미적용 시 게이트 점수 기준 확정(#99).
- `09-operations/03-observability.md`: §8 런북 열의 (제안) RB 번호를 06-runbooks 번호로(#141).
- `09-operations/05-security-and-compliance.md`: `tenant_admin`의 `pii_officer` 자기 부여 직무 분리 통제 수용(#62).
- `09-operations/06-runbooks.md`: RB-16 색인 등재·버킷 손실 전용 런북 여부 판단, 07-backup §4.1 참조 동기화(#59·#60).
- `09-operations/08-upgrade-and-migration.md`: `**제안:**` 표기 유지, 릴리스 ADR은 ADR-0039+ 백로그(#4).
- `10-development/03-coding-standards.md`: 모호한 `01 §x`를 전체 경로로(#10), §13 마커 목록을 04-testing-strategy §21 인용으로(#187), §14·§15를 07-contributing 정본 인용으로(#194).
- `10-development/05-ci-cd.md`·`07-contributing.md`: 봇 PR 자동 머지 vs "팀 1인" 규칙, `Breaking-Kind`·`Cache-Invalidation` 트레일러 템플릿 합의(#94), 05 미해결 16 종결(R-07).
- `10-development/08-release-process.md`: §5.4 핫픽스 PR 행 추가 검토(#95).
- `11-roadmap/01-milestones.md`: T-MGT-30/T-CHK-23 의존 인용 문장 확인(#23).
- ADR-0012: `lite`에서 `analyzer_id` 변경이 `sparse_bm25` 공간 id 변경 → Qdrant blue/green을 유발함을 문구에 반영(#61, patch).
- ADR-0020: `Chunk.text`(markdown) 직렬화와 표시 html의 역할 분담 문구(#104, patch).
- ADR-0033: "비재시도 `parse.*`는 폴백 없이 전파" 문구를 바이블 §4.2 실패 정책과 정합(CR-45, patch).
- 링크 표기(#138·#142~#145·#147): A1 링크 검사 결과로 일괄 처리, 대상 문서가 모두 작성되었으므로 "(작성 예정)"·전방 참조 표기를 제거한다.

### 6.2 계약 감사 정본 결정 47건의 처리

정본 결정은 이미 03-contracts·`schemas/`에 적용되어 있다. 아래는 바이블 쪽 연계(AM)와 하류 전파 대상이다. "확인"은 정본 위반이 없어 전파가 필요 없는 항목이다.

| CR | 처리 | 전파 대상 |
|---:|------|-----------|
| 01 | 전파 | 04-pipelines/01·03(R-10), 03-contracts/06·07·08 예시, 08 §2.4, `index-commit.schema.json`(T3) |
| 02 | 전파 → AM-35 | 03-contracts/08(사본 방식, 승격 후 `$ref`) |
| 03 | 전파 | 03-contracts/05 표 청크 `original_char_*`, 04-pipelines/10 |
| 04 | AM-26으로 잠정 해제 | 03-contracts/04·05, 04-pipelines/01·10(잠정 표기 → 결정) |
| 05 | 전파 | 03-contracts/07 §9 |
| 06 | 전파 | 03-contracts/08 예시 2 |
| 07 | 전파 | 03-contracts/06 예시 1·07 예시 3, 04-pipelines/10 |
| 08 | AM-10(CR-25로 대체) | 03-contracts/00 §2 |
| 09 | 전파(T3) | 03-contracts/03~08 스키마 `schema_version` 패턴 |
| 10 | 전파(T3) | `index-record.schema.json` `analyzer_id` 패턴 |
| 11 | 전파 | 03-contracts/00 §3.2 |
| 12 | 보류 AM-50 | 03-contracts/06 E-12(경고로만) |
| 13 | AM-12 | 03-contracts/02 §3 |
| 14 | 전파 | 03-contracts/09 P-11, 04-pipelines/14·17 |
| 15 | 전파 | 03-contracts/09 `PackPlan.k_max 1..20` |
| 16 | 전파 | 03-contracts/11 P-13 |
| 17 | 전파 + AM-12 | 03-contracts/09 §5.4 |
| 18 | 전파 | 03-contracts/11 `PackFiltersApplied` → `$ref` |
| 19 | AM-08 | 04-pipelines/15·17 |
| 20 | 전파 | 03-contracts/11 §6·§9 |
| 21 | 전파 | 03-contracts/07 §9 |
| 22 | 전파 | 03-contracts/11 P-6 |
| 23 | 전파 | 03-contracts/11 §8.2 |
| 24 | AM-16 | 03-contracts/09·11 |
| 25 | AM-10 | 03-contracts/01~16 인라인 열거(T3 이동) |
| 26 | AM-35 | 03-contracts/07·10 |
| 27 | 전파(T3) | 03-contracts/07·10·11 스키마 |
| 28 | 확인 | — |
| 29 | 보류 AM-46(잠정 규칙) | 03-contracts/08 §3 규칙 (6) |
| 30 | 전파 | 03-contracts/08 §7 |
| 31 | AM-18 | 03-contracts/08 |
| 32 | 확인 | — |
| 33 | 확인(바이블 현행 표는 두 코드를 `—` 열에 둠) | 03-contracts/13 인용 확인 |
| 34 | AM-28 | 03-contracts/00·13 |
| 35 | 확인 | — |
| 36 | AM-15 | 03-contracts/15 |
| 37 | AM-34 | 03-contracts/15·16 |
| 38 | 전파(T3) + AM-35 | `schemas/plugin-meta.schema.json` `ContractsCompat` |
| 39 | 전파 → AM-35 | 03-contracts/08 |
| 40 | 전파 | 03-contracts/16 EF-9 |
| 41 | 전파 | 03-contracts/16 `index_commit_ids` 상한 재산정 |
| 42 | AM-13 | 03-contracts/14 예시 4 |
| 43 | 전파 | 03-contracts/00 §4.12 |
| 44 | AM-12 | 03-contracts/16 §6.2; `mapping_version` 위치는 미해결 |
| 45 | 전파 | ADR-0033 문구 |
| 46 | 전파 | 03-contracts/15 `PackConfig.k_max ≤ 20`·`ChannelConfig.top_k ≤ 300` |
| 47 | 확인 | — |

## 결정 사항 요약

- **결정:** 요청 200행은 채택 patch 31 · minor 34 · major 0 · 보류 14 · 기각 10 · 문서 내부 111로 판정하고, 개정 항목 AM-01~AM-56(patch 25, minor 19, 보류 12)과 기각 R-01~R-10으로 병합했다.
- **결정:** 바이블 목표 버전은 **1.3.0**(minor), 브리프는 **v1.2.2**(§8 문서 맵 patch). major 채택은 없고 M1 필수 개정(AM-26·AM-27)은 가산으로 표현한다.
- **결정:** 계약·스키마 영향이 있다. 가산 변경만이며 계약 `schema_version`은 M1 이전 개정이므로 1.0.0을 유지하고 버전 이력에 기록한다. T3가 반영하고 `validate-contracts.mjs` ERROR 0을 게이트로 한다.
- **결정:** `FR-MGT-01`은 바이블 §14 `/v1/tenants` 계열 추가(AM-39)로 충족하고, 관리 API DTO는 API 전용 뷰(AM-02), 추적은 기계 생성 매트릭스(06), CLI 정본은 10-development/02 §CLI다.
- **결정:** 재색인 모드 B·green 물리 이름 문제는 개방 결정 O-11·O-12로 번호를 배정하고(AM-21) 해결은 ADR-0039 이후로 보류한다(AM-45).
- **결정:** minor 가산 묶음은 T2가 다음 빈 ADR 번호 한 건으로 발의한다(바이블 §1.2). `09-operations/08`이 제안한 0039 slug와 번호가 겹치면 ADR 인덱스 순번을 따른다.

## 미해결 이슈

1. **미정(O-11):** `profile_hash`만 바뀐 컬렉션 프로파일 변경의 green 물리 이름·재색인 모드 B(AM-45). 04-pipelines/19 실측 뒤 ADR-0026 개정.
2. **미정(O-12):** blue/green 채움 중 `documents` 원장 포인터와 정합성 검사 기준(AM-45).
3. `mapping_version`(렉시컬 매핑 버전)의 계약 위치(CR-44)는 03-contracts/15 등재 제안 상태다. T2가 AM-12와 함께 §6.2 설명에 "위치: 03-contracts/15 확정 대기"로만 적는다.
4. AM-39의 할당량 초과 HTTP 상태(`api.quota_exceeded`: 403 vs 429)는 05-api/01 §9와 02-architecture/07 §10(레이트 리밋·쿼터)에서 확정한다. 초안은 QPS 초과 = 기존 `api.rate_limited` 429, 문서 수·저장 용량 초과 = `api.quota_exceeded` 403이다.
5. 계약 `schema_version` 1.0.0 유지 결정은 03-contracts/14 §3.1 절차 표에 "M1 이전 개정" 규칙이 없어서 내린 판단이다. T2는 14에 이 예외를 1행으로 명시할지 판단한다.
6. AM-36 오류 코드 16개 가운데 경고 코드(`—`)는 발생 위치가 여러 파이프라인 문서에 흩어져 있다. P1에서 각 문서의 제안 표기를 결정 표기로 바꿀 때 13-error-model §3.2 표와 개수·철자를 대조해야 한다(카탈로그 68 → 84종).

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) §4·§5·§6·§8·§9
- [설계 바이블](../02-architecture/00-design-bible.md) §1.2, §3.2, §4.1~§4.4, §5.1~§5.7, §6.1~§6.7, §7.1~§7.3, §9.5, §10.1·§10.3, §11.2~§11.5, §12, §13.1~§13.4, §14
- [3단계 완전성 검토](01-phase3-completeness-review.md) §3·§4
- [진행 보고서](00-progress-report.md) §6·§7
- [기능 요구사항](../01-requirements/01-functional-requirements.md) FR-MGT-01, FR-API-04, FR-API-06, FR-PLG-02, FR-SEC-07, FR-SEC-08
- [관리 API](../05-api/04-management-api.md) 미해결 이슈 1~15
- [마일스톤](../11-roadmap/01-milestones.md) M1 정의
- 입력(문서 맵 등재 전이라 경로만 표기): `12-appendix/02-phase4-5-plan.md` §2.3·§7, `12-appendix/03-bible-amendment-triage-input.md` §2·§3, `12-appendix/06-traceability-matrix.md`
