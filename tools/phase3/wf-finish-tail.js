
// ---------------------------------------------------------------- Finish (2026-09-23): complete Phase 3 after the previous session's workflows died
// Built into wf-phase3-finish.js by: node -e "..." (see tools/phase3/README or progress report §7.1). Uses head prompts/schemas + WAVE_B outlines.
//
// Phase 3 마감(finish) 조각 — `wf-phase3-finish.js`의 뒷부분으로, 이전 세션에서 죽은 워크플로 이후 Phase 3를
// 완결하는 잔여 문서 작성·리뷰·ADR 사이클·완결성 비평 로직을 담는다(일회성 도구, 단독 실행 대상 아님).
// 설계 근거: `docs/12-appendix/00-progress-report.md` §7.1(잔여 작업 목록), §7.3(재개 절차).
// 구성: `EXTRA`/`byPath`/`pick` — `wf-head.js`가 정의한 `WAVE_B` 개요에서 문서를 골라 마감 실행 함수에 넘기는
// 헬퍼.
// 불변식: Phase 3가 이미 완료·커밋되었으므로 이 조각은 재실행 대상이 아니다(기록 보존 목적).
// 검증 계층: 1층(여기서 검증) — 조립된 `wf-phase3-finish.js`는 Phase 3 완료 시점에 이미 실행·검증되었다.
const EXTRA = `${W('03-contracts/00-contract-overview.md')} (계약 인벤토리·공통 타입·명명 요약)`
const byPath = Object.fromEntries(WAVE_B.map((d) => [d.path, d]))
const pick = (paths) => paths.map((p) => { if (!byPath[p]) throw new Error('unknown doc ' + p); return byPath[p] })

// (A) missing documents: full write → review → fix → verify → fix2
const FULL = pick([
  '05-api/02-ingestion-api.md', '05-api/04-management-api.md', '05-api/05-mcp-server.md',
  '10-development/05-ci-cd.md', '11-roadmap/02-epics-and-backlog.md', '11-roadmap/03-risks-and-mitigations.md',
])
// (B) written but review/fix/verify incomplete (fix or verify agent killed by proxy, or reviews never ran): review → fix → verify → fix2, no rewrite
const CYCLE_API = pick(['05-api/01-api-design-guidelines.md', '05-api/03-retrieval-api.md'])
const CYCLE_REST = pick([
  '04-pipelines/02-fetching-and-source-resolution.md', '04-pipelines/03-parsing-router-and-format-detection.md', '04-pipelines/04-parser-hwpx-and-hwp.md',
  '04-pipelines/05-parser-pdf.md', '04-pipelines/06-parser-doc-and-docx.md', '04-pipelines/07-parser-html.md', '04-pipelines/08-parser-txt-md-and-others.md',
  '04-pipelines/09-normalization-and-cleaning.md', '04-pipelines/10-chunking-strategies.md', '04-pipelines/11-enrichment.md',
  '08-evaluation/02-retrieval-metrics-and-harness.md', '08-evaluation/03-golden-dataset-construction.md', '08-evaluation/04-llm-judge-and-generation-quality.md', '08-evaluation/05-benchmark-plan-and-baselines.md',
  '09-operations/01-deployment-guide.md', '09-operations/02-configuration-reference.md', '09-operations/03-observability.md', '09-operations/04-scaling-and-performance.md',
  '09-operations/05-security-and-compliance.md', '09-operations/06-runbooks.md', '09-operations/07-backup-and-disaster-recovery.md', '09-operations/08-upgrade-and-migration.md',
  '10-development/01-repository-structure.md', '10-development/02-development-environment.md', '10-development/03-coding-standards.md', '10-development/04-testing-strategy.md',
  '10-development/06-plugin-development-guide.md', '10-development/07-contributing.md', '10-development/08-release-process.md',
])

