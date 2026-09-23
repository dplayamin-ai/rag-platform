"""`query_transformer.korean_normalize` — `KoreanNormalizeTransformer` Stage 5멤버 래퍼(ADR-0032).

역할: `plan` 파이프 첫 단계(04-pipelines/14 §1.1 `normalize_ko`)의 순수 구현은 `rag_platform.korean.
normalize`(바이블 §12상 `retrieval`도 import할 수 있는 `korean` 층)에 있다 — 이 모듈은 그 함수들을
재노출하고, `PluginRegistry`가 조회할 `QueryTransformer` 프로토콜 래퍼(`config_schema`·
`capabilities()`·`fingerprint()`·`run(draft, ctx)`)만 더한다.
설계 근거: 04-pipelines/14 §2(정규화)·§6(키워드), ADR-0021(Kiwi 승격·mecab-ko 임시); 계약
`query_plan.LexicalTerm`.
구성: `normalize_query`/`detect_lang`/`NormalizeResult` — `korean.normalize` 재노출;
`KoreanNormalizeConfig`/`KoreanNormalizeTransformer` — Stage 5멤버 래퍼.
불변식·주의: 순수 정규화 로직 자체의 불변식(표시 뷰 NFC/렉시컬 뷰 NFKC 비혼용 등)은 `korean/
normalize.py`가 진다. 이 모듈은 플러그인 등록 표면만 책임진다.
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_planner.py`. `kiwipiepy` 미설치가 기본 테스트 경로.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rag_platform.contracts import common_types as ct
from rag_platform.korean.normalize import NormalizeResult, detect_lang, normalize_query, resolve_kiwi
from rag_platform.sdk.hashing import hash_of

__all__ = [
    "PLUGIN_VERSION",
    "KoreanNormalizeConfig",
    "KoreanNormalizeTransformer",
    "NormalizeResult",
    "detect_lang",
    "normalize_query",
]

PLUGIN_VERSION = "0.1.0"


class KoreanNormalizeConfig(BaseModel):
    """`query_transformer.korean_normalize`의 `config_schema`(04-pipelines/14 §2.3 표 초안)."""

    model_config = ConfigDict(extra="forbid")

    use_kiwi: bool | None = Field(default=None, description="테스트용 오버라이드. 기본은 자동 감지")


class KoreanNormalizeTransformer:
    """`QueryTransformer` 프로토콜 구현(04-pipelines/14 §1.1) — Stage 5멤버 래퍼.

    `retrieval/planner.py`는 바이블 §12 계층상 이 어댑터를 임포트할 수 없는 형제 계층이라(§0 참고)
    `plan()`은 `PluginRegistry` 배선 전까지 `rag_platform.korean.normalize.normalize_query()`를 직접
    호출한다(F4 배치 검증으로 해소 — `korean` 층은 `retrieval`·`adapters` 모두 import할 수 있다).
    """

    plugin_id = "query_transformer.korean_normalize"
    config_schema = KoreanNormalizeConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: KoreanNormalizeConfig | None = None) -> None:
        """설정을 고정한다."""
        self.config = config or KoreanNormalizeConfig()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """결정적 변환기 공통 선언(ADR-0032) — `in_process`, 재개 지원, `determinism=pure`."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=True,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=[],
            requires_gpu=False,
            extra={"determinism": "pure"},
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", analyzer_id)`(바이블 §6.2)."""
        _kiwi, analyzer_id = resolve_kiwi(use_kiwi=self.config.use_kiwi)
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", analyzer_id)

    async def run(self, draft: Any, _ctx: Any = None) -> Any:
        """`draft`(`PlanDraft`)의 질의 필드를 `normalize_query()` 결과로 채워 반환한다."""
        result = normalize_query(draft.request.query, use_kiwi=self.config.use_kiwi)
        draft.original_query = result.original_query
        draft.normalized_query = result.normalized_query
        draft.lexical_view = result.lexical_view
        draft.lang = result.lang
        draft.lexical_terms = result.lexical_terms
        draft.analyzer_id = result.analyzer_id
        # `korean.normalize.normalize_query()`는 `sdk`를 import할 수 없어(바이블 §12) `dictionary_hash`를
        # 채우지 않는다 — `H("dict")`는 `sdk.hashing`을 가진 이 어댑터가 직접 계산한다.
        draft.dictionary_hash = hash_of("dict")
        return draft
