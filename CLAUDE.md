# RAG Platform — 프로젝트 지침

> 이 파일은 Claude Code가 자동으로 읽는 형식이다. 다른 코드 에이전트(Codex·Cursor·Gemini CLI 등)는 같은 규칙의
> 에이전트 중립 요약본 `AGENTS.md`를 먼저 읽는다 — 두 파일이 어긋나면 이 파일(더 상세)이 정본이다.

RAG Platform은 수집된 문서(HWPX·HWP·PDF·DOC/DOCX·TXT·HTML)의 URI·메타데이터를 API로 받아
파싱 → 정규화 → 의미 청킹 → 보강 → 임베딩 → 하이브리드 인덱싱을 수행하고,
LLM이 바로 참고할 Top-K Context Pack을 리트리벌 API와 MCP로 제공하는 오픈소스(Apache-2.0) 플랫폼이다.

**현재 상태(2026-09-24): 설계 완료, 6단계 6A·6B·6D·6E·6F 완료 — M1 lite 코어가 층 1(순수 Python·Qdrant 로컬 모드·`FakeEmbedder`·`TestClient`)에서 구현·검증됨(pytest 886 통과·27 xfail). 층 2(Docker)·2b(모델)·3(GPU)은 미검증(`HANDOFF.md`).**
저장소에는 `docs/`(설계 문서)·`schemas/`(JSON Schema 정본) 외에 실행·검증되는 코드가 있다:
`contracts/`(스키마에서 생성한 Pydantic v2 계약 모델), `sdk/`·`storage/`·`plugins/`·`profiles/`·
`orchestration/local/`(코어 프레임워크와 로컬 실행기), `testing/`(적합성 키트 + 인메모리 테스트 대역),
`adapters/`의 3종 스파이크(HWPX 파서, Qdrant lite 인덱스 백엔드, TEI/vLLM BGE-M3 임베더 — 모델 가중치
없이 결정적 가짜로 검증). 그 밖의 §12 모듈(`api`·`cli`·`eval`·`korean`·`ledger`·`mcp`·`pipelines`·`render`·
`retrieval`·`security`·`settings`·`telemetry`·`orchestration/{outbox,temporal}`, `adapters/`의 나머지
확장 지점)은 아직 패키지 스텁(docstring뿐)이다 —
코드가 동작하는 것처럼(설치 절차·벤치마크 수치 포함) 쓰지 마라. 구현되지 않은 범위는 전부 "초안 목표"다.

## 앵커 우선순위

**설계 브리프 > 설계 바이블 > ADR > 개별 설계 문서.** 충돌하면 상위 문서가 이긴다.
개별 문서가 바이블과 어긋나면 문서 쪽을 고친다.
바이블이 틀렸다고 판단되면 코드를 바이블에 맞추지 말고, 그 문서의 `## 미해결 이슈`에 개정 제안만 남긴다(절차는 §3).

- 브리프: `docs/00-vision/00-design-brief.md` — 요구사항, D-01~D-20 확정 결정, 문서 규약(§9).
- 바이블: `docs/02-architecture/00-design-bible.md` — 결정 레지스터, 계약 인벤토리, 명명·열거 정본.
  **약 281KB(287,307바이트, v1.3.0). 절대 통째로 읽지 마라.**
  먼저 `grep -n "^#" docs/02-architecture/00-design-bible.md`로 절 헤더를 찾는다.
  필요한 절만 `Read`(offset/limit)로 읽는다.
  절을 인용할 때는 반드시 절 번호를 쓴다(예: "바이블 §5.7 `item_kind`").
- ADR: `docs/06-adr/0001-…` ~ `0039-…`(38건 + 인덱스).
  목록·상태값·발의 절차는 `docs/06-adr/README.md`.
  ADR은 바이블 표를 바꾸지 못한다 — 근거와 대안을 기록하는 문서일 뿐이다.
