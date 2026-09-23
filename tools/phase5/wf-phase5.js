export const meta = {
  name: 'rag-phase5-finalize',
  description: 'Phase 5: root README (ko + en summary), CLAUDE.md for implementation sessions, one review pass and fix (Sonnet)',
  phases: [
    { title: 'Write', detail: 'README.md and CLAUDE.md' },
    { title: 'Review', detail: 'one reviewer for both, then fix' },
  ],
}
const ROOT = 'C:\\Workspaces\\rag-platform'
const D = ROOT + '\\docs\\'
const BRIEF = D + '00-vision\\00-design-brief.md'
const BIBLE = D + '02-architecture\\00-design-bible.md'
const DATE = (args && args.date) || '2026-09-23'
const OUT = { type: 'object', properties: { file: { type: 'string' }, summary: { type: 'string' }, lines: { type: 'integer' }, open_issues: { type: 'array', items: { type: 'string' } } }, required: ['file', 'summary', 'lines', 'open_issues'] }
const REVIEW = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, location: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['file', 'severity', 'location', 'problem', 'fix'] } }, verdict: { type: 'string', enum: ['accept', 'revise'] } }, required: ['findings', 'verdict'] }
const RULES = `## 규칙
- 사실은 문서에서 확인한 것만 쓴다(브리프 ${BRIEF}, 바이블 ${BIBLE} — Grep으로 헤더를 찾아 필요한 절만 Read, docs/README.md, docs/12-appendix/00-progress-report.md §3·§8, 02-phase4-5-plan.md, 05-phase6-implementation-kit-plan.md, 06-adr/README.md, 07-tech-landscape/00-summary-and-selection-matrix.md).
- 현재 상태를 과장하지 않는다: **설계 완료, 구현 전**. 코드·설치 절차·벤치마크 수치를 있는 것처럼 쓰지 않는다. 품질 목표는 "초안 목표"로 표기.
- 한국어 본문, 영문 식별자. 이모지·과장 금지. 링크는 실제 파일 경로만(존재 확인).
- 지정 파일만 쓴다.`

