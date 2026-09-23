---
title: 3단계 문서 원장 (Phase 3 Document Ledger)
status: active
owner: architecture
version: 1.0.0
last_updated: 2026-09-23
depends_on: ["00-progress-report.md"]
generated_by: tools/phase3/ledger.mjs
---

# 3단계 문서 원장

## 목적

3단계(설계 문서 작성)까지 생성된 모든 문서의 **실측 상태**를 한 표로 남긴다. 이 문서는 `tools/phase3/ledger.mjs`가 frontmatter·행 수·`tools/phase3/results/*.json`(워크플로우 결과)에서 기계 생성하며, 사람이 편집하지 않는다. 재생성: `node tools/phase3/ledger.mjs --date <YYYY-MM-DD>`.

## 범위

`docs/**/*.md`(업스트림 사본 `12-appendix/sources/` 제외)와 `schemas/*.schema.json`. 리뷰 결과 열은 결과 JSON에 기록된 **마지막** 처리 결과이며, 결과 JSON이 없는 문서(1·1b·2단계 산출물, 세션 중단으로 결과가 저장되지 않은 문서)는 "-"로 표시한다.

## 1. 요약

| 항목 | 값 |
|------|----|
| 문서 수 | 151 |
| 총 행 수 | 99,572 |
| JSON Schema | 35 |
| status 분포 | active 106, - 1, accepted 38, draft 6 |
| 리뷰 결과 분포 | - 41, 수정 후 검증 통과 26, 2차 수정(검증 미해결 반영) 12, 수정 실패 7, 경량 수정(독립 검증 없음) 21, minor만 수정 29, 이전 리뷰 결과로 수정(독립 검증 없음) 13, 리뷰 통과(이슈 0) 2 |
| 미해결 이슈(결과 JSON 누적) | 480 (문서별 상세는 03-bible-amendment-triage-input.md) |
| "확인 필요" 표기 | 1277곳 |

리뷰 결과 값의 의미: `pass` 리뷰 이슈 0 · `verified` 수정 후 독립 검증 통과 · `fixed_twice` 검증 미해결분 2차 수정 · `minor_fixed` minor만 수정 · `fixed_unverified` / `fixed_from_prereview` 경량 모드 수정(독립 검증 없음, 4단계 표본 검증 대상) · `*_failed` 해당 단계 에이전트 실패(4단계 재처리 대상).

## 2. 디렉터리별 원장

### (root) — 1개, 45행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| README.md | 45 | draft | 0.3.0 | 2026-09-23 | - | - | 0 | 0 | - |

### 00-vision — 5개, 2,726행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 00-design-brief.md | 182 | active | 1.2.1 | 2026-09-22 | - | - | 0 | 2 | - |
| 01-vision-and-goals.md | 455 | active | 0.1.0 | 2026-09-18 | - | - | 0 | 4 | - |
| 02-design-principles.md | 683 | active | 0.1.0 | 2026-09-18 | - | - | 0 | 2 | - |
| 03-glossary.md | 673 | active | 0.1.0 | 2026-09-18 | - | - | 0 | 16 | - |
| 04-scope-and-non-goals.md | 733 | active | 0.1.0 | 2026-09-18 | - | - | 0 | 18 | - |

### 01-requirements — 4개, 3,182행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 01-functional-requirements.md | 579 | active | 0.1.0 | 2026-09-18 | - | - | 0 | 0 | - |
| 02-non-functional-requirements.md | 801 | active | 0.2.0 | 2026-09-18 | - | - | 0 | 26 | - |
| 03-personas-and-use-cases.md | 901 | - | - | - | - | - | 0 | 0 | - |
| 04-user-stories-and-acceptance-criteria.md | 901 | active | 0.1.0 | 2026-09-18 | - | - | 0 | 0 | - |

