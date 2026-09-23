---
title: 플러그인 개발 가이드
status: active
owner: architecture
version: 0.1.0
last_updated: 2026-09-23
depends_on:
  - ../00-vision/00-design-brief.md
  - ../02-architecture/00-design-bible.md
  - ../02-architecture/05-plugin-architecture.md
  - ../04-pipelines/01-pipeline-framework.md
  - ../03-contracts/00-contract-overview.md
  - ../03-contracts/15-collection-profile-and-policy-contracts.md
  - ../07-tech-landscape/00-summary-and-selection-matrix.md
  - ../07-tech-landscape/06-vector-and-lexical-index-backends.md
  - ../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md
  - ../06-adr/0033-sidecar-convert-contract-and-isolation-ladder.md
  - ./01-repository-structure.md
  - ../09-operations/03-observability.md
---

# 플러그인 개발 가이드

## 목적

이 문서는 외부 개발자(그리고 코어 어댑터를 추가하는 코어 기여자)가 **파일 몇 개로 플러그인 하나를 만들어 배포·등재하기까지**의 절차를 순서대로 적은 실무 가이드다. 설계 바이블(`02-architecture/00-design-bible.md`, 이하 "바이블") §4.1(스테이지 공통 규약)·§5.3(`Capabilities`)·§5.6(`PluginMeta`)·§6.1(`plugin_id`)·§6.7(패키지·entry point)·§7.4(로딩 검증)·§12(모듈 맵)와 [플러그인 아키텍처](../02-architecture/05-plugin-architecture.md)(이하 "05")·[파이프라인 프레임워크](../04-pipelines/01-pipeline-framework.md)(이하 "01")가 정본이며, 이 문서는 그것을 **튜토리얼과 체크리스트로 옮기되 바꾸지 않는다**. 정본과 다른 이름이 필요한 곳은 "(제안)"으로 표시하고 `## 미해결 이슈`에 남긴다.

세 개의 튜토리얼(파서 PPTX, 인덱스 백엔드 pgvector, 리랭커 llama.cpp + 후처리기 변형)은 각각 다른 형태의 확장 지점 — `Stage` 특수화(수집 측), 포트(port) `IndexBackend`, `Stage` 특수화(질의 측) — 을 하나씩 다룬다. 코드는 **스케치**이며 임포트는 05 §2.1 규약대로 생략한다(`from rag_platform.contracts import *`, `from rag_platform.sdk import *`, `pydantic` 전제).

## 범위

- 포함: 개발 흐름, 프로젝트 템플릿(디렉터리·`pyproject.toml`·CI), entry point 등록, 설정 모델(`config_schema`) 선언, 능력 선언(`Capabilities`), `PluginMeta` 작성, 튜토리얼 3종, 적합성 키트(conformance kit) 사용과 결과 리포트 `conformance.json`(이 문서 소유), 격리 모드 선택과 사이드카 템플릿(서버·클라이언트), 관측성 자동 계측에서 플러그인이 하는 일과 하지 않는 일, 버전·호환성 선언, 배포(PyPI), 카탈로그 등재 절차, 리뷰 기준(라이선스·보안), 안티패턴.
- 제외: SDK 인터페이스 정의 자체(05 §2~§3), 셸 동작(01 §5~§7), 계약 필드 전문(03-contracts), 프로파일 스키마(03-contracts/15), 사이드카 이미지 하드닝 매니페스트(02-architecture/08), 코어 릴리스 절차(10-development/08), 테스트 전략 전반([테스팅 전략](./04-testing-strategy.md); 동시 작성 중이므로 바이블 §12 `testing/`·§11.6을 정본으로 삼는다).
- 작성 지시와 정본이 다른 곳은 정본을 따른다: 배포 패키지 이름은 `rag-platform-plugin-*`가 아니라 **`rag-plugin-{name}`**(바이블 §6.7), 사이드카는 **REST `POST /v1/convert`만**이며 gRPC 서버 템플릿은 두지 않는다(바이블 §3.2 O-10, [ADR-0033](../06-adr/0033-sidecar-convert-contract-and-isolation-ladder.md)).

## 1. 개발 흐름 한눈에

```mermaid
flowchart LR
    T["1 템플릿 생성<br/>cookiecutter-rag-plugin(제안)"] --> I["2 구현<br/>Stage 5멤버 또는 포트"]
    I --> D["3 선언<br/>config_schema · capabilities() · PluginMeta · entry point"]
    D --> C["4 적합성<br/>rag_platform.testing 상속 → conformance.json"]
    C --> S["5 격리 결정<br/>in_process / helper_process / sidecar"]
    S --> V["6 로컬 검증<br/>rag profile validate · rag plugin list --check-license · rag run-stage(제안)"]
    V --> P["7 배포<br/>uv build → PyPI rag-plugin-{name}"]
    P --> K["8 카탈로그 등재<br/>05 §13 PR + 리뷰(라이선스·보안)"]
```

| 단계 | 산출물 | 게이트(실패 코드) | 정본 |
|------|--------|-------------------|------|
| 구현 | `Stage[In, Out]` 5멤버(`plugin_id`, `config_schema`, `capabilities()`, `fingerprint()`, `run()`) 또는 포트(`IndexBackend`·`ContextRenderer`·`TokenCounter`·`KoreanAnalyzer`) | mypy strict 구조적 타입 검사(D-01) | 바이블 §4.1, 05 §2·§3 |
| 선언 | `pyproject.toml`의 entry point + `[tool.rag_platform.plugin]`(= `PluginMeta` 1개) | `PluginMeta` 스키마·`plugin_id` 조립값 대조(`contract.violation`) | 바이블 §5.6·§6.7, 03-contracts/15 §4 |
| 적합성 | `tests/test_conformance.py`, `conformance.json` | 키트 6모듈 통과(미통과 = 카탈로그 미등재) | 바이블 §12 `testing/`, 05 §10 |
| 격리 | `isolation_supported`, `linkage`, `sidecar_image` | `rag profile validate` (1)(2)(10) — `plugin.license_denied`, `plugin.capability_unsupported`, `profile.invalid` | 바이블 §4.1·§7.4, ADR-0033 |
| 배포 | wheel/sdist `rag-plugin-{name}`, 태그 `rag-plugin-{name}/v{semver}`(제안) | `uv lock --check`, 라이선스 게이트(pip-licenses + liccheck + SBOM) | 바이블 §6.7, 10-development/01 §5 |
| 등재 | 05 §13 카탈로그 행 PR | 등재 조건 5개(§13) | 05 §13 |

**결정:** 플러그인은 `rag_platform.sdk`·`rag_platform.contracts`(테스트에서만 `rag_platform.testing`)만 임포트한다. `rag_platform.adapters.*` 상속, `orchestration`·`api`·`storage`·`ledger` 임포트, 다른 플러그인 임포트는 금지다(10-development/01 §4.3; 바이블 §12 의존 방향, [ADR-0032](../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md)).

## 2. 프로젝트 템플릿

### 2.1 디렉터리 구조(cookiecutter)

템플릿 저장소 `cookiecutter-rag-plugin`(**제안**; 도구는 cookiecutter 2.x 또는 copier — 확인 필요 as of 2026-09)이 아래 구조를 생성한다. 변수는 `name`(kebab, `rag-plugin-` 접두 제외), `extension_point`(`ExtensionPoint` 14값), `implementation`(snake_case), `isolation`(3값), `license`(SPDX)다. 워크스페이스 멤버 레이아웃(10-development/01 §3.3: `src/{import_name}/`, `tests/`, `pyproject.toml`, `README.md`, `LICENSE`)과 같다.

```text
rag-plugin-{{name}}/
├── pyproject.toml                       # [project] + entry point + [tool.rag_platform.plugin] (§2.2)
├── README.md                            # 지원 포맷·모델·격리 모드·프로파일 예시(YAML 발췌)
├── LICENSE                              # SPDX = PluginMeta.license; NOTICE는 제3자 고지가 있을 때만
├── src/rag_plugin_{{name}}/
│   ├── __init__.py                      # __version__ = PluginMeta.version (단일 소스: hatch-vcs 또는 정적)
│   ├── config.py                        # config_schema (Pydantic v2, extra="forbid", frozen=True)
│   ├── {{extension_point}}.py           # Stage 특수화 또는 포트 구현 1개
│   ├── errors.py                        # 벤더 예외 → 카탈로그 코드 변환표(§3.3)
│   └── conformance.json                 # CI가 생성·갱신(§8.3); 패키지 데이터로 동봉
├── tests/
│   ├── test_conformance.py              # rag_platform.testing.{extension_point} 기반 클래스 상속(§8.1)
│   ├── golden/cases.json                # 골든 회귀(01 §12.2 제안)
│   └── fixtures/                        # 재배포 가능 라이선스 픽스처만(공공누리 제1유형 등), PII는 합성
├── sidecar/                             # isolation=sidecar 일 때만: Dockerfile · app.py(§9.3) · convert-options.schema.json
└── .github/workflows/ci.yml             # uv sync → ruff → mypy --strict → pytest → license gate → conformance.json 갱신
```

### 2.2 `pyproject.toml` 템플릿

```toml
[project]
name = "rag-plugin-{{name}}"                     # 바이블 §6.7: rag-plugin-{name} / import rag_plugin_{name}
version = "0.1.0"                                # = PluginMeta.version = Producer.plugin_version
requires-python = ">=3.12,<3.14"                 # D-01 · ADR-0035(코어와 동일 범위)
dependencies = ["rag-platform>=1.0,<2.0"]        # SDK 버전 = 코어 패키지 버전(05 §8)
license = "{{license}}"

[project.entry-points."rag_platform.{{extension_point}}"]   # 그룹 = rag_platform.{extension_point}
{{implementation}} = "rag_plugin_{{name}}.{{extension_point}}:{{ClassName}}"

[tool.rag_platform.plugin]                       # PluginMeta 1개(바이블 §5.6). schema_version 키 없음(plugin-meta.schema.json additionalProperties:false)
plugin_id = "{{extension_point}}.{{implementation}}"   # = "{그룹 접미}.{entry point 이름}" — 불일치는 contract.violation
extension_point = "{{extension_point}}"
role = "{{role_or_null}}"                        # 서브 역할(format_detector, korean_analyzer, token_counter, renderer …) 또는 생략
version = "0.1.0"
license = "{{license}}"
license_grade = "A"                              # A/B/C/D/X(D-02, ADR-0001); C는 isolation_supported=["sidecar"] 강제
territory = []                                   # 빈 배열 = 제한 없음
linkage = "pure_python"                          # 자기 배포물에 번들한 네이티브 코드 형태(의존성의 네이티브 확장은 무관)
isolation_supported = ["{{isolation}}"]          # = capabilities.isolation_modes (집합 동치, 03-contracts/15 M-2)
contracts_compat = ">=1.0,<2.0"                  # = capabilities.contracts_compat
capabilities = { isolation_modes = ["{{isolation}}"], supports_resumable = false, contracts_compat = ">=1.0,<2.0" }

[tool.uv.sources]
rag-platform = { workspace = true }              # 코어 모노레포 plugins/ 멤버일 때만; 외부 저장소는 이 표를 지운다

[tool.importlinter]                              # 10-development/01 §3.2와 같은 C 등급 차단·SDK 표면 계약(플러그인 사본)
root_packages = ["rag_plugin_{{name}}"]
[[tool.importlinter.contracts]]
name = "sdk-surface-only"
type = "forbidden"
source_modules = ["rag_plugin_{{name}}"]
forbidden_modules = ["rag_platform.adapters", "rag_platform.orchestration", "rag_platform.api", "rag_platform.storage", "rag_platform.ledger", "temporalio", "fastapi"]
```

한 배포 패키지가 여러 확장 지점을 제공하는 형태(예: 인덱스 백엔드 + 리트리버)는 배열 테이블 `[[tool.rag_platform.plugin]]`(항목마다 `PluginMeta` 하나, entry point와 1:1)이 필요한데 이는 **제안**(05 미해결 이슈 13)이다. 확정 전에는 확장 지점마다 패키지를 나눈다(§5.1).

### 2.3 로컬 명령

| 목적 | 명령 | 비고 |
|------|------|------|
| 의존성 | `uv sync --extra dev` | `uv lock --check`가 CI 첫 단계 |
| 정적 검사 | `uv run ruff check . && uv run mypy --strict src` | 금지 API 규칙(`datetime.now`, `random`, `time.time`, `open`, `httpx`/`requests` 직접 임포트)은 01 §2.5 제안 |
| 적합성 | `uv run pytest tests/test_conformance.py --conformance-report src/rag_plugin_{{name}}/conformance.json` | 옵션 이름은 제안(§8.3) |
| 등록 확인 | `uv run rag plugin list --check-license` | 정본 CLI(바이블 §12 `cli/plugin`) — 도출 신뢰 수준·라이선스 판정·리포트 유무 출력 |
| 프로파일 검증 | `uv run rag profile validate ./profiles/dev.yaml` | §7.4 12규칙 |
| 단건 실행 | `uv run rag run-stage parse --input ./samples/deck.pptx --profile lite --plugin parser.pptx_python_pptx --json` | **제안**(01 §13) |