const FLIP = { type: 'object', properties: { file: { type: 'string' }, changed: { type: 'boolean' } }, required: ['file', 'changed'] }
const CYCLE_NOTE = `

주의(재개 맥락): 이 문서는 이전 세션에서 작성된 뒤 수정 또는 검증 에이전트가 네트워크 장애로 중단되었다. 부분적으로만 반영된 수정(예: 일부 절만 고쳐져 앞뒤가 다른 서술, frontmatter status가 review인 채 남음)이 있을 수 있으니 문서 내부 모순을 특히 확인한다. frontmatter status 값 자체는 finding으로 잡지 않는다(마무리 단계에서 일괄 처리).`
const ADR_NOTE = `

ADR 예외(MADR): frontmatter status는 "accepted"를 유지하고 "active"로 바꾸지 않는다. ADR에는 ## 목적/## 범위/## 결정 사항 요약/## 미해결 이슈 절을 두지 않으며(MADR 절 구조: 맥락과 문제 / 결정 동인 / 고려한 대안 / 결정 / 결과 / 준수 확인 방법 / 재검토 조건 / 참조), 그 부재를 finding으로 잡지 않는다. 결정 문장은 바이블 §3.1~3.3·관련 절과 정확히 일치해야 하며 새 결정을 만들지 않는다.`

const FAST = !!(args && args.fast)
function reviewFastP(d, note) {
  return `당신은 앵커 준수 감사자 겸 기술 리뷰어다. 한 번의 검토로 아래를 모두 확인하고, 문서를 수정하지 말고 결과만 반환한다. 불필요한 재읽기를 피하고 Grep으로 필요한 절만 읽는다.

문서: ${W(d.path)}
앵커: 브리프 ${BRIEF}(§4 확정 결정, §8 문서 맵, §9 규약), 바이블 ${BIBLE}(Grep으로 헤더 줄 번호를 얻어 공통 필수 절 [${BIBLE_COMMON}] 과 지정 절 [${d.bible || hint(d.path)}] 만 Read), depends_on: ${JSON.stringify(d.deps || [])}.
지시(outline): ${d.outline.slice(0, 2500)}

검토 항목:
1. 철자·정본: 문서의 타입명·필드명·열거값·ID 형식·엔드포인트·이벤트·오류 코드·메트릭 이름을 바이블 §5/§5.7/§6/§14와 대조. 다른 철자·임의 이름은 finding(fix에 정본 철자와 절 번호).
2. 결정 위반: 브리프 D-01~D-20·바이블 결정 레지스터와 모순, 앵커에 없는 결정의 단정, 기각된 대안(PyMuPDF·pyhwp 기본, Redis/MinIO 기본, TEI로 BGE-M3 sparse, SPLADE 기본, chunk_ulid 등) 재등장.
3. 완전성: outline 항목 중 실질 내용이 없는 것.
4. 문법: 모든 json 블록을 임시 파일로 저장해 node -e 로 파싱(실패는 blocker); Mermaid 문법(타입 선언, 노드 ID, 따옴표, subgraph end); Python/YAML 블록의 명백한 오류.
5. 내부 모순·규약: 표와 본문 불일치, frontmatter 필수 필드, 절 구조(목적/범위/결정 사항 요약/미해결 이슈/참조), 링크가 브리프 §8 문서 맵 경로인가, 이모지·근거 없는 수치, 분량(${d.len || '350~900'}행).
계약·ID·결정·필수 필드·문법 오류는 major/blocker, 표현은 minor. 문제 없으면 findings 빈 배열 + accept. 리뷰 시간이 제한되어 있으므로 심각한 문제를 우선 찾고 minor는 5개 이내로 제한한다.${note}`
}

async function flipStatus(d, ph) {
  return agent(`파일 ${W(d.path)} 의 frontmatter만 수정한다: status를 "active"로, last_updated를 ${DATE} 로. 본문은 한 글자도 바꾸지 않는다(Edit 도구로 해당 두 줄만). 이미 active면 last_updated만 확인한다. 결과 반환(changed=실제 변경 여부).`, { label: `finalize:${d.path}`, phase: ph, schema: FLIP, effort: 'low' })
}

