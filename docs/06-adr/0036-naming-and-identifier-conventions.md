---
title: "ADR-0036: 명명·식별자·열거 타입명·이벤트·메트릭 규약"
status: accepted
date: 2026-09-22
deciders: architecture
owner: architecture
version: 0.1.0
last_updated: 2026-09-23
priority: P2
related: ["D-03", "D-06"]
depends_on:
  - ../00-vision/00-design-brief.md
  - ../02-architecture/00-design-bible.md
  - ../07-tech-landscape/00-summary-and-selection-matrix.md
  - ../07-tech-landscape/06-vector-and-lexical-index-backends.md
  - ../07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md
  - ../07-tech-landscape/09-evaluation-and-observability.md
  - ../07-tech-landscape/10-llm-context-optimization-and-mcp.md
  - ../07-tech-landscape/12-security-multitenancy-pii-and-licensing.md
  - ../07-tech-landscape/13-korean-nlp-tokenization-and-language-resources.md
  - ../12-appendix/design-proposals/proposal-A-operability-first.md
  - ../12-appendix/design-proposals/proposal-B-retrieval-quality-first.md
  - ../12-appendix/design-proposals/proposal-C-simplicity-and-extensibility-first.md
  - ../03-contracts/00-contract-overview.md
  - ./0004-deterministic-chunk-id-scoped-record-id-and-ulid-exception.md
  - ./0022-observability-genai-semconv-pin-and-license-boundary.md
---

# ADR-0036: 명명·식별자·열거 타입명·이벤트·메트릭 규약

> MADR(Markdown Architectural Decision Record) 형식. 바이블 §3.3 표의 0036행(slug `naming-and-identifier-conventions`, P2)이며 관련 결정은 브리프 확정 결정 D-03(바이블 §3.1 `confirmed`, "§6 명명 규약으로 정밀화")과 D-06(브리프 §4 개정 v1.2, 바이블 §3.1 `amended`)이다. 이 ADR은 바이블 §5.7·§6·§13.3·§13.4의 명명 결정을 근거·대안과 함께 기록하고 바이블 표를 바꾸지 않는다(바이블 §1.1). 해시 결합식과 `record_id`·`point_id`의 **값**은 [ADR-0004](./0004-deterministic-chunk-id-scoped-record-id-and-ulid-exception.md), 메트릭·스팬이 실리는 관측 스택은 [ADR-0022](./0022-observability-genai-semconv-pin-and-license-boundary.md), REST·RFC 9457 규약은 [ADR-0018](./0018-api-rest-sse-mcp-no-grpc-rfc9457.md), 이벤트 전달은 [ADR-0017](./0017-event-delivery-outbox-cloudevents-no-broker.md)이 다루며, 본 문서는 그들이 쓰는 **이름의 형식과 유일성**만 다룬다.

## 맥락과 문제

브리프 D-03은 한 줄("문서 한국어, 식별자·필드·API 영문 snake_case")이고 브리프 §9.9가 타입 `PascalCase`·필드 `snake_case`·이벤트 `domain.entity.action`·메트릭 `rag_<stage>_<name>_<unit>`를 정했다. 그러나 세 설계 제안(A 운영성, B 검색 품질, C 단순성)과 14개 기술 지형 문서는 같은 개념에 다른 이름을, 다른 개념에 같은 이름을 붙였다(매트릭스 미해결 이슈 6: "계약 제안 필드는 이름·타입이 문서마다 조금씩 다르다"). 계약이 코드보다 먼저인 플랫폼(브리프 원칙 1)에서 이름은 계약 그 자체이므로, 바이블 §1.2가 명시한 CI 기계 대조("`schemas/*.schema.json`의 열거값과 §5.7 열거 표를 대조, 이벤트·메트릭·오류 코드도 동일")가 성립하려면 **무엇이 유효한 이름인가**를 형식 규칙으로 고정해야 한다. 확인된 사실은 다음과 같다.

