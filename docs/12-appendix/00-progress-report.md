---
title: 진행 보고서 (Progress Report)
status: active
owner: architecture
version: 0.7.0
last_updated: 2026-09-24
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
| `12-appendix/` | 10 + sources | 참고 | 진행 보고서, 완전성 검토([01](01-phase3-completeness-review.md), 누락 12건), 4·5단계 계획, 통합 목록, 원장, 6단계 계획, 제안서 A/B/C. (6단계 이후 06~10 추가: 추적성·트리아지 결정·전파 지시서·보류 검증 원장·[구현 설계 갭 원장](10-implementation-design-gaps.md)) |
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

### 3.2 6단계 코드 실측(2026-09-24 03:13, 6F-F5 커밋 `835feb2` 후)

`uv run pytest -q`·`uv run mypy src`·`uv run lint-imports`·`node tools/verify/check-headers.mjs`·`node tools/verify/gen-deferred-ledger.mjs` 실행 결과 기준. **M1 lite 코어(층 1)가 이 VDI에서 구현·검증 완료**됐다. 층 2(Docker)·2b(모델 가중치)·3(GPU)은 미검증이며 [보류 검증 원장](09-deferred-verification-ledger.md)과 루트 `HANDOFF.md`로 이관됐다.

| 항목 | 값 |
|------|----|
| `src/rag_platform/` | 224 파일, 40,819행(생성 계약 모델 `contracts/` 포함) |
| `tests/` | 55 파일, 14,891행(`adapters`·`api`·`contracts`·`e2e`·`mcp`·`retrieval`·`security`·`unit` 등) |
| 작업 패키지 `docs/13-implementation/wp/` | 21건 — WP-101~106(수집 전단), 201~203(청킹·보강), 301~303(임베딩·인덱스·수집 e2e), 401~405(검색 경로 + 리뷰 수정), 501~504(API·MCP·CLI·e2e + 리뷰 수정). 색인은 [13-implementation/README.md](../13-implementation/README.md) |
| pytest | **886 통과 · 27 xfail · 4 deselected**(`needs_docker`·`needs_model`) — xfail은 전부 계약 왕복(문서 예시 오류·중첩 nullable) |
| mypy strict | 224 파일 0 오류 |
| import-linter | 6 계약 유지(바이블 §12 계층 + 오케스트레이터 중립 + adapters-no-storage + contracts-pure + no-c-grade + testing 격리) |
| ruff check / format | 통과 / 301 파일 정렬 |
| 한국어 헤더 규칙 | 307 파일 위반 0 |
| 보류 검증 원장 | 7건(docker 2 · model 1 · gpu 1 · network 1 · 미분류 3; LF 정규화 후 재스캔에서 2건 추가 발견) |
| 표본 | 공공누리 제1유형 HWPX 3건 + 합성 1건(`samples/hwpx/`, `MANIFEST.json` sha256) |
| CLI | `uv run rag {ingest,query,serve,profile}` |

바이블 §12 모듈 맵 대비 구현 범위:

