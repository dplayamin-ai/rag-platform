export const meta = {
  name: 'rag-phase6a-scaffold',
  description: 'Phase 6A: reference scaffold — uv project, toolchain, generated contracts package from schemas, core stubs (Stage/Context/ArtifactStore/Registry/profile loader/LocalRunner), in-memory test doubles, CI, HANDOFF and deferred-verification ledger; everything runnable on the VDI is executed and verified',
  phases: [
    { title: 'S1 Foundation', detail: 'pyproject/uv/ruff/mypy/import-linter/pytest markers; uv sync passes' },
    { title: 'S2 Contracts', detail: 'schemas → Pydantic package via generator; roundtrip tests from doc examples' },
    { title: 'S3 Core', detail: 'Stage/PipelineContext/ArtifactStore/Registry/profile loader/LocalRunner + doubles' },
    { title: 'S4 Handoff', detail: 'CI yaml, HANDOFF.md, deferred ledger generator' },
    { title: 'S5 Review', detail: 'static review vs bible §12/ADR-0035 + full test run, one fix round' },
  ],
}
const ROOT = 'C:\\Workspaces\\rag-platform'
const D = ROOT + '\\docs\\'
const BRIEF = D + '00-vision\\00-design-brief.md'
const BIBLE = D + '02-architecture\\00-design-bible.md'
const DATE = (args && args.date) || '2026-09-24'
const OUT = { type: 'object', properties: { summary: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, commands_run: { type: 'array', items: { type: 'string' } }, tests: { type: 'object', properties: { passed: { type: 'integer' }, failed: { type: 'integer' }, deferred: { type: 'integer' } }, required: ['passed', 'failed', 'deferred'] }, open_issues: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'files', 'commands_run', 'tests', 'open_issues'] }
const REVIEW = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['file', 'severity', 'problem', 'fix'] } }, verdict: { type: 'string', enum: ['accept', 'revise'] }, test_summary: { type: 'string' } }, required: ['findings', 'verdict', 'test_summary'] }

const ENV = `## 실행 환경(반드시 이대로)
- 작업 루트 ${ROOT}. Windows VDI, Git Bash 셸. Python은 시스템에 없고 **uv 0.12**만 있다: \`uv python find 3.12\`(3.12.14 설치됨), 가상환경은 \`uv venv --python 3.12\`(\`.venv\`), 패키지는 \`uv add\`/\`uv sync\`, 실행은 \`uv run <cmd>\`(예: \`uv run pytest -q\`, \`uv run ruff check .\`, \`uv run mypy\`). 프록시는 환경변수(HTTPS_PROXY)로 이미 설정되어 PyPI·GitHub·Hugging Face 접근이 된다. Docker·WSL·GPU는 없다.
- 3층 검증 규칙(05-phase6 계획 §8): 여기서 실행 가능한 것은 **반드시 실행해 통과**시킨다. Docker·GPU·외부 서비스가 필요한 코드는 Protocol 뒤에 두고 인메모리 대역으로 단위 검증하며, 실제 통합 테스트는 pytest 마커 \`needs_docker\`/\`needs_model\`(모델 가중치 다운로드 필요 — **다운로드 금지**, 사용자 결정)/\`needs_gpu\`/\`needs_network\`로 표시하고 코드에 \`# DEFERRED: <무엇을 어디서 어떻게 검증>\` 주석을 남긴다. 마커 테스트는 기본 실행에서 제외(pyproject addopts \`-m "not needs_docker and not needs_model and not needs_gpu and not needs_network"\`). 임베딩·리랭킹·OCR은 결정적 가짜 구현(FakeEmbedder 등)으로 검증한다.
- 정본: 브리프 ${BRIEF} > 바이블 ${BIBLE}(Grep으로 절 위치를 찾아 필요한 절만 Read; §6 명명, §12 모듈 맵, §5.7 열거, §4 스테이지) > ADR > 개별 문서. 계약 모델은 \`schemas/*.schema.json\`이 정본이며 Pydantic은 **생성물**(손으로 쓰지 않는다).
- 코드 규약: 10-development/03(ruff·mypy strict·Pydantic v2·async 우선·StageError), 계층 규칙 import-linter(contracts ← core ← stages ← workflows ← api). 식별자·docstring 영어, 커밋은 하지 않는다(오케스트레이터가 함). 이모지 금지.
- 다른 에이전트가 다른 디렉터리를 동시에 편집할 수 있다. 지정된 범위만 쓴다. 완료 전 \`uv run pytest -q\`와 \`uv run ruff check .\`을 실행해 결과를 tests/commands_run에 적는다.`

