// Phase 6B(적합성 키트, Sonnet, 그룹 실행) + 6D(어댑터 스파이크 — HWPX 파서·Qdrant lite는 Opus, 임베더 인터페이스+
// `FakeEmbedder`는 Sonnet) 병행 워크플로 — 의존성을 먼저 추가해 pyproject 충돌을 피한다(`Workflow` 하네스가 실행).
// 설계 근거: `docs/12-appendix/05-phase6-implementation-kit-plan.md`(6B·6D 범위), 사용자 결정(2026-09-23, 모델
// 가중치 다운로드 금지 — `FakeEmbedder`만 사용).
// 구성: `meta`(워크플로 메타데이터·단계 목록: S0 Deps, 6B Conformance, 6D 어댑터 스파이크).
// 불변식: 토큰 규율 — 구현 에이전트는 과제가 지정한 파일만 읽는다; Phase 6B/6D가 이미 완료·커밋되었으므로 이
// 워크플로는 재실행 대상이 아니다(기록 보존 목적).
// 검증 계층: 1층(여기서 검증) — Phase 6B/6D 완료 시점에 `uv run pytest`/`ruff`/`mypy`/`lint-imports`로 이미 검증.
export const meta = {
  name: 'rag-phase6-6b-6d',
  description: 'Phase 6B conformance kit (Sonnet, grouped) in parallel with 6D adapter spikes (HWPX parser + Qdrant lite on Opus; embedder interface + FakeEmbedder on Sonnet); deps added first to avoid pyproject conflicts; token discipline: read only what the task names',
  phases: [
    { title: 'S0 Deps', detail: 'uv add all third-party deps once' },
    { title: '6B Conformance', detail: 'testing/ kit suites + plugin conformance base classes' },
    { title: '6D Spikes', detail: 'hwpx parser, qdrant lite backend, embedder ports' },
    { title: 'Verify', detail: 'full ruff/mypy/lint-imports/pytest + deferred ledger regen' },
  ],
}
const ROOT = 'C:\\Workspaces\\rag-platform'
const D = ROOT + '\\docs\\'
const BIBLE = D + '02-architecture\\00-design-bible.md'
const RULE = ROOT + '\\tools\\phase6\\CODE-HEADER-RULE.md'
const OUT = { type: 'object', properties: { summary: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, tests: { type: 'object', properties: { passed: { type: 'integer' }, failed: { type: 'integer' }, deferred: { type: 'integer' } }, required: ['passed', 'failed', 'deferred'] }, doc_updates: { type: 'array', items: { type: 'string' } }, open_issues: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'files', 'tests', 'doc_updates', 'open_issues'] }

const ENV = `## 실행 환경·규율(반드시)
- 루트 ${ROOT}, Git Bash. Python은 uv 관리 3.12(\`.venv\`), 실행은 \`uv run <cmd>\`. Docker·GPU 없음. **모델 가중치 다운로드 금지**(임베딩·리랭킹·OCR은 결정적 가짜 구현; 실제 모델 테스트는 \`needs_model\` 마커). 프록시는 환경변수로 설정되어 PyPI·GitHub 접근 가능.
- **읽기 예산(토큰 규율)**: 이 지시문에 명시된 파일과 직접 편집할 파일, 테스트 출력만 읽는다. 바이블은 지시문이 지정한 절만 Grep 후 Read(offset/limit), 그 외 설계 문서는 열지 않는다. 테스트 재실행은 최대 3회. 파일 3~6개 범위를 넘기지 않는다.
- 3층 검증: 여기서 실행 가능한 것은 반드시 실행해 통과. Docker·모델·GPU가 필요한 테스트는 \`needs_docker\`/\`needs_model\`/\`needs_gpu\`/\`needs_network\` 마커 + 코드 주석 \`# DEFERRED: <무엇을 어디서 어떻게>\`.
- 모든 소스 파일 첫 줄은 **한국어 설명 헤더**(${RULE}: 역할 → 설계 근거 → 구성 → 불변식·주의 → 검증 계층, 6~15줄, 식별자 영문 백틱).
- 계약 모델은 \`src/rag_platform/contracts/\` 생성물을 그대로 쓴다(손편집 금지). 열거·필드 철자는 생성물이 정본. 계층 규칙(import-linter)은 pyproject의 §12 계약을 따른다. 커밋 금지, 이모지 금지. 완료 전 \`uv run pytest -q <대상>\`, \`uv run ruff check <대상>\`, \`uv run mypy src\`를 실행해 결과를 tests에 적는다.`

