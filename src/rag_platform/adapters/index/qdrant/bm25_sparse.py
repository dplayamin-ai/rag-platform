"""`lite` BM25 sparse 벡터 계산 — 형태소 토큰을 BM25 TF 포화값(k1=1.2, b=0.75)으로 바꿔 `sparse_bm25`를 만든다.

설계 근거: ADR-0012(Qdrant는 BM25를 계산하지 않음 — TF 포화·길이 정규화는 클라이언트, IDF만 서버 `modifier: idf`),
04-pipelines/13 §6(적재 측)·04-pipelines/12 §12.3(계산식·`indices` 해시·`avgdl` 프로파일 상수 400),
ADR-0021(`korean_analyzer`: Kiwi는 `[kiwi]` extra 옵트인). 계약 타입: `IndexRecord.vectors.sparse_bm25`(`SparseVector`).

구성:
- `WhitespaceTokenizer` / `KiwiTokenizer` — 공백 폴백 / Kiwi 형태소(J*·E*·S* 태그 제거) 토크나이저
- `default_tokenizer()` — kiwipiepy가 설치되어 있으면 Kiwi, 없으면 공백 폴백
- `bm25_index(token)` — `int.from_bytes(blake3(utf8(token))[:4], "little")`(u32)
- `saturate(tf, dl, avgdl)` — 포화식 단일 구현; `document_vector`·`query_vector` — sparse 벡터 조립
- `validate_sparse(indices, values)` — 오름차순·유일·양수 검사(위반 `contract.violation`)

불변식: `tf`를 그대로 `values`에 넣는 경로는 없다(TF-IDF 퇴화 금지, 리스크 #5). 해시 충돌은 같은 인덱스의 `tf`를
합산한 뒤 포화한다. 질의 측 `values`(`tf_q`)의 정본은 04-pipelines/15 §3.5 — 여기서는 질의 토큰 빈도 원값만 낸다.
검증 계층: 1층(여기서 검증) — `tests/adapters/index/test_qdrant_local.py`(참조 포화식 일치 1e-9, 서버 IDF 결합).
DEFERRED: bm25s 참조 구현과의 상위 k 순위 일치(ADR-0012 준수 확인 (b))는 MIRACL-ko 표본이 필요해 2층에서 수행.
"""

from __future__ import annotations

import importlib
import importlib.util
import itertools
import unicodedata
from collections import Counter
from typing import Any, Protocol

from rag_platform.contracts.index_record import SparseVector
from rag_platform.sdk.hashing import blake3_hex
from rag_platform.sdk.stage import StageError

__all__ = [
    "BM25_B",
    "BM25_K1",
    "DEFAULT_AVGDL",
    "KiwiTokenizer",
    "SparseTokenizer",
    "WhitespaceTokenizer",
    "bm25_index",
    "default_tokenizer",
    "document_vector",
    "query_vector",
    "saturate",
    "validate_sparse",
]

_CONTRACT_VIOLATION = "contract.violation"

#: D-15 fixed saturation constants (ADR-0012, 04-pipelines/12 §12.3).
BM25_K1 = 1.2
BM25_B = 0.75
#: Profile constant `ingest.embed.sparse_bm25.avgdl` draft default (12 §12.3; part of the space `revision`).
DEFAULT_AVGDL = 400.0

#: Kiwi POS tag prefixes dropped before counting: particles (J*), endings (E*), symbols (S*) (13 §6 diagram).
_DROPPED_TAG_PREFIXES = ("J", "E", "S")
_U32_MAX = 0xFFFFFFFF


class SparseTokenizer(Protocol):
    """Minimal analyzer surface used here: an `analyzer_id` (= sparse `vocab_id`) and `tokenize`."""

    analyzer_id: str

    def tokenize(self, text: str) -> list[str]:
        """Return the lexical tokens of `text` in order (duplicates kept)."""
        ...


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


class WhitespaceTokenizer:
    """Fallback tokenizer: NFKC + lowercase + whitespace split, stripping surrounding punctuation."""

    analyzer_id = "whitespace:1.0:none"

    def tokenize(self, text: str) -> list[str]:
        """Split NFKC-lowercased `text` on whitespace; drop tokens that are punctuation only."""
        tokens = []
        for raw in _normalize(text).split():
            token = "".join(ch for ch in raw if not unicodedata.category(ch).startswith(("P", "S")))
            if token:
                tokens.append(token)
        return tokens