### 02-architecture — 10개, 9,549행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 00-design-bible.md | 1999 | active | 1.2.1 | 2026-09-22 | - | - | 0 | 11 | - |
| 01-system-overview.md | 632 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 1 | 5 | 2 | architecture |
| 02-component-architecture.md | 994 | active | 0.2.0 | 2026-09-22 | 수정 후 검증 통과 | 10 | 10 | 6 | architecture |
| 03-data-flow-and-document-lifecycle.md | 648 | active | 0.2.1 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 11 | 6 | 1 | architecture |
| 04-storage-architecture.md | 900 | active | 0.2.0 | 2026-09-22 | 수정 후 검증 통과 | 13 | 8 | 13 | architecture |
| 05-plugin-architecture.md | 979 | active | 0.1.0 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 16 | 6 | 10 | architecture |
| 06-orchestration-and-workflows.md | 1023 | active | 0.2.1 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 11 | 4 | 5 | architecture |
| 07-multi-tenancy-and-security-architecture.md | 910 | active | 0.2.1 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 7 | 3 | 12 | architecture |
| 08-deployment-architecture.md | 818 | active | 0.1.2 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 11 | 3 | 12 | architecture |
| 09-failure-modes-and-resilience.md | 646 | active | 0.1.0 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 5 | 4 | 10 | architecture |

### 03-contracts — 17개, 21,091행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 소유 스키마 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|---|
| 00-contract-overview.md | 1410 | active | 0.1.2 | 2026-09-22 | 수정 후 검증 통과 | 6 | 7 | 3 | candidate-set.schema.json, capabilities.schema.json, chunk-set.schema.json, cloud-event-envelope.schema.json, collection-spec.schema.json, common-types.schema.json, context-pack.schema.json, convert-request.schema.json, convert-response.schema.json, egress-policy.schema.json, embedded-chunk-set.schema.json, enriched-chunk-set.schema.json, eval-dataset.schema.json, eval-report.schema.json, eval-run.schema.json, feedback-event.schema.json, index-commit.schema.json, index-record.schema.json, ingest-request.schema.json, job-status.schema.json, normalized-document.schema.json, parsed-document.schema.json, plugin-meta.schema.json, problem-details.schema.json, profile.schema.json, query-plan.schema.json, query-request.schema.json, ranked-set.schema.json, rendered-context.schema.json, source-document.schema.json, stage-error.schema.json, stage-policy.schema.json, tiering-policy.schema.json, user-dict-entry.schema.json | contracts |
| 01-ingest-request.md | 935 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 6 | 8 | 2 | common-types.schema.json, ingest-request.schema.json | contracts |
| 02-source-document.md | 863 | active | 0.2.0 | 2026-09-22 | 수정 후 검증 통과 | 4 | 9 | 11 | common-types.schema.json, source-document.schema.json | contracts |
| 03-parsed-document.md | 1428 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 6 | 7 | 6 | common-types.schema.json, parsed-document.schema.json | contracts |
| 04-normalized-document.md | 1023 | active | 0.3.1 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 6 | 4 | 3 | common-types.schema.json, normalized-document.schema.json | contracts |
| 05-chunk-set.md | 1079 | active | 0.3.0 | 2026-09-22 | 수정 후 검증 통과 | 8 | 10 | 0 | chunk-set.schema.json, common-types.schema.json | contracts |
| 06-enriched-chunk-set.md | 1035 | active | 0.2.2 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 9 | 3 | 0 | chunk-set.schema.json, common-types.schema.json, enriched-chunk-set.schema.json | contracts |
| 07-embedded-chunk-set-and-index-record.md | 1269 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 3 | 6 | 3 | chunk-set.schema.json, common-types.schema.json, embedded-chunk-set.schema.json, index-record.schema.json | contracts |
| 08-index-commit.md | 922 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 6 | 10 | 0 | chunk-set.schema.json, common-types.schema.json, embedded-chunk-set.schema.json, index-commit.schema.json, source-document.schema.json | contracts |
| 09-query-request-and-query-plan.md | 1254 | active | 0.1.0 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 5 | 3 | 2 | common-types.schema.json, query-plan.schema.json, query-request.schema.json | contracts |
| 10-candidate-set-and-ranked-set.md | 1663 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 6 | 6 | 0 | candidate-set.schema.json, common-types.schema.json, ranked-set.schema.json | contracts |
| 11-context-pack.md | 1425 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 7 | 8 | 6 | common-types.schema.json, context-pack.schema.json, rendered-context.schema.json | contracts |
| 12-jobs-events-and-status.md | 1206 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 8 | 8 | 0 | cloud-event-envelope.schema.json, job-status.schema.json | contracts |
| 13-error-model.md | 1219 | active | 0.1.2 | 2026-09-22 | 수정 후 검증 통과 | 7 | 9 | 4 | common-types.schema.json, problem-details.schema.json, stage-error.schema.json | contracts |
| 14-schema-versioning-and-compatibility.md | 861 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 12 | 8 | 1 | common-types.schema.json, problem-details.schema.json, profile.schema.json, schema-diff-report.schema.json, stage-error.schema.json | contracts |
| 15-collection-profile-and-policy-contracts.md | 1870 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 6 | 7 | 5 | capabilities.schema.json, collection-spec.schema.json, common-types.schema.json, egress-policy.schema.json, plugin-meta.schema.json, profile.schema.json, schema-diff-report.schema.json, stage-policy.schema.json, tiering-policy.schema.json | contracts |
| 16-eval-feedback-and-sidecar-contracts.md | 1629 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 9 | 6 | 4 | common-types.schema.json, convert-request.schema.json, convert-response.schema.json, eval-dataset.schema.json, eval-report.schema.json, eval-run.schema.json, feedback-event.schema.json, user-dict-entry.schema.json | contracts |

