---
title: 개발 환경
status: active
owner: architecture
version: 0.1.0
last_updated: 2026-09-23
depends_on:
  - ../00-vision/00-design-brief.md
  - ../02-architecture/00-design-bible.md
  - ../07-tech-landscape/00-summary-and-selection-matrix.md
  - ../03-contracts/00-contract-overview.md
  - ./01-repository-structure.md
  - ../09-operations/01-deployment-guide.md
  - ../09-operations/02-configuration-reference.md
  - ../04-pipelines/01-pipeline-framework.md
  - ../02-architecture/08-deployment-architecture.md
  - ../05-api/06-client-sdks.md
  - ../06-adr/0035-python-version-and-toolchain-pins.md
  - ../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md
---

# 개발 환경

## 목적

이 문서는 RAG Platform 기여자가 **빈 개발 머신에서 첫 `ContextPack`을 받고, 스테이지 하나를 단독으로 디버깅하고, 정적 검사를 CI와 같은 결과로 로컬에서 통과시키기까지** 필요한 도구·절차·설정을 확정한다. 설계 바이블(Design Bible) §11.6 "개발 모드(5분 기동)"가 사용자 관점의 다섯 단계를 정했다면, 이 문서는 그 뒤에 있는 기여자 관점 — 저장소 체크아웃, `uv` 워크스페이스 동기화, pre-commit, compose 개발 스택, 인프로세스 러너(in-process runner) `LocalRunner`, 샘플 데이터, IDE 연동, GPU 옵션, Windows/WSL 주의점 — 을 다룬다.

정본은 바이블 §6.6(환경 변수), §6.7(패키지·extras), §11.1(두 실행기), §11.6(개발 모드), §12(모듈 맵), §13.3(오브젝트 키)과 [ADR-0035](../06-adr/0035-python-version-and-toolchain-pins.md)(Python 버전·툴체인), [ADR-0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md)(비내구 `LocalRunner`)이다. 이 문서는 그것을 **확장하되 바꾸지 않으며**, 바이블 §12 `cli/` 목록에 없는 CLI 하위 명령과 바이블 트리에 없는 파일은 모두 `(제안)`으로 표기하고 "## 미해결 이슈"에 모았다. [저장소 구조](./01-repository-structure.md)가 이 문서에 위임한 결정(`.python-version` 값, `[kiwi]` extra 공백기 전략, Node 툴체인 등재)은 §1·§2에서 확정한다.

## 범위

- **포함**: 요구 도구와 버전, 설정 절차(clone → `uv sync` → `pre-commit install` → compose 개발 스택 → 마이그레이션 → 샘플 수집 → 첫 질의), Temporal 없는 개발 모드(`LocalRunner`)의 동작·제약·프로파일, 샘플 데이터(`samples/`) 구성 규칙과 라이선스, 디버깅(스테이지 단독 실행, 산출물 열람, 설명 가능 질의, 로그·트레이스), GPU 개발 옵션, IDE 설정(ruff·mypy·import-linter), 환경 변수 예시(`.env.example` 개발 값), 흔한 문제, Windows/WSL2 참고.
- **제외**: 저장소 레이아웃·의존 방향([저장소 구조](./01-repository-structure.md)), 린트 규칙 세부·타입 스텁 정책([코딩 표준](./03-coding-standards.md)), 테스트 종류·마커·픽스처 보관([테스트 전략](./04-testing-strategy.md)), CI 잡 정의([CI/CD](./05-ci-cd.md)), 플러그인 템플릿([플러그인 개발 가이드](./06-plugin-development-guide.md)), 운영 배포([배포 가이드](../09-operations/01-deployment-guide.md)), 환경 변수 전체 목록·기본값([설정 레퍼런스](../09-operations/02-configuration-reference.md)).
- **수치**: 소요 시간·하드웨어 값은 바이블 §11.6과 배포 가이드 §2.1의 "초안 목표"를 옮긴 것이다. 외부 도구 버전은 선정 매트릭스 확인일(2026-09-18~22) 기준이며 `uv.lock`·이미지 digest가 정본이다. 07-tech-landscape에 비교 조사가 없는 도구(pre-commit, just, Node 코드젠 도구, VS Code 확장)는 "확인 필요(as of 2026-09)"로 표기한다.
- **전제**: 저장소는 현재 설계 문서(`docs/`)·스키마(`schemas/`)·도구(`tools/`)만 담고 있다. 아래 절차는 구현 착수 시점의 **목표 상태**이며, 이미 존재하는 경로는 그대로 흡수된다(저장소 구조 §범위).

---

## 1. 요구 도구

**결정:** 개발 머신의 필수 도구는 **uv, Python 3.12/3.13(uv 관리), Docker Engine + Compose v2, git** 넷이다. 나머지는 작업 영역에 따른 선택 도구다. 코어 파이프라인의 A 등급 순수 Python 경로(HWPX·디지털 PDF·DOCX·HTML·TXT·형태소 분석·ONNX 임베딩·RapidOCR)는 **시스템 패키지 없이** `uv sync`만으로 동작해야 하며, JVM·LibreOffice·CUDA가 필요한 경로는 컨테이너(사이드카·서빙 이미지)로만 제공한다(바이블 §4.1 격리 모드, §6.7; [ADR-0035](../06-adr/0035-python-version-and-toolchain-pins.md), [ADR-0033](../06-adr/0033-sidecar-convert-contract-and-isolation-ladder.md)).

| 도구 | 버전·범위 | 지위 | 용도 | 근거·비고 |
|------|-----------|:----:|------|-----------|
| `uv` | 최신 안정(정확 버전은 CI 이미지가 고정; 확인 필요 as of 2026-09) | 필수 | 인터프리터 설치(`uv python install`), 워크스페이스 동기화, 잠금(`uv lock --check`), `rag` CLI 설치(`uv tool install`) | D-01, 바이블 §11.6, ADR-0035 대안 7 |
| Python | `>=3.12,<3.14`. 개발 기본 **3.12**(`.python-version`), 3.13은 `uv run --python 3.13`으로 병행 | 필수 | 코어 패키지·플러그인·클라이언트 SDK(Python) | ADR-0035; 시스템 Python 사용 금지(uv가 내려받은 인터프리터만) |
| Docker Engine + Compose v2 | Docker Desktop(macOS·Windows) 또는 Docker Engine(Linux). `docker compose` 서브커맨드 | 필수 | `rag up`이 호출하는 개발 스택(PostgreSQL·Qdrant·Valkey), 선택 오버레이(Temporal·오브젝트 스토리지·TEI·관측) | 배포 가이드 §2.3, §3.1 |
| git | 2.x | 필수 | `core.autocrlf=false` + `.gitattributes`(§10) | 골든 해시 안정성 |
| pre-commit | 확인 필요(as of 2026-09) | 권장 | 커밋 전 ruff·import-linter·잠금·JSON·비밀 검사(§7.3). dev 그룹 의존으로 설치 | 이 문서 제안 |
| `just` | 확인 필요(as of 2026-09) | 선택 | `justfile`(제안) 태스크 래퍼. 정본 명령은 항상 `uv`·`rag` CLI이며 `just`는 편의 수단 | §1.1 |
| Node.js | **22 LTS 이상** | 선택(권장) | `sdk/typescript` 코드젠·빌드(`npm run generate`), `tools/*.mjs` 문서·스키마 검증기(`node tools/validate-contracts.mjs --root .`) | [클라이언트 SDK](../05-api/06-client-sdks.md) §2 런타임 행(확인 필요 as of 2026-09), 저장소 구조 미해결 이슈 11 → §1.1 결정 |
| Java 21 + Maven 3 | `maven:3-eclipse-temurin-21` 빌드 이미지와 동일 | 선택 | `sidecars/parser-workers`(hwplib·hwp2hwpx·hwpxlib·Tika) 소스 작업. 로컬 JDK 없이 `docker build sidecars/parser-workers`만으로도 가능 | 배포 아키텍처 §3.3, 저장소 구조 §3.1 |
| NVIDIA 드라이버 + NVIDIA Container Toolkit | CUDA 12.2+ 호환 드라이버(TEI), Compute Capability ≥ 7.5 | 선택 | GPU 서빙 컨테이너(TEI·vLLM pooling)·`ocr-gpu` 사이드카 로컬 실행(§6) | 배포 가이드 §2.2 |
| `curl`, `jq` | — | 권장 | API 수동 호출, smoke 스크립트 | 배포 가이드 §7.2 |
| Temporal CLI | 1.x(`temporal server start-dev`) | 선택 | Temporal 셸 통합 테스트·`tests/replay`용 개발 서버. **프로덕션·`--durable` 대체 아님** | ADR-0003 중립 항, 배포 가이드 §4.5 |

**설치하지 않는 것**(자주 오해되는 항목):

| 항목 | 이유 |
|------|------|
| LibreOffice(`soffice`) 네이티브 설치 | DOC/RTF/ODT 변환과 HWP 최후 폴백은 GPL 사이드카 `lo-sidecar`(별도 저장소 `rag-platform-gpl-sidecars`, opt-in)의 컨테이너 전용이다. 코어 저장소·코어 이미지·개발 의존에 LibreOffice를 넣지 않는다(D-02 C 등급, [ADR-0001](../06-adr/0001-license-grade-table-and-d02-interpretation.md), [ADR-0007](../06-adr/0007-hwp5-java-sidecar-first-pyhwp-demoted.md)). `lite` 프로파일에서 DOC은 `parse.unsupported_format`이 정상 동작이다(바이블 §7.1) |
| `libmagic`(`python-magic`, `python-magic-bin`) | 포맷 판별 1차는 puremagic + 자체 ZIP/OLE 스니퍼(MIT, 순수 Python)다. libmagic은 배포판별 시그니처 편차와 Windows DLL 문제로 Linux 컨테이너 선택 경로에만 남았다(선정 매트릭스 `format_detector` 행, [07-tech-landscape/03](../07-tech-landscape/03-document-parsing-office-html-text.md)). `python-magic-bin`을 의존에 추가하는 PR은 거부한다 |
| `fitz`/`pymupdf`, `hwp5`(pyhwp) | C 등급 임포트 금지(import-linter `forbidden`, 저장소 구조 §3.2 계약 (5)). 개발 편의로도 설치하지 않는다 |
| `kiwipiepy` 0.23.x | LGPL 정적 링크 wheel은 기본 설치 금지(D-02 B 등급). `[kiwi]` extra는 Apache-2.0 wheel(≥0.24.0) 공개 확인 후에만(§2.2, [ADR-0021](../06-adr/0021-korean-analyzer-kiwi-promotion-and-interim-mecab-kss.md)) |
| CUDA 툴킷(호스트) | 코어 패키지 `[gpu]` extra는 비어 있고 CUDA는 서빙·`ocr-gpu` 이미지 안에만 있다(배포 아키텍처 §3.3). 호스트에는 드라이버와 Container Toolkit만 |

### 1.1 태스크 러너와 Node 툴체인

**결정:** 태스크 러너로 `make`를 요구하지 않는다. 저장소 루트에 `justfile`(제안)을 두어 아래 §2 명령을 레시피로 감싸되, 모든 레시피는 문서화된 `uv`·`rag`·`docker compose` 명령 한 줄로 환원되어야 하며 `just` 없이도 같은 결과가 나와야 한다(Windows 기본 환경에 `make`가 없고, 레시피가 정본 명령을 숨기면 CI와 로컬이 갈라진다). 근거 문서가 없으므로 `just` 자체의 버전·라이선스는 확인 필요(as of 2026-09)다.

