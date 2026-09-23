// Phase 3 ADR 고속 리뷰 워크플로 `wf-adr-fast.js`를 조립하는 빌드 스크립트(2026-09-23, 일회성 도구) — 이전 세션에서
// 죽은 워크플로의 저널에서 이미 리뷰된 13개 ADR(0001-0013)의 사전 리뷰 결과를 병합하고, 나머지 25개는 결합 고속
// 리뷰어 1개로 처리하도록 스크립트를 생성한다.
// 설계 근거: `docs/12-appendix/00-progress-report.md` §7.2d(고속 ADR 사이클 결정), Phase 3 마감 계획.
// 구성: 13개 ADR용 `tools/phase3/results/adr-prereviews/NNNN.json` 병합 로직, 나머지 25개용 결합 리뷰어(effort
// medium) + 조건부 수정 에이전트, `06-adr/README.md` 색인 생성 단계.
// 불변식: Phase 3가 이미 완료·커밋되었으므로 이 스크립트는 재실행 대상이 아니다(기록 보존 목적).
// 검증 계층: 1층(여기서 검증) — 산출물 `wf-adr-fast.js`는 Phase 3 완료 시점에 이미 실행·검증되었다.
import fs from 'node:fs'
import path from 'node:path'
const dir = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1') + '/'
const journal = process.argv[2] // path to previous session's adrs journal.jsonl
const outDir = dir + 'results/adr-prereviews/'
fs.mkdirSync(outDir, { recursive: true })

// 1) merge pre-reviews
const pre = {}
if (journal && fs.existsSync(journal)) {
  const lines = fs.readFileSync(journal, 'utf8').trim().split('\n').map((l) => JSON.parse(l))
  const started = {}
  for (const l of lines) if (l.type === 'started') started[l.agentId] = l
  for (const l of lines) {
    if (l.type !== 'result' || !l.result || !Array.isArray(l.result.findings)) continue
    const s = started[l.agentId]; if (!s) continue
    const m = /^review-(anchor|tech):06-adr\/(\d{4})-/.exec(s.label || ''); if (!m) continue
    const id = m[2]; pre[id] = pre[id] || { id, findings: [], verdicts: {} }
    pre[id].verdicts[m[1]] = l.result.verdict
    for (const f of l.result.findings) pre[id].findings.push({ ...f, lens: m[1] })
  }
  for (const [id, v] of Object.entries(pre)) fs.writeFileSync(outDir + id + '.json', JSON.stringify(v, null, 1))
}
const PRE_IDS = Object.keys(pre).sort()
console.log('pre-reviewed ADRs:', PRE_IDS.join(','), 'findings:', Object.values(pre).reduce((a, v) => a + v.findings.length, 0))

// 2) static ADR list (bible §3.3, verified 2026-09-23 against docs/06-adr file names)
const adrFiles = fs.readdirSync(path.resolve(dir, '../../docs/06-adr')).filter((f) => /^\d{4}-.*\.md$/.test(f)).sort()
if (adrFiles.length !== 38) throw new Error('expected 38 ADR files, got ' + adrFiles.length)
const ADRS = adrFiles.map((f) => ({ id: f.slice(0, 4), file: f }))