| 구분 | 모듈 |
|------|------|
| 구현·검증(lite) | `contracts`(생성), `sdk`, `storage`(file:// 아티팩트 저장소·Valkey 포트+인메모리), `plugins`, `profiles`(내장 5종), `orchestration/local`(`LocalRunner`), `pipelines/{ingest,query}`, `adapters/fetch`(fsspec·httpx), `adapters/parse`(포맷 판별·라우터·HWPX·TXT/MD/CSV·HTML·PDF 고속 경로), `adapters/normalize/korean`, `adapters/chunk`(구조 인식·표 행·recount), `adapters/enrich`(결정적 접두어·형태소 키워드·파생 메타), `adapters/embed`(`FakeEmbedder`·플랫폼 BM25 sparse; TEI·vLLM 골격), `adapters/index/qdrant`(로컬 모드·커밋 사가), `adapters/retrieve`(dense·sparse_bm25), `adapters/query`, `retrieval/{planner,filters,channels,fusion,hydrate,postprocess/*,pack/*}`, `render/{markdown,anthropic_search_result,citation_map}`, `security/security_context`, `api`(FastAPI, RFC 9457), `mcp`(커서 페이지네이션), `cli`, `korean`, `testing`(적합성 키트·대역) |
| 포트만/스텁 | `ledger`(포트만, PostgreSQL 미연결), `orchestration/{outbox,temporal}`, `adapters/{rerank,llm}`, `eval`, `telemetry`, `settings`, OpenSearch 채널, HWP5 사이드카·DOCX·OCR 파서 |
| 작성만(미검증) | `deploy/compose/compose.lite.yaml`(`needs_docker`), `.github/workflows/ci.yml`(GitHub Actions 미실행) |

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
| T1~P4 워크플로우 | `tools/phase4/wf-phase4.js`(Run `wf_9464fd89-d43`, 12:44 착수): T1 Opus 트리아지(200건 + 완전성 12건) → T2 Opus 바이블 개정·브리프 §8 갱신·전파 지시서([07](07-bible-amendment-triage-decisions.md), [08](08-propagation-directives.md)) → T3 Sonnet 스키마 동기화(계약 영향 시) → P1 Sonnet 묶음 전파(디렉터리별 4~6문서, 용어집 단독) → P2 900행 초과 9건 절 이관 → P3 경량 수정 표본 14건 검증·수정 → P4 검증기·감사 재실행과 잔여 수정, 미인용 FR 20건 표본 판정 | T1 완료(38분, 채택 patch 25·minor 19·major 0, 기각 10, 보류 12, 바이블 목표 1.3.0, 계약 영향 있음) → T2 이후 실행 중 |
| 병행 착수(13:35~) | 사용자 지시로 5단계와 6A를 4단계와 병행. 5단계 `tools/phase5/wf-phase5.js`(Run `wf_19c804c1-495`: README·CLAUDE.md 작성·리뷰), `schemas/README.md` 생성, `LICENSE`(Apache-2.0 원문)·`NOTICE`, **git 초기화 + 기준선 커밋**(246 파일). 6A `tools/phase6/wf-6a-scaffold.js`(uv 프로젝트·계약 생성기·코어 스텁·인메모리 대역·CI·HANDOFF·보류 원장). 겹침 대응: 4단계 종료 후 계약 생성기 재실행, S4의 CLAUDE.md 절 추가는 5단계 완료 뒤 도달. **5단계 완료 14:15**(README 252행·CLAUDE.md 220행, 리뷰 7건 반영, 에이전트 4). **6A 1차 실행(`wf_25dbfe1b-97e`)은 S1 완료 직후 중단**: 지시문의 단순화 계층(core·stages·workflows)이 바이블 §12 모듈 맵과 달랐음 → §12 경로·의존 방향을 그대로 인용하도록 S1·S2·S3 지시를 고쳐 **2차 실행 `wf_8eef8c02-a6c`**(14:20). 교훈: 코드 골격 지시에는 바이블 §12 경로를 문자 그대로 인용한다 | 4단계·6A 실행 중 |

### 7.2e 4단계 완료(2026-09-23 16:30, Run `wf_9464fd89-d43`, 3시간 35분, 에이전트 36, 실패 0)

| 단계 | 결과 |
|------|------|
| T1 트리아지(Opus) | 200건 판정: 채택 patch 31·minor 34, 문서 내부 지시 111, 보류 14, 기각 10 → 개정 항목 AM-01~44(patch 25·minor 19), 보류 AM-45~56, 기각 R-01~10. [07-bible-amendment-triage-decisions.md](07-bible-amendment-triage-decisions.md) |
| T2 바이블 개정(Opus) | 바이블 **1.3.0**(§1.2·§2.2·§3.2 O-11·O-12 등록·§3.3 ADR-0039·§4~§14 국소 개정, §5.1 35번째 행, 오류 코드 16종·`TenantStatus`·`JobKind.delete_collection`·`tenant.policies.changed`), 브리프 **1.2.2**(§8 문서 맵 실측 동기화; D-xx 개정 없음), 전파 지시서 93문서·525항목 [08-propagation-directives.md](08-propagation-directives.md). 결정: 추가형 개정 묶음은 ADR-0039, `schema_version`은 M1 전이라 1.0.0 유지 |
| T3 스키마 동기화(Sonnet) | 공용 타입 9종 승격·중복 $defs 제거, 오류 코드 84종, 개별 선택 필드 추가, 12개 계약 문서 스키마 블록 재동기화. 검증기 ERROR 1→0, WARN 2→0 |
| P1 전파(Sonnet 22묶음) | 93문서 반영, 용어집 v0.2.0(바이블 §16 55행 전개) |
| P2 분량 이관(Sonnet 3) | 초과 9건 전부 899~900행 이내(예: 02-architecture/06 §9 사이징 → 09-operations/04, 사가 상세 → 04-pipelines/19) |
| P3 표본 검증(Sonnet 7) | 경량 수정 문서 14건 리뷰 → **심각 이슈 0, minor 0**. 경량 모드 품질 우려 완화 |
| P4 잔여(Sonnet) | 검증기 0/0, 감사 A1·A2·A5 0, A3 87건 문맥 전수 검토(전부 감사기 오탐), A7 1(ADR-0040 제안 문맥, 허용), A10 4건은 감사기 조합 오탐 확인. 미인용 FR 20건 표본 판정(설계 갭 2건: `FR-NRM-09` 정규화 품질 지표↔격리 정책 연결 부재, `FR-PRS-19` 0바이트 문서 오류 코드 상충) |
| 게이트(오케스트레이터 재실행) | `validate-contracts` 0 오류·0 경고, `audit-docs` A1 0·A2 0·A5 0·A9 35/35, ADR 39건 파일 존재 |

남은 4단계 이슈(5·6단계로 이관): 감사기 A3 기각 명칭 휴리스틱 보강, 미인용 FR 140건 전수 판정, `FR-NRM-09`·`FR-PRS-19` 설계 결정, 4단계 중 6A 1차 실행이 남긴 CLAUDE.md §4 구 구조 서술(6A 2차 완료 후 갱신).

### 7.2f 6A 레퍼런스 골격 완료(2026-09-23 19:00, Run `wf_8eef8c02-a6c`, 2시간 20분, 에이전트 6, 실패 0, 약 1.9B 토큰)

| 단계 | 결과 |
|------|------|
| S1 기반(Opus) | 1차 실행의 구 구조 제거 후 바이블 §12 모듈 맵 35 패키지로 재구성. pyproject(uv, 3.12/3.13, ruff, mypy strict, pytest 마커 4종), import-linter 6계약(§12 계층 + 오케스트레이터 중립 + adapters-no-storage + contracts-pure + no-c-grade + testing 격리; 위반 탐지 실증), justfile·pre-commit·tools/dev.py. 72 테스트 |
| S2 계약(Sonnet) | `tools/contracts_gen.py`: urn `$ref` 재작성 후 datamodel-code-generator로 35 스키마 → 38 모듈(StrEnum, versioning.py 포함), 재생성 바이트 동일. 계약 예시 80건 픽스처 추출 → 왕복 테스트(xfail 40: nullable 필드 null 보존 미구현 → 6B 선행 과제). ADR-0004 해시 벡터 테스트 통과 |
| S3 코어(Sonnet) | sdk(stage 5멤버·context·policy·ports·hashing), storage(artifact_store file://·keys·valkey 포트), plugins/registry(14 확장 지점), profiles(loader·validate·builtin 5종), orchestration/local/runner(LocalRunner), pipelines/ingest, ledger/repo 포트, testing/doubles 4종(`# DEFERRED:` 6건). 220 테스트 |
| S4 인계(Sonnet) | `.github/workflows/ci.yml`(6 잡 + 수동 deferred 잡), `HANDOFF.md`, `tools/verify/{gen-deferred-ledger.mjs, run-deferred.sh/.ps1}`, [09-deferred-verification-ledger.md](09-deferred-verification-ledger.md) 첫 생성(6건) |
| S5 리뷰·수정 | 3건(심각 1: §12의 `contracts/versioning.py` 누락 → 생성기 확장으로 해결) |
| 게이트(오케스트레이터 재실행) | ruff 통과, mypy 148파일 0, import-linter 6/6, **pytest 298 통과·40 xfail**. 커밋 완료 |

미해결 이관: xfail 40건(6B 선행 수정), `compose.lite.yaml` 부재(6F), 바이블 §12 같은 층 내 의존(pipelines.query → retrieval·render 등)이 import-linter `|` 독립 해석과 충돌할 가능성(구현 시 계층 계약 조정 필요), CLAUDE.md §4 구 구조 서술(6B/6D 검증 단계에서 갱신). 이어서 헤더 주석 소급 적용(`wf-header-pass.js`) → 6B·6D(`wf-6bd.js`).

### 7.2g 6B·6D 완료(2026-09-23 22:10, Run `wf_0755d3ae-470`, 1시간 26분, 에이전트 8, 실패 0, 0.26B 토큰)

| 단계 | 결과 |
|------|------|
| S0 의존성 | python-hwpx·qdrant-client·fsspec·lxml·charset-normalizer·markdown-it-py·trafilatura·pypdfium2, extra `kiwi`(kiwipiepy 0.23.2 LGPL — Apache 버전 0.24 미출시, 라이선스 검토 이슈), dev respx. Windows 휠 전부 확보 |
| 6B 적합성 키트(Sonnet 3) | `testing/`: contract_roundtrip·idempotency·security_invariants·fuser_equivalence(골든 벡터)·litm_order·renderer_citation_roundtrip, 확장 지점 14종 적합성 기반 클래스, 프로파일 4종 로딩·`profile_hash` 안정성. 생성기에 `ContractModel` 베이스 추가(xfail 40 → 27; 잔여는 문서 예시 오류·중첩 nullable) |
| 6D HWPX(Opus) | `adapters/parse/hwpx_python_hwpx.py` + `owpml_adapter.py`. 공공누리 표본 3건(기재부·복지부·개인정보위) + 합성 1건, 테스트 28. 파서 문서 "확인 필요" 20곳 실측 갱신. **설계 갭 발견 11건**(예: `Figure.artifact` 필수 vs 크기 초과 시 생략 규칙 충돌, `StageContext.source_bytes` 포트 부재, Hancom 기본 `repeatHeader=1`로 header_inferred 판정 왜곡, `opf:title` 신뢰 정책, 장르·표 역할 휴리스틱 오탐) — `tools/phase6/results/6bd.json` d[0].issues |
| 6D Qdrant(Opus) | 로컬 모드 백엔드·필터 변환(tenant·acl 사전 필터 없으면 예외)·결정적 point_id·형태소 BM25 sparse, 테스트 12. 서버 모드는 `needs_docker`(Windows 바이너리 실행은 권한 정책으로 차단). 갭 8건(IndexBackend 포트 시그니처 ↔ 문서 13 불일치, 서버 RRF k=61 등가, ACL visible_set 정책 확인, analyzer_id 라벨) |
| 6D 임베더(Sonnet) | TEI·vLLM pooling 어댑터 골격(모의 HTTP), FakeEmbedder 플러그인, 테스트 31. 실 서버·모델 항목 7곳은 `needs_model`/`needs_docker` 보류 |
| 검증 | ruff·mypy(168)·import-linter 6/6·pytest **476 통과·27 xfail**, `tools/verify/check-headers.mjs` 신설(229파일 위반 0), 보류 원장 3건, CLAUDE.md §4·README 상태 갱신 |

토큰: 6A 2차 0.44B(초기 보고의 1.9B는 알림의 출력 토큰 필드를 오독한 값이며 PAYMENT.MD 기준으로 정정), 헤더 패스 0.06B, 6B·6D 0.26B → 6단계 누적 0.76B(검문선 1B 이하, 축소 없이 진행). 전체 누적 **9.74B**. 6E·6F는 "작업 패키지 우선 구현"(한 에이전트가 WP 문서를 쓰고 바로 구현·테스트)으로 합쳐 배치 F1~F5로 실행한다(`tools/phase6/wf-6f.js`, 배치마다 커밋).

### 7.2h 6E·6F 배치 F1~F5 완료(2026-09-23 18:48 → 2026-09-24 03:13, 5 Run, 에이전트 28, 실패 0, 1.82B 토큰)

6E(작업 패키지 작성)와 6F(M1 lite 구현)를 "WP 우선 구현"으로 합쳐 `tools/phase6/wf-6f.js --batch F1..F5`로 실행했다. 배치마다 구현 에이전트(Sonnet, WP 문서 작성 → 구현 → 테스트; 읽기 예산 = WP + 대상 파일 + 테스트 출력) → 검증 에이전트(ruff/format/mypy/lint-imports/pytest/check-headers/deferred 원장) → F4·F5는 Opus 보안·수식 리뷰 → Sonnet 수정 순서다. 배치 결과는 `tools/phase6/results/f1..f5.json`, 배치마다 커밋했다.

| 배치 | Run | 경과 | 에이전트 | 토큰 | 내용 | 게이트(누적 테스트) |
|------|-----|-----:|--------:|-----:|------|------|
| F1 수집 전단 | `wf_b7ec72fc-7e3` | 1h 13m | 7 | 0.41B | WP-101~106: fetch(fsspec·httpx, 허용 루트·`max_bytes`), 포맷 판별·파서 라우터, TXT/MD/CSV, HTML(trafilatura, 표 native 재구성), PDF 고속 경로(pypdfium2), 한국어 정규화(유니코드·공백·표 셀) | 636 통과 · 27 xfail(커밋 `bcedbb0`) |
| F2 청킹·보강 | `wf_9a81fe63-40d` | 49m | 4 | 0.16B | WP-201~203: 구조 인식 계층 청킹(512/2048/64, 결정적 `chunk_id`), 표 행 그룹·recount, 결정적 문맥 접두어·형태소 키워드·파생 메타 | 692 통과(`9ab5dae`) |
| F3 임베딩·인덕스 → 인덱스·수집 e2e | `wf_52b111c5-c82` | 1h 13m | 4 | 0.29B | WP-301~303: embed 스테이지(`FakeEmbedder` + 플랫폼 BM25 `sparse_bm25`), `IndexRecord` 변환·단일 백엔드 `IndexCommit` 사가, lite 수집 파이프라인 `LocalRunner` 종단 실행(HWPX 표본 3건) | 733 통과(`3a79118`) |
| F4 검색 경로 | `wf_a6cb70da-507` | 2h 38m | 7 | 0.55B | WP-401~404: 규칙 플래너·3층 필터(tenant/acl 사전 필터 필수), 병렬 채널(dense·sparse_bm25)·RRF(k=60, 가중 1:1:1, 변형 0.5)·hydrate(Qdrant payload), 후처리 `relevance_gate → dedup → mmr → parent_expand → dedup`, 패킹 `acl_recheck → budget_cut → reorder(litm) → citation_align`, 렌더러(markdown·anthropic `search_result`), 질의 파이프라인. **Opus 리뷰 13건(심각 6)** → WP-405: `acl_recheck` 삭제 플래그 우선·§10.2 OR 의미론·`tenant:*` allow 측 제거, 컬렉션 교집합 필터, 필터 값 검증(`plan.filter_field_forbidden`), `route=no_retrieval` 빈 CandidateSet, import-linter 계층 위반 5건 해소(순수 로직을 `korean/`로 이동) | 804 통과(`18b0ca9`) |
| F5 API·MCP·CLI·e2e | `wf_6681bb3d-290` | 2h 13m | 6 | 0.41B | WP-501~503: FastAPI 수집 접수·잡 조회·질의·렌더(RFC 9457 `problem+json`, `SecurityContext` 서버 주입, 결과 캐시 없음), MCP 서버(도구 3종, 커서 페이지네이션 `cursor_store`), `rag` CLI(ingest/query/serve/profile), 수집→질의→렌더 전 구간 e2e. **Opus 리뷰 10건(심각 3)** → WP-504: API 키 주체를 `service:{subject}`·`visible_set=[public]`로 고정(ADR-0027), `pack_id` 캐시에 주체 해시·TTL 600s 바인딩(불일치 시 404), MCP `search` 페이지를 렌더 순서가 아닌 `rank` 순으로 절단 | **886 통과 · 27 xfail**(`835feb2`) |

오케스트레이터 마무리(F5 후): `ruff format` 1건, 헤더 위반 1건(`tests/security/test_security_context.py` "구성" 항목) 수정 후 게이트 재통과. 6단계 누적 토큰 **2.58B**(6A 0.44B, 헤더 패스 0.06B, 6B·6D 0.26B, F1~F5 1.82B) — 검문선 1B를 넘었지만 배치별 소모가 계획(0.2~0.5B)과 같은 규모여서 축소 없이 완주했다. 전체 누적 **11.61B**(PAYMENT.MD 2026-09-24 03:10 재집계, 에이전트 861).

**설계 갭·후속 백로그**(다음 바이블 패치 입력, 전체 목록은 [구현 설계 갭 원장](10-implementation-design-gaps.md) — `tools/phase6/results/open-issues.json`에서 `gen-design-gaps.mjs`가 생성):

- 미해결 항목 **186건**(6B·6D 36 — 예: `Figure.artifact` 필수 vs 생략 규칙, `StageContext.source_bytes` 포트 부재, `IndexBackend` 포트 ↔ 문서 13 시그니처, 서버 RRF k=61 등가, Hancom `repeatHeader` 기본값; F1 36 · F2 28 · F3 17 · F4 36 · F5 33(매뉴얼 검증 6 포함) — 예: fetch의 `requires_lineage` 선언 vs 바이블 §4.1 문구, `canonical_json` 근사, 정책 해소 포트 부재). Opus 리뷰 발견 23건(F4 13·F5 10)은 WP-405·504에서 수정 완료.
- 계약 왕복 xfail 27건: 계약 문서 예시 오류(문서 수정 대상)와 중첩 nullable 보존(생성기 확장 대상)으로 분류해 처리.
- `kiwipiepy 0.23.2`(LGPL 정적 휠) 라이선스 등급 결정 — Apache 전환판(0.24) 출시 전까지 extra `kiwi`로 격리.
- 층 2·2b·3 검증 7건(원장), `compose.lite.yaml` 기동, GitHub Actions 첫 실행 — `HANDOFF.md` 절차로 다른 머신에서.
- 6C 미니 골든셋(표본 3건 기준 질의·`answer_spans` 초안, 사람 검수 필수), 6G 공개 준비(CONTRIBUTING·SECURITY, 내부 기록 분리)는 미착수.

### 7.3 재개 절차(새 세션)

1. 파일 상태를 먼저 본다: `docs/03-contracts/*.md`의 `status`(review = 리뷰 통과·미수정 또는 리뷰 대기, active = 수정 완료), `schemas/*.json` 수, `docs/06-adr/README.md` 존재 여부, `docs/04-pipelines/*.md` 수. `node tools/validate-contracts.mjs --root C:\Workspaces\rag-platform`로 오류 수를 확인.
2. 중단된 그룹은 같은 세션이면 `Workflow({scriptPath: "tools/phase3/wf-phase3.js", resumeFromRunId, args: {group}})`로 재개(완료 에이전트는 캐시). 다른 세션이면 같은 `args`로 새로 실행 — 이미 `active`인 문서는 재작성되므로, 필요하면 `wf-tail.js`의 그룹 배열에서 완료 문서를 제외하고 `node tools/phase3/build-wf.mjs`로 재조립한다(`build-wf.mjs`는 같은 디렉터리의 조각을 읽는다).
3. 순서: `contracts`·`adrs` 완료 확인 → `contracts-audit`(기계 검증 → 의미 감사 3방향 → 파일별 수정 → 재검증) → `api-eval` ∥ `ops-dev-roadmap`(`pipelines`가 아직이면 함께) → `openapi` → `critic`(`docs/12-appendix/01-phase3-completeness-review.md` 생성).
4. 그룹이 끝날 때마다 결과 JSON을 `tools/phase3/results/<group>.json`에 저장하고 `openIssues` 중 바이블 개정 요청을 §6 표에 누적한다.
5. 4단계: 바이블 개정 요청 일괄 처리(§1.2 절차, 버전 1.2.x/1.3.0), ID 접두 정리, 링크·필드명·열거 grep 감사, `status: review` → `active`, 900행 초과 문서 절 이관. 5단계: 루트 `README.md`(한/영), `CLAUDE.md`, `docs/README.md` 확정, 브리프 §8 최종 갱신.
6. 6단계(코드) 재개: `git log --oneline -10`으로 마지막 배치 커밋을 확인하고 `uv sync --all-extras --group dev` → `uv run pytest -q`(886 통과·27 xfail 기대) → `uv run mypy src` → `uv run lint-imports` → `node tools/verify/check-headers.mjs`로 게이트를 재현한다. 새 구현은 `docs/13-implementation/wp/`에 WP 문서를 먼저 쓰고(`tools/phase6/wf-6f.js`의 배치 정의를 본보기로) 구현·테스트를 같은 커밋에 넣는다. Docker·모델·GPU가 있는 머신이면 `HANDOFF.md` 첫 30분 절차 → `tools/verify/run-deferred.sh`로 [보류 원장](09-deferred-verification-ledger.md) 5건을 먼저 검증한다.

## 8. 통계

| 항목 | 값 |
|------|----|
| 생성 문서(3단계 종료, 2026-09-23) | 151개(설계 문서 136, 부속 15), 99,572행 + `openapi.yaml` 8,461행 |
| JSON Schema | 35(인벤토리 34 + 1) |
| 실행 에이전트(누적, 2026-09-23 PAYMENT.MD 재집계) | 769 — 1단계 72, 1b 24, 2단계 11, 3단계 계약 88·아키텍처 51·ADR 71·파이프라인 138·API·평가 52·운영·개발·로드맵 48·계약 감사 60, 마무리 중단 6·마무리 84·ADR 경량 62, 오케스트레이터 세션 2 |
| 토큰(2026-09-23 재집계, 전 세션 합산) | **7.28B** — 입력 1.38M, 캐시 쓰기 1.20B, 캐시 읽기 6.05B, 출력 30.2M. API 호출 46,011회, 도구 호출 35,282회. 상세는 루트 `PAYMENT.MD`(단가 미적용) |
| 경량 모드 실측 단가 | ADR 사이클 2.8M/에이전트, 마무리 4.3M/에이전트(3단계 표준 모드 7~10M 대비 절반 이하) |
| **4단계 실측(2026-09-23)** | **1.46B 토큰**, 에이전트 36(평균 40M) — 계획 추정 0.18~0.25B의 약 6배. 원인: P1 전파 22묶음이 지시서(525항목)·바이블 절·대상 문서를 광범위하게 읽고 Edit를 반복(캐시 쓰기 지배). 5단계 32M(4 에이전트). 6A 2차는 진행 중 0.4B(5 에이전트; uv·pytest 실행 루프가 문맥을 키움). 누적 **9.33B** |
| 6단계 예산 규율(재설정) | 구현 에이전트는 **작업 패키지(WP) 문서 + 직접 편집 파일 + 테스트 출력만** 읽고 바이블·설계 문서를 열지 않는다(WP가 필요한 발췌를 담는다). 한 에이전트당 파일 3개 이하, 테스트 재실행 최대 3회. 6B+6D 종료 시 소모를 재측정해 1B 초과면 6E는 코어 WP만, 6F는 F1~F5 최소 경로로 축소. 재예측: 6A 잔여 0.1B, 헤더 패스 0.1B, 6B 0.2B, 6D 0.2B, 6E 0.3B, 6C 0.1B, 6F 1.0~1.5B → **추가 2.0~2.5B**(공시가 기준 약 $2,500~3,500) |
| **6단계 실측(2026-09-24 03:10)** | 6A 0.44B(6) · 헤더 패스 0.06B(5) · 6B·6D 0.26B(8) · F1 0.41B(7) · F2 0.16B(4) · F3 0.29B(4) · F4 0.55B(7) · F5 0.41B(6) = **2.58B**, 에이전트 47(괄호). 구현 에이전트 평균 70~110M(uv·pytest 실행 루프가 캐시 읽기를 키움), 검증 에이전트 120~150M, Opus 리뷰 2~10M |
| **전체 누적(2026-09-24)** | **11.61B** 토큰, 에이전트 861, API 호출 64,722, 도구 호출 46,257(입력 1.42M · 캐시 쓰기 1.27B · 캐시 읽기 10.30B · 출력 39.6M). 상세 `PAYMENT.MD` |
| 코드(6F-F5 후) | `src/` 224 파일 40,819행 · `tests/` 55 파일 14,891행 · WP 21건 · pytest 886 통과/27 xfail · 보류 7건 |
| 소요 시간 | 1단계 3.7h, 1b 1.5h, 2단계 2.3h, 3단계 2026-09-22 13:37~20:20(그룹 병렬) + 2026-09-23 마무리 실행, 4단계 3h 35m, 5단계 26m, 6A 2h 21m, 헤더 패스 21m, 6B·6D 1h 26m, 6F F1~F5 8h 6m(2026-09-23 18:48 → 09-24 03:02) |

## 결정 사항 요약

- 설계 브리프 v1.2.1과 설계 바이블 v1.2.0이 앵커. 우선순위: 브리프 > 바이블 > ADR > 개별 문서. 개별 문서가 바이블과 어긋나면 문서를 고치고, 바이블 오류는 "미해결 이슈"로 개정 요청만 남긴다(§1.2).
- 3단계 문서는 작성·2렌즈 리뷰·수정·검증·2차 수정을 거쳐 `status: active`가 된다. 계약·스키마는 `tools/validate-contracts.mjs`가 0 오류여야 한다.
- 워크플로우는 그룹 단위로 병렬 실행하고(CPU 8코어 → 워크플로우당 동시 에이전트 6), 결과 JSON을 `tools/phase3/results/`에 보존한다.
- 6단계는 3층 검증(층 1 VDI 검증, 층 2·2b·3 대역+마커로 작성 후 보류 원장 이관, 모델 가중치 다운로드 금지)으로 진행했고, 6E·6F는 "WP 우선 구현"(한 에이전트가 WP 문서 → 구현 → 테스트)으로 합쳐 배치 F1~F5·커밋 단위로 실행했다. 모든 코드 파일은 한국어 설명 헤더 규칙(`tools/phase6/CODE-HEADER-RULE.md`)을 따르고 `check-headers.mjs`가 게이트다.
- 구현 중 발견한 설계 갭은 코드가 바이블을 앞서 바꾸지 않고 WP `## 미해결 이슈`와 결과 JSON에 기록해 다음 바이블 패치 입력으로 모은다(§7.2h).

## 미해결 이슈

- §6 표 참조. 3단계 완료 후 완전성 비평(`critic`) 결과와 각 그룹 `openIssues`를 4단계 입력으로 통합한다.
- 6단계 후속 백로그는 §7.2h 끝의 목록(설계 갭 186건 → [10-implementation-design-gaps.md](10-implementation-design-gaps.md), xfail 27건, 보류 검증 7건, kiwipiepy 라이선스, 6C·6G 미착수)을 따른다.

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) · [설계 바이블](../02-architecture/00-design-bible.md) · [기술 지형 종합](../07-tech-landscape/00-summary-and-selection-matrix.md)
- [계약 개요](../03-contracts/00-contract-overview.md) · [시스템 개요](../02-architecture/01-system-overview.md)
- [설계 경쟁 제안서 A](design-proposals/proposal-A-operability-first.md) · [B](design-proposals/proposal-B-retrieval-quality-first.md) · [C](design-proposals/proposal-C-simplicity-and-extensibility-first.md)
