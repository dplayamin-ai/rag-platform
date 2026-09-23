// 스키마 인덱스 생성기 — `schemas/README.md`를 기계 생성한다: 스키마 파일 ↔ `$id` ↔ `title` ↔ 소유 계약 문서(`docs/03-contracts/*.md`) ↔ 바이블 §5.1 등재 여부(LLM 없음).
// 설계 근거: 4·5단계 계획 `12-appendix/02-phase4-5-plan.md` §3(5단계 할 일 — `schemas/README.md` 산출물), 바이블 §5.1(스키마 인벤토리 정본), 계약 개요 `03-contracts/00-contract-overview.md`(변경 절차·검증 명령 인용).
// 구성: 스키마 파일 순회 후 소유 계약 문서(파일명 언급 여부로 추정) 탐색 → 바이블 §5.1 인벤토리(스키마 파일명 패턴 추출)와 대조 → 표 형태 md 조립·저장.
// 불변식·주의: 수동 편집 금지 문서(재생성이 항상 덮어씀). 소유 문서 판정은 계약 문서 본문에 스키마 파일명이 등장하는지의 텍스트 포함 검사이므로 오탐 가능성이 있다 — 정확한 소유 관계는 계약 개요 §2 인벤토리가 정본이다.
// 검증 계층: 1층(여기서 검증, 콘솔 출력의 "바이블 미등재" 목록으로 확인). 실행: `node tools/phase5/gen-schemas-readme.mjs [--root <repo>] [--date YYYY-MM-DD]`
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