// review → fix → verify → fix2 (mirrors processDoc without the write stage)
async function cycleDoc(d, extraReads, ph, isAdr) {
  const note = isAdr ? ADR_NOTE : CYCLE_NOTE
  if (FAST) {
    const r = await agent(reviewFastP(d, note), { label: `review:${d.path}`, phase: ph, schema: REVIEW, effort: 'medium' })
    if (!r) { log(`${d.path}: 리뷰 에이전트 실패`); return { file: W(d.path), review: 'review_failed', serious: null } }
    const fs1 = (r.findings || []).map((f) => ({ ...f, lens: 'combined' }))
    if (r.verdict === 'rewrite') fs1.unshift({ severity: 'blocker', location: '(전체)', problem: '리뷰어 verdict=rewrite', fix: '문서를 지시와 앵커에 맞게 다시 작성', lens: 'review' })
    const ser = fs1.filter((f) => f.severity !== 'minor')
    if (!fs1.length) { log(`${d.path}: 리뷰 통과(이슈 0)`); if (!isAdr) await flipStatus(d, ph); return { file: W(d.path), review: 'pass', serious: 0 } }
    log(`${d.path}: 리뷰 이슈 ${fs1.length}개(심각 ${ser.length}) → 수정(경량: 검증 생략)`)
    const fx = await agent(fixP(d, fs1, extraReads, 1) + note + '\n\n경량 모드: 별도 검증 단계가 없으므로 수정 후 스스로 각 blocker/major 항목이 해결되었는지 파일을 다시 읽어 확인하고, 확인 결과를 summary에 항목별로 적는다.', { label: `fix:${d.path}`, phase: ph, schema: DONE })
    if (!fx) { log(`${d.path}: 수정 에이전트 실패`); return { file: W(d.path), review: 'fix_failed', serious: ser.length } }
    return { ...fx, review: ser.length ? 'fixed_unverified' : 'minor_fixed', serious: ser.length }
  }
  const [ra, rb] = await parallel([
    () => agent(reviewAnchorP(d) + note, { label: `review-anchor:${d.path}`, phase: ph, schema: REVIEW }),
    () => agent(reviewTechP(d) + note, { label: `review-tech:${d.path}`, phase: ph, schema: REVIEW }),
  ])
  if (!ra && !rb) { log(`${d.path}: 리뷰 에이전트 모두 실패`); return { file: W(d.path), review: 'review_failed', serious: null } }
  const findings = [
    ...((ra && ra.findings) || []).map((f) => ({ ...f, lens: 'anchor' })),
    ...((rb && rb.findings) || []).map((f) => ({ ...f, lens: 'tech' })),
  ]
  const verdicts = [ra && ra.verdict, rb && rb.verdict].filter(Boolean)
  if (verdicts.includes('rewrite')) findings.unshift({ severity: 'blocker', location: '(전체)', problem: '리뷰어 verdict=rewrite', fix: '문서를 지시와 앵커에 맞게 다시 작성', lens: 'review' })
  const serious = findings.filter((f) => f.severity !== 'minor')
  if (!findings.length) {
    log(`${d.path}: 리뷰 통과(이슈 0)`)
    if (!isAdr) await flipStatus(d, ph)
    return { file: W(d.path), review: 'pass', serious: 0 }
  }
  log(`${d.path}: 리뷰 이슈 ${findings.length}개(심각 ${serious.length}) → 수정`)
  const fx = await agent(fixP(d, findings, extraReads, 1) + note, { label: `fix:${d.path}`, phase: ph, schema: DONE })
  if (!fx) { log(`${d.path}: 수정 에이전트 실패`); return { file: W(d.path), review: 'fix_failed', serious: serious.length } }
  if (!serious.length) return { ...fx, review: 'minor_fixed', serious: 0 }
  const v = await agent(verifyP(d, serious) + note, { label: `verify:${d.path}`, phase: ph, schema: VERIFY })
  if (!v) return { ...fx, review: 'verify_failed', serious: serious.length }
  if (v.verdict === 'pass') { log(`${d.path}: 검증 통과(해결 ${v.resolved.length})`); return { ...fx, review: 'verified', serious: serious.length } }
  const round2 = [...v.unresolved.map((f) => ({ ...f, lens: 'verify:unresolved' })), ...v.new_issues.map((f) => ({ ...f, lens: 'verify:new' }))]
  log(`${d.path}: 검증 실패(미해결 ${v.unresolved.length}, 신규 ${v.new_issues.length}) → 2차 수정`)
  const fx2 = await agent(fixP(d, round2, extraReads, 2) + note, { label: `fix2:${d.path}`, phase: ph, schema: DONE })
  return { ...(fx2 || fx), review: fx2 ? 'fixed_twice' : 'fix2_failed', serious: serious.length, residual: round2.length }
}
async function cycle(docs, extraReads, ph, isAdr) {
  const out = await parallel(docs.map((d) => () => cycleDoc(d, extraReads, ph, isAdr)))
  const dropped = docs.filter((d, i) => !out[i]).map((d) => d.path)
  if (dropped.length) log(`${ph}: 드롭된 문서 ${dropped.length}개 — ${dropped.join(', ')}`)
  return { out, dropped }
}