class KiwiTokenizer:
    """Kiwi morpheme tokenizer (`[kiwi]` extra, ADR-0021); keeps content morphemes only."""

    def __init__(self) -> None:
        """Load `kiwipiepy` lazily (optional, LGPL opt-in extra) and build one `Kiwi` instance."""
        kiwipiepy = importlib.import_module("kiwipiepy")
        self._kiwi: Any = kiwipiepy.Kiwi()
        self.analyzer_id = f"kiwi:{kiwipiepy.__version__}:default"

    def tokenize(self, text: str) -> list[str]:
        """Return lowercase morpheme forms of `text`, excluding J*/E*/S* tags."""
        return [
            str(token.form).lower()
            for token in self._kiwi.tokenize(unicodedata.normalize("NFKC", text))
            if not str(token.tag).startswith(_DROPPED_TAG_PREFIXES)
        ]


def default_tokenizer() -> SparseTokenizer:
    """Return `KiwiTokenizer` when `kiwipiepy` is importable, else `WhitespaceTokenizer`."""
    if importlib.util.find_spec("kiwipiepy") is not None:
        return KiwiTokenizer()
    return WhitespaceTokenizer()


def bm25_index(token: str) -> int:
    """Return the u32 sparse index of `token`: first 4 BLAKE3 bytes of `utf8(token)`, little-endian."""
    return int.from_bytes(bytes.fromhex(blake3_hex(token)[:8]), "little")


def saturate(tf: float, dl: float, avgdl: float, k1: float = BM25_K1, b: float = BM25_B) -> float:
    """BM25 TF saturation `tf*(k1+1) / (tf + k1*(1 - b + b*dl/avgdl))` (ADR-0012, D-15)."""
    if tf <= 0 or dl <= 0 or avgdl <= 0:
        msg = f"saturate() needs tf, dl, avgdl > 0 (got tf={tf}, dl={dl}, avgdl={avgdl})"
        raise ValueError(msg)
    return tf * (k1 + 1.0) / (tf + k1 * (1.0 - b + b * dl / avgdl))


def _counts(tokens: list[str]) -> Counter[int]:
    counts: Counter[int] = Counter()
    for token in tokens:
        counts[bm25_index(token)] += 1  # collisions: sum tf first, then saturate (12 §12.3)
    return counts


def document_vector(
    tokens: list[str], *, avgdl: float = DEFAULT_AVGDL, k1: float = BM25_K1, b: float = BM25_B
) -> SparseVector | None:
    """Build the document-side `sparse_bm25` vector; `None` when there are no tokens."""
    if not tokens:
        return None
    counts = _counts(tokens)
    dl = float(len(tokens))
    ordered = sorted(counts)
    values = [saturate(float(counts[i]), dl, avgdl, k1, b) for i in ordered]
    return SparseVector.model_validate({"indices": ordered, "values": values})


def query_vector(tokens: list[str]) -> SparseVector | None:
    """Build the query-side vector with raw query term frequency `tf_q(t)` (15 §3.5 owns the rule)."""
    if not tokens:
        return None
    counts = _counts(tokens)
    ordered = sorted(counts)
    return SparseVector.model_validate({"indices": ordered, "values": [float(counts[i]) for i in ordered]})


def validate_sparse(indices: list[int], values: list[float]) -> None:
    """Reject non-ascending/duplicate indices, length mismatch or non-positive values (13 §6 `indices`)."""
    problem = None
    if len(indices) != len(values):
        problem = "indices/values length mismatch"
    elif any(b <= a for a, b in itertools.pairwise(indices)):
        problem = "indices must be strictly ascending"
    elif any(i < 0 or i > _U32_MAX for i in indices):
        problem = "indices must be u32"
    elif any(v <= 0 for v in values):
        problem = "values must be > 0"
    if problem is not None:
        raise StageError(_CONTRACT_VIOLATION, stage="index", plugin_id="index_backend.qdrant", detail=problem)