**결정:** Node.js 22 LTS를 **선택 개발 도구로 등재**한다(저장소 구조 미해결 이슈 11의 (b)). 이유는 (1) `sdk/typescript` 코드젠이 이미 npm을 요구하고(클라이언트 SDK §2), (2) 기존 `tools/validate-contracts.mjs`가 의존성 0의 Node 스크립트로 JSON Schema 2020-12 부분 검증·바이블 §5.7 열거 대조·인벤토리 커버리지를 이미 수행하고 있어 Python 이식의 이득이 없기 때문이다. 단, Node가 없는 기여자도 코어 개발이 가능해야 하므로 Node 의존 검사는 pre-commit에서 `node` 존재 시에만 실행하고 CI에서는 항상 실행한다. `tools/phase3/*.js`(문서 작성 워크플로우 스크립트)는 개발 도구가 아니며 `docs/12-appendix/` 이관 대상이다(저장소 구조 미해결 이슈 11·12).

| `justfile` 레시피(제안) | 환원되는 명령 |
|--------------------------|---------------|
| `just sync` | `uv sync --all-packages --all-extras --group dev` |
| `just up` / `just down` | `uv run rag up --profile lite` / `docker compose -f deploy/compose/compose.lite.yaml down` |
| `just lint` | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` |
| `just typecheck` | `uv run mypy src/` |
| `just test` | `uv run pytest tests/unit tests/contracts tests/golden` |
| `just test-matrix` | `uv run --python 3.12 pytest … && uv run --python 3.13 pytest …` |
| `just check` | `lint` + `typecheck` + `test` + `uv lock --check` + (`node` 있으면) `node tools/validate-contracts.mjs --root .` |
| `just schema-export` | `uv run python -m rag_platform.contracts.export --out build/schemas-export`(저장소 구조 §6 제안) |

---

## 2. 설정 절차

### 2.1 전체 흐름

```mermaid
flowchart TD
    A["1. git clone<br/>core.autocrlf=false"] --> B["2. uv python install 3.12 3.13<br/>uv sync --all-packages --all-extras --group dev"]
    B --> C["3. uv run pre-commit install"]
    C --> D["4. cp deploy/compose/.env.example deploy/compose/.env<br/>비밀 파일 .secrets/ 생성"]
    D --> E["5. uv run rag up --profile lite<br/>compose(PostgreSQL·Qdrant·Valkey) + 마이그레이션 + 모델 다운로드 + /readyz 대기"]
    E --> F["6. 테넌트·API 키·컬렉션 부트스트랩<br/>(rag tenant create · rag api-key create 제안 · POST /v1/collections)"]
    F --> G["7. uv run rag ingest ./samples/*.hwpx --collection <id> --wait"]
    G --> H["8. uv run rag query '정보공개 청구 절차' --collection <id> --render markdown --explain"]
    H --> I["9. just check (또는 개별 명령)<br/>CI와 동일한 게이트 로컬 통과"]
    E -. "선택 오버레이" .-> O["compose.lite-durable.yaml(Temporal·objectstore·TEI CPU)<br/>compose.observability.yaml(otel-collector·jaeger·prometheus)<br/>compose.dev-opensearch.yaml(제안)"]
