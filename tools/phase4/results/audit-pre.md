# 문서 기계 감사 결과 (2026-09-23)

| 검사 | 건수 |
|---|---:|
| A1_broken_links | 1 |
| A2_frontmatter_issues | 5 |
| A3_spelling_hits | 188 |
| A3_needs_context_review | 123 |
| A5_over_900 | 11 |
| A6_review_or_draft | 2 |
| A7_bad_citations | 8 |
| A8_confirm_docs | 122 |
| A8_confirm_total | 1285 |
| A10 | [object Object] |
| fixes | 0 |
| A9 스키마 인벤토리 | 바이블 34 / 디스크 35; 바이블에만 -; 디스크에만 schema-diff-report.schema.json |

## A1 깨진 링크 (1)

| file | line | target |
|---|---|---|
| 12-appendix/06-traceability-matrix.md | 383 | ./01-functional-requirements.md |

## A2 frontmatter (5)

| file | problem |
|---|---|
| 01-requirements/03-personas-and-use-cases.md | 필수 필드 누락: title |
| 01-requirements/03-personas-and-use-cases.md | 필수 필드 누락: status |
| 01-requirements/03-personas-and-use-cases.md | 필수 필드 누락: owner |
| 01-requirements/03-personas-and-use-cases.md | 필수 필드 누락: version |
| 01-requirements/03-personas-and-use-cases.md | 필수 필드 누락: last_updated |

## A3 철자·기각 명칭 (likely_ok=false 우선 검토) (188)