phase('S0 Deps')
const s0 = await agent(`의존성 담당이다. ${ROOT}\\pyproject.toml 을 읽고 다음을 한 번에 추가한다(다른 에이전트가 동시에 pyproject를 고치지 않도록 이 단계에서만 수정): 런타임 — \`python-hwpx>=6.4,<7\`, \`qdrant-client\`, \`fsspec\`, \`httpx\`, \`lxml\`, \`charset-normalizer\`, \`markdown-it-py\`, \`trafilatura\`(있으면), \`pypdfium2\`; extras — \`kiwi = ["kiwipiepy"]\`(B 등급 LGPL 동적 링크, 선택 extra; 바이블 §6.7 extras 이름 그대로 있으면 유지); dev — \`respx\`, \`pytest-httpx\` 중 하나, \`hypothesis\`. \`uv add\`/\`uv add --optional kiwi\`/\`uv add --dev\` 로 추가하고 \`uv sync --all-extras\`가 성공하는지 확인한다(Windows 휠이 없는 패키지는 제거하고 open_issues에 적는다). ruff·mypy·pytest가 여전히 통과하는지 확인.
${ENV}`, { label: 's0:deps', phase: 'S0 Deps', schema: OUT, model: 'sonnet' })
log(`S0: ${s0 ? s0.summary.slice(0, 160) : '실패'}`)

phase('6B Conformance')
const b = parallel([
  () => agent(`적합성 키트 담당(1/3). 바이블 §12의 \`testing/\` 패키지(적합성 키트: contract_roundtrip idempotency security_invariants renderer_citation_roundtrip litm_order fuser_equivalence)와 ADR-0032(${D}06-adr\\0032-plugin-sdk-stage-protocol-and-conformance-kit.md)의 적합성 키트 절만 읽고, \`src/rag_platform/testing/\`에 다음을 만든다: (0) **선행 수정**: tests/contracts/test_contract_roundtrip.py의 xfail 40건 원인은 Y(nullable) 필드의 명시적 null이 \`exclude_none=True\`로 탈락하는 것이다(계약 개요 ${D}03-contracts\\00-contract-overview.md §8.1은 nullable 필드의 null 보존을 요구). 해결: tools/contracts_gen.py가 생성 모델의 공통 베이스 \`ContractModel\`(schemas의 \`type: [..., "null"]\` 필드를 등록해 \`dump_contract()\`가 nullable 필드의 None은 남기고 N-선택 필드의 None만 제거)을 함께 생성하도록 확장 → 재생성 → 왕복 테스트를 \`dump_contract()\` 기준으로 바꿔 xfail 제거(진짜 문서 오류만 xfail 유지). contracts/ 손편집 금지. (a) \`contract_roundtrip.py\` — 왕복 로직을 재사용 가능한 함수/픽스처로 승격(임의 계약 모델 + 예시 JSON → 스키마 검증 → 파싱 → 재직렬화 동치); (b) \`idempotency.py\` — 같은 입력·설정으로 Stage를 두 번 실행하면 \`stage_key\`와 산출물 해시가 같음을 검사하는 헬퍼(sdk의 Stage·hashing 사용); (c) \`security_invariants.py\` — QueryPlan/IndexRecord류 객체에 tenant_id·acl 사전 필터 필드가 존재·비어있지 않음을 검사하는 헬퍼(계약 생성물의 실제 필드명을 읽어 사용). 각각 tests/unit/testing/에 3케이스 이상.
${ENV}`, { label: '6b:kit-1', phase: '6B Conformance', schema: OUT, model: 'sonnet' }),
  () => agent(`적합성 키트 담당(2/3). 바이블 §8.1(융합 불변식 Σcontribution = fused_score, 타이브레이크 record_id), §9.2(litm_alternating 순서 공식), §9.3(렌더러·cite_id 규칙)만 Grep 후 읽고 \`src/rag_platform/testing/\`에 (a) \`fuser_equivalence.py\` — 임의 Fuser 구현이 RRF 정본(k=60, 가중 1:1:1, 변형 0.5)과 동치인지 골든 벡터로 검사(골든 벡터 JSON은 tests/fixtures/fusion/에 직접 작성: 채널 3개 × 후보 5개 소형 예), (b) \`litm_order.py\` — 순위 목록을 litm_alternating으로 배치한 결과의 불변식(최상위가 양끝, 마지막 항목이 질의 직전) 검사, (c) \`renderer_citation_roundtrip.py\` — 렌더 결과의 cite_id(d1..dK)가 ContextPack 항목과 1:1이고 provenance로 역매핑되는지 검사하는 헬퍼. tests/unit/testing/에 케이스 추가. 계약 필드명은 contracts 생성물에서 확인.
${ENV}`, { label: '6b:kit-2', phase: '6B Conformance', schema: OUT, model: 'sonnet' }),
  () => agent(`적합성 키트 담당(3/3). ${D}10-development\\06-plugin-development-guide.md 의 적합성 테스트 절과 6A가 만든 \`src/rag_platform/plugins/registry.py\`·\`src/rag_platform/sdk/stage.py\`·\`testing/doubles/\`를 읽고, 확장 지점 14종(fetcher parser normalizer chunker enricher embedder index_backend query_transformer retriever fuser reranker postprocessor packer evaluator)별 **플러그인 적합성 기반 테스트 클래스**를 \`src/rag_platform/testing/conformance/\`에 만든다(pytest 상속용: 시그니처 5멤버, 계약 입출력 타입, 멱등성, StageError 분류, PluginMeta 필수 필드·license_grade). 6A의 인메모리 대역(FakeEmbedder·InMemoryIndexBackend 등)이 해당 클래스를 상속해 통과하는 테스트를 tests/unit/conformance/에 둔다. 프로파일 4종 로딩·profile_hash 안정성 테스트도 추가.
${ENV}`, { label: '6b:kit-3', phase: '6B Conformance', schema: OUT, model: 'sonnet' }),
])

