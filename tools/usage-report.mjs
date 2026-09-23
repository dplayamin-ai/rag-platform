#!/usr/bin/env node
// usage-report.mjs — per-agent token usage and wall-clock report from Claude Code session transcripts.
// Usage: node tools/usage-report.mjs --out PAYMENT.MD
// Reads <projects>/<session>.jsonl (orchestrator) and <projects>/<session>/subagents/workflows/<run>/{journal.jsonl,agent-*.jsonl}.
import fs from 'node:fs'
import path from 'node:path'

const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const OUT = opt('--out', 'PAYMENT.MD')
const PROJ = opt('--projects', 'C:\\Users\\dplaya.min\\.claude\\projects\\C--Workspaces-rag-platform')

// Human labels for known runs (session → run → phase name). Unknown runs fall back to the journal phases.
const RUN_NAMES = {
  'wf_270deb6d-bba': '1단계 기술 지형 리서치',
  'wf_3115816b-af8': '1b단계 비전·요구사항',
  'wf_97157829-22c': '2단계 설계 경쟁·바이블',
  'wf_aae863e5-fec': '3단계 계약(contracts)',
  'wf_6d211baa-983': '3단계 아키텍처(architecture)',
  'wf_f8852269-0c1': '3단계 ADR(adrs)',
  'wf_02322627-3eb': '3단계 파이프라인(pipelines)',
  'wf_7bfc9aa6-c62': '3단계 API·평가(api-eval)',
  'wf_18a2a477-09d': '3단계 운영·개발·로드맵(ops-dev-roadmap)',
  'wf_8890c66f-daf': '3단계 계약 감사(contracts-audit)',
}
const SESSION_NAMES = {
  '191997a7-5344-4140-8c45-e6e69a62b25f': '세션 1 (2026-09-18~22: 브리프, 1·1b·2단계)',
  'dd0ede14-9151-48af-9821-b4079efd2595': '세션 2 (2026-09-22: 3단계 준비·실행)',
}

function readJsonl(p) {
  const out = []
  for (const line of fs.readFileSync(p, 'utf8').split('\n')) { if (!line.trim()) continue; try { out.push(JSON.parse(line)) } catch { /* skip partial line */ } }
  return out
}
function usageOf(lines) {
  const u = { calls: 0, input: 0, cache_write: 0, cache_read: 0, output: 0, tool_uses: 0, models: new Set(), first: null, last: null }
  for (const l of lines) {
    if (l.timestamp) { if (!u.first || l.timestamp < u.first) u.first = l.timestamp; if (!u.last || l.timestamp > u.last) u.last = l.timestamp }
    if (l.type !== 'assistant' || !l.message) continue
    const m = l.message
    if (m.usage) {
      u.calls++
      u.input += m.usage.input_tokens || 0
      u.cache_write += m.usage.cache_creation_input_tokens || 0
      u.cache_read += m.usage.cache_read_input_tokens || 0
      u.output += m.usage.output_tokens || 0
    }
    if (m.model) u.models.add(m.model)
    if (Array.isArray(m.content)) u.tool_uses += m.content.filter((c) => c && c.type === 'tool_use').length
  }
  u.total = u.input + u.cache_write + u.cache_read + u.output
  return u
}
const kst = (iso) => iso ? new Date(new Date(iso).getTime() + 9 * 3600 * 1000).toISOString().replace('T', ' ').slice(5, 16) : '-'
const mins = (a, b) => (a && b) ? ((new Date(b) - new Date(a)) / 60000) : 0
const fmt = (n) => Math.round(n).toLocaleString('en-US')
const fmin = (m) => m >= 60 ? `${Math.floor(m / 60)}h ${Math.round(m % 60)}m` : `${m.toFixed(1)}m`
const short = (s, n = 58) => (s.length > n ? s.slice(0, n - 1) + '…' : s)
const modelStr = (set) => [...set].map((m) => m.replace('claude-', '')).join(', ') || '-'

