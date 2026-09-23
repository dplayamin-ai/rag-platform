---
title: 3단계 완전성 검토
status: active
owner: architecture
version: 0.1.0
last_updated: 2026-09-23
depends_on:
  - ../00-vision/00-design-brief.md
  - ../02-architecture/00-design-bible.md
  - ../01-requirements/01-functional-requirements.md
  - ../01-requirements/02-non-functional-requirements.md
  - 00-progress-report.md
  - 02-phase4-5-plan.md
  - 03-bible-amendment-triage-input.md
  - 04-phase3-document-ledger.md
---

# 3단계 완전성 검토 (Phase 3 Completeness Review)

## 목적

3단계(설계 문서 작성)가 만든 문서 세트 **전체**를 놓고 "무엇이 빠졌는가"를 찾는다. 문서 하나하나의 내부 품질(정확성·문법·앵커 준수)은 3단계 리뷰 사이클이 이미 다뤘으므로 여기서는 다루지 않는다. 검토 대상은 (1) 브리프 §8 문서 맵과 실제 파일의 차이, (2) 설계 바이블 §2~§16의 정본 항목(타입·열거·이벤트·오류 코드·메트릭·강제 지점·프로파일·워크플로우·테이블·API 경로)이 바이블 밖 어느 문서에서도 상세화되지 않은 경우, (3) 브리프 R1~R6·D-01~D-20·품질 목표와 요구사항 ID(FR/NFR)의 인용 여부, (4) 스키마 34종·ADR 38종의 존재와 frontmatter `status` 잔여분이다. 결과는 4단계(교차 일관성) 입력으로 넘기며, **이 문서는 다른 문서를 고치지 않는다**.

## 범위

- 포함: `docs/**/*.md`(업스트림 사본 `12-appendix/sources/` 제외 149개)와 `docs/05-api/openapi.yaml`, `schemas/*.schema.json` 35개.
- 제외: ADR 본문의 내용 검토(사용자 지시 "ADR 제외"; ADR은 파일 존재·slug·frontmatter만 대조), 문서 내부 서술의 정확성, 외부 사실("확인 필요" 1,269곳)의 재확인, 코드.
- 정본 관계: 브리프 > 바이블 > ADR > 개별 문서(바이블 §1.1). 누락 판정의 기준은 브리프 §8·§9와 바이블 §2~§16이며, 이 문서는 그 기준을 바꾸지 않는다.

## 1. 방법

| 단계 | 절차 | 도구 |
|------|------|------|
| M1 문서 맵 대조 | 브리프 §8의 디렉터리별 파일 목록과 `docs/` 실측 목록을 양방향 비교(맵에 있으나 없는 문서 / 파일은 있으나 맵에 없는 문서) | `find`, 수작업 대조 |
| M2 바이블 정본 항목 검색 | 바이블 §4.2~4.4(스테이지·큐·오류 코드), §5.1(스키마 파일 34), §5.7(열거 타입명 79종·이벤트 24·오류 코드 68·`FilterableField`), §6.1~6.6(식별자·해시 결합식·메트릭 25·환경 변수 9), §7.1(프로파일 4), §8.2(후처리·pack 서브스텝), §9(패커·렌더러·프롬프트 캐싱 필드), §10.3(E1~E17), §11.2(워크플로우 10·큐 6), §12(모듈·CLI 명령·적합성 키트), §13.1~13.4(테이블 21·오브젝트 키·Qdrant/OpenSearch/Valkey 명명), §14(엔드포인트 41행)에서 **고유 명칭 약 640개**를 추출해 바이블을 제외한 전 문서에서 고정 문자열(`grep -F`) 또는 단어 경계 정규식으로 검색. 출현 파일 0개 = 누락, 1~2개 = 박약으로 기록 | `grep -rnoF -f`, `awk` 집계(스크립트는 세션 스크래치, 재현 가능) |
| M3 요구사항 인용 표본 | `01-functional-requirements.md`의 `FR-XXX-NN` 217개, `02-non-functional-requirements.md`의 `NFR-XXX-NN` 150개를 추출해 (a) 01-requirements 밖 전체, (b) 설계 문서(02~05·08~10)만을 대상으로 인용 여부를 계산. 브리프 R1~R6·D-01~D-20·O-01~O-10·K1~K7·§7 수치도 파일 수를 셈 | `grep -ohE`, `comm` |
| M4 스키마·ADR·frontmatter | §5.1 스키마 파일명 34개 ↔ `schemas/` 35개; §3.3 ADR 번호·slug 38개 ↔ `06-adr/` 파일명; `status:` 값 분포와 `draft`/`review` 파일 목록; `depends_on`·`schema_version`·ADR `version` 누락; 브리프 §9.3 필수 절(`## 목적`·`## 범위`·`## 결정 사항 요약`·`## 미해결 이슈`·`## 참조`, 계약 문서는 `## 스키마`·`## 예시`·`## 불변식`·`## 버전 이력`) 존재; §9.11 분량(250~900행) | `grep -L`, `wc -l` |
| M5 API 표면 대조 | 바이블 §14의 경로 41행 ↔ `openapi.yaml` `paths` 키 | `grep -nE "^  \"/"` |

