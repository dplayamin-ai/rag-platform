// Phase 3 본 워크플로의 앞부분 조각(fragment) — `build-wf.mjs`가 이 파일 + 패치된 v1 개요 + `wf-tail.js`를
// 이어붙여 `wf-phase3.js`를 만든다(일회성 도구, 단독 실행 대상 아님).
// 설계 근거: `docs/12-appendix/00-progress-report.md` §7.2d(계약·아키텍처·ADR·파이프라인·API·평가·운영·개발·
// 로드맵 문서 작성 계획).
// 구성: `meta`(워크플로 메타데이터·단계 목록), 문서별 작성·양면 적대적 리뷰·수정·검증 헬퍼 함수들.
// 불변식: Phase 3가 이미 완료·커밋되었으므로 이 조각은 재실행 대상이 아니다(기록 보존 목적).
// 검증 계층: 1층(여기서 검증) — 조립된 `wf-phase3.js`는 Phase 3 완료 시점에 이미 실행·검증되었다.
export const meta = {
  name: 'rag-phase3-core-docs',
  description: 'RAG Platform Phase 3: write contracts + JSON Schemas, architecture, ADRs, pipelines, API, evaluation, operations, development, roadmap docs; each doc gets two-lens adversarial review, fix, verification; contract audit; OpenAPI; completeness critic',
  phases: [
    { title: 'Contracts T0', detail: 'contract overview + common-types schema, error model, versioning' },
    { title: 'Contracts T1', detail: '14 stage/operational contract docs + schemas' },
    { title: 'Architecture', detail: '02-architecture 01~09' },
    { title: 'ADRs', detail: '38 ADRs (MADR) + index' },
    { title: 'Contract Audit', detail: 'mechanical validator + semantic audits + fixes' },
    { title: 'Pipelines', detail: '04-pipelines 01~19' },
    { title: 'API & Evaluation', detail: '05-api 01~07, 08-evaluation 01~06' },
    { title: 'Ops, Dev, Roadmap', detail: '09-operations, 10-development, 11-roadmap' },
    { title: 'OpenAPI', detail: 'assemble and review openapi.yaml' },
    { title: 'Completeness Critic', detail: 'gap review across the whole doc set' },
  ],
}