| # | 사실 | 출처 |
|---|------|------|
| F1 | 제안 A는 `Chunk.kind`(`text, table, table_part, code, figure_caption, list, parent, sentence_window, summary`)와 `IndexRecord.item_kind`(`chunk, summary, community_report, entity, page_image, table, figure`)를 **따로** 두어 같은 검색 단위 의미가 두 열거로 갈라졌다. B는 04·10·14 문서의 두 열거를 `item_kind` 하나(11값)로 병합할 것을 제안했고 C도 통합안을 냈다 | 제안 A `Chunk`·`IndexRecord` 표, 제안 B §ChunkSet "계층"·미해결 이슈 1, 제안 C `Chunk` 표, 매트릭스 계약 제안 묶음 `ChunkSet` 행 |
| F2 | 같은 필드명 `mode`가 B `QueryRequest.mode`(`hybrid, dense, lexical, sparse`)와 C `EmbeddedChunkSet.mode`(`document`; 질의 측 `query`), 매트릭스 `mode: query\|document`에서 서로 다른 열거를 가리켰다. JSON Schema `$defs`에 `Mode` 키 하나만 둘 수 없고, 필드명만으로는 어느 값 집합인지 기계가 판정할 수 없다 | 제안 B `QueryRequest` 표, 제안 C `EmbeddedChunkSet` 표, 매트릭스 `EmbeddedChunkSet / IndexRecord` 행 |
| F3 | `run_id`가 제안 A `JobStatus.run_id`(Temporal run), 09 문서 `EvalRun.run_id`(평가 실행), 채널 런(채널 × 컬렉션 × 변형)에 동시에 쓰였다 | 제안 A `JobStatus` 행, 09 문서 §계약 제안 `EvalRun`, 바이블 §3.2 O-01 "런은 (채널 × 컬렉션 × 변형)" |
| F4 | 06 문서는 `chunk_id`를 ULID로 두고 Qdrant 포인트 ID 제약(u64 또는 UUID)을 `ulid_to_uuid`로 우회했고, C는 `ulid_from_hash`(시간 비트를 해시로 대체), A·B는 미정의 `chunk_ulid`를 썼다. 결정적 콘텐츠 주소 키는 시간 정렬 ULID로 표현할 수 없어 D-06이 "발급형 = ULID / 콘텐츠 파생 = BLAKE3 hex"로 개정되었다 | 06 문서 §매핑, 제안 C `Chunk` 표·미해결 이슈 4, 바이블 §3.1 D-06, ADR-0004 |
| F5 | 08 문서는 CloudEvents `source = urn:rag:{tenant_id}:{service}`, `subject = job_id 또는 document_id`, RFC 9457 확장 멤버 `error_code` + `type = https://rag-platform.dev/problems/{code}`를 제안했다. 바이블은 `source = urn:rag:{component}`, `subject = tenant/{tenant_id}/{entity}/{id}`, 확장 속성 `tenantid`, `ProblemDetails.code` + `type = urn:rag:error:{code}`(`StageError.code`와 1:1)로 확정했다 | 08 문서 §아웃박스 CloudEvents 매핑·§API 프레임워크와 HTTP 규약, 바이블 §4.1 오류 모델·§5.3 `CloudEventEnvelope`·`ProblemDetails` |
| F6 | 09 문서 메트릭 표는 라벨 `collection_id, model, provider, device, dataset_id`와 이름 `rag_query_candidates_count`·`rag_feedback_events_total`을, 12 문서 §1.5는 `tenant_id` 속성을 제안했다. 바이블 §6.5는 라벨 7종·`tenant_id` 금지·정본 목록으로 고정했다 | 09 문서 §메트릭 이름, 12 문서 §1.5 노이지 네이버 격리와 비용 계량(계량 원칙), ADR-0022 F9 |
| F7 | 08 문서는 페이지네이션에 Google AIP-158 관례를 따르되 "필드명은 브리프 규약대로 snake_case"라 적었고, MCP Python SDK v2(`mcp>=2,<3`, D-13)는 필드명을 snake_case(`input_schema`, `is_error`, `next_cursor`)로 바꾼 파괴적 변경을 포함한다. 렌더러 대상 외부 API(Anthropic·OpenAI·Gemini)는 공급자 표기를 그대로 쓴다 | 08 문서 §API 프레임워크와 HTTP 규약, 10 문서 §MCP SDK v2 변경, 바이블 §9.3 |
| F8 | 13 문서는 표시 텍스트 NFC / 색인 뷰 NFKC 이중 뷰와 "오프셋은 표시 텍스트 기준"을, 12 문서는 주체 접두 `user:`·`group:`·`tenant:*`를 제안했고 바이블 §6.3·§10.1이 채택했다. 문자 오프셋의 단위(바이트·UTF-16 코드 유닛·코드포인트)는 어느 문서도 명시하지 않았다 | 13 문서 §유니코드 정규화·§결정 사항 요약, 12 문서 §2.1 문서 단위 ACL 필드 설계·§3.1 OIDC 공급자 연동(토큰 → 주체 매핑), 바이블 §5.3 `Provenance`·§6.3 |
| F9 | 물리명은 문서마다 달랐다: Qdrant 컬렉션·alias, OpenSearch 인덱스·alias, Valkey 키 접두, 오브젝트 키, PostgreSQL 테이블, Temporal 워크플로우·액티비티·큐 이름을 바이블 §6.7·§13.1·§13.3·§13.4가 확정했으나 규칙의 **형식**(테넌트 접두 필수 여부, 해시 절단 길이, 복수형)이 한 곳에 없었다 | 바이블 §6.7, §13.1, §13.3, §13.4, ADR-0028 준수 표 5행 |

따라서 결정할 질문은 여섯이다. (1) 표기 체계 — 언어·케이스·접두/접미, (2) 식별자 이름의 형식(ULID/BLAKE3/합성)과 **의미당 하나** 원칙, (3) 열거 타입명의 유일성과 스키마 `$defs` 대응, (4) 이벤트·메트릭·스팬·로그·오류 코드의 형식, (5) 물리명(REST·Temporal·테이블·오브젝트 키·인덱스·Valkey), (6) 어떤 게이트로 강제하는가.

## 결정 동인(decision drivers)

| 동인 | 출처 | 함의 |
|------|------|------|
| Contracts First — 이름은 계약이며 CI가 기계 대조한다 | 브리프 §3 원칙 1, 바이블 §1.2 | 이름 형식이 결정적(정규식으로 판정 가능)이어야 `schemas/` ↔ 바이블 §5.7·§6.5 대조가 성립한다 |
| D-03 한국어 문서·영문 snake_case | 브리프 §4 D-03, §9.2·§9.9 | Python(PEP 8)·Pydantic v2 필드명과 JSON 필드명이 alias 없이 일치해 스키마 ↔ 모델 동치 검증(03-contracts/00)이 단순하다 |
| D-06 발급형/콘텐츠 파생 이분 | 브리프 §4 D-06(v1.2), ADR-0004 | 이름만 보고 ULID(`*_id`, 대문자 26자)인지 BLAKE3(`*_hash`·`doc_version`·`block_id`·`chunk_id`·`record_id`·`stage_key`, 소문자 hex)인지 구분되어야 한다 |
| 단일 좌표계 K1·점수 원장 K3 | 바이블 §2.1 | 같은 구조(`BlockRef`, `ChannelScore`, `ScoreBreakdown`)가 `Chunk`·`IndexRecord`·`RankedResult`·`ContextItem`에서 같은 이름을 가져야 좌표·점수가 소실 없이 흐른다 |
| 멀티테넌시·저카디널리티·E13 | 브리프 §3 원칙 9, 바이블 §6.5·§10.3 E13·§13.4 | 메트릭 `tenant_id` 라벨 금지, 스팬은 `rag.tenant_id_hash`, Valkey 테넌트 스코프 키는 `{tenant}` 접두 필수, 오브젝트 키는 `tenants/{tenant_id}/` 접두 |
| Korean-First — 한글·전각·호환 자모 | 브리프 §3 원칙 6, 13 문서 | 오프셋은 유니코드 코드포인트(바이트·UTF-16 단위 배제), 표시 NFC / 렉시컬 NFKC 혼용 금지, 언어 태그 BCP 47 |
| Adapters over Forks·표준 준수 | 브리프 §3 원칙 2, D-08·D-11, 08·09 문서 | 벤더 명(Docling `TITLE`·`self_ref`, Qdrant `point_id`, OpenSearch `_id`)은 어댑터 경계에서 우리 이름(`heading` level 0, `element_path`, `record_id`)으로 변환되고, 자체 규약은 표준(CloudEvents 1.0.2, RFC 9457, RFC 3339, BCP 47, Prometheus 명명, OTel semconv)이 비워 둔 자리(`type` 값, `type` URN, 메트릭 이름, `rag.*`)만 채운다 |
| 플러그인 생태계 D-10 | 브리프 §4 D-10, ADR-0032 | `plugin_id = {extension_point}.{implementation}`이 entry point 그룹 `rag_platform.{extension_point}`·이름과 기계적으로 대응한다 |

## 고려한 대안

