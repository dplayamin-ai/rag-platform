---
title: "WP-403 후처리와 컨텍스트 패킹"
status: active
version: 0.1.0
---

# WP-403 후처리와 컨텍스트 패킹 (F4-03, postprocess-and-pack)

## 0. 실행 배경(병렬 배치 주의)

F4 배치는 F4-01(planner·filters)·F4-02(channels·fusion·hydrate)·F4-03(본 WP)·F4-04
(render·query 파이프라인)를 **병렬** 에이전트로 실행한다(`WP-404-render-and-query-pipeline.md`
§0). WP-404는 `Postprocessor`/`Packer`를 각각
`(ranked: RankedSet, plan: QueryPlan) -> RankedSet` / `(ranked, plan, security) -> ContextPack`
Protocol로만 선언하고 실 배선은 지연 임포트로 미룬다. 이 WP는 `QueryPlan`/`Profile` 계약을
읽기 예산 밖에 두므로, 각 단계 함수는 `QueryPlan`이 아니라 이 문서가 정의하는 **원시 설정
객체**(dataclass)를 받는다. `QueryPlan → 설정 객체` 변환과 `retrieval/postprocess/__init__.py`·
`retrieval/pack/__init__.py`(플랫폼 셸, 이 WP 파일 목록 밖) 조립은 F4 배치 검증자가 맡는다.

## 1. 목표

바이블 §8.2(후처리 고정 순서)·§9.1~9.2(패커 규칙·`litm_alternating`)·04-pipelines/17
§2~§3(의사코드 정본)에 따라 `RankedSet(reranked) → RankedSet(postprocessed) → ContextPack`
경로의 알고리즘 단계 9개를 구현한다: 후처리 4단계(`relevance_gate`·`dedup`·`mmr`·
`parent_expand`)와 패커 4단계(`acl_recheck`·`budget_cut`·`reorder`·`citation_align`) +
이를 묶는 `packer.pack()`.

## 2. 파일

- `src/rag_platform/retrieval/postprocess/relevance_gate.py` — `StepResult`(공유 dataclass) +
  `apply`.
- `src/rag_platform/retrieval/postprocess/dedup.py` — 완전/근중복/부모-흡수 제거.
- `src/rag_platform/retrieval/postprocess/mmr.py` — 재정렬만(제거 없음).
- `src/rag_platform/retrieval/postprocess/parent_expand.py` — `ChunkTextStore`/`ParentEntry`
  (이 문서 로컬 제안 타입) + small-to-big 병합.
- `src/rag_platform/retrieval/pack/acl_recheck.py`, `budget_cut.py`, `reorder.py`,
  `citation_align.py` — §3.2~§3.5.
- `src/rag_platform/retrieval/pack/packer.py` — 4단계 조립 + `sufficiency`/`content_hash`
  (전용 모듈 `sufficiency.py`·`conflicts.py`가 배치에 없어 이 파일에 인라인).
- `tests/retrieval/test_postprocess_pack.py`.

## 3. 시그니처