## 3. 구현 규약 요약

### 3.1 5멤버와 선택 멤버

| 멤버 | 플러그인이 쓰는 값 | 쓰지 말 것 |
|------|--------------------|------------|
| `plugin_id: str` | `"{extension_point}.{implementation}"`(snake_case 둘) | 버전·벤더명을 `plugin_id`에 넣기(버전은 `PluginMeta.version`) |
| `config_schema: type[BaseModel]` | `ConfigDict(extra="forbid", frozen=True)`; 기본값 = 바이블 §7.2 `standard` 값 | 격리·큐·재시도·타임아웃 필드(그것은 `StagePolicy`), 절대 경로·호스트명·비밀·시각 |
| `capabilities() -> Capabilities` | 설정 반영 후 실행 시 값(임베더 `model_ids` 등) | `PluginMeta.capabilities`(정적)와 정적 부분이 다른 값 |
| `fingerprint() -> str` | SDK `hash_of("producer", plugin_id, plugin_version, config_hash, image_digest or "", ",".join(model_ids))` 단일 식 — `StageBase`(01 §2.4 제안) 상속 시 자동 | 자유 구성(ADR-0032 기각 대안 D) |
| `async run(inp, ctx) -> Out` | 순수 변환; 외부 세계는 `ctx`만 | `datetime.now`, `random`, 파일·네트워크 직접 I/O, 재시도 루프, 전역 캐시 |
| `requires_lineage`(선택) | `index`만 `("EnrichedChunkSet", "ChunkSet", "SourceDocument")` | 다른 확장 지점에서 선언(`evaluator` 확장은 05 미해결 이슈 19) |
| `StageLifecycle`(선택, 제안) | `init(services)`·`warmup()`·`health()`·`close()` — 모델·커넥션 풀은 여기서만 | `run()` 안에서 모델 로딩 |

### 3.2 `StageContext`에서 허용되는 것(01 §2.5·§3.1)

`ctx.tenant_id`·`collection_id`·`document_id`·`job_id`·`trace_id`·`profile_hash`, `ctx.security`·`ctx.plan`(질의 측), `ctx.token_counter`·`ctx.token_counters`, `ctx.analyzer`, `ctx.lineage`, `ctx.now()`, `ctx.heartbeat(details)`·`ctx.resume_details`, `ctx.artifacts.put_source/put_derived`(쓰기 전용), `ctx.remaining_ms()`, `ctx.cancelled`(제안). 원본 바이트는 스테이지가 스토리지에서 읽지 않으며 셸이 넘긴 포트 `ctx.source_bytes()`(**제안**, 04-pipelines/04 미해결 이슈 18)를 쓴다. 외부 서버 호출은 `RuntimeServices.http`(EgressGuard 적용) 팩토리로만 클라이언트를 얻고 `ctx.remaining_ms()`를 존중한다.

### 3.3 오류

플러그인은 `StageFailure(stage_error(code, stage=…, plugin_id=…, detail=None))` **하나만** 던진다(01 §10.1). `code`는 바이블 §5.7 카탈로그의 `{stage}.{reason}`만 유효하고 `retryable`은 카탈로그가 채운다. 벤더 예외는 어댑터 안에서 변환표로 바꾼다. 부분 성공은 예외가 아니라 데이터다(`quality=degraded` + `warnings[]` + `page_status[]` / `degraded[]`). `detail`·`Warning.message`에 본문 문자열을 넣으면 적합성 `security_invariants`가 실패한다(E13).

## 4. 튜토리얼 1 — 새 파서 플러그인: PPTX

### 4.1 전제와 열거 확장

PPTX(Office Open XML Presentation)는 바이블 §5.7 `SourceFormat`(`hwpx, hwp5, hwp3, pdf, docx, doc, rtf, odt, html, txt, md, json, unknown`)에 **없다**. 파서 `Capabilities.input_formats`는 `SourceFormat` 부분집합이어야 하고(05 §3.3) `parse.router`는 `SourceFormat` 전 값을 키로 가지므로(§7.4 (10)), 새 포맷 파서는 코드보다 먼저 **열거값 추가(minor) 절차**(바이블 §1.2: ADR 발의 → 바이블 §5.7 표 갱신 → `schemas/common-types.schema.json` 갱신은 03-contracts/00)를 밟아야 한다. 이 튜토리얼은 그 절차가 필요한 포맷을 일부러 골랐다. 확정 전까지 개발·테스트는 `rag run-stage`(제안)와 적합성 키트로 하고, 프로덕션 프로파일에는 넣을 수 없다(`profile.invalid`). `format_detector`(코어 `parser.format_detector`) 쪽에도 ZIP 내부 `ppt/presentation.xml` 스니핑 규칙이 추가되어야 하며 이것은 04-pipelines/03 소유다(§미해결 이슈 1).

래핑 라이브러리는 python-pptx(MIT; 07-tech-landscape에 조사 문서가 없어 버전·API·라이선스는 **확인 필요 as of 2026-09**)다. lxml·Pillow는 A 등급 의존성이며 의존성의 네이티브 확장은 플러그인 `linkage`를 바꾸지 않으므로(03-contracts/15 §4) `linkage = pure_python`, 격리 `in_process`다.

### 4.2 매핑 설계(먼저 표로)

| PPTX 요소 | `Block.type` / 계약 필드 | 규칙 |
|-----------|--------------------------|------|
| 프레젠테이션 코어 속성 `title` | `metadata.title`, 첫 블록 `heading level=0` | 없으면 첫 슬라이드 제목 → `heading_inferred=true` |
| 슬라이드 n | `Provenance.page = n`(1-based), `page_break{page_no: n}` | PPTX는 페이지 있는 포맷이므로 `page`·`bbox` 비-null(D-04) |
| 제목 플레이스홀더 | `heading level=1` | `numbering_label` 없음 |
| 텍스트 프레임 단락 | `paragraph` / 글머리 단락은 `list_item`(`level` = 단락 들여쓰기 수준, `ordered`) | 단락마다 블록 1개; `text`는 원문(NFC 미적용) |
| 표 | `table` + `TableData{n_rows, n_cols, cells[], header_row_indices, role=data}` | 병합 셀은 앵커 1개(`row_span`·`col_span`); `header_row_indices=[0]`는 표 스타일 `first_row` 플래그가 참일 때만, 아니면 `header_inferred` |
| 그림 | `figure{artifact, kind: image, alt_text}` | 바이트는 `ctx.artifacts.put_derived(kind="figure_crop")`; `alt_text`는 `descr` 속성 |
| 슬라이드 번호·바닥글 플레이스홀더 | `page_footer`, `furniture=true`, `container=page_footer` | 기본 청킹 제외 |
| 발표자 노트 | `annotations[]{kind: memo, block_id: 슬라이드 heading}` (기본) 또는 `paragraph`(설정) | 인덱싱 제외가 기본(바이블 §5.4 `annotations`) |
| 도형 좌표(EMU) | `bbox = [x0, y0, x1, y1]` 포인트, 좌상단 원점 | `pt = emu / 12700` |
| `element_path` | `ppt/slides/slide{n}.xml#sp{shape_id}/p{i}` | 문서 내 유일; `block_id = H("block", doc_version, element_path)[:32]` |

### 4.3 설정 모델과 능력

```python
# src/rag_plugin_pptx/config.py
class PptxParserConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    notes_mode: Literal["annotation", "paragraph", "skip"] = "annotation"   # 발표자 노트 처리
    include_hidden_slides: bool = False
    default_language: str = Field("ko", pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")   # 코어 속성에 언어가 없을 때(BCP 47)
    profile_option: Literal["pptx_default"] = "pptx_default"                # ParsedDocument.parser_fingerprint.profile_option
```

```python
# src/rag_plugin_pptx/parser.py — StageBase는 01 §2.4 제안(상속 선택); 프로토콜은 구조적이므로 상속 없이도 5멤버만 있으면 된다
EMU_PER_PT = 12700

class PptxParser(StageBase[SourceDocument, ParsedDocument]):
    plugin_id = "parser.pptx_python_pptx"
    config_schema = PptxParserConfig
    formats = frozenset({"pptx"})                        # 05 §3.3 Parser.formats = Capabilities.input_formats

    def capabilities(self) -> Capabilities:
        return Capabilities(isolation_modes=["in_process"], supports_resumable=True, contracts_compat=">=1.0,<2.0",
                            input_formats=["pptx"], model_ids=[], requires_gpu=False,
                            extra={"source_kinds": ["born_digital"], "page_provenance": True,      # extra 필드는 05 §5 제안
                                   "table_merged_cells": True, "arch": ["x86_64", "aarch64"]})

    def can_parse(self, source: SourceDocument) -> bool:
        return source.format == "pptx" and not source.container_flags.encrypted

    async def run(self, inp: SourceDocument, ctx: StageContext) -> ParsedDocument:
        if inp.container_flags.encrypted:                                                 # 암호화 OOXML(EncryptedPackage)
            raise StageFailure(stage_error("parse.document_encrypted", stage="parse", plugin_id=self.plugin_id))
        try:
            prs = Presentation(io.BytesIO(ctx.source_bytes()))                           # 원본 바이트 포트(제안, §3.2)
        except (zipfile.BadZipFile, KeyError) as e:                                       # 벤더 예외 → 카탈로그 코드(§3.3)
            raise StageFailure(stage_error("parse.corrupt_container", stage="parse", plugin_id=self.plugin_id,
                                           detail=f"python-pptx open failed: {type(e).__name__}")) from e
        blocks, artifacts, annotations, warnings = [], [], [], []
        start = (ctx.resume_details or {}).get("page", 1) if ctx.resume_details else 1  # ResumeCursor(01 §11.2)
        slides = [s for s in prs.slides if self.config.include_hidden_slides or not s.element.get("show") == "0"]
        for n, slide in enumerate(slides, start=1):
            if n < start:
                continue
            heading = self._heading_block(slide, n, inp.doc_version, blocks)             # heading level=1 (+ level=0은 첫 슬라이드)
            for shape in slide.shapes:
                path = f"ppt/slides/slide{n}.xml#sp{shape.shape_id}"
                bbox = [shape.left / EMU_PER_PT, shape.top / EMU_PER_PT,
                        (shape.left + shape.width) / EMU_PER_PT, (shape.top + shape.height) / EMU_PER_PT]
                if shape.has_text_frame and not shape == heading.source_shape:
                    blocks += self._paragraph_blocks(shape, path, n, bbox, heading.block_id, inp.doc_version)
                elif shape.has_table:
                    blocks.append(self._table_block(shape, path, n, bbox, heading.block_id, inp.doc_version, warnings))
                elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    ref = ctx.artifacts.put_derived(shape.image.blob, kind="figure_crop", ext=shape.image.ext,
                                                    media_type=shape.image.content_type)                 # 파생물(봉투 없음)
                    blocks.append(self._figure_block(shape, ref, path, n, bbox, heading.block_id, inp.doc_version))
                    artifacts.append({"kind": "figure_crop", "ref": ref, "page": n, "block_id": blocks[-1].block_id})
            if slide.has_notes_slide and self.config.notes_mode != "skip":
                self._notes(slide, n, heading.block_id, blocks, annotations, inp.doc_version)
            ctx.heartbeat({"schema_version": "1.0.0", "stage": "parse", "unit": "page", "done": n, "total": len(slides),
                           "page": n + 1, "updated_at": ctx.now().isoformat(timespec="milliseconds").replace("+00:00", "Z")})
        return ParsedDocument(
            schema_version="1.0.0", schema_type="ParsedDocument", tenant_id=ctx.tenant_id, collection_id=ctx.collection_id,
            producer=self.producer(), quality="full" if not warnings else "degraded", warnings=warnings, created_at=ctx.now(),
            lineage_refs=dict(inp.lineage_refs),                                          # 자기 입력 키(source)는 셸이 완성(01 §5.3)
            document_id=inp.document_id, doc_version=inp.doc_version, source_ref=inp.artifact,
            parser_fingerprint={"parser_id": self.plugin_id, "parser_version": pptx_version, "model_ids": [],
                                "sidecar_image_digest": None, "profile_option": self.config.profile_option},
            parser_chain=[self.plugin_id], source_kind="born_digital", page_count=len(slides),
            language=prs.core_properties.language or self.config.default_language,
            metadata={"title": prs.core_properties.title or None, "authors": [a for a in [prs.core_properties.author] if a]},
            blocks=blocks, artifacts=artifacts, annotations=annotations,
            text_length=sum(len(b.text) for b in blocks), block_count=len(blocks))
```

