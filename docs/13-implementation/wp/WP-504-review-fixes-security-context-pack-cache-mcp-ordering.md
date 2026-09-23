---
title: "WP-504 리뷰 수정 — API 키 서비스 주체, pack_id 캐시 주체 바인딩, MCP search 관련도순 절단"
status: done
version: 0.1.0
---

# WP-504 리뷰 수정 — 서비스 주체·pack_id 캐시·MCP 순위 정렬 (F5-04, review-fixes)

## 1. 목표

F5-01/02(`WP-501`/`WP-502`) 코드 리뷰의 major 3건을 고친다. 새 기능이 아니라 기존 모듈의 버그
수정이므로 파일·계약(생성물)은 그대로다. 대상:

1. `security.security_context.derive_security_context`가 API 키(서비스) 주체에도
   `principals=["user:{subject}", "tenant:*"]`·`visible_set=["public","tenant"]`를 주어, 리트리벌이
   배선되면 그 키가 자신의 `acl_allow`에 없는 `acl_visibility=tenant` 문서까지 전부 보게 되는 문제
   (ADR-0027 SecurityContext 불릿, `05-api/03` §2 "주체 문자열" 행 위반). MCP `resolve_security`도
   이 함수를 재사용할 예정이라 같은 과다 인가가 그쪽에도 번진다.
2. `api.query`의 `pack_cache`가 주체 바인딩·TTL 없이 `(tenant_id, pack_id) → ContextPack`만 저장해,
   `POST /v1/render {pack_id}`가 같은 테넌트의 아무 키에게나(허용 컬렉션이 달라도) 팩을 내주고,
   10분 조회 창(`05-api/03` §4.4)도 없이 무기한 남아 메모리가 계속 자라는 문제.
3. `mcp.tools.search`/`_fit_search_page_to_budget`가 `pack.items`를 `position`(렌더 순서) 순으로
   자르고 잘라내, `litm_alternating`처럼 `position != rank`인 순서 전략에서 `cite_id` 구멍(`d1..dM`
   비연속)이 생기는 문제(`05-api/05` §4.2 outputSchema·§5.1 절단 규칙 위반).

## 2. 파일

- `src/rag_platform/security/security_context.py` — (1). `derive_security_context`만 수정, 새 예외
  `TooManyPrincipalsError` 추가.
- `src/rag_platform/api/query.py` — (2). `post_query`/`post_render`와 `app.state.pack_cache`의 값
  모양(엔트리 타입 신규, `app.py`의 `pack_cache = {}` 초기화 자체는 안 바뀜 — 여전히 빈 dict).
- `src/rag_platform/mcp/tools.py` — (3). `search`·`_fit_search_page_to_budget`만 수정.
- 테스트: `tests/security/test_security_context.py`(신규 파일, 디렉터리는 `.gitkeep`만 있던 빈
  디렉터리) · `tests/api/test_api.py`(2) · `tests/mcp/test_mcp_tools.py`(3).

## 3. 시그니처(바뀐 부분만)

```python
# security_context.py
class TooManyPrincipalsError(Exception):  # 신규. code="auth.too_many_principals", status=422
    def __init__(self, detail: str) -> None: ...

def derive_security_context(...) -> ct.SecurityContext:
    # principals = sorted(dict.fromkeys(["service:{record.subject}"]))  # user:/tenant:* 없음
    # visible_set = ["public"]  # 고정
    # len(principals) > 1024 -> raise TooManyPrincipalsError(...)
    ...

# query.py — 신규 비공개 헬퍼(공개 시그니처는 그대로: post_query/post_render 라우트 불변)
_PACK_CACHE_TTL_S: int = 600  # 05-api/03 §4.4 10분
_PACK_CACHE_MAX_ENTRIES: int = 10_000  # 메모리 상한(방어적)

@dataclass(frozen=True)
class _PackCacheEntry:
    pack: ContextPack
    security_context_hash: str
    expires_at: datetime

def _pack_security_context_hash(
    *, tenant_id: str, principals: Sequence[str], collection_ids: Sequence[str],
    as_of: str, classification_max: str, visible_set: Sequence[str],
) -> str: ...  # mcp.cursor_store.security_context_hash와 동일 공식(H("sec", ...))의 독립 구현

def _prune_pack_cache(cache: dict[tuple[str, str], _PackCacheEntry], *, now: datetime) -> None: ...

# mcp/tools.py — 공개 시그니처 불변, 내부 정렬만 교체
def _select_page_by_rank(items: Sequence[ContextItem], top_k: int) -> list[ContextItem]: ...  # 신규
def _fit_search_page_to_budget(
    pack: ContextPackType, items: list[ContextItem], response_format: str, max_tokens: int,
) -> tuple[list[dict[str, Any]], str, bool]: ...  # items는 이미 rank 오름차순으로 들어옴
```

