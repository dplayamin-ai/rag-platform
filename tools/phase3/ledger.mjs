// 3단계 기록 생성기 — 디스크의 파일만으로(LLM 없이) 결정론적으로 두 문서를 만든다: `docs/12-appendix/04-phase3-document-ledger.md`(문서별 행 수·status·version·최종 리뷰 결과·심각 이슈·소유 스키마)와 `docs/12-appendix/03-bible-amendment-triage-input.md`(3단계 에이전트가 남긴 미해결 이슈를 바이블 절별로 그룹화).
// 설계 근거: 진행 보고서 `00-progress-report.md` §3(산출물 현황 — 이 원장이 근거 데이터)·§7.2b(3단계 기록 체계 정비), 4·5단계 계획 `02-phase4-5-plan.md` §2.3 D4-4(경량 수정분 표본 검증 대상 표시).
// 구성:
//   - 결과 JSON 수집 — `tools/phase3/results/*.json`을 재귀 순회해 리뷰 결과(`outcomes`)·미해결 이슈(`openIssues`)·계약 감사 정본 결정(`canonical`) 추출
//   - `rows` — frontmatter·행 수·최종 리뷰 결과를 문서별 원장 행으로 구성
//   - 원장·트리아지 입력 md 조립 — frontmatter 포함해 두 파일에 저장
// 불변식·주의: 두 출력 모두 기계 생성 문서이며 사람이 편집하지 않는다(원장과 진행 보고서가 다르면 원장이 우선). 미해결 이슈는 앞 160자 동일 기준으로 중복 병합하고, "바이블 관련" 판정은 정규식 휴리스틱이라 4단계 트리아지에서 재분류될 수 있다.
// 검증 계층: 1층(여기서 검증, 콘솔 요약으로 확인). 실행: `node tools/phase3/ledger.mjs [--root <repo>] [--date YYYY-MM-DD]`
import fs from 'node:fs'
import path from 'node:path'
const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const ROOT = opt('--root', 'C:\\Workspaces\\rag-platform')
const DATE = opt('--date', new Date().toISOString().slice(0, 10))
const DOCS = path.join(ROOT, 'docs')
const RES = path.join(ROOT, 'tools', 'phase3', 'results')

function walk(d, out = []) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p, out); else if (p.endsWith('.md')) out.push(p) } return out }
const rel = (p) => path.relative(DOCS, p).split(path.sep).join('/')
function fm(text) {
  if (!text.startsWith('---')) return {}
  const end = text.indexOf('\n---', 3); if (end < 0) return {}
  const o = {}
  for (const line of text.slice(3, end).split('\n')) { const m = /^([a-z_]+):\s*(.*)$/.exec(line); if (m) o[m[1]] = m[2].trim().replace(/^"(.*)"$/, '$1') }
  return o
}

// ---- collect review outcomes from results/*.json (objects having file + review)
const outcomes = {} // relpath -> [{review, serious, group}]
const openIssues = [] // {group, source, text}
const canonical = [] // contracts-audit canonical decisions
function walkJson(o, group, fn) { if (!o || typeof o !== 'object') return; fn(o, group); for (const k of Object.keys(o)) if (typeof o[k] === 'object') walkJson(o[k], group, fn) }
if (fs.existsSync(RES)) for (const f of fs.readdirSync(RES).filter((f) => f.endsWith('.json') && !f.startsWith('validator'))) {
  let j; try { j = JSON.parse(fs.readFileSync(path.join(RES, f), 'utf8')) } catch { continue }
  const group = f.replace('.json', '')
  walkJson(j, group, (o) => {
    if (typeof o.file === 'string' && typeof o.review === 'string') {
      const r = o.file.replace(/\\/g, '/'); const i = r.indexOf('/docs/'); const key = i >= 0 ? r.slice(i + 6) : r
      ;(outcomes[key] = outcomes[key] || []).push({ review: o.review, serious: o.serious ?? null, group })
    }
    if (Array.isArray(o.openIssues)) for (const s of o.openIssues) if (typeof s === 'string') { const m = /^([^:]+\.md):\s*(.*)$/s.exec(s); openIssues.push({ group, source: m ? m[1] : '(unknown)', text: m ? m[2] : s }) }
    if (Array.isArray(o.canonicalDecisions)) for (const s of o.canonicalDecisions) if (typeof s === 'string') canonical.push(s)
  })
}
const REVIEW_KO = { pass: '리뷰 통과(이슈 0)', verified: '수정 후 검증 통과', fixed_twice: '2차 수정(검증 미해결 반영)', minor_fixed: 'minor만 수정', fixed_unverified: '경량 수정(독립 검증 없음)', fixed_from_prereview: '이전 리뷰 결과로 수정(독립 검증 없음)', fix_failed: '수정 실패', verify_failed: '검증 에이전트 실패', fix2_failed: '2차 수정 실패', review_failed: '리뷰 실패' }
const finalOutcome = (key) => { const a = outcomes[key]; if (!a || !a.length) return null; return a[a.length - 1] }

