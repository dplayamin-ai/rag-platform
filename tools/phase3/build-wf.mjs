// Assemble wf-phase3.js from head + extracted (patched) outlines of the v1 script + tail.
import fs from 'node:fs'
const dir = new URL(".", import.meta.url).pathname.replace(/^/([A-Za-z]:)/, "$1") + "/"
const orig = fs.readFileSync(dir + 'wf-phase3-v1-orig.js', 'utf8')
const head = fs.readFileSync(dir + 'wf-head.js', 'utf8')
const tail = fs.readFileSync(dir + 'wf-tail.js', 'utf8')

const archM = /\/\/ ---- architecture\n([\s\S]*?)\n\]\n/.exec(orig)
const bM = /const WAVE_B = \[\n([\s\S]*?)\n\]\n/.exec(orig)
if (!archM || !bM) throw new Error('extraction failed')
let arch = archM[1], waveB = bM[1]

// [pattern, replacement, expectedCount(min)]
const patches = [
  ['PostgreSQL, 오브젝트 스토리지, Qdrant, OpenSearch, Redis, 관측성 스택', 'PostgreSQL, 오브젝트 스토리지(RustFS 또는 SeaweedFS), Qdrant, OpenSearch, Valkey, 관측성 스택', 1],
  ['모델 서빙(TEI/Infinity)', '모델 서빙(vLLM pooling / TEI — ADR-0009)', 1],
  ['Redis 용도(캐시:', 'Valkey 용도(캐시:', 1],
  ['Redis 장애(캐시 미스 허용', 'Valkey 장애(캐시 미스 허용', 1],
  ['서빙(TEI/Infinity/vLLM 컨테이너 설정 예', '서빙(vLLM pooling·TEI 컨테이너 설정 예 — Infinity는 ADR-0009로 제외', 1],
  ['서빙 TEI/Infinity/vLLM 설정', '서빙 TEI/vLLM 설정(§5.7 RerankBackend)', 1],
  ['BGE-M3 sparse/SPLADE 질의 인코딩', 'BGE-M3 sparse 질의 인코딩(SPLADE-v3는 CC-BY-NC로 제외, O-02)', 1],
  ['Postgres/MinIO/Qdrant/OpenSearch/Redis/Temporal dev server/TEI CPU', 'PostgreSQL/RustFS 또는 SeaweedFS/Qdrant/OpenSearch/Valkey/Temporal dev server/TEI CPU', 1],
  ['오브젝트 스토리지, Redis, Qdrant, OpenSearch, Temporal', '오브젝트 스토리지, Valkey, Qdrant, OpenSearch, Temporal', 1],
  ['kind=summary_parent 청크로 인덱싱', 'item_kind=summary, level=2 청크로 인덱싱(§5.7 ItemKind·ChunkLevel)', 1],
  ['exclude_chunk_ids', 'exclude_ids', 2],
  ['[cite_id] 제목', '[d1] 제목(cite_id = d{rank}, §6.1)', 1],
  ['인용 규칙 [c3] 형식', '인용 규칙 [d3] 형식', 1],
  ['응답의 [cN] 추출', '응답의 [dN] 추출', 1],
  ['render 옵션으로 anthropic/openai/xml/markdown 렌더 포함', 'renderer 옵션(바이블 §5.7 Renderer 9종)으로 RenderedContext 포함', 1],
  ['스팬 이름 규약 rag.stage.<name>', '스팬 이름 규약 rag.{stage}(§6.5)', 1],
  ['rag.stage.*, rag.retrieve.*, gen_ai.* semconv 매핑', 'rag.{stage} — rag.plan, rag.retrieve.dense, rag.rerank, rag.ingest.parse 등(§6.5), gen_ai.* semconv 매핑', 1],
  ['entry points 그룹 이름 규약(rag_platform.parsers 등)', 'entry points 그룹 이름 규약(rag_platform.{extension_point}, §6.7)', 1],
  ['격리 모드(in-process / subprocess / sidecar HTTP-gRPC — AGPL 컴포넌트는 sidecar 강제)', '격리 모드(§5.7 IsolationMode: in_process / helper_process / sidecar — C등급(GPL/AGPL) 컴포넌트는 sidecar 강제, ADR-0033)', 1],
  ['렌더러 4종 상세(anthropic:', '렌더러 상세(바이블 §9.3 Renderer 9종 전부; 정본 anthropic_search_result:', 1],
  ['Temporal 기반 설계: 워크플로우 목록(IngestBatchWorkflow', 'Temporal 기반 설계(바이블 §11 정본; 워크플로우 타입명은 §6.7 {domain}.{entity}.v{n}, 액티비티 stage.{stage_name}, 태스크 큐는 §4.4): 워크플로우 목록(ingest.document.v1 등 — 아래 이름은 역할 설명이며 정식 이름은 §11.2 — IngestBatchWorkflow', 1],
  ['태스크 큐 분리(cpu-parse, gpu-ocr, gpu-embed, io-fetch, index)', '태스크 큐 분리(§4.4 StagePolicy 표의 task_queue 값 그대로)', 1],
  ['엔드포인트 표와 상세(요청/응답 예시 JSON, 상태 코드, 에러): POST /v1/ingest', '엔드포인트 표와 상세(요청/응답 예시 JSON, 상태 코드, 에러) — 경로·메서드는 바이블 §14 API 표면 정본을 그대로 따른다(아래 목록은 참고): POST /v1/ingest', 1],
  ['POST /v1/retrieve (QueryRequest → ContextPack;', 'POST /v1/query (바이블 §14: QueryRequest → {context_pack, rendered?, explain?};', 1],
  ['POST /v1/search (RankedSet만: 경량, explain 옵션), POST /v1/retrieve/explain (QueryPlan + 점수 분해 + dropped), GET /v1/chunks/{chunk_id} (본문·provenance), POST /v1/chunks/expand (부모/이웃 확장), POST /v1/citations/resolve (cite_id → provenance), POST /v1/answer', 'POST /v1/render ({pack_id | context_pack, renderer, options} → RenderedContext), response_format=pack_only·explain 옵션(별도 엔드포인트 없음 — §14에 없는 경로는 "미해결 이슈"의 제안으로만), POST /v1/answer', 1],
  ['테넌트(CRUD, 쿼터), 컬렉션(CRUD, 프로파일 지정·버전, 통계, 재색인 시작 POST /collections/{id}/reindex, alias 상태)', '경로·메서드는 바이블 §14 그대로. 테넌트(usage·policies), 컬렉션(GET/POST /v1/collections, GET/PATCH/DELETE /v1/collections/{collection_id}, reindex, stats, dictionary)', 1],
  ['도구 정의(JSON Schema 전문 + 설명문 — 에이전트가 잘 쓰도록 작성): search(query, collection_ids, top_k, filters, budget_tokens, exclude_ids, render: markdown|structured) → ContextPack 요약(structuredContent + 텍스트), get_document(document_id, sections?) , get_chunk / expand_context(chunk_id, direction, n), list_collections, resolve_citation(cite_id), (옵션) ingest_uri(관리 권한)', '도구 정의(JSON Schema 전문 + 설명문 — 에이전트가 잘 쓰도록 작성; 도구 집합은 바이블 §14 /mcp 행과 ADR-0025 그대로): search(query, collection_ids?, top_k?, filters?, response_format?, cursor?) → mcp_tool_result 렌더(structuredContent + 텍스트), get_document(document_id, view?, cursor?), list_collections(); v1.1 후보 search_batch·expand는 "미해결 이슈"로', 1],
  ['피드백 신호 수집 API(POST /v1/feedback: pack_id/cite_id 단위 유용/무용, 답변 평가, 클릭/확장 이벤트, 에이전트 재검색 횟수)', '피드백 신호 수집 API(POST /v1/feedback: FeedbackEvent — kind cited/rated/corrected, cite_ids, rating; 바이블 §5.6·§5.7 FeedbackKind 그대로; 클릭·재검색 같은 추가 신호는 제안으로만)', 1],
  ['qrels 포맷(TREC 확장: query_id, doc_id, chunk_id 또는 span, grade)', 'qrels 포맷(TREC qrels + answer_spans JSONL — ADR-0023; EvalDataset 필드 §5.6)', 1],
  ['유의성 검정(paired t-test/윌콕슨)', '유의성 검정(paired t-test/윌콕슨 + Holm 보정 — ADR-0023)', 1],
  ['환경변수 표(이름 RAG_… | 타입 | 기본 | 설명 | 민감)', '환경변수 표(이름 RAG_… — 접두·중첩 규약은 §6.6 | 타입 | 기본 | 설명 | 민감)', 1],
  ['메트릭 카탈로그(이름 | 타입 | 라벨 | 설명) 최소 40개', '메트릭 카탈로그(이름 | 타입 | 라벨 | 설명) — 바이블 §6.5 정본 목록을 전부 포함하고 최소 40개(tenant_id 라벨 금지)', 1],
  ['ACL 강제 지점(QueryPlan effective_filters 불변식; 백엔드 pre-filter; 결과 후검증)', 'ACL 강제 지점 17개(바이블 §10.3 E1~E17 표 그대로; QueryPlan 필터 불변식 §10.2; 백엔드 사전 필터; pack acl_recheck)', 1],
  ['격리 수준 옵션(shared-with-filter / dedicated-collection / dedicated-deployment)', '격리 수준(§5.7 TenantIsolationTier: payload_filter / shard_key / index_per_tenant + §10.4·TieringPolicy E15)', 1],
  ['principal 모델 user/group/role/service', 'principal 모델(§6.1 주체 문자열 user:/group:/service:/tenant:*)', 1],
  ['Enrichment 필드: context_prefix', 'Enrichment 필드(바이블 §5.4 Enrichment 표가 정본): context_prefix', 0],
]
let all = arch + '\n@@SPLIT@@\n' + waveB
for (const [from, to, min] of patches) {
  const n = all.split(from).length - 1
  if (n < min) throw new Error(`patch expected >=${min} match(es), got ${n}: ${from.slice(0, 60)}`)
  all = all.split(from).join(to)
}
// generic date fix inside outlines (if any)
all = all.split('2026-09-18').join('2026-09-22')
// sanity: no leftovers of superseded tech in outlines
for (const bad of ['Redis', 'MinIO', 'Infinity', 'SPLADE 질의', 'PyMuPDF 기본', 'exclude_chunk_ids', 'rag.stage.']) {
  const n = all.split(bad).length - 1
  if (n) { const i = all.indexOf(bad); console.warn(`WARN leftover "${bad}" x${n} near: ${all.slice(Math.max(0, i - 80), i + 80).replace(/\n/g, ' ')}`) }
}
;[arch, waveB] = all.split('\n@@SPLIT@@\n')
if (/\$\{(?!CC\})/.test(arch + waveB)) throw new Error('unexpected template interpolation in extracted outlines')

const out = `${head}
// ---------------------------------------------------------------- Wave A: architecture (outlines from v1 script, patched to bible v1.2)
const ARCH = [
${arch}
]

// ---------------------------------------------------------------- Wave B (outlines from v1 script, patched to bible v1.2)
const WAVE_B = [
${waveB}
]
${tail}`
fs.writeFileSync(dir + 'wf-phase3.js', out)
console.log('written wf-phase3.js', out.length, 'bytes;', out.split('\n').length, 'lines; ARCH entries', (arch.match(/path: '/g) || []).length, '; WAVE_B entries', (waveB.match(/path: '/g) || []).length)
