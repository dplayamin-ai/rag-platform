---
title: 6단계 실행 계획 — 구현 킷과 M1 lite 레퍼런스 (동작 우선)
status: draft
owner: architecture
version: 0.1.0
last_updated: 2026-09-23
depends_on: ["02-phase4-5-plan.md", "00-progress-report.md", "../02-architecture/00-design-bible.md", "../10-development/01-repository-structure.md", "../11-roadmap/01-milestones.md"]
---

# 6단계 실행 계획: 구현 킷과 M1 lite 레퍼런스

## 목적

설계 문서만으로는 신뢰를 얻지 못한다. 6단계는 **문서를 동작하는 것으로 바꾸는 최소 단위**를 만든다. 목표는 두 가지다. (1) 프론티어 모델을 쓰는 개발자 누구나 이 저장소를 받아 바이브 코딩으로 플랫폼을 구축·확장할 수 있게 하는 **구현 킷(implementation kit)**, (2) 킷이 실제로 동작함을 증명하는 **M1 lite 레퍼런스 구현**(HWPX·PDF 수집 → 하이브리드 검색 → 인용 포함 ContextPack, MCP 도구). 공개는 이 둘이 갖춰진 뒤에 한다.

## 범위

- 포함: 레퍼런스 골격 저장소, 계약·플러그인 적합성 키트, 표본 코퍼스와 미니 골든셋, 어댑터 스파이크 3종, 구현 작업 패키지(WP) 60~80개, M1 lite 레퍼런스 구현, 공개 준비(라이선스·README·내부 기록 분리).
- 제외: standard/premium 프로파일(Temporal·OpenSearch·GPU 리랭커)의 구현, GraphRAG·RAPTOR, 영어 전문 번역. 이들은 M2 이후 로드맵([마일스톤](../11-roadmap/01-milestones.md))을 따른다.
- 전제: 4·5단계([계획](02-phase4-5-plan.md)) 완료. 계약·스키마·바이블은 6단계에서 코드가 요구하는 경우에만 바이블 §1.2 절차로 고친다.

## 1. 원칙

1. **동작이 정의다.** 모든 산출물은 실행으로 확인한다(테스트 통과, compose 기동, e2e 시연). 실행 확인이 없는 코드는 킷에 넣지 않는다.
2. **"확인 필요"는 스파이크로 닫는다.** 외부 라이브러리를 부르는 코드는 실제 설치·호출로 검증한 뒤 문서의 표기를 갱신한다. 4단계 감사 A8 목록이 스파이크의 체크리스트다.
3. **계약이 정본, 코드는 생성.** Pydantic 모델은 `schemas/`에서 생성기로 만들고 사람이나 모델이 손으로 쓰지 않는다. 골든 예시는 곧 테스트 픽스처다.
4. **작게, 검증 가능하게.** 작업 패키지 하나는 파일 1개·시그니처·테스트를 갖는 3~5k 토큰 자기완결 단위다(무료·소형 모델도 처리 가능하도록).
5. **비용은 4단계 전략을 그대로.** 스크립트·생성기 우선, 코드 작성은 Sonnet, 스파이크와 보안·ACL·상태 기계 리뷰만 Opus. 사람(사용자) 체크포인트는 골든셋 검수와 공개 판단 두 곳.

## 2. 작업 분해

### 6A 레퍼런스 골격(scaffold)