검색은 이름 단위이므로 "이름은 등장하지만 의미가 얕게만 다뤄진" 경우는 잡지 못한다. 그런 항목은 4단계 교차 일관성 검사의 몫이다.

## 2. 통계

### 2.1 산출물

| 항목 | 값 | 비고 |
|------|---:|------|
| 문서(`docs/**/*.md`, `sources/` 제외) | 149 | 00-vision 5 · 01-requirements 4 · 02-architecture 10 · 03-contracts 17 · 04-pipelines 19 · 05-api 7(+`openapi.yaml`) · 06-adr 38+README · 07-tech-landscape 15 · 08-evaluation 6 · 09-operations 8 · 10-development 8 · 11-roadmap 3 · 12-appendix 4+제안서 3 · README 1 |
| 업스트림 사본(`12-appendix/sources/otel-genai-semconv/`) | 5 | 문서 규약 적용 제외(frontmatter 없음) |
| JSON Schema(`schemas/`) | 35 | 바이블 §5.1 인벤토리 34 + `schema-diff-report.schema.json`(§5.1 미등재, 03-contracts/14 소유) |
| ADR | 38 | §3.3 번호·slug 38/38 일치, 전부 `status: accepted`, `version` 전부 존재(진행 보고서 §6의 "8건 누락"은 해소됨) |
| OpenAPI `paths` | 41 | 바이블 §14의 41행 전부 존재(`/mcp`, `/v1/convert`, `/.well-known/oauth-protected-resource` 포함) |
| frontmatter `status` 분포 | active 106 · accepted 38 · draft 5 · 없음 5 | `review` 0(원장 04의 13건은 마무리 실행에서 전환 완료) |
| 브리프 §9.3 필수 절 누락 문서 | 0 | 02~05·07~11 전 문서; 계약 문서 17종의 `## 스키마`·`## 예시`·`## 불변식`·`## 버전 이력`도 전부 존재 |
| `depends_on` 누락 | 2 | `00-design-brief.md`(앵커, 예외 가능), `README.md` |
| "확인 필요" 표기 | 1,269곳 | 외부 사실 재확인 백로그(4단계 범위 밖, 계획 02 §2.1 A8) |

### 2.2 바이블 정본 항목의 하위 문서 출현률(바이블 제외)

