# sdk/python/

Python client SDK (proposed distribution `rag-platform-client`, import `rag_platform_client`;
name confirmed by docs/05-api/06-client-sdks.md). It reuses the contract models and becomes a uv
workspace member once its `pyproject.toml` exists (10-development/01 §3.1, §3.3).

Not to be confused with `src/rag_platform/sdk/`, the plugin and stage kernel SDK (01 §2.5).
Allowed imports: `rag_platform.contracts` only (01 §4.3).
