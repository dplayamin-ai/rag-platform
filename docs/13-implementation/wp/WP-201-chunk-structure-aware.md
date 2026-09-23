---
title: "WP-201 chunk-structure-aware"
status: done
owner: implementation
---

# WP-201 chunk-structure-aware (F2-01)

## 목표

`chunker.structure_aware` 스테이지(`NormalizedDocument → ChunkSet`, 바이블 §4.2 `chunk` 행)의 축소 범위
구현. 04-pipelines/10 §2(기본 전략 단계 A~G)·§3(부모-자식)·§7.2(파라미터 기본값)만 대상이며, 표 청킹(§4,
`adapters/chunk/table_rows.py`), `genre_rules`(§2.3 장르 경계), 캡션·각주·목록·그림·코드 세분(§2.2·§2.4,
`Block.type` 필요), `ctx.lineage["ParsedDocument"]` 필수 선언(ADR-0020 결정), `flat_text` 폴백 라우팅(§6.3)은
이 WP 범위 밖이며 DEFERRED다. **설계 결정(이 WP):** `NormalizedDocument`만으로 동작한다 —
`NormalizedBlock`에 `type` 필드가 없어 heading 여부는 `heading_tree`의 `block_id` 집합으로만 판정하고, 그
외 비-boilerplate 블록은 모두 `item_kind=text` 리프 후보 1개로 취급한다(단계 C 그룹화는 1블록=1후보로
단순화). `BlockRef.element_path`(`Block.provenance.element_path` 원본)는 `ParsedDocument` 없이 계산할 수
없어 `"/blocks/{doc_order_index}"` 자리표시자를 쓴다(DEFERRED, open_issue).

## 파일

- `src/rag_platform/adapters/chunk/structure_aware.py` — `StructureAwareChunkerConfig`(config_schema),
  `StructureAwareChunkerStage`(Stage 5멤버), 기본 `TokenCounter` 구현(`ApproxCharTokenCounter`·
  tiktoken 있으면 사용하는 팩토리), 문장 경계(kss 있으면 사용·정규식 폴백), heading_path 유도, 초과
  분할(D)·병합(E)·부모 생성(F)·좌표·ID·접두어(G) 순수 함수들.
- `tests/adapters/chunk/test_structure_aware.py` — 단위(오프셋 맵 사상, heading_path 유도, 문장 분할
  폴백, 초과 분할, 병합 트리거, 부모 생성, `chunk_id` 결정성) + `StructureAwareChunkerStage.run()` 통합 2건
  (짧은 문서 1리프, 여러 섹션 부모 생성).

## 시그니처

```python
class StructureAwareChunkerConfig(BaseModel):
    tokenizer: str = "hf:BAAI/bge-m3"
    secondary_tokenizers: list[str] = ["tiktoken:o200k_base"]
    leaf_max_tokens: int = 512
    parent_max_tokens: int = 2048
    merge_min_tokens: int = 64
    prefix_max_tokens: int = 100

class StructureAwareChunkerStage:
    plugin_id = "chunker.structure_aware"
    config_schema = StructureAwareChunkerConfig
    requires_lineage: tuple[str, ...] = ()
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: NormalizedDocument, ctx: Any) -> ChunkSet: ...

def default_token_counter(tokenizer_id: str) -> TokenCounter: ...  # approx char, tiktoken if importable
```

## 입출력 계약 발췌 (철자 정본)

- 입력 `NormalizedDocument{document_id, doc_version, language, genre, analyzer_id, dictionary_hash,
  quality, lineage_refs{source, parsed}, heading_tree[{block_id, level, path}], blocks[]}`;
  `NormalizedBlock{block_id, display_text, lexical_text, offset_map, sentence_spans, lang, boilerplate,
  text_source, confidence}` — `offset_map: list<[disp,orig,len]>`. `NormalizedBlock`에 `type` 없음(구조는
  `ParsedDocument`가 정본, 이 WP 범위 밖).
- 출력 `ChunkSet{schema_version, schema_type, tenant_id, collection_id, producer, quality, warnings,
  created_at, lineage_refs{source,parsed,normalized}, chunk_set_id, document_id, doc_version,
  normalized_ref, document_hash, chunker_id="chunker.structure_aware", chunker_config_hash,
  primary_tokenizer_id, secondary_tokenizer_ids, genre_route, analyzer_id, dictionary_hash, language,
  pii_policy_applied, stats{leaf_count,parent_count,table_part_count=0,summary_count=0,oversized_blocks},
  token_budgets{leaf_max_tokens,parent_max_tokens,merge_min_tokens,table_row_group_tokens}, chunks[]}`.