| 정본 항목군 | 항목 수 | 출현 0 | 출현 1~2 파일 | 비고 |
|-------------|--------:|-------:|--------------:|------|
| 열거 타입명(§5.7) | 79 | 0 | 1 | `TextFormat`(03-contracts/00·11만) |
| 공용·계약 타입명(§5.1·§5.3) | 56 | 0 | 0 | `ParentEntry`·`IndexPerTenantMode`·`ScoreKind`·`SufficiencyMethod`는 3~4파일 |
| 이벤트 이름(§5.7 카탈로그) | 24 | 0 | 0 | 최소 4파일(`ingest.document.enriched`) |
| 오류 코드(§5.7 카탈로그 + §4.2) | 68 | 0 | 0 | |
| 메트릭 정본(§6.5) | 25 | 0 | 0 | |
| 해시·식별자 규칙(§6.1·6.2) | 32 | 0 | 0 | `security_context_hash`·`RAG-Signature`·`NAMESPACE_RAG_CHUNK`·`canonical_json` 포함 |
| 강제 지점 E1~E17(§10.3) | 17 | 0 | 0 | 바이블 제외 17~47파일; 02-architecture/07에 전부 등장(E11은 2회로 가장 박약) |
| 프로파일 4종(§7) | 4 | 0 | 0 | 09-operations/02에 `lite`·`standard`·`premium`·`korean-gov` YAML 전문 |
| 워크플로우·큐(§11.2) | 16 | 0 | 0 | |
| PostgreSQL 테이블(§13.1) | 21 | 0 | 0 | `eval_runs`·`calibrations`·`audit_log`는 4파일 |
| Valkey 키 접두·오브젝트 키·물리 명명(§13.3·13.4) | 24 | 0 | 0 | |
| 환경 변수(§6.6) | 9 | 0 | 0 | |
| API 경로(§14) | 41 | 0 | 0 | `openapi.yaml` + 05-api |
| 모듈·적합성 키트·CLI 명령(§12) | 60 | 0 | 2 | `rag reprocess`(02-architecture/02만), `rag reindex`(02-architecture/02·09-operations/06) |
| 패커·렌더러·프롬프트 캐싱 필드(§9) | 30 | 0 | 0 | `litm_alternating_primacy`·`search_result_location`·`stable_prefix` 포함 |

바이블 §2~§15 각 절의 상세화 문서(절 번호를 인용하는 문서 기준)는 다음과 같다.