```python
# postprocess/relevance_gate.py
@dataclass(frozen=True)
class StepResult:                       # 문서 §2.1 StepResult 제안의 구현
    results: list[RankedResult]; omitted: list[RankedOmittedEntry]
    removed: int; added: int; degraded: list[common_types.DegradedEntry]
    gate: RelevanceGateReport | None = None

def apply(results: Sequence[RankedResult], *, tau: float, retries: int = 0) -> StepResult: ...

# postprocess/dedup.py
def apply(results, *, vectors: Mapping[str, Sequence[float]] | None = None,
          cosine_threshold=0.95, minhash_threshold=0.8, num_perm=128, seed=42,
          analyzer: KoreanAnalyzer | None = None) -> StepResult: ...

# postprocess/mmr.py
def apply(results, vectors: Mapping[str, Sequence[float]] | None, lam: float | None) -> StepResult: ...

# postprocess/parent_expand.py
class ParentTextMiss(Exception): ...
class ChunkTextStore(Protocol):
    def get_many(self, chunk_set_blake3: str, parent_chunk_ids: Sequence[str],
                 security: common_types.SecurityContext) -> Mapping[str, ParentEntry]: ...
@dataclass(frozen=True)
class ParentEntry:                      # 바이블 §13.2 번들 + n_children(제안)
    text: str; heading_path, numbering_path: list[str] | None
    token_counts: Mapping[str, int]; block_refs: list[BlockRef] | None
    sentence_spans: list[SentenceSpan2] | None; text_source: BlockSource | None
    ocr_confidence_min: float | None; page_start, page_end: int | None
    n_children: int | None = None

def apply(results, *, text_store: ChunkTextStore, security, token_counter: TokenCounter,
          ratio_threshold=0.5, max_parent_tokens=2048, max_parent_text_bytes=32768,
          max_context_tokens: int, reserved_answer_tokens: int, budget_guard_ratio=0.8,
          remaining_ms: Callable[[], int] | None = None, min_bundle_ms=15) -> StepResult: ...

# pack/acl_recheck.py
@dataclass(frozen=True)
class RevocationHint: acl_hash: str; allow, deny: Sequence[str]
    visibility: Visibility; classification: Classification
    embargo_until, expires_at: str | None; deleted: bool = False

def apply(candidates: Sequence[RankedResult], security: SecurityContext, *,
          revocation_hints: Mapping[str, RevocationHint] | None = None
          ) -> tuple[list[RankedResult], list[PackOmittedEntry], AclRecheckReport,
                     dict[str, common_types.Acl2]]: ...

# pack/budget_cut.py
@dataclass
class PackedItem:                       # 이 문서 제안 작업 타입(계약 아님)
    result: RankedResult; header: common_types.Header
    tables: list[common_types.Table] | None; figures: list[common_types.Figure1] | None
    acl2: common_types.Acl2 | None = None
    token_count: int = 0; position: int | None = None

@dataclass(frozen=True)
class BudgetCutConfig:
    k_max: int; max_context_tokens: int; reserved_answer_tokens: int
    overflow_policy: Sequence[OverflowPolicy]; table_format_preference: Sequence[TableFormat]
    default_lang: str = "ko"; max_serialized_bytes: int = 512 * 1024

def apply(items: Sequence[RankedResult], cfg: BudgetCutConfig, counter: TokenCounter,
          acl2_by_chunk_id: Mapping[str, common_types.Acl2]
          ) -> tuple[list[PackedItem], list[PackOmittedEntry], list[common_types.Warning]]: ...

# pack/reorder.py
def litm_position(k: int, K: int) -> int: ...   # 바이블 §9.2 정본 공식
def apply(items: Sequence[PackedItem], strategy: OrderingStrategy) -> tuple[list[PackedItem], bool]: ...

# pack/citation_align.py
def apply(items: Sequence[PackedItem], *, as_of: str, include_scores: bool = False,
          confidence_high=0.7, confidence_medium=0.4
          ) -> tuple[list[common_types.ContextItem], list[common_types.Warning]]: ...

# pack/packer.py
@dataclass(frozen=True)
class PackConfig:                       # QueryPlan.pack + security_context 대역(이 문서 제안)
    security: SecurityContext; token_counter: TokenCounter
    budget_cut: BudgetCutConfig; ordering_strategy: OrderingStrategy
    tokenizer: TokenizerSpec; count_method: CountMethod
    calibration_ratio: float | None; safety_margin: float
    render_hints: RenderHints; profile_id: str; profile_hash: str; trace_id: str
    producer: Producer; pack_id: str; explain: bool = False
    revocation_hints: Mapping[str, RevocationHint] | None = None
    risk_flagged: Callable[[RankedResult], bool] | None = None
    total_variant_ids: Sequence[str] = (); lexical_terms: Sequence[str] = ()
    filters_applied: FiltersApplied | None = None
    latency_ms_upstream: Mapping[str, int] | None = None
    index_generations_seen: Sequence[int] = (); route_no_retrieval: bool = False

def pack(ranked: RankedSet, cfg: PackConfig, *, now: datetime) -> ContextPack: ...
```

## 4. 입출력 계약 발췌(정본 철자, 손편집 금지 파일에서 그대로 복사)

- `RankedResult`(common_types): `chunk_id`/`record_id`(Hex64|None)·`collection_id`/
  `document_id`(Ulid)·`final_rank`·`final_score`·`item_kind`(`ItemKind`)·`level`(`ChunkLevel`
  0/1/2)·`parent_chunk_id`·`expanded_from`·`channels_hit`·`variant_ids`·`explain`
  (`list[ExplainCode]`)·`acl`(`Acl1|None`)·`block_refs`·`token_count_primary`·`ordinal`·
  `chunk_set_blake3`·`table_ref`(dict)·`text`.
- `PostprocessStep` = `relevance_gate|dedup|mmr|parent_expand|sentence_window|compress`.
  `PackStep` = `acl_recheck|budget_cut|reorder|citation_align`. `Reason`(ranked_set.py) =
  `below_threshold|duplicate|budget_exceeded|acl_denied|parent_merged|item_kind_excluded|
  risk_flagged|hydrate_missing`. `OmitReason`(common_types, pack용) = 위와 동일 철자.
- `RelevanceGateReport{tau, max_score, passed, retries}`, `RankedOmittedEntry{chunk_id,
  collection_id, document_id, reason, step, related_chunk_id?, explain?}`.
