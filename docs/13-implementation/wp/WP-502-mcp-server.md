---
title: "WP-502 MCP 서버"
status: active
version: 0.1.0
---

# WP-502 MCP 서버 (F5-02, mcp-server)

## 0. 실행 배경(병렬 배치 주의)

F5 배치의 다른 에이전트가 `api/`·`cli/` 등 인접 파일을 동시에 편집한다. 이 WP는
`src/rag_platform/mcp/{server.py,tools.py,cursor_store.py}`·`tests/mcp/test_mcp_tools.py`만
쓴다. `pipelines/query.py`가 정의하는 `QueryPipelineDeps`(F4-04)는 F4-01~03 실 모듈(`retrieval.*`)
배선이 아직 없다(그 파일 자체의 주석: "배선은 F5(api/mcp/cli) 몫"). 이 WP는 그 배선을 하지
않는다 — `tools.py`는 `ContextPack`을 만드는 방법을 몰라도 되도록 **자체 Protocol**
(`QueryRunner`/`DocumentReader`/`CollectionLister`)로 경계를 긋고, 실 배선(질의 파이프라인 조립,
문서 조회 함수, 컬렉션 레지스트리 조회)은 이후 WP(`api`와 공유하는 서비스 계층 조립)의 몫으로
남긴다(open_issues).

## 1. 목표

1. MCP 도구 3종(`search`, `get_document`, `list_collections`) 핸들러를 `mcp/tools.py`에
   순수 함수로 구현한다 — SDK 세션·전송 없이 직접 호출·단위 테스트 가능.
2. 커서 저장소(`mcp/cursor_store.py`)를 `storage.valkey.KeyValueCache` 포트 위에 구현한다
   (운영은 Valkey, 테스트는 `testing.doubles.InMemoryKV`를 주입 — 프로덕션 코드는
   `testing`을 임포트하지 않는다, import-linter `testing-not-in-production`).
3. `mcp/server.py`에 공식 SDK(`mcp>=2,<3`, ADR-0025 §12) 기반 stdio 진입점을 얇게 구성한다.

## 2. 파일

- `src/rag_platform/mcp/tools.py`
- `src/rag_platform/mcp/cursor_store.py`
- `src/rag_platform/mcp/server.py`
- `tests/mcp/test_mcp_tools.py`

## 3. 시그니처

```python
# mcp/cursor_store.py
DEFAULT_CURSOR_TTL_S: int = 600

@dataclass(frozen=True)
class CursorRecord:
    cursor_id: str; tenant_id: str; tool: Literal["search", "get_document"]
    offset: int; security_context_hash: str; as_of: str; issued_at: str; expires_at: str
    index_generations_seen: tuple[int, ...] = ()
    query_id: str | None = None; query_request: dict[str, Any] | None = None
    seen_chunk_ids: tuple[str, ...] = ()
    document_id: str | None = None; view: str | None = None; block_offset: int | None = None

def security_context_hash(*, tenant_id: str, principals: Sequence[str], collection_ids: Sequence[str],
                           as_of: str, classification_max: str, visible_set: Sequence[str]) -> str: ...

class CursorStore:
    def __init__(self, kv: KeyValueCache, *, ttl_s: int = DEFAULT_CURSOR_TTL_S) -> None: ...
    async def issue(self, record: CursorRecord) -> str | None: ...  # None = Valkey 발급 실패(§6.4)
    async def redeem(self, *, tenant_id: str, cursor_id: str, tool: Literal["search", "get_document"],
                      current_hash: str) -> CursorRecord | None: ...  # None = 만료·변조·불일치(존재 비노출)

# mcp/tools.py
class QueryRunner(Protocol):
    async def __call__(self, request: QueryRequest, security: SecurityContext) -> ContextPack: ...
class DocumentReader(Protocol):
    async def __call__(self, document_id: str, view: str, security: SecurityContext) -> DocumentContent | None: ...
class CollectionLister(Protocol):
    async def __call__(self, security: SecurityContext) -> list[CollectionSpec]: ...

@dataclass(frozen=True)
class ToolDeps:
    query_runner: QueryRunner; document_reader: DocumentReader; collection_lister: CollectionLister
    cursor_store: CursorStore

@dataclass(frozen=True)
class ToolResult:
    is_error: bool; structured_content: dict[str, Any]; text: str

async def search(args: dict[str, Any], security: SecurityContext, deps: ToolDeps) -> ToolResult: ...
async def get_document(args: dict[str, Any], security: SecurityContext, deps: ToolDeps) -> ToolResult: ...
async def list_collections(args: dict[str, Any], security: SecurityContext, deps: ToolDeps) -> ToolResult: ...

# mcp/server.py
def build_server(deps: ToolDeps) -> mcp.server.mcpserver.MCPServer: ...
async def serve_stdio(deps: ToolDeps) -> None: ...
def main() -> None: ...  # `rag mcp serve --stdio` 진입점 대상(배선은 cli WP 몫)
```

