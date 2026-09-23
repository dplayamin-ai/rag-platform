---
title: "WP-405 리뷰 수정 — retrieve/acl_recheck/filters"
status: done
version: 0.1.0
---

# WP-405 리뷰 수정 — retrieve·acl_recheck·filters (F4-05, review-fixes)

## 1. 목표

F4-01~04 코드 리뷰의 blocker/major 6건을 고친다. 새 기능이 아니라 기존 WP-401~402가 낸 모듈의
버그 수정이므로 파일·시그니처는 그대로이고, 계약(생성물)도 바꾸지 않는다. 대상:

1. `pack.acl_recheck._evaluate`가 AND 의미로 §10.2(a)의 OR(`visible_set` 포함 OR `allow` 일치)를
   깨서 `restricted`·`allow`에 없는 `public`/`tenant` 문서를 전부 거부하던 문제.
2. `pack.acl_recheck.apply`가 `deleted=True` 힌트를 `acl_hash`가 payload와 같으면 무시하던 문제
   (삭제는 ACL을 바꾸지 않아 `acl_hash`가 그대로다 — E9 골든 시나리오 위반).
3. `retrieval.filters.build_security_filter`가 `security.collection_ids`(허용된 전체 컬렉션)를
   그대로 써서 요청 스코프가 새고, Qdrant 어댑터가 공유 물리 컬렉션(§13.4)에서 `channel.collection_id`
   를 고정하지 않아 다중 컬렉션 요청이 서로의 후보를 중복 반환하던 문제.
4. `retrieval.channels.retrieve_once`가 `route=no_retrieval`(런 0건)에도 `retrieve.unavailable`
   (503)을 던지던 문제.
5. `retrieval.filters._validate_leaf`가 연산자만 검사하고 값 모양을 보지 않아, 오류가 plan 단계가
   아니라 Qdrant 빌더의 늦은 `contract.violation`으로 터지고 그게 다시 `retrieve.unavailable`로
   뭉개지던 문제.
6. `adapters.retrieve.{qdrant_dense,qdrant_sparse_bm25}`가 동기 `QdrantClient` 호출을 `await` 없이
   불러 이벤트 루프를 막던 문제(§8.1 7단계 채널 타임아웃 무력화).

## 2. 파일

- `src/rag_platform/retrieval/pack/acl_recheck.py` — (1)(2).
- `src/rag_platform/retrieval/filters.py` — (3)(5).
- `src/rag_platform/retrieval/planner.py` — (3) 호출측(`build_plan_filters`에 `collection_ids` 전달).
- `src/rag_platform/retrieval/channels.py` — (4), 그리고 (5)의 `contract.violation` 비은닉 재던짐.
- `src/rag_platform/adapters/retrieve/qdrant_dense.py`, `qdrant_sparse_bm25.py` — (3)의 컬렉션 고정,
  (6)의 `asyncio.to_thread`.
- 테스트: `tests/retrieval/test_postprocess_pack.py`(1·2) · `tests/retrieval/test_planner.py`(3·5) ·
  `tests/retrieval/test_fusion_channels.py`(3·4·6).

## 3. 시그니처(바뀐 부분만)