| 바이블 절 | 주 상세화 문서 | 판정 |
|-----------|----------------|------|
| §2 아키텍처 요약(K1~K7, C4) | 02-architecture/01·02 | 있음 |
| §3 결정 레지스터 | 06-adr/0001~0038 + README | 있음 |
| §4 스테이지 파이프라인 | 04-pipelines/01(프레임워크), 02~13(수집), 14~17(검색), 03-contracts/15(`StagePolicy`) | 있음 |
| §5 계약 인벤토리·열거 | 03-contracts/00~16, `schemas/` | 있음(§5.1 표만 35번째 파일 미등재) |
| §6 명명 규약 | ADR-0036, 03-contracts/00, 10-development/03 | 있음 |
| §7 프로파일 | 03-contracts/15, 09-operations/02, ADR-0031 | 있음 |
| §8 검색 경로 | 04-pipelines/14·15·16·17, 05-api/03 | 있음 |
| §9 ContextPack·렌더러 | 03-contracts/11, 04-pipelines/17, ADR-0024 | 있음 |
| §10 멀티테넌시·ACL | 02-architecture/07, 09-operations/05, ADR-0027·0028·0038 | 있음 |
| §11 오케스트레이션 | 02-architecture/06, 03-contracts/12, 04-pipelines/19 | 있음 |
| §12 모듈 맵 | 10-development/01 | 있음(CLI 표면만 소유 문서 없음, 누락 #10) |
| §13 저장소 | 02-architecture/04, 09-operations/07 | 있음 |
| §14 API 표면 | 05-api/01~07, `openapi.yaml` | 있음(테넌트 생성 API 부재, 누락 #3) |
| §15 리스크 Top 10 | 11-roadmap/03(레지스터 49건, §15 매핑) | 있음 |
| §16 용어 추가·변경 | 00-vision/03-glossary.md | **미반영**(누락 #1) |

### 2.3 요구사항·브리프 인용

| 항목 | 값 |
|------|----|
| FR 정의 / 01-requirements 밖 미인용 / 설계 문서(02~05·08~10) 기준 미인용 | 217 / 161(74%) / 186(86%) |
| NFR 정의 / 01-requirements 밖 미인용 / 설계 문서 기준 미인용 | 150 / 37(25%) / 83(55%) |
| 설계 문서에서 인용 0인 FR 그룹 | FR-ENR(0/9), FR-MGT(0/14), FR-NRM(0/10), FR-PCK(0/15), FR-PLG(0/10), FR-PRS(0/22), FR-QRY(0/11) |
| 설계 문서에서 인용 0인 NFR 그룹 | NFR-CMP(0/10), NFR-CST(0/8), NFR-PORT(0/8) |
| 디렉터리별 인용 고유 ID 수 | 02-architecture 66 · 03-contracts 0 · 04-pipelines 17 · 05-api 13 · 06-adr 0 · 08-evaluation 6 · 09-operations 27 · 10-development 6 · 11-roadmap 121 |
| 정의되지 않은 ID 인용 | `NFR-I-02`(00-vision/04 I-13), `NFR-REL-17`(09-operations/07 미해결 이슈 — 신설 제안) |
| 사용자 스토리 US 104 중 설계 문서 인용 / 유즈케이스 UC 20 중 인용 | 96 / 6 |
| 브리프 R1~R6 인용 파일 수(브리프 제외) | R1 56 · R2 49 · R3 37 · R4 29 · R5 18 · R6 51 |
| D-01~D-20 인용 파일 수(브리프·바이블 제외) | 최소 D-03 10 · 최대 D-02 85; 전부 10 이상 |
| O-01~O-10 / K1~K7 인용 파일 수 | 전부 32 이상 / K4 10 · K7 17 · 그 외 22 이상 |
| 브리프 §7 품질 목표 수치(800ms·1.5s·30s·5min·0.80·0.92·99.9%·+15%p) | 전부 10파일 이상 등장 |

## 3. 누락 목록

심각도: **blocker** = 4단계 종료 전 반드시 해소(정본 충돌·요구사항 미충족), **major** = 4단계에서 해소(문서 세트의 신뢰성에 영향), **minor** = 4·5단계 중 기계 처리 또는 소폭 편집.

| # | 영역 | 심각도 | 설명 | 반영할 문서 |
|--:|------|--------|------|-------------|
| 1 | 용어집 | **major** | 바이블 §16 "다음 개정에 반영" 표(추가 38행·변경 17행)가 용어집에 반영되지 않았다. `03-glossary.md`는 v0.1.0(2026-09-18) 그대로이며 `hydrate`, `ChunkTextStore`, `record_id`, `scope_key`/`stage_key`, `RAG-Signature`, `EgressPolicy`, `TieringPolicy`, `litm_alternating`, 3-텍스트 규칙, 점수 원장, 단일 좌표계, `index_generation`/`is_current`, `aclrev`, `channel_run_id`/`variant_id`/`workflow_run_id`, `cite_id`, `point_id`, `sufficiency`/`confidence_tier`, `PackStep`, `recount`, `korean-gov`, `payload_filter`/`shard_key`/`index_per_tenant`, `ArtifactRef`, `SecurityContext`, `item_kind`, `LocalRunner`, `RustFS`, Cedar, OpenBao가 **0회** 등장한다(`Valkey`·`qrels`·`IndexCommit`·small-to-big는 있음). 변경 행 중 MinIO → RustFS/SeaweedFS, `point_id = uuid5(record_id)`, 강제 지점 15 → 17도 미반영 | `00-vision/03-glossary.md`(v0.2.0) |
| 2 | 상류 문서 동기화 | **major** | 비전 01·02·04와 요구사항 01·02·04가 모두 v0.1.0~0.2.0(2026-09-18)에 고정되어 브리프 v1.2.1·바이블 v1.2.1의 개정(D-01·02·04·06·07·08·11~20 amended, E16·E17, `hydrate`, `record_id` 세대 합성, `LocalRunner`, Valkey/RustFS, pypdfium2)을 알지 못한다. 여섯 문서에서 `hydrate`·`record_id`·`LocalRunner`·`TieringPolicy`·`EgressPolicy`·`korean-gov`·E16/E17은 0회, 기각 기술은 Redis 9회·MinIO 5회·PyMuPDF 5회·Infinity 7회·pyhwp 5회 등장한다(기각 사실을 서술하는 문맥인지 4단계 A3에서 판정). 요구사항은 설계의 앵커이므로 "요구사항이 설계보다 낡은" 상태는 추적성(#4)을 무력화한다 | `00-vision/01·02·04`, `01-requirements/01·02·04` — 개정 범위는 4단계 T1이 결정(브리프 §4 개정 행을 근거로 patch/minor) |
| 3 | API 표면 ↔ 요구사항 | **major** | `FR-MGT-01`(Must: 테넌트 생성·조회·비활성화·할당량 API)에 해당하는 엔드포인트가 바이블 §14·`openapi.yaml`·05-api/04에 없다. 05-api/01 §은 "v1 표면에 없다(§14에 `POST /v1/tenants` 없음), `rag` CLI·원장 마이그레이션 경로"로 명시해 요구사항과 설계가 충돌한다(02-architecture/01 미해결 이슈 12도 같은 지적). 같은 묶음으로 05-api/04 미해결 이슈 1의 제안 엔드포인트(`/v1/api-keys*`, `/v1/plugins*`, `GET /v1/schemas`, `/v1/version`(FR-API-06), `/v1/capacity`, `POST …/consistency-check`, `GET /v1/audit-events`, `GET /v1/tenants/{tenant_id}/policies`, `POST /v1/profiles`, `POST …/unmask`)이 "제안" 상태다. 할당량(quota) 관리는 어느 API 문서에도 없다 | 바이블 §14(minor 발의) → `05-api/04`, `openapi.yaml`; 또는 `FR-MGT-01`을 CLI 경로로 개정(요구사항 소유자 결정) |
| 4 | 요구사항 추적성 | **major** | FR 217개 중 161개(74%)가 01-requirements 밖 어느 문서에서도 인용되지 않고, 설계 문서(02~05·08~10) 기준으로는 186개(86%)·NFR 83개(55%)가 미인용이다. 03-contracts와 06-adr은 FR/NFR 인용이 0이며, FR-ENR·MGT·NRM·PCK·PLG·PRS·QRY와 NFR-CMP·CST·PORT는 설계 문서 인용이 한 건도 없다. 사실상 유일한 추적 경로는 11-roadmap/02(121개 ID → 에픽)다. 유즈케이스 UC 20건 중 6건만 인용된다(US는 104 중 96 인용으로 양호). 브리프 §9는 문서별 FR 인용을 의무화하지 않으므로 규약 위반은 아니지만, 요구사항 → 설계 → 검증(T-CONTRACT·T-E2E 등 FR의 검증 열)이 이어지지 않아 "요구사항이 어디서 충족되는지"를 기계로 확인할 수 없다 | 추적 매트릭스 신설(`12-appendix/05-requirements-traceability-matrix.md` 또는 `01-requirements/05-…`; 문서 맵 개정 필요) — FR/NFR → 설계 문서 §·계약·ADR·에픽·테스트 종류. 최소안: 각 설계 문서 `## 범위`에 "관련 요구사항" 한 줄 |
| 5 | 관리 API 응답 객체 | **major** | 05-api/04가 쓰는 `TenantPolicies`, `TenantUsage`, `CollectionCreateRequest`, `ReindexEstimate`, `CollectionStatsView`, `DictionaryReplaceResult`, `ProfileSummary`, `ProfileValidationResult`, `PluginCapabilitiesView`, `PluginHealth`, `SchemaDescriptor`, `ApiKey`, `VersionInfo`, `CapacityView`, `Document` 15종이 바이블 §5.1 인벤토리와 `schemas/` 밖에 있고 `openapi.yaml` `components`(140개 정의)에만 존재한다. `FR-API-04`(Must)는 "OpenAPI 스키마가 계약 JSON Schema와 동일 출처에서 생성"을 요구하므로, 이 객체들의 계약 지위(인벤토리 등재 vs "API 전용 DTO" 예외 규칙, 05-api/01 §8)를 정하지 않으면 동일 출처 원칙이 성립하지 않는다 | 바이블 §5.1(추가 행 또는 "API 전용 DTO" 각주), `05-api/01` §8, `03-contracts/00` |
| 6 | 문서 지도(README) | **major** | `docs/README.md`가 `status: draft`이고 디렉터리 현황 표가 실측과 다르다(05-api "4/7 작성", 10-development "7/8", 11-roadmap "1/3", ADR "인덱스 마무리 중" — 실제로는 전부 작성 완료·active). 12-appendix 01~04(본 문서·계획·트리아지 입력·원장) 링크가 없고 `depends_on`이 없다. README는 브리프 §8이 "읽기 순서·문서 지도"로 지정한 진입점이므로 낡은 상태는 문서 세트 전체의 신뢰도를 떨어뜨린다 | `docs/README.md`(5단계 마감 산출물; 4단계 A6에서 `active` 전환 금지 — 내용 갱신 후 전환) |
| 7 | 문서 맵 | minor | 브리프 §8 문서 맵과 파일 불일치: (a) `07-tech-landscape/`가 "00, 01-… 12-…"로 적혀 있으나 `13-korean-nlp-tokenization-and-language-resources.md`·`14-advanced-rag-graph-raptor-agentic-multimodal.md`가 존재(선정 매트릭스 00은 두 문서를 인용), (b) `12-appendix/`에 `02-phase4-5-plan`·`03-bible-amendment-triage-input`·`04-phase3-document-ledger` 미등재. 맵에 있으나 없던 `01-phase3-completeness-review`는 본 문서로 해소. 브리프 §9.6 "문서 맵에 있는 경로만 링크"에 따라 미등재 문서로의 링크는 기술적으로 규약 위반이 된다 | `00-vision/00-design-brief.md` §8(v1.2.2 patch) |
| 8 | 스키마 인벤토리 | minor | `schemas/schema-diff-report.schema.json`(`$id urn:rag:schema:schema-diff-report:1`, 03-contracts/14 소유, 15·05-api/04·10-development/05·06·08이 인용)이 바이블 §5.1 인벤토리에 없다. 34 → 35 | 바이블 §5.1(진행 보고서 §6 기등재) |
| 9 | 미정의 ID 인용 | minor | (a) `00-vision/04` I-13이 `NFR-I-02`를 인용하지만 NFR 문서에 그 ID가 없다(NFR 문서의 이슈 ID는 `ISS-NFR-NN`). (b) `09-operations/07` 미해결 이슈가 `NFR-REL-17` 신설(리전 손실 RPO/RTO)을 제안 — 요구사항 소유자 결정이 없으면 미정의 ID가 남는다 | `00-vision/04-scope-and-non-goals.md`, `01-requirements/02-non-functional-requirements.md` |
| 10 | CLI 표면 | minor | 바이블 §12 `cli/`가 정의한 `rag up·ingest·query·reprocess·reindex·eval·profile(validate diff)·plugin(list --check-license)·cache(invalidate --stage)·serve(api worker relay sidecar)·mcp` 명령을 소유하는 문서가 없다. `rag reprocess`는 02-architecture/02 한 곳, `rag reindex`는 두 곳에만 등장하고, 04-pipelines/01 §13 `rag run-stage`·04-pipelines/09 §8.5 "diff 리포트 CLI"가 각각 "제안"으로 흩어져 있다. 테넌트 생성(#3)이 CLI 경로로 위임된 만큼 CLI 정본이 필요하다 | `09-operations/02-configuration-reference.md`(CLI 절 추가) 또는 `10-development/02`; 새 문서로 두려면 문서 맵 개정 |
| 11 | frontmatter 상태 | minor | `status: draft` 5건 — `README.md`(#6), `12-appendix/02-phase4-5-plan.md`(계획 확정 시 `active`), 설계 경쟁 제안서 A·B·C(역사 기록: `deprecated`로 전환하거나 아카이브 표기 후 `active`). `review` 0건. `12-appendix/sources/*` 5건은 frontmatter 없음(브리프 §8이 규약 제외로 명시 — 정상) | 해당 파일 frontmatter(4단계 A6 기계 처리) |
| 12 | 카탈로그 등재 후보 | minor | 개별 문서가 제안했으나 바이블 §5.7 카탈로그에 없는 이름: 이벤트 `tenant.policies.changed`(05-api/04 미해결 3), 잡 종류 `JobKind.delete_collection`·워크플로우 `collection.delete.v1`(04-pipelines/19 §6.1, 05-api/04가 채택 전제로 기술), 경고 코드 `profile.gate_pending` 등 `ProfileValidationResult.warnings[].code`(05-api/04 미해결 9), `Profile.profile_hash`(readOnly, 05-api/04 미해결 8). 등재 여부가 정해지지 않으면 05-api/04·04-pipelines/19가 존재하지 않는 열거값을 참조하는 상태로 남는다 | 바이블 §5.7·§11.2(T1 트리아지), `03-contracts/12·15` |

박약(출현 1~2파일)으로만 기록하고 누락으로 보지 않은 항목: `TextFormat`(계약 00·11), `rag reprocess`/`rag reindex`(#10에 포함), E11(02-architecture/07에서 2회). 모두 정본 소유 문서에는 등장한다.

## 4. 4단계(교차 일관성)로 넘길 항목

계획 02 §2의 단계 코드(A1~A9 기계 처리, T1 트리아지, T2 전파)에 매핑한다.

| # | 항목 | 단계 | 입력 |
|--:|------|------|------|
| 1 | 용어집 v0.2.0 개정(누락 #1) — 바이블 §16 표 55행을 정의문으로 전개, 변경 행은 구 용어에 "→" 표기 | T2(편집) | 바이블 §16, 본 문서 §3 #1 |
| 2 | 상류 문서(비전 01·02·04, 요구사항 01·02·04) 동기화 범위 결정(누락 #2) — 기각 기술 언급 34곳의 문맥 판정 후 patch/minor | A3 → T1 → T2 | 본 문서 §3 #2, 계획 02 A3 |
| 3 | 테넌트 생성·API 키·버전·용량 엔드포인트의 바이블 §14 minor 발의 또는 `FR-MGT-01` 개정(누락 #3) | T1 | 05-api/04 미해결 1, 05-api/01 §3.1 예외 행, 02-architecture/01 미해결 12 |
| 4 | 추적 매트릭스 신설 여부와 형식(누락 #4) — 신설 시 문서 맵 개정과 함께 | T1(결정) → 스크립트 생성 | 본 문서 §2.3; `11-roadmap/02`의 FR→에픽 표를 시드로 기계 생성 가능 |
| 5 | 관리 API DTO 15종의 계약 지위(누락 #5) | T1 | 05-api/04 미해결 2, 05-api/01 §8 |
| 6 | README 갱신·`active` 전환(누락 #6) — A6 자동 전환 대상에서 제외하고 5단계 마감 편집 뒤 전환 | 5단계 | 본 문서 §2.1 |
| 7 | 브리프 §8 문서 맵 v1.2.2(누락 #7) + 바이블 §5.1 35번째 행(누락 #8) | T1(patch) | — |
| 8 | `NFR-I-02`·`NFR-REL-17` 정리(누락 #9) | A4(ID 접두) + 요구사항 소유자 | 00-vision/04 I-13, 09-operations/07 |
| 9 | CLI 정본 절 위치 결정(누락 #10) | T1 | 바이블 §12, 04-pipelines/01 §13, 04-pipelines/09 §8.5 |
| 10 | 제안서 A·B·C `status` 처리 규칙(누락 #11) | A6 | 브리프 §9.1 상태값 |
| 11 | 카탈로그 등재 후보 4건(누락 #12) | T1 | 트리아지 입력 03 해당 행 |
| 12 | 분량 규약(브리프 §9.11, 250~900행) 초과 실측 9건: 02-architecture/02(993)·05(978)·06(1,022)·07(909), 04-pipelines/01(1,111)·17(1,083), 08-evaluation/04(950), 09-operations/02(1,006), 11-roadmap/02(996). 계획 02 A5 목록은 10-development/06을 포함하고 08-evaluation/04를 빠뜨렸으므로 A5 목록을 이 실측으로 갱신 | A5 | 본 행 |
| 13 | 검증 스크립트화 — 본 문서 M2(정본 명칭 640개 출현 검사)·M3(FR/NFR 인용)·M5(§14 ↔ openapi)를 `tools/audit-docs.mjs`(계획 02 §2.1)에 A9로 편입해 4단계 종료 시 재실행 | A9 | 본 문서 §1 |

## 결정 사항 요약

- **결정:** 완전성 판정의 기준은 브리프 §8·§9와 바이블 §2~§16의 **이름**(타입·열거·이벤트·코드·메트릭·경로·테이블·명령)이며, 이름이 바이블 밖 어느 문서에도 없을 때만 "누락"으로 기록한다. 이 기준으로 바이블 정본 항목 약 640개는 **누락 0**, 박약 3이다.
- **결정:** 스키마 34/34, ADR 38/38(slug 일치), OpenAPI 경로 41/41, 필수 절·`schema_version`·ADR `version` 누락 0을 확인했다. 3단계의 "문서가 없다"는 종류의 누락은 없다.
- **결정:** 남은 누락은 모두 **문서 간 동기화**(용어집·상류 문서·README·문서 맵) 또는 **결정 대기**(테넌트 API, DTO 계약 지위, 추적 매트릭스, CLI 정본)이며 4단계 T1 트리아지와 5단계 마감으로 넘긴다. 이 문서는 어떤 문서도 고치지 않았다.
- **결정:** 심각도 blocker는 없다. 단, 누락 #3(`FR-MGT-01` Must 미충족)은 T1에서 요구사항 개정 또는 §14 개정 중 하나를 반드시 택해야 하며 결정 없이 4단계를 닫지 않는다.

## 미해결 이슈

1. **이름 단위 검색의 한계**: 이름이 등장해도 정의·규칙이 바이블 문장의 복제에 그친 문서가 있을 수 있다(예: 오류 코드 68개가 13-error-model에 표로만 있고 발생 조건은 각 파이프라인 문서마다 다르게 서술될 가능성). 의미 수준 대조는 4단계 T2의 몫이다.
2. **FR 인용률의 해석**: 브리프 §9가 문서별 FR 인용을 요구하지 않으므로 74% 미인용을 "규약 위반"으로 볼지 "추적 도구 부재"로 볼지는 T1 결정(§4 #4)에 달렸다. 이 문서는 후자로 기록했다.
3. **상류 문서의 기각 기술 언급 34곳**은 "기각했다"는 서술일 수도 있어 본 문서는 건수만 기록했다. 문맥 판정은 A3 출력으로 한다.
4. **UC 인용 6/20**: 유즈케이스가 설계 문서에서 거의 인용되지 않는 것이 설계 누락인지(유즈케이스가 요구하는 흐름을 어느 문서도 다루지 않음) 인용 습관의 문제인지(US가 96/104 인용되어 흐름은 다뤄짐) 표본 3건을 T2에서 확인한다.
5. **`openapi.yaml` `components` 140개와 `schemas/` 35개의 자동 대조**는 도구가 없어 수행하지 않았다(FR-API-04 동일 출처 원칙). 계획 02 A9에 검사 항목으로 추가할지 결정한다.
6. **`12-appendix/sources/`의 규약 제외**는 브리프 §8 한 줄에만 근거한다. 5단계에서 README 또는 브리프 §9에 "업스트림 사본은 frontmatter·절 규약 제외"를 명문화할지 결정한다.

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) §8 문서 맵, §9 문서 규약, §4 확정 결정, §7 품질 목표
- [설계 바이블](../02-architecture/00-design-bible.md) §3.3 ADR 목록, §5.1 계약 인벤토리, §5.7 열거·이벤트·오류 코드, §6 명명 규약, §7 프로파일, §10.3 강제 지점, §11.2 워크플로우, §12 모듈 맵, §13 저장소, §14 API 표면, §16 용어 반영 사항
- [기능 요구사항](../01-requirements/01-functional-requirements.md), [비기능 요구사항](../01-requirements/02-non-functional-requirements.md)
- [용어집](../00-vision/03-glossary.md)
- [API 설계 가이드라인](../05-api/01-api-design-guidelines.md), [관리 API](../05-api/04-management-api.md), `05-api/openapi.yaml`
- [진행 보고서](00-progress-report.md) §3·§6, [4·5단계 실행 계획](02-phase4-5-plan.md) §2, [바이블 개정 요청 통합 목록](03-bible-amendment-triage-input.md), [3단계 문서 원장](04-phase3-document-ledger.md)
- [ADR 인덱스](../06-adr/README.md)
