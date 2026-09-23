// Whole-docs mechanical audit for Phase 4 (2026-09-23). No LLM.
// Checks A1 links, A2 frontmatter, A3 enum/type spelling & rejected names, A4 ID prefix map, A5 length, A6 status,
//        A7 citation integrity (ADR/D/O/FR/NFR/UC/US), A8 "확인 필요" counts, A9 schema inventory vs bible §5.1.
// Usage: node tools/audit-docs.mjs [--root <repo>] [--json out.json] [--md out.md] [--fix]
//   --fix applies only safe edits: missing frontmatter version → 0.1.0; status review→active for docs whose last
//   result JSON outcome is a completed review/fix (non-ADR); nothing else is modified.
import fs from 'node:fs'
import path from 'node:path'
const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const FIX = argv.includes('--fix')
const ROOT = opt('--root', 'C:\\Workspaces\\rag-platform')
const DOCS = path.join(ROOT, 'docs'), SCHEMAS = path.join(ROOT, 'schemas'), RES = path.join(ROOT, 'tools', 'phase3', 'results')
const rel = (p) => path.relative(DOCS, p).split(path.sep).join('/')
function walk(d, out = []) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p, out); else if (p.endsWith('.md')) out.push(p) } return out }
const files = walk(DOCS).filter((p) => !rel(p).startsWith('12-appendix/sources/')).sort()
const texts = Object.fromEntries(files.map((p) => [p, fs.readFileSync(p, 'utf8')]))
function fmParse(t) { if (!t.startsWith('---')) return null; const e = t.indexOf('\n---', 3); if (e < 0) return null; const o = {}; for (const l of t.slice(3, e).split('\n')) { const m = /^([a-z_]+):\s*(.*)$/.exec(l); if (m) o[m[1]] = m[2].trim() } return { o, end: e } }
const stripCode = (t) => t.replace(/```[\s\S]*?```/g, (m) => m.replace(/[^\n]/g, ' ')) // keep line numbers
const lineOf = (t, idx) => t.slice(0, idx).split('\n').length
const report = { date: new Date().toISOString(), root: ROOT, A1_links: [], A2_frontmatter: [], A3_spelling: [], A4_id_prefix: {}, A5_length: [], A6_status: [], A7_citations: [], A8_confirm: [], A9_schema_inventory: {}, fixes: [] }

