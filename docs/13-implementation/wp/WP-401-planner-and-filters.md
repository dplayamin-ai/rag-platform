---
title: "WP-401 규칙 경로 플래너와 필터"
status: active
owner: implementation
version: 0.1.0
last_updated: 2026-09-24
implementation_status: done
depends_on: ["../README.md", "../../12-appendix/10-implementation-design-gaps.md"]
---
# WP-401 규칙 경로 플래너와 필터 (F4-01, planner-and-filters)

## 0. 실행 배경(병렬 배치 주의)

F4 배치는 F4-01(본 WP)·F4-02(channels·fusion·hydrate)·F4-03(postprocess·pack)·F4-04(render·query
파이프라인)를 병렬 에이전트로 실행한다(`WP-404-render-and-query-pipeline.md` §0). `uv run lint-imports`로
확인한 결과 F4-02/04가 이미 `rag_platform.retrieval`↔`rag_platform.adapters`/`rag_platform.pipelines`
간 바이블 §12 "layers" 계약(같은 계층 `plugins|adapters|pipelines|retrieval|render`는 서로 독립)을 깨고
있다(`pipelines.query -> retrieval.channels/fusion/hydrate/pack/postprocess.*`,
`retrieval.hydrate -> adapters.index.qdrant.filters`). 이 WP도 같은 이유로 `retrieval/planner.py`가
`adapters/query/korean_normalize.py`·`rule_router.py`를 직접 임포트한다(순수 함수 호출, 부작용 없음).
mypy처럼 import-linter 정합도 이 WP 완료 기준에 없고 F4 배치 검증자가 최종 정리한다(아래 미해결 이슈).

## 1. 목표

`plan` 스테이지의 **규칙 경로**(LLM 없음, `retrieval_variant=default|fast`)만 구현한다: 정규화
(NFC 표시 뷰 + NFKC 렉시컬 뷰, 04-pipelines/14 §2.1)·언어 감지(§2.2)·형태소 키워드(Kiwi 있으면 사용,
없으면 폴백, §6.1)·규칙 라우터(6종 의도 → `route`/`complexity`/`strategy`, §3.1~§3.2)·필터 3층 결합
(security 서버 주입·불변, strategy 고정값, user 화이트리스트 검증, §8/§10.2)·`QueryPlan` 조립(채널
`dense`+`lexical`(`sparse_bm25` 백엔드), `fusion.method=rrf, k=60`, `k` 산정 §9.2, 예산 §9.3 일부).
`self_query`·LLM 재작성·`multi_query`·HyDE·`quality` 변형은 플러그인 자리로 남기고 이 WP는 채우지
않는다(`filters.self_query=null`, `budget.llm_calls_allowed=false` 고정).

## 2. 파일

- `src/rag_platform/adapters/query/korean_normalize.py` — 표시/렉시컬 뷰 정규화, 언어 감지, 형태소
  키워드(`LexicalTerm[]`), `analyzer_id`/`dictionary_hash`. Stage 5멤버 `KoreanNormalizeTransformer`
  (plugin_id `query_transformer.korean_normalize`)로도 감싼다.
- `src/rag_platform/adapters/query/rule_router.py` — 의도 분류 6종(§3.2 표) + `route`/`complexity`
  매핑(§3.1) + `strategy_hint` 채택/거부(§3.4, 능력 대조는 이 WP 범위 밖이라 항상 거부). Stage 5멤버
  `RuleRouterTransformer`(plugin_id `query_transformer.rule_router`).
- `src/rag_platform/retrieval/filters.py` — `build_security_filter`·`STRATEGY_FILTERS`(hybrid·
  iterative만)·`validate_and_normalize_user_filter`(화이트리스트+깊이≤3+절≤32+`relaxable_keys`)·
  `build_plan_filters`(3층 결합 + `effective_hash`)·`canonical_json`.
- `src/rag_platform/retrieval/planner.py` — `PlannerDefaults`(lite.yaml 값 복사, CollectionSpec
  미배선 자리표시자)·`plan(request, security, *, plan_id=None, defaults=None) -> QueryPlan`
  (`WP-404-render-and-query-pipeline.md` §3 `Planner` 프로토콜과 호출부 호환).
- `tests/retrieval/test_planner.py` — 단위(정규화/라우팅/필터) + `plan()` 통합.

## 3. 시그니처