```

| 단계 | 명령 | 기대 결과 | 소요(초안 목표) | 실패 시 |
|------|------|-----------|:---:|---------|
| 1 | `git clone <repo> && cd rag-platform` | `.python-version`이 `3.12` | — | §10 줄바꿈·경로 길이 |
| 2 | `uv python install 3.12 3.13` → `uv sync --all-packages --all-extras --group dev` | `.venv/` 생성, 루트·`sdk/python`·`plugins/*` 전부 편집 가능 설치, `uv.lock` 불변 | 3~5분(최초; 캐시 후 30초) | §2.2 `[kiwi]` 공백기, §9 |
| 3 | `uv run pre-commit install` | `.git/hooks/pre-commit` 설치 | 10초 | pre-commit이 dev 그룹에 있는지 확인 |
| 4 | `cp deploy/compose/.env.example deploy/compose/.env`; `mkdir -p .secrets && … > .secrets/pg_owner_password` | `.env`·`.secrets/`는 `.gitignore` 대상 | 1분 | §8 |
| 5 | `uv run rag up --profile lite` | 컨테이너 3개 `healthy`(`postgres`·`qdrant`·`valkey`), `app` 컨테이너 또는 호스트 프로세스 `GET :8000/readyz` 200, `./.rag/models`에 bge-m3 ONNX int8·mecab-ko-dic·RapidOCR ONNX, 마이그레이션 완료 | 90초(모델 최초 다운로드 제외 시; 바이블 §11.6) | §9 포트 충돌·모델 다운로드 |
| 6 | `uv run rag tenant create --name demo`(제안) → `rag api-key create --tenant <tenant_id> --principal service:bootstrap`(제안) → `curl -X POST :8000/v1/collections`(배포 가이드 §5.4 JSON, `profile_id: lite`) | `tenant_id`·`collection_id`(ULID), 키 1회 표시, `backends[0].alias = col_<id>_vec` | 1분 | `profile.invalid` → `rag profile validate` |
| 7 | `uv run rag ingest ./samples/*.hwpx --collection <collection_id> --wait` | 잡 `succeeded`, `index.commit.published`, `workflow_run_id = null`(`LocalRunner`) | 30초(바이블 §11.6) | `GET /v1/jobs/{job_id}`의 `last_error.code` |
| 8 | `uv run rag query "정보공개 청구 절차" --collection <collection_id> --render markdown --explain` | `ContextPack.items ≥ 1`, Markdown 렌더, `score_breakdown`; 리랭커 없으면 `degraded[{rerank, skipped_by_policy}]` | 2초 | §9 검색 0건 |
| 9 | `just check` 또는 §1.1 표의 개별 명령 | ruff·mypy·import-linter·pytest·`uv lock --check` 전부 통과 | 3~8분 | §7, §9 |

`rag up`이 하는 일은 배포 가이드 §3.5와 같다 — compose 파일 렌더·기동, 원장 마이그레이션(`rag ledger migrate`, 제안), 모델 최초 다운로드(`HF_HUB_OFFLINE=0`), `/readyz` 대기. 6단계의 테넌트·API 키 부트스트랩은 바이블 §11.6에 없는 절차이며 CLI 이름은 배포 가이드 미해결 이슈 1·2의 제안이다. 개발 모드에서 `rag up`이 `demo` 테넌트·컬렉션까지 만들어 주는지는 미해결 이슈 3이다.

### 2.2 `uv` 워크스페이스 동기화 규칙

**결정:** 개발 기본 인터프리터는 **3.12**(`.python-version = 3.12`)다. 하한 인터프리터에서 개발하면 3.12 전용 회귀(3.13에서만 되는 표준 라이브러리 기능 사용)를 가장 먼저 잡고, ruff `target-version = "py312"`와 일치한다. 3.13은 커밋 전 `uv run --python 3.13 pytest`(또는 `just test-matrix`)로 검증하며 CI는 두 버전 모두 실행한다(ADR-0035 준수 확인 "CI 매트릭스"; 저장소 구조 §2.1 `.python-version` 행의 위임 사항).

**결정(잠정, `[kiwi]` 공백기):** `kiwipiepy>=0.24.0`(Apache-2.0 wheel)의 PyPI 공개가 확인되기 전까지 `[kiwi]` extra는 루트 `pyproject.toml`의 `[project.optional-dependencies]`에 **선언하지 않는다**(저장소 구조 미해결 이슈 15의 (a)). 단일 `uv.lock`은 모든 extras를 함께 해소하므로 해소 불가 extra 하나가 `uv lock` 전체를 실패시키고, 환경 마커로 조건부 처리하는 (b)는 uv가 extra 단위 실패를 허용하는지 확인 필요(as of 2026-09)이기 때문이다. 바이블 §6.7의 extras 6종 철자는 문서·CI 대조 목록에 그대로 유지하고, 공개 확인 즉시 pin-and-bump PR로 extra를 복원한다(ADR-0021 재검토 조건). 이 조치로 §1.1 `just sync`의 `--all-extras`가 실제로 동작한다. 그 전까지 Kiwi가 필요한 기여자는 `uv pip install kiwipiepy==0.23.2`처럼 **개인 환경에서만** 설치하되 `uv.lock`·`pyproject.toml`에 반영하지 않는다(LGPL 정적 링크 wheel, D-02 B).

| 작업 | 명령 | 비고 |
|------|------|------|
| 전체 동기화 | `uv sync --all-packages --all-extras --group dev` | 저장소 구조 §3.4 |
| 코어만(플러그인 제외) | `uv sync --all-extras --group dev` | 빠른 반복 |
| 특정 플러그인 | `uv sync --package rag-plugin-lightrag` | 플러그인 CI와 동일 |
| 사이드카 `ocr-gpu` | `cd sidecars/ocr-gpu && uv sync` | 별도 `uv.lock`, 워크스페이스 비멤버(CUDA 의존 격리) |
| 의존 추가 | `uv add <pkg>` → `uv lock` → 라이선스 등급 확인(`uv run pip-licenses`, `uv run liccheck`) | A 등급만, `requires-python`이 3.12·3.13 포함(ADR-0035 코드 리뷰 항목) |
| 잠금 검사 | `uv lock --check` | 실패 = CI 실패 |
| 인터프리터 매트릭스 | `uv run --python 3.13 pytest tests/unit` | 두 버전 모두 통과 필수 |

### 2.3 compose 개발 스택

개발 스택은 배포 가이드 §3의 `lite` compose를 그대로 쓴다. 기본은 `compose.lite.yaml`(데이터 계층 3 + `app`)이고, 필요할 때만 오버레이를 겹친다. 이 표는 배포 가이드 §3.2·§2.5의 요약이며 이미지 digest는 `rag up`이 렌더하는 파일이 정본이다.

| 서비스 | 파일 | 기본 | 포트(호스트) | 개발 용도 | 비고 |
|--------|------|:----:|------|-----------|------|
| `postgres` | `compose.lite.yaml` | 켬 | 5432 | 원장(`rag_ledger`), Procrastinate 스키마 | 역할 4종은 `init/postgres` 스크립트(배포 가이드 §5.1) |
| `qdrant` | `compose.lite.yaml` | 켬 | 6333 REST / 6334 gRPC | `dense` + `sparse_bm25`(lite) | 1.19 |
| `valkey` | `compose.lite.yaml` | 켬 | 6379 | 캐시·레이트리밋·멱등 조회 캐시 | 영속화 끔 |
| `app` | `compose.lite.yaml` | 켬(모드 A) | 8000 / 9090 | `rag serve api` + `LocalRunner` 동거 | 모드 B(§3.2)에서는 내리고 호스트에서 실행 |
| `temporal-setup`, `temporal` | `compose.lite-durable.yaml` | 끔 | 7233 | Temporal 셸 통합 테스트, `--durable` 동작 확인 | 단일 바이너리 + PostgreSQL. `start-dev`와 다름 |
| `objectstore` | `compose.lite-durable.yaml` | 끔 | 9000 | `s3://` 경로 테스트 | RustFS 또는 SeaweedFS(ADR-0011 택1 전 플레이스홀더) |
| `reranker` | `compose.lite-durable.yaml` | 끔 | 8080 | TEI CPU + gte-multilingual-reranker-base(30→10) | 생략 시 `rerank.applied=false` |
| `otel-collector`, `jaeger`, `prometheus` | `compose.observability.yaml` | 끔 | 4317 / UI | 트레이스·메트릭 열람(§5.5) | Grafana·Tempo·Loki는 AGPL 분리 컨테이너, 개발 기본 아님 |
| `opensearch` | `compose.dev-opensearch.yaml`(제안) | 끔 | 9200 | `index_backend.opensearch`·Nori 어댑터 개발 | `lite`는 OpenSearch 없음(바이블 §7.1). `standard` 프로파일 컬렉션으로만 테스트, 미해결 이슈 4 |

`rag up --profile lite`는 `compose.lite.yaml`만, `--durable`은 `compose.lite-durable.yaml`을 겹친다(배포 가이드 §3.1). 관측·OpenSearch 오버레이를 `rag up` 플래그로 켤지 `docker compose -f … -f …`를 직접 쓸지는 미해결 이슈 4다. 하드웨어 최소는 4 vCPU / 16GB / SSD 100GB, 권장 8 vCPU / 32GB(배포 가이드 §2.1 초안 목표; Docker Desktop·WSL2는 §10.3 메모리 상한 주의).

### 2.4 마이그레이션과 부트스트랩

- **원장 마이그레이션**은 `rag up`이 수행한다. 수동 실행은 `rag ledger migrate`(제안; 도구 선정은 저장소 구조 미해결 이슈 5 — Alembic 후보, 확인 필요). RLS `FORCE`와 정책이 마이그레이션 안에서 함께 적용되며, 검증은 배포 가이드 §5.1과 같다(`SET LOCAL app.tenant_id` 없는 트랜잭션에서 `SELECT count(*) FROM documents` = 0).
- **Temporal 스키마**는 `--durable`일 때만 `temporal-setup` 컨테이너가 두 DB(`temporal`, `temporal_visibility`)에 적용한다. `LocalRunner` 개발 모드에는 필요 없다.
- **테넌트·API 키**: 바이블 §14에 테넌트 생성 엔드포인트가 없어 CLI(`rag tenant create`, `rag api-key create`; 제안)로 만든다. 개발 모드의 인증은 API 키 + 정적 역할이다(바이블 §7.1 `lite` 이벤트·API 행).
- **컬렉션**: `POST /v1/collections`에 `profile_id: "lite"`. 물리 컬렉션 `rag_vec_{embedding_profile_hash[:12]}`·alias `col_{collection_id}_vec`는 어댑터가 만든다(배포 가이드 §5.4). 개발자가 Qdrant 컬렉션을 손으로 만들지 않는다.

---

## 3. 개발 모드: 인프로세스 러너(Temporal 없음)

### 3.1 동작

**결정:** 개발·CI·평가 하네스는 **비내구 `LocalRunner`**로 실행한다. `RAG_TEMPORAL__ADDRESS`가 비어 있으면 `api` 프로세스가 `LocalContext`로 같은 파이프라인 정의(`rag_platform.pipelines.ingest.run`)를 `asyncio` + `StagePolicy` 재시도로 실행하고, 검색 경로는 모든 프로파일에서 항상 `LocalContext` 인프로세스다. 프로덕션은 `--durable`(Temporal 단일 바이너리 + PostgreSQL) 이상만 허용한다(바이블 §11.1; [ADR-0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md)).

```mermaid
flowchart LR
    subgraph HOST["개발 머신"]
        subgraph API["api 프로세스 (rag serve api, RAG_TEMPORAL__ADDRESS 없음)"]
            R["FastAPI /v1 · /mcp"]
            L["LocalRunner (LocalContext)<br/>asyncio · StagePolicy 재시도 · 비내구"]
            Q["retrieval (LocalContext)<br/>plan → retrieve → fuse/hydrate → rerank → postprocess → pack → render"]
            W["Procrastinate 릴레이(아웃박스 → SSE·웹훅)"]
        end
        FS["file://./.rag/artifacts<br/>tenants/{tenant_id}/artifacts · sources · derived"]
        M["./.rag/models (HF_HOME)"]
        subgraph COMPOSE["docker compose (compose.lite.yaml)"]
            PG["postgres 5432<br/>rag_ledger"]
            QD["qdrant 6333/6334<br/>dense · sparse_bm25"]
            VK["valkey 6379"]
        end
    end
    R --> L --> FS
    L --> PG
    L --> QD
    Q --> QD
    Q --> VK
    L --> M
    W --> PG
```

| 항목 | `LocalRunner`(개발) | Temporal(`--durable` 이상) | 개발자에게 미치는 영향 |
|------|--------------------|---------------------------|-------------------------|
| 내구성 | 없음 — 프로세스 종료 시 진행 중 잡 `failed` | 있음 | 서버 재시작 후 `POST /v1/jobs/{job_id}/retry`; 완료 스테이지 산출물은 `stage_key` 캐시로 재사용 |
| `JobStatus.workflow_run_id` | `null` | Temporal run id | 테스트 단언에 `null` 허용 |
| `commit_id`·`event_id` 발급 | 일반 생성 | 워크플로우가 1회 생성 | 재시도 시 값 불변 규칙은 두 셸 모두 준수 |
| 시그널·업데이트(취소·우선순위) | 제한적(프로세스 내) | 완전 | 취소 경로 테스트는 Temporal 셸에서 |
| 큐 | 없음(단일 프로세스) | `ingest`·`maintenance`(lite) | GIL 병목은 개발 모드 특성 |
| 산출물 동등성 | 같은 골든 입력 → 같은 `IndexCommit.commit_hash`·`golden_hash` | 동일 | 두 셸 동등성은 적합성 키트 항목(ADR-0003 준수 확인 5, [파이프라인 프레임워크](../04-pipelines/01-pipeline-framework.md) §8.3) |
| `file://` 원천 | `runtime.orchestrator=local` + `RAG_FETCH__FILE__ALLOWED_ROOTS`에서만 | 거부(`fetch.egress_denied`) | 샘플 수집은 개발 모드 전용 경로 |

### 3.2 두 가지 실행 형태

| 모드 | 구성 | 언제 | 명령 |
|------|------|------|------|
| **A. 컨테이너 앱** | `app` 컨테이너 안에서 `rag serve api`(코어 이미지) + compose 데이터 계층 | 배포 형상과 같은 환경 확인, 이미지 빌드 검증, e2e(`tests/e2e`) | `uv run rag up --profile lite` |
| **B. 호스트 앱** | 데이터 계층만 compose로 띄우고 `api`는 호스트 `.venv`에서 실행 | 코드 수정·디버거 부착·스테이지 단독 실행(일상 개발 기본) | `docker compose -f deploy/compose/compose.lite.yaml up -d postgres qdrant valkey` → `.env`의 호스트명을 `localhost`로 바꾼 사본 로드(§8) → `uv run rag ledger migrate`(제안) → `uv run rag serve api` |

모드 B에서 컨테이너 이름(`postgres`, `qdrant`, `valkey`)은 호스트에서 해석되지 않으므로 `RAG_PG__DSN`·`RAG_VALKEY__URL`·`RAG_QDRANT__URL`(제안)의 호스트를 `localhost`로 바꾼다(§8 표). `RAG_OBJECT_STORE__URI`는 호스트 경로 `file://`로 지정하고, `RAG_FETCH__FILE__ALLOWED_ROOTS`(제안)에 `samples/` 절대 경로를 넣어야 `file://` 원천 수집이 통과한다(E16, [ADR-0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md)).

### 3.3 개발 프로파일

내장 `lite`는 `runtime.orchestrator: temporal`이고 `runtime.egress.allowed_schemes`에 `file`이 없으며 `security.rate_limit.fail_mode`가 운영 `closed`다. 환경 변수로 프로파일 값을 덮어쓸 수 없으므로(설정 레퍼런스 §1.1) 개발 모드는 **개발용 파생 프로파일**로 돈다 — 가칭 `lite-local`(`runtime.orchestrator: local`, `security.rate_limit: {store: memory, fail_mode: open}`, `runtime.egress.allowed_schemes`에 `file`·`http` 추가). 이 프로파일을 내장 6번째로 추가할지(바이블 §7 내장 목록 minor) `rag up`이 생성·등록할지는 설정 레퍼런스 미해결 이슈 2가 소유하며, 이 문서는 어느 쪽이든 **`profile_id` 접미 `-local`/`-dev`가 붙은 프로파일은 프로덕션 컬렉션에 쓰지 않는다**는 규칙만 더한다(배포 가이드 §5.3 `-dev` 접미 규칙과 정합). 프로파일 로딩 규칙 P-4(`file` 스킴은 `orchestrator=local`에서만)가 이를 기계적으로 막는다(설정 레퍼런스 §6.2).

### 3.4 Temporal 셸을 로컬에서 시험하기

두 셸이 같은 정의를 실행하므로 대부분의 어댑터·파이프라인 변경은 `LocalRunner`로 충분하다. 다음 변경은 Temporal 셸에서도 확인한다: `orchestration/temporal/*`(워크플로우·액티비티 래퍼·컨버터·스케줄), `StagePolicy` 값, 사가 보상(§11.4), 시그널·업데이트, `continue_as_new`.

| 방법 | 명령 | 용도 | 제약 |
|------|------|------|------|
| 시간 건너뛰기 테스트 환경 | `uv run pytest tests/replay`(`WorkflowEnvironment.start_time_skipping()`) | 단위 테스트·`Replayer` 히스토리 회귀 | `[temporal]` extra 필요; 서버 불필요 |
| 개발 서버 | `temporal server start-dev` → `RAG_TEMPORAL__ADDRESS=localhost:7233 uv run rag serve api` | 시그널·취소·스케줄 수동 확인, Web UI 8233 | SQLite, 재시작 시 상태 소실. 프로덕션·`--durable` 대체 아님(ADR-0003 중립 항) |
| `--durable` 오버레이 | `uv run rag up --profile lite --durable` | 배포 형상 동일 확인(`temporal-setup` 스키마, 단일 바이너리 + PostgreSQL) | 컨테이너 5~6개, 기동 시간 증가 |

---

## 4. 샘플 데이터

### 4.1 규칙

**결정:** `samples/`에는 **재배포 가능 라이선스 문서만** 둔다 — 공공누리(KOGL, Korea Open Government License) 제1유형(출처 표시만 요구, 상업적 이용·변경 허용), 자체 작성(Apache-2.0), 합성 문서. 개인정보가 들어간 실제 문서는 금지하고 PII 경로는 합성 문서로만 검증한다. 각 파일의 출처·라이선스·해시는 `samples/MANIFEST.json`(제안)에 기록하고 CI가 (1) 매니페스트에 없는 파일, (2) 허용 목록 밖의 `license`, (3) 해시 불일치를 실패로 처리한다. 파일 하나는 1MB 이하이며 그 이상(스캔 PDF 다페이지, 대형 HWPX)은 저장소에 넣지 않고 오브젝트 스토리지 미러 + 해시 매니페스트로 참조한다(저장소 구조 §7 배치 규칙; 보관 방식은 [테스트 전략](./04-testing-strategy.md) 확정). 근거: 브리프 D-02, [ADR-0001](../06-adr/0001-license-grade-table-and-d02-interpretation.md), [ADR-0023](../06-adr/0023-evaluation-qrels-answer-spans-and-linear-ndcg.md)(골든셋 코퍼스도 KOGL 제1유형), [07-tech-landscape/09](../07-tech-landscape/09-evaluation-and-observability.md) §골든셋 구축.

`samples/`는 **5분 기동 데모와 개발자 수동 확인용**이다. 계약 테스트 코퍼스(`tests/adapters/{extension_point}/…`)와 골든 케이스(`tests/golden/{stage}/cases.json`)는 별도이며(저장소 구조 §2.2 `samples/` 행), 외부 평가셋(Allganize RAG-Evaluation-Dataset-KO 등)은 `samples/`에 복제하지 않고 `EvalDataset`으로 등록해 하네스가 내려받는다([골든셋 구축](../08-evaluation/03-golden-dataset-construction.md)).

### 4.2 샘플 목록(초안)

파일명은 배포 가이드 §3.5·파이프라인 프레임워크 §13 예시와 맞췄다. "출처" 열은 문서 유형이며 실제 원문 URL·제목·게시 기관은 수집 시 `MANIFEST.json`에 기록한다(개별 문서의 KOGL 유형 표기는 문서마다 확인 필요 as of 2026-09).

| 파일 | `SourceFormat` | 검증하는 경로 | 출처·라이선스 | 비고 |
|------|----------------|---------------|---------------|------|
| `information-disclosure-guide.hwpx` | `hwpx` | python-hwpx OWPML 어댑터: heading 계층·표·각주·`element_path`; `rag query "정보공개 청구 절차"` 데모 질의의 정답 문서 | 공공기관 안내문, KOGL 제1유형 | 바이블 §11.6 4단계 질의와 짝 |
| `notice.hwpx` | `hwpx` | 개조식 번호 문단·글머리 기호·문장 분리(kss `punct`), `flat_text` 폴백 | 공공기관 공지, KOGL 제1유형 | `rag run-stage parse` 예시 입력 |
| `notice.hwp` | `hwp5` | `lite` 폴백 체인 unhwp(helper_process, x64) → hwp-hwpx-parser; arm64에서는 후자만 | 위 문서의 HWP 5.0 병행 게시본(기관이 함께 게시한 경우만; 배포용·암호화 아님) | 없으면 생략. 배포용 문서는 `parse.distribution_document`가 정상 |
| `regulation-digital.pdf` | `pdf`(`born_digital`) | `pdf_fast_cpu`(pypdfium2 + pdftext): 2단·표·머리말/꼬리말 furniture | 고시·규정 PDF, KOGL 제1유형(법령 본문 자체의 저작권 지위는 확인 필요 as of 2026-09) | `page`·`bbox` 비 null 확인 |
| `scanned-sample.pdf` | `pdf`(`scanned`) | RapidOCR PP-OCRv5 korean mobile(CPU), `page_status[]`, `Block.source=ocr`, `ocr_confidence` | 합성 — `information-disclosure-guide.hwpx` 렌더 → 이미지 → PDF(라이선스 상속) | 3페이지 이하로 1MB 유지 |
| `press-release.html` | `html` | Trafilatura(`xml`) → Docling HTML: nav·header 제거, 표 보존 | 정부 보도자료 저장본, KOGL 제1유형 | 외부 리소스 참조 제거(오프라인 재현) |
| `guide.docx` | `docx` | Docling `MsWordDocumentBackend` + docx2python 각주·미주 병합 | 합성(Apache-2.0) 또는 KOGL 제1유형 | 각주 ≥ 2개 포함 필수 |
| `readme-ko.md` | `md` | markdown-it-py 토큰 `map` → `char_start/char_end` | 자체 작성(Apache-2.0) | 코드 블록·표 포함 |
| `plain-cp949.txt` | `txt` | charset-normalizer + `euc-kr` 라벨 → `cp949` 디코딩, NFC | 자체 작성(Apache-2.0) | 확장 완성형 글자(`똠` 등) 포함 |
| `pii-synthetic.hwpx` | `hwpx` | Presidio KR 인식기 5종·`pii_policy=mask` | 합성(Apache-2.0); 생성기가 만든 가짜 주민등록번호·전화번호·계좌 | 실제 개인정보 금지. 체크섬 통과값 사용 안 함 |
| `queries.jsonl`(제안) | — | 데모 질의와 기대 문서(`external_id`) 3~5쌍; smoke 확인용(qrels가 아님) | 자체 작성 | `tests/e2e`가 재사용 |

`MANIFEST.json` 항목 예시. `format` 값은 바이블 §5.7 `SourceFormat` 철자를 그대로 쓰고, `license`는 SPDX 식별자 또는 `LicenseRef-KOGL-1`(SPDX 목록에 공공누리가 없으므로 [평가·피드백·사이드카 계약](../03-contracts/16-eval-feedback-and-sidecar-contracts.md) §EvalDataset의 표기를 따른다; 확인 필요 as of 2026-09). 해시는 원본 바이트의 BLAKE3 소문자 hex(바이블 §6.2 `content_hash`)다.

```json
{
  "generated_at": "2026-09-22T09:00:00.000Z",
  "allowed_licenses": ["LicenseRef-KOGL-1", "Apache-2.0"],
  "items": [
    {
      "path": "information-disclosure-guide.hwpx",
      "format": "hwpx",
      "title": "정보공개 청구 안내",
      "publisher": "행정안전부",
      "source_url": "https://www.example.go.kr/placeholder/information-disclosure-guide.hwpx",
      "license": "LicenseRef-KOGL-1",
      "license_note": "공공누리 제1유형(출처표시). 원문 URL과 유형 표기는 수집 시 확인",
      "content_hash": "9f3a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4",
      "size_bytes": 348160,
      "retrieved_at": "2026-09-20T03:00:00.000Z",
      "purpose": ["demo_query", "hwpx_tables_footnotes"]
    },
    {
      "path": "scanned-sample.pdf",
      "format": "pdf",
      "title": "정보공개 청구 안내(스캔 합성본)",
      "publisher": "rag-platform",
      "source_url": null,
      "license": "LicenseRef-KOGL-1",
      "license_note": "information-disclosure-guide.hwpx 렌더 이미지에서 합성. 원문 라이선스 상속",
      "content_hash": "0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d",
      "size_bytes": 812544,
      "retrieved_at": "2026-09-20T03:10:00.000Z",
      "purpose": ["ocr_cpu", "page_status"]
    }
  ]
}
```

### 4.3 외부 데이터셋(샘플 아님)

| 데이터셋 | 라이선스 | 용도 | 접근 |
|----------|----------|------|------|
| Allganize RAG-Evaluation-Dataset-KO(PDF 63건·질의 300) | MIT | 한국어 PDF 종단 회귀 1차 외부 셋(`allganize-ko`) | `EvalDataset` 등록 후 `rag eval run --dataset allganize-ko`; `answer_spans` 재라벨 필요(ADR-0023) |
| `ko-public-v1` 소형 분할 | KOGL 제1유형(자체 골든셋) | `tests/eval` 소형 골든셋 게이트(`lite` 0.70/0.85) | 하네스 M1 산출물; 위치·형식은 [골든셋 구축](../08-evaluation/03-golden-dataset-construction.md) |
| AI Hub 데이터 | 내국인 한정·재배포 불가 | 조직 내부 시드만 | 저장소·`samples/`·공개 골든셋에 포함 금지 |

---

## 5. 디버깅

### 5.1 스테이지 단독 실행

스테이지 하나를 프로덕션과 같은 `run_stage` 경로로 실행하는 CLI `rag run-stage`는 [파이프라인 프레임워크](../04-pipelines/01-pipeline-framework.md) §13의 제안이다(바이블 §12 `cli/` 미등재). 셸은 `LocalRuntime` + `FileArtifactStore` + 기본 `InMemoryLedger`이므로 compose 없이도 돈다(`--ledger pg`일 때만 원장 필요).

```text
uv run rag run-stage parse --input ./samples/notice.hwpx --profile lite --json
uv run rag run-stage normalize --input ./.rag/artifacts/out/parse.ref.json --profile lite --out ./.rag/artifacts/out
uv run rag run-stage chunk --input ./.rag/artifacts/out/normalize.ref.json --profile lite --plugin chunker.structure_aware --config ./tmp/chunk-512.yaml
```

| 상황 | 방법 |
|------|------|
| 파서 출력이 이상하다 | `run-stage parse --json`의 `artifact_ref.uri`를 열어 `ParsedDocument.blocks[]`의 `element_path`·`char_start/char_end`·`provenance`를 확인. HWPX 파생물(변환본·표 HTML)은 `derived/` |
| 청킹 파라미터 A/B | `--plugin`·`--config`로 프로파일 값 덮어쓰기(`profile_hash` 재계산). 결과 `ChunkSet.chunks[].token_counts`를 비교 |
| 캐시 적중이 의심된다 | `--no-cache`(`force=true`) 또는 `rag cache invalidate --stage <name> [--document …]`(바이블 §12). 지문(`fingerprint`)이 바뀌면 자연히 미스 |
| 재개 경로 재현 | `--resume <resume_cursor.json>`으로 `ctx.resume_details` 주입; 재개 유무와 무관하게 `golden_hash`가 같아야 한다(프레임워크 §11.3) |
| 골든 케이스 생성·갱신 | `tests/golden/{stage}/cases.json`에 입력 픽스처와 `expected_golden_hash`를 추가; 헬퍼 `rag_platform.testing.golden`이 `FakeStageContext`(고정 `now()`, 인메모리 저장소)로 실행 |
| 종료 코드 | `profile.invalid` 2, `StageFailure`(`StageError` JSON) 3, `contract.violation` 4(프레임워크 §13 동작 규칙) |

### 5.2 산출물 열람

산출물은 `RAG_OBJECT_STORE__URI=file://…` 아래 바이블 §13.3 키 규약으로 놓인다. 개발 모드 기본 루트는 `./.rag/artifacts`다.

| 대상 | 경로(루트 기준) | 열람 방법 |
|------|-----------------|-----------|
| 원본 | `tenants/{tenant_id}/sources/{blake3[:2]}/{blake3}` | `blake3`는 `SourceDocument.content_hash` |
| 스테이지 산출물(계약 JSON) | `tenants/{tenant_id}/artifacts/{schema_type_kebab}/{stage_key[:2]}/{stage_key}.json` | `jq . <file>`; `schema_type`·`schema_version` 봉투 확인. `stage_key`는 `GET /v1/jobs/{job_id}`의 진행 정보 또는 `run-stage --json` 출력에서 |
| 파생물 | `tenants/{tenant_id}/derived/{kind}/{blake3[:2]}/{blake3}.{ext}` | HWPX 변환본·페이지 이미지·표 HTML·부모 텍스트 번들(`derived/parent_texts/{chunk_set_blake3}.json`) |
| API로 열람 | `GET /v1/documents/{document_id}/content?view=parsed\|normalized\|chunks` | ACL 필터 적용, 커서 페이지네이션(바이블 §14) |
| 계보·커밋 | `GET /v1/documents/{document_id}/commits`; 원장 `lineage`·`artifacts` 테이블 | `psql`은 `SET LOCAL app.tenant_id = '<ulid>'` 후 조회(RLS fail-closed; 배포 가이드 §9) |
| 인덱스 레코드 | Qdrant REST `:6333/collections/{physical}/points/scroll`(payload에 `chunk_id`·`block_refs`·`acl_*`) | `point_id = uuid5(NAMESPACE_RAG_CHUNK, record_id)`; 개발 편의 조회이며 코드는 어댑터만 사용 |

산출물 JSON을 손으로 고쳐 다음 스테이지에 넣는 것은 허용되지만, 셸이 입력 로드 시 계약 검증을 하므로 위반은 `contract.violation`(종료 코드 4)로 즉시 드러난다.

### 5.3 설명 가능한 질의

`rag query … --explain`(또는 `QueryRequest.explain: true`)은 `QueryPlan`(재작성 질의·채널·필터 트리·`filters.effective_hash`)과 `RankedSet.score_breakdown`(채널별 원점수·순위·RRF `contribution`·`rerank`)을 응답에 포함한다. 확인 순서: (1) `plan.filters`에 보안 필터(`tenant_id`·`collection_id`·`acl_*`·`is_current`)가 있는가 (2) `channel_runs[].status`가 `ok`인가(`timeout`·`error`면 `degraded[]`) (3) 후보의 `explain[]`에 `below_gate`·`deduped`·`mmr_demoted` 사유 (4) `ContextPack.omitted[].reason`. 검색 0건의 흔한 원인은 §9 표에 있다.

### 5.4 IDE 디버거 부착

`rag` 콘솔 스크립트는 `rag_platform.cli:main`이다. 디버거가 `python -m rag_platform.cli`로 기동할 수 있도록 `src/rag_platform/cli/__main__.py`(제안, `main()` 호출 한 줄)를 둔다. VS Code `launch.json` 예시(`.vscode/`는 개인 설정이므로 커밋하지 않고 아래를 복사한다; 디버거 타입 이름 `debugpy`는 확인 필요 as of 2026-09):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "rag serve api (LocalRunner)",
      "type": "debugpy",
      "request": "launch",
      "module": "rag_platform.cli",
      "args": ["serve", "api"],
      "envFile": "${workspaceFolder}/.rag/env.host",
      "justMyCode": false,
      "console": "integratedTerminal"
    },
    {
      "name": "rag run-stage parse (samples/notice.hwpx)",
      "type": "debugpy",
      "request": "launch",
      "module": "rag_platform.cli",
      "args": ["run-stage", "parse", "--input", "samples/notice.hwpx", "--profile", "lite", "--json"],
      "justMyCode": false
    },
    {
      "name": "pytest: current file",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-x", "-p", "no:cacheprovider"],
      "justMyCode": false
    }
  ]
}
```

`envFile`의 `.rag/env.host`는 §8의 호스트 모드 값을 담은 개인 파일(gitignored)이다.

### 5.5 로그·트레이스·메트릭

| 신호 | 개발 설정 | 열람 |
|------|-----------|------|
| 로그 | `RAG_LOG__FORMAT=console`, `RAG_LOG__LEVEL=debug`(제안, 설정 레퍼런스 §2.13). 필드는 바이블 §6.5(`event, level, tenant_id_hash, job_id, trace_id, stage, code`) | 터미널. 비밀·본문 텍스트는 절대 기록되지 않는다(`SecretStr`, redaction) |
| 트레이스 | `compose.observability.yaml` 기동 + `RAG_OTEL__EXPORTER_OTLP_ENDPOINT=http://localhost:4317`(모드 B) | Jaeger UI에서 스팬 `rag.ingest.parse`, `rag.retrieve.dense`, `rag.rerank`… 속성은 Weaver 생성 상수만(`gen_ai.*`, `retrieval.*`, `rag.*`) |
| 콘텐츠 캡처 | `RAG_OTEL__CONTENT_CAPTURE=none` — v1은 `none`만 허용(정본) | 청크 본문은 트레이스에 없다. 점수 분해는 `RankedSet`에서 |
| 메트릭 | `GET :9090/metrics` | `rag_ingest_stage_duration_seconds{stage}`, `rag_query_latency_seconds` 등 바이블 §6.5 정본 목록; `tenant_id` 라벨 없음 |

---

## 6. GPU 개발 옵션

**결정:** 코어 패키지·코어 이미지는 CUDA를 포함하지 않고 `[gpu]` extra는 비어 있다. GPU는 **서빙 컨테이너**(TEI GPU 리랭커, vLLM pooling BGE-M3 3-in-1)와 **사이드카 `ocr-gpu`**에만 있으며, 개발자는 이를 로컬 컨테이너 또는 원격 엔드포인트로 붙이고 코어는 `RAG_SIDECAR__*_URL`(제안)만 바꾼다(바이블 §7.1, 배포 아키텍처 §3.3; [ADR-0009](../06-adr/0009-embedding-serving-vllm-pooling-tei-inprocess.md), [ADR-0008](../06-adr/0008-ocr-default-rapidocr-ppocrv5-korean.md), [ADR-0035](../06-adr/0035-python-version-and-toolchain-pins.md) 중립 항).

| 옵션 | 구성 | 필요 자원(초안) | 환경 변수 | 언제 |
|------|------|------|-----------|------|
| **A. CPU 전용(기본)** | `lite`: bge-m3 dense ONNX int8 `in_process` + `sparse_bm25`, RapidOCR CPU, 리랭커 생략 또는 TEI CPU(`reranker` 서비스) | 4~8 vCPU, 16~32GB | 없음(`RAG_SIDECAR__RERANKER_SERVER_URL=http://localhost:8080`은 TEI CPU 켠 경우만) | 어댑터·계약·검색 로직 개발 전부 |
| **B. 로컬 GPU 서빙** | Docker `--gpus all` + NVIDIA Container Toolkit로 TEI GPU(`bge-reranker-v2-m3`) 및 vLLM 0.29 `--runner pooling`(`BAAI/bge-m3` dense+sparse) 컨테이너 | GPU 1장, VRAM 6~8GB 권장(bge-m3·bge-reranker 각 fp16 약 1.1GB; 배포 가이드 §2.1) | `RAG_SIDECAR__EMBEDDING_SERVER_URL`, `RAG_SIDECAR__RERANKER_SERVER_URL`; 컬렉션은 `standard` 프로파일 | `adapters/embed/vllm_pooling_bge_m3`, `adapters/rerank/tei_cross_encoder`, `sparse_learned` 경로 |
| **C. `ocr-gpu` 사이드카** | `docker build sidecars/ocr-gpu`(자체 `uv.lock`, PaddlePaddle CUDA 베이스) → `POST /v1/convert` | GPU(T4/L4급), 이미지 수 GB | `RAG_SIDECAR__OCR_GPU_URL`; 프로파일 `premium` 또는 `parse.options.ocr` 오버라이드 | `pdf_scanned_gpu` 경로, PP-OCRv5 server 비교 |
| **D. 원격 GPU(공유 스테이징)** | 스테이징 `rag-serving` 엔드포인트를 개발자가 참조 | 없음(로컬) | 위 URL을 원격 주소로; 원격 호스트는 `EgressPolicy.allowed_hosts`에 등재 | GPU 없는 노트북에서 `standard` 경로 확인 |

주의 사항:

- **임베딩 공간이 다르다.** `embedding_space_id = H("space", model_id, revision, dim, normalized, prompt_hash, quantization, vocab_id)`(바이블 §6.2)에 `quantization`이 들어가므로 `lite`의 ONNX int8 `in_process`와 옵션 B의 vLLM fp16은 **다른 공간**이다. 서빙을 바꾸면 컬렉션을 새로 만들거나 blue/green 재색인해야 하며, 같은 공간 안에서 이미지·엔진만 바꾸는 경우에만 코사인 ≥ 0.9999 동등성 게이트(D-16)가 적용된다.
- **청크 임베딩 캐시는 봉투가 없어** `H("embed", embedding_space_id, "document", embed_text)`로 공간별로 적중한다(바이블 §4.1). 서빙 이미지 digest가 바뀌어도 같은 공간이면 재임베딩 비용이 없다.
- **WSL2 GPU**는 Windows NVIDIA 드라이버 + WSL2 CUDA 지원 + Docker Desktop GPU 패스스루 조합이며 조합별 지원 여부는 확인 필요(as of 2026-09; §10.4).
- 개발용 GPU 공유(`time_slicing`)는 스테이징까지만 허용되고 운영은 MIG 또는 전용 GPU다(배포 가이드 §2.2). 개발 머신에는 해당 없음.

---

## 7. IDE 설정

### 7.1 단일 진실 원천

**결정:** ruff·mypy·import-linter 설정은 **루트 `pyproject.toml`만**이 정본이다(`[tool.ruff]`, `[tool.mypy]`, `[tool.importlinter]`; 저장소 구조 §3.2, [ADR-0035](../06-adr/0035-python-version-and-toolchain-pins.md) 정적 검사 행). IDE·pre-commit·CI는 같은 파일을 읽으며, IDE 설정으로 규칙을 켜거나 끄지 않는다. `.editorconfig`(제안, 커밋)로 인코딩 UTF-8·LF·끝 개행·들여쓰기(Python 4칸, YAML/JSON 2칸)를 편집기 중립으로 고정한다. `.vscode/`·`.idea/`는 개인 설정이므로 커밋하지 않고(저장소 구조 §9), 권장 확장 목록만 `.vscode/extensions.json`(제안)으로 공유한다.

| 도구 | 로컬 명령(CI와 동일) | 통과 기준 |
|------|----------------------|-----------|
| ruff lint | `uv run ruff check .` | 위반 0. 자동 수정은 `--fix` |
| ruff format | `uv run ruff format --check .` | diff 0 |
| mypy | `uv run mypy src/` | 오류 0(`strict = true`, `pydantic.mypy`). 벤더 스텁 부재는 모듈 단위 `ignore_missing_imports`만, 함수 단위 `type: ignore`는 사유 주석 필수(ADR-0035) |
| import-linter | `uv run lint-imports` | 계약 5개 전부 KEPT(저장소 구조 §3.2) |
| 잠금 | `uv lock --check` | 변경 없음 |
| 스키마·문서 | `node tools/validate-contracts.mjs --root .` | 오류 0(`--json report.json`으로 리포트) |

### 7.2 VS Code

권장 확장: `ms-python.python`, `charliermarsh.ruff`, `ms-python.mypy-type-checker`(확장 ID·설정 키는 확인 필요 as of 2026-09). 인터프리터는 워크스페이스 `.venv`(Linux/macOS `.venv/bin/python`, Windows 네이티브 `.venv/Scripts/python.exe`). 아래는 `.vscode/settings.json` 개인 사본 예시다.

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "ruff.nativeServer": "on",
  "ruff.configuration": "${workspaceFolder}/pyproject.toml",
  "mypy-type-checker.importStrategy": "fromEnvironment",
  "mypy-type-checker.args": ["--config-file=${workspaceFolder}/pyproject.toml"],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "files.eol": "\n",
  "files.insertFinalNewline": true,
  "files.trimTrailingWhitespace": true,
  "files.exclude": {
    "**/.rag": true,
    "**/build": true,
    "**/__pycache__": true
  }
}
```

PyCharm: 인터프리터를 `.venv`로 지정하고 Ruff 플러그인을 `pyproject.toml` 설정으로 연결한다. mypy는 IDE 플러그인 대신 `uv run mypy src/`를 외부 도구로 등록해도 된다(IDE 내장 검사기는 `strict` 결과와 다를 수 있다).

### 7.3 pre-commit

**결정:** 커밋 훅은 **빠른 검사만**(ruff check·format, import-linter, 잠금 검사, JSON/YAML 문법, 끝 개행·공백, 비밀 키 탐지, `schemas/`·문서 검증기) 실행하고, mypy·pytest·라이선스 게이트는 훅에 두지 않는다(수 분 소요 → 훅 우회 유발). 이들은 `just check`와 CI가 강제한다. 훅 저장소·리비전은 확인 필요(as of 2026-09)이며 아래는 구조 예시다.

```yaml
# .pre-commit-config.yaml (예시; rev 는 확인 후 고정)
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: "<pin>"
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format
  - repo: https://github.com/astral-sh/uv-pre-commit
    rev: "<pin>"
    hooks:
      - id: uv-lock            # uv lock --check 와 동치인지 확인 필요(as of 2026-09)
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: "<pin>"
    hooks:
      - id: check-json
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: detect-private-key
      - id: check-added-large-files
        args: ["--maxkb=1024"]   # samples/·tests 픽스처 1MB 규칙(§4.1)
  - repo: local
    hooks:
      - id: lint-imports
        name: import-linter (layers + forbidden, C 등급 임포트 차단)
        entry: uv run lint-imports
        language: system
        pass_filenames: false
        files: ^(src|plugins|sdk/python)/.*\.py$
      - id: validate-contracts
        name: schemas/ + 03-contracts 기계 검증 (node 있을 때만)
        entry: sh -c 'command -v node >/dev/null 2>&1 && node tools/validate-contracts.mjs --root . --quiet || echo "node 없음: CI에서 검사"'
        language: system
        pass_filenames: false
        files: ^(schemas/|docs/03-contracts/|docs/02-architecture/00-design-bible\.md)