| file | line | token | hint | likely_ok |
|---|---|---|---|---|
| 00-vision/00-design-brief.md | 24 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | true |
| 00-vision/00-design-brief.md | 66 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | true |
| 00-vision/00-design-brief.md | 66 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 00-vision/00-design-brief.md | 66 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 00-vision/00-design-brief.md | 66 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 00-vision/00-design-brief.md | 62 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 00-vision/00-design-brief.md | 62 | MinIO | RustFS/SeaweedFS(ADR-0011) | false |
| 00-vision/00-design-brief.md | 62 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 00-vision/00-design-brief.md | 62 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 00-vision/00-design-brief.md | 62 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 00-vision/00-design-brief.md | 64 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 00-vision/00-design-brief.md | 64 | Infinity | vLLM pooling + TEI(ADR-0009) | false |
| 00-vision/00-design-brief.md | 75 | SPLADE-v3 | 제외(O-02) | false |
| 00-vision/01-vision-and-goals.md | 353 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 00-vision/03-glossary.md | 416 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 00-vision/03-glossary.md | 416 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 00-vision/03-glossary.md | 552 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 00-vision/03-glossary.md | 397 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 00-vision/03-glossary.md | 405 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 00-vision/03-glossary.md | 405 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 00-vision/03-glossary.md | 553 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 00-vision/03-glossary.md | 333 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 00-vision/03-glossary.md | 359 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 00-vision/03-glossary.md | 359 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 00-vision/03-glossary.md | 272 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 00-vision/03-glossary.md | 323 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 00-vision/03-glossary.md | 355 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 00-vision/03-glossary.md | 355 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 00-vision/03-glossary.md | 555 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 00-vision/03-glossary.md | 164 | Infinity | vLLM pooling + TEI(ADR-0009) | false |
| 00-vision/03-glossary.md | 271 | Infinity | vLLM pooling + TEI(ADR-0009) | false |
| 00-vision/03-glossary.md | 263 | SPLADE-v3 | 제외(O-02) | false |
| 00-vision/04-scope-and-non-goals.md | 466 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 00-vision/04-scope-and-non-goals.md | 466 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 00-vision/04-scope-and-non-goals.md | 520 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 00-vision/04-scope-and-non-goals.md | 668 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 00-vision/04-scope-and-non-goals.md | 464 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 00-vision/04-scope-and-non-goals.md | 464 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 00-vision/04-scope-and-non-goals.md | 519 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 00-vision/04-scope-and-non-goals.md | 167 | MinIO | RustFS/SeaweedFS(ADR-0011) | false |
| 00-vision/04-scope-and-non-goals.md | 546 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 00-vision/04-scope-and-non-goals.md | 55 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 00-vision/04-scope-and-non-goals.md | 415 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 00-vision/04-scope-and-non-goals.md | 672 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 00-vision/04-scope-and-non-goals.md | 672 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 00-vision/04-scope-and-non-goals.md | 55 | Infinity | vLLM pooling + TEI(ADR-0009) | false |
| 00-vision/04-scope-and-non-goals.md | 216 | Infinity | vLLM pooling + TEI(ADR-0009) | false |
| 00-vision/04-scope-and-non-goals.md | 336 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 00-vision/04-scope-and-non-goals.md | 337 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 00-vision/04-scope-and-non-goals.md | 567 | Infinity | vLLM pooling + TEI(ADR-0009) | false |
| 01-requirements/02-non-functional-requirements.md | 582 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 01-requirements/02-non-functional-requirements.md | 745 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 01-requirements/02-non-functional-requirements.md | 745 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 01-requirements/02-non-functional-requirements.md | 589 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 01-requirements/02-non-functional-requirements.md | 747 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 01-requirements/02-non-functional-requirements.md | 502 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 01-requirements/02-non-functional-requirements.md | 552 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 01-requirements/02-non-functional-requirements.md | 579 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 01-requirements/02-non-functional-requirements.md | 90 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 01-requirements/02-non-functional-requirements.md | 272 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 01-requirements/02-non-functional-requirements.md | 578 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 01-requirements/02-non-functional-requirements.md | 746 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 01-requirements/02-non-functional-requirements.md | 746 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 01-requirements/02-non-functional-requirements.md | 595 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 01-requirements/02-non-functional-requirements.md | 621 | SPLADE-v3 | 제외(O-02) | true |
| 01-requirements/03-personas-and-use-cases.md | 865 | exclude_chunk_ids | exclude_ids | true |
| 01-requirements/03-personas-and-use-cases.md | 360 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 01-requirements/03-personas-and-use-cases.md | 298 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | true |
| 01-requirements/03-personas-and-use-cases.md | 62 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 01-requirements/03-personas-and-use-cases.md | 266 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 01-requirements/03-personas-and-use-cases.md | 460 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 01-requirements/04-user-stories-and-acceptance-criteria.md | 209 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/01-system-overview.md | 185 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 02-architecture/01-system-overview.md | 580 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 02-architecture/01-system-overview.md | 185 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/01-system-overview.md | 185 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/01-system-overview.md | 185 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/01-system-overview.md | 231 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/01-system-overview.md | 579 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/01-system-overview.md | 572 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 02-architecture/01-system-overview.md | 178 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 02-architecture/01-system-overview.md | 573 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 02-architecture/01-system-overview.md | 576 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 02-architecture/02-component-architecture.md | 944 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 02-architecture/02-component-architecture.md | 944 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/04-storage-architecture.md | 366 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 02-architecture/04-storage-architecture.md | 694 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 02-architecture/04-storage-architecture.md | 722 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 02-architecture/05-plugin-architecture.md | 926 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/05-plugin-architecture.md | 926 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/05-plugin-architecture.md | 936 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/05-plugin-architecture.md | 978 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/08-deployment-architecture.md | 133 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | true |
| 02-architecture/08-deployment-architecture.md | 148 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/08-deployment-architecture.md | 166 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/08-deployment-architecture.md | 337 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 02-architecture/08-deployment-architecture.md | 770 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 03-contracts/00-contract-overview.md | 507 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 03-contracts/00-contract-overview.md | 599 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 03-contracts/01-ingest-request.md | 289 | Infinity | vLLM pooling + TEI(ADR-0009) | false |
| 03-contracts/02-source-document.md | 310 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 03-contracts/02-source-document.md | 824 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 03-contracts/02-source-document.md | 860 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 03-contracts/03-parsed-document.md | 1398 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 03-contracts/03-parsed-document.md | 1425 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 03-contracts/16-eval-feedback-and-sidecar-contracts.md | 1626 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 03-contracts/16-eval-feedback-and-sidecar-contracts.md | 1555 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 04-pipelines/03-parsing-router-and-format-detection.md | 650 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 04-pipelines/03-parsing-router-and-format-detection.md | 24 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/03-parsing-router-and-format-detection.md | 51 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/03-parsing-router-and-format-detection.md | 632 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/03-parsing-router-and-format-detection.md | 636 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/03-parsing-router-and-format-detection.md | 650 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/04-parser-hwpx-and-hwp.md | 19 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/04-parser-hwpx-and-hwp.md | 155 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/04-parser-hwpx-and-hwp.md | 464 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/04-parser-hwpx-and-hwp.md | 472 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/04-parser-hwpx-and-hwp.md | 590 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/04-parser-hwpx-and-hwp.md | 131 | pageBreak | 열거값 camelCase 변형 → page_break |  |
| 04-pipelines/04-parser-hwpx-and-hwp.md | 136 | pageBreak | 열거값 camelCase 변형 → page_break |  |
| 04-pipelines/04-parser-hwpx-and-hwp.md | 411 | pageBreak | 열거값 camelCase 변형 → page_break |  |
| 04-pipelines/04-parser-hwpx-and-hwp.md | 411 | pageBreak | 열거값 camelCase 변형 → page_break |  |
| 04-pipelines/05-parser-pdf.md | 78 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 04-pipelines/05-parser-pdf.md | 95 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 04-pipelines/05-parser-pdf.md | 761 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 04-pipelines/05-parser-pdf.md | 783 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 04-pipelines/06-parser-doc-and-docx.md | 595 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/06-parser-doc-and-docx.md | 633 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 04-pipelines/12-embedding.md | 250 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 04-pipelines/12-embedding.md | 304 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 04-pipelines/12-embedding.md | 306 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 04-pipelines/12-embedding.md | 677 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 04-pipelines/12-embedding.md | 244 | SPLADE-v3 | 제외(O-02) | false |
| 04-pipelines/15-hybrid-search-and-fusion.md | 227 | SPLADE-v3 | 제외(O-02) | true |
| 04-pipelines/15-hybrid-search-and-fusion.md | 649 | SPLADE-v3 | 제외(O-02) | true |
| 04-pipelines/16-reranking.md | 294 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 04-pipelines/16-reranking.md | 305 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 04-pipelines/16-reranking.md | 751 | Infinity | vLLM pooling + TEI(ADR-0009) | false |
| 05-api/01-api-design-guidelines.md | 551 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 06-adr/README.md | 132 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 06-adr/README.md | 132 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 06-adr/README.md | 183 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | true |
| 06-adr/README.md | 133 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 06-adr/README.md | 133 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 06-adr/README.md | 133 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 06-adr/README.md | 184 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 06-adr/README.md | 137 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 06-adr/README.md | 178 | MinIO | RustFS/SeaweedFS(ADR-0011) | false |
| 06-adr/README.md | 137 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 06-adr/README.md | 178 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 06-adr/README.md | 135 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 06-adr/README.md | 135 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 09-operations/01-deployment-guide.md | 127 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 09-operations/01-deployment-guide.md | 426 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 09-operations/01-deployment-guide.md | 426 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 09-operations/01-deployment-guide.md | 426 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 09-operations/02-configuration-reference.md | 165 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 09-operations/05-security-and-compliance.md | 684 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 09-operations/05-security-and-compliance.md | 462 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 09-operations/05-security-and-compliance.md | 684 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 09-operations/05-security-and-compliance.md | 462 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 10-development/01-repository-structure.md | 39 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 10-development/01-repository-structure.md | 44 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 10-development/01-repository-structure.md | 631 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 10-development/01-repository-structure.md | 671 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 10-development/02-development-environment.md | 61 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 10-development/02-development-environment.md | 63 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | true |
| 10-development/02-development-environment.md | 675 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 10-development/03-coding-standards.md | 633 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | true |
| 10-development/03-coding-standards.md | 630 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | true |
| 10-development/03-coding-standards.md | 633 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | true |
| 10-development/03-coding-standards.md | 633 | MinIO | RustFS/SeaweedFS(ADR-0011) | true |
| 10-development/03-coding-standards.md | 633 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 10-development/03-coding-standards.md | 633 | Infinity | vLLM pooling + TEI(ADR-0009) | true |
| 10-development/07-contributing.md | 640 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 10-development/07-contributing.md | 640 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 10-development/07-contributing.md | 722 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 10-development/07-contributing.md | 666 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | true |
| 11-roadmap/01-milestones.md | 648 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 11-roadmap/01-milestones.md | 695 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 11-roadmap/02-epics-and-backlog.md | 996 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 11-roadmap/03-risks-and-mitigations.md | 113 | PyMuPDF | 기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함 | false |
| 11-roadmap/03-risks-and-mitigations.md | 98 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 11-roadmap/03-risks-and-mitigations.md | 113 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 11-roadmap/03-risks-and-mitigations.md | 440 | pyhwp | 선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반 | false |
| 11-roadmap/03-risks-and-mitigations.md | 113 | Redis | Valkey(ADR-0011) — "Redis 호환" 표현만 허용 | false |
| 11-roadmap/03-risks-and-mitigations.md | 105 | Infinity | vLLM pooling + TEI(ADR-0009) | false |
| 11-roadmap/03-risks-and-mitigations.md | 114 | SPLADE-v3 | 제외(O-02) | false |