- 그 밖의 진입점: `docs/README.md`(문서 지도, 읽기 순서), `docs/12-appendix/00-progress-report.md`(진행 상황의 단일 원천), `DEVELOPER.md`(개발자 입문 강좌 — 전체 흐름·코드 지도·게이트), `MANUAL.md`(사용자 매뉴얼 — CLI·API·MCP 계약·문제 해결).

## 1. 작업 유형별로 무엇을 먼저 읽나

작업을 시작하기 전에 아래 순서대로 읽는다. 한 번에 다 읽지 말고, 바이블 항목은 항상 grep 후 절만 읽는다.

**계약(`schemas/*`, `contracts/*`) 작업**
1. `docs/03-contracts/00-contract-overview.md`
2. 바이블 §5(계약 인벤토리 정본, grep으로 하위 절 탐색)
3. `schemas/{대상}.schema.json`
4. 대응하는 `docs/03-contracts/NN-*.md`
5. 관련 ADR(예: 0002, 0004, 0030, 0036)

**파이프라인 스테이지(fetch/parse/chunk/enrich/embed/index/retrieve 등)**
1. `docs/04-pipelines/01-pipeline-framework.md`
2. 대응하는 `docs/04-pipelines/NN-{stage}.md`
3. 바이블 §4(스테이지 파이프라인 정본)
4. 바이블 §12(모듈/패키지 맵에서 `adapters/` 서브패키지 확인)
5. 관련 ADR

**API(REST/SSE/MCP)**
1. `docs/05-api/01-api-design-guidelines.md`
2. 대응하는 `docs/05-api/0N-*.md`(예: `03-retrieval-api.md`, `05-mcp-server.md`)
3. `docs/05-api/openapi.yaml`
4. 바이블 §14(API 표면 정본)
5. ADR-0018, ADR-0025

**인프라·배포**
1. `docs/02-architecture/08-deployment-architecture.md`
2. `docs/09-operations/01-deployment-guide.md`
3. `docs/10-development/01-repository-structure.md`
4. 바이블 §13(저장소 정본)
5. ADR-0011

**평가(golden set/harness)**
1. `docs/08-evaluation/01-evaluation-strategy.md`
2. `docs/08-evaluation/02-retrieval-metrics-and-harness.md`
3. `docs/08-evaluation/03-golden-dataset-construction.md`
4. 바이블 §3.1 D-12
5. ADR-0023

**플러그인(외부 확장) 개발**
1. `docs/02-architecture/05-plugin-architecture.md`
2. `docs/10-development/06-plugin-development-guide.md` §1(개발 흐름)
3. 바이블 §4.1(`Stage` 5멤버)
4. ADR-0032

## 2. 절대 규칙

1. **계약 정본은 `schemas/*.schema.json`이다.**
   `src/rag_platform/contracts/*.py`(Pydantic v2)는 스키마에서 만든 **생성물**이다.
   구현이 시작되면 Pydantic 모델을 손으로 고치지 말고, 스키마를 고친 뒤 생성기를 재실행하라
   ("계약이 정본, 코드는 생성" — `docs/12-appendix/05-phase6-implementation-kit-plan.md` §1 원칙 3).
   골든 예시(JSON)의 정본도 각 `docs/03-contracts/NN-*.md`의 `## 예시`이지 테스트 코드가 아니다.
2. **열거값·필드명 철자는 바이블 §5.7(열거 정본)·§6(명명 규약 정본)을 그대로 쓴다.**
   새 값이 필요하면 임의로 추가하지 말고 §3의 바이블 §1.2 변경 절차(ADR 선행)를 따른다.
   CI는 `schemas/*.schema.json`의 열거값 집합과 바이블 §5.7 표를 기계 대조한다 — 불일치는 빌드 실패다.
3. **D-01~D-20(브리프 §4)과 ADR(바이블 §3.3)에 모순되는 코드를 작성하지 마라.**
   확정 결정을 뒤집는 유일한 방법은 새 ADR이다.
