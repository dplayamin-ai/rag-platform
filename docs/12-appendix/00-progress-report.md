---
title: 진행 보고서 (Progress Report)
status: active
owner: architecture
version: 0.6.0
last_updated: 2026-09-23
depends_on: ["../00-vision/00-design-brief.md", "../02-architecture/00-design-bible.md", "../07-tech-landscape/00-summary-and-selection-matrix.md"]
---

# RAG Platform 설계 산출물 진행 보고서

## 목적

2026-09-18에 시작한 오픈소스 RAG Platform 설계 작업의 **현재까지 산출물, 핵심 결정, 남은 작업, 재개 방법**을 한 문서로 보고한다. 이 개정(0.4.0)은 2026-09-22 오후 3단계(핵심 설계 문서) 진행 중 상태를 기록한다.

## 범위

`C:\Workspaces\rag-platform\` 아래 생성된 모든 Markdown 산출물·JSON Schema·도구와 그 생성 과정. 코드는 아직 없다(설계 단계).

## 1. 요청과 해석

| 원 요구 | 해석 | 반영 위치 |
|---------|------|-----------|
| R1 HWPX·PDF·DOC·TXT·HTML 주소와 메타를 API로 수신 | Pull 모델 비동기 수집(`IngestRequest`), HWPX/HWP 1급 | 브리프 §2, 바이블 §4.2, 계약 01, 기술 지형 01·03 |
| R2 파싱·의미 청킹·임베딩에 오픈소스 최대 활용 | 어댑터 패턴, 22종 이상 파서 후보·청커·임베딩 모델 조사 후 선정 | 기술 지형 01~05, 선정 매트릭스 |
| R3 리트리벌 API로 Top-K 최적 | 3-way 하이브리드 → RRF → 크로스인코더 리랭킹 → 후처리 | 바이블 §8, 기술 지형 06·07 |
| R4 우아하고 모든 기술 수용 | 14개 플러그인 확장 지점 + 4개 프로파일(lite/standard/premium/korean-gov) | 바이블 §7, §12, 아키텍처 05 |
| R5 단계별 입출력 표준화 | 13개 스테이지 계약 + 21개 운영 계약 + 공통 봉투 + 열거 정본, JSON Schema 34개 | 바이블 §5, 계약 00~16, `schemas/` |
| R6 Top-K가 LLM에 최고 효과 | `ContextPack` + 렌더러 9종(Anthropic `search_result` 정본) + MCP | 바이블 §9, 계약 11, 기술 지형 10 |

## 2. 진행 방법

사람 개입 없이 다단계 멀티에이전트 워크플로우로 진행했다. 3단계부터는 문서마다 **작성 → 2렌즈 병렬 리뷰(앵커 준수 / 기술·문법·완전성) → 수정 → 검증 → 2차 수정**의 5단계를 거친다.

| 단계 | 내용 | 에이전트 수 | 상태 |
|------|------|------------|------|
| 0 | 설계 브리프(앵커 문서) 작성 | 수동 | 완료(v1.2.1) |
| 1 | 기술 지형 리서치 14개 영역 + 웹 사실 검증 + 종합 선정 매트릭스 | 43 | 완료 |
| 1b | 비전·원칙·용어집·범위, 기능/비기능 요구사항, 페르소나·유즈케이스, 사용자 스토리 | 24 | 완료 |
| 2 | 아키텍처 설계 경쟁(3안) → 3인 심사 → 설계 바이블 종합 → 3관점 리뷰·수정 | 11 | 완료(바이블 v1.2.0) |
| 3 | 계약 17종 + JSON Schema 34종, 아키텍처 9종, ADR 38종 + 인덱스, 파이프라인 19종, API 7종 + OpenAPI, 평가 6종, 운영 8종, 개발 8종, 로드맵 3종, 완전성 비평 | 아키텍처 51 완료; 나머지 진행 중 | **진행 중**(§7 참조) |
| 4 | 문서 간 교차 일관성 감사(ID·필드명·링크·바이블 개정 요청 처리) 및 수정 | 예정 | 대기 |
| 5 | 루트 README, CLAUDE.md, 문서 지도 최종화, 브리프 §8 갱신 | 예정 | 대기 |

## 3. 산출물 현황

### 3.0 3단계 완료 실측(2026-09-23, 마무리·ADR 워크플로우 종료 후)

기계 생성 원장([04-phase3-document-ledger.md](04-phase3-document-ledger.md))과 `tools/audit-docs.mjs` 결과 기준. **설계 문서 전부가 `active`(ADR은 `accepted`)** 이며 `review`로 남은 문서는 없다(`draft`는 부속 계획서·제안서 5건만).

| 디렉터리 | 문서 | 상태 | 비고 |
|----------|-----:|------|------|
| `00-vision/` | 5 | active | 브리프 v1.2.1 |
| `01-requirements/` | 4 | active | |
| `02-architecture/` | 10 | active | 바이블 v1.2.1 |
| `03-contracts/` + `schemas/` | 17 + 35 | active | 검증기 0 오류·0 경고(API 문서 작성으로 링크 경고 해소) |
| `04-pipelines/` | 19 | active | 02~11 경량 리뷰·수정 완료(10건 중 5건 심각 이슈 수정, 독립 검증 없음) |
| `05-api/` | 7 + `openapi.yaml` | active | 02·04·05 신규 작성. `openapi.yaml` 8,461행, 경로 36, 연산 51(리뷰 9건 반영) |
| `06-adr/` | 38 + README | accepted | 경량 사이클 완료, 인덱스 생성 |
| `07-tech-landscape/` | 15 | active | |
| `08-evaluation/` | 6 | active | 04는 심각 이슈 6건 수정(독립 검증 없음 → 표본 검증 1순위) |
| `09-operations/` | 8 | active | 8건 전부 경량 리뷰·수정 완료 |
| `10-development/` | 8 | active | 05 CI/CD 신규 작성 |
| `11-roadmap/` | 3 | active | 02·03 신규 작성 |
| `12-appendix/` | 10 + sources | 참고 | 진행 보고서, 완전성 검토([01](01-phase3-completeness-review.md), 누락 12건), 4·5단계 계획, 통합 목록, 원장, 6단계 계획, 제안서 A/B/C |
| **합계** | **151**(부속 15 포함) | | **99,572행**, 미해결 이슈 누적 480건(바이블 관련 200건) |

마무리 실행(`wf_7b7b22c8-830`) 결과: 문서 37건 처리(신규 6, 리뷰 사이클 31), 드롭 0, 경량 수정 20건(심각 이슈 합계 39건 수정, 독립 검증 없음), minor만 수정 17건, 미해결 이슈 126건 추가. 기계 감사(`--fix`) 결과: 깨진 링크 0, 900행 초과 비계약 문서 11건, 기각 명칭 문맥 검토 필요 123곳, 인용 무결성 6건, "확인 필요" 1,284곳(122문서), 자동 수정 1건.

### 3.1 세션 시작 시 실측(2026-09-23 오전, 마무리 전 — 참고용)

이전 세션(2026-09-22)이 남긴 보고(18:25 기준)와 실제 파일 상태를 대조한 결과다. 상태 열은 frontmatter `status` 실측값이며, "리뷰 사이클 필요"는 이전 세션의 리뷰·수정·검증 에이전트가 프록시 차단 또는 세션 종료로 중단되어 마무리가 필요함을 뜻한다(저널 `subagents/workflows/<run_id>/journal.jsonl` 분석 근거는 §7.2a).

| 디렉터리 | 문서 | 행 수 | 상태(실측) | 비고 |
|----------|-----:|------:|------|------|
| `00-vision/` | 5 | 2,726 | active 5 | 브리프 v1.2.1 |
| `01-requirements/` | 4 | 3,182 | active 4 | FR 217, NFR 184, 유즈케이스 20, 스토리 91 |
| `02-architecture/` | 10 | 9,549 | active 10 | 바이블 v1.2.1(1,999행) + 01~09 완료 |
| `03-contracts/` | 17/17 | 21,091 | active 17 | 계약 감사 완료. 기계 검증 **0 오류**, 경고 20건은 모두 미작성 API 문서 링크(05-api/02·04·05, 10-development/05) |
| `schemas/` | 35 | — | 완료 | 바이블 §5.1 인벤토리 34 + `schema-diff-report.schema.json`(14-schema-versioning 소유, 인벤토리 미등재 → 4단계에서 바이블 §5.1 반영) |
| `04-pipelines/` | 19/19 | 14,612 | active 15, review 4 | 02·06·07·11은 수정 에이전트 중단으로 review 잔존; 03·04·05·08·09·10은 수정 에이전트가 파일을 고친 뒤 중단되어 부분 반영 가능 → 10건 리뷰 사이클 필요 |
| `05-api/` | 4/7 | 3,248 | active 3, review 1 | 01(review, 수정 중단)·03(검증 중단)·06·07 완료. **02 수집 API·04 관리 API·05 MCP 서버 미작성**, `openapi.yaml` 미작성 |
| `06-adr/` | 38/38 | 7,773 | accepted 38 | 38건 작성 완료. 저널상 **리뷰는 0001~0013만 완료, 수정 단계는 한 건도 실행되지 않음**(이전 보고의 "리뷰·수정 거의 완료"는 과대 보고). `README.md` 인덱스 미작성 |
| `07-tech-landscape/` | 15 | 9,637 | active 15 | |
| `08-evaluation/` | 6/6 | 4,488 | active 6 | 02(2차 수정 중단)·03(검증 중단)·04·05(수정 중단 후 파일만 갱신) → 4건 리뷰 사이클 필요 |
| `09-operations/` | 8/8 | 6,319 | review 8 | 작성 완료. 01은 수정 중단, 02~08은 리뷰 에이전트 전부 실패 → 8건 리뷰 사이클 필요 |
| `10-development/` | 7/8 | 5,354 | active 1, review 6 | **05 CI/CD 미작성**. 04·06·07·08은 작성 에이전트가 파일을 저장한 뒤 중단(끝 절까지 완결 확인). 01(검증 중단)·02·03(리뷰 실패) → 7건 리뷰 사이클 필요 |
| `11-roadmap/` | 1/3 | 696 | active 1 | 01 완료. **02 에픽·백로그, 03 리스크 미작성** |
| `12-appendix/` | 4 + sources | 4,117 + 3,478 | reference | 진행 보고서, 제안서 A/B/C, `sources/otel-genai-semconv/`(업스트림 사본 4개, 규약 제외) |
| **합계** | **144**(설계 문서 129 + 부속 15) | **96,316** | | 12.2MB |

루트에 남아 있던 검증용 코드 블록 추출 파일 9개(`json_5~8.json`, `mermaid_0/1/3/4.mmd`, `yaml_2.yaml`; 04-pipelines/06의 코드 블록과 동일 내용)는 2026-09-23에 삭제했다.

## 4. 핵심 결정 요약

### 4.1 리서치·리뷰가 바로잡은 브리프 결정(v1.0 → v1.2)

| 결정 | 문제 | 개정 |
|------|------|------|
| D-18 PDF | PyMuPDF는 AGPL-3.0 인프로세스 링크 | pypdfium2 + pdftext(Apache/BSD), Docling 레이아웃 경로 유지 |
| D-18 HWP 5.0 | pyhwp는 AGPL이며 2020년 이후 정체, H2Orestart는 GPL(MIT 표기 오류) | Apache-2.0 Java 사이드카(hwplib + hwp2hwpx + hwpxlib) → HWPX 변환 → 단일 OWPML 어댑터. LibreOffice는 opt-in 폴백 |
| D-18 OCR | 엔진 우선순위 부재 | RapidOCR PP-OCRv5 korean(기본) / PaddleOCR server(GPU) / Tesseract(폴백) |
| D-16 서빙 | TEI·Infinity로는 BGE-M3 sparse 생산 불가 | vLLM pooling + TEI + 인프로세스. jina 계열(CC-BY-NC) 제외 |
| D-14 저장소 | Redis 8 삼중 라이선스, MinIO 아카이브·AGPL 전환 | Valkey, RustFS 또는 SeaweedFS |
| D-15 경량 프로파일 | Qdrant는 BM25를 계산하지 않고 한국어 형태소 분석이 없음 | 플랫폼 측 형태소 토큰화 + BM25 → `sparse_bm25` 벡터 |
| D-04 provenance | HWP·DOCX·HTML은 페이지·bbox가 없음 | `element_path`·문자 오프셋 필수, `page`/`bbox` nullable |
| D-06 ID | 결정적 청크 ID는 ULID로 표현 불가; 스코프 없는 `chunk_id` 물리 키는 테넌트 간 덮어쓰기 | 발급형 ULID, 콘텐츠 파생 BLAKE3, 물리 키 `record_id`는 테넌트·컬렉션·문서·세대 합성 |
| D-07 후처리 | 순서 오류로 부모 중복 재발 | `relevance_gate → dedup → mmr → parent_expand → dedup → …`, `reorder`·`citation_align`은 `pack` 내부 |
| D-02 라이선스 | LGPL·SSPL·모델 라이선스 규칙 공백 | 등급표 A/B/C/D/X + CI 게이트 + `model_license_ack` |
| D-17 오케스트레이션 | 워크플로우 정의 재사용 방식 불명확 | 오케스트레이터 중립 `PipelineContext`, 비내구 `LocalRunner`, Temporal은 실행기 |

### 4.2 개방 결정 해결(O-01~O-10)

RRF k=60 → convex 2단계(O-01), BGE-M3 sparse + lexical 유지(O-02), GraphRAG 외부 플러그인/RAPTOR 코어 옵션(O-03), late interaction 별도 슬롯(O-04), LLM 보강 기본 끔(O-05), 브로커 없는 아웃박스 + CloudEvents(O-06), HWP 5.0 Java 사이드카(O-07), RapidOCR(O-08), 자식 512/부모 2048 토큰(O-09), REST + SSE + MCP, gRPC 미제공(O-10). 상세는 바이블 §3.2, ADR 0001~0038.

### 4.3 3단계에서 내린 운영 결정(2026-09-22)

- **문서 맵 개정 v1.2.1**: 바이블 §5.1의 운영 계약 18종(`CollectionSpec`·`Profile`·`PluginMeta`·`Capabilities`·`StagePolicy`·`TieringPolicy`·`EgressPolicy` / `EvalDataset`·`EvalRun`·`EvalReport`·`FeedbackEvent`·`UserDictEntry`·`ConvertRequest`·`ConvertResponse`)은 문서 맵에 소유 문서가 없었다 → `03-contracts/15-collection-profile-and-policy-contracts.md`, `16-eval-feedback-and-sidecar-contracts.md` 신설.
- **공용 스키마 소유**: `schemas/common-types.schema.json`(§5.3 공용 타입 + Block·Chunk 등 + §5.7 열거 전부)은 `03-contracts/00`만 수정한다. 다른 계약은 `urn:rag:schema:common-types:1#/$defs/<Type>`로 참조만 한다.
- **`$id` 형식**은 바이블 §6.4 `urn:rag:schema:{kebab}:{major}`(이전 스크립트의 `https://rag-platform.dev/...` 폐기).
- **바이블은 절 단위로 읽는다**: 258KB라 에이전트가 전체를 읽지 못하므로 문서별 "읽을 절" 힌트 표를 스크립트에 두었다(`tools/phase3/wf-head.js` `HINTS`).
- 루트에 있던 OpenTelemetry GenAI semconv 원문 4개는 `docs/12-appendix/sources/otel-genai-semconv/`로 이동(README에 출처·규약 제외 명시).

