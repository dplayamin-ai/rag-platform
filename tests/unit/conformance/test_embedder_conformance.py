"""`EmbedderConformance` 적합성 기반 클래스를 `testing.doubles.FakeEmbedder`로 통과시키는 구체 테스트.

검증 대상: `rag_platform.testing.conformance.kits.EmbedderConformance` — 역할 포트 프로토콜
준수, `embed_documents`/`embed_query` 결정성(멱등성), 선언된 `dim`/`normalized`와의 일관성,
그리고 이 기반 클래스가 공유하는 `PluginMeta` 필수 필드·`license_grade`(D-02)·`StageError`
카탈로그(`embed.*`) 검사.
설계 근거: `docs/10-development/06-plugin-development-guide.md` §8.1, `sdk/ports.py`(embedder는
정합성 페이크의 최소 표면), 6A `testing/doubles/fake_embedder.py`(sha256 결정적 벡터, 모델
가중치 없음 — 2026-09-23 사용자 결정).
구성: `FakeEmbedder`를 `EmbedderConformance`에 연결하는 구체 테스트 클래스 하나.
불변식: `FakeEmbedder`는 같은 입력에 항상 같은 벡터를 반환한다(결정성) — 이 테스트가 그 성질과
선언된 `dim`/`normalized`의 일관성을 함께 지킨다.
검증 계층: 1층(여기서 검증) — 모델 가중치 없음(결정적 해시 기반), `needs_model` 불필요.
"""

from __future__ import annotations

from typing import Any, ClassVar

from rag_platform.testing.conformance.kits import EmbedderConformance
from rag_platform.testing.doubles.fake_embedder import FakeEmbedder

_PLUGIN_META: dict[str, Any] = {
    "plugin_id": "embedder.fake_hash",
    "extension_point": "embedder",
    "version": "1.0.0",
    "license": "Apache-2.0",
    "license_grade": "A",
    "territory": ["KR"],
    "linkage": "pure_python",
    "isolation_supported": ["in_process"],
    "contracts_compat": ">=1.0,<2.0",
    "capabilities": {
        "isolation_modes": ["in_process"],
        "supports_resumable": False,
        "contracts_compat": ">=1.0,<2.0",
    },
}


class TestFakeEmbedderConformance(EmbedderConformance):
    """`FakeEmbedder`(sha256 결정적 해시 벡터, 모델 가중치 없음)의 적합성 통과를 확인한다."""

    plugin_meta: ClassVar[dict[str, Any]] = _PLUGIN_META

    def build_embedder(self) -> FakeEmbedder:
        """Return a fresh `FakeEmbedder` (dim=16, normalized=True — the double's defaults)."""
        return FakeEmbedder()