// 3) tail
const tail = `
// ---------------------------------------------------------------- ADR fast cycle (2026-09-23)
const PRE = ${JSON.stringify(PRE_IDS)}
const ADR_FILES = ${JSON.stringify(ADRS)}
const PRE_DIR = ROOT + '\\\\tools\\\\phase3\\\\results\\\\adr-prereviews\\\\'
const ADR_NOTE = \`

ADR 예외(MADR): frontmatter status는 "accepted"를 유지하고 "active"로 바꾸지 않는다. frontmatter에 version(없으면 0.1.0 추가)·date·deciders·priority·related·depends_on이 있어야 한다. ADR에는 ## 목적/## 범위/## 결정 사항 요약/## 미해결 이슈 절을 두지 않으며(MADR 절 구조: 맥락과 문제 / 결정 동인 / 고려한 대안 / 결정 / 결과 / 준수 확인 방법 / 재검토 조건 / 참조), 그 부재를 finding으로 잡지 않는다. "## 결정" 절의 문장은 바이블 §3.1~3.3·관련 절과 정확히 일치해야 하며 새 결정을 만들지 않는다. 바이블 §3.3 표에서 이 ADR 행(번호·제목·slug·우선·관련 결정)을 Grep으로 찾아 대조한다.\`
function adrDoc(a) {
  return { path: '06-adr/' + a.file, title: 'ADR-' + a.id, len: '90~240',
    deps: ['02-architecture/00-design-bible.md', '07-tech-landscape/00-summary-and-selection-matrix.md'],
    bible: '§3.3 표의 ' + a.id + ' 행과 그 행의 관련 결정(D-xx/O-xx)에 해당하는 §3.1~3.2 행, 그리고 결정이 정밀화된 절(§3.3 행의 제목으로 판단)',
    outline: 'MADR 형식(맥락과 문제 / 결정 동인 / 고려한 대안(기각 대안 포함, 07-tech-landscape 근거) / 결정(**결정:**으로 시작, 바이블 문장과 일치) / 결과 / 준수 확인 방법(CI 게이트·스키마 제약·리뷰 항목) / 재검토 조건 / 참조). 바이블 §3.3 표의 ' + a.id + ' 행과 정확히 일치.' }
}
function reviewFastP(d, note) {
  return \`당신은 앵커 준수 감사자 겸 기술 리뷰어다. 한 번의 검토로 아래를 모두 확인하고, 문서를 수정하지 말고 결과만 반환한다. Grep으로 필요한 절만 읽는다.

문서: \${W(d.path)}
앵커: 브리프 \${BRIEF}(§4 확정 결정, §9 규약), 바이블 \${BIBLE}(Grep으로 헤더 줄 번호를 얻어 [\${BIBLE_COMMON}] 과 지정 절 [\${d.bible}] 만 Read), 선정 매트릭스 \${MATRIX}(관련 절만).
지시(outline): \${d.outline}

검토 항목:
1. 결정 문장·근거가 바이블 §3.1~3.3 및 관련 절과 일치하는가(철자·수치·기각 대안 포함). 임의 결정·바이블에 없는 규칙의 단정은 major.
2. 문서 내부 모순: 표 ↔ 다이어그램 ↔ 본문(오류 코드·필드명·순서·수치), 잘못된 바이블 절 인용.
3. 기술 정확성: 라이브러리·라이선스·버전 주장이 07-tech-landscape와 일치하는가.
4. 문법: json 블록은 임시 파일로 저장해 node -e 로 파싱(실패는 blocker); Mermaid 문법; Python/YAML 블록 명백한 오류.
5. 규약: frontmatter(title, status: accepted, date, deciders, priority, related, depends_on, version), 링크가 브리프 §8 문서 맵 경로인가, 이모지·근거 없는 수치, 분량 \${d.len}행.
계약·결정·문법 오류는 major/blocker, 표현은 minor(5개 이내). 문제 없으면 findings 빈 배열 + accept.\${note}\`
}
function fixFromFileP(d, file) {
  return \`당신은 문서의 최종 편집자다. 이전 세션 리뷰어 2명(anchor=앵커 준수, tech=기술)의 결과가 파일에 저장되어 있다. 그것을 읽고 문서를 수정한다.

파일: \${W(d.path)}
리뷰 결과 파일(JSON: findings[] {severity, location, problem, fix, lens}, verdicts): \${file}

규칙: blocker/major는 모두 수정하고 minor는 합리적인 것만 반영한다. 리뷰어의 "정본" 주장도 바이블 \${BIBLE} 해당 절(Grep으로 위치 확인 후 Read)을 직접 읽어 확인한 뒤 반영한다 — 리뷰어가 앵커와 다르게 주장하면 앵커(브리프 > 바이블)가 우선한다. Edit로 국소 수정하고(전체 재작성 금지), 수정 후 문서 전체를 다시 읽어 표·다이어그램·본문이 일치하는지 확인한다. last_updated 또는 date 갱신은 하지 않는다(ADR date는 결정일). JSON 블록은 node -e 로 파싱 검증. 별도 검증 단계가 없으므로 각 blocker/major 항목이 해결되었는지 스스로 확인하고 summary에 항목별로 적는다. 저장 후 구조화 결과를 반환한다.
\${conv(d, null)}\${ADR_NOTE}\`
}
async function adrCycle(a) {
  const d = adrDoc(a)
  if (PRE.includes(a.id)) {
    const fx = await agent(fixFromFileP(d, PRE_DIR + a.id + '.json'), { label: \`fix:\${d.path}\`, phase: 'ADR fast cycle', schema: DONE })
    return fx ? { ...fx, review: 'fixed_from_prereview' } : { file: W(d.path), review: 'fix_failed' }
  }
  const r = await agent(reviewFastP(d, ADR_NOTE), { label: \`review:\${d.path}\`, phase: 'ADR fast cycle', schema: REVIEW, effort: 'medium' })
  if (!r) { log(\`\${d.path}: 리뷰 실패\`); return { file: W(d.path), review: 'review_failed' } }
  const fs1 = (r.findings || []).map((f) => ({ ...f, lens: 'combined' }))
  const ser = fs1.filter((f) => f.severity !== 'minor')
  if (!fs1.length) { log(\`\${d.path}: 리뷰 통과(이슈 0)\`); return { file: W(d.path), review: 'pass', serious: 0 } }
  log(\`\${d.path}: 리뷰 이슈 \${fs1.length}개(심각 \${ser.length}) → 수정\`)
  const fx = await agent(fixP(d, fs1, null, 1) + ADR_NOTE + '\\n\\n경량 모드: 별도 검증 단계가 없으므로 수정 후 각 blocker/major 항목의 해결을 스스로 확인하고 summary에 항목별로 적는다. ADR이므로 status는 accepted 유지, date는 갱신하지 않는다.', { label: \`fix:\${d.path}\`, phase: 'ADR fast cycle', schema: DONE })
  return fx ? { ...fx, review: ser.length ? 'fixed_unverified' : 'minor_fixed', serious: ser.length } : { file: W(d.path), review: 'fix_failed', serious: ser.length }
}

phase('ADR fast cycle')
log(\`ADR 경량 사이클: 기존 리뷰 재사용 수정 \${PRE.length}건, 경량 리뷰 \${ADR_FILES.length - PRE.length}건\`)
const out = await parallel(ADR_FILES.map((a) => () => adrCycle(a)))
const res = out.filter(Boolean)
const failed = res.filter((r) => /failed/.test(r.review)).map((r) => r.file)
log(\`ADR 사이클 완료 \${res.length}/\${ADR_FILES.length}, 실패 \${failed.length}\`)
phase('ADR index')
const idx = await agent(\`\${D}06-adr\\\\ 의 모든 ADR 파일(frontmatter와 ## 결정 절)을 읽고 인덱스 \${D}06-adr\\\\README.md 를 작성한다: frontmatter(title: ADR 인덱스, status: active, owner: architecture, version: 0.1.0, last_updated: \${DATE}, depends_on: ["../02-architecture/00-design-bible.md"]), MADR 소개와 작성 규칙(바이블 §1.2 변경 절차와의 관계), 상태 정의(proposed/accepted/deprecated/superseded), 표(ID | 제목 | 상태 | 우선 | 관련 결정(D/O-xx) | 요약 한 줄 | 링크), 주제별 그룹(라이선스·의존성 / 파싱·문서 모델 / 청킹·보강 / 임베딩·인덱스 / 검색·패킹 / 오케스트레이션·원장 / 보안·테넌시 / 계약·명명 / 운영·관측·평가 / API·MCP), P0 ADR 우선 읽기 안내, 새 ADR 절차. 한국어. 파일 목록이 바이블 §3.3 38건과 일치하는지 확인하고 누락이 있으면 summary에 적는다. Write 후 결과 반환.\`, { label: 'adr:index', phase: 'ADR index', schema: DONE })
return { date: DATE, adrs: res.map((r) => ({ file: r.file, review: r.review, serious: r.serious })), failed, index: idx ? idx.file : null }
`
const src = fs.readFileSync(dir + 'wf-phase3.js', 'utf8').split('\n')
const marker = src.findIndex((l) => l.startsWith('// ---------------------------------------------------------------- ADRs'))
if (marker < 0) throw new Error('marker not found')
const out = src.slice(0, marker).join('\n') + '\n' + tail
fs.writeFileSync(dir + 'wf-adr-fast.js', out)
new Function('args', 'agent', 'parallel', 'pipeline', 'phase', 'log', 'budget', 'workflow', 'return (async()=>{' + out.replace(/^export const meta/m, 'const meta') + '})()')
console.log('written wf-adr-fast.js', out.split('\n').length, 'lines; syntax OK')