phase('S1 Foundation')
const s1 = await agent(`당신은 이 플랫폼의 레퍼런스 구현 골격을 만드는 수석 엔지니어다. 저장소 구조 문서 ${D}10-development\\01-repository-structure.md, 개발 환경 ${D}10-development\\02-development-environment.md, 코딩 표준 ${D}10-development\\03-coding-standards.md, 테스트 전략 ${D}10-development\\04-testing-strategy.md, ADR-0035(${D}06-adr\\0035-python-version-and-toolchain-pins.md), 바이블 §12(모듈/패키지 맵)·§6.7(패키지·모듈 명명)을 읽고 다음을 만든다.

1. \`pyproject.toml\`(uv 프로젝트; 패키지명·import 이름은 10-development/01·바이블 §6.7 그대로; Python \`>=3.12,<3.14\`; 의존성 최소: pydantic>=2, pydantic-settings, ulid 라이브러리(python-ulid), blake3, pyyaml, jsonschema(2020-12 지원), httpx, anyio; dev: pytest, pytest-asyncio, hypothesis, ruff, mypy, import-linter, datamodel-code-generator), \`.python-version\`(3.12), \`uv.lock\`(\`uv lock\` 실행), \`.gitignore\`(.venv, __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, dist, *.egg-info, samples/cache).
2. 패키지 디렉터리 골격 \`src/rag_platform/\`(contracts, core, stages/{fetch,parse,normalize,chunk,enrich,embed,index,retrieve}, workflows, api, mcp, eval, observability, plugins, cli — 각 \`__init__.py\`와 모듈 docstring), \`tests/{unit,contract,integration,e2e}\`, \`plugins/\`, \`sidecars/\`, \`deploy/compose/\`, \`samples/\`, \`tools/verify/\`(빈 README).
3. 도구 설정: ruff(선택 규칙은 03 문서), mypy strict(pyproject), import-linter 계약(\`[tool.importlinter]\` layers: rag_platform.api → workflows → stages → core → contracts; 위반 시 실패), pytest(마커 4종 needs_docker·needs_model·needs_gpu·needs_network 등록, \`asyncio_mode = "auto"\`, addopts로 마커 기본 제외, testpaths).
4. 검증: \`uv sync\` → \`uv run ruff check .\` → \`uv run mypy src\` → \`uv run lint-imports\` → \`uv run pytest -q\`(빈 테스트 1개라도 통과) 모두 성공. 실패하면 고친다.
5. 루트 \`Makefile\` 대신 크로스플랫폼 \`tools/dev.py\`(uv run python tools/dev.py lint|type|test|test-deferred|contracts-gen) 스크립트.
결과: 만든 파일 목록, 실행한 명령, 테스트 수.
${ENV}`, { label: 's1:foundation', phase: 'S1 Foundation', schema: OUT, model: 'opus', effort: 'high' })
if (!s1) throw new Error('S1 failed')
log(`S1: 파일 ${s1.files.length}, 테스트 ${s1.tests.passed}/${s1.tests.failed}`)

