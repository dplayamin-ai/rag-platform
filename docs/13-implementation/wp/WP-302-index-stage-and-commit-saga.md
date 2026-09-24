---
title: "WP-302 index-stage-and-commit-saga"
status: active
owner: implementation
version: 1.0.0
last_updated: 2026-09-23
implementation_status: done
depends_on: ["../README.md", "../../12-appendix/10-implementation-design-gaps.md"]
---
# WP-302 index-stage-and-commit-saga (F3-02)

## 목표

`index` 스테이지(바이블 §4.2 `index` 행, ADR-0032 5멤버)를 `lite`(Qdrant 단독) 범위로 구현한다:
`EmbeddedChunkSet` + `requires_lineage`(`EnrichedChunkSet`, `ChunkSet`, `SourceDocument`) →
`IndexRecord[]` 조립(레코드 필드·`acl_*`·`is_current`·세대 합성 `record_id`/`point_id`) → 단일 백엔드
(`index_backend.qdrant`, 로컬 모드) upsert → `IndexCommit` 세대 사가(9단 `CommitStatus`, 단일 백엔드
경로는 `lexical_written`/`flipping_lexical`을 즉시 통과) → 원장 기록(`ledger.repo.Ledger` 포트 모양,
`InMemoryLedger` 대역) → 실패 시 보상(플립 전 신규 세대 삭제, 플립 후 이전 세대 복원 후 신규 세대
삭제). 재실행 멱등성(같은 입력 → 같은 `record_id`·`commit_hash`)을 테스트로 고정한다.

## 파일

- `src/rag_platform/adapters/index/stage.py` — `IndexLineage`(dataclass), `resolve_lineage(ctx)`,
  `build_index_records(embedded, lineage, dense_vectors, *, commit_id, index_generation, now)`(순수
  함수: `EmbeddedChunkSet.vectors`의 각 `chunk_id`를 EMB·ENR·CS·SRC·IDX에서 조립), `commit_hash_of(...)`,
  `IndexStage`(5멤버 `Stage` 프로토콜 — `requires_lineage=("EnrichedChunkSet","ChunkSet","SourceDocument")`).
- `src/rag_platform/adapters/index/saga.py` — `IndexSaga`(세대 할당 → 레코드 조립 위임 →
  `QdrantIndexBackend.upsert`/`set_current` → 원장 `pending→…→committed` 전이 → 실패 시 `_rollback`
  보상). `Ledger`(`ledger/repo.py`)를 직접 import하지 않는 로컬 대역 모양(`_DocumentState`/
  `_CommitState` 미러 dataclass) — 계층 위반 회피(아래 불변식·open_issues 참조).
- `tests/adapters/index/test_index_commit.py` — 조립·사가·롤백·멱등성 테스트.

## 시그니처

```python
# stage.py
@dataclass(frozen=True)
class IndexLineage:
    chunk_set: ChunkSet
    enriched: EnrichedChunkSet
    source: SourceDocument

def resolve_lineage(ctx: Any, *, plugin_id: str) -> IndexLineage: ...

def build_index_records(
    embedded: EmbeddedChunkSet,
    lineage: IndexLineage,
    dense_vectors: Mapping[str, Sequence[float]],
    *,
    commit_id: str,
    index_generation: int,
    now: datetime,
) -> list[IndexRecord]: ...

def commit_hash_of(records: Sequence[IndexRecord], embedded: EmbeddedChunkSet, *, profile_hash: str) -> str: ...

class IndexStage:
    plugin_id = "index_backend.pipeline"
    requires_lineage = ("EnrichedChunkSet", "ChunkSet", "SourceDocument")
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: EmbeddedChunkSet, ctx: Any) -> IndexCommit: ...

# saga.py
@dataclass
class IndexSaga:
    backend: QdrantIndexBackend
    ledger: Any  # duck-typed subset of ledger.repo.Ledger (get_document/upsert_document/upsert_commit/get_commit)
    plugin_version: str = "0.1.0"

    async def commit(
        self,
        embedded: EmbeddedChunkSet,
        lineage: IndexLineage,
        *,
        dense_vectors: Mapping[str, Sequence[float]],
        embedded_ref: ct.ArtifactRef,
        job_id: str,
        profile_id: str,
        profile_hash: str,
        now: datetime,
        commit_id: str | None = None,
    ) -> IndexCommit: ...
```

