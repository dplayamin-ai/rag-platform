# AGENTS.md — 코드 에이전트용 진입 지침 (에이전트 중립)

이 파일은 Claude Code·Codex·Cursor·Gemini CLI·Copilot 등 **어떤 코드 에이전트든** 이 저장소에서 작업을 이어받을 때 가장 먼저 읽는 문서다. 상세 규칙은 [CLAUDE.md](CLAUDE.md)(같은 내용, 더 길다)이고, 두 파일이 어긋나면 CLAUDE.md가 정본이다. 사람 개발자는 [DEVELOPER.md](DEVELOPER.md)부터 읽는 편이 빠르다.

## 1. 이 저장소는 무엇인가 (30초)

문서(HWPX·PDF·HTML·TXT 등)를 수집해 파싱 → 정규화 → 청킹 → 보강 → 임베딩 → 하이브리드 인덱싱하고, LLM에게 줄 Top-K **Context Pack**을 CLI·REST API·MCP로 내주는 오픈소스(Apache-2.0) RAG 플랫폼이다. 설계 문서 151건(`docs/`), JSON Schema 계약 35개(`schemas/`), 그리고 `lite` 프로파일의 **M1 코어 구현**(`src/rag_platform/`, pytest 886 통과)이 들어 있다.

현재 상태(2026-09-24): 수집·검색 전 구간은 **CLI(`rag ingest`/`rag query`)에서 실제 동작**한다. 임베더는 결정적 가짜(`FakeEmbedder`)라 검색 품질은 아직 무의미하고, REST API는 스텁 팩을 돌려주며, MCP는 stdio 조립이 없다. Docker·실제 모델·GPU가 필요한 층은 Windows VDI에서 작성만 되고 **미검증**이다. 정직한 표는 [MANUAL.md §0](MANUAL.md).

## 2. 시작 절차 (순서대로, 건너뛰지 않는다)

1. `git log --oneline -15`로 마지막 커밋과 메시지를 읽는다. 진행 상황의 단일 정본은 [docs/12-appendix/00-progress-report.md](docs/12-appendix/00-progress-report.md) §3.2(코드 실측)·§7.2h(마지막 실행 기록)·§7.3(재개 절차)다. 이전 세션의 산문이 아니라 git 로그·frontmatter·테스트 결과로 상태를 확인한다.
2. 게이트를 재현한다(전부 초록이어야 그다음을 믿을 수 있다):
   ```bash
   uv sync --all-extras --group dev
   uv run ruff check . && uv run ruff format --check .
   uv run mypy src
   uv run lint-imports
   uv run pytest -q                      # 886 passed, 27 xfailed 기대(Windows에서 측정)
   node tools/verify/check-headers.mjs
   node tools/validate-contracts.mjs
   node tools/audit-docs.mjs
   ```
   Linux/macOS에서는 처음 도는 것이다. 실패가 나오면 코드를 고치기 전에 원인을 진행 보고서 §6에 기록한다.
3. 무엇을 할지 정한다. 우선순위는 §5. 새 구현은 반드시 **WP 문서 먼저**(`docs/13-implementation/wp/WP-6xx-<slug>.md`, 본보기 [WP-401](docs/13-implementation/wp/WP-401-planner-and-filters.md)), 코드·테스트는 같은 커밋에.
4. 끝나면 진행 보고서 §7에 실행 기록을 추가하고 커밋한다. 커밋 메시지는 한국어, 무엇을·왜.

## 3. 절대 규칙 (요약 — 전문은 CLAUDE.md §2)

- **앵커 우선순위**: 설계 브리프(`docs/00-vision/00-design-brief.md`) > 설계 바이블(`docs/02-architecture/00-design-bible.md`, 281KB — **절대 통째로 읽지 말고** `grep -n "^#"`로 절을 찾아 부분만 읽는다) > ADR > 개별 문서.
- **계약 정본은 `schemas/*.schema.json`**. `src/rag_platform/contracts/`는 생성물이다(`just contracts-gen`). 손으로 고치지 않는다. 열거값·필드명 철자는 바이블 §5.7·§6.
- **코드가 바이블을 앞질러 바꾸지 않는다.** 설계가 틀렸다고 판단되면 임시 근사로 구현하고 갭을 기록만 한다 → `tools/phase6/results/open-issues.json`에 항목 추가 후 `node tools/phase6/gen-design-gaps.mjs`로 [설계 갭 원장](docs/12-appendix/10-implementation-design-gaps.md)을 재생성. 바이블 수정은 ADR 선행.
- **계층 규칙**(import-linter가 강제): `contracts ← sdk ← plugins|adapters|pipelines|retrieval|render ← orchestration|ledger|storage|security|profiles|settings|eval ← api|mcp|cli`. `adapters`는 `storage`·`security`를 모른다. `pipelines` 이하는 `temporalio`·`fastapi`·`ledger`·`orchestration`을 임포트하지 않는다.
- **기각 기술 금지**: PyMuPDF/`fitz`, pyhwp 기본 경로, MinIO, Redis 기본 KV, Infinity, SPLADE 기본값, jina 계열 기본 모델. 이유는 CLAUDE.md §2-4.
- **보안 불변식**: 모든 검색에 `tenant_id`·ACL 사전 필터(사후 필터 금지), 리트리벌 결과 캐시 없음, `SecurityContext`는 서버 주입(요청 본문 값 무시).
- **모든 소스 파일은 첫 줄부터 한국어 설명 헤더**(역할 → 설계 근거 → 구성 → 불변식·주의 → 검증 계층, 6~15줄). 규칙 전문 `tools/phase6/CODE-HEADER-RULE.md`, 검사 `node tools/verify/check-headers.mjs`.
- **모델 가중치 다운로드는 사용자 승인 후에만.** Docker·GPU·네트워크·모델이 필요한 테스트는 `needs_docker`/`needs_model`/`needs_gpu`/`needs_network` 마커 + `# DEFERRED:` 주석, 이후 `node tools/verify/gen-deferred-ledger.mjs`.
- 문서 규약(`docs/` 편집 시): frontmatter 필수 필드, 한국어 본문 + 영문 식별자, Mermaid만, 근거 없는 수치는 "확인 필요(as of 2026-09)". 전문 CLAUDE.md §5.