블록 생성 헬퍼의 핵심 규칙: `block_id = hash_of("block", doc_version, element_path)[:32]`(SDK `hash_of`만 사용, `blake3` 직접 임포트 금지), `provenance = Provenance(element_path=path + f"/p{i}", char_start=0, char_end=len(text), page=n, bbox=bbox, section_index=None)`(코드포인트 오프셋 = Python `len`), `source="text_layer"`, `container="body"`(글상자 안 텍스트는 `text_box`), `ordinal`은 형제 내 0-based. 표 셀은 `TableCell{row, col, row_span, col_span, text, is_header, header_kind}`이며 병합 셀은 앵커만 넣고 `quality.merged_cells_preserved=true`, `structure_source="native"`.

### 4.4 `PluginMeta`

```json
{
  "plugin_id": "parser.pptx_python_pptx",
  "extension_point": "parser",
  "role": null,
  "version": "0.1.0",
  "license": "Apache-2.0",
  "license_grade": "A",
  "territory": [],
  "linkage": "pure_python",
  "isolation_supported": ["in_process"],
  "model_ids": [],
  "model_license_ack_required": false,
  "sidecar_image": null,
  "contracts_compat": ">=1.0,<2.0",
  "capabilities": {
    "isolation_modes": ["in_process"],
    "supports_resumable": true,
    "contracts_compat": ">=1.0,<2.0",
    "input_formats": ["pptx"],
    "model_ids": [],
    "requires_gpu": false,
    "extra": {"source_kinds": ["born_digital"], "page_provenance": true, "table_merged_cells": true, "arch": ["x86_64", "aarch64"]}
  }
}
```

### 4.5 테스트와 프로파일 연결

```python
# tests/test_conformance.py
from rag_platform.testing.parser import ParserConformance

class TestPptxParser(ParserConformance):
    plugin_ref = "parser.pptx_python_pptx"
    corpus = "pptx-public-v1"                    # 키트 픽스처 ID(제안; 공공누리 제1유형 발표자료로 구성, §미해결 이슈 1)
    config = {"notes_mode": "annotation"}
```

키트가 이 파서에 적용하는 항목: `contract_roundtrip`(스키마·봉투·K1 좌표 — 표·그림 블록의 `text`가 `""`인 경우 `char_start=char_end=0`), `idempotency`(2회 실행 바이트 동일; `notes_mode` 변경 → `config_hash` 변경; 두 테넌트 동일 바이트 → `stage_key` 각자), `security_invariants`(로그·`detail`에 본문 없음), 그리고 `supports_resumable=true`이므로 제안 모듈 `resumable_equivalence`(`resume_details.page`에서 재개한 결과 = 처음부터 실행한 결과, §8.1)다. 프로파일에는 열거 확정 뒤 `ingest.parse.router.pptx: [parser.pptx_python_pptx]`로 붙인다.

## 5. 튜토리얼 2 — 새 인덱스 백엔드: pgvector

### 5.1 형태와 범위

`index_backend`는 `Stage`가 아니라 **포트 `IndexBackend`**(05 §3.8)다. 플랫폼 `index` 사가가 `ensure_physical`·`upsert`·`flip_current`·`restore_generation`·`delete_by_filter`·`update_acl`·`swap_alias`·`count`를, `hydrate`가 `retrieve`를, 리트리버 어댑터가 `search`를 부른다. 질의 채널을 실제로 열려면 `retriever` 확장 지점 구현(`retriever.pgvector_dense`, `Stage[RetrieveInput, ChannelRun]`)이 따로 필요하다. 배열 `PluginMeta`(05 미해결 이슈 13) 확정 전이므로 패키지는 둘로 나눈다: `rag-plugin-pgvector`(`index_backend.pgvector`)와 `rag-plugin-pgvector-retriever`(`retriever.pgvector_dense`, `retriever.pgvector_sparse`).

07-tech-landscape/06 기준 pgvector 0.8.6(PostgreSQL License, A)은 `vector`(HNSW 2,000d)·`halfvec`(HNSW 4,000d)·`sparsevec`(인덱스 비영 1,000)·iterative index scan(0.8+)을 제공하고 BM25·멀티벡터·한국어 분석기는 없다. 따라서 이 백엔드는 **`role: vector`**(named vectors `dense`, `sparse_learned`)만 맡고 렉시컬 레그는 OpenSearch(`standard`) 또는 별도 pg_textsearch 어댑터(미래)가 맡는다. `sparse_bm25`(lite)는 Qdrant `modifier: idf`에 의존하는 계약이므로 이 백엔드로는 `lite` 대체가 되지 않는다.

**결정:** pgvector 백엔드는 원장(PostgreSQL 메타 DB)과 **다른 DSN·커넥션 풀**(`RAG_INDEX_PGVECTOR__DSN`, 제안)로 접속한다. 검색 핫패스가 원장 PostgreSQL을 읽지 않는다는 규칙([ADR-0034](../06-adr/0034-retrieval-hot-path-postgres-independence-and-hydrate.md))은 "인덱스 백엔드 payload만 읽는다"는 뜻이므로 인덱스가 PostgreSQL이어도 위배되지 않지만, 같은 인스턴스에 두는 단일 DB 프로파일은 §미해결 이슈 3이다.

### 5.2 능력 선언과 그 결과

```json
{
  "plugin_id": "index_backend.pgvector",
  "extension_point": "index_backend",
  "role": null,
  "version": "0.1.0",
  "license": "Apache-2.0",
  "license_grade": "A",
  "territory": [],
  "linkage": "pure_python",
  "isolation_supported": ["in_process"],
  "model_ids": [],
  "model_license_ack_required": false,
  "sidecar_image": null,
  "contracts_compat": ">=1.0,<2.0",
  "capabilities": {
    "isolation_modes": ["in_process"],
    "supports_resumable": false,
    "contracts_compat": ">=1.0,<2.0",
    "extra": {
      "supports_server_bm25": false,
      "korean_analyzer": false,
      "supports_server_fusion": [],
      "tenant_isolation": ["payload_filter"],
      "supports_alias_swap": true,
      "supports_multivector": false,
      "max_vector_dim": 2000,
      "max_multivector_elements": null,
      "supports_payload_only_points": true
    }
  }
}
```

| 선언 | 프로파일 로딩·플래너 결과(바이블 §7.4 (2), §8.1 6단계) |
|------|-------------------------------------------------------|
| `supports_multivector=false` | `late_interaction` 채널 자동 비활성 + `degraded{channel.late_interaction, capability_unsupported}` |
| `supports_server_bm25=false`, `korean_analyzer=false` | 렉시컬 레그를 이 백엔드에 배정하면 `plugin.capability_unsupported`; 프로파일은 다른 `role: lexical` 백엔드를 둔다 |
| `supports_server_fusion=[]` | 서버 융합 위임 불가 → 항상 플랫폼 `fuser`(기본값이므로 영향 없음) |
| `max_vector_dim=2000` | `dense.dim > 2000`이면 `plugin.capability_unsupported`(`halfvec` 4,000d 채택 시 값 갱신) |
| `tenant_isolation=["payload_filter"]` | `security.tenant_isolation_tier`가 `shard_key`·`index_per_tenant`이면 로딩 거부; 테넌트별 테이블 승격은 후속 버전 |
| `supports_alias_swap=true` | blue/green 재색인 허용(뷰 교체, §5.4) |

### 5.3 물리 스키마(DDL 스케치)

물리 이름은 Qdrant 규약(바이블 §13.4)을 그대로 따른다: 테이블 `rag_vec_{embedding_profile_hash[:12]}`, alias는 뷰 `col_{collection_id}_vec`. 기본 키는 OpenSearch와 같이 `record_id`다(`point_id`는 Qdrant 전용 변환이므로 컬럼으로 두지 않는다).

```sql
CREATE TABLE rag_vec_9f3a6c1e2b7d (
  record_id            char(64) PRIMARY KEY,                 -- H("record", tenant_id, collection_id, document_id, index_generation, chunk_id)
  tenant_id            char(26) NOT NULL, collection_id char(26) NOT NULL, document_id char(26) NOT NULL,
  doc_version          char(64) NOT NULL, commit_id char(26) NOT NULL, chunk_id char(64) NOT NULL,
  index_generation     integer  NOT NULL, is_current boolean NOT NULL DEFAULT false,
  item_kind            text NOT NULL, level smallint NOT NULL, parent_chunk_id char(64),
  dense                halfvec(1024),                        -- NULL 허용(supports_payload_only_points: 부모 번들 행)
  sparse_learned       sparsevec(250002),                    -- vocab_id=xlm-roberta-250k 어휘 크기(확인 필요 as of 2026-09)
  acl_allow            text[] NOT NULL, acl_deny text[] NOT NULL DEFAULT '{}',
  acl_visibility       text NOT NULL, acl_classification_rank smallint NOT NULL,   -- public=0 … secret=3 (Classification 순서)
  acl_embargo_until    timestamptz, acl_expires_at timestamptz, acl_hash char(64) NOT NULL,
  doc_date date, doc_type text, department text, tags text[], lang text NOT NULL, genre text NOT NULL,
  page_start integer, page_end integer, entity_ids text[], custom jsonb,
  payload              jsonb NOT NULL,                        -- 나머지 IndexRecord 필드(text, context_prefix, block_refs, sentence_spans, …)
  updated_at           timestamptz NOT NULL
);
CREATE INDEX ON rag_vec_9f3a6c1e2b7d USING hnsw (dense halfvec_cosine_ops);
CREATE INDEX ON rag_vec_9f3a6c1e2b7d (tenant_id, collection_id, is_current);
CREATE INDEX ON rag_vec_9f3a6c1e2b7d USING gin (acl_allow);
ALTER TABLE rag_vec_9f3a6c1e2b7d ENABLE ROW LEVEL SECURITY; ALTER TABLE rag_vec_9f3a6c1e2b7d FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON rag_vec_9f3a6c1e2b7d USING (tenant_id = current_setting('app.tenant_id'));   -- 이중 방어(E8)
```

### 5.4 포트 구현 스케치