4. **기각된 기술을 쓰지 마라**(전부 근거 있는 배제):
   - PyMuPDF / `fitz` — AGPL 인프로세스 링크. 대신 pypdfium2 + pdftext(고속 텍스트), Docling(레이아웃)(ADR-0006).
   - pyhwp를 기본 경로로 사용 — AGPL, 2020년 이후 무릴리스. HWP 5.0 기본은 Java 사이드카(hwplib+hwp2hwpx+hwpxlib), pyhwp는 선택 플러그인뿐(ADR-0007).
   - MinIO — 2026-04 아카이브·AGPL 소스 전용 전환. 로컬 오브젝트 스토리지는 RustFS 또는 SeaweedFS(ADR-0011).
   - Redis를 기본 KV로 사용 — Redis 8 삼중 라이선스(RSALv2/SSPLv1/AGPLv3). 기본은 Valkey(BSD-3, Redis 프로토콜 호환)(ADR-0011).
   - Infinity 임베딩 서버 — BGE-M3 sparse 미생산·릴리스 정체. 서빙은 vLLM pooling + TEI + 인프로세스(ADR-0009).
   - SPLADE-v3 — sparse 표현 기본값 채택에서 기각. 기본은 BGE-M3 sparse(동일 패스)(ADR-0014).
   - jina 계열 임베딩/리랭커 모델 — CC-BY-NC/Qwen Research 라이선스. 기본 프로파일 외 모델(A/B 등급)만 채택(D-16).
   - 저장소 전체에서 `fitz`/`pymupdf`/`hwp5` 임포트는 import-linter `forbidden` 계약으로 기계 차단된다(D-02, ADR-0001).
5. **보안 불변식**
   - 모든 채널·모든 백엔드에서 `tenant_id`·`acl` **사전 필터**를 강제한다(바이블 §10.2). 사후 필터 금지.
   - 리트리벌 결과는 캐시하지 않는다 — ACL 시점성(`as_of`) 때문에 `retrieve` 스테이지의 캐시는 항상 "없음"이다(바이블 §4.3 `retrieve` 행).
   - `SecurityContext`는 서버가 주입하는 읽기 전용 필드이며 요청 본문의 값은 무시한다(D-09, ADR-0027).
   - 멀티테넌시 강제 지점은 17개(E1~E17, 바이블 §10.3).
   - 격리 등급은 `payload_filter`(기본) → `shard_key` → `index_per_tenant`(§10.4)로 승격한다.

## 2-1. 코드 파일 상단 한글 설명 주석(필수)

모든 소스 파일(`src/**/*.py`, `tests/**/*.py`, `tools/**/*.{py,mjs,js}`, `sdk/**/*.ts`, 생성 파일 포함)은 **첫 줄부터 한국어 설명 헤더**로 시작한다. 규칙 전문과 예시는 `tools/phase6/CODE-HEADER-RULE.md`.

- 필수 항목 순서: 역할(한 문장) → 설계 근거(바이블 절·ADR·계약 문서) → 구성(공개 클래스·함수 한 줄씩) → 불변식·주의 → 검증 계층(`1층` / `needs_docker` / `needs_model` / `needs_gpu`, 보류 시 `DEFERRED:`).
- 식별자는 영문 백틱, 본문은 한국어, 6~15줄. 생성 파일은 첫 줄 `GENERATED — 수정 금지. 재생성: <명령>`.
- 코드를 새로 만들거나 크게 고칠 때 헤더도 함께 갱신한다. `ruff D100`으로 존재를, `tools/verify/check-headers.mjs`로 한국어·필수 항목을 검사한다.

## 3. 툴체인·명령

- 언어/런타임: Python **3.12/3.13**(파서 워커 이미지 고정, 3.14는 호환성 검증 후), 계약 모델 **Pydantic v2**,
  API **FastAPI**, 패키지 관리 **uv**(`uv lock --check`가 CI 게이트), 린트 **ruff**,
  타입 **mypy strict**(+`pydantic.mypy`), 계층 규칙 **import-linter**(D-01, ADR-0035).
