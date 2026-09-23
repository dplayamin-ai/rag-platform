// 보류 검증 원장 생성기 — src/tests 소스에서 검증을 미룬 항목을 모아 문서로 기계 생성한다(LLM 미사용, 결정적).
// 설계 근거: `docs/12-appendix/05-phase6-implementation-kit-plan.md` §8(실행 환경 제약과 3층 검증 전략 —
// 층 2 `needs_docker`/층 2b `needs_model`/층 3 `needs_gpu`/네트워크 `needs_network`, 상태는 항상 "미검증"으로 시작).
// 구성: `walk()`로 `src/`·`tests/`의 `.py`를 모아, (1) `# DEFERRED: <...>` 주석 블록과 (2) 테스트 함수의
// `@pytest.mark.needs_*` 마커를 각각 수집해 위치·마커·설명을 딴 뒤, 표로 렌더링해
// `docs/12-appendix/09-deferred-verification-ledger.md`(위치|층|무엇|검증 방법|기대 결과|상태)로 저장한다.
// 불변식: 상태 열은 이 스크립트가 절대 낮추지 않는다(항상 신규 행만 "미검증"으로 시작하고, 기존 검증 결과는
// 사람이 손으로 갱신). 마커 없는 `# DEFERRED:`는 "미분류"로, 마커만 있고 인접 주석이 없으면 규약 위반으로 표시.
// 검증 계층: 1층(여기서 검증) — 산출 문서는 `tools/audit-docs.mjs`로 별도 감사.
// 실행: node tools/verify/gen-deferred-ledger.mjs [--root C:\Workspaces\rag-platform] [--date 2026-09-23]
import fs from 'node:fs'
import path from 'node:path'

const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const ROOT = opt('--root', 'C:\\Workspaces\\rag-platform')
const DATE = opt('--date', new Date().toISOString().slice(0, 10))
const OUT = path.join(ROOT, 'docs', '12-appendix', '09-deferred-verification-ledger.md')

const MARKERS = ['needs_docker', 'needs_model', 'needs_gpu', 'needs_network']
const TIER_LABEL = {
  needs_docker: '2 (Docker/Linux)',
  needs_model: '2b (모델 가중치)',
  needs_gpu: '3 (GPU)',
  needs_network: '네트워크',
}
const WHERE_HOW = {
  needs_docker: 'Docker/Linux 머신에서 compose lite 기동 후 `uv run pytest -m needs_docker` (`tools/verify/run-deferred.sh` 또는 `.ps1`)',
  needs_model: '모델 가중치 접근이 가능한 머신에서 실제 모델을 내려받아 `uv run pytest -m needs_model` (VDI에서는 다운로드 금지, 사용자 결정)',
  needs_gpu: 'CUDA GPU가 있는 머신에서 `uv run pytest -m needs_gpu`',
  needs_network: '외부 네트워크 접근이 허용된 환경에서 `uv run pytest -m needs_network`',
}
const EXPECTED = {
  needs_docker: '실제 백엔드(PostgreSQL/Valkey/Qdrant 등)에서 인메모리 대역(`testing.doubles.*`)과 동일한 계약 동작을 확인하고 적합성 테스트를 통과한다',
  needs_model: '실제 서빙 모델의 출력이 결정적 가짜 구현(`FakeEmbedder` 등)이 지키는 계약(차원·정규화 등)과 일치한다; 검색 품질 수치(nDCG 등)는 별도로 골든셋에서 측정한다',
  needs_gpu: 'GPU 경로의 처리량/정확도가 CPU 경로의 계약과 동일함을 확인한다',
  needs_network: '외부 서비스 호출이 성공하고 실패·재시도 경로가 계약대로 동작한다',
}

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === '__pycache__') continue
    const p = path.join(dir, e.name)
    if (e.isDirectory()) walk(p, out)
    else if (p.endsWith('.py')) out.push(p)
  }
  return out
}
const rel = (p) => path.relative(ROOT, p).split(path.sep).join('/')

const files = []
for (const d of ['src', 'tests']) {
  const abs = path.join(ROOT, d)
  if (fs.existsSync(abs)) walk(abs, files)
}
files.sort()

