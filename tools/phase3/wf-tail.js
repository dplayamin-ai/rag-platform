
// ---------------------------------------------------------------- ADRs
async function runAdrs() {
  phase('ADRs')
  const ADR_LIST = { type: 'object', properties: { adrs: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, slug: { type: 'string' }, title: { type: 'string' }, priority: { type: 'string' },
    decision_summary: { type: 'string' }, related: { type: 'array', items: { type: 'string' } }, bible_sections: { type: 'array', items: { type: 'string' } },
  }, required: ['id', 'slug', 'title', 'priority', 'decision_summary', 'related', 'bible_sections'] } } }, required: ['adrs'] }
  const adrList = await agent(`설계 바이블 ${BIBLE} 의 §3.3 "ADR 목록" 표(번호 | 제목 | slug | 우선 | 관련 결정)를 Grep으로 찾아 읽고 38건을 **그대로**(번호·제목·slug·우선순위·관련 결정 철자 변경 없이) 반환한다. 각 ADR에 대해 §3.1(D-xx)·§3.2(O-xx) 표의 해당 행과 관련 절(예: ADR-0004 → §6.1~6.2, ADR-0026 → §11.4)을 찾아 decision_summary(바이블 문장 기반 3~6문장, 기각 대안 포함)와 bible_sections(절 번호 목록)를 채운다. 브리프 ${BRIEF} §4·§5의 해당 결정 행도 참고한다.`, { label: 'adr:list', phase: 'ADRs', schema: ADR_LIST })
  const ADRS = ((adrList && adrList.adrs) || []).map((a) => ({
    path: `06-adr/${a.id}-${a.slug.replace(/^\d+-/, '')}.md`, title: `ADR-${a.id}: ${a.title}`, len: '90~220',
    deps: ['02-architecture/00-design-bible.md', '07-tech-landscape/00-summary-and-selection-matrix.md'],
    bible: `§3.3 표의 ${a.id} 행, §3.1~3.2의 관련 결정(${(a.related || []).join(', ')}) 행, ${(a.bible_sections || []).join(', ')}`,
    outline: `MADR 형식. frontmatter(title: "ADR-${a.id}: ${a.title}", status: accepted, date: ${DATE}, deciders: architecture, priority: ${a.priority}, related: ${JSON.stringify(a.related || [])}, depends_on) → # ADR-${a.id}: ${a.title} → ## 맥락과 문제 → ## 결정 동인(decision drivers) → ## 고려한 대안(각 대안: 설명·장점·단점 — docs/07-tech-landscape 근거 인용; 바이블이 기각한 대안을 반드시 포함) → ## 결정(\`**결정:**\`으로 시작; 바이블 문장과 정확히 일치) → ## 결과(긍정/부정/중립) → ## 준수 확인 방법(어떤 CI 게이트·스키마 제약·코드 리뷰 항목으로 강제하는가) → ## 재검토 조건 → ## 참조(바이블 절 번호, 브리프 D/O-xx, 기술 지형 문서, 관련 ADR). 바이블 결정 요약: ${a.decision_summary}. 바이블·선정 매트릭스와 정확히 일치해야 하며 새 결정을 만들지 않는다. ADR 문서에는 ## 목적/## 범위/## 결정 사항 요약/## 미해결 이슈 절을 두지 않는다(MADR 구조가 우선).`,
  }))
  log(`ADR ${ADRS.length}개 작성(바이블 §3.3)`)
  if (ADRS.length !== 38) log(`경고: ADR 수가 38이 아니다(${ADRS.length}) — 결과 확인 필요`)
  const res = ADRS.length ? await produce(ADRS, null, 'ADRs') : { out: [], dropped: [] }
  const idx = await agent(`${D}06-adr\\ 의 모든 ADR 파일(frontmatter와 ## 결정 절)을 읽고 인덱스 ${D}06-adr\\README.md 를 작성한다: frontmatter(title: ADR 인덱스, status: active, owner: architecture, version: 0.1.0, last_updated: ${DATE}, depends_on: ["../02-architecture/00-design-bible.md"]), MADR 소개와 작성 규칙(바이블 §1.2 변경 절차와의 관계), 상태 정의(proposed/accepted/deprecated/superseded), 표(ID | 제목 | 상태 | 우선 | 관련 결정(D/O-xx) | 요약 한 줄 | 링크), 주제별 그룹(라이선스·의존성 / 파싱·문서 모델 / 청킹·보강 / 임베딩·인덱스 / 검색·패킹 / 오케스트레이션·원장 / 보안·테넌시 / 계약·명명 / 운영·관측·평가 / API·MCP), P0 ADR 우선 읽기 안내, 새 ADR 절차. 한국어. 파일 목록이 바이블 §3.3 38건과 일치하는지 확인하고 누락이 있으면 summary에 적는다. Write 후 결과 반환.`, { label: 'adr:index', phase: 'ADRs', schema: DONE })
  return { ...summarize(res, ADRS), index: idx ? idx.file : null, count: ADRS.length }
}

