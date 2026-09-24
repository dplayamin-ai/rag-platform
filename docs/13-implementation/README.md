---
title: 구현 작업 패키지 색인 (Implementation Work Packages)
status: active
owner: architecture
version: 1.0.0
last_updated: 2026-09-24
depends_on: ["../12-appendix/05-phase6-implementation-kit-plan.md", "../12-appendix/00-progress-report.md", "../12-appendix/10-implementation-design-gaps.md"]
---

# 구현 작업 패키지(WP) 색인

## 목적

6단계 6E·6F에서 M1 lite 레퍼런스를 구현하며 만든 작업 패키지(Work Package, WP) 문서의 색인이다. WP 하나가 구현 단위(플러그인·스테이지·모듈 묶음)이며, 같은 커밋에 코드와 테스트가 함께 들어간다. 각 WP는 목표 → 파일·시그니처 → 입출력 계약 발췌(바이블 절·ADR·계약 문서) → 불변식·금지 → 단계 → 테스트 → 완료 기준 → 검증 계층·DEFERRED 순서다.

## 범위

`wp/WP-nnn-<slug>.md` 21건. 번호 첫 자리가 배치(F1~F5)이고, WP-405·WP-504는 Opus 리뷰 수정 WP다. 실행 기록과 게이트 결과는 [진행 보고서 §7.2h](../12-appendix/00-progress-report.md), 배치 정의는 `tools/phase6/wf-6f.js`, 결과 JSON은 `tools/phase6/results/f1..f5.json`. 구현 중 발견한 설계 갭(에이전트 `open_issues`)은 WP 본문이 아니라 [구현 설계 갭 원장](../12-appendix/10-implementation-design-gaps.md)에 모여 있다(아래 표의 "설계 갭" 열은 그 원장에서 이 WP 출처로 집계한 건수).

## WP 목록


### F1 수집 전단

흐름: fetch → format-detect/route → parse(TXT/MD/CSV·HTML·PDF) → normalize(korean)