## A5 900행 초과 (11)

| file | lines |
|---|---|
| 01-requirements/03-personas-and-use-cases.md | 901 |
| 01-requirements/04-user-stories-and-acceptance-criteria.md | 901 |
| 02-architecture/02-component-architecture.md | 994 |
| 02-architecture/05-plugin-architecture.md | 979 |
| 02-architecture/06-orchestration-and-workflows.md | 1023 |
| 02-architecture/07-multi-tenancy-and-security-architecture.md | 910 |
| 04-pipelines/01-pipeline-framework.md | 1112 |
| 04-pipelines/17-post-processing-and-context-packing.md | 1084 |
| 08-evaluation/04-llm-judge-and-generation-quality.md | 951 |
| 09-operations/02-configuration-reference.md | 1007 |
| 11-roadmap/02-epics-and-backlog.md | 997 |

## A6 review/draft 상태 (2)

| file | status | last_outcome | fixable |
|---|---|---|---|
| 12-appendix/05-phase6-implementation-kit-plan.md | draft |  | false |
| README.md | draft |  | false |

## A7 인용 무결성 (8)

| file | line | ref | problem |
|---|---|---|---|
| 06-adr/README.md | 282 | ADR-0039 | ADR 파일 없음 |
| 09-operations/07-backup-and-disaster-recovery.md | 605 | NFR-REL-17 | 요구사항 문서에 미정의 |
| 12-appendix/00-progress-report.md | 143 | NFR-REL-17 | 요구사항 문서에 미정의 |
| 12-appendix/01-phase3-completeness-review.md | 107 | NFR-REL-17 | 요구사항 문서에 미정의 |
| 12-appendix/02-phase4-5-plan.md | 19 | ADR-0039 | ADR 파일 없음 |
| 12-appendix/02-phase4-5-plan.md | 154 | NFR-REL-17 | 요구사항 문서에 미정의 |
| 12-appendix/03-bible-amendment-triage-input.md | 32 | ADR-0039 | ADR 파일 없음 |
| 12-appendix/06-traceability-matrix.md | 30 | NFR-REL-17 | 요구사항 문서에 미정의 |

