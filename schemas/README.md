# JSON Schema 인덱스

생성: 2026-09-23 · 도구: `tools/phase5/gen-schemas-readme.mjs`(기계 생성, 수동 편집 금지). 정본 규칙은 [계약 개요](../docs/03-contracts/00-contract-overview.md)와 [설계 바이블 §5.1](../docs/02-architecture/00-design-bible.md)이다.

- 스키마 표준: JSON Schema 2020-12. `$id`는 `urn:rag:schema:<kebab>:<major>`. 공용 타입·열거는 `common-types.schema.json#/$defs/<Type>`로 참조한다.
- 검증: `node tools/validate-contracts.mjs --root <repo>` (문법·`$ref`·열거 ↔ 바이블 §5.7·예시 ↔ 스키마·문서 구조).
- 변경 절차: 바이블 §1.2(필드 추가·열거값 추가 = minor, 제거·의미 변경 = major → ADR).

| 파일 | `$id` | title | `$defs` | 소유 계약 문서 | 바이블 §5.1 |
|---|---|---|---:|---|---|
| candidate-set.schema.json | urn:rag:schema:candidate-set:1 | CandidateSet | 5 | 00-contract-overview.md, 10-candidate-set-and-ranked-set.md | 등재 |
| capabilities.schema.json | urn:rag:schema:capabilities:1 | Capabilities | 0 | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md | 등재 |
| chunk-set.schema.json | urn:rag:schema:chunk-set:1 | ChunkSet | 3 | 00-contract-overview.md, 05-chunk-set.md, 06-enriched-chunk-set.md, 07-embedded-chunk-set-and-index-record.md, 08-index-commit.md | 등재 |
| cloud-event-envelope.schema.json | urn:rag:schema:cloud-event-envelope:1 | CloudEventEnvelope | 25 | 00-contract-overview.md, 12-jobs-events-and-status.md | 등재 |
| collection-spec.schema.json | urn:rag:schema:collection-spec:1 | CollectionSpec | 6 | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md | 등재 |
| common-types.schema.json | urn:rag:schema:common-types:1 | CommonTypes | 152 | 00-contract-overview.md, 01-ingest-request.md, 02-source-document.md, 03-parsed-document.md, 04-normalized-document.md, 05-chunk-set.md, 06-enriched-chunk-set.md, 07-embedded-chunk-set-and-index-record.md, 08-index-commit.md, 09-query-request-and-query-plan.md, 10-candidate-set-and-ranked-set.md, 11-context-pack.md, 13-error-model.md, 14-schema-versioning-and-compatibility.md, 15-collection-profile-and-policy-contracts.md, 16-eval-feedback-and-sidecar-contracts.md | 등재 |
| context-pack.schema.json | urn:rag:schema:context-pack:1 | ContextPack | 19 | 00-contract-overview.md, 11-context-pack.md | 등재 |
| convert-request.schema.json | urn:rag:schema:convert-request:1 | ConvertRequest | 0 | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md | 등재 |
| convert-response.schema.json | urn:rag:schema:convert-response:1 | ConvertResponse | 0 | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md | 등재 |
| egress-policy.schema.json | urn:rag:schema:egress-policy:1 | EgressPolicy | 0 | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md | 등재 |
| embedded-chunk-set.schema.json | urn:rag:schema:embedded-chunk-set:1 | EmbeddedChunkSet | 5 | 00-contract-overview.md, 07-embedded-chunk-set-and-index-record.md, 08-index-commit.md | 등재 |
| enriched-chunk-set.schema.json | urn:rag:schema:enriched-chunk-set:1 | EnrichedChunkSet | 3 | 00-contract-overview.md, 06-enriched-chunk-set.md | 등재 |
| eval-dataset.schema.json | urn:rag:schema:eval-dataset:1 | EvalDataset | 4 | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md | 등재 |
| eval-report.schema.json | urn:rag:schema:eval-report:1 | EvalReport | 6 | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md | 등재 |
| eval-run.schema.json | urn:rag:schema:eval-run:1 | EvalRun | 2 | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md | 등재 |
| feedback-event.schema.json | urn:rag:schema:feedback-event:1 | FeedbackEvent | 0 | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md | 등재 |
| index-commit.schema.json | urn:rag:schema:index-commit:1 | IndexCommit | 5 | 00-contract-overview.md, 08-index-commit.md | 등재 |
| index-record.schema.json | urn:rag:schema:index-record:1 | IndexRecord | 3 | 00-contract-overview.md, 07-embedded-chunk-set-and-index-record.md | 등재 |
| ingest-request.schema.json | urn:rag:schema:ingest-request:1 | IngestRequest | 9 | 00-contract-overview.md, 01-ingest-request.md | 등재 |
| job-status.schema.json | urn:rag:schema:job-status:1 | JobStatus | 4 | 00-contract-overview.md, 12-jobs-events-and-status.md | 등재 |
| normalized-document.schema.json | urn:rag:schema:normalized-document:1 | NormalizedDocument | 13 | 00-contract-overview.md, 04-normalized-document.md | 등재 |
| parsed-document.schema.json | urn:rag:schema:parsed-document:1 | ParsedDocument | 10 | 00-contract-overview.md, 03-parsed-document.md | 등재 |
| plugin-meta.schema.json | urn:rag:schema:plugin-meta:1 | PluginMeta | 2 | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md | 등재 |
| problem-details.schema.json | urn:rag:schema:problem-details:1 | ProblemDetails | 0 | 00-contract-overview.md, 13-error-model.md, 14-schema-versioning-and-compatibility.md | 등재 |
| profile.schema.json | urn:rag:schema:profile:1 | Profile | 49 | 00-contract-overview.md, 14-schema-versioning-and-compatibility.md, 15-collection-profile-and-policy-contracts.md | 등재 |
| query-plan.schema.json | urn:rag:schema:query-plan:1 | QueryPlan | 16 | 00-contract-overview.md, 09-query-request-and-query-plan.md | 등재 |
| query-request.schema.json | urn:rag:schema:query-request:1 | QueryRequest | 5 | 00-contract-overview.md, 09-query-request-and-query-plan.md | 등재 |
| ranked-set.schema.json | urn:rag:schema:ranked-set:1 | RankedSet | 14 | 00-contract-overview.md, 10-candidate-set-and-ranked-set.md | 등재 |
| rendered-context.schema.json | urn:rag:schema:rendered-context:1 | RenderedContext | 1 | 00-contract-overview.md, 11-context-pack.md | 등재 |
| schema-diff-report.schema.json | urn:rag:schema:schema-diff-report:1 | SchemaDiffReport | 6 | 14-schema-versioning-and-compatibility.md, 15-collection-profile-and-policy-contracts.md | 등재 |
| source-document.schema.json | urn:rag:schema:source-document:1 | SourceDocument | 6 | 00-contract-overview.md, 02-source-document.md, 08-index-commit.md | 등재 |
| stage-error.schema.json | urn:rag:schema:stage-error:1 | StageError | 0 | 00-contract-overview.md, 13-error-model.md, 14-schema-versioning-and-compatibility.md | 등재 |
| stage-policy.schema.json | urn:rag:schema:stage-policy:1 | StagePolicy | 0 | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md | 등재 |
| tiering-policy.schema.json | urn:rag:schema:tiering-policy:1 | TieringPolicy | 0 | 00-contract-overview.md, 15-collection-profile-and-policy-contracts.md | 등재 |
| user-dict-entry.schema.json | urn:rag:schema:user-dict-entry:1 | UserDictEntry | 1 | 00-contract-overview.md, 16-eval-feedback-and-sidecar-contracts.md | 등재 |

합계 35개(바이블 §5.1 등재 35).