```

훅을 건너뛰어야 할 때(`--no-verify`)는 PR 설명에 사유를 적고, CI가 같은 검사를 다시 실행하므로 결과는 같다.

---

## 8. 환경 변수 예시(`.env.example`)

정본 변수 이름은 바이블 §6.6의 여덟 개(`RAG_PG__DSN`, `RAG_OBJECT_STORE__URI`, `RAG_VALKEY__URL`, `RAG_TEMPORAL__ADDRESS`, `RAG_PROFILE__PATH`, `RAG_AUTH__OIDC_ISSUER`, `RAG_OTEL__EXPORTER_OTLP_ENDPOINT`, `RAG_OTEL__CONTENT_CAPTURE`) + `RAG_SECRETS__PROVIDER`이고, 나머지는 [설정 레퍼런스](../09-operations/02-configuration-reference.md) §2의 제안 변수다. 파일 정본은 `deploy/compose/.env.example`(배포 가이드 §3.3)이며 아래는 그것을 **개발 관점**으로 주석한 것이다. 환경 변수는 프로파일 값을 덮어쓰지 못한다(설정 레퍼런스 §1.1) — 청크 크기·`fusion.k`·레이트리밋 모드는 프로파일 키다.

```bash
# ===== 정본(바이블 §6.6) =====
RAG_PG__DSN=postgresql://rag_app:CHANGE_ME@postgres:5432/rag_ledger   # 모드 B(호스트 앱): postgres → localhost
RAG_OBJECT_STORE__URI=file:///data/artifacts                          # 모드 B: file:///home/<user>/src/rag-platform/.rag/artifacts
RAG_VALKEY__URL=redis://valkey:6379/0                                 # 모드 B: valkey → localhost
# RAG_TEMPORAL__ADDRESS=temporal:7233        # 비우면 LocalRunner(개발). --durable 또는 start-dev 시에만 설정
# RAG_PROFILE__PATH=/config/profiles         # 비우면 내장 프로파일만. 운영자 YAML 디렉터리 실험 시
# RAG_AUTH__OIDC_ISSUER=                     # 개발 모드는 API 키. standard 프로파일 실험 시 Keycloak/Dex
RAG_OTEL__EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317           # observability 오버레이 없으면 비움(내보내기 끔, 계측 유지)
RAG_OTEL__CONTENT_CAPTURE=none                                        # v1은 none 만 허용
RAG_SECRETS__PROVIDER=env