```python
# adapters/query/korean_normalize.py
@dataclass(frozen=True)
class NormalizeResult:
    original_query: str; normalized_query: str; lexical_view: str; lang: str
    lexical_terms: list[LexicalTerm]; analyzer_id: str; dictionary_hash: str

def normalize_query(raw_query: str, *, use_kiwi: bool | None = None) -> NormalizeResult: ...
def detect_lang(text: str) -> str: ...  # "ko"|"ja"|"zh"|"en"

class KoreanNormalizeConfig(BaseModel): ...
class KoreanNormalizeTransformer:
    plugin_id = "query_transformer.korean_normalize"; config_schema = KoreanNormalizeConfig
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, draft: PlanDraft, ctx: Any = None) -> PlanDraft: ...

# adapters/query/rule_router.py
def classify_intent(lexical_terms: Sequence[LexicalTerm], raw_query: str, *, has_conversation: bool) -> str: ...
def route_for_intent(intent: str) -> tuple[ct.Route, ct.Complexity]: ...
def adopt_strategy(strategy_hint: ct.Strategy | None) -> tuple[ct.Strategy, list[ct.DegradedEntry]]: ...
class RuleRouterConfig(BaseModel): ...
class RuleRouterTransformer:
    plugin_id = "query_transformer.rule_router"; config_schema = RuleRouterConfig
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, draft: PlanDraft, ctx: Any = None) -> PlanDraft: ...

# retrieval/filters.py
def canonical_json(data: Any) -> str: ...
def build_security_filter(security: ct.SecurityContext) -> ct.SecurityFilter: ...
def strategy_filter_for(strategy: ct.Strategy) -> ct.StrategyFilter: ...
def validate_and_normalize_user_filter(
    node: ct.FilterNode | None,
) -> tuple[ct.FilterNode | None, list[ct.FilterableField1]]: ...
def compute_effective_hash(security, strategy, user, self_query) -> str: ...
def build_plan_filters(*, security: ct.SecurityContext, strategy: ct.Strategy,
                        user_filter: ct.FilterNode | None,
                        relaxable_keys: list[ct.FilterableField1]) -> qp.PlanFilters: ...

# retrieval/planner.py
@dataclass
class PlanDraft:  # 계약 아님, 내부 초안(04-pipelines/14 §1.1)
    request: QueryRequest; security: ct.SecurityContext
    original_query: str = ""; normalized_query: str = ""; lexical_view: str = ""
    lang: str = "ko"; intent: str = "natural_question"
    route: ct.Route = ct.Route.single; complexity: ct.Complexity = ct.Complexity.single_step
    strategy: ct.Strategy = ct.Strategy.hybrid
    lexical_terms: list[LexicalTerm] = field(default_factory=list)
    analyzer_id: str = ""; dictionary_hash: str = ""
    degraded: list[ct.DegradedEntry] = field(default_factory=list)

@dataclass(frozen=True)
class PlannerDefaults: ...  # lite.yaml 상수 사본(§7 참조)

def plan(
    request: QueryRequest, security: ct.SecurityContext | None,
    *, plan_id: str | None = None, defaults: PlannerDefaults | None = None,
) -> QueryPlan: ...
```

## 4. 입출력 계약 발췌(철자 정본)

- `QueryRequest{schema_version, query_id, query, collection_ids[1..20], conversation?, filters?
  (FilterNode), top_k?, mode?, retrieval_variant?, strategy_hint?, target_model?,
  max_context_tokens?, renderer?, ordering_strategy?, include_parents?, response_format?,
  session_id?, exclude_ids?, cursor?, budget?{max_latency_ms, max_tool_calls, max_context_tokens},
  experiment_id?, team_assignment?, explain?, requested_at}`.
- `SecurityContext{tenant_id, principals[1..], collection_ids, as_of, classification_max,
  policy_version, auth_method, visible_set}` — "서버 주입·읽기 전용"(`as_of` = "서버 now()").
- `common_types.FilterNode = FilterNode1{and}|FilterNode2{or}|FilterNode3{not}|FilterNode4
  {field: FilterableField1, op: FilterOp, value}`; `FilterableField`(15개: document_id,
  doc_version, external_id, doc_date, doc_type, department, tags, lang, genre, item_kind,
  heading_path, entity_ids, page_start, page_end, page) ∪ `custom.*`(`FilterableField3`, 이 WP는
  선언 카탈로그가 없어 항상 거부). "깊이 ≤ 3, 절 ≤ 32"(FilterNode4 docstring).
