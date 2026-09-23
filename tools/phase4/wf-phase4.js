export const meta = {
  name: 'rag-phase4-cross-consistency',
  description: 'Phase 4: Opus triage of bible amendment requests → bible/brief revision + propagation directives → Sonnet propagation (grouped), oversize trimming, sampled verification of fast-mode fixes, residual cleanup',
  phases: [
    { title: 'T1 Triage', detail: 'Opus: classify 200 bible-related requests + completeness items' },
    { title: 'T2 Bible Revision', detail: 'Opus: apply accepted amendments, write propagation directives' },
    { title: 'T3 Schema Sync', detail: 'Sonnet: schemas/contracts follow bible; validator 0 errors' },
    { title: 'P1 Propagate', detail: 'Sonnet: grouped docs apply directives' },
    { title: 'P2 Trim', detail: 'Sonnet: 900-line rule by section relocation' },
    { title: 'P3 Sample Verify', detail: 'Sonnet: verify fast-mode fixes on 14 docs' },
    { title: 'P4 Residual', detail: 'Sonnet: rerun validator/audit and fix leftovers' },
  ],
}

const ROOT = 'C:\\Workspaces\\rag-platform'
const D = ROOT + '\\docs\\'
const BRIEF = D + '00-vision\\00-design-brief.md'
const BIBLE = D + '02-architecture\\00-design-bible.md'
const PLAN = D + '12-appendix\\02-phase4-5-plan.md'
const TRIAGE_IN = D + '12-appendix\\03-bible-amendment-triage-input.md'
const CRITIC = D + '12-appendix\\01-phase3-completeness-review.md'
const TRACE = D + '12-appendix\\06-traceability-matrix.md'
const TRIAGE_OUT = D + '12-appendix\\07-bible-amendment-triage-decisions.md'
const DIRECTIVES = D + '12-appendix\\08-propagation-directives.md'
const AUDIT_MD = (args && args.audit) || (ROOT + '\\tools\\phase4\\results\\audit-pre.md')
const VALIDATOR = ROOT + '\\tools\\validate-contracts.mjs'
const AUDIT = ROOT + '\\tools\\audit-docs.mjs'
const DATE = (args && args.date) || '2026-09-23'
const W = (p) => D + p.replace(/\//g, '\\')

const OUT = { type: 'object', properties: { file: { type: 'string' }, summary: { type: 'string' }, changes: { type: 'array', items: { type: 'string' } }, open_issues: { type: 'array', items: { type: 'string' } } }, required: ['file', 'summary', 'changes', 'open_issues'] }
const TRIAGE_SCHEMA = { type: 'object', properties: { file: { type: 'string' }, counts: { type: 'object', properties: { accepted_patch: { type: 'integer' }, accepted_minor: { type: 'integer' }, accepted_major: { type: 'integer' }, rejected: { type: 'integer' }, deferred: { type: 'integer' } }, required: ['accepted_patch', 'accepted_minor', 'accepted_major', 'rejected', 'deferred'] }, bible_version_target: { type: 'string' }, contracts_affected: { type: 'boolean' }, summary: { type: 'string' } }, required: ['file', 'counts', 'bible_version_target', 'contracts_affected', 'summary'] }
const DIRECTIVE_SCHEMA = { type: 'object', properties: { file: { type: 'string' }, bible_version: { type: 'string' }, brief_version: { type: 'string' }, contracts_affected: { type: 'boolean' }, docs: { type: 'array', items: { type: 'object', properties: { path: { type: 'string', description: 'docs/ 기준 상대 경로, 예: 04-pipelines/10-chunking-strategies.md' }, directives: { type: 'integer' } }, required: ['path', 'directives'] } }, summary: { type: 'string' } }, required: ['file', 'bible_version', 'brief_version', 'contracts_affected', 'docs', 'summary'] }
const REVIEW = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, location: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['file', 'severity', 'location', 'problem', 'fix'] } }, verdict: { type: 'string', enum: ['accept', 'revise'] } }, required: ['findings', 'verdict'] }
const TOOLRUN = { type: 'object', properties: { validator_errors: { type: 'integer' }, audit_summary: { type: 'string' }, fixed: { type: 'array', items: { type: 'string' } }, remaining: { type: 'array', items: { type: 'string' } } }, required: ['validator_errors', 'audit_summary', 'fixed', 'remaining'] }