- 임포트 방향(바이블 §12 정본):
  `contracts ← sdk ← plugins|adapters|pipelines|retrieval|render ← orchestration|ledger|storage|security|profiles|settings|eval ← api|mcp|cli`.
  `docs/12-appendix/05-phase6-implementation-kit-plan.md` §6A는 이를 착수 순서로
  "contracts ← core ← stages ← workflows ← api"로 요약한다.
  `pipelines`·`retrieval`·`render`·`adapters`·`sdk`·`contracts`는
  `temporalio`·`fastapi`·`rag_platform.ledger`·`rag_platform.orchestration`을 임포트하지 않는다
  (계층 규칙 채택은 D-01·ADR-0035; `temporalio` 임포트 금지 린트는 D-17·ADR-0003).
  `adapters`는 `storage`를 모른다(ArtifactRef 로드는 셸). `security`는 `api`·`retrieval`·`adapters/index`에서만
  사용한다 — 즉 `adapters` 하위에서는 `adapters/index`만 `security`를 임포트할 수 있고, 나머지 `adapters/*`는
  `storage`·`security` 모두 임포트하지 않는다(포트는 `sdk`로 받는다).
- `pyproject.toml` extras 6종: `kiwi`, `docling-chunker`, `gpu`(비움, CUDA는 사이드카 이미지), `opensearch`, `temporal`, `eval`(바이블 §6.7).
- 검증 명령:
  - `node tools/validate-contracts.mjs --root <repo>` — 계약·스키마 기계 검증, 0 오류가 아니면 커밋 금지.
  - `node tools/audit-docs.mjs --root <repo>` — 전 문서 기계 감사(링크·frontmatter·열거 철자·ID 접두·분량·"확인 필요" 집계).
- 스키마(계약) 변경 절차는 바이블 §1.2 표를 따른다:
  - 오탈자/설명 보강 = 소유자 직접 patch.
  - 필드·열거값 추가, 기본 파라미터 값 변경 = ADR + 바이블 minor(가산만).
  - 필수화·제거·의미 변경, 명명 변경 = ADR + 바이블 major + 영향 문서 일괄 개정.
  - D-xx 개정 = ADR + 바이블 §3.1 `amended` + 브리프 §4 행 갱신.

## 4. 저장소 구조(현재 구현 범위 + 목표 레이아웃)

정본은 바이블 §12(모듈/패키지 맵)이고, 확장은 `docs/10-development/01-repository-structure.md` §2.1이다.
이 저장소는 `docs/`·`schemas/`·`tools/`·`.claude/`에 더해 `src/rag_platform/`·`tests/`·`deploy/`·`plugins/`·
`samples/`·`sidecars/`가 이미 있다.

**현재 구현 범위(6A+6B+6D+6E/6F F1~F5, `src/rag_platform/` 기준, 2026-09-24)** — 바이블 §12 모듈 맵 중 `lite` 프로파일 전 구간(상세 표는 진행 보고서 §3.2):
- `contracts/`(GENERATED — `tools/contracts_gen.py`가 `schemas/*.schema.json`에서 생성한 Pydantic v2 모델
  93개 파일, 손편집 금지)
- `sdk/`(`stage.py`·`context.py`·`policy.py`·`ports.py`·`hashing.py` — `Stage`/`PipelineContext`/
  `StageContext` 프로토콜, `StagePolicy`, 역할 포트)
- `storage/`(`artifact_store.py`·`keys.py`·`valkey.py`), `plugins/`(`registry.py` — `EXTENSION_POINTS` 14종),
  `profiles/`(`loader.py`·`validate.py`·`builtin/` 내장 4종: `base`/`lite`/`standard`/`premium`(+`korean-gov`)),
  `orchestration/local/`(`runner.py` — 비내구 `LocalRunner`)
