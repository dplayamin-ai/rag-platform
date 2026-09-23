# tests/

Repository tests (not shipped). The conformance kit that plugins import lives in
`src/rag_platform/testing/` instead (10-development/01 §2.5).

| Directory | Layer marker | External dependencies | Status |
|-----------|--------------|-----------------------|--------|
| `contracts/` | `contract` | none (schemas, doc examples, hash vectors) | bible §12 |
| `adapters/` | `component` | cassettes by default; live sidecars nightly | bible §12 |
| `security/` | `security` | compose `lite` for canary tenants | bible §12 |
| `replay/` | `integration` | `[temporal]` extra (`Replayer`, time-skipping environment) | bible §12 |
| `eval/` | `quality` | `[eval]` extra, small golden set | bible §12 |
| `golden/` | `component` | none (`FakeStageContext`) | 10-development/01 §7 |
| `unit/` | `unit` | none; mirrors `src/rag_platform/` | 10-development/01 §7 |
| `integration/` | `integration` | PostgreSQL, Valkey, Qdrant, TEI (mark `needs_docker`) | 10-development/01 §7 |
| `e2e/` | `e2e` | compose `lite` (mark `needs_docker`) | 10-development/01 §7 |

Layer markers are attached by `tests/conftest.py` from the directory. Tests that need Docker,
model weights, a GPU or external network carry `needs_docker`, `needs_model`, `needs_gpu` or
`needs_network` plus a `# DEFERRED: <what, where, how>` comment. They are excluded by default
(`pyproject.toml` addopts); run them with `uv run python tools/dev.py test-deferred`.