# ===== 제안(설정 레퍼런스 §2; 확정 전) =====
RAG_PROFILE__ID=lite
RAG_SERVE__PORT=8000
RAG_SERVE__METRICS_PORT=9090
RAG_API__PUBLIC_BASE_URL=http://localhost:8000                        # orchestrator=local 만 http 허용
RAG_QDRANT__URL=http://qdrant:6333                                    # 모드 B: localhost
RAG_QDRANT__PREFER_GRPC=true
RAG_FETCH__FILE__ALLOWED_ROOTS=["/samples"]                           # 모드 B: ["/home/<user>/src/rag-platform/samples"]; 비우면 file:// 전부 fetch.egress_denied
RAG_MODELS__CACHE_DIR=/models                                         # 모드 B: ./.rag/models 절대 경로
RAG_MODELS__OFFLINE=false                                             # 개발: 최초 다운로드 허용
RAG_LOG__FORMAT=console                                               # 운영 json
RAG_LOG__LEVEL=debug
RAG_PLUGINS__ALLOW_UNVERIFIED=true                                    # 개발 전용. orchestrator=temporal 이면 기동 실패
RAG_RELAY__MODE=procrastinate                                         # lite

# ===== 서드파티 패스스루(설정 레퍼런스 §2.18) =====
HF_HOME=/models/hf                                                    # RAG_MODELS__CACHE_DIR 과 같은 볼륨
HF_HUB_OFFLINE=0
OMP_NUM_THREADS=4                                                     # Docling·ONNX Runtime
```

규칙:

- **비밀은 `.env`에 두지 않는다.** compose `secrets:`(`.secrets/` 파일) 또는 `RAG_SECRETS__PROVIDER=openbao`의 `credentials_ref`. 개발용 `CHANGE_ME`도 커밋 금지(`.env`·`.secrets/`·`.rag/`는 `.gitignore`).
- **미지 변수는 기동 실패다.** `RAG_` 접두 변수 중 `Settings`가 모르는 이름(`RAG_VALKY__URL`)은 `check_unknown_env()`가 거부한다(컴포넌트 아키텍처 §5.2, 설정 레퍼런스 §2.1). 제안 변수도 모델에 있어야 쓸 수 있다.
- **모드 B 사본**은 `.rag/env.host`(gitignored)에 두고 셸(`set -a; . .rag/env.host; set +a`)·direnv·IDE `envFile`로 로드한다. 배열 값(`RAG_FETCH__FILE__ALLOWED_ROOTS`)은 pydantic-settings JSON 배열 문법이다.
- Windows 네이티브에서 `file://` URI는 `file:///C:/Users/<user>/src/rag-platform/.rag/artifacts` 형식이다(§10).