- `testing/`(적합성 키트 — `conformance/base.py`·`conformance/kits.py` + `doubles/`의 인메모리 대역 4종
  `FakeEmbedder`/`InMemoryIndexBackend`/`InMemoryKV`/`InMemoryLedger`, 그 외 `contract_roundtrip`·
  `idempotency`·`fuser_equivalence`·`litm_order`·`renderer_citation_roundtrip`·`security_invariants`)
- `adapters/` 수집 어댑터 — `fetch/fsspec_httpx.py`; `parse/`(`format_detector.py`·`router.py`,
  HWPX `hwpx_python_hwpx.py`+`owpml_adapter.py`, `text_charset_markdown_it.py`, `html_trafilatura_docling.py`,
  `pdf_fast_pdftext.py`); `normalize/korean/*`+`normalize/stage.py`; `chunk/`(`structure_aware.py`·
  `table_rows.py`·`recount.py`); `enrich/`(`deterministic_prefix.py`·`korean_keywords.py`·`derived_meta.py`);
  `embed/`(`stage.py`·`sparse_bm25.py`·`inprocess_fake.py`, TEI·vLLM 골격 — 모델 가중치 없이 결정적
  가짜로 검증); `index/`(`stage.py`·`saga.py`·`qdrant/*`, Qdrant 로컬 모드)
- 검색 경로 — `adapters/retrieve/`(`qdrant_dense.py`·`qdrant_sparse_bm25.py`), `adapters/query/`,
  `retrieval/`(`planner.py`·`filters.py`·`channels.py`·`fusion.py`·`hydrate.py`, `postprocess/`
  `relevance_gate`·`dedup`·`mmr`·`parent_expand`, `pack/` `acl_recheck`·`budget_cut`·`reorder`·
  `citation_align`·`packer`), `render/`(`markdown.py`·`anthropic_search_result.py`·`citation_map.py`),
  `korean/`(정규화·규칙 라우터·유니코드 — 순수 로직)
- 파이프라인·표면 — `pipelines/{ingest,query}`, `security/security_context.py`, `api/`(`app.py`·`ingest.py`·
  `jobs.py`·`query.py`·`problems.py`), `mcp/`(`server.py`·`tools.py`·`cursor_store.py`), `cli/main.py`
  (`rag ingest|query|serve|profile`). **주의**: 실 파이프라인 배선은 `cli/main.py`(`ingest_paths`·`run_query_lite`)에만 있다.
  `api/`는 스텁 스테이지·스텁 팩, `mcp/server.py`의 `main()`은 `ToolDeps` 미조립(`NotImplementedError`) — 인증·오류·
  캐시·커서는 실제. API/MCP를 "동작한다"고 쓰지 마라.

**아직 포트/스텁인 §12 모듈** — `ledger`(포트만, PostgreSQL 미연결)·`orchestration/{outbox,temporal}`·
`adapters/{rerank,llm}`·`eval`·`telemetry`·`settings`, OpenSearch 채널, HWP5 사이드카·DOCX·OCR 파서.
`deploy/compose/compose.lite.yaml`과 `.github/workflows/ci.yml`은 작성만 됐고 이 VDI에서 실행하지 못했다.

**작업 패키지(WP)**: 구현 단위 문서는 `docs/13-implementation/wp/WP-nnn-<slug>.md`(21건, 색인
`docs/13-implementation/README.md`)이며, 새 구현은 WP 문서를 먼저 쓰고 같은 커밋에 코드·테스트를 넣는다.
구현 중 발견한 설계 갭은 코드가 바이블을 앞서 바꾸지 않고 결과 `open_issues`(또는 WP 끝 미해결 항목)에 기록해
`node tools/phase6/gen-design-gaps.mjs`로 `docs/12-appendix/10-implementation-design-gaps.md`(186건)에 모은다.

아래는 전체 구현 완료 시 바이블 §12 목표 트리다:

