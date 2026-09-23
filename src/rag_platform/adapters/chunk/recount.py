"""`recount` 스테이지 — 임베더 교체로 `token_counts` 키가 빠졌을 때 토큰 수만 다시 센다(F2-02).

역할: 바이블 §3.2 O-09/ADR-0019가 정의하는 `ChunkSet → ChunkSet` 스테이지. 재청킹(`chunker.*`
재실행)이 아니라 `ctx.token_counter`가 가리키는 대상 토크나이저 하나로 `chunks[].text`를 다시 세어
`token_counts`에 키를 채우고 `secondary_tokenizer_ids`에 누적한다. `span`·`chunk_id`·`block_refs`·
`item_kind`·`level`·`parent_chunk_id`·`lineage_refs`·`chunk_set_id`·`chunker_id`·
`chunker_config_hash`·`token_budgets`는 입력 그대로 보존한다(바이블 §4.1 stage_key 표 "recount는
fingerprint 자리에 tokenizer_id를 포함한 지문을 쓴다" — 대상 토크나이저는 `config`에 실려
`config_hash`/`fingerprint`를 통해 이미 반영된다, 별도 특수 처리 불필요).
설계 근거: 바이블 §3.2 O-09("임베더 교체 시 token_counts 키 누락이면 recount 스테이지(재청킹
아님)"), §4.1(5멤버 스테이지·`stage_key`), §5.4 `ChunkSet`(`secondary_tokenizer_ids`: "recount가
추가한 tokenizer_id도 여기에 누적된다"); ADR-0019, ADR-0032; 계약 `contracts/chunk_set.py`.
구성: `RecountConfig` — `config_schema`(대상 `tokenizer_id` 하나); `RecountStage` — Stage 5멤버
(`plugin_id`/`config_schema`/`capabilities()`/`fingerprint()`/`run()`).
불변식·주의: `ctx.token_counter.tokenizer_id != config.tokenizer_id`면 실행하지 않고
`chunk.tokenizer_missing`(§5.7 카탈로그에 `recount.*` 전용 코드가 없어 재사용 — WP-202 open issue)을
던진다. `adapters`는 `storage`/`security`를 import하지 않는다. `pydantic.model_copy`는 검증을 건너뛰므로
갱신 필드에는 이미 유효한 계약 인스턴스만 대입한다(원본 값 재사용 또는 새 인스턴스 생성, 원시 dict 금지).
검증 계층: 1층(여기서 검증) — tests/adapters/chunk/test_table_rows.py(recount 케이스). `needs_docker`/
`needs_model`/`needs_gpu`/`needs_network` 해당 없음.
"""

from __future__ import annotations

import json
from datetime import UTC
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from rag_platform.contracts import common_types as ct
from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from datetime import datetime

    from rag_platform.contracts.chunk_set import ChunkSet

__all__ = ["RecountConfig", "RecountStage"]

PLUGIN_VERSION = "0.1.0"
#: `common_types.TokenizerId`/`TokenCounts1` 키 철자 정본(바이블 §6.1).
_TOKENIZER_ID_PATTERN = r"^(hf|tiktoken|anthropic|gemini):\S+$"


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


class RecountConfig(BaseModel):
    """`recount.token_counter`의 설정 스키마 — 대상 `tokenizer_id` 하나(O-09).

    임베더 교체 이벤트 하나가 보통 토크나이저 하나를 새로 요구하므로(§3.2 O-09), 이 스테이지 호출
    1회는 토크나이저 1개만 다룬다. 여러 개가 빠졌다면 셸이 `recount`를 여러 번 체이닝한다.
    """

    model_config = ConfigDict(extra="forbid")

    tokenizer_id: str = Field(..., pattern=_TOKENIZER_ID_PATTERN)


class RecountStage:
    """`recount.token_counter` — 재청킹 없이 `token_counts`만 갱신하는 `Stage[ChunkSet, ChunkSet]`."""

    plugin_id = "recount.token_counter"
    config_schema = RecountConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: RecountConfig) -> None:
        """대상 토크나이저를 고정한다(`config`는 `config_hash` → `fingerprint` → `stage_key` 입력)."""
        self.config = config

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`, 재개 미지원, GPU 불필요(카운팅만 하는 순수 함수 스테이지)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=[],
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", tokenizer_id)`.

        `config_hash`가 이미 `config.tokenizer_id`를 포함하므로, 같은 `ChunkSet`에 다른 대상
        토크나이저로 `recount`를 두 번 실행하면 `fingerprint`(→ `stage_key`)가 자동으로 달라진다
        (바이블 §4.1 "recount는 fingerprint 자리에 tokenizer_id를 포함한 지문을 쓴다"의 실현).
        """
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", self.config.tokenizer_id)

    async def run(self, inp: ChunkSet, ctx: Any) -> ChunkSet:
        """`inp.chunks[].text`를 `config.tokenizer_id`로 다시 세어 `token_counts`를 채운 `ChunkSet`."""
        target = self.config.tokenizer_id
        token_counter = ctx.token_counter
        if token_counter.tokenizer_id != target:
            code = "chunk.tokenizer_missing"
            detail = (
                f"ctx.token_counter.tokenizer_id={token_counter.tokenizer_id!r} != "
                f"config.tokenizer_id={target!r} (recount does not re-chunk; the shell must wire "
                "the TokenCounter matching this stage's config, 바이블 §3.2 O-09)"
            )
            raise StageError(code, stage="recount", plugin_id=self.plugin_id, detail=detail)

        new_chunks: list[ct.Chunk] = []
        for chunk in inp.chunks:
            counts = {tokenizer_id: count.root for tokenizer_id, count in chunk.token_counts.root.items()}
            counts[target] = token_counter.count(chunk.text)
            updated = chunk.model_copy(update={"token_counts": ct.TokenCounts1(root=counts)})  # type: ignore[arg-type]
            new_chunks.append(updated)

        primary_str = inp.primary_tokenizer_id.root
        secondary = list(inp.secondary_tokenizer_ids)
        already_tracked = target == primary_str or any(item.root == target for item in secondary)
        if not already_tracked:
            secondary.append(ct.TokenizerId(target))

        return inp.model_copy(
            update={
                "chunks": new_chunks,
                "secondary_tokenizer_ids": secondary,
                "producer": ct.Producer(
                    plugin_id=self.plugin_id,
                    plugin_version=PLUGIN_VERSION,
                    config_hash=self.config_hash(),
                    image_digest=None,
                ),
                "created_at": ct.DateTime(_rfc3339_ms(ctx.now())),
            }
        )