// ---------------------------------------------------------------- constants
const GROUP = (args && args.group) || 'contracts'
const DATE = (args && args.date) || '2026-09-22'
const ROOT = 'C:\\Workspaces\\rag-platform'
const D = ROOT + '\\docs\\'
const BRIEF = D + '00-vision\\00-design-brief.md'
const BIBLE = D + '02-architecture\\00-design-bible.md'
const MATRIX = D + '07-tech-landscape\\00-summary-and-selection-matrix.md'
const SCHEMAS = ROOT + '\\schemas\\'
const VALIDATOR = (args && args.validator) || 'C:\\Workspaces\\rag-platform\\tools\\validate-contracts.mjs'
const W = (p) => D + p.replace(/\//g, '\\')

// ---------------------------------------------------------------- structured output schemas
const FINDING = { type: 'object', properties: {
  severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
  location: { type: 'string', description: 'section heading or line number' },
  problem: { type: 'string' },
  fix: { type: 'string', description: 'concrete fix; for spelling/anchor issues cite the canonical form and bible section' },
}, required: ['severity', 'location', 'problem', 'fix'] }
const REVIEW = { type: 'object', properties: {
  findings: { type: 'array', items: FINDING },
  verdict: { type: 'string', enum: ['accept', 'revise', 'rewrite'] },
  checked: { type: 'array', items: { type: 'string' }, description: 'what was actually cross-checked (bible sections, files, commands run)' },
}, required: ['findings', 'verdict', 'checked'] }
const DONE = { type: 'object', properties: {
  file: { type: 'string' },
  summary: { type: 'string' },
  defined: { type: 'array', items: { type: 'string' }, description: 'types/fields/IDs/endpoints this doc defines that others reference' },
  open_issues: { type: 'array', items: { type: 'string' } },
  extra_files: { type: 'array', items: { type: 'string' }, description: 'other files written (schemas, yaml)' },
  lines: { type: 'integer' },
}, required: ['file', 'summary', 'defined', 'open_issues', 'extra_files', 'lines'] }
const VERIFY = { type: 'object', properties: {
  resolved: { type: 'array', items: { type: 'string' } },
  unresolved: { type: 'array', items: FINDING },
  new_issues: { type: 'array', items: FINDING },
  verdict: { type: 'string', enum: ['pass', 'fail'] },
}, required: ['resolved', 'unresolved', 'new_issues', 'verdict'] }
const CONS = { type: 'object', properties: {
  issues: { type: 'array', items: { type: 'object', properties: {
    file: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' },
    severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
  }, required: ['file', 'problem', 'fix', 'severity'] } },
  canonical_decisions: { type: 'array', items: { type: 'string' }, description: 'when two docs disagree, the chosen canonical form and the bible section that decides it' },
  checked_pairs: { type: 'array', items: { type: 'string' } },
}, required: ['issues', 'canonical_decisions', 'checked_pairs'] }
const TOOLRUN = { type: 'object', properties: {
  errors_before: { type: 'integer' }, errors_after: { type: 'integer' }, warnings_after: { type: 'integer' },
  iterations: { type: 'integer' }, files_changed: { type: 'array', items: { type: 'string' } },
  residual: { type: 'array', items: { type: 'string' }, description: 'errors that could not be fixed and why' },
}, required: ['errors_before', 'errors_after', 'warnings_after', 'iterations', 'files_changed', 'residual'] }

// ---------------------------------------------------------------- bible reading hints
const BIBLE_COMMON = '§1(우선순위·변경 절차), §3.1~3.2(결정 표 — 이 문서와 관련된 행), §3.3(ADR 번호·slug), §5.1(계약 인벤토리), §5.7(열거 정본·이벤트 카탈로그·오류 코드), §6(명명 규약)'
const HINTS = {
  '02-architecture/01': '§2(아키텍처 요약·C4·컨테이너 책임), §4(스테이지 표), §7.1(프로파일 컴포넌트), §12(모듈 맵), §13(저장소), §14(API 표면)',
  '02-architecture/02': '§2.1(핵심 아이디어), §4.1(스테이지 공통 규약), §12(모듈/패키지 맵 전체), §5.3(Capabilities·StagePolicy), §11.1',
  '02-architecture/03': '§4(스테이지 파이프라인 전체), §11.4(세대 사가), §11.5(잡 상태 기계), §13(저장소·원장), §6.2(stage_key·lineage 해시)',
  '02-architecture/04': '§13(저장소 정본 전체), §7.1, §11.4, §5.4 IndexRecord 표, §10.4(격리 수준)',
  '02-architecture/05': '§12(모듈 맵), §7(프로파일 정본 전체), §5.3(Capabilities·IndexBackendCapabilities·StagePolicy), §5.6 PluginMeta, §3.1 D-02·D-10, §11.1',
  '02-architecture/06': '§11(오케스트레이션 정본 전체), §4.4(StagePolicy 표), §4.2~4.3, §3.2 O-06',
  '02-architecture/07': '§10(멀티테넌시·ACL 정본 전체), §5.3(SecurityContext·Principal·Acl·EgressPolicy), §3.1 D-09, §6.1 주체 규약',
  '02-architecture/08': '§2.2(C4 Container), §7.1(프로파일 컴포넌트 표), §12, §13, §6.7(이미지·패키지), §3.1 D-02(GPL 사이드카 격리)',
  '02-architecture/09': '§11.3(재시도 분류), §11.4(보상), §4.2~4.4(실패 정책 열), §8.3(지연 예산), §15(리스크)',
  '04-pipelines/01': '§4.1(스테이지 공통 규약), §11.1(두 실행기), §12(core 모듈), §5.3(ArtifactRef·Producer·StagePolicy), §6.2(stage_key)',
  '04-pipelines/02': '§4.2 fetch·detect 행, §5.3 EgressPolicy, §10.3 E16, §5.4 SourceDocument, §13.3',
  '04-pipelines/03': '§4.2 detect·parse 행, §5.7 SourceFormat·SourceKind·PageStatus, §5.4 ParsedDocument·Block, §7.3 parse.router',
  '04-pipelines/04': '§4.2 parse 행, §5.4 ParsedDocument·Block·TableData 표, §5.3 Provenance, §5.6 ConvertRequest/Response, §3.1 D-18, §3.2 O-07',
  '04-pipelines/05': '§4.2 parse 행, §5.4 ParsedDocument·Block·TableData 표, §5.3 Provenance(bbox 좌표계), §3.1 D-18, §3.2 O-08',
  '04-pipelines/06': '§4.2 parse 행, §5.4 ParsedDocument·Block, §5.6 ConvertRequest/Response, §3.1 D-02·D-18',
  '04-pipelines/07': '§4.2 parse 행, §5.4 ParsedDocument·Block, §5.3 Provenance(element_path=XPath)',
  '04-pipelines/08': '§4.2 parse 행, §5.4 ParsedDocument·Block, §5.7 SourceFormat',
  '04-pipelines/09': '§4.2 normalize 행, §5.4 NormalizedDocument·NormalizedBlock 표, §6.3(NFC/NFKC·오프셋), §5.7 FurnitureReason·Genre·PiiPolicy, §3.3 ADR-0021·0029',
  '04-pipelines/10': '§4.2 chunk·recount 행, §5.4 ChunkSet·Chunk 표(불변식 포함), §7.2(청크 파라미터), §5.7 ItemKind·ChunkLevel·TableSerialization, §3.2 O-09, §3.3 ADR-0019·0020',
  '04-pipelines/11': '§4.2 enrich 행, §5.4 EnrichedChunkSet·Enrichment·Entity 표, §7.2, §5.7 KeywordSource·EntityExtractor·EnrichStatus, §3.2 O-05, §3.3 ADR-0016·0029',
  '04-pipelines/12': '§4.2 embed 행, §5.4 EmbeddedChunkSet·VectorBundle 표, §7.1(임베딩 서빙), §5.7 VectorName·Pooling·EmbeddingMode, §6.2 embedding_space_id, §3.1 D-16, §3.3 ADR-0009·0010',
  '04-pipelines/13': '§4.2 index 행, §5.4 IndexRecord·IndexCommit 표, §11.4(세대 사가), §13.4(물리명), §6.1~6.2 record_id·point_id, §3.1 D-15, §3.3 ADR-0004·0012·0026',
  '04-pipelines/14': '§4.3 plan 행, §8.1(알고리즘 1~6단계), §5.5 QueryRequest·QueryPlan 표, §5.3 FilterNode·SecurityContext, §10.2(필터 불변식), §5.7 Route·Complexity·Strategy·QueryRole·FilterOp·FilterableField',
  '04-pipelines/15': '§4.3 retrieve·fuse·hydrate 행, §8(검색 경로 정본 전체), §5.5 CandidateSet·RankedSet 표, §5.3 ChannelScore·ScoreBreakdown, §3.2 O-01·O-02, §3.3 ADR-0013·0014·0030·0034',
  '04-pipelines/16': '§4.3 rerank 행, §8.1~8.3, §5.5 RankedSet 표, §5.7 RerankBackend·RerankResponseSchema·ScoreNormalization, §3.2 O-04',
  '04-pipelines/17': '§4.3 postprocess·pack·render 행, §8.2(후처리·pack 서브스텝), §9(ContextPack·렌더러 정본 전체), §5.5 ContextPack·ContextItem·RenderedContext 표, §3.1 D-07·D-20, §3.3 ADR-0024',
  '04-pipelines/18': '§3.2 O-03·O-04, §5.7 Strategy·Channel·ItemKind(level 2), §8.1, §5.3 Entity·Relation, §3.3 ADR-0015·0010',
  '04-pipelines/19': '§11.4(세대 사가·보상), §11.5, §4.2 index 행, §13.1(원장 테이블), §14(reprocess·acl·metadata·reindex 엔드포인트), §3.3 ADR-0005·0026',
  '05-api/01': '§14(API 표면 정본 전체), §6.7(엔드포인트 규약), §5.3 ProblemDetails, §10.1, §3.1 D-08, §3.2 O-10, §3.3 ADR-0018',
  '05-api/02': '§14(ingest·jobs·documents 행), §11.5(잡 상태 ↔ API), §5.4 IngestRequest, §5.6 JobStatus, §3.1 D-08',
  '05-api/03': '§14(query·render·answer 행), §5.5 QueryRequest·ContextPack·RenderedContext, §9.3~9.4, §8.3(지연 예산), §10.2',
  '05-api/04': '§14(collections·profiles·tenants·subscriptions·eval·schemas 행), §5.6 CollectionSpec·Profile·UserDictEntry, §7.4(검증 규칙), §13.1',
  '05-api/05': '§14 /mcp 행과 /.well-known 행, §9.3(mcp_tool_result 렌더러), §5.5 QueryRequest(cursor·session_id·exclude_ids), §3.1 D-13, §3.3 ADR-0025',
  '05-api/06': '§14, §6.7(패키지명), §9.3(렌더러), §5.3 ProblemDetails',
  '05-api/07': '§5.3 CloudEventEnvelope, §5.7 이벤트 카탈로그, §6.2(웹훅 서명), §6.5, §3.2 O-06, §3.3 ADR-0017·0038, §14 subscriptions·events 행',
  '08-evaluation/01': '§5.6 EvalDataset·EvalRun·EvalReport, §7.4(품질 게이트), §3.1 D-12, §3.3 ADR-0023, §15',
  '08-evaluation/02': '§5.6 EvalDataset·EvalRun·EvalReport, §5.5 RankedSet(TREC run), §7.4, §3.3 ADR-0023·0030',
  '08-evaluation/03': '§5.6 EvalDataset, §5.7 JudgmentLevel·LabelProvenance, §3.3 ADR-0023',
  '08-evaluation/04': '§5.5 ContextPack(sufficiency·citation_map), §9.3, §5.6 EvalReport, §3.3 ADR-0024',
  '08-evaluation/05': '§7.2(파라미터 기본값), §7.4(게이트), §3.2 O-01~O-09(실측 확정 조건), §8.3',
  '08-evaluation/06': '§5.6 FeedbackEvent, §5.7 FeedbackKind·이벤트 카탈로그(feedback.*), §14 feedback 행',
  '09-operations/01': '§2.2~2.3, §7.1(프로파일 컴포넌트), §11.6(개발 모드), §13, §6.6(환경 변수), §6.7(이미지)',
  '09-operations/02': '§6.6(환경 변수 규약), §7(프로파일 정본 전체: 7.1~7.4), §5.6 Profile, §4.4 StagePolicy',
  '09-operations/03': '§6.5(이벤트·메트릭·스팬·로그 규약 — 정본 메트릭 목록), §3.1 D-11, §3.3 ADR-0022, §5.3 DegradedEntry',
  '09-operations/04': '§8.3(지연 예산), §4.4(큐·정책), §13.4, §7.1~7.2, §11.2',
  '09-operations/05': '§10(멀티테넌시·ACL), §3.1 D-02·D-09, §5.3 EgressPolicy, §6.6(비밀), §3.3 ADR-0001·0027·0038',
  '09-operations/06': '§11.3~11.5, §4.2~4.4(실패 정책), §15(리스크), §5.7 오류 코드',
  '09-operations/07': '§13(저장소·원장), §11.4(세대 사가·복구=재적재), §2.1 K6',
  '09-operations/08': '§1.2(변경 절차), §6.4(schema_version), §7(profile_hash·blue/green), §11.4',
  '10-development/01': '§12(모듈/패키지 맵 전체), §6.7(패키지·이미지·저장소)',
  '10-development/02': '§11.6(개발 모드 5분 기동), §6.6, §7.1 lite 열',
  '10-development/03': '§6(명명 규약 전체), §12, §4.1, §3.1 D-01, §3.3 ADR-0035·0036',
  '10-development/04': '§1.2(CI 게이트), §7.4, §5.1, §3.3 ADR-0032(적합성 키트)',
  '10-development/05': '§1.2, §3.1 D-01·D-02, §6.7',
  '10-development/06': '§12, §5.3 Capabilities, §5.6 PluginMeta, §7.4, §3.3 ADR-0032·0033, §6.1 plugin_id',
  '10-development/07': '§1.2(변경 절차·ADR)',
  '10-development/08': '§1.2, §6.4, §6.7',
  '11-roadmap/01': '§3.3(ADR 우선순위 P0~P3), §2.1, §7.1(프로파일별 컴포넌트), §15',
  '11-roadmap/02': '§12(모듈 맵 — 태스크 분해 단위), §4(스테이지), §3.3',
  '11-roadmap/03': '§15(리스크 Top 10), §3.1~3.2, §미해결 이슈',
}
function hint(p) { const k = p.slice(0, p.indexOf('/') + 3); return HINTS[k] || HINTS[p.slice(0, 16)] || '이 문서 주제와 관련된 절(§ 헤더로 판단)' }

// ---------------------------------------------------------------- prompts
const conv = (d, extraReads) => `## 공통 규약 (반드시 준수)
- 읽기 순서: (1) 설계 브리프 ${BRIEF} 전체 (2) 설계 바이블 ${BIBLE} — 258KB이므로 한 번에 읽지 말고, 먼저 Grep으로 헤더(^## |^### |^#### )의 줄 번호를 얻은 뒤 공통 필수 절 [${BIBLE_COMMON}] 과 이 문서 지정 절 [${d.bible || hint(d.path)}] 을 Read(offset/limit)로 읽는다. 타입 표는 Grep으로 "#### \`TypeName\`" 을 찾아 그 절을 읽는다 (3) 선정 매트릭스 ${MATRIX} 는 이 문서 주제 관련 절만 (4) depends_on 문서${extraReads ? ' 및 ' + extraReads : ''}.
- 정본 규칙: 아래 "내용 지시"의 필드명·열거값·기술명·엔드포인트·이벤트명은 방향 제시일 뿐이다. 바이블(§5 계약 표, §5.7 열거, §6 명명, §7 프로파일, §14 API 표면)과 다르면 **바이블이 정본**이며 지시를 무시한다. 바이블에 없는 것은 단정하지 말고 선택 필드(N) 또는 "## 미해결 이슈"의 제안으로만 남긴다. 브리프 D-xx·바이블 결정 레지스터·열거 철자를 절대 바꾸지 않는다.
- depends_on 문서가 아직 없으면(동시 작성 중) 바이블 해당 절을 정본으로 삼고, 링크만 문서 맵 경로로 건다. 링크는 브리프 §8 산출물 맵에 있는 경로만 상대 경로로 쓴다. 바이블 인용은 절 번호로 쓴다("바이블 §5.7").
- 한국어 본문, 영문 식별자(snake_case 필드, PascalCase 타입, snake_case 열거값). 기술 용어 첫 등장 시 한국어(English) 병기. 이모지·ASCII 아트·과장 금지. 다이어그램은 Mermaid.
- frontmatter(YAML): title, status: review, owner: architecture, version: 0.1.0, last_updated: ${DATE}, depends_on(실제 읽은 문서의 상대 경로 배열)${d.path.startsWith('03-contracts/') ? ', schema_version: "1.0.0"' : ''}.
- 구조: # 제목 → ## 목적 → ## 범위 → 본문 → ## 결정 사항 요약 → ## 미해결 이슈 → ## 참조.${d.path.startsWith('03-contracts/') ? ' 계약 문서는 ## 스키마, ## 예시, ## 불변식(Invariants), ## 버전 이력 절 필수.' : ''}
- 결정은 \`**결정:**\`으로 시작하고 관련 ADR을 링크한다(경로 ../06-adr/NNNN-slug.md, 번호·slug는 바이블 §3.3 표 그대로). 수치는 표로, 근거 없는 수치 금지("초안 목표" 명시). 외부 라이브러리 API·버전·라이선스는 docs/07-tech-landscape 근거가 있을 때만 단정, 아니면 "확인 필요(as of 2026-09)".
- 다른 에이전트가 동시에 다른 문서를 쓰고 있다. 지정된 파일(과 명시된 부속 파일)만 쓴다. \`schemas/common-types.schema.json\` 은 03-contracts/00 문서만 수정한다.
- JSON 코드 블록은 완전한 JSON(주석·생략 부호 금지)이어야 하며, 저장한 스키마·예시는 node -e "JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'))" <파일> 로 문법을 검증한다. 문서 안의 예시 JSON은 임시 파일에 써서 같은 방법으로 검증한다.`

function writeP(d, extraReads) {
  return `당신은 이 오픈소스 RAG 플랫폼의 수석 아키텍트 겸 테크니컬 라이터다. 다음 문서를 작성한다.

파일: ${W(d.path)}
제목: ${d.title}
depends_on(반드시 읽을 문서, docs/ 기준 상대): ${JSON.stringify(d.deps || [])}

## 내용 지시
${d.outline}

${conv(d, extraReads)}

분량 ${d.len || '350~900'}행(브리프 §9.11). Write 도구로 저장한 뒤 구조화 결과를 반환한다(defined에는 이 문서가 정의한 타입/필드/ID/엔드포인트/이벤트/오류 코드 이름을 나열, lines에는 저장한 문서의 줄 수).`
}
function reviewAnchorP(d) {
  return `당신은 앵커 준수 감사자다. 문서를 앵커 문서와 **행 단위로 대조**하여 적대적으로 검토한다. 문서를 수정하지 말고 결과만 반환한다.

문서: ${W(d.path)}
앵커: 브리프 ${BRIEF}(§4 확정 결정, §8 문서 맵, §9 규약), 바이블 ${BIBLE}(공통 필수 절 [${BIBLE_COMMON}] + 지정 절 [${d.bible || hint(d.path)}]; 바이블은 Grep으로 헤더 줄 번호를 얻어 필요한 절만 Read), depends_on: ${JSON.stringify(d.deps || [])}.

검토 항목(각각 실제로 대조한 근거를 checked에 남긴다):
1. 철자 대조: 문서에 등장하는 모든 타입명·필드명·열거값·ID 형식·해시 결합식·엔드포인트·이벤트 이름·오류 코드·메트릭 이름을 바이블 §5/§5.7/§6/§14 와 대조한다. 다른 철자·다른 의미·바이블에 없는 임의 이름은 각각 finding 하나(fix에 정본 철자와 바이블 절 번호를 적는다).
2. 누락: ${d.path.startsWith('03-contracts/') ? '바이블 해당 타입 표의 모든 필드(필수/타입/의미)가 문서 필드 표·스키마·Pydantic·예시에 들어 있는가. 봉투 필드(§5.2)와 공용 타입 $ref 사용이 맞는가.' : '바이블이 이 주제에 대해 확정한 규칙·파라미터·불변식이 문서에 반영되어 있는가.'}
3. 결정 위반: 브리프 D-01~D-20, 바이블 §3 결정 레지스터·O-xx 해결과 모순되는 서술; 앵커에 없는 결정을 단정적으로 도입(미해결 이슈로 남겨야 함); 바이블이 기각한 대안(예: chunk_ulid, kind/item_kind 이중, PyMuPDF·pyhwp 기본, Redis/MinIO 기본, TEI로 BGE-M3 sparse, SPLADE 기본)의 재등장.
4. depends_on 문서와의 불일치(필드명·ID·절 번호 인용).
5. 문서 규약: frontmatter 필드(title, status, owner, version, last_updated, depends_on${d.path.startsWith('03-contracts/') ? ', schema_version' : ''}), 절 구조(목적/범위/결정 사항 요약/미해결 이슈/참조${d.path.startsWith('03-contracts/') ? ' + 스키마/예시/불변식/버전 이력' : ''}), 링크가 브리프 §8 문서 맵 경로인가(존재하지 않는 문서 링크 금지), 이모지·과장·근거 없는 수치, 분량(${d.len || '350~900'}행).
지시(outline): ${d.outline.slice(0, 3000)}
계약·ID·결정·필수 필드 관련은 major 또는 blocker, 문체·표현은 minor. 문제 없으면 findings 빈 배열 + accept.`
}
function reviewTechP(d) {
  return `당신은 기술 리뷰어다. 문서의 완전성·기술 정확성·문법·설계 품질을 적대적으로 검토한다. 문서를 수정하지 말고 결과만 반환한다.

문서: ${W(d.path)}
읽기: 문서 전체, 관련 07-tech-landscape 문서(라이브러리·모델 주장 근거), 바이블 지정 절 [${d.bible || hint(d.path)}](Grep으로 헤더 위치를 얻어 필요한 절만 Read).
지시(outline): ${d.outline}

검토 항목(각각 실제로 확인한 방법을 checked에 남긴다):
1. 완전성: outline의 각 항목이 실질적으로 다뤄졌는가(제목만 있고 내용이 없는 절, 장식적 산문, "추후 정의" 회피). 누락 항목마다 finding.
2. 기술 정확성: 라이브러리 API·옵션·버전·라이선스·모델 식별자 주장이 docs/07-tech-landscape 와 일치하는가; 근거 없는 벤치마크 수치; 존재하지 않는 API.
3. 문법: 문서의 모든 \`\`\`json 블록을 임시 파일로 저장해 node -e 로 실제 파싱한다(하나라도 실패하면 blocker). Mermaid 블록의 문법(다이어그램 타입 선언, 노드 ID에 공백·한글 직접 사용 여부, 화살표, 따옴표 짝, subgraph end, stateDiagram-v2 전이 문법, erDiagram 관계 문법, C4 문법). YAML 들여쓰기. Python 코드 블록의 명백한 오류(들여쓰기, 미정의 이름, Pydantic v2 문법 — validator는 field_validator/model_validator).
${d.path.startsWith('03-contracts/') ? `4. 계약 정합: 예시 JSON 각각이 문서 스키마에 유효한가(필수 필드 전부 존재, 열거값 철자, 타입, ULID 26자·hex64 패턴, date-time 형식) — 필드 하나씩 대조; 스키마 $ref 가 실제 존재하는 $defs 또는 urn:rag:schema:common-types:1#/$defs/<Type> 을 가리키는가; 문서 내 스키마 블록과 schemas/ 파일이 동일한가(diff); Pydantic 모델의 필드·타입·기본값이 스키마와 일치하는가; additionalProperties 정책 명시; $id 형식 urn:rag:schema:<kebab>:1.` : '4. 예시·표·다이어그램이 본문 서술과 일치하는가(예: 표의 단계 순서와 다이어그램 순서).'}
5. 설계 품질: 스테이지 경계·실패 모드·멱등성·관측성·보안(tenant_id/ACL 강제)이 명확한가; 문서 내부 모순; 한국어 문서(HWPX/공문서) 특성이 반영되었는가; 우아함(단일 책임·중복 없는 정의).
6. 분량과 밀도: ${d.len || '350~900'}행 범위, 표·코드·다이어그램 대비 산문 비율이 적절한가.
문법 오류·예시-스키마 불일치·기술적 허위는 blocker/major, 표현은 minor. 문제 없으면 findings 빈 배열 + accept.`
}
function fixP(d, findings, extraReads, round) {
  return `당신은 문서의 최종 편집자다. 리뷰 결과를 반영해 문서를 수정한다(${round === 2 ? '2차 — 검증에서 미해결로 남은 항목만' : '1차'}).

파일: ${W(d.path)}
리뷰 결과(lens: anchor=앵커 준수, tech=기술):
${JSON.stringify(findings, null, 1).slice(0, 24000)}

규칙: blocker/major는 모두 수정하고 minor는 합리적인 것만 반영한다. 리뷰어의 "정본" 주장도 바이블 해당 절을 직접 읽어 확인한 뒤 반영한다 — 리뷰어가 앵커와 다르게 주장하면 앵커(브리프 > 바이블 > ADR)가 우선한다. 부속 파일(schemas/*.schema.json 등)도 함께 고쳐 문서 내 스키마 블록·저장 파일·Pydantic·예시가 모두 일치하게 한다. 전체 재작성은 verdict가 rewrite였을 때만; 그 외에는 Edit로 국소 수정한다. 수정 후 문서 전체 일관성을 확인하고 frontmatter status를 "active", last_updated를 ${DATE} 로 한다. JSON 블록·스키마 파일은 node -e 로 다시 파싱 검증한다. 저장 후 구조화 결과를 반환한다(summary에 무엇을 바꿨는지, open_issues에 반영하지 않은 리뷰 항목과 이유).
${conv(d, extraReads)}`
}
function verifyP(d, serious) {
  return `당신은 수정 검증자다. 아래 심각(blocker/major) 이슈들이 문서 ${W(d.path)}(및 부속 파일)에서 **실제로** 해결되었는지 파일을 읽어 하나씩 확인한다. 각 이슈를 resolved(간단한 근거 포함 문자열) 또는 unresolved(왜 아직 문제인지)로 분류한다. 또한 수정 과정에서 새로 생긴 문제(앵커 위반·문법 오류·문서 내부 모순·깨진 링크)를 new_issues에 적는다. 바이블 지정 절 [${d.bible || hint(d.path)}] 을 Grep/Read로 대조한다. JSON 블록은 node -e 로 파싱 확인한다. 문서를 수정하지 않는다. unresolved와 new_issues 중 blocker/major가 하나라도 있으면 verdict=fail.

이슈 목록:
${JSON.stringify(serious, null, 1).slice(0, 20000)}`
}

// ---------------------------------------------------------------- per-doc pipeline: write → (anchor ∥ tech review) → fix → verify → fix2
async function processDoc(d, extraReads, ph) {
  const w = await agent(writeP(d, extraReads), { label: `write:${d.path}`, phase: ph, schema: DONE })
  if (!w) { log(`${d.path}: 작성 실패(드롭) — 재개 시 재실행됨`); return null }
  const [ra, rb] = await parallel([
    () => agent(reviewAnchorP(d), { label: `review-anchor:${d.path}`, phase: ph, schema: REVIEW }),
    () => agent(reviewTechP(d), { label: `review-tech:${d.path}`, phase: ph, schema: REVIEW }),
  ])
  const findings = [
    ...((ra && ra.findings) || []).map((f) => ({ ...f, lens: 'anchor' })),
    ...((rb && rb.findings) || []).map((f) => ({ ...f, lens: 'tech' })),
  ]
  const verdicts = [ra && ra.verdict, rb && rb.verdict].filter(Boolean)
  if (verdicts.includes('rewrite')) findings.unshift({ severity: 'blocker', location: '(전체)', problem: '리뷰어 verdict=rewrite', fix: '문서를 지시와 앵커에 맞게 다시 작성', lens: verdicts.indexOf('rewrite') === 0 ? 'anchor' : 'tech' })
  const serious = findings.filter((f) => f.severity !== 'minor')
  if (!findings.length) { log(`${d.path}: 리뷰 통과(이슈 0)`); return { ...w, review: 'pass', serious: 0 } }
  log(`${d.path}: 리뷰 이슈 ${findings.length}개(심각 ${serious.length}; anchor ${(ra && ra.findings.length) || 0}, tech ${(rb && rb.findings.length) || 0}) → 수정`)
  const fx = await agent(fixP(d, findings, extraReads, 1), { label: `fix:${d.path}`, phase: ph, schema: DONE })
  if (!fx) { log(`${d.path}: 수정 에이전트 실패`); return { ...w, review: 'fix_failed', serious: serious.length } }
  if (!serious.length) return { ...fx, review: 'minor_fixed', serious: 0 }
  const v = await agent(verifyP(d, serious), { label: `verify:${d.path}`, phase: ph, schema: VERIFY })
  if (!v) return { ...fx, review: 'verify_failed', serious: serious.length }
  if (v.verdict === 'pass') { log(`${d.path}: 검증 통과(해결 ${v.resolved.length})`); return { ...fx, review: 'verified', serious: serious.length } }
  const round2 = [...v.unresolved.map((f) => ({ ...f, lens: 'verify:unresolved' })), ...v.new_issues.map((f) => ({ ...f, lens: 'verify:new' }))]
  log(`${d.path}: 검증 실패(미해결 ${v.unresolved.length}, 신규 ${v.new_issues.length}) → 2차 수정`)
  const fx2 = await agent(fixP(d, round2, extraReads, 2), { label: `fix2:${d.path}`, phase: ph, schema: DONE })
  return { ...(fx2 || fx), review: fx2 ? 'fixed_twice' : 'fix2_failed', serious: serious.length, residual: round2.length }
}
async function produce(docs, extraReads, ph) {
  const out = await parallel(docs.map((d) => () => processDoc(d, extraReads, ph)))
  const dropped = docs.filter((d, i) => !out[i]).map((d) => d.path)
  if (dropped.length) log(`${ph}: 드롭된 문서 ${dropped.length}개 — ${dropped.join(', ')}`)
  return { out, dropped }
}
function summarize(res, docs) {
  return { done: res.out.filter(Boolean).map((r) => ({ file: r.file, review: r.review, serious: r.serious, lines: r.lines })), dropped: res.dropped,
    openIssues: res.out.filter(Boolean).flatMap((r) => (r.open_issues || []).map((o) => (r.file || '').split(/[\\/]/).pop() + ': ' + o)) }
}

// ---------------------------------------------------------------- Wave A: contracts (bible §5 is canonical; outlines only add semantics/topics)
const CC = `
계약 문서 공통 요구:
(a) 정본: 필드 표는 바이블 §5의 해당 타입 표(필드·타입·필수·의미)를 **모두** 포함하고 같은 철자·같은 필수 여부를 쓴다. 봉투 필드는 §5.2, 공용 타입은 §5.3, 열거는 §5.7의 타입명·값 철자, ID·해시 결합식은 §6.1~6.2, 인라인/산출물 한계는 §5.1 마지막 열, 생산/소비 스테이지는 §5.1·§4. 바이블에 없는 필드는 선택(N)으로만 추가하고 "## 미해결 이슈"에 바이블 반영 제안으로 기록한다.
(b) 필드 표(필드|타입|필수|설명|예시) — 중첩 객체는 별도 표. 타입 표기는 브리프 §9.5(JSON Schema 용어).
(c) JSON Schema 2020-12 전문을 "## 스키마" 절 코드 블록으로 포함하고 **동일 내용**을 schemas/<kebab-name>.schema.json 파일로 저장한다: "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:rag:schema:<kebab-name>:1", "title": "<TypeName>", "description". 공용 타입(§5.3 및 Block·NormalizedBlock·Chunk·Enrichment·VectorBundle·RankedResult·ContextItem)은 {"$ref": "urn:rag:schema:common-types:1#/$defs/<TypeName>"} 로 참조하고 재정의하지 않는다. 열거 필드는 {"$ref": "urn:rag:schema:common-types:1#/$defs/<EnumTypeName>"} 로 참조한다(common-types가 §5.7 전체 열거를 $defs로 보유). 계약 전용 하위 타입은 자기 $defs. additionalProperties는 명시(기본 false; extensions/custom/metadata 같은 열린 객체만 true 또는 스키마). format(date-time, uri, uuid, duration), pattern(ULID "^[0-9A-HJKMNP-TV-Z]{26}$", hex64 "^[0-9a-f]{64}$", hex32 "^[0-9a-f]{32}$", semver). nullable은 "type": ["string", "null"].
(d) Pydantic v2 모델 코드 블록(Field(description=...), field_validator/model_validator로 불변식, ConfigDict(extra='forbid')).
(e) 완전한 JSON 예시 최소 2개(한국어 공문서 시나리오 1개 포함; 공공기관 HWPX 문서 등), 스키마와 **정확히** 일치(필수 필드 전부, 열거값 철자, 패턴). ID는 형식 규약을 지키는 플레이스홀더(ULID 26자 Crockford 대문자, hex64 소문자). 봉투를 갖는 타입의 예시는 schema_type·schema_version을 포함한다. 예시에 주석·생략 부호(…, ...) 금지.
(f) "## 불변식(Invariants)": 바이블 표 아래 불변식 전부 + 이 문서가 추가한 것. 위반 시 오류 코드는 §5.7 카탈로그의 {stage}.{reason} 철자(contract.violation 등)로 쓰고 13-error-model 링크.
(g) 크기 한계·대형 데이터 처리(§5.1 한계; 본문은 ArtifactRef 참조, 인라인 금지 규칙).
(h) 산출물 저장 규약(§13.3 오브젝트 키, content hash, zstd, 미디어 타입 application/vnd.rag.<kebab>+json).
(i) "## 버전 이력": 1.0.0(${DATE}) 초판 + 호환성 규칙(14-schema-versioning 링크).
(j) LLM 최종 소비에 영향을 주는 정보(provenance·인용 가능성·3-텍스트 규칙·보안 삼중항) 명시.
(k) 저장한 스키마 파일과 문서 내 모든 JSON 예시를 node -e "JSON.parse(...)" 로 파싱 검증하고, 예시의 필수 필드·열거값을 스키마와 손으로 대조한다.`

const CONTRACTS_T0 = [
  { path: '03-contracts/00-contract-overview.md', title: '계약 개요와 공통 규약', len: '700~1300', deps: ['02-architecture/00-design-bible.md'],
    bible: '§5.1(인벤토리 전체), §5.2(봉투 전체), §5.3(공용 타입 전체), §5.4의 Block·NormalizedBlock·Chunk·Enrichment·VectorBundle 표, §5.5의 RankedResult·ContextItem 표, §5.7(열거 전체·이벤트·오류 코드), §6(명명·해시 결합 전체), §13.3(오브젝트 키), §1.2(변경 절차·CI 게이트), §2.1 K1~K7',
    outline: `모든 계약의 공통 규약이자 공용 스키마의 소유 문서. 내용: 계약 철학(Contracts First, 순수 스테이지, 단일 좌표계·점수 원장 ADR-0030, 3-텍스트 규칙 ADR-0029); 계약 인벤토리 표(바이블 §5.1 전체 행 + "소유 문서" 열: 01~16 중 어느 03-contracts 문서가 정의하는지 — RenderedContext→11, JobStatus·CloudEventEnvelope→12, StageError·ProblemDetails→13, CollectionSpec·Profile·PluginMeta·Capabilities·IndexBackendCapabilities·StagePolicy·TieringPolicy·EgressPolicy→15, EvalDataset·EvalRun·EvalReport·FeedbackEvent·UserDictEntry·ConvertRequest·ConvertResponse→16, 공용 타입·열거→00); 공통 봉투(§5.2 표 전체와 lineage_refs 전파 규칙); 공용 타입(§5.3 표 전체 — ArtifactRef, Producer, Provenance, Acl, SecurityContext, Principal, TokenCounts, Warning, DegradedEntry, StageError, ProblemDetails, CloudEventEnvelope, ChannelScore, ScoreBreakdown, FilterNode, Entity, Relation, BlockRef, Capabilities, IndexBackendCapabilities, StagePolicy, TieringPolicy, EgressPolicy) 각각 필드 표; 명명 규약 요약(§6.1 ID 표, §6.3 시간·언어·오프셋, §6.4 필드·열거·스키마, ADR-0036 링크); 해시 결합 규칙 H()와 canonical_json 정의 및 §6.2 표 전체 인용; null/미지정 규칙(nullable vs 생략), 확장 필드 정책(custom/extensions), 직렬화(JSON UTF-8, 대량은 ArtifactRef), 산출물 키 규약(§13.3), 계약 검증 시점(스테이지 셸에서 입출력 강제 → contract.violation), 계약 테스트(골든 예시 회귀, CI 열거 대조 §1.2), 미디어 타입.
**부속 파일(이 문서만 소유)**: schemas/common-types.schema.json — "$id": "urn:rag:schema:common-types:1", $defs에 (1) §5.3 공용 타입 전부 (2) §5.4·§5.5의 Block, NormalizedBlock, Chunk, Enrichment, VectorBundle, RankedResult, ContextItem(해당 표 그대로; 표에 있는 필수/nullable 반영) (3) §5.7 열거 타입 전부를 타입명 그대로 $defs 키로 두고 enum 값 배열(ChunkLevel은 integer enum [0,1,2]; DegradedComponent는 §5.3 DegradedEntry 행의 목록을 enum으로 — "channel.*" 는 개별 채널 값으로 전개; FilterableField는 고정 값 enum + "custom.{key}"는 pattern "^custom\\\\.[a-z0-9_]+$" 을 anyOf로) (4) 원시 형식 $defs: Ulid, Hex64, Hex32, Semver, Bcp47, DateTime, Duration, Principal 문자열 패턴. 모든 object에 additionalProperties 명시. 문서 "## 스키마" 절에는 이 파일 전문을 넣지 말고(너무 크다) $defs 키 목록 표와 대표 $defs 3개(ArtifactRef, Provenance, FilterNode)만 코드 블록으로 보인다. 저장 후 node -e 로 파싱 검증하고 $defs 키 수를 결과 summary에 적는다.${CC}` },
  { path: '03-contracts/13-error-model.md', title: '에러 모델', len: '500~1000', deps: ['03-contracts/00-contract-overview.md'],
    bible: '§5.3 StageError·ProblemDetails 행, §5.7 "오류 코드 접두 규약과 카탈로그" 표 전체, §11.3(재시도 분류), §4.2~4.3 실패 정책 열, §5.7 PageStatus·Quality, §5.3 DegradedEntry, §14(HTTP 상태)',
    outline: `단일 에러 모델. StageError·ProblemDetails(RFC 9457) 필드 표(§5.3 그대로)와 스키마 2개(schemas/stage-error.schema.json, schemas/problem-details.schema.json). 오류 코드 카탈로그 표(코드 | HTTP | 재시도 | 스테이지 | 설명 | 복구 지침): 바이블 §5.7 카탈로그의 모든 코드를 같은 철자로 전부 수록하고, 필요한 추가 코드는 "제안" 표시로 별도 표에 둔다(코드 형식 {stage}.{reason}, type = urn:rag:error:{code}). 재시도 분류(§11.3: transient/permanent/poison, StagePolicy.non_retryable_error_codes와의 관계), 부분 실패 의미론(page_status, quality=degraded, warnings, DegradedEntry — 실패가 아닌 저하로 다루는 기준), 변환 규칙(StageError → JobStatus.last_error → API ProblemDetails; errors[] 다중 오류), HTTP 매핑 표, 로그·메트릭 라벨(code, outcome; tenant_id 라벨 금지 §6.5), 메시지 지역화 정책(코드 고정, message 한/영, detail에 콘텐츠 미포함), 클라이언트 처리 지침(retryable·Retry-After). 예시: ProblemDetails 3개(400 contract.violation with errors[], 403 auth.forbidden, 503 retrieve.unavailable + Retry-After), StageError 2개.${CC}` },
  { path: '03-contracts/14-schema-versioning-and-compatibility.md', title: '스키마 버전 관리와 호환성', len: '400~800', deps: ['03-contracts/00-contract-overview.md'],
    bible: '§1.2(변경 절차 표·CI 게이트), §6.4(schema_version·$id·미디어 타입), §5.1(schema_version 열), §5.3 ArtifactRef(schema_type/schema_version)·Capabilities(contracts_compat), §7(profile_hash·프로파일 version), §11.4(재색인), §14 /v1/schemas',
    outline: `schema_version(semver, 계약별 독립, 초기 1.0.0)과 $id urn:rag:schema:{kebab}:{major} 규칙, 호환성 규칙(minor: 선택 필드·열거값 추가 — 소비자는 unknown 열거값을 허용해야 하는 계약과 거부해야 하는 계약을 표로; major: 제거·의미 변경·필수화·개명), 변경 절차(§1.2 표 그대로: 오탈자 / 선택 필드 추가 / 파괴적 변경 / D-xx 개정 — ADR·게이트 근거·영향 문서), 생산자·소비자 호환 매트릭스(ArtifactRef.schema_type/schema_version으로 로드 시 판정, contracts_compat 범위), 스키마 레지스트리(schemas/ 디렉터리 + GET /v1/schemas/{name} 게시, dataschema), 저장 산출물 마이그레이션(업캐스팅 함수 체인, lazy 마이그레이션, 재처리 트리거: Producer.fingerprint 변경 → from_stage 결정 표 — 파서 major 변경 시 parse부터, 임베딩 모델 변경 시 embed부터, 프로파일 version 변경 → profile_hash → 컬렉션 blue/green 재색인), 폐기(deprecation) 정책과 기간(Deprecation/Sunset 헤더), 프로파일 버전과 계약 버전의 관계, 클라이언트 SDK 버전 정합, 자동 호환성 테스트(이전 버전 골든 예시가 새 스키마에 유효한지, JSON Schema diff 분류 규칙, CI 열거 대조 §1.2), unknown 필드 정책 표(계약별 additionalProperties). 이 문서는 스키마 파일을 만들지 않는다.${CC}` },
]
const CONTRACTS_T1 = [
  { path: '03-contracts/01-ingest-request.md', title: 'IngestRequest 계약', len: '450~900', deps: ['03-contracts/00-contract-overview.md', '03-contracts/13-error-model.md'],
    bible: '§5.4 IngestRequest 표, §14 POST /v1/ingest·/v1/ingest/batch 행, §11.2(디스패처·문서 직렬화), §11.5, §5.7 DedupPolicy·SplitHint·PiiPolicy·SourceFormat, §5.3 Acl·EgressPolicy, §10.3 E16, §3.1 D-08, §6.2 acl_hash·metadata_hash',
    outline: `R1의 직접 구현. IngestRequest 필드 표(§5.4 그대로; documents/metadata/acl/options 등 중첩은 별도 표), 202 응답 본문(job_id, status_url, events_url; 배치는 건별) 표, 멱등성(Idempotency-Key 필수 + request_id; 재전송 200/409 api.idempotency_conflict/422 api.idempotency_payload_mismatch, 키 스코프·TTL), dedup_policy·split_hint 의미, 예약 메타데이터 키 표와 정규화 규칙(doc_date, doc_type, department, tags, lang, genre 등 §5.7 FilterableField와 정합), ACL 입력 규칙(주체 문자열 §6.1, 거부 우선, 문서 단위), URI 스킴 허용목록과 EgressPolicy(E16, fetch.egress_denied), credentials_ref(비밀 값 직접 전달 금지), 검증 규칙과 한계(64KB 본문, metadata 16KB, 배치 100건), 문서 단위 잡 분할과 같은 document_id 직렬화(§11.2), 예시: 공공기관 HWPX 1건 + 배치(PDF 2건, 필터 메타 포함) + dry_run/reprocess 옵션 예시. 스키마 파일 schemas/ingest-request.schema.json.${CC}` },
  { path: '03-contracts/02-source-document.md', title: 'SourceDocument 계약', len: '400~800', deps: ['03-contracts/00-contract-overview.md', '03-contracts/01-ingest-request.md'],
    bible: '§5.4 SourceDocument 표, §4.2 fetch·detect 행, §5.7 SourceFormat·SourceKind, §5.3 ArtifactRef·Acl, §6.2 content_hash·doc_version·acl_hash·metadata_hash, §13.3(원본 오브젝트 키), §3.3 ADR-0005',
    outline: `fetch(+detect) 출력. 필드 표(§5.4 그대로), 문서 버전 규칙(doc_version = content_hash; ACL·메타데이터 변경은 새 버전이 아니라 payload 갱신 — ADR-0005), 포맷 판별 결과(SourceFormat, 신뢰도, 판별기)와 라우팅 힌트, 중복 감지(같은 content_hash 다른 URI/테넌트 — 산출물 파생물 derived 공유 규칙 §6.2 derived 키), 원본 저장(ArtifactRef, §13.3 키, 200MB 한계, 스트리밍 해시), fetch 진단(HTTP etag/last-modified, 리다이렉트, 크기), 암호화·배포용 문서 플래그와 오류(parse.document_encrypted, parse.distribution_document), 언어 힌트, 예시 2개(HWPX s3, PDF https).${CC}` },
  { path: '03-contracts/03-parsed-document.md', title: 'ParsedDocument 계약 (표준 문서 모델)', len: '700~1300', deps: ['03-contracts/00-contract-overview.md', '03-contracts/02-source-document.md'],
    bible: '§5.4 ParsedDocument·Block·TableData·TableCell 표(불변식 포함), §5.3 Provenance·BlockRef, §5.7 BlockType·BlockContainer·BlockSource·SourceKind·PageStatus·TableRole·Quality, §6.2 block_id, §6.3(오프셋·좌표), §3.1 D-04, §3.3 ADR-0002, §4.2 parse 행',
    outline: `가장 중요한 계약: 포맷 독립 표준 문서 모델. ParsedDocument 필드 표(§5.4 그대로), Block(공용 $ref)·TableData·TableCell·Provenance 표를 이 문서에서 상세 설명(필드 의미·예시), provenance 규칙(ADR-0002: element_path·char_start/char_end 필수, page/bbox nullable, 좌표계 §6.3), 블록 평면 배열 + parent/order/path로 트리 복원(알고리즘 의사코드), 읽기 순서 규칙, source_kind·page_status·quality 의미, 표의 이중 표현(TableData 구조 + serialization 문자열; 병합 셀 row_span/col_span; 헤더 행), 그림·캡션·각주 연결, 어댑터 매핑 표 3개(Docling 라벨 → BlockType, HWPX OWPML 요소 → BlockType, DOCX/HTML 요소 → BlockType; §5.7 BlockType 주석 반영), 대형 문서 분할·한계(256MB, 블록 200,000, 블록 텍스트 1MB), 불변식(트리 무결성, block_id 유일·결정성, provenance 필수, 표 셀 범위, 스캔 문서 bbox 필수), 예시: 한국어 공문서(제목·개조식 본문·표·각주) 완전 예시 1개 + 스캔 PDF 페이지 예시 1개. 스키마 schemas/parsed-document.schema.json.${CC}` },
  { path: '03-contracts/04-normalized-document.md', title: 'NormalizedDocument 계약', len: '450~900', deps: ['03-contracts/03-parsed-document.md'],
    bible: '§5.4 NormalizedDocument·NormalizedBlock 표, §4.2 normalize 행, §6.3(NFC/NFKC·offset_map), §5.7 FurnitureReason·Genre·PiiPolicy·PiiTokenizeMode·BlockSource, §6.2 normalizer_fingerprint·dictionary_hash, §3.3 ADR-0021·0029',
    outline: `normalize 출력. 필드 표(§5.4 그대로), 3-텍스트 규칙(ADR-0029: 표시 텍스트 NFC / 렉시컬 뷰 NFKC / 임베딩 텍스트는 enrich에서 — 각 텍스트의 필드와 오프셋 기준), offset_map(정규화 전후 코드포인트 사상; 인용 복원 알고리즘), furniture(머리말·꼬리말·반복 요소) 제거 기록과 furniture_reason, genre 감지와 chunk 라우팅 힌트, 언어 감지(문서·블록 lang), PII 정책 적용 기록(pii_policy_applied, 토큰화 모드), 사용자 사전(analyzer_id·dictionary_hash)이 정규화에 미치는 영향, 통계(chars, tokens), 불변식(블록 집합은 ParsedDocument 부분집합·순서 보존, offset_map 단조성), 예시 2개(공문서 정규화 전후 오프셋 매핑 포함). 스키마 schemas/normalized-document.schema.json.${CC}` },
  { path: '03-contracts/05-chunk-set.md', title: 'ChunkSet 계약', len: '550~1000', deps: ['03-contracts/04-normalized-document.md'],
    bible: '§5.4 ChunkSet·Chunk 표(불변식 5개), §4.2 chunk·recount 행, §7.2(청크 파라미터 정본), §5.7 ItemKind·ChunkLevel·TableSerialization·Genre, §6.2 chunk_id·chunker_config_hash·content_hash(청크), §5.3 BlockRef·TokenCounts, §3.2 O-09, §3.3 ADR-0004·0019·0020',
    outline: `chunk(+recount) 출력. 필드 표(§5.4 그대로), chunk_id 결정식(H("chunk", doc_version, chunker_config_hash, str(level), span), span 형식)과 재현성, level 0/1/2·item_kind 의미(부모는 임베딩하지 않음; level 2 파생 노드), block_refs·sentence_spans·table_ref·window 의미와 오프셋 기준(§6.3), heading_path, token_counts(recount 스테이지 ADR-0019, primary_tokenizer_id), 표 청크(table/table_part, serialization, 헤더 반복 행 그룹), 오버랩 표현, 부모/자식 불변식(§5.4 5개 그대로 + 추가), 한계(청크 50,000; 페이징), 예시 2개(공문서 leaf 2개 + parent 1개 관계를 보이는 ChunkSet). 스키마 schemas/chunk-set.schema.json.${CC}` },
  { path: '03-contracts/06-enriched-chunk-set.md', title: 'EnrichedChunkSet 계약', len: '450~900', deps: ['03-contracts/05-chunk-set.md'],
    bible: '§5.4 EnrichedChunkSet·Enrichment 표, §5.3 Entity·Relation, §4.2 enrich 행, §5.7 KeywordSource·EntityExtractor·EnrichStatus·PiiPolicy, §6.2 enricher_fingerprint·LLM 보강 캐시 키, §7.2 enrichment_budget_tokens, §3.2 O-05, §3.3 ADR-0016·0029',
    outline: `enrich 출력. 필드 표(§5.4 그대로; enrichments는 object<chunk_id, Enrichment>), 결정적 context_prefix 규칙(ADR-0029: 문서 제목·heading_path·doc_date 기반 템플릿, LLM 보강은 옵트인), index_text/embed_text 구성 규칙(3-텍스트: 무엇이 임베딩·BM25 입력으로 가고 text와 어떻게 분리 저장되는지, embed_text_hash), keywords(source별), entities/relations(그래프 플러그인 슬롯), hypothetical_questions·summary(옵션), PII 결과, status complete/partial과 enrich.budget_exceeded, LLM 보강의 캐시 키·비용 기록(cost), 어떤 필드가 IndexRecord payload로 나가는지 표(indexable), 불변식(context_prefix ⊄ text; enrichments 키 = chunk_id 집합), 예시 2개. 스키마 schemas/enriched-chunk-set.schema.json.${CC}` },
  { path: '03-contracts/07-embedded-chunk-set-and-index-record.md', title: 'EmbeddedChunkSet과 IndexRecord 계약', len: '650~1200', deps: ['03-contracts/06-enriched-chunk-set.md'],
    bible: '§5.4 EmbeddedChunkSet·VectorBundle·IndexRecord 표("원천" 열 포함), §4.2 embed·index 행, §5.7 VectorName·Pooling·EmbeddingMode·ItemKind·Visibility·Classification, §6.1~6.2 record_id·point_id·embedding_space_id·embedding_profile_hash, §13.4(Qdrant/OpenSearch 명명·payload 인덱스), §10.2(보안 필드·필터 불변식), §3.1 D-06·D-09·D-15, §3.3 ADR-0004·0012',
    outline: `embed 출력과 인덱스 백엔드 레코드. EmbeddedChunkSet·VectorBundle 필드 표(§5.4 그대로: 이름별 dense/sparse/multivector, dtype, 정규화, 대량은 ArtifactRef), embedding_space_id·embedding_profile_hash 결합식과 모델 변경 = 재색인 규칙, IndexRecord 필드 표(§5.4 그대로 + 원천 스테이지 열), record_id/point_id 스코프·세대 합성(ADR-0004 v1.2, E17; 왜 chunk_id를 물리 키로 쓰면 안 되는지), 보안 삼중항(tenant_id, acl_*, is_current/index_generation)과 index.security_fields_missing, 백엔드 매핑 표(Qdrant: named vectors(VectorName), payload 인덱스 필드·타입, 컬렉션 물리명 §13.4 / OpenSearch: 매핑·Nori 분석기 필드·_id=record_id), lite 프로파일 sparse_bm25(ADR-0012), payload 한계(32KB, text 8,192바이트)와 부모 텍스트 저장(ChunkTextStore §13.2), 불변식, 예시: EmbeddedChunkSet 1개(dense+sparse_learned) + IndexRecord 2개(leaf·parent). 스키마 2개 schemas/embedded-chunk-set.schema.json, schemas/index-record.schema.json.${CC}` },
  { path: '03-contracts/08-index-commit.md', title: 'IndexCommit 계약', len: '450~900', deps: ['03-contracts/07-embedded-chunk-set-and-index-record.md'],
    bible: '§5.4 IndexCommit 표, §11.4(세대 사가 전체), §11.5, §5.7 CommitStatus·CommitKind, §6.2 commit_hash, §13.1(index_commits·lineage 원장), §2.1 K6, §3.3 ADR-0026',
    outline: `index 출력·원장 행. 필드 표(§5.4 그대로), CommitStatus 9단 상태 기계(stateDiagram-v2; §11.4 순서: pending → vector_written → lexical_written → flipping_lexical → flipping_vector → committed; rolling_back/rolled_back/failed; 보상 규칙 플립 전/후), index_generation·is_current 플립과 세대 공존·롤백, commit_hash 식과 재현성, artifact_refs/lineage(재처리 판단 from_stage), CommitKind upsert/delete(tombstone), supersedes 관계, 재색인(reindex.collection.v1)·alias, 조회 API(GET /v1/documents/{id}/commits) 응답으로의 사용, 불변식(한 문서 버전당 current 커밋 ≤ 1 등), 예시 2개(committed, rolled_back with compensation). 스키마 schemas/index-commit.schema.json.${CC}` },
  { path: '03-contracts/09-query-request-and-query-plan.md', title: 'QueryRequest와 QueryPlan 계약', len: '650~1200', deps: ['03-contracts/00-contract-overview.md', '03-contracts/07-embedded-chunk-set-and-index-record.md'],
    bible: '§5.5 QueryRequest·QueryPlan 표, §5.3 FilterNode·SecurityContext·Principal, §10.2(필터 불변식·3층 필터), §8.1(플래너 1~6단계), §5.7 Route·Complexity·Strategy·QueryRole·FilterOp·FilterableField·Renderer·ResponseFormat·RetrievalVariant·RetrievalMode·OrderingStrategy·Channel·FusionMethod, §6.1 variant_id·channel_run_id·cite_id, §6.2 plan 캐시 키·security_context_hash·filters.effective_hash·planner_fingerprint, §14 POST /v1/query',
    outline: `리트리벌 API 입력과 질의 이해 결과. QueryRequest 필드 표(§5.5 그대로; filters는 FilterNode DSL, session_id/exclude_ids/cursor, renderer/response_format/retrieval_variant/mode/strategy_hint/ordering_strategy, budget), SecurityContext 서버 주입(readOnly, 클라이언트 입력 무시 — ADR-0027)과 Principal 도출, FilterNode DSL(논리 결합 깊이·절 한계, FilterOp, FilterableField 화이트리스트, custom.{key}, page 가상 필드 변환, 금지 필드 → plan.filter_field_forbidden), 필터 3층(security ∧ strategy ∧ user ∧ self_query — §10.2 불변식과 effective_hash), QueryPlan 필드 표(§5.5 그대로: route/complexity/strategy, rewritten_queries[].variant_id·role, channels[](k 산정), fusion, hydrate, rerank, postprocess.order, pack, budget 해석, degraded), 계획 캐시 키(§6.2), planner_fingerprint, explain 응답 포함 규칙, 백엔드 필터 변환 원칙(Qdrant Filter / OpenSearch bool — 상세는 04-pipelines), 불변식(security 필터 항상 존재·최전방, k ≥ top_k 등), 예시: 한국어 질의 QueryRequest 2개(단순, 필터+세션) + QueryPlan 1개 전문. 스키마 2개 schemas/query-request.schema.json, schemas/query-plan.schema.json.${CC}` },
  { path: '03-contracts/10-candidate-set-and-ranked-set.md', title: 'CandidateSet과 RankedSet 계약', len: '550~1000', deps: ['03-contracts/09-query-request-and-query-plan.md'],
    bible: '§5.5 CandidateSet·RankedSet·RankedResult 표(hydrate 조건 필수 포함), §5.3 ChannelScore·ScoreBreakdown·DegradedEntry, §8(검색 경로: 융합 공식·hydrate·후처리 순서), §5.7 Channel·ScoreKind·BoostKind·FusionMethod·ScoreNormalization·ChannelRunStatus·RankedStage·PostprocessStep·ExplainCode·OmitReason, §6.1 channel_run_id, §3.2 O-01, §3.3 ADR-0013·0030·0034',
    outline: `retrieve/fuse/hydrate/rerank/postprocess 경계. CandidateSet 필드 표(§5.5 그대로: 채널 런 단위, payload_slim, stats), RankedSet 필드 표(§5.5 그대로: stage, hydrated, results[], omitted[], postprocess_report, channel_runs, degraded), RankedResult·ChannelScore·ScoreBreakdown 상세(점수 원장 ADR-0030: 채널 원점수·순위·contribution, 불변식 Σ contribution = fused_score, rerank_raw/normalized, boosts), RRF 기여 공식(w/(k+rank), k=60, 변형 질의 0.5)과 타이브레이크(record_id 오름차순), hydrate 조건 필수 필드(§5.5 표), expanded_from/duplicates_of/window_chunk_ids·parent 항목(record_id null), omitted(OmitReason)·explain(ExplainCode) 규칙, PostprocessStep 고정 순서와 postprocess_report, 평가용 TREC run 변환 규칙, 한계(채널 런당 300, RankedSet 100), 예시: 3채널 × 5후보 융합 계산표 + CandidateSet 1개 + RankedSet(reranked, hydrated) 1개. 스키마 2개 schemas/candidate-set.schema.json, schemas/ranked-set.schema.json.${CC}` },
  { path: '03-contracts/11-context-pack.md', title: 'ContextPack 계약 (LLM 소비용 최종 출력)', len: '800~1400', deps: ['03-contracts/10-candidate-set-and-ranked-set.md', '07-tech-landscape/10-llm-context-optimization-and-mcp.md'],
    bible: '§5.5 ContextPack·ContextItem·RenderedContext 표, §9(패커 규칙·litm_alternating 공식·렌더러 규칙·프롬프트 캐싱·JSON 예시 전체), §8.2 pack 서브스텝, §5.7 OrderingStrategy·ConfidenceTier·CountMethod·OverflowPolicy·OmitReason·SufficiencyStatus·SufficiencyMethod·ConflictKind·TextFormat·CitationStyle·DataMarking·AclCheckSource·Renderer·PackStep·ExplainCode, §6.1 cite_id, §6.2 ContextPack.content_hash, §3.1 D-20, §3.3 ADR-0024, §14 POST /v1/render',
    outline: `R6의 직접 구현. ContextPack 필드 표(§5.5 그대로), ContextItem 상세(cite_id d{rank}, header, text/text_source/text_format, segments·sentence_spans, acl 재검사 소스, parent 정보, conflicts_with, token_counts), ordering(litm_alternating 정본 공식 §9.2 의사코드, relevance_desc, document_order), budget(count_method, overflow_policy, 안전 마진), sufficiency(status/method/coverage/confidence — partial 기각 근거 ADR-0024), omitted·diagnostics.pack_steps(acl_recheck → budget_cut → reorder → citation_align), instructions/render_hints(TextFormat/CitationStyle/DataMarking — 인젭션 완화: 검색 콘텐츠는 데이터임을 표시), RenderedContext 필드 표와 Renderer 9종 규칙(§9.3: anthropic_search_result 정본 블록 구조·citations, anthropic_document, openai_messages, gemini_messages, xml_documents, markdown, mcp_tool_result, plain_records, dify_external_knowledge; render.mixed_blocks·render.citations_with_structured_output 오류), citation_map 역매핑(공급자 인용 위치 → cite_id → chunk provenance → 원문 페이지/오프셋 알고리즘), 프롬프트 캐싱 규약(§9.4), content_hash 식, 크기 한계(512KB, 항목 20, 24,000 토큰 초안), 불변식(cite_id 연속 d1..dK, acl_checked 전부 true, Σ token ≤ budget). 예시: 한국어 공문서 청크 3개로 ContextPack 전문 1개 + 같은 팩의 RenderedContext(anthropic_search_result) 전문 1개 + markdown 렌더 1개(모델 식별자는 플레이스홀더 또는 claude-opus-5). 스키마 2개 schemas/context-pack.schema.json, schemas/rendered-context.schema.json.${CC}` },
  { path: '03-contracts/12-jobs-events-and-status.md', title: 'Job·Event·Status 계약', len: '550~1000', deps: ['03-contracts/00-contract-overview.md', '03-contracts/01-ingest-request.md', '03-contracts/08-index-commit.md'],
    bible: '§5.6 JobStatus 표, §5.3 CloudEventEnvelope·StageError·DegradedEntry, §11.5(잡 상태 기계와 API 매핑), §11.2(워크플로우·큐·디스패처), §5.7 JobKind·JobState + 이벤트 이름 카탈로그 전체, §6.5(이벤트 규약), §6.2(웹훅 서명), §14 jobs·events·subscriptions 행, §3.2 O-06, §3.3 ADR-0017·0038',
    outline: `JobStatus 필드 표(§5.6 그대로)와 JobKind/JobState 상태 기계(stateDiagram-v2; §11.5 허용 전이 표, partial 의미, cancelling, waiting_for 직렬화), progress·cost·timings 의미, CloudEventEnvelope 필드 표(§5.3 그대로; CloudEvents 1.0 속성, source=urn:rag:{component}, subject 형식, tenantid 확장, dataschema, data에 콘텍스트 본문 금지), 이벤트 카탈로그 표 전체(§5.7 수집·잡·인덱스·ACL·컬렉션·감사·피드백·평가 — 이벤트별 data 스키마 요약과 발생 시점), 아웃박스·릴레이(ADR-0017: at-least-once, 순서, event_id 멱등), 웹훅 전달(RAG-Signature HMAC 헤더 §6.2, 재시도 백오프, 재생 창), SSE(/v1/jobs/{id}/events, /v1/events; Last-Event-ID), 상태 조회 응답, 예시: JobStatus 2개(running with progress, failed with last_error) + CloudEvent 3개(ingest.document.indexed, job.state.changed, acl.document.updated). 스키마 2개 schemas/job-status.schema.json, schemas/cloud-event-envelope.schema.json.${CC}` },
  { path: '03-contracts/15-collection-profile-and-policy-contracts.md', title: '컬렉션·프로파일·정책 계약 (CollectionSpec·Profile·PluginMeta·Capabilities·StagePolicy·TieringPolicy·EgressPolicy)', len: '700~1300', deps: ['03-contracts/00-contract-overview.md', '03-contracts/07-embedded-chunk-set-and-index-record.md'],
    bible: '§5.6 CollectionSpec·PluginMeta·Profile 표, §5.3 Capabilities·IndexBackendCapabilities·StagePolicy·TieringPolicy·EgressPolicy 행, §7(프로파일 정본 전체: 7.1 컴포넌트 표, 7.2 파라미터, 7.3 YAML 스키마 개요, 7.4 검증 규칙), §4.4 StagePolicy 표, §5.7 ProfileTier·LicenseGrade·Linkage·IsolationMode·TenantIsolationTier·IndexPerTenantMode·ExtensionPoint, §6.2 profile_hash·embedding_profile_hash·config_hash, §10.3 E15·E16, §10.4, §14 collections·profiles 행, §3.3 ADR-0001·0028·0031·0032·0038',
    outline: `운영·설정 계약 7종을 한 문서에서 정의한다(각 타입마다 필드 표·스키마·Pydantic·예시·불변식 절을 갖는 소절). CollectionSpec(§5.6: 프로파일 해시 바인딩, embedding_space_ids, analyzer_id·dictionary_hash, tenant_isolation_tier, backends[], policies, filterable_fields, license_policy, stats), Profile(§5.6 최상위 키 + §7.3 YAML 개요: extends 단일 상속·깊은 병합 규칙 ADR-0031, tier, license_policy, runtime, ingest 스테이지별 {plugin, policy, config}, query, security, observability, eval, 게이트 값 형식 {value, gate}), PluginMeta(§5.6: plugin_id 형식, extension_point 14종, license/license_grade/territory, linkage, isolation_supported, contracts_compat, capabilities), Capabilities·IndexBackendCapabilities(§5.3), StagePolicy(§5.3·§4.4), TieringPolicy(§5.3, E15), EgressPolicy(§5.3, E16·ADR-0038 기본값). 프로파일 로딩 검증 규칙(§7.4 전부 — 라이선스 게이트, 능력 검증, parse.router 완전성 등)과 오류(profile.invalid, plugin.license_denied), profile_hash 계산과 컬렉션 blue/green, 4 프로파일(lite/standard/premium/korean-gov)의 차이 요약 표(전문 YAML은 09-operations/02에 위임). 스키마 7개: schemas/collection-spec.schema.json, profile.schema.json, plugin-meta.schema.json, capabilities.schema.json(IndexBackendCapabilities는 $defs), stage-policy.schema.json, tiering-policy.schema.json, egress-policy.schema.json. 예시: CollectionSpec 1개(korean-gov), Profile 1개(standard 축약이 아닌 유효한 완전 예시 — 필수 키 전부), PluginMeta 2개(parser.hwpx_python_hwpx, index_backend.qdrant), 나머지 각 1개.${CC}` },
  { path: '03-contracts/16-eval-feedback-and-sidecar-contracts.md', title: '평가·피드백·사용자 사전·사이드카 계약 (EvalDataset·EvalRun·EvalReport·FeedbackEvent·UserDictEntry·ConvertRequest·ConvertResponse)', len: '600~1100', deps: ['03-contracts/00-contract-overview.md', '03-contracts/13-error-model.md'],
    bible: '§5.6 EvalDataset·EvalRun·EvalReport·UserDictEntry·FeedbackEvent·ConvertRequest/ConvertResponse 표, §5.7 JudgmentLevel·LabelProvenance·EvalRunStatus·DictSource·FeedbackKind, §7.4(게이트 결과), §6.1 run_id(EvalRun 전용)·entry_id·feedback_id, §6.2 dictionary_hash·derived 키, §14 eval·feedback·dictionary·convert 행, §3.1 D-12, §3.3 ADR-0023·0033',
    outline: `운영 계약 7종을 소절별로 정의(각각 필드 표·스키마·Pydantic·예시·불변식). EvalDataset(qrels TREC + answer_spans JSONL ArtifactRef, judgment_level, label_provenance, license — ADR-0023), EvalRun(run_id 전용 명명, profile_hash, index_commit_ids 고정으로 재현성, status), EvalReport(metrics 키 규약 ndcg@10 등, comparison{baseline_run_id, deltas, p_values, correction: holm}, gate_result{passed, failed_gates[]} — §7.4 게이트 형식과 정합), FeedbackEvent(kind cited/rated/corrected, cite_ids → pack_id 역추적, PII 정책 후 저장), UserDictEntry(surface/pos/reading/synonyms/weight/source; 변경 → dictionary_hash → 렉시컬 재색인 제안 경로), ConvertRequest/ConvertResponse(사이드카 POST /v1/convert; 본문은 ArtifactRef만, credentials_ref, deadline_ms, warnings·error(StageError)·producer; output=null ⇒ error 필수; 격리 사다리 ADR-0033). 스키마 7개: schemas/eval-dataset.schema.json, eval-run.schema.json, eval-report.schema.json, feedback-event.schema.json, user-dict-entry.schema.json, convert-request.schema.json, convert-response.schema.json. 예시 각 1개 이상(한국어 사용자 사전 항목·HWP→HWPX 변환 요청/응답 포함).${CC}` },
]