```python
# src/rag_plugin_pgvector/backend.py
class PgvectorBackend:                                    # IndexBackend 포트(05 §3.8); Stage 아님
    backend_id = "pgvector"
    plugin_id = "index_backend.pgvector"
    config_schema = PgvectorConfig                        # {dsn_ref: credentials_ref 간접 참조, dense_dim: 1024, vocab_size: 250002, ef_search: PositiveInt = 100, iterative_scan: Literal["off", "relaxed_order", "strict_order"] = "relaxed_order"}

    def capabilities(self) -> Capabilities: ...          # §5.2 JSON과 동일 값(extra = IndexBackendCapabilities)
    def fingerprint(self) -> str: ...                     # IndexCommit.producer용 — index_backend 포트는 필수(05 §3.1)

    async def ensure_physical(self, spec: CollectionSpec) -> str:
        name = f"rag_vec_{spec.embedding_profile_hash[:12]}"      # DDL은 idempotent(IF NOT EXISTS); 뷰 col_{collection_id}_vec 보장
        ...
        self._physical.register(name, f"col_{spec.collection_id}_vec")   # search/retrieve/count가 받는 physical_name·alias 허용 목록(§14.2 입력 위생)
        return name

    async def upsert(self, records: Sequence[IndexRecord], *, commit_id: str) -> BackendResult:
        missing = [r.record_id for r in records if not (r.tenant_id and r.collection_id and r.acl_allow is not None and r.acl_visibility and r.acl_hash)]
        if missing:                                               # E5: 1건이라도 누락이면 배치 전체 거부, 쓰기 0건
            raise StageFailure(stage_error("index.security_fields_missing", stage="index", plugin_id=self.plugin_id))
        async with self._pool.tenant_tx(records[0].tenant_id) as tx:   # SET LOCAL app.tenant_id
            for batch in chunked(records, 256):                   # 바이블 §5.1 upsert 배치 256
                await tx.executemany(UPSERT_SQL, [self._row(r, commit_id) for r in batch])   # INSERT … ON CONFLICT (record_id) DO UPDATE; is_current=false
        return BackendResult(backend_id=self.backend_id, backend_version=self._server_version, physical_name=..., alias=...,
                             upserted=len(records), deleted=0, duration_ms=..., status="ok")

    async def flip_current(self, scope: DocumentScope, *, generation: int) -> BackendResult:
        # 단일 UPDATE로 원자적: gen == generation → true, gen < generation → false (OpenSearch update_by_query와 달리 트랜잭션)
        sql = "UPDATE {t} SET is_current = (index_generation = $4) WHERE tenant_id=$1 AND collection_id=$2 AND document_id=$3 AND index_generation <= $4"
        ...

    async def restore_generation(self, scope: DocumentScope, *, generation: int) -> BackendResult: ...   # 보상: 이전 세대 복원(같은 문장, generation=이전)
    async def delete_by_filter(self, flt: EffectiveFilter) -> BackendResult: ...                       # tenant_id 없는 필터는 계약 위반(수집 측)
    async def update_acl(self, scope: DocumentScope, *, acl_fields: Mapping[str, Any]) -> BackendResult: ...   # acl_* 컬럼 + acl_hash만(E11)

    async def search(self, req: BackendSearchRequest) -> list[BackendHit]:
        if "tenant_id" not in req.filter.security_fields:         # E7: 사후 필터 금지, tenant_id 없으면 예외
            raise StageFailure(stage_error("retrieve.security_context_missing", stage="retrieve", plugin_id=self.plugin_id))
        table = self._physical.resolve(req.physical_name)         # ensure_physical/swap_alias가 등록한 이름만 허용, quote_ident 적용; 미등록 → contract.violation
        where, params = to_sql(req.filter, start=2)               # EffectiveFilter{security, strategy, user, self_query} → WHERE (사전 필터); 값은 전부 $n 바인딩
        async with self._pool.tenant_tx(req.filter.security_fields["tenant_id"]) as tx:   # SET LOCAL app.tenant_id(RLS, E8)
            # 세션 GUC는 SET LOCAL에 바인딩이 불가하므로 set_config($n, $n, true)로 트랜잭션 범위 설정. 값은 config_schema가 검증(Literal·양의 정수)
            await tx.execute("SELECT set_config('hnsw.iterative_scan', $1, true), set_config('hnsw.ef_search', $2, true)",
                             self.config.iterative_scan, str(self.config.ef_search))
            rows = await tx.fetch(
                f"SELECT record_id, chunk_id, collection_id, document_id, doc_version, item_kind, level, parent_chunk_id, "
                f"1 - (dense <=> $1::halfvec) AS score, payload - 'text' - 'block_refs' - 'sentence_spans' AS payload_slim "
                f"FROM {table} WHERE {where} ORDER BY dense <=> $1::halfvec LIMIT ${len(params) + 2}",   # 식별자만 f-string; 값은 전부 바인딩
                req.vector, *params, req.top_k)
        ...

    async def retrieve(self, record_ids, *, with_payload, with_vectors, security) -> list[Mapping[str, Any]]:
        ...   # WHERE record_id = ANY($1) AND <security (a) 조건 재적용(E10)>; 누락은 빈 자리로

    async def swap_alias(self, alias: str, physical_name: str) -> None:
        ...   # BEGIN; CREATE OR REPLACE VIEW {alias} AS SELECT * FROM {physical_name}; COMMIT  — 트랜잭션 원자성(07/06 alias 표); 두 이름 모두 self._physical에 등록
    async def count(self, flt: EffectiveFilter) -> int: ...
```

`to_sql`은 `FilterNode` 트리(`and`/`or`/`not`, 리프 `field`·`op`·`value`; 깊이 ≤ 3, 절 ≤ 32)를 파라미터 바인딩 SQL(`$n` 자리표시자 + 값 목록)로 옮기며 필드는 `FilterableField` 화이트리스트 + 보안·전략 필드만 컬럼에 대응시킨다. SQL 문자열에 직접 들어가는 것은 **식별자만**(화이트리스트 컬럼명, `ensure_physical`·`swap_alias`가 등록한 테이블·뷰 이름을 `quote_ident`로 감싼 값)이고 필터 값·질의 벡터·`top_k`·세션 GUC 값은 전부 바인딩한다 — 프로파일이 넘긴 `collection_alias`라도 등록 목록에 없으면 `contract.violation`이다(§14.2 입력 위생). 보안 불변식 (a)(바이블 §10.2)의 각 절은 컬럼식으로 고정 번역한다: `acl_visibility = ANY(:visible_set) OR acl_allow && :principals`, `NOT (acl_deny && :principals)`, `acl_classification_rank <= :classification_max_rank`, embargo·expires는 `:as_of` 비교. 어댑터는 `CandidateSet.security_context_hash`로 "필터에 `tenant_id` 포함"을 서명한다(§6.2).

### 5.5 리트리버(`retriever.pgvector_dense`)

```python
class PgvectorDenseRetriever(StageBase[RetrieveInput, ChannelRun]):   # 질의 측 Stage 특수화; plan·security는 ctx(05 §2.2)
    plugin_id = "retriever.pgvector_dense"
    channel: Channel = "dense"
    config_schema = PgvectorRetrieverConfig                            # {} (파라미터는 ctx.plan.channels[i]에서)

    def capabilities(self) -> Capabilities:
        return Capabilities(isolation_modes=["in_process"], supports_resumable=False, contracts_compat=">=1.0,<2.0",
                            extra={"channel": "dense", "backend_id": ["pgvector"], "supports_prefilter": True, "supports_variants": True})   # 05 §5 제안

    async def run(self, inp: RetrieveInput, ctx: StageContext) -> ChannelRun:
        if ctx.security is None or ctx.plan is None:
            raise StageFailure(stage_error("retrieve.security_context_missing", stage="retrieve", plugin_id=self.plugin_id))
        t0 = ctx.now()
        try:
            hits = await self._backend.search(BackendSearchRequest(
                physical_name=inp.channel.collection_alias, filter=ctx.plan.filters.effective(inp.channel.collection_id, ctx.security),
                vector=self._query_vector(inp.variant),                # QueryVariant의 질의 벡터 번들 필드명은 03-contracts/09 확정
                top_k=inp.channel.top_k, timeout_ms=min(inp.channel.timeout_ms, ctx.remaining_ms() or inp.channel.timeout_ms)))
            status, error = "ok", None
        except StageFailure as f:                                     # 실패는 예외가 아니라 데이터(05 §3.10)
            hits, status, error = [], "error", f.error
        return ChannelRun(channel_run_id=f"dense:{inp.channel.collection_id}:{inp.variant.variant_id}", channel="dense", retriever_id=self.plugin_id,
                          collection_id=inp.channel.collection_id, variant_id=inp.variant.variant_id, backend_id="pgvector",
                          collection_alias=inp.channel.collection_alias, embedding_profile_hash=inp.channel.embedding_profile_hash,
                          index_generation_seen=sorted({h.index_generation for h in hits}), status=status, took_ms=elapsed_ms(t0, ctx.now()),
                          returned=len(hits), total_hits=None, truncated=len(hits) >= inp.channel.top_k, error=error,
                          candidates=[Candidate(**h.identity_fields(), score=h.score, rank=i + 1, payload_slim=h.payload_slim) for i, h in enumerate(hits)])
                          # identity_fields = record_id, chunk_id, collection_id, document_id, doc_version, item_kind, level, parent_chunk_id
```

`payload_slim`은 바이블 §5.5의 10키(`heading_path, page_start, page_end, doc_date, acl_classification, acl_hash, token_count_primary, text_preview, content_hash, text_source`)만 담고 본문·좌표·전체 ACL은 `hydrate`가 채운다. 결과 캐시는 ACL 시점성 때문에 금지다.

### 5.6 적합성 항목(이 확장 지점 특유)

| 키트 | 검사 |
|------|------|
| `security_invariants` | `search`·`retrieve`·`update_acl`·`delete_by_filter`에 `tenant_id` 없으면 예외(E7); 보안 필드 누락 1건 → 배치 전체 거부·쓰기 0건(E5); 사후 필터 없음(SQL 로그에 `WHERE tenant_id` 존재) |
| `idempotency` | 두 테넌트·두 컬렉션이 동일 바이트를 적재해도 `record_id`가 다르고 덮어쓰지 않음(E17); `from_stage=embed` 재색인에서 이전 세대가 플립 전까지 `is_current=true`; 같은 `commit_id` 재시도 = 같은 `record_id` no-op |
| 사가 시나리오(`idempotency` 하위) | `upsert(is_current=false)` → 검색에 안 보임 → `flip_current` → 새 세대만 보임 → `restore_generation` → 이전 세대 복원 |
| 프로파일 검증 | `late_interaction` 요구 프로파일 → 채널 비활성 + `degraded`; `role: lexical` 배정 → `plugin.capability_unsupported` |

프로파일 발췌(`standard` 변형): `ingest.index.backends: [{plugin: index_backend.pgvector, role: vector, named_vectors: [dense, sparse_learned], tenant_isolation: payload_filter}, {plugin: index_backend.opensearch, role: lexical}]`, `query.channels[dense].retriever: retriever.pgvector_dense`, `query.hydrate.backend: index_backend.pgvector`.

## 6. 튜토리얼 3 — 새 리랭커와 후처리기 변형

### 6.1 리랭커 `reranker.llamacpp_rerank`

`RerankBackend` 열거(바이블 §5.7)에는 `llamacpp`가 있고 07-tech-landscape/07은 CPU 대안으로 "llama.cpp `--rerank` + bge-reranker-v2-m3 GGUF"를 든다. llama.cpp 서버의 `/v1/rerank` 응답 형식은 `{"results": [{"index", "relevance_score"}]}` 계열로 알려져 있어 `RerankResponseSchema = cohere`로 파싱하되(**확인 필요 as of 2026-09**), 어댑터는 코어 `reranker.tei_cross_encoder`처럼 `tei`(`[{index, score}]`)·`cohere` 두 스키마를 모두 파싱하고 어느 쪽도 아니면 `rerank.schema_mismatch`(비재시도)다.

```python
class LlamaCppReranker(StageBase[RankedSet, RankedSet]):
    plugin_id = "reranker.llamacpp_rerank"
    config_schema = LlamaCppRerankerConfig            # {endpoint_ref: 서비스 디스커버리 이름(호스트 리터럴 금지), model_id: "BAAI/bge-reranker-v2-m3", revision: "<sha>", tokenizer_id: "hf:BAAI/bge-reranker-v2-m3"}

    def model_ids(self) -> list[str]:                 # 지문 필수 구성요소(01 §2.4: reranker → model_id@revision + 서빙 image_digest)
        return [f"{self.config.model_id}@{self.config.revision}"]

    def capabilities(self) -> Capabilities:
        return Capabilities(isolation_modes=["in_process"], supports_resumable=False, contracts_compat=">=1.0,<2.0",
                            model_ids=self.model_ids(), requires_gpu=False,
                            extra={"backend": "llamacpp", "response_schema": "cohere", "max_tokens_per_text": 512,
                                   "tokenizer_id": self.config.tokenizer_id})                                   # 05 §5 제안 필드

    @instrumented_call(kind="rerank")                 # 자식 스팬 rag.rerank.call(제안, 05 §9·09-operations/03); 플러그인은 스팬을 직접 만들지 않는다
    async def _call(self, query: str, docs: list[str], top_n: int, timeout_ms: int) -> list[tuple[int, float]]:
        resp = await self._http.post(f"{self._endpoint}/v1/rerank", json={"model": self.config.model_id, "query": query,
                                     "documents": docs, "top_n": top_n}, timeout=timeout_ms / 1000)
        resp.raise_for_status()
        return parse_rerank_response(resp.json())     # tei | cohere → [(index, raw_score)]; 실패 시 StageFailure(rerank.schema_mismatch)

    async def run(self, ranked: RankedSet, ctx: StageContext) -> RankedSet:
        p = ctx.plan.rerank                            # {model_id, backend, response_schema, top_n_in, top_n_out, max_tokens_per_text, timeout_ms, normalization}
        counter = ctx.token_counters[self.config.tokenizer_id]                       # 리랭커 토크나이저로 절단(O-09)
        head, tail = ranked.results[: p.top_n_in], ranked.results[p.top_n_in :]
        docs = [counter.truncate(f"{r.context_prefix}\n{r.text}", p.max_tokens_per_text) for r in head]   # hydrate 값(hydrated=true 전제)
        t0 = ctx.now()
        try:
            scored = await self._call(ctx.plan.normalized_query, docs, p.top_n_out, min(p.timeout_ms, ctx.remaining_ms() or p.timeout_ms))
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.TransportError) as e:
            return fused_order_fallback(ranked, self.plugin_id, reason="timeout" if isinstance(e, httpx.TimeoutException) else "unavailable",
                                        took_ms=elapsed_ms(t0, ctx.now()))            # rerank.applied=false, explain += rerank_skipped, degraded{rerank, …}
        results = []
        for new_rank, (idx, raw) in enumerate(sorted(scored, key=lambda s: -s[1])[: p.top_n_out], start=1):
            r, norm = head[idx], normalize(raw, p.normalization)                     # sigmoid | minmax | identity
            results.append(r.model_copy(update={"final_rank": new_rank, "final_score": norm, "rerank_rank": new_rank, "rerank_raw_score": raw,
                                                "rerank_normalized_score": norm, "score_breakdown": r.score_breakdown.model_copy(update={
                                                    "rerank_raw": raw, "rerank_normalized": norm, "normalization": p.normalization})}))
        return ranked.model_copy(update={"stage": "reranked", "results": results,
            "rerank": {"applied": True, "plugin_id": self.plugin_id, "model_id": self.model_ids()[0], "backend": "llamacpp", "response_schema": "cohere",
                       "normalization": p.normalization, "top_n_in": len(head), "top_n_out": len(results), "took_ms": elapsed_ms(t0, ctx.now())},
            "stats": {**ranked.stats, "n_in": len(ranked.results), "n_out": len(results)}})
```

