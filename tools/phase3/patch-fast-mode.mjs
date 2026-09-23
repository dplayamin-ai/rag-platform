// One-off patch (2026-09-23): add fast review mode (single reviewer, no verify) and rebuild wf-phase3-finish.js
import fs from 'node:fs'
const dir = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1') + '/'
let t = fs.readFileSync(dir + 'wf-finish-tail.js', 'utf8')
function rep(a, b) { if (!t.includes(a)) throw new Error('anchor missing: ' + a.slice(0, 70)); t = t.replace(a, b) }

if (!t.includes('const FAST = ')) {
rep('async function flipStatus(d, ph) {',
`const FAST = !!(args && args.fast)
function reviewFastP(d, note) {
  return \`당신은 앵커 준수 감사자 겸 기술 리뷰어다. 한 번의 검토로 아래를 모두 확인하고, 문서를 수정하지 말고 결과만 반환한다. 불필요한 재읽기를 피하고 Grep으로 필요한 절만 읽는다.

문서: \${W(d.path)}
앵커: 브리프 \${BRIEF}(§4 확정 결정, §8 문서 맵, §9 규약), 바이블 \${BIBLE}(Grep으로 헤더 줄 번호를 얻어 공통 필수 절 [\${BIBLE_COMMON}] 과 지정 절 [\${d.bible || hint(d.path)}] 만 Read), depends_on: \${JSON.stringify(d.deps || [])}.
지시(outline): \${d.outline.slice(0, 2500)}

검토 항목:
1. 철자·정본: 문서의 타입명·필드명·열거값·ID 형식·엔드포인트·이벤트·오류 코드·메트릭 이름을 바이블 §5/§5.7/§6/§14와 대조. 다른 철자·임의 이름은 finding(fix에 정본 철자와 절 번호).
2. 결정 위반: 브리프 D-01~D-20·바이블 결정 레지스터와 모순, 앵커에 없는 결정의 단정, 기각된 대안(PyMuPDF·pyhwp 기본, Redis/MinIO 기본, TEI로 BGE-M3 sparse, SPLADE 기본, chunk_ulid 등) 재등장.
3. 완전성: outline 항목 중 실질 내용이 없는 것.
4. 문법: 모든 json 블록을 임시 파일로 저장해 node -e 로 파싱(실패는 blocker); Mermaid 문법(타입 선언, 노드 ID, 따옴표, subgraph end); Python/YAML 블록의 명백한 오류.
5. 내부 모순·규약: 표와 본문 불일치, frontmatter 필수 필드, 절 구조(목적/범위/결정 사항 요약/미해결 이슈/참조), 링크가 브리프 §8 문서 맵 경로인가, 이모지·근거 없는 수치, 분량(\${d.len || '350~900'}행).
계약·ID·결정·필수 필드·문법 오류는 major/blocker, 표현은 minor. 문제 없으면 findings 빈 배열 + accept. 리뷰 시간이 제한되어 있으므로 심각한 문제를 우선 찾고 minor는 5개 이내로 제한한다.\${note}\`
}

async function flipStatus(d, ph) {`)

rep(`  const note = isAdr ? ADR_NOTE : CYCLE_NOTE
  const [ra, rb] = await parallel([`,
`  const note = isAdr ? ADR_NOTE : CYCLE_NOTE
  if (FAST) {
    const r = await agent(reviewFastP(d, note), { label: \`review:\${d.path}\`, phase: ph, schema: REVIEW, effort: 'medium' })
    if (!r) { log(\`\${d.path}: 리뷰 에이전트 실패\`); return { file: W(d.path), review: 'review_failed', serious: null } }
    const fs1 = (r.findings || []).map((f) => ({ ...f, lens: 'combined' }))
    if (r.verdict === 'rewrite') fs1.unshift({ severity: 'blocker', location: '(전체)', problem: '리뷰어 verdict=rewrite', fix: '문서를 지시와 앵커에 맞게 다시 작성', lens: 'review' })
    const ser = fs1.filter((f) => f.severity !== 'minor')
    if (!fs1.length) { log(\`\${d.path}: 리뷰 통과(이슈 0)\`); if (!isAdr) await flipStatus(d, ph); return { file: W(d.path), review: 'pass', serious: 0 } }
    log(\`\${d.path}: 리뷰 이슈 \${fs1.length}개(심각 \${ser.length}) → 수정(경량: 검증 생략)\`)
    const fx = await agent(fixP(d, fs1, extraReads, 1) + note + '\\n\\n경량 모드: 별도 검증 단계가 없으므로 수정 후 스스로 각 blocker/major 항목이 해결되었는지 파일을 다시 읽어 확인하고, 확인 결과를 summary에 항목별로 적는다.', { label: \`fix:\${d.path}\`, phase: ph, schema: DONE })
    if (!fx) { log(\`\${d.path}: 수정 에이전트 실패\`); return { file: W(d.path), review: 'fix_failed', serious: ser.length } }
    return { ...fx, review: ser.length ? 'fixed_unverified' : 'minor_fixed', serious: ser.length }
  }
  const [ra, rb] = await parallel([`)

rep(`const pFull = produce(FULL, EXTRA, 'Finish: write missing')`,
`async function produceFast(docs, extraReads, ph) {
  const out = await parallel(docs.map((d) => () => (async () => {
    const w = await agent(writeP(d, extraReads), { label: \`write:\${d.path}\`, phase: ph, schema: DONE })
    if (!w) { log(\`\${d.path}: 작성 실패(드롭)\`); return null }
    const c = await cycleDoc(d, extraReads, ph, false)
    return { ...w, ...(c || {}), lines: (c && c.lines) || w.lines }
  })()))
  const dropped = docs.filter((d, i) => !out[i]).map((d) => d.path)
  if (dropped.length) log(\`\${ph}: 드롭된 문서 \${dropped.length}개 — \${dropped.join(', ')}\`)
  return { out, dropped }
}
const pFull = FAST ? produceFast(FULL, EXTRA, 'Finish: write missing') : produce(FULL, EXTRA, 'Finish: write missing')`)

rep(`const pApi = cycle(CYCLE_API, EXTRA, 'Finish: review cycle', false)`,
`log(FAST ? '경량 모드: 문서당 리뷰어 1명(effort medium), 검증·2차 수정 생략' : '표준 모드: 리뷰어 2명 → 수정 → 검증 → 2차 수정')
const pApi = cycle(CYCLE_API, EXTRA, 'Finish: review cycle', false)`)
fs.writeFileSync(dir + 'wf-finish-tail.js', t)
}

const src = fs.readFileSync(dir + 'wf-phase3.js', 'utf8').split('\n')
const marker = src.findIndex((l) => l.startsWith('// ---------------------------------------------------------------- ADRs'))
if (marker < 0) throw new Error('marker not found')
const out = src.slice(0, marker).join('\n') + '\n' + t
fs.writeFileSync(dir + 'wf-phase3-finish.js', out)
new Function('args', 'agent', 'parallel', 'pipeline', 'phase', 'log', 'budget', 'workflow', 'return (async()=>{' + out.replace(/^export const meta/m, 'const meta') + '})()')
console.log('rebuilt wf-phase3-finish.js', out.split('\n').length, 'lines; syntax OK; FAST:', out.includes('const FAST'), 'SKIP_ADRS:', out.includes('SKIP_ADRS'))