| WP | 제목 | 목표(발췌) | 설계 갭 |
|----|------|-----------|--------:|
| [WP-101](wp/WP-101-fetch-fsspec-httpx.md) | WP-101: fetch-fsspec-httpx (F1-01) | `fetcher` 확장 지점의 코어 플러그인 `fetcher.fsspec_httpx`(`Stage[IngestRequest, SourceDocument]`)를 구현한다. 이 WP 범위는 스킴 `file://`(허용 루트 제한)와 `http(s)://`(httpx, `m… | 7 |
| [WP-102](wp/WP-102-format-detector-and-parse-router.md) | WP-102 format-detector-and-parse-router | `04-pipelines/03-parsing-router-and-format-detection.md`가 정의하는 두 결정 — **판별**(`detect` 서브스테이지: 이 바이트가 무엇인가)과 **라우팅**(`parser.router`: 누가 파싱하는가) — 을 이 W… | 7 |
| [WP-103](wp/WP-103-parse-text-markdown-csv.md) | WP-103 parse-text-markdown-csv | `04-pipelines/08-parser-txt-md-and-others.md`가 정의하는 텍스트 계열 파서 플러그인 `parser.text_charset_markdown_it`를 구현한다. `SourceDocument{format ∈ {txt, md}}` 바이트를 … | 4 |
| [WP-104](wp/WP-104-parse-html-trafilatura.md) | WP-104 parse-html-trafilatura | `04-pipelines/07-parser-html.md`가 정의하는 HTML 파서 플러그인 `parser.html_trafilatura_docling`을 구현한다. `SourceDocument{format=html}` 바이트를 받아 `ParsedDocument`를 만… | 4 |
| [WP-105](wp/WP-105-parse-pdf-fast-pypdfium2.md) | WP-105 parse-pdf-fast-pypdfium2 | `04-pipelines/05-parser-pdf.md` §4(빠른 경로 `pdf_fast_cpu`)·§7.2(heading 레벨 추론)·§7.3(읽기 순서· 2단 컬럼)·§7.7(provenance·좌표계)·§11(품질 게이트)이 정의하는 PDF 디지털 빠른 경로 파… | 4 |
| [WP-106](wp/WP-106-normalize-korean.md) | WP-106 normalize-korean | `normalizer.chain` 스테이지(`ParsedDocument → NormalizedDocument`, 바이블 §4.2 `normalize` 행)의 축소 범위 구현. 04-pipelines/09 §2(체인 정본 순서)의 N1~N10 중 이 WP가 다루는 부분만… | 3 |

### F2 청킹·보강

흐름: chunk(structure-aware·table rows·recount) → enrich(deterministic)

| WP | 제목 | 목표(발췌) | 설계 갭 |
|----|------|-----------|--------:|
| [WP-201](wp/WP-201-chunk-structure-aware.md) | WP-201 chunk-structure-aware | `chunker.structure_aware` 스테이지(`NormalizedDocument → ChunkSet`, 바이블 §4.2 `chunk` 행)의 축소 범위 구현. 04-pipelines/10 §2(기본 전략 단계 A~G)·§3(부모-자식)·§7.2(파라미터 기본… | 5 |
| [WP-202](wp/WP-202-chunk-table-rows-and-recount.md) | WP-202 chunk-table-rows-and-recount | `chunk` 스테이지가 표(table) 블록을 처리할 때 쓰는 **표 청킹 하위 모듈**(`table_rows.py`, 04-pipelines/10 §4 판정 흐름·규칙·직렬화 옵션의 축소 구현)과, 임베더 교체로 `token_counts` 키가 누락됐을 때 **재청… | 4 |
| [WP-203](wp/WP-203-enrich-deterministic.md) | WP-203 enrich-deterministic | `enrich` 스테이지(바이블 §4.2 `enrich` 행)의 결정적(규칙 기반, LLM 미사용) 보강기 체인 중 3종을 구현한다: 체인 순서 1 `enricher.deterministic_prefix`(ADR-0029 3-텍스트 조립: `embed_text`/ `i… | 5 |

### F3 임베딩·인덱스·수집 e2e

흐름: embed(FakeEmbedder + sparse_bm25) → index(Qdrant local, commit saga) → ingest pipeline e2e

| WP | 제목 | 목표(발췌) | 설계 갭 |
|----|------|-----------|--------:|
| [WP-301](wp/WP-301-embed-stage-and-sparse-bm25.md) | WP-301 embed-stage-and-sparse-bm25 | `embed` 스테이지(바이블 §4.2 `embed` 행, ADR-0032 5멤버)를 `lite` 프로파일 범위로 구현한다: `EnrichedChunkSet` → `EmbeddedChunkSet`. dense는 `sdk.ports.Embedder` 포트(기본 `Inpr… | 11 |
| [WP-302](wp/WP-302-index-stage-and-commit-saga.md) | WP-302 index-stage-and-commit-saga | `index` 스테이지(바이블 §4.2 `index` 행, ADR-0032 5멤버)를 `lite`(Qdrant 단독) 범위로 구현한다: `EmbeddedChunkSet` + `requires_lineage`(`EnrichedChunkSet`, `ChunkSet`, `S… | 5 |
| [WP-303](wp/WP-303-ingest-pipeline-e2e.md) | WP-303 ingest-pipeline-e2e | 바이블 §11.1(`pipelines.ingest.run(ctx, req_ref, profile) -> IndexCommit`)의 파이프라인 정의를 완성하고(`out_type` 자리표시자 `object`를 실제 생성 계약 클래스로 교체), `lite` 프로파일 값으로 … | 0 |

### F4 검색 경로

흐름: plan/filters → channels/fusion/hydrate → postprocess/pack → render/query pipeline (+ Opus 리뷰 수정 WP-405)

| WP | 제목 | 목표(발췌) | 설계 갭 |
|----|------|-----------|--------:|
| [WP-401](wp/WP-401-planner-and-filters.md) | WP-401 규칙 경로 플래너와 필터 | `plan` 스테이지의 **규칙 경로**(LLM 없음, `retrieval_variant=default\|fast`)만 구현한다: 정규화 (NFC 표시 뷰 + NFKC 렉시컬 뷰, 04-pipelines/14 §2.1)·언어 감지(§2.2)·형태소 키워드(Kiwi 있으… | 8 |
| [WP-402](wp/WP-402-channels-fusion-hydrate.md) | WP-402 channels-fusion-hydrate | 검색 경로의 세 단계를 `lite` 프로파일 범위로 구현한다: (1) `retrieve` 코디네이터 — `QueryPlan.channels[] x rewritten_queries[]`를 곱집합으로 펼친 런을 `asyncio`로 병렬 실행해 `CandidateSet`을 … | 6 |
| [WP-403](wp/WP-403-postprocess-and-pack.md) | WP-403 후처리와 컨텍스트 패킹 | 바이블 §8.2(후처리 고정 순서)·§9.1~9.2(패커 규칙·`litm_alternating`)·04-pipelines/17 §2~§3(의사코드 정본)에 따라 `RankedSet(reranked) → RankedSet(postprocessed) → ContextPac… | 5 |
| [WP-404](wp/WP-404-render-and-query-pipeline.md) | WP-404 렌더러와 질의 파이프라인 | 1. `ContextPack → RenderedContext` 렌더러 2종(`markdown`, `anthropic_search_result`)을 바이블 §9.3(렌더러 정본)·§4.1(공통 렌더 규칙)에 맞게 구현한다. 2. `citation_map.py`에 `Cit… | 5 |
| [WP-405](wp/WP-405-review-fixes-retrieve-acl-filters.md) | WP-405 리뷰 수정 — retrieve/acl_recheck/filters | F4-01~04 코드 리뷰의 blocker/major 6건을 고친다. 새 기능이 아니라 기존 WP-401~402가 낸 모듈의 버그 수정이므로 파일·시그니처는 그대로이고, 계약(생성물)도 바꾸지 않는다. 대상: | 4 |

### F5 API·MCP·CLI·전체 e2e

흐름: FastAPI ingest/jobs/query → MCP server → CLI + full e2e (+ Opus 리뷰 수정 WP-504)

| WP | 제목 | 목표(발췌) | 설계 갭 |
|----|------|-----------|--------:|
| [WP-501](wp/WP-501-api-ingest-jobs-query.md) | WP-501 API — 수집 접수·잡 조회·질의·렌더 | 1. `POST /v1/ingest` — `Idempotency-Key` 필수, 202 `{job_id, request_id, document_id, status_url, events_url}`, `SecurityContext` 서버 주입, `orchestration.… | 6 |
| [WP-502](wp/WP-502-mcp-server.md) | WP-502 MCP 서버 | 1. MCP 도구 3종(`search`, `get_document`, `list_collections`) 핸들러를 `mcp/tools.py`에 순수 함수로 구현한다 — SDK 세션·전송 없이 직접 호출·단위 테스트 가능. 2. 커서 저장소(`mcp/cursor_stor… | 6 |
| [WP-503](wp/WP-503-cli-and-full-e2e.md) | WP-503 CLI와 전체 e2e | 1. `rag` CLI에 `ingest <paths…> --profile lite-dev --collection`, `query "<질의>" --collection [--format text\|json]`, `serve api\|mcp`, `profile validat… | 8 |
| [WP-504](wp/WP-504-review-fixes-security-context-pack-cache-mcp-ordering.md) | WP-504 리뷰 수정 — API 키 서비스 주체, pack_id 캐시 주체 바인딩, MCP search 관련도순 절단 | F5-01/02(`WP-501`/`WP-502`) 코드 리뷰의 major 3건을 고친다. 새 기능이 아니라 기존 모듈의 버그 수정이므로 파일·계약(생성물)은 그대로다. 대상: | 2 |


합계: WP 21건, 설계 갭 109건(원장 전체 186건 중 WP 출처가 식별된 것; 나머지는 검증 에이전트·6B/6D 스파이크 출처).

## 규약

- 새 구현은 WP 문서를 먼저 쓴다(`WP-nnn-<slug>.md`, 다음 배치 번호 6xx부터). 구현 에이전트·개발자는 WP + 대상 파일 + 테스트 출력만 읽어도 작업할 수 있도록 WP가 필요한 설계 발췌를 담는다.
- 코드가 바이블·계약을 앞서 바꾸지 않는다. 설계 갭은 결과 `open_issues`(또는 WP 끝의 미해결 항목)에 남기고 `node tools/phase6/gen-design-gaps.mjs`로 원장에 모은다. 바이블 패치는 ADR 절차(CLAUDE.md §3)로 따로 한다.
- 모든 코드 파일은 한국어 설명 헤더 규칙(`tools/phase6/CODE-HEADER-RULE.md`)을 따른다. 게이트: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run lint-imports`, `uv run pytest -q`, `node tools/verify/check-headers.mjs`, `node tools/verify/gen-deferred-ledger.mjs`.

## 결정 사항 요약

- 6E(WP 작성)와 6F(구현)를 분리하지 않고 "WP 우선 구현"으로 합쳤다 — 한 에이전트가 WP → 구현 → 테스트를 연속으로 수행해 앵커 재독 비용을 줄였다.
- 리뷰 수정도 WP(405·504)로 남겨 무엇이 왜 바뀌었는지 추적한다.

## 미해결 이슈

- WP 문서의 frontmatter·절 번호 형식이 배치별로 조금 다르다(F1~F3는 영문 슬러그 제목·번호 없는 절, F4~F5는 한국어 제목·번호 절; WP-101은 frontmatter 없음). 6G 공개 준비에서 통일한다.
- 설계 갭 186건의 처리 순서는 [구현 설계 갭 원장](../12-appendix/10-implementation-design-gaps.md) "미해결 이슈" 절을 따른다.

## 참조

- [6단계 구현 킷 계획](../12-appendix/05-phase6-implementation-kit-plan.md) · [진행 보고서](../12-appendix/00-progress-report.md) · [구현 설계 갭 원장](../12-appendix/10-implementation-design-gaps.md) · [보류 검증 원장](../12-appendix/09-deferred-verification-ledger.md) · [저장소 구조](../10-development/01-repository-structure.md) · [테스트 전략](../10-development/04-testing-strategy.md)