// ---------------------------------------------------------------- contract audit (barrier justified: needs all contracts + schemas)
async function runValidator(tag) {
  return agent(`당신은 계약 정합성 수리자다. 기계 검증기를 실행하고 보고된 오류를 모두 고친다.
1. 실행: node "${VALIDATOR}" --root "${ROOT}" --json "${ROOT}\\schemas\\.validate-report.json"  (표준 출력에 ERROR/WARN/INFO 행이 나온다. 종료 코드 1 = 오류 있음.)
2. ERROR 전부를 고친다: JSON 파싱 실패(schemas/*.json, 03-contracts 문서 내 json 블록), $id/$schema/파일명 규약, 해결되지 않는 $ref, 열거 $defs 값이 바이블 §5.7 과 불일치(바이블이 정본 — 바이블 표를 Grep으로 찾아 읽고 스키마 값을 맞춘다), 문서 내 스키마 블록 ≠ 저장 파일(저장 파일을 정본으로 문서 블록을 갱신하거나 반대로 — 더 완전한 쪽), 예시가 스키마에 위배(필수 필드·열거·패턴 — 예시를 고치되 스키마가 바이블과 다르면 스키마를 고친다), 필수 절 누락, 이모지.
3. WARN 중 "additionalProperties 정책 미명시", "schema_version 누락", "링크 대상 미존재(문서 맵 경로가 맞으면 무시)", "common-types 참조 형식", "스키마 파일 누락"(해당 소유 문서의 스키마를 새로 만들어야 하면 그 문서 절을 읽고 최소 완전 스키마를 작성)은 가능한 한 고친다.
4. 다시 실행해 ERROR 0이 될 때까지 반복(최대 5회). 수정한 파일마다 대응 문서 블록·Pydantic·예시도 함께 일치시킨다. 다른 문서(03-contracts, schemas 외)는 수정하지 않는다.
5. 마지막 실행 결과의 오류/경고 수와 남은 문제를 반환한다(errors_before는 첫 실행 값).`, { label: `contracts:validator:${tag}`, phase: 'Contract Audit', schema: TOOLRUN })
}
async function runContractAudit() {
  phase('Contract Audit')
  const v1 = await runValidator('pre')
  log(`기계 검증 1차: 오류 ${v1 ? v1.errors_before : '?'} → ${v1 ? v1.errors_after : '?'} (경고 ${v1 ? v1.warnings_after : '?'})`)
  const scopes = [
    { key: 'ingest-chain', files: ['00-contract-overview', '01-ingest-request', '02-source-document', '03-parsed-document', '04-normalized-document', '05-chunk-set', '06-enriched-chunk-set', '07-embedded-chunk-set-and-index-record', '08-index-commit'], focus: '수집 체인: 봉투·lineage_refs 전파, block_id/chunk_id/record_id 결합식, Block↔BlockRef↔Chunk 오프셋 기준(§6.3), 3-텍스트 규칙, ItemKind/level, 보안 삼중항(tenant_id·acl_*·is_current), provenance 체인 SourceDocument→ParsedDocument→ChunkSet→IndexRecord' },
    { key: 'query-chain', files: ['00-contract-overview', '07-embedded-chunk-set-and-index-record', '09-query-request-and-query-plan', '10-candidate-set-and-ranked-set', '11-context-pack'], focus: '질의 체인: SecurityContext 주입·필터 3층·effective_hash, variant_id/channel_run_id, 점수 원장(ChannelScore·ScoreBreakdown·Σcontribution), hydrate 조건 필수 필드, RankedResult→ContextItem 필드 승계, cite_id·citation_map, Renderer 열거, provenance 체인 IndexRecord→RankedSet→ContextPack' },
    { key: 'ops-common', files: ['00-contract-overview', '12-jobs-events-and-status', '13-error-model', '14-schema-versioning-and-compatibility', '15-collection-profile-and-policy-contracts', '16-eval-feedback-and-sidecar-contracts'], focus: '운영 계약: JobState/JobKind·CommitStatus 상태 기계 일치(08과 12), 이벤트 카탈로그·오류 코드 철자(§5.7), StageError↔ProblemDetails 변환, Profile↔CollectionSpec↔PluginMeta↔Capabilities 해시·검증 규칙(§7.4), StagePolicy↔§4.4, EvalRun↔IndexCommit 참조, UserDictEntry↔analyzer_id/dictionary_hash, ConvertRequest↔ParsedDocument 파서 경로' },
  ]
  const audits = await parallel(scopes.map((s) => () => agent(`당신은 계약 일관성 감사자(${s.key})다. 다음 문서들과 그들이 소유한 schemas/*.schema.json, 그리고 schemas/common-types.schema.json, 설계 바이블 ${BIBLE} 의 §5.1~5.3, §5.7, §6 및 해당 타입 표(#### \`TypeName\`)를 읽는다.
대상 문서(${D}03-contracts\\): ${s.files.map((f) => f + '.md').join(', ')}
초점: ${s.focus}
검사: (1) 같은 개념의 필드명·타입·필수 여부·열거값이 문서 간/문서-스키마-Pydantic-예시 간 다르게 쓰인 곳 (2) 참조 무결성(문서 A가 참조한 타입·필드·절이 B에 실제 정의) (3) 봉투·공용 타입 $ref 사용 일관성(재정의 금지) (4) 바이블 표와의 일치(필드 누락·철자·필수) (5) 보안 필드·ACL·tenant 스코프가 모든 관련 계약에 있는가(D-09) (6) provenance/오프셋 기준의 연속성 (7) 불변식 간 모순 (8) 한계 수치(§5.1)의 일치.
서로 다르면 바이블 > 계약 개요(00) > 상류 계약(생산자) 순으로 정본을 정하고 canonical_decisions에 바이블 절 번호와 함께 적는다. 수정하지 말고 파일별(문서 또는 스키마 경로) 이슈 목록을 반환한다. checked_pairs에 실제 대조한 쌍을 적는다.`, { label: `contracts:audit:${s.key}`, phase: 'Contract Audit', schema: CONS })))
  const issues = audits.filter(Boolean).flatMap((a) => a.issues)
  const canon = [...new Set(audits.filter(Boolean).flatMap((a) => a.canonical_decisions))]
  const byFile = {}
  for (const i of issues) { const k = i.file.replace(/\\/g, '/').replace(/^.*\/(docs|schemas)\//, '$1/'); (byFile[k] = byFile[k] || []).push(i) }
  const files = Object.keys(byFile)
  log(`의미 감사 이슈 ${issues.length}개, 파일 ${files.length}개, 정본 결정 ${canon.length}개`)
  await parallel(files.map((f) => () => agent(`계약 일관성 감사 결과를 반영해 파일을 수정한다.
대상 파일(경로가 상대면 ${ROOT}\\ 기준): ${f}
정본 결정(반드시 따른다; 바이블 절 번호를 확인한다): ${JSON.stringify(canon, null, 1).slice(0, 12000)}
이 파일의 이슈: ${JSON.stringify(byFile[f], null, 1).slice(0, 16000)}
문서를 고치면 그 문서가 소유한 schemas/*.schema.json, 문서 내 스키마 블록, Pydantic 코드 블록, JSON 예시를 모두 함께 고쳐 일치시킨다. 스키마 파일을 고치면 소유 문서의 스키마 블록도 같게 한다. schemas/common-types.schema.json 은 이슈가 그 파일을 직접 지목했을 때만 수정한다. 다른 파일은 수정하지 않는다. JSON은 node -e 로 파싱 검증. 완료 후 무엇을 바꿨는지 요약 반환.`, { label: `contracts:fix:${f.split(/[\\/]/).pop()}`, phase: 'Contract Audit' })))
  const v2 = await runValidator('post')
  log(`기계 검증 2차: 오류 ${v2 ? v2.errors_before : '?'} → ${v2 ? v2.errors_after : '?'} (경고 ${v2 ? v2.warnings_after : '?'})`)
  return { validatorPre: v1, semanticIssues: issues.length, filesFixed: files, canonicalDecisions: canon, validatorPost: v2 }
}

// ---------------------------------------------------------------- OpenAPI + critic
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
4. 바이블 §5.1 스키마 파일 34개가 모두 schemas/ 에 있는지, ADR 38개가 모두 있는지.
5. 결과를 ${D}12-appendix\\01-phase3-completeness-review.md 로 작성한다(frontmatter title: 3단계 완전성 검토, status: active, owner: architecture, version: 0.1.0, last_updated: ${DATE}, depends_on; 절: 목적 / 범위 / 방법 / 통계 표 / 누락 목록 표(영역 | 심각도 | 설명 | 반영할 문서) / 4단계(교차 일관성)로 넘길 항목 / 결정 사항 요약 / 미해결 이슈 / 참조). 한국어. 수정은 하지 않는다.`, { label: 'critic:completeness', phase: 'Completeness Critic', schema: GAPS })
  return c
}

// ---------------------------------------------------------------- dispatch
const RESULT = { group: GROUP, date: DATE }
if (GROUP === 'contracts') {
  phase('Contracts T0')
  log(`계약 T0: ${CONTRACTS_T0.length}개(공용 스키마·에러·버전)`)
  const t0 = await produce(CONTRACTS_T0, null, 'Contracts T0')
  RESULT.t0 = summarize(t0, CONTRACTS_T0)
  phase('Contracts T1')
  log(`계약 T1: ${CONTRACTS_T1.length}개`)
  const t1 = await produce(CONTRACTS_T1, `${W('03-contracts/00-contract-overview.md')} (공통 봉투·공용 타입·common-types $defs 키 목록), ${W('03-contracts/13-error-model.md')} (오류 코드)`, 'Contracts T1')
  RESULT.t1 = summarize(t1, CONTRACTS_T1)
} else if (GROUP === 'architecture') {
  phase('Architecture')
  log(`아키텍처: ${ARCH.length}개`)
  RESULT.architecture = summarize(await produce(ARCH, null, 'Architecture'), ARCH)
} else if (GROUP === 'adrs') {
  RESULT.adrs = await runAdrs()
} else if (GROUP === 'contracts-audit') {
  RESULT.audit = await runContractAudit()
} else if (GROUP === 'pipelines' || GROUP === 'api-eval' || GROUP === 'ops-dev-roadmap') {
  const sel = GROUP === 'pipelines' ? ['04-pipelines/'] : GROUP === 'api-eval' ? ['05-api/', '08-evaluation/'] : ['09-operations/', '10-development/', '11-roadmap/']
  const ph = GROUP === 'pipelines' ? 'Pipelines' : GROUP === 'api-eval' ? 'API & Evaluation' : 'Ops, Dev, Roadmap'
  const docs = WAVE_B.filter((d) => sel.some((p) => d.path.startsWith(p)))
  const T0_PATHS = ['04-pipelines/01-pipeline-framework.md', '05-api/01-api-design-guidelines.md', '08-evaluation/01-evaluation-strategy.md', '09-operations/01-deployment-guide.md', '10-development/01-repository-structure.md', '11-roadmap/01-milestones.md']
  const t0 = docs.filter((d) => T0_PATHS.includes(d.path)), t1 = docs.filter((d) => !T0_PATHS.includes(d.path))
  const extra = `${W('03-contracts/00-contract-overview.md')} (계약 인벤토리·공통 타입·명명 요약)`
  phase(ph)
  log(`${ph}: 기반 문서 ${t0.length}개 → 나머지 ${t1.length}개`)
  const r0 = await produce(t0, extra, ph)
  const r1 = await produce(t1, extra, ph)
  RESULT.waveB = { tier0: summarize(r0, t0), tier1: summarize(r1, t1) }
} else if (GROUP === 'openapi') {
  RESULT.openapi = await runOpenapi()
} else if (GROUP === 'critic') {
  RESULT.critic = await runCritic()
} else {
  throw new Error(`unknown group: ${GROUP}`)
}
return RESULT