const RULES = `## 공통 규칙
- 우선순위: 브리프 > 바이블 > ADR > 개별 문서. 바이블은 258KB이므로 Grep으로 헤더(^## |^### |^#### ) 줄 번호를 얻어 필요한 절만 Read한다. 통째로 읽지 않는다.
- 한국어 본문, 영문 식별자. 이모지·과장 금지. 링크는 브리프 §8 문서 맵 경로만. 결정은 \`**결정:**\`, 미정은 \`**미정(O-xx):**\`.
- 문서를 고치면 frontmatter \`version\`을 patch 올리고 \`last_updated: ${DATE}\`. \`status\`는 바꾸지 않는다(ADR은 accepted 유지).
- JSON 블록·스키마를 고치면 node -e 로 파싱 검증하고, 계약·스키마를 고쳤으면 \`node "${VALIDATOR}" --root "${ROOT}"\` 를 실행해 ERROR 0을 확인한다.
- 지정된 파일만 수정한다. 다른 에이전트가 다른 문서를 동시에 편집 중이다.`

// ---------------------------------------------------------------- T1
phase('T1 Triage')
const t1 = await agent(`당신은 이 플랫폼의 수석 아키텍트다. 3단계 문서들이 남긴 **바이블 개정 요청 200건과 완전성 검토 항목**을 트리아지한다. 바이블·브리프는 이 단계에서 수정하지 않는다(다음 단계 T2가 한다).

## 입력(순서대로 읽기)
1. 4·5단계 계획 ${PLAN} §2.3(결정 D4-1~D4-4는 제안값 채택: GL/PL 접두 전환 완료, 900행 초과는 절 이관, 바이블 목표 1.3.0 minor·major 유발 요청은 보류, 표본 검증 20%)과 §7(완전성 검토 편입 표).
2. 통합 목록 ${TRIAGE_IN} §2(바이블 개정 요청 후보 200행)·§3(계약 감사 정본 결정 47건 — 이미 계약에 적용됨, 하류 전파 대상).
3. 완전성 검토 ${CRITIC} §3(누락 12건)·§4(인계 13건).
4. 브리프 ${BRIEF} §4·§8, 바이블 ${BIBLE} 의 관련 절(요청이 가리키는 절만 Grep으로 확인).

## 판정 규칙
- 채택(patch): 오탈자·설명 보강·예시·누락 행 추가(§5.1 인벤토리 35번째 행, §8 문서 맵 07-13·14, §14 표기 정정 등).
- 채택(minor): 선택 필드·열거값·이벤트·JobKind 추가, 기본 파라미터 값 변경, §14 엔드포인트 추가(FR-MGT-01 테넌트 API 포함), 게이트 근거가 있는 것.
- 채택(major)·보류: 필드 제거·의미 변경·필수화·타입명·스테이지 경계 변경은 **보류**(ADR-0039 이후로 이관)하고 이유를 적는다. 6단계 M1 구현에 반드시 필요하면 예외적으로 major 채택하되 영향 문서를 열거한다.
- 기각: 바이블이 이미 정한 것을 다른 문서가 오독한 경우(문서 쪽 수정 지시로 전환), 근거 없는 제안, 중복.
- 요청이 "[미반영]", "[관찰]", "[유지]" 등 문서 내부 메모인 경우는 "문서 내부(전파 지시)"로 분류하고 해당 문서에 줄 지시를 한 줄로 적는다.
- 같은 취지의 요청은 병합해 개정 항목(AM-nn)으로 묶는다.

## 산출물
${TRIAGE_OUT} 을 작성한다(frontmatter: title "바이블 개정 요청 트리아지 결정", status active, owner architecture, version 1.0.0, last_updated ${DATE}, depends_on).
절: 목적 / 범위 / 1. 집계(판정별 건수) / 2. 개정 항목 AM-01~(표: 항목 | 판정 | 바이블 절 | 변경 요지 | 병합한 요청 # | 영향 문서) / 3. 요청별 판정(표: # | 출처 | 판정 | AM 또는 이유) — 200행 전부 / 4. 완전성 검토 항목 판정(#1~#12 각각) / 5. 보류(ADR-0039+) 목록과 이유 / 6. 문서 내부 전파 지시(문서별 한 줄 목록) / 결정 사항 요약 / 미해결 이슈 / 참조.
바이블 버전 목표를 명시한다(minor 채택이 하나라도 있으면 1.3.0). 계약 문서·스키마에 영향이 있는 개정이 있으면 contracts_affected=true.
${RULES}`, { label: 't1:triage', phase: 'T1 Triage', schema: TRIAGE_SCHEMA, model: 'opus', effort: 'high' })
if (!t1) throw new Error('T1 failed')
log(`T1: 채택 patch ${t1.counts.accepted_patch} / minor ${t1.counts.accepted_minor} / major ${t1.counts.accepted_major}, 기각 ${t1.counts.rejected}, 보류 ${t1.counts.deferred}, 바이블 목표 ${t1.bible_version_target}`)

