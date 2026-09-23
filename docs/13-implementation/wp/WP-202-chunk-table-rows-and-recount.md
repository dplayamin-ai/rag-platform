---
title: "WP-202 chunk-table-rows-and-recount"
status: done
owner: implementation
---

# WP-202 chunk-table-rows-and-recount (F2-02)

## 목표

`chunk` 스테이지가 표(table) 블록을 처리할 때 쓰는 **표 청킹 하위 모듈**(`table_rows.py`, 04-pipelines/10
§4 판정 흐름·규칙·직렬화 옵션의 축소 구현)과, 임베더 교체로 `token_counts` 키가 누락됐을 때 **재청킹 없이
토큰 수만 재계산**하는 `recount` 스테이지(바이블 §3.2 O-09, ADR-0019)를 구현한다. `table_rows.py`는
`structure_aware` 청커(별도 WP, 아직 미구현)가 표 블록마다 호출할 순수 함수 모듈이며, 표 블록 판정
(role=layout 강등, 중첩 표 분리)과 `NormalizedDocument.table_cell_views` vs `TableData.cells[].text`
선택은 호출자 책임으로 남긴다(아래 불변식·open issue 참조). `recount`는 `Stage[ChunkSet, ChunkSet]` 5멤버
구현이다.

## 파일

- `src/rag_platform/adapters/chunk/table_rows.py` — `TableChunkContext`(공유 메타데이터),
  `build_table_chunks()`(판정 흐름 + 그룹화 + 조립), 직렬화 헬퍼 4종, `TableChunkResult`.
- `src/rag_platform/adapters/chunk/recount.py` — `RecountConfig`(config_schema), `RecountStage`(Stage
  5멤버).
- `tests/adapters/chunk/test_table_rows.py` — 두 모듈의 단위 테스트(대상 테스트 파일이 이것 하나로
  지정됐으므로 `recount` 테스트도 이 파일에 포함).

## 시그니처

```python
# table_rows.py
@dataclass(frozen=True)
class TableChunkContext:
    table_block_id: str          # Hex32
    doc_version: str              # Hex64
    chunker_config_hash: str      # Hex64
    heading_path: tuple[str, ...]
    lang: str
    text_source: ct.BlockSource
    ocr_confidence_min: float | None
    context_prefix: ct.ContextPrefix
    element_path: str
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None

@dataclass(frozen=True)
class TableChunkResult:
    chunks: list[ct.Chunk]
    warnings: list[ct.Warning]
    applied_table_row_group_tokens: int

def build_table_chunks(
    table: ct.TableData,
    ctx: TableChunkContext,
    *,
    token_counters: Sequence[TokenCounter],
    cell_texts: Mapping[tuple[int, int], tuple[str, str]] | None = None,
    text_format: ct.TableSerialization = ct.TableSerialization.markdown,
    table_row_group_tokens: int = 256,
    parent_max_tokens: int = 2048,
    section_parent_chunk_id: str | None = None,
    ordinal_offset: int = 0,
    max_parts: int | None = None,
) -> TableChunkResult: ...

# recount.py
class RecountConfig(BaseModel):
    tokenizer_id: str  # pattern ^(hf|tiktoken|anthropic|gemini):\S+$

class RecountStage:
    plugin_id = "recount.token_counter"
    config_schema = RecountConfig
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: ChunkSet, ctx: Any) -> ChunkSet: ...
```

## 입출력 계약 발췌 (철자 정본)

- `contracts/chunk_set.py`: `ChunkSet{schema_version, schema_type="ChunkSet", tenant_id,
  collection_id, producer, quality, warnings, created_at, lineage_refs, chunk_set_id, document_id,
  doc_version, normalized_ref, document_hash, chunker_id, chunker_config_hash,
  primary_tokenizer_id, secondary_tokenizer_ids, genre_route, analyzer_id, dictionary_hash,
  language, pii_policy_applied, stats, token_budgets?, chunks[]}`. `LineageRefs{source, parsed,
  normalized, chunk_set?, enriched?, embedded?}` — recount 출력은 입력 그대로(불변식, 이 WP가 지킨다).
