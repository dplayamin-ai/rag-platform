// Phase 5: generate schemas/README.md (schema file ↔ $id ↔ title ↔ owning contract doc ↔ bible §5.1 presence). No LLM.
// Usage: node tools/phase5/gen-schemas-readme.mjs [--root <repo>] [--date YYYY-MM-DD]
import fs from 'node:fs'
import path from 'node:path'
const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const ROOT = opt('--root', 'C:\\Workspaces\\rag-platform')
const DATE = opt('--date', new Date().toISOString().slice(0, 10))
const SCHEMAS = path.join(ROOT, 'schemas'), CONTRACTS = path.join(ROOT, 'docs', '03-contracts')
const bible = fs.readFileSync(path.join(ROOT, 'docs', '02-architecture', '00-design-bible.md'), 'utf8')
const inv = new Set([...bible.matchAll(/`([a-z0-9-]+\.schema\.json)`/g)].map((m) => m[1]))
const contractDocs = fs.readdirSync(CONTRACTS).filter((f) => f.endsWith('.md')).map((f) => ({ f, t: fs.readFileSync(path.join(CONTRACTS, f), 'utf8') }))
const rows = []
for (const f of fs.readdirSync(SCHEMAS).filter((f) => f.endsWith('.schema.json')).sort()) {
  let j = {}; try { j = JSON.parse(fs.readFileSync(path.join(SCHEMAS, f), 'utf8')) } catch { j = { title: '(JSON 파싱 실패)' } }
  const owners = contractDocs.filter((d) => d.t.includes(f)).map((d) => d.f)
  const defs = j.$defs ? Object.keys(j.$defs).length : 0
  rows.push({ f, id: j.$id || '-', title: j.title || '-', owners, defs, inBible: inv.has(f) })
}
let md = `# JSON Schema 인덱스

생성: ${DATE} · 도구: \`tools/phase5/gen-schemas-readme.mjs\`(기계 생성, 수동 편집 금지). 정본 규칙은 [계약 개요](../docs/03-contracts/00-contract-overview.md)와 [설계 바이블 §5.1](../docs/02-architecture/00-design-bible.md)이다.

- 스키마 표준: JSON Schema 2020-12. \`$id\`는 \`urn:rag:schema:<kebab>:<major>\`. 공용 타입·열거는 \`common-types.schema.json#/$defs/<Type>\`로 참조한다.
- 검증: \`node tools/validate-contracts.mjs --root <repo>\` (문법·\`$ref\`·열거 ↔ 바이블 §5.7·예시 ↔ 스키마·문서 구조).
- 변경 절차: 바이블 §1.2(필드 추가·열거값 추가 = minor, 제거·의미 변경 = major → ADR).

| 파일 | \`$id\` | title | \`$defs\` | 소유 계약 문서 | 바이블 §5.1 |
|---|---|---|---:|---|---|
`
for (const r of rows) md += `| ${r.f} | ${r.id} | ${r.title} | ${r.defs} | ${r.owners.join(', ') || '(미참조)'} | ${r.inBible ? '등재' : '**미등재**'} |\n`
md += `\n합계 ${rows.length}개(바이블 §5.1 등재 ${rows.filter((r) => r.inBible).length}).\n`
fs.writeFileSync(path.join(SCHEMAS, 'README.md'), md)
console.log('schemas/README.md written:', rows.length, 'schemas; not in bible:', rows.filter((r) => !r.inBible).map((r) => r.f))
