---
title: "ADR-0039: 바이블 1.3.0 가산 개정 묶음(선택 필드·열거값·이벤트·JobKind·§14 엔드포인트·해시 키, AM-26~AM-44)"
status: accepted
date: 2026-09-23
deciders: architecture
owner: architecture
version: 1.0.0
last_updated: 2026-09-23
priority: P1
related: ["§1.2 minor", "FR-MGT-01"]
depends_on:
  - ../00-vision/00-design-brief.md
  - ../02-architecture/00-design-bible.md
  - ../12-appendix/07-bible-amendment-triage-decisions.md
  - ../03-contracts/14-schema-versioning-and-compatibility.md
---

# ADR-0039: 바이블 1.3.0 가산 개정 묶음

## 맥락과 문제

4단계 T1 트리아지(`12-appendix/07-bible-amendment-triage-decisions.md` §2)가 요청 200행 중 34행을 채택(minor)으로 판정했고, 그중 AM-26~AM-44(19개 개정 항목)는 바이블 §4.1·§5.1~§5.7·§6.2·§6.5·§11.2·§13.1·§14에 선택 필드·열거값·엔드포인트·해시 키를 가산했다(바이블 1.3.0). 바이블 §1.2 변경 절차 표는 "필드 추가(선택), 열거값 추가"를 ADR 필수 항목으로 두고 게이트 근거(§7.4)와 `## 계약 영향` 절을 요구한다. AM-26~AM-44는 모두 가산이며 기존 필드 제거·개명·필수화가 없어(D4-3: major 유발 요청은 1.3.0에서 보류) 19건을 개별 ADR로 쪼개지 않고 이 한 건으로 묶는다(바이블 §3.3 결정, A7 "ADR-0039 파일 없음" 해소). 계약 스키마가 이미 `schema_version` 1.0.0으로 게시된 뒤의 첫 번째 개정이므로, ADR 인덱스(README §1.4)가 소급 면제한 기존 38건과 달리 이 ADR은 `## 계약 영향` 절을 실제로 채운다.

## 결정 동인(decision drivers)

- **D4-3(4·5단계 계획 §2.3)**: 바이블 목표 버전은 1.3.0(minor). major를 유발하는 요청(필드 제거·의미 변경·필수화·개명)은 이번 개정에 넣지 않는다.
- **§1.2 변경 절차**: 선택 필드·열거값 추가는 ADR 필수이나 게이트(§7.4) 대상은 아니다 — 기본 파라미터 값을 바꾸지 않기 때문.
- **문서 오버헤드 대 변경 규모**: 19건 각각을 60~200행 ADR로 만들면 근거(가산·minor·게이트 없음)가 19번 반복된다. 근거가 같은 항목은 한 결정으로 묶는 편이 §1.5 "근거 없는 수치·중복" 금지에 맞는다.
- **하위 호환성(스키마 버전 관리 §2.1)**: 모든 항목이 선택(N) 필드·가산 열거값이라 기존 소비자를 깨지 않아야 한다.

## 고려한 대안

1. **19건 개별 ADR(기각)** — 형식 오버헤드가 변경 규모 대비 과도하고, 근거 문단이 반복된다.
2. **계약 문서군별 ADR(예: 03-contracts용 1건, 05-api용 1건 등, 기각)** — 여전히 여러 ADR이 필요하고 트리아지 항목(AM-nn) 하나가 여러 계약에 걸쳐 있어(예: AM-35 공용 타입 승격은 03-contracts 8개 문서에 영향) 경계가 인위적이다.
3. **단일 가산 묶음 ADR(채택)** — 바이블 §3.3이 지정한 방식. 19건 모두 근거(가산·minor·게이트 근거 없음)가 동일하므로 한 결정문으로 충분하고, `## 계약 영향` 절의 7항목을 한 번만 채우면 된다.
4. **보류 14건(AM-45 등) 동반 개정(기각, D4-3)** — 의미 변경·개명·제약 강화가 섞인 요청을 이번 가산 묶음에 포함하는 안. 1.3.0 minor 목표와 맞지 않아 기각하고 O-11·O-12로 번호만 배정해 ADR-0039 이후로 이관했다(트리아지 결정 §5.2 AM-45).

## 결정

**결정:** 바이블 1.3.0이 확정한 가산 개정 AM-26~AM-44(트리아지 결정 §2)를 이 ADR 한 건으로 기록한다. 게이트 근거는 **해당 없음**(§7.4) — 선택 필드·열거값·엔드포인트 추가만이고 프로파일 기본 파라미터 값(`profile_hash`에 영향을 주는 값)은 바뀌지 않는다.