phase('6D Spikes')
const d = parallel([
  () => agent(`HWPX 파서 스파이크(Opus). 읽기: ${D}04-pipelines\\04-parser-hwpx-and-hwp.md 의 HWPX 절(매핑 표·heading 추론·표 처리·provenance), 바이블 §5.4 ParsedDocument·Block 표(Grep '#### \`ParsedDocument\`'), contracts 생성물 \`parsed_document.py\`. 할 일: (1) python-hwpx(설치됨)의 실제 API를 탐색해 HWPX → \`ParsedDocument\` 어댑터 \`src/rag_platform/adapters/parse/hwpx_python_hwpx.py\`(+ \`owpml_adapter.py\`)를 구현: 문단→paragraph, 개요 레벨→heading level, 표(병합 셀 row_span/col_span)→table cells, 그림 BinData→figure+resource, 각주, \`element_path\`·char offset provenance(page/bbox null). (2) 표본 HWPX: 공공누리 문서 2~3건을 네트워크로 받아 \`samples/hwpx/\`에 두고 MANIFEST.json(출처·라이선스) 작성; 다운로드가 막히면 python-hwpx로 표·개요·각주가 있는 합성 문서를 만들어 표본으로 쓴다. (3) tests/adapters/parse/test_hwpx.py: 표본 전량 파싱, 트리 무결성, 병합 셀·heading 회귀 스냅샷. (4) 문서 04의 "확인 필요(as of 2026-09)" 중 실측으로 확인한 항목을 실측값으로 갱신(doc_updates에 목록). 예외 타입·API 이름은 실행으로 확인하고 추측하지 않는다.
${ENV}`, { label: '6d:hwpx', phase: '6D Spikes', schema: OUT, model: 'opus', effort: 'high' }),
  () => agent(`Qdrant lite 백엔드 스파이크(Opus). 읽기: ${D}04-pipelines\\13-indexing.md 의 Qdrant 어댑터·경량 프로파일 절, ADR-0012(${D}06-adr\\0012-lite-profile-qdrant-only-client-bm25.md), 바이블 §13.4(Qdrant 명명)·§6.1(point_id), contracts 생성물 \`index_record.py\`·\`query_plan.py\`, 6A의 \`sdk/hashing.py\`·\`testing/doubles/\`의 IndexBackend Protocol. 할 일: (1) \`src/rag_platform/adapters/index/qdrant/\`(backend.py, filters.py, point_id.py, bm25_sparse.py)를 qdrant-client **로컬 모드**(\`QdrantClient(":memory:")\` 또는 path)로 구현: named vectors(dense + sparse_bm25), payload 인덱스, 표준 필터 DSL → Qdrant Filter 변환(tenant_id·acl 사전 필터 필수 — 없으면 예외), \`record_id → uuid5 point_id\`, upsert/delete/search_dense/search_sparse, alias 스왑 자리. (2) bm25_sparse: 형태소 토큰(kiwipiepy가 설치되면 사용, 없으면 공백 토큰 폴백)과 BM25 TF 포화값 계산 → sparse 벡터(modifier idf는 Qdrant 설정). (3) tests/adapters/index/test_qdrant_local.py: 두 테넌트 동일 chunk_id 격리, 필터 누락 시 거부, 결정적 point_id, 재upsert 멱등. (4) 서버 모드 테스트는 \`needs_docker\`로 표시(Windows 바이너리 실행은 선택: 시간이 남으면 GitHub 릴리스 zip을 받아 1회 확인하고 결과만 기록). (5) 문서 13·ADR-0012의 "확인 필요"를 실측값으로 갱신.
${ENV}`, { label: '6d:qdrant', phase: '6D Spikes', schema: OUT, model: 'opus', effort: 'high' }),
  () => agent(`임베더 포트 스파이크(Sonnet). 읽기: ${D}04-pipelines\\12-embedding.md 의 Embedder 인터페이스 절, ADR-0009, 6A의 \`sdk/ports.py\`(Embedder Protocol)·\`testing/doubles/\`(FakeEmbedder), contracts 생성물 \`embedded_chunk_set.py\`. 할 일: (1) \`src/rag_platform/adapters/embed/\`에 \`tei_dense.py\`(TEI HTTP 어댑터: 배치·질의/문서 비대칭·L2 정규화·타임아웃·재시도, httpx)와 \`vllm_pooling_bge_m3.py\` 골격(dense+sparse 응답 파싱), \`inprocess_fake.py\`(FakeEmbedder를 어댑터·PluginMeta로 등록). **모델 다운로드 금지.** (2) HTTP는 respx/pytest-httpx로 모의 응답을 만들어 파싱·정규화·오류 분류를 단위 테스트; 실제 서버 테스트는 \`needs_model\`/\`needs_docker\` 마커 + DEFERRED. (3) embedding_space_id·차원·정규화 규약이 EmbeddedChunkSet 계약과 맞는지 테스트. (4) 문서 12의 "확인 필요" 중 코드로 확정된 규약만 갱신.
${ENV}`, { label: '6d:embedder', phase: '6D Spikes', schema: OUT, model: 'sonnet' }),
])
const [bRes, dRes] = await Promise.all([b, d])
log(`6B ${bRes.filter(Boolean).length}/3, 6D ${dRes.filter(Boolean).length}/3`)