// (C) ADRs: all 38 were written; only 13 got reviews and none got fixes → review cycle for all, then index
async function runAdrCycle() {
  phase('ADRs')
  const ADR_LIST = { type: 'object', properties: { adrs: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, slug: { type: 'string' }, title: { type: 'string' }, priority: { type: 'string' },
    decision_summary: { type: 'string' }, related: { type: 'array', items: { type: 'string' } }, bible_sections: { type: 'array', items: { type: 'string' } },
  }, required: ['id', 'slug', 'title', 'priority', 'decision_summary', 'related', 'bible_sections'] } } }, required: ['adrs'] }
  const adrList = await agent(`설계 바이블 ${BIBLE} 의 §3.3 "ADR 목록" 표(번호 | 제목 | slug | 우선 | 관련 결정)를 Grep으로 찾아 읽고 38건을 **그대로**(번호·제목·slug·우선순위·관련 결정 철자 변경 없이) 반환한다. 각 ADR에 대해 §3.1(D-xx)·§3.2(O-xx) 표의 해당 행과 관련 절(예: ADR-0004 → §6.1~6.2, ADR-0026 → §11.4)을 찾아 decision_summary(바이블 문장 기반 3~6문장, 기각 대안 포함)와 bible_sections(절 번호 목록)를 채운다. 브리프 ${BRIEF} §4·§5의 해당 결정 행도 참고한다.`, { label: 'adr:list', phase: 'ADRs', schema: ADR_LIST })
  const ADRS = ((adrList && adrList.adrs) || []).map((a) => ({
    path: `06-adr/${a.id}-${a.slug.replace(/^\d+-/, '')}.md`, title: `ADR-${a.id}: ${a.title}`, len: '90~240',
    deps: ['02-architecture/00-design-bible.md', '07-tech-landscape/00-summary-and-selection-matrix.md'],
    bible: `§3.3 표의 ${a.id} 행, §3.1~3.2의 관련 결정(${(a.related || []).join(', ')}) 행, ${(a.bible_sections || []).join(', ')}`,
    outline: `MADR 형식. frontmatter(title: "ADR-${a.id}: ${a.title}", status: accepted, date, deciders: architecture, priority: ${a.priority}, related: ${JSON.stringify(a.related || [])}, depends_on, version) → # ADR-${a.id}: ${a.title} → ## 맥락과 문제 → ## 결정 동인(decision drivers) → ## 고려한 대안(각 대안: 설명·장점·단점 — docs/07-tech-landscape 근거 인용; 바이블이 기각한 대안을 반드시 포함) → ## 결정(\`**결정:**\`으로 시작; 바이블 문장과 정확히 일치) → ## 결과(긍정/부정/중립) → ## 준수 확인 방법(어떤 CI 게이트·스키마 제약·코드 리뷰 항목으로 강제하는가) → ## 재검토 조건 → ## 참조(바이블 절 번호, 브리프 D/O-xx, 기술 지형 문서, 관련 ADR). 바이블 결정 요약: ${a.decision_summary}. 바이블·선정 매트릭스와 정확히 일치해야 하며 새 결정을 만들지 않는다.`,
  }))
  log(`ADR 리뷰 사이클 ${ADRS.length}건`)
  if (ADRS.length !== 38) log(`경고: ADR 수가 38이 아니다(${ADRS.length})`)
  const res = ADRS.length ? await cycle(ADRS, null, 'ADRs', true) : { out: [], dropped: [] }
  const idx = await agent(`${D}06-adr\\ 의 모든 ADR 파일(frontmatter와 ## 결정 절)을 읽고 인덱스 ${D}06-adr\\README.md 를 작성한다: frontmatter(title: ADR 인덱스, status: active, owner: architecture, version: 0.1.0, last_updated: ${DATE}, depends_on: ["../02-architecture/00-design-bible.md"]), MADR 소개와 작성 규칙(바이블 §1.2 변경 절차와의 관계), 상태 정의(proposed/accepted/deprecated/superseded), 표(ID | 제목 | 상태 | 우선 | 관련 결정(D/O-xx) | 요약 한 줄 | 링크), 주제별 그룹(라이선스·의존성 / 파싱·문서 모델 / 청킹·보강 / 임베딩·인덱스 / 검색·패킹 / 오케스트레이션·원장 / 보안·테넌시 / 계약·명명 / 운영·관측·평가 / API·MCP), P0 ADR 우선 읽기 안내, 새 ADR 절차. 한국어. 파일 목록이 바이블 §3.3 38건과 일치하는지 확인하고 누락이 있으면 summary에 적는다. Write 후 결과 반환.`, { label: 'adr:index', phase: 'ADRs', schema: DONE })
  return { ...summarize(res, ADRS), index: idx ? idx.file : null, count: ADRS.length }
}