| AM | 바이블 절 | 요지 |
|----|-----------|------|
| AM-26 | §4.1 경계 페이로드 | `requires_lineage` 사용 범위: `index`(기존) + `chunk`(`ParsedDocument` 구조 필드, M1 필수) + `enrich` LLM 서브스텝(`ChunkSet`) |
| AM-27 | §4.1 스테이지 시그니처 | `StageContext` 선택 멤버 `plan`·`artifacts`(파생물 쓰기 포트) |
| AM-28 | §5.3 `StageError`·`ProblemDetails` | 선택 필드 `message`·`occurred_at`·`attempt`·`location`·`cause`·`retry_after`·`request_id`, `ProblemDetails.instance` 타입 명시(RFC 9457 §3.1.5) |
| AM-29 | §5.3 `Provenance`·`BlockRef` | `section_index` 의미 확장: HWPX `secPr`, OOXML `w:sectPr` |
| AM-30 | §5.3 `EgressPolicy` | 선택 필드 `max_bytes`·`connect_timeout_ms`·`allowed_ports`·`strip_query_keys` |
| AM-31 | §5.4 `NormalizedDocument` | `table_cell_views`·`genre_source`·`pii_report.tokenize_mode_applied`·`stats`·`pii_spans[].row/col` 등재 |
| AM-32 | §5.4 `EnrichedChunkSet.budget_used` | 선택 키 `charged_tokens` |
| AM-33 | §5.5 `RankedResult` | 선택 필드 `token_count_primary`·`ordinal`·`text_truncated`·`pii_policy_applied`(hydrate 시 채움) |
| AM-34 | §5.6 `EvalDataset`·게이트·`Profile` | 선택 필드 `relevance_max`·`topics_ref`·`language`; 게이트 선택 키; `Profile.profile_hash`(readOnly) |
| AM-35 | §5.1 공용 타입 | common-types 승격 11종(`SecurityFilter` 등), 사본·교차 `$ref` 전환 |
| AM-36 | §5.7 오류 코드 카탈로그 | 오류·경고 16종 추가(68→84종) |
| AM-37 | §5.7 `JobKind`, §11.2, §13.1 | `JobKind.delete_collection`, `collection.delete.v1`, `collections.deleted_at` |
| AM-38 | §5.7 이벤트·열거 | `tenant.policies.changed`(24→25종), `TenantStatus` |
| AM-39 | §14, §13.1, §6.7 | `/v1/tenants` 계열·API 키·플러그인·스키마 목록·버전·정합성 검사·감사 이벤트·프로파일 게시·unmask 엔드포인트, `tenants.status/quotas/disabled_at` |
| AM-40 | §6.2 | 캐시·해시 키 보강: `derived.options_hash`, `plan` 캐시 `opts` 해시, `query_hash`·`principal_hash` |
| AM-41 | §6.5 | 정본 메트릭 36종·스팬 2종(라벨 규약 불변) |
| AM-42 | §7.1 TXT·MD·JSON, §12 | 하위 경로 라이브러리 병기(`clevercsv`·`orjson`/`ijson`·`lxml`·`mdit_py_plugins`) |
| AM-43 | §7.3 `ingest.normalize.pii` | 선택 키 `reject_entities`(`korean-gov` 주민등록번호 reject) |
| AM-44 | §13.1 `idempotency_keys`·`jobs` | 배치 멱등 `idempotency_keys.job_ids`, 배치 자식 잡 `jobs.idempotency_key` NULL 허용 |

## 계약 영향

바이블 §1.2 minor 변경이므로 스키마 버전 관리(`03-contracts/14`) §3.3의 7항목을 적는다.

1. **바뀌는 스키마 파일과 `declared_level`**: `common-types`, `stage-error`·`problem-details`, `parsed-document`, `egress-policy`, `normalized-document`, `enriched-chunk-set`, `ranked-set`, `eval-dataset`·`eval-run`·`eval-report`, `profile`, `job-status`, `cloud-event-envelope`, `ingest-request`, `schema-diff-report`(신규) — 전부 `declared_level: minor`(선택 필드·가산 열거값만, `additionalProperties` 위반 없음).
2. **`SchemaDiffReport` 요약**: 필드 제거·개명·필수화 0건, 선택 필드 추가 다수, 열거값 추가 다수(오류 코드 16·이벤트 1), 신규 계약 1종(`SchemaDiffReport` 자신, 인벤토리 34→35종) — 전부 `additive`, 하위 호환.
3. **생산·소비 스테이지**: 바이블 §4.2·§4.3 표 그대로(스테이지 이름 변경 없음). AM-26·AM-27은 `chunk`·`enrich`·`index` 셸의 로딩 방식만 바꾼다(계약 스키마 자체는 불변, 봉투 `lineage_refs` 사용).
4. **저장 산출물 영향**: 신규 컬럼(AM-39 `tenants.status/quotas/disabled_at`, AM-37 `collections.deleted_at`, AM-44 `idempotency_keys.job_ids`)은 추가 전용(마이그레이션은 `ALTER TABLE ADD COLUMN`, 기존 행은 기본값/NULL). 재처리 트리거 없음.
5. **외부 소비자 영향(SDK·웹훅·MCP)**: 신규 엔드포인트(AM-39)는 클라이언트 SDK 부가 기능이며 기존 메서드 시그니처를 바꾸지 않는다. 웹훅 페이로드는 이벤트 열거값 1종 추가(`tenant.policies.changed`)로 하위 호환. MCP `structuredContent`는 선택 필드가 늘어나도 슬림 팩 상한(20k 토큰)은 불변.
6. **`profile_hash` 영향**: 없음 — 프로파일 기본 파라미터 값 변경이 없으므로 기존 `profile_hash`는 재계산되지 않는다(blue/green 불필요).
7. **폐기 일정**: 해당 없음 — 가산 항목이라 폐기 대상 필드·엔드포인트가 없다.