```text
rag-platform/
├── pyproject.toml, uv.lock     # 워크스페이스 루트, extras 6종
├── src/rag_platform/           # contracts/ sdk/ plugins/ adapters/ pipelines/ retrieval/ render/
│                                #   orchestration/ ledger/ storage/ security/ profiles/ korean/ eval/
│                                #   telemetry/ api/ mcp/ testing/ cli/  (L0~L10, §12·§3 참고)
├── schemas/                    # JSON Schema 2020-12 정본(손 작성), 35개 파일
├── docs/                       # 설계 문서 세트(브리프 §8 문서 맵)
├── plugins/                    # A/B 등급 별도 배포 플러그인(rag-plugin-*), 워크스페이스 멤버
├── sidecars/                   # 코어 Python 의존 없는 변환 사이드카(parser-workers, ocr-gpu)
├── sdk/{python,typescript}/    # 클라이언트 SDK(루트 — `src/rag_platform/sdk/`의 인프로세스 프레임워크와 다르다)
├── deploy/{compose,helm}/      # 프로파일별 배포 매니페스트
├── tests/                      # contracts/ adapters/ security/ replay/ eval/
├── samples/, examples/         # 5분 기동 데모 문서, SDK 예제
└── tools/                      # 문서·스키마·헤더 검증기(validate-contracts.mjs, audit-docs.mjs,
                                 #   verify/check-headers.mjs, verify/gen-deferred-ledger.mjs 등)
```

GPL/AGPL(C 등급) 이미지·플러그인(`lo-sidecar`, pyhwp/pymupdf 사이드카)은 이 저장소에 두지 않는다.
별도 저장소 `rag-platform-gpl-sidecars`에서 빌드하고, 이 저장소에는 참조 링크와 Helm `optIn.*`(기본 `false`) 값만 둔다.

## 5. 문서 규약(`docs/` 편집 시)

브리프 §9 요약:

- frontmatter 필수: `title`·`status`·`owner`·`version`·`last_updated`·`depends_on`(계약 문서는 `schema_version`도).
- 한국어 본문 + 영문 식별자. 기술 용어는 처음 등장 시 `한국어(English)` 병기.
- 다이어그램은 Mermaid만(ASCII 아트 금지).
- 상호참조는 브리프 §8 문서 맵에 있는 경로만 상대 링크로 건다.
- 근거 없는 수치·확실하지 않은 사실은 **"확인 필요(as of 2026-09)"**로 표기한다.
- 구조: `# 제목` → `## 목적` → `## 범위` → 본문 → `## 결정 사항 요약` → `## 미해결 이슈` → `## 참조`.
  계약 문서는 `## 스키마`·`## 예시`·`## 불변식`·`## 버전 이력`을 더한다.

문서를 고칠 때:

- frontmatter `version`을 patch 올리고 `last_updated`를 오늘 날짜로 갱신한다.
- 처리된 항목은 그 문서의 `## 미해결 이슈`에서 제거하고, 새로 발견한 것만 추가한다.
- 계약·바이블 표를 바꾸는 변경은 §3 절차(ADR 선행)를 반드시 지킨다 — 문서가 바이블을 앞질러 바뀌는 일은 없다.

## 6. 작업 방식(비용 규율)

`docs/12-appendix/02-phase4-5-plan.md` §1과 `docs/12-appendix/05-phase6-implementation-kit-plan.md` §1의 원칙을 그대로 따른다.

- **스크립트가 먼저, 에이전트(LLM)는 판단에만.** 링크·철자·frontmatter·분량 같은 결정적 검사·치환은 Node 스크립트로 한다.
- **에이전트 1개가 문서 3~6개를 묶어 처리한다.** 문서당 에이전트 1개를 띄우지 마라.
  앵커(브리프·바이블 절) 읽기 비용이 에이전트 단위로 반복 발생한다.
- **리뷰는 경량으로.** 기계 게이트(ruff/mypy/import-linter/`validate-contracts`/`audit-docs`)로 잡을 수 있는 것은 리뷰에 올리지 않는다.
  판단이 필요한 것(보안·ACL·상태 기계 등)만 상위 모델 리뷰로 돌린다.