- `common_types.Chunk{chunk_id, span, item_kind, level, parent_chunk_id, child_chunk_ids?, ordinal,
  text, lexical_text, heading_path, numbering_path?, block_refs[], sentence_spans[], token_counts,
  lang, table_ref?, window?, context_prefix, tree_level?, page_image_ref?, text_source,
  ocr_confidence_min, content_hash}`. `chunk_id = H("chunk", doc_version, chunker_config_hash,
  str(level), span)`(`sdk.hashing.chunk_id`), `span = "{blk}:{start}-{blk}:{end}"`(hex32 블록 ID),
  `content_hash = blake3_hex(text)`.
- `common_types.TableRef{table_block_id, header_row_indices[], row_range[2], col_range[2],
  serialization: enum(TableSerialization=html|markdown|triplet|row_json), html_ref}`.
- `common_types.TableData{n_rows, n_cols, cells: TableCell[], header_row_indices[],
  header_inferred, role: enum(TableRole), quality, html_ref}`; `TableCell{row, col, row_span,
  col_span, text, is_header, header_kind: enum(column|row|section|none), provenance?,
  nested_table_block_id?}` — 앵커 셀만(병합 셀은 앵커 1개), `row_span/col_span ≥ 1`.
  `TableCell.text`는 이미 중첩 표 자리에 `[table:{block_id}]` placeholder를 포함한다.
- `common_types.TokenCounts1 = dict[{hf|tiktoken|anthropic|gemini}:\S+, int]`(`min_length=1`).
- `common_types.ItemKind ∈ {..., table, table_part, parent, ...}`; `ChunkLevel ∈ {0,1,2}`
  (`table`/`table_part` = 0, table 부모 = 1).
- `ErrorCodeCatalog.chunk_block_oversized = "chunk.block_oversized"`,
  `.chunk_count_exceeded = "chunk.count_exceeded"`, `.chunk_tokenizer_missing =
  "chunk.tokenizer_missing"`(재시도 열: block_oversized 경고/비스테이지실패, count_exceeded
  비재시도, tokenizer_missing 비재시도 — `sdk/stage.py CODE_CLASSIFICATION`).
- `sdk.ports.TokenCounter{tokenizer_id: str, count(text) -> int}`; `sdk.stage.Stage`(5멤버),
  `StageError(code, *, stage, plugin_id, detail)`(코드는 `{stage}.{reason}` 철자만).
- `sdk.hashing.{chunk_id, blake3_hex, hash_of}`.

## 04-pipelines/10 §4 규칙 요약(구현 대상)

- 작은 표: 헤더행 + 전체 데이터행 markdown이 `table_row_group_tokens`(256) 이하 → 단일 리프
  `item_kind=table`, `row_range=[first_data_row, n_rows)`, `col_range=[0, n_cols)`.
- 큰 표: 데이터 행을 문서 순 greedy로 묶되 그룹(헤더 포함)이 256 초과하지 않게. 조각 `item_kind=
  table_part`, `row_range`는 데이터 행만, 헤더 행은 모든 조각 `text`·`lexical_text` 앞에 반복.
- 병합 셀: 그룹 경계가 `row_span`을 가르면 뒤로 민다(예산 초과해도 경고만 —
  `chunk.block_oversized` 재사용, §5.7에 전용 코드 없음).
- 한 행 자체가 예산 초과: 그 행 하나가 그룹 → `chunk.block_oversized`.
- 열 분할 없음(`col_range=[0, n_cols)` 고정).
- 헤더 없는 표: markdown 헤더 행은 빈 칸(`""`), triplet 열 이름은 `"열{j}"`(1-based).
- 행 헤더(`header_kind=row`, 셀 단위): triplet은 `"{행 헤더} · {열 헤더}: {셀}"`, 반복 대상 아님.
- 표 부모(level 1): 큰 표에서 전체 표 markdown 직렬화를 하나의 level=1 `parent` 청크로 만들고
  `child_chunk_ids`에 모든 `table_part` chunk_id를 담는다(§4.4 결정 수용).
- `sentence_spans`: 렌더된 `text`의 헤더행·데이터행(구분선 제외) 줄 범위.
- 세트 상한 근접 시 `table_row_group_tokens`를 2배씩 늘려 재시도(`max_parts` 초과 시), 이 WP의
  `leaf_max_tokens` 상한(512)까지도 넘으면 `chunk.count_exceeded`(비재시도).