| # | 대안 | 판정 | 근거 요약 |
|---|------|------|-----------|
| A | 검색 단위 의미를 `Chunk.kind`와 `IndexRecord.item_kind` 두 열거로(제안 A) | 기각 | F1; K1 위반, 매핑 표 필요, `FilterableField.item_kind`·전략 필터 `item_kinds`가 어느 열거를 가리키는지 불명 |
| B | 동명 열거 허용 — 필드명 `mode`를 문맥으로 구분(`$defs/Mode` 또는 인라인 `enum[...]`) | 기각 | F2; `$defs` 키 충돌, CI 기계 대조 불가, 코드젠 타입명 충돌 |
| C | JSON API 필드 camelCase(JavaScript 관례) + Pydantic `alias_generator` | 기각 | F7; D-03 위반, 스키마·모델·문서 삼중 표기, MCP SDK v2·CloudEvents·RFC 9457·OTel 모두 snake_case 또는 점 표기 |
| D | 자유 형식 메트릭 이름·라벨(문서별 제안 그대로: `rag_query_candidates_count{stage}`, 라벨 `model`·`collection_id`·`tenant_id`) | 기각 | F6; 카디널리티 폭증·E13 위반, 정본 목록 없이는 대시보드·알림 규칙을 기계 검증할 수 없다 |
| E | 모든 `*_id`를 ULID로 통일(`chunk_id` ULID + `ulid_to_uuid` / `ulid_from_hash` / `chunk_id` + `chunk_key` 이중 필드) | 기각(ADR-0004) | F4; 콘텐츠 주소 키는 시간 정렬을 가질 수 없고 이중 필드는 어느 것이 조인 키인지 모호 |
| F | `run_id` 다의어 허용(잡·평가·채널 런에서 문맥으로 구분) | 기각 | F3; 로그 필드 `job_id`·`trace_id`와 상관할 때 어느 런인지 판정 불가 |
| G | CloudEvents `source`에 테넌트 포함(`urn:rag:{tenant_id}:{service}`)·`subject`에 ID만; RFC 9457 `error_code` + HTTPS 문제 URL(08 문서) | 기각 | F5; `source`는 발행 컴포넌트, 테넌트는 `tenantid`·`subject`가 운반; `code` 하나가 `StageError`와 1:1, URN은 호스트명에 의존하지 않는다 |
| H | 바이블 §6 규약 전체 — D-03 snake_case, ULID/BLAKE3 이분, 고유 열거 타입명, 의미당 식별자 하나, `domain.entity.action`, `rag_<stage>_<name>_<unit>`, `{stage}.{reason}`, 물리명 §13.3·§13.4 — 와 CI 기계 대조 | **채택** | 바이블 §5.7·§6·§13, 매트릭스 "운영·평가 공통 요구" CI 게이트·관측 메트릭 표준 |

기각 대안 A~D의 장단점과 판정 근거(표의 근거 요약 보충; 대안 H(채택)의 장단점은 "결과" 절에 적는다):

- **A — 이중 열거**(청킹 의미 `figure_caption`·`sentence_window` 등과 인덱스 의미 `community_report`·`page_image` 등을 각각의 열거로 두고 `index` 어댑터가 매핑). 장점: 각 스테이지가 자기 열거만 알면 되고 그래프·시각 플러그인 값이 청킹 열거를 오염시키지 않는다. 단점: 한 검색 단위가 두 이름을 가져 K1(단일 좌표계)이 깨지고, 후처리 `item_kind_penalty`·`omitted[].reason = item_kind_excluded`·`FilterableField.item_kind`·전략 필터 `item_kinds`가 어느 열거인지 매 문서가 다시 정해야 한다 — 매트릭스 미해결 이슈 6이 지적한 불일치의 원인(F1). 판정: 바이블 §5.7 `ItemKind` 단일 열거 11값(`text, list_group, code, table, table_part, figure, parent, summary, community_report, entity, page_image`)을 `Chunk`·`IndexRecord`·후보·결과·항목이 공유하고 계층은 `ChunkLevel`(`0, 1, 2`) 하나로 표현하며, `figure_caption`은 `figure` + `caption` 블록 참조로, `sentence_window`는 후처리 결과(`ExplainCode.window_added`)로 표현된다.
- **B — 동명 열거 `mode`**(`EmbeddedChunkSet.mode`·`QueryRequest.mode`처럼 필드명이 같으면 문맥으로 구분하고 스키마에는 인라인 `enum[...]`). 장점: 필드명이 짧고 제안서 표를 그대로 옮길 수 있다. 단점: `$defs` 키가 열거 타입명이어야 CI가 §5.7과 대조할 수 있는데(바이블 §5.7 첫 문단) 동명 열거는 키를 하나로 만들 수 없고 Pydantic·TypeScript 코드젠에서 `Mode` 클래스가 충돌하며(F2), 인라인 열거는 값 집합의 변경을 추적할 수 없다. 판정: 열거 타입명은 PascalCase **고유**(`EmbeddingMode`/`RetrievalMode`), 필드 표는 `enum(TypeName)`, 값 제약(고정값 `document`·부분집합)은 스키마 `const`/`enum` 부분집합으로, 표에 없는 인라인 열거는 `{Type}.{path}`(예: `Block.figure.kind`) 이름으로 `$defs`에 등재한다(바이블 §5.7·§6.4; 계약 개요 §5).
- **C — camelCase API**(응답·요청 필드를 camelCase로 내보내고 서버는 `alias_generator=to_camel`로 변환). 장점: JavaScript 클라이언트 관례와 일치하고 Anthropic·OpenAI 클라이언트 라이브러리 표기와 비슷해 보인다. 단점: D-03 위반; JSON Schema(게시 정본)·Pydantic 모델·문서 표가 서로 다른 이름을 갖게 되어 03-contracts/00의 스키마 ↔ 모델 동치 검증이 alias 해소를 포함해야 하고 `schemas/` 기계 대조·OpenAPI 경로 린트가 두 표기를 알아야 한다; 정합 대상인 MCP SDK v2(`input_schema`, `next_cursor`), CloudEvents(`specversion`, `datacontenttype`), RFC 9457, OTel 속성(점 표기 + snake_case)이 모두 camelCase가 아니다(F7). 렌더러가 만드는 공급자 페이로드(`search_result`, `cache_control` 등)는 공급자 스키마의 문제이며 우리 계약이 아니다. 판정: 필드·열거값·쿼리 파라미터·경로 변수는 snake_case, 헤더는 HTTP 관례(`Idempotency-Key`), TypeScript SDK는 JSON Schema 코드젠으로 snake_case를 그대로 노출한다(바이블 §12 `sdk/typescript`).
- **D — 자유 형식 메트릭**(각 컴포넌트가 Prometheus 명명 관례 안에서 이름·라벨을 자유롭게 정의; 09 문서 초안 표). 장점: 구현이 빠르고 문서별 제안(`rag_query_candidates_count`, `rag_feedback_events_total`)을 그대로 쓸 수 있다. 단점: 라벨 `collection_id`·`tenant_id`·`model`은 테넌트 수 × 컬렉션 수 × 모델 수로 시계열을 폭증시키고, `tenant_id` 평문은 E13(텔레메트리에는 `rag.tenant_id_hash`만)과 어긋난다(F6, ADR-0022 대안 D); 정본 목록이 없으면 대시보드·알림 규칙·런북(09-operations/03)이 어떤 이름을 전제해야 하는지 기계 검증할 수 없다. 판정: `rag_<stage>_<name>_<unit>`(단위 `seconds, bytes, total, count, ratio`), 라벨은 `stage, channel, backend_id, profile_id, outcome, renderer, queue`만, **`tenant_id` 라벨 금지**, 정본 목록은 바이블 §6.5이며 새 메트릭은 §1.2 minor 절차로 §6.5에 먼저 추가한다.

