"""`enricher.deterministic_prefix` — 결정적 접두어로 `embed_text`·`index_text`·`strip_offsets`를 조립한다.

역할: `enrich` 체인(04-pipelines/11 §2.1 표) 순서 1 — 다른 모든 보강기의 전제가 되는 3-텍스트(Three-Text
Rule) 조립기다(F2-03, WP-203).
설계 근거: 04-pipelines/11 §3(`embed_text`·`index_text` 조립 규약)·§4(결정적 보강), ADR-0029(3-텍스트
규칙과 결정적 `context_prefix`), 바이블 §5.4 `Enrichment`.
구성: `EnrichmentAccumulator` — 세 결정적 보강 모듈이 공유하는 `acc[chunk_id]` 모양(타입 별칭);
`assemble_texts(chunk)` — 순수 함수로 `embed_text`/`index_text`/`StripOffsets` 계산; `DeterministicPrefixConfig`
— 빈 설정(조립식은 ADR-0029 고정, 프로파일로 바꿀 수 없다); `DeterministicPrefixEnricher` — `plugin_id`/
`config_schema`/`capabilities()`/`fingerprint()`/`enrich()`.
불변식·주의: `context_prefix.deterministic`은 `chunk` 스테이지 산출을 바이트 그대로 쓴다(재계산 금지).
LLM 접두어(G)는 이 WP 범위 밖(기본 꺼짐)이라 `embed_text = deterministic + LF + text` 고정. `acc`에는
이 모듈이 담당하는 `embed_text`/`index_text`/`strip_offsets` 키만 쓴다.
검증 계층: 1층(여기서 검증) — `tests/adapters/enrich/test_enrich.py`.
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import MutableMapping
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from rag_platform.contracts import common_types as ct
from rag_platform.sdk.hashing import hash_of

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "PLUGIN_VERSION",
    "DeterministicPrefixConfig",
    "DeterministicPrefixEnricher",
    "EnrichmentAccumulator",
    "assemble_texts",
]

#: 세 결정적 보강 모듈(deterministic_prefix·korean_keywords·derived_meta)이 공유하는 누산기 모양
#: (04-pipelines/11 §2.2 초안 `EnrichmentAccumulator`). 각 모듈은 자기 필드만 쓴다. 런타임에 실제로
#: 평가되는 별칭이라 `MutableMapping`/`Any`는 `TYPE_CHECKING` 밖에서 가져온다(ruff TC 규칙).
EnrichmentAccumulator = MutableMapping[str, MutableMapping[str, Any]]

PLUGIN_VERSION = "0.1.0"

#: 청크 N개마다 재개 커서를 남긴다(04-pipelines/11 §2.2 재개 행 초안 N=50).
_HEARTBEAT_EVERY = 50


def assemble_texts(chunk: ct.Chunk) -> tuple[str, str, ct.StripOffsets]:
    """ADR-0029 3-텍스트 조립식으로 `embed_text`/`index_text`/`strip_offsets`를 계산한다.

    LLM 생성 접두어(G)는 이 WP 범위 밖(기본 꺼짐)이므로 `embed_text = deterministic + LF + text`,
    `index_text = NFKC(deterministic) + LF + lexical_text`로 고정한다(ADR-0029 §결정 표).

    Args:
        chunk: 조립 대상 청크(`text`/`lexical_text`/`context_prefix.deterministic`을 읽기 전용으로 사용).

    Returns:
        `(embed_text, index_text, strip_offsets)` 튜플. 오프셋은 코드포인트 기준.
    """
    deterministic = chunk.context_prefix.deterministic
    embed_text = f"{deterministic}\n{chunk.text}"
    prefix_lexical = unicodedata.normalize("NFKC", deterministic)
    index_text = f"{prefix_lexical}\n{chunk.lexical_text}"
    strip_offsets = ct.StripOffsets(
        text_start_in_embed=len(deterministic) + 1,
        text_start_in_index=len(prefix_lexical) + 1,
    )
    return embed_text, index_text, strip_offsets


class DeterministicPrefixConfig(BaseModel):
    """`enricher.deterministic_prefix`의 설정 스키마 — 조정 가능한 값 없음(ADR-0029가 조립식을 고정)."""

    model_config = ConfigDict(extra="forbid")


class DeterministicPrefixEnricher:
    """`enricher.deterministic_prefix` — 체인 순서 1(04-pipelines/11 §2.1 표)."""

    plugin_id = "enricher.deterministic_prefix"
    config_schema = DeterministicPrefixConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: DeterministicPrefixConfig | None = None) -> None:
        """설정을 고정한다(현재 필드 없음, 향후 `config_hash`/`fingerprint()` 입력 자리만 유지)."""
        self.config = config or DeterministicPrefixConfig()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """결정적 보강기 공통 선언(04-pipelines/11 §2.2 표): `in_process`, 재개 지원, `determinism=pure`."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=True,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=[],
            requires_gpu=False,
            extra={"determinism": "pure"},
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(모델 없음, 바이블 §6.2)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def enrich(
        self,
        chunks: Sequence[ct.Chunk],
        ctx: Any,
        acc: EnrichmentAccumulator,
    ) -> None:
        """청크마다 `assemble_texts`를 실행해 `acc[chunk_id]`에 조립 결과 3필드만 쓴다.

        Args:
            chunks: 이 세트의 청크(리프·부모·상위 파생 모두; 도해는 항상 계산한다).
            ctx: `StageContext`(순수 함수라 `heartbeat` 외에는 쓰지 않는다).
            acc: `chunk_id(str) -> 부분 Enrichment 필드 매핑` 누산기(04-pipelines/11 §2.2).
        """
        for index, chunk in enumerate(chunks):
            embed_text, index_text, strip_offsets = assemble_texts(chunk)
            bucket = acc.setdefault(chunk.chunk_id.root, {})
            bucket["embed_text"] = embed_text
            bucket["index_text"] = index_text
            bucket["strip_offsets"] = strip_offsets
            if (index + 1) % _HEARTBEAT_EVERY == 0:
                ctx.heartbeat({"chunk_offset": index + 1})