## 4. 입출력 계약 발췌(변경 없음 — 재확인만)

- `common_types.SecurityContext.principals: list[PrincipalString]`(패턴
  `^(user:\S+|group:\S+|service:\S+|tenant:\*)$`, `max_length=1024`) — API 키 경로는 이 중
  `service:\S+` 한 값만 만든다.
- `common_types.SecurityContext.visible_set: list[Visibility]` — `05-api/03` §2: "서비스 주체(API
  키·M2M·mTLS): `["service:{client_id}"]`만 — `tenant:*`가 없으므로 `visible_set=[public]`".
- `05-api/03` §4.4 표: 저장 값 `{context_pack, security_context_hash}`, TTL 10분(초안), 조회 시
  `collection_ids' = allowed ∩ pack.collection_ids`·`as_of`는 팩의 저장 값으로 고정해 재계산,
  불일치·만료는 404 `api.not_found`(`_CODE_NOT_FOUND`, 이미 정의됨). `as_of`는
  `pack.diagnostics.filters_applied.security.as_of`(= 저장 시점 `SecurityContext.as_of`)에서 읽는다
  — 별도 저장 불필요(§4.4 "원 `as_of`는 팩 자체에 있으므로 별도 저장하지 않는다").
- `contracts.common_types.ContextItem.rank: int`(1-based 관련도 순위, `cite_id = "d" + str(rank)`)·
  `.position: int`(0-based 렌더 위치) — 이미 계약에 둘 다 있다(신규 필드 아님). `05-api/05` §4.2
  outputSchema `items`: "렌더 순서(position 오름차순). cite_id는 관련도순 d1..dK". §5.1 절단:
  "(1) `items`를 `min(top_k, K)`개로 자른다 → (2) 상한 초과면 **하위 순위부터** 제거(`cite_id`는
  `d1..dM` 연속 유지)".
- 바이블 §9.2 `litm_alternating`(K=1..5 표): 예 K=3 render order = `[r2, r3, r1]`(position 0→2),
  즉 `rank=1`(`d1`)이 `position=2`에 온다 — 지금 버그가 정확히 이 배치를 깬다.

## 5. 불변식·금지

- `derive_security_context`는 API 키 전용이라 이 함수 안에서는 OIDC `user:`/`group:` 분기를 만들지
  않는다(그 경로는 별도 open_issues, 이 모듈 docstring에 이미 명시). `visible_set`은 상수
  `["public"]`(리스트 리터럴 그대로) — 조건 분기 없음(오늘은 이 함수가 API 키만 다루므로).
- `TooManyPrincipalsError`는 오늘의 레지스트리(키당 주체 1개)에서는 도달 불가능하지만 계약 상한을
  구현에서도 지킨다는 걸 보여주려고 넣는다 — 억지로 트리거하는 테스트를 만들 필요는 없다(mock으로
  강제하지 않는 한 불가능).
- `_pack_security_context_hash`는 `mcp.cursor_store.security_context_hash`와 **같은 공식**이지만
  별도 구현이다 — `api`↔`mcp`는 import-linter `layers` 계약에서 같은 층(`api | mcp | cli`, 독립)이라
  서로 임포트할 수 없다(바이블 §12). 공유 헬퍼를 두려면 그 아래 층(`security`)에 새 함수를 추가해야
  하는데 그러면 `mcp/cursor_store.py`(이 배치가 지정하지 않은 파일)도 고쳐야 해서 이번 배치
  범위를 벗어난다 — open_issues에 남긴다.