phase('S2 Contracts')
const [s2, s3] = await parallel([
  () => agent(`당신은 계약 패키지 담당이다. \`schemas/*.schema.json\`(35개, JSON Schema 2020-12, \`$id\` urn:rag:schema:<kebab>:1, 공용 타입·열거는 \`urn:rag:schema:common-types:1#/$defs/<Type>\` 참조)에서 Pydantic v2 모델을 **생성기로** 만든다.
1. \`tools/contracts_gen.py\`: (a) schemas/를 임시 디렉터리로 복사하며 \`urn:rag:schema:<name>:1#/$defs/X\` 참조를 \`<name>.schema.json#/$defs/X\` 상대 참조로 재작성 (b) datamodel-code-generator(\`--input-file-type jsonschema --output-model-type pydantic_v2.BaseModel --use-standard-collections --use-union-operator --field-constraints --strict-nullable --use-schema-description --target-python-version 3.12\`)로 \`src/rag_platform/contracts/\`에 모듈 생성(파일당 스키마 1개, \`common_types.py\` 공용; \`__init__.py\`에서 재노출) (c) 생성 헤더에 "GENERATED — do not edit; run uv run python tools/contracts_gen.py" 표기 (d) 생성 결과가 import 가능하고 mypy를 통과하는지 확인, 통과 못 하면 생성기 옵션·전처리를 조정(수동 편집 금지). 열거는 \`StrEnum\`으로 생성되게 한다(옵션 \`--enum-field-as-literal none\` 등 조정).
2. 계약 왕복 테스트 \`tests/contract/\`: \`docs/03-contracts/*.md\`의 \`\`\`json 예시 블록을 스크립트(\`tools/extract_examples.py\`)로 \`tests/contract/fixtures/<schema>/<n>.json\`으로 추출(어느 스키마의 인스턴스인지는 예시 앞 문맥·\`schema_type\`·파일 절로 판정, 판정 불가는 건너뛰고 목록 출력) → 각 픽스처를 jsonschema(2020-12, urn 리졸버)로 검증 → Pydantic 파싱 → \`model_dump(mode="json", by_alias=True, exclude_none=True)\` 재직렬화 → 원본과 의미 동치(키 순서 무시). 실패 픽스처는 문서 오류일 수 있으니 \`xfail(reason)\`으로 표시하고 open_issues에 적는다(문서는 고치지 않는다).
3. 결정적 키 벡터 테스트: 바이블 §6.2 \`H()\` 결합식과 ADR-0004의 고정 벡터(문서에서 Grep)를 \`src/rag_platform/core/keys.py\`(blake3 기반 H, block_id/chunk_id/record_id/point_id) 구현과 함께 테스트. 이 파일은 core 소유이므로 S3와 충돌하지 않도록 \`core/keys.py\` 한 파일만 만든다.
4. \`uv run pytest -q tests/contract\` 통과(xfail 제외), ruff·mypy 통과.
${ENV}`, { label: 's2:contracts', phase: 'S2 Contracts', schema: OUT, model: 'sonnet' }),
  () => agent(`당신은 코어 프레임워크 담당이다. 파이프라인 프레임워크 ${D}04-pipelines\\01-pipeline-framework.md, 컴포넌트 아키텍처 ${D}02-architecture\\02-component-architecture.md, 플러그인 아키텍처 ${D}02-architecture\\05-plugin-architecture.md, ADR-0003(오케스트레이터 중립·LocalRunner)·ADR-0032(Stage 프로토콜 5멤버)·ADR-0037(stage_key 스코프), 바이블 §4(스테이지 정본)·§7.3(프로파일 YAML 스키마)·§11.1(두 실행기)을 읽고 \`src/rag_platform/core/\`(keys.py 제외 — S2가 만든다; 필요하면 \`from rag_platform.core.keys import H\`를 가정하고 인터페이스만 맞춘다)와 테스트를 만든다.
1. \`stage.py\`: \`Stage\` Protocol(ADR-0032의 5멤버 그대로), \`StageError\`(계약 StageError 모델을 감싸는 예외; 코드는 바이블 §5.7 \`{stage}.{reason}\` 철자), 재시도 분류.
2. \`context.py\`: \`PipelineContext\` Protocol과 \`LocalContext\` 구현(tenant/collection/profile/trace/clock/budget/logger, artifact store, secrets 참조만).
3. \`artifacts.py\`: \`ArtifactStore\` Protocol + \`FileArtifactStore\`(file://; 콘텐츠 주소화 키 규약 바이블 §13.3, zstd 선택) + \`InMemoryArtifactStore\`(테스트 대역).
4. \`registry.py\`: entry points 기반 \`PluginRegistry\`(그룹 이름 \`rag_platform.<extension_point>\` 14종, \`PluginMeta\` 검증, 격리 모드 enum) + 테스트용 수동 등록 API.
5. \`profile.py\`: 프로파일 YAML 로더 — \`schemas/profile.schema.json\`으로 검증(jsonschema 2020-12 + urn 리졸버), \`extends\` 단일 상속(ADR-0031), \`profile_hash\` 계산, 로딩 검증 규칙(바이블 §7.4) 중 구현 가능한 것; 바이블 §7.3 예시 YAML 4종을 \`profiles/{lite,standard,premium,korean-gov}.yaml\`로 저장하고 로딩 테스트.
6. \`runner_local.py\`: 비내구 \`LocalRunner\` — 프로파일의 수집 스테이지 순서를 받아 \`Stage.run\`을 직렬 실행, 산출물을 ArtifactStore에 저장, \`stage_key\` 캐시 히트 시 생략(ADR-0037), 실패 시 StageError 분류에 따라 중단/부분.
7. 테스트 대역 \`src/rag_platform/core/testing/\`: \`InMemoryLedger\`(원장 Protocol 최소: 문서·잡·커밋 레코드), \`InMemoryKV\`(Valkey 대역), \`FakeEmbedder\`(결정적 해시 벡터), \`InMemoryIndexBackend\`(IndexBackend Protocol의 upsert/search_dense/search_lexical 최소; 코사인 브루트포스). 각각 \`# DEFERRED:\` 주석으로 실제 구현(PostgreSQL·Valkey·TEI·Qdrant)의 검증 위치를 남긴다.
8. 단위 테스트 \`tests/unit/core/\`: 각 모듈 최소 3케이스, LocalRunner는 더미 Stage 2개 체인 + 캐시 히트 + 실패 분류. \`uv run pytest -q tests/unit\`·ruff·mypy·lint-imports 통과.
${ENV}`, { label: 's3:core', phase: 'S3 Core', schema: OUT, model: 'sonnet' }),
])
log(`S2: 테스트 ${s2 ? s2.tests.passed + '/' + s2.tests.failed : '실패'} · S3: ${s3 ? s3.tests.passed + '/' + s3.tests.failed : '실패'}`)