## 불변식·금지

- `adapters`는 `storage`/`security`를 import하지 않는다(`sdk`/`contracts`만).
- `table_rows.py`는 순수 함수 모듈이다 — `ctx.now()`/난수/IO 없음; 시간이 필요한 필드
  (`created_at`)는 `ChunkSet` 조립 단계(별도 WP, structure_aware) 몫이라 이 모듈은 다루지 않는다.
- `chunk_id`/`content_hash`는 반드시 `sdk.hashing`을 통해서만 계산한다(직접 `blake3` import 금지 —
  ADR-0004 "단일 구현 린트").
- `StageError` 코드는 §5.7 철자만.
- `recount`는 재청킹하지 않는다: `chunks[].span`/`chunk_id`/`block_refs`/`item_kind`/`level`/
  `parent_chunk_id`는 그대로, `token_counts`만 갱신. `lineage_refs`·`chunk_set_id`·`chunker_id`·
  `chunker_config_hash`·`token_budgets`도 그대로(재청킹이 아니므로 변경 근거 없음).
- `recount`는 `ctx.token_counter.tokenizer_id`가 `config.tokenizer_id`와 다르면 실행하지 않고
  `chunk.tokenizer_missing`을 던진다(셸이 잘못된 카운터를 배선한 방어적 검증).

## 단계

1. **`table_rows.py` 판정**: `table.cells`로부터 앵커 셀 그리드를 구성(anchor 위치에 `cell_texts`
   오버레이 또는 `cell.text` 폴백 → display/lexical 텍스트), `header_row_indices`로 헤더/데이터 행
   분리, 전체 markdown 렌더 토큰 수로 작은/큰 표 판정(초기 `table_row_group_tokens`).
2. **큰 표 그룹화**: 데이터 행 시퀀스에 대해 `row_span` 기반 "분할 금지 경계" 배열을 먼저 계산한 뒤,
   그리디 확장(`fits(start,end) or blocked(end)`)으로 `table_row_group_tokens` 그룹을 만든다. 그룹이
   예산을 넘으면(단일 행이거나 병합 강제) `chunk.block_oversized` 경고를 남긴다. `max_parts`가 주어지고
   그룹 수가 넘으면 `table_row_group_tokens`를 2배로 늘려 1단계부터 재시도, `leaf_max_tokens`까지
   늘려도 넘으면 `chunk.count_exceeded`.
3. **직렬화**: `text_format`(기본 markdown)으로 `text`, 항상 triplet으로 `lexical_text`(header_kind
   유추는 `TableCell.header_kind == row`인 셀 존재 여부로 판정), 각각 줄 단위 오프셋을 반환해
   `sentence_spans`를 만든다.
4. **Chunk 조립**: 작은 표 → 단일 `Chunk(item_kind=table, level=0, parent_chunk_id=
   section_parent_chunk_id, ordinal=ordinal_offset)`. 큰 표 → `table_part` 리프 N개(level=0,
   parent_chunk_id=표 부모 chunk_id, ordinal 0..N-1) + 표 부모 1개(level=1, item_kind=parent,
   parent_chunk_id=None, child_chunk_ids=리프 chunk_id 목록, ordinal=ordinal_offset). `chunk_id`는
   `sdk.hashing.chunk_id(doc_version, chunker_config_hash, level, span)`, `span`은 `table_block_id`
   자기 참조(원문 표 전체를 가리키는 근사 좌표 — 아래 open issue).
5. **`recount.py`**: `ctx.token_counter` 검증 → 모든 `chunk.text`를 재계산해 `token_counts`에 대상
   `tokenizer_id` 키를 추가/갱신 → `secondary_tokenizer_ids`에 없으면 추가 → `producer`/`created_at`만
   갱신한 `ChunkSet` 반환.

## 테스트(파일·케이스)