## 5. 주요 발견(리서치)

1. HWP 생태계는 취약하다(python-hwpx Alpha·단일 메인테이너). 상한 고정과 계약 테스트 기반 pin-and-bump 필수.
2. 브리프 초안에 라이선스 지뢰 다수(PyMuPDF·pyhwp·MinIO AGPL, H2Orestart GPL, Redis 8, jina·SPLADE-v3 CC-BY-NC). 모두 개정.
3. 한국어 문서 수준 골든셋이 없다. 평가 하네스를 M1로 앞당겨야 한다.
4. BGE-M3 sparse는 TEI/Infinity로 서빙할 수 없다(vLLM pooling 필요).
5. MCP 스펙(2026-07-28)이 세션을 제거했으므로 페이지네이션은 커서 기반.
6. Anthropic RAG GA 경로는 `search_result` 블록이며 인용은 구조화 출력과 병용 불가.

## 6. 알려진 이슈

| 이슈 | 영향 | 처리 계획 |
|------|------|-----------|
| 아키텍처 01~09가 남긴 바이블 개정 요청 17건(§2.2 C4 `Rel(api, s3)` 누락, §14 테넌트 생성 API 부재, §4.1 `StageContext.plan`·`artifacts` 제안, §12 `rag_platform.settings` 모듈, §13.3 압축 규약 미정(U-4), §11.4 사가 A-6 표현, 질의 측 확장 지점 시그니처 02↔05 불일치, `orchestration/stage_shell.py`↔`context.py`, O-11·O-12 후보 등) | 문서 간 불일치 | 4단계에서 바이블 patch/minor 일괄 처리. 원문: `tools/phase3/results/architecture.json` `openIssues` |
| 아키텍처 02(993행)·06(1,022행)이 브리프 §9.11 상한(900행) 초과 | 규약 위반 | 4단계에서 절 이관(설정 모델 → 09-operations/02 등) |
| 리뷰를 통과해 수정 단계를 거치지 않은 문서는 `status: review`로 남음 | frontmatter 불일치 | 마무리 스크립트의 리뷰 사이클이 이슈 0인 문서를 `active`로 전환. 잔여분은 4단계에서 일괄 처리 |
| 이전 세션 보고와 실제 파일 상태 불일치(ADR "리뷰·수정 거의 완료" → 실제 수정 0건; `05-api`·`09~11` 대부분 미완) | 진행률 과대 보고 | 2026-09-23 저널 실측으로 §3·§7.2a 정정. 이후 보고는 반드시 frontmatter `status`와 저널을 근거로 작성 |
| `schemas/schema-diff-report.schema.json`이 바이블 §5.1 인벤토리에 없음(검증기 INFO) | 인벤토리 불일치 | 4단계에서 바이블 §5.1에 추가(14-schema-versioning 소유) |
| ADR 8건의 frontmatter `version` 누락 | 규약 위반 | 해결: ADR 경량 사이클에서 추가(2026-09-23) |
| 완전성 검토([01](01-phase3-completeness-review.md)) 누락 12건 — major 6: 용어집이 바이블 §16 개정 55행 미반영, 비전·요구사항 문서가 브리프·바이블 v1.2 개정 미동기화, `FR-MGT-01` 테넌트 API가 바이블 §14·openapi에 없음, FR 217건 중 74%가 설계 문서에서 미인용(추적 매트릭스 부재), 관리 API DTO 15종의 계약 지위 미정, README 상태 불일치(해결). minor 6: 브리프 §8 문서 맵·바이블 §5.1 인벤토리 불일치, `NFR-I-02`·`NFR-REL-17` 미정의 인용, CLI 정본 절 부재, 제안서 status, 카탈로그 등재 후보 4건 | 문서 세트 신뢰성 | 4단계 T1/T2 입력으로 편입([4·5단계 계획](02-phase4-5-plan.md) §7). 검토 문서 §4의 13개 인계 항목이 단계 코드(A/T/P)에 매핑됨 |
| 경량 모드 수정 43건(문서 37 + ADR 6, 심각 이슈 합계 39+7건)에 독립 검증 없음 | 잔존 결함 가능 | 4단계 D4-4 표본 검증(1순위: 08-evaluation/04 심각 6건, 04-pipelines/04 5건, 02 3건) |
| ID 접두 충돌(비전 `PB-xx`·`G-xx`, 원칙 `DP-xx`, 용어집 이슈 `G-xx`, 링크 키 `[P-xx]`) | 교차 참조 혼동 | 4단계 접두 정리 |
| npm 레지스트리가 사내 프록시(CA 오류)에 차단 → ajv 사용 불가 | 스키마 검증 도구 부재 | 의존성 없는 `tools/validate-contracts.mjs` 작성(2020-12 부분 구현: 문법·`$id`·`$ref`·열거 ↔ 바이블 §5.7·예시 ↔ 스키마·문서 구조) |
| 프록시가 에이전트 API 호출을 간헐 차단 | 워크플로우 중단 | `resumeFromRunId` 재개(완료 에이전트는 캐시 재생) |