---

## 9. 흔한 문제

| 증상 | 원인 | 조치 |
|------|------|------|
| `uv lock`/`uv sync` 실패: `kiwipiepy>=0.24.0` 해소 불가 | Apache-2.0 wheel 미공개 상태에서 `[kiwi]` extra가 선언됨 | §2.2 잠정 결정대로 extra 미선언 상태인지 확인; 개인 설치는 `uv pip install`로만 |
| `uv sync`가 시스템 Python을 잡음 | `.python-version` 무시 또는 uv 관리 인터프리터 미설치 | `uv python install 3.12 3.13`; `uv python pin 3.12` |
| `app` 기동 실패 `unknown environment variable RAG_VALKY__URL` | 최상위 변수명 오타(`check_unknown_env`) | 바이블 §6.6·설정 레퍼런스 §2 철자로 수정 |
| `/readyz`가 120초 넘게 503 | bge-m3 ONNX int8·mecab-ko-dic·RapidOCR 최초 다운로드, 또는 `HF_HUB_OFFLINE=1`인데 미러 없음 | 로그 확인; 개발은 `HF_HUB_OFFLINE=0`, `RAG_MODELS__OFFLINE=false`; 캐시 볼륨 `./.rag/models` 재사용 |
| `rag up` 실패 `port is already allocated`(8000·5432·6333·6379·7233) | 호스트 포트 충돌(로컬 PostgreSQL 등) | compose 호스트 포트 변경 또는 `RAG_SERVE__PORT`(제안); 컨테이너 간 주소는 영향 없음 |
| 모드 B에서 `connection refused` to `postgres:5432` | 컨테이너 이름을 호스트에서 해석 불가 | `.rag/env.host`의 호스트를 `localhost`로 |
| 샘플 수집 잡 `failed`, `last_error.code = fetch.egress_denied` | `file://` 스킴 불허(프로파일 `allowed_schemes`) 또는 `RAG_FETCH__FILE__ALLOWED_ROOTS` 비움·경로 불일치 | 개발 프로파일(`orchestrator=local`, §3.3) + 허용 루트에 `samples/` 절대 경로; 운영 프로파일로는 재현되지 않는 것이 정상 |
| HWP 5.0 샘플만 실패(`parse.sidecar_unavailable` 후 폴백 실패) | `lite`는 사이드카 없음; unhwp는 x64 전용(arm64 macOS에서는 hwp-hwpx-parser만) | 정상 동작. Java 사이드카 경로는 `docker build sidecars/parser-workers` 후 `RAG_SIDECAR__PARSER_WORKERS_URL` |
| DOC 샘플 `parse.unsupported_format` | `lite`에 `lo-sidecar` 없음(GPL opt-in) | 정상. DOC 경로 개발은 `rag-platform-gpl-sidecars` 이미지를 컨테이너로 띄우고 `RAG_SIDECAR__LO_SIDECAR_URL` + `optIn` 승인 프로파일 |
| 검색 0건 | 잡 미완료(`is_current=false` 세대만), ACL(`visibility`·`allow_principals`) 필터, 다른 `collection_id`, 질의 언어 불일치 | `GET /v1/documents/{id}/commits`의 `status=committed`; `--explain`으로 `plan.filters` 확인 |
| `degraded[{rerank, skipped_by_policy}]` | 리랭커 미구성(`lite` 기본) | 정상. TEI CPU `reranker` 서비스 켜고 `RAG_SIDECAR__RERANKER_SERVER_URL` |
| 모든 질의 429 `api.rate_limited` | Valkey 중단 + 프로파일 `fail_mode: closed` | 개발 프로파일은 `open`(§3.3); Valkey 복구 |
| `lint-imports` 실패: 새 모듈이 계층에 없음 | 바이블 §12 트리 밖 모듈 추가 | 저장소 구조 §9 규칙대로 미해결 이슈 제안 후 `layers` 갱신; 임시 우회 금지 |
| `lint-imports` 실패: `pipelines`가 `temporalio` 임포트 | D-17 위반 | 오케스트레이션 기능은 `orchestration/temporal/`로(ADR-0003 준수 확인 1) |
| mypy `strict` 오류: 벤더 라이브러리 타입 없음 | 스텁 부재(ONNX 바인딩, hwpx 등) | `pyproject.toml` `[[tool.mypy.overrides]]` 모듈 단위 `ignore_missing_imports = true`; 함수 단위 `type: ignore[<code>]  # 사유` |
| 골든 테스트 `golden_hash` 불일치(내용은 같아 보임) | 픽스처 줄바꿈 CRLF, NFC/NFKC 혼용, 시계 주입 누락 | `.gitattributes` `* text=auto eol=lf`; 픽스처는 바이너리 취급(`-text`); `FakeStageContext` 고정 `now()` |
| Windows: `.rag/artifacts` 쓰기 실패 `path too long` | `tenants/{ulid}/artifacts/{kebab}/{2}/{64자}.json` 경로가 MAX_PATH 초과 | 긴 경로 활성화(`LongPathsEnabled`) 또는 짧은 루트(`C:\src`) 또는 WSL2(§10) |
| Docker Desktop에서 Qdrant·PostgreSQL OOM | WSL2 VM 기본 메모리 상한 | `%UserProfile%\.wslconfig`의 `memory=16GB` 이상(초안), Docker Desktop 재시작 |
| `temporal server start-dev` 재시작 후 잡 사라짐 | 개발 서버는 SQLite·비영속 | 정상. 내구 확인은 `--durable` |
| `tests/replay` 실패 `Nondeterminism` | 워크플로우 코드에 `datetime.now`·난수·I/O | `ctx.now()`·`workflow.random()`만; ADR-0003 코드 리뷰 (c) |
| `node tools/validate-contracts.mjs` 실패 `열거 불일치` | `schemas/*.schema.json` `$defs` 값이 바이블 §5.7과 다름 | 스키마 소유 문서(03-contracts) 절차로 수정; 바이블 표를 임의 변경 금지(§1.2) |