규칙 요약: 타임아웃·5xx는 **오류가 아니라 폴백**(fused 순서 유지, `rerank.applied=false`, `explain += rerank_skipped`, `degraded{rerank, timeout|unavailable}`); 메트릭 `rag_rerank_fallback_total`은 플랫폼 `rerank.apply`가 기록하므로 플러그인은 카운터를 만들지 않는다. `top_n_in` 밖의 `tail`은 버린다(top-100→20). 지문에는 `model_id@revision`과 서빙 `image_digest`가 들어가야 하며 GGUF 파일은 `models.lock` 행(id, revision, sha256, license, grade, territory)으로 고정한다.

### 6.2 후처리기 변형 `postprocessor.dedup_simhash`

후처리 순서 `relevance_gate → dedup → mmr → parent_expand → dedup → sentence_window → compress`는 플랫폼이 고정하고(D-07 v1.2), 플러그인은 **한 단계의 구현을 교체**할 수 있을 뿐이다(05 §3.13). 예: 코사인 근중복 대신 SimHash(64비트, 해밍 거리 ≤ 3)로 `dedup`을 구현해 `hydrate.with_vectors=false` 환경에서 벡터 재조회를 없앤다.

```python
class SimhashDedup(StageBase[RankedSet, RankedSet]):
    plugin_id = "postprocessor.dedup_simhash"         # 05 §3.13은 plugin_id = postprocessor.{step}로 적으나 대체 구현은 고유 이름이 필요(§미해결 이슈 4)
    step: PostprocessStep = "dedup"
    config_schema = SimhashDedupConfig                # {hamming_max: 3, shingle: 3} — 결정적(시드 고정)

    def capabilities(self) -> Capabilities:
        return Capabilities(isolation_modes=["in_process"], supports_resumable=False, contracts_compat=">=1.0,<2.0",
                            extra={"step": "dedup", "mutates_text": False, "requires_vectors": False})   # 05 §5 제안

    async def run(self, ranked: RankedSet, ctx: StageContext) -> RankedSet:
        seen_hash, seen_sim, out = {}, [], []
        for r in ranked.results:                       # final_rank 오름차순 = 대표는 상위 순위
            if r.duplicates_of:                        # 1차 dedup이 이미 표시한 항목은 그대로 통과
                out.append(r); continue
            if (rep := seen_hash.get(r.content_hash)):                       # 정확 중복(다른 컬렉션 포함)
                out.append(r.model_copy(update={"duplicates_of": rep, "explain": [*r.explain, "deduped"]})); continue
            h = simhash(shingles(r.text, self.config.shingle))
            if (rep := first(seen_sim, lambda s: hamming(s[0], h) <= self.config.hamming_max)):
                out.append(r.model_copy(update={"duplicates_of": rep[1], "explain": [*r.explain, "deduped"]})); continue
            seen_hash[r.content_hash] = r.chunk_id; seen_sim.append((h, r.chunk_id)); out.append(r)
        return ranked.model_copy(update={"results": out})     # 순위 재부여·postprocess_report.steps[] 기록은 플랫폼 postprocess.run
```

프로파일 바인딩은 단계 키 아래 `plugin`(05 §12.3 `compress {plugin: postprocessor.compress_exit}` 패턴): `query.postprocess.dedup: {plugin: postprocessor.dedup_simhash, hamming_max: 3}`. `mutates_text=false`이므로 `renderer_citation_roundtrip` 좌표 재계산 검사는 면제되고, `text`를 바꾸는 단계(`sentence_window`·`compress`)를 구현할 때는 `block_refs`·`sentence_spans`를 함께 재계산해야 한다(K1).

## 7. 선언 3종 체크리스트

| 선언 | 규칙 | 검증 위치·실패 코드 |
|------|------|---------------------|
| entry point | 그룹 `rag_platform.{extension_point}`(14값 정확 일치), 이름 = `implementation`; `plugin_id`와 조립값 동일; 코어 어댑터와 이름 충돌 방지를 위해 외부 패키지는 벤더 접두(`lightrag_`, `pgvector_`) | 레지스트리 로딩 → `contract.violation`; 중복 `plugin_id` → `profile.invalid` |
| `config_schema` | `extra="forbid"`, `frozen=True`; 셸 예약 키(`plugin`, `policy`, `isolation`, `image`, `then`, `fallback`) 사용 금지; 기본값 = 바이블 §7.2; `model_json_schema()` 출력 가능 | 프로파일 로딩 → `profile.invalid`; 적합성 키트(기본값 대조) |
| `capabilities()` / `PluginMeta.capabilities` | 정적 부분(`isolation_modes`, `contracts_compat`, `input_formats`) 동치; `isolation_supported == capabilities.isolation_modes`(M-2); `index_backend`는 `extra` = `IndexBackendCapabilities` 9필드 전부 | `rag profile validate` (2) → `plugin.capability_unsupported` |
| `PluginMeta` 라이선스 | `license`(SPDX)·`license_grade`·`territory`·`linkage` 필수; C 등급 → `isolation_supported=["sidecar"]` + `sidecar_image`; D 모델 → `model_ids` + `model_license_ack_required=true`; B + `static_bundled`는 기본 프로파일 거부 | `rag profile validate` (1) → `plugin.license_denied` |

## 8. 적합성 키트 사용

### 8.1 기반 클래스 상속

**결정:** 모든 플러그인은 `rag_platform.testing`의 확장 지점별 기반 클래스를 상속해 CI에서 6모듈(`contract_roundtrip`, `idempotency`, `security_invariants`, `renderer_citation_roundtrip`, `litm_order`, `fuser_equivalence`)을 실행한다. 통과하지 못한 플러그인은 카탈로그에 등재되지 않는다(바이블 §12 `testing/`, [ADR-0032](../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md)).

| 확장 지점 | 기반 클래스(제안 명) | 필수 속성 | 적용 모듈 |
|-----------|----------------------|-----------|-----------|
| `parser` | `ParserConformance` | `plugin_ref`, `corpus`, `config` | `contract_roundtrip`, `idempotency`, `security_invariants`, (`supports_resumable=true`면) `resumable_equivalence`(제안, 01 미해결 이슈 10) |
| `index_backend` | `IndexBackendConformance` | `plugin_ref`, `config`, `fixtures`(`IndexRecord` 배치) | `security_invariants`, `idempotency`(E17·사가) |
| `retriever` | `RetrieverConformance` | `plugin_ref`, `backend_ref` | `security_invariants`, `contract_roundtrip` |
| `reranker` / `postprocessor` | `RerankerConformance` / `PostprocessorConformance` | `plugin_ref`, `cassette`(기록형 HTTP) | `contract_roundtrip`, `idempotency`, (`mutates_text=true`면) `renderer_citation_roundtrip` |
| `packer` / `fuser` | `PackerConformance` / `FuserConformance` | `plugin_ref` | `litm_order`, `renderer_citation_roundtrip` / `fuser_equivalence` |

기반 클래스 이름은 05 §10의 `ParserConformance` 예시를 확장 지점 전체로 일반화한 **제안**이다. `resumable_equivalence`는 정본 6모듈 밖의 **제안** 모듈(01 미해결 이슈 10)로 `Capabilities.supports_resumable=true`인 플러그인에만 적용되며, 리포트 스키마(§8.3)의 `module` 열거에도 제안으로 포함해 두었다. 키트는 `FakeStageContext`(고정 `now()`, 인메모리 `DerivedArtifacts`, 고정 `analyzer`·`token_counter`)와 `FakeRuntimeServices`(기록형 HTTP 카세트)를 제공한다(01 §12). `model_pinned`·`generative` 플러그인(임베더·리랭커·LLM 보강)은 카세트 없이는 `idempotency`를 통과할 수 없으므로 `tests/fixtures/cassettes/`를 함께 커밋한다.

### 8.2 골든 회귀

`tests/golden/cases.json`(01 §12.2 `GoldenCase`)에 입력 픽스처와 `expected_golden_hash`(`created_at`·`producer`·`lineage_refs` 제외 정규화 해시)를 두고 `rag_platform.testing.golden.run_golden`으로 비교한다. 래핑 라이브러리를 범프(pin-and-bump)할 때 골든이 바뀌면 PR 설명에 변경 사유를 적어야 한다.

### 8.3 결과 리포트 `conformance.json`(이 문서 소유)