- `common_types.SecurityFilter{tenant_id, collection_ids, principals, visible_set, as_of,
  is_current: Literal[True], classification_max}`; `StrategyFilter{level_in: ChunkLevel[],
  item_kinds: ItemKind[]}`.
- `query_plan.PlanFilters{security, strategy, user: FilterNode|null, self_query: FilterNode|null,
  relaxable_keys: FilterableField1[], effective_hash: Hex64}` — F-5: `effective_hash =
  H("filters", canonical_json({security(as_of→":as_of" 바인드 이름 치환), strategy, user,
  self_query}))`(계획 트리, `page` 변환 전).
- `QueryPlan{schema_version, schema_type="QueryPlan", tenant_id, collection_ids, producer,
  warnings, degraded, created_at, plan_id, query_id, security_context, profile_id, profile_hash,
  original_query, normalized_query, dense_query_text, analyzer_id, dictionary_hash, route,
  complexity?, strategy, rewritten_queries[1..16], sub_queries?, lexical_terms(≤128),
  filters: PlanFilters, channels[1..140]: ChannelPlan[], fusion: FusionPlan, hydrate: HydratePlan,
  rerank: RerankPlan, late_interaction_rerank?, postprocess: PostprocessPlan, pack: PackPlan,
  latency_budget_ms, budget, cache_keys, explain, planner_fingerprint, session_id?, exclude_ids?,
  experiment_id?, team_assignment?}`.
- `ChannelPlan{channel: Channel, collection_id, retriever_id, backend_id,
  collection_alias: "col_{collection_id}_vec|_lex", embedding_profile_hash: Hex64,
  index_generation_min, top_k, timeout_ms, weight, embedding_space_id?, query_vector_ref?,
  enabled}`; `Channel`에는 `sparse_bm25` 값이 없다 — lite 프로파일 주석대로 "sparse_bm25 벡터는 항상
  `channel=lexical`"(선택된 채널: `dense`, `lexical`).
- `FusionPlan{method, k, weights: {channel: float}, variant_query_weight}`;
  `RewrittenQuery{variant_id, text, role, weight, channels}` — `original`은
  `variant_id=query_id, weight=1.0, text=normalized_query`.
- `common_types.ErrorCodeCatalog`: `plan.security_context_missing`, `plan.filter_field_forbidden`,
  `plan.collection_forbidden`, `contract.violation`(플래너 결함, 04-pipelines/14 §1.1).
- `sdk.stage.StageError(code, *, stage="plan", detail=...)` — 코드 철자 검사·재시도 분류 내장.

## 5. 불변식·금지

- **F-1**(§8): `filters.security`는 `security_context`를 그대로 복사, `is_current=True` 고정. `security`
  가 `None`이면 `StageError("plan.security_context_missing", stage="plan")`.
- **F-4**: `relaxable_keys ⊆ user`(이 WP는 `self_query`가 없어 `user`만) 리프 필드, 보안·전략 키 불가 —
  §7.3의 "사용자 필터의 부정 절(`not`·`ne`·`not_in`)만 완화"를 그대로 적용(`self_query` 없음 → 신뢰도
  오름차순 부분은 이 WP에 해당 없음).
- **F-5**: `effective_hash`는 `as_of`를 `":as_of"`로 치환한 계획 트리의 해시(캐시 재사용을 위해 시각에
  불변).
- 사용자 필터 금지 필드·불허 연산자·`custom.*`(카탈로그 미보급) → 422 `plan.filter_field_forbidden`
  (요청 컬렉션 ∩ 보안 컬렉션 = ∅ → 403 `plan.collection_forbidden`; `security=None` → 400
  `plan.security_context_missing`). Pydantic `QueryPlan` 생성 실패는 `contract.violation`으로
  격상한다(04-pipelines/14 §1.1).
- `datetime.datetime.now()`/`time.time()`/`uuid.uuid4()` 직접 호출 금지(banned-api, `pyproject.toml`).
  이 WP는 "서버 now()"인 `security_context.as_of`를 `created_at`으로 재사용해 시계 의존을 없앤다(§10.2
  `SecurityContext.as_of` 정의). `plan_id`는 미주입 시 `ulid.ULID()`로 발급한다(`adapters/index/saga.py`
  선례).