const sessions = fs.readdirSync(PROJ).filter((f) => f.endsWith('.jsonl') && fs.existsSync(path.join(PROJ, f.replace(/\.jsonl$/, ''))))
  .map((f) => f.replace(/\.jsonl$/, '')).sort((a, b) => fs.statSync(path.join(PROJ, a + '.jsonl')).mtimeMs - fs.statSync(path.join(PROJ, b + '.jsonl')).mtimeMs)

const report = [], grand = { calls: 0, input: 0, cache_write: 0, cache_read: 0, output: 0, tool_uses: 0, agents: 0, minutes: 0 }
const add = (acc, u) => { acc.calls += u.calls; acc.input += u.input; acc.cache_write += u.cache_write; acc.cache_read += u.cache_read; acc.output += u.output; acc.tool_uses += u.tool_uses }

for (const sid of sessions) {
  const sess = { id: sid, name: SESSION_NAMES[sid] || sid, orchestrator: null, runs: [] }
  const mainLines = readJsonl(path.join(PROJ, sid + '.jsonl'))
  sess.orchestrator = usageOf(mainLines)
  sess.orchestrator.minutes = mins(sess.orchestrator.first, sess.orchestrator.last)
  const wfDir = path.join(PROJ, sid, 'subagents', 'workflows')
  if (fs.existsSync(wfDir)) {
    for (const run of fs.readdirSync(wfDir).sort((a, b) => fs.statSync(path.join(wfDir, a)).birthtimeMs - fs.statSync(path.join(wfDir, b)).birthtimeMs)) {
      const rd = path.join(wfDir, run)
      const journal = fs.existsSync(path.join(rd, 'journal.jsonl')) ? readJsonl(path.join(rd, 'journal.jsonl')) : []
      const meta = {}
      for (const j of journal) {
        if (j.type === 'started') meta[j.agentId] = { label: j.label, phase: j.phase, status: 'running' }
        if (j.type === 'result' && meta[j.agentId]) meta[j.agentId].status = j.result === null ? 'empty' : 'done'
        if (j.type === 'failed' && meta[j.agentId]) meta[j.agentId].status = 'failed'
      }
      const agents = []
      for (const f of fs.readdirSync(rd).filter((x) => /^agent-.*\.jsonl$/.test(x))) {
        const id = f.replace(/^agent-/, '').replace(/\.jsonl$/, '')
        const u = usageOf(readJsonl(path.join(rd, f)))
        const m = meta[id] || {}
        let label = m.label
        if (!label) { const mp = path.join(rd, `agent-${id}.meta.json`); if (fs.existsSync(mp)) { try { label = JSON.parse(fs.readFileSync(mp, 'utf8')).description } catch { /* ignore */ } } }
        agents.push({ id, label: label || id, phase: m.phase || '-', status: m.status || 'unknown', ...u, minutes: mins(u.first, u.last) })
      }
      agents.sort((a, b) => (a.first || '').localeCompare(b.first || ''))
      const tot = { calls: 0, input: 0, cache_write: 0, cache_read: 0, output: 0, tool_uses: 0 }
      for (const a of agents) add(tot, a)
      const first = agents.map((a) => a.first).filter(Boolean).sort()[0], last = agents.map((a) => a.last).filter(Boolean).sort().at(-1)
      sess.runs.push({ id: run, name: RUN_NAMES[run] || run, agents, tot: { ...tot, total: tot.input + tot.cache_write + tot.cache_read + tot.output }, first, last, minutes: mins(first, last), phases: [...new Set(agents.map((a) => a.phase))] })
    }
  }
  report.push(sess)
}

// ---------------------------------------------------------------- render
const L = []
L.push('# PAYMENT — 에이전트별 토큰 사용량과 수행 시간')
L.push('')
L.push(`생성: ${kst(new Date().toISOString())} KST · 원천: Claude Code 세션 트랜스크립트(\`${PROJ}\`) · 생성 도구: \`tools/usage-report.mjs\``)
L.push('')
L.push('토큰 열의 의미: **입력**(비캐시 입력), **캐시 쓰기**(프롬프트 캐시 생성 입력), **캐시 읽기**(캐시 적중 입력), **출력**(생성 토큰), **합계**(네 값의 합). 비용은 모델·계층별 단가가 다르므로(캐시 읽기·쓰기는 별도 단가) 이 표의 네 열에 현재 단가표를 곱해 산출한다. 시각은 KST, 소요는 에이전트 첫 메시지~마지막 메시지의 실제 경과 시간이다(동시 실행이므로 합계 소요는 실제 경과 시간보다 길다).')
L.push('')