05 §10은 외부 플러그인이 키트 결과 리포트를 패키지에 동봉하도록 하고 스키마 소유를 이 문서에 두었다. 리포트는 패키지 데이터 `rag_plugin_{name}/conformance.json`으로 배포되며 레지스트리·`rag plugin list --check-license`가 `importlib.resources`로 읽어 신뢰 수준 `verified` 도출(05 §11.1)에 쓴다. 스키마 파일 위치는 03-contracts 인벤토리 밖 도구 스키마(`schema-diff-report`와 같은 부류)로 `schemas/conformance-report.schema.json`(`$id = urn:rag:schema:conformance-report:1`)을 **제안**하며 파일 생성은 03-contracts/14·00과 합의 후다(§미해결 이슈 5).

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:rag:schema:conformance-report:1",
  "title": "ConformanceReport",
  "description": "플러그인 CI가 rag_platform.testing 키트를 실행한 결과. 패키지 데이터 rag_plugin_{name}/conformance.json 으로 동봉하며 레지스트리가 신뢰 수준 verified 도출에 사용한다(05 §10·§11.1). 소유 문서: docs/10-development/06-plugin-development-guide.md(제안, 03-contracts 인벤토리 밖 도구 스키마).",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "plugin_id", "plugin_version", "extension_point", "kit_version", "contracts_tested", "modules", "generated_at"],
  "properties": {
    "schema_version": {"type": "string", "const": "1.0.0"},
    "plugin_id": {"$ref": "urn:rag:schema:common-types:1#/$defs/PluginId"},
    "plugin_version": {"$ref": "urn:rag:schema:common-types:1#/$defs/Semver"},
    "extension_point": {"$ref": "urn:rag:schema:common-types:1#/$defs/ExtensionPoint"},
    "kit_version": {"$ref": "urn:rag:schema:common-types:1#/$defs/Semver", "description": "키트를 제공한 rag-platform 패키지 버전"},
    "contracts_tested": {
      "type": "array", "minItems": 1, "uniqueItems": true,
      "items": {"type": "object", "additionalProperties": false, "required": ["schema_type", "schema_version"],
                "properties": {"schema_type": {"type": "string", "pattern": "^[A-Z][A-Za-z0-9]*$"}, "schema_version": {"$ref": "urn:rag:schema:common-types:1#/$defs/Semver"}}}
    },
    "modules": {
      "type": "array", "minItems": 1,
      "items": {"type": "object", "additionalProperties": false, "required": ["module", "status", "cases_total", "cases_failed"],
                "properties": {
                  "module": {"type": "string", "enum": ["contract_roundtrip", "idempotency", "security_invariants", "renderer_citation_roundtrip", "litm_order", "fuser_equivalence", "resumable_equivalence"]},
                  "status": {"type": "string", "enum": ["passed", "failed", "skipped"]},
                  "cases_total": {"type": "integer", "minimum": 0},
                  "cases_failed": {"type": "integer", "minimum": 0},
                  "skip_reason": {"type": "string", "maxLength": 256}}}
    },
    "corpus_ids": {"type": "array", "items": {"type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"}, "uniqueItems": true},
    "determinism": {"type": "string", "enum": ["pure", "model_pinned", "generative"]},
    "environment": {"type": "object", "additionalProperties": false, "required": ["python", "arch"],
                    "properties": {"python": {"type": "string"}, "arch": {"type": "string", "enum": ["x86_64", "aarch64"]}, "os": {"type": "string"}}},
    "generated_at": {"type": "string", "format": "date-time"},
    "ci_run_url": {"type": "string", "format": "uri"},
    "report_hash": {"$ref": "urn:rag:schema:common-types:1#/$defs/Hex64", "description": "H(\"conformance\", canonical_json(report_hash 제외 본문))"}
  }
}
```

```json
{
  "schema_version": "1.0.0",
  "plugin_id": "parser.pptx_python_pptx",
  "plugin_version": "0.1.0",
  "extension_point": "parser",
  "kit_version": "1.0.0",
  "contracts_tested": [
    {"schema_type": "SourceDocument", "schema_version": "1.0.0"},
    {"schema_type": "ParsedDocument", "schema_version": "1.0.0"}
  ],
  "modules": [
    {"module": "contract_roundtrip", "status": "passed", "cases_total": 24, "cases_failed": 0},
    {"module": "idempotency", "status": "passed", "cases_total": 9, "cases_failed": 0},
    {"module": "security_invariants", "status": "passed", "cases_total": 6, "cases_failed": 0},
    {"module": "resumable_equivalence", "status": "passed", "cases_total": 3, "cases_failed": 0}
  ],
  "corpus_ids": ["pptx-public-v1"],
  "determinism": "pure",
  "environment": {"python": "3.12.9", "arch": "x86_64", "os": "linux"},
  "generated_at": "2026-09-22T09:00:00.000Z",
  "ci_run_url": "https://ci.example.org/rag-plugin-pptx/runs/1842",
  "report_hash": "3f0a9c2e7b1d4e6f8a9c0b1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f"
}
```

`modules[].status=failed`가 하나라도 있으면 신뢰 수준은 `untrusted`다. `skipped`는 해당 확장 지점에 적용되지 않는 모듈(파서의 `litm_order` 등)에만 허용되고 `skip_reason`이 필수다. `report_hash`는 조작 감지용이며 서명(§12)이 없으면 진위를 보증하지 않는다.

## 9. 격리 모드 선택과 사이드카 템플릿

### 9.1 결정 표

| 질문 | 예 → 모드 | 근거 |
|------|-----------|------|
| 순수 Python이고 A 등급인가(`linkage=pure_python`, 의존성 네이티브 확장은 무관) | `in_process` | 바이블 §4.1; ADR-0033 배정 표 |
| `ctypes`·확장 모듈로 네이티브를 로드해 크래시가 인터프리터를 죽일 수 있는가(`linkage ∈ {dynamic, static_bundled}`) | `helper_process`(문서 1건 = `multiprocessing spawn` 1개; 어댑터는 헬퍼 래퍼만 호출, 직접 `ctypes` 로딩 금지) | 크래시 → `parse.conversion_failed` |
| JVM·LibreOffice·CUDA 결합 프레임워크·대형 모델 서빙인가 | `sidecar` | 코어 이미지에 들어갈 수 없음 |
| GPL/AGPL(C 등급)인가 | `sidecar` **강제**, 이미지는 별도 저장소 `rag-platform-gpl-sidecars`, Helm `optIn.*` | D-02, [ADR-0001](../06-adr/0001-license-grade-table-and-d02-interpretation.md) |
| D 등급 모델을 포함하는가 | 격리 강제 없음; `model_license_ack_required=true` + 기본 프로파일 제외 | 브리프 D-02 |

실행 모드는 `PluginMeta.isolation_supported ∩ Capabilities.isolation_modes ∩ 프로파일 지정값` 중 가장 낮은 단이며 위 강제 규칙이 우선한다(05 §7.2). 헬퍼 프로세스 안에서는 네트워크를 쓰지 않아야 한다(키트가 소켓 생성을 감시).

### 9.2 사이드카 계약 요약(ADR-0033)

**결정:** 사이드카는 REST `POST /v1/convert`(`ConvertRequest{input: ArtifactRef, options, tenant_id, document_id, deadline_ms, trace_id, credentials_ref}` → `ConvertResponse{output, derived[], warnings, error, took_ms, producer}`)와 `GET /healthz`만 제공한다. 본문은 참조만, 비밀은 `credentials_ref`만, 변환 실패는 **200 + `output=null` + `error`**, 전송·검증 오류만 RFC 9457(400 `contract.violation`, 503 `parse.sidecar_unavailable` + `Retry-After`)이다. gRPC·스트리밍은 두지 않으며 페이지 진행은 부분 산출물 + 폴링이다([ADR-0033](../06-adr/0033-sidecar-convert-contract-and-isolation-ladder.md), [ADR-0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md)).

```mermaid
sequenceDiagram
    participant W as 워커 · SidecarStage 서브클래스
    participant S as 사이드카(FastAPI)
    participant O as Object Storage(tenants/{tenant_id}/…)
    W->>W: derived 키 H("derived", content_hash, image_digest) 조회 → 히트면 호출 생략
    W->>S: POST /v1/convert (ConvertRequest; deadline_ms = 잔여 start_to_close × 0.8)
    S->>O: GET input.uri (자기 자격 증명)
    S->>S: 변환 · deadline_ms 감시 · trace_id 전파
    S->>O: PUT derived/{kind}/{blake3}
    S-->>W: 200 ConvertResponse{output | null, derived[], warnings, error | null, took_ms, producer{image_digest}}
```

### 9.3 서버 템플릿(`sidecar/app.py`)

사이드카 이미지는 코어에 의존하지 않으므로(바이블 §12 `sidecars/`) `rag_platform`을 임포트하지 않고 `schemas/convert-request.schema.json`·`convert-response.schema.json`에서 생성한 Pydantic 모델을 쓴다(코드젠 도구는 10-development/05 확정).

```python
# sidecar/app.py — 템플릿. 코어 임포트 없음. 모델은 JSON Schema 코드젠(ConvertRequest, ConvertResponse, StageError, Producer, ArtifactRef)
app = FastAPI()
IMAGE_DIGEST = os.environ["SIDECAR_IMAGE_DIGEST"]          # 배포 매니페스트가 주입하는 자기 이미지 digest(sha256:…); 태그 금지
READY = {"ok": False}

@app.on_event("startup")
async def warmup() -> None:                                 # 모델·JVM·LO 준비, 샘플 변환 1건(초안 목표 5s)
    READY["ok"] = await engine.warmup()

@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"status": "ok" if READY["ok"] else "starting", "image_digest": IMAGE_DIGEST}   # image_digest 포함 여부는 03-contracts/16 미결

@app.post("/v1/convert")
async def convert(req: ConvertRequest, response: Response) -> ConvertResponse | JSONResponse:
    if not READY["ok"]:
        return problem(503, "parse.sidecar_unavailable", retry_after=5)                   # RFC 9457 + Retry-After
    t0 = time.monotonic()
    with tracer.start_as_current_span("convert", context=propagate(req.trace_id)):        # rag.ingest.parse 의 자식(§6.5)
        try:
            data = await storage.get_bytes(req.input)                                       # 자기 자격 증명; s3:// · file://(개발)만
            out_bytes, derived_bytes, warnings = await asyncio.wait_for(engine.convert(data, req.options), timeout=req.deadline_ms / 1000)
        except asyncio.TimeoutError:
            return ConvertResponse(output=None, derived=[], warnings=[], took_ms=ms(t0), producer=producer(),
                                   error=StageError(code="parse.conversion_failed", type="urn:rag:error:parse.conversion_failed",
                                                    retryable=False, stage="parse", plugin_id=PLUGIN_ID, detail="deadline_ms exceeded"))
        except EngineError as e:                                                            # 손상 입력·변환 실패 → 200 + error
            return ConvertResponse(output=None, derived=[], warnings=[], took_ms=ms(t0), producer=producer(), error=e.to_stage_error())
    out_ref = await storage.put_derived(out_bytes, tenant_id=req.tenant_id, kind="derived_source", ext=engine.ext, media_type=engine.media_type)
    return ConvertResponse(output=out_ref, derived=[await storage.put_derived(b, tenant_id=req.tenant_id, **m) for b, m in derived_bytes],
                           warnings=warnings, error=None, took_ms=ms(t0), producer=producer())

def producer() -> Producer:                                 # 워커가 Producer.image_digest 로 복사 → 지문(리스크 #8)
    return Producer(plugin_id=PLUGIN_ID, plugin_version=VERSION, config_hash=CONFIG_HASH, image_digest=IMAGE_DIGEST, model_ids=MODEL_IDS)
```

이미지 요건(ADR-0033 준수 표): PID 1 `tini`, 비루트 UID, 읽기 전용 루트 FS + `/work` tmpfs, seccomp `RuntimeDefault`, egress는 오브젝트 스토리지·OTel Collector만, 변환 N회 또는 RSS 상한 시 재기동, `killpg` 타임아웃 경로, 응답 본문에 콘텐츠 문자열·비밀 부재. 공통 계약 테스트 6경로(정상, `deadline_ms` 초과, 손상 입력, 존재하지 않는 `input.uri`, 잘못된 본문 400, 미준비 503)를 `sidecar/tests/`에 둔다.

### 9.4 클라이언트(`SidecarStage` 서브클래스)

```python
class PptRenderSidecarParser(SidecarStage[SourceDocument, ParsedDocument]):   # 예: 레거시 바이너리 → OOXML 변환 사이드카를 감싸는 어댑터
    plugin_id = "parser.ppt_render_sidecar"
    config_schema = PptRenderConfig
    sidecar_image: ClassVar[str] = "rag-plugin-ppt-render-sidecar"               # PluginMeta.sidecar_image; digest는 런타임 Producer.image_digest

    def to_request(self, inp: SourceDocument, ctx: StageContext) -> ConvertRequest:
        return ConvertRequest(input=inp.artifact, options={"target": "pptx"}, tenant_id=ctx.tenant_id, document_id=ctx.document_id,
                              deadline_ms=int((ctx.remaining_ms() or 60000) * 0.8), trace_id=ctx.trace_id, credentials_ref=inp.credentials_ref)

    def from_response(self, inp: SourceDocument, resp: ConvertResponse, ctx: StageContext) -> ParsedDocument:
        ...   # resp.output(변환본 ArtifactRef)을 in_process 파서(§4)에 재투입하거나 라우터 then: pptx 로 넘김; resp.derived[] → ParsedDocument.artifacts[]; warnings 병합