### 04-pipelines — 19개, 14,652행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 01-pipeline-framework.md | 1112 | active | 0.1.1 | 2026-09-22 | 수정 후 검증 통과 | 8 | 7 | 1 | pipelines-pass1 |
| 02-fetching-and-source-resolution.md | 723 | active | 0.1.0 | 2026-09-23 | 수정 실패 | 8 | 20 | 21 | pipelines-pass1 |
| 03-parsing-router-and-format-detection.md | 676 | active | 0.1.2 | 2026-09-23 | 수정 실패 | 18 | 21 | 11 | pipelines-pass1 |
| 04-parser-hwpx-and-hwp.md | 775 | active | 0.1.0 | 2026-09-23 | 수정 실패 | 8 | 18 | 34 | pipelines-pass1 |
| 05-parser-pdf.md | 826 | active | 0.1.2 | 2026-09-23 | 수정 실패 | 14 | 21 | 16 | pipelines-pass1 |
| 06-parser-doc-and-docx.md | 634 | active | 0.1.0 | 2026-09-23 | 수정 실패 | 9 | 19 | 10 | pipelines-pass1 |
| 07-parser-html.md | 692 | active | 0.1.0 | 2026-09-23 | 수정 실패 | 5 | 19 | 8 | pipelines-pass1 |
| 08-parser-txt-md-and-others.md | 895 | active | 0.1.0 | 2026-09-23 | 2차 수정(검증 미해결 반영) | 8 | 6 | 6 | pipelines-pass1 |
| 09-normalization-and-cleaning.md | 766 | active | 0.1.0 | 2026-09-23 | 수정 후 검증 통과 | 18 | 13 | 2 | pipelines-pass1 |
| 10-chunking-strategies.md | 720 | active | 0.1.0 | 2026-09-23 | 수정 후 검증 통과 | 20 | 8 | 0 | pipelines-pass1 |
| 11-enrichment.md | 691 | active | 0.1.0 | 2026-09-23 | 수정 실패 | 12 | 18 | 7 | pipelines-pass1 |
| 12-embedding.md | 718 | active | 0.1.1 | 2026-09-22 | 수정 후 검증 통과 | 7 | 6 | 10 | pipelines-pass1 |
| 13-indexing.md | 701 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 10 | 7 | 13 | pipelines-pass1 |
| 14-query-understanding.md | 865 | active | 0.1.0 | 2026-09-22 | 수정 후 검증 통과 | 11 | 7 | 6 | pipelines-pass1 |
| 15-hybrid-search-and-fusion.md | 699 | active | 0.1.2 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 11 | 4 | 6 | pipelines-pass1 |
| 16-reranking.md | 756 | active | 0.1.0 | 2026-09-22 | 2차 수정(검증 미해결 반영) | 4 | 4 | 11 | pipelines-pass1 |
| 17-post-processing-and-context-packing.md | 1084 | active | 0.1.1 | 2026-09-22 | 수정 후 검증 통과 | 13 | 9 | 8 | pipelines-pass1 |
| 18-advanced-retrieval-graph-raptor-agentic.md | 699 | active | 0.1.1 | 2026-09-22 | 수정 후 검증 통과 | 6 | 6 | 5 | pipelines-pass1 |
| 19-update-delete-and-reindexing.md | 620 | active | 0.1.1 | 2026-09-22 | 수정 후 검증 통과 | 5 | 7 | 2 | pipelines-pass1 |

