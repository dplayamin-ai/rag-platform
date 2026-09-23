"""Conformance-kit test doubles (bible §12 `testing`, outside the layer stack).

Each double implements a protocol defined in the production layer it stands in for
(`ledger.repo.Ledger`, `storage.valkey.KeyValueCache`, `sdk.ports.Embedder`,
`sdk.ports.IndexBackend`) so unit tests can exercise callers without PostgreSQL, Valkey, a TEI
server or a Qdrant cluster. Every module below carries a ``# DEFERRED:`` comment pointing at where
the real, `needs_docker`/`needs_model`/`needs_network` implementation is verified instead (phase-6
plan §8 three-tier verification).

Production entry points (`api`, `mcp`, `orchestration`) must never import this package
(import-linter `testing-not-in-production`, 10-development/01 §4.2).
"""

from __future__ import annotations