## 입출력 계약 발췌 (철자 정본)

- `IndexRecord`(`contracts/index_record.py`): `record_id`(hex64) = `H("record", tenant_id,
  collection_id, document_id, str(index_generation), chunk_id)`; `point_id` =
  `uuid5(NAMESPACE_RAG_CHUNK, record_id)`(`sdk.hashing.record_id`/`point_id_for_record`, 재구현
  금지). 원천 표기: EMB=`EmbeddedChunkSet`, ENR=`EnrichedChunkSet`, CS=`ChunkSet`,
  SRC=`SourceDocument`, IDX=사가 인자. `is_current`는 적재 시 항상 `false`. `text`≤8192 UTF-8
  바이트(초과 시 문장 경계 절단 + `text_truncated=true`, `block_refs`/`sentence_spans` 재계산).
  `acl_allow/acl_deny/acl_visibility/acl_classification/acl_embargo_until/acl_expires_at/acl_hash`
  = `SourceDocument.acl`/`acl_hash` 평탄화(`acl_classification` 부재 시 기본 `internal`).
  `lexical_terms` = `Enrichment.keywords[].term` 정렬·중복 제거. `entity_ids` =
  `Enrichment.entities[].canonical_id`(non-null) 정렬·중복 제거. `chunk_set_blake3` =
  `EmbeddedChunkSet.lineage_refs.chunk_set.blake3`.
- `IndexCommit`(`contracts/index_commit.py`): `status: CommitStatus`(`pending, vector_written,
  lexical_written, flipping_lexical, flipping_vector, committed, rolling_back, rolled_back,
  failed`); `kind: CommitKind`(`upsert, delete`); `previous_commit_id`/`supersedes_commit_ids`/
  `superseded_by`; `commit_hash` = `H("commit", profile_hash, *sorted(f"{chunk_id}:{content_hash}:
  {embed_text_hash}"))`; `backend_results[]{backend_id, backend_version, physical_name, alias,
  upserted, deleted, duration_ms, status: ok|failed|compensated}`; `compensation{reason,
  failed_at_status, deleted_counts, restored_generation, completed_at}`; `artifact_refs`/
  `lineage_refs`(6키: source/parsed/normalized/chunk_set/enriched/embedded).
- ADR-0026/바이블 §11.4: `index_generation` = 문서 잠금 아래 단조 증가 할당(폐기 세대 재사용 금지);
  플립 전(`pending~lexical_written`) 실패 → `delete_by_filter(commit_id)`만; 플립 후
  (`flipping_*`) 실패 → `previous_commit_id` 세대 `is_current=true` 복원 후 신규 세대 삭제 →
  `rolled_back`(`compensation.restored_generation=N`). 04-pipelines/13 §6: 렉시컬 백엔드가 없으면
  `vector_written → lexical_written → flipping_lexical`을 즉시 통과(no-op)로 기록, `backend_results`
  1개.
- `ledger.repo.Ledger`(읽기 전용 인용, import 금지 — 아래 불변식): `DocumentRecord{tenant_id,
  document_id, collection_id, external_id, current_doc_version, current_generation,
  current_commit_id}`, `CommitRecord{tenant_id, commit_id, document_id, index_generation, status}`,
  메서드 `get_document/upsert_document/upsert_commit/get_commit`(모두 `async`).

## 불변식·금지

- import-linter "adapters never import `rag_platform.ledger`"(`pyproject.toml`
  `pipelines-orchestrator-neutral` 계약, `rag_platform.adapters`가 `source_modules`,
  `rag_platform.ledger`가 `forbidden_modules`)를 지킨다 — `saga.py`는 `ledger.repo`를 import하지
  않고, `DocumentRecord`/`CommitRecord`와 같은 모양(같은 필드명·타입)의 로컬 미러 dataclass
  (`_DocumentState`/`_CommitState`)를 정의해 `InMemoryLedger`(속성 기반 dict 키, isinstance 검사
  없음)와 구조적으로만 호환시킨다. `sdk/ports.py`의 `Embedder`/`IndexBackend`가 같은 이유로
  존재하는 것과 같은 회피(그 파일 docstring 참조).