- `post_render`의 `pack_id` 조회 실패(엔트리 없음/만료/해시 불일치)는 **모두** 404
  `api.not_found`로 합친다(존재 비노출) — 원인별로 다른 코드/상태를 주지 않는다.
- `_prune_pack_cache`는 `post_query`가 새 엔트리를 넣기 **전에** 호출한다(매 요청 O(n) 청소 —
  이 WP 규모에서는 허용, 더 큰 캐시가 필요하면 별도 WP에서 만료 인덱스를 둔다).
- MCP `search`: `top_k`로 자르는 대상은 **관련도 순위**(`rank` 오름차순)이지 `position`이 아니다.
  예산 초과로 제거하는 대상도 선택된 부분집합 안에서 가장 낮은 관련도(가장 큰 `rank`)다. 최종
  방출 순서는 살아남은 항목을 **원래 `position` 오름차순**으로 다시 정렬한 것이다(순서 전략
  보존, `05-api/05` §5 "렌더러는 `cite_id`를 재계산하지 않는다"와 같은 취지로 `position`도 여기서
  다시 계산하지 않는다).
- 폴백(예산이 1건도 못 담을 때)은 항상 `rank=1`(`d1`) 항목이어야 한다 — `pack.items[0]`이 아니다.

## 6. 단계

1. `security_context.py`: `TooManyPrincipalsError` 추가, `derive_security_context`의 `principals`/
   `visible_set` 리터럴 교체 + 상한 검사, 모듈 docstring 갱신.
2. `query.py`: `_PackCacheEntry`/`_pack_security_context_hash`/`_prune_pack_cache` 추가.
   `post_query`: 저장 직전 `_prune_pack_cache` 호출, `cache[(tenant, pack_id)] = _PackCacheEntry(...)`.
   `post_render`(`pack_id` 분기): 엔트리 조회 → 없거나 만료면 즉시 삭제 + 404 → `pack.collection_ids`
   기준으로 `derive_security_context` 재호출(현재 자격 증명) → `as_of`는 팩에 저장된 값으로 고정해
   해시 재계산 → 불일치면 404. 모듈 docstring의 open_issues 문장(TTL·주체 바인딩 미구현) 제거.
3. `mcp/tools.py`: `_select_page_by_rank(items, top_k)` 추가(`sorted(items, key=lambda it: it.rank)`
   후 `[:min(top_k, len(items))]`). `search`에서 `pack.items[:page_count]` 대신 이 함수를 쓴다.
   `_fit_search_page_to_budget`의 절단 루프를 `working[:-1]`(마지막 **원소** 제거, 이미 `rank` 순으로
   정렬됐으므로 이게 "가장 낮은 순위 제거"와 같다) 유지하되, 반환 직전에 `working`을 `position`
   오름차순으로 재정렬한 리스트로 바꾼다(별도 슬림화 없이 `sorted(..., key=lambda s: s["_position"])`
   식으로 위치를 같이 들고 다니거나, `_slim_item` 호출 전에 `ContextItem` 리스트 단계에서 최종
   `position` 정렬을 적용). 폴백 1건도 `min(items, key=lambda it: it.rank)`(=rank 1) 사용.
4. 테스트 추가(§7), `uv run pytest -q tests/retrieval tests/api tests/mcp tests/security` 3회 이내
   통과 확인, `ruff check`로 5개 소스+테스트 파일 통과.

## 7. 테스트(파일·케이스)

- `tests/security/test_security_context.py`(신규)
  - `test_api_key_context_has_no_tenant_wildcard_and_public_only_visible_set` — `derive_security_context`
    결과의 `principals == ["service:{subject}"]`(`user:`/`tenant:*` 부재), `visible_set == ["public"]`,
    `auth_method == "api_key"`.
  - `test_api_key_context_collection_intersection_unaffected`(회귀) — `allowed_collection_ids` 교집합
    로직이 그대로 동작하는지(기존 동작 보존 확인).