### 05-api — 7개, 5,778행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 01-api-design-guidelines.md | 851 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 2 | 4 | 4 | finish |
| 02-ingestion-api.md | 899 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 3 | 0 | finish |
| 03-retrieval-api.md | 800 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 2 | 4 | finish |
| 04-management-api.md | 748 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 3 | 0 | finish |
| 05-mcp-server.md | 881 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 3 | 8 | finish |
| 06-client-sdks.md | 785 | active | 0.1.0 | 2026-09-22 | - | - | 0 | 13 | - |
| 07-webhooks-and-events.md | 814 | active | 0.1.0 | 2026-09-22 | - | - | 0 | 0 | - |

### 06-adr — 39개, 8,110행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 0001-license-grade-table-and-d02-interpretation.md | 199 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 3 | adr-fast |
| 0002-provenance-element-path-and-nullable-page-bbox.md | 201 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 0 | adr-fast |
| 0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md | 223 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 2 | adr-fast |
| 0004-deterministic-chunk-id-scoped-record-id-and-ulid-exception.md | 211 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 1 | adr-fast |
| 0005-doc-version-content-hash-only-and-acl-payload-update.md | 181 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 0 | adr-fast |
| 0006-pdf-fast-path-pypdfium2-pdftext-replaces-pymupdf.md | 183 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 3 | adr-fast |
| 0007-hwp5-java-sidecar-first-pyhwp-demoted.md | 227 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 0 | adr-fast |
| 0008-ocr-default-rapidocr-ppocrv5-korean.md | 197 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 5 | adr-fast |
| 0009-embedding-serving-vllm-pooling-tei-inprocess.md | 201 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 6 | adr-fast |
| 0010-bge-m3-rationale-and-late-interaction-slot.md | 186 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 4 | adr-fast |
| 0011-kv-and-object-storage-valkey-rustfs-seaweedfs.md | 195 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 3 | adr-fast |
| 0012-lite-profile-qdrant-only-client-bm25.md | 175 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 6 | adr-fast |
| 0013-fusion-rrf-k60-then-convex-combination-and-postprocess-order.md | 187 | accepted | 0.1.0 | 2026-09-22 | 이전 리뷰 결과로 수정(독립 검증 없음) | - | 0 | 2 | adr-fast |
| 0014-sparse-representation-bge-m3-lexical-leg-kept.md | 210 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 3 | adr-fast |
| 0015-graph-rag-external-plugin-raptor-core-option.md | 219 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 2 | adr-fast |
| 0016-llm-enrichment-default-off-and-budget-policy.md | 200 | accepted | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 0 | 0 | adr-fast |
| 0017-event-delivery-outbox-cloudevents-no-broker.md | 210 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 0 | adr-fast |
| 0018-api-rest-sse-mcp-no-grpc-rfc9457.md | 215 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 0 | adr-fast |
| 0019-chunk-size-tokenizer-defaults-and-recount-stage.md | 180 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 1 | adr-fast |
| 0020-default-chunker-structure-aware-and-dependency-locks.md | 200 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 0 | adr-fast |
| 0021-korean-analyzer-kiwi-promotion-and-interim-mecab-kss.md | 191 | accepted | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 0 | 6 | adr-fast |
| 0022-observability-genai-semconv-pin-and-license-boundary.md | 219 | accepted | 0.1.0 | 2026-09-22 | 리뷰 통과(이슈 0) | 0 | 0 | 1 | adr-fast |
| 0023-evaluation-qrels-answer-spans-and-linear-ndcg.md | 213 | accepted | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 0 | 0 | adr-fast |
| 0024-context-pack-ordering-and-anthropic-search-result-renderer.md | 197 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 4 | adr-fast |
| 0025-mcp-cursor-pagination-and-tool-set.md | 220 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 2 | adr-fast |
| 0026-index-commit-generation-saga-and-ledger.md | 219 | accepted | 0.1.0 | 2026-09-22 | 리뷰 통과(이슈 0) | 0 | 0 | 0 | adr-fast |
| 0027-security-context-injection-and-acl-enforcement-points.md | 195 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 2 | adr-fast |
| 0028-tenant-isolation-tiering-policy.md | 209 | accepted | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 0 | 3 | adr-fast |
| 0029-three-text-rule-and-deterministic-context-prefix.md | 204 | accepted | 0.1.0 | 2026-09-22 | minor만 수정 | 0 | 0 | 0 | adr-fast |
| 0030-single-coordinate-system-and-score-ledger.md | 220 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 0 | adr-fast |
| 0031-profile-schema-extends-and-quality-gates.md | 219 | accepted | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 2 | 0 | 1 | adr-fast |
| 0032-plugin-sdk-stage-protocol-and-conformance-kit.md | 221 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 0 | adr-fast |
| 0033-sidecar-convert-contract-and-isolation-ladder.md | 203 | accepted | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 0 | 0 | adr-fast |
| 0034-retrieval-hot-path-postgres-independence-and-hydrate.md | 219 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 4 | adr-fast |
| 0035-python-version-and-toolchain-pins.md | 240 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 4 | adr-fast |
| 0036-naming-and-identifier-conventions.md | 198 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 0 | adr-fast |
| 0037-artifact-cache-scope-and-stage-key-composition.md | 206 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 1 | adr-fast |
| 0038-outbound-egress-policy-and-webhook-signing.md | 178 | accepted | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 0 | 3 | adr-fast |
| README.md | 339 | active | 0.1.0 | 2026-09-23 | - | - | 0 | 1 | - |