- `ContextPack`(contracts/context_pack): `budget{tokenizer{provider,model,name},
  count_method, calibration_ratio, safety_margin, max_context_tokens, used_tokens,
  reserved_answer_tokens, k_max, overflow_policy[]}`, `ordering{strategy, applied}`,
  `items: list[ContextItem]`(≤20, position 오름차순), `omitted: list[PackOmittedEntry]`,
  `sufficiency{status, coverage, confidence, missing_aspects[], method}`, `stop_signal`,
  `redaction_summary{pii_policy, entity_counts}`, `classification_max`, `render_hints`,
  `diagnostics{dedup_removed, parent_expansions, mmr_lambda, filters_applied, latency_ms,
  index_generations_seen, count_method_fallback, pack_steps[4], acl_recheck}`,
  `content_hash`.
- `ContextItem`: `cite_id`(`d{rank}`)·`rank`·`position`·`header{title, section_path,
  numbering_path, source_uri, external_id?, doc_date?, doc_type?, page_start?, page_end?,
  lang, doc_version_label?}`·`segments[]{index, text, char_start, char_end, block_id}`·
  `provenance[]{element_path, char_start, char_end, page, bbox, section_index}`·
  `acl{classification, checked, checked_at, source}`(`Acl2`)·`conflicts_with[]{cite_id,
  kind, note}`·`token_count`.
- `litm_alternating`(바이블 §9.2 정본): 홀수 `k` → `position = K-(k+1)//2`, 짝수 `k` →
  `position = k//2-1`. `LITM_ALTERNATING_TABLE`(K=1..5)은
  `rag_platform.testing.litm_order`가 고정.

## 5. 불변식·금지

1. 고정 순서: `relevance_gate → dedup → mmr → parent_expand → dedup`(후처리, 부분열만
   허용) / `acl_recheck → budget_cut → reorder → citation_align`(pack, 고정 4개 전부).
2. 각 단계는 `fused_rank`·`rerank_rank`·`score_breakdown`을 바꾸지 않는다(K3,
   ADR-0030). `final_rank`는 셸이 매기므로 이 WP 함수들은 재부여하지 않는다(테스트가
   직접 재부여해 검증).
3. `cite_id`는 `budget_cut` 뒤 최종 K개에 `final_rank` 오름차순으로 연속 `d1..dK`
   (건너뜀 없음). `position`은 `reorder`가 별도로 매기고 `cite_id`와 독립.
4. `retrieval`은 계층상 `storage`·`security`·`profiles`·`ledger`·`orchestration`을
   import할 수 없다(pyproject import-linter `layers`) — ACL 재검증·해시는 이 WP가
   자체 구현(§10.2 (a) 재현이 아니라 §3.2 요약 재현), 산출물 로드는 하지 않는다.
5. `sdk.hashing.blake3_hex`/`hash_of`만 사용하고 `blake3`를 직접 import하지 않는다
   (ADR-0004 단일 구현 린트).
6. 계약 생성물(`contracts/*`)은 손대지 않는다.

## 6. 단계

1. `relevance_gate.py`: `max(final_score) >= tau`, 미달 항목만 `omitted`.
2. `dedup.py`: (a) 부모에 흡수된 자식(`expanded_from`) 제거 → (b) `chunk_id` 완전
   동일 제거 → (c) 코사인(있으면)·MinHash(없으면, `num_perm=128, seed=42`) 근중복
   그리디 제거(상위 `final_rank`부터). 결과 리스트 순서는 원 순서 보존.
3. `mmr.py`: 문서 §2.4 의사코드 그대로(재정렬만, `mmr_demoted` explain).
4. `parent_expand.py`: `(chunk_set_blake3, parent_chunk_id)`로 그룹 → `|C|>=2`
   그룹만 대상 → `ChunkTextStore.get_many` 1회/세트 → 조건 (a)(n_children 없으면
   `|C|>=2`로 대체, 문서 §2.5 결정문 우선; 의사코드의 `ratio_ok = n_children is not
   None and ...`와는 불일치하며 이 WP는 결정문을 따름) 또는 (b)(자식 토큰 합
   ≥60% 부모) → 크기·예산 사전검사 → 최상위 자식 자리를 부모로 교체(`model_validate`
   재구성, `model_copy`의 검증 생략 위험을 피함).
5. `acl_recheck.py`: `payload`(Acl1) 또는 `revocation_hints`(해시 다르면 힌트 우선)로
   원칙(a) 재판정(허용/거부 주체, `visible_set`, `classification_max` 서열,
   `embargo_until`/`expires_at`). 통과 항목마다 `Acl2` 기록.
