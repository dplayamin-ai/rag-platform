"""Unit tests for `rag_platform.sdk.ports` role-port protocols (bible §4.1, ADR-0032)."""

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