## 4. 입출력 계약 발췌(정본 철자, 05-api/05 §4·§5·§6 / ADR-0025)

- 도구 인자(§14 `/mcp` 행, 05 §4.2~4.4): `search(query, collection_ids?, top_k?, filters?,
  response_format?, cursor?)`, `get_document(document_id, view?, cursor?)`, `list_collections()`.
  `top_k` 1..50 기본 10(MCP는 페이지 크기로 씀). `response_format ∈ {concise, detailed}`(MCP
  부분집합, 기본 `concise`). `view ∈ {parsed, normalized, chunks}` 기본 `normalized`.
- 오류 코드(`contracts.common_types.ErrorCodeCatalog`, 철자 그대로): `contract_violation =
  "contract.violation"`(인자 스키마 위반·금지 필드·허용 컬렉션>20 생략·만료/불일치 커서, 채택
  전까지 `cursor` 오류도 이 코드), `plan_collection_forbidden = "plan.collection_forbidden"`(교집합
  빈 집합), `plan_filter_field_forbidden = "plan.filter_field_forbidden"`. 텍스트 형식:
  `"{code} ({pointer}): {detail}. {hint}"`(05 §8).
- 슬림 팩 outputSchema(05 §4.2): `{schema_version, pack_id, items[]{cite_id, chunk_id,
  collection_id, document_id, header, text_preview|text, confidence_tier, text_source,
  provenance}, sufficiency, truncated, next_cursor}`. `Header`·`Provenance`·`Sufficiency`는
  `contracts.common_types.Header`/`Provenance`, `contracts.context_pack.Sufficiency`의 필드 집합과
  1:1 동일(각각 `model_dump(mode="json")`으로 그대로 투영 가능 — 별도 매핑 불요).
  `FilterableField`(`contracts.common_types.FilterableField`, `custom.*`는 `FilterableField3`)
  화이트리스트 밖 필드는 `plan.filter_field_forbidden`.
- 커서(05 §6.1~§6.4, ADR-0025): 키 `cursor:{tenant_id}:{cursor_id}`(Valkey, TTL 600s), 값
  `CursorRecord`(05 §6.2 표). 주체 바인딩(§6.3): `H("sec", tenant_id, ",".join(sorted(principals)),
  ",".join(sorted(collection_ids')), 저장 as_of, classification_max, ",".join(sorted(visible_set)))`
  — `hash_of`(`sdk.hashing`) 재사용, `collection_ids'= 현재 security.collection_ids ∩ 저장
  collection_ids`. 불일치·만료·다른 테넌트·다른 도구는 모두 커서 오류(존재 비노출, §6.4).
  Valkey 발급 실패 시 `truncated=false, next_cursor=null`(P-14 위반 방지, §6.4 표 3행) — ADR-0025
  "부정" 절의 `truncated=true/next_cursor=null` 폴백은 **채택하지 않는다**(05 §6.4 명시).
- 결과 크기(05 §5.1): `max_result_tokens = 20,000`(초안), 절단 순서 (1) `items` →
  `min(top_k, len(pack.items))` (2) 상한 초과면 하위 순위부터 제거 (3) 1건도 못 담으면 `concise`로
  강등 재시도. `truncated ⇔ (제거 항목 > 0) ∨ (top_k < len(pack.items)) ∧ next_cursor 발급 성공`.
- 안내 문구(05 §9.3 정본, 한/영 병기 그대로 사용): "정상·더 있음"/"정상·끝"/"충분성 부족"/
  "커서 발급 불가"/"제외 상한"/"get_document 더 있음" 6종.
- `get_document` outputSchema(05 §4.3): `DocBlock{block_id, type, level, numbering_label,
  heading_path, text, text_source, page, element_path}`, `DocChunk{chunk_id, item_kind, level,
  parent_chunk_id, ordinal, heading_path, text, text_source}`. `document_id` 미존재·ACL 거부는
  존재 비노출(`contract.violation` `/document_id`, 05 §8 표 — `api.not_found` 전환은 미채택).

## 5. 불변식·금지

1. `mcp/`는 코어 검색·문서조회 로직을 재구현하지 않는다 — `QueryRunner`/`DocumentReader`/
   `CollectionLister` Protocol 뒤에 숨기고 실 배선은 다른 WP가 채운다(패키지 `__init__.py` 불변식
   그대로 유지).
2. 프로덕션 코드(`server.py`/`tools.py`/`cursor_store.py`)는 `rag_platform.testing`을 임포트하지
   않는다(import-linter `testing-not-in-production`) — KV 인메모리 대역은 테스트 파일에서만
   `testing.doubles.InMemoryKV`를 주입한다.
3. 커서 키는 `cursor_store.py`가 `{tenant_id}:{cursor_id}` 조합으로만 만든다 — `{tenant}` 접두 없는
   키 생성 API를 제공하지 않는다(E17, ADR-0025 준수 확인 4).
