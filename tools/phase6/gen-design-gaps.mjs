// 구현 설계 갭 원장 생성기 — 6단계(6B·6D·6F F1~F5) 에이전트가 결과로 남긴 `open_issues`(설계 갭·계약 충돌·공용
// 파일 변경 요청)와 Opus 리뷰 `findings`를 한 문서(`docs/12-appendix/10-implementation-design-gaps.md`)로 렌더링한다.
// 설계 근거: 진행 보고서 §7.2h(구현 중 발견한 갭은 코드가 바이블을 앞서 바꾸지 않고 기록만 남겨 다음 바이블 패치
// 입력으로 모은다), `05-phase6-implementation-kit-plan.md` §1(스크립트가 먼저, LLM은 판단에만), CLAUDE.md §5 문서 규약.
// 구성: `loadItems`(입력 JSON 읽기·정규화) → `classify`(키워드 휴리스틱 분류: 바이블 개정·계약/스키마·SDK 포트·
// 보류 검증·후속 마일스톤·기타) → `render`(frontmatter + 요약 표 + 배치별 표 + 리뷰 findings 표) → 파일 쓰기.
// 불변식·주의: 입력 정본은 `tools/phase6/results/open-issues.json`(워크플로우 journal의 result 페이로드를 추출한 사본)
// 이며 사람이 표를 직접 편집하지 않는다(재생성: `node tools/phase6/gen-design-gaps.mjs`). 분류 열은 휴리스틱이므로
// 바이블 트리아지 때 사람이 다시 판정한다. 표 셀의 `|`와 줄바꿈은 이스케이프한다.
// 검증 계층: 1층(여기서 검증) — 실행 후 `node tools/audit-docs.mjs`(A1 링크·A2 frontmatter)로 결과 문서를 검사한다.
import fs from 'node:fs'
import path from 'node:path'