## 7. 3단계 진행 상세와 재개 방법

### 7.1 도구

| 파일 | 역할 |
|------|------|
| `tools/phase3/wf-phase3.js` | 3단계 워크플로우 스크립트(단일 파일). `args.group`으로 그룹 선택: `contracts`(T0 00·13·14 → T1 14종) / `architecture` / `adrs` / `contracts-audit` / `pipelines` / `api-eval` / `ops-dev-roadmap` / `openapi` / `critic`. `args.date`(기본 2026-09-22), `args.validator`(검증기 절대 경로) |
| `tools/phase3/wf-head.js`, `wf-tail.js`, `build-wf.mjs`, `wf-phase3-v1-orig.js` | 스크립트 조립 소스(프롬프트·힌트 표·처리 함수 / 그룹 디스패치 / 빌더 / 이전 세션 원본 — 개요 40여 곳을 바이블 v1.2 기준으로 패치) |
| `tools/validate-contracts.mjs` | 계약 기계 검증기: `node tools/validate-contracts.mjs --root C:\Workspaces\rag-platform [--json out.json]` |
| `tools/phase3/results/*.json` | 그룹별 워크플로우 결과(문서별 리뷰 결과·미해결 이슈) |
| `tools/phase3/wf-finish-tail.js` → `wf-phase3-finish.js` | 2026-09-23 마무리 스크립트. 조립: `node -e` 로 `wf-phase3.js`의 `// ---- ADRs` 마커 이전 행(프롬프트·스키마·`WAVE_B` 개요)과 `wf-finish-tail.js`를 이어 붙인다. 실행: `Workflow({scriptPath: tools/phase3/wf-phase3-finish.js, args: {date, validator}})`. 대상 문서 목록은 tail 상단 `FULL`/`CYCLE_API`/`CYCLE_REST` 배열 |
| `tools/usage-report.mjs` → `PAYMENT.MD`(루트) | 세션 트랜스크립트에서 에이전트별 토큰(입력·캐시 쓰기·캐시 읽기·출력)과 수행 시간을 집계. 워크플로우 종료 후 `node tools/usage-report.mjs --out PAYMENT.MD`로 갱신 |