- **진행 기록은 `docs/12-appendix/00-progress-report.md`에 남긴다**(§3 산출물 현황, §7 재개 절차, §8 통계).
  새 세션은 이 문서 §7.3 재개 절차부터 읽는다.
- **토큰 집계는 `node tools/usage-report.mjs --out PAYMENT.MD`.**

## 7. 6단계 구현 순서(`docs/12-appendix/05-phase6-implementation-kit-plan.md`)

- **6A** 레퍼런스 골격 — uv workspace, 툴체인(ruff/mypy/import-linter), 계약 패키지 생성(스키마 → Pydantic), 코어 스텁(`Stage`/`PipelineContext`/`ArtifactStore`/`PluginRegistry`), CI.
- **6B** 적합성 키트 — 계약 왕복 테스트, 확장 지점 14종별 플러그인 적합성 테스트, 결정적 키 벡터(`H()`/`record_id`/`point_id`), 프로파일 검증.
- **6C** 표본 코퍼스·미니 골든셋 — 공공누리 제1유형 문서 20~50건, 질의 50~100개(TREC qrels + `answer_spans`), 검수는 반드시 사람.
- **6D** 어댑터 스파이크 3종 — HWPX 파서, Qdrant lite 백엔드, 임베더 골격(모델 가중치 다운로드는 보류, `FakeEmbedder`로 1층 검증).
- **6E** 구현 작업 패키지(WP) — `docs/13-implementation/wp/WP-nnn-<slug>.md` + 테스트 동봉.
  (실행은 6F와 합쳐 "WP 우선 구현" 배치 F1~F5로 진행, 21건 완료 — `tools/phase6/wf-6f.js`.)
- **6F** M1 lite 레퍼런스 구현 — **완료(2026-09-24, 층 1)**:
  contracts/core → fetch/parse/normalize → chunk/enrich → embed/index(Qdrant) →
  plan/retrieve/fuse/hydrate/postprocess/pack/render → API/MCP/CLI. compose 기동은 `needs_docker`로 보류.
- **6G** 공개 준비 — LICENSE/NOTICE/CONTRIBUTING, README(한/영), 내부 기록(`PAYMENT.MD`, 진행 보고서, `tools/phase3/results/`) 분리, 잔여 "확인 필요"를 GitHub 이슈로 전환.

**M1 lite 범위(끄는 것)**: `lite` 프로파일만 구현한다.
- 리랭커·OpenSearch·Temporal은 **끈다**(인터페이스와 적합성 테스트만 유지).
- 실행은 `LocalRunner` + Qdrant 단독 하이브리드(`dense` + 형태소 분석기가 계산하는 `sparse_bm25`)만 쓴다.
- GraphRAG/RAPTOR, standard/premium 프로파일, 영어 전문 번역은 M2 이후로 미룬다.

## 8. 테스트·플러그인 핵심 원칙

테스트 8원칙(`docs/10-development/04-testing-strategy.md` §1):

1. 셸이 계약을 강제한다 — 스테이지 코드 안에 검증 호출을 넣지 않는다.
2. 결정성 우선 — 고정 픽스처로 시각·난수·ID를 주입하고 `golden_hash`로 동치를 확인한다.
3. 정본은 하나 — 계약 예시는 `03-contracts/*.md`, 스키마는 `schemas/`, 열거는 바이블 §5.7.
4. `LocalRunner`와 Temporal 두 실행기는 같은 골든 입력에서 동등해야 한다.
5. PR CI는 재생(cassette)만 — 모델·사이드카·외부 LLM 실물 호출은 야간 빌드부터.
6. 보안 불변식(E1~E17)은 최소 한 층(단위/계약/통합/e2e)에서 테스트한다.
7. 품질 기본값 변경은 `EvalReport.gate_result.passed` 게이트 없이 금지한다.
8. 실패는 `StageError.code`·`ProblemDetails.code` 카탈로그 철자로 단정한다(예외 타입으로 단정하지 않는다).

