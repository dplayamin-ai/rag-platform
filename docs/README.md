---
title: 문서 지도 (Documentation Map)
status: draft
owner: architecture
version: 0.4.0
last_updated: 2026-09-23
---

# RAG Platform 설계 문서 지도

수집된 문서(HWPX·HWP·PDF·DOC/DOCX·TXT·HTML)의 URI와 메타데이터를 API로 받아 파싱·정규화·의미 청킹·보강·임베딩·하이브리드 인덱싱하고, LLM이 최고의 답을 낼 수 있는 Top-K Context Pack을 리트리벌 API와 MCP로 제공하는 오픈소스(Apache-2.0) 플랫폼의 설계 문서 세트다. **3단계(설계 문서 작성)는 2026-09-23에, 4단계(교차 일관성)·5단계(마감)·6단계 6A~6F(구현 킷과 M1 lite 레퍼런스, 층 1 검증)는 2026-09-24에 완료**됐다. 구현 단위 문서(작업 패키지)는 `13-implementation/`에 있다.

## 읽기 순서

1. [설계 브리프](00-vision/00-design-brief.md) — 요구사항, 확정 결정, 문서 규약. **모든 문서의 앵커.**
2. [설계 바이블](02-architecture/00-design-bible.md) — 결정 레지스터, 계약 인벤토리, 스테이지·프로파일·검색 경로 정본. 258KB이므로 절 단위로 읽는다.
3. [기술 지형 종합: 선정 매트릭스](07-tech-landscape/00-summary-and-selection-matrix.md) — 역할별 오픈소스 선정과 근거.
4. [비전과 목표](00-vision/01-vision-and-goals.md) → [설계 원칙](00-vision/02-design-principles.md) → [범위와 비범위](00-vision/04-scope-and-non-goals.md) → [용어집](00-vision/03-glossary.md)
5. [기능 요구사항](01-requirements/01-functional-requirements.md) → [비기능 요구사항](01-requirements/02-non-functional-requirements.md) → [페르소나와 유즈케이스](01-requirements/03-personas-and-use-cases.md) → [사용자 스토리](01-requirements/04-user-stories-and-acceptance-criteria.md)
6. 기술 지형 상세(07) → [계약 개요](03-contracts/00-contract-overview.md)와 계약(03) → [파이프라인 프레임워크](04-pipelines/01-pipeline-framework.md)와 파이프라인(04) → API(05, [openapi.yaml](05-api/openapi.yaml)) → [ADR 인덱스](06-adr/README.md)(06) → 평가(08) → 운영(09) → 개발(10) → 로드맵(11)

## 디렉터리 현황(2026-09-24, 6F 완료)

| 디렉터리 | 내용 | 상태 |
|----------|------|------|
| `00-vision/` | 브리프(v1.2.1), 비전·목표, 원칙, 용어집, 범위 | 완료 |
| `01-requirements/` | FR 217, NFR 184, 유즈케이스 20, 사용자 스토리 91 | 완료 |
| `02-architecture/` | 설계 바이블(v1.2.1) + 시스템 개요·컴포넌트·데이터 흐름·저장소·플러그인·오케스트레이션·보안·배포·회복력(01~09) | 완료 |
| `03-contracts/` + `schemas/` | 17개 문서, JSON Schema 2020-12 35개 | 완료(계약 감사·기계 검증 0 오류) |
| `04-pipelines/` | 프레임워크, 페치, 파서(HWPX/HWP·PDF·DOCX·HTML·TXT), 정규화, 청킹, 보강, 임베딩, 인덱싱, 질의 이해, 하이브리드 융합, 리랭킹, 패킹, 고급 모듈, 갱신·삭제(01~19) | 완료 |
| `05-api/` | 가이드라인, 수집·리트리벌·관리 API, MCP 서버, SDK, 웹훅, `openapi.yaml`(경로 36·연산 51) | 완료 |
| `06-adr/` | ADR 38건(MADR) + 인덱스 README | 완료 |
| `07-tech-landscape/` | 14개 영역 리서치 + 선정 매트릭스 | 완료 |
| `08-evaluation/` | 전략, IR 메트릭·하네스, 골든셋, LLM-judge, 벤치마크, 온라인 피드백 | 완료 |
| `09-operations/` | 배포, 설정, 관측성, 확장, 보안, 런북, 백업·DR, 업그레이드 | 완료 |
| `10-development/` | 저장소 구조, 개발 환경, 코딩 표준, 테스트, CI/CD, 플러그인 개발, 기여, 릴리스 | 완료 |
| `11-roadmap/` | 마일스톤, 에픽·백로그, 리스크 | 완료 |
| `12-appendix/` | [진행 보고서](12-appendix/00-progress-report.md)(단일 진행 원천), [3단계 완전성 검토](12-appendix/01-phase3-completeness-review.md), [4·5단계 계획](12-appendix/02-phase4-5-plan.md), [바이블 개정 요청 통합 목록](12-appendix/03-bible-amendment-triage-input.md), [3단계 문서 원장](12-appendix/04-phase3-document-ledger.md), [6단계 구현 킷 계획](12-appendix/05-phase6-implementation-kit-plan.md), [추적성 매트릭스](12-appendix/06-traceability-matrix.md), [바이블 트리아지 결정](12-appendix/07-bible-amendment-triage-decisions.md), [전파 지시서](12-appendix/08-propagation-directives.md), [보류 검증 원장](12-appendix/09-deferred-verification-ledger.md), [구현 설계 갭 원장](12-appendix/10-implementation-design-gaps.md), 설계 경쟁 제안서 A/B/C, `sources/`(업스트림 참고 사본) | 참고 |
| `13-implementation/` | [작업 패키지 색인](13-implementation/README.md) — WP 21건(수집 전단 101~106, 청킹·보강 201~203, 임베딩·인덱스 301~303, 검색 경로 401~405, API·MCP·CLI 501~504). 구현 중 발견한 설계 갭 180건은 [구현 설계 갭 원장](12-appendix/10-implementation-design-gaps.md) | M1 lite 완료(층 1) |

주의: 3단계 후반 문서 43건(문서 37 + ADR 6)은 경량 모드로 수정되어 독립 검증이 없다. 미해결 이슈 480건(바이블 개정 요청 후보 200건)은 4단계 입력이며, 그 전까지 문서 간 필드명이 어긋나면 **바이블과 `schemas/`가 정본**이다.

## 문서 규약

브리프 §9를 따른다. 한국어 본문·영문 식별자, frontmatter 필수, Mermaid 다이어그램, 상호참조는 브리프 §8 문서 맵 경로만. 계약·스키마를 고치면 `node tools/validate-contracts.mjs --root <repo>`가 0 오류여야 하고, 전 문서 기계 감사는 `node tools/audit-docs.mjs`다.