## 결정

**결정:** 문서 기본 언어 **한국어**(기술 용어·식별자는 영문). 코드·스키마 필드·API는 **영문 snake_case**(브리프 §4 D-03; 바이블 §3.1 D-03 `confirmed` — "§6 명명 규약으로 정밀화").

**결정:** 모든 열거값(고유 타입명 `enum(TypeName)`)·이벤트·오류 코드·메트릭 이름은 §5.7·§6에 적힌 철자만 유효하며 CI가 `schemas/`와 대조한다(바이블 결정 사항 요약).

**결정:** 발급형 ID(`request_id`, `document_id`, `job_id`, `commit_id`, `query_id`, `plan_id`, `pack_id` 등 `*_id`)는 **ULID**(시간 정렬). **콘텐츠 파생 키는 예외로 BLAKE3 hex를 그대로 쓴다**: 결합식 `H(label, *parts) = blake3_hex(label ‖ 0x1F ‖ 0x1F로 결합한 parts)`(바이블 §6.2), `block_id = H("block", doc_version, element_path)[:32]`, `chunk_id = H("chunk", doc_version, chunker_config_hash, level, span)`, `stage_key`(잡 스코프 `tenant_id/collection_id/document_id` 포함), `doc_version`, `*_hash`. **물리 인덱스 키는 스코프·세대 합성** `record_id = H("record", tenant_id, collection_id, document_id, index_generation, chunk_id)`이며 Qdrant 포인트 ID는 `uuid5(NAMESPACE_RAG_CHUNK, record_id)`, OpenSearch `_id = record_id`(콘텐츠 주소 `chunk_id`는 payload 필드로 유지). 콘텐츠 해시는 **BLAKE3**(소문자 hex). 시간은 **RFC 3339 UTC**. 언어 코드는 **BCP 47**(브리프 §4 D-06, 개정 v1.2, 근거: ADR-0004, ADR-0037 — 값의 결정은 그 두 ADR, 이름의 형식은 본 문서).

결정에 딸린 정본 세부(모두 바이블 인용; 이 문서가 새로 정하지 않는다):