// grand summary
L.push('## 1. 총계')
L.push('')
L.push('| 구분 | 에이전트 | API 호출 | 도구 호출 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |')
L.push('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
for (const s of report) {
  const o = s.orchestrator
  L.push(`| ${s.name} — 오케스트레이터(메인 세션) | 1 | ${fmt(o.calls)} | ${fmt(o.tool_uses)} | ${fmt(o.input)} | ${fmt(o.cache_write)} | ${fmt(o.cache_read)} | ${fmt(o.output)} | ${fmt(o.total)} |`)
  add(grand, o); grand.agents += 1
  for (const r of s.runs) {
    L.push(`| ${s.name.split(' ')[0]} ${s.name.split(' ')[1]} — ${r.name} (${r.agents.length} 에이전트, ${fmin(r.minutes)}) | ${r.agents.length} | ${fmt(r.tot.calls)} | ${fmt(r.tot.tool_uses)} | ${fmt(r.tot.input)} | ${fmt(r.tot.cache_write)} | ${fmt(r.tot.cache_read)} | ${fmt(r.tot.output)} | ${fmt(r.tot.total)} |`)
    add(grand, r.tot); grand.agents += r.agents.length
  }
}
const gtotal = grand.input + grand.cache_write + grand.cache_read + grand.output
L.push(`| **전체** | **${grand.agents}** | **${fmt(grand.calls)}** | **${fmt(grand.tool_uses)}** | **${fmt(grand.input)}** | **${fmt(grand.cache_write)}** | **${fmt(grand.cache_read)}** | **${fmt(grand.output)}** | **${fmt(gtotal)}** |`)
L.push('')

// per phase breakdown per run
L.push('## 2. 워크플로우·단계별 요약')
L.push('')
L.push('| 세션 | 워크플로우(Run ID) | 단계(phase) | 에이전트 | 완료/실패/진행 | 소요(실제 경과(첫~끝)) | 에이전트 활동 시간 합산 | 출력 토큰 | 합계 토큰 |')
L.push('|---|---|---|---:|---|---|---:|---:|---:|')
for (const s of report) for (const r of s.runs) {
  for (const ph of r.phases) {
    const ag = r.agents.filter((a) => a.phase === ph)
    const st = { done: 0, failed: 0, running: 0, empty: 0, unknown: 0 }; for (const a of ag) st[a.status] = (st[a.status] || 0) + 1
    const f = ag.map((a) => a.first).filter(Boolean).sort()[0], l = ag.map((a) => a.last).filter(Boolean).sort().at(-1)
    L.push(`| ${s.name.split(' ').slice(0, 2).join(' ')} | ${r.name} (\`${r.id}\`) | ${ph} | ${ag.length} | ${st.done}/${st.failed}/${st.running + st.unknown}${st.empty ? ` (빈 결과 ${st.empty})` : ''} | ${kst(f)} → ${kst(l)} (${fmin(mins(f, l))}) | ${fmin(ag.reduce((x, a) => x + a.minutes, 0))} | ${fmt(ag.reduce((x, a) => x + a.output, 0))} | ${fmt(ag.reduce((x, a) => x + a.total, 0))} |`)
  }
}
L.push('')

// per agent
L.push('## 3. 에이전트별 상세')
L.push('')
L.push('상태: done = 결과 반환, failed = API 오류로 중단(프록시 차단 등), running = 보고 시점에 진행 중(부분 집계), empty = null 결과.')
L.push('')
for (const s of report) {
  L.push(`### ${s.name}`)
  L.push('')
  const o = s.orchestrator
  L.push(`오케스트레이터(메인 세션): ${kst(o.first)} → ${kst(o.last)} (${fmin(o.minutes)}), API 호출 ${fmt(o.calls)}, 도구 호출 ${fmt(o.tool_uses)}, 모델 ${modelStr(o.models)}, 입력 ${fmt(o.input)} / 캐시 쓰기 ${fmt(o.cache_write)} / 캐시 읽기 ${fmt(o.cache_read)} / 출력 ${fmt(o.output)} / 합계 ${fmt(o.total)}`)
  L.push('')
  for (const r of s.runs) {
    L.push(`#### ${r.name} — \`${r.id}\` · ${r.agents.length} 에이전트 · 실제 경과 시간 ${kst(r.first)} → ${kst(r.last)} (${fmin(r.minutes)}${r.minutes > 24 * 60 ? ', 중단 후 재개 구간 포함' : ''}) · 에이전트 활동 시간 합산 ${fmin(r.agents.reduce((x, a) => x + a.minutes, 0))} · 합계 ${fmt(r.tot.total)} 토큰(출력 ${fmt(r.tot.output)})`)
    L.push('')
    L.push('| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |')
    L.push('|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    r.agents.forEach((a, i) => {
      L.push(`| ${i + 1} | ${short(a.label)} | ${a.phase} | ${a.status} | ${modelStr(a.models)} | ${kst(a.first)} | ${fmin(a.minutes)} | ${a.calls} | ${a.tool_uses} | ${fmt(a.input)} | ${fmt(a.cache_write)} | ${fmt(a.cache_read)} | ${fmt(a.output)} | ${fmt(a.total)} |`)
    })
    L.push(`| | **소계** | | | | | **${fmin(r.agents.reduce((x, a) => x + a.minutes, 0))}** | **${fmt(r.tot.calls)}** | **${fmt(r.tot.tool_uses)}** | **${fmt(r.tot.input)}** | **${fmt(r.tot.cache_write)}** | **${fmt(r.tot.cache_read)}** | **${fmt(r.tot.output)}** | **${fmt(r.tot.total)}** |`)
    L.push('')
  }
}
L.push('## 4. 산출 방법과 한계')
L.push('')
L.push('- 각 에이전트 트랜스크립트(`agent-<id>.jsonl`)의 assistant 메시지 `usage` 필드를 합산했다. 재시도로 중복 과금된 호출이 있으면 실제 청구와 차이가 날 수 있다.')
L.push('- 오케스트레이터 행은 메인 세션 트랜스크립트(`<session>.jsonl`) 기준이며, 컨텍스트 요약(compaction)으로 잘린 구간이 있으면 그 이전 호출은 포함되지 않을 수 있다.')
L.push('- `running` 상태 에이전트는 보고 생성 시점까지의 부분 집계다. 워크플로우가 끝난 뒤 `node tools/usage-report.mjs --out PAYMENT.MD` 를 다시 실행하면 갱신된다.')
L.push('- 소요 시간은 실제 경과 시간(첫 메시지~마지막 메시지)이며 대기·큐잉 시간을 포함한다. 워크플로우는 동시 실행(워크플로우당 최대 6)이므로 에이전트 소요 합계 ≠ 경과 시간.')
L.push('')
fs.writeFileSync(OUT, L.join('\n'))
console.log(`written ${OUT}: sessions=${report.length}, runs=${report.reduce((x, s) => x + s.runs.length, 0)}, agents=${grand.agents}, total tokens=${fmt(gtotal)}, output=${fmt(grand.output)}`)
for (const s of report) { console.log(`- ${s.name}: orchestrator ${fmt(s.orchestrator.total)} (${fmin(s.orchestrator.minutes)})`); for (const r of s.runs) console.log(`    ${r.name}: ${r.agents.length} agents, ${fmt(r.tot.total)} tokens, out ${fmt(r.tot.output)}, ${fmin(r.minutes)}, statuses=${JSON.stringify(r.agents.reduce((o, a) => (o[a.status] = (o[a.status] || 0) + 1, o), {}))}`) }