### 7.2 2026-09-22 실행 기록

| 그룹 | Run ID | 상태(18:25) | 비고 |
|------|--------|------|------|
| `architecture` | `wf_6d211baa-983` | **완료** | 51 에이전트, 12.3M 토큰, 2시간 3분, 문서 9/9, 드롭 0 |
| `contracts` | `wf_aae863e5-fec` | **완료**(18:35) | 88 에이전트, 26.2M 토큰, 4시간 58분. 17/17 active(1차 검증 통과 14, 2차 수정 3), 드롭 0, 심각 이슈 114건 수정, 미해결 이슈 119건(바이블 개정 요청 38건 — `results/contracts.json`) |
| `adrs` | `wf_f8852269-0c1` | 마무리 중 | 38건 accepted, 리뷰·수정 거의 완료, 인덱스 README 생성 대기 |
| `pipelines` | `wf_02322627-3eb` | 1차 완료(19:58) → 재개 중 | 91 에이전트, 26.7M 토큰, 4시간 14분. 19/19 작성(620~1,112행), 심각 이슈 195건. 1차 검증 통과 9, 2차 수정 3, **수정 에이전트 프록시 차단 7**(02·03·04·05·06·07·11) → `resumeFromRunId`로 재개(실패한 수정 → 검증 → 2차 수정 체인 재실행). 미해결 이슈 186건(바이블 개정 요청 45건 — `results/pipelines-pass1.json`) |
| `api-eval` | `wf_7bfc9aa6-c62` | 진행 중 | 18:30 착수. 기반 05-api/01·08-evaluation/01 → 나머지 11개 |
| `ops-dev-roadmap` | `wf_18a2a477-09d` | 진행 중 | 18:30 착수. 기반 09-operations/01·10-development/01·11-roadmap/01 → 나머지 16개 |
| `contracts-audit` | `wf_8890c66f-daf` | **완료**(20:20, 재개 포함) | 32 에이전트(+재개 6), 9.0M 토큰, 76분 + 24분. 기계 검증 3→0 오류; 의미 감사 이슈 69건·정본 결정 47건(`results/contracts-audit.json`); 파일별 수정 27건 완료(1차에서 프록시 차단된 6건은 재개로 완료). **최종 검증: 35 스키마·17 문서 0 오류·29 경고**(모두 미작성 문서 링크). 계약 17/17 active. 감사 중 **바이블 1.2.1 patch**(§7.3 YAML 예시 `security.tiering` 정합, §5.6 게이트 값 형식, §5.7 경고 코드 행 분리; 열거·철자 변경 없음) |
| `openapi`, `critic` | — | 대기 | `api-eval` 완료 후 `openapi`, 전 그룹 완료 후 `critic` |