## A8 확인 필요 (122)

| file | count |
|---|---|
| 00-vision/00-design-brief.md | 2 |
| 00-vision/01-vision-and-goals.md | 4 |
| 00-vision/02-design-principles.md | 2 |
| 00-vision/03-glossary.md | 16 |
| 00-vision/04-scope-and-non-goals.md | 18 |
| 01-requirements/02-non-functional-requirements.md | 26 |
| 02-architecture/00-design-bible.md | 11 |
| 02-architecture/01-system-overview.md | 2 |
| 02-architecture/02-component-architecture.md | 6 |
| 02-architecture/03-data-flow-and-document-lifecycle.md | 1 |
| 02-architecture/04-storage-architecture.md | 13 |
| 02-architecture/05-plugin-architecture.md | 10 |
| 02-architecture/06-orchestration-and-workflows.md | 5 |
| 02-architecture/07-multi-tenancy-and-security-architecture.md | 12 |
| 02-architecture/08-deployment-architecture.md | 12 |
| 02-architecture/09-failure-modes-and-resilience.md | 10 |
| 03-contracts/00-contract-overview.md | 3 |
| 03-contracts/01-ingest-request.md | 2 |
| 03-contracts/02-source-document.md | 11 |
| 03-contracts/03-parsed-document.md | 6 |
| 03-contracts/04-normalized-document.md | 3 |
| 03-contracts/07-embedded-chunk-set-and-index-record.md | 3 |
| 03-contracts/09-query-request-and-query-plan.md | 2 |
| 03-contracts/11-context-pack.md | 6 |
| 03-contracts/13-error-model.md | 4 |
| 03-contracts/14-schema-versioning-and-compatibility.md | 1 |
| 03-contracts/15-collection-profile-and-policy-contracts.md | 5 |
| 03-contracts/16-eval-feedback-and-sidecar-contracts.md | 4 |
| 04-pipelines/01-pipeline-framework.md | 1 |
| 04-pipelines/02-fetching-and-source-resolution.md | 21 |
| 04-pipelines/03-parsing-router-and-format-detection.md | 11 |
| 04-pipelines/04-parser-hwpx-and-hwp.md | 34 |
| 04-pipelines/05-parser-pdf.md | 16 |
| 04-pipelines/06-parser-doc-and-docx.md | 10 |
| 04-pipelines/07-parser-html.md | 8 |
| 04-pipelines/08-parser-txt-md-and-others.md | 6 |
| 04-pipelines/09-normalization-and-cleaning.md | 2 |
| 04-pipelines/11-enrichment.md | 7 |
| 04-pipelines/12-embedding.md | 10 |
| 04-pipelines/13-indexing.md | 13 |
| 04-pipelines/14-query-understanding.md | 6 |
| 04-pipelines/15-hybrid-search-and-fusion.md | 6 |
| 04-pipelines/16-reranking.md | 11 |
| 04-pipelines/17-post-processing-and-context-packing.md | 8 |
| 04-pipelines/18-advanced-retrieval-graph-raptor-agentic.md | 5 |
| 04-pipelines/19-update-delete-and-reindexing.md | 2 |
| 05-api/01-api-design-guidelines.md | 4 |
| 05-api/03-retrieval-api.md | 4 |
| 05-api/05-mcp-server.md | 8 |
| 05-api/06-client-sdks.md | 13 |
| 06-adr/0001-license-grade-table-and-d02-interpretation.md | 3 |
| 06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md | 2 |
| 06-adr/0004-deterministic-chunk-id-scoped-record-id-and-ulid-exception.md | 1 |
| 06-adr/0006-pdf-fast-path-pypdfium2-pdftext-replaces-pymupdf.md | 3 |
| 06-adr/0008-ocr-default-rapidocr-ppocrv5-korean.md | 5 |
| 06-adr/0009-embedding-serving-vllm-pooling-tei-inprocess.md | 6 |
| 06-adr/0010-bge-m3-rationale-and-late-interaction-slot.md | 4 |
| 06-adr/0011-kv-and-object-storage-valkey-rustfs-seaweedfs.md | 3 |
| 06-adr/0012-lite-profile-qdrant-only-client-bm25.md | 6 |
| 06-adr/0013-fusion-rrf-k60-then-convex-combination-and-postprocess-order.md | 2 |
| 06-adr/0014-sparse-representation-bge-m3-lexical-leg-kept.md | 3 |
| 06-adr/0015-graph-rag-external-plugin-raptor-core-option.md | 2 |
| 06-adr/0019-chunk-size-tokenizer-defaults-and-recount-stage.md | 1 |
| 06-adr/0021-korean-analyzer-kiwi-promotion-and-interim-mecab-kss.md | 6 |
| 06-adr/0022-observability-genai-semconv-pin-and-license-boundary.md | 1 |
| 06-adr/0024-context-pack-ordering-and-anthropic-search-result-renderer.md | 4 |
| 06-adr/0025-mcp-cursor-pagination-and-tool-set.md | 2 |
| 06-adr/0027-security-context-injection-and-acl-enforcement-points.md | 2 |
| 06-adr/0028-tenant-isolation-tiering-policy.md | 3 |
| 06-adr/0031-profile-schema-extends-and-quality-gates.md | 1 |
| 06-adr/0034-retrieval-hot-path-postgres-independence-and-hydrate.md | 4 |
| 06-adr/0035-python-version-and-toolchain-pins.md | 4 |
| 06-adr/0037-artifact-cache-scope-and-stage-key-composition.md | 1 |
| 06-adr/0038-outbound-egress-policy-and-webhook-signing.md | 3 |
| 06-adr/README.md | 1 |
| 07-tech-landscape/00-summary-and-selection-matrix.md | 5 |
| 07-tech-landscape/01-document-parsing-hwpx-hwp.md | 21 |
| 07-tech-landscape/02-document-parsing-pdf-layout-ocr.md | 35 |
| 07-tech-landscape/03-document-parsing-office-html-text.md | 9 |
| 07-tech-landscape/04-chunking-strategies-and-libraries.md | 28 |
| 07-tech-landscape/05-embedding-models-and-serving.md | 35 |
| 07-tech-landscape/06-vector-and-lexical-index-backends.md | 32 |
| 07-tech-landscape/07-retrieval-techniques-fusion-reranking.md | 36 |
| 07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md | 21 |
| 07-tech-landscape/09-evaluation-and-observability.md | 26 |
| 07-tech-landscape/10-llm-context-optimization-and-mcp.md | 52 |
| 07-tech-landscape/11-existing-rag-platforms-gap-analysis.md | 18 |
| 07-tech-landscape/12-security-multitenancy-pii-and-licensing.md | 61 |
| 07-tech-landscape/13-korean-nlp-tokenization-and-language-resources.md | 28 |
| 07-tech-landscape/14-advanced-rag-graph-raptor-agentic-multimodal.md | 34 |
| 08-evaluation/01-evaluation-strategy.md | 1 |
| 08-evaluation/02-retrieval-metrics-and-harness.md | 9 |
| 08-evaluation/03-golden-dataset-construction.md | 11 |
| 08-evaluation/04-llm-judge-and-generation-quality.md | 23 |
| 08-evaluation/05-benchmark-plan-and-baselines.md | 6 |
| 09-operations/01-deployment-guide.md | 25 |
| 09-operations/02-configuration-reference.md | 4 |
| 09-operations/03-observability.md | 9 |
| 09-operations/04-scaling-and-performance.md | 15 |
| 09-operations/05-security-and-compliance.md | 41 |
| 09-operations/06-runbooks.md | 9 |
| 09-operations/07-backup-and-disaster-recovery.md | 6 |
| 09-operations/08-upgrade-and-migration.md | 7 |
| 10-development/01-repository-structure.md | 8 |
| 10-development/02-development-environment.md | 23 |
| 10-development/03-coding-standards.md | 6 |
| 10-development/04-testing-strategy.md | 25 |
| 10-development/05-ci-cd.md | 30 |
| 10-development/06-plugin-development-guide.md | 6 |
| 10-development/07-contributing.md | 11 |
| 10-development/08-release-process.md | 16 |
| 11-roadmap/01-milestones.md | 3 |
| 11-roadmap/02-epics-and-backlog.md | 6 |
| 11-roadmap/03-risks-and-mitigations.md | 1 |
| 12-appendix/00-progress-report.md | 4 |
| 12-appendix/01-phase3-completeness-review.md | 2 |
| 12-appendix/02-phase4-5-plan.md | 2 |
| 12-appendix/03-bible-amendment-triage-input.md | 33 |
| 12-appendix/04-phase3-document-ledger.md | 15 |
| 12-appendix/05-phase6-implementation-kit-plan.md | 6 |
| 12-appendix/design-proposals/proposal-A-operability-first.md | 1 |
| 12-appendix/design-proposals/proposal-C-simplicity-and-extensibility-first.md | 1 |