---

## 10. Windows/WSL 참고

### 10.1 지원 지위

**결정:** Windows 개발 머신은 **WSL2(Ubuntu 계열) + Docker Desktop(WSL2 백엔드)** 조합을 1급 개발 환경으로 지원하고, Windows 네이티브(WSL 없는 PowerShell + `.venv`)는 **A 등급 순수 Python 경로의 코드 편집·단위 테스트·`run-stage`에 한해** 동작을 기대하되 CI 대상은 아니다. Windows 네이티브 워커(컨테이너 없는 운영)는 비지원이다([범위와 비목표](../00-vision/04-scope-and-non-goals.md) 플랫폼 표; 배포 가이드 §2.1 OS 행). Linux x86_64가 기준 플랫폼이고 arm64(macOS)는 `lite` 개발에 한정된다(unhwp x64 전용).

| 경로·도구 | WSL2 | Windows 네이티브 | 비고 |
|-----------|:----:|:----:|------|
| uv, Python 3.12/3.13, ruff, mypy, import-linter, pytest | 지원 | 지원 | uv 설치는 공식 설치 안내(설치 명령·`winget` 패키지 ID는 확인 필요 as of 2026-09) |
| python-hwpx(HWPX), pypdfium2 + pdftext, docx2python, Trafilatura, charset-normalizer, markdown-it-py | 지원 | 지원(순수 Python·manylinux/win wheel) | Docling 2.129.x·RapidOCR ONNX의 Windows wheel 동작은 확인 필요(as of 2026-09) |
| python-mecab-ko 1.3.7 + mecab-ko-dic, kss 6.0 | 지원 | 지원(Windows wheel 제공) | [ADR-0021](../06-adr/0021-korean-analyzer-kiwi-promotion-and-interim-mecab-kss.md) 결정 동인 "설치 용이성"; KoNLPy의 "Windows 미지원"은 KoNLPy 래퍼 한정([07-tech-landscape/13](../07-tech-landscape/13-korean-nlp-tokenization-and-language-resources.md) 함정 행) |
| unhwp(HWP 5.0 헬퍼, x64) | 지원 | 확인 필요 | `helper_process`(`multiprocessing spawn`) |
| compose 개발 스택(PostgreSQL·Qdrant·Valkey) | Docker Desktop | Docker Desktop | 컨테이너는 어느 쪽에서도 Linux |
| 사이드카(`parser-workers` JVM, `ocr-gpu` CUDA, `lo-sidecar` GPL) | 컨테이너만 | 컨테이너만 | 네이티브 설치 금지(§1) |
| pre-commit 훅 | 지원 | 지원(sh 훅은 Git for Windows의 sh) | 저장소를 WSL 안에 두었으면 훅도 WSL에서 설치 |
| Node 22(코드젠·검증기) | 지원 | 지원 | — |

### 10.2 LibreOffice·libmagic

- **LibreOffice는 설치하지 않는다.** DOC/RTF/ODT와 HWP 최후 폴백은 `lo-sidecar` 컨테이너(GPLv3, 별도 저장소 `rag-platform-gpl-sidecars`, Helm `optIn.loSidecar`)이며 코어 이미지·개발 의존에 없다. Windows에 LibreOffice를 네이티브로 설치해 `soffice --headless --convert-to`로 **픽스처를 한 번 변환하는 것**(예: 합성 DOC 만들기)은 개발자 개인 작업으로 허용되지만, 파이프라인 코드가 호스트 `soffice`를 호출하는 경로는 만들지 않는다([07-tech-landscape/03](../07-tech-landscape/03-document-parsing-office-html-text.md) DOC 운영 이슈 — 프로파일 락·행 걸림·좀비 프로세스는 컨테이너 격리로만 다룬다).
- **libmagic도 설치하지 않는다.** 포맷 판별은 puremagic + 자체 ZIP/OLE 스니퍼이고 HWPX는 ZIP 내부 `mimetype`(`application/hwp+zip`) 또는 `Contents/content.hpf`로 판정하므로 libmagic 결과에 의존하지 않는다(선정 매트릭스 `format_detector` 행). `python-magic-bin`(Windows DLL 번들)을 개발 편의로 추가하면 Linux 컨테이너와 판정이 갈리므로 거부한다.

### 10.3 WSL2 구성 권고(초안)

| 항목 | 권고 | 이유 |
|------|------|------|
| 저장소 위치 | WSL 파일시스템 안(`~/src/rag-platform`), `/mnt/c/…` 금지 | I/O 성능·inotify(파일 감시)·권한 비트; `.rag/artifacts` 수천 파일 |
| 메모리 | `%UserProfile%\.wslconfig`에 `memory=16GB` 이상, `swap` 여유 | Qdrant + PostgreSQL + bge-m3 ONNX + Docling 동시 기동(배포 가이드 §2.1 최소 16GB) |
| 줄바꿈 | `git config --global core.autocrlf false` + 저장소 `.gitattributes`(`* text=auto eol=lf`, 픽스처·샘플은 `-text`) | 골든 해시·`content_hash` 안정성 |
| 경로 | `file://` URI는 WSL 경로(`file:///home/<user>/src/rag-platform/samples`) | Windows 드라이브 경로를 컨테이너·WSL이 다르게 해석 |
| Docker | Docker Desktop "Use the WSL 2 based engine" + 해당 배포판 통합 켬 | `rag up`이 WSL 셸에서 `docker compose` 호출 |
| 시각 | WSL 시계가 호스트와 어긋나면 `Idempotency-Key` 만료·JWT `exp` 판정 오류 | 절전 복귀 후 시각 동기화 확인(배포 가이드 §2.1 시각 행) |

### 10.4 GPU(WSL2)

Windows NVIDIA 드라이버(WSL CUDA 지원 포함) + Docker Desktop GPU 지원으로 §6 옵션 B·C 컨테이너를 `--gpus all`로 띄울 수 있다. 드라이버·CUDA 마이너 조합, Docker Desktop 버전별 GPU 패스스루 지원은 확인 필요(as of 2026-09)이며 CI는 Linux GPU 러너만 쓴다.

### 10.5 PowerShell 사용자 메모

- 이 문서의 셸 예시는 POSIX sh 기준이다. PowerShell에서는 `&&` 대신 `;` 또는 `if ($?) { … }`, 환경 변수는 `$env:RAG_LOG__LEVEL = "debug"`, `.env` 로드는 IDE `envFile` 또는 스크립트로 한다.
- `uv run …`·`docker compose …`는 PowerShell에서도 같다. `just` Windows 바이너리 존재는 확인 필요(as of 2026-09).
- 긴 경로: `.rag/artifacts` 키(§5.2)는 100자 이상이므로 레지스트리 `LongPathsEnabled` 또는 짧은 루트를 쓴다(§9).

---

## 결정 사항 요약

- **결정:** 필수 개발 도구는 uv·Python 3.12/3.13(uv 관리)·Docker Engine + Compose v2·git 넷이며, JVM·LibreOffice·CUDA·libmagic은 개발 머신에 설치하지 않고 컨테이너(사이드카·서빙 이미지) 또는 대체 라이브러리(puremagic)로 대신한다([ADR-0035](../06-adr/0035-python-version-and-toolchain-pins.md), [ADR-0001](../06-adr/0001-license-grade-table-and-d02-interpretation.md), [ADR-0033](../06-adr/0033-sidecar-convert-contract-and-isolation-ladder.md)).
- **결정:** `.python-version = 3.12`(하한 인터프리터에서 개발), 3.13은 `uv run --python 3.13`·CI 매트릭스로 검증한다. `make`는 요구하지 않고 `justfile`(제안)은 정본 `uv`·`rag` 명령의 래퍼다. Node.js 22 LTS는 선택 개발 도구로 등재하며 기존 `tools/validate-contracts.mjs`는 Python 이식 없이 유지한다(저장소 구조 미해결 이슈 11 해소).
- **결정(잠정):** `kiwipiepy>=0.24.0` Apache-2.0 wheel 공개 확인 전까지 `[kiwi]` extra를 `pyproject.toml`에 선언하지 않는다(단일 `uv.lock` 해소 보장). 바이블 §6.7 extras 6종 철자는 유지하고 공개 즉시 pin-and-bump로 복원한다([ADR-0021](../06-adr/0021-korean-analyzer-kiwi-promotion-and-interim-mecab-kss.md)).
- **결정:** 개발·CI·하네스는 비내구 `LocalRunner`(`RAG_TEMPORAL__ADDRESS` 미설정)로 실행하고, 일상 개발은 "모드 B: compose 데이터 계층 + 호스트 `api` 프로세스"를 기본으로 한다. 개발 파생 프로파일(`-local`/`-dev` 접미)은 프로덕션 컬렉션에 쓰지 않으며 Temporal 셸 검증은 `start_time_skipping` 테스트·`start-dev`·`--durable` 오버레이로 한다([ADR-0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md)).
- **결정:** `samples/`는 KOGL 제1유형·Apache-2.0·합성 문서만, 파일당 1MB 이하, `samples/MANIFEST.json`(제안)에 출처·라이선스·`content_hash`를 기록하고 CI가 대조한다. PII 경로는 합성 문서로만 검증하고 외부 평가셋은 `EvalDataset`으로 등록한다([ADR-0023](../06-adr/0023-evaluation-qrels-answer-spans-and-linear-ndcg.md)).
- **결정:** 스테이지 디버깅은 프로덕션과 같은 `run_stage` 위의 `rag run-stage`(파이프라인 프레임워크 §13 제안)와 바이블 §13.3 키 규약의 `file://` 산출물 열람, `--explain` 점수 분해로 한다. 콘텐츠 캡처는 `none`만이며 디버거 기동용 `cli/__main__.py`(제안)를 둔다([ADR-0032](../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md), [ADR-0037](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md)).
- **결정:** GPU는 서빙 컨테이너(TEI·vLLM pooling)와 `ocr-gpu` 사이드카에만 있고 코어 `[gpu]` extra는 비어 있다. 개발자는 `RAG_SIDECAR__*_URL`(제안)만 바꾸며, `in_process` int8과 vLLM fp16은 `embedding_space_id`가 다른 별개 공간이므로 컬렉션을 새로 만든다([ADR-0009](../06-adr/0009-embedding-serving-vllm-pooling-tei-inprocess.md), [ADR-0008](../06-adr/0008-ocr-default-rapidocr-ppocrv5-korean.md)).
- **결정:** ruff·mypy·import-linter 설정은 루트 `pyproject.toml`만이 정본이고 IDE·pre-commit·CI가 같은 파일을 읽는다. pre-commit은 빠른 검사(ruff·import-linter·잠금·JSON/YAML·비밀·1MB 파일·스키마 검증기)만, mypy·pytest·라이선스 게이트는 `just check`·CI가 강제한다. `.editorconfig`·`.vscode/extensions.json`(제안)만 공유하고 개인 IDE 설정은 커밋하지 않는다.
- **결정:** Windows는 WSL2 + Docker Desktop을 1급으로, Windows 네이티브는 A 등급 순수 Python 경로의 편집·단위 테스트에 한해 지원(CI 미포함), 네이티브 워커는 비지원이다. LibreOffice·libmagic은 어떤 경우에도 개발 의존에 넣지 않는다.

## 미해결 이슈