- `Chunk{chunk_id, span, item_kind, level, parent_chunk_id, child_chunk_ids, ordinal, text, lexical_text,
  heading_path, block_refs, sentence_spans, token_counts, lang, context_prefix{deterministic,generated=
  null,generated_by=null}, text_source, ocr_confidence_min, content_hash}` — `table_ref`/`window`/
  `tree_level`/`page_image_ref`/`numbering_path` 항상 null(DEFERRED, 표·flat_text 전용).
  `BlockRef{block_id, element_path, char_start, char_end, original_char_start, original_char_end,
  page=null, bbox=null, section_index=null}`.
- 결합식: `chunk_id = H("chunk", doc_version, chunker_config_hash, str(level), span)`(ADR-0004),
  `chunker_config_hash = H("config", canonical_json(config))`, `span =
  "{first_block_id}:{orig_char_start}-{last_block_id}:{orig_char_end}"`, `content_hash =
  blake3_hex(utf8(text))`. `ItemKind.text`(level 0)·`ItemKind.parent`(level 1). `BlockSource` 우선순위
  `text_layer > converted > vlm > ocr`(최저 등급 채택).

## 불변식·금지

- (1) `block_refs`의 `char_start/char_end`(청크 로컬) 합집합이 `text`를 재구성한다 — 병합·부모 생성 시
  U+000A로 이어붙이며 각 조각 오프셋을 누적 이동한다.
- (2) `level=0` 청크는 `token_counts[primary_tokenizer_id] ≤ leaf_max_tokens`(초과 시 문장/정규식 경계로
  분할, 오버랩 0).
- (3) `context_prefix.deterministic`은 `text`와 분리 저장(본문에 넣지 않음); 100토큰 초과 시 heading_path
  얕은 단계부터 제거 → 그래도 넘으면 title 코드포인트 절단.
- (4) `parent_chunk_id`가 있는 리프의 부모는 `chunks[]`에 존재하고 `child_chunk_ids`가 그 리프를 포함한다.
  자식이 1개뿐인 묶음은 부모를 만들지 않는다(`parent_chunk_id=null`).
- (5) 부모(`level=1`)는 절대 임베딩되지 않는다(이 스테이지가 보장할 것은 아니지만 `item_kind=parent`로
  하류가 판별 가능해야 한다).
- `3-텍스트 규칙`: `text`(접두어 없음)·`lexical_text`(같은 좌표, `display_text`/`lexical_text` 슬라이스 —
  NFKC 폴딩으로 인한 길이 차이는 무시, DEFERRED)·`embed_text`는 하류가 `context_prefix + text`로 조립(이
  스테이지는 조립하지 않는다, ADR-0029).
- `StageError` 코드는 §5.7 철자만(`chunk.tokenizer_missing`, `chunk.block_oversized`는 경고이지 예외 아님).
  이 WP는 `contract.violation`(입력 아티팩트 참조 포트 부재, WP-106 `_resolve_parsed_ref`와 동일 관례)만
  던진다.
- `adapters`는 `storage`/`security`/`plugins`/`orchestration`을 import하지 않는다 — `sdk`/`contracts`만.
  Stage 5멤버(`plugin_id`/`config_schema`/`capabilities()`/`fingerprint()`/`run()`) 외 확장 금지.

## 단계

1. `heading_tree`의 `block_id` 집합과 문서 순서 포인터 walk로 각 비-heading 블록의 `heading_path`를
   유도(04-pipelines/10 §2.3 식: 가장 가까운 선행 heading의 `path`, 제목 `path[0]` 제거 규칙).
2. `boilerplate=true`·heading·빈 `display_text` 블록 제외, 나머지 1블록=1리프 후보(단계 A·C 축소).
3. `token_counts[primary] > leaf_max_tokens`인 후보는 문장 경계(kss 있으면 사용, 없으면 정규식 폴백)로
   그리디 누적 분할, 문장 하나가 여전히 넘으면 공백 경계 그리디(semchunk 미배선 대체, DEFERRED) → 문자
   윈도우 최종 폴백. 분할마다 `chunk.block_oversized` 경고 + `stats.oversized_blocks` 증가(단계 D).
4. 같은 `heading_path`·같은 우세 언어인 인접 후보를 `merge_min_tokens` 트리거로 병합(`leaf_max_tokens`
   상한), 섹션 끝 잔여 소단위는 역방향 병합 1회 시도(단계 E).
5. 같은 `heading_path`의 연속 리프를 묶어 자식 ≥ 2일 때만 부모 생성, `parent_max_tokens` 초과 시 순차
   분할(단계 F). 부모 `text`는 자식 `text`를 ordinal 순 U+000A 결합.