| 영역 | 규약(바이블 절) |
|------|-----------------|
| 표기 체계(§6.4) | 타입 `PascalCase`, 필드·열거값 `snake_case`, 열거값은 문자열. 불리언은 `is_`/`has_`/`supports_` 접두 또는 형용사(`enabled`, `truncated`). 컬렉션 필드는 복수형(`chunks`, `warnings`). 참조 필드는 `*_ref`(단수 `ArtifactRef`)/`*_refs`. 봉투 `schema_type`은 PascalCase 타입명(§5.2) |
| 열거 타입명(§5.7·§6.4) | PascalCase **고유** — 같은 이름의 열거는 하나만 존재(`mode` 같은 동명 이의 금지 → `EmbeddingMode`/`RetrievalMode`); 필드 표는 `enum(TypeName)`; 값 제약은 스키마 `const`/`enum` 부분집합; 스키마 `$defs` 키 = 열거 타입명; 표에 없는 인라인 열거는 `{Type}.{path}` 이름으로 `$defs` 등재. `ItemKind`는 단일 열거 11값(A의 `kind`/`item_kind` 이중 폐기), `ChunkLevel`은 integer `0, 1, 2` |
| 식별자는 의미당 하나(§6.1·§6.4) | `run_id`는 `EvalRun`만; 채널 런 `channel_run_id = "{channel}:{collection_id}:{variant_id}"`; Temporal `workflow_run_id`(`string(uuid)`, Temporal 발급, `LocalRunner`는 null); 질의 변형 `variant_id`(ULID 서버 발급, `original` 변형은 `variant_id = query_id`) |
| 발급형 ID(§6.1) | `request_id, document_id, job_id, commit_id, chunk_set_id, query_id, variant_id, plan_id, candidate_set_id, ranked_set_id, pack_id, event_id, collection_id, tenant_id, entry_id, feedback_id, dataset_id, run_id(EvalRun 전용)` — ULID 26자 Crockford base32 **대문자**, 서버 발급(`commit_id`·`event_id`는 워크플로우가 1회 생성, §11.4) |
| 콘텐츠 파생 키(§6.1·§6.2) | `block_id, chunk_id, record_id, stage_key, content_hash, doc_version, commit_hash, *_hash, embedding_space_id, embedding_profile_hash, profile_hash, dictionary_hash` — BLAKE3 **소문자 hex** 기본 64자, `block_id`만 32자 절단; `point_id = uuid5(NAMESPACE_RAG_CHUNK, record_id)`, `NAMESPACE_RAG_CHUNK = uuid5(NAMESPACE_URL, "urn:rag:chunk")` |
| 합성·표기형 식별자(§6.1·§10.1) | `cite_id = d{rank}`(1-based 관련도순, 최종 항목 연속 `d1..dK`); `plugin_id = {extension_point}.{implementation}`(둘 다 snake_case; `parser.hwpx_python_hwpx`, `fuser.rrf`); `analyzer_id = {engine}:{version}:{dictionary}`(`mecab-ko:1.3.7:ko-dic-2.1.1`); `tokenizer_id = hf:{repo} \| tiktoken:{encoding} \| anthropic:{model} \| gemini:{model}`; `model_id = {repo}@{revision}`(HF SHA 또는 태그; 서빙 이미지는 `image_digest` 별도); `profile_id` kebab-case(`standard`, `korean-gov`); 주체 `user:{subject}`, `group:{group_id}`, `service:{client_id}`, `tenant:*` |
| 시간·언어·오프셋·정규화(§6.3) | 시각 `*_at` RFC 3339 UTC `Z` 접미 밀리초(`2026-09-22T09:00:00.000Z`); 날짜만 `*_date`(`YYYY-MM-DD`); 언어 BCP 47 소문자(`ko`, `en`, `ko-KR`), 필드명 `lang`(블록·청크·레코드·항목 `header.lang`) / `language`(문서·팩 힌트 `render_hints.language`); 문자 오프셋은 **유니코드 코드포인트** 0-based 끝 미포함(`Provenance`는 원문 `Block.text`, `BlockRef.char_*`·`sentence_spans`·`segments`는 `display_text`/`Chunk.text`); 표시 텍스트 NFC, 렉시컬 뷰 NFKC(혼용 금지) |
| 이벤트(§5.7·§6.5) | `domain.entity.action`(과거형 동사) = CloudEvents `type`; `source = urn:rag:{component}`; `subject = tenant/{tenant_id}/{entity}/{id}`; 확장 속성 `tenantid`; `id = event_id`(ULID, 소비자 멱등 키); `dataschema = urn:rag:schema:{name}:{major}`; 카탈로그 6개 도메인(`ingest.document.*`, `job.state.changed`, `index.commit.*`·`index.consistency.mismatch`, `acl.document.updated`·`collection.*`, `audit.*`, `feedback.query.*`·`eval.run.completed`); `data`는 ID·해시·상태만 |
| 메트릭·스팬·로그(§6.5) | `rag_<stage>_<name>_<unit>`(Prometheus; 단위 `seconds, bytes, total, count, ratio`); 라벨은 `stage, channel, backend_id, profile_id, outcome, renderer, queue`만, **`tenant_id` 라벨 금지**; 정본 목록 §6.5(`rag_query_latency_seconds` … `rag_eval_metric_value{metric}`); 스팬 `rag.{stage}`(`rag.plan`, `rag.retrieve.dense`, `rag.rerank`, `rag.ingest.parse`); 속성은 Weaver 생성 상수 `gen_ai.*` + OpenInference `retrieval.documents.*`/`reranker.*` + 자체 `rag.*`(`rag.tenant_id_hash`, `rag.profile_hash`, `rag.plan_id`, `rag.degraded_count`); 로그 structlog JSON 필드 `event, level, tenant_id_hash, job_id, trace_id, stage, code` |
| 오류 코드(§4.1·§5.7) | `{stage}.{reason}`(snake_case), 접두 `fetch, parse, normalize, chunk, enrich, embed, index, publish, plan, retrieve, fuse, hydrate, rerank, postprocess, pack, render, auth, api, profile, plugin, contract, outbox`; `StageError.code` ↔ RFC 9457 `type = urn:rag:error:{code}` 1:1; `ProblemDetails.code`; 재시도 여부는 카탈로그가 결정; `Warning.code`·`DegradedEntry`도 같은 형식 |
| 스키마·미디어 타입(§5.1·§6.4) | 파일 `schemas/{kebab-name}.schema.json`, `$id = urn:rag:schema:{kebab-name}:{major}`, `schema_version` semver(추가 minor, 제거·의미 변경 major), 플러그인 `contracts_compat` 범위; 미디어 타입 `application/vnd.rag.{kebab-name}+json` |
| 환경 변수·설정(§6.6) | 접두 `RAG_`, 중첩 `__`(pydantic-settings): `RAG_PG__DSN`, `RAG_OBJECT_STORE__URI`, `RAG_VALKEY__URL`, `RAG_TEMPORAL__ADDRESS`, `RAG_PROFILE__PATH`, `RAG_AUTH__OIDC_ISSUER`, `RAG_OTEL__EXPORTER_OTLP_ENDPOINT`, `RAG_OTEL__CONTENT_CAPTURE=none`; 비밀은 `RAG_SECRETS__PROVIDER=env\|openbao\|aws_kms` + `credentials_ref` 간접 참조 |
| 패키지·엔드포인트(§6.7·§14) | `rag-platform`(import `rag_platform`), extras `[kiwi]`·`[docling-chunker]`·`[gpu]`·`[opensearch]`·`[temporal]`·`[eval]`; 플러그인 `rag-plugin-{name}`(import `rag_plugin_{name}`), entry point 그룹 `rag_platform.{extension_point}`; REST `/v1/{plural-kebab}`, 액션은 하위 POST(`/v1/jobs/{job_id}/cancel`), 경로 변수 `{snake_id}`, 쿼리 파라미터 snake_case, 헤더 `Idempotency-Key`, `RateLimit`, `RateLimit-Policy`, `Deprecation`, `Sunset`; 사이드카 `POST /v1/convert`·`GET /healthz`; `GET /healthz`·`/readyz`·`/metrics`; MCP `/mcp` |
| Temporal·테이블(§6.7·§13.1) | 워크플로우 타입 `{domain}.{entity}.v{n}`(`ingest.document.v1`), 액티비티 `stage.{stage_name}`, 태스크 큐 kebab-case(`ingest-io`); PostgreSQL 테이블 snake_case 복수(`index_commits`, `idempotency_keys`, `user_dictionary_entries`), 모두 `tenant_id` 컬럼 |
| 오브젝트 키(§13.3) | 원본 `tenants/{tenant_id}/sources/{blake3[:2]}/{blake3}`; 산출물 `tenants/{tenant_id}/artifacts/{schema_type_kebab}/{stage_key[:2]}/{stage_key}.json`; 파생물 `tenants/{tenant_id}/derived/{kind}/{blake3[:2]}/{blake3}.{ext}`(부모 번들 `derived/parent_texts/{chunk_set_blake3}.json`); 평가 `eval/datasets/{dataset_id}/{qrels\|answer_spans}.jsonl`; 모델 `models/{repo}/{revision}/…`; 스냅샷 `snapshots/{backend_id}/{physical_name}/{timestamp}` |
| Qdrant·OpenSearch·Valkey(§13.4) | Qdrant 물리 컬렉션 `rag_vec_{embedding_profile_hash[:12]}`, 테넌트 전용 `rag_vec_{hash12}_t_{tenant_id}`, alias `col_{collection_id}_vec`, named vectors = `VectorName` 열거, payload 인덱스 필드명 = `IndexRecord` 필드명(`acl_allow`, `page_start`, `custom.*`); OpenSearch `rag_lex_{lexical_profile_hash[:12]}`(`_t_{tenant_id}` 접미), alias `col_{collection_id}_lex`·`t_{tenant_id}_lex`, `_id = record_id`, `routing = tenant_id`; Valkey `{prefix}:{tenant}:…`(`plan:`, `ptxt:`, `idem:`, `aclrev:`, `rl:`, `cursor:`, `groups:`) — 모든 테넌트 스코프 키는 `{tenant}` 접두 필수, 콘텐츠 해시 키 `qemb:`·`tok:`·`rr:`와 `collspec:{collection_id}`만 예외 |