// ---------------------------------------------------------------- T2
phase('T2 Bible Revision')
const t2 = await agent(`당신은 수석 아키텍트다. 트리아지 결정 ${TRIAGE_OUT} 의 채택 항목(AM-nn)을 **바이블과 브리프에 반영**하고, 하류 문서용 **전파 지시서**를 작성한다.

## 절차
1. ${TRIAGE_OUT} §2·§4·§6을 읽는다.
2. 바이블 ${BIBLE}: 채택 항목마다 해당 절을 Grep으로 찾아 Edit로 국소 수정한다(표 행 추가·문구 정정·열거값 추가). §1.2 절차대로 frontmatter version을 ${t1.bible_version_target} 로 올리고, 문서 끝 "## 결정 사항 요약" 아래 또는 §범위의 변경 이력에 "v${t1.bible_version_target}(${DATE}) 변경 목록"을 AM 번호와 함께 남긴다. §5.1 인벤토리에 schema-diff-report.schema.json 행을 추가한다. §16(용어 반영 표)은 용어집 개정의 입력이므로 유지한다.
3. 브리프 ${BRIEF}: §8 문서 맵을 실제 파일과 일치시킨다(07-tech-landscape 13·14, 12-appendix 00~08·design-proposals, 06-adr README, 05-api openapi.yaml, schemas/README 예정). §4 결정 행이 바이블 개정으로 바뀌면 "(개정 v1.3, 근거: AM-nn/ADR-xxxx)" 표기로 갱신. frontmatter version 1.2.2(§4 변경 시 1.3.0).
4. 전파 지시서 ${DIRECTIVES} 작성(frontmatter 포함). 구조: 목적 / 범위 / 1. 공통 지시(모든 문서: GL-/PL- 접두 전환 확인, 바이블 v${t1.bible_version_target} 인용 갱신, 기각 기술 언급은 "대안·기각" 문맥 명시) / 2. 문서별 지시 — **docs/ 상대 경로를 ### 제목으로** 하는 절마다 체크리스트(- [ ] 항목: 바이블 절·AM 번호·구체 변경). 포함해야 할 출처: (a) AM 채택 항목의 영향 문서, (b) 통합 목록 §3 계약 감사 정본 결정 47건 중 04-pipelines·05-api·08~11 문서가 같은 필드·열거를 쓰는 곳, (c) 트리아지 §6 문서 내부 지시, (d) 기계 감사 ${AUDIT_MD} 의 A3(likely_ok=false 행: 문맥 검토 후 수정 또는 "기각 대안" 명시)·A7(미정의 인용 정정) 행, (e) 완전성 검토 #1(용어집: 바이블 §16 표 55행 전개, 변경 행 "→" 표기, 미해결 이슈 GL- 접두 유지), #2(비전 01·02·04·요구사항 01·02·04: 브리프 v1.2 개정 반영 — 기각 기술·구 명칭·개정된 D-xx 요지), #9(00-vision/04의 NFR-I-02 오인용, 09-operations/07의 NFR-REL-17 신설 제안 처리), #10(CLI 정본 절 소유 문서 지정), #12(카탈로그 등재 후보). 문서마다 지시 3~15개, 총 문서 수는 40~70개 예상.
5. 구조화 결과로 문서 목록(path, directives 수)을 반환한다. path는 docs/ 기준 상대 경로 철자를 정확히(존재하는 파일만).
${RULES}`, { label: 't2:bible-revision', phase: 'T2 Bible Revision', schema: DIRECTIVE_SCHEMA, model: 'opus', effort: 'high' })
if (!t2) throw new Error('T2 failed')
log(`T2: 바이블 ${t2.bible_version} / 브리프 ${t2.brief_version}, 지시 대상 문서 ${t2.docs.length}개, 계약 영향 ${t2.contracts_affected}`)