- `tests/api/test_api.py`
  - `TestRender.test_render_by_pack_id_rejects_other_key_with_narrower_collections`(신규) — 키1(허용
    컬렉션 A·B)로 질의해 `pack_id` 획득 → 같은 테넌트의 키2(허용 컬렉션 A만, 원 질의는 A·B 둘 다
    반환)로 그 `pack_id`를 렌더 → 404 `api.not_found` 기대(pack.collection_ids가 A·B라 키2의 허용
    교집합이 A만이라 재계산 해시가 달라짐). 기존 `test_render_by_pack_id`(동일 키)는 그대로 200 유지.
- `tests/mcp/test_mcp_tools.py`
  - `test_search_litm_positions_keep_cite_id_contiguous_under_tight_budget`(신규) — K=5 풀을 만들되
    `_make_item`이 아니라 `position`을 바이블 §9.2 표(K=5 → `[r2,r4,r5,r3,r1]`, 즉 rank1→position4,
    rank2→position0, rank3→position3, rank4→position1, rank5→position2)로 덮어써 픽스처를 만들고,
    좁은 `max_result_tokens`로 2~3건만 남게 한 뒤 `cite_id`가 `d1..dM` 연속(구멍 없음)인지, 남은
    항목이 항상 `rank` 오름차순 부분집합(가장 낮은 순위부터 빠짐)인지 확인.
  - `test_search_top_k_selects_by_rank_not_position`(신규) — 위와 같은 K=5 픽스처, `top_k=3`·충분한
    예산으로 호출해 반환 `cite_id`가 `{"d1","d2","d3"}`인지(포지션 순으로 처음 3개를 자르면
    `{"d2","d4","d5"}`가 되어 실패했을 버그) 확인.

## 8. 완료 기준

- 위 3개 테스트 파일이 `uv run pytest -q tests/retrieval tests/api tests/mcp tests/security`에서
  전부 통과(회귀 없음).
- 3건 수정 각각을 되돌려 새 테스트가 재현하는지 확인.
- `ruff check`가 수정한 3개 소스 파일 + 관련 테스트 파일에서 통과.

## 9. 검증 계층·DEFERRED

1층(여기서 검증) — 순수 함수·인메모리 캐시·`TestClient`, 외부 자원 없음.
DEFERRED: 없음(이 3건은 F4/F5 스텁 범위 안에서 완결).

## 10. open_issues

- `_pack_security_context_hash`(query.py)와 `mcp.cursor_store.security_context_hash`가 같은 공식을
  독립 구현한다 — `security` 패키지에 공유 함수를 두는 리팩터는 `mcp/cursor_store.py` 동시 수정이
  필요해 이 배치(지정 파일 3개) 범위 밖이다. 다음 배치에서 `security.security_context_hash`로
  승격하고 두 호출부를 갈아 끼우는 편을 권한다.
- `pack_cache`는 여전히 프로세스 내 dict다(Valkey 아님, `05-api/03` §4.4가 원하는 `pack:{tenant}:
  {pack_id}` Valkey 키는 그대로 open_issues) — 이번 수정은 주체 바인딩·TTL·크기 상한만 인메모리
  수준에서 채운다.

## 결과: 통과 8(신규: security 5 · api 1 · mcp 2) + 136(기존, 회귀 없음) = 144/144 / xfail 0 /
DEFERRED 0. 3건 모두 되돌려 새/수정 테스트가 재현함을 확인(security: `principals`에 `tenant:*`
포함·`visible_set=[public,tenant]`로 실패; api: 다른 허용 컬렉션 키의 렌더가 200으로 새 버그
재현; mcp: `top_k`가 `{d2,d4,d5}`를 고르고 예산 절단이 `d1`을 남기지 않는 것을 확인 — 이 과정에서
`_make_litm_pool` 픽스처가 `position` 정렬 없이 `rank` 순서 그대로 반환해 버그를 가리던 결함도
같이 고쳤다).