### 07-tech-landscape — 15개, 9,637행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 00-summary-and-selection-matrix.md | 364 | active | 1.0.0 | 2026-09-22 | - | - | 0 | 5 | - |
| 01-document-parsing-hwpx-hwp.md | 472 | active | 0.2.1 | 2026-09-22 | - | - | 0 | 21 | - |
| 02-document-parsing-pdf-layout-ocr.md | 701 | active | 0.3.0 | 2026-09-22 | - | - | 0 | 35 | - |
| 03-document-parsing-office-html-text.md | 661 | active | 0.2.0 | 2026-09-22 | - | - | 0 | 9 | - |
| 04-chunking-strategies-and-libraries.md | 597 | active | 0.3.0 | 2026-09-22 | - | - | 0 | 28 | - |
| 05-embedding-models-and-serving.md | 609 | active | 0.3.0 | 2026-09-22 | - | - | 0 | 35 | - |
| 06-vector-and-lexical-index-backends.md | 622 | active | 0.3.0 | 2026-09-22 | - | - | 0 | 32 | - |
| 07-retrieval-techniques-fusion-reranking.md | 572 | active | 0.2.0 | 2026-09-22 | - | - | 0 | 36 | - |
| 08-orchestration-messaging-and-api-frameworks.md | 852 | active | 0.3.0 | 2026-09-22 | - | - | 0 | 21 | - |
| 09-evaluation-and-observability.md | 715 | active | 0.3.0 | 2026-09-22 | - | - | 0 | 26 | - |
| 10-llm-context-optimization-and-mcp.md | 799 | active | 0.3.0 | 2026-09-22 | - | - | 0 | 52 | - |
| 11-existing-rag-platforms-gap-analysis.md | 607 | active | 0.2.0 | 2026-09-22 | - | - | 0 | 18 | - |
| 12-security-multitenancy-pii-and-licensing.md | 876 | active | 0.2.0 | 2026-09-22 | - | - | 0 | 61 | - |
| 13-korean-nlp-tokenization-and-language-resources.md | 490 | active | 0.2.0 | 2026-09-22 | - | - | 0 | 28 | - |
| 14-advanced-rag-graph-raptor-agentic-multimodal.md | 700 | active | 0.2.0 | 2026-09-22 | - | - | 0 | 34 | - |

