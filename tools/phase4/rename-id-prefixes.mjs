// Phase 4 D4-1: resolve ID prefix collisions mechanically.
//  - Glossary open-issue IDs  G-xx  -> GL-xx  (inside 03-glossary.md: all; elsewhere: only when the context refers to the glossary)
//  - Glossary link keys      [P-xx] -> [PL-xx] (glossary-internal reference-style links)
//  Vision goals G-xx (01-vision-and-goals.md and citations like "비전 G-10", "PB-06, G-04, KPI-11") are left untouched.
// Usage: node tools/phase4/rename-id-prefixes.mjs [--apply]
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
