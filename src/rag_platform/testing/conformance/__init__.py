"""플러그인 적합성(conformance) 키트 — 확장 지점 14종 pytest 기반 클래스 모음(바이블 §12 `testing`, 계층 스택 밖).

역할: `docs/10-development/06-plugin-development-guide.md` §8.1이 선언한 "확장 지점별 기반
클래스 상속" 방식의 실제 구현. 외부 `rag-plugin-*` 배포판과 이 저장소의 코어 어댑터가 똑같이
`rag_platform.testing.conformance`에서 자신의 확장 지점에 맞는 기반 클래스를 상속해 CI에서
6모듈(§8.1: `contract_roundtrip`/`idempotency`/`security_invariants`/...) 대신 이 문서가 실제로
좁혀 쓴 다섯 검사 — 5멤버 시그니처, 계약 입출력 타입, 멱등성, `StageError` 분류, `PluginMeta`
필수 필드·`license_grade` — 를 돌린다.
설계 근거: 위 가이드 §8.1(기반 클래스 표)·§3.1(5멤버)·§3.3(오류); ADR-0032(플러그인 SDK, 적합성 키트).
구성: `base` — 공용 믹스인(`PluginMetaConformance`/`StageErrorCatalogConformance`/
`StageSignatureConformance`/`ContractRoundtripConformance`/`IdempotencyConformance`)과
`default_stage_context()`; `kits` — 확장 지점 14종 각각의 완성된 기반 클래스와
`CONFORMANCE_KIT_BY_EXTENSION_POINT` 조회 표.
불변식: 프로덕션 진입점(`api`/`mcp`/`orchestration`)은 이 패키지를 임포트할 수 없다(import-linter
`testing-not-in-production`).
검증 계층: 1층(여기서 검증) — `tests/unit/conformance/`.
"""

from __future__ import annotations

from rag_platform.testing.conformance.base import (
    ConformanceKitBase,
    ContractRoundtripConformance,
    IdempotencyConformance,
    PluginMetaConformance,
    PortConformanceKitBase,
    StageConformanceBase,
    StageConformanceMethods,
    StageErrorCatalogConformance,
    StageSignatureConformance,
    default_stage_context,
    normalize_for_comparison,
)
from rag_platform.testing.conformance.kits import (
    CONFORMANCE_KIT_BY_EXTENSION_POINT,
    ChunkerConformance,
    EmbedderConformance,
    EnricherConformance,
    EvaluatorConformance,
    FetcherConformance,
    FuserConformance,
    IndexBackendConformance,
    NormalizerConformance,
    PackerConformance,
    ParserConformance,
    PostprocessorConformance,
    QueryTransformerConformance,
    RerankerConformance,
    RetrieverConformance,
)

__all__ = [
    "CONFORMANCE_KIT_BY_EXTENSION_POINT",
    "ChunkerConformance",
    "ConformanceKitBase",
    "ContractRoundtripConformance",
    "EmbedderConformance",
    "EnricherConformance",
    "EvaluatorConformance",
    "FetcherConformance",
    "FuserConformance",
    "IdempotencyConformance",
    "IndexBackendConformance",
    "NormalizerConformance",
    "PackerConformance",
    "ParserConformance",
    "PluginMetaConformance",
    "PortConformanceKitBase",
    "PostprocessorConformance",
    "QueryTransformerConformance",
    "RerankerConformance",
    "RetrieverConformance",
    "StageConformanceBase",
    "StageConformanceMethods",
    "StageErrorCatalogConformance",
    "StageSignatureConformance",
    "default_stage_context",
    "normalize_for_comparison",
]