// (D) OpenAPI + (E) completeness critic — verbatim from wf-tail.js
async function runOpenapi() {
  phase('OpenAPI')
  const oa = await agent(`당신은 API 스펙 작성자다. ${D}05-api\\01-api-design-guidelines.md, 02-ingestion-api.md, 03-retrieval-api.md, 04-management-api.md, 07-webhooks-and-events.md 와 설계 바이블 ${BIBLE} §14(API 표면 정본 — Grep으로 위치를 찾아 그 절만 읽는다)·§5.1·§6.7, 그리고 ${SCHEMAS} 의 스키마 파일 목록($id·title)을 읽고 ${D}05-api\\openapi.yaml 을 작성한다.
요구: OpenAPI 3.1.0; info(title: RAG Platform API, version: 0.1.0, license Apache-2.0, description 한국어); servers; securitySchemes(bearer JWT(OIDC), apiKey 헤더, mTLS 언급); tags; 바이블 §14의 **모든** 엔드포인트(경로·메서드 철자 그대로; 문서와 바이블이 다르면 바이블) — 요청/응답 스키마는 components.schemas 에 계약 타입을 두되 가능한 한 schemas/ 파일을 상대 경로 $ref 로 참조('../../schemas/context-pack.schema.json' 형식; 열거·공용 타입은 '../../schemas/common-types.schema.json#/$defs/<Type>'); 오류 응답은 application/problem+json + problem-details 스키마 $ref; 공통 파라미터 재사용(cursor·limit·Idempotency-Key·traceparent, RateLimit·Deprecation·Sunset 응답 헤더); operationId 규약 {domain}_{action}(snake_case); 각 주요 엔드포인트에 요청·응답 example 1개(계약 문서의 예시와 정합); SSE 엔드포인트는 text/event-stream; 사이드카 /v1/convert 는 별도 태그와 servers 오버라이드. YAML 문법을 신중히(들여쓰기 2칸, 콜론 뒤 공백, 따옴표가 필요한 값 — '*', ':', '#' 포함 문자열, 경로 키는 따옴표). 작성 후 결과 반환(file=openapi.yaml 경로, defined=operationId 전체 목록, lines=줄 수).`, { label: 'openapi:assemble', phase: 'OpenAPI', schema: DONE })
  const rv = await agent(`당신은 OpenAPI 리뷰어다. ${D}05-api\\openapi.yaml 을 읽고 검토한다. 문서를 수정하지 않는다.
검토: (1) YAML 문법 — 들여쓰기 일관성, 따옴표 짝, 콜론 뒤 공백, 중복 키, 탭 문자; 의심스러운 줄은 줄 번호와 함께 (2) 바이블 ${BIBLE} §14 표(Grep으로 찾아 읽기)의 모든 경로·메서드가 있는가, 철자가 같은가, 표에 없는 경로가 있는가 (3) 모든 $ref 대상(components 내부, ../../schemas/*.schema.json, #/$defs/...)이 실제로 존재하는가 — 파일 존재와 $defs 키를 확인 (4) operationId 유일성·규약 (5) 오류 응답이 problem+json인가, 202 비동기 패턴(Location/status_url)·Idempotency-Key 헤더 (6) 예시가 계약 문서 예시와 필드 철자에서 일치하는가 (7) 3.1 규격 위반(nullable 대신 type 배열, exclusiveMinimum 불리언 등). 발견마다 finding.`, { label: 'openapi:review', phase: 'OpenAPI', schema: REVIEW })
  let fx = null
  if (rv && rv.findings.length) {
    log(`OpenAPI 리뷰 이슈 ${rv.findings.length}개 → 수정`)
    fx = await agent(`OpenAPI 리뷰 결과를 반영해 ${D}05-api\\openapi.yaml 을 수정한다. 리뷰: ${JSON.stringify(rv.findings, null, 1).slice(0, 20000)}. blocker/major는 모두, minor는 합리적인 것만. 바이블 §14가 정본. 수정 후 파일 전체를 다시 읽어 YAML 들여쓰기·따옴표를 재점검한다. 결과 반환.`, { label: 'openapi:fix', phase: 'OpenAPI', schema: DONE })
  }
  return { openapi: oa ? oa.file : null, operations: oa ? oa.defined.length : 0, reviewFindings: rv ? rv.findings.length : null, fixed: !!fx }
}
async function runCritic() {
  phase('Completeness Critic')
  const GAPS = { type: 'object', properties: { file: { type: 'string' }, gaps: { type: 'array', items: { type: 'object', properties: {
    area: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, description: { type: 'string' }, suggested_doc: { type: 'string' } }, required: ['area', 'severity', 'description', 'suggested_doc'] } },
    stats: { type: 'object', properties: { docs: { type: 'integer' }, schemas: { type: 'integer' }, adrs: { type: 'integer' } }, required: ['docs', 'schemas', 'adrs'] } }, required: ['file', 'gaps', 'stats'] }
  const c = await agent(`당신은 완전성 비평가다. 문서 세트 전체의 **누락**을 찾는다(문서 내부 품질은 이미 리뷰됨). 절차:
1. ${D} 아래 디렉터리별 파일 목록과 ${SCHEMAS} 파일 목록을 얻는다(브리프 ${BRIEF} §8 문서 맵과 대조: 없는 문서, 맵에 없는 문서).
2. 설계 바이블 ${BIBLE} 의 헤더 목록(§2~§14)을 얻고, 각 절이 "상세화된 하위 문서"를 갖는지 확인한다: 절마다 Grep으로 핵심 타입명·규칙 이름(예: litm_alternating, security_context_hash, TieringPolicy, hydrate, RAG-Signature, usage_ledger, ChunkTextStore, 17개 강제 지점 E1~E17, 프로파일 4종, 이벤트 이름 전부, 오류 코드 전부, 메트릭 정본 목록)을 docs/ 전체에서 검색하여 어떤 문서에도 등장하지 않는 항목을 누락으로 기록한다.
3. 브리프 R1~R6·D-01~D-20·품질 목표 §7, 요구사항 문서(01-requirements/01·02)의 FR/NFR ID 중 어떤 설계 문서에서도 인용되지 않은 것을 표본 검사(Grep으로 'FR-', 'NFR-' 접두 목록 대비)한다.
4. 바이블 §5.1 스키마 파일 34개가 모두 schemas/ 에 있는지, ADR 38개가 모두 있는지, frontmatter status가 review/draft로 남은 문서가 있는지(파일별 목록).
5. 결과를 ${D}12-appendix\\01-phase3-completeness-review.md 로 작성한다(frontmatter title: 3단계 완전성 검토, status: active, owner: architecture, version: 0.1.0, last_updated: ${DATE}, depends_on; 절: 목적 / 범위 / 방법 / 통계 표 / 누락 목록 표(영역 | 심각도 | 설명 | 반영할 문서) / 4단계(교차 일관성)로 넘길 항목 / 결정 사항 요약 / 미해결 이슈 / 참조). 한국어. 수정은 하지 않는다.`, { label: 'critic:completeness', phase: 'Completeness Critic', schema: GAPS })
  return c
}