- `record_id`/`point_id` 계산은 `sdk.hashing`만 호출한다(재구현 금지, ADR-0004 "단일 구현").
- `datetime.now(UTC)` 직접 호출 금지 — `now`는 항상 호출자(테스트의 고정 시각, 실제로는
  `ctx.now()`)가 주입한다.
- 어댑터는 `storage`를 모른다 — `EmbeddedChunkSet.vectors_ref`(npz) 실물 로딩은 이 WP 범위 밖이며
  `dense_vectors: Mapping[chunk_id, Sequence[float]]`를 호출자가 이미 역참조해 넘겨준다고 가정한다
  (아래 open_issues: `embed` 스테이지의 `vectors_ref` 실물 직렬화가 아직 없다 — WP-301 DEFERRED와
  같은 공백).
- `IndexRecord.is_current`는 조립 시 항상 `false`(바이블 §11.4 (1)); 플립은 `backend.set_current`가
  한다.
- `record_count`는 리프+level 2 파생물 수만(부모 제외, `embedded.vectors` 키 집합과 1:1).

## 단계

1. `resolve_lineage(ctx)`: `ctx.lineage["ChunkSet"]`/`["EnrichedChunkSet"]`/`["SourceDocument"]`를
   읽어 `IndexLineage`로 감싼다(문자열 키는 `fsspec_httpx.py`의 `ctx.lineage["SourceDocument"]`
   선례와 동일 관례). 없거나 `schema_type` 불일치면 `contract.violation`.
2. `build_index_records`: `embedded.vectors`의 `chunk_id`마다 — `chunk_set.chunks`에서 청크,
   `enriched.enrichments`에서 보강, `dense_vectors`에서 dense 배열을 찾아 `IndexRecord` 발췌를
   조립한다. `text`가 8,192 UTF-8 바이트를 넘으면 문장 경계(마지막에 안 넘는 `sentence_spans`
   항목)에서 절단하고 `block_refs`를 그 경계로 클리핑, `text_truncated=true`.
3. `IndexSaga.commit`: `ledger.get_document`로 `(current_generation, current_commit_id)` 조회 →
   `index_generation = current_generation + 1`(`documents.current_generation` 기준 근사 — 아래
   open_issues) → `commit_id`(없으면 `ULID()`) → `build_index_records` 호출 → `ensure_collection`
   (dense 차원은 첫 레코드에서 추론) → `backend.upsert(...)`(실패 시 `_rollback(failed_at="vector_written")`)
   → `backend.set_current(...)`(단일 백엔드라 `lexical_written`/`flipping_lexical`은 즉시
   `committed` 상태 필드로만 기록, 실패 시 `_rollback(failed_at="flipping_vector")`) → 원장
   `upsert_document`/`upsert_commit(status="committed")` → `IndexCommit` 조립·반환.
4. `_rollback`: 플립 전이면 `backend.delete(scope_filter(..., index_generation=N+1))`만; 플립 후면
   먼저 `backend.set_current(..., index_generation=previous_generation)`로 이전 세대 복원 후 신규
   세대 삭제. 원장 `status="rolled_back"` 기록, `IndexCommit.compensation`·`error` 채움.
5. 같은 `commit_id`로 두 번째 호출 시 사가 인스턴스의 프로세스 내 캐시(`_committed`)에서 이미
   `committed`인 커밋을 그대로 반환(no-op) — 실 원장 재적재 경로(ADR-0026 결과 절)의 축소판(아래
   open_issues).

## 테스트(파일·케이스)

`tests/adapters/index/test_index_commit.py`(자체 구성 `SourceDocument`/`ChunkSet`/
`EnrichedChunkSet`/`EmbeddedChunkSet` 픽스처 — 부모 1 + 리프 2, `tests/contracts/fixtures/
index-record/001.json` 모양을 참고해 필드 철자를 맞춘다):

- `build_index_records`: 리프 2개 → `IndexRecord` 2개(부모 제외); `record_id`/`point_id`가
  `sdk.hashing`과 대조 일치; `acl_*`·`title`·`tags`·`custom`이 `SourceDocument`에서 정확히
  투영; `lexical_terms`/`entity_ids` 정렬·중복 제거; `chunk_set_blake3` =
  `embedded.lineage_refs.chunk_set.blake3`.
- 절단: 8,192바이트를 넘는 합성 `text`로 `text_truncated=true`, 인코딩 길이 ≤ 8192, 마지막
  `block_refs` 항목 `char_end` 클리핑, `original_char_*` 불변.
