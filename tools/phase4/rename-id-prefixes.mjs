// ID 접두 충돌 정규식 치환기 — 용어집 미해결 이슈 `G-xx` → `GL-xx`(문맥상 용어집을 가리킬 때만; `03-glossary.md` 내부는 전부)와 용어집 링크 키 `[P-xx]` → `[PL-xx]`를 문서 전체(`docs/**/*.md`)에서 치환한다.
// 설계 근거: 4·5단계 계획 `12-appendix/02-phase4-5-plan.md` §2.3 D4-1(ID 접두 충돌 해소 결정), 완전성 검토 `01-phase3-completeness-review.md`의 A4 ID 접두 사용 지도.
// 구성: 파일별 치환 규칙 3분기 — `03-glossary.md`(전체 치환) / `06-adr`·`03-contracts`·바이블(문맥상 글로서리 참조로 간주) / 그 외(글로서리·용어집 언급 40자 이내 근접 문맥만 치환); 콘솔에 파일별 교체 건수와 잔여 `G-xx` 표본을 보고.
// 불변식·주의: 비전 목표 `G-xx`(`00-vision/01-vision-and-goals.md`와 "비전 G-10" 같은 인용)는 건드리지 않는다 — 용어집 이슈 접두와 비전 목표 접두가 같은 `G-`를 공유하므로 오탐 방지가 이 스크립트의 핵심이다. 기본은 드라이런이며 `--apply` 없이는 파일을 쓰지 않는다.
// 검증 계층: 1층(여기서 검증, 콘솔 리포트의 잔여 `G-xx` 표본으로 오탐 확인). 실행: `node tools/phase4/rename-id-prefixes.mjs [--apply]`
import fs from 'node:fs'
import path from 'node:path'
const APPLY = process.argv.includes('--apply')
const root = 'C:/Workspaces/rag-platform'
function walk(d, out = []) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p, out); else if (p.endsWith('.md')) out.push(p) } return out }
const files = walk(path.join(root, 'docs')).filter((p) => !p.includes('12-appendix' + path.sep + 'sources'))
const report = []
let totalChanges = 0
for (const p of files) {
  const rel = path.relative(root, p).split(path.sep).join('/')
  let t = fs.readFileSync(p, 'utf8'); const orig = t
  if (rel === 'docs/00-vision/03-glossary.md') {
    t = t.replace(/\[P-(\d{2})\]/g, '[PL-$1]')
    t = t.replace(/(?<![A-Z])G-(\d{2})\b/g, 'GL-$1')
  } else if (/^docs\/(06-adr|03-contracts)\//.test(rel) || rel === 'docs/02-architecture/00-design-bible.md') {
    // in ADRs, contracts and the bible every G-xx reference is a glossary issue unless explicitly "비전 G-xx"
    t = t.replace(/(비전\s*)?(?<![A-Z])G-(\d{2})\b/g, (m, vision, n) => (vision ? m : 'GL-' + n))
  } else if (rel !== 'docs/00-vision/01-vision-and-goals.md') {
    // glossary-issue citations: "글로서리 G-12", "글로서리는 … G-15", "§16 G-07·G-13·G-14", "G-12 해소", "(G-05)" right after 글로서리/용어집 within 40 chars
    t = t.replace(/(§16\s+)((?:G-\d{2}(?:·|, | ))*G-\d{2})/g, (m, pre, list) => pre + list.replace(/G-(\d{2})/g, 'GL-$1'))
    t = t.replace(/((?:글로서리|용어집)[^\n|]{0,40}?)(?<![A-Z])G-(\d{2})\b/g, (m, pre, n) => pre + 'GL-' + n)
    t = t.replace(/(?<![A-Z])G-(\d{2})(\s*해소)/g, 'GL-$1$2')
    t = t.replace(/(?<![A-Z])G-(\d{2})(·GL-\d{2})/g, 'GL-$1$2') // lists partially converted
  }
  if (t !== orig) {
    const n = (orig.match(/(?<![A-Z])G-\d{2}\b|\[P-\d{2}\]/g) || []).length - (t.match(/(?<![A-Z])G-\d{2}\b|\[P-\d{2}\]/g) || []).length
    totalChanges += n
    const remaining = [...t.matchAll(/.{0,40}(?<![A-Z])G-\d{2}\b.{0,30}/g)].map((m) => m[0].replace(/\s+/g, ' ')).slice(0, 4)
    report.push({ file: rel, replaced: n, remaining_G_refs_sample: remaining })
    if (APPLY) fs.writeFileSync(p, t)
  }
}
console.log(JSON.stringify({ apply: APPLY, files: report.length, replacements: totalChanges, report }, null, 1))