### 08-evaluation — 6개, 4,549행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 01-evaluation-strategy.md | 584 | active | 0.1.0 | 2026-09-22 | - | - | 0 | 1 | - |
| 02-retrieval-metrics-and-harness.md | 783 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 2 | 9 | finish |
| 03-golden-dataset-construction.md | 791 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 3 | 11 | finish |
| 04-llm-judge-and-generation-quality.md | 951 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 6 | 4 | 23 | finish |
| 05-benchmark-plan-and-baselines.md | 589 | active | 0.1.2 | 2026-09-23 | 경량 수정(독립 검증 없음) | 3 | 5 | 6 | finish |
| 06-online-feedback-loop.md | 851 | active | 0.1.0 | 2026-09-22 | - | - | 0 | 0 | - |

### 09-operations — 8개, 6,424행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 01-deployment-guide.md | 896 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 4 | 25 | finish |
| 02-configuration-reference.md | 1007 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 2 | 5 | 4 | finish |
| 03-observability.md | 851 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 2 | 3 | 9 | finish |
| 04-scaling-and-performance.md | 708 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 4 | 15 | finish |
| 05-security-and-compliance.md | 741 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 3 | 41 | finish |
| 06-runbooks.md | 896 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 4 | 9 | finish |
| 07-backup-and-disaster-recovery.md | 640 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 3 | 6 | finish |
| 08-upgrade-and-migration.md | 685 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 3 | 7 | finish |

### 10-development — 8개, 6,234행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 01-repository-structure.md | 673 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 2 | 8 | finish |
| 02-development-environment.md | 677 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 2 | 23 | finish |
| 03-coding-standards.md | 873 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 3 | 6 | finish |
| 04-testing-strategy.md | 737 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 3 | 25 | finish |
| 05-ci-cd.md | 900 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 5 | 30 | finish |
| 06-plugin-development-guide.md | 896 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 4 | 6 | finish |
| 07-contributing.md | 723 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 2 | 5 | 11 | finish |
| 08-release-process.md | 755 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 4 | 16 | finish |

### 11-roadmap — 3개, 2,134행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 01-milestones.md | 696 | active | 0.1.1 | 2026-09-22 | - | - | 0 | 3 | - |
| 02-epics-and-backlog.md | 997 | active | 0.1.0 | 2026-09-23 | 경량 수정(독립 검증 없음) | 1 | 3 | 6 | finish |
| 03-risks-and-mitigations.md | 441 | active | 0.1.0 | 2026-09-23 | minor만 수정 | 0 | 3 | 1 | finish |

### 12-appendix — 9개, 5,461행

| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | 결과 그룹 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| 00-progress-report.md | 239 | active | 0.5.0 | 2026-09-23 | - | - | 0 | 3 | - |
| 01-phase3-completeness-review.md | 180 | active | 0.1.0 | 2026-09-23 | - | - | 0 | 2 | - |
| 02-phase4-5-plan.md | 159 | draft | 0.1.0 | 2026-09-23 | - | - | 0 | 2 | - |
| 03-bible-amendment-triage-input.md | 463 | active | 1.0.0 | 2026-09-23 | - | - | 0 | 26 | - |
| 04-phase3-document-ledger.md | 304 | active | 1.0.0 | 2026-09-23 | - | - | 0 | 15 | - |
| 05-phase6-implementation-kit-plan.md | 169 | draft | 0.1.0 | 2026-09-23 | - | - | 0 | 6 | - |
| proposal-A-operability-first.md | 1290 | draft | 0.1.0 | 2026-09-22 | - | - | 0 | 1 | - |
| proposal-B-retrieval-quality-first.md | 1479 | draft | 0.1.0 | 2026-09-22 | - | - | 0 | 0 | - |
| proposal-C-simplicity-and-extensibility-first.md | 1178 | draft | 0.1.0 | 2026-09-22 | - | - | 0 | 1 | - |