// ---- schemas owned per contract doc
const schemaFiles = fs.existsSync(path.join(ROOT, 'schemas')) ? fs.readdirSync(path.join(ROOT, 'schemas')).filter((f) => f.endsWith('.schema.json')) : []

// ---- document rows
const files = walk(DOCS).filter((p) => !rel(p).startsWith('12-appendix/sources/')).sort()
const rows = files.map((p) => {
  const t = fs.readFileSync(p, 'utf8'); const f = fm(t); const r = rel(p)
  const owned = r.startsWith('03-contracts/') ? schemaFiles.filter((s) => t.includes(s)) : []
  const o = finalOutcome(r)
  return { rel: r, dir: r.includes('/') ? r.split('/')[0] : '(root)', lines: t.split('\n').length, status: f.status || '-', version: f.version || '-', updated: f.last_updated || f.date || '-', schema_version: f.schema_version || '', review: o ? o.review : '-', serious: o && o.serious != null ? o.serious : '-', group: o ? o.group : '-', owned, confirm: (t.match(/확인 필요/g) || []).length, openIssueCount: openIssues.filter((x) => x.source === path.basename(r)).length }
})

// ---- ledger markdown
const byDir = {}
for (const r of rows) (byDir[r.dir] = byDir[r.dir] || []).push(r)
const tot = { docs: rows.length, lines: rows.reduce((a, r) => a + r.lines, 0) }
const statusCount = {}; for (const r of rows) statusCount[r.status] = (statusCount[r.status] || 0) + 1
const reviewCount = {}; for (const r of rows) reviewCount[r.review] = (reviewCount[r.review] || 0) + 1
let md = `---
title: 3단계 문서 원장 (Phase 3 Document Ledger)
status: active
owner: architecture
version: 1.0.0
last_updated: ${DATE}
depends_on: ["00-progress-report.md"]
generated_by: tools/phase3/ledger.mjs
---

# 3단계 문서 원장

## 목적

3단계(설계 문서 작성)까지 생성된 모든 문서의 **실측 상태**를 한 표로 남긴다. 이 문서는 \`tools/phase3/ledger.mjs\`가 frontmatter·행 수·\`tools/phase3/results/*.json\`(워크플로우 결과)에서 기계 생성하며, 사람이 편집하지 않는다. 재생성: \`node tools/phase3/ledger.mjs --date <YYYY-MM-DD>\`.

## 범위

\`docs/**/*.md\`(업스트림 사본 \`12-appendix/sources/\` 제외)와 \`schemas/*.schema.json\`. 리뷰 결과 열은 결과 JSON에 기록된 **마지막** 처리 결과이며, 결과 JSON이 없는 문서(1·1b·2단계 산출물, 세션 중단으로 결과가 저장되지 않은 문서)는 "-"로 표시한다.

## 1. 요약

| 항목 | 값 |
|------|----|
| 문서 수 | ${tot.docs} |
| 총 행 수 | ${tot.lines.toLocaleString()} |
| JSON Schema | ${schemaFiles.length} |
| status 분포 | ${Object.entries(statusCount).map(([k, v]) => `${k} ${v}`).join(', ')} |
| 리뷰 결과 분포 | ${Object.entries(reviewCount).map(([k, v]) => `${REVIEW_KO[k] || k} ${v}`).join(', ')} |
| 미해결 이슈(결과 JSON 누적) | ${openIssues.length} (문서별 상세는 03-bible-amendment-triage-input.md) |
| "확인 필요" 표기 | ${rows.reduce((a, r) => a + r.confirm, 0)}곳 |

리뷰 결과 값의 의미: \`pass\` 리뷰 이슈 0 · \`verified\` 수정 후 독립 검증 통과 · \`fixed_twice\` 검증 미해결분 2차 수정 · \`minor_fixed\` minor만 수정 · \`fixed_unverified\` / \`fixed_from_prereview\` 경량 모드 수정(독립 검증 없음, 4단계 표본 검증 대상) · \`*_failed\` 해당 단계 에이전트 실패(4단계 재처리 대상).

## 2. 디렉터리별 원장
`
for (const d of Object.keys(byDir).sort()) {
  const rs = byDir[d]
  md += `\n### ${d} — ${rs.length}개, ${rs.reduce((a, r) => a + r.lines, 0).toLocaleString()}행\n\n| 문서 | 행 | status | version | 갱신일 | 리뷰 결과 | 심각 이슈 | 미해결 이슈 | 확인 필요 | ${d === '03-contracts' ? '소유 스키마 | ' : ''}결과 그룹 |\n|---|---:|---|---|---|---|---:|---:|---:|${d === '03-contracts' ? '---|' : ''}---|\n`
  for (const r of rs) md += `| ${path.basename(r.rel)} | ${r.lines} | ${r.status} | ${r.version} | ${r.updated} | ${REVIEW_KO[r.review] || r.review} | ${r.serious} | ${r.openIssueCount} | ${r.confirm} | ${d === '03-contracts' ? r.owned.join(', ') + ' | ' : ''}${r.group} |\n`
}
md += `\n## 3. 스키마 파일\n\n| 파일 | 소유 문서 |\n|---|---|\n`
for (const s of schemaFiles) { const owners = rows.filter((r) => r.owned.includes(s)).map((r) => path.basename(r.rel)); md += `| ${s} | ${owners.join(', ') || '(문서에서 미참조)'} |\n` }
md += `\n## 결정 사항 요약\n\n- 이 원장은 진행 보고서 §3의 근거 데이터이며, 두 문서가 다르면 원장(기계 생성)이 우선한다.\n\n## 미해결 이슈\n\n- \`*_failed\`·\`fixed_unverified\` 문서의 후속 처리는 4·5단계 계획 §2.3 D4-4를 따른다.\n\n## 참조\n\n- [진행 보고서](00-progress-report.md) · [4·5단계 계획](02-phase4-5-plan.md) · [바이블 개정 요청 통합 목록](03-bible-amendment-triage-input.md)\n`
fs.writeFileSync(path.join(DOCS, '12-appendix', '04-phase3-document-ledger.md'), md)