phase('S4 Handoff')
const s4 = await agent(`당신은 인계 담당이다. 05-phase6 계획 ${D}12-appendix\\05-phase6-implementation-kit-plan.md §8(3층 검증)과 CI/CD 문서 ${D}10-development\\05-ci-cd.md 를 읽고 다음을 만든다.
1. \`.github/workflows/ci.yml\`: PR에서 uv 설치 → \`uv sync\` → ruff → mypy → lint-imports → \`pytest -q\`(마커 제외) → \`node tools/validate-contracts.mjs --root .\` → \`node tools/audit-docs.mjs --root .\`; 별도 job \`deferred\`(수동 트리거 workflow_dispatch, Docker 서비스 컨테이너 PostgreSQL·Qdrant·Valkey)에서 \`pytest -m needs_docker\`. 문서의 파이프라인 정의를 따르되 지금 존재하는 것만 실행한다.
2. \`tools/verify/gen-deferred-ledger.mjs\`: src/·tests/의 \`# DEFERRED:\` 주석과 pytest 마커(\`@pytest.mark.needs_docker|needs_gpu|needs_network\`)를 수집해 \`docs/12-appendix/09-deferred-verification-ledger.md\`(frontmatter, 표: 위치 | 층 | 무엇 | 어디서·어떻게 검증 | 기대 결과 | 상태(미검증)) 생성. 실행해 첫 원장을 만든다.
3. \`tools/verify/run-deferred.sh\`(Linux/macOS)와 \`run-deferred.ps1\`: docker compose lite 기동 → \`uv run pytest -m "needs_docker"\` → 결과를 \`tools/verify/results/deferred-<date>.json\`으로.
4. 루트 \`HANDOFF.md\`: 다른 머신(Docker 있는 Linux/macOS)의 첫 30분 절차 — uv 설치, \`uv sync\`, 1층 테스트 재확인, 보류 원장 열기, \`run-deferred.sh\`, 실패분 수정 규칙(계약·바이블 우선), 이 VDI에서 검증되지 않은 범위 명시, 연락·기록 위치(진행 보고서). 한국어, 120~200행.
5. \`CLAUDE.md\`가 있으면 끝에 "## 실행 환경 주의(VDI)" 절을 추가(2·3층 미검증, 마커 규칙, HANDOFF 링크). 없으면 open_issues에 적는다.
${ENV}`, { label: 's4:handoff', phase: 'S4 Handoff', schema: OUT, model: 'sonnet' })
log(`S4: 파일 ${s4 ? s4.files.length : '?'}`)

phase('S5 Review')
const rv = await agent(`당신은 코드 리뷰어다. 생성된 골격을 정적 검토하고 전체 검증 명령을 실행한다. 수정하지 않는다.
검토: (1) 바이블 §12 모듈 맵·§6.7 명명과 패키지 구조 일치 (2) ADR-0032 Stage 5멤버, ADR-0037 stage_key 스코프, ADR-0004 키 결합식이 코드와 일치(테스트 벡터 포함) (3) contracts/가 생성물임이 헤더로 표시되고 손편집 흔적이 없는가 (4) import-linter 계층 위반 (5) 마커·DEFERRED 규칙 준수, 보류 원장에 누락 없음 (6) \`uv run ruff check .\`, \`uv run mypy src\`, \`uv run lint-imports\`, \`uv run pytest -q\` 실제 실행 결과(test_summary에 적는다).
${ENV}`, { label: 's5:review', phase: 'S5 Review', schema: REVIEW, model: 'sonnet', effort: 'medium' })
let fx = null
if (rv && rv.findings.some((f) => f.severity !== 'minor')) {
  fx = await agent(`리뷰의 blocker/major를 수정하고 전체 검증 명령(ruff·mypy·lint-imports·pytest)을 다시 통과시킨다. 리뷰: ${JSON.stringify(rv.findings.filter((f) => f.severity !== 'minor'), null, 1).slice(0, 16000)}
contracts/ 생성물은 직접 고치지 말고 생성기·스키마 전처리를 고친다.
${ENV}`, { label: 's5:fix', phase: 'S5 Review', schema: OUT, model: 'sonnet' })
}
return { s1, s2, s3, s4, review: rv ? { findings: rv.findings.length, serious: rv.findings.filter((f) => f.severity !== 'minor').length, tests: rv.test_summary } : null, fixed: fx ? fx.summary : null }