## 3. 스키마 파일

| 파일 | 소유 문서 |
|---|---|
| candidate-set.schema.json | 00-contract-overview.md, 10-candidate-set-and-ranked-set.md |
| capabilities.schema.json | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md |
| chunk-set.schema.json | 00-contract-overview.md, 05-chunk-set.md, 06-enriched-chunk-set.md, 07-embedded-chunk-set-and-index-record.md, 08-index-commit.md |
| cloud-event-envelope.schema.json | 00-contract-overview.md, 12-jobs-events-and-status.md |
| collection-spec.schema.json | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md |
| common-types.schema.json | 00-contract-overview.md, 01-ingest-request.md, 02-source-document.md, 03-parsed-document.md, 04-normalized-document.md, 05-chunk-set.md, 06-enriched-chunk-set.md, 07-embedded-chunk-set-and-index-record.md, 08-index-commit.md, 09-query-request-and-query-plan.md, 10-candidate-set-and-ranked-set.md, 11-context-pack.md, 13-error-model.md, 14-schema-versioning-and-compatibility.md, 15-collection-profile-and-policy-contracts.md, 16-eval-feedback-and-sidecar-contracts.md |
| context-pack.schema.json | 00-contract-overview.md, 11-context-pack.md |
| convert-request.schema.json | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md |
| convert-response.schema.json | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md |
| egress-policy.schema.json | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md |
| embedded-chunk-set.schema.json | 00-contract-overview.md, 07-embedded-chunk-set-and-index-record.md, 08-index-commit.md |
| enriched-chunk-set.schema.json | 00-contract-overview.md, 06-enriched-chunk-set.md |
| eval-dataset.schema.json | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md |
| eval-report.schema.json | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md |
| eval-run.schema.json | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md |
| feedback-event.schema.json | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md |
| index-commit.schema.json | 00-contract-overview.md, 08-index-commit.md |
| index-record.schema.json | 00-contract-overview.md, 07-embedded-chunk-set-and-index-record.md |
| ingest-request.schema.json | 00-contract-overview.md, 01-ingest-request.md |
| job-status.schema.json | 00-contract-overview.md, 12-jobs-events-and-status.md |
| normalized-document.schema.json | 00-contract-overview.md, 04-normalized-document.md |
| parsed-document.schema.json | 00-contract-overview.md, 03-parsed-document.md |
| plugin-meta.schema.json | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md |
| problem-details.schema.json | 00-contract-overview.md, 13-error-model.md, 14-schema-versioning-and-compatibility.md |
| profile.schema.json | 00-contract-overview.md, 14-schema-versioning-and-compatibility.md, 15-collection-profile-and-policy-contracts.md |
| query-plan.schema.json | 00-contract-overview.md, 09-query-request-and-query-plan.md |
| query-request.schema.json | 00-contract-overview.md, 09-query-request-and-query-plan.md |
| ranked-set.schema.json | 00-contract-overview.md, 10-candidate-set-and-ranked-set.md |
| rendered-context.schema.json | 00-contract-overview.md, 11-context-pack.md |
| schema-diff-report.schema.json | 14-schema-versioning-and-compatibility.md, 15-collection-profile-and-policy-contracts.md |
| source-document.schema.json | 00-contract-overview.md, 02-source-document.md, 08-index-commit.md |
| stage-error.schema.json | 00-contract-overview.md, 13-error-model.md, 14-schema-versioning-and-compatibility.md |
| stage-policy.schema.json | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md |
| tiering-policy.schema.json | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md |
| user-dict-entry.schema.json | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md |

## 결정 사항 요약

- 이 원장은 진행 보고서 §3의 근거 데이터이며, 두 문서가 다르면 원장(기계 생성)이 우선한다.

## 미해결 이슈

- `*_failed`·`fixed_unverified` 문서의 후속 처리는 4·5단계 계획 §2.3 D4-4를 따른다.

## 참조

- [진행 보고서](00-progress-report.md) · [4·5단계 계획](02-phase4-5-plan.md) · [바이블 개정 요청 통합 목록](03-bible-amendment-triage-input.md)