규약이 한 봉투에 어떻게 겹쳐 나타나는지 보이는 예시(`index.commit.published`; `data` 필드 구성은 [잡·이벤트·상태 계약](../03-contracts/12-jobs-events-and-status.md)이 확정한다):

```json
{
  "specversion": "1.0",
  "id": "01J9ZQ4K7X2M8N3P5R6S7T8V9W",
  "source": "urn:rag:worker",
  "type": "index.commit.published",
  "time": "2026-09-22T09:00:00.000Z",
  "subject": "tenant/01J9ZQ4K7X2M8N3P5R6S7T8VA0/document/01J9ZQ4K7X2M8N3P5R6S7T8VA1",
  "datacontenttype": "application/json",
  "dataschema": "urn:rag:schema:index-commit:1",
  "tenantid": "01J9ZQ4K7X2M8N3P5R6S7T8VA0",
  "data": {
    "job_id": "01J9ZQ4K7X2M8N3P5R6S7T8VA2",
    "document_id": "01J9ZQ4K7X2M8N3P5R6S7T8VA1",
    "commit_id": "01J9ZQ4K7X2M8N3P5R6S7T8VA3",
    "doc_version": "9f3a7c1e5b2d8046a3f9e1c7b5d20e4f6a8c1b3d5e7f90a2c4e6081b3d5f7a9c",
    "index_generation": 3,
    "status": "committed"
  }
}
```

`id`·`tenantid`·`data.*_id`는 ULID 대문자, `doc_version`은 BLAKE3 소문자 hex 64자, `type`은 카탈로그의 과거형 이벤트, `time`은 밀리초 `Z`, `status`는 `CommitStatus` 열거값이며 본문 텍스트는 없다.

## 결과

### 긍정

- 이름이 정규식으로 판정된다: ULID `^[0-9A-HJKMNP-TV-Z]{26}$`, hex64 `^[0-9a-f]{64}$`, hex32 `^[0-9a-f]{32}$`, `plugin_id` `^[a-z_]+\.[a-z0-9_]+$`, 이벤트 `^[a-z]+\.[a-z_]+\.[a-z_]+$`, 메트릭 `^rag_[a-z_]+_(seconds|bytes|total|count|ratio)$`(게이지 `rag_eval_metric_value`만 예외로 정본 목록에 명시), 오류 코드 `^[a-z]+\.[a-z_]+$`. 계약 개요는 이를 `$defs/Ulid`·`Hex64`·`Hex32`·`PluginId`·`TokenizerId`·`ModelId`·`CiteId`·`PrincipalString` 원시 형식으로 게시한다.
- 이름만으로 성질이 드러난다 — `*_id` 대문자는 발급형·시간 정렬, `*_hash`·`doc_version`·`block_id`·`chunk_id`·`record_id`·`stage_key` 소문자 hex는 결정적·재계산 가능, `*_ref(s)`는 `ArtifactRef`, `*_at`는 시각, `is_/has_/supports_`는 불리언, `tenants/`·`{tenant}:` 접두는 테넌트 스코프.
- 세 제안의 불일치(`kind`/`item_kind`, `mode`, `run_id`, `chunk_ulid`)가 열거 타입명 고유화와 "의미당 식별자 하나"로 구조적으로 재발하지 않는다. 코드젠(Pydantic·TypeScript)에서 타입명 충돌이 없고, Pydantic 필드명 = JSON 필드명 = 문서 표 필드명이라 alias 계층 없이 스키마 ↔ 모델 동치 검증(03-contracts/00)이 단순하다.
- 메트릭·스팬·이벤트·오류 코드가 정본 목록을 가지므로 대시보드·알림·런북·웹훅 구독 필터(`subscriptions.events[]`)를 CI에서 검증할 수 있다.

### 부정

- 명명 규약 변경은 항상 major(바이블 §1.2)라, 초기에 굳은 이름(`sparse_learned`, `litm_alternating`, `korean-gov`)을 나중에 다듬기 어렵다.
- 규약 표가 길어 신규 기여자의 학습 비용이 있고, 린트 규칙(정규식·정본 목록 대조·문자열 리터럴 금지)을 `telemetry/`·`contracts/enums.py`·`schemas/`·OpenAPI에 걸쳐 유지해야 한다.
- 외부 표준 표기(CloudEvents `specversion`·`datacontenttype`, OTel `gen_ai.request.model`, Qdrant `point_id`, OpenSearch `_id`)가 우리 규약과 섞여 보이며, 이 경계는 어댑터·봉투 문서가 매번 설명해야 한다. 인라인 열거를 `{Type}.{path}`로 모두 등재하면 `$defs`가 커지고 값 하나 추가도 §5.7 갱신(minor)을 동반한다.

### 중립

- 값의 결정은 다른 ADR에 있다: 해시 결합식·`record_id`·`point_id`(ADR-0004·ADR-0037), 이벤트 전달과 `event_id` 멱등(ADR-0017), REST·RFC 9457·`Idempotency-Key`(ADR-0018), 관측 스택·Weaver 상수(ADR-0022), 물리명이 격리 등급과 맺는 관계(ADR-0028), 워크플로우·액티비티(ADR-0003). 본 문서는 그 이름들의 형식만 고정한다.
- 08 문서의 `source = urn:rag:{tenant_id}:{service}`·`error_code`·HTTPS 문제 URL, 09 문서의 라벨 제안, 06 문서의 `ulid_to_uuid`는 바이블 §5.3·§6으로 대체되었다(바이블이 정본). 브리프 §9.5 스키마 표기(`string(ulid)`, `enum[...]`)는 문서 표 표기이고 스키마 파일에서는 `$defs` 원시 형식 `$ref`로 구현된다(계약 개요 §6).

## 준수 확인 방법