6. 좌표·ID: `offset_map`으로 원문 좌표 사상, `span`·`chunk_id`·`content_hash` 계산, `context_prefix`
   조립(단계 G). 형제(같은 `level`·`parent_chunk_id`) 단위로 `ordinal` 0-based 부여.
7. `ChunkSet` 조립(`stats`·`token_budgets`·`lineage_refs`·`normalized_ref` 포함) 후 반환.

## 테스트(파일·케이스)

`tests/adapters/chunk/test_structure_aware.py`:
- `_to_original`(오프셋 맵 사상): identity·삭제 마커·치환 세그먼트 3종.
- `_assign_heading_paths`: 제목 없음/있음, 레벨 생략, 첫 heading 이전 본문(`[]`).
- 문장 분할 폴백(정규식): 종결 부호·개행 경계 2종.
- 초과 분할: `leaf_max_tokens`를 넘는 긴 블록이 문장 경계에서 나뉘고 경고·`oversized_blocks`가 붙는지.
- 병합: `merge_min_tokens` 미만 인접 리프가 합쳐지고 상한을 넘기지 않는지.
- 부모 생성: 같은 섹션 리프 ≥ 2개면 부모가 생기고 자식 1개면 부모가 없는지, `parent_max_tokens` 분할.
- `StructureAwareChunkerStage.run()` 통합 2건: (a) 짧은 문서(리프 1개, 부모 없음), (b) heading 2개 섹션 →
  부모 2개·`chunk_id` 결정성(같은 입력 재실행 시 동일 `chunk_id` 집합) 검증.

## 완료 기준

`uv run pytest -q tests/adapters/chunk/test_structure_aware.py` 전부 통과, `uv run ruff check
src/rag_platform/adapters/chunk/structure_aware.py` 통과. mypy는 배치 검증자가 별도 실행.

## 검증 계층·DEFERRED

1층(여기서 검증). `needs_docker`/`needs_model`/`needs_gpu`/`needs_network` 해당 없음(순수 함수, tiktoken·
kss는 optional import + try/except 폴백이라 미설치 환경에서도 정규식/근사 경로로 통과).

- DEFERRED: 표 청킹(§4, `table_rows.py`)·`genre_rules`(§2.3 조/항 경계)·캡션·각주·목록·그림·코드 세분·
  `flat_text` 폴백 라우팅(§6.3)·`ctx.lineage["ParsedDocument"]` 배선 — 모두 `Block.type`/`TableData`가
  필요해 이 WP 범위 밖. 현재는 모든 비-heading 본문 블록이 `item_kind=text`다.
- DEFERRED: `BlockRef.element_path`는 `"/blocks/{idx}"` 자리표시자(`Block.provenance.element_path` 필요).
- DEFERRED: semchunk 3.2.5(ADR-0020 잠금)를 아직 추가하지 않아 D3 대체로 공백 경계 그리디 폴백을 쓴다.
- DEFERRED: PII 구간 스냅(`snap_to_pii_spans`) — 현재 상류(`normalize`, WP-106)가 `pii_spans=[]`만 내므로
  no-op이지만, PII가 채워지면 이 스테이지도 갱신해야 한다.
- open_issue(공용 파일 제안, 손대지 않음): `sdk/context.py`의 `StageContext`에 (a) 스테이지 자신의 입력
  `ArtifactRef`를 읽는 표준 포트가 없다(WP-106이 이미 지적한 공백 — 이 WP는 `ctx.normalized_ref`를 같은
  방식으로 방어적 처리), (b) `ctx.token_counters`(복수, secondary tokenizer용) 포트가 없어(04-pipelines/10
  §2.10 의사코드는 이를 전제) 이 WP는 `secondary_tokenizers`마다 독자적으로 기본 카운터를 만든다.
- open_issue: ADR-0019 준수 확인 체크리스트 (a)는 "스테이지 코드가 tiktoken을 직접 임포트하지 않는다"고
  하는데, `default_token_counter`(tiktoken 있으면 사용하는 기본 구현)는 이 WP의 파일 제약(구조 인식
  청커·테스트 파일만 생성) 때문에 같은 파일에 있다 — 알고리즘 자체(분할·병합·부모 생성)는 주입된
  `TokenCounter` 객체만 호출하고 tiktoken을 직접 부르지 않지만, 엄밀한 계층 분리를 원하면 이 팩토리를
  `sdk/token_counters.py`(신규)로 옮기는 후속 변경이 필요하다.

## 결과: 통과 19 / xfail 0 / DEFERRED 6