```python
# acl_recheck.py — 내부 헬퍼 교체(공개 시그니처 불변: apply(candidates, security, *, revocation_hints))
def _denied_by(principals: Sequence[str], deny: Sequence[str]) -> bool: ...
def _allowed_by(principals: Sequence[str], allow: Sequence[str]) -> bool: ...  # tenant:* 무조건 일치 없음
# apply() 루프: `hint.deleted`를 acl_hash 비교보다 먼저 검사.

# filters.py
def build_security_filter(
    security: ct.SecurityContext, *, collection_ids: Sequence[ct.Ulid] | None = None
) -> ct.SecurityFilter: ...
def build_plan_filters(
    *, security, strategy, user_filter, relaxable_keys,
    collection_ids: Sequence[ct.Ulid] | None = None,
) -> PlanFilters: ...
def _validate_leaf_value(op: ct.FilterOp, value: Any, field_name: str) -> None: ...  # 신규

# planner.py: build_plan_filters(..., collection_ids=collection_ids)  # 요청 ∩ 보안

# channels.py: retrieve_once — runs가 비면 raise 없이 빈 CandidateSet; StageError.code가
# {retrieve.security_context_missing, contract.violation} 중 하나면 재던짐(그 외는 기존과 동일).

# qdrant_dense.py / qdrant_sparse_bm25.py: _build_query_filter가 `collection_id == channel.
# collection_id` must를 추가; run()의 backend 호출이 `await asyncio.to_thread(...)`.
```

## 4. 입출력 계약 발췌(변경 없음 — 재확인만)

- `contracts.context_pack.AclRecheckReport.hint_hits` — "회수 힌트가 payload와 달라 힌트로 판정한
  수". 삭제 힌트가 `acl_hash`까지 같을 때는 "힌트로 판정"이 아니라 "무조건 거부"라 `hint_hits`를
  올리지 않는다(값 의미를 그대로 지킨다).
- 바이블 §10.1·§10.2(a): `(acl_visibility IN :visible_set OR acl_allow ANY :principals) AND NOT
  (acl_deny ANY :principals)`. `public`은 allow 검사 생략(= 항상 `visible_set`에 있다고 간주하지
  않고, `public`이 `visible_set`에 항상 있다는 `SecurityContext.visible_set` 기본값에 의존).
- `contracts.query_plan.PlanFilters.security: common_types.SecurityFilter`(`collection_ids: list[Ulid],
  max_length=20, min_length=1`) — 필드 자체는 안 바뀜, 채우는 값만 "요청 ∩ 보안"으로 정정.

## 5. 불변식·금지

- 거부(`deny`)는 항상 우선(§10.1) — 두 헬퍼 분리 후에도 `_evaluate`는 `_denied_by`를 가장 먼저 본다.
- `_allowed_by`는 리터럴 멤버십만 본다 — `tenant:*`를 무조건 일치시키면 OR 결합에서 `visible_set`이
  그 `visibility`를 빼 둔 service 전용 주체에게 allow 경로로 샌다(리뷰가 명시한 금지).
- `build_security_filter`/`build_plan_filters`의 `collection_ids` 생략 시 동작은 이전과 동일
  (`security.collection_ids` 그대로) — 기존 호출부·테스트 호환. `planner.plan()`만 항상 명시적으로
  넘긴다.
- `retrieve_once`가 "런 0건 → 빈 CandidateSet"과 "시도한 런 ≥1, 성공 0건 → `retrieve.unavailable`"을
  구별한다 — 둘을 합치면 안 된다.
- `_validate_leaf_value`가 잡는 값 모양 오류는 F-7과 같은 코드(`plan.filter_field_forbidden`)로
  올린다 — 새 오류 코드를 만들지 않는다(카탈로그 철자 §5.7 준수).
- Qdrant 어댑터 두 곳의 `_build_query_filter` 로직은 의도적으로 중복이다(`retrieval`↔`adapters`는
  서로 모르는 형제 계층이라 공유 헬퍼를 둘 자리가 이 배치 범위에는 없다 — open_issues).

## 6. 단계

1. `acl_recheck.py`: `_principal_allowed`를 `_denied_by`/`_allowed_by`로 분리, `_evaluate`를 OR로
   재작성. `apply()`의 힌트 분기를 `hint.deleted` 우선 검사로 재배열.
2. `filters.py`: `build_security_filter`/`build_plan_filters`에 `collection_ids` 파라미터 추가.
   `_validate_leaf`에 `_validate_leaf_value` 호출 추가(리스트/bool/문자열/스칼라 검사).
3. `planner.py`: `build_plan_filters` 호출에 `collection_ids=collection_ids`(이미 계산된 교집합) 추가.
4. `channels.py`: `retrieve_once` 초입에 `runs` 빈 배열 조기 반환 추가. 예외 재던짐 목록에
   `contract.violation` 추가(`_NON_MASKABLE_CODES` 상수).
5. `qdrant_dense.py`/`qdrant_sparse_bm25.py`: `_build_query_filter`에 `collection_id` must 추가;
   `run()`의 백엔드 호출을 `asyncio.to_thread`로 감쌈.
6. 테스트 추가·기존 1건 수정(§8).

## 7. 테스트(파일·케이스)

- `tests/retrieval/test_postprocess_pack.py`
  - `test_acl_recheck_prefers_revocation_hint` **수정**: 힌트 `visibility`를 `tenant`→`restricted`로
    바꿔 OR 의미에서도 "힌트가 payload와 다른 결과를 낸다"를 증명하도록 재구성(기존 값은 새 OR
    의미에서 payload만으로도 이미 통과라 테스트 의도가 깨졌었다).
  - `test_acl_recheck_denies_deletion_hint_even_when_acl_hash_matches_payload` 신규.
  - `test_acl_recheck_matches_bible_10_2_a_or_semantics` 신규(6 케이스: public/tenant/restricted x
    user/service 주체).
  - `test_acl_recheck_deny_always_wins_over_visible_set` 신규.
- `tests/retrieval/test_planner.py`
  - `test_validate_user_filter_rejects_malformed_value_before_retrieve` 신규(5 케이스: 리뷰가 든
    3건 + range 스칼라 1건 + prefix 빈 문자열 1건).
  - `test_build_security_filter_defaults_to_all_security_collection_ids`/
    `test_build_security_filter_narrows_to_explicit_collection_ids`/
    `test_plan_scopes_security_filter_to_requested_collection_ids` 신규.
- `tests/retrieval/test_fusion_channels.py`
  - `test_retrieve_once_returns_empty_candidate_set_when_no_runs_are_enabled` 신규.
  - `test_retrieve_once_reraises_contract_violation_instead_of_masking_it` 신규.
  - `test_qdrant_{dense,sparse_bm25}_retriever_pins_to_channel_collection_id` 신규(공유 별칭에 두
    컬렉션 레코드를 넣고 한쪽만 반환되는지 확인).
  - `test_qdrant_{dense,sparse_bm25}_retriever_does_not_block_event_loop` 신규(동기 백엔드를 두 번
    동시 호출해 총 시간이 순차(`2×sleep`)가 아니라 병렬(`~1×sleep`)인지 측정).

## 8. 완료 기준

- 위 4개 테스트 파일이 `uv run pytest -q tests/retrieval tests/security`에서 전부 통과.
- 6건 수정 각각을 실제로 되돌려 재현되는지 로컬에서 확인(모두 재현됨, 아래 결과 참고).
- `ruff check`가 수정한 6개 소스 파일 + 3개 테스트 파일에서 통과.
- `tests/api`·`tests/mcp`는 이 저장소에 아직 없음(open_issues) — 지시된 4개 경로 중 존재하는
  `tests/retrieval`·`tests/security`만 실행.

## 9. 검증 계층·DEFERRED

1층(여기서 검증) — 로컬 Qdrant `:memory:` + 순수 함수 + 페이크, 외부 자원 없음.
DEFERRED: 실 Qdrant 서버 대상 채널 타임아웃 강제(§8.1 7단계 250ms, `asyncio.wait_for`가 서버 왕복을
실제로 끊는지)는 `needs_docker` — 이 WP는 "이벤트 루프를 막지 않는다"만 로컬 모드로 검증했다
(open_issues에 기록).

## 10. open_issues

- `tests/api`, `tests/mcp` 디렉터리가 저장소에 없다(지시된 실행 명령의 경로 2개). 이 배치 범위 밖.
- `qdrant_dense.py`/`qdrant_sparse_bm25.py`의 `_build_query_filter` 컬렉션 고정 로직이 두 파일에
  중복된다 — `retrieval`↔`adapters`가 서로 모르는 형제 계층이라 공유 헬퍼 자리가 없다(바이블 §12).
  공용 헬퍼가 필요하면 `sdk.channel_run`처럼 그 아래 층에 두는 결정이 필요하다.
- `fusion._fuse_runs`에 "같은 채널·같은 변형 런에서 `record_id`가 두 번 나오지 않는다"는 방어적
  assert를 추가하는 안(리뷰의 "optionally")은 이번 배치에 넣지 않았다 — 근본 수정(어댑터 컬렉션
  고정)으로 원인이 막혀 있고, 이 assert는 별도 WP에서 다른 채널까지 함께 볼 때 추가하는 편이 낫다.
- 실 Qdrant 서버 타임아웃 강제 검증(`needs_docker`)은 만들지 않았다 — §9 참고.

## 결과: 통과 22(신규) + 71(기존, 회귀 없음, 그중 1건은 새 OR 의미에 맞게 수정) = 93/93 / xfail 0 /
DEFERRED 1(needs_docker 서버 타임아웃 강제)