플러그인 확장 지점은 14종이다(D-10):
`fetcher, parser, normalizer, chunker, enricher, embedder, index_backend, query_transformer, retriever, fuser, reranker, postprocessor, packer, evaluator`.
플러그인은 `rag_platform.sdk`·`rag_platform.contracts`(테스트에서만 `rag_platform.testing`)만 임포트한다.
코어 `adapters` 상속, `orchestration`/`api`/`storage`/`ledger` 임포트, 다른 플러그인 임포트는 금지한다(ADR-0032).

## 9. "확인 필요(as of 2026-09)" 표기를 만나면

추측으로 채우지 마라. 실제로 설치·호출·측정해서 닫는다 —
"확인 필요는 스파이크로 닫는다"(`docs/12-appendix/05-phase6-implementation-kit-plan.md` §1 원칙 2).
닫은 뒤에는 해당 문서의 표기를 실측값으로 갱신하고 §5의 규칙대로 `version`을 patch 올린다.
남은 항목의 전체 목록은 4단계 감사 A8 결과
(`docs/12-appendix/00-progress-report.md` §6, `docs/12-appendix/03-bible-amendment-triage-input.md`)를 참고한다.

## 10. 실행 환경 주의(VDI)

이 저장소는 Windows VDI(Docker·WSL·GPU 없음, `uv 0.12`만 있음)에서 작성됐다. **3층 검증 전략**
(`docs/12-appendix/05-phase6-implementation-kit-plan.md` §8)의 층 1(순수 Python·단위 테스트·계약
왕복·Qdrant 로컬 모드·`FakeEmbedder`·`TestClient` e2e)만 이 VDI에서 실행해 통과시켰다. **층
2(Docker: PostgreSQL·Valkey·Qdrant 실서버)·층 2b(모델 가중치: BGE-M3·리랭커·OCR)·층 3(GPU)는 이
VDI에서 실행 검증하지 못했다** — 해당 코드는 Protocol 뒤에 두고 인메모리 대역(`testing.doubles.*`)으로만
단위 검증했다.

- **마커 규칙**: Docker·GPU·외부 네트워크·모델 가중치가 필요한 테스트는 pytest 마커
  `needs_docker`/`needs_model`/`needs_gpu`/`needs_network`로 표시하고, 바로 위에 `# DEFERRED: <무엇을
  어디서 어떻게 검증>` 주석을 남긴다. 이 네 마커는 `pyproject.toml` addopts에서 기본 실행 제외다
  (`-m "not needs_docker and not needs_model and not needs_gpu and not needs_network"`). 마커를 추가·
  변경했으면 `node tools/verify/gen-deferred-ledger.mjs`로
  [`docs/12-appendix/09-deferred-verification-ledger.md`](docs/12-appendix/09-deferred-verification-ledger.md)를
  다시 만든다 — 표는 손으로 편집하지 않는다.
- **모델 가중치 금지**: `needs_model` 테스트를 통과시키려고 이 VDI에서 모델을 내려받지 않는다(사용자
  결정, 2026-09-23). 임베딩·리랭킹·OCR은 결정적 가짜 구현(`FakeEmbedder` 등)으로만 검증한다.
- **다른 머신 인수인계**: Docker가 있는 Linux/macOS 머신에서 층 2를 이어받는 절차는 루트
  [`HANDOFF.md`](HANDOFF.md)(첫 30분 절차, 실패 수정 규칙, 검증되지 않은 범위)를 그대로 따른다.
  `tools/verify/run-deferred.sh`(Linux/macOS)·`run-deferred.ps1`(Windows+Docker)이 그 머신에서
  `docker compose`로 서비스를 올리고 `uv run pytest -m needs_docker`를 실행한다.
  `.github/workflows/ci.yml`의 `deferred` 잡(`workflow_dispatch` 수동 트리거, Docker 서비스 컨테이너
  PostgreSQL·Qdrant·Valkey)이 같은 일을 CI에서 한다.