- `retrieval`/`adapters`는 `storage`·`security`(패키지)·`ledger`·`orchestration`을 모른다(바이블 §12).
  `retrieval/planner.py -> adapters/query/*`는 §0에서 밝힌 기존 위반(F4-02/04)과 같은 종류이며 이 WP가
  새로 만드는 예외가 아니다(미해결 이슈 참고).
- Stage 5멤버(`plugin_id`/`config_schema`/`capabilities()`/`fingerprint()`/`run()`) 외 확장 금지
  (ADR-0032). 계약 생성물(`contracts/*`) 손편집 금지.

## 6. 단계

1. `korean_normalize.py`: `clean_unicode`/`apply_edits`/`fold_lexical`(기존
   `adapters/normalize/korean/unicode.py`, 같은 배치 F1 산출물 재사용)로 표시 뷰(NFC) 조립 후 공백
   접기; 렉시컬 뷰는 `fold_lexical` + 기호 통일(가운뎃점·물결·대시류) + 소문자화. 한자→한글 독음은
   DEFERRED(문서 자체가 "정확도 확인 필요"로 미확정).
2. `detect_lang`: 한글·한자·가나·라틴 문자 비율 규칙(§2.2 표).
3. 형태소 키워드: `kiwipiepy` 있으면 `NNG`/`NNP`/`SL`/`SN` 태그만 채택, 없으면 한글/라틴/숫자 문자
   클래스 폴백(조사 접미 스트립) — `enricher.korean_keywords`(F2 배치)와 같은 try/except 관례.
   공용 불용어 + 질의 전용 불용어(§6.3, `이후·이전·최근·방법·가능`/의문 불용어) 제거, `여부`·`이내`는
   유지. `(term, tag)` 유일, 상한 128.
4. `rule_router.py`: §3.2 6우선순위 규칙으로 내부 의도 라벨 산정(정규식·소형 어휘 목록만, 외부 모델
   없음) → §3.1 표로 `route`/`complexity` 매핑. `strategy_hint`는 `hybrid`/`iterative`만 그대로 채택,
   그 외는 `hybrid` 유지 + `degraded{channel.graph|tree|visual, capability_unsupported}`(능력 대조에
   필요한 `CollectionSpec`/`IndexBackendCapabilities`가 이 WP 읽기 예산 밖).
5. `filters.py`: 사용자 필터를 깊이·절수·화이트리스트·연산자로 검증하며 동시에 부정 절
   `relaxable_keys`를 수집; `security`/`strategy`/`user`/`self_query(=null)`을 결합해
   `effective_hash` 계산.
6. `planner.py`: 요청·보안 컬렉션 교집합 → 채널(각 컬렉션 × `{dense, lexical}`, `PlannerDefaults`의
   `lite.yaml` 값) → `fusion(rrf, k=60)` → `hydrate`/`rerank`(`retrieval_variant=fast`면 리랭크
   끔·`hydrate.top_n=k_max×2`) → `postprocess`/`pack`(lite 고정값) → `latency_budget_ms.total =
   min(profile total, request.budget.max_latency_ms)` → `budget.llm_calls_allowed=false` 고정 →
   `cache_keys`(§10 식, `query_embedding=null` — 임베딩 공간 미배선) → Pydantic `QueryPlan` 생성.

## 7. `PlannerDefaults` 값(lite.yaml 사본, 04-pipelines/14 §9.1·§9.2 표와 함께 확인)

`profile_id="lite"`, 채널 `{dense: retriever.qdrant_dense, lexical: retriever.qdrant_sparse_bm25}`
(둘 다 `index_backend.qdrant`, `top_k=100, timeout_ms=250`), `fusion{method=rrf, k=60,
variant_query_weight=0.5}`, `hydrate{backend_id=index_backend.qdrant, with_vectors=false}`,
`rerank{plugin_id=reranker.flashrank, backend=in_process, response_schema=tei, top_n_in=100,
top_n_out=20, max_tokens_per_text=512, timeout_ms=300, normalization=sigmoid}`,
`pack{k_max=20, max_context_tokens=24000, reserved_answer_tokens=4000,
ordering=litm_alternating, renderer=anthropic_search_result, tokenizer.provider=anthropic,
tokenizer.model="claude-placeholder", count_method=approximate,
table_format_preference=[html,markdown,json], overflow_policy=[downgrade_tables,truncate],
confidence_tiers={high:0.7, medium:0.4}}`, `latency_budget_ms{total=800, plan=60, retrieve=120,
rerank=250, postprocess=60, pack=40}`. `embedding_profile_hash`/`profile_hash`는
`hash_of(...)` 플레이스홀더(진짜 `CollectionSpec`/`profiles.loader` 미배선, 미해결 이슈).