| 산출물 | 내용 | 근거 문서 |
|--------|------|-----------|
| 모노레포 초기화 | `pyproject.toml`(uv workspace), 패키지 레이아웃 `src/rag_platform/`, `plugins/`, `sidecars/`, `deploy/compose/`, `tests/`, `schemas/`(기존), `tools/` | [저장소 구조](../10-development/01-repository-structure.md), [개발 환경](../10-development/02-development-environment.md) |
| 툴체인 | ruff, mypy strict, import-linter 계층 규칙은 **바이블 §12 의존 방향 그대로**(`contracts ← sdk ← plugins \| adapters \| pipelines \| retrieval \| render ← orchestration \| ledger \| storage \| security \| profiles \| settings \| eval ← api \| mcp \| cli`), pre-commit, justfile | [코딩 표준](../10-development/03-coding-standards.md), 바이블 §12, ADR-0035 |
| 계약 패키지 | `schemas/*.schema.json` → Pydantic v2 모델 생성(datamodel-code-generator 또는 자체 생성기), `common-types` 열거 → `StrEnum`, 생성 스크립트와 CI 검사(스키마 변경 시 재생성 강제) | [계약 개요](../03-contracts/00-contract-overview.md), 바이블 §5.7 |
| 코어 스텁 | `Stage` Protocol, `PipelineContext`/`LocalContext`, `ArtifactStore`(file://), `PluginRegistry`(entry points), 프로파일 로더(`profile.schema.json` 검증) | [컴포넌트 아키텍처](../02-architecture/02-component-architecture.md), [플러그인 아키텍처](../02-architecture/05-plugin-architecture.md), [파이프라인 프레임워크](../04-pipelines/01-pipeline-framework.md) |
| CI | PR: lint·type·unit·contract·스키마 diff·라이선스 게이트(pip-licenses + liccheck)·문서 감사(`tools/audit-docs.mjs`) | [CI/CD](../10-development/05-ci-cd.md) |

### 6B 적합성 키트(conformance kit)

| 산출물 | 내용 |
|--------|------|
| 계약 왕복 테스트 | 계약 문서의 모든 JSON 예시를 픽스처로 추출 → 스키마 검증 → Pydantic 파싱 → 직렬화 → 원본과 동치. `tools/validate-contracts.mjs`와 결과 일치 |
| 플러그인 적합성 테스트 | 확장 지점 14종별 추상 테스트 클래스(ADR-0032): 시그니처, 계약 입출력, 멱등성, `StageError` 분류, 관측 속성. 플러그인 저장소가 상속해 실행 |
| 결정적 키 벡터 | `H()` 결합식·`record_id`·`point_id` 고정 벡터(ADR-0004의 적합성 벡터를 실행 가능한 테스트로) |
| 프로파일 검증 | lite/standard/premium/korean-gov YAML이 로더 검증을 통과하고 `profile_hash`가 안정적 |

### 6C 표본 코퍼스와 미니 골든셋

| 항목 | 내용 |
|------|------|
| 코퍼스 | 공공누리 제1유형 등 재배포 가능한 공개 HWPX·PDF·HTML 20~50건(중앙부처 보도자료, 지자체 고시, 법령 해설, 표 중심 문서 포함). 출처·라이선스 매니페스트(`samples/MANIFEST.json`) |
| 골든셋 | 질의 50~100개(사실·절차·비교·표 조회·정답 없음 포함), TREC qrels + `answer_spans` JSONL([골든 데이터셋 구축](../08-evaluation/03-golden-dataset-construction.md)). 합성 초안은 Sonnet, **검수는 사람(사용자)** |
| 베이스라인 기록 | M1 lite에서 B0(dense-only)·B1(dense+BM25)·B3-lite 수치를 측정해 README에 기록. 브리프 §7 목표와의 거리를 숫자로 공개 |

### 6D 어댑터 스파이크 3종("확인 필요" 닫기)

| 스파이크 | 확인 대상 | 산출물 |
|----------|-----------|--------|
| HWPX 파서 | python-hwpx 6.4.x 객체 모델·lxml 경로, 표 병합 셀, 개요 레벨, BinData, `element_path` 규약, 예외 타입 | 동작하는 `parser.hwpx` 어댑터 + 표본 문서 회귀 테스트 + [파서 문서](../04-pipelines/04-parser-hwpx-and-hwp.md) 갱신 |
| Qdrant lite 백엔드 | named vectors(dense + `sparse_bm25`), payload 인덱스, 사전 필터, `record_id`→`point_id`, 형태소 토큰화 + BM25 TF 포화값 계산(ADR-0012) | `index_backend.qdrant` 어댑터 + 통합 테스트(testcontainers) |
| 임베더 | `Embedder` Protocol과 어댑터 골격(배치·질의/문서 비대칭·정규화·`embedding_space_id`)을 작성하고, **모델 가중치 다운로드는 보류**(사용자 결정 2026-09-23). 1층 검증은 결정적 `FakeEmbedder`(해시 기반 벡터, 차원·정규화 규약 준수)로 수행하며, BGE-M3 ONNX·TEI 실측은 `needs_model` 마커로 보류 원장에 등재 | `embedder` 어댑터 골격 + FakeEmbedder + 보류 테스트(실제 모델 회귀는 다른 머신) |

스파이크는 Opus가 수행한다(라이브러리 API 탐색·에러 해석이 필요). 각 스파이크는 문서의 "확인 필요"를 실측값으로 바꾸는 PR을 동반한다.

### 6E 구현 작업 패키지(WP) 생성

- 범위: M1 lite 구현에 필요한 60~80개. 형식은 [4·5단계 계획](02-phase4-5-plan.md)에서 논의한 패키지 템플릿: `WP-nnn`, 파일 경로, 목표, 입출력 계약 발췌(필드·열거값 복사), 불변식, 시그니처, 금지 사항, 단계, **테스트 파일과 픽스처 포함**, 완료 기준 = 테스트 통과.
- 생성: 스크립트가 바이블·계약·파이프라인 문서에서 시그니처·필드·열거를 추출하고, Sonnet이 테스트와 단계를 채운다(패키지 4~6개 묶음당 에이전트 1개).
- 언어: 식별자·지시문 영어, 요약 한국어. 소형·무료 모델 시범용으로 순수 로직 WP 10개를 표시한다.
- 저장: `docs/13-implementation/wp/WP-nnn-<slug>.md` + `tests/`(빈 테스트 파일은 두지 않고 WP와 함께 커밋).

### 6F M1 lite 레퍼런스 구현

| 순서 | 모듈 | 완료 기준 |
|-----:|------|-----------|
| 1 | contracts, core(Stage·Context·ArtifactStore·Registry·프로파일 로더), LocalRunner | 계약 왕복·적합성 테스트 통과 |
| 2 | fetch(file, http), detect, parse(txt·md·html·pdf 텍스트 경로, hwpx 스파이크 어댑터), normalize | 표본 코퍼스 전량 `ParsedDocument` 생성, provenance 무결성 테스트 |
| 3 | chunk(StructureAwareChunker 512/2048/64, 표 행 그룹), enrich(결정적 `context_prefix`, 형태소 키워드) | 청크 경계·부모/자식 불변식 테스트, 한국어 예시 스냅샷 |
| 4 | embed(BGE-M3), index(Qdrant lite, IndexCommit 단일 백엔드 사가) | 재실행 멱등성(같은 입력 → 같은 `record_id`·해시) |
| 5 | plan(규칙 경로) → retrieve(dense·sparse_bm25 병렬) → fuse(RRF) → hydrate → postprocess(dedup·parent_expand) → pack(litm, cite_id) → render(markdown, anthropic search_result) | 골든셋 nDCG@10·Recall@20 측정, 인용 역매핑 테스트 |
| 6 | API(`POST /v1/ingest`, `GET /v1/jobs/{id}`, `POST /v1/query`, `POST /v1/render`), MCP 서버(`search`, `get_document`, `list_collections`, 커서) | e2e: compose 기동 → 표본 수집 → 질의 → 인용 포함 ContextPack; Claude Code에서 MCP로 검색 시연 |
| 7 | `deploy/compose/lite.yaml`(PostgreSQL·Qdrant·Valkey·RustFS 또는 file://·api·worker), 5분 기동 스크립트, 스모크 테스트 | 새 머신에서 README만 보고 10분 내 기동 재현 |

리랭커·OpenSearch·Temporal은 M1에서 끄고(lite 프로파일), 인터페이스와 적합성 테스트만 갖춘다.

### 6G 공개 준비

- `LICENSE`(Apache-2.0), `NOTICE`, `CONTRIBUTING.md`, 보안 보고 채널, 행동 강령.
- `README.md` 한국어 + 영어 요약, 5분 quickstart, 측정된 베이스라인 수치, 로드맵.
- 내부 기록 분리: `PAYMENT.MD`, 진행 보고서, 저널, `tools/phase3/results/`는 공개 저장소에서 제외(별도 `internal/` 또는 비공개 브랜치).
- "확인 필요" 잔여 항목은 GitHub 이슈로 변환(라벨 `needs-verification`).
- 릴리스 `v0.1.0-alpha` 태그와 릴리스 노트(브레이킹·재색인 필요 플래그 규약 시범).

## 3. LLM 전략과 예상 비용

| 하위 단계 | 담당 | 에이전트 | 토큰(추정, 경량 모드 실측 3~4M/에이전트 기준) |
|-----------|------|--------:|--------------:|
| 6A 골격 | 스크립트·생성기 + Sonnet | 4~6 | 15~25M |
| 6B 적합성 키트 | 스크립트(픽스처 추출) + Sonnet | 6~8 | 20~30M |
| 6C 코퍼스·골든셋 | Sonnet(합성 초안) + **사람 검수** | 4~6 | 15~25M |
| 6D 스파이크 3종 | **Opus** (실행 환경 필요) | 3~6 | 30~60M |
| 6E WP 생성 | 스크립트 + Sonnet | 15~20 | 50~80M |
| 6F M1 구현 | Sonnet(WP 구현) + Opus(보안·상태 기계·ACL 리뷰 5) | 45~65 | 150~250M |
| 6G 공개 준비 | Sonnet | 2~3 | 8~12M |
| **합계** | | **80~115** | **0.29~0.48B** |

3단계(4.2B)와 비교하면 10분의 1 이하다. 단, 6D·6F는 **코드 실행 결과에 따라 반복**되므로 상한을 넉넉히 본다. 메인 세션은 Opus로 운영한다.

## 4. 결정이 필요한 항목

| ID | 결정 | 제안 |
|----|------|------|
| D6-1 | 실행 환경 | **확정(§8)**: VDI 개선 불가 → uv 관리 Python 3.12로 1층 검증, Docker·GPU 의존은 모의 객체 검증 + 보류 원장으로 다른 머신 인계 |
| D6-2 | 표본 코퍼스 출처·라이선스 | 공공누리 제1유형 문서만. 목록은 6C 첫 작업으로 작성해 사용자 승인 |
| D6-3 | M1 범위 | lite 프로파일만(Qdrant 단독, 리랭커 끔, LocalRunner, Temporal 없음). HWPX는 스파이크 결과에 따라 M1 포함 여부 결정(포함 목표) |
| D6-4 | 공개 저장소·문서 라이선스 | GitHub 조직명·저장소명 확정. 코드 Apache-2.0, 문서도 Apache-2.0(단일 라이선스로 단순화) |
| D6-5 | 사람 체크포인트 | 골든셋 검수(6C), 스파이크 결과 검토(6D), 공개 판단(6G) 세 곳. 그 외는 자율 진행 |

## 5. 일정(실제 경과 시간, 사람 체크포인트 제외)

| 하위 단계 | 소요 | 의존 |
|-----------|------|------|
| 6A | 1~2일 | 4·5단계 완료, D6-1 |
| 6B | 1~2일 | 6A |
| 6C | 2~3일 + 검수 | D6-2 |
| 6D | 3~5일 | 6A, D6-1 |
| 6E | 2~3일 | 6A, 6D(어댑터 WP는 스파이크 후) |
| 6F | 1~2주 | 6B~6E |
| 6G | 1~2일 | 6F |
| **합계** | **약 3~5주** | |

## 6. 완료 기준(Definition of Done)

1. 새 머신에서 README quickstart대로 `compose up` → 표본 코퍼스 수집 → 한국어 질의 → 인용 포함 ContextPack까지 10분 내 재현.
2. 계약 왕복·적합성·단위·통합 테스트와 `validate-contracts`·`audit-docs` 전부 통과(CI 녹색).
3. 미니 골든셋에서 B0·B1·B3-lite nDCG@10·Recall@20 측정값이 README에 기록됨.
4. HWPX 표 병합 셀·개요 레벨이 `ParsedDocument`로 보존되는 회귀 테스트 통과.
5. Claude Code(또는 임의 MCP 클라이언트)에서 `search` → `get_document` 시연 기록.
6. 공개 저장소에 내부 기록이 없고, "확인 필요" 잔여가 이슈로 추적됨.

## 7. 리스크

| 리스크 | 완화 |
|--------|------|
| 실행 환경·프록시 문제로 스파이크 지연 | D6-1을 6단계 첫 작업으로. 미러 불가 시 모델 가중치·휠을 수동 반입 |
| python-hwpx Alpha 릴리스 변동 | 상한 고정(`>=6.4,<7`) + 표본 회귀 테스트(pin-and-bump) |
| 골든셋 편향(작은 표본) | 질의 유형 배분 고정, 정답 없음 질의 포함, 결과는 "미니 골든셋 기준"으로만 주장 |
| WP 구현이 계약을 임의 수정 | 계약 패키지는 생성물이며 수정 금지(CI가 재생성 diff로 차단) |
| 공개 후 기대치 과대 | README에 M1 lite 범위와 미구현 목록을 명시 |

## 8. 실행 환경 제약과 3층 검증 전략(2026-09-23 확정)

작업 머신은 VDI(Windows, Python 미설치·Docker·WSL 없음·GPU 없음·환경 개선 불가)다. 실측: `uv 0.12`로 Python 3.12 가상환경 생성과 PyPI 설치가 프록시를 통과하고, Hugging Face·GitHub·PyPI·PyTorch 휠에 접근 가능하며, Qdrant는 Windows 바이너리(v1.19.1)가 있다. 따라서 D6-1은 "VDI에서 작성·1층 검증, 2·3층 검증은 다른 머신으로 인계"로 확정한다(사용자 합의: "모의 객체까지 반영하면 충분").

| 층 | 대상 | VDI에서 | 인계 방식 |
|----|------|---------|-----------|
| 1 여기서 검증 | 순수 Python 코드·단위 테스트·계약 왕복·HWPX 파서(표본 파일)·Qdrant 로컬 모드·ONNX CPU 임베더·FastAPI TestClient e2e·ruff·mypy·정적 LLM 코드 리뷰 | 작성 + 실행 검증 + 수정 완료 | 없음 |
| 2 Docker/Linux 필요 | compose 기동, PostgreSQL·Valkey 통합 테스트, TEI 컨테이너, 배포 가이드 실행 확인 | 작성 + **모의 객체(mock)·인메모리 대역으로 인터페이스 단위 검증** | pytest 마커 `needs_docker`, 보류 원장 등재 |
| 2b 모델 가중치 필요 | BGE-M3 ONNX/TEI 임베딩 실측, 리랭커·OCR 모델 회귀 테스트 | 작성 + `FakeEmbedder`·모의 응답으로 인터페이스 검증(**모델 다운로드 보류**, 사용자 결정) | 마커 `needs_model`, 보류 원장 등재 |
| 3 GPU 필요 | 리랭커·GPU 임베딩 처리량, PaddleOCR GPU | 작성 + 모의 응답 검증 | 마커 `needs_gpu`, 보류 원장 등재 |

인계 장치(6A 골격에 포함):

- `pyproject.toml` + `uv.lock` + `.python-version` — 다른 머신은 `uv sync` 한 번으로 동일 환경.
- pytest 마커 `needs_docker`·`needs_model`·`needs_gpu`·`needs_network`, `tools/verify/run-deferred.sh`(Linux) — 보류 검증 일괄 실행. 6F의 e2e는 `FakeEmbedder`로 검색 경로 전체(질의 임베딩 → 하이브리드 → 융합 → 팩)를 검증하고, 검색 품질 수치(골든셋 nDCG)는 실제 모델이 들어가는 다른 머신에서 측정한다.
- `docs/12-appendix/09-deferred-verification-ledger.md` — 코드 주석 `# DEFERRED:`와 마커에서 스크립트(`tools/verify/gen-deferred-ledger.mjs`)로 생성하는 보류 항목 원장(무엇·어떻게·기대 결과·상태).
- 루트 `HANDOFF.md` — 다른 머신의 첫 30분 절차(설치 → `uv sync` → 보류 테스트 → 실패분 수정). `CLAUDE.md`에 "VDI 작성, 2·3층 미검증" 표기.
- 테스트 대역: 원장(PostgreSQL)·KV(Valkey)·임베딩 서버·인덱스 백엔드는 Protocol 뒤에 두고 인메모리 구현을 함께 작성한다. 이는 바이블의 프로파일이 아닌 **테스트 대역**이며 운영 구성으로 승격하지 않는다.
- 저장소: 5단계 마감 시 `git init` + 단계별 커밋(원격은 회사 정책에 따라 후속). 다른 머신은 클론 또는 zip으로 이어받는다.

연휴 자율 진행 순서: 4·5단계 마감 → 6A → 6B → 6D(3종 모두 1층) → 6E → 6F 코어(1층 범위) → 2·3층은 작성 후 보류 원장 등재. 6C 골든셋은 초안까지(검수는 사람), 6G 공개 판단은 보류.

## 결정 사항 요약

- **결정(D6-1):** 실행 환경은 VDI이며 개선 불가. 1층은 여기서 검증, 2·3층은 모의 객체로 인터페이스 검증 후 보류 원장·마커·HANDOFF.md로 다른 머신에 인계한다.
- **결정:** 6단계는 구현 킷(6A·6B·6C·6E)과 M1 lite 레퍼런스(6D·6F)를 함께 만들고, 공개(6G)는 완료 기준 6항을 모두 충족한 뒤에 한다.
- **결정:** 모델 배분은 스크립트·생성기 → Sonnet → Opus(스파이크·보안 리뷰) 순이며, 사람 체크포인트는 세 곳이다.
- 미정: D6-1~D6-5.

## 미해결 이슈

- 4단계 감사 A8("확인 필요" 1,267곳) 중 M1 범위 밖 항목의 처리(이슈 전환 시점).
- 표본 코퍼스에 스캔 PDF(OCR 경로)를 포함할지: M1 lite는 RapidOCR CPU를 포함하되 코퍼스 비중은 소량 제안.

## 참조

- [4·5단계 계획](02-phase4-5-plan.md) · [진행 보고서](00-progress-report.md) · [마일스톤](../11-roadmap/01-milestones.md) · [저장소 구조](../10-development/01-repository-structure.md) · [테스트 전략](../10-development/04-testing-strategy.md) · [플러그인 개발 가이드](../10-development/06-plugin-development-guide.md)