## 4. 이전 세션에서 넘어오지 않는 것 (Claude Code 전용이었던 것)

- `tools/phase3~6/wf-*.js`: Claude Code의 `Workflow` 도구용 다중 에이전트 오케스트레이션 스크립트다. 다른 에이전트에서는 실행되지 않으며 **실행 기록·프롬프트 설계의 참고 자료**로만 읽는다. 같은 일을 하려면 WP 우선 절차(§2-3)를 손으로 따르면 된다.
- `tools/usage-report.mjs`·`PAYMENT.MD`: Claude Code 세션 트랜스크립트를 읽어 토큰을 집계한다. 다른 머신·에이전트에서는 재생성할 수 없다(파일은 기록으로 보존).
- 에이전트 메모리(`~/.claude/projects/...`)는 저장소 밖이다. 필요한 상태는 전부 진행 보고서·git 로그·이 파일에 있다.
- 결과 JSON(`tools/phase*/results/*.json`)은 기록이며 입력으로 다시 쓰지 않는다. 예외: `tools/phase6/results/open-issues.json`은 설계 갭 원장의 정본 입력이다(항목 추가 가능).

## 5. 지금 가장 값진 다음 작업 (우선순위 순)

1. **층 2 검증(Docker 머신)** — [HANDOFF.md](HANDOFF.md) "첫 30분" 절차 → `tools/verify/run-deferred.sh`로 [보류 원장](docs/12-appendix/09-deferred-verification-ledger.md) 항목을 검증하고 상태 열을 갱신. `deploy/compose/compose.lite.yaml` 첫 기동.
2. **WP-601 API·MCP 실 배선** — `cli/main.py`의 `ingest_paths`/`run_query_lite`/`build_query_deps`에 있는 실제 배선을 L3 서비스 계층으로 옮겨 `api/`(스텁 팩 제거)와 `mcp/`(`ToolDeps`·`resolve_security` 조립, stdio 진입점)가 공유하게 한다. API 키 외부 설정(파일/환경 변수)도 여기서.
3. **WP-602 CLI 견고화** — `ingest_paths`에서 `StageError`·파일 부재를 경로별 `status: failed`로 정리(현재 트레이스백으로 전체 종료), 단일 파일 인자 확장자 검사, 메타 파일(`MANIFEST.json`) 제외. 근거는 설계 갭 원장 F5 절.
4. **설계 갭 트리아지** — 원장 186건 중 "바이블 개정 후보" 83건을 ADR 절차로 일괄 처리. 계약 왕복 xfail 27건(문서 예시 오류)도 함께.
5. **6C 미니 골든셋** — `samples/hwpx/`의 공공누리 문서 3건으로 질의·`answer_spans` 초안(`schemas/eval-dataset.schema.json` 형식, [골든셋 구축](docs/08-evaluation/03-golden-dataset-construction.md)). 검수는 사람.
6. **층 2b(실제 BGE-M3·리랭커)** — 사용자 승인 후. 그때부터 검색 품질 수치가 의미를 갖는다.

## 6. 에이전트별 메모

- **Claude Code**: `CLAUDE.md`가 자동 로드된다. 이 파일은 그 요약이다.
- **Codex / OpenAI 계열**: 이 `AGENTS.md`가 자동 로드된다. 상세 규칙이 필요하면 `CLAUDE.md` §1~§10을 읽는다.
- **Cursor / Windsurf / Copilot**: 규칙 파일이 자동 생성돼 있지 않다. 첫 프롬프트에 "AGENTS.md와 CLAUDE.md를 먼저 읽어라"를 넣거나, 도구별 규칙 파일(`.cursor/rules/*.mdc`, `.github/copilot-instructions.md`)을 이 파일을 참조하도록 만든다(이 저장소는 특정 도구 파일을 두지 않는다).
- **Gemini CLI**: `GEMINI.md`가 없다. 같은 방식으로 이 파일을 가리키는 한 줄짜리 `GEMINI.md`를 만들어도 된다(커밋해도 무방).

어느 에이전트든 지켜야 할 한 가지: **사람이 실시간으로 대기하지 않는다.** 질문이 생기면 멈추지 말고 관련 문서의 "## 미해결 이슈" 또는 설계 갭 원장에 남기고 계속한다. 유일한 예외는 모델 가중치 다운로드다.