// ---------------------------------------------------------------- orchestration: A ∥ B ∥ C → (A_api + B_api done) → D → (all) → E
phase('Finish: write missing')
log(`누락 문서 작성 ${FULL.length}건, 리뷰 사이클 ${CYCLE_API.length + CYCLE_REST.length}건${(args && args.adrs === false) ? "" : ", ADR 38건 리뷰"} → OpenAPI → 완전성 비평`)
async function produceFast(docs, extraReads, ph) {
  const out = await parallel(docs.map((d) => () => (async () => {
    const w = await agent(writeP(d, extraReads), { label: `write:${d.path}`, phase: ph, schema: DONE })
    if (!w) { log(`${d.path}: 작성 실패(드롭)`); return null }
    const c = await cycleDoc(d, extraReads, ph, false)
    return { ...w, ...(c || {}), lines: (c && c.lines) || w.lines }
  })()))
  const dropped = docs.filter((d, i) => !out[i]).map((d) => d.path)
  if (dropped.length) log(`${ph}: 드롭된 문서 ${dropped.length}개 — ${dropped.join(', ')}`)
  return { out, dropped }
}
const pFull = FAST ? produceFast(FULL, EXTRA, 'Finish: write missing') : produce(FULL, EXTRA, 'Finish: write missing')
log(FAST ? '경량 모드: 문서당 리뷰어 1명(effort medium), 검증·2차 수정 생략' : '표준 모드: 리뷰어 2명 → 수정 → 검증 → 2차 수정')
const pApi = cycle(CYCLE_API, EXTRA, 'Finish: review cycle', false)
const pRest = cycle(CYCLE_REST, EXTRA, 'Finish: review cycle', false)
const SKIP_ADRS = !!(args && args.adrs === false)
if (SKIP_ADRS) log("ADR 리뷰 사이클 생략(args.adrs=false)")
const pAdr = SKIP_ADRS ? Promise.resolve(null) : runAdrCycle()
const full = await pFull
const apiC = await pApi
log('API 문서 완료 → OpenAPI 조립')
const oa = await runOpenapi()
const restC = await pRest
const adr = await pAdr
log('전 그룹 완료 → 완전성 비평')
const critic = await runCritic()
return {
  date: DATE,
  full: summarize(full, FULL), cycleApi: summarize(apiC, CYCLE_API), cycleRest: summarize(restC, CYCLE_REST),
  adrs: adr, openapi: oa, critic: critic ? { file: critic.file, gaps: critic.gaps.length, stats: critic.stats } : null,
}
