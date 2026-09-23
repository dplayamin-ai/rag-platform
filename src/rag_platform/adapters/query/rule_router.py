"""`query_transformer.rule_router` — `RuleRouterTransformer` Stage 5멤버 래퍼(ADR-0032).

역할: `plan` 파이프 두 번째 단계(`router`)의 순수 구현(의도 분류·라우팅·전략 채택)은
`rag_platform.korean.rule_router`(바이블 §12상 `retrieval`도 import할 수 있는 `korean` 층)에 있다 —
이 모듈은 그 함수들을 재노출하고, `PluginRegistry`가 조회할 `QueryTransformer` 프로토콜 래퍼
(`config_schema`·`capabilities()`·`fingerprint()`·`run(draft, ctx)`)만 더한다.
설계 근거: 04-pipelines/14 §3.1(의도→계약 매핑)·§3.2(규칙 라우터, "항상 실행")·§3.4(`strategy_hint`
채택 조건); 바이블 §5.7 `Route`/`Complexity`/`Strategy`/`DegradedComponent`/`DegradedReason`.
구성: `classify_intent`/`route_for_intent`/`adopt_strategy`/`is_explanatory` — `korean.rule_router`
재노출; `RuleRouterConfig`/`RuleRouterTransformer` — Stage 5멤버 래퍼.
불변식·주의: 순수 라우팅 로직 자체의 불변식(외부 모델 미호출 등)은 `korean/rule_router.py`가 진다.
이 모듈은 플러그인 등록 표면만 책임진다.
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_planner.py`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from rag_platform.contracts import common_types as ct
from rag_platform.korean.rule_router import adopt_strategy, classify_intent, is_explanatory, route_for_intent
from rag_platform.sdk.hashing import hash_of

__all__ = [
    "PLUGIN_VERSION",
    "RuleRouterConfig",
    "RuleRouterTransformer",
    "adopt_strategy",
    "classify_intent",
    "is_explanatory",
    "route_for_intent",
]

PLUGIN_VERSION = "0.1.0"


class RuleRouterConfig(BaseModel):
    """`query_transformer.rule_router`의 `config_schema`(04-pipelines/14 §3.2 "어휘 목록 교체 가능")."""

    model_config = ConfigDict(extra="forbid")

    lexicon_ref: ct.ArtifactRef | None = None


class RuleRouterTransformer:
    """`QueryTransformer` 프로토콜 구현(04-pipelines/14 §1.1) — Stage 5멤버 래퍼.

    `retrieval/planner.py`는 `PluginRegistry` 배선 전까지 이 클래스가 아니라
    `rag_platform.korean.rule_router`의 `classify_intent`/`route_for_intent`/`adopt_strategy`를 직접
    호출한다(F4 배치 검증으로 해소 — `korean` 층은 `retrieval`·`adapters` 모두 import할 수 있다).
    """

    plugin_id = "query_transformer.rule_router"
    config_schema = RuleRouterConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: RuleRouterConfig | None = None) -> None:
        """설정을 고정한다(`lexicon_ref` 로딩은 DEFERRED — 내장 어휘 목록만 사용)."""
        self.config = config or RuleRouterConfig()

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
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(바이블 §6.2, 모델 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, hash_of("config", "{}"), "", "")

    async def run(self, draft: Any, _ctx: Any = None) -> Any:
        """`draft`(`PlanDraft`)의 `intent`/`route`/`complexity`/`strategy`/`degraded`를 채워 반환한다."""
        has_conversation = bool(draft.request.conversation)
        intent = classify_intent(draft.lexical_terms, draft.normalized_query, has_conversation=has_conversation)
        route, complexity = route_for_intent(intent)
        strategy, degraded = adopt_strategy(draft.request.strategy_hint)
        draft.intent = intent
        draft.route = route
        draft.complexity = complexity
        draft.strategy = strategy
        draft.degraded = [*draft.degraded, *degraded]
        return draft