phase('Write')
const [readme, claude] = await parallel([
  () => agent(`당신은 오픈소스 프로젝트의 테크니컬 라이터다. 저장소 루트 ${ROOT}\\README.md 를 작성한다(현재 없음).
구성(한국어, 250~400행):
1. 제목·한 문장 정의(브리프 §1) + 상태 배지 문구("설계 완료 · 구현 전 · Apache-2.0")
2. 왜 이 플랫폼인가(브리프 §2 R1~R6 요약 표: 요구 → 설계 답)
3. 핵심 특징 6~8개(HWPX/HWP 1급, 표준 계약 13종 + JSON Schema 35, 3-way 하이브리드 + RRF + 리랭킹, Context Pack과 인용, MCP 서버, 멀티테넌시·ACL 사전 필터, 평가 하네스 내장, 플러그인 14 확장 지점)
4. 아키텍처 한 장(바이블 §2.2 C4 Container를 요약한 Mermaid flowchart 1개 + 컨테이너 표 6~8행)
5. 검색 경로(바이블 §8.1 단계 목록과 §8.3 지연 예산 표 요약 — "초안 목표")
6. 프로파일 4종 표(바이블 §7.1: lite / standard / premium / korean-gov — 임베딩·인덱스·리랭커·오케스트레이션 열)
7. 기술 선정 요약 표(선정 매트릭스 00의 주요 역할 12개: 파서·OCR·임베딩·리랭커·벡터·렉시컬·오케스트레이션·KV·오브젝트 스토리지·평가·관측·MCP — 라이선스 포함)
8. 문서 지도(docs/README.md 링크 + 읽기 순서 6줄)
9. 현재 상태와 로드맵(3단계 완료 실측: 문서 151·99k행·스키마 35·ADR 38·openapi 51연산; 4·5단계 진행; 6단계 구현 킷·M1 lite 계획 링크; M1~M5 마일스톤 한 줄씩)
10. 기여·라이선스(Apache-2.0, CONTRIBUTING 예정, 보안 보고 채널 예정)
11. "## English Summary" 절(200~300단어: what it is, key design ideas, status, how to read the docs)
${RULES}`, { label: 'write:README.md', phase: 'Write', schema: OUT, model: 'sonnet' }),
  () => agent(`당신은 이 저장소에서 앞으로 코드를 구현할 Claude Code 세션을 위한 프로젝트 지침 ${ROOT}\\CLAUDE.md 를 작성한다(현재 없음). 이 파일은 모든 구현 세션의 시스템 컨텍스트로 자동 주입되므로 **짧고 명령형**이어야 한다(150~260행).
구성:
1. 프로젝트 한 줄 + 현재 상태(설계 완료·구현 전) + 앵커 우선순위(브리프 > 바이블 > ADR > 개별 문서) + "바이블은 절 단위로 Grep 후 Read, 통째로 읽지 말 것"
2. 무엇을 먼저 읽나(작업 유형별 3~5개 문서 경로 표: 계약 작업 / 파이프라인 스테이지 / API / 인프라·배포 / 평가)
3. 절대 규칙: 계약은 schemas/가 정본이며 Pydantic은 생성물(수정 금지, 생성기 재실행); 열거값·필드명은 바이블 §5.7·§6 철자 그대로; D-01~D-20·ADR과 모순되는 코드 금지; 기각 기술 사용 금지 목록(PyMuPDF·pyhwp 기본·MinIO·Redis(Valkey 사용)·Infinity·SPLADE-v3·jina CC-BY-NC 모델); 보안 불변식(tenant_id·acl 사전 필터, 결과 캐시 금지, SecurityContext 서버 주입)
4. 툴체인·명령: Python 3.12/3.13, uv, ruff, mypy strict, import-linter 계층(contracts ← core ← stages ← workflows ← api); 검증 명령 node tools/validate-contracts.mjs --root <repo>, node tools/audit-docs.mjs; 스키마 변경 절차(바이블 §1.2)
5. 저장소 구조 요약(10-development/01 기준 트리 12줄)
6. 문서 규약 요약(브리프 §9: frontmatter·한국어·Mermaid·링크·"확인 필요" 표기)과 문서를 고칠 때의 규칙(version patch, last_updated, 미해결 이슈 절)
7. 작업 방식(비용 규율): 스크립트 우선, 에이전트는 문서 3~6개 묶음, 리뷰는 경량, 진행 기록은 docs/12-appendix/00-progress-report.md에, 토큰 집계는 node tools/usage-report.mjs
8. 6단계 구현 순서 요약(05-phase6 계획 6A~6G 한 줄씩)과 M1 lite 범위(무엇을 끄는지)
9. "확인 필요(as of 2026-09)" 표기를 만나면: 실측으로 닫고 문서를 갱신할 것
${RULES}`, { label: 'write:CLAUDE.md', phase: 'Write', schema: OUT, model: 'sonnet' }),
])
log(`작성: README ${readme ? readme.lines : '?'}행, CLAUDE.md ${claude ? claude.lines : '?'}행`)

phase('Review')
const rv = await agent(`두 파일 ${ROOT}\\README.md 와 ${ROOT}\\CLAUDE.md 를 검토한다. 확인: (1) 사실 대조 — 문서 수·스키마 수·프로파일 구성·기술 선정·라이선스가 브리프·바이블·선정 매트릭스·진행 보고서와 일치하는가(Grep으로 확인) (2) 과장·미구현을 구현된 것처럼 쓴 문장 (3) 링크 대상 파일 존재 (4) Mermaid 문법 (5) CLAUDE.md의 규칙이 바이블·브리프와 모순되지 않는가, 명령형이고 짧은가 (6) 영어 요약의 정확성. 수정하지 않고 findings 반환.
${RULES}`, { label: 'review:root-docs', phase: 'Review', schema: REVIEW, model: 'sonnet', effort: 'medium' })
let fx = null
if (rv && rv.findings.length) {
  fx = await agent(`리뷰 결과를 반영해 ${ROOT}\\README.md 와 ${ROOT}\\CLAUDE.md 를 수정한다(blocker/major 전부, minor는 합리적인 것). 리뷰: ${JSON.stringify(rv.findings, null, 1).slice(0, 16000)}
${RULES}`, { label: 'fix:root-docs', phase: 'Review', schema: OUT, model: 'sonnet' })
}
return { readme, claude, review: rv ? rv.findings.length : null, fixed: !!fx }