// ---------------------------------------------------------------- T3
phase('T3 Schema Sync')
let t3 = null
if (t2.contracts_affected || t1.contracts_affected) {
  t3 = await agent(`계약·스키마 동기화 담당이다. 바이블 v${t2.bible_version}의 변경(${TRIAGE_OUT} §2의 채택 항목 중 계약 관련)과 전파 지시서 ${DIRECTIVES} 의 03-contracts/* 절을 읽고, 해당 계약 문서(필드 표·스키마 블록·Pydantic·예시)와 ${ROOT}\\schemas\\*.schema.json 을 일치시킨다. 열거값 추가는 schemas/common-types.schema.json 에도 반영한다. 완료 후 node "${VALIDATOR}" --root "${ROOT}" 를 실행해 ERROR 0이 될 때까지 고친다(최대 4회). 결과 반환.
${RULES}`, { label: 't3:schema-sync', phase: 'T3 Schema Sync', schema: TOOLRUN, model: 'sonnet' })
  log(`T3: 검증기 오류 ${t3 ? t3.validator_errors : '?'}`)
} else log('T3: 계약 영향 없음 → 생략')

// ---------------------------------------------------------------- P1 (grouped propagation)
phase('P1 Propagate')
const OVERSIZE = ['02-architecture/02-component-architecture.md', '02-architecture/05-plugin-architecture.md', '02-architecture/06-orchestration-and-workflows.md', '02-architecture/07-multi-tenancy-and-security-architecture.md', '04-pipelines/01-pipeline-framework.md', '04-pipelines/17-post-processing-and-context-packing.md', '08-evaluation/04-llm-judge-and-generation-quality.md', '09-operations/02-configuration-reference.md', '11-roadmap/02-epics-and-backlog.md']
const docs = t2.docs.map((d) => d.path.replace(/\\/g, '/').replace(/^docs\//, '')).filter((p) => p !== '02-architecture/00-design-bible.md' && p !== '00-vision/00-design-brief.md' && !p.startsWith('03-contracts/'))
const glossary = docs.filter((p) => p.endsWith('03-glossary.md'))
const rest = docs.filter((p) => !p.endsWith('03-glossary.md'))
const byDir = {}
for (const p of rest) (byDir[p.split('/')[0]] = byDir[p.split('/')[0]] || []).push(p)
const groups = []
for (const [dir, ps] of Object.entries(byDir)) { const size = dir === '06-adr' ? 6 : 4; for (let i = 0; i < ps.length; i += size) groups.push(ps.slice(i, i + size)) }
if (glossary.length) groups.unshift(glossary)
log(`P1: 문서 ${docs.length}개 → 묶음 ${groups.length}개`)
const p1 = await parallel(groups.map((g, i) => () => agent(`당신은 문서 편집자다. 전파 지시서 ${DIRECTIVES} 에서 아래 문서들의 절(### <경로>)과 "1. 공통 지시"를 읽고 **지시된 변경만** 반영한다.

대상 문서(docs/ 기준): ${g.join(', ')}
${g.some((p) => p.endsWith('03-glossary.md')) ? `용어집 특별 지시: 바이블 ${BIBLE} §16 표(Grep으로 "## 16." 위치)를 읽어 추가 행은 정의문(용어 | English | 정의 | 관련 계약/문서 | 비고)으로 전개하고, 변경 행은 기존 정의를 고치며 비고에 "v1.3 변경 → …"를 남긴다. 용어집 미해결 이슈 ID는 GL-xx, 링크 키는 [PL-xx]다. version을 0.2.0으로 올린다.` : ''}
규칙: 지시 항목마다 바이블 해당 절을 Grep으로 확인한 뒤 Edit로 국소 수정한다. 처리한 항목은 각 문서 "## 미해결 이슈"에서 제거하거나 "해소(v1.3, AM-nn)"로 표기한다. 기각 기술(PyMuPDF·pyhwp·MinIO·Redis·Infinity·SPLADE-v3) 언급은 삭제하지 않고 "대안·기각(ADR-nnnn)" 문맥이 드러나게 고친다. 문서 분량이 900행을 넘게 되면 늘리지 말고 압축한다. 완료 후 문서마다 무엇을 바꿨는지 changes에 "경로: 요지"로 적는다.
${RULES}`, { label: `p1:group-${i + 1}`, phase: 'P1 Propagate', schema: OUT, model: 'sonnet' })))
log(`P1 완료 ${p1.filter(Boolean).length}/${groups.length}`)

// ---------------------------------------------------------------- P2 (oversize trimming; sequential after P1 to avoid edit conflicts)
phase('P2 Trim')
const TRIM_GROUPS = [
  ['02-architecture/02-component-architecture.md', '02-architecture/05-plugin-architecture.md', '02-architecture/06-orchestration-and-workflows.md'],
  ['02-architecture/07-multi-tenancy-and-security-architecture.md', '04-pipelines/01-pipeline-framework.md', '04-pipelines/17-post-processing-and-context-packing.md'],
  ['08-evaluation/04-llm-judge-and-generation-quality.md', '09-operations/02-configuration-reference.md', '11-roadmap/02-epics-and-backlog.md'],
]
const p2 = await parallel(TRIM_GROUPS.map((g, i) => () => agent(`당신은 문서 편집자다. 브리프 §9.11 분량 규약(비계약 문서 250~900행)을 초과한 문서들을 **절 이관 또는 압축**으로 900행 이내로 만든다. 내용을 삭제해 정보를 잃지 않는다.

대상: ${g.join(', ')} (각각 현재 900행 초과)
방법 우선순위: (1) 다른 문서가 소유해야 할 절을 그 문서로 옮기고 원 위치에 요약 2~3줄 + 링크를 남긴다(이관 후보: 02-architecture/02 설정 모델·환경변수 상세 → 09-operations/02; 02-architecture/06 사가 상세 → 04-pipelines/19; 04-pipelines/01 CLI·테스트 유틸 → 10-development/02·04; 09-operations/02는 환경변수 표를 압축(중복 설명 제거); 11-roadmap/02 태스크 표는 에픽별 파일 분할 대신 열 축소; 08-evaluation/04 프롬프트 전문은 부록 절로 축약). 이관받는 문서가 900행을 넘게 되면 이관하지 않고 압축한다. (2) 중복 서술·장식 산문 제거. (3) 표 병합.
이관 시 양쪽 문서의 링크·목차·"## 참조"를 갱신하고 이관받는 문서의 version도 patch 올린다. 완료 후 wc -l 로 행 수를 확인해 changes에 "경로: 전 → 후 행"으로 적는다.
${RULES}`, { label: `p2:trim-${i + 1}`, phase: 'P2 Trim', schema: OUT, model: 'sonnet' })))
log(`P2 완료 ${p2.filter(Boolean).length}/${TRIM_GROUPS.length}`)

// ---------------------------------------------------------------- P3 (sample verification of fast-mode fixes)
phase('P3 Sample Verify')
const SAMPLE = [
  ['08-evaluation/04-llm-judge-and-generation-quality.md', '04-pipelines/04-parser-hwpx-and-hwp.md'],
  ['04-pipelines/02-fetching-and-source-resolution.md', '05-api/01-api-design-guidelines.md'],
  ['04-pipelines/05-parser-pdf.md', '04-pipelines/07-parser-html.md'],
  ['05-api/02-ingestion-api.md', '10-development/05-ci-cd.md'],
  ['11-roadmap/02-epics-and-backlog.md', '04-pipelines/11-enrichment.md'],
  ['06-adr/0031-profile-schema-extends-and-quality-gates.md', '06-adr/0016-llm-enrichment-default-off-and-budget-policy.md'],
  ['06-adr/0021-korean-analyzer-kiwi-promotion-and-interim-mecab-kss.md', '06-adr/0023-evaluation-qrels-answer-spans-and-linear-ndcg.md'],
]
const reviews = await parallel(SAMPLE.map((pair, i) => () => agent(`당신은 검증 리뷰어다. 아래 두 문서는 3단계 마지막에 **경량 모드로 수정되어 독립 검증이 없다**. 각 문서를 읽고 (1) 바이블 ${BIBLE} 관련 절(Grep으로 찾기)과의 철자·결정 일치, (2) 문서 내부 모순(표 ↔ 본문 ↔ 다이어그램), (3) JSON/Mermaid 문법(json 블록은 node -e 로 파싱), (4) 부분 수정 흔적(앞뒤가 다른 서술)을 점검한다. 수정하지 않고 findings만 반환한다(file 필드에 경로). 문제 없으면 빈 배열.
문서: ${pair.map((p) => W(p)).join(' , ')}
${RULES}`, { label: `p3:review-${i + 1}`, phase: 'P3 Sample Verify', schema: REVIEW, model: 'sonnet', effort: 'medium' })))
const findings = reviews.filter(Boolean).flatMap((r) => r.findings)
const serious = findings.filter((f) => f.severity !== 'minor')
log(`P3: 표본 ${SAMPLE.flat().length}건, 이슈 ${findings.length}(심각 ${serious.length}), 심각 발견율 ${(serious.length / SAMPLE.flat().length).toFixed(2)}건/문서`)
const byFile = {}
for (const f of serious) (byFile[f.file] = byFile[f.file] || []).push(f)
const p3fix = await parallel(Object.entries(byFile).map(([file, fs]) => () => agent(`검증 리뷰가 찾은 심각 이슈를 문서에 반영한다. 파일: ${file}
이슈: ${JSON.stringify(fs, null, 1).slice(0, 12000)}
리뷰어 주장도 바이블 해당 절을 직접 확인한 뒤 반영한다(앵커 우선). Edit로 국소 수정. 결과 반환.
${RULES}`, { label: `p3:fix:${file.split(/[\\/]/).pop()}`, phase: 'P3 Sample Verify', schema: OUT, model: 'sonnet' })))
log(`P3 수정 ${p3fix.filter(Boolean).length}/${Object.keys(byFile).length}`)

// ---------------------------------------------------------------- P4 (residual cleanup with tools)
phase('P4 Residual')
const p4 = await agent(`당신은 정합성 수리자다. 다음을 실행하고 남은 문제를 고친다.
1. node "${VALIDATOR}" --root "${ROOT}"  → ERROR가 있으면 계약·스키마를 고쳐 0으로.
2. node "${AUDIT}" --root "${ROOT}" --json "${ROOT}\\tools\\phase4\\results\\audit-post.json" --md "${ROOT}\\tools\\phase4\\results\\audit-post.md"  → A1 깨진 링크, A2 frontmatter 누락, A7 미정의 인용(ADR-0039는 "제안" 문맥이면 허용), A5 900행 초과(비계약)를 고친다. A3 likely_ok=false 행은 문맥을 보고 "대안·기각" 문맥이 아니면 정정한다. A10(바이블 §14 ↔ openapi) 불일치는 바이블 §14가 정본이므로 openapi.yaml 또는 05-api 문서를 맞춘다(§14에 새로 추가된 엔드포인트가 있으면 openapi에 최소 정의 추가). 단, 감사기의 A10은 §14 표의 "GET/POST" 병기 행과 "\`/retry\`" 같은 축약 표기를 메서드×경로로 기계 조합하므로 오탐이 있을 수 있다 — 반드시 §14 표 원문을 읽어 실제로 정의된 (메서드, 경로) 쌍만 반영하고, 표기 축약 때문에 생긴 조합(예: "POST /v1/subscriptions/{id}")은 무시한다.
3. 다시 실행해 결과를 확인한다(최대 3회 반복).
4. 추적 매트릭스 ${TRACE} §1의 미인용 FR 중 20건을 표본으로 뽑아 "실제 설계 갭"인지 "ID만 미인용"인지 판정한 표를 그 문서 끝 "## 표본 판정" 절로 추가한다(기계 생성 문서이지만 이 절은 수동 절로 표시).
결과 반환(validator_errors, audit_summary, fixed, remaining).
${RULES}`, { label: 'p4:residual', phase: 'P4 Residual', schema: TOOLRUN, model: 'sonnet' })
log(`P4: 검증기 오류 ${p4 ? p4.validator_errors : '?'}, 남은 항목 ${p4 ? p4.remaining.length : '?'}`)

return { t1, t2: { ...t2, docs: t2.docs.length }, t3, p1: p1.filter(Boolean).map((r) => r.summary.slice(0, 200)), p2: p2.filter(Boolean).map((r) => r.changes), p3: { sampled: SAMPLE.flat().length, findings: findings.length, serious: serious.length, fixed: p3fix.filter(Boolean).length, byFile: Object.keys(byFile) }, p4 }