// ---- 1. `# DEFERRED:` comment blocks (module docstrings and inline comments alike; the trigger line is
// anchored at line-start so prose that merely *mentions* the token — e.g. tests/README.md's explanation of
// the convention — is never matched).
const commentRows = []
for (const p of files) {
  const text = fs.readFileSync(p, 'utf8')
  const lines = text.split('\n')
  for (let i = 0; i < lines.length; i++) {
    const m = /^\s*#\s*DEFERRED:\s*(.*)$/.exec(lines[i])
    if (!m) continue
    const startLine = i + 1
    const parts = [m[1]]
    let j = i + 1
    while (j < lines.length && /^\s*#\s?(.*)$/.test(lines[j])) {
      const cm = /^\s*#\s?(.*)$/.exec(lines[j])
      if (cm[1].trim() === '') break
      parts.push(cm[1])
      j++
    }
    const what = parts.join(' ').replace(/\s+/g, ' ').trim()
    // symbol for a readable location: prefer whichever backtick-quoted identifier from the comment
    // itself resolves to a class/def in this file (e.g. `Ledger`, `KeyValueCache`); otherwise fall
    // back to the nearest following `class` (preferred over a helper `def`) within 120 lines.
    let symbol = null
    const candidates = [...what.matchAll(/`([A-Za-z_][A-Za-z0-9_]*)`/g)].map((cm) => cm[1])
    for (const cand of candidates) {
      const re = new RegExp(`^\\s*(class|def)\\s+${cand}\\b`, 'm')
      const cm = re.exec(text)
      if (cm) { symbol = `${cm[1]} ${cand}`; break }
    }
    if (!symbol) {
      let firstClass = null, firstDef = null
      for (let k = j; k < Math.min(lines.length, j + 120); k++) {
        const sm = /^\s*(class|def)\s+([A-Za-z_][A-Za-z0-9_]*)/.exec(lines[k])
        if (!sm) continue
        if (sm[1] === 'class' && !firstClass) firstClass = sm[2]
        if (sm[1] === 'def' && !firstDef) firstDef = sm[2]
        if (firstClass) break
      }
      symbol = firstClass ? `class ${firstClass}` : firstDef ? `def ${firstDef}` : null
    }
    const markers = MARKERS.filter((mk) => new RegExp('`' + mk + '`|\\b' + mk + '\\b').test(what))
    commentRows.push({
      location: `${rel(p)}:${startLine}` + (symbol ? ` (${symbol})` : ''),
      markers: markers.length ? markers : null,
      what,
      source: 'comment',
    })
  }
}

// ---- 2. pytest attribute markers on test functions (currently none in the repo; scanned for completeness
// and so this generator keeps working once tier-2/2b/3 tests are added by a later work package).
const markerRows = []
for (const p of files) {
  if (!rel(p).startsWith('tests/')) continue
  const text = fs.readFileSync(p, 'utf8')
  const lines = text.split('\n')
  for (let i = 0; i < lines.length; i++) {
    const dm = /^\s*@pytest\.mark\.(needs_docker|needs_model|needs_gpu|needs_network)\b/.exec(lines[i])
    if (!dm) continue
    let name = null
    for (let k = i + 1; k < Math.min(lines.length, i + 6); k++) {
      const fm = /^\s*(?:async\s+)?def\s+(test_[A-Za-z0-9_]*)/.exec(lines[k])
      if (fm) { name = fm[1]; break }
    }
    // a preceding `# DEFERRED:` comment (within 5 lines above the decorator) supplies the "what" text
    let what = null
    for (let k = i - 1; k >= Math.max(0, i - 5); k--) {
      const cm = /^\s*#\s*DEFERRED:\s*(.*)$/.exec(lines[k])
      if (cm) { what = cm[1]; break }
    }
    markerRows.push({
      location: `${rel(p)}:${i + 1}` + (name ? ` (${name})` : ''),
      markers: [dm[1]],
      what: what || `\`@pytest.mark.${dm[1]}\` — 인접한 \`# DEFERRED:\` 주석 없음(코드 규약 위반, 보강 필요)`,
      source: 'marker',
    })
  }
}

const rows = [...commentRows, ...markerRows].sort((a, b) => a.location.localeCompare(b.location))

const tierLabelFor = (markers) => (markers ? markers.map((mk) => TIER_LABEL[mk]).join(' + ') : '미분류(마커 언급 없음, 수동 분류 필요)')
const whereHowFor = (markers) => (markers ? markers.map((mk) => WHERE_HOW[mk]).join('; ') : '`# DEFERRED:` 주석에 마커(`needs_docker`/`needs_model`/`needs_gpu`/`needs_network`)를 명시한 뒤 재생성')
const expectedFor = (markers) => (markers ? markers.map((mk) => EXPECTED[mk]).join('; ') : '분류 후 결정')

const counts = { needs_docker: 0, needs_model: 0, needs_gpu: 0, needs_network: 0, unclassified: 0 }
for (const r of rows) { if (!r.markers) { counts.unclassified++; continue } for (const mk of r.markers) counts[mk]++ }

