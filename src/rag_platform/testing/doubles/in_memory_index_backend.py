"""`InMemoryIndexBackend`: `sdk.ports.IndexBackend` double, brute-force cosine, no Qdrant.

# DEFERRED: verify against a real Qdrant cluster (gRPC, named vectors, payload filters,
# `is_current`/`index_generation` flip, bible §11.4) — `needs_docker` (phase-6 plan §8 tier 2).
# Track in `docs/12-appendix/09-deferred-verification-ledger.md`.
"""

from __future__ import annotations

import math
from typing import Any

__all__ = ["InMemoryIndexBackend"]


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        msg = f"vector length mismatch: {len(a)} vs {len(b)}"
        raise ValueError(msg)
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (norm_a * norm_b)


class InMemoryIndexBackend:
    """`IndexBackend` double: `upsert` stores `{id, tenant_id, vector?, text?}` records in a dict."""

    def __init__(self) -> None:
        """Start with an empty record store."""
        self._records: dict[str, dict[str, Any]] = {}

    def upsert(self, records: list[dict[str, object]]) -> None:
        """Insert or replace each record in `records`, keyed by its `id` field."""
        for record in records:
            self._records[str(record["id"])] = dict(record)

    def search_dense(self, tenant_id: str, vector: list[float], top_k: int) -> list[tuple[str, float]]:
        """Return up to `top_k` `(record_id, cosine_similarity)` pairs scoped to `tenant_id`."""
        scored = [
            (record_id, _cosine(vector, record["vector"]))
            for record_id, record in self._records.items()
            if record.get("tenant_id") == tenant_id and record.get("vector") is not None
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def search_lexical(self, tenant_id: str, query: str, top_k: int) -> list[tuple[str, float]]:
        """Return up to `top_k` `(record_id, term_overlap_count)` pairs scoped to `tenant_id`."""
        terms = set(query.lower().split())
        scored = []
        for record_id, record in self._records.items():
            if record.get("tenant_id") != tenant_id:
                continue
            text = str(record.get("text", "")).lower()
            hits = sum(1 for term in terms if term in text)
            if hits > 0:
                scored.append((record_id, float(hits)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