// ---- triage input
const BIBLE_RE = /(바이블|bible|§\s?\d)/i
const AMEND_RE = /(개정|반영|추가|제안|정정|갱신|수정|누락|불일치|충돌|모순)/
const secOf = (s) => { const m = /§\s?(\d+(?:\.\d+)*)/.exec(s); return m ? m[1] : '' }
const norm = (s) => s.replace(/\s+/g, ' ').trim()
const seen = new Set(); const items = []
for (const it of openIssues) { const k = norm(it.text).slice(0, 160); if (seen.has(k)) continue; seen.add(k); items.push({ ...it, bible: BIBLE_RE.test(it.text) && AMEND_RE.test(it.text), sec: secOf(it.text) }) }
const bibleItems = items.filter((i) => i.bible).sort((a, b) => (a.sec || 'zz').localeCompare(b.sec || 'zz', undefined, { numeric: true }) || a.source.localeCompare(b.source))
const otherItems = items.filter((i) => !i.bible).sort((a, b) => a.source.localeCompare(b.source))
let tri = `---
title: 바이블 개정 요청 통합 목록 (4단계 트리아지 입력)
status: active
owner: architecture
version: 1.0.0
last_updated: ${DATE}
depends_on: ["04-phase3-document-ledger.md", "../02-architecture/00-design-bible.md"]
generated_by: tools/phase3/ledger.mjs
---

# 바이블 개정 요청 통합 목록

## 목적

3단계 에이전트들이 각 문서의 "## 미해결 이슈"와 결과 JSON \`openIssues\`에 남긴 항목 전부를 한 곳에 모아, 4단계 T1(Opus 트리아지)의 **단일 입력**으로 쓴다. 트리아지 에이전트는 결과 JSON을 다시 열지 않고 이 문서만 읽는다(앵커 읽기 비용 절감). 기계 생성 문서이며 재생성은 \`node tools/phase3/ledger.mjs\`.

## 범위

결과 JSON ${fs.existsSync(RES) ? fs.readdirSync(RES).filter((f) => f.endsWith('.json') && !f.startsWith('validator')).join(', ') : '(없음)'}. 중복(앞 160자 동일)은 1건으로 병합. "바이블 관련" 판정은 정규식(바이블/§ 언급 + 개정·반영·추가·불일치 등 동사)이며 트리아지에서 재분류될 수 있다.

## 1. 집계

| 구분 | 건수 |
|------|-----:|
| 전체 미해결 이슈(중복 제거) | ${items.length} |
| 바이블 관련(개정 요청 후보) | ${bibleItems.length} |
| 문서 내부·기타 | ${otherItems.length} |
| 계약 감사 정본 결정(이미 계약에 적용, 하류 전파 대상) | ${canonical.length} |

## 2. 바이블 개정 요청 후보 (바이블 절 순)

트리아지 판정 열은 T1 에이전트가 채운다: 채택(patch/minor/major) · 기각 · 보류(ADR-0039+).

| # | 바이블 절 | 출처 문서 | 결과 그룹 | 요청 내용 | 판정 |
|--:|---|---|---|---|---|
`
bibleItems.forEach((i, n) => { tri += `| ${n + 1} | ${i.sec ? '§' + i.sec : '-'} | ${i.source} | ${i.group} | ${norm(i.text).replace(/\|/g, '\\|')} | |\n` })
tri += `\n## 3. 계약 감사 정본 결정 (하류 문서 전파 대상)\n\n계약 감사(\`contracts-audit\`)가 03-contracts와 schemas/에는 이미 적용한 결정이다. 04-pipelines·05-api·08~11 문서가 같은 필드·열거를 쓰는 곳에 전파해야 한다.\n\n| # | 결정 |\n|--:|---|\n`
canonical.forEach((c, n) => { tri += `| ${n + 1} | ${norm(c).replace(/\|/g, '\\|')} |\n` })
tri += `\n## 4. 문서 내부·기타 미해결 이슈 (출처 문서 순)\n\n바이블 개정이 아닌 항목(문서 자체 보강, 외부 확인 필요, 다른 문서 소유자 결정 대기). 4단계 P1 전파 에이전트가 해당 문서를 다룰 때 함께 처리한다.\n\n| # | 출처 문서 | 결과 그룹 | 내용 |\n|--:|---|---|---|\n`
otherItems.forEach((i, n) => { tri += `| ${n + 1} | ${i.source} | ${i.group} | ${norm(i.text).replace(/\|/g, '\\|')} |\n` })
tri += `\n## 결정 사항 요약\n\n- 이 목록이 4단계 T1의 유일한 입력이다. T1 이후 새로 발생하는 요청은 4단계 백로그로 넘긴다.\n\n## 미해결 이슈\n\n- "바이블 관련" 자동 판정의 오분류는 T1에서 정정한다.\n\n## 참조\n\n- [3단계 문서 원장](04-phase3-document-ledger.md) · [4·5단계 계획](02-phase4-5-plan.md) · [설계 바이블](../02-architecture/00-design-bible.md)\n`
fs.writeFileSync(path.join(DOCS, '12-appendix', '03-bible-amendment-triage-input.md'), tri)
console.log(`ledger: ${rows.length} docs, ${tot.lines} lines; outcomes for ${Object.keys(outcomes).length} docs; open issues ${openIssues.length} → unique ${items.length} (bible ${bibleItems.length}); canonical ${canonical.length}`)