| # | 규칙 | 강제 수단 | 게이트·위치 |
|---|------|-----------|-------------|
| 1 | 열거값·열거 타입명 = 바이블 §5.7 | `schemas/*.schema.json`의 `$defs/{TypeName}` 값 집합과 `contracts/enums.py`(§5.7 단일 소스)를 §5.7 표와 기계 대조; `$defs` 키가 PascalCase 고유이며 인라인 `enum`은 `{Type}.{path}` 이름으로만 존재(불일치·중복 = 빌드 실패) | CI 스키마 대조(바이블 §1.2), 계약 개요 §5 |
| 2 | 필드·열거값·쿼리 파라미터·경로 변수 snake_case, 타입 PascalCase, 불리언·복수형·`*_ref(s)` 접미 | 스키마 린트: `properties` 키 `^[a-z][a-z0-9_]*$`, `$defs` 키 `^[A-Z][A-Za-z0-9]*(\.[a-z_]+)*$`, `type: boolean` 필드는 `is_/has_/supports_` 접두 또는 허용 형용사 목록, `type: array` 필드는 복수형 또는 `*_ids`/`*_refs`; Pydantic 모델에 `alias`·`alias_generator` 금지(ruff/AST 린트) | CI 스키마 린트 + 코드 리뷰 |
| 3 | ID 형식 — 발급형 ULID 대문자, 콘텐츠 파생 hex64(`block_id` hex32), 합성형(`cite_id`, `plugin_id`, `channel_run_id`, `analyzer_id`, `tokenizer_id`, `model_id`, 주체) | 스키마는 `$defs/Ulid`·`Hex64`·`Hex32`·`CiteId`·`PluginId`·`TokenizerId`·`ModelId`·`PrincipalString`을 `$ref`(직접 `pattern` 재정의 금지); 적합성 키트 `contract_roundtrip`이 예시 인스턴스로 패턴 검증; `run_id`는 `EvalRun`·`EvalReport` 스키마 밖에서 등장 시 실패 | CI 스키마 대조, 적합성 키트(ADR-0032) |
| 4 | 이벤트 `type`·오류 코드·메트릭 이름·스팬 이름 = 정본 카탈로그 | 런타임 레지스트리 스냅샷(발행 가능한 `type` 집합, `StageError.code` 카탈로그, Prometheus 레지스트리, 스팬 이름 상수) ↔ 바이블 §5.7·§6.5 목록 기계 대조; 메트릭 라벨은 7종만, `tenant_id` 라벨은 실패; 오류 코드 접두는 22종만 | CI 이름 대조(바이블 §1.2), ADR-0022 준수 표 3 |
| 5 | CloudEvents 봉투 형식 | `CloudEventEnvelope` 스키마: `source` `^urn:rag:[a-z-]+$`, `subject` `^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/.+$`, `id`·`tenantid` ULID, `time` `Z` 접미; 계약 테스트 "data에 `text`·`context_prefix`·`query` 키 없음" | 계약 테스트(ADR-0017) |
| 6 | 시각·날짜·언어·오프셋 | `*_at` → `$defs/DateTime`(`Z` 강제), `*_date` → `format: date`, `lang`/`language` → BCP 47 패턴(소문자); 오프셋은 적합성 키트 `contract_roundtrip`이 `Chunk.text`를 코드포인트로 슬라이스해 `block_refs` 재구성(불변식 "block_refs 합집합 = text") | 스키마 린트, 적합성 키트 |
| 7 | REST 경로·헤더 | OpenAPI 린트: 경로 `^/v1/[a-z-]+(/\{[a-z_]+_id\}(/[a-z-]+)?)*$`, 액션은 POST 하위 경로, 쿼리 파라미터 snake_case, 헤더 이름 허용 목록 | OpenAPI 린트(ADR-0018 준수 표 7; 05-api/01 확정 후 실패로 승격) |
| 8 | 환경 변수 `RAG_` + `__` | pydantic-settings `env_prefix="RAG_"`, `env_nested_delimiter="__"`; 설정 레퍼런스(09-operations/02)를 설정 모델에서 생성해 문서 ↔ 코드 diff | CI 문서 생성 diff |
| 9 | 물리명 — Temporal 타입·액티비티·큐, 테이블, 오브젝트 키, Qdrant·OpenSearch·Valkey 키 | 어댑터 명명 함수(`storage/keys`, `adapters/index/qdrant`·`opensearch`, `storage/valkey`)의 단위 테스트가 §13.3·§13.4 정규식과 대조; Valkey 테넌트 스코프 키는 `{tenant}` 접두가 없으면 키 빌더가 예외(바이블 §13.4; E17 콘텐츠 키 스코프와 같은 원칙이나 E17 자체는 `record_id`·`stage_key`·PK만 다룬다); Temporal 워크플로우 타입 `^[a-z]+\.[a-z_]+\.v[0-9]+$`, 액티비티 `^stage\.[a-z_]+$`; 마이그레이션 린트로 테이블명 snake_case 복수 | 어댑터 테스트(ADR-0028 준수 표 5), 보안 불변식 테스트(ADR-0027) |
| 10 | 플러그인 `plugin_id` = entry point 그룹·이름 조립값 | 레지스트리 로딩 시 `PluginMeta.plugin_id == f"{extension_point}.{entry_point_name}"` 검증, 불일치는 `plugin.capability_unsupported`가 아닌 로딩 거부(`profile.invalid`) | 플러그인 레지스트리(ADR-0032) |

코드 리뷰 체크리스트(요약): (a) 새 필드가 snake_case이고 불리언·복수형·`*_ref(s)` 규칙을 따르는가, (b) 새 열거에 고유 PascalCase 타입명이 있고 §5.7에 먼저 등재되었는가(동명 이의 없음), (c) 새 식별자가 발급형(`*_id`, ULID)인지 콘텐츠 파생(hex)인지 명확하며 기존 의미와 겹치지 않는가(`run_id` 금지), (d) 이벤트·메트릭·오류 코드가 정본 목록에 있고 `tenant_id` 라벨·본문 텍스트가 없는가, (e) 벤더 이름이 어댑터 경계 밖으로 새지 않는가, (f) 문서 본문이 한국어이고 식별자는 영문 그대로인가.

## 재검토 조건