const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const ROOT = opt('--root', path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..', '..'))
const IN = opt('--in', path.join(ROOT, 'tools', 'phase6', 'results', 'open-issues.json'))
const OUT = opt('--out', path.join(ROOT, 'docs', '12-appendix', '10-implementation-design-gaps.md'))

const BATCH_TITLE = {
  '6BD': '6B 적합성 키트 · 6D 어댑터 스파이크(HWPX·Qdrant·임베더)',
  F1: 'F1 수집 전단(fetch·판별/라우터·TXT/MD/CSV·HTML·PDF·한국어 정규화)',
  F2: 'F2 청킹·보강',
  F3: 'F3 임베딩·인덱스 커밋·수집 e2e',
  F4: 'F4 검색 경로(플래너·채널·융합·후처리·패킹·렌더)',
  F5: 'F5 API·MCP·CLI·전체 e2e',
}
const BATCH_ORDER = ['6BD', 'F1', 'F2', 'F3', 'F4', 'F5']
const CLASSES = [
  ['바이블 개정 후보', /바이블|bible|§\d|ADR-\d{4}|정본|문구/],
  ['계약·스키마', /계약|스키마|schema|contract|\bSemver\b|RootModel|nullable|열거|enum/i],
  ['SDK 포트·공용 파일', /포트|port|sdk\/|ports\.py|StageContext|PipelineContext|doubles|pyproject|공용 파일/i],
  ['보류 검증(층 2·2b·3)', /DEFERRED|needs_docker|needs_model|needs_gpu|needs_network|Docker|모델 가중치|서버 모드|compose/i],
  ['후속 마일스톤(M2+)', /M2|M3|후속 WP|후속 과제|standard|premium|OpenSearch|리랭커|rerank|Temporal|사이드카|sidecar/i],
]
function classify(text) {
  for (const [name, re] of CLASSES) if (re.test(text)) return name
  return '기타(구현 메모)'
}
function cell(s) { return String(s ?? '').replace(/\r?\n+/g, ' ').replace(/\|/g, '\\|').trim() }

function loadItems() {
  const j = JSON.parse(fs.readFileSync(IN, 'utf8'))
  const items = (j.items || []).map((it, i) => ({ ...it, n: i + 1, cls: classify(it.text) }))
  return { meta: j, items, reviews: j.reviews || [] }
}

function render({ meta, items, reviews }) {
  const byBatch = new Map(BATCH_ORDER.map((b) => [b, []]))
  for (const it of items) { if (!byBatch.has(it.batch)) byBatch.set(it.batch, []); byBatch.get(it.batch).push(it) }
  const clsCount = new Map()
  for (const it of items) clsCount.set(it.cls, (clsCount.get(it.cls) || 0) + 1)
  const findingsTotal = reviews.reduce((a, r) => a + r.findings.length, 0)
  const sev = (r) => r.findings.reduce((m, f) => { m[f.severity || '?'] = (m[f.severity || '?'] || 0) + 1; return m }, {})

  let md = `---
title: 구현 설계 갭 원장 (Implementation Design-Gap Ledger)
status: active
owner: architecture
version: 1.0.0
last_updated: ${meta.generated_at || '2026-09-24'}
depends_on: ["00-progress-report.md", "05-phase6-implementation-kit-plan.md", "../13-implementation/README.md", "../02-architecture/00-design-bible.md"]
generated_by: tools/phase6/gen-design-gaps.mjs
---

# 구현 설계 갭 원장

## 목적

6단계(6B 적합성 키트, 6D 어댑터 스파이크, 6E·6F 배치 F1~F5)에서 코드를 쓰던 에이전트가 "설계 문서대로 구현할 수 없거나, 문서끼리 어긋나거나, 공용 파일·포트를 바꿔야 한다"고 남긴 미해결 항목(\`open_issues\`)과 Opus 리뷰의 발견(\`findings\`)을 한 곳에 모은다. 코드가 바이블을 앞서 바꾸지 않는다는 원칙(CLAUDE.md §3)에 따라 이 항목들은 구현 중 고치지 않고 기록만 했으며, **다음 바이블 패치(ADR 선행)의 입력**이다. 이 문서는 \`tools/phase6/results/open-issues.json\`에서 \`tools/phase6/gen-design-gaps.mjs\`가 기계 생성하며 표를 직접 편집하지 않는다.

## 범위

워크플로우 Run ${meta.runs.map((r) => `\`${r}\``).join(', ')}의 에이전트 결과 페이로드(구현·검증·리뷰 수정 에이전트의 \`open_issues\`, Opus 리뷰의 \`findings\`). 6A 골격의 미해결 항목은 진행 보고서 §7.2f에, 층 2·2b·3 보류 검증 항목은 [보류 검증 원장](09-deferred-verification-ledger.md)에 따로 있다. "분류" 열은 키워드 휴리스틱이며 트리아지 때 사람이 다시 판정한다.

## 1. 요약

| 배치 | 미해결 항목 |
|------|-----------:|
${BATCH_ORDER.filter((b) => byBatch.get(b).length).map((b) => `| ${BATCH_TITLE[b] || b} | ${byBatch.get(b).length} |`).join('\n')}
| **합계** | **${items.length}** |

| 분류(휴리스틱) | 건수 |
|------|-----:|
${[...clsCount.entries()].sort((a, b) => b[1] - a[1]).map(([k, v]) => `| ${k} | ${v} |`).join('\n')}

Opus 리뷰 발견 ${findingsTotal}건(${reviews.map((r) => `${r.batch} ${r.findings.length}건 — ${Object.entries(sev(r)).map(([k, v]) => `${k} ${v}`).join(', ')}`).join('; ')})은 §3에 있으며, 전부 같은 배치의 리뷰 수정 WP(F4 → WP-405, F5 → WP-504)에서 수정·회귀 테스트됐다. 따라서 §3은 "남은 일"이 아니라 "설계 문서가 놓치기 쉬운 지점"의 기록이다.

## 2. 배치별 미해결 항목
`
  for (const b of BATCH_ORDER) {
    const rows = byBatch.get(b)
    if (!rows.length) continue
    md += `\n### 2.${BATCH_ORDER.indexOf(b) + 1} ${BATCH_TITLE[b] || b} (${rows.length}건)\n\n| # | 출처(에이전트 · WP) | 내용 | 분류 |\n|--:|------|------|------|\n`
    for (const it of rows) md += `| ${it.n} | ${cell(it.label)}${it.wp ? ` · ${cell(it.wp)}` : ''} | ${cell(it.text)} | ${it.cls} |\n`
  }
  md += `\n## 3. Opus 리뷰 발견(수정 완료)\n`
  for (const r of reviews) {
    md += `\n### 3.${reviews.indexOf(r) + 1} ${r.batch} — 판정 \`${r.verdict}\`, ${r.findings.length}건 (Run \`${r.run}\`)\n\n| # | 심각도 | 파일 | 문제 | 수정 방향 |\n|--:|------|------|------|------|\n`
    r.findings.forEach((f, i) => { md += `| ${i + 1} | ${cell(f.severity)} | \`${cell(f.file)}\` | ${cell(f.problem)} | ${cell(f.fix)} |\n` })
  }
  md += `
## 결정 사항 요약

- 구현 중 발견한 설계 갭은 코드에서 임시 근사(예: 기본값 채택, 포트 부재 시 직접 읽기)로 처리하고 여기에 기록만 남긴다. 바이블·계약 수정은 ADR 선행 절차(CLAUDE.md §3)로 일괄 처리한다.
- 리뷰 발견은 같은 배치 안에서 수정 WP(WP-405·WP-504)로 즉시 반영했다 — 보안·ACL 의미론(E1~E17)은 다음 배치로 미루지 않는다.

## 미해결 이슈

- 본문 §2 전체(${items.length}건)가 미해결이다. 다음 바이블 패치 트리아지에서 "바이블 개정 후보"와 "계약·스키마" 분류를 먼저 다루고, "SDK 포트·공용 파일"은 6단계 후속 WP(6xx)로, "보류 검증"은 [보류 검증 원장](09-deferred-verification-ledger.md)과 합쳐 다른 머신에서 처리한다.
- 휴리스틱 분류의 오탐·누락은 트리아지 결과 문서에서 바로잡고 이 문서는 재생성만 한다.

## 참조

- [진행 보고서](00-progress-report.md) §7.2g·§7.2h · [6단계 구현 킷 계획](05-phase6-implementation-kit-plan.md) · [작업 패키지 색인](../13-implementation/README.md) · [보류 검증 원장](09-deferred-verification-ledger.md) · [바이블 개정 트리아지 결정(4단계)](07-bible-amendment-triage-decisions.md)
`
  return md
}

const data = loadItems()
fs.writeFileSync(OUT, render(data))
console.log(`# gen-design-gaps — items=${data.items.length} reviews=${data.reviews.length} → ${path.relative(ROOT, OUT)}`)