## 8. 테스트(파일·케이스)

`tests/retrieval/test_planner.py`:
- `korean_normalize.normalize_query`: NFC 표시/NFKC 렉시컬 뷰 분리, 제어문자·zero-width·NBSP 제거,
  공백 접기, 기호 통일(물결·가운뎃점), `lexical_terms` 태그 집합 ⊆ `{NNG,NNP,SL,SN,USER_DICT}`,
  불용어 제거(`여부`/`이내` 유지 확인).
- `rule_router.classify_intent`/`route_for_intent`: `keyword_lookup`("정보공개법 시행령 제10조" →
  `single`/`single_step`), `natural_question`("며칠 이내에 결정해야 하나요?"), `compare_aggregate`
  ("2024년과 2025년 실적을 비교해줘").
- `rule_router.adopt_strategy`: `hybrid` 그대로, `graph_local` → `hybrid` + `degraded{channel.graph,
  capability_unsupported}`.
- `filters.validate_and_normalize_user_filter`: 화이트리스트 필드 통과, 금지 필드(`tenant_id`)
  → `StageError plan.filter_field_forbidden`, 부정 절 → `relaxable_keys`, 깊이 4 → 거부.
- `filters.build_plan_filters`: `as_of`만 다른 두 `SecurityContext`가 같은 `effective_hash`를 냄.
- `planner.plan()` 통합: (a) 정상 요청 → `QueryPlan` 필드(2채널×1컬렉션, `fusion.k=60`, `route=single`);
  (b) `security=None` → `plan.security_context_missing`; (c) 요청 컬렉션 ∩ 보안 컬렉션 = ∅ →
  `plan.collection_forbidden`; (d) `retrieval_variant=fast` → `rerank.enabled=False`,
  `hydrate.top_n=40`; (e) `budget.max_latency_ms=300` → `latency_budget_ms.total=300`.

## 9. 완료 기준

`uv run pytest -q tests/retrieval/test_planner.py` 전부 통과(최대 3회), `uv run ruff check
src/rag_platform/retrieval/planner.py src/rag_platform/retrieval/filters.py
src/rag_platform/adapters/query/korean_normalize.py src/rag_platform/adapters/query/rule_router.py`
통과. mypy·import-linter는 배치 검증자가 별도 실행.

## 10. 검증 계층·DEFERRED

1층(여기서 검증). `needs_docker`/`needs_model`/`needs_gpu`/`needs_network` 해당 없음(순수 함수,
`kiwipiepy`는 선택 의존성이며 미설치 시 폴백 — 폴백 경로가 이 WP의 기본 테스트 경로).

- DEFERRED: 한자→한글 독음(§2.1 규칙 5) — 문서 자체가 정확도 미검증(as of 2026-09)이라 원문 유지.
- DEFERRED: `self_query`(정규식/LLM) 추출 — `filters.self_query`는 항상 `null`. 별도 WP.
- DEFERRED: §9.3 4단계 사전 저하 사다리(멀티쿼리 끔→리랭크 절반→리랭크 끔→채널 축소) — 이 WP는
  `latency_budget_ms.total`의 상한 클램프만 구현하고 나머지 3단계는 F4-02/후속 WP로 이월.
- DEFERRED: `CollectionSpec`/`IndexBackendCapabilities`/`profiles.loader` 실배선(채널 능력 대조,
  진짜 `embedding_profile_hash`/`profile_hash`/`embedding_space_id`, `cache_keys.query_embedding`) —
  §12 계층 규칙상 `retrieval`은 `profiles`를 알 수 없고 이 WP 읽기 예산은 `CollectionSpec`을 제외한다.
- DEFERRED: 소형 분류기·LLM 라우터/재작성/`multi_query`/HyDE/분해(§3.3, §4.2, §5) — 플러그인 자리만
  남긴다(`budget.llm_calls_allowed=false` 고정, `rewritten_queries`는 `original` 1개뿐).

결과: 통과 31 / xfail 0 / DEFERRED 5