## 결과

- 긍정: 계약 인벤토리 35종(`SchemaDiffReport` 추가), 오류·경고 코드 84종, 이벤트 카탈로그 25종으로 바이블·하류 문서 인용이 갱신된다(전파는 `12-appendix/08-propagation-directives.md` §1 카탈로그 개수 인용 항목).
- 긍정: `FR-MGT-01`(테넌트 관리 API)이 AM-39로 바이블·`openapi.yaml`에 등재되어 3단계 완전성 검토 누락 항목이 해소된다.
- 중립: O-11(프로파일 해시만 바뀐 재색인)·O-12(blue/green 채움 중 원장 기준)는 이 묶음에 포함하지 않고 `open`으로 남긴다(AM-21). 해결은 이 ADR 이후 ADR(0040+)의 ADR-0026 개정으로 넘긴다(AM-45).
- 부정: 없음(순수 가산이며 기존 계약 소비자의 파싱 로직 변경이 불필요).
- 하류 문서 편집(03-contracts·04-pipelines·05-api·09-operations 등 각 문서에 필드·엔드포인트 서술 반영)은 전파 지시서(`12-appendix/08-propagation-directives.md` §2)가 문서별로 담당하며, 이 ADR은 근거만 고정한다.

## 준수 확인 방법

- 계약·스키마 파일을 건드리는 하류 편집마다 `node tools/validate-contracts.mjs --root <repo>` ERROR 0(기계 강제).
- 문서 검증기: 링크·frontmatter 필수 항목·행 수(§1.5).
- `## 결정` 표의 AM 번호가 트리아지 결정(`12-appendix/07-bible-amendment-triage-decisions.md`) §2 표와 일치하는지 코드 리뷰 체크리스트에 추가.
- ADR 번호·slug·우선순위가 바이블 §3.3과 이 인덱스(README §3)에 글자 단위로 일치.

## 재검토 조건

- O-11·O-12를 해결하는 ADR(다음 번호 0040+)이 채택되면 이 ADR의 "결과" 절에 상호 참조를 추가한다(`version` minor, `date` 유지).
- 09-operations/08·10-development/08이 제안한 릴리스 버전 정책 ADR이 0040으로 발의되면(README §6 결정) 그 ADR의 `related`에 이 ADR 번호를 적어 순번 경위를 남긴다.
- AM-45(보류 14건)가 근거를 확보해 재발의되면 새 ADR로 다루고 이 ADR은 개정하지 않는다(보류 항목은 이 ADR의 채택 범위 밖).

## 참조

- [설계 바이블](../02-architecture/00-design-bible.md) — §1.2 변경 절차, §3.2 O-11·O-12, §3.3 ADR 목록(정본), §4.1 경계 페이로드, §5.1~§5.7 계약 인벤토리·공용 타입·열거 정본, §6.2 해시 결합, §6.5 메트릭·스팬, §11.2 워크플로우, §13.1 테이블, §14 관리 API
- [바이블 개정 요청 트리아지 결정](../12-appendix/07-bible-amendment-triage-decisions.md) — §2 AM-26~AM-44, §5.2 AM-45(보류)
- [스키마 버전 관리와 호환성](../03-contracts/14-schema-versioning-and-compatibility.md) — §2.1 변경 분류, §3.3 ADR "계약 영향" 절 필수 항목
- [4·5단계 계획](../12-appendix/02-phase4-5-plan.md) — D4-3(major 유발 요청 보류)
- [ADR 인덱스](README.md) — §1.4 절 구성, §6 새 ADR 절차(다음 번호 0040)
- [ADR-0013](0013-fusion-rrf-k60-then-convex-combination-and-postprocess-order.md), [ADR-0026](0026-index-commit-generation-saga-and-ledger.md) — O-11·O-12가 개정 대상으로 삼는 결정