- `IndexSaga.commit`: 정상 경로 — `committed`, `is_current=true` 레코드가 Qdrant 로컬 모드에서
  조회됨, 원장 `documents.current_generation`이 1 전진, `backend_results` 1건(`status=ok`).
- 재실행 멱등성: 같은 입력으로 두 번 `build_index_records` 호출 → 동일 `record_id`·
  `commit_hash_of(...)`; `IndexSaga.commit`을 같은 `commit_id`로 두 번 호출 → 두 번째는 캐시
  no-op(백엔드 upsert 호출 횟수 불변, 결과 객체는 `is` 동일성 또는 필드 동일).
- 롤백: 백엔드 `upsert`가 실패하도록 페이크로 주입 → `status=rolled_back`,
  `compensation.restored_generation is None`(플립 전); 두 번째 세대에서 `set_current`(플립) 실패를
  주입 → 이전 세대가 다시 `is_current=true`로 복원되고 `compensation.restored_generation=1`.
- `IndexStage.capabilities()`/`fingerprint()`: 스모크(값 존재·결정성).

## 완료 기준

`uv run pytest -q tests/adapters/index/test_index_commit.py` 전부 통과, `uv run ruff check
src/rag_platform/adapters/index/stage.py src/rag_platform/adapters/index/saga.py
tests/adapters/index/test_index_commit.py` 통과. mypy는 배치 검증자가 별도 실행.

## 검증 계층·DEFERRED

1층(여기서 검증) — `QdrantIndexBackend.local()`(qdrant-client 로컬 모드), `InMemoryLedger`. 서버
모드·payload 인덱스 효과는 `test_qdrant_local.py`가 이미 `needs_docker`로 추적 중이라 이 WP는
반복하지 않는다.

- DEFERRED: `embed` 스테이지의 `vectors_ref`(npz) 실물 직렬화·역참조가 없다(WP-301 범위 밖으로
  기록됨) — 이 WP는 `dense_vectors` 매핑을 호출자 인자로 받는 임시 경계를 쓴다. 실제 `ctx`가
  이를 어떻게 노출할지(예 `ctx.artifacts`류 읽기 포트, 또는 `embed` 산출물 자체에 인라인 배치)는
  별도 WP/ADR 결정 필요.
- DEFERRED: OpenSearch 백엔드·렉시컬 플립(`lexical_written`/`flipping_lexical`의 실제 호출)은
  범위 밖(`lite`만); `index_backend.opensearch`가 생기면 `backend_results`가 2건이 되고 플립
  순서(렉시컬→벡터)가 실질화되어야 한다.
- 해소(F3 배치 검증, 2026-09-23): `ledger.repo.Ledger`에 `list_commits(tenant_id, document_id)`를
  추가하고(`testing.doubles.InMemoryLedger`도 구현), `IndexSaga.commit`이 `documents.
  current_generation + 1` 근사 대신 `max(list_commits(...).index_generation, previous_generation) +
  1`로 할당하도록 고쳤다 — 롤백된 세대 번호를 재사용하지 않는다(회귀 테스트
  `test_generation_after_rollback_is_not_reused`). 실 PostgreSQL `Ledger`도 이 메서드를 구현해야
  한다(여전히 `needs_docker` DEFERRED인 부분은 실 구현 자체뿐).
- DEFERRED: `IndexSaga`의 커밋 재실행 무결성은 프로세스 내 캐시(`_committed`)로만 구현했다 — 실제
  재현은 원장 `index_commits.artifact_refs`에서 `EmbeddedChunkSet`(+`requires_lineage`)을 다시
  읽어 같은 사가를 재실행하는 경로(ADR-0026 결과 절)이며, 이는 오케스트레이션/원장 계층이 아직
  없는 이 배치 범위 밖이다.
- DEFERRED: §9 텍스트 절단 규칙은 "마지막 완결 문장 경계 우선" 단순화만 구현했다(다중 바이트 경계
  전수 조건·`text_preview` 절단 규칙의 모든 코너 케이스는 미검증).

## 결과: 통과 13 / xfail 0 / DEFERRED 3 (F3 배치 검증이 세대 할당 근사 1건 해소 + 회귀 테스트 1건 추가)