4. 슬림 팩·오류 결과에 `tenant_id`·주체 문자열·`acl_*`·`record_id`·원시 점수를 넣지 않는다(05 §5
   표, §9.3 공통 규칙 1).
5. 계약 생성물(`contracts/*`)은 손대지 않는다 — 읽기만.
6. 공용 파일(`pyproject.toml`)은 이 WP가 도입하는 `mcp>=2,<3` 의존성 한 줄만 추가한다(주석이
   이미 "이 코드를 import하는 WP가 추가" 규약을 명시); 그 외 공용 파일은 건드리지 않는다.

## 6. 단계

1. `cursor_store.py`: `CursorRecord`(dataclass, canonical 아닌 단순 JSON 직렬화 — Valkey 값은
   해시 입력이 아니므로 `json.dumps(sort_keys=True)`로 충분), `security_context_hash`, `CursorStore`
   (`issue`/`redeem`, ULID 발급은 `python-ulid`).
2. `tools.py`: Protocol 3종 + `ToolDeps`/`ToolResult`, 슬림 아이템·XML 텍스트·안내 문구 빌더,
   20k 토큰 절단 루프(근사 카운터: `ceil(len(text)/4)` — 실 토크나이저 연동은 DEFERRED),
   오류 빌더(`ProblemDetails` + 텍스트 한 줄), 세 핸들러(`search`/`get_document`/
   `list_collections`).
3. `server.py`: `MCPServer` 생성(`mcp.server.mcpserver.MCPServer`), 도구 3종을 `tools.py` 핸들러로
   등록(`CallToolResult` 직접 구성), `run_stdio_async` 진입점.
4. `pyproject.toml`: `uv add "mcp>=2,<3"`(ADR-0025 SDK 핀; 이번 지시문의 `mcp>=1,<3` 제안보다
   좁은 ADR 값을 정본으로 채택 — open_issues 1행).
5. `tests/mcp/test_mcp_tools.py`: 페이크 `QueryRunner`/`DocumentReader`/`CollectionLister` +
   `InMemoryKV` 기반 `CursorStore`로 핸들러 직접 호출 검증.

## 7. 테스트(파일·케이스)

`tests/mcp/test_mcp_tools.py`:

- `test_search_basic_returns_slim_pack_and_xml_text` — 항목 2개, `truncated=false`.
- `test_search_collection_ids_omitted_defaults_to_security_context`
- `test_search_collection_ids_forbidden_intersection_empty` — `plan.collection_forbidden`.
- `test_search_more_than_20_accessible_without_collection_ids` — `contract.violation` `/collection_ids`.
- `test_search_filter_field_forbidden` — `plan.filter_field_forbidden`.
- `test_search_top_k_pagination_issues_cursor_and_seen_chunk_ids_accumulate`
- `test_search_cursor_redeem_reruns_with_exclude_ids`
- `test_search_cursor_wrong_tenant_rejected` — 존재 비노출(`contract.violation` `/cursor`).
- `test_search_cursor_wrong_tool_rejected` — `get_document` 커서를 `search`에 제시.
- `test_search_response_format_detailed_uses_full_text`
- `test_search_result_token_budget_truncates_from_lowest_rank`(작은 `max_result_tokens` 주입)
- `test_search_valkey_unavailable_falls_back_truncated_false`
- `test_get_document_normalized_view_default`
- `test_get_document_not_found_is_contract_violation_not_api_not_found`(존재 비노출)
- `test_get_document_chunks_view`
- `test_get_document_cursor_continues_at_block_offset`
- `test_list_collections_projects_allowed_only`
- `test_list_collections_empty`

## 8. 완료 기준

`uv run pytest -q tests/mcp/test_mcp_tools.py` 전부 통과, `uv run ruff check
src/rag_platform/mcp/server.py src/rag_platform/mcp/tools.py src/rag_platform/mcp/cursor_store.py
tests/mcp/test_mcp_tools.py` 통과. mypy는 배치 검증자가 별도 실행.

## 9. 검증 계층·DEFERRED

1층(여기서 검증) — 위 테스트 파일, 핸들러 직접 호출(SDK 서버 미기동). `# DEFERRED: 실 SDK
stdio 서버 기동 대상 적합성 테스트(@modelcontextprotocol/conformance --spec-version 2026-07-28)는
needs_network(Node 런타임) — 05-api/05 §13`. `# DEFERRED: 실 QueryRunner/DocumentReader/
CollectionLister 배선(retrieval.* 실 모듈 + 문서조회 서비스)과 그 위의 e2e는 이후 WP(api/mcp 공유
서비스 계층 조립) 몫`. `# DEFERRED: render.mcp_tool_result/render.xml_documents 전용 렌더러 모듈
승격(현재 tools.py 내부 헬퍼로 구현, open_issues 참고)`. 모델·Docker·GPU 의존 없음.

결과: 통과 18 / xfail 0 / DEFERRED 3
