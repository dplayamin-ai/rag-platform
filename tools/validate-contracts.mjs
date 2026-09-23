#!/usr/bin/env node
// validate-contracts.mjs — mechanical checks for RAG Platform contract docs + JSON Schemas.
// Usage: node validate-contracts.mjs --root C:\Workspaces\rag-platform [--json report.json] [--quiet]
// No dependencies (corporate proxy blocks npm). Implements a JSON Schema 2020-12 subset validator.
import fs from 'node:fs'
import path from 'node:path'

const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const ROOT = opt('--root', 'C:\\Workspaces\\rag-platform')
const JSON_OUT = opt('--json', null)
const QUIET = argv.includes('--quiet')
const SCHEMAS = path.join(ROOT, 'schemas')
const CONTRACTS = path.join(ROOT, 'docs', '03-contracts')
const BIBLE = path.join(ROOT, 'docs', '02-architecture', '00-design-bible.md')

const errors = [], warnings = [], infos = []
const err = (file, msg) => errors.push({ file: rel(file), msg })
const warn = (file, msg) => warnings.push({ file: rel(file), msg })
const info = (file, msg) => infos.push({ file: rel(file), msg })
const rel = (f) => (f ? path.relative(ROOT, f).replace(/\\/g, '/') : '')

// ---------------------------------------------------------------- 1. load schemas
const registryById = new Map(), registryByFile = new Map(), schemaFiles = []
if (!fs.existsSync(SCHEMAS)) { err(SCHEMAS, 'schemas/ 디렉터리가 없다'); finish() }
for (const f of fs.readdirSync(SCHEMAS).filter((x) => x.endsWith('.schema.json')).sort()) {
  const full = path.join(SCHEMAS, f)
  let s
  try { s = JSON.parse(fs.readFileSync(full, 'utf8')) } catch (e) { err(full, `JSON 파싱 실패: ${e.message}`); continue }
  schemaFiles.push({ file: full, name: f, schema: s })
  registryByFile.set(f, s)
  if (!f.endsWith('.schema.json')) err(full, '파일명은 <kebab-name>.schema.json 이어야 한다')
  const kebab = f.replace(/\.schema\.json$/, '')
  if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(kebab)) err(full, `kebab-case 파일명이 아니다: ${kebab}`)
  if (s.$schema !== 'https://json-schema.org/draft/2020-12/schema') err(full, `$schema 는 https://json-schema.org/draft/2020-12/schema 이어야 한다 (현재: ${s.$schema})`)
  if (typeof s.$id !== 'string') err(full, '$id 누락')
  else {
    const m = /^urn:rag:schema:([a-z0-9-]+):(\d+)$/.exec(s.$id)
    if (!m) err(full, `$id 형식은 urn:rag:schema:<kebab-name>:<major> (현재: ${s.$id})`)
    else if (m[1] !== kebab) err(full, `$id 의 이름(${m[1]})이 파일명(${kebab})과 다르다`)
    if (registryById.has(s.$id)) err(full, `$id 중복: ${s.$id}`)
    registryById.set(s.$id, s)
  }
  if (!s.title) warn(full, 'title 누락')
}