phase('Verify')
const v = await agent(`${ROOT} 에서 \`uv run ruff check .\`, \`uv run mypy src\`, \`uv run lint-imports\`, \`uv run pytest -q\` 를 실행하고 실패를 고친다(로직 변경은 최소; 계층 위반은 임포트 방향을 고쳐 해결). 그다음 \`node tools/verify/gen-deferred-ledger.mjs\` 로 보류 원장을 재생성하고, \`node tools/verify/check-headers.mjs\`가 없으면 만들어(모든 소스 파일 첫 docstring/주석이 한국어 헤더 규칙 ${RULE}의 필수 항목 5개를 포함하는지 검사; 미준수 파일 목록 출력) 실행해 위반 파일의 헤더를 보완한다. 마지막으로 ${ROOT}\\CLAUDE.md 의 "현재 상태" 문단과 §4(저장소 구조)에서 6A 1차의 구 구조(core·stages·workflows·observability) 서술을 실제 §12 구조·현재 구현 범위(contracts 생성물, sdk·storage·plugins·profiles·orchestration/local·testing 대역, adapters 3종 스파이크, testing 키트)로 고치고, ${ROOT}\\README.md 의 상태 문구도 "6A·6B·6D 완료"로 갱신한다(사실만). 결과 요약.
${ENV}`, { label: 'verify:all', phase: 'Verify', schema: OUT, model: 'sonnet' })
return { s0: s0 ? s0.summary : null, b: bRes.filter(Boolean).map((r) => r.tests), d: dRes.filter(Boolean).map((r) => ({ tests: r.tests, docs: r.doc_updates.length, issues: r.open_issues })), verify: v ? v.summary : null }