1. **`justfile`·`.editorconfig`·`.vscode/extensions.json`·`.pre-commit-config.yaml`·`samples/MANIFEST.json`·`src/rag_platform/cli/__main__.py`의 바이블 §12 등재.** 모두 바이블 트리에 없는 제안 파일이다. 저장소 구조 미해결 이슈 2와 묶어 patch로 등재 여부를 architecture 소유자에게 제안한다.
2. **`rag run-stage`·`rag ledger migrate`·`rag tenant create`·`rag api-key create`의 CLI 등재.** 각각 파이프라인 프레임워크 §13, 배포 가이드 미해결 이슈 1·2의 제안이며 바이블 §12 `cli/` 목록 개정(minor)이 필요하다. 이 문서의 §2·§5 절차는 이 이름을 전제한다.
3. **개발 모드 부트스트랩 범위.** `rag up --profile lite`가 `demo` 테넌트·API 키·컬렉션까지 만들지(5분 기동 목표에 유리), 별도 명령으로 남길지(운영 절차와 동형) 배포 가이드 미해결 이슈 2·[보안과 컴플라이언스](../09-operations/05-security-and-compliance.md)와 합의한다.
4. **compose 오버레이 표면.** `compose.observability.yaml`·`compose.dev-opensearch.yaml`(제안)을 `rag up` 플래그(예: `--with observability,opensearch`)로 켤지 `docker compose -f … -f …` 직접 호출로 둘지, 그리고 OpenSearch 개발 오버레이의 이미지(`analysis-nori` 포함 빌드)와 값 파일 소유(배포 아키텍처 §4.1 compose 목록에 없음)를 확정한다.
5. **개발 프로파일의 형태.** 내장 `lite-local` 추가 vs `rag up` 생성·등록은 설정 레퍼런스 미해결 이슈 2가 소유한다. 확정되면 §3.3의 가칭을 실명으로 바꾸고 `-local`/`-dev` 접미 규칙을 프로파일 로딩 규칙(P-4 확장)으로 승격할지 검토한다.
6. **`[kiwi]` extra 복원 시점과 방식.** kiwipiepy 0.24.0 Apache-2.0 wheel의 PyPI 공개 확인(ADR-0021 재검토 조건) 후 pin-and-bump PR 한 번으로 extra 선언·잠금·문서를 되돌린다. 그 전까지 `uv sync --all-extras`가 5종 extras만 해소한다는 점을 CI 잠금 범위 검사(`tools/ci/check_lock_ranges.py`, 저장소 구조 제안)에 반영한다.
7. **Windows 네이티브 wheel 확인 목록.** Docling 2.129.x(docling-parse 네이티브 확장)·RapidOCR 3.9.x(ONNX Runtime)·unhwp(x64 헬퍼)의 Windows 동작은 확인 필요(as of 2026-09)다. 확인 결과에 따라 §10.1 표의 "지원/확인 필요"를 갱신하고, 미지원이면 Windows 네이티브 지원 범위를 "계약·검색·렌더 계층 편집"으로 좁힌다.
8. **`samples/` 원문 확정과 공공누리 표기.** §4.2의 문서 유형별 실제 원문(게시 기관·URL·KOGL 유형 표기)을 [골든셋 구축](../08-evaluation/03-golden-dataset-construction.md)의 코퍼스 선정과 함께 확정하고, `LicenseRef-KOGL-1` 표기(SPDX 미등재)를 03-contracts/16과 통일한다. HWP 5.0 병행 게시본이 없으면 `notice.hwp`는 생략한다.
9. **대용량 샘플·픽스처 보관.** 1MB 초과 파일의 오브젝트 스토리지 미러 + 해시 매니페스트 형식, `check-added-large-files` 임계값과의 정합은 [테스트 전략](./04-testing-strategy.md)에서 확정한다(저장소 구조 미해결 이슈 10).
10. **pre-commit 훅 저장소·리비전 고정과 `uv-lock` 훅 의미론.** `uv-pre-commit`의 `uv-lock` 훅이 `uv lock --check`와 동치인지, 훅 리비전을 어떤 주기로 범프할지(pin-and-bump 대상에 포함) [CI/CD](./05-ci-cd.md)에서 확정한다.
11. **TypeScript 코드젠 도구와 Node 잠금.** `json-schema-to-typescript`·`openapi-typescript`·`@hey-api/openapi-ts`의 JSON Schema 2020-12(`$defs`, URN `$ref`, `const`, `readOnly`) 지원·라이선스는 클라이언트 SDK 미해결 이슈 3이 소유한다. 이 문서는 Node 22 등재만 확정했으며 `package-lock.json` 커밋·`npm audit` 게이트는 같은 문서에서 정한다.
12. **`RAG_FETCH__FILE__ALLOWED_ROOTS`와 컨테이너 마운트 정합.** 모드 A(`/samples:ro` 마운트)와 모드 B(호스트 절대 경로)의 허용 루트가 다르므로 `.env.example`이 두 값을 어떻게 안내할지, `rag up`이 모드 B용 `.rag/env.host`(제안)를 생성할지 설정 레퍼런스·배포 가이드와 합의한다.
13. **두 셸 동등성 테스트의 개발 흐름.** 같은 골든 입력을 `LocalRunner`와 `start_time_skipping` 환경에서 실행해 `commit_hash`·`golden_hash`를 비교하는 적합성 키트 항목(ADR-0003 준수 확인 5, 파이프라인 프레임워크 미해결 이슈 10)이 확정되면 `just test`에 포함할지, 야간 CI만으로 둘지 [테스트 전략](./04-testing-strategy.md)에서 정한다.

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) §3 원칙 3·4·7, §4 D-01·D-02·D-14·D-17·D-18, §6 시스템 경계, §7 재현성, §9 문서 규약
- [설계 바이블](../02-architecture/00-design-bible.md) §1.2 변경 절차, §3.3 ADR 목록, §4.1 공통 규약(격리 모드·`stage_key`), §4.2 수집 파이프라인, §5.7 열거(`SourceFormat`)·오류 코드, §6.2 해시 결합(`embedding_space_id`·`content_hash`), §6.5 메트릭·스팬·로그, §6.6 환경 변수, §6.7 패키지·extras·사이드카, §7.1 `lite` 열, §11.1 두 실행기, §11.6 개발 모드·CI, §12 모듈 맵·`cli/`, §13.3 오브젝트 키, §14 API 표면
- [기술 지형 종합: 선정 매트릭스](../07-tech-landscape/00-summary-and-selection-matrix.md) `format_detector`·`korean_tokenizer`·`embedding_server`·`ocr_engine`·`orchestrator`·`license_scanner` 행, §프로파일별 기본 조합 `lite` 열, §운영·평가 공통 요구
- [Office·HTML·텍스트 파싱](../07-tech-landscape/03-document-parsing-office-html-text.md) 포맷 판별(puremagic vs python-magic), DOC 운영 이슈(LibreOffice 프로파일 락·행 걸림)
- [한국어 NLP·토크나이징](../07-tech-landscape/13-korean-nlp-tokenization-and-language-resources.md) python-mecab-ko Windows wheel, KoNLPy 함정
- [평가와 관측성](../07-tech-landscape/09-evaluation-and-observability.md) 골든셋 코퍼스 출처(KOGL 제1유형), Allganize RAG-Evaluation-Dataset-KO(MIT)
- [계약 개요](../03-contracts/00-contract-overview.md) §2 인벤토리, §6 명명 요약, §7 `H()`, §9 산출물 저장 규약
- [평가·피드백·사이드카 계약](../03-contracts/16-eval-feedback-and-sidecar-contracts.md) `EvalDataset.license`(`LicenseRef-KOGL-*`)
- [저장소 구조](./01-repository-structure.md) §2.1 트리(`.python-version`·`samples/`·`tools/`), §3 uv 워크스페이스, §3.4 명령, §6 생성 파일, §7 테스트 디렉터리, §9 위생 규칙, 미해결 이슈 2·5·10·11·12·15
- [배포 가이드](../09-operations/01-deployment-guide.md) §2 사전 요구(하드웨어·GPU·포트), §3 `lite` compose(서비스·`.env.example`·quickstart), §5 초기화(마이그레이션·부트스트랩·프로파일 검증·컬렉션), §6 모델 준비, §9 흔한 문제, 미해결 이슈 1·2
- [설정 레퍼런스](../09-operations/02-configuration-reference.md) §1 설정 계층, §2 환경 변수(정본·제안 지위), §2.13 관측성·로그, §2.18 서드파티 패스스루, §6.2 로딩 규칙 P-4, 미해결 이슈 2
- [파이프라인 프레임워크](../04-pipelines/01-pipeline-framework.md) §8.3 두 셸 동등성, §11.3 재개 재현성, §12 골든 회귀·`FakeStageContext`, §13 `rag run-stage`(제안)
- [컴포넌트 아키텍처](../02-architecture/02-component-architecture.md) §1.2 import-linter 계약, §5.2 `Settings`·`check_unknown_env`
- [배포 아키텍처](../02-architecture/08-deployment-architecture.md) §3.3 멀티스테이지 빌드(`python:3.13-slim` + uv, 기본 extras, `[gpu]` 제외), §3.4 모델 캐시, §4.1 compose 파일 목록
- [클라이언트 SDK](../05-api/06-client-sdks.md) §2 런타임(Node.js 22 LTS), 미해결 이슈 3
- [범위와 비목표](../00-vision/04-scope-and-non-goals.md) 플랫폼 지원 표(macOS/Windows 개발 머신·Windows 네이티브 워커)
- [골든셋 구축](../08-evaluation/03-golden-dataset-construction.md) 코퍼스 선정·라이선스
- 개발 문서(문서 맵 경로, 작성 예정 포함): [코딩 표준](./03-coding-standards.md), [테스트 전략](./04-testing-strategy.md), [CI/CD](./05-ci-cd.md), [플러그인 개발 가이드](./06-plugin-development-guide.md), [기여 가이드](./07-contributing.md), [릴리스 프로세스](./08-release-process.md)
- ADR: [0001 라이선스 등급표](../06-adr/0001-license-grade-table-and-d02-interpretation.md), [0003 오케스트레이터 중립 파이프라인·비내구 LocalRunner](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md), [0007 HWP 5.0 경로](../06-adr/0007-hwp5-java-sidecar-first-pyhwp-demoted.md), [0008 OCR 기본값](../06-adr/0008-ocr-default-rapidocr-ppocrv5-korean.md), [0009 임베딩 서빙](../06-adr/0009-embedding-serving-vllm-pooling-tei-inprocess.md), [0011 Valkey·오브젝트 스토리지](../06-adr/0011-kv-and-object-storage-valkey-rustfs-seaweedfs.md), [0012 lite Qdrant 단독](../06-adr/0012-lite-profile-qdrant-only-client-bm25.md), [0021 한국어 분석기](../06-adr/0021-korean-analyzer-kiwi-promotion-and-interim-mecab-kss.md), [0022 관측성 규약](../06-adr/0022-observability-genai-semconv-pin-and-license-boundary.md), [0023 평가 하네스](../06-adr/0023-evaluation-qrels-answer-spans-and-linear-ndcg.md), [0032 플러그인 SDK·적합성 키트](../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md), [0033 사이드카 convert 계약](../06-adr/0033-sidecar-convert-contract-and-isolation-ladder.md), [0035 Python 버전·툴체인](../06-adr/0035-python-version-and-toolchain-pins.md), [0037 산출물 캐시 스코프](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md), [0038 egress 정책](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md)
- 저장소 도구: `tools/validate-contracts.mjs`(`node tools/validate-contracts.mjs --root . [--json report.json] [--quiet]`; 의존성 0, JSON Schema 2020-12 부분 검증·바이블 §5.7 열거 대조·§5.1 인벤토리 커버리지)
