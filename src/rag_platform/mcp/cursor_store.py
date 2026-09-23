"""MCP 커서 저장소 — `search`/`get_document` "더 보기" 핸들의 발급·해석(05-api/05 §6, ADR-0025).

역할: 서버 발행 불투명 핸들(`cursor`/`next_cursor`)을 `storage.valkey.KeyValueCache` 포트 위에
`cursor:{tenant_id}:{cursor_id}`(TTL 10분)로 저장·조회하고, 해석 시 테넌트·주체 바인딩을
재대조한다(05 §6.2~§6.3). 커서는 검색 결과 자체를 담지 않는다 — 다음 페이지는 저장된 요청 +
누적 `seen_chunk_ids`로 전체 검색 경로를 다시 실행해야 한다(호출부인 `tools.py`의 몫).
설계 근거: `docs/05-api/05-mcp-server.md` §6(모델·`CursorRecord`·주체 바인딩 대조·만료/불일치/
Valkey 불가), ADR-0025(결정 딸린 세부: 커서 키·주체 바인딩·`isError` 표현), 바이블 §13.4
(`cursor:{tenant}:{ulid}` 10분, 모든 테넌트 스코프 키는 `{tenant}` 접두 필수).
구성: `CursorRecord`(05 §6.2 표의 필드 부분집합 — `query_request`/`seen_chunk_ids`는 `search`
전용, `document_id`/`view`/`block_offset`은 `get_document` 전용); `security_context_hash()` —
05 §6.3 결합 해시(`sdk.hashing.hash_of` 재사용); `CursorStore.issue`/`redeem`.
불변식·주의: 이 모듈은 `rag_platform.testing`을 임포트하지 않는다(운영 KV는 호출부가
`storage.valkey.KeyValueCache` 구현체를 주입한다 — 테스트는 `testing.doubles.InMemoryKV`를
그 자리에 주입, import-linter `testing-not-in-production`). 키는 `_cursor_key()`로만 만들어
`{tenant_id}` 접두 없는 키가 생성될 수 없다(E17). `redeem()`은 만료·변조(ULID 형식 아님)·다른
테넌트·다른 도구·주체 불일치를 모두 `None`으로 반환한다(존재 비노출, 05 §6.4) — 원인을 구분하는
로그는 호출부 책임이 아니라 이 모듈 밖(관측성)에서 남긴다. `issue()`가 `None`을 반환하면 Valkey
발급 실패(§6.4 3행) — 호출부는 `truncated=false, next_cursor=null`로 응답해야 한다(11 P-14
`truncated ⇒ next_cursor` 위반 방지).
검증 계층: 1층(여기서 검증) — `tests/mcp/test_mcp_tools.py`(`InMemoryKV` 주입). `# DEFERRED: 실
Valkey 서버 대상 TTL·동시성 검증은 needs_docker(phase-6 계획 §8 tier 2)`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Literal

from ulid import ULID

from rag_platform.sdk.hashing import hash_of

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.storage.valkey import KeyValueCache

__all__ = ["DEFAULT_CURSOR_TTL_S", "CursorRecord", "CursorStore", "security_context_hash"]

#: 바이블 §13.4 `cursor:{tenant}:{ulid}` 기본 TTL(초). `RAG_CACHE__CURSOR_TTL`의 코드 기본값(05 §6.1).
DEFAULT_CURSOR_TTL_S = 600

_ToolName = Literal["search", "get_document"]


def _cursor_key(tenant_id: str, cursor_id: str) -> str:
    """`cursor:{tenant_id}:{cursor_id}`(바이블 §13.4) — 이 함수만이 커서 키를 만든다(E17)."""
    return f"cursor:{tenant_id}:{cursor_id}"


def security_context_hash(
    *,
    tenant_id: str,
    principals: Sequence[str],
    collection_ids: Sequence[str],
    as_of: str,
    classification_max: str,
    visible_set: Sequence[str],
) -> str:
    """05 §6.3 결합 해시 ``H("sec", tenant_id, sorted(principals), ...)``를 계산한다.

    발급 시점은 그 요청의 `SecurityContext`로, 해석 시점은 현재 `SecurityContext`의 주체·등급·
    가시 집합에 저장된 `as_of`와 `collection_ids' = 현재 allowed ∩ 저장 collection_ids`를 넣어
    재계산한다(`CursorStore.redeem`이 수행).
    """
    return hash_of(
        "sec",
        tenant_id,
        ",".join(sorted(principals)),
        ",".join(sorted(collection_ids)),
        as_of,
        classification_max,
        ",".join(sorted(visible_set)),
    )


@dataclass(frozen=True)
class CursorRecord:
    """Valkey 값(05 §6.2 표). `tool`에 따라 `search`/`get_document` 전용 필드만 채워진다."""

    tenant_id: str
    tool: _ToolName
    offset: int
    security_context_hash: str
    as_of: str
    issued_at: str
    expires_at: str
    index_generations_seen: tuple[int, ...] = ()
    # `search` 전용(05 §6.2)
    query_id: str | None = None
    query_request: dict[str, Any] | None = None
    seen_chunk_ids: tuple[str, ...] = ()
    # `get_document` 전용(05 §6.2)
    document_id: str | None = None
    view: str | None = None
    block_offset: int | None = None

    def to_json_bytes(self) -> bytes:
        """단순 JSON 직렬화(해시 입력이 아니므로 바이블 §6.2 canonical_json 불요)."""
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True).encode("utf-8")

    @classmethod
    def from_json_bytes(cls, data: bytes) -> CursorRecord:
        """`to_json_bytes()`의 역. `tuple` 필드는 JSON 배열로 왕복하므로 여기서 복원한다."""
        raw = json.loads(data.decode("utf-8"))
        raw["index_generations_seen"] = tuple(raw.get("index_generations_seen") or ())
        raw["seen_chunk_ids"] = tuple(raw.get("seen_chunk_ids") or ())
        return cls(**raw)


class CursorStore:
    """`KeyValueCache` 포트 위의 커서 발급·해석(05 §6). 포트 구현은 호출부가 주입한다."""

    def __init__(self, kv: KeyValueCache, *, ttl_s: int = DEFAULT_CURSOR_TTL_S) -> None:
        """`kv`는 운영에서 Valkey 어댑터, 테스트에서 `testing.doubles.InMemoryKV`."""
        self._kv = kv
        self._ttl_s = ttl_s

    @property
    def ttl_s(self) -> int:
        """현재 인스턴스의 커서 TTL(초) — 호출부가 `expires_at`을 계산할 때 참조한다."""
        return self._ttl_s

    async def issue(self, record: CursorRecord) -> str | None:
        """레코드를 저장하고 새 `cursor_id`(ULID)를 반환한다. Valkey 발급 실패 시 `None`(05 §6.4)."""
        cursor_id = str(ULID())
        key = _cursor_key(record.tenant_id, cursor_id)
        try:
            await self._kv.set(key, record.to_json_bytes(), ttl_s=self._ttl_s)
        except Exception:  # noqa: BLE001 - Valkey 불가는 폴백 경로(05 §6.4), 예외 종류를 가리지 않는다
            return None
        return cursor_id

    async def redeem(  # noqa: PLR0911 - guard clauses read clearer than one combined boolean (05 §6.4 cases)
        self,
        *,
        tenant_id: str,
        cursor_id: str,
        tool: _ToolName,
        principals: Sequence[str],
        collection_ids: Sequence[str],
        classification_max: str,
        visible_set: Sequence[str],
    ) -> CursorRecord | None:
        """해석해 반환하거나, 만료·변조·다른 도구·주체 불일치면 `None`(존재 비노출, 05 §6.4).

        테넌트 바인딩은 키 자체가 `{tenant_id}`를 접두로 가지므로(E17) 다른 테넌트가 같은
        `cursor_id`를 제시해도 그 테넌트의 키에는 값이 없어 자연히 실패한다. 주체 바인딩(§6.3)은
        저장된 `as_of`를 고정하고 현재 `principals`/`classification_max`/`visible_set`과
        `collection_ids' = 현재 allowed(collection_ids) ∩ 저장 collection_ids`(search 전용 —
        `get_document`는 저장된 컬렉션 집합이 없으므로 현재 값을 그대로 쓴다)로 해시를 재계산해
        저장 값과 대조한다 — 호출부는 해시를 스스로 계산하지 않는다.
        """
        if not _looks_like_ulid(cursor_id):
            return None
        key = _cursor_key(tenant_id, cursor_id)
        try:
            raw = await self._kv.get(key)
        except Exception:  # noqa: BLE001 - Valkey 해석 실패는 만료와 같은 커서 오류(05 §6.4)
            return None
        if raw is None:
            return None
        try:
            record = CursorRecord.from_json_bytes(raw)
        except (ValueError, TypeError, KeyError):
            return None
        if record.tool != tool or record.tenant_id != tenant_id:
            return None
        effective_collection_ids = collection_ids
        if record.query_request is not None:
            stored_collection_ids = set(record.query_request.get("collection_ids") or [])
            effective_collection_ids = sorted(set(collection_ids) & stored_collection_ids)
        recomputed = security_context_hash(
            tenant_id=tenant_id,
            principals=principals,
            collection_ids=effective_collection_ids,
            as_of=record.as_of,
            classification_max=classification_max,
            visible_set=visible_set,
        )
        if recomputed != record.security_context_hash:
            return None
        return record


_ULID_LENGTH = 26


def _looks_like_ulid(value: str) -> bool:
    """26자 Crockford base32(대문자, `I`·`L`·`O`·`U` 제외)인지 얕게 검사(§6.4 "변조" 판정)."""
    if len(value) != _ULID_LENGTH:
        return False
    alphabet = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    return all(char in alphabet for char in value)
