"""`IndexBackendConformance` 적합성 기반 클래스를 `testing.doubles.InMemoryIndexBackend`로 통과시키는 구체 테스트.

검증 대상: `rag_platform.testing.conformance.kits.IndexBackendConformance` — 역할 포트 프로토콜
준수, `upsert`의 `record_id` 멱등성(E17), `tenant_id` 검색 스코프(E7 보안 불변식), 그리고
`PluginMeta` 필수 필드·`license_grade`(D-02)·`StageError` 카탈로그(`index.*`) 검사.
설계 근거: `docs/10-development/06-plugin-development-guide.md` §5.6(index_backend 특유 적합성
항목), §8.1, 6A `testing/doubles/in_memory_index_backend.py`(무차별 대입 코사인 유사도, Qdrant
없음).
구성: `InMemoryIndexBackend`를 `IndexBackendConformance`에 연결하는 구체 테스트 클래스 하나.
검증 계층: 1층(여기서 검증) — Qdrant 없이 순수 파이썬 대역만으로 검증한다.
"""

from __future__ import annotations

from typing import Any, ClassVar

from rag_platform.testing.conformance.kits import IndexBackendConformance
from rag_platform.testing.doubles.in_memory_index_backend import InMemoryIndexBackend

_PLUGIN_META: dict[str, Any] = {
    "plugin_id": "index_backend.in_memory",
    "extension_point": "index_backend",
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
        "extra": {
            "supports_server_bm25": False,
            "korean_analyzer": False,
            "supports_server_fusion": [],
            "tenant_isolation": ["payload_filter"],
            "supports_alias_swap": False,
            "supports_multivector": False,
            "max_vector_dim": None,
            "max_multivector_elements": None,
            "supports_payload_only_points": None,
        },
    },
}


class TestInMemoryIndexBackendConformance(IndexBackendConformance):
    """`InMemoryIndexBackend`(무차별 대입 코사인 유사도, Qdrant 없음)의 적합성 통과를 확인한다."""

    plugin_meta: ClassVar[dict[str, Any]] = _PLUGIN_META

    def build_backend(self) -> InMemoryIndexBackend:
        """Return a fresh, empty `InMemoryIndexBackend` for each test."""
        return InMemoryIndexBackend()