// ---- A1 links
for (const p of files) {
  const t = texts[p]
  for (const m of t.matchAll(/\]\(([^)\s]+)\)/g)) {
    let tgt = m[1]; if (/^(https?:|mailto:|#|urn:)/.test(tgt)) continue
    if (/[\[\](){}*\\]/.test(tgt) || !/\.(md|json|yaml|yml)$|\/$/.test(tgt.split('#')[0])) continue // skip code fragments and non-file targets
    tgt = tgt.split('#')[0]; if (!tgt) continue
    const abs = path.resolve(path.dirname(p), tgt)
    if (!fs.existsSync(abs)) report.A1_links.push({ file: rel(p), line: lineOf(t, m.index), target: m[1] })
  }
}
// ---- A2 frontmatter
const isAdr = (r) => r.startsWith('06-adr/') && /^\d{4}-/.test(path.basename(r))
const isContract = (r) => r.startsWith('03-contracts/')
const STATUS_OK = new Set(['draft', 'review', 'active', 'deprecated', 'accepted', 'proposed', 'superseded'])
for (const p of files) {
  const r = rel(p); const fm = fmParse(texts[p])
  if (!fm) { report.A2_frontmatter.push({ file: r, problem: 'frontmatter 없음' }); continue }
  const req = isAdr(r) ? ['title', 'status', 'date', 'deciders', 'priority', 'related', 'version'] : ['title', 'status', 'owner', 'version', 'last_updated']
  if (isContract(r)) req.push('schema_version')
  for (const k of req) if (!(k in fm.o)) report.A2_frontmatter.push({ file: r, problem: `필수 필드 누락: ${k}` })
  if (fm.o.status && !STATUS_OK.has(fm.o.status)) report.A2_frontmatter.push({ file: r, problem: `status 값 비허용: ${fm.o.status}` })
  if (fm.o.last_updated && !/^\d{4}-\d{2}-\d{2}$/.test(fm.o.last_updated)) report.A2_frontmatter.push({ file: r, problem: `last_updated 형식: ${fm.o.last_updated}` })
}
// ---- A3 spelling: enums/types from common-types + rejected names
let enumValues = new Set(), typeNames = new Set()
const ct = path.join(SCHEMAS, 'common-types.schema.json')
if (fs.existsSync(ct)) { const j = JSON.parse(fs.readFileSync(ct, 'utf8')); for (const [k, v] of Object.entries(j.$defs || {})) { typeNames.add(k); if (Array.isArray(v.enum)) for (const e of v.enum) if (typeof e === 'string') enumValues.add(e) } }
const REJECTED = [
  ['chunk_ulid', 'chunk_id(BLAKE3, ADR-0004)'], ['exclude_chunk_ids', 'exclude_ids'], ['rag.stage.', 'rag.{stage}(§6.5)'], ['summary_parent', 'item_kind=summary(§5.7)'],
  ['PyMuPDF', '기본 경로 아님(ADR-0006) — 언급은 대안·기각 문맥이어야 함'], ['pyhwp', '선택 플러그인(ADR-0007) — 기본 경로 문맥이면 위반'], ['MinIO', 'RustFS/SeaweedFS(ADR-0011)'], ['Redis', 'Valkey(ADR-0011) — "Redis 호환" 표현만 허용'],
  ['Infinity', 'vLLM pooling + TEI(ADR-0009)'], ['SPLADE-v3', '제외(O-02)'], ['cite_id = c', 'cite_id는 d{rank}(§6.1)'], ['[c1]', '[d1]'], ['/v1/retrieve', '/v1/query(§14)'], ['/v1/search', '§14에 없음'],
]
const camel = (s) => s.replace(/_([a-z])/g, (m, c) => c.toUpperCase())
for (const p of files) {
  const r = rel(p); if (r.startsWith('07-tech-landscape/') || r.startsWith('12-appendix/')) continue // research/appendix may discuss rejected options
  const t = texts[p]; const body = stripCode(t)
  // rejected names: ADRs and the bible legitimately discuss rejected alternatives → excluded; other docs are flagged for context review (each hit needs a "대안/기각/제외" context)
  if (!isAdr(r) && r !== '02-architecture/00-design-bible.md') for (const [bad, hint] of REJECTED) { let i = -1; let n = 0; while ((i = body.indexOf(bad, i + 1)) >= 0 && n < 5) { n++; const ctx = body.slice(Math.max(0, i - 40), i + bad.length + 40).replace(/\s+/g, ' '); const excused = /(대안|기각|제외|금지|아님|않|대신|이전|구 |구명|폐기|호환)/.test(ctx); report.A3_spelling.push({ file: r, line: lineOf(t, i), token: bad, hint, context: ctx, likely_ok: excused }) } }
  for (const e of enumValues) { if (!e.includes('_')) continue; const c = camel(e); if (c === e || c.length < 8) continue; let i = -1; while ((i = body.indexOf(c, i + 1)) >= 0) { const before = body[i - 1] || ' ', after = body[i + c.length] || ' '; if (/[A-Za-z0-9_]/.test(before) || /[A-Za-z0-9_]/.test(after)) continue; report.A3_spelling.push({ file: r, line: lineOf(t, i), token: c, hint: `열거값 camelCase 변형 → ${e}` }) } }
}
// ---- A4 ID prefix map
const PREFIXES = ['PB', 'G', 'GL', 'DP', 'KPI', 'SC', 'DF', 'UC', 'US', 'FR', 'NFR', 'DRC', 'T', 'PL', 'P']
for (const p of files) { const t = texts[p]; for (const pre of PREFIXES) { const re = new RegExp(`(?<![A-Za-z])${pre}-\\d{2}`, 'g'); const n = (t.match(re) || []).length; if (n) (report.A4_id_prefix[pre] = report.A4_id_prefix[pre] || {})[rel(p)] = n } }
// ---- A5 length (non-contract, non-bible, non-appendix)
for (const p of files) { const r = rel(p); if (isContract(r) || r === '02-architecture/00-design-bible.md' || r.startsWith('12-appendix/')) continue; const n = texts[p].replace(/\n$/, '').split('\n').length; if (n > 900) report.A5_length.push({ file: r, lines: n }) }
// ---- A6 status
const outcomes = {}
if (fs.existsSync(RES)) for (const f of fs.readdirSync(RES).filter((f) => f.endsWith('.json') && !f.startsWith('validator'))) { let j; try { j = JSON.parse(fs.readFileSync(path.join(RES, f), 'utf8')) } catch { continue } ;(function w(o) { if (!o || typeof o !== 'object') return; if (typeof o.file === 'string' && typeof o.review === 'string') { const s = o.file.replace(/\\/g, '/'); const i = s.indexOf('/docs/'); outcomes[i >= 0 ? s.slice(i + 6) : s] = o.review } for (const k of Object.keys(o)) if (typeof o[k] === 'object') w(o[k]) })(j) }
const COMPLETED = new Set(['pass', 'verified', 'fixed_twice', 'minor_fixed', 'fixed_unverified', 'fixed_from_prereview'])
for (const p of files) { const r = rel(p); const fm = fmParse(texts[p]); if (!fm) continue; if (fm.o.status === 'review' || fm.o.status === 'draft') report.A6_status.push({ file: r, status: fm.o.status, last_outcome: outcomes[r] || null, fixable: !isAdr(r) && COMPLETED.has(outcomes[r]) }) }
// ---- A7 citations
const adrIds = new Set(fs.existsSync(path.join(DOCS, '06-adr')) ? fs.readdirSync(path.join(DOCS, '06-adr')).filter((f) => /^\d{4}-/.test(f)).map((f) => f.slice(0, 4)) : [])
const defined = { FR: new Set(), NFR: new Set(), UC: new Set(), US: new Set() }
for (const p of files) { const r = rel(p); if (!r.startsWith('01-requirements/')) continue; const t = texts[p]; for (const m of t.matchAll(/\b(FR|NFR)-[A-Z]{2,4}-\d{2,3}\b/g)) defined[m[1]].add(m[0]); for (const m of t.matchAll(/\bUC-\d{2}\b/g)) defined.UC.add(m[0]); for (const m of t.matchAll(/\bUS-[A-Z]{2,4}-\d{2,3}\b/g)) defined.US.add(m[0]) }
for (const p of files) {
  const r = rel(p); const t = texts[p]; const seen = new Set()
  for (const m of t.matchAll(/ADR-(\d{4})/g)) if (!adrIds.has(m[1]) && !seen.has(m[0])) { seen.add(m[0]); report.A7_citations.push({ file: r, line: lineOf(t, m.index), ref: m[0], problem: 'ADR 파일 없음' }) }
  for (const m of t.matchAll(/\bD-(\d{2})\b/g)) { const n = +m[1]; if ((n < 1 || n > 20) && !seen.has(m[0])) { seen.add(m[0]); report.A7_citations.push({ file: r, line: lineOf(t, m.index), ref: m[0], problem: 'D-01~D-20 범위 밖' }) } }
  for (const m of t.matchAll(/\bO-(\d{2})\b/g)) { const n = +m[1]; if ((n < 1 || n > 12) && !seen.has(m[0])) { seen.add(m[0]); report.A7_citations.push({ file: r, line: lineOf(t, m.index), ref: m[0], problem: 'O-01~O-12 범위 밖' }) } }
  if (!r.startsWith('01-requirements/')) { for (const m of t.matchAll(/\b(FR|NFR)-[A-Z]{2,4}-\d{2,3}\b/g)) if (!defined[m[1]].has(m[0]) && !seen.has(m[0])) { seen.add(m[0]); report.A7_citations.push({ file: r, line: lineOf(t, m.index), ref: m[0], problem: '요구사항 문서에 미정의' }) } for (const m of t.matchAll(/\bUS-[A-Z]{2,4}-\d{2,3}\b/g)) if (!defined.US.has(m[0]) && !seen.has(m[0])) { seen.add(m[0]); report.A7_citations.push({ file: r, line: lineOf(t, m.index), ref: m[0], problem: '사용자 스토리 문서에 미정의' }) } }
}
// ---- A8 confirm-needed
for (const p of files) { const n = (texts[p].match(/확인 필요/g) || []).length; if (n) report.A8_confirm.push({ file: rel(p), count: n }) }
// ---- A9 schema inventory vs bible §5.1
const bible = texts[path.join(DOCS, '02-architecture', '00-design-bible.md')] || ''
const invNames = new Set([...bible.matchAll(/`([a-z0-9-]+\.schema\.json)`/g)].map((m) => m[1]))
const onDisk = fs.existsSync(SCHEMAS) ? fs.readdirSync(SCHEMAS).filter((f) => f.endsWith('.schema.json')) : []
report.A9_schema_inventory = { in_bible_not_on_disk: [...invNames].filter((n) => !onDisk.includes(n)), on_disk_not_in_bible: onDisk.filter((n) => !invNames.has(n)), bible_count: invNames.size, disk_count: onDisk.length }

// ---- A10 bible §14 API surface vs openapi.yaml
report.A10_api_surface = { in_bible_not_in_openapi: [], in_openapi_not_in_bible: [] }
{
  const s14 = bible.slice(bible.indexOf('\n## 14.'), bible.indexOf('\n## 15.'))
  const bibleOps = new Set()
  for (const line of s14.split('\n')) {
    const m = /^\|\s*(GET|POST|PUT|PATCH|DELETE|[A-Z/]+)\s*\|\s*([^|]+)\|/.exec(line); if (!m) continue
    const methods = m[1].split('/').map((x) => x.trim()).filter((x) => /^(GET|POST|PUT|PATCH|DELETE)$/.test(x)); if (!methods.length) continue
    const toks = [...m[2].matchAll(/`([^`]+)`/g)].map((x) => x[1]).filter((x) => x.startsWith('/'))
    let base = null
    for (const tok of toks) {
      let p = tok
      if (!/^\/(v1|mcp|healthz|readyz|metrics|\.well-known)/.test(tok) && base) p = base.replace(/\/[^/]+$/, '') + tok // shorthand like `/retry`
      else base = tok
      for (const me of methods) bibleOps.add(me + ' ' + p.replace(/\{[^}]+\}/g, '{}'))
    }
  }
  const oaPath = path.join(DOCS, '05-api', 'openapi.yaml')
  const oaOps = new Set()
  if (fs.existsSync(oaPath)) { let cur = null; for (const line of fs.readFileSync(oaPath, 'utf8').split('\n')) { const pm = /^  ['"]?(\/[^'":\s]+)['"]?:\s*$/.exec(line); if (pm) { cur = pm[1]; continue } const mm = /^    (get|post|put|patch|delete):\s*$/.exec(line); if (mm && cur) oaOps.add(mm[1].toUpperCase() + ' ' + cur.replace(/\{[^}]+\}/g, '{}')); if (/^[a-z]/.test(line)) cur = null } }
  report.A10_api_surface = { bible_ops: bibleOps.size, openapi_ops: oaOps.size, in_bible_not_in_openapi: [...bibleOps].filter((x) => !oaOps.has(x)), in_openapi_not_in_bible: [...oaOps].filter((x) => !bibleOps.has(x)) }
}
// ---- fixes
if (FIX) {
  for (const p of files) {
    const r = rel(p); let t = texts[p]; const fm = fmParse(t); if (!fm) continue; let changed = false
    if (!('version' in fm.o)) { t = t.replace(/^---\n/, '---\nversion: 0.1.0\n'); changed = true; report.fixes.push({ file: r, fix: 'version: 0.1.0 추가' }) }
    const st = report.A6_status.find((s) => s.file === r)
    if (st && st.fixable) { t = t.replace(/^status:\s*(review|draft)\s*$/m, 'status: active'); changed = true; report.fixes.push({ file: r, fix: `status ${st.status} → active (결과: ${st.last_outcome})` }) }
    if (changed) fs.writeFileSync(p, t)
  }
}
// ---- outputs
const summary = { A1_broken_links: report.A1_links.length, A2_frontmatter_issues: report.A2_frontmatter.length, A3_spelling_hits: report.A3_spelling.length, A3_needs_context_review: report.A3_spelling.filter((x) => x.likely_ok === false).length, A5_over_900: report.A5_length.length, A6_review_or_draft: report.A6_status.length, A7_bad_citations: report.A7_citations.length, A8_confirm_docs: report.A8_confirm.length, A8_confirm_total: report.A8_confirm.reduce((a, x) => a + x.count, 0), A9: report.A9_schema_inventory, A10: report.A10_api_surface, fixes: report.fixes.length }
report.summary = summary
const jsonOut = opt('--json', null); if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(report, null, 1))
const mdOut = opt('--md', null)
if (mdOut) {
  let md = `# 문서 기계 감사 결과 (${report.date.slice(0, 10)})\n\n| 검사 | 건수 |\n|---|---:|\n` + Object.entries(summary).filter(([k]) => k !== 'A9').map(([k, v]) => `| ${k} | ${v} |`).join('\n')
  md += `\n| A9 스키마 인벤토리 | 바이블 ${summary.A9.bible_count} / 디스크 ${summary.A9.disk_count}; 바이블에만 ${summary.A9.in_bible_not_on_disk.join(', ') || '-'}; 디스크에만 ${summary.A9.on_disk_not_in_bible.join(', ') || '-'} |\n`
  const sec = (title, rows, cols) => rows.length ? `\n## ${title} (${rows.length})\n\n| ${cols.join(' | ')} |\n|${cols.map(() => '---').join('|')}|\n` + rows.map((r) => `| ${cols.map((c) => String(r[c] ?? '').replace(/\|/g, '\\|')).join(' | ')} |`).join('\n') + '\n' : `\n## ${title} (0)\n`
  md += sec('A1 깨진 링크', report.A1_links, ['file', 'line', 'target']) + sec('A2 frontmatter', report.A2_frontmatter, ['file', 'problem']) + sec('A3 철자·기각 명칭 (likely_ok=false 우선 검토)', report.A3_spelling, ['file', 'line', 'token', 'hint', 'likely_ok']) + sec('A5 900행 초과', report.A5_length, ['file', 'lines']) + sec('A6 review/draft 상태', report.A6_status, ['file', 'status', 'last_outcome', 'fixable']) + sec('A7 인용 무결성', report.A7_citations, ['file', 'line', 'ref', 'problem']) + sec('A8 확인 필요', report.A8_confirm, ['file', 'count'])
  md += `\n## A10 바이블 §14 ↔ openapi.yaml\n\n바이블 ${summary.A10.bible_ops} 연산 / openapi ${summary.A10.openapi_ops} 연산. 바이블에만: ${summary.A10.in_bible_not_in_openapi.join(', ') || '-'}. openapi에만: ${summary.A10.in_openapi_not_in_bible.join(', ') || '-'}\n`
  md += `\n## A4 ID 접두 사용 지도\n\n| 접두 | 파일 수 | 총 출현 | 파일(상위 5) |\n|---|---:|---:|---|\n` + Object.entries(report.A4_id_prefix).map(([k, v]) => `| ${k}- | ${Object.keys(v).length} | ${Object.values(v).reduce((a, b) => a + b, 0)} | ${Object.entries(v).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([f, n]) => `${f}(${n})`).join(', ')} |`).join('\n') + '\n'
  if (report.fixes.length) md += `\n## 적용된 자동 수정 (${report.fixes.length})\n\n` + report.fixes.map((f) => `- ${f.file}: ${f.fix}`).join('\n') + '\n'
  fs.writeFileSync(mdOut, md)
}
console.log(JSON.stringify(summary))