// ---------------------------------------------------------------- 2. $ref resolution
function resolvePointer(doc, pointer) {
  if (!pointer || pointer === '#' || pointer === '') return doc
  const parts = pointer.replace(/^#\//, '').split('/').map((p) => p.replace(/~1/g, '/').replace(/~0/g, '~'))
  let cur = doc
  for (const p of parts) { if (cur && typeof cur === 'object' && p in cur) cur = cur[p]; else return undefined }
  return cur
}
function resolveRef(ref, base) {
  // returns {schema, root} or null
  const hashIdx = ref.indexOf('#')
  const uri = hashIdx >= 0 ? ref.slice(0, hashIdx) : ref
  const frag = hashIdx >= 0 ? ref.slice(hashIdx) : ''
  let root = null
  if (uri === '') root = base
  else if (registryById.has(uri)) root = registryById.get(uri)
  else {
    const fname = path.basename(uri.replace(/\\/g, '/'))
    if (registryByFile.has(fname)) root = registryByFile.get(fname)
  }
  if (!root) return null
  const target = resolvePointer(root, frag)
  return target === undefined ? null : { schema: target, root }
}
function walk(node, cb, p = '') {
  if (Array.isArray(node)) node.forEach((n, i) => walk(n, cb, `${p}/${i}`))
  else if (node && typeof node === 'object') { cb(node, p); for (const [k, v] of Object.entries(node)) walk(v, cb, `${p}/${k}`) }
}
for (const { file, schema } of schemaFiles) {
  walk(schema, (n, p) => {
    if (typeof n.$ref === 'string') {
      if (!resolveRef(n.$ref, schema)) err(file, `해결되지 않는 $ref ${n.$ref} (at ${p || '/'})`)
      if (/^urn:rag:schema:common-types:\d+#\/\$defs\//.test(n.$ref) === false && /common-types/.test(n.$ref) && !n.$ref.startsWith('urn:')) warn(file, `common-types 참조는 urn:rag:schema:common-types:1#/$defs/<Type> 형식을 권장 (at ${p}): ${n.$ref}`)
    }
    if (n.type === 'object' && n.properties && n.additionalProperties === undefined && !n.$ref && !p.includes('/patternProperties')) {
      // policy: additionalProperties should be explicit on object schemas
      warn(file, `additionalProperties 정책 미명시 (at ${p || '/'})`)
    }
    for (const k of ['definitions']) if (k in n) warn(file, `2020-12에서는 ${k} 대신 $defs 를 쓴다 (at ${p})`)
  })
}

// ---------------------------------------------------------------- 3. enum cross-check against bible §5.7
const enumInSchemas = new Map() // TypeName -> [{file, values}]
for (const { file, schema } of schemaFiles) {
  const defs = schema.$defs || {}
  for (const [name, def] of Object.entries(defs)) {
    if (def && Array.isArray(def.enum)) {
      if (!enumInSchemas.has(name)) enumInSchemas.set(name, [])
      enumInSchemas.get(name).push({ file, values: def.enum.map(String) })
    }
  }
}
// duplicate enum definitions with different values across files
for (const [name, list] of enumInSchemas) {
  const sets = new Set(list.map((l) => JSON.stringify([...l.values].sort())))
  if (sets.size > 1) err(list[0].file, `열거 $defs/${name} 가 파일마다 다르다: ${list.map((l) => rel(l.file)).join(', ')}`)
  if (list.length > 1) info(list[0].file, `열거 $defs/${name} 가 ${list.length}개 파일에 중복 정의됨(common-types 한 곳만 권장): ${list.map((l) => rel(l.file)).join(', ')}`)
}
const bibleEnums = parseBibleEnums()
for (const [name, values, loose] of bibleEnums) {
  const list = enumInSchemas.get(name)
  if (!list) { info(BIBLE, `바이블 §5.7 열거 ${name} 가 어떤 스키마 $defs 에도 없다`); continue }
  const have = new Set(list[0].values), want = new Set(values)
  const missing = [...want].filter((v) => !have.has(v)), extra = [...have].filter((v) => !want.has(v))
  if (missing.length || extra.length) {
    const msg = `열거 ${name}: 바이블 §5.7과 불일치 — 누락 [${missing.join(', ')}] 초과 [${extra.join(', ')}]`
    if (loose) warn(list[0].file, msg + ' (와일드카드/패턴 행: 확인 필요)'); else err(list[0].file, msg)
  }
}
function parseBibleEnums() {
  const out = []
  if (!fs.existsSync(BIBLE)) { warn(BIBLE, '바이블 파일 없음 — 열거 대조 생략'); return out }
  const text = fs.readFileSync(BIBLE, 'utf8')
  const start = text.indexOf('### 5.7')
  if (start < 0) { warn(BIBLE, '§5.7 절을 찾을 수 없음'); return out }
  const end = text.indexOf('\n## 6.', start)
  const section = text.slice(start, end < 0 ? undefined : end)
  for (const line of section.split('\n')) {
    if (!line.startsWith('| `')) continue
    const cells = line.replace(/\\\|/g, '\u0001').split('|').slice(1, -1).map((c) => c.replace(/\u0001/g, '|').trim())
    if (cells.length < 3) continue
    const names = [...cells[0].matchAll(/`([A-Z][A-Za-z0-9]*)`(\((integer|string)\))?/g)].filter((m) => !m[2]).map((m) => m[1])
    if (!names.length) continue
    const valueParts = names.length > 1 ? splitTopLevel(cells[2]) : [cells[2]]
    if (valueParts.length !== names.length) { info(BIBLE, `§5.7 행 파싱 생략(타입 ${names.length} vs 값 그룹 ${valueParts.length}): ${names.join('/')}`); continue }
    names.forEach((n, i) => {
      const m = /`([^`]+)`/.exec(valueParts[i])
      if (!m) return
      const raw = m[1]
      if (/^[A-Z][A-Za-z]+$/.test(raw.trim()) || raw.includes('∪')) { info(BIBLE, `§5.7 열거 ${n} 는 합성 정의(${raw}) — 수동 확인`); return }
      const loose = /[*{]/.test(raw)
      const vals = raw.split(',').map((v) => v.trim()).filter((v) => v && !/[*{}]/.test(v))
      out.push([n, vals, loose])
    })
  }
  return out
}
function splitTopLevel(s) {
  // split on " / " that is outside backticks and parentheses
  const parts = []; let depth = 0, tick = false, cur = ''
  for (let i = 0; i < s.length; i++) {
    const c = s[i]
    if (c === '`') tick = !tick
    if (!tick) { if (c === '(') depth++; if (c === ')') depth--; }
    if (!tick && depth === 0 && s.slice(i, i + 3) === ' / ') { parts.push(cur); cur = ''; i += 2; continue }
    cur += c
  }
  parts.push(cur)
  return parts
}

// ---------------------------------------------------------------- 4. mini JSON Schema validator (2020-12 subset)
function validate(instance, schema, root, ipath = '$', spath = '#', out = [], depth = 0) {
  if (depth > 64) { out.push(`${ipath}: 스키마 깊이 초과`); return out }
  if (schema === true || schema === undefined) return out
  if (schema === false) { out.push(`${ipath}: false 스키마`); return out }
  if (typeof schema.$ref === 'string') {
    const r = resolveRef(schema.$ref, root)
    if (!r) { out.push(`${ipath}: $ref 미해결 ${schema.$ref}`); return out }
    validate(instance, r.schema, r.root, ipath, schema.$ref, out, depth + 1)
    const rest = { ...schema }; delete rest.$ref
    if (Object.keys(rest).some((k) => !['description', 'title', '$comment', 'examples', 'default'].includes(k))) validate(instance, rest, root, ipath, spath, out, depth + 1)
    return out
  }
  const t = typeOf(instance)
  if (schema.type !== undefined) {
    const types = Array.isArray(schema.type) ? schema.type : [schema.type]
    const ok = types.some((ty) => ty === t || (ty === 'number' && t === 'integer') || (ty === 'integer' && t === 'number' && Number.isInteger(instance)))
    if (!ok) { out.push(`${ipath}: 타입 ${t} 는 ${types.join('|')} 이 아니다`); return out }
  }
  if (schema.enum && !schema.enum.some((v) => deepEq(v, instance))) out.push(`${ipath}: 값 ${JSON.stringify(instance)} 는 enum [${schema.enum.map((v) => JSON.stringify(v)).join(', ')}] 에 없다`)
  if ('const' in schema && !deepEq(schema.const, instance)) out.push(`${ipath}: const ${JSON.stringify(schema.const)} 와 다르다`)
  if (t === 'string') {
    if (schema.minLength !== undefined && [...instance].length < schema.minLength) out.push(`${ipath}: minLength ${schema.minLength}`)
    if (schema.maxLength !== undefined && [...instance].length > schema.maxLength) out.push(`${ipath}: maxLength ${schema.maxLength}`)
    if (schema.pattern) { try { if (!new RegExp(schema.pattern, 'u').test(instance)) out.push(`${ipath}: pattern ${schema.pattern} 불일치 (${instance.slice(0, 60)})`) } catch { out.push(`${spath}: 잘못된 pattern ${schema.pattern}`) } }
    if (schema.format) {
      const f = schema.format
      const ok = f === 'date-time' ? /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/.test(instance) && !isNaN(Date.parse(instance))
        : f === 'date' ? /^\d{4}-\d{2}-\d{2}$/.test(instance)
        : f === 'uri' ? /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(instance)
        : f === 'uuid' ? /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(instance)
        : f === 'duration' ? /^P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+(\.\d+)?S)?)?$/.test(instance) || /^\d+(ms|s|m|h|d)$/.test(instance)
        : true
      if (!ok) out.push(`${ipath}: format ${f} 불일치 (${instance.slice(0, 60)})`)
    }
  }
  if (t === 'number' || t === 'integer') {
    if (schema.minimum !== undefined && instance < schema.minimum) out.push(`${ipath}: minimum ${schema.minimum}`)
    if (schema.maximum !== undefined && instance > schema.maximum) out.push(`${ipath}: maximum ${schema.maximum}`)
    if (schema.exclusiveMinimum !== undefined && instance <= schema.exclusiveMinimum) out.push(`${ipath}: exclusiveMinimum ${schema.exclusiveMinimum}`)
    if (schema.exclusiveMaximum !== undefined && instance >= schema.exclusiveMaximum) out.push(`${ipath}: exclusiveMaximum ${schema.exclusiveMaximum}`)
    if (schema.multipleOf !== undefined && Math.abs(instance / schema.multipleOf - Math.round(instance / schema.multipleOf)) > 1e-9) out.push(`${ipath}: multipleOf ${schema.multipleOf}`)
  }
  if (t === 'array') {
    if (schema.minItems !== undefined && instance.length < schema.minItems) out.push(`${ipath}: minItems ${schema.minItems}`)
    if (schema.maxItems !== undefined && instance.length > schema.maxItems) out.push(`${ipath}: maxItems ${schema.maxItems}`)
    if (schema.uniqueItems && new Set(instance.map((x) => JSON.stringify(x))).size !== instance.length) out.push(`${ipath}: uniqueItems 위반`)
    if (Array.isArray(schema.prefixItems)) schema.prefixItems.forEach((ps, i) => { if (i < instance.length) validate(instance[i], ps, root, `${ipath}[${i}]`, `${spath}/prefixItems/${i}`, out, depth + 1) })
    if (schema.items !== undefined) {
      const startIdx = Array.isArray(schema.prefixItems) ? schema.prefixItems.length : 0
      for (let i = startIdx; i < instance.length; i++) validate(instance[i], schema.items, root, `${ipath}[${i}]`, `${spath}/items`, out, depth + 1)
    }
    if (schema.contains !== undefined && !instance.some((x) => validate(x, schema.contains, root, ipath, spath, [], depth + 1).length === 0)) out.push(`${ipath}: contains 불충족`)
  }
  if (t === 'object') {
    const props = schema.properties || {}
    for (const r of schema.required || []) if (!(r in instance)) out.push(`${ipath}: 필수 필드 누락 "${r}"`)
    for (const [k, v] of Object.entries(instance)) {
      let matched = false
      if (k in props) { matched = true; validate(v, props[k], root, `${ipath}.${k}`, `${spath}/properties/${k}`, out, depth + 1) }
      if (schema.patternProperties) for (const [pat, ps] of Object.entries(schema.patternProperties)) { if (new RegExp(pat, 'u').test(k)) { matched = true; validate(v, ps, root, `${ipath}.${k}`, `${spath}/patternProperties`, out, depth + 1) } }
      if (!matched) {
        if (schema.additionalProperties === false) out.push(`${ipath}: 허용되지 않은 필드 "${k}"`)
        else if (schema.additionalProperties && typeof schema.additionalProperties === 'object') validate(v, schema.additionalProperties, root, `${ipath}.${k}`, `${spath}/additionalProperties`, out, depth + 1)
      }
    }
    if (schema.minProperties !== undefined && Object.keys(instance).length < schema.minProperties) out.push(`${ipath}: minProperties ${schema.minProperties}`)
    if (schema.maxProperties !== undefined && Object.keys(instance).length > schema.maxProperties) out.push(`${ipath}: maxProperties ${schema.maxProperties}`)
    if (schema.dependentRequired) for (const [k, reqs] of Object.entries(schema.dependentRequired)) if (k in instance) for (const r of reqs) if (!(r in instance)) out.push(`${ipath}: "${k}" 가 있으면 "${r}" 필수`)
    if (schema.propertyNames) for (const k of Object.keys(instance)) validate(k, schema.propertyNames, root, `${ipath}.<key:${k}>`, `${spath}/propertyNames`, out, depth + 1)
  }
  if (Array.isArray(schema.allOf)) schema.allOf.forEach((s, i) => validate(instance, s, root, ipath, `${spath}/allOf/${i}`, out, depth + 1))
  if (Array.isArray(schema.anyOf)) { const oks = schema.anyOf.map((s, i) => validate(instance, s, root, ipath, `${spath}/anyOf/${i}`, [], depth + 1)); if (!oks.some((o) => o.length === 0)) out.push(`${ipath}: anyOf 모두 실패 — ${oks.map((o, i) => `[${i}] ${o.slice(0, 2).join('; ')}`).join(' | ')}`) }
  if (Array.isArray(schema.oneOf)) { const oks = schema.oneOf.map((s, i) => validate(instance, s, root, ipath, `${spath}/oneOf/${i}`, [], depth + 1)); const n = oks.filter((o) => o.length === 0).length; if (n !== 1) out.push(`${ipath}: oneOf 에서 ${n}개 일치(정확히 1개여야 함)${n === 0 ? ' — ' + oks.map((o, i) => `[${i}] ${o.slice(0, 2).join('; ')}`).join(' | ') : ''}`) }
  if (schema.not !== undefined && validate(instance, schema.not, root, ipath, `${spath}/not`, [], depth + 1).length === 0) out.push(`${ipath}: not 위반`)
  if (schema.if !== undefined) {
    const cond = validate(instance, schema.if, root, ipath, `${spath}/if`, [], depth + 1).length === 0
    if (cond && schema.then !== undefined) validate(instance, schema.then, root, ipath, `${spath}/then`, out, depth + 1)
    if (!cond && schema.else !== undefined) validate(instance, schema.else, root, ipath, `${spath}/else`, out, depth + 1)
  }
  return out
}
function typeOf(v) { if (v === null) return 'null'; if (Array.isArray(v)) return 'array'; if (typeof v === 'number') return Number.isInteger(v) ? 'integer' : 'number'; return typeof v }
function deepEq(a, b) { return JSON.stringify(a) === JSON.stringify(b) }
const kebab = (s) => s.replace(/([a-z0-9])([A-Z])/g, '$1-$2').replace(/([A-Z]+)([A-Z][a-z])/g, '$1-$2').toLowerCase()

