"""`embedder.sparse_bm25` — `lite` 프로파일의 클라이언트측 BM25 sparse 벡터 생산자(F3-01, WP-301).

역할: `EnrichedChunkSet.enrichments[chunk_id].index_text`를 형태소 토큰화해
`common_types.SparseBm25`(TF 포화값)와 그 공간 식별자를 만든다. `embed` 스테이지가 이 모듈을 불러
"공간 계산"만 맡기고, 실제 토큰화는 (있으면) `ctx.analyzer`가, 없으면 이 모듈의 폴백 토크나이저가 한다.
설계 근거: 04-pipelines/12 §9(2) "생산은 embed 스테이지", §12("책임 경계" 표 — 입력은 `index_text`),
§12.3(토큰 해시·포화식·공간 입력 레시피, 이 문서가 확정); ADR-0012(Qdrant는 BM25를 계산하지 않음).
BM25 산술(토큰화·해시·TF 포화)은 `adapters.index.qdrant.bm25_sparse`(D-15 고정 상수, ADR-0021 Kiwi)의
공개 심볼을 그대로 재사용한다 — 두 곳에 같은 수식을 베끼지 않는다(§9(2) "SDK 단일 구현"의 근사;
`sdk/`로 옮기는 것은 공용 파일 변경이라 이 WP 범위 밖, WP 문서 open_issues 참조).
구성: `tokens_to_sparse_bm25` — 토큰 목록 → `SparseBm25`(해시 충돌은 tf 합산 후 포화); `sparse_bm25_revision`/
`sparse_bm25_space_id` — §12.3 공간 입력 레시피; `SparseBm25Embedder` — 플러그인 표면(기본 토크나이저는
하네스 폴백일 뿐, `ctx.analyzer`가 있으면 스테이지가 그것을 우선한다).
불변식·주의: `qdrant/bm25_sparse.py`는 import만 하고 손대지 않는다. 토큰이 없으면 빈 `indices`/`values`를
내지 `None`을 내지 않는다 — `VectorBundle2.sparse_bm25`는 필수 필드(계약)라 결측을 허용하지 않는다.
검증 계층: 1층(여기서 검증) — `tests/adapters/embed/test_embed_stage.py`. `needs_model`/`needs_network`
해당 없음(순수 함수 + 공백 폴백 토크나이저).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rag_platform.adapters.embed import space_id
from rag_platform.adapters.index.qdrant.bm25_sparse import (
    BM25_B,
    BM25_K1,
    DEFAULT_AVGDL,
    SparseTokenizer,
    bm25_index,
    default_tokenizer,
    saturate,
)
from rag_platform.contracts.common_types import Indice, SparseBm25
from rag_platform.sdk.hashing import hash_of

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "PLUGIN_ID",
    "SparseBm25Embedder",
    "sparse_bm25_revision",
    "sparse_bm25_space_id",
    "tokens_to_sparse_bm25",
]

PLUGIN_ID = "embedder.sparse_bm25"
PLUGIN_VERSION = "0.1.0"
#: doc 12 sec 12.3 공간 입력 레시피의 고정 부분(`model_id`/해시 공간 차원/비정규화/무프롬프트).
_SPACE_MODEL_ID = "rag_platform/sparse_bm25"
_SPACE_DIM = 2**32
_EMPTY_PROMPT_HASH = hash_of("config", "{}")  # doc 12 sec 2.5 "빈 객체의 해시"; sparse_bm25는 프롬프트 없음
#: doc 12 sec 12.1 rule 4 관례(저장 크기): float32 반올림 6자리. sparse_bm25 값에도 그대로 적용한다.
_VALUE_ROUND_NDIGITS = 6


def tokens_to_sparse_bm25(
    tokens: Sequence[str],
    *,
    vocab_id: str,
    avgdl: float = DEFAULT_AVGDL,
    k1: float = BM25_K1,
    b: float = BM25_B,
) -> SparseBm25:
    """형태소 `tokens`(`index_text` 토큰화 결과)로 `sparse_bm25` 벡터 하나를 만든다(doc 12 sec 12.3).

    해시 충돌(`bm25_index` 값이 같은 서로 다른 토큰)은 같은 인덱스의 `tf`를 합산한 뒤 포화한다
    (`qdrant.bm25_sparse` docstring "해시 충돌은 같은 인덱스의 tf를 합산한 뒤 포화").

    Args:
        tokens: 형태소 원형(NFKC) 목록, 순서 무관(빈도만 쓴다).
        vocab_id: `= analyzer_id`(doc 12 sec 12.3 "vocab_id = analyzer_id").
        avgdl: 프로파일 상수(초안 400, doc 12 sec 12.3).
        k1: BM25 포화 상수(D-15 고정 1.2).
        b: BM25 길이 정규화 상수(D-15 고정 0.75).

    Returns:
        `SparseBm25{name="sparse_bm25", vocab_id, indices, values}`. `tokens`가 비었으면 빈
        `indices`/`values`(계약 필수 필드라 `None`을 내지 않는다).
    """
    if not tokens:
        return SparseBm25(name="sparse_bm25", vocab_id=vocab_id, indices=[], values=[])
    counts: Counter[int] = Counter(bm25_index(token) for token in tokens)
    dl = float(len(tokens))
    ordered = sorted(counts)
    values = [round(saturate(float(counts[i]), dl, avgdl, k1, b), _VALUE_ROUND_NDIGITS) for i in ordered]
    return SparseBm25(name="sparse_bm25", vocab_id=vocab_id, indices=[Indice(i) for i in ordered], values=values)


def sparse_bm25_revision(
    *, k1: float = BM25_K1, b: float = BM25_B, avgdl: float = DEFAULT_AVGDL, dictionary_hash: str
) -> str:
    """§12.3 공간 `revision = H("config", canonical_json({k1, b, avgdl, dictionary_hash}))`.

    사용자 사전 변경(`dictionary_hash`)이 공간을 바꾸도록 revision에 포함한다(doc 12 sec 11.2 표
    "분석기·사용자 사전 변경(lite sparse_bm25)").
    """
    canonical = json.dumps(
        {"k1": k1, "b": b, "avgdl": avgdl, "dictionary_hash": dictionary_hash},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hash_of("config", canonical)


def sparse_bm25_space_id(
    *,
    analyzer_id: str,
    dictionary_hash: str,
    k1: float = BM25_K1,
    b: float = BM25_B,
    avgdl: float = DEFAULT_AVGDL,
) -> str:
    """`embedding_space_ids.sparse_bm25`(doc 12 sec 12.3 레시피 그대로, `Hex64` 산출)."""
    revision = sparse_bm25_revision(k1=k1, b=b, avgdl=avgdl, dictionary_hash=dictionary_hash)
    return space_id(
        model_id=_SPACE_MODEL_ID,
        revision=revision,
        dim=_SPACE_DIM,
        normalized=False,
        prompt_hash_value=_EMPTY_PROMPT_HASH,
        quantization="none",
        vocab_id=analyzer_id,
    )


@dataclass
class SparseBm25Embedder:
    """`embedder.sparse_bm25` 플러그인 표면 — 하네스 폴백 토크나이저 + 공간 ID 계산.

    `EmbedStage`는 `ctx.analyzer`(`sdk.ports.KoreanAnalyzer`)가 있으면 그것으로 토큰화하고, 이
    인스턴스의 `tokenizer`/`analyzer_id`는 `ctx.analyzer`가 없는 하네스·테스트 경로에서만 쓰인다
    (doc 12 sec 12.3 "token은 ctx.analyzer가 낸 형태소").
    """

    tokenizer: SparseTokenizer = field(default_factory=default_tokenizer)
    k1: float = BM25_K1
    b: float = BM25_B
    avgdl: float = DEFAULT_AVGDL
    dictionary_hash: str = field(default_factory=lambda: hash_of("dict"))
    plugin_id: str = PLUGIN_ID

    @property
    def analyzer_id(self) -> str:
        """`= vocab_id`(doc 12 sec 12.3), 폴백 토크나이저의 `analyzer_id` 그대로."""
        return self.tokenizer.analyzer_id

    @property
    def embedding_space_id(self) -> str:
        """이 인스턴스의 설정(토크나이저·상수·사전)으로 계산한 `sparse_bm25` 공간 `Hex64`."""
        return sparse_bm25_space_id(
            analyzer_id=self.analyzer_id, dictionary_hash=self.dictionary_hash, k1=self.k1, b=self.b, avgdl=self.avgdl
        )

    def tokenize(self, text: str) -> list[str]:
        """폴백 토크나이저로 `text`를 형태소 토큰 목록으로 분해."""
        return self.tokenizer.tokenize(text)

    def embed_documents(self, texts: list[str]) -> list[SparseBm25]:
        """문서 각각의 `index_text`를 이 인스턴스의 토크나이저로 토큰화해 `sparse_bm25` 벡터를 낸다."""
        return [
            tokens_to_sparse_bm25(
                self.tokenize(text), vocab_id=self.analyzer_id, avgdl=self.avgdl, k1=self.k1, b=self.b
            )
            for text in texts
        ]
