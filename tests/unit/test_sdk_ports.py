"""`rag_platform.sdk.ports` 단위 테스트 — 역할별 포트 프로토콜이 구조적 타이핑으로 만족되는지 검증한다.

설계 근거: 바이블 §4.1(스테이지는 `ctx.token_counter`/`ctx.analyzer` 등 포트로만 시간·분석기에 접근),
`ADR-0032`(플러그인 SDK `Stage` 프로토콜과 포트 구조적 타이핑).

구성:
- `_WordCounter`/`_SpaceAnalyzer` — `TokenCounter`/`KoreanAnalyzer` 프로토콜을 만족하는 가짜 구현.
- `TokenCounter`/`KoreanAnalyzer`/`Embedder`/`IndexBackend` 각각을 대상 이중체(double)가 만족함을 확인.
- 필수 멤버(`count` 등)가 없는 객체는 프로토콜을 만족하지 않음을 확인.

불변식: 모든 포트는 `runtime_checkable` `Protocol`이며 상속이 아니라 구조로 판별된다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from rag_platform.sdk.ports import Embedder, IndexBackend, KoreanAnalyzer, TokenCounter
from rag_platform.testing.doubles.fake_embedder import FakeEmbedder
from rag_platform.testing.doubles.in_memory_index_backend import InMemoryIndexBackend


class _WordCounter:
    tokenizer_id = "hf:BAAI/bge-m3"

    def count(self, text: str) -> int:
        return len(text.split())


class _SpaceAnalyzer:
    analyzer_id = "mecab-ko"

    def normalize(self, text: str) -> str:
        return text.strip()

    def tokenize(self, text: str) -> tuple[str, ...]:
        return tuple(text.split())


def test_token_counter_protocol_is_satisfied_structurally() -> None:
    assert isinstance(_WordCounter(), TokenCounter)
    assert _WordCounter().count("hello world") == 2


def test_korean_analyzer_protocol_is_satisfied_structurally() -> None:
    analyzer = _SpaceAnalyzer()
    assert isinstance(analyzer, KoreanAnalyzer)
    assert analyzer.tokenize("정보공개 청구") == ("정보공개", "청구")


def test_fake_embedder_satisfies_embedder_protocol() -> None:
    assert isinstance(FakeEmbedder(), Embedder)


def test_in_memory_index_backend_satisfies_index_backend_protocol() -> None:
    assert isinstance(InMemoryIndexBackend(), IndexBackend)


def test_token_counter_protocol_rejects_object_without_count() -> None:
    class _NotACounter:
        tokenizer_id = "x"

    assert not isinstance(_NotACounter(), TokenCounter)