6. `budget_cut.py`: `final_rank` 오름차순 `k_max`까지 → `materialize`(헤더 문자열,
   `table_ref` 기반 `tables[]`; `figures[]`는 `RankedResult`에 원천 필드가 없어
   항상 `None` — §7 open_issue) → 토큰 재카운트 → `overflow_policy` 순서대로
   `downgrade_tables`→(`compress`는 압축기 미배선이라 즉시 truncate와 동일하게
   처리, 문서 §3.3 의사코드의 else 분기와 동치)→`truncate`.
7. `reorder.py`: `litm_alternating`(기본)/`document_order`(문서 간 최고 rank, 문서 내
   `(page, section_index, element_path 자연정렬, char_start)`)/`relevance_desc`.
   `document_order`가 `block_refs` 없는 항목을 만나면 `relevance_desc`로 폴백
   (`applied=false`).
8. `citation_align.py`: `rank=1..K`(최종 K개 재부여)·`cite_id=d{rank}`·`segments`
   (`sentence_spans`→없으면 `block_refs` 단위)·`provenance`(`block_refs`의
   `original_char_*` 복사)·`confidence_tier`(high≥0.7/medium≥0.4)·`conflicts_with`
   (version/source/date 규칙, 누락 시 `pack.conflict_unlabeled` 경고).
9. `packer.py`: 위 4단계 + `sufficiency`(§3.6 규칙 기반만, `llm_judge` 미구현)
   + `redaction_summary`(첫 non-null `pii_policy_applied`, 없으면 `keep`) +
   `classification_max` + `content_hash`(`hash_of("pack", canonical_json(hash_view
   (items)))`, `acl.checked_at` 제거).

## 7. 알려진 축소 범위(open_issues로도 보고)

- `figures[]`·`Parent`(자식 쪽 `child_chunk_ids`)·`doc_version_label`은 `RankedResult`에
  원천 필드가 없어 항상 생략/`None`.
- `text_format`은 `RankedResult`에 필드가 없어 `markdown` 고정.
- L1 위험 제외(§4.7)는 `risk_flagged` 콜백 주입식(기본 전부 통과) — `Enrichment.risk_flags`
  가 `RankedResult`에 없음.
- `sentence_window`·`compress`(후처리 단계)는 이 WP 파일 목록 밖(문서 §2.7·§2.8은
  플랫폼이 무효화/별도 모듈로 다룸).
- `PackConfig`↔`QueryPlan.pack`/`SecurityContext` 실 배선, `retrieval/postprocess/__init__.py`·
  `retrieval/pack/__init__.py` 셸 조립은 F4 배치 검증자 몫(§0).

## 8. 테스트(`tests/retrieval/test_postprocess_pack.py`)

- `test_relevance_gate_filters_below_tau`, `test_relevance_gate_empty_input_max_score_zero`.
- `test_dedup_removes_exact_and_near_duplicates`, `test_dedup_removes_parent_merged_children`.
- `test_mmr_reorders_and_marks_demoted`, `test_mmr_noop_when_lambda_disabled`.
- `test_parent_expand_merges_majority_children`,
  `test_parent_expand_skips_when_over_budget_guard`.
- `test_acl_recheck_denies_on_classification_and_embargo`,
  `test_acl_recheck_prefers_revocation_hint`.
- `test_budget_cut_truncates_lowest_rank_first`, `test_budget_cut_downgrades_tables`.
- `test_reorder_litm_alternating_matches_pinned_table`(K=1..5,
  `testing.litm_order.assert_pinned_table`), `test_reorder_document_order_fallback`.
- `test_citation_align_cite_ids_are_d1_dk_continuous`(K=3, `d1..d3`).
- `test_packer_end_to_end_builds_valid_context_pack` — K=6 합성 `RankedSet` →
  `ContextPack` 스키마 유효성(`ContractModel`) + `litm_order`/
  `renderer_citation_roundtrip`(`citation_map` 없이 `items`만으로
  `assert_cite_ids_bijective_with_items`) 동시 검증.

## 9. 완료 기준

`uv run pytest -q tests/retrieval/test_postprocess_pack.py` 전부 통과,
`uv run ruff check` 대상 9개 소스 파일 통과.

## 10. 검증 계층·DEFERRED

1층(여기서 검증) — 위 테스트. 모델·Docker·GPU·네트워크 의존 없음(순수 함수, 벡터는
합성 입력). `# DEFERRED: F4 배치 검증자가 QueryPlan.pack/SecurityContext 실 값을
PackConfig로 배선하고 retrieval/postprocess/__init__.py·retrieval/pack/__init__.py
셸에서 이 단계 함수들을 호출하도록 조립(§0, §7)`.

결과: 통과 16 / xfail 0 / DEFERRED 1(F4 배치 검증자의 QueryPlan 배선)