`tests/adapters/chunk/test_table_rows.py`:
- 직렬화 헬퍼: markdown 이스케이프(`|`, 개행), 헤더 없는 표의 `열{j}` triplet, row-header triplet.
- 작은 표(헤더 1 + 데이터 2, 합계 ≤256토큰) → 단일 `table` 리프, `row_range=[1,3)`.
- 큰 표(합계 > 256토큰): 그룹 2개 이상, 각 조각에 헤더 반복, `table_part` + 표 부모(`parent`) 1개,
  `child_chunk_ids` 일치, `row_range`가 헤더 행 인덱스를 포함하지 않음.
- 병합 셀(`row_span=2`)이 그리디 경계와 겹치는 경우 그룹이 합쳐지고 `chunk.block_oversized` 경고 발생.
- 한 행 단독 초과 → 그 행이 단독 그룹 + 경고.
- `max_parts` escalation: 작은 `max_parts`를 줘서 `table_row_group_tokens`가 2배로 늘어나
  `applied_table_row_group_tokens`에 반영되는지; `leaf_max_tokens`까지 늘려도 안 되면
  `chunk.count_exceeded` `StageError`.
- `chunk_id`/`content_hash` 결정성(같은 입력 재실행 시 동일 값).
- `recount`: 정상 케이스(새 tokenizer_id 추가, 기존 값 보존, `secondary_tokenizer_ids` 갱신,
  `lineage_refs`/`chunk_set_id`/`chunks[].span` 불변), `tokenizer_id` 불일치 시 `StageError
  chunk.tokenizer_missing`.

## 완료 기준

`uv run pytest -q tests/adapters/chunk/test_table_rows.py` 전부 통과(최대 3회 재시도),
`uv run ruff check src/rag_platform/adapters/chunk/table_rows.py
src/rag_platform/adapters/chunk/recount.py tests/adapters/chunk/test_table_rows.py` 통과. mypy는
배치 검증자가 별도 실행.

## 검증 계층·DEFERRED

1층(여기서 검증) — 순수 함수·인메모리 페이크 토크나이저만 사용, 외부 자원 없음.
`needs_docker`/`needs_model`/`needs_gpu`/`needs_network` 해당 없음.

- DEFERRED: 표 전체(표 부모) 직렬화가 `parent_max_tokens`(2048)를 넘는 극단적 큰 표를 여러 "run"으로
  나누는 것(04-pipelines/10 §4.1 "표 전체 > 2048이면 표 부모도 run 분할")은 구현하지 않았다 — 이 WP는
  표 부모를 항상 1개만 만들고, 2048을 넘으면 `chunk.block_oversized` 경고만 남긴다(드문 경우이고
  2단계 run 분할은 상당한 추가 복잡도라 별도 WP로 이월). 실 사용 시 재분할이 필요하면 이 함수를
  재귀 호출하도록 확장한다.
- DEFERRED: 열 분할(`col_range` 부분 범위) — 바이블·04 모두 "플러그인 옵션"이라 기본 청커 범위 밖
  (04-pipelines/10 미해결 이슈 5와 동일 이월).
- DEFERRED: 중첩 표(`nested_table_block_id`) 자체를 별도 표로 청킹하는 재귀 호출 — 호출자
  (structure_aware, 미구현)가 중첩 표마다 `build_table_chunks`를 별도로 호출해야 한다는 계약만
  이 문서에 명시했다. `TableCell.text`의 `[table:{block_id}]` placeholder는 그대로 통과시킨다.
- DEFERRED: `NormalizedDocument.table_cell_views` vs `TableData.cells[].text`(`policy_applied=keep`)
  선택 로직 — `cell_texts` 오버레이 매핑을 호출자가 채우는 계약으로 대체했다(읽기 예산 밖 계약이라
  이 WP에서 `normalized_document.py`를 읽지 않음, open issue 참조).
- DEFERRED: `Chunk.block_refs`의 정확한 원문 `char_start/char_end`(표는 `serialization`으로
  재구성되므로 불변식 (1)이 완화되지만, `original_char_*`를 `NormalizedBlock.offset_map`으로 사상하는
  일반 규칙은 이 WP 범위 밖) — 표 블록 전체를 가리키는 근사 `BlockRef`(문자 오프셋 0..len(text))
  하나만 붙인다.

## 결과: 통과 16 / xfail 0 / DEFERRED 4
