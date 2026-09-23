// 요구사항 추적 매트릭스 생성기 — `docs/12-appendix/06-traceability-matrix.md`를 결정론적으로(LLM 없이) 만든다. `01-requirements/`에 정의된 모든 `FR`/`NFR`/`UC`/`US` ID가 설계 문서(02~11, `01-requirements`·`12-appendix` 제외)에서 인용되는지와 `11-roadmap/02-epics-and-backlog.md`의 어느 태스크에 매핑되는지 집계한다.
// 설계 근거: 완전성 검토 `12-appendix/01-phase3-completeness-review.md` §3 누락 #4(FR 74% 미인용), 4·5단계 계획 `02-phase4-5-plan.md` §2.3, 전파 지시서 `12-appendix/08-propagation-directives.md` §1(매 편집 시 frontmatter `version` patch 증가·`last_updated` 갱신).
// 구성:
//   - `defs` 수집 — 01-requirements 표 첫 열·제목에서 ID 정의 추출
//   - `cites`/`undefinedRefs` 집계 — 설계 문서 본문에서 ID 언급 스캔
//   - `epicOf` — 로드맵(11-roadmap/02)의 같은 행 태스크 ID 매핑
//   - 본문(md) 조립·저장 — frontmatter 포함, 기존 버전에서 patch 증가
// 불변식·주의: 이 매트릭스가 추적성의 정본이다 — 인용률을 올리기 위한 형식적 인용은 금지한다. 재생성은 항상 파일을 덮어쓴다(수동 편집 금지).
// 검증 계층: 1층(여기서 검증, 콘솔 출력의 `undefinedRefs`·인용률로 확인). 실행: `node tools/traceability.mjs [--root <repo>] [--date YYYY-MM-DD]`
import fs from 'node:fs'
import path from 'node:path'
const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const ROOT = opt('--root', 'C:\\Workspaces\\rag-platform')
const DATE = opt('--date', new Date().toISOString().slice(0, 10))
const DOCS = path.join(ROOT, 'docs')
const TARGET = path.join(DOCS, '12-appendix', '06-traceability-matrix.md')
// version: patch-bump from whatever is currently on disk (propagation directives §1: version patch + last_updated on every edit)
let VERSION = opt('--version', null)
if (!VERSION) {
  VERSION = '1.0.0'
  try {
    const vm = /^version:\s*(\d+)\.(\d+)\.(\d+)/m.exec(fs.readFileSync(TARGET, 'utf8'))
    if (vm) VERSION = `${vm[1]}.${vm[2]}.${Number(vm[3]) + 1}`
  } catch { /* first generation */ }
}
function walk(d, out = []) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p, out); else if (p.endsWith('.md')) out.push(p) } return out }
const rel = (p) => path.relative(DOCS, p).split(path.sep).join('/')
const files = walk(DOCS).filter((p) => !rel(p).startsWith('12-appendix/'))
const ID_RE = /\b(FR|NFR)-[A-Z]{2,4}-\d{2,3}\b|\bUC-\d{2}\b|\bUS-[A-Z]{2,4}-\d{2,3}\b/g
// A1: titles are sourced from 01-requirements/*.md; a same-directory link (`./foo.md`) there is only
// valid relative to 01-requirements/. Rewrite it so the copied title stays correct from 12-appendix/.
const fixTitleLinks = (s) => s.replace(/\]\(\.\//g, '](../01-requirements/')
// definitions: first column of a table row in 01-requirements docs, or heading
const defs = {} // id -> {file, title}
for (const p of files.filter((p) => rel(p).startsWith('01-requirements/'))) {
  const t = fs.readFileSync(p, 'utf8')
  for (const line of t.split('\n')) {
    const m = /^\|\s*(\*\*)?((?:FR|NFR)-[A-Z]{2,4}-\d{2,3}|UC-\d{2}|US-[A-Z]{2,4}-\d{2,3})(\*\*)?\s*\|\s*([^|]*)\|/.exec(line)
    if (m && !defs[m[2]]) defs[m[2]] = { file: rel(p), title: fixTitleLinks(m[4].trim().replace(/\*\*/g, '')).slice(0, 80) }
    const h = /^#{2,4}\s+((?:FR|NFR)-[A-Z]{2,4}-\d{2,3}|UC-\d{2}|US-[A-Z]{2,4}-\d{2,3})\b[:\s]*(.*)$/.exec(line)
    if (h && !defs[h[1]]) defs[h[1]] = { file: rel(p), title: fixTitleLinks(h[2].trim()).slice(0, 80) }
  }
}
// citations in design docs
const cites = {} // id -> Set(files)
const undefinedRefs = {} // id -> Set(files)
for (const p of files.filter((p) => !rel(p).startsWith('01-requirements/'))) {
  const t = fs.readFileSync(p, 'utf8')
  for (const m of t.matchAll(ID_RE)) { const id = m[0]; if (defs[id]) (cites[id] = cites[id] || new Set()).add(rel(p)); else (undefinedRefs[id] = undefinedRefs[id] || new Set()).add(rel(p)) }
}
// roadmap epic/task mapping
const roadmap = files.find((p) => rel(p) === '11-roadmap/02-epics-and-backlog.md')
const epicOf = {} // id -> Set(task or epic ids)
if (roadmap) {
  for (const line of fs.readFileSync(roadmap, 'utf8').split('\n')) {
    const ids = [...line.matchAll(ID_RE)].map((m) => m[0]).filter((id) => defs[id]); if (!ids.length) continue
    const task = (line.match(/\bT-[A-Z]{2,4}-\d{2,3}\b/) || line.match(/\bE-?\d{1,2}\b|에픽\s*\d{1,2}/) || [''])[0]
    for (const id of ids) (epicOf[id] = epicOf[id] || new Set()).add(task || '(로드맵 02 언급)')
  }
}
const groups = { FR: [], NFR: [], UC: [], US: [] }
for (const id of Object.keys(defs).sort()) groups[id.split('-')[0]].push(id)
const stat = (ids) => { const cited = ids.filter((i) => cites[i] && cites[i].size).length; return { total: ids.length, cited, pct: ids.length ? Math.round((cited / ids.length) * 100) : 0 } }
let md = `---
title: 요구사항 추적 매트릭스 (Traceability Matrix)
status: active
owner: architecture
version: ${VERSION}
last_updated: ${DATE}
depends_on: ["../01-requirements/01-functional-requirements.md", "../01-requirements/02-non-functional-requirements.md", "../11-roadmap/02-epics-and-backlog.md"]
generated_by: tools/traceability.mjs
---

# 요구사항 추적 매트릭스

## 목적

01-requirements가 정의한 모든 FR·NFR·UC·US ID에 대해 **어느 설계 문서(02~11)가 인용하는지**와 로드맵 백로그(11-roadmap/02)의 어느 태스크가 구현하는지를 기계적으로 집계한다. 3단계 완전성 검토 누락 #4(FR 74% 미인용)에 대한 대응이며, 문서 본문에 인용을 억지로 추가하는 대신 이 매트릭스가 추적성의 정본이 된다. 재생성: \`node tools/traceability.mjs --date <날짜>\`.

## 범위

정의: 01-requirements/01·02·03·04의 표 첫 열 또는 제목의 ID. 인용: docs/ 아래 01-requirements와 12-appendix를 제외한 모든 문서의 본문. 로드맵 매핑: 11-roadmap/02의 같은 행에 등장하는 태스크 ID(\`T-XXX-nn\`).

## 1. 집계

| 구분 | 정의 | 설계 문서 인용 | 인용률 |
|------|-----:|-----:|-----:|
${Object.entries(groups).map(([k, ids]) => { const s = stat(ids); return `| ${k} | ${s.total} | ${s.cited} | ${s.pct}% |` }).join('\n')}

미정의 ID 인용(설계 문서가 쓰지만 요구사항 문서에 없음): ${Object.keys(undefinedRefs).length}건 — ${Object.entries(undefinedRefs).map(([id, s]) => `${id}(${[...s].map((f) => f.split('/').pop()).join(', ')})`).join('; ') || '없음'}

## 2. 매트릭스
`
for (const [k, ids] of Object.entries(groups)) {
  if (!ids.length) continue
  md += `\n### ${k} (${ids.length})\n\n| ID | 제목 | 정의 문서 | 인용 설계 문서 | 로드맵 태스크 |\n|---|---|---|---|---|\n`
  for (const id of ids) {
    const c = cites[id] ? [...cites[id]].map((f) => f.replace(/\.md$/, '')).sort() : []
    const e = epicOf[id] ? [...epicOf[id]].sort() : []
    md += `| ${id} | ${defs[id].title.replace(/\|/g, '\\|')} | ${defs[id].file.split('/').pop()} | ${c.length ? c.join(', ') : '**미인용**'} | ${e.join(', ') || '-'} |\n`
  }
}
md += `\n## 결정 사항 요약\n\n- **결정:** 추적성의 정본은 이 매트릭스다. 설계 문서는 관련 요구사항을 자연스럽게 인용하되, 인용률을 올리기 위한 형식적 인용은 금지한다.\n\n## 미해결 이슈\n\n- 미인용 요구사항은 (a) 실제로 어느 설계 문서도 다루지 않는 갭인지, (b) 다루지만 ID를 쓰지 않은 것인지 4단계 P1에서 표본 판정한다.\n\n## 참조\n\n- [기능 요구사항](../01-requirements/01-functional-requirements.md) · [비기능 요구사항](../01-requirements/02-non-functional-requirements.md) · [에픽과 백로그](../11-roadmap/02-epics-and-backlog.md) · [3단계 완전성 검토](01-phase3-completeness-review.md)\n`
fs.writeFileSync(TARGET, md)
console.log(JSON.stringify({ defs: Object.keys(defs).length, stats: Object.fromEntries(Object.entries(groups).map(([k, ids]) => [k, stat(ids)])), undefinedRefs: Object.keys(undefinedRefs) }))