- 명명 규약 자체의 변경(케이스·접두·형식)은 바이블 §1.2에서 **major**이며 본 ADR 개정과 영향 문서 목록을 동반한다. 열거값·이벤트·메트릭·오류 코드의 **추가**는 minor로 §5.7·§6.5 표 갱신만 필요하며 이 ADR은 바뀌지 않는다.
- 오케스트레이션 문서가 내부 액티비티 이름군 `ledger.*`·`dispatch.*`·`backend.*`·`outbox.relay_loop`·`eval.*`를 쓰고 있다([오케스트레이션과 워크플로우](../02-architecture/06-orchestration-and-workflows.md) 미해결 이슈 1). 액티비티 명명을 `stage.{stage_name}` 외로 확장할지, 내부 이름으로 두고 §6.7에 "내부 액티비티는 `{component}.{action}`" 규칙을 추가할지 02-architecture/06 확정 시 본 ADR을 개정한다.
- 회복탄력성 문서의 메트릭 후보 `rag_retrieve_circuit_open_total{backend_id}`·`rag_retrieve_retry_budget_ratio{backend_id}`·`rag_query_degraded_total{component}`([실패 모드와 회복탄력성](../02-architecture/09-failure-modes-and-resilience.md) 미해결 이슈 10)와 큐 대기 메트릭은 §6.5 정본 목록에 없다. 09-operations/03에서 일괄 추가(minor)하되 라벨은 7종 안이어야 하며 `component`는 라벨 허용 목록 개정이 필요하다.
- `string(duration)` 표기가 바이블(`5m`, `24h`)과 ISO 8601(`PT5M`) 둘로 쓰인다(계약 개요 미해결 이슈 U-1). 03-contracts/14가 하나로 확정하면 §6.3에 기간 표기 규칙을 추가한다.
- gRPC/ConnectRPC 도입 시(ADR-0018 재검토 조건) protobuf 필드명 snake_case 유지·JSON Schema 코드젠 원칙을 §6.4에 추가하고, 블록·청크 단위 ACL 도입 시 `Block.acl_override`·`Chunk.acl` 필드명(바이블 §10.1)과 payload 매핑 접두(`acl_*`)를 재확인한다. GenAI semconv Stable 승격에 따른 `rag.*` 속성 축소는 ADR-0022 재검토 조건을 따른다.

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) — §3 원칙 1·2·6·9, §4 D-03·D-06(v1.2)·D-08·D-10·D-11·D-13, §9.2·§9.5·§9.9·§9.11, §11
- [설계 바이블](../02-architecture/00-design-bible.md) — §1.1~1.2, §2.1 K1·K3·K5, §2.3, §3.1 D-03·D-06, §3.2 O-01, §3.3 0036행, §4.1 오류 모델, §5.1~5.3, §5.7(열거·이벤트 카탈로그·오류 코드), §6.1~6.7, §10.1, §11.4, §12, §13.1, §13.3, §13.4, §14, §16(`channel_run_id`·`variant_id`·`workflow_run_id`, 열거 `mode` 고유화 행), 결정 사항 요약
- [기술 지형 종합: 선정 매트릭스와 결정 권고](../07-tech-landscape/00-summary-and-selection-matrix.md) — 역할과 D-10 확장 지점 매핑(채널 열거), 계약 제안 묶음(`ChunkSet`·`EmbeddedChunkSet / IndexRecord`·잡·이벤트·평가 행), 어댑터·플러그인 공통 요구 2·6·7, 운영·평가 공통 요구(CI 게이트·관측 메트릭 표준), 미해결 이슈 6
- [벡터·렉시컬 인덱스 백엔드](../07-tech-landscape/06-vector-and-lexical-index-backends.md) — §매핑(`ulid_to_uuid`, Qdrant 포인트 ID 제약); [LLM 컨텍스트 최적화와 MCP](../07-tech-landscape/10-llm-context-optimization-and-mcp.md) — §MCP SDK v2 변경(snake_case), ContextPack 제안 필드(ULID·RFC 3339·BLAKE3 용어 재사용)
- [오케스트레이션·메시징·API 프레임워크](../07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md) — §아웃박스(CloudEvents 매핑), §API 프레임워크와 HTTP 규약(RFC 9457 확장 멤버, 페이지네이션 snake_case)
- [평가 프레임워크·벤치마크·관측성](../07-tech-landscape/09-evaluation-and-observability.md) — §메트릭 이름(라벨 초안), §표준 모델 매핑, §계약 제안(`EvalRun.run_id`)
- [보안·멀티테넌시·PII·라이선스 컴플라이언스](../07-tech-landscape/12-security-multitenancy-pii-and-licensing.md) — §2.1 문서 단위 ACL 필드 설계(주체 접두), §3.1 OIDC 공급자 연동(토큰 → 주체 매핑), §1.5 노이지 네이버 격리와 비용 계량(계량 원칙), §3.5 레이트 리밋과 감사 로그(감사 이벤트 명명)
- [한국어 NLP·토크나이징·언어 자원](../07-tech-landscape/13-korean-nlp-tokenization-and-language-resources.md) — §유니코드 정규화(NFC/NFKC), §결정 사항 요약
- 설계 제안 [A](../12-appendix/design-proposals/proposal-A-operability-first.md)(`Chunk.kind`·`IndexRecord.item_kind`·`JobStatus.run_id`), [B](../12-appendix/design-proposals/proposal-B-retrieval-quality-first.md)(`QueryRequest.mode`, `item_kind` 통합 제안), [C](../12-appendix/design-proposals/proposal-C-simplicity-and-extensibility-first.md)(`EmbeddedChunkSet.mode`, `ulid_from_hash`)
- [계약 개요](../03-contracts/00-contract-overview.md) — §5 `$defs` 인벤토리·인라인 열거 `{Type}.{path}`, §6 명명 규약 요약·원시 형식 `$defs`
- 관련 ADR(바이블 §3.3 번호·slug): [ADR-0003 오케스트레이터 중립 파이프라인](./0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md), [ADR-0004 결정적 chunk_id·record_id와 ULID 예외](./0004-deterministic-chunk-id-scoped-record-id-and-ulid-exception.md), [ADR-0017 이벤트 전달](./0017-event-delivery-outbox-cloudevents-no-broker.md), [ADR-0018 API 규약](./0018-api-rest-sse-mcp-no-grpc-rfc9457.md), [ADR-0022 관측성 규약](./0022-observability-genai-semconv-pin-and-license-boundary.md), [ADR-0023 평가 하네스](./0023-evaluation-qrels-answer-spans-and-linear-ndcg.md), [ADR-0026 IndexCommit 세대 사가](./0026-index-commit-generation-saga-and-ledger.md), [ADR-0027 SecurityContext·강제 지점](./0027-security-context-injection-and-acl-enforcement-points.md), [ADR-0028 테넌트 격리 등급](./0028-tenant-isolation-tiering-policy.md), [ADR-0030 단일 좌표계와 점수 원장](./0030-single-coordinate-system-and-score-ledger.md), [ADR-0031 프로파일 스키마](./0031-profile-schema-extends-and-quality-gates.md), [ADR-0032 플러그인 SDK](./0032-plugin-sdk-stage-protocol-and-conformance-kit.md), [ADR-0037 산출물 캐시 스코프](./0037-artifact-cache-scope-and-stage-key-composition.md)
- 이 결정을 전제로 하는 설계 문서(문서 맵): [스키마 버저닝과 호환성](../03-contracts/14-schema-versioning-and-compatibility.md), [오류 모델](../03-contracts/13-error-model.md), [잡·이벤트·상태](../03-contracts/12-jobs-events-and-status.md), [API 설계 지침](../05-api/01-api-design-guidelines.md), [웹훅과 이벤트](../05-api/07-webhooks-and-events.md), [관측성](../09-operations/03-observability.md), [설정 레퍼런스](../09-operations/02-configuration-reference.md), [코딩 표준](../10-development/03-coding-standards.md), [플러그인 개발 가이드](../10-development/06-plugin-development-guide.md)