```

`SidecarStage.run`이 `_convert`(연결 실패·5xx·타임아웃 → `parse.sidecar_unavailable`)와 `output=null → StageFailure(resp.error)`를 처리하므로 서브클래스는 두 메서드만 쓴다. `PluginMeta`는 `isolation_supported=["sidecar"]`, `sidecar_image` 비-null이고, `fingerprint()`에 `image_digest`가 없으면 등록이 거부된다.

## 10. 관측성: 플러그인이 하는 일과 하지 않는 일

| 하지 않는다 | 대신 |
|-------------|------|
| 스팬 생성(`tracer.start_span`), 메트릭 생성 | 셸이 `rag.ingest.{stage}`·`rag.{stage}`·`rag.retrieve.{channel}` 스팬과 `rag_ingest_stage_duration_seconds{stage, outcome, queue}` 등 정본 메트릭(바이블 §6.5)을 자동 기록 |
| 임의 메트릭 이름 | 정본 목록만 유효; 플러그인 고유 카운터가 필요하면 09-operations/03에 Weaver 등재 제안 |
| 로그 필드 직접 삽입, `tenant_id` 평문 | `structlog.get_logger()`만; 셸이 `tenant_id_hash, job_id, trace_id, stage`를 contextvars로 바인딩 |
| 질의문·청크 본문을 스팬·로그·`detail`에 기록 | 콘텐츠 캡처 기본 끔(`RAG_OTEL__CONTENT_CAPTURE=none`); ID·점수·길이만 |
| 점수 분해를 스팬 속성으로 | `RankedSet.score_breakdown`에 기록 |

하는 일은 하나다: 외부 호출(모델 서버·사이드카·LLM) 메서드에 `@instrumented_call(kind="embedding"|"rerank"|"llm"|"sidecar"|"ocr")`(**제안**, 05 §9·09-operations/03)를 붙여 자식 스팬 `rag.{stage}.call`과 `gen_ai.*`·`server.address` 속성을 얻는다. 속성 상수는 `rag_platform.telemetry.otel`(Weaver 생성)에서만 가져오고 문자열 리터럴은 린트가 거부한다([ADR-0022](../06-adr/0022-observability-genai-semconv-pin-and-license-boundary.md)).

## 11. 버전·호환성 선언

| 축 | 선언 위치 | 규칙 |
|----|-----------|------|
| 계약 `schema_version` | `contracts_compat`(`PluginMeta`·`Capabilities` 동치), 문법 `(>=|<=|==|<|>)MAJOR.MINOR` 쉼표 결합(patch 불참) | 코어 현재 계약 집합이 범위 밖이면 `plugin.capability_unsupported`; 산출물 minor > 소비자 minor는 `contract.violation`(관용 읽기 없음, 05 §8); 계약 major 상승 시 `">=1.0,<3.0"`으로 넓혀 두 major 모두 키트 통과 |
| SDK 버전 | `dependencies = ["rag-platform>=1.0,<2.0"]` | 코어 패키지 버전 = SDK 버전; `Stage` 멤버 추가는 minor, 시그니처 변경은 major. 별도 `sdk.API_VERSION` 상수는 제안(10-development/08) |
| 플러그인 버전 | `[project].version` = `PluginMeta.version` = `Producer.plugin_version` | **출력에 영향을 주는 변경(알고리즘·기본값·래핑 라이브러리 버전·번들 네이티브)은 minor 이상**. 버전이 지문에 들어가 `stage_key`를 바꾸므로 patch로 출력이 바뀌면 낡은 산출물이 재사용된다(바이블 §15 #8, [ADR-0037](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md)) |
| 래핑 라이브러리 | `uv.lock` 정확 고정, `pyproject` 상한(`python-pptx>=1.0,<2`처럼) | pin-and-bump: 업스트림 릴리스마다 계약 코퍼스·골든 통과 후 범프 + 플러그인 minor |
| 모델 | `model_ids = ["{repo}@{revision}"]`, `models.lock` | revision 변경 = 지문 변경; `safetensors` 전용, `.bin/.pt/.pkl` 로더 거부 |
| Python | `requires-python = ">=3.12,<3.14"` | 코어와 동일([ADR-0035](../06-adr/0035-python-version-and-toolchain-pins.md)) |

`role`은 `string | null`이라 열거 대조 대상이 아니다. 05 §5.6 예시 철자(`format_detector`, `korean_analyzer`, `sentence_splitter`, `pii_detector`, `token_counter`, `renderer`, `ocr_engine`, `vlm_document_parser`)를 그대로 쓴다.

## 12. 배포

**결정:** 플러그인은 PyPI 패키지 `rag-plugin-{name}`(import `rag_plugin_{name}`)으로 배포한다. 코어 모노레포 `plugins/`에는 A/B 등급만 두고, GPL/AGPL 플러그인·이미지는 `rag-platform-gpl-sidecars`에서 독립 릴리스한다(바이블 §6.7·§12, [ADR-0036](../06-adr/0036-naming-and-identifier-conventions.md)).

| 단계 | 내용 |
|------|------|
| 빌드 | `uv build`(wheel + sdist); wheel 메타데이터 `License` = `PluginMeta.license`(라이선스 게이트가 pip 메타데이터를 읽음) |
| 리포트 동봉 | CI가 생성한 `conformance.json`을 패키지 데이터로 포함(§8.3); 없으면 신뢰 수준 `untrusted` |
| 게이트 | `uv lock --check`, ruff, mypy strict, import-linter, pip-licenses + liccheck(등급표), cyclonedx SBOM, 적합성 키트 |
| 게시 | PyPI Trusted Publishing(OIDC)으로 CI에서 직접 업로드; 태그 `rag-plugin-{name}/v{semver}`(제안, 10-development/01 §5) |
| 서명 | 배포 아티팩트 서명(Sigstore cosign 또는 조직 키; **확인 필요 as of 2026-09**, 05 미해결 이슈 5) — 서명 없으면 `verified`로 도출되지 않음 |
| 사이드카 이미지 | 레지스트리에 digest 고정 태그; Helm values는 `image@sha256:…` 참조; C 등급은 위성 저장소 |
| 설치 | 운영 환경은 잠금 파일로만 설치(런타임 `pip install` 금지); 프로파일이 참조하지 않는 플러그인은 임포트되지 않으므로 선택 설치가 가능 |

## 13. 카탈로그 등재 절차

카탈로그는 05 §13(코어 내장 §13.1 / 별도 패키지 §13.2)이다. 등재 조건은 05 §13 그대로 다섯 가지 — `PluginMeta` 유효, 적합성 키트 통과 리포트, 라이선스 등급·`territory` 판정, 격리 모드 선언, 소유자 연락처.

1. **사전 점검**: `uv run rag plugin list --check-license`가 도출 신뢰 수준 `verified`(외부) 또는 `core`(코어)를 출력하고 `conformance.json`의 모든 `modules[].status`가 `passed`/`skipped`인지 확인한다.
2. **PR 작성**: 05 §13.2 표에 행 추가(패키지, 저장소, 확장 지점/`plugin_id`, 격리, 등급, 비고) + 이 문서 §4~§6 형식의 README 링크 + `conformance.json` + pip-licenses 출력 + SBOM + `models.lock`(모델 있을 때).
3. **리뷰어**: CODEOWNERS(10-development/01 §8)에 따라 `@rag-platform/kernel`(SDK 표면·적합성)과 `@rag-platform/license-compliance`(등급·`territory`·`linkage`)가 필수 승인한다. 새 열거값·계약 필드가 필요한 플러그인(§4.1의 `pptx`)은 바이블 §1.2 절차(ADR + 바이블 표 갱신)가 **선행**되어야 한다.
4. **등재 후**: 프로파일 예시(`profiles/examples/{name}.yaml`, 제안)를 함께 두고 `rag profile validate`를 CI에 추가한다. 카탈로그 행의 `plugin_id`·등급은 바뀌면 PR로 갱신하며, 릴리스 정체 6개월·적합성 실패 방치 시 `restricted` 표기 후 제거 후보로 올린다(운영 규칙 제안).

## 14. 리뷰 기준

### 14.1 라이선스

| 항목 | 기준 | 위반 시 |
|------|------|---------|
| 등급표 | `license_grade` A(Apache/MIT/BSD/MPL-2.0) 자유; B(LGPL) `dynamic` + 선택 extra만; C(GPL/AGPL/SSPL/ELv2/BUSL) `sidecar` + 위성 저장소 + `optIn`; D(모델 제한·지역 제한·매출 임계·귀속) 기본 프로파일 금지 + `model_license_ack`; X 금지(D-02, ADR-0001) | `plugin.license_denied` |
| 의존성 전수 | pip-licenses + liccheck 결과가 등급표와 일치; 전이 의존성 포함; "sunset 공지 패키지"(`langchain_classic` 등) 없음 | 머지 거부 |
| 모델 | `models.lock`(id, revision, sha256, license, grade, territory) 행 존재; `safetensors`; 가중치·LICENSE 자체 스토리지 미러링 | 머지 거부 |
| `territory` | 지역 제한 모델(HunyuanOCR류 X) 배제; `territory`가 비어 있지 않으면 `license_policy.territory` 전부 포함 | 로딩 거부 |
| 고지 | `LICENSE`·`NOTICE`(제3자), REUSE 헤더; 한컴 고지 문자열 검사(HWP 계열) | 머지 거부 |

### 14.2 보안

| 항목 | 기준(강제 지점) |
|------|-----------------|
| 테넌트 경계 | 백엔드 요청에 `tenant_id` 필터 존재, 사후 필터 없음(E7); 보안 필드 누락 배치 거부(E5); `record_id`·`stage_key` 스코프 합성 준수(E17); 타 테넌트 키 생성 불가(`ctx.artifacts` 쓰기 전용); 렌더러 페이로드에 `tenant_id`·주체·`acl_*`·`record_id` 없음(순수성·콘텐츠 유출 E13은 §3.1·§3.3·§10) |
| 비밀 | 비밀은 `credentials_ref` 간접 참조만; 환경 변수 직접 읽기·설정에 비밀·호스트 리터럴 없음(바이블 §6.6); 사이드카 주소는 서비스 디스커버리 이름만(E16) |
| 입력 위생 | 크기 상한(`fetch.max_bytes`), 압축 폭탄 상한(제안 100:1·1GiB), 매크로 실행 없음; 역직렬화는 JSON/XML 파서만(pickle·`eval` 금지); SQL·질의 DSL은 값 바인딩만, 식별자는 등록 목록·화이트리스트만(§5.4) |
| 공급망 | `uv lock --check`, SBOM, 잠금 파일 설치, 서명 |
| 필터 불변식 | `filters.security`·`filters.strategy` 변경 시도 없음(E6, `query_transformer`) |

### 14.3 품질·명명

적합성 6모듈 통과, 골든 케이스 존재, 결정성 등급 선언(`pure`/`model_pinned`/`generative`, 01 §8.1 제안)과 카세트, `plugin_id` = entry point 조립값, `role` 철자, `config_schema` 기본값 = 바이블 §7.2, 오류 코드가 카탈로그 철자, 부분 성공이 데이터로 표현됨.

## 15. 안티패턴

앞 절에서 규칙으로 적은 것을 리뷰어가 한눈에 대조하도록 묶은 표다. 근거·대안의 정본은 괄호의 절이다.

| 안티패턴 | 대신(정본 절) |
|----------|----------------|
| `datetime.now()`·`random`·`uuid4()`; `run()` 안 재시도·자체 타임아웃·모델 로딩; `ArtifactRef.uri`로 스토리지 직접 읽기 | `ctx.now()`·결정적 `H()` 파생 키(발급형 ID는 셸이 전달); 셸 `StagePolicy` + `ctx.remaining_ms()`; 모델은 `StageLifecycle.init`; 바이트는 `ctx.source_bytes()`(제안)·`ctx.lineage`·`ctx.artifacts.put_*`(§3.1·§3.2) |
| `StageError`를 `raise`; 카탈로그 밖 오류 코드·`retryable` 임의 설정; 리랭크·카운트 실패를 예외로 전파 | `raise StageFailure(stage_error(...))`, 바이블 §5.7 코드만; 부분 실패는 데이터(`rerank.applied=false`, `degraded[]`)(§3.3·§6.1) |
| 결과를 가져온 뒤 Python에서 ACL 필터링(사후 필터); SQL·DSL에 값 문자열 결합; `tenant_id`를 메트릭 라벨·스팬 평문에; 본문을 `detail`·로그에 | 백엔드 사전 필터 + `security_context_hash` 서명, 값 바인딩·식별자 화이트리스트; `rag.tenant_id_hash`; ID·오프셋·길이만(§5.4·§10·§14.2) |
| `fingerprint()` 자유 구성, 모델 revision·이미지 digest 누락; 출력이 바뀌는 patch 릴리스 | SDK `hash_of` 단일 식 + 필수 구성요소; minor 이상(§3.1·§11, 리스크 #8) |
| `extra="allow"` 설정 모델·계약 외 필드(`extensions`, `x-*`); 새 entry point 그룹 추가; 후처리 순서 변경·단계 생략 | `extra="forbid"`, 필드는 소유 문서 미해결 이슈로 제안; 서브 역할은 `PluginMeta.role`(D-10); 한 단계 구현만 교체(D-07, §6.2·§7) |
| GPL/AGPL을 `in_process`·`helper_process`로; 사이드카에 바이트·비밀번호 인라인 | `sidecar` + 위성 저장소; `ArtifactRef` + `credentials_ref`(§9) |
| 코어 어댑터 클래스 상속; `.pt/.pkl` 모델 로딩 | 프로토콜 구조적 구현(`StageBase` 상속은 선택, §1); `safetensors` + `models.lock`(§11·§14.1) |

## 결정 사항 요약

- **결정:** 플러그인은 `Stage[In, Out]` 5멤버(또는 포트 4종) 구현 + `pyproject.toml`의 entry point(`rag_platform.{extension_point}`)와 `[tool.rag_platform.plugin]`(`PluginMeta` 1개) 선언으로 등록되며, `plugin_id`는 그룹·이름 조립값과 일치해야 한다([ADR-0032](../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md), [ADR-0036](../06-adr/0036-naming-and-identifier-conventions.md)).
- **결정:** 배포 패키지는 `rag-plugin-{name}`(import `rag_plugin_{name}`)이며 작성 지시의 `rag-platform-plugin-*`는 채택하지 않는다(바이블 §6.7). GPL/AGPL은 `rag-platform-gpl-sidecars`에서 독립 릴리스한다([ADR-0001](../06-adr/0001-license-grade-table-and-d02-interpretation.md)).
- **결정:** 플러그인은 `rag_platform.sdk`·`rag_platform.contracts`(테스트는 `rag_platform.testing`)만 임포트하고, I/O·시간·난수는 `ctx`로만 접근하며, 오류는 `StageFailure` 하나만 던진다(바이블 §4.1; 01 §2.5·§10.1).
- **결정:** 모든 플러그인은 적합성 키트 6모듈을 상속 실행하고 결과 `conformance.json`(이 문서 소유 스키마, §8.3)을 패키지에 동봉한다. 미통과는 카탈로그 미등재다([ADR-0032](../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md)).
- **결정:** 격리는 `in_process / helper_process / sidecar` 3단이고 C 등급은 `sidecar` 강제, 사이드카는 REST `POST /v1/convert` + `GET /healthz`만(gRPC 템플릿 없음)이며 클라이언트는 `SidecarStage` 서브클래스다([ADR-0033](../06-adr/0033-sidecar-convert-contract-and-isolation-ladder.md), [ADR-0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md)).
- **결정:** 새 포맷 파서(PPTX)는 `SourceFormat` 열거 추가(바이블 §1.2 minor, ADR 발의)가 선행되어야 프로파일에 들어갈 수 있다. 개발·테스트는 키트와 `rag run-stage`(제안)로 한다.
- **결정:** pgvector 백엔드는 `IndexBackend` 포트 구현이며 `role: vector`만 맡고(`supports_server_bm25=false`, `korean_analyzer=false`, `supports_multivector=false`), 원장 PostgreSQL과 다른 DSN·풀로 접속한다. 리트리버는 별도 확장 지점 구현이다([ADR-0004](../06-adr/0004-deterministic-chunk-id-scoped-record-id-and-ulid-exception.md), [ADR-0026](../06-adr/0026-index-commit-generation-saga-and-ledger.md), [ADR-0034](../06-adr/0034-retrieval-hot-path-postgres-independence-and-hydrate.md)).
- **결정:** 리랭커 실패는 예외가 아니라 fused 순서 폴백 데이터이고, 후처리기는 고정 순서 안의 한 단계 구현만 교체한다([ADR-0013](../06-adr/0013-fusion-rrf-k60-then-convex-combination-and-postprocess-order.md)).
- **결정:** 플러그인은 스팬·메트릭을 만들지 않으며 외부 호출에만 `@instrumented_call`(제안)을 붙인다. 출력에 영향을 주는 변경은 minor 이상이다([ADR-0022](../06-adr/0022-observability-genai-semconv-pin-and-license-boundary.md), [ADR-0037](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md)).

## 미해결 이슈

1. **`SourceFormat`에 `pptx` 추가.** 튜토리얼 1은 열거 확장을 전제한다. ADR 발의(minor) → 바이블 §5.7·`schemas/common-types.schema.json`(03-contracts/00) 갱신 → 코어 `parser.format_detector`의 OOXML 프레젠테이션 스니핑(04-pipelines/03) → 내장 프로파일 `parse.router.pptx` 키 추가(§7.4 (10)) 순서로 처리한다. 키트 픽스처 `pptx-public-v1`(공공누리 제1유형 발표자료) 구성도 함께. 발표자 노트의 정본 매핑(`annotations.kind=memo` vs `footnote`)은 03-contracts/03과 합의.
2. **`ctx.source_bytes()` 포트.** 파서가 원본 바이트를 얻는 포트는 04-pipelines/04 미해결 이슈 18의 제안이며 01 §3 `StageContext` 확장(바이블 §4.1 표 갱신)으로 확정되어야 한다. 확정 전 파서 튜토리얼 코드는 스케치다.
3. **pgvector 단일 DB 프로파일과 ADR-0034.** 07-tech-landscape/06 "postgres-only(소규모)"는 원장과 인덱스를 한 PostgreSQL에 두지만 ADR-0034는 검색 핫패스의 원장 PostgreSQL 미의존을 요구한다. 이 문서는 "다른 DSN·풀"을 결정으로 두었고, 같은 인스턴스 허용 여부·설정 키(`RAG_INDEX_PGVECTOR__DSN`, 제안; 바이블 §6.6 개정)는 02-architecture/04·09-operations/02와 합의. `sparsevec` 차원(어휘 크기 250,002), `halfvec` 채택 시 `max_vector_dim=4000`, `acl_classification_rank` 컬럼화 규칙, RLS 정책의 `app.tenant_id` 주입 경로도 04-pipelines/13에서 확정.
4. **후처리기 대체 구현의 `plugin_id`.** 05 §3.13은 `plugin_id = postprocessor.{step}`로 적어 대체 구현이 같은 ID로 충돌한다(`profile.invalid` duplicate). 이 문서는 `postprocessor.{step}_{variant}` + `Capabilities.extra.step`을 바인딩 키로 쓰는 안을 제안하며, 프로파일 단계 키 아래 `plugin` 필드(`postprocess.dedup.plugin`)는 03-contracts/15 프로파일 스키마 확정 대상이다.
5. **`conformance.json` 스키마 파일과 CLI.** §8.3 스키마의 파일 위치(`schemas/conformance-report.schema.json`, 인벤토리 밖 도구 스키마)와 `$id`는 03-contracts/14·00과 합의 후 생성한다. pytest 옵션 `--conformance-report`, 기반 클래스 명 `{ExtensionPoint}Conformance`, `rag plugin verify {plugin_id}@{version}`·`rag plugin schema {plugin_id}`(05 미해결 이슈 5), `resumable_equivalence` 모듈(01 미해결 이슈 10)은 제안이다. 서명 수단(Sigstore vs 조직 키)은 09-operations/05.
6. **배열 `PluginMeta`(`[[tool.rag_platform.plugin]]`).** 튜토리얼 2가 백엔드·리트리버를 두 패키지로 나눈 이유다. 05 미해결 이슈 13·03-contracts/15 확정 시 이 문서 §2.2·§5.1을 갱신한다.
7. **llama.cpp rerank 응답 스키마.** `/v1/rerank`가 `cohere` 스키마(`results[].relevance_score`)인지 확인 필요(as of 2026-09). 다르면 `RerankResponseSchema` 열거 추가(minor)가 필요하다. 어댑터가 두 스키마를 모두 파싱하므로 코드 변경은 없다.
8. **`Capabilities.extra` 확장 지점별 필드.** 튜토리얼이 쓴 `parser.extra{source_kinds, page_provenance, table_merged_cells, arch}`, `retriever.extra{channel, backend_id, supports_prefilter, supports_variants}`, `reranker.extra{backend, response_schema, max_tokens_per_text, tokenizer_id}`, `postprocessor.extra{step, mutates_text, requires_vectors}`는 05 §5 제안이며 03-contracts/15가 확정한다.
9. **cookiecutter 템플릿 저장소.** `cookiecutter-rag-plugin`의 소유·위치(코어 모노레포 `tools/` vs 별도 저장소), 도구(cookiecutter/copier), `importlinter` 플러그인 계약 표준 문구는 10-development/07·08과 합의.
10. **`QueryVariant`의 질의 벡터 필드.** 리트리버가 질의 벡터를 어디서 읽는지(`rewritten_queries[]` 원소의 벡터 번들 필드명)는 03-contracts/09 확정 대상이다. 확정 전 튜토리얼 2 리트리버 코드의 `_query_vector`는 자리표시자다.
11. **카탈로그 유지 규칙.** 릴리스 정체 6개월·적합성 실패 방치 시 `restricted` 표기 후 제거 후보(§13 4항)는 운영 규칙 제안이며 10-development/07(기여 가이드)에서 확정.

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) — §2 R2·R4, §3 원칙 2·3·4·5·8·9, §4 D-01·D-02·D-04·D-06·D-07·D-10·D-15·D-17, §6 플러그인 SDK, §9 문서 규약
- [설계 바이블](../02-architecture/00-design-bible.md) — §1.2 변경 절차, §3.1 D-10, §3.2 O-04·O-10, §3.3, §4.1~§4.4, §5.1 `PluginMeta`·`Capabilities`·`ConvertRequest`, §5.3, §5.4 `SourceDocument`·`ParsedDocument`·`IndexRecord`·`IndexCommit`, §5.5 `CandidateSet`·`RankedSet`, §5.6 `PluginMeta`, §5.7 열거·오류 카탈로그, §6.1·§6.2·§6.5·§6.7, §7.4, §8.2, §10.2·§10.3 E5·E7·E8·E13·E16·E17, §11.3·§11.4, §12, §13.4, §15 #8
- [플러그인 아키텍처](../02-architecture/05-plugin-architecture.md) — §2 커널, §3 확장 지점 14종(§3.3 `Parser`, §3.8 `IndexBackend`, §3.10 `Retriever`, §3.12 `Reranker`, §3.13 `Postprocessor`), §4 `config_schema`, §5 `Capabilities`, §6 등록·레지스트리, §7 격리·`SidecarStage`, §8 버전, §9 관측성, §10 적합성 키트, §11 보안·신뢰 수준, §12 프로파일, §13 카탈로그, 미해결 이슈 5·13
- [파이프라인 프레임워크](../04-pipelines/01-pipeline-framework.md) — §2.3~§2.5 `config_schema`·`fingerprint`·순수성, §3 `StageContext`, §5.3 계약 검증, §8 결정성 등급, §9 관측성, §10 오류, §11 `ResumeCursor`, §12 테스트 유틸리티, §13 `rag run-stage`
- [계약 개요](../03-contracts/00-contract-overview.md) — §4.19~§4.21, §8.2 확장 필드 정책, §10.3 CI 게이트 · [컬렉션·프로파일·정책 계약](../03-contracts/15-collection-profile-and-policy-contracts.md) — §4 `PluginMeta`, §5 `Capabilities`·`IndexBackendCapabilities`, M-1·M-2 · [평가·피드백·사이드카 계약](../03-contracts/16-eval-feedback-and-sidecar-contracts.md) · [스키마 버전 관리](../03-contracts/14-schema-versioning-and-compatibility.md) · [오류 모델](../03-contracts/13-error-model.md)
- [저장소 구조](./01-repository-structure.md) — §1 저장소 경계, §3.3 멤버 `pyproject.toml`, §4.3 플러그인 의존 규칙, §5 명명, §7 테스트 디렉터리, §8 CODEOWNERS · [테스팅 전략](./04-testing-strategy.md) · [CI/CD](./05-ci-cd.md) · [기여 가이드](./07-contributing.md) · [릴리스 프로세스](./08-release-process.md)
- [관측성](../09-operations/03-observability.md) — `rag.{stage}.call`·`@instrumented_call`(제안), 메트릭 표 · [설정 레퍼런스](../09-operations/02-configuration-reference.md) · [보안·컴플라이언스](../09-operations/05-security-and-compliance.md)
- [기술 지형 종합: 선정 매트릭스](../07-tech-landscape/00-summary-and-selection-matrix.md) — 역할과 D-10 매핑, 어댑터·플러그인 공통 요구 1~7 · [벡터·렉시컬 인덱스 백엔드](../07-tech-landscape/06-vector-and-lexical-index-backends.md) — pgvector·pg_textsearch, `IndexBackendCapabilities` 초안, 백엔드 매핑·alias 표 · [검색 기법·융합·리랭킹](../07-tech-landscape/07-retrieval-techniques-fusion-reranking.md) — 리랭커 대안(llama.cpp)
- 파서 관련: [파싱 라우터와 포맷 판별](../04-pipelines/03-parsing-router-and-format-detection.md), [HWPX/HWP 파서](../04-pipelines/04-parser-hwpx-and-hwp.md)(`ctx.source_bytes()` 제안), [인덱싱](../04-pipelines/13-indexing.md), [리랭킹](../04-pipelines/16-reranking.md), [후처리와 컨텍스트 패킹](../04-pipelines/17-post-processing-and-context-packing.md)
- ADR(바이블 §3.3 번호·slug): [0001](../06-adr/0001-license-grade-table-and-d02-interpretation.md), [0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md), [0004](../06-adr/0004-deterministic-chunk-id-scoped-record-id-and-ulid-exception.md), [0013](../06-adr/0013-fusion-rrf-k60-then-convex-combination-and-postprocess-order.md), [0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md), [0022](../06-adr/0022-observability-genai-semconv-pin-and-license-boundary.md), [0026](../06-adr/0026-index-commit-generation-saga-and-ledger.md), [0032](../06-adr/0032-plugin-sdk-stage-protocol-and-conformance-kit.md), [0033](../06-adr/0033-sidecar-convert-contract-and-isolation-ladder.md), [0034](../06-adr/0034-retrieval-hot-path-postgres-independence-and-hydrate.md), [0035](../06-adr/0035-python-version-and-toolchain-pins.md), [0036](../06-adr/0036-naming-and-identifier-conventions.md), [0037](../06-adr/0037-artifact-cache-scope-and-stage-key-composition.md)
