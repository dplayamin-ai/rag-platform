#!/usr/bin/env node
// 코드 헤더 검사기 — 모든 소스 파일 첫 줄의 docstring/주석 블록이 한국어 설명 헤더 규칙의 필수 항목 5개를 담고 있는지 기계적으로 검사한다(LLM 미사용, 결정적).
// 설계 근거: `tools/phase6/CODE-HEADER-RULE.md`(적용 대상 §, 규칙 2 언어, 규칙 4 필수 항목 순서 고정 — 역할/설계 근거/구성/불변식·주의/검증 계층, 규칙 8 "한국어 여부·필수 항목은 tools/verify/check-headers.mjs가 검사한다").
// 구성:
//   - `HEADER_GLOBS` — 검사 대상 확장자별 루트(`src/**/*.py`, `tests/**/*.py`, `tools/**/*.py`, `tools/**/*.mjs`, `tools/**/*.js`, `sdk/**/*.ts`)
//   - `extractPyHeader`/`extractCLikeHeader` — 파일 맨 앞(shebang/인코딩 선언 제외)의 모듈 docstring 또는 `//`·`/** */` 주석 블록만 추출
//   - `checkHeader` — Hangul 존재 여부 + 필수 항목 5개(역할/설계 근거/구성/불변식/검증 계층) 부분 문자열 포함 여부 판정
//   - `finish` — 위반 파일 목록·사유 출력, `--json` 저장, 오류 유무로 종료 코드 결정
// 불변식·주의: 정본은 `CODE-HEADER-RULE.md`이며, 이 스크립트는 그 규칙의 필수 항목 존재만 기계적으로 확인한다(문장 품질·정확성은 사람이 판단). 헤더를 고치지 않는다(읽기 전용 검사).
// 검증 계층: 1층(여기서 검증). 실행: `node tools/verify/check-headers.mjs [--root <repo>] [--json out.json] [--quiet]`
import fs from 'node:fs'
import path from 'node:path'

const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const ROOT = opt('--root', process.cwd())
const JSON_OUT = opt('--json', null)
const QUIET = argv.includes('--quiet')

const HANGUL_RE = /[\uac00-\ud7a3]/
const SKIP_DIRS = new Set(['__pycache__', 'node_modules', '.venv', 'results', '.git', 'dist', 'build'])

const HEADER_TARGETS = [
  { dir: 'src', ext: '.py' },
  { dir: 'tests', ext: '.py' },
  { dir: 'tools', ext: '.py' },
  { dir: 'tools', ext: '.mjs' },
  { dir: 'tools', ext: '.js' },
  { dir: 'sdk', ext: '.ts' },
]

function walk(dir, ext, out = []) {
  if (!fs.existsSync(dir)) return out
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(e.name)) continue
    const p = path.join(dir, e.name)
    if (e.isDirectory()) walk(p, ext, out)
    else if (p.endsWith(ext)) out.push(p)
  }
  return out
}

const rel = (p) => path.relative(ROOT, p).split(path.sep).join('/')

// -------------------------------------------------------------- header extraction
function extractPyHeader(text) {
  const lines = text.split('\n')
  let i = 0
  if (lines[i] && lines[i].startsWith('#!')) i++
  while (lines[i] && /^#.*coding[:=]/.test(lines[i])) i++
  while (lines[i] !== undefined && lines[i].trim() === '') i++
  const first = lines[i]
  if (first === undefined) return null
  const m = /^\s*([ruRU]{0,2})("""|''')/.exec(first)
  if (!m) return null
  const quote = m[2]
  const startCol = m.index + m[0].length
  const rest = first.slice(startCol)
  const closeIdx = rest.indexOf(quote)
  if (closeIdx >= 0) return rest.slice(0, closeIdx) // single-line docstring
  const buf = [rest]
  let j = i + 1
  for (; j < lines.length; j++) {
    const idx = lines[j].indexOf(quote)
    if (idx >= 0) { buf.push(lines[j].slice(0, idx)); break }
    buf.push(lines[j])
  }
  return buf.join('\n')
}

function extractCLikeHeader(text) {
  const lines = text.split('\n')
  let i = 0
  if (lines[i] && lines[i].startsWith('#!')) i++
  while (lines[i] !== undefined && lines[i].trim() === '') i++
  if (lines[i] === undefined) return null
  if (/^\s*\/\*/.test(lines[i])) {
    const buf = []
    for (; i < lines.length; i++) {
      buf.push(lines[i])
      if (lines[i].includes('*/')) break
    }
    return buf.join('\n')
  }
  if (/^\s*\/\//.test(lines[i])) {
    const buf = []
    for (; i < lines.length && /^\s*\/\//.test(lines[i]); i++) buf.push(lines[i])
    return buf.join('\n')
  }
  return null
}

// "역할" is the opening description and, per `CODE-HEADER-RULE.md`'s own canonical examples, is not
// always given an explicit "역할:" label — it can simply be the header's first sentence/paragraph.
// So it is satisfied either by the literal label or by non-trivial Korean prose preceding the first
// occurrence of one of the other four (always-labelled) markers.
const OTHER_MARKERS = ['설계 근거', '구성', '불변식', '검증 계층']
function hasRole(header) {
  if (header.includes('역할')) return true
  const re = new RegExp(OTHER_MARKERS.join('|'))
  const idx = header.search(re)
  const lead = idx === -1 ? header : header.slice(0, idx)
  return lead.trim().length >= 8 && HANGUL_RE.test(lead)
}

function checkHeader(file) {
  const text = fs.readFileSync(file, 'utf8')
  if (text.trim() === '') return { ok: false, reasons: ['파일이 비어 있다 — 헤더 없음'] }
  const header = file.endsWith('.py') ? extractPyHeader(text) : extractCLikeHeader(text)
  if (header === null) return { ok: false, reasons: ['첫 줄에 docstring/주석 블록이 없다'] }
  const reasons = []
  if (!HANGUL_RE.test(header)) reasons.push('한국어 본문이 없다(한글 문자 미검출)')
  if (!hasRole(header)) reasons.push('필수 항목 누락: "역할"(명시 라벨 또는 선행 서술 없음)')
  for (const marker of OTHER_MARKERS) {
    if (!header.includes(marker)) reasons.push(`필수 항목 누락: "${marker}"`)
  }
  return { ok: reasons.length === 0, reasons }
}

// -------------------------------------------------------------- main
const files = []
for (const { dir, ext } of HEADER_TARGETS) walk(path.join(ROOT, dir), ext, files)
files.sort()
const seen = new Set()
const violations = []
let checked = 0
for (const f of files) {
  if (seen.has(f)) continue
  seen.add(f)
  checked++
  const { ok, reasons } = checkHeader(f)
  if (!ok) violations.push({ file: rel(f), reasons })
}

function finish() {
  const report = { root: ROOT, checked, violations }
  if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify(report, null, 2))
  if (!QUIET) {
    console.log(`# check-headers — checked=${checked} violations=${violations.length}`)
    for (const v of violations) {
      console.log(`FAIL ${v.file}`)
      for (const r of v.reasons) console.log(`  - ${r}`)
    }
    if (violations.length === 0) console.log('모든 파일이 헤더 규칙을 만족한다.')
  }
  process.exit(violations.length ? 1 : 0)
}
finish()