// ---------------------------------------------------------------- 5. contract docs: json fences
const docStats = []
if (fs.existsSync(CONTRACTS)) {
  for (const f of fs.readdirSync(CONTRACTS).filter((x) => x.endsWith('.md')).sort()) {
    const full = path.join(CONTRACTS, f)
    const text = fs.readFileSync(full, 'utf8')
    const stat = { file: rel(full), fences: 0, parsed: 0, schemasInDoc: 0, validated: 0, skipped: 0 }
    // frontmatter checks
    const fm = /^---\n([\s\S]*?)\n---/.exec(text)
    if (!fm) err(full, 'frontmatter 없음')
    else {
      for (const k of ['title', 'status', 'owner', 'version', 'last_updated', 'depends_on']) if (!new RegExp(`^${k}:`, 'm').test(fm[1])) err(full, `frontmatter ${k} 누락`)
      if (!/^schema_version:/m.test(fm[1]) && !/^00-|^13-|^14-/.test(f)) warn(full, 'frontmatter schema_version 누락(계약 문서)')
    }
    for (const sec of ['## 목적', '## 범위', '## 결정 사항 요약', '## 미해결 이슈', '## 참조']) if (!text.includes(sec)) err(full, `필수 절 누락: ${sec}`)
    if (!/^00-|^14-/.test(f)) for (const sec of ['## 스키마', '## 예시', '## 불변식', '## 버전 이력']) if (!text.includes(sec)) err(full, `계약 문서 필수 절 누락: ${sec}`)
    if (/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u.test(text)) err(full, '이모지 사용 금지(브리프 §9.10)')
    // links must point to doc-map paths that exist
    for (const m of text.matchAll(/\]\((\.\.?\/[^)#\s]+)(#[^)]*)?\)/g)) {
      const target = path.resolve(path.dirname(full), m[1])
      if (!fs.existsSync(target)) warn(full, `링크 대상 미존재(동시 작성 중일 수 있음): ${m[1]}`)
    }
    // primary schemas referenced in this doc
    const docSchemaIds = new Set()
    const fenceRe = /```(json|jsonc|json5)?[^\n]*\n([\s\S]*?)```/g
    let m
    while ((m = fenceRe.exec(text))) {
      if (!m[1]) continue
      stat.fences++
      const body = m[2]
      const lineNo = text.slice(0, m.index).split('\n').length
      if (/(^|\n)\s*(\/\/|#)|…|\.\.\.(?!")/.test(body) && !/"\.\.\."/.test(body)) { stat.skipped++; warn(full, `L${lineNo}: JSON 블록에 주석/생략 부호(…, ...)가 있어 파싱 불가 — 예시는 완전해야 한다(브리프 §9.5)`); continue }
      let obj
      try { obj = JSON.parse(body) } catch (e) { err(full, `L${lineNo}: JSON 파싱 실패: ${e.message.slice(0, 120)}`); continue }
      stat.parsed++
      if (obj && typeof obj === 'object' && typeof obj.$schema === 'string') {
        stat.schemasInDoc++
        if (typeof obj.$id === 'string') {
          docSchemaIds.add(obj.$id)
          const saved = registryById.get(obj.$id)
          if (!saved) err(full, `L${lineNo}: 문서 내 스키마 ${obj.$id} 에 대응하는 schemas/ 파일이 없다`)
          else if (!deepEq(saved, obj)) warn(full, `L${lineNo}: 문서 내 스키마 블록과 schemas/${kebabFromId(obj.$id)}.schema.json 내용이 다르다(동기화 필요)`)
        }
        continue
      }
      // instance → find schema
      let target = null, how = ''
      if (obj && typeof obj === 'object' && typeof obj.schema_type === 'string') {
        const id = `urn:rag:schema:${kebab(obj.schema_type)}:1`
        target = registryById.get(id) || null; how = `schema_type=${obj.schema_type}`
        if (!target) { warn(full, `L${lineNo}: schema_type ${obj.schema_type} 에 대응하는 스키마(${id})가 없다`); stat.skipped++; continue }
      } else if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
        // heuristic: single primary schema in doc whose properties overlap
        const cands = [...docSchemaIds].map((id) => registryById.get(id)).filter(Boolean)
        const scored = cands.map((s) => ({ s, score: overlap(Object.keys(obj), Object.keys(s.properties || {})) })).filter((x) => x.score >= 0.6).sort((a, b) => b.score - a.score)
        if (scored.length) { target = scored[0].s; how = `heuristic(${target.$id}, overlap ${scored[0].score.toFixed(2)})` }
      }
      if (!target) { stat.skipped++; info(full, `L${lineNo}: 인스턴스 대상 스키마를 정하지 못해 검증 생략(schema_type 없음)`); continue }
      const probs = validate(obj, target, target)
      stat.validated++
      if (probs.length) err(full, `L${lineNo}: 예시가 스키마(${how})에 위배 — ${probs.slice(0, 8).join('; ')}${probs.length > 8 ? ` … 외 ${probs.length - 8}건` : ''}`)
    }
    docStats.push(stat)
  }
} else warn(CONTRACTS, '03-contracts/ 디렉터리가 없다')
function overlap(a, b) { if (!a.length) return 0; const B = new Set(b); return a.filter((k) => B.has(k)).length / a.length }
function kebabFromId(id) { const m = /^urn:rag:schema:([a-z0-9-]+):/.exec(id); return m ? m[1] : id }

// ---------------------------------------------------------------- 6. inventory coverage vs bible §5.1
const expected = ['ingest-request', 'source-document', 'parsed-document', 'normalized-document', 'chunk-set', 'enriched-chunk-set', 'embedded-chunk-set', 'index-record', 'index-commit', 'query-request', 'query-plan', 'candidate-set', 'ranked-set', 'context-pack', 'rendered-context', 'job-status', 'cloud-event-envelope', 'stage-error', 'problem-details', 'collection-spec', 'profile', 'plugin-meta', 'convert-request', 'convert-response', 'eval-dataset', 'eval-run', 'eval-report', 'user-dict-entry', 'feedback-event', 'capabilities', 'stage-policy', 'tiering-policy', 'egress-policy', 'common-types']
const present = new Set(schemaFiles.map((s) => s.name.replace(/\.schema\.json$/, '')))
for (const e of expected) if (!present.has(e)) warn(SCHEMAS, `바이블 §5.1 스키마 파일 누락: ${e}.schema.json`)
for (const p of present) if (!expected.includes(p)) info(SCHEMAS, `§5.1 인벤토리에 없는 스키마 파일: ${p}.schema.json`)

finish()
function finish() {
  const report = { root: ROOT, schemas: schemaFiles.length, errors, warnings, infos, docs: docStats }
  if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify(report, null, 2))
  const line = (tag, x) => `${tag} ${x.file}: ${x.msg}`
  if (!QUIET) {
    console.log(`# validate-contracts — schemas=${schemaFiles.length} docs=${docStats.length} errors=${errors.length} warnings=${warnings.length} infos=${infos.length}`)
    for (const s of docStats) console.log(`  ${s.file}: fences=${s.fences} parsed=${s.parsed} schemaBlocks=${s.schemasInDoc} validated=${s.validated} skipped=${s.skipped}`)
    for (const e of errors) console.log(line('ERROR', e))
    for (const w of warnings) console.log(line('WARN ', w))
    for (const i of infos) console.log(line('INFO ', i))
  }
  process.exit(errors.length ? 1 : 0)
}