## A10 바이블 §14 ↔ openapi.yaml

바이블 54 연산 / openapi 51 연산. 바이블에만: DELETE /v1/subscriptions, POST /v1/subscriptions/{}, POST /v1/eval/runs/{}, POST /v1/eval/runs/{}/report. openapi에만: POST /mcp

## A4 ID 접두 사용 지도

| 접두 | 파일 수 | 총 출현 | 파일(상위 5) |
|---|---:|---:|---|
| PB- | 2 | 46 | 00-vision/01-vision-and-goals.md(30), 01-requirements/03-personas-and-use-cases.md(16) |
| G- | 4 | 87 | 00-vision/01-vision-and-goals.md(57), 01-requirements/03-personas-and-use-cases.md(24), 11-roadmap/01-milestones.md(5), 10-development/07-contributing.md(1) |
| KPI- | 7 | 234 | 00-vision/01-vision-and-goals.md(70), 01-requirements/03-personas-and-use-cases.md(68), 11-roadmap/01-milestones.md(54), 11-roadmap/02-epics-and-backlog.md(15), 10-development/07-contributing.md(13) |
| SC- | 2 | 26 | 00-vision/01-vision-and-goals.md(25), 01-requirements/03-personas-and-use-cases.md(1) |
| DF- | 2 | 35 | 00-vision/01-vision-and-goals.md(23), 01-requirements/03-personas-and-use-cases.md(12) |
| P- | 25 | 250 | 03-contracts/09-query-request-and-query-plan.md(43), 11-roadmap/03-risks-and-mitigations.md(32), 03-contracts/11-context-pack.md(28), 03-contracts/03-parsed-document.md(21), 04-pipelines/14-query-understanding.md(20) |
| DP- | 3 | 329 | 00-vision/02-design-principles.md(321), 06-adr/README.md(5), 00-vision/04-scope-and-non-goals.md(3) |
| DRC- | 1 | 40 | 00-vision/02-design-principles.md(40) |
| T- | 3 | 103 | 11-roadmap/03-risks-and-mitigations.md(63), 00-vision/02-design-principles.md(33), 02-architecture/01-system-overview.md(7) |
| GL- | 8 | 67 | 00-vision/03-glossary.md(33), 03-contracts/09-query-request-and-query-plan.md(10), 02-architecture/00-design-bible.md(8), 06-adr/0005-doc-version-content-hash-only-and-acl-payload-update.md(5), 06-adr/0010-bge-m3-rationale-and-late-interaction-slot.md(4) |
| PL- | 1 | 236 | 00-vision/03-glossary.md(236) |
| NFR- | 7 | 62 | 01-requirements/02-non-functional-requirements.md(42), 02-architecture/07-multi-tenancy-and-security-architecture.md(11), 02-architecture/09-failure-modes-and-resilience.md(3), 02-architecture/03-data-flow-and-document-lifecycle.md(2), 08-evaluation/05-benchmark-plan-and-baselines.md(2) |
| UC- | 5 | 255 | 01-requirements/03-personas-and-use-cases.md(215), 12-appendix/06-traceability-matrix.md(20), 08-evaluation/01-evaluation-strategy.md(10), 02-architecture/03-data-flow-and-document-lifecycle.md(6), 01-requirements/04-user-stories-and-acceptance-criteria.md(4) |
