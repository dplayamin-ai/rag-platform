// 코드 헤더 소급 적용 워크플로 — 헤더 규칙(`tools/phase6/CODE-HEADER-RULE.md`)이 생기기 전에 만든 모든 소스
// 파일(src/tests/tools)에 한국어 설명 헤더를 보완하고, `ruff`·`pytest`가 여전히 통과하는지 검증한다(`Workflow`
// 하네스가 실행).
// 설계 근거: `tools/phase6/CODE-HEADER-RULE.md`(필수 항목 5개), 사용자 지시(2026-09-23, 코드 상단 한글 설명
// 주석).
// 구성: `meta`(워크플로 메타데이터·단계 목록: Header pass — 디렉터리별 그룹 실행, Verify — ruff/mypy/lint-imports/
// pytest).
// 불변식: 로직은 바꾸지 않는다 — 문서화(헤더)만 추가·보완한다; 그룹 1 담당만 `pyproject.toml`의 ruff 설정을 고칠
// 수 있다(중복 수정 방지).
// 검증 계층: 1층(여기서 검증) — 이 워크플로 자체가 `uv run ruff check .`/`uv run pytest -q`를 실행해 검증한다.
export const meta = {
  name: 'rag-code-header-pass',
  description: 'Retrofit Korean explanatory header comments onto every source file created before the header rule existed (src, tests, tools); verify ruff D100 and tests still pass',
  phases: [{ title: 'Header pass', detail: 'grouped by directory' }, { title: 'Verify', detail: 'ruff/pytest' }],
}
const ROOT = 'C:\\Workspaces\\rag-platform'
const RULE = ROOT + '\\tools\\phase6\\CODE-HEADER-RULE.md'
const OUT = { type: 'object', properties: { summary: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, skipped: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'files', 'skipped'] }
const GROUPS = (args && args.groups) || [
  ['src/rag_platform/sdk', 'src/rag_platform/contracts/__init__.py', 'src/rag_platform/plugins', 'src/rag_platform/storage'],
  ['src/rag_platform/profiles', 'src/rag_platform/orchestration', 'src/rag_platform/pipelines', 'src/rag_platform/testing', 'src/rag_platform/ledger'],
  ['tests', 'tools/contracts_gen.py', 'tools/extract_examples.py', 'tools/dev.py', 'tools/verify'],
  ['tools/validate-contracts.mjs', 'tools/audit-docs.mjs', 'tools/traceability.mjs', 'tools/usage-report.mjs', 'tools/phase3/ledger.mjs', 'tools/phase4/rename-id-prefixes.mjs', 'tools/phase5/gen-schemas-readme.mjs'],
]
phase('Header pass')
const res = await parallel(GROUPS.map((g, i) => () => agent(`당신은 코드 문서화 담당이다. 규칙 ${RULE} 을 먼저 읽는다. 아래 경로(디렉터리면 재귀)의 모든 소스 파일(.py/.mjs/.js/.ts)에 규칙대로 **한국어 설명 헤더**를 추가 또는 보완한다.
대상: ${g.map((p) => ROOT + '\\' + p.replace(/\//g, '\\')).join(' , ')}
규칙 요약: 첫 줄부터(shebang 아래) 모듈 docstring 또는 // 블록; 역할 → 설계 근거(바이블 절·ADR·계약 문서 — 파일 내용을 읽고 실제로 해당하는 절을 Grep으로 확인해 적는다, 추측 금지) → 구성(공개 클래스·함수 한 줄씩) → 불변식·주의 → 검증 계층(1층/needs_docker/needs_model/needs_gpu, DEFERRED). 6~15줄, 식별자 영문 백틱, 본문 한국어, 이모지 금지.
제외: 생성 파일(\`GENERATED\` 헤더가 이미 있는 src/rag_platform/contracts/*.py 모델 파일 — 대신 생성기 tools/contracts_gen.py가 헤더를 넣는지 확인하고, 안 넣으면 생성기 템플릿을 고쳐 재생성한다), 빈 __init__.py(한 줄 역할 docstring만), 외부 사본.
기존 영어 docstring이 있으면 한국어 헤더로 바꾸되 정보를 잃지 않는다. 코드 로직은 바꾸지 않는다. 완료 후 \`uv run ruff check <대상>\`을 실행해 D100·포맷 문제가 없는지 확인한다(ruff에 D100이 꺼져 있으면 pyproject의 select에 "D100"을 추가 — 단 그룹 1 담당만 pyproject를 고친다: ${i === 0 ? '당신이 담당' : '다른 담당이 함'}).
결과: 수정 파일 목록, 건너뛴 파일과 이유.`, { label: `headers:group-${i + 1}`, phase: 'Header pass', schema: OUT, model: 'sonnet' })))
phase('Verify')
const v = await agent(`${ROOT} 에서 \`uv run ruff check .\`, \`uv run ruff format --check .\`, \`uv run mypy src\`, \`uv run pytest -q\` 를 실행한다. 헤더 추가로 생긴 오류(들여쓰기·docstring 위치·D2xx 규칙 충돌 등)만 고치고 로직은 건드리지 않는다. 결과 요약 반환.`, { label: 'headers:verify', phase: 'Verify', schema: OUT, model: 'sonnet' })
return { groups: res.filter(Boolean).map((r) => r.files.length), verify: v ? v.summary : null }