12:55~18:25 사이 세션 컨텍스트가 여러 번 소진되어 진행 상태를 이 문서에 저장했다(15:50, 17:15, 18:25). 토큰·시간 집계는 루트 `PAYMENT.MD`(`tools/usage-report.mjs`로 재생성). 워크플로우는 세션 종료 시 함께 중단될 수 있으므로 새 세션은 §7.3의 1번(파일 상태 확인)부터 시작한다.

세션 스크래치패드(`%LOCALAPPDATA%\Temp\claude\C--Workspaces-rag-platform\dd0ede14-9151-48af-9821-b4079efd2595\`)의 `subagents\workflows\<run_id>\journal.jsonl`에 에이전트별 반환값이 있다.

### 7.2a 2026-09-23 실측과 마무리 실행

이전 세션의 워크플로우 `adrs`·`pipelines`(재개분)·`api-eval`·`ops-dev-roadmap`은 세션 종료와 함께 중단되었다. 저널(`dd0ede14-…/subagents/workflows/<run_id>/journal.jsonl`)의 `started/result/failed` 레코드를 문서·단계별로 집계한 결과:

| 그룹 | Run ID | 저널 실측 | 남은 작업 |
|------|--------|-----------|-----------|
| `adrs` | `wf_f8852269-0c1` | 작성 38/38 완료. 리뷰(anchor·tech) 완료 13건(0001~0013), 진행 중 끊김 3건, 미착수 22건. **수정·검증 0건**, 인덱스 미착수 | 38건 전부 리뷰 → 수정 → 검증 사이클 + `README.md` |
| `pipelines`(재개) | `wf_02322627-3eb` | 재개 시 스크립트가 재조립되어 프롬프트가 바뀌었고, 이미 검증된 08~19까지 리뷰가 다시 실행됨. 마지막 수정 에이전트 실패: 02·03·04·05·06·07·08·09·10·11 | 10건 리뷰 사이클(12~19는 1차 검증 완료 상태로 유지) |
| `api-eval` | `wf_7bfc9aa6-c62` | 52 에이전트(결과 43, 실패 9). 05-api/02·04·05 작성 실패, 01 수정 실패, 03 검증 실패; 08-evaluation/02 2차 수정 실패, 03 검증 실패, 04·05 수정 실패(파일은 갱신됨) | 작성 3건, 리뷰 사이클 6건, 이후 `openapi` |
| `ops-dev-roadmap` | `wf_18a2a477-09d` | 48 에이전트(결과 20, 실패 28). 09-operations 02~08 리뷰 전부 실패, 01 수정 실패; 10-development 04·06·07·08 작성 에이전트는 파일을 저장한 뒤 실패, 05 미작성, 01 검증 실패, 02·03 리뷰 실패; 11-roadmap 02·03 미작성 | 작성 3건, 리뷰 사이클 15건 |

마무리 실행(2026-09-23, Run ID `wf_94f7a864-1a2`, 세션 `191997a7-…`): `tools/phase3/wf-finish-tail.js`를 작성하고 `wf-phase3.js`의 앞부분(프롬프트·스키마·문서 개요, 1~394행)에 이어 붙여 `tools/phase3/wf-phase3-finish.js`를 조립했다(조립 명령은 §7.1). 이 스크립트는 단일 실행으로 (A) 누락 6건 작성 ∥ (B) 미완 31건 리뷰→수정→검증→2차 수정(리뷰 이슈 0이면 `status: active`로 전환) ∥ (C) ADR 38건 리뷰 사이클 + 인덱스 → (D) API 문서 완료 후 `openapi.yaml` → (E) 전체 완료 후 완전성 비평(`12-appendix/01-phase3-completeness-review.md`)을 수행한다. 리뷰 프롬프트에는 "이전 세션의 부분 수정 가능성"과 "ADR은 MADR 구조·status accepted 유지" 주의를 추가했다.

**중단(2026-09-23)**: 사용자 요청(ADR 리뷰의 토큰 비용 우려, 상황 보고 작성)으로 실행 7.5분 만에 `TaskStop`으로 중단했다. 시작된 에이전트 6개(작성 5: 05-api/02·04·05, 10-development/05, 11-roadmap/02; ADR 목록 1) 중 결과를 반환한 것은 없고 파일도 생성되지 않았다. 소모 토큰 57.8M(캐시 쓰기 13.4M, 출력 0.08M) — 에이전트 1개가 앵커 문서(브리프·바이블 절·계약 개요)를 읽는 데 약 7~10M 토큰이 든다는 단가 근거로 쓸 수 있다. 재개를 위해 스크립트에 `args.adrs === false`이면 ADR 사이클을 생략하는 옵션을 추가했다.

| 남은 작업 단위 | 에이전트 수(예상) | 토큰(예상, 에이전트당 7~10M) |
|----------------|------------------:|------------------------------:|
| 누락 6건 작성(작성·리뷰 2·수정·검증·2차 수정) | 약 30 | 0.2~0.3B |
| 미완 31건 리뷰 사이클(리뷰 2·수정·검증·2차 수정) | 약 120 | 0.8~1.2B |
| OpenAPI 조립·리뷰·수정 + 완전성 비평 | 4 | 0.03~0.05B |
| ADR 38건 리뷰 사이클 + 인덱스(보류) | 약 150 | 1.0~1.5B |

재개 명령: `Workflow({scriptPath: "C:\\Workspaces\\rag-platform\\tools\\phase3\\wf-phase3-finish.js", args: {group: "finish", date: "<오늘>", validator: "<절대경로>", adrs: false, fast: true}})`. ADR까지 포함하려면 `adrs` 키를 생략한다. `fast: true`(경량 모드, `tools/phase3/patch-fast-mode.mjs`로 추가)는 문서당 리뷰어를 2명에서 1명(앵커·기술 통합, effort medium)으로 줄이고 검증·2차 수정 단계를 생략한다(수정 에이전트가 자체 재확인). 표준 모드 대비 에이전트 수 약 55%, 토큰 약 50% 절감이 목표이며, 그 대가로 수정 결과가 독립 검증되지 않으므로 4단계 교차 감사에서 표본 검증한다.

**재개(2026-09-23, Run ID `wf_7b7b22c8-830`, 세션 `191997a7-…`)**: 사용자 지시 "ADR 제외, 리뷰는 빠르게"에 따라 `adrs: false, fast: true`로 실행했다. 범위: 누락 6건 작성 → 경량 리뷰·수정, 미완 31건 경량 리뷰·수정, `openapi.yaml`, 완전성 비평.

**마무리 실행 결과(완료 2026-09-23, 2시간 52분, 에이전트 84, 실패 0, 363.7M 토큰 = 에이전트당 4.3M)**: 신규 6건(05-api/02·04·05, 10-development/05, 11-roadmap/02·03) 작성·리뷰·수정, 리뷰 사이클 31건 완료, 드롭 0. 결과 분포: 심각 이슈 포함 경량 수정 20건(합계 39건), minor만 수정 17건. `openapi.yaml` 조립(51 연산) → 리뷰 9건 → 수정. 완전성 비평 → [01-phase3-completeness-review.md](01-phase3-completeness-review.md)(누락 12건, 문서 149·스키마 35·ADR 38 확인). 결과: `tools/phase3/results/finish.json`. **3단계 종료.**

**ADR 경량 사이클(2026-09-23, Run ID `wf_6cfeebb9-60e`, 별도 워크플로우 `tools/phase3/wf-adr-fast.js`, 빌드 `build-adr-fast.mjs`)**: 사용자가 경량 리뷰를 선택하여 병행 실행했다. 이전 세션에서 리뷰가 끝난 0001~0013은 저널의 anchor·tech 리뷰 결과(총 175건: major 29, minor 146, blocker 0)를 `tools/phase3/results/adr-prereviews/NNNN.json`으로 병합해 **리뷰 없이 수정 에이전트만** 실행하고, 0014~0038은 통합 리뷰어 1명(effort medium) → 수정으로 처리한 뒤 `06-adr/README.md` 인덱스를 작성한다. 예상 에이전트 약 65개. ADR은 MADR 구조·`status: accepted`·`date`(결정일)를 유지하고, `version` 누락 8건은 수정 시 추가한다.

**ADR 경량 사이클 결과(완료 2026-09-23, 63분, 에이전트 62, 실패 0)**: 38건 전부 처리 — 이전 리뷰 재사용 수정 13(0001~0013), 리뷰 이슈 0 통과 2(0022·0026), minor만 수정 17, 심각 이슈 포함 경량 수정 6(0016·0021·0023·0028·0033 각 1건, 0031 2건; 독립 검증 없음 → 4단계 D4-4 표본 검증 우선 대상). `06-adr/README.md` 인덱스 생성(338행), `version` 누락 8건 해소, status 38건 모두 `accepted`. 결과: `tools/phase3/results/adr-fast.json`.

### 7.2b 3단계 기록 체계(2026-09-23 정비)

사용자 요구("4단계 전에 3단계 기록을 꼼꼼히")에 따라 기록을 **사람이 쓴 산문에 의존하지 않고 파일·결과 JSON에서 기계 생성**하도록 정비했다. 각 기록물과 재생성 명령:

| 기록물 | 내용 | 생성·갱신 |
|--------|------|-----------|
| [3단계 문서 원장](04-phase3-document-ledger.md) | 전 문서(146)의 행 수·status·version·갱신일·최종 리뷰 결과·심각 이슈 수·미해결 이슈 수·"확인 필요" 수·소유 스키마, 스키마 파일 ↔ 소유 문서 표 | `node tools/phase3/ledger.mjs --date <날짜>` (frontmatter + `tools/phase3/results/*.json`) |
| [바이블 개정 요청 통합 목록](03-bible-amendment-triage-input.md) | 결과 JSON의 미해결 이슈 전부(중복 제거 354건; 바이블 관련 141건은 바이블 절 순 정렬), 계약 감사 정본 결정 47건. 4단계 T1의 단일 입력 | 같은 명령으로 동시 생성 |
| 문서 기계 감사 보고 | A1 링크·A2 frontmatter·A3 열거 철자와 기각 명칭(문맥 판정 `likely_ok`)·A4 ID 접두 지도·A5 900행 초과·A6 review/draft 잔존·A7 인용 무결성(ADR/D/O/FR/NFR/US)·A8 "확인 필요" 집계·A9 스키마 인벤토리 | `node tools/audit-docs.mjs --json <out.json> --md <out.md> [--fix]` (`--fix`는 frontmatter version 보정과 결과 JSON상 완료 문서의 status→active만) |
| `tools/phase3/results/<group>.json` | 그룹별 워크플로우 반환값(문서별 리뷰 결과·미해결 이슈·정본 결정) | 워크플로우 종료 시 오케스트레이터가 저장(`finish.json`, `adr-fast.json` 예정) |
| `tools/phase3/results/adr-prereviews/NNNN.json` | 이전 세션 ADR 0001~0013의 리뷰 결과 원본(175건) | `node tools/phase3/build-adr-fast.mjs <journal>` |
| 저널 `~/.claude/projects/C--Workspaces-rag-platform/<session>/subagents/workflows/<run>/journal.jsonl` | 에이전트별 started/result/failed 원본. 세션·Run ID는 §7.2·§7.2a | 자동 |
| 루트 `PAYMENT.MD` | 세션·워크플로우·에이전트별 토큰(입력/캐시 쓰기/캐시 읽기/출력)·시간 | `node tools/usage-report.mjs --out PAYMENT.MD` |
| 본 보고서 §3·§7·§8 | 실측 요약과 실행 기록 | 오케스트레이터가 단계 종료마다 갱신(원장과 다르면 원장이 우선) |

2026-09-23 첫 실행 결과(마무리 워크플로우 진행 중 시점): 원장 146문서·98,007행, 결과 JSON에 리뷰 결과가 있는 문서 45(나머지는 결과 미저장 또는 1·1b·2단계); 감사 A1 깨진 링크는 대부분 미작성 `06-adr/README.md`(19+12 파일)이고, A3 기각 명칭 출현은 문맥 판정 후 4단계 P1 입력으로 넘긴다; A7에서 `NFR-REL-17`(09-operations/07이 인용, 요구사항 문서에 미정의) 1건 발견; A8 "확인 필요" 1,263곳(118문서) — 외부 사실 재확인 백로그로 4단계 범위 밖.

### 7.2c 단계 계획 문서

| 단계 | 계획 문서 | 요지 |
|------|-----------|------|
| 4·5 | [02-phase4-5-plan.md](02-phase4-5-plan.md) | 기계 감사 → Opus 바이블 트리아지 → Sonnet 전파·표본 검증 → 마감(README·CLAUDE.md). 29~34 에이전트, 0.22~0.32B |
| 6 | [05-phase6-implementation-kit-plan.md](05-phase6-implementation-kit-plan.md) | 구현 킷(골격·적합성 키트·표본 코퍼스·골든셋·WP 60~80개) + M1 lite 레퍼런스(HWPX·PDF 수집 → 하이브리드 검색 → 인용 ContextPack, MCP) → 공개. 80~115 에이전트, 0.29~0.48B, 3~5주. 사용자 결정(2026-09-23): "동작해야 신뢰한다" — 공개는 M1 동작 후 |

### 7.2d 4단계 실행 기록(2026-09-23)

사용자 지시: "4단계 진행, 단계 종료 시 진행 상태 갱신 후 5단계 진행". 결정 D4-1~D4-4는 계획서 제안값으로 확정.

| 단계 | 내용 | 결과 |
|------|------|------|
| A 기계 처리(LLM 없음) | `tools/phase4/rename-id-prefixes.mjs --apply`: 용어집 이슈 `G-xx`→`GL-xx`, 링크 키 `[P-xx]`→`[PL-xx]`, 바이블·계약·ADR의 용어집 인용 동시 전환(8파일 303곳; 비전 목표 `G-xx` 인용은 유지). 제안서 A/B/C `deprecated`, 4·5단계 계획 `active`. `tools/traceability.mjs` → [06-traceability-matrix.md](06-traceability-matrix.md)(FR 217 중 인용 56=26%, NFR 150 중 113=75%, UC 20 중 6, US 91 중 91; 미정의 인용 `NFR-REL-17`). `tools/audit-docs.mjs`에 A10(바이블 §14 ↔ openapi 연산 대조) 추가, 사전 감사 `tools/phase4/results/audit-pre.{json,md}` | 완료 |
| T1~P4 워크플로우 | `tools/phase4/wf-phase4.js`: T1 Opus 트리아지(200건 + 완전성 12건) → T2 Opus 바이블 개정·브리프 §8 갱신·전파 지시서([07](07-bible-amendment-triage-decisions.md), [08](08-propagation-directives.md)) → T3 Sonnet 스키마 동기화(계약 영향 시) → P1 Sonnet 묶음 전파(디렉터리별 4~6문서, 용어집 단독) → P2 900행 초과 9건 절 이관 → P3 경량 수정 표본 14건 검증·수정 → P4 검증기·감사 재실행과 잔여 수정, 미인용 FR 20건 표본 판정 | 실행 중 |

### 7.3 재개 절차(새 세션)

1. 파일 상태를 먼저 본다: `docs/03-contracts/*.md`의 `status`(review = 리뷰 통과·미수정 또는 리뷰 대기, active = 수정 완료), `schemas/*.json` 수, `docs/06-adr/README.md` 존재 여부, `docs/04-pipelines/*.md` 수. `node tools/validate-contracts.mjs --root C:\Workspaces\rag-platform`로 오류 수를 확인.
2. 중단된 그룹은 같은 세션이면 `Workflow({scriptPath: "tools/phase3/wf-phase3.js", resumeFromRunId, args: {group}})`로 재개(완료 에이전트는 캐시). 다른 세션이면 같은 `args`로 새로 실행 — 이미 `active`인 문서는 재작성되므로, 필요하면 `wf-tail.js`의 그룹 배열에서 완료 문서를 제외하고 `node tools/phase3/build-wf.mjs`로 재조립한다(`build-wf.mjs`는 같은 디렉터리의 조각을 읽는다).
3. 순서: `contracts`·`adrs` 완료 확인 → `contracts-audit`(기계 검증 → 의미 감사 3방향 → 파일별 수정 → 재검증) → `api-eval` ∥ `ops-dev-roadmap`(`pipelines`가 아직이면 함께) → `openapi` → `critic`(`docs/12-appendix/01-phase3-completeness-review.md` 생성).
4. 그룹이 끝날 때마다 결과 JSON을 `tools/phase3/results/<group>.json`에 저장하고 `openIssues` 중 바이블 개정 요청을 §6 표에 누적한다.
5. 4단계: 바이블 개정 요청 일괄 처리(§1.2 절차, 버전 1.2.x/1.3.0), ID 접두 정리, 링크·필드명·열거 grep 감사, `status: review` → `active`, 900행 초과 문서 절 이관. 5단계: 루트 `README.md`(한/영), `CLAUDE.md`, `docs/README.md` 확정, 브리프 §8 최종 갱신.

## 8. 통계

| 항목 | 값 |
|------|----|
| 생성 문서(3단계 종료, 2026-09-23) | 151개(설계 문서 136, 부속 15), 99,572행 + `openapi.yaml` 8,461행 |
| JSON Schema | 35(인벤토리 34 + 1) |
| 실행 에이전트(누적, 2026-09-23 PAYMENT.MD 재집계) | 769 — 1단계 72, 1b 24, 2단계 11, 3단계 계약 88·아키텍처 51·ADR 71·파이프라인 138·API·평가 52·운영·개발·로드맵 48·계약 감사 60, 마무리 중단 6·마무리 84·ADR 경량 62, 오케스트레이터 세션 2 |
| 토큰(2026-09-23 재집계, 전 세션 합산) | **7.28B** — 입력 1.38M, 캐시 쓰기 1.20B, 캐시 읽기 6.05B, 출력 30.2M. API 호출 46,011회, 도구 호출 35,282회. 상세는 루트 `PAYMENT.MD`(단가 미적용) |
| 경량 모드 실측 단가 | ADR 사이클 2.8M/에이전트, 마무리 4.3M/에이전트(3단계 표준 모드 7~10M 대비 절반 이하) |
| 소요 시간 | 1단계 3.7h, 1b 1.5h, 2단계 2.3h, 3단계 2026-09-22 13:37~20:20(그룹 병렬) + 2026-09-23 마무리 실행 |

## 결정 사항 요약

- 설계 브리프 v1.2.1과 설계 바이블 v1.2.0이 앵커. 우선순위: 브리프 > 바이블 > ADR > 개별 문서. 개별 문서가 바이블과 어긋나면 문서를 고치고, 바이블 오류는 "미해결 이슈"로 개정 요청만 남긴다(§1.2).
- 3단계 문서는 작성·2렌즈 리뷰·수정·검증·2차 수정을 거쳐 `status: active`가 된다. 계약·스키마는 `tools/validate-contracts.mjs`가 0 오류여야 한다.
- 워크플로우는 그룹 단위로 병렬 실행하고(CPU 8코어 → 워크플로우당 동시 에이전트 6), 결과 JSON을 `tools/phase3/results/`에 보존한다.

## 미해결 이슈

- §6 표 참조. 3단계 완료 후 완전성 비평(`critic`) 결과와 각 그룹 `openIssues`를 4단계 입력으로 통합한다.

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) · [설계 바이블](../02-architecture/00-design-bible.md) · [기술 지형 종합](../07-tech-landscape/00-summary-and-selection-matrix.md)
- [계약 개요](../03-contracts/00-contract-overview.md) · [시스템 개요](../02-architecture/01-system-overview.md)
- [설계 경쟁 제안서 A](design-proposals/proposal-A-operability-first.md) · [B](design-proposals/proposal-B-retrieval-quality-first.md) · [C](design-proposals/proposal-C-simplicity-and-extensibility-first.md)