let md = `---
title: 보류 검증 원장 (Deferred Verification Ledger)
status: active
owner: architecture
version: 1.0.0
last_updated: ${DATE}
depends_on: ["05-phase6-implementation-kit-plan.md", "../10-development/05-ci-cd.md"]
generated_by: tools/verify/gen-deferred-ledger.mjs
---

# 보류 검증 원장

## 목적

Windows VDI(Docker·WSL·GPU 없음)에서 작성했지만 이 머신에서는 실행 검증할 수 없는 항목을 한 곳에 모은다. 항목은 \`src/\`·\`tests/\`의 \`# DEFERRED: <무엇을 어디서 어떻게 검증>\` 주석과 pytest 속성 마커(\`needs_docker\`·\`needs_model\`·\`needs_gpu\`·\`needs_network\`)에서 \`tools/verify/gen-deferred-ledger.mjs\`가 기계 생성하며, 사람이 표를 직접 편집하지 않는다(재생성: \`node tools/verify/gen-deferred-ledger.mjs\`). Docker가 있는 머신에서 검증을 마친 뒤에는 원본 주석과 이 문서의 상태 열을 함께 갱신하고 재생성한다.

## 범위

\`src/**/*.py\`·\`tests/**/*.py\`(\`__pycache__\` 제외) 전체. 3층 검증 전략(\`docs/12-appendix/05-phase6-implementation-kit-plan.md\` §8)의 층 2(Docker/Linux)·층 2b(모델 가중치)·층 3(GPU)와, 마커 목록에는 없지만 외부 네트워크가 필요한 항목(\`needs_network\`)을 포함한다. 층 1(순수 Python·단위 테스트·계약 왕복·Qdrant 로컬 모드·ONNX CPU·FastAPI TestClient)은 이 VDI에서 이미 실행 검증했으므로 이 원장에 없다.

## 1. 요약

| 항목 | 건수 |
|------|-----:|
| 전체 보류 항목 | ${rows.length} |
| 층 2 — \`needs_docker\` | ${counts.needs_docker} |
| 층 2b — \`needs_model\` | ${counts.needs_model} |
| 층 3 — \`needs_gpu\` | ${counts.needs_gpu} |
| 네트워크 — \`needs_network\` | ${counts.needs_network} |
| 미분류(마커 언급 없이 \`# DEFERRED:\`만 있음) | ${counts.unclassified} |
| \`# DEFERRED:\` 주석에서 수집 | ${commentRows.length} |
| pytest 속성 마커에서 수집 | ${markerRows.length}${markerRows.length === 0 ? ' (2026-09-23 기준 코드에 마커 데코레이터가 아직 없다 — M1 lite 구현이 진행되며 늘어난다)' : ''} |

## 2. 보류 항목

| 위치 | 층 | 무엇 | 어디서·어떻게 검증 | 기대 결과 | 상태 |
|---|---|---|---|---|---|
`
for (const r of rows) {
  const esc = (s) => String(s).replace(/\|/g, '\\|').replace(/\n/g, ' ')
  md += `| ${esc(r.location)} | ${esc(tierLabelFor(r.markers))} | ${esc(r.what)} | ${esc(whereHowFor(r.markers))} | ${esc(expectedFor(r.markers))} | 미검증 |\n`
}
md += `
## 결정 사항 요약

- 이 원장의 모든 행은 최초 생성 시 상태 \`미검증\`으로 시작한다(05-phase6-implementation-kit-plan.md §8 D6-1). 다른 머신에서 \`tools/verify/run-deferred.sh\`(또는 \`.ps1\`)를 실행해 통과한 항목만 상태를 \`검증됨\`으로 바꾸고, 실패한 항목은 원인과 함께 \`검증 실패\`로 남긴다.
- \`needs_model\`은 모델 가중치 다운로드가 전제이며, VDI에서는 사용자 결정으로 다운로드하지 않는다. 다른 머신에서도 다운로드 여부는 매번 사용자 결정을 따른다.

## 미해결 이슈

- 미분류 항목(마커 언급이 없는 \`# DEFERRED:\` 주석)이 있으면 주석에 해당 마커를 명시하고 재생성한다.
- pytest 속성 마커가 있는데 인접한 \`# DEFERRED:\` 주석이 없는 테스트는 코드 규약(05-phase6-implementation-kit-plan.md §8) 위반이며 주석을 보강해야 한다.

## 참조

- [6단계 실행 계획](05-phase6-implementation-kit-plan.md) §8 · [CI/CD](../10-development/05-ci-cd.md) · [테스트 전략](../10-development/04-testing-strategy.md) · 루트 [HANDOFF.md](../../HANDOFF.md)
`
fs.mkdirSync(path.dirname(OUT), { recursive: true })
fs.writeFileSync(OUT, md)
console.log(`deferred ledger: ${rows.length} items (docker ${counts.needs_docker}, model ${counts.needs_model}, gpu ${counts.needs_gpu}, network ${counts.needs_network}, unclassified ${counts.unclassified}) -> ${rel(OUT)}`)
